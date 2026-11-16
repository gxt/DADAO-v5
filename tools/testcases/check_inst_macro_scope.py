#!/usr/bin/env python3
r"""check_inst_macro_scope.py — 汇编宏**作用域**门控（L1；m15-testcases-002）。

判据（用户 2026-11-15/16 口径：「如果某个宏就只用于某个汇编测试程序，则应该把这个
宏移动到该汇编测试中」）——三层，任一违反即红：

  S1 **共享层只放跨册宏**：`tests/inst/macros/inst_test.inc` 里每个宏的使用者必须
     覆盖 **≥2 个册**（`tests/inst/<册>/`）；
  S2 **册 `.inc` 只放本册宏**：`tests/inst/<册>/<册>.inc` 里每个宏的使用者必须全部
     在该册内；
  S3 **`.S` 内定义的宏只被该文件使用**；
  S4 **死宏 = 0**：三层任一宏若无使用者 ⇒ 红；
  S5 **include 接线**：每个 `.S` 必须 `.include` 共享层**一次**；该册有 `<册>.inc`
     时必须在其后 `.include` 一次（顺序 = 共享层在前）。

整例宏化三条（m15-testcases-004；用户 2026-11-16 裁定「整例宏化」）——防「把用例藏进宏里」：

  S6 **宏内断言的点号必须来自调用方**：`__PT_*` 宏体里每条断言（`__CHECK_*` /
     `TEST_*` / `__VERIFY_*`）的点号实参必须是**本宏的形参引用**（`\name`），
     其中**占检查点的那一条**（`__CHECK_*` / `TEST_*`）必须是 `\pt` —— 写常量
     等于把失败点号钉死，`pts_ok`（点号 == 用例序号）就失去意义；
  S7 **一行用例 = 一个检查点**：`.S` 正文里每个 `__PT_*` 调用行，其**传递展开**
     恰产出 1 个检查点（`__CHECK_*` 计 1；`TEST_*` 宏调用计 1，不深入其分支体）；
  S8 **正文不得留裸断言**：凡正文出现 `__PT_*` 调用行的 `.S`（= 已整例宏化的文件），
     正文（宏体之外）不得再有 `__CHECK_RD*`/`__CHECK_MEM*` 行 —— 否则同一用例的
     检查点计数在「扫描器口径」与「宏展开口径」下分叉。

2 行级结构重复（m15-testcases-005；用户 2026-11-16 裁定 B「判据 = 净收益 > 0」）：

  S9 **宏化要划算**：净收益 = `k×n − (n+2+k)`（`n` = 宏定义行数、`k` = 展开次数、
     `2` = `.macro`/`.endm`）≤ 0 ⇒ **报告**（默认打印 `[WARN]`，`--strict` 时 rc=1）。
     正收益门槛：2 行 ⇒ k≥5、3 行 ⇒ k≥3、**4 行 ⇒ k≥3**（代入公式，n=4/k=2 恰为 0）；
  S9 **一次展开不得含 ≥2 个不同点号的检查点**（任意宏，不只 `__PT_*`；与 S7 互补）：
     `.if*` 分支取**点号并集**（同一点号只算一个）。把两个用例压进一个宏会让
     「一行 = 一个检查点」的用例身份失效。

「使用者」= **反向闭包**：`.S` 直接使用 + 宏被别的宏调用时继承调用者的使用者
（宏体里的 `__CHECK_*` 等行不是用例行，扫描时跳过 `.macro`..`.endm`）。

用法：
    python3 tools/testcases/check_inst_macro_scope.py              # 门控（默认）
    python3 tools/testcases/check_inst_macro_scope.py --root DIR   # 检查另一棵树
    python3 tools/testcases/check_inst_macro_scope.py --strict     # 净收益≤0 也判红
    python3 tools/testcases/check_inst_macro_scope.py --selfcheck  # 干净基线 + 12 类注入
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent / "inst"))
import run_asm_suite  # noqa: E402  (宏体跳过的单一真源)

INC_ROOT_REL = "tests/inst"
SHARED_REL = "tests/inst/macros/inst_test.inc"
MACRO_DEF_RE = re.compile(r"^\.macro\s+(\w+)")
MACRO_END_RE = re.compile(r"^\s*\.endm\b")
INCLUDE_RE = re.compile(r'^\s*\.include\s+"([^"]+)"\s*$')
TMP_ROOT = Path(tempfile.gettempdir()) / "opencode" / "m15-testcases-002"
# 整例宏化（S6/S7/S8）：`__PT_*` = 一行一条用例的宏；宏体里**占检查点**的行是
# `__CHECK_*` 与 `TEST_*`（与扫描器 `run_asm_suite.CHAIN_CASE_RE` 同一口径）。
PT_MACRO_RE = re.compile(r"^__PT_")
PT_CASE_LINE_RE = re.compile(r"^\t(__PT_\w*)(?:\s|$)")
COUNTING_ASSERT_RE = re.compile(r"^\s+(__CHECK_\w*|TEST_\w+)\s+(\S.*)$")
ANY_ASSERT_RE = re.compile(r"^\s+(__CHECK_\w*|TEST_\w+|__VERIFY_\w*)\s+(\S.*)$")
BARE_CHECK_RE = re.compile(r"^\t(__CHECK_(?:RD|MEM)\w*)\b")
PARAM_REF_RE = re.compile(r"^\\\w+")
# 2 行级结构重复（S9；m15-testcases-005）：判据 = **净收益 > 0**，
# 净收益 = k×n − (n+2+k)（n = 模式行数、k = 展开次数、2 = `.macro`/`.endm`）。
# 宏体里的 `.if*`/`.else*`/`.endif` 用于「一次展开的检查点点号集合」与「调用点计数」：
# 分支互斥 ⇒ 点号取**并集**（同一点号只算一个）、调用点取 min（保守，宁严不松）。
IF_OPEN_RE = re.compile(r"^\s*\.if\w*\b")
IF_ELSE_RE = re.compile(r"^\s*\.else(?:if\w*)?\b")
IF_END_RE = re.compile(r"^\s*\.endif\b")
S9_NET_HINT = ("（定义成本 = n+2 = {cost} 行 ≥ 净收益 {gain} 行 ⇒ 宏化不划算；"
               "判据 k×n − (n+2+k) > 0）")


# ---------------------------------------------------------------------------
# 解析
# ---------------------------------------------------------------------------
def strip_comment(line: str) -> str:
    """去掉 `@@` 行注释（本仓库汇编注释语法）。"""
    i = line.find("@@")
    return line if i < 0 else line[:i]


def parse_macros(text: str) -> dict[str, tuple[int, int]]:
    """宏名 -> (start, end) 行号（0-based，含 `.macro`/`.endm`）。"""
    lines = text.splitlines()
    out: dict[str, tuple[int, int]] = {}
    i = 0
    while i < len(lines):
        m = MACRO_DEF_RE.match(lines[i].lstrip())
        if not m:
            i += 1
            continue
        j = i
        while j < len(lines) and not MACRO_END_RE.match(lines[j]):
            j += 1
        out[m.group(1)] = (i, j)
        i = j + 1
    return out


def macro_body_uses(text: str, defs: dict[str, tuple[int, int]],
                    names: re.Pattern) -> dict[str, set[str]]:
    """宏 -> 其宏体里调用到的其它宏（边）。"""
    lines = text.splitlines()
    edges: dict[str, set[str]] = defaultdict(set)
    for name, (s, e) in defs.items():
        for k in range(s, e + 1):
            if k == s:
                continue
            for hit in names.findall(strip_comment(lines[k])):
                if hit != name:
                    edges[name].add(hit)
    return edges


def collect(root: Path) -> dict:
    """收集三层宏定义 + `.S` 直接使用 + include 接线。"""
    shared_path = root / SHARED_REL
    if not shared_path.is_file():
        raise SystemExit(f"check-inst-macro-scope: ERROR: 共享层缺失 {SHARED_REL}")
    layers: dict[str, dict[str, tuple[int, int]]] = {}
    texts: dict[str, str] = {}
    layers["shared"] = parse_macros(shared_path.read_text(encoding="utf-8"))
    texts["shared"] = shared_path.read_text(encoding="utf-8")

    inst_root = root / INC_ROOT_REL
    books = sorted(p.name for p in inst_root.iterdir() if p.is_dir() and p.name != "macros")
    wrong_incs: list[str] = []
    for book in books:
        for inc in sorted((inst_root / book).glob("*.inc")):
            if inc.name != book + ".inc":
                wrong_incs.append(inc.relative_to(root).as_posix())
                continue
            rel = inc.relative_to(root).as_posix()
            texts["book:" + book] = inc.read_text(encoding="utf-8")
            layers["book:" + book] = parse_macros(texts["book:" + book])
    for inc in sorted((inst_root / "macros").glob("*.inc")):
        if inc.name != "inst_test.inc":
            wrong_incs.append(inc.relative_to(root).as_posix())

    s_files = sorted(inst_root.glob("*/*.S"))
    for p in s_files:
        rel = p.relative_to(root).as_posix()
        texts["file:" + rel] = p.read_text(encoding="utf-8")
        layers["file:" + rel] = parse_macros(texts["file:" + rel])

    all_names = sorted({n for layer in layers.values() for n in layer},
                       key=len, reverse=True)
    names = re.compile(r"\b(" + "|".join(map(re.escape, all_names)) + r")\b")

    direct: dict[str, set[str]] = defaultdict(set)
    for p in s_files:
        rel = p.relative_to(root).as_posix()
        for line in run_asm_suite.iter_code_lines(texts["file:" + rel]):
            for hit in names.findall(strip_comment(line)):
                direct[hit].add(rel)

    edges: dict[str, set[str]] = defaultdict(set)
    for layer, defs in layers.items():
        for caller, callees in macro_body_uses(texts[layer], defs, names).items():
            edges[caller] |= callees

    # 宏体逐行（去注释）——S6/S7 用；`.macro`/`.endm` 行本身不进体。
    bodies: dict[str, list[str]] = {}
    for layer, defs in layers.items():
        lines = texts[layer].splitlines()
        for name, (s, e) in defs.items():
            bodies[name] = [strip_comment(ln) for ln in lines[s + 1:e]]

    return {
        "shared": layers["shared"],
        "books": {k.split(":", 1)[1]: v for k, v in layers.items()
                  if k.startswith("book:")},
        "files": {k.split(":", 1)[1]: v for k, v in layers.items()
                  if k.startswith("file:")},
        "texts": texts,
        "direct": direct,
        "edges": edges,
        "bodies": bodies,
        "book_names": books,
        "s_files": [p.relative_to(root).as_posix() for p in s_files],
        "wrong_incs": wrong_incs,
        "names": names,
    }


def book_of(rel_s: str) -> str:
    return rel_s.split("/")[2]


def _first_arg(rest: str) -> str:
    return rest.split(",")[0].strip()


def macro_point_counts(bodies: dict[str, list[str]]) -> tuple[dict[str, int], list[str]]:
    """宏的**传递展开**检查点数。

    口径与扫描器一致：宏体里的 `__CHECK_*` 记 1；`TEST_*` 宏调用记 1（其内部多条
    `__CHECK_*` 是被 `.ifc` 分支择一的，按调用行计一次即可）；其它已定义宏递归求和。
    """
    memo: dict[str, int] = {}
    cycles: list[str] = []

    def count(name: str, stack: tuple[str, ...]) -> int:
        if name in memo:
            return memo[name]
        if name in stack:
            cycles.append(name)
            return 0
        total = 0
        for line in bodies.get(name, ()):
            if COUNTING_ASSERT_RE.match(line):
                total += 1
                continue
            tok = line.split(None, 1)[0] if line.strip() else ""
            if tok and tok != name and tok in bodies:
                total += 1 if tok.startswith("TEST_") else count(tok, stack + (name,))
        memo[name] = total
        return total

    for name in bodies:
        count(name, ())
    return memo, cycles


def split_if_blocks(lines: list[str]) -> list:
    """把宏体行序列切开：`("line", 文本)` / `("if", [各分支的行列表…])`。

    `.if*` 的各个 `.else*` 分支互斥；嵌套按同法递归（内层 `.if`/`.endif` 留在
    分支行里，交给递归再切一次）。
    """
    out, i = [], 0
    while i < len(lines):
        if IF_OPEN_RE.match(lines[i]):
            depth, j, branches = 1, i + 1, [[]]
            while j < len(lines):
                if IF_OPEN_RE.match(lines[j]):
                    depth += 1
                elif IF_END_RE.match(lines[j]):
                    depth -= 1
                    if depth == 0:
                        break
                elif IF_ELSE_RE.match(lines[j]) and depth == 1:
                    branches.append([])
                    j += 1
                    continue
                branches[-1].append(lines[j])
                j += 1
            out.append(("if", branches))
            i = j + 1
            continue
        out.append(("line", lines[i]))
        i += 1
    return out


def macro_point_keys(bodies: dict[str, list[str]]) -> tuple[dict[str, set[str]], list[str]]:
    """每个宏**一次展开**里出现的**检查点点号**集合（S9；与 S7 互补）。

    「检查点 = 一行计数断言」：`__CHECK_*` / `TEST_*`（与扫描器
    `run_asm_suite.CHAIN_CASE_RE` 同一口径）；`__VERIFY_*` 是同一检查点的后续核对，
    不产生新检查点。同一宏里出现**两个不同点号**的检查点 = 把两个用例/两个检查点压进
    一个宏 ⇒ 一行用例身份失效。同一宏里多条检查点共用同一 `\\pt`（如 `TEST_MOV1` 的
    `.ifc` 分支各一条）合法。`.if*` 分支：取**并集**（每支都可能发生；同一点号只算
    一个）。`TEST_*` 调用行按「点号 = 其第一个实参」计一次，不深入其体。
    """
    memo: dict[str, set[str]] = {}
    cycles: list[str] = []

    def body_keys(lines: list[str], owner: str, stack: tuple[str, ...]) -> set[str]:
        keys: set[str] = set()
        for kind, val in split_if_blocks(lines):
            if kind == "if":
                for branch in val:
                    keys |= body_keys(branch, owner, stack)
                continue
            m = COUNTING_ASSERT_RE.match(val)
            if m:
                keys.add(_first_arg(m.group(2)))
                continue
            parts = val.split(None, 1)
            tok = parts[0] if parts and parts[0] else ""
            if tok.startswith("TEST_"):
                keys.add(_first_arg(parts[1]) if len(parts) > 1 else "")
            elif tok in bodies and tok != owner:
                keys |= macro_keys(tok, stack)
        return keys

    def macro_keys(name: str, stack: tuple[str, ...]) -> set[str]:
        if name in memo:
            return memo[name]
        if name in stack:
            cycles.append(name)
            return set()
        val = body_keys(bodies.get(name, []), name, stack + (name,))
        memo[name] = val
        return val

    for name in bodies:
        macro_keys(name, ())
    return memo, cycles


def body_refs_by_name(lines: list[str], names: re.Pattern) -> dict[str, int]:
    """宏体里各被调宏的出现次数；`.if*` 分支互斥 ⇒ **逐 name 取 min**。"""
    totals: dict[str, int] = defaultdict(int)
    for kind, val in split_if_blocks(lines):
        if kind == "line":
            for hit in names.findall(strip_comment(val)):
                totals[hit] += 1
        else:
            subs = [body_refs_by_name(b, names) for b in val]
            for name in {k for s in subs for k in s}:
                totals[name] += min(s.get(name, 0) for s in subs)
    return totals


def macro_expansions(data: dict, names: re.Pattern) -> dict[str, int]:
    """每个宏的展开次数 k（S9 净收益用）。

    k = `.S` 正文调用点数 + Σ(宏体里被调次数 × 外层宏的展开次数)（递归、记忆化；
    成环返回 0，由 S7 单独报）。死宏 k=0（S4 报），不参与净收益判定。
    """
    direct: dict[str, int] = defaultdict(int)
    for rel in data["s_files"]:
        for line in run_asm_suite.iter_code_lines(data["texts"]["file:" + rel]):
            for hit in names.findall(strip_comment(line)):
                direct[hit] += 1
    body_refs = {name: body_refs_by_name(body, names)
                 for name, body in data["bodies"].items()}
    memo: dict[str, int] = {}

    def k(name: str, stack: tuple[str, ...]) -> int:
        if name in memo:
            return memo[name]
        if name in stack:
            return 0
        total = direct.get(name, 0)
        for caller, refs in body_refs.items():
            hit = refs.get(name, 0)
            if caller != name and hit:
                total += hit * k(caller, stack + (name,))
        memo[name] = total
        return total

    for name in data["bodies"]:
        k(name, ())
    return memo


def macro_def_lines(body: list[str]) -> int:
    """宏定义正文行数 n（空行不计；`.macro`/`.endm` 不计入 n，单独按 2 行成本算）。"""
    return sum(1 for ln in body if ln.strip())


# ---------------------------------------------------------------------------
# 判据
# ---------------------------------------------------------------------------
def analyze(root: Path) -> tuple[list[str], dict]:
    data = collect(root)
    users: dict[str, set[str]] = defaultdict(set)
    for name, rels in data["direct"].items():
        users[name] |= rels
    changed = True
    while changed:
        changed = False
        for caller, callees in data["edges"].items():
            for callee in callees:
                if not users[caller] <= users[callee]:
                    users[callee] |= users[caller]
                    changed = True

    bad: list[str] = []
    for rel in data["wrong_incs"]:
        bad.append(f"[S2] 非法 .inc（册宏文件必须叫 `<册>/<册>.inc`）: {rel}")

    # S1 共享层：≥2 册
    for name in sorted(data["shared"]):
        books = {book_of(u) for u in users[name]}
        if not users[name]:
            continue  # 死宏由 S4 单独报
        if len(books) < 2:
            bad.append(f"[S1] 共享层宏 `{name}` 只被 {len(books)} 册使用 "
                       f"({', '.join(sorted(books))}) ⇒ 应下沉到册/文件")

    # S2 册 .inc：使用者只在该册
    for book, defs in sorted(data["books"].items()):
        for name in sorted(defs):
            if not users[name]:
                continue
            out = sorted(u for u in users[name] if book_of(u) != book)
            if out:
                bad.append(f"[S2] 册宏 `{name}`（{book}/{book}.inc）被册外使用: "
                           f"{', '.join(out)}")

    # S3 `.S` 内宏：使用者只在该文件
    for rel, defs in sorted(data["files"].items()):
        for name in sorted(defs):
            if not users[name]:
                continue
            out = sorted(u for u in users[name] if u != rel)
            if out:
                bad.append(f"[S3] 文件宏 `{name}`（{rel}）被其它文件使用: "
                           f"{', '.join(out)}")

    # S4 死宏 = 0
    dead = []
    for layer_name, defs in (("shared", data["shared"]),
                             *((f"{b}/{b}.inc", d) for b, d in sorted(data["books"].items())),
                             *((rel, d) for rel, d in sorted(data["files"].items()))):
        for name in sorted(defs):
            if not users[name]:
                dead.append(f"[S4] 死宏 `{name}`（{layer_name}）无任何使用者 ⇒ 应删除")
    bad.extend(dead)

    # S5 include 接线
    shared_inc = SHARED_REL
    for rel in data["s_files"]:
        text = data["texts"]["file:" + rel]
        incs = []
        for i, line in enumerate(text.splitlines()):
            m = INCLUDE_RE.match(line)
            if m:
                incs.append((i, m.group(1)))
        paths = [p for _, p in incs]
        if paths.count(shared_inc) != 1:
            bad.append(f"[S5] {rel} 必须 `.include` 共享层一次（实为 {paths.count(shared_inc)} 次）")
            continue
        book = book_of(rel)
        if book in data["books"]:
            book_inc = f"tests/inst/{book}/{book}.inc"
            if paths.count(book_inc) != 1:
                bad.append(f"[S5] {rel} 必须 `.include` 册层 `{book_inc}` 一次"
                           f"（实为 {paths.count(book_inc)} 次）")
            else:
                i_shared = paths.index(shared_inc)
                i_book = paths.index(book_inc)
                if i_book < i_shared:
                    bad.append(f"[S5] {rel} 的册层 include 必须在共享层之后"
                               f"（行序 {i_book} < {i_shared}）")
        allowed = {shared_inc}
        if book in data["books"]:
            allowed.add(f"tests/inst/{book}/{book}.inc")
        for p in paths:
            if p.startswith(INC_ROOT_REL + "/") and p not in allowed:
                bad.append(f"[S5] {rel} include 了非本册/非共享层文件: {p}")

    # S6 宏内断言的点号必须来自调用方（不得写常量）
    for name in sorted(data["bodies"]):
        if not PT_MACRO_RE.match(name):
            continue
        for line in data["bodies"][name]:
            m = ANY_ASSERT_RE.match(line)
            if not m:
                continue
            mnem, arg = m.group(1), _first_arg(m.group(2))
            if mnem.startswith("__CHECK_") or mnem.startswith("TEST_"):
                if arg != r"\pt":
                    bad.append(f"[S6] 用例宏 `{name}` 的 `{mnem}` 点号实参是 `{arg}`"
                               r"，必须引用 `\pt`（写常量 ⇒ 失败点号被钉死）")
            elif not PARAM_REF_RE.match(arg):
                bad.append(f"[S6] 用例宏 `{name}` 的断言 `{mnem}` 点号实参是 `{arg}`"
                           r"，必须是本宏形参引用（如 `\pt`）")

    # S7 一行 `__PT_*` 用例行 = 一个检查点
    counts, cycles = macro_point_counts(data["bodies"])
    for c in sorted(set(cycles)):
        bad.append(f"[S7] 宏调用成环: `{c}`")
    for rel in data["s_files"]:
        for line in run_asm_suite.iter_code_lines(data["texts"]["file:" + rel]):
            m = PT_CASE_LINE_RE.match(line)
            if not m:
                continue
            name = m.group(1)
            n = counts.get(name)
            if n is None:
                bad.append(f"[S7] {rel} 用例行调用了未定义的宏 `{name}`")
            elif n != 1:
                bad.append(f"[S7] {rel} 用例行 `{name}` 传递展开出 {n} 个检查点"
                           "（要求恰 1 —— 一行用例只能对应一个检查点）")

    # S8 已整例宏化的文件正文不得留裸 `__CHECK_*`
    converted = []
    for rel in data["s_files"]:
        body = list(run_asm_suite.iter_code_lines(data["texts"]["file:" + rel]))
        if not any(PT_CASE_LINE_RE.match(line) for line in body):
            continue
        converted.append(rel)
        for line in body:
            m = BARE_CHECK_RE.match(line)
            if m:
                bad.append(f"[S8] {rel} 正文仍有裸 `{m.group(1)}`"
                           "（已整例宏化的文件里用例只能以 `__PT_*` 调用行出现）")

    # S9（m15-testcases-005）①：宏内出现**两个不同点号**的断言 ⇒ 红
    # （与 S7 互补：S7 只管 `__PT_*` 用例行，S9 覆盖任意宏——把两个用例压进一个宏
    #   会让「一行 = 一个检查点」的身份判断失效）
    keys, bcycles = macro_point_keys(data["bodies"])
    for c in sorted(set(bcycles)):
        bad.append(f"[S9] 宏调用成环: `{c}`")
    for name in sorted(data["bodies"]):
        if len(keys.get(name, set())) >= 2:
            pts = ", ".join(sorted(keys[name]))
            bad.append(f"[S9] 宏 `{name}` 一次展开含 {len(keys[name])} 个不同点号的断言"
                       f"（{pts}）⇒ 把多个检查点/用例压进一个宏，用例身份失效")

    # S9 ②：净收益 = k×n − (n+2+k) ≤ 0 的宏化 ⇒ **报告**（默认告警；
    # `--strict` 时参与 rc）。判据见 tests/inst/README.md。
    kx = macro_expansions(data, data["names"])
    s9_neg = []
    for name in sorted(data["bodies"]):
        k = kx.get(name, 0)
        if k <= 0:
            continue                       # 死宏由 S4 报，不重复判净收益
        n = macro_def_lines(data["bodies"][name])
        net = k * n - (n + 2 + k)
        if net <= 0:
            s9_neg.append((name, k, n, net))

    stats = {
        "shared": len(data["shared"]),
        "book_incs": {b: len(d) for b, d in data["books"].items()},
        "file_macros": sum(len(d) for d in data["files"].values()),
        "file_macro_files": sum(1 for d in data["files"].values() if d),
        "s_files": len(data["s_files"]),
        "dead": len(dead),
        "pt_macros": sum(1 for n in data["bodies"] if PT_MACRO_RE.match(n)),
        "converted_files": len(converted),
        "pt_case_lines": sum(1 for rel in converted
                             for line in run_asm_suite.iter_code_lines(
                                 data["texts"]["file:" + rel])
                             if PT_CASE_LINE_RE.match(line)),
        "macros": len(data["bodies"]),
        "s9_neg": s9_neg,
        "s9_points": {n: sorted(v) for n, v in keys.items() if len(v) >= 2},
    }
    return bad, stats


# ---------------------------------------------------------------------------
# 自检（每条判据都有可达 FAIL 路径）
# ---------------------------------------------------------------------------
FIXTURE = {
    "tests/inst/macros/inst_test.inc": (
        "@@ 共享层\n"
        ".macro SH x\n"
        "\tnop\n"
        ".endm\n"),
    "tests/inst/aa/aa.inc": (
        "@@ aa 册\n"
        ".macro BOOKA x\n"
        "\tnop\n"
        ".endm\n"
        "@@ 整例宏：一行一条用例（点号取调用方实参）\n"
        ".macro __PT_CASE pt, x\n"
        "\tnop\n"
        "\t__CHECK_RD \\pt, rd5, 0x0\n"
        ".endm\n"
        "@@ 2 行准备段宏（S9 净收益：n=2、k=5 ⇒ 净收益 = 5×2−(2+2+5) = 1 > 0）\n"
        ".macro __PREP_PAIR x, y\n"
        "\tnop\t\\x\n"
        "\tnop\t\\y\n"
        ".endm\n"),
    "tests/inst/aa/one.S": (
        '\t.include "tests/inst/macros/inst_test.inc"\n'
        '\t.include "tests/inst/aa/aa.inc"\n'
        ".macro FILEA y\n"
        "\tnop\n"
        ".endm\n"
        "\tSH 1\n"
        "\tBOOKA 2\n"
        "\tFILEA 3\n"
        "\t__PT_CASE 4, rd5\n"
        "\t__PREP_PAIR 1, 2\n"
        "\t__PREP_PAIR 3, 4\n"
        "\t__PREP_PAIR 5, 6\n"
        "\t__PREP_PAIR 7, 8\n"
        "\t__PREP_PAIR 9, 10\n"),
    "tests/inst/bb/one.S": (
        '\t.include "tests/inst/macros/inst_test.inc"\n'
        "\tSH 1\n"),
}


def _write_tree(root: Path, files: dict[str, str]) -> None:
    if root.exists():
        shutil.rmtree(root)
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")


def selfcheck() -> int:
    """干净基线 = 0 违规；8 类注入各自必须红，且命中对应判据。"""
    TMP_ROOT.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="inst-macro-scope-", dir=TMP_ROOT))
    ok = True

    def run(name: str, mutate, expect: str) -> None:
        nonlocal ok
        files = dict(FIXTURE)
        mutate(files)
        _write_tree(tmp / "t", files)
        bad, stats = analyze(tmp / "t")
        hit = any(v.startswith(expect) for v in bad)
        want_rc = 0 if expect == "" else 1
        rc = 0 if not bad else 1
        good = (rc == want_rc) and (not bad if not expect else hit)
        status = "PASS" if good else "FAIL"
        if status == "FAIL":
            ok = False
        print(f"  [selfcheck] {name}: rc={rc} 期望 {want_rc} / 判据 {expect or '(无)'} "
              f"/ 违规 {len(bad)} → {status}")
        for v in bad[:3]:
            print(f"      {v}")

    def run9(name: str, mutate, macro: str, expect_warn: bool) -> None:
        """S9 净收益：该宏必须/必须不出现告警；且 `--strict` 的 rc 与告警非空等价。"""
        nonlocal ok
        files = dict(FIXTURE)
        mutate(files)
        _write_tree(tmp / "t", files)
        bad, stats = analyze(tmp / "t")
        neg = {w[0]: w for w in stats["s9_neg"]}
        got = macro in neg
        strict_rc = 0 if (not bad and not stats["s9_neg"]) else 1
        want_strict = 1 if (bad or stats["s9_neg"]) else 0
        good = (got == expect_warn) and not bad and strict_rc == want_strict
        status = "PASS" if good else "FAIL"
        if status == "FAIL":
            ok = False
        detail = (f"k={neg[macro][1]} n={neg[macro][2]} 净收益={neg[macro][3]}"
                  if got else "无告警")
        print(f"  [selfcheck] {name}: 宏 {macro} 告警={got} 期望 {expect_warn} / "
              f"{detail} / --strict rc={strict_rc} 期望 {want_strict} / 违规 {len(bad)} "
              f"→ {status}")
        for v in bad[:3]:
            print(f"      {v}")

    def clean(_files):
        pass

    def move_book_to_shared(files):
        files["tests/inst/macros/inst_test.inc"] += ".macro BOOKA x\n\tnop\n.endm\n"
        files["tests/inst/aa/aa.inc"] = files["tests/inst/aa/aa.inc"].replace(
            ".macro BOOKA x\n\tnop\n.endm\n", "")

    def drop_book_include(files):
        files["tests/inst/aa/one.S"] = files["tests/inst/aa/one.S"].replace(
            '\t.include "tests/inst/aa/aa.inc"\n', "")

    def add_dead(files):
        files["tests/inst/macros/inst_test.inc"] += ".macro DEADZ\n\tnop\n.endm\n"

    def file_macro_used_elsewhere(files):
        files["tests/inst/bb/one.S"] += "\tFILEA 9\n"

    def book_macro_used_outside(files):
        files["tests/inst/bb/one.S"] += "\tBOOKA 9\n"

    def pt_body_constant_point(files):
        files["tests/inst/aa/aa.inc"] = files["tests/inst/aa/aa.inc"].replace(
            "\t__CHECK_RD \\pt, rd5, 0x0\n", "\t__CHECK_RD 4, rd5, 0x0\n")

    def pt_body_two_checks(files):
        files["tests/inst/aa/aa.inc"] = files["tests/inst/aa/aa.inc"].replace(
            "\t__CHECK_RD \\pt, rd5, 0x0\n",
            "\t__CHECK_RD \\pt, rd5, 0x0\n\t__CHECK_MEM \\pt, A0, 0, 0x0\n")

    def bare_check_in_body(files):
        files["tests/inst/aa/one.S"] += "\t__CHECK_MEM 4, A0, 0, 0x0\n"

    def rf_pair_few_calls(files):
        files["tests/inst/aa/one.S"] = files["tests/inst/aa/one.S"].replace(
            "\t__PREP_PAIR 7, 8\n\t__PREP_PAIR 9, 10\n", "", 1)

    def rf_pair_many_calls(files):
        files["tests/inst/aa/one.S"] += "\t__PREP_PAIR 11, 12\n\t__PREP_PAIR 13, 14\n"

    def two_checks_in_plain_macro(files):
        files["tests/inst/aa/aa.inc"] += (
            ".macro __PREP_TWO pt\n\tnop\n\t__CHECK_RD \\pt, rd5, 0x0\n"
            "\t__CHECK_MEM 6, A0, 0, 0x0\n.endm\n")
        files["tests/inst/aa/one.S"] += "\t__PREP_TWO 5\n"

    def same_point_twice(files):
        files["tests/inst/aa/aa.inc"] += (
            ".macro __PREP_SAME pt\n\tnop\n\t__CHECK_RD \\pt, rd5, 0x0\n"
            "\t__CHECK_MEM \\pt, A0, 0, 0x0\n.endm\n")
        files["tests/inst/aa/one.S"] += "\t__PREP_SAME 5\n"

    def ifc_branch_checks(files):
        files["tests/inst/aa/aa.inc"] += (
            ".macro __PREP_COND pt, kind\n\t.ifc \\kind, a\n\t__CHECK_RD \\pt, rd5, 0x0\n"
            "\t.else\n\t__CHECK_MEM \\pt, A0, 0, 0x0\n\t.endif\n.endm\n")
        files["tests/inst/aa/one.S"] += "\t__PREP_COND 5, a\n"

    run("干净基线", clean, "")
    run("册宏挪回共享层", move_book_to_shared, "[S1]")
    run("删掉册 .inc 的 include", drop_book_include, "[S5]")
    run("塞一个死宏", add_dead, "[S4]")
    run("文件宏被别文件用", file_macro_used_elsewhere, "[S3]")
    run("册宏被别册用", book_macro_used_outside, "[S2]")
    run("用例宏点号写常量", pt_body_constant_point, "[S6]")
    run("用例宏体塞两条断言", pt_body_two_checks, "[S7]")
    run("正文留裸 __CHECK_MEM", bare_check_in_body, "[S8]")
    run9("S9 净收益为负：2 行宏 k=3（净收益 −1，做了不如不做）",
         rf_pair_few_calls, "__PREP_PAIR", True)
    run9("S9 净收益为正：2 行宏 k=7（净收益 3）不告警",
         rf_pair_many_calls, "__PREP_PAIR", False)
    run("S9 普通宏体两条**不同点号**的检查点（把两个用例压进一个宏）",
        two_checks_in_plain_macro, "[S9]")
    run("S9 同一检查点两条核对（同点号 ⇒ 合法，不判红）",
        same_point_twice, "")
    run("S9 `.ifc` 互斥分支各一条检查点（同点号，合法）",
        ifc_branch_checks, "")
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"check-inst-macro-scope: selfcheck {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=None, help="检查另一棵树（默认仓库根）")
    ap.add_argument("--selfcheck", action="store_true",
                    help="干净基线 + 12 类注入自检（含 S9 两路）")
    ap.add_argument("--strict", action="store_true",
                    help="S9 净收益≤0 的宏化也判红（默认只告警）")
    args = ap.parse_args()
    if args.selfcheck:
        return selfcheck()
    root = args.root.resolve() if args.root else ROOT
    if not (root / SHARED_REL).is_file():
        print(f"check-inst-macro-scope: ERROR: 共享层缺失 {SHARED_REL}", file=sys.stderr)
        return 2
    bad, stats = analyze(root)
    print(f"check-inst-macro-scope: 共享层宏 {stats['shared']} / 册 .inc "
          f"{len(stats['book_incs'])} 个（{sum(stats['book_incs'].values())} 宏）/ "
          f"`.S` 内宏 {stats['file_macros']} 个（{stats['file_macro_files']} 文件）/ "
          f"`.S` {stats['s_files']} / 死宏 {stats['dead']}")
    print(f"  整例宏：`__PT_*` {stats['pt_macros']} 个 / 已宏化 `.S` "
          f"{stats['converted_files']} 个（用例行 {stats['pt_case_lines']} 行）")
    print(f"  S9 净收益（k×n−(n+2+k)>0）：宏 {stats['macros']} 个，"
          f"净收益≤0 的 {len(stats['s9_neg'])} 个"
          f"（{'--strict 判红' if args.strict else '告警'}）")
    for book, n in sorted(stats["book_incs"].items()):
        print(f"  {book}.inc: {n} 宏")
    for name, k, n, net in stats["s9_neg"]:
        print(f"[WARN] [S9] 宏 `{name}` 净收益 {net} ≤ 0（k={k} n={n}）"
              + S9_NET_HINT.format(cost=n + 2, gain=net))
    if bad:
        for v in bad:
            print(f"[FAIL] {v}", file=sys.stderr)
        print(f"check-inst-macro-scope: FAIL（{len(bad)} 条违规）", file=sys.stderr)
        return 1
    if args.strict and stats["s9_neg"]:
        print(f"check-inst-macro-scope: FAIL（--strict：{len(stats['s9_neg'])} 个宏"
              "净收益 ≤ 0）", file=sys.stderr)
        return 1
    print("check-inst-macro-scope: PASS（三分层 + 死宏 0 + include 接线 + 用例宏 S6/S7/S8 "
          "+ S9 净收益/可达检查点）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
