#!/usr/bin/env python3
"""Render ISA operation blocks from ``idl/*.idl`` into ``spec/`` (m15-spec-001).

Why
---
``idl/`` 是 ISA 语义的**机器可读源**（每册一个 ``.idl``，每条指令以 ``# id:``
开头）；``spec/SimRISC-*`` 里的 ```idl 块是**渲染结果**，不得手改。本脚本是该
渲染的**唯一生成器**与门控：块内容按 ``# id:`` 逐字节搬运，因此「规范里的块是否
等于源」可机械判定。

标记约定
--------
源册 ``idl/SimRISC-NN.idl`` 对应 ``spec/SimRISC-NN-*.md``；该册内每条指令的落点写作::

    <!-- IDL:<instr-id> BEGIN -->
    ...（本脚本生成，勿手改）...
    <!-- IDL:<instr-id> END -->

布局（m15-spec-005）
--------------------
每个带编号的 ``## N.`` 节末尾**集中**该节全部 operation，配一个三级标题
``### N.M 形式化语义（IDL）``（M = 该节已有子节号 +1）、一句导语，随后是块序列::

    ### 1.2 形式化语义（IDL）

    本节各指令的形式化语义由 `idl/SimRISC-03.idl` 生成，逐条如下：

    <!-- IDL:<instr-id> BEGIN -->
    <!-- 由 idl/render.py 生成，勿手改 -->
    **`<instr-id>`**                    ← 替代块内原有的 `# id:` 行
    ```idl
    ...
    ```
    <!-- IDL:<instr-id> END -->

散文一行不动：重渲染只移动/重建「标记块 + 生成标题 + 导语」，其余行逐字节保持。

断言（全部 fail-closed）
------------------------
A. 源：``idl/*.idl`` 的文件名形如 ``SimRISC-NN.idl``；文件头（首个 ``# id:`` 之前）
   不得有非空内容；每条 operation 以 ``# id: <instr-id>`` 开头、id 全局唯一。
B. id 存在于 ``contracts/opcodes.yaml``（防与编码表脱节）。
C. 落点：每个 id 在对应册内**恰好一对**标记（BEGIN 先于 END、期间无其它 BEGIN）；
   每个 ``# id:`` 都有落点；**每个落点都有源**（防空标记）；落点所在册 == 源文件册。
D. 一致性：重渲染后的整册文本与磁盘**逐字节相同**（``--check``）；两次渲染同结果。
E. 交叉断言：每条 operation 调用的函数都在语义库声明（``spec/IDL-ISA语义描述语言与语义库.md``
   §4 的代码块 **加 ``idl/lib/*.idl``**；含 ``?`` 后缀函数名；防「引用了不存在的语义库」——
   语义正确性由编写期 ``idlc`` oracle 另行检查，不动门控）。
F. 解码变量不得当寄存器内容用：``rdHA``…/``rbH*``/``raH*``/``rfH*`` **紧跟 ``[``** 即 FAIL
   （散文里 ``rdHC`` 指**内容**，``.idl`` 里它是 **6 位寄存器号**；合法用法只有作下标
   ``rd[rdHC]``）。``idlc`` 不校验位宽 ⇒ ``rdHC[i]`` 会静默取到寄存器号的位（m15-idl-014）。
G. 布局：每个块必须落在带编号 ``## N.`` 节内；节末生成区（三级标题 + 导语 + 块序列）
   里不得混入手写内容（防「把散文塞进生成区」被静默吞掉）。

用法
----
* ``python3 idl/render.py``              # 生成/更新 spec 册内的标记块
* ``python3 idl/render.py --check``      # 只校验（漂移 ⇒ 非零退出）
* ``python3 idl/render.py --self-test``  # 临时树内多类注入自检（各自须 FAIL）
* ``python3 idl/render.py --prose-hash`` # 打印各册「剥掉生成内容后」的散文哈希
* ``--root DIR``：在另一棵树（同布局）内运行，供注入自检使用

退出码：0 = 通过；1 = 任一断言失败。
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

IDL_REL = "idl"
SPEC_REL = "spec"
OPCODES_REL = "contracts/opcodes.yaml"
# 语义库正文所在册（断言 E 的扫描面之一；另一半是 `idl/lib/*.idl`）
SEMANTICS_REL = "spec/IDL-ISA语义描述语言与语义库.md"

ID_RE = re.compile(r"^#\s*id:\s*(\S+)\s*$")
BEGIN_RE = re.compile(r"^<!--\s*IDL:(\S+)\s+BEGIN\s*-->\s*$")
END_RE = re.compile(r"^<!--\s*IDL:(\S+)\s+END\s*-->\s*$")
BOOK_RE = re.compile(r"^SimRISC-(\d{2})\.idl$")
# 节末生成区：`## N.` 节 → 三级标题 `### N.M 形式化语义（IDL）`
HEADING_RE = re.compile(r"^###\s+(\d+)\.(\d+)\s+形式化语义（IDL）\s*$")
H3_ANY_RE = re.compile(r"^###\s+(\d+)\.(\d+)\s+\S")
SECTION_RE = re.compile(r"^##\s+(\d+)\.\s+\S")
# 其它生成区的起点（`check-asm-list` / `check-legality-drift` 维护）：节末插入须让位
GEN_START_RE = re.compile(r"^<!--\s*(?:ASSEMBLY_LIST|LEGALITY)_START\s*-->\s*$")
LEAD_RE = re.compile(r"^本节各指令的形式化语义由 `idl/SimRISC-\d{2}\.idl` 生成，逐条如下：$")
DECL_RE = re.compile(r"^\s*(?:builtin\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*\??)\s*\{")
CALL_RE = re.compile(r"(?<![\w$.])([A-Za-z_][A-Za-z0-9_]*)\s*\(")
# 以 `?` 结尾的函数名（如 `is_sp_nan?`）：上面 CALL_RE 要求标识符后紧跟 `(`，捕不到 `?`，
# 故单列一条；两条分开匹配可避免把三目 `a ? (…)` 误当函数调用。
QBANG_CALL_RE = re.compile(r"(?<![\w$.])([A-Za-z_][A-Za-z0-9_]*\?)\s*\(")
# 解码变量（寄存器号）：rdHA…rdHD / rbH* / raH* / rfH*；它们**不是**内容
DECODE_VAR = r"(?:rd|rb|ra|rf)H[A-Za-z0-9]*"
DECODE_VAR_RE = re.compile(r"(?<![\w$])(" + DECODE_VAR + r")\s*\[")
DECODE_VAR_ANY_RE = re.compile(r"(?<![\w$])(" + DECODE_VAR + r")\b")
# 关键字/内建转换不算「调用语义库函数」
NON_CALL = frozenset({"if", "for", "while", "return", "assert", "sizeof", "true", "false"})

GENERATED_NOTE = "<!-- 由 idl/render.py 生成，勿手改 -->"
FENCE_OPEN = "```idl"
FENCE_CLOSE = "```"


class RenderError(Exception):
    """任一门控断言失败。"""


@dataclass(frozen=True)
class Op:
    id: str
    book: str          # 形如 "SimRISC-01"
    source: Path
    text: str          # 自 `# id:` 行起、末行非空的多行正文（不含结尾换行）


def _split_lines(text: str) -> list[str]:
    """按 ``\n`` 切行；不静默改写其它行尾（CRLF 一律拒绝，避免「逐字节」名不副实）。"""
    if "\r" in text:
        raise RenderError("含 CR 行尾，拒绝渲染（逐字节比对要求 LF）")
    return text.split("\n")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def same_bytes(path: Path, text: str) -> bool:
    """逐字节比对（UTF-8 编码后与磁盘字节流全等）。"""
    return path.read_bytes() == text.encode("utf-8")


def parse_idl(path: Path, book: str) -> list[Op]:
    """把一册 ``.idl`` 按 ``# id:`` 切成若干 operation。"""
    lines = _split_lines(read_text(path))
    chunks: list[tuple[str, list[str]]] = []
    cur_id: str | None = None
    cur_lines: list[str] = []
    for lineno, line in enumerate(lines, 1):
        m = ID_RE.match(line)
        if m:
            if cur_id is not None:
                chunks.append((cur_id, cur_lines))
            cur_id = m.group(1)
            cur_lines = [line]
            continue
        if cur_id is None:
            if line.strip():
                raise RenderError(f"{path}:{lineno}: 首个 `# id:` 之前不得有内容（{line!r}）")
            continue
        cur_lines.append(line)
    if cur_id is not None:
        chunks.append((cur_id, cur_lines))

    ops: list[Op] = []
    for op_id, body in chunks:
        while body and not body[-1].strip():
            body.pop()
        if len(body) < 2:
            raise RenderError(f"{path}: operation `{op_id}` 只有 `# id:` 行、没有正文")
        ops.append(Op(id=op_id, book=book, source=path, text="\n".join(body)))
    if not ops:
        raise RenderError(f"{path}: 没有任何 `# id:` operation")
    return ops


def load_ops(idl_dir: Path) -> dict[str, Op]:
    """读全部源册；id 全局唯一；文件名须为 ``SimRISC-NN.idl``。"""
    files = sorted(idl_dir.glob("*.idl"))
    if not files:
        raise RenderError(f"{idl_dir}: 没有任何 `.idl` 源册")
    ops: dict[str, Op] = {}
    for path in files:
        m = BOOK_RE.match(path.name)
        if not m:
            raise RenderError(f"{path.name}: 源册名须形如 `SimRISC-NN.idl`")
        for op in parse_idl(path, path.stem):
            if op.id in ops:
                raise RenderError(
                    f"operation id 重复: `{op.id}`（{ops[op.id].source.name} 与 {path.name}）")
            ops[op.id] = op
    return ops


def load_opcodes(root: Path) -> set[str]:
    import yaml  # type: ignore

    path = root / OPCODES_REL
    data = yaml.safe_load(read_text(path))
    if not isinstance(data, list) or not data:
        raise RenderError(f"{OPCODES_REL}: 期望非空列表")
    ids = {entry["id"] for entry in data if isinstance(entry, dict) and "id" in entry}
    if not ids:
        raise RenderError(f"{OPCODES_REL}: 没有解析到任何 id")
    return ids


LIB_SUBDIR = "lib"


def load_declared(root: Path) -> set[str]:
    """语义库声明的函数名（``function X {`` / ``builtin function X {``）。

    扫描面 = ``spec/IDL-ISA语义描述语言与语义库.md`` §4 的代码块
    **+ ``idl/lib/*.idl``**（m15-idl-015 起浮点族等大库拆到 ``idl/lib/``）。
    """
    book = root / SEMANTICS_REL
    text = read_text(book)
    if "## 4." not in text or "## 5." not in text:
        raise RenderError(f"{SEMANTICS_REL}: 找不到 §4 语义库小节（约定见该册）")
    section = text.split("## 4.", 1)[1].split("## 5.", 1)[0]
    declared = {m.group(1) for m in (DECL_RE.match(line) for line in section.split("\n")) if m}
    for path in sorted((root / IDL_REL / LIB_SUBDIR).glob("*.idl")):
        for line in strip_comments(read_text(path)).split("\n"):
            m = DECL_RE.match(line)
            if m:
                declared.add(m.group(1))
    if not declared:
        raise RenderError(f"{SEMANTICS_REL} §4: 没有解析到任何函数声明")
    return declared


def strip_comments(text: str) -> str:
    """抹掉 ``#`` 行尾注释（只用于「未声明函数」扫描）。

    operation 的注释里常引述散文的记号（如 ``rol(x, n)``、``GF(2)``），
    按字面扫会把注释误判成「调用了未声明的函数」，逼人改注释措辞。
    """
    return "\n".join(line.split("#", 1)[0] for line in text.split("\n"))


def check_calls_declared(ops: dict[str, Op], declared: set[str]) -> int:
    """每条 operation 调用的函数都必须在语义库声明（防「引用了不存在的语义库」）。

    函数名可带 ``?`` 后缀（如 ``is_sp_nan?``）；``CALL_RE`` 与 ``QBANG_CALL_RE`` 分开匹配，
    两类都按**原名**比对（``?`` 也算名字的一部分）。
    """
    bad: list[str] = []
    total = 0
    for op in ops.values():
        body = strip_comments(op.text)
        called = [m.group(1) for m in CALL_RE.finditer(body)]
        called += [m.group(1) for m in QBANG_CALL_RE.finditer(body)]
        for name in called:
            if name in NON_CALL:
                continue
            total += 1
            if name not in declared:
                bad.append(f"{op.id}: 调用未声明的函数 `{name}(`")
    if bad:
        raise RenderError("语义库缺项:\n  " + "\n  ".join(sorted(set(bad))))
    return total


def check_decode_vars(root: Path) -> int:
    """F 类：解码变量不得紧跟 ``[``（即把它当**寄存器内容**用）。

    散文（``spec/SimRISC-04 §2.2``、``spec/SimRISC-10 §2``）里的 ``rdHD`` 指**该寄存器的
    内容**；``.idl`` 里它是 **6 位解码变量（寄存器号）**，取内容必须写 ``rd[rdHD]``。
    ``idlc`` 不校验位宽 ⇒ ``rdHD[2:0]`` 会静默取到寄存器号的低 3 位（m15-idl-014）。
    注释一并扫描：注释紧接渲染进 spec 块，散文记号会重新制造同一歧义。
    """
    hits: list[str] = []
    refs = 0
    for path in sorted((root / IDL_REL).glob("*.idl")):
        cur_id = "<文件头>"
        for lineno, line in enumerate(_split_lines(read_text(path)), 1):
            m_id = ID_RE.match(line)
            if m_id:
                cur_id = m_id.group(1)
                continue
            refs += len(DECODE_VAR_ANY_RE.findall(line))
            for m in DECODE_VAR_RE.finditer(line):
                var = m.group(1)
                hits.append(
                    f"{path.name}:{lineno}: `{cur_id}` 里解码变量 `{var}` 直接当寄存器内容用"
                    f" —— 应写 `{var[:2]}[{var}]`（{var} 是 6 位寄存器号，取内容须再下标一次）")
    if hits:
        raise RenderError("解码变量被当成寄存器内容:\n  " + "\n  ".join(hits))
    if refs == 0:
        raise RenderError(
            f"{IDL_REL}/*.idl: 扫不到任何解码变量（rdH*/rbH*/raH*/rfH*）⇒ 断言空转，拒绝通过")
    print(f"  [decode-var] 解码变量引用 {refs} 处，全部作寄存器号使用（取内容一律 `rd[<var>]`）")
    return refs


def book_of_spec(path: Path) -> str | None:
    """``SimRISC-01-取数存数.md`` → ``SimRISC-01``。"""
    m = re.match(r"^(SimRISC-\d{2})-", path.name)
    return m.group(1) if m else None


def book_spec_files(root: Path) -> dict[str, Path]:
    """册名 → spec 文件（每册恰好一个）。"""
    out: dict[str, Path] = {}
    for path in sorted((root / SPEC_REL).glob("SimRISC-*.md")):
        book = book_of_spec(path)
        if book is None:
            continue
        if book in out:
            raise RenderError(f"册 `{book}` 对应多个 spec 文件: {out[book].name} / {path.name}")
        out[book] = path
    if not out:
        raise RenderError(f"{SPEC_REL}: 没有 SimRISC-*.md")
    return out


def marker_spans(lines: list[str], path: Path) -> dict[str, tuple[int, int]]:
    """找出 ``<!-- IDL:<id> BEGIN -->`` … ``<!-- IDL:<id> END -->`` 的行区间（0 基）。"""
    spans: dict[str, tuple[int, int]] = {}
    i = 0
    n = len(lines)
    while i < n:
        mb = BEGIN_RE.match(lines[i])
        if not mb:
            me = END_RE.match(lines[i])
            if me:
                raise RenderError(f"{path.name}:{i + 1}: 孤立的 END 标记 `{me.group(1)}`")
            i += 1
            continue
        op_id = mb.group(1)
        if op_id in spans:
            raise RenderError(f"{path.name}:{i + 1}: `{op_id}` 有多对 BEGIN 标记")
        j = i + 1
        while j < n and not END_RE.match(lines[j]):
            if BEGIN_RE.match(lines[j]):
                raise RenderError(
                    f"{path.name}:{j + 1}: 标记嵌套（`{op_id}` 块内又出现 BEGIN）")
            j += 1
        if j >= n:
            raise RenderError(f"{path.name}:{i + 1}: `{op_id}` 缺少 END 标记")
        end_id = END_RE.match(lines[j]).group(1)  # type: ignore[union-attr]
        if end_id != op_id:
            raise RenderError(
                f"{path.name}:{j + 1}: END 标记 `{end_id}` 与 BEGIN `{op_id}` 不匹配")
        spans[op_id] = (i, j)
        i = j + 1
    return spans


def lead_line(book: str) -> str:
    """节末生成区的导语（逐册指明源文件）。"""
    return f"本节各指令的形式化语义由 `idl/{book}.idl` 生成，逐条如下："


def op_body_lines(op: Op) -> list[str]:
    """块正文：去掉首行 ``# id: <id>``（HTML 侧改用一行粗体 id 标注）。"""
    lines = op.text.split("\n")
    m = ID_RE.match(lines[0])
    if m is None or m.group(1) != op.id:
        raise RenderError(f"{op.source.name}: operation `{op.id}` 的首行不是 `# id: {op.id}`")
    if len(lines) < 2:
        raise RenderError(f"{op.source.name}: operation `{op.id}` 只有 `# id:` 行、没有正文")
    return lines[1:]


def strip_generated(text: str) -> str:
    """剥掉「标记块 + 生成标题 + 导语」，并把连续空行压成一行。

    用于「散文零改动」核对：对改造前后的同一册分别调用，结果须逐字节相同。
    """
    lines = _split_lines(text)
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if BEGIN_RE.match(line):
            i += 1
            while i < len(lines) and not END_RE.match(lines[i]):
                i += 1
            i += 1                                   # 跳过 END
            continue
        if HEADING_RE.match(line) or LEAD_RE.match(line):
            i += 1
            continue
        out.append(line)
        i += 1
    collapsed: list[str] = []
    for line in out:
        if not line.strip() and collapsed and not collapsed[-1].strip():
            continue
        collapsed.append(line)
    return "\n".join(collapsed)


def generated_regions(lines: list[str], path: Path) -> list[tuple[int, int, str]]:
    """找节末生成区：``### N.M 形式化语义（IDL）`` 起、到下一个 ``##``/其它生成区/EOF 止。

    返回 ``[(start, end, section_num)]``（0 基半开区间）。区内只允许空行、导语、块，
    混入其它内容即 FAIL（防「把散文塞进生成区」被重渲染静默吞掉）。
    """
    regions: list[tuple[int, int, str]] = []
    for i, line in enumerate(lines):
        m = HEADING_RE.match(line)
        if m is None:
            continue
        enclosing = None
        for t in range(i):
            sm = SECTION_RE.match(lines[t])
            if sm:
                enclosing = sm.group(1)
        if enclosing != m.group(1):
            raise RenderError(
                f"{path.name}:{i + 1}: 生成标题 `### {m.group(1)}.{m.group(2)} 形式化语义（IDL）` "
                f"不在 `## {m.group(1)}.` 节内（当前节 `## {enclosing}.`）")
        j = i + 1
        while j < len(lines) and not lines[j].startswith("## ") and not GEN_START_RE.match(lines[j]):
            j += 1
        in_block = False
        leads = 0
        blocks = 0
        for k in range(i + 1, j):
            body = lines[k]
            if in_block:
                if END_RE.match(body):
                    in_block = False
                continue
            if BEGIN_RE.match(body):
                in_block = True
                blocks += 1
                continue
            if not body.strip():
                continue
            if LEAD_RE.match(body):
                leads += 1
                continue
            raise RenderError(
                f"{path.name}:{k + 1}: 生成区（`### {m.group(1)}.{m.group(2)} 形式化语义（IDL）` "
                f"之后、下一 `##` 之前）混入了非生成内容: {body[:60]!r}")
        if leads != 1:
            raise RenderError(
                f"{path.name}:{i + 1}: 生成区应有且仅有 1 行导语，实得 {leads} 行")
        if blocks == 0:
            raise RenderError(f"{path.name}:{i + 1}: 生成区没有任何 IDL 块")
        regions.append((i, j, m.group(1)))
    return regions


def section_index(lines: list[str], idx: int) -> tuple[int, str] | None:
    """``idx`` 之前最近一个带编号 ``## N.`` 节（返回 (行号, 编号)）。"""
    found: tuple[int, str] | None = None
    for i in range(idx):
        m = SECTION_RE.match(lines[i])
        if m:
            found = (i, m.group(1))
    return found


def section_end(lines: list[str], start: int) -> int:
    """节末插入点：下一个 ``##``/其它生成区/EOF 的行号。"""
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("## ") or GEN_START_RE.match(lines[j]):
            return j
    return len(lines)


def build_region(section: str, child: int, book: str,
                 op_ids: list[str], ops: dict[str, Op]) -> list[str]:
    """节末生成区（标题 + 导语 + 块序列）；末尾留一个空行。"""
    region = [f"### {section}.{child} 形式化语义（IDL）", "", lead_line(book), ""]
    for op_id in op_ids:
        region.append(f"<!-- IDL:{op_id} BEGIN -->")
        region.append(GENERATED_NOTE)
        region.append(f"**`{op_id}`**")
        region.append(FENCE_OPEN)
        region.extend(op_body_lines(ops[op_id]))
        region.append(FENCE_CLOSE)
        region.append(f"<!-- IDL:{op_id} END -->")
        region.append("")
    return region


def render_file(path: Path, ops: dict[str, Op], book: str) -> tuple[str, int]:
    """渲染一册（节末集中布局）；返回（新文本, 块数）。"""
    lines = _split_lines(read_text(path))
    spans = marker_spans(lines, path)

    for op_id in spans:
        if op_id not in ops:
            raise RenderError(f"{path.name}: 标记 `{op_id}` 没有对应的 `# id:` 源（空标记）")
        if ops[op_id].book != book:
            raise RenderError(
                f"{path.name}: 标记 `{op_id}` 的源在 {ops[op_id].source.name}（{ops[op_id].book}），"
                f"与落点册 `{book}` 不符")

    regions = generated_regions(lines, path)
    # 块的目标节：生成区内以标题号为序；散文内（旧布局）按所在 `## N.` 节
    grouped: dict[str, list[str]] = {}
    for op_id, (start, _end) in sorted(spans.items(), key=lambda kv: kv[1][0]):
        target = None
        for rstart, rend, num in regions:
            if rstart <= start < rend:
                target = num
                break
        if target is None:
            found = section_index(lines, start)
            if found is None:
                raise RenderError(
                    f"{path.name}:{start + 1}: 块 `{op_id}` 不在带编号 `## N.` 节内（不能生成节号）")
            target = found[1]
        grouped.setdefault(target, []).append(op_id)

    # 删掉旧生成区（整段）与散文里的旧块；倒序删除保持下标有效
    deletions: list[tuple[int, int, bool]] = [
        (rstart, rend - 1, False) for rstart, rend, _num in regions]
    for start, end in spans.values():
        if not any(rstart <= start < rend for rstart, rend, _num in regions):
            deletions.append((start, end, True))
    for start, end, cleanup in sorted(deletions, reverse=True):
        del lines[start:end + 1]
        if cleanup and 0 < start < len(lines) \
                and not lines[start - 1].strip() and not lines[start].strip():
            del lines[start]

    # 节末插入（倒序，保持下标有效）
    section_pos: dict[str, int] = {}
    for i, line in enumerate(lines):
        m = SECTION_RE.match(line)
        if m and m.group(1) not in section_pos:
            section_pos[m.group(1)] = i
    insertions: list[tuple[int, list[str]]] = []
    for num, op_ids in grouped.items():
        if num not in section_pos:
            raise RenderError(f"{path.name}: 找不到 `## {num}.` 节（块的目标节缺失）")
        idx = section_end(lines, section_pos[num])
        child = 1
        for k in range(section_pos[num] + 1, idx):
            m = H3_ANY_RE.match(lines[k])
            if m and m.group(1) == num:
                child = max(child, int(m.group(2)) + 1)
        region = build_region(num, child, book, op_ids, ops)
        if idx == 0 or lines[idx - 1].strip():
            region = [""] + region
        insertions.append((idx, region))
    for idx, region in sorted(insertions, key=lambda kv: kv[0], reverse=True):
        lines[idx:idx] = region
    return "\n".join(lines), sum(len(v) for v in grouped.values())


def render_all(root: Path) -> tuple[dict[Path, str], dict[str, Op], int]:
    """算出全部落点册的新文本；同时做 C/D 类断言。"""
    idl_dir = root / IDL_REL
    ops = load_ops(idl_dir)
    opcode_ids = load_opcodes(root)

    check_decode_vars(root)

    missing = sorted(set(ops) - opcode_ids)
    if missing:
        raise RenderError("源里的 id 不在 contracts/opcodes.yaml: " + ", ".join(missing))

    check_calls_declared(ops, load_declared(root))

    books = book_spec_files(root)
    for op in ops.values():
        if op.book not in books:
            raise RenderError(f"{op.source.name}: 找不到对应 spec 册 `{op.book}-*.md`")

    # 落点集合（全 spec 册扫一遍，含「不该有标记的册」）
    placed: dict[str, str] = {}
    per_file: dict[Path, dict[str, tuple[int, int]]] = {}
    for path in sorted((root / SPEC_REL).glob("*.md")):
        lines = _split_lines(read_text(path))
        spans = marker_spans(lines, path)
        if spans:
            per_file[path] = spans
        for op_id in spans:
            if op_id in placed:
                raise RenderError(
                    f"标记 `{op_id}` 出现在多个册: {placed[op_id]} / {path.name}")
            placed[op_id] = path.name
    orphans = sorted(set(placed) - set(ops))
    if orphans:
        raise RenderError("spec 标记没有对应源: " + ", ".join(orphans))
    unplaced = sorted(set(ops) - set(placed))
    if unplaced:
        raise RenderError("源没有落点标记: " + ", ".join(unplaced))

    rendered: dict[Path, str] = {}
    total = 0
    for path, spans in per_file.items():
        book = book_of_spec(path)
        if book is None:
            raise RenderError(f"{path.name}: 含 IDL 标记但不是 SimRISC-NN 册")
        if not any(ops[op_id].book == book for op_id in spans):
            raise RenderError(f"{path.name}: 含 IDL 标记但 {IDL_REL}/ 无对应源册")
        text, n = render_file(path, ops, book)
        rendered[path] = text
        total += n

    for book, path in books.items():
        book_ops = [op_id for op_id, op in ops.items() if op.book == book]
        if book_ops and path not in rendered:
            raise RenderError(f"{path.name}: 源册 `{book}` 有 {len(book_ops)} 条 operation 但册内无标记")
    return rendered, ops, total


def print_diff(path: Path, want: str) -> None:
    have_lines = read_text(path).split("\n")
    want_lines = want.split("\n")
    print(f"  {path.name}: 与渲染结果不一致（磁盘 {len(have_lines)} 行 / 渲染 {len(want_lines)} 行）")
    diff = list(difflib.unified_diff(have_lines, want_lines, fromfile="spec", tofile="rendered", lineterm=""))
    for line in diff[:20]:
        print("    " + line)
    if len(diff) > 20:
        print(f"    … 其余 {len(diff) - 20} 行见 --check 全量输出")


def run(root: Path) -> int:
    rendered, ops, total = render_all(root)
    drifted = [p for p, text in rendered.items() if not same_bytes(p, text)]
    if drifted:
        print(f"idl-render: FAIL（{len(drifted)} 册漂移 / 共 {len(rendered)} 册；"
              f"源 operation={len(ops)}、标记块={total}）")
        for path in drifted:
            print_diff(path, rendered[path])
        return 1
    print(f"idl-render: PASS（源 operation={len(ops)} 条 / 落点 {len(rendered)} 册 / "
          f"标记块 {total} 个，逐字节一致）")
    return 0


def write(root: Path) -> int:
    rendered, ops, total = render_all(root)
    changed = 0
    for path, text in rendered.items():
        if not same_bytes(path, text):
            path.write_bytes(text.encode("utf-8"))
            changed += 1
    print(f"idl-render: WROTE（源 operation={len(ops)} 条 / 标记块 {total} 个 / "
          f"更新 {changed} 册）")
    return 0


def run_rc(root: Path) -> int:
    """``run`` 的 rc 化版本：断言失败也返回 1（自检要观察 rc，不要异常冒泡）。"""
    try:
        return run(root)
    except RenderError as exc:
        print(f"  (RenderError) {exc}")
        return 1


def prose_hash(root: Path) -> int:
    """逐册打印「剥掉生成内容后」的散文 sha256（核对『散文零改动』）。"""
    paths = sorted((root / SPEC_REL).glob("SimRISC-*.md"))
    if not paths:
        print(f"idl-render: FAIL — {root / SPEC_REL}: 没有 SimRISC-*.md", file=sys.stderr)
        return 1
    for path in paths:
        digest = hashlib.sha256(strip_generated(read_text(path)).encode("utf-8")).hexdigest()
        print(f"{path.name}\t{digest}")
    return 0


def self_test() -> int:
    """临时树内注入自检：基线 PASS、各类注入 FAIL、还原后 PASS。"""
    repo = REPO
    tmp_parent = Path(tempfile.gettempdir()) / "opencode"
    tmp_parent.mkdir(parents=True, exist_ok=True)
    tmpdir = Path(tempfile.mkdtemp(prefix="idl-render-", dir=tmp_parent))
    ok = True

    def copy_tree(dst: Path) -> None:
        for rel in (IDL_REL, SPEC_REL):
            shutil.copytree(repo / rel, dst / rel)
        (dst / "contracts").mkdir()
        shutil.copy2(repo / OPCODES_REL, dst / OPCODES_REL)

    def first_op_file(root: Path) -> Path:
        return sorted((root / IDL_REL).glob("*.idl"))[0]

    def first_rendered_region(root: Path) -> tuple[Path, int]:
        for path in sorted((root / SPEC_REL).glob("SimRISC-*.md")):
            lines = read_text(path).split("\n")
            spans = marker_spans(lines, path)
            if spans:
                start, end = sorted(spans.values())[0]
                k = start + 1                      # 跳过 BEGIN/注释/粗体 id/围栏 ⇒ 首条正文行
                while k < end and (not lines[k].strip() or lines[k] == GENERATED_NOTE
                                   or lines[k] == FENCE_OPEN
                                   or (lines[k].startswith("**`") and lines[k].endswith("`**"))):
                    k += 1
                if k >= end:
                    raise RenderError(f"{path.name}: 首个标记块内没有正文行")
                return path, k
        raise RenderError("临时树内没有标记块")

    def first_heading(root: Path) -> tuple[Path, int]:
        for path in sorted((root / SPEC_REL).glob("SimRISC-*.md")):
            for i, line in enumerate(read_text(path).split("\n")):
                if HEADING_RE.match(line):
                    return path, i
        raise RenderError("临时树内没有生成标题")

    def first_lead(root: Path) -> tuple[Path, int]:
        for path in sorted((root / SPEC_REL).glob("SimRISC-*.md")):
            for i, line in enumerate(read_text(path).split("\n")):
                if LEAD_RE.match(line):
                    return path, i
        raise RenderError("临时树内没有导语")

    cases = ["baseline", "spec-char", "heading-drift", "drop-lead", "region-section-mismatch",
             "idl-drift", "drop-id", "undeclared-call", "decode-var-as-content",
             "qbang-undeclared-call", "restored"]
    try:
        for idx, name in enumerate(cases, 1):
            root = tmpdir / f"{idx}-{name}"
            root.mkdir()
            copy_tree(root)
            if name == "spec-char":
                # 改 spec 渲染结果的一个字符（模拟手改生成段）
                path, lineno = first_rendered_region(root)
                lines = read_text(path).split("\n")
                orig = lines[lineno]
                lines[lineno] = orig + " "        # 行尾加一个空格 ⇒ 字节不同
                if lines[lineno] == orig:
                    raise RenderError("空注入（spec-char）")
                path.write_text("\n".join(lines), encoding="utf-8")
            elif name == "heading-drift":
                # 改节末生成标题（模拟手改生成段）⇒ --check 须红
                path, lineno = first_heading(root)
                lines = read_text(path).split("\n")
                orig = lines[lineno]
                lines[lineno] = orig.replace("形式化语义", "形式语义")
                if lines[lineno] == orig:
                    raise RenderError("空注入（heading-drift）")
                path.write_text("\n".join(lines), encoding="utf-8")
            elif name == "drop-lead":
                # 删掉节末导语（模拟误删生成段）⇒ --check 须红
                path, lineno = first_lead(root)
                lines = read_text(path).split("\n")
                del lines[lineno]
                path.write_text("\n".join(lines), encoding="utf-8")
            elif name == "region-section-mismatch":
                # 把生成标题的节号改错（模拟整段被搬到别的节）⇒ 必须 FAIL（防止块被静默搬回错误节）
                path, lineno = first_heading(root)
                lines = read_text(path).split("\n")
                orig = lines[lineno]
                lines[lineno] = re.sub(r"^### (\d+)\.", lambda m: f"### {int(m.group(1)) + 1}.", orig)
                if lines[lineno] == orig:
                    raise RenderError("空注入（region-section-mismatch）")
                path.write_text("\n".join(lines), encoding="utf-8")
            elif name == "idl-drift":
                # 改源但不重渲染
                path = first_op_file(root)
                text = read_text(path)
                path.write_text(text.replace("\n", "\n# drift-injection\n", 1), encoding="utf-8")
                if read_text(path) == text:
                    raise RenderError("空注入（idl-drift）")
            elif name == "drop-id":
                # 删一条 `# id:` 行但保留标记（⇒ 空标记）
                path = first_op_file(root)
                lines = read_text(path).split("\n")
                for i, line in enumerate(lines):
                    if ID_RE.match(line):
                        del lines[i]
                        break
                else:
                    raise RenderError("空注入（drop-id）：没有找到 `# id:` 行")
                path.write_text("\n".join(lines), encoding="utf-8")
            elif name == "undeclared-call":
                # 调用语义库未声明的函数（模拟「例句引用了不存在的库函数」）
                path = first_op_file(root)
                text = read_text(path)
                injected = text + "rd_read_typo(6'd0);\n"
                path.write_text(injected, encoding="utf-8")
                if injected == text:
                    raise RenderError("空注入（undeclared-call）")
            elif name == "qbang-undeclared-call":
                # `?` 后缀函数名未声明（CALL_RE 要求标识符后紧跟 `(` ⇒ 只有 QBANG_CALL_RE 抓得到；
                # 缺了它这类调用会被断言 E 静默漏检，m15-idl-015）
                path = first_op_file(root)
                text = read_text(path)
                injected = text + "Boolean probe_q = no_such_predicate?(32'd0);\n"
                path.write_text(injected, encoding="utf-8")
                if injected == text:
                    raise RenderError("空注入（qbang-undeclared-call）")
            elif name == "decode-var-as-content":
                # 把解码变量当寄存器内容用（m15-idl-014 的缺陷类：`rdHC[0]` 取到的是寄存器号的位）
                path = first_op_file(root)
                text = read_text(path)
                path.write_text(text + "Bits<1> probe = rdHC[0];\n", encoding="utf-8")
                if read_text(path) == text:
                    raise RenderError("空注入（decode-var-as-content）")
            elif name == "restored":
                # 重新从真实树拷贝 ⇒ 还原后必须回绿
                shutil.rmtree(root)
                root.mkdir()
                copy_tree(root)

            rc = run_rc(root)
            expect_zero = name in ("baseline", "restored")
            good = (rc == 0) == expect_zero
            print(f"[self-test {idx}/{len(cases)}] {name}: rc={rc} 期望 rc={'0' if expect_zero else '!=0'} "
                  f"⇒ {'PASS' if good else 'FAIL'}")
            ok = ok and good
    except RenderError as exc:
        print(f"[self-test] 注入准备失败: {exc}", file=sys.stderr)
        ok = False
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    print("idl-render self-test: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Render idl/*.idl into spec/ marker blocks")
    ap.add_argument("--check", action="store_true", help="只校验，不写盘")
    ap.add_argument("--self-test", action="store_true", help="临时树内注入自检")
    ap.add_argument("--prose-hash", action="store_true", help="打印各册剥掉生成内容后的散文哈希")
    ap.add_argument("--root", type=Path, default=REPO, help="另一棵同布局的树（默认仓库根）")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()
    if args.prose_hash:
        try:
            return prose_hash(args.root)
        except RenderError as exc:
            print(f"idl-render: FAIL — {exc}", file=sys.stderr)
            return 1
    try:
        return run(args.root) if args.check else write(args.root)
    except RenderError as exc:
        print(f"idl-render: FAIL — {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
