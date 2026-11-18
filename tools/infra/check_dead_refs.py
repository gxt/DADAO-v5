#!/usr/bin/env python3
"""check_dead_refs.py -- 仓内路径常量的死引用检查（m15-infra-004；**尚未接入门控**）。

背景：`.tao/knowledge/` 下 `refs/` 目录清空（`m15-infra-002`/`m15-infra-004`）暴露了一类问题——
代码里的**路径常量**指向已删文件，静态阶段没人报，只在运行时才断（长尾驱动、
`check-gem5-decode`、`--check` 复现都不经过门控）。本脚本把「**常量**指向不存在的
仓内路径」一次性列出来。用户 2026-11-18 裁定：**先出脚本，不注册 Makefile 目标、
不接 `make check`**。

扫描面（只这三处，不扩张）：
  * `tools/**/*.py`、`tests/**/*.py` —— **模块级**常量（顶层赋值右值），
    用 `ast` 解析：字符串常量 + **全常量**的 `os.path.join(...)` / `Path()/"..."`
    折叠结果；f-string 插值不折叠（不可判定）；函数体里的字面量**不算常量**
    （自测/注入用的临时树 fixture 都在函数体内，按此口径天然排除）。
  * `Makefile` —— **变量赋值**的右值（`NAME = ...` / `:=` / `+=` / `?=`），
    注释与 recipe 里的散文不算常量（recipe 里 `docs/Process-07` 这类简称是
    文档名，不是路径）。

判定口径：
  * **仓内路径** = 首段是该树 **git 跟踪**的顶层条目（`git ls-tree HEAD`，现场派生、
    不写死目录名；非 git 树回退到文件系统清单）。`src/arch/...`、`include/...` 这类
    **上游/组件内**路径首段不在顶层 ⇒ 天然跳过，不误报；而 `tests/...`、`.tao/...`、
    `tools/...` 的口径错误会被抓到。
  * `.work/`、`.cache/`、`.dadao/` 是构建/参考/安装**运行期树**（都不在 git 里），
    显式排除——否则「本机装没装工具链」会改变判定，fresh clone 与主控机结论不一致。
  * 另排除：`/tmp/**`、URL（`scheme://`）、glob/占位（`*` `?` `[` `{` `<` `>` `$` `~`）、
    含 `:` 的 `file:line`/`refs/heads/...` 形 token、含空白或反斜杠的串；
  * 去掉行尾标点（`.` `,` `;`）与截断后缀 `-` 后再判（散文里常见的
    「…paths.py.」「docs/Process-01-」不算候选）。

**只报告、不修改**：不存在 ≠ 一定错（也可能是运行期才生成的产物），所以脚本只
打印 `文件:行: 路径`，由人判断是否真死引用。

已知的**非活引用**（`NON_LIVE`）逐条列出、每次运行都打印，不计入 FAIL：现只剩
**自测 fixture**（写在临时树里、真树不该有）。**新增**死引用（不在表内）才判红；
表只许逐条收窄，且表项若已不再缺失 ⇒ 打印 `STALE` 提示删除（防白名单腐烂）。

用法::

    python3 tools/infra/check_dead_refs.py             # 检查当前树
    python3 tools/infra/check_dead_refs.py --root DIR  # 检查另一棵树
    python3 tools/infra/check_dead_refs.py --verbose   # 逐条打印已解析的候选
    python3 tools/infra/check_dead_refs.py --strict    # 非活引用也判红

退出码：0 = 候选全部存在（或只剩非活引用）；1 = 有**新增**缺失（逐条列出）；
2 = 扫描面空转（一个候选都没解析到，fail-closed，防「候选规则改坏了还报绿」）。
"""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parents[2]

#: 非活引用（逐条、带引用处与理由；**只许收窄**）。每次运行都打印，不计 FAIL：
#: 现只剩**自测 fixture**（文件写在临时树里、真树不该有）——不是活消费者的路径。
#: 按**路径**匹配（同一路径多处出现一并列出）。新增死路径不在表内 ⇒ 判红。
NON_LIVE = {
    "tests/inst/aa/aa.inc":
        ("tools/testcases/check_inst_macro_scope.py:560（`FIXTURE` 表）",
         "自测 fixture：文件写在临时树里，真树不该有"),
    "tests/inst/aa/one.S":
        ("tools/testcases/check_inst_macro_scope.py:575（`FIXTURE` 表）",
         "自测 fixture：文件写在临时树里，真树不该有"),
    "tests/inst/bb/one.S":
        ("tools/testcases/check_inst_macro_scope.py:590（`FIXTURE` 表）",
         "自测 fixture：文件写在临时树里，真树不该有"),
}

# 整体排除的子树（构建/参考/安装运行期树，均不在 git 里）。
EXCLUDED_PREFIXES = (".work/", ".cache/", ".dadao/")
EXCLUDED_ABSOLUTE = ("/tmp/", "/dev/", "/proc/", "/sys/")

# 一段路径字符：允许点开头（`.tao`），不含 glob/占位/空白/冒号。
_SEGMENT_RE = re.compile(r"^\.?[A-Za-z0-9_][A-Za-z0-9_.+-]*$")
_FORBIDDEN = set('*?[]{}<>$~\\|"\'`')
_ASSIGN_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*(?::=|\+=|\?=|=)\s*(.+)$")
_TOKEN_RE = re.compile(r"[A-Za-z0-9_.][A-Za-z0-9_./+-]*")


def _top_entries(root: Path) -> set[str]:
    """顶层条目：取 git 跟踪面（确定性），非 git 树回退到文件系统清单。"""
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "ls-tree", "--name-only", "HEAD"],
            capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        out = ""
    entries = {line.strip() for line in out.splitlines() if line.strip()}
    if entries:
        return entries
    return {p.name for p in root.iterdir()}


def _candidate(text: str, top: set[str]) -> str | None:
    """把一段字符串判成「仓内路径」并归一，否则 None。"""
    text = text.strip()
    # 散文里的行尾标点 / 前缀截断：`…paths.py.`、`docs/Process-01-`
    while text and text[-1] in ".,;":
        text = text[:-1]
    if text.endswith("-") or len(text) < 3:
        return None
    if any(ch in _FORBIDDEN or ch.isspace() for ch in text):
        return None
    if "://" in text or ":" in text:
        return None
    if text.startswith(EXCLUDED_ABSOLUTE) or text.startswith(("/", "~")):
        return None
    segs = text.split("/")
    if len(segs) < 2:
        return None
    if any(s in ("", ".", "..") or ".." in s for s in segs):
        return None
    if not all(_SEGMENT_RE.match(s) for s in segs):
        return None
    if segs[0] not in top:
        return None
    norm = "/".join(segs)
    if any(norm.startswith(p) for p in EXCLUDED_PREFIXES):
        return None
    return norm


def _fold(node: ast.AST) -> str | None:
    """全常量的路径表达式折叠（字符串 / os.path.join / Path()/… ）。"""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        left = _fold(node.left)
        right = _fold(node.right)
        if left is None or right is None:
            return None
        return left.rstrip("/") + "/" + right.strip("/")
    if isinstance(node, ast.Call):
        name = ""
        if isinstance(node.func, ast.Attribute):
            name = node.func.attr
        elif isinstance(node.func, ast.Name):
            name = node.func.id
        args = [_fold(a) for a in node.args]
        if any(a is None for a in args):
            return None
        if name == "join" and args:
            return "/".join(a.strip("/") for a in args)
        if name in ("Path", "PurePath", "PosixPath") and len(args) == 1:
            return args[0]
    return None


def _module_constants(tree: ast.Module):
    """模块级赋值的右值（含 class/模块级 AnnAssign）；函数体内的字面量不算常量。"""
    nodes = []
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign):
            nodes.extend(stmt.value.elts if isinstance(stmt.value, ast.Tuple)
                         else [stmt.value])
        elif isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
            nodes.append(stmt.value)
        elif isinstance(stmt, ast.ClassDef):
            for sub in stmt.body:
                if isinstance(sub, ast.Assign):
                    nodes.extend(sub.value.elts
                                 if isinstance(sub.value, ast.Tuple) else [sub.value])
    return nodes


def scan_python(path: Path, top: set[str]) -> list[tuple[int, str]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError) as exc:  # 解析不了就响亮报错
        print(f"check_dead_refs: WARN cannot parse {path}: {exc}", file=sys.stderr)
        return []
    found: set[tuple[int, str]] = set()
    for root_node in _module_constants(tree):
        for node in ast.walk(root_node):
            value = _fold(node)
            if value is None:
                continue
            cand = _candidate(value, top)
            if cand is not None:
                found.add((getattr(node, "lineno", 0), cand))
    return sorted(found)


def scan_makefile(path: Path, top: set[str]) -> list[tuple[int, str]]:
    """只取变量赋值的右值（注释/recipe 的散文不算路径常量）。"""
    found: set[tuple[int, str]] = set()
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue
        m = _ASSIGN_RE.match(line)
        if not m:
            continue
        for token in _TOKEN_RE.findall(m.group(2)):
            cand = _candidate(token, top)
            if cand is not None:
                found.add((lineno, cand))
    return sorted(found)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="扫 tools/**, tests/** 的模块级路径常量与 Makefile 变量赋值，"
                    "指向不存在路径即非零退出（只报告，不接门控）。")
    ap.add_argument("--root", default=str(DEFAULT_ROOT),
                    help="仓库根（默认 = 本脚本上溯两层）")
    ap.add_argument("--verbose", action="store_true", help="逐条打印已解析的候选")
    ap.add_argument("--strict", action="store_true",
                    help="非活引用（NON_LIVE）也判红")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    if not (root / "Makefile").is_file():
        print(f"check_dead_refs: not a repo root (no Makefile): {root}", file=sys.stderr)
        return 2
    top = _top_entries(root)

    hits: list[tuple[str, int, str]] = []  # (file, line, candidate)
    scanned_files = 0
    self_path = Path(__file__).resolve()
    for path in sorted(root.glob("tools/**/*.py")) + sorted(root.glob("tests/**/*.py")):
        if path.resolve() == self_path:
            continue  # NON_LIVE 表本身是数据，不是引用
        rel = path.relative_to(root).as_posix()
        scanned_files += 1
        for line, cand in scan_python(path, top):
            hits.append((rel, line, cand))
    scanned_files += 1
    for line, cand in scan_makefile(root / "Makefile", top):
        hits.append(("Makefile", line, cand))

    candidates = len({(f, line, cand) for f, line, cand in hits})
    missing = sorted({(f, line, cand) for f, line, cand in hits
                      if not (root / cand).exists()})
    pre = [(f, line, cand) for f, line, cand in missing if cand in NON_LIVE]
    new = [(f, line, cand) for f, line, cand in missing if cand not in NON_LIVE]

    if args.verbose:
        for f, line, cand in sorted({(f, line, cand) for f, line, cand in hits}):
            print(f"  candidate {f}:{line}: {cand}")
    for cand, (owner, why) in NON_LIVE.items():
        if any(c == cand for _f, _l, c in pre):
            print(f"check_dead_refs: NON-LIVE {cand} ({owner}; {why})")
        else:
            print(f"check_dead_refs: STALE table entry {cand} -- no longer missing, "
                  f"prune it from NON_LIVE")

    print(f"check_dead_refs: scanned {scanned_files} file(s), "
          f"{candidates} repo-path constant(s), "
          f"{len(new)} missing, {len(pre)} non-live")

    if candidates == 0:
        print("check_dead_refs: FAIL: no repo-path constant found "
              "(vacuous scan -- the candidate rule is broken)", file=sys.stderr)
        return 2
    if new:
        print("check_dead_refs: FAIL: constants point at missing paths:",
              file=sys.stderr)
        for f, line, cand in new:
            print(f"  {f}:{line}: {cand}", file=sys.stderr)
        return 1
    if pre and args.strict:
        print("check_dead_refs: FAIL (--strict): non-live dead refs remain",
              file=sys.stderr)
        return 1
    print("check_dead_refs: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
