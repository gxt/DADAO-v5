#!/usr/bin/env python3
"""check-knowledge-refs: 被引用的 `.work/**` 材料不得悬空 (INFRA-058t / INTEG-037t)。

背景（用户 2026-10-11 裁定「认 + 并入 INFRA-058t」，`lessons §3.16`）：
  - `.work/` 被 `.gitignore` 整体忽略、只在本机存在 ⇒ 仅放 `.work/` 的**被引用材料**
    会**悬空**、不可复现。
  - 归类判据（四分类）：`spec/` = 规范正文；`.tao/knowledge/` = 结论/设计/口径（含长文）；
    `.work/log/` = 一次性过程（可删）；**凡被引用的材料，一律不得只放 `.work/`**。

本门控机械做的事（**悬空即红**）：
  扫描 `AGENTS.md` / `spec/**/*.md` / `.tao/knowledge/**/*.md` / `.tao/tasks/**/*.md`
  / `.tao/contracts/**/*.md` 中对 `.work/**` 的引用；对**可判定的具体路径**做存在性检查，不存在即 FAIL。

引用形态口径（详见 AGENTS.md「文档分层与单一真源」与 lessons §3.16）：
  - `<>` / `*` / `$` 形（占位或通配，如 `.work/log/<模块>/`、`.work/log/**`、
    `.work/log/testcases/TESTCASES-036t-*.log`）⇒ **不可判定，跳过**；
  - 以 `-` 结尾（前缀截断，如 `.work/log/testcases/TESTCASES-039t-`）⇒ **跳过**；
  - 位于「删除语境」行（含 `已删`/`删旧`/`删除`/`deleted`/`removed`）的引用 ⇒ 记录
    「历史/删除引用」，**不要求存在**；
  - `.work/build/**`、`.work/source/**`（构建/源码树，`clean-work` 即清）⇒ **显式豁免**；
  - 其余具体路径 ⇒ **要求存在**（文件或目录），不存在即红。

fail-closed: 有悬空 → exit 1; 无悬空 → exit 0。

Usage:
    python3 tools/infra/check_knowledge_refs.py [--root DIR]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# 引用 token：`.work/` 后接路径字符；遇空白 / 反引号 / CJK 等即止。
_REF_RE = re.compile(r"\.work/[A-Za-z0-9_./<>*$-]+")

# 占位/通配/不可判定标记。
_PLACEHOLDER_CHARS = ("<", ">", "*", "$")

# 删除语境标记（历史引用：记录「某路径已删」，不要求其存在）。
_DELETION_MARKERS = ("已删", "删旧", "删除", "删掉", "deleted", "removed")

# 构建/源码树豁免（`clean-work` 即清；risk B）。
_EXEMPT_PREFIXES = (".work/build", ".work/source")


def _is_exempt(path: str) -> bool:
    for p in _EXEMPT_PREFIXES:
        if path == p or path.startswith(p + "/"):
            return True
    return False


def _classify(raw: str) -> str:
    """Return one of: 'skip_placeholder', 'skip_prefix', 'exempt', 'check'."""
    tok = raw
    if any(c in tok for c in _PLACEHOLDER_CHARS):
        return "skip_placeholder"
    # strip a trailing sentence period (paths never end with '.')
    tok = tok.rstrip(".")
    if tok.endswith("-"):
        return "skip_prefix"
    if _is_exempt(tok):
        return "exempt"
    # path used for existence check is the cleaned token
    return "check"


def _scan_files(root: Path) -> list[Path]:
    files: list[Path] = []
    agents = root / "AGENTS.md"
    if agents.is_file():
        files.append(agents)
    for sub in ("spec", ".tao/knowledge", ".tao/contracts", ".tao/tasks"):
        d = root / sub
        if d.is_dir():
            files.extend(sorted(d.rglob("*.md")))
    return files


def audit(root: Path) -> int:
    files = _scan_files(root)
    if not files:
        print("ERROR: no scannable files found (AGENTS.md / spec / .tao/knowledge / .tao/contracts / .tao/tasks)",
              file=sys.stderr)
        return 1

    found = 0                 # total `.work/` refs seen
    checked = 0               # concrete paths existence-checked
    dangling: list[tuple[str, int, str]] = []
    n_placeholder = 0
    n_prefix = 0
    n_exempt = 0
    n_deleted = 0

    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for m in _REF_RE.finditer(line):
                found += 1
                raw = m.group(0)
                kind = _classify(raw)
                if kind == "skip_placeholder":
                    n_placeholder += 1
                    continue
                if kind == "skip_prefix":
                    n_prefix += 1
                    continue
                if kind == "exempt":
                    n_exempt += 1
                    continue
                # deletion-context historical reference: record, do not require existence
                if any(mk in line for mk in _DELETION_MARKERS):
                    n_deleted += 1
                    continue
                checked += 1
                tok = raw.rstrip(".")
                if not (root / tok).exists():
                    dangling.append((str(f.relative_to(root)), lineno, tok))

    print("=" * 72)
    print("check-knowledge-refs — 被引用 `.work/**` 材料悬空检查")
    print("=" * 72)
    print(f"  扫描文件数: {len(files)}")
    print(f"  `.work/` 引用总数: {found}")
    print(f"    占位/通配 (跳过): {n_placeholder}")
    print(f"    前缀截断 (跳过): {n_prefix}")
    print(f"    构建/源码 (豁免): {n_exempt}")
    print(f"    删除语境 (历史): {n_deleted}")
    print(f"    具体路径 (校验): {checked}")
    print(f"  悬空: {len(dangling)}")
    if dangling:
        print()
        for rel, lineno, tok in dangling:
            print(f"    {rel}:{lineno}  {tok}")
    print("-" * 72)

    # §2.20 自证命中：扫描面必须确有 `.work/` 引用被判定，否则判为「空转」而 FAIL。
    if checked == 0:
        print("ERROR: 无任何可校验的 `.work/**` 引用（扫描面为空 ⇒ 门控空转，fail-closed）",
              file=sys.stderr)
        print("结果: FAIL (vacuous: no checkable .work/** refs)")
        return 1
    if dangling:
        print(f"结果: FAIL ({len(dangling)} 悬空引用)")
        return 1
    print("结果: PASS (0 悬空引用)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path,
                        default=Path(__file__).resolve().parents[2],
                        help="repository root (default: repo root)")
    args = parser.parse_args()
    return audit(args.root.resolve())


if __name__ == "__main__":
    sys.exit(main())
