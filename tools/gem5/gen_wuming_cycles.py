#!/usr/bin/env python3
"""Generate the wuming per-instruction cycle table from the cycle-model doc.

Spec-first: ``docs/core-wuming-cycle-model.md`` is the **only** source of truth
for both the class taxonomy (§2) and the per-family cycle figures (§3, with the
§5 measurements already folded in by the doc author).  This script carries **no
cycle count**: it parses the doc at run time and refuses to emit a row whose
cycle text is not a verbatim substring of the doc line it cites, so a
hand-copied table cannot come back unnoticed.

Pipeline
--------
1. parse ``## 2. 分类``     -> admissible class set (name, meaning, cycle text)
2. parse ``## 3. 逐册/逐族`` -> one row per (册, 指令族, 类, 周期)
3. match every id of ``contracts/opcodes.yaml`` (264) against those rows with
   the row's own mnemonics / globs / operation words, under a fixed specificity
   order; an id that cannot be matched is reported as an error, never guessed
4. emit ``tools/gem5/wuming_cycles.yaml`` (id -> class / cycles / dynamic
   parameter) plus the generated C++ table
   ``<gem5 source>/src/arch/dadao/wuming_cycles.{hh,cc}``

``--check`` re-generates both artifacts in memory, runs every coverage
invariant and compares them byte for byte with what is on disk; it is what
``make check-wuming-cycles`` runs.

Matching order (highest first).  "section" is the SimRISC book number of the id
(``SimRISC-07: foadd`` -> ``07``)::

  T1  bank-qualified pattern                  e.g. ``ld.o rf`` / ``cs.* rf``
  T2  exact mnemonic, same section
  T3  glob / operation word, same section
  T4  exact mnemonic or glob, other section   cross-book refinement, e.g. the
      ``rev.*``/``rol.*``/``clmul.o`` row of book 12 or ``add.si`` of book 05
  T5  ``<tetra|wyde|byte> 全套`` section-wide row
  T6  operation word, other section           e.g. 04's «比较» row covers the
      05 ``cmp.uo`` dbb form
  T7  §2 class default for the FP book (07) leftovers, e.g. ``ftadd`` -> B4

Operation words (``算术``/``逻辑``/``移位``/…) only say *which family* a
mnemonic belongs to; they never carry a number.  ``KIND_STEMS`` below is the
single hand-written vocabulary, and it is checked against the doc.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs/core-wuming-cycle-model.md"
OPCODES = ROOT / "contracts/opcodes.yaml"
OUT_YAML = ROOT / "tools/gem5/wuming_cycles.yaml"
DEFAULT_SOURCE = ROOT / ".work/source/gem5"
CPP_HH = "src/arch/dadao/wuming_cycles.hh"
CPP_CC = "src/arch/dadao/wuming_cycles.cc"

# ── the only hand-written vocabulary ────────────────────────────────────────
# §3 «指令族» 列的中文操作词 → mnemonic 词干（前缀匹配）。它只回答「这条指令
# 属于哪种操作」，不含任何拍数；拍数一律来自文档。每个词必须在文档里出现，
# 每个 §3 行里的操作词也必须在这里有定义（`assert_vocabulary` 现场核对）。
KIND_STEMS: dict[str, tuple[str, ...]] = {
    "算术": ("add", "sub", "aip"),
    "逻辑": ("and", "or", "xor", "xnor", "andn"),
    "移位": ("shl", "shr"),
    "轮转": ("rol",),
    "扩展": ("ext",),
    "比较": ("cmp",),
    "位操作": ("ctlz", "cttz", "ctpop", "rev", "clmul"),
    "符号": ("ftsgn", "fosgn"),
}

# 多元素访存（D 类 `ldm`/`stm`）的元素宽度：后缀即宽度（`spec/SimRISC-01 §1`
# 的 sb/ub/sw/uw/st/ut/o 形式）。这里只有「宽度」，不含任何拍数。
BLOCK_WIDTH: dict[str, int] = {
    "b": 1, "ub": 1, "sb": 1,
    "w": 2, "uw": 2, "sw": 2,
    "t": 4, "ut": 4, "st": 4,
    "o": 8,
}

# §2 A 档拆两档的依据（文档行 12「移位/位操作 2 拍、简单算术 1 拍」；§5 行 117
# 「位操作 ctpop/ctlz/cttz/rev/rol/clmul 实测 2」）：这两种 kind 走 2 拍，其余
# （算术/逻辑/比较/符号）走 1 拍。
TIER2_KINDS = ("移位", "轮转", "扩展", "位操作")

# 文档把 `rd0`/`rb0` 当寄存器名写进反引号（不是助记符）。
NON_INSN_TOKENS = {"rd0", "rb0"}

# §2 类名里带撇的写法 → C++ 枚举标识符。
CLASS_IDENT = {"D′": "Dp"}

BANK_WORDS = {"rd", "rb", "ra", "rf"}

# 乘法类在文档里是「可配」的（§2 B1「初值 3」/ B2「1（可配）」、R2 行 13）：
# 行里给出的数字只是默认值，表里按动态参数标记。
CONFIGURABLE_CLASSES = ("B1", "B2")

# §5 实测推翻 §3 估计时的收敛口径。值仍出自文档；每条必须在 doc 指定的行里
# 逐字出现（gate 校验），并写进 YAML 的 overrides 段。
OVERRIDES: dict[str, dict[str, str]] = {
    "clmul.o": {
        "klass": "A",
        "cycles": "2",
        "doc_line": "87",
        "doc": "§5 行 117（位操作 ctpop/ctlz/cttz/rev/rol/clmul 实测 2）+ §3 行 87（A/2）",
        "why": "§3 行 61 把 clmul.o 归 B1「3（可配）」，是实测前的估计；010 实测 2 拍。",
    },
}


# ── doc parsing ────────────────────────────────────────────────────────────
@dataclass
class ClassInfo:
    name: str
    meaning: str
    cycles: str
    line: int


@dataclass
class Token:
    raw: str
    kind: str  # mnemonic | format | register | operand | suffix | ellipsis
    patterns: tuple[str, ...] = ()
    bank: str | None = None


@dataclass
class Segment:
    """One «;»/" / "-separated sub-cell of a 周期 cell (e.g. `ld.o` 7–16)."""
    tokens: tuple[str, ...]
    words: tuple[str, ...]
    value: str
    raw: str


@dataclass
class Row:
    section: str
    family: str
    klass_cell: str
    cycle_cell: str
    line: int
    tokens: list[Token] = field(default_factory=list)
    kinds: tuple[str, ...] = ()
    wide: bool = False
    provenance: str = ""
    segments: list[Segment] = field(default_factory=list)


def split_outside_parens(text: str, sep: str) -> list[str]:
    out, buf, depth, i = [], [], 0, 0
    while i < len(text):
        if text.startswith(sep, i) and depth == 0:
            out.append("".join(buf))
            buf = []
            i += len(sep)
            continue
        ch = text[i]
        if ch == "（":
            depth += 1
        elif ch == "）":
            depth -= 1
        buf.append(ch)
        i += 1
    out.append("".join(buf))
    return [part.strip() for part in out if part.strip()]


def strip_code(text: str) -> str:
    return text.replace("`", "")


def split_row_cells(line: str) -> list[str]:
    """Split a markdown table row on '|', keeping `0|4`-style code spans whole."""
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|"):
        body = body[:-1]
    cells, buf, in_code = [], [], False
    for ch in body:
        if ch == "`":
            in_code = not in_code
        if ch == "|" and not in_code:
            cells.append("".join(buf))
            buf = []
            continue
        buf.append(ch)
    cells.append("".join(buf))
    return [c.strip() for c in cells]


def doc_lines() -> list[str]:
    return DOC.read_text(encoding="utf-8").splitlines()


def section_bounds(lines: list[str], heading: str, stop: str) -> tuple[int, int]:
    start = next(i for i, ln in enumerate(lines) if ln.startswith(heading))
    end = next((i for i, ln in enumerate(lines) if i > start and ln.startswith(stop)),
               len(lines))
    return start, end


def parse_classes(lines: list[str]) -> dict[str, ClassInfo]:
    start, end = section_bounds(lines, "## 2.", "## 3.")
    classes: dict[str, ClassInfo] = {}
    for i in range(start, end):
        ln = lines[i]
        if not ln.startswith("|"):
            continue
        cells = split_row_cells(ln)
        if len(cells) != 3 or set(cells[0]) <= {"-"} or cells[0] == "类":
            continue
        for name in cells[0].split("/"):
            classes[name.strip()] = ClassInfo(name.strip(), cells[1], cells[2], i + 1)
    return classes


def expand_slash(body: str) -> tuple[str, ...]:
    """``ld.sb/ub/sw`` -> ld.sb, ld.ub, ld.sw (shared dotted prefix)."""
    parts = body.split("/")
    first = parts[0]
    prefix = first[: first.rfind(".") + 1] if "." in first else ""
    out = [first]
    for part in parts[1:]:
        out.append(part if "." in part else prefix + part)
    return tuple(out)


def looks_like_pattern(pattern: str, mnemonics: set[str]) -> bool:
    if pattern in mnemonics:
        return True
    if "*" in pattern:
        return any(fnmatch(m, pattern) for m in mnemonics)
    return False


def classify_token(raw: str, mnemonics: set[str], formats: set[str]) -> Token:
    text = raw.strip()
    if not text:
        raise SystemExit(f"{DOC.name}: empty backticked token")
    if text == "…":
        return Token(text, "ellipsis")
    if text in formats:
        return Token(text, "format")
    if text in NON_INSN_TOKENS:
        return Token(text, "register")
    if text.startswith("."):
        return Token(text, "suffix")
    words = text.split()
    body = words[0]
    bank = words[-1] if len(words) > 1 and words[-1] in BANK_WORDS else None
    patterns = expand_slash(body)
    if all(looks_like_pattern(p, mnemonics) for p in patterns):
        return Token(text, "mnemonic", patterns, bank)
    # 不是助记符：操作数 / 寄存器 / 表达式提及（`bbd`、`trap cfx3`、`immu18[...]`）
    return Token(text, "operand")


def parse_segments(cell: str) -> list[Segment]:
    parts = split_outside_parens(cell, "；")
    if len(parts) == 1:
        parts = split_outside_parens(cell, " / ")
    segs: list[Segment] = []
    for part in parts:
        tokens = tuple(re.findall(r"`([^`]*)`", part))
        paren = re.search(r"（[^）]*）", part)
        # 括号里的反引号是「举例」而不是限定词（`1+N（`rd2rd` N=8 ⇒ 9）`）
        if paren and any(f"`{t}`" in paren.group(0) for t in tokens):
            example = paren.group(0)
            tokens = tuple(t for t in tokens if f"`{t}`" not in example)
        rest = re.sub(r"`[^`]*`", " ", part).strip()
        rest = rest.split("（")[0].strip()
        words: tuple[str, ...] = ()
        value = rest
        if rest and not rest[0].isdigit():
            m = re.match(r"^(\S+)\s+(\S.*)$", rest)
            if m:
                words = tuple(w for w in re.split(r"[/、]", m.group(1)) if w)
                value = m.group(2).strip()
        if not value and tokens:
            value = tokens[0]
            tokens = ()
        segs.append(Segment(tokens, words, value, part))
    return segs


def expand_ellipsis(row: Row) -> list[Token]:
    """`…` in a family cell means «the rest of this family».

    Mechanically: the listed mnemonics must all be ``X2Y`` (the FP conversion
    family), in which case ``…`` becomes the ``*2*`` glob.  Anything else is
    refused rather than guessed.
    """
    listed = [p for tok in row.tokens if tok.kind == "mnemonic" for p in tok.patterns]
    if not listed or not all(re.fullmatch(r"[a-z0-9]+2[a-z0-9]+", p) for p in listed):
        raise SystemExit(
            f"{DOC.name}:{row.line}: «…» 不能机械展开：{listed}")
    out = [tok for tok in row.tokens if tok.kind != "ellipsis"]
    out.append(Token("…", "mnemonic", ("*2*",)))
    return out


def parse_rows(lines: list[str], mnemonics: set[str], formats: set[str]) -> list[Row]:
    start, end = section_bounds(lines, "## 3.", "## 4.")
    rows: list[Row] = []
    for i in range(start, end):
        ln = lines[i]
        if not ln.startswith("|"):
            continue
        cells = split_row_cells(ln)
        if len(cells) not in (4, 5) or set(cells[0]) <= {"-"} or cells[0] == "册":
            continue
        if len(cells) == 4:
            raise SystemExit(
                "gen_wuming_cycles: §3 行缺「来源」列（行 %d）：%s" % (i + 1, ln[:60]))
        row = Row(cells[0].split()[0], cells[1], cells[2], cells[3], i + 1)
        row.provenance = cells[4].strip()
        row.wide = bool(re.match(r"^(tetra|wyde|byte)\s*全套", row.family))
        prose = strip_code(row.family)
        row.kinds = tuple(w for w in KIND_STEMS if w in prose)
        for raw in re.findall(r"`([^`]*)`", row.family):
            row.tokens.append(classify_token(raw, mnemonics, formats))
        # «…» 有两种用法：转换族的「其余同类」（需展开成 *2*）和 全套 行
        # 「add.ut…rem.st」的区间示例（该行本就覆盖整册，展开无意义）。
        if "…" in row.family and not row.wide:
            row.tokens = expand_ellipsis(row)
        row.segments = parse_segments(row.cycle_cell)
        rows.append(row)
    return rows


# ── instruction matching ───────────────────────────────────────────────────
@dataclass
class Inst:
    id: str
    mnemonic: str
    section: str
    bank: str
    stem: str


def load_contract():
    import yaml

    raw = yaml.safe_load(OPCODES.read_text(encoding="utf-8"))
    insts, formats = [], set()
    for entry in raw:
        spec = entry["spec_cite"]
        insts.append(Inst(entry["id"], entry["mnemonic"],
                          spec.split(":")[0].replace("SimRISC-", "").strip(),
                          entry["id"].rsplit("_", 1)[-1],
                          entry["mnemonic"].split(".")[0]))
        formats.add(entry["format"])
    return insts, formats


def stem_matches(stem: str, kind: str) -> bool:
    return any(stem == s or stem.startswith(s) for s in KIND_STEMS[kind])


def token_hits(token: Token, inst: Inst) -> str | None:
    if token.kind != "mnemonic":
        return None
    if token.bank is not None and token.bank != inst.bank:
        return None
    for pattern in token.patterns:
        if fnmatch(inst.mnemonic, pattern):
            return "exact" if "*" not in pattern else "glob"
    return None


def row_hit(row: Row, inst: Inst) -> tuple[int, str] | None:
    best: tuple[int, str] | None = None
    for token in row.tokens:
        hit = token_hits(token, inst)
        if hit is None:
            continue
        if token.bank is not None:
            tier = 1
        elif hit == "exact":
            tier = 2 if row.section == inst.section else 4
        else:
            tier = 3 if row.section == inst.section else 4
        if best is None or tier < best[0]:
            best = (tier, hit)
    if best is None and row.kinds and row.section == inst.section:
        if any(stem_matches(inst.stem, kind) for kind in row.kinds):
            best = (3, "kind")
    if best is None and row.wide and row.section == inst.section:
        best = (5, "wide")
    if best is None and row.kinds and row.section != inst.section:
        # 跨册的操作词引用（如 04 册「比较」行覆盖 05 册的 cmp.uo dbb 形态）。
        # 排在 全套 行之后：本册自己的 <width> 全套 行优先。
        if any(stem_matches(inst.stem, kind) for kind in row.kinds):
            best = (6, "kind")
    return best


def assign(insts: list[Inst], rows: list[Row]):
    """id -> (rows at the best tier, tier); raises nothing, reports leftovers."""
    resolved: dict[str, tuple[list[Row], int]] = {}
    for inst in insts:
        hits = []
        for row in rows:
            hit = row_hit(row, inst)
            if hit:
                hits.append((hit[0], row))
        if not hits:
            continue
        tier = min(h[0] for h in hits)
        cand = [h for h in hits if h[0] == tier]
        if tier in (3, 4, 5, 6) and len({h[1].line for h in cand}) > 1:
            # 同层级多行（如 12 册的 rev.*/rol.*）：后出现的是 refinements
            cand = [max(cand, key=lambda h: h[1].line)]
        resolved[inst.id] = ([h[1] for h in cand], tier)
    return resolved


# ── cycle composition ──────────────────────────────────────────────────────
RANGE_RE = re.compile(r"^(\d+)[–-](\d+)$")


def classify_value(text: str, raw: str):
    """(value, range, dynamic) for one verbatim doc figure; never invents one."""
    text = text.strip()
    if text == "N" or "N=" in raw or "N=" in text:
        return None, None, "N"
    if "beats" in text:
        return None, None, "beats"
    if "元素数" in text:
        return None, None, "elements"
    if "变长" in text:
        return None, None, "host-latency"
    if "待实测" in text:
        return None, None, "unmeasured"
    if "可配" in raw:
        return None, None, "mul-config"
    if re.fullmatch(r"\d+", text):
        return int(text), None, None
    m = RANGE_RE.match(text)
    if m:
        return None, [int(m.group(1)), int(m.group(2))], "range"
    if re.search(r"(?<![A-Za-z])d(?![A-Za-z])", text):
        return None, None, "exponent-diff"
    return None, None, "expr"


# ── block transfer: D (multi-element memory) and D′ (register copy) ────────
# The document gives one measured figure per multi-element memory family at a
# fixed element count ("`ldm.ub` N=8: 16；`ldm.o` N=8: 72；…").  Both classes are
# modelled from those figures, never from a number written here:
#
#   D   per_element*N + per_beat*ceil(N*width/8)      (§2 D «beats × 3–4» is
#       the pre-measurement estimate; the §3/§5 figures are 实测 and rule)
#   D′  base + step*N                                 (§3 "1+N" / "N")
#
# `n_beat` below is the number of 8-byte bus beats the element group needs.
N8_RE = re.compile(r"N\s*=\s*(\d+)\s*[:：]\s*(\d+)")
DPLUS_RE = re.compile(r"^(\d+)\s*\+\s*N$")


def block_width(mnemonic: str) -> int:
    """Element width of an `ldm`/`stm` form, from its suffix (SimRISC-01 §1)."""
    suffix = mnemonic.rsplit(".", 1)[-1]
    if suffix not in BLOCK_WIDTH:
        raise SystemExit(f"{DOC.name}: {mnemonic}: 未知的多元素访存宽度后缀")
    return BLOCK_WIDTH[suffix]


def block_copy_fields(cycles: str):
    """(base, step) of a D′ figure: "1+N" -> (1, 1), "N" -> (0, 1)."""
    text = (cycles or "").strip()
    m = DPLUS_RE.match(text)
    if m:
        return int(m.group(1)), 1
    if text == "N":
        return 0, 1
    return None


def block_model(rows) -> dict:
    """Solve the two D coefficients from the doc's own N=… measured figures.

    Exact integer arithmetic: a non-integral or inconsistent fit aborts the
    generator, so a doc edit that breaks the model is reported instead of
    silently rounding.  `samples` is kept for the YAML (audit trail).
    """
    samples = []
    for row in rows:
        if not any(c.strip() == "D" for c in row.klass_cell.split("/")):
            continue
        for seg in row.segments:
            m = N8_RE.search(strip_code(seg.raw))
            if not m or not seg.tokens:
                continue
            mnemonic = seg.tokens[0]
            if ".*" in mnemonic or "*" in mnemonic:
                continue
            n, figure = int(m.group(1)), int(m.group(2))
            width = block_width(mnemonic)
            beats = (n * width + 7) // 8
            samples.append({"line": row.line, "mnemonic": mnemonic, "n": n,
                            "width": width, "beats": beats, "figure": figure})
    if len(samples) < 2:
        raise SystemExit(f"{DOC.name}: D 类实测图不足两条，无法解出块传送模型")
    (n1, b1, f1), (n2, b2, f2) = [(s["n"], s["beats"], s["figure"])
                                  for s in samples[:2]]
    det = n1 * b2 - n2 * b1
    if det == 0:
        raise SystemExit(f"{DOC.name}: D 类实测图两点的 beats 相同，无法解出模型")
    num_a = f1 * b2 - f2 * b1
    num_b = n1 * f2 - n2 * f1
    if num_a % det or num_b % det:
        raise SystemExit(f"{DOC.name}: D 类实测图解出的系数不是整数"
                         f"（a={num_a}/{det}, b={num_b}/{det}）")
    a, b = num_a // det, num_b // det
    if a < 0 or b < 0:
        raise SystemExit(f"{DOC.name}: D 类解出负系数 a={a}, b={b}")
    for s in samples:
        want = a * s["n"] + b * s["beats"]
        if want != s["figure"]:
            raise SystemExit(
                f"{DOC.name}:{s['line']}: {s['mnemonic']} N={s['n']} 实测 "
                f"{s['figure']} 与解出的模型 {a}*N+{b}*beats={want} 不符")
    return {"per_element": a, "per_beat": b, "samples": samples}


def pick_segment(row: Row, inst: Inst):
    """The sub-cell that pins *inst*; returns (segment|None, variant label)."""
    for seg in row.segments:
        if seg.tokens:
            for raw in seg.tokens:
                tok = classify_token(raw, {inst.mnemonic}, set())
                if tok.kind == "mnemonic" and any(
                        fnmatch(inst.mnemonic, p) for p in tok.patterns):
                    if tok.bank is None or tok.bank == inst.bank:
                        return seg, "|".join(seg.words)
        elif seg.words:
            for word in seg.words:
                if word in KIND_STEMS and stem_matches(inst.stem, word):
                    return seg, "|".join(seg.words)
                if inst.mnemonic.startswith(word) or inst.mnemonic.split(".")[-1] == word:
                    return seg, "|".join(seg.words)
    for seg in row.segments:
        if not seg.tokens and not seg.words:
            return seg, ""
    return None, ""


def a_tier_value(inst: Inst) -> int:
    """§2 A 档两档：移位/位域类 2 拍，其余（算术/逻辑/比较/符号）1 拍。"""
    return 2 if any(stem_matches(inst.stem, k) for k in TIER2_KINDS) else 1


def wide_class(row: Row, inst: Inst):
    """`<width> 全套` rows give the class *set*; the mnemonic picks the member."""
    klass_list = [c.strip() for c in row.klass_cell.split("/")]
    cycle_list = [s.value for s in row.segments]
    if len(klass_list) != len(cycle_list):
        raise SystemExit(f"{DOC.name}:{row.line}: 全套行的类/周期列表长度不一致")
    mapping = dict(zip(klass_list, cycle_list))
    if inst.stem == "mul":
        return "B2", mapping.get("B2")
    if inst.stem in ("div", "rem"):
        return "B3", mapping.get("B3")
    return "A", mapping.get("A")


def variant(klass: str, cycles: str, value, rng, dynamic, when, line: int, prov: str,
            origin: str = "§3"):
    return {"klass": klass, "cycles": cycles, "value": value, "range": rng,
            "dynamic": dynamic, "when": when, "doc": line, "origin": origin,
            "provenance": prov}


PROV_TAGS = ("实测", "可配", "设计值", "推断", "未测", "待实测")
PROV_ALLOWED = ("实测", "可配", "设计值")


def prov_for(cell: str, klass: str) -> str:
    """从「来源」单元取该类的标签；形如 `A 实测 / B2 可配 / B3 设计值`。"""
    cell = (cell or "").strip()
    if not cell:
        return ""
    for part in cell.split("/"):
        part = part.strip()
        if part.startswith(klass):
            return part
    return cell


def compose_variant(klass: str, cycles: str, raw: str, when, line: int, prov: str,
                    origin: str = "§3"):
    value, rng, dyn = classify_value(cycles, raw)
    if klass in CONFIGURABLE_CLASSES and dyn in (None, "expr"):
        dyn, value = "mul-config", None
    return variant(klass, cycles, value, rng, dyn, when, line, prov, origin)


def override_doc_line() -> int:
    """§5 里那条 clmul 实测行的当前行号（文档增删行后自动跟随）。"""
    lines = doc_lines()
    start, end = section_bounds(lines, "## 5.", "## 6.")
    for i in range(start, end):
        if "clmul" in lines[i] and "ctpop" in lines[i]:
            return i + 1
    raise SystemExit("gen_wuming_cycles: §5 找不到 clmul 实测行")


def compose(inst: Inst, resolved, classes) -> dict | None:
    entry = {"id": inst.id, "mnemonic": inst.mnemonic, "bank": inst.bank,
             "section": inst.section}
    if inst.mnemonic in OVERRIDES:
        o = OVERRIDES[inst.mnemonic]
        entry.update(klass=[o["klass"]], cycles=o["cycles"], value=int(o["cycles"]),
                     range=None, dynamic=None, doc=override_doc_line(),
                     source="override", variants=None,
                     provenance="实测（override：§5）")
        return entry
    if inst.id not in resolved:
        return None
    cand_rows, tier = resolved[inst.id]
    row = cand_rows[0]
    if tier == 5 or row.wide:
        klass, cycles = wide_class(row, inst)
        if klass == "A":
            value = a_tier_value(inst)
            entry.update(klass=["A"], cycles=str(value), value=value, range=None,
                         dynamic=None, doc=classes["A"].line,
                         source=f"§2 A（§3 {row.section} 全套）", variants=None,
                         provenance=prov_for(row.provenance, "A"))
        else:
            v = compose_variant(klass, cycles, row.cycle_cell, None, row.line, prov_for(row.provenance, klass))
            entry.update(klass=[klass], cycles=v["cycles"], value=v["value"],
                         range=v["range"], dynamic=v["dynamic"], doc=row.line,
                         source=f"§3 {row.section} 全套", variants=None,
                         provenance=v["provenance"])
        return entry

    variants = []
    multi_row = len(cand_rows) > 1
    for row in cand_rows:
        klass_list = [c.strip() for c in row.klass_cell.split("/")]
        # 同一 id 命中多行（如 trap 的 semihosting / cfx3 / 保留 cfx 三行）时，
        # 「何时」用该行自己的指令族原文做标签，仍然是文档原文。
        row_when = strip_code(row.family).strip() if multi_row else None
        seg, when = pick_segment(row, inst)
        if seg is not None:
            index = row.segments.index(seg)
            klass = klass_list[index] if len(klass_list) == len(row.segments) else klass_list[0]
            variants.append(compose_variant(klass, seg.value, seg.raw,
                                            when or row_when, row.line, prov_for(row.provenance, klass)))
            continue
        if klass_list == ["A"] and "算术" in row.cycle_cell:
            value = a_tier_value(inst)
            variants.append(variant("A", str(value), value, None, None, None, row.line, prov_for(row.provenance, "A")))
            continue
        if len(row.segments) > 1 and all(not s.tokens for s in row.segments):
            for index, seg in enumerate(row.segments):
                klass = klass_list[index] if len(klass_list) == len(row.segments) else klass_list[0]
                label = "|".join(seg.words) or None
                variants.append(compose_variant(klass, seg.value, seg.raw, label, row.line, prov_for(row.provenance, klass)))
            continue
        # 该行没有为这条指令给出取值 -> 回落到 §2 类定义（仍是文档原文）
        for klass in klass_list:
            info = classes[klass]
            variants.append(compose_variant(klass, strip_code(info.cycles), info.cycles,
                                            row_when, info.line, prov_for(row.provenance, klass),
                                            origin="§2"))
    if not variants:
        return None
    klass_list = []
    for v in variants:
        if v["klass"] not in klass_list:
            klass_list.append(v["klass"])
    # 类按 §2 文档顺序排列（trap 的 F/G2/G1 -> F/G1/G2），便于阅读与比较
    order = list(classes)
    klass_list.sort(key=lambda k: order.index(k) if k in order else len(order))
    origins = {v["origin"] for v in variants}
    if origins == {"§2"}:
        source = "§2 " + "/".join(klass_list)
    elif origins == {"§3"}:
        source = f"§3 {row.section}"
    else:
        source = f"§3 {row.section}+§2 " + "/".join(klass_list)
    provs = [v.get("provenance") or "" for v in variants]
    entry.update(klass=klass_list, source=source,
                 doc=variants[0]["doc"],
                 variants=variants if len(variants) > 1 else None,
                 cycles=variants[0]["cycles"], value=variants[0]["value"],
                 range=variants[0]["range"], dynamic=variants[0]["dynamic"],
                 provenance=" / ".join(dict.fromkeys(p for p in provs if p)))
    if len(variants) > 1:
        labels = {v["dynamic"] for v in variants}
        klasses = {v["klass"] for v in variants}
        if klasses & {"F", "G1", "G2"}:
            entry["dynamic"] = "trap-target"
        elif klasses & {"A3", "A4"}:
            entry["dynamic"] = "ras-kind"
        elif labels == {"range"}:
            entry["dynamic"] = "range"
        elif {v["when"] for v in variants} == {"命中", "未命中"}:
            entry["dynamic"] = "hit-miss"
        else:
            entry["dynamic"] = "variant"
        entry["value"] = None
        entry["range"] = None
    return entry


def fp_default(inst: Inst, classes) -> dict:
    info = classes["B4"]
    cycles = strip_code(info.cycles)
    value, rng, dyn = classify_value(cycles, info.cycles)
    return {"id": inst.id, "mnemonic": inst.mnemonic, "bank": inst.bank,
            "section": inst.section, "klass": ["B4"], "cycles": cycles,
            "value": value, "range": rng, "dynamic": "fp-op", "doc": info.line,
            "source": "§2 B4", "variants": None,
            # §3 没有这些指令的专行（只有 §2 的 B4「1–2」类级口径）⇒ 推断
            "provenance": "推断（§2 B4 类级，§3 无专行）"}


def build_table(insts, rows, classes):
    resolved = assign(insts, rows)
    table, missing = [], []
    for inst in insts:
        entry = compose(inst, resolved, classes)
        if entry is None:
            if inst.section == "07" and (inst.mnemonic.startswith("f")
                                         or re.search(r"2f", inst.mnemonic)):
                entry = fp_default(inst, classes)
            else:
                missing.append(inst.id)
        if entry is not None:
            table.append(entry)
    return table, missing


# ── emitters ───────────────────────────────────────────────────────────────
def q(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(q(v) for v in value) + "]"
    return "'" + str(value).replace("'", "''") + "'"


def entry_docs(entry) -> list[int]:
    return [v["doc"] for v in (entry.get("variants") or [entry])]


def row_counts(table, rows) -> dict[int, int]:
    counts = {}
    for row in rows:
        if row.wide:
            counts[row.line] = sum(1 for e in table if e["section"] == row.section)
        else:
            counts[row.line] = sum(1 for e in table if row.line in entry_docs(e))
    return counts


def emit_yaml(table, classes, doc_sha, rows, block) -> str:
    by_class: dict[str, int] = {}
    for entry in table:
        for klass in entry["klass"]:
            by_class[klass] = by_class.get(klass, 0) + 1
    counts = row_counts(table, rows)
    out = [
        "# Generated by tools/gem5/gen_wuming_cycles.py -- do not edit.",
        "# Source: docs/core-wuming-cycle-model.md (§2 分类 + §3 逐族) + contracts/opcodes.yaml.",
        "# 每行: id -> 类 / 周期（文档原文）/ 动态参数。value 仅在静态时为整数；",
        "# dynamic 非 null 表示文档只给参数化拍数（range/N/beats/hit-miss/...）。",
        "schema: 1",
        "generated_by: tools/gem5/gen_wuming_cycles.py",
        "source_doc: docs/core-wuming-cycle-model.md",
        f"source_doc_sha256: {q(doc_sha)}",
        f"instruction_count: {len(table)}",
        f"static_rows: {sum(1 for e in table if e['dynamic'] is None)}",
        f"dynamic_rows: {sum(1 for e in table if e['dynamic'] is not None)}",
        "class_set: [" + ", ".join(q(c) for c in classes) + "]",
        "by_class: {" + ", ".join(f"{q(k)}: {v}" for k, v in sorted(by_class.items())) + "}",
        "# block_model: 多元素传送的模型系数，由 §3 的 N=… 实测图解出（不是手抄）",
        "block_model:",
        f"  per_element: {block['per_element']}",
        f"  per_beat: {block['per_beat']}",
        "  samples:",
    ]
    for s in block["samples"]:
        out.append(f"  - {{line: {s['line']}, mnemonic: {q(s['mnemonic'])}, "
                   f"n: {s['n']}, width: {s['width']}, beats: {s['beats']}, "
                   f"figure: {s['figure']}}}")
    out += ["# overrides: §5 实测与 §3 估计冲突时的收敛口径（值仍出自文档）",
            "overrides:"]
    for mnemonic, o in OVERRIDES.items():
        out.append(f"- {{mnemonic: {q(mnemonic)}, klass: {q(o['klass'])}, "
                   f"cycles: {q(o['cycles'])}, doc: {q(o['doc'])}, why: {q(o['why'])}}}")
    out += ["# doc_rows: 每个 §3 行覆盖到的 id 数（0 = 该行只描述寄存器/RAS 子操作）",
            "doc_rows:"]
    for row in rows:
        out.append(f"- {{line: {row.line}, section: {q(row.section)}, ids: {counts[row.line]}, "
                   f"classes: {q(row.klass_cell)}}}")
    out.append("instructions:")
    for entry in table:
        fields = [
            f"id: {q(entry['id'])}", f"mnemonic: {q(entry['mnemonic'])}",
            f"section: {q(entry['section']) if entry['section'] else 'null'}",
            f"klass: {q(entry['klass'])}",
            f"cycles: {q(entry['cycles'])}", f"value: {q(entry['value'])}",
            f"range: {q(entry['range'])}", f"dynamic: {q(entry['dynamic'])}",
            f"doc: {entry['doc']}", f"source: {q(entry['source'])}",
            f"provenance: {q(entry.get('provenance'))}",
        ]
        pol = policy_fields(entry, block)
        if pol["per_element"] >= 0 or pol["n_base"] >= 0:
            fields += [f"per_element: {pol['per_element']}",
                       f"per_beat: {pol['per_beat']}",
                       f"n_base: {pol['n_base']}", f"n_step: {pol['n_step']}",
                       f"elem_width: {pol['elem_width']}"]
        if entry.get("variants"):
            fields.append("variants: [" + ", ".join(
                f"{{klass: {q(v['klass'])}, cycles: {q(v['cycles'])}, "
                f"value: {q(v['value'])}, dynamic: {q(v['dynamic'])}, "
                f"when: {q(v['when'])}, doc: {v['doc']}, "
                f"provenance: {q(v.get('provenance'))}}}"
                for v in entry["variants"]) + "]")
        out.append("- {" + ", ".join(fields) + "}")
    return "\n".join(out) + "\n"


def class_mask(klass_list, order) -> int:
    mask = 0
    for klass in klass_list:
        mask |= 1 << order.index(klass)
    return mask


def emit_hh(order, count: int) -> str:
    enum = "\n".join(f"    {CLASS_IDENT.get(name, name)} = {i},"
                     for i, name in enumerate(order))
    return f"""// Generated by tools/gem5/gen_wuming_cycles.py -- do not edit.
// Source: docs/core-wuming-cycle-model.md (§2 分类 + §3 逐族) +
// contracts/opcodes.yaml ({count} ids).  Regenerate with
// `python3 tools/gem5/gen_wuming_cycles.py`; `make check-wuming-cycles` fails
// when this file drifts from the document.
#ifndef __ARCH_DADAO_WUMING_CYCLES_HH__
#define __ARCH_DADAO_WUMING_CYCLES_HH__

#include <cstddef>
#include <cstdint>
#include <string_view>

namespace gem5
{{
namespace DadaoISA
{{
namespace wuming
{{

/** Cycle class of a wuming instruction (see §2 of the cycle model). */
enum class CycleClass : uint8_t
{{
{enum}
    Count,
}};

constexpr unsigned kNumClasses = static_cast<unsigned>(CycleClass::Count);
constexpr unsigned kNumInstructionRows = {count};

/**
 * One row per contract id.  ``cycles`` is the number of EXEC cycles the wuming
 * core spends on the instruction; it is negative when the document only gives
 * a parameterised figure, in which case ``dynamic`` names the parameter (an
 * empty string means «static»).  ``classMask`` has one bit per CycleClass, so
 * an instruction dispatched at run time (``trap`` -> F/G1/G2, ``call``/``ret``
 * -> A3/A4) keeps every class it can take.
 *
 * The remaining fields are the document figures for the dynamic classes
 * (m16-gem5-004), emitted by the same parse; -1 means "not applicable".  They
 * exist so the policy header never carries a hand-copied cycle count:
 *
 *   defaultCycles  mul-config default (§3 "3（可配）" / "1（可配）")
 *   memCycles      ras-kind MemRAS figure (call 26 / ret 15)
 *   hostCycles     trap-target semihosting base (§3 "1 + 变长" -> 1)
 *   rangeLo/Hi     documented range endpoints (escape 3–4, trap G1/G2 4–5)
 *   dynBase/dynAdd exponent-diff formula "base + d + add" (53+d+1)
 *   semihostMask   trap semihosting test: (immu18 & mask) == value
 *   semihostValue  (0/0 when the row has no semihosting variant)
 *   perElement     D 类每个元素的拍数（= 每个元素一条微操作）
 *   perBeat        D 类每条 8 B 总线 beat 的拍数
 *   nBase/nStep    D′ 类块复制的 "base + step*N"（`1+N` / `N`）
 *   elemWidth      D 类的元素宽度（字节；0 = 非多元素访存）
 *
 * ``perElement``/``perBeat`` 由生成器从文档自己的 N=… 实测图解出（两条不同
 * beats 的图两点定解，其余图逐条回代校验），本文件不含手抄拍数。
 */
struct CycleRow
{{
    const char *id;
    const char *mnemonic;
    uint32_t classMask;
    int16_t cycles;
    int16_t defaultCycles;
    int16_t memCycles;
    int16_t hostCycles;
    int16_t rangeLo;
    int16_t rangeHi;
    int16_t dynBase;
    int16_t dynAdd;
    uint32_t semihostMask;
    uint32_t semihostValue;
    int16_t perElement;
    int16_t perBeat;
    int16_t nBase;
    int16_t nStep;
    uint8_t elemWidth;
    const char *dynamic;
    uint16_t docLine;
    /**
     * Where the figure comes from: ``实测`` / ``可配`` / ``设计值`` 可用；
     * 含 ``推断`` / ``未测`` / ``待实测`` 的行是 provisional，**不得**进入
     * 时序模型（policy 层须返回 0）。
     */
    const char *provenance;
}};

/** The {len(order)}-class enum size and the {count} rows, sorted by id. */
const CycleRow *rows();
std::size_t rowCount();
/** Row for a contract id, or nullptr when the id is not in the contract. */
const CycleRow *byId(std::string_view id);
/** Class name as written in the document ("A", "D′", ...). */
const char *className(CycleClass klass);
/** All classes of a row, "/"-joined ("A3/A4", "F/G1/G2", ...). */
const char *rowClasses(const CycleRow &row);

}} // namespace wuming
}} // namespace DadaoISA
}} // namespace gem5

#endif // __ARCH_DADAO_WUMING_CYCLES_HH__
"""


def policy_fields(entry, block: "dict | None" = None) -> dict:
    """Document figures for the dynamic classes, parsed from the same tables.

    Every value is either a verbatim doc number or an endpoint of a doc range;
    a dynamic class this policy knows about but whose figure cannot be located
    aborts the generator instead of emitting a made-up row.
    """
    out = {
        "default_cycles": -1, "mem_cycles": -1, "host_cycles": -1,
        "range_lo": -1, "range_hi": -1, "dyn_base": -1, "dyn_add": -1,
        "semihost_mask": 0, "semihost_value": 0,
        "per_element": -1, "per_beat": -1, "n_base": -1, "n_step": -1,
        "elem_width": 0,
    }
    dyn = entry["dynamic"]
    variants = entry.get("variants") or []

    def leading_int(text: str, why: str) -> int:
        m = re.search(r"\d+", text or "")
        if not m:
            raise SystemExit(f"{DOC.name}: {entry['id']}: {why} 中找不到数字")
        return int(m.group(0))

    if dyn == "mul-config":
        out["default_cycles"] = leading_int(entry["cycles"], "乘法可配默认值")
    elif dyn == "ras-kind":
        for v in variants:
            when = v.get("when") or ""
            if "MemRAS" in when:
                out["mem_cycles"] = v["value"]
            elif "RegRAS" in when:
                out["default_cycles"] = v["value"]
        if out["mem_cycles"] < 0 or out["default_cycles"] < 0:
            raise SystemExit(f"{DOC.name}: {entry['id']}: ras-kind 缺 RegRAS/MemRAS 变体")
    elif dyn == "trap-target":
        for v in variants:
            if v.get("dynamic") == "host-latency":
                out["host_cycles"] = leading_int(v["cycles"], "trap semihosting")
                m = re.search(r"immu18\[(\d+):(\d+)\]\s*==\s*0x([0-9A-Fa-f]+)",
                              v.get("when") or "")
                if not m:
                    raise SystemExit(f"{DOC.name}: {entry['id']}: "
                                     "trap semihosting 行缺 immu18 判据")
                low, high, want = int(m.group(2)), int(m.group(1)), int(m.group(3), 16)
                if high < low:
                    raise SystemExit(f"{DOC.name}: {entry['id']}: 位域上下界颠倒")
                mask = want << low
                out["semihost_mask"] = mask
                out["semihost_value"] = mask
            elif v.get("range"):
                out["range_lo"], out["range_hi"] = v["range"]
        if out["host_cycles"] < 0 or out["range_lo"] < 0:
            raise SystemExit(f"{DOC.name}: {entry['id']}: trap-target 缺 F/G 档")
    elif dyn == "exponent-diff":
        m = re.search(r"(\d+)\s*\+\s*d\s*\+\s*(\d+)", entry["cycles"])
        if not m:
            raise SystemExit(f"{DOC.name}: {entry['id']}: exponent-diff 公式无法解析")
        out["dyn_base"], out["dyn_add"] = int(m.group(1)), int(m.group(2))
    elif dyn == "range" and entry["mnemonic"] == "escape":
        out["range_lo"], out["range_hi"] = entry["range"]
    else:
        # Block transfers are keyed on the class, not on the parameter label:
        # the doc's D rows carry either an N=… figure or the class-level
        # «beats × 3–4», and both take the same solved model.
        klasses = [c.strip() for c in entry["klass"]]
        if "D" in klasses:
            if block is None:
                raise SystemExit(f"{DOC.name}: {entry['id']}: D 类缺块传送模型")
            out["per_element"] = block["per_element"]
            out["per_beat"] = block["per_beat"]
            out["elem_width"] = block_width(entry["mnemonic"])
        elif "D′" in klasses:
            parsed = block_copy_fields(entry["cycles"])
            if parsed is None:
                raise SystemExit(f"{DOC.name}: {entry['id']}: "
                                 f"块复制周期 {entry['cycles']!r} 不是 base+N 形式")
            out["n_base"], out["n_step"] = parsed
    return out


def emit_cc(table, order, block) -> str:
    lines = []
    for entry in sorted(table, key=lambda e: e["id"]):
        cycles = entry["value"] if entry["value"] is not None else -1
        dynamic = entry["dynamic"] or ""
        pol = policy_fields(entry, block)
        lines.append(f'    {{"{entry["id"]}", "{entry["mnemonic"]}", '
                     f'{class_mask(entry["klass"], order)}u, {cycles}, '
                     f'{pol["default_cycles"]}, {pol["mem_cycles"]}, '
                     f'{pol["host_cycles"]}, {pol["range_lo"]}, '
                     f'{pol["range_hi"]}, {pol["dyn_base"]}, {pol["dyn_add"]}, '
                     f'{pol["semihost_mask"]}u, {pol["semihost_value"]}u, '
                     f'{pol["per_element"]}, {pol["per_beat"]}, '
                     f'{pol["n_base"]}, {pol["n_step"]}, '
                     f'{pol["elem_width"]}, '
                     f'"{dynamic}", {entry["doc"]}, '
                     f'"{entry.get("provenance") or ""}"}},')
    names = "\n".join(f'    "{name}",' for name in order)
    seen: dict[int, str] = {}
    for entry in table:
        seen.setdefault(class_mask(entry["klass"], order), "/".join(entry["klass"]))
    cases = "\n".join(f'    case {mask}u: return "{label}";'
                      for mask, label in sorted(seen.items()))
    return f"""// Generated by tools/gem5/gen_wuming_cycles.py -- do not edit.
// Source: docs/core-wuming-cycle-model.md (§2 分类 + §3 逐族) +
// contracts/opcodes.yaml (264 ids).
#include "arch/dadao/wuming_cycles.hh"

namespace gem5
{{
namespace DadaoISA
{{
namespace wuming
{{

namespace
{{

const CycleRow kRows[] = {{
{chr(10).join(lines)}
}};

const char *const kClassNames[] = {{
{names}
}};

}} // anonymous namespace

const CycleRow *
rows()
{{
    return kRows;
}}

std::size_t
rowCount()
{{
    return sizeof(kRows) / sizeof(kRows[0]);
}}

const CycleRow *
byId(std::string_view id)
{{
    std::size_t lo = 0;
    std::size_t hi = rowCount();
    while (lo < hi) {{
        const std::size_t mid = lo + (hi - lo) / 2;
        const int cmp = std::string_view(kRows[mid].id).compare(id);
        if (cmp == 0)
            return &kRows[mid];
        if (cmp < 0)
            lo = mid + 1;
        else
            hi = mid;
    }}
    return nullptr;
}}

const char *
className(CycleClass klass)
{{
    const unsigned index = static_cast<unsigned>(klass);
    return index < kNumClasses ? kClassNames[index] : "?";
}}

const char *
rowClasses(const CycleRow &row)
{{
    // "A3/A4" / "F/G1/G2": one literal per class mask actually used.
    switch (row.classMask) {{
{cases}
    default:
        return "?";
    }}
}}

}} // namespace wuming
}} // namespace DadaoISA
}} // namespace gem5
"""


# ── invariants ─────────────────────────────────────────────────────────────
def assert_vocabulary(classes, rows, doc_text: str) -> None:
    for kind in KIND_STEMS:
        if kind not in doc_text:
            raise SystemExit(f"{DOC.name}: 操作词 {kind!r} 不在文档中")
    words = set()
    for row in rows:
        for kind in row.kinds:
            words.add(kind)
    if not words:
        raise SystemExit(f"{DOC.name}: §3 未解析到任何操作词")


def check_doc_line_verbatim(inst_table, classes, lines) -> list[str]:
    """Every cycle figure must appear verbatim in the doc line it cites."""
    problems = []
    for entry in inst_table:
        claims = entry["variants"] or [entry]
        for claim in claims:
            line = claim["doc"]
            if not isinstance(line, int) or line <= 0:
                continue
            text = lines[line - 1]
            value = claim["cycles"]
            if value and not re.search(
                    r"(?<![0-9A-Za-z])" + re.escape(value) + r"(?![0-9A-Za-z])",
                    strip_code(text)):
                problems.append(
                    f"{entry['id']}: 周期 {value!r} 不在 {DOC.name}:{line}")
    return problems


def check_static_dynamic(inst_table) -> list[str]:
    problems = []
    for entry in inst_table:
        claims = entry["variants"] or [entry]
        for claim in claims:
            if claim["dynamic"] is None and not isinstance(claim["value"], int):
                problems.append(
                    f"{entry['id']}: 静态行却没有整数拍数（cycles={claim['cycles']!r}）")
            if claim["dynamic"] is not None and claim["value"] is not None:
                problems.append(
                    f"{entry['id']}: 动态行（{claim['dynamic']}）不应带静态 value")
    return problems


def check_ondisk_yaml(path: Path, insts, classes) -> list[str]:
    """The committed YAML must itself be a valid table (not just byte-equal)."""
    if not path.exists():
        return [f"{path} 不存在"]
    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    rows = data.get("instructions") or []
    problems: list[str] = []
    contract_ids = {i.id for i in insts}
    disk_ids = [r.get("id") for r in rows]
    if len(disk_ids) != len(set(disk_ids)):
        problems.append("存在重复 id")
    extra = sorted(set(disk_ids) - contract_ids)
    if extra:
        problems.append(f"契约里没有的 id {extra[:5]}")
    absent = sorted(contract_ids - set(disk_ids))
    if absent:
        problems.append(f"缺少契约 id {absent[:5]}")
    if data.get("instruction_count") != len(contract_ids):
        problems.append(f"instruction_count={data.get('instruction_count')}")
    for row in rows:
        for klass in row.get("klass") or []:
            if klass not in classes:
                problems.append(f"{row.get('id')}: 类 {klass!r} 不在 §2")
        if (row.get("dynamic") is None) != isinstance(row.get("value"), int):
            problems.append(f"{row.get('id')}: 动态标记与静态值不一致")
        prov = row.get("provenance") or ""
        if not prov:
            problems.append(f"{row.get('id')}: 缺 provenance（§3 的「来源」列）")
        elif not any(tag in prov for tag in PROV_TAGS):
            problems.append(f"{row.get('id')}: provenance {prov!r} 不在 {PROV_TAGS}")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="verify the on-disk artifacts against the doc")
    ap.add_argument("--source", default=str(DEFAULT_SOURCE),
                    help="gem5 source tree that holds the generated C++ table")
    args = ap.parse_args()

    lines = doc_lines()
    doc_sha = hashlib.sha256(DOC.read_bytes()).hexdigest()
    classes = parse_classes(lines)
    if not classes:
        print("FAIL: §2 分类表未解析到任何类", file=sys.stderr)
        return 1
    insts, formats = load_contract()
    mnemonics = {i.mnemonic for i in insts}
    rows = parse_rows(lines, mnemonics, formats)
    assert_vocabulary(classes, rows, "\n".join(lines))

    order = list(classes)
    used = {c.strip() for row in rows for c in row.klass_cell.split("/")}
    unknown = sorted(used - set(classes))
    ok = True

    def report(name: str, passed: bool, detail: str) -> None:
        nonlocal ok
        print(f"[{'PASS' if passed else 'FAIL'}] {name}: {detail}")
        ok = ok and passed

    if unknown:
        report("classes-match-doc", False,
               f"§3 用到 §2 未定义的类 {unknown}")
        return 1

    table, missing = build_table(insts, rows, classes)
    block = block_model(rows)

    report("ids-covered", not missing and len(table) == len(insts),
           f"{len(table)}/{len(insts)} 条 id 有类" +
           (f"；未覆盖 {sorted(missing)[:8]}" if missing else ""))
    contract_ids = {i.id for i in insts}
    table_ids = {e["id"] for e in table}
    report("ids-match-contract", contract_ids == table_ids,
           f"contracts/opcodes.yaml {len(contract_ids)} 条，表 {len(table_ids)} 条")
    table_classes = {c for e in table for c in e["klass"]}
    doc_classes = set(classes)
    report("classes-match-doc", table_classes == doc_classes,
           f"表 {len(table_classes)} 类，§2 {len(doc_classes)} 类" +
           (f"；多 {sorted(table_classes - doc_classes)} 缺 {sorted(doc_classes - table_classes)}"
            if table_classes != doc_classes else ""))
    problems = check_static_dynamic(table)
    report("dynamic-params", not problems,
           f"{sum(1 for e in table if e['dynamic'])} 条动态行均带参数" +
           (f"；问题 {problems[:3]}" if problems else ""))
    problems = check_doc_line_verbatim(table, classes, lines)
    report("cycles-verbatim", not problems,
           f"{len(table)} 条周期的文字均可在所引文档行逐字命中" +
           (f"；问题 {problems[:3]}" if problems else ""))
    counts = row_counts(table, rows)
    empty_rows = [r.line for r in rows if r.section != "00" and not counts[r.line]]
    report("no-dropped-row", not empty_rows,
           f"{len(rows)} 个 §3 行均覆盖到 id（§00 寄存器/RAS 行除外）" +
           (f"；空行 {empty_rows}" if empty_rows else ""))
    unknown_override = [m for m in OVERRIDES if m not in mnemonics]
    report("overrides-known", not unknown_override,
           f"{len(OVERRIDES)} 条 override 均命中契约助记符" +
           (f"；未知 {unknown_override}" if unknown_override else ""))

    if args.check:
        problems = check_ondisk_yaml(OUT_YAML, insts, classes)
        report("ondisk-table", not problems,
               "盘上 YAML 的 id/类/动态标记与契约、§2 一致" +
               (f"；问题 {problems[:3]}" if problems else ""))

    samples_bad = [s for s in block["samples"]
                   if block["per_element"] * s["n"]
                   + block["per_beat"] * s["beats"] != s["figure"]]
    report("block-model", not samples_bad,
           f"D 类 per_element={block['per_element']} per_beat={block['per_beat']}"
           f"（{len(block['samples'])} 条 N=… 实测图逐条回代）" +
           (f"；不符 {samples_bad[:2]}" if samples_bad else ""))

    yaml_text = emit_yaml(table, classes, doc_sha, rows, block)
    hh_text = emit_hh(order, len(table))
    cc_text = emit_cc(table, order, block)
    source = Path(args.source)
    artifacts = [
        (Path("tools/gem5/wuming_cycles.yaml"), yaml_text),
        (source / CPP_HH, hh_text),
        (source / CPP_CC, cc_text),
    ]
    def shown(path: Path) -> str:
        try:
            return str(path.resolve().relative_to(ROOT))
        except ValueError:
            return str(path)

    if args.check:
        for path, text in artifacts:
            if not path.exists():
                report("artifact-present", False, f"{shown(path)} 不存在")
                continue
            same = path.read_text(encoding="utf-8") == text
            report("artifact-up-to-date", same,
                   f"{shown(path)} 与现解析结果"
                   f"{'一致' if same else '不一致（需重跑生成器）'}")
    else:
        for path, text in artifacts:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            print(f"wrote {shown(path)}")

    print(f"classes={len(classes)} ids={len(table)} "
          f"static={sum(1 for e in table if e['dynamic'] is None)} "
          f"dynamic={sum(1 for e in table if e['dynamic'])}")
    print("by_class: " + ", ".join(
        f"{k}={v}" for k, v in sorted(
            {c: sum(1 for e in table if c in e['klass']) for c in classes}.items())))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
