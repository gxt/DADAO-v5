#!/usr/bin/env python3
"""盘点 `idl/*.idl` + `idl/lib/*.idl` 实际用到的 IDL 语法构造，并校验两份盘点文档。

为什么
------
M17 的执行器用 Python 重写 IDL 前端（用户 2026-11-20 定，不用 Ruby/`idlc`）。UDB 的
`idl.treetop` 有 652 行语法，但本仓只用到其中一小部分；本脚本**现场统计**这部分，
供 `idl/syntax-subset.md`（构造清单）与 `idl/width-rules.md`（宽度规则）引用，
并机械校验两份文档的数字与出处没有漂移。

计数口径
--------
* 扫描面 = `idl/SimRISC-*.idl` + `idl/lib/*.idl`（**不含** `spec/` 里的渲染结果，
  两者逐字节相等由 `idl/render.py --check` 保证）。
* 「次数」= 出现次数；一律先抹掉两处自然语言（`#` 行尾注释、`description { … }` 自由文本块）
  再统计——它们会引述伪码；只有 `S01`–`S03` 按原文统计（`S01`/`S02` 是注释、`S03` 是文件头）。
* 运算符统计前把 `Bits<N>` 与字面量归一化，避免 `<`/`>` 被 `Bits<64>`、`32'h…` 误计。
* 花括号按位置分类：行首/表达式位置的 `{` 记作拼接或复制，语句块与函数体/枚举体的
  `{` 不计（判据见 `_expr_brace_positions`）。
* 所有数字现场派生，**不写死**；`--check` 把文档里的数字与出处逐条对回本脚本。

用法
----
* ``python3 idl/subset_stats.py``            # 打印构造计数（人读 / 给文档抄数）
* ``python3 idl/subset_stats.py --json``     # 机器可读
* ``python3 idl/subset_stats.py --check``    # 校验 syntax-subset.md / width-rules.md
* ``--root DIR``：在另一棵树（同布局）里运行，供注入自检使用

退出码：0 = 通过；1 = 统计或文档校验失败。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
IDL_REL = "idl"
LIB_REL = "idl/lib"
SUBSET_DOC = "idl/syntax-subset.md"
WIDTH_DOC = "idl/width-rules.md"
OPCODES_REL = "contracts/opcodes.yaml"
SEMANTICS_REL = "spec/IDL-ISA语义描述语言与语义库.md"
CONTRACT_ISA_REL = ".tao/contracts/contract-isa.md"


class CheckError(Exception):
    """任一断言失败。"""


# ── 文本装载 ────────────────────────────────────────────────────────────────

def idl_files(root: Path) -> list[Path]:
    books = sorted((root / IDL_REL).glob("SimRISC-*.idl"))
    libs = sorted((root / LIB_REL).glob("*.idl"))
    if not books or not libs:
        raise CheckError(f"{IDL_REL}: 找不到源册（books={len(books)}, lib={len(libs)}）")
    return books + libs


def strip_comments(text: str) -> str:
    """抹掉 `#` 行尾注释与 `description { … }` 散文块（两者都是自然语言，不是语法使用）。

    `description` 块是自由文本，里面会引述伪码（如 `` `+Inf` ``、`floor(…)`、`GF(2)`），
    按字面统计会把散文误计成语法；语言里没有字符串字面量，故 `#` 直接按行切。
    """
    out: list[str] = []
    in_desc = False
    for line in text.split("\n"):
        if in_desc:
            if re.match(r"^\s*\}\s*$", line):     # description 块唯一的结构行就是收尾 `}`
                in_desc = False
            out.append("")
            continue
        if re.match(r"^\s*description\s*\{\s*$", line):
            in_desc = True
            out.append("")
            continue
        out.append(line.split("#", 1)[0])
    return "\n".join(out)


@dataclass(frozen=True)
class Source:
    path: Path
    raw: str
    code: str

    @property
    def rel(self) -> str:
        return self.path.as_posix()


def load_sources(root: Path) -> list[Source]:
    out: list[Source] = []
    for path in idl_files(root):
        raw = path.read_text(encoding="utf-8")
        out.append(Source(path=path.relative_to(root), raw=raw, code=strip_comments(raw)))
    return out


def normalize_ops(code: str) -> str:
    """归一化后用于运算符计数：类型参数与字面量不含比较/移位符。"""
    text = re.sub(r"Bits<\d+>", "BINSTYPE", code)
    text = re.sub(r"\d*\'\s*[sS]?[dhboDHBO][0-9a-fA-F_]+", "LIT", text)
    text = re.sub(r"0[xX][0-9a-fA-F_]+", "LIT", text)
    return text


def strip_widening(code: str) -> str:
    """去掉加宽运算（反引号形式）后再数普通移位，避免 `` `<< `` 被当成 `<<`。"""
    return code.replace("`+", "").replace("`*", "").replace("`<<", "")


# ── 构造统计 ────────────────────────────────────────────────────────────────

EXPR_PREFIX = set("=(,[:{?><!+-*/%&|^~")
BANK_RE = re.compile(r"\b(rd|rb|rf|ra|fo|ft)\s*\[")
BLOCK_TAIL_RE = re.compile(r"(\belse|\)|\bbody|\bdescription|\bfunction\s+\w+\??|\benum\s+\w+)\s*$")


def _expr_brace_positions(code: str) -> list[tuple[int, int]]:
    """返回「表达式花括号」的（行号, 列号）。

    判据：`{` 之前的非空白前缀不是 `)`/`else`/`body`/`description`/`function NAME`/
    `enum NAME` 结尾 ⇒ 视为表达式位置（拼接或复制）。语句块与函数体/枚举体的 `{`
    一律以这些形式开头，故排除。
    """
    out: list[tuple[int, int]] = []
    for lineno, line in enumerate(code.split("\n"), 1):
        for m in re.finditer(r"\{", line):
            prefix = line[: m.start()].rstrip()
            if not prefix or BLOCK_TAIL_RE.search(prefix):
                continue
            if prefix[-1] in EXPR_PREFIX:
                out.append((lineno, m.start() + 1))
    return out


def count_occurrences(sources: list[Source], pattern: re.Pattern[str], *,
                      field: str = "code") -> list[tuple[str, int]]:
    hits: list[tuple[str, int]] = []
    for src in sources:
        text = src.raw if field == "raw" else src.code
        for m in pattern.finditer(text):
            hits.append((src.rel, text[: m.start()].count("\n") + 1))
    return hits


def count_line_matches(sources: list[Source], pattern: re.Pattern[str], *,
                       field: str = "code") -> list[tuple[str, int]]:
    hits: list[tuple[str, int]] = []
    for src in sources:
        text = src.raw if field == "raw" else src.code
        for lineno, line in enumerate(text.split("\n"), 1):
            if pattern.search(line):
                hits.append((src.rel, lineno))
    return hits


def _paren_braces(sources: list[Source]) -> list[tuple[str, int]]:
    return [(src.rel, ln) for src in sources for ln, _col in _expr_brace_positions(src.code)]


def _replication(sources: list[Source]) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for src in sources:
        exprs = _expr_brace_positions(src.code)
        for ln, col in exprs:
            line = src.code.split("\n")[ln - 1]
            if re.match(r"\{\s*\d+\s*\{", line[col - 1:]):
                out.append((src.rel, ln))
    return out


def _assign_lines(sources: list[Source]) -> list[tuple[str, int]]:
    pat = re.compile(r"(?<![=!<>+\-*/&|^~%])=(?!=)")
    return count_line_matches(sources, pat)


def _slice_assign_lines(sources: list[Source]) -> list[tuple[str, int]]:
    pat = re.compile(r"(?<![=!<>+\-*/&|^~%])=(?!=)")
    out: list[tuple[str, int]] = []
    for src in sources:
        for lineno, line in enumerate(src.code.split("\n"), 1):
            m = pat.search(line)
            if not m:
                continue
            if re.search(r"\[[^\[\]]*:[^\[\]]*\]", line[: m.start()]):
                out.append((src.rel, lineno))
    return out


def _bit_assign_lines(sources: list[Source]) -> list[tuple[str, int]]:
    pat = re.compile(r"(?<![=!<>+\-*/&|^~%])=(?!=)")
    out: list[tuple[str, int]] = []
    for src in sources:
        for lineno, line in enumerate(src.code.split("\n"), 1):
            m = pat.search(line)
            if not m:
                continue
            lhs = line[: m.start()]
            # 左值末段是单下标（无冒号），且不是寄存器组下标本身
            m2 = re.search(r"\[([^\[\]:]*)\]\s*$", lhs)
            if m2 and not BANK_RE.search(lhs[: m2.start() + 2]):
                out.append((src.rel, lineno))
    return out


def _double_subscript(sources: list[Source]) -> list[tuple[str, int]]:
    return count_occurrences(sources, re.compile(r"\w+\s*\[[^\[\]]*\]\s*\["))


def _bit_index(sources: list[Source]) -> list[tuple[str, int]]:
    """单比特/单下标**取位**：`[expr]`（无冒号）且不是寄存器组数组下标。"""
    out: list[tuple[str, int]] = []
    for src in sources:
        for m in re.finditer(r"\[([^\[\]:]*)\]", src.code):
            prefix = src.code[: m.start()]
            word = re.search(r"([A-Za-z_]\w*)\s*$", prefix.rstrip())
            if word and word.group(1) in {"rd", "rb", "rf", "ra", "fo", "ft"}:
                continue
            out.append((src.rel, prefix.count("\n") + 1))
    return out


def _slice_reads(sources: list[Source]) -> list[tuple[str, int]]:
    return count_occurrences(sources, re.compile(r"\[[^\[\]]*:[^\[\]]*\]"))


def _call_names(sources: list[Source]) -> dict[str, int]:
    skip = {"if", "for", "while", "return", "assert", "sizeof", "true", "false"}
    counts: dict[str, int] = {}
    for src in sources:
        for m in re.finditer(r"(?<![\w$.])([A-Za-z_]\w*\??)\s*\(", src.code):
            name = m.group(1)
            if name in skip:
                continue
            counts[name] = counts.get(name, 0) + 1
    return counts


def _call_sites(sources: list[Source]) -> list[tuple[str, int]]:
    skip = {"if", "for", "while", "return", "assert", "sizeof", "true", "false"}
    out: list[tuple[str, int]] = []
    for src in sources:
        for m in re.finditer(r"(?<![\w$.])([A-Za-z_]\w*\??)\s*\(", src.code):
            if m.group(1) in skip:
                continue
            out.append((src.rel, src.code[: m.start()].count("\n") + 1))
    return out


def categories(root: Path) -> tuple[list[tuple[str, str, int, tuple[str, int] | None]], dict]:
    """返回 [(ID, 说明, 次数, 首个出处)] 与补充信息。"""
    srcs = load_sources(root)
    norm = [Source(path=s.path, raw=s.raw, code=normalize_ops(strip_widening(s.code))) for s in srcs]
    ops_src = [Source(path=s.path, raw=s.raw, code=normalize_ops(s.code)) for s in srcs]

    def occ(cid: str, label: str, hits: list[tuple[str, int]]) -> tuple[str, str, int, tuple[str, int] | None]:
        return (cid, label, len(hits), hits[0] if hits else None)

    rows = [
        occ("S01", "operation 头 `# id:`", count_occurrences(srcs, re.compile(r"^#\s*id:\s*\S+\s*$", re.M), field="raw")),
        occ("S02", "注释行（含 `#` 的源码行）", count_line_matches(srcs, re.compile(r"#"), field="raw")),
        occ("S03", "`%version` 文件头", count_occurrences(srcs, re.compile(r"^%version:", re.M), field="raw")),
        occ("S04", "枚举声明 `enum X {`", count_occurrences(srcs, re.compile(r"^enum\s+\w+\s*\{", re.M))),
        occ("S05", "枚举成员引用 `Enum::Member`", count_occurrences(srcs, re.compile(r"\b[A-Za-z_]\w*::[A-Za-z_]\w*"))),
        occ("S06", "`Bits<N>` 类型", count_occurrences(srcs, re.compile(r"\bBits<\d+>"))),
        occ("S07", "`U32` 类型", count_occurrences(srcs, re.compile(r"\bU32\b"))),
        occ("S08", "`Boolean` 类型", count_occurrences(srcs, re.compile(r"\bBoolean\b"))),
        occ("S09", "局部变量/常量声明（`Bits<N> x =`、`U32`、`Boolean`）",
            count_line_matches(srcs, re.compile(r"^\s*(?:Bits<\d+>|U32|Boolean)\s+\w+\s*="))),
        occ("S66", "无初值声明行（`Bits<N> x;` 等）",
            count_line_matches(srcs, re.compile(r"^\s*(?:Bits<\d+>|U32|Boolean)\s+\w+\s*;"))),
        occ("S10", "`function` 声明", count_occurrences(srcs, re.compile(r"^function\s+\w+\??\s*\{", re.M))),
        occ("S11", "`?` 后缀谓词函数名（声明或调用）", count_occurrences(srcs, re.compile(r"\b[A-Za-z_]\w*\?"))),
        occ("S12", "`if (...)` 条件语句（含 `else if`）", count_occurrences(srcs, re.compile(r"\bif\s*\("))),
        occ("S13", "`else if` 分支", count_occurrences(srcs, re.compile(r"\belse\s+if\s*\("))),
        occ("S14", "`else {` 分支", count_occurrences(srcs, re.compile(r"\belse\s*\{"), )),
        occ("S15", "`for (...)` 循环", count_occurrences(srcs, re.compile(r"\bfor\s*\("))),
        occ("S16", "`return` 语句", count_occurrences(srcs, re.compile(r"\breturn\b"))),
        occ("S17", "`++` 自增", count_occurrences(srcs, re.compile(r"\+\+"))),
        occ("S18", "赋值/初始化语句行（`=`，不含 `==`/`<=`/`>=`/`!=`）", _assign_lines(srcs)),
        occ("S19", "切片赋值行（左值含 `[msb:lsb]`）", _slice_assign_lines(srcs)),
        occ("S20", "单比特赋值行（左值末段为单下标）", _bit_assign_lines(srcs)),
        occ("S21", "加宽加 `` `+ ``", count_occurrences(srcs, re.compile(r"`\+"))),
        occ("S22", "加宽乘 `` `* ``", count_occurrences(srcs, re.compile(r"`\*"))),
        occ("S23", "加宽左移 `` `<< ``", count_occurrences(srcs, re.compile(r"`<<"))),
        occ("S24", "逻辑左移 `<<`", count_occurrences(norm, re.compile(r"<<(?!>)"))),
        occ("S25", "逻辑右移 `>>`", count_occurrences(norm, re.compile(r">>(?!>)"))),
        occ("S26", "算术右移 `>>>`", count_occurrences(norm, re.compile(r">>>"))),
        occ("S27", "相等比较 `==` / `!=`", count_occurrences(norm, re.compile(r"==|!="))),
        occ("S28", "大小比较 `< <= > >=`", count_occurrences(norm, re.compile(r"<=|>=|(?<![<>=!])<(?![<=])|(?<![<>=!-])>(?![>=])"))),
        occ("S29", "逻辑 `&&` / `||` / `!`", count_occurrences(norm, re.compile(r"&&|\|\||!(?!=)"))),
        occ("S30", "位运算 `& | ^ ~`", count_occurrences(norm, re.compile(r"(?<!&)&(?!&)|(?<!\|)\|(?!\|)|\^|~"))),
        occ("S31", "三目 `? :`", count_occurrences(ops_src, re.compile(r"\?(?=\s)|(?<=[\w)\]])\?(?![\w(])"))),
        occ("S32", "拼接/复制表达式（表达式位置的花括号）", _paren_braces(srcs)),
        occ("S33", "复制 `{N{a}}`（N 为字面常量）", _replication(srcs)),
        occ("S34", "位切片 `[msb:lsb]`（读与写左值）", _slice_reads(srcs)),
        occ("S35", "单比特取位/单下标取值 `[expr]`", _bit_index(srcs)),
        occ("S36", "双重下标 `x[i][j]`（数组 + 切片/取位）", _double_subscript(srcs)),
        occ("S37", "`$signed(...)` 有符号视图", count_occurrences(srcs, re.compile(r"\$signed\s*\("))),
        occ("S38", "Verilog 定宽字面量（`6'd0`/`32'h…`/`1'b0`，含下划线）",
            count_occurrences(srcs, re.compile(r"\d*\'\s*[sS]?[dhboDHBO][0-9a-fA-F_]+"))),
        occ("S39", "有符号字面量 `0s` / `'sd`", count_occurrences(srcs, re.compile(r"\b0s\b|\d+\'s[dh]"))),
        occ("S40", "C 风格十六进制字面量 `0x…`", count_occurrences(srcs, re.compile(r"0[xX][0-9a-fA-F_]+"))),
        occ("S41", "函数调用（不含 `if`/`for`/`return` 等关键字）", _call_sites(srcs)),
        occ("S42", "`rd[]` 访问", count_occurrences(srcs, re.compile(r"\brd\s*\["))),
        occ("S43", "`rb[]` 访问", count_occurrences(srcs, re.compile(r"\brb\s*\["))),
        occ("S44", "`rf[]` 访问", count_occurrences(srcs, re.compile(r"\brf\s*\["))),
        occ("S45", "`ra[]` 访问", count_occurrences(srcs, re.compile(r"\bra\s*\["))),
        occ("S46", "`fo[]` 访问（rf 的 64 位视图）", count_occurrences(srcs, re.compile(r"\bfo\s*\["))),
        occ("S47", "`ft[]` 访问（rf 的低 32 位视图）", count_occurrences(srcs, re.compile(r"\bft\s*\["))),
        occ("S48", "`raise(...)`", count_occurrences(srcs, re.compile(r"\braise\s*\("))),
        occ("S49", "`mode()`", count_occurrences(srcs, re.compile(r"\bmode\s*\(\s*\)"))),
        occ("S50", "`ip()`", count_occurrences(srcs, re.compile(r"\bip\s*\(\s*\)"))),
        occ("S51", "`read_memory(`", count_occurrences(srcs, re.compile(r"\bread_memory\s*\("))),
        occ("S52", "`write_memory(`", count_occurrences(srcs, re.compile(r"\bwrite_memory\s*\("))),
        occ("S53", "`is_naturally_aligned(`", count_occurrences(srcs, re.compile(r"\bis_naturally_aligned\s*\("))),
        occ("S54", "`reservation_set(` / `reservation_clear_all(`",
            count_occurrences(srcs, re.compile(r"\breservation_(?:set|clear_all)\s*\("))),
        occ("S55", "`store_conditional(`", count_occurrences(srcs, re.compile(r"\bstore_conditional\s*\("))),
        occ("S56", "`jump(`", count_occurrences(srcs, re.compile(r"\bjump\s*\("))),
        occ("S57", "`ras_push(` / `ras_pop(` / `ras_cnt(`",
            count_occurrences(srcs, re.compile(r"\bras_(?:push|pop|cnt)\s*\("))),
        occ("S58", "`cfx_*` 库调用", count_occurrences(srcs, re.compile(r"\bcfx_\w+\s*\("))),
        occ("S59", "浮点库调用（`ft_*`/`fo_*`/`softfloat_*`/`is_sp_*`/`is_dp_*`）",
            count_occurrences(srcs, re.compile(r"\b(?:ft|fo|softfloat|is_sp|is_dp)_\w+\??\s*\("))),
        # 未使用构造（次数必须为 0；把「不使用」变成机械断言）
        occ("S60", "`while` 循环（不使用）", count_occurrences(srcs, re.compile(r"\bwhile\s*\("))),
        occ("S61", "`assert` / `sizeof`（不使用）",
            count_occurrences(srcs, re.compile(r"\b(?:assert|sizeof)\b"))),
        occ("S62", "`struct` / `bitfield` / `tuple` / `include`（不使用）",
            count_occurrences(srcs, re.compile(r"\b(?:struct|bitfield|tuple|include)\b"))),
        occ("S63", "`fetch_memory(`（不使用）", count_occurrences(srcs, re.compile(r"\bfetch_memory\s*\("))),
        occ("S64", "RISC-V 式 `X[…]` / `CSR[…]` / `$encoding`（不使用）",
            count_occurrences(srcs, re.compile(r"\b(?:X|CSR)\s*\[|\$encoding"))),
        occ("S65", "变量作复制次数 `{N{a}}`（N 非字面常量）",
            count_occurrences(srcs, re.compile(r"\{\s*[A-Za-z_]\w*\s*\{")), ),
    ]

    extra = {
        "books": {s.path.name: len(re.findall(r"^#\s*id:\s*\S+\s*$", s.raw, re.M))
                  for s in srcs if s.path.parent.name == IDL_REL},
        "calls": _call_names(srcs),
        "total_calls": sum(_call_names(srcs).values()),
        "distinct_calls": len(_call_names(srcs)),
    }
    return rows, extra


def opcode_ids(root: Path) -> list[str]:
    text = (root / OPCODES_REL).read_text(encoding="utf-8")
    ids = re.findall(r"^-\s+id:\s*(\S+)\s*$", text, re.M)
    if not ids:
        raise CheckError(f"{OPCODES_REL}: 没有解析到 `- id:` 条目")
    return ids


# ── 文档校验：构造清单 ──────────────────────────────────────────────────────

ROW_RE = re.compile(
    r"^\|\s*(S\d{2})\s*\|((?:\\\||[^|])*)\|((?:\\\||[^|])*)\|((?:\\\||[^|])*)\|\s*$")


def parse_subset_doc(path: Path) -> dict[str, tuple[int, str]]:
    rows: dict[str, tuple[int, str]] = {}
    for lineno, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
        m = ROW_RE.match(line)
        if not m:
            continue
        cid, _label, count, cite = m.groups()
        if cid in rows:
            raise CheckError(f"{path.name}:{lineno}: 构造 ID `{cid}` 重复")
        rows[cid] = (int(count.strip()), cite.strip())
    if not rows:
        raise CheckError(f"{path.name}: 没有解析到任何构造行（| Sxx | 构造 | 次数 | 出处 |）")
    return rows


def check_subset_doc(root: Path, rows: list[tuple[str, str, int, tuple[str, int] | None]],
                     extra: dict) -> str:
    doc = root / SUBSET_DOC
    if not doc.is_file():
        raise CheckError(f"{SUBSET_DOC}: 文件不存在")
    parsed = parse_subset_doc(doc)
    computed = {cid: (count, first) for cid, _label, count, first in rows}

    missing = sorted(set(computed) - set(parsed))
    extra_ids = sorted(set(parsed) - set(computed))
    if missing:
        raise CheckError(f"{SUBSET_DOC}: 缺构造行（脚本统计到但文档没写）: {', '.join(missing)}")
    if extra_ids:
        raise CheckError(f"{SUBSET_DOC}: 多出未知构造 ID（脚本没有这一类）: {', '.join(extra_ids)}")

    bad: list[str] = []
    for cid, (count, first) in sorted(computed.items()):
        doc_count, cite = parsed[cid]
        if doc_count != count:
            bad.append(f"{cid}: 文档写 {doc_count}，现场统计 {count}")
            continue
        if count == 0:
            if cite not in ("—", "无", "-"):
                bad.append(f"{cid}: 次数为 0，出处应为 `—`，实得 {cite!r}")
            continue
        m = re.search(r"`?(idl/[\w./-]+\.idl):(\d+)`?", cite)
        if not m:
            bad.append(f"{cid}: 出处须形如 `idl/<file>.idl:<行>`，实得 {cite!r}")
            continue
        rel, lineno = m.group(1), int(m.group(2))
        if first is None:
            bad.append(f"{cid}: 脚本没有首个出处，文档却写了 {cite!r}")
            continue
        if (rel, lineno) != first:
            bad.append(f"{cid}: 出处 {rel}:{lineno} 与首次出现 {first[0]}:{first[1]} 不符")
    if bad:
        raise CheckError(f"{SUBSET_DOC}: 构造计数/出处不一致:\n  " + "\n  ".join(bad))

    # 总 operation 数与 contracts/opcodes.yaml 独立对账（不从 IDL 自证）
    id_rows = [r for r in rows if r[0] == "S01"]
    total = id_rows[0][2]
    opcodes = opcode_ids(root)
    if total != len(opcodes):
        raise CheckError(
            f"operation 数不自洽: idl `# id:` = {total}，{OPCODES_REL} `- id:` = {len(opcodes)}")

    # 每册 operation 数表：`| `idl/SimRISC-NN.idl` | N |`
    book_re = re.compile(r"^\|\s*`?(idl/SimRISC-(\d{2})\.idl)`?\s*\|\s*(\d+)\s*\|")
    books: dict[str, int] = {}
    for line in doc.read_text(encoding="utf-8").split("\n"):
        m = book_re.match(line)
        if m:
            books[m.group(2)] = int(m.group(3))
    expect_books = {re.match(r"SimRISC-(\d{2})", name).group(1): c
                    for name, c in extra["books"].items()}
    if books != expect_books:
        raise CheckError(f"{SUBSET_DOC}: 每册 operation 数与现场统计不符: {books} vs {expect_books}")
    if sum(books.values()) != total:
        raise CheckError(f"每册 operation 数之和 {sum(books.values())} ≠ 总数 {total}")

    # 关系断言：两侧独立派生的事实互相印证（任一侧漂移即红）
    n = {cid: count for cid, _label, count, _first in rows}
    if n["S49"] != n["S48"]:
        raise CheckError(f"`mode()` 次数 {n['S49']} ≠ `raise(` 次数 {n['S48']}"
                         f"（mode() 只作 raise 的 from_mode 实参）")
    if n["S33"] > n["S32"]:
        raise CheckError(f"复制式 {n['S33']} > 拼接/复制表达式 {n['S32']}（复制必须是表达式花括号的子集）")

    return (f"构造 {len(computed)} 类、operation {total} 条（= opcodes.yaml）、"
            f"每册数 {len(books)} 册一致、关系断言 2 条通过")


# ── 文档校验：宽度规则 ──────────────────────────────────────────────────────

# 规则 ID → (出处文件, 节号, 该节必须出现的锚点正则)
# 锚点把「出处」钉到具体章节的正文，换错节号/换错文件都会红。
RULES: dict[str, tuple[str, str, str]] = {
    "W01": (SEMANTICS_REL, "1", r"Bits<N>"),
    "W02": (SEMANTICS_REL, "1", r"U32"),
    "W03": (SEMANTICS_REL, "1", r"Boolean"),
    "W04": (SEMANTICS_REL, "1", r"符号扩展"),
    "W05": (SEMANTICS_REL, "1", r"\$signed"),
    "W06": (SEMANTICS_REL, "1", r"结果宽 = 两操作数最大宽 \+ 1"),
    "W07": (SEMANTICS_REL, "1", r"编译期常量"),
    "W08": (SEMANTICS_REL, "4.7", r"加宽乘"),
    "W09": (SEMANTICS_REL, "3", r"四组寄存器各 64 个 64 位"),
    "W10": (SEMANTICS_REL, "3", r"写宽度"),
    "W11": (SEMANTICS_REL, "4.4", r"大端"),
    "W12": (SEMANTICS_REL, "4.4", r"结果零扩展至 64 位"),
    "W13": (CONTRACT_ISA_REL, "1.1", r"每组 64 个，每个寄存器 64 位"),
    "W14": (CONTRACT_ISA_REL, "1.3.1", r"固定为 0，只读"),
    "W15": (CONTRACT_ISA_REL, "1.3.2", r"当前正在执行的指令的地址"),
    "W16": (CONTRACT_ISA_REL, "1.3.3", r"\[33:32\]"),
    "W17": (CONTRACT_ISA_REL, "1.3.4", r"RACNT"),
    "W18": (CONTRACT_ISA_REL, "1.4", r"octa"),
    "W19": (CONTRACT_ISA_REL, "1.5", r"rb\[47:0\]"),
    "W20": (CONTRACT_ISA_REL, "1.6", r"大端序"),
    "W21": (CONTRACT_ISA_REL, "2.5", r"octa（64 位）"),
    "W22": ("spec/SimRISC-00-指令系统设计.md", "2.3", r"只写目的寄存器低 32 位，高 32 位保持原值"),
    "W23": ("spec/SimRISC-04-64位数据运算.md", "1.3", r"结果（-1/0/1）写入目的寄存器全 64 位"),
    "W24": ("spec/SimRISC-04-64位数据运算.md", "2.2", r"算术右移，高位补"),
    "W25": ("spec/SimRISC-04-64位数据运算.md", "2.2", r"低位补零"),
    "W26": ("spec/SimRISC-08-32位数据运算.md", "1.1", r"溢出部分静默丢弃"),
    "W27": ("spec/SimRISC-12-其它指令.md", "1.1", r"只写低 32/16/8 位"),
    "W28": (SEMANTICS_REL, "2", r"imms12"),
}

@dataclass(frozen=True)
class Undefined:
    """一条「本仓规范未定义」：文档行须写明 anchor；probe 文件的相关节（散文，剥掉代码块）
    必须**不出现** absent；`repo_wide` 时还要求 `spec/`+`.tao/contracts/` 全文（散文）都不出现；
    usage 非空时，该用法还须在 `.idl` 里真实出现（证明缺口有实际影响）。"""
    anchor: str
    probe: str
    section: str | None
    absent: str
    usage: str | None
    repo_wide: bool = True


# 未定义项：凡本仓 `spec/` 与 `.tao/contracts/` 都查不到定义的，一律列这里，不自行裁定。
UNDEFINED: dict[str, Undefined] = {
    "U01": Undefined("bits_cast", SEMANTICS_REL, None, r"bits_cast", None),
    "U02": Undefined("sign_cast", SEMANTICS_REL, None, r"sign_cast", None),
    "U03": Undefined("bits_width_cast", SEMANTICS_REL, None, r"bits_width_cast", None),
    "U04": Undefined("0s", SEMANTICS_REL, "1", r"\d*'s[dh]|(?<![\w.])0s\b", r"\b0s\b|'s[dh]",
                     repo_wide=False),
    "U05": Undefined("拼接", SEMANTICS_REL, "1", r"(拼接|复制)[^。\n]{0,30}宽",
                     r"\{[^{}\n]*,[^{}\n]*\}", repo_wide=False),
    "U06": Undefined("`*", SEMANTICS_REL, "4.7", r"结果宽", r"`\*", repo_wide=False),
    "U07": Undefined("MXLEN", SEMANTICS_REL, None, r"MXLEN", None),
    "U08": Undefined("除零", SEMANTICS_REL, None, r"除零", r"(?<![/*])/(?![/*])|%",
                     repo_wide=False),
    "U09": Undefined("迭代", SEMANTICS_REL, "1", r"迭代", r"\bfor\s*\(", repo_wide=False),
    "U10": Undefined("结果宽度", SEMANTICS_REL, "1", r"结果宽度|两侧取较宽|截断|同宽",
                     r"Bits<(?:8|16|32)>\s+\w+\s*=[^;\n]*[+\-*/]", repo_wide=False),
}

RULE_ROW_RE = re.compile(r"^\|\s*(W\d{2})\s*\|([^|]*)\|([^|]*)\|\s*$")
UNDEF_ROW_RE = re.compile(r"^\|\s*(U\d{2})\s*\|([^|]*)\|([^|]*)\|\s*$")
SECTION_HEAD_RE = re.compile(r"^(#{2,4})\s+§?(\d+(?:\.\d+)*)\.?\s")


def section_body(text: str, number: str) -> str | None:
    """取 `§<number>` 节的正文（到下一个同级/更高级标题、或非子孙编号标题止）。"""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        m = SECTION_HEAD_RE.match(line)
        if m and m.group(2) == number:
            level = len(m.group(1))
            for j in range(i + 1, len(lines)):
                m2 = SECTION_HEAD_RE.match(lines[j])
                if not m2:
                    continue
                if len(m2.group(1)) <= level or not m2.group(2).startswith(number + "."):
                    return "\n".join(lines[i + 1: j])
            return "\n".join(lines[i + 1:])
    return None


def strip_fences(text: str) -> str:
    """去掉 ``` 围栏内的代码块（保留行数与空行）：散文才是「定义」的载体，
    渲染进 spec 的 `.idl` 代码块与语义库代码块是**用例**，不是定义。"""
    out: list[str] = []
    inside = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            inside = not inside
            out.append("")
            continue
        out.append("" if inside else line)
    return "\n".join(out)


def check_width_doc(root: Path) -> str:
    doc = root / WIDTH_DOC
    if not doc.is_file():
        raise CheckError(f"{WIDTH_DOC}: 文件不存在")
    text = doc.read_text(encoding="utf-8")

    rules: dict[str, str] = {}
    undefined: dict[str, str] = {}
    for line in text.split("\n"):
        m = RULE_ROW_RE.match(line)
        if m:
            rules[m.group(1)] = m.group(3).strip()
            continue
        m = UNDEF_ROW_RE.match(line)
        if m:
            undefined[m.group(1)] = (m.group(2) + " " + m.group(3)).strip()

    if set(rules) != set(RULES):
        raise CheckError(f"{WIDTH_DOC}: 规则 ID 集合与校验表不符: 缺 {sorted(set(RULES) - set(rules))}、"
                         f"多 {sorted(set(rules) - set(RULES))}")
    if set(undefined) != set(UNDEFINED):
        raise CheckError(f"{WIDTH_DOC}: 未定义项 ID 集合不符: 缺 {sorted(set(UNDEFINED) - set(undefined))}、"
                         f"多 {sorted(set(undefined) - set(UNDEFINED))}")

    bad: list[str] = []
    for rid, (rel, number, anchor) in sorted(RULES.items()):
        cite = rules[rid]
        m = re.search(r"`([^`]+\.md)`\s*§([0-9.]+)", cite)
        if not m:
            bad.append(f"{rid}: 出处须形如 `` `path.md` §N ``，实得 {cite!r}")
            continue
        if m.group(1) != rel or m.group(2) != number:
            bad.append(f"{rid}: 出处写 {m.group(1)} §{m.group(2)}，应为 {rel} §{number}")
            continue
        path = root / rel
        if not path.is_file():
            bad.append(f"{rid}: 出处文件不存在: {rel}")
            continue
        body = section_body(path.read_text(encoding="utf-8"), number)
        if body is None:
            bad.append(f"{rid}: {rel} 里找不到 §{number} 节")
        elif not re.search(anchor, body):
            bad.append(f"{rid}: {rel} §{number} 正文里找不到锚点 /{anchor}/（出处指向了不定义该规则的地方）")
    if bad:
        raise CheckError(f"{WIDTH_DOC}: 规则出处不一致:\n  " + "\n  ".join(bad))

    spec_files = sorted((root / "spec").glob("*.md")) + sorted((root / ".tao/contracts").glob("*.md"))
    idl_text = "\n".join(s.code for s in load_sources(root))
    for uid, spec in sorted(UNDEFINED.items()):
        if spec.anchor not in undefined[uid]:
            bad.append(f"{uid}: 文档行未写明 {spec.anchor!r}")
            continue
        probe = root / spec.probe
        if not probe.is_file():
            bad.append(f"{uid}: 探测文件不存在: {spec.probe}")
            continue
        body = probe.read_text(encoding="utf-8")
        if spec.section is not None:
            scoped = section_body(body, spec.section)
            if scoped is None:
                bad.append(f"{uid}: {spec.probe} 里找不到 §{spec.section}")
                continue
            body = scoped
        body = strip_fences(body)
        if re.search(spec.absent, body):
            bad.append(f"{uid}: {spec.probe}"
                       f"{' §' + spec.section if spec.section else ''} 的散文里出现了 /{spec.absent}/ "
                       f"⇒ 该构造已有出处，不应列「未定义」")
        if spec.usage is not None and not re.search(spec.usage, idl_text):
            bad.append(f"{uid}: `.idl` 里并没有 /{spec.usage}/ 的用法 ⇒ 该「未定义」项与本仓无关")
        if spec.repo_wide:
            hits = 0
            for path in spec_files:
                hits += len(re.findall(spec.absent, strip_fences(path.read_text(encoding="utf-8"))))
            if hits:
                bad.append(f"{uid}: spec/ 或 .tao/contracts/ 散文里出现 {hits} 次 /{spec.absent}/ "
                           f"⇒ 已定义，不从「未定义」")
    if bad:
        raise CheckError(f"{WIDTH_DOC}: 未定义清单不自洽:\n  " + "\n  ".join(bad))
    return f"规则 {len(RULES)} 条出处逐条命中、未定义 {len(UNDEFINED)} 条探测通过"


# ── 入口 ────────────────────────────────────────────────────────────────────

def fmt_loc(first: tuple[str, int] | None) -> str:
    return f"`{first[0]}:{first[1]}`" if first else "—"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="IDL 语法子集/宽度规则的现场统计与文档校验")
    ap.add_argument("--check", action="store_true", help="校验 syntax-subset.md / width-rules.md")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--root", type=Path, default=REPO, help="另一棵同布局的树（默认仓库根）")
    args = ap.parse_args(argv)

    try:
        rows, extra = categories(args.root)
        if args.json:
            print(json.dumps({
                "categories": [{"id": cid, "label": label, "count": count,
                                "first": fmt_loc(first)} for cid, label, count, first in rows],
                "books": extra["books"],
                "total_calls": extra["total_calls"],
                "distinct_calls": extra["distinct_calls"],
            }, ensure_ascii=False, indent=2))
            return 0
        if args.check:
            print("subset: " + check_subset_doc(args.root, rows, extra))
            print("width:  " + check_width_doc(args.root))
            print("subset-stats: PASS")
            return 0
        for cid, label, count, first in rows:
            print(f"{cid}  {count:5d}  {label:<52s} {fmt_loc(first)}")
        total = next(count for cid, _l, count, _f in rows if cid == "S01")
        print(f"-- operation 总数: {total}；每册: {extra['books']}")
        print(f"-- 函数调用: {extra['total_calls']} 次 / {extra['distinct_calls']} 个不同名字")
        return 0
    except CheckError as exc:
        print(f"subset-stats: FAIL — {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
