#!/usr/bin/env python3
"""gen_isa_coverage.py — ISA↔后端覆盖矩阵（生成式，两层分列）。

真源（**只读**）：``contracts/opcodes.yaml``（全部记录，不做人工挑拣）。

两层口径
--------
1. **第①层「汇编器可受理」**：逐条记录取其**规范操作数形态**（由
   ``tools/testcases/generate_lit_vectors.py`` 的 ``build_case`` 机械派生，
   与现有 lit 全量档 ``tests/unit/llvm/lit/MC/DADAO-gen/gen-*.s`` **同一口径、
   同一行文本**），喂 ``llvm-mc``：记录受理/拒绝；受理时再独立比对
   「llvm-mc 产出编码 == 真源派生编码」（``word``）。
2. **第②层「ISel 用得上」**：**机械提取**（非人工判读）后端补丁树
   ``components/llvm-project/patches/llvm/lib/Target/DADAO/`` 中的：
   - ``pat``：TableGen ``Pat<...>`` DAG 体内出现的指令 def 名；
   - ``pat-args``：``def``/``defm`` 实例化的 Pat 类实参（含 ``multiclass``
     经 ``defm`` 传入的指令）；
   - ``isel-cpp``：``DADAOISelDAGToDAG.cpp`` / ``DADAOISelLowering.cpp`` 中以
     ``DADAO::<def>`` 显式引用的指令；
   - ``pseudo``：伪指令展开路径（``DADAOInstrInfo::expandPostRAPseudo`` 的
     ``case DADAO::<PSEUDO>:`` 块内 ``BuildMI(... DADAO::<def>)``），
     把 ``Pat`` 里的 ``*_PSEUDO`` 引用解析到实际发射的指令（ISS-327 ①）；
   - ``buildmi``：**任意**后端 C++ 补丁中 ``BuildMI(...)`` 调用里的
     ``DADAO::<def>`` 常量（含 post-ISel：帧处理/寄存器分配等）（ISS-327 ③）；
   - ``synonym``：``.td`` def 与 opcodes 记录**编码身份相同但助记符不同**时，
     证据按编码身份互认（ISS-327 ②，防改名导致假「未用」）。
   每条证据给出 **补丁文件物理行号**（可直接 ``sed -n '<N>p'`` 复核）。

输出（随产物入库、可重跑、幂等；计数一律现场统计）：
  - ``tools/llvm/llvm-isa-backend-matrix.tsv``（机器可读）
  - ``tools/llvm/llvm-isa-backend-matrix.md``（人类可读：口径 + 矩阵 + 缺口汇总）

``--check`` 模式：由真源**重新派生**矩阵并与已入库产物逐字节比对；任一
记录缺层取值、行数与真源不符、证据行复核失败 ⇒ 非零退出（反例门控）。

仅用标准库 + PyYAML；除第①层调 ``llvm-mc`` 外不启动其它外部工具。
"""

from __future__ import annotations

import argparse
import collections
import difflib
import os
import re
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
OPCODES_DEFAULT = REPO / "contracts" / "opcodes.yaml"
BACKEND_DIR = REPO / "components/llvm-project/patches/llvm/lib/Target/DADAO"
LIT_GEN_DIR = REPO / "tests/unit/llvm/lit/MC/DADAO-gen"
TSV_DEFAULT = REPO / "tools/llvm/llvm-isa-backend-matrix.tsv"
MD_DEFAULT = REPO / "tools/llvm/llvm-isa-backend-matrix.md"

# TableGen 源（补丁）与角色。
TD_FILES = [
    "DADAOInstrInfo.td.patch",
    "DADAOInstrInfoFP.td.patch",
    "DADAOCodeGen.td.patch",
    "DADAOInstrFormats.td.patch",
]
# 含指令 def 的文件（用于建立 opcodes 记录 ↔ .td def 的映射）。
TD_DEF_FILES = [
    "DADAOInstrInfo.td.patch",
    "DADAOInstrInfoFP.td.patch",
    "DADAOCodeGen.td.patch",
]
# 第②层：ISel 选入路径（C++ 自定义选择器 / lowering）。
ISEL_CPP_FILES = ["DADAOISelDAGToDAG.cpp.patch", "DADAOISelLowering.cpp.patch"]
# 辅助信息（**不计入**第②层）：伪指令展开 / 帧处理 / 寄存器分配（均 post-ISel）。
POST_ISEL_FILES = [
    "DADAOInstrInfo.cpp.patch",
    "DADAOFrameLowering.cpp.patch",
    "DADAORegisterInfo.cpp.patch",
]

# 缺口三分类里「汇编层/特权族」的机械判据（format / mnemonic 口径，非人工挑拣）：
# crrr/ciii 为特权 cfx 族（经 cfx 访问/cfx2rd 读出），fence/swym 为占位/屏障。
ASM_LEVEL_FORMATS = frozenset({"crrr", "ciii"})
ASM_LEVEL_MNEMONICS = frozenset({"fence", "swym"})

# TableGen 指令格式类 → opcodes.yaml 的 format 字符串（与 validate_instrinfo 同）。
FMT_BY_CLASS = {
    "DADAORrrr": "rrrr", "DADAORrri": "rrri", "DADAORrii": "rrii",
    "DADAORiii": "riii", "DADAOIiii": "iiii", "DADAORwii": "rwii",
    "DADAOOrrr": "orrr", "DADAOOrri": "orri", "DADAOOiii": "oiii",
    "DADAOCrrr": "crrr", "DADAOCiii": "ciii",
    "DADAOLROrrr": "orrr",  # lr.*: hb = rd0 fixed (ADR-0034 D5; LLVM-121t)
}

DEF_HDR = re.compile(r'^def (\w+) : (DADAO\w+)<"([^"]+)">\s*\{')
OP_RE = re.compile(r"let op = (0x[0-9A-Fa-f]+)")
HA_RE = re.compile(r"let ha = (0x[0-9A-Fa-f]+)")
TOKEN_RE = re.compile(r"[A-Za-z_]\w*")
CPP_REF_RE = re.compile(r"DADAO::(\w+)")

# `frem`（= libm `fmod`，余数符号随被除数）与 `forem`/`ftrem`（IEEE remainder，
# 商取最近/平局取偶）**语义不同** ⇒ 后端禁止把 `frem` 直接接到 `forem`/`ftrem`
# （`LLVM-126t` 用户 2026-10-22 裁定；`forem` 只经 `__builtin_dadao_remainder` 接）。
# 取证面 = **已跟踪**的补丁树（`components/llvm-project/patches`）；不使用
# `.work/source/**`（未跟踪树，`git grep` 恒空 ⇒ 死断言，INFRA-103t）。
FREM_WIRED_RE = re.compile(r"\(frem\b[^)]*\)\s*,\s*\(([a-z]+rem\w*)")
REMAINDER_INTRINSIC_RE = re.compile(r"int_dadao_remainder_f(?:32|64)")

# TSV 列（顺序即真源；机器可读）。
TSV_COLUMNS = [
    "id", "mnemonic", "format", "scope", "td_def",
    "L1_assembler", "L1_encoding", "L1_asm",
    "L2_isel", "L2_evidence", "backend_post_isel",
]


# ---------------------------------------------------------------------------
# 补丁文本重建（保留「行 → 补丁物理行号」映射，供证据复核）
# ---------------------------------------------------------------------------
def reconstruct_patch(patch_text: str) -> tuple[str, list[int]]:
    """返回 (重建文本, 重建行号→补丁物理行号1-based 的映射)。"""
    out: list[str] = []
    raw: list[int] = []
    started = False
    for lineno, line in enumerate(patch_text.split("\n"), 1):
        if not started:
            if line.startswith("@@"):
                started = True
            continue
        if line.startswith("+") or line.startswith(" "):
            out.append(line[1:])
            raw.append(lineno)
    return "\n".join(out), raw


def line_of(text: str, offset: int, raw_map: list[int]) -> int:
    """重建文本内字符偏移 → 补丁物理行号。"""
    idx = text.count("\n", 0, offset)  # 0-based 重建行号
    if 0 <= idx < len(raw_map):
        return raw_map[idx]
    return -1


def parse_instr_defs(text: str, keep: list[int]) -> list[dict]:
    """解析 ``def NAME : DADAO<Class><"mnemonic"> { ... }``（体按整行 ``}`` 收尾）。

    不用 ``[^}]*``——def 体注释里可能出现 ``{rfN}`` 之类的花括号。
    """
    lines = text.split("\n")
    defs: list[dict] = []
    i = 0
    while i < len(lines):
        m = DEF_HDR.match(lines[i])
        if not m:
            i += 1
            continue
        name, cls, mnemonic = m.groups()
        body: list[str] = []
        start = i
        i += 1
        while i < len(lines) and lines[i].strip() != "}":
            body.append(lines[i])
            i += 1
        blob = "\n".join(body)
        op = OP_RE.search(blob)
        ha = HA_RE.search(blob)
        defs.append({
            "name": name,
            "format": FMT_BY_CLASS.get(cls),
            "mnemonic": mnemonic,
            "op": op.group(1).lower() if op else None,
            "ha": ha.group(1).lower() if ha else None,
            "line": keep[start] if start < len(keep) else -1,
        })
        i += 1
    return defs


def balanced_angle(text: str, start: int) -> str | None:
    """``text[start] == '<'``；返回匹配到的 ``<...>`` 内层文本。"""
    depth = 0
    for i in range(start, len(text)):
        c = text[i]
        if c == "<":
            depth += 1
        elif c == ">":
            depth -= 1
            if depth == 0:
                return text[start + 1:i]
    return None


# ---------------------------------------------------------------------------
# 记录 ↔ .td def 映射（(mnemonic, format, op, ha) 显式 join）
# ---------------------------------------------------------------------------
def rec_ha(rec: dict) -> int | None:
    """mask 覆盖 ha 位域（bits[23:18]）时，从 value 取该域；否则 None。"""
    mask = int(rec["mask"], 16)
    return (int(rec["value"], 16) >> 18) & 0x3F if (mask & 0xFC0000) == 0xFC0000 else None


def def_key(d: dict) -> tuple:
    return (d["mnemonic"], d["format"],
            int(d["op"], 16) if d["op"] else None,
            int(d["ha"], 16) if d["ha"] else None)


def rec_key(r: dict) -> tuple:
    return (r["mnemonic"], r["format"], int(r["opc"], 16), rec_ha(r))


def build_def_map(defs: list[dict], recs: list[dict]) -> dict[str, list[str]]:
    idx: dict[tuple, list[str]] = collections.defaultdict(list)
    for d in defs:
        idx[def_key(d)].append(d["name"])
    out: dict[str, list[str]] = {}
    for r in recs:
        hits = sorted(set(idx.get(rec_key(r), [])))
        if hits:
            out[r["id"]] = hits
    return out


# ---------------------------------------------------------------------------
# 第②层证据提取
# ---------------------------------------------------------------------------
def extract_evidence(defnames: set[str], patches: dict[str, tuple[str, list[int]]],
                     pseudo_map: dict[str, set[str]] | None = None) -> dict[str, set]:
    """返回 def 名 → {(kind, 文件名, 补丁物理行号)}。

    `pseudo_map` 非空时，Pat 体/实参里的 ``*_PSEUDO`` 引用按其展开体解析到实际
    指令 def，证据类型记 ``pseudo``（ISS-327 ①）。
    """
    pseudo_map = pseudo_map or {}
    ev: dict[str, set] = collections.defaultdict(set)

    def add(tok: str, kind: str, fname: str, offset: int) -> None:
        if tok in defnames:
            ev[tok].add((kind, fname, line_of(text, offset, raw), tok))
            return
        for target in pseudo_map.get(tok, ()):
            if target in defnames:
                # 5 元组：末位记「经哪条伪指令解析」（证据回读时该行含伪指令名）。
                ev[target].add(("pseudo", fname, line_of(text, offset, raw),
                                target, tok))

    # (a) Pat<...> DAG 体； (b) Pat 类实例化的**类实参**（含 defm 的 multiclass 实参）
    for fname in TD_FILES:
        text, raw = patches[fname]
        for m in re.finditer(r"Pat<", text):
            lt = text.index("<", m.start())
            body = balanced_angle(text, lt)
            if body is None:
                continue
            base = lt + 1
            for tm in TOKEN_RE.finditer(body):
                add(tm.group(0), "pat", fname, base + tm.start())
        statements = [(m, m.group(0)) for m in re.finditer(r"^[ \t]*def\b[^;{]*;", text, re.M)]
        statements += [(m, m.group(0)) for m in re.finditer(r"^[ \t]*defm\b.*?;", text, re.M | re.S)]
        for m, seg in statements:
            is_defm = seg.lstrip().startswith("defm")
            if "Pat" not in seg and not is_defm:
                continue
            # 类实参 = 语句内**不在** Pat<...> 体内的 <...> 组（Pat 体已由 (a) 覆盖）
            in_pat = []
            for pm in re.finditer(r"Pat<", seg):
                lt = seg.index("<", pm.start())
                body = balanced_angle(seg, lt)
                if body is not None:
                    in_pat.append((lt, lt + len(body) + 2))
            for tm in re.finditer(r"<", seg):
                if any(lo <= tm.start() < hi for lo, hi in in_pat):
                    continue
                body = balanced_angle(seg, tm.start())
                if body is None:
                    continue
                base = m.start() + tm.start() + 1
                for tk in TOKEN_RE.finditer(body):
                    add(tk.group(0), "pat-args", fname, base + tk.start())

    # (c) ISel C++ 显式引用
    for fname in ISEL_CPP_FILES:
        text, raw = patches[fname]
        for m in CPP_REF_RE.finditer(text):
            tok = m.group(1)
            if tok in defnames:
                ev[tok].add(("isel-cpp", fname, line_of(text, m.start(), raw), tok))
    return ev


def extract_pseudo_pattern_evidence(pseudo_map: dict[str, set[str]],
                                    defnames: set[str],
                                    patches: dict[str, tuple[str, list[int]]]) -> dict[str, set]:
    """伪指令自身带 TableGen 选择模式（`DADAOPseudo<... [(set ...)]>`）⇒ 被 ISel 选中。

    `ADD_PSEUDO`/`MUL_PSEUDO` 等 def 的模式写在 def 体内（不是 `Pat<`），旧提取
    规则看不到，导致其展开后的真实指令被误判「未用」（ISS-327 ①）。
    """
    ev: dict[str, set] = collections.defaultdict(set)
    for fname in TD_FILES:
        text, raw = patches[fname]
        for pseudo, targets in pseudo_map.items():
            m = re.search(r"^[ \t]*def\s+" + re.escape(pseudo)
                          + r"\s*:\s*DADAOPseudo<", text, re.M)
            if not m:
                continue
            semi = text.find(";", m.end())
            if semi == -1:
                continue
            span = text[m.end():semi]
            pat = re.search(r"\[(.*?)\]\s*>\s*$", span, re.S)
            if not pat or not pat.group(1).strip():
                continue  # 模式为空：由 C++ BuildMI 路径覆盖
            for tgt in targets:
                if tgt in defnames:
                    ev[tgt].add(("pseudo", fname, line_of(text, m.start(), raw),
                                 tgt, pseudo))
    return ev


def extract_pseudo_map(patches: dict[str, tuple[str, list[int]]]) -> dict[str, set[str]]:
    """从 expandPostRAPseudo 的 `case DADAO::<PSEUDO>:` 块解析伪指令 → 实际 def。

    伪指令 def（``*_PSEUDO``）不是 ISA 记录，但 ``Pat`` 会引用它们；其展开体
    里的 ``DADAO::<def>`` 才是真正发射的指令（ISS-327 ①）。
    """
    text, _raw = patches["DADAOInstrInfo.cpp.patch"]
    cases = list(re.finditer(r"case\s+DADAO::(\w+)\s*:", text))
    blocks: list[set[str]] = []
    for i, m in enumerate(cases):
        end = cases[i + 1].start() if i + 1 < len(cases) else len(text)
        block = text[m.end():end]
        # 展开体里既可能有 `BuildMI(... DADAO::x)`，也可能先算 `Opc = ... DADAO::x`
        # 再 `TII.get(Opc)`（ADD_PSEUDO/SUB_PSEUDO 合并展开），故收块内**全部**引用。
        blocks.append(set(CPP_REF_RE.findall(block)))
    mapping: dict[str, set[str]] = {}
    # `case A:` 无 body 直接落到 `case B:` ⇒ 共享 B 的展开体（fall-through）。
    for i in range(len(cases) - 1, -1, -1):
        real = blocks[i]
        if not real and i + 1 < len(blocks):
            real = blocks[i + 1]
            blocks[i] = real  # 多级 fall-through（ADD/SUB/MUL 共享一个 body）
        if real:
            mapping[cases[i].group(1)] = set(real)
    return mapping


def extract_buildmi(defnames: set[str], pseudo_map: dict[str, set[str]],
                    patches: dict[str, tuple[str, list[int]]],
                    files: list[str]) -> dict[str, set]:
    """任意后端 C++ 补丁：`BuildMI(...)` 调用内的 `DADAO::<def>` 常量（ISS-327 ③）。"""
    ev: dict[str, set] = collections.defaultdict(set)
    for fname in files:
        text, raw = patches[fname]
        for m in re.finditer(r"BuildMI\s*\(", text):
            semi = text.find(";", m.end())
            span = text[m.start(): semi if semi != -1 else m.end() + 400]
            for tm in CPP_REF_RE.finditer(span):
                tok = tm.group(1)
                if tok in defnames:
                    ev[tok].add(("buildmi", fname,
                                 line_of(text, m.start() + tm.start(), raw), tok))
                    continue
                for tgt in pseudo_map.get(tok, ()):
                    if tgt in defnames:
                        ev[tgt].add(("buildmi", fname,
                                     line_of(text, m.start() + tm.start(), raw),
                                     tgt, tok))
    return ev


def extract_post_isel(defnames: set[str], patches: dict[str, tuple[str, list[int]]]) -> dict[str, set]:
    """辅助信息：post-ISel（伪指令展开/帧/寄存器分配）引用；不计入第②层。"""
    ev: dict[str, set] = collections.defaultdict(set)
    for fname in POST_ISEL_FILES:
        text, raw = patches[fname]
        for m in CPP_REF_RE.finditer(text):
            tok = m.group(1)
            if tok in defnames:
                ev[tok].add((fname, line_of(text, m.start(), raw)))
    return ev


# ---------------------------------------------------------------------------
# 第①层：llvm-mc 受理 + 编码复核
# ---------------------------------------------------------------------------
def resolve_llvm_mc(explicit: str | None) -> Path:
    if explicit:
        p = Path(explicit)
        if not p.is_file():
            raise SystemExit(f"ERROR: --llvm-mc 不存在: {p}")
        return p
    try:
        sys.path.insert(0, str(REPO / "tools/infra"))
        import paths as dadao_paths  # noqa: WPS433 (repo 内工具模块)
        cand = Path(dadao_paths.host_toolchain_bin()) / "llvm-mc"
    except Exception:
        cand = Path("")
    if cand.is_file():
        return cand
    for alt in (REPO / ".work/build/llvm/bin/llvm-mc",
                Path(os.environ.get("DADAO_ROOT", ".")) / ".work/build/llvm/bin/llvm-mc"):
        if alt.is_file():
            return alt
    raise SystemExit(
        "ERROR: 找不到 llvm-mc（试过 $DADAO_HOST_TOOLCHAIN_BIN、"
        ".work/build/llvm/bin/）。先 `make install-host` 或用 --llvm-mc 指定。")


def elf_text_section(data: bytes) -> bytes | None:
    """取 ELF（32/64、大端）首个 .text 段内容。"""
    if len(data) < 0x34 or data[:4] != b"\x7fELF":
        return None
    ei_class = data[4]
    endian = ">" if data[5] == 2 else "<"
    if ei_class == 1:
        e_shoff = struct.unpack_from(endian + "I", data, 0x20)[0]
        e_shentsize = struct.unpack_from(endian + "H", data, 0x2E)[0]
        e_shnum = struct.unpack_from(endian + "H", data, 0x30)[0]
        e_shstrndx = struct.unpack_from(endian + "H", data, 0x32)[0]
        sh_name_off, sh_offset_off, sh_size_off = 0, 16, 20
        u = endian + "I"
    elif ei_class == 2:
        e_shoff = struct.unpack_from(endian + "Q", data, 0x28)[0]
        e_shentsize = struct.unpack_from(endian + "H", data, 0x3A)[0]
        e_shnum = struct.unpack_from(endian + "H", data, 0x3C)[0]
        e_shstrndx = struct.unpack_from(endian + "H", data, 0x3E)[0]
        sh_name_off, sh_offset_off, sh_size_off = 0, 24, 32
        u = endian + "Q"
    else:
        return None
    if e_shnum == 0 or e_shoff == 0:
        return None
    hdr = e_shoff + e_shstrndx * e_shentsize
    str_off = struct.unpack_from(u, data, hdr + sh_offset_off)[0]
    str_size = struct.unpack_from(u, data, hdr + sh_size_off)[0]
    shstr = data[str_off:str_off + str_size]
    for i in range(e_shnum):
        off = e_shoff + i * e_shentsize
        name_idx = struct.unpack_from(endian + "I", data, off + sh_name_off)[0]
        end = shstr.find(b"\0", name_idx)
        if end == -1:
            continue
        if shstr[name_idx:end].decode("ascii", "replace") == ".text":
            o = struct.unpack_from(u, data, off + sh_offset_off)[0]
            s = struct.unpack_from(u, data, off + sh_size_off)[0]
            return data[o:o + s]
    return None


def run_layer1(recs: list[dict], cases: dict[str, dict], llvm_mc: Path) -> dict[str, dict]:
    """逐记录：llvm-mc 受理？受理时编码 == 真源？（真源派生值来自 build_case）"""
    out: dict[str, dict] = {}
    mask_value = [(r["id"], int(r["mask"], 16), int(r["value"], 16)) for r in recs]
    with tempfile.TemporaryDirectory(prefix="dadao-isa-cov-") as tmp:
        obj = os.path.join(tmp, "case.o")
        for rec in recs:
            case = cases[rec["id"]]
            asm = case["asm"]
            try:
                proc = subprocess.run(
                    [str(llvm_mc), "--triple=dadao-unknown-elf", "-filetype=obj",
                     "-o", obj, "-"],
                    input=(asm + "\n").encode(), capture_output=True, timeout=20)
            except subprocess.TimeoutExpired:
                out[rec["id"]] = {"assembler": "timeout", "encoding": "—",
                                  "stderr": "timeout", "asm": asm}
                continue
            if proc.returncode != 0:
                err = proc.stderr.decode("utf-8", "replace").strip().splitlines()
                out[rec["id"]] = {"assembler": "reject", "encoding": "—",
                                  "stderr": err[0] if err else "", "asm": asm}
                continue
            word = None
            try:
                with open(obj, "rb") as fh:
                    text = elf_text_section(fh.read())
                if text and len(text) >= 4:
                    word = struct.unpack_from(">I", text, 0)[0]
            except OSError:
                word = None
            enc = "mismatch"
            if word is not None:
                hits = [rid for rid, mk, val in mask_value if (word & mk) == val]
                if hits == [rec["id"]] and word == case.get("word"):
                    enc = "ok"
            out[rec["id"]] = {"assembler": "accept", "encoding": enc,
                              "stderr": "", "asm": asm}
    return out


# ---------------------------------------------------------------------------
# 矩阵构建
# ---------------------------------------------------------------------------
def load_cases(recs: list[dict]) -> dict[str, dict]:
    """复用 lit 向量生成器的「规范操作数形态」（同一口径、同一行文本）。"""
    sys.path.insert(0, str(REPO / "tools/testcases"))
    try:
        import generate_lit_vectors as glv
    except Exception as exc:  # pragma: no cover
        raise SystemExit(f"ERROR: 无法导入 tools/testcases/generate_lit_vectors.py: {exc}")
    return {r["id"]: glv.build_case(r) for r in recs}


def build_synonym_map(defs: list[dict], recs: list[dict]) -> dict[str, list[str]]:
    """编码身份（format, op, ha）相同但助记符不同的 def → 记录 id（ISS-327 ②）。

    例：opcodes 记录 `it2ft` 若被后端以 `io2fo` 名字引用（同一编码），证据应
    记到该记录上，而不是因助记符不同判「未用」。
    """
    idx: dict[tuple, list[dict]] = collections.defaultdict(list)
    for r in recs:
        idx[(r["format"], int(r["opc"], 16), rec_ha(r))].append(r)
    out: dict[str, list[str]] = {}
    for d in defs:
        key = (d["format"], int(d["op"], 16) if d["op"] else None,
               int(d["ha"], 16) if d["ha"] else None)
        hits = idx.get(key, [])
        if len(hits) == 1 and d["mnemonic"] != hits[0]["mnemonic"]:
            out.setdefault(hits[0]["id"], []).append(d["name"])
    return out


def build_matrix(opcodes: Path, llvm_mc: Path) -> tuple[list[dict], dict]:
    recs = yaml.safe_load(opcodes.read_text(encoding="utf-8"))
    if not isinstance(recs, list) or not recs:
        raise SystemExit(f"ERROR: {opcodes}: 顶层必须是列表且非空")

    cpp_files = sorted({p.name for p in BACKEND_DIR.glob("*.cpp.patch")}
                       | set(ISEL_CPP_FILES) | set(POST_ISEL_FILES))
    patches = {f: reconstruct_patch((BACKEND_DIR / f).read_text(encoding="utf-8"))
               for f in TD_FILES + cpp_files}

    defs = [d for f in TD_DEF_FILES for d in parse_instr_defs(*patches[f])]
    defnames = {d["name"] for d in defs}
    pseudo_map = extract_pseudo_map(patches)
    id2defs = build_def_map(defs, recs)
    synonym_by_id = build_synonym_map(defs, recs)
    ev_by_def = extract_evidence(defnames, patches, pseudo_map)
    for extra in (extract_buildmi(defnames, pseudo_map, patches, cpp_files),
                  extract_pseudo_pattern_evidence(pseudo_map, defnames, patches)):
        for defname, ev in extra.items():
            ev_by_def.setdefault(defname, set()).update(ev)
    post_by_def = extract_post_isel(defnames, patches)
    cases = load_cases(recs)
    l1 = run_layer1(recs, cases, llvm_mc)

    rows = []
    for rec in recs:
        rid = rec["id"]
        ds = id2defs.get(rid, [])
        synonym_defs = synonym_by_id.get(rid, [])
        evidence = set()
        post = set()
        for d in ds + synonym_defs:
            for item in ev_by_def.get(d, ()):
                evidence.add(item)
            post |= post_by_def.get(d, set())
        rows.append({
            "id": rid,
            "mnemonic": rec["mnemonic"],
            "format": rec["format"],
            "scope": rec.get("scope", ""),
            "td_def": ";".join(ds),
            "L1_assembler": l1[rid]["assembler"],
            "L1_encoding": l1[rid]["encoding"],
            "L1_asm": l1[rid]["asm"],
            "L2_isel": "yes" if evidence else "no",
            "L2_evidence": ";".join(":".join(str(x) for x in item)
                                    for item in sorted(evidence)) if evidence else "",
            "_evidence": sorted(evidence),
            "_synonym": sorted(synonym_defs),
            "backend_post_isel": ";".join("%s:%d" % (f, ln) for f, ln in sorted(post)) if post else "",
        })
    rows.sort(key=lambda r: r["id"])
    stats = summarise(rows, len(recs))
    return rows, stats


def summarise(rows: list[dict], total: int) -> dict:
    l1_accept = [r for r in rows if r["L1_assembler"] == "accept"]
    l1_reject = [r for r in rows if r["L1_assembler"] == "reject"]
    l1_other = [r for r in rows if r["L1_assembler"] not in ("accept", "reject")]
    enc_bad = [r for r in rows if r["L1_encoding"] == "mismatch"]
    l2_yes = [r for r in rows if r["L2_isel"] == "yes"]
    gap = [r for r in rows if r["L2_isel"] == "no"]
    scope = collections.Counter(r["scope"] for r in rows)
    gap_excluded = [r for r in gap if r["scope"] == "excluded"]
    gap_asm = [r for r in gap if r["scope"] != "excluded"
               and (r["format"] in ASM_LEVEL_FORMATS or r["mnemonic"] in ASM_LEVEL_MNEMONICS)]
    gap_post = [r for r in gap if r["scope"] != "excluded" and r["backend_post_isel"]
                and r not in gap_asm]
    gap_true = [r for r in gap if r["scope"] != "excluded" and not r["backend_post_isel"]
                and r not in gap_asm]
    kinds = collections.Counter()
    for r in rows:
        for e in r["_evidence"]:
            kinds[e[0]] += 1
    return {
        "total": total, "scope": scope,
        "l1_accept": len(l1_accept), "l1_reject": len(l1_reject), "l1_other": len(l1_other),
        # 反例 mnemonic 现场派生（不写死名单：excluded 记录的 MC 支持随 .td 落地而变）
        "l1_reject_mnemonics": sorted({r["mnemonic"] for r in l1_reject}),
        "enc_bad": len(enc_bad),
        "l2_yes": len(l2_yes), "gap": len(gap),
        "gap_excluded": gap_excluded, "gap_post": gap_post, "gap_true": gap_true,
        "gap_asm": gap_asm,
        "evidence_kinds": kinds,
    }


# ---------------------------------------------------------------------------
# 渲染
# ---------------------------------------------------------------------------
def render_tsv(rows: list[dict]) -> str:
    out = ["\t".join(TSV_COLUMNS)]
    for r in rows:
        out.append("\t".join(str(r[c]) for c in TSV_COLUMNS))
    return "\n".join(out) + "\n"


RENDER = ("**生成器**：`tools/llvm/gen_isa_coverage.py`（生成物，勿手工编辑；"
          "改生成器或真源后重跑）")
REGEN = "python3 tools/llvm/gen_isa_coverage.py"
CHECK = "python3 tools/llvm/gen_isa_coverage.py --check"


def render_md(rows: list[dict], st: dict) -> str:
    scope = st["scope"]
    lines: list[str] = []
    a = lines.append
    a("# ISA↔后端覆盖矩阵（生成式，两层分列）")
    a("")
    a(f"> {RENDER}")
    a(f"> **真源**：`contracts/opcodes.yaml`（**{st['total']}** 条 = "
      f"`m1` {scope.get('m1', 0)} + `fp` {scope.get('fp', 0)} + "
      f"`excluded` {scope.get('excluded', 0)} + `m3` {scope.get('m3', 0)} + "
      f"`m8` {scope.get('m8', 0)} + `m9` {scope.get('m9', 0)}；"
      "计数由脚本现场统计，不写死）")
    a(f"> **重跑**：`{REGEN}`　**门控（反例可失败）**：`{CHECK}`")
    a("> **机器可读**：`tools/llvm/llvm-isa-backend-matrix.tsv`（同源同批生成）")
    a("")
    a("## 1. 两层口径")
    a("")
    a("### 第①层「汇编器可受理」")
    a("")
    a("逐条记录取**规范操作数形态**（每记录一个合法 shape）喂 `llvm-mc "
      "(--triple=dadao-unknown-elf -filetype=obj)`，记 `accept`/`reject`。")
    a("")
    a("- 形态来源：`tools/testcases/generate_lit_vectors.py` 的 `build_case()`"
      "（与现有 lit 全量档 `tests/unit/llvm/lit/MC/DADAO-gen/gen-*.s` **同一口径、同一行文本**；"
      "本工具不另立操作数拼装逻辑）。")
    a("- 受理后**另做编码复核**：由对象 `.text` 取 4 字节大端字，要求"
      "「按真源 `(word & mask) == value` 唯一命中本记录」且等于真源派生编码"
      "（`L1_encoding = ok / mismatch`）。这一列把第①层钉在真源上，而非只看 `llvm-mc` 自洽。")
    a(f"- 现场统计：`accept` **{st['l1_accept']}** / `reject` **{st['l1_reject']}**"
      f"{(' / 异常 ' + str(st['l1_other'])) if st['l1_other'] else ''}；"
      f"编码复核不符 **{st['enc_bad']}**。")
    if st["l1_reject_mnemonics"]:
        a(f"- `scope: excluded` 且后端未实现者（{'/'.join('`' + m + '`' for m in st['l1_reject_mnemonics'])}，"
          "现场派生）由汇编器**显式拒绝**（`reject`）；其余 `scope: excluded` 记录（MC 层已受理、"
          "执行侧仍 ILLI）与 `tests/unit/llvm/lit/MC/DADAO-gen/gen-excluded.s` 的反例同口径。")
    else:
        a("- 无 `reject` 记录（现场派生：`scope: excluded` 现为 0 条——`cfxld`/`cfxst` 已从 ISA "
          "删除，`crii` 格式一并撤销），故无 `gen-excluded.s` 反例档。")
    a("")
    a("### 第②层「ISel 用得上」（机械提取，非人工判读）")
    a("")
    a("对每条记录，取其 `.td` def（由 `(mnemonic, format, op, ha)` 显式 join 真源），"
      "在后端补丁树中机械收集引用：")
    a("")
    a("| 证据类型 | 含义 | 采集点 |")
    a("|---|---|---|")
    a("| `pat` | TableGen `Pat<...>` DAG 体内出现的指令 def 名（自动生成的 ISel 选入表） | `DADAOCodeGen.td.patch` 等 |")
    a("| `pat-args` | `def`/`defm` 的 Pat 类实参（含 `multiclass` 经 `defm` 传入的指令） | `DADAOCodeGen.td.patch` |")
    a("| `isel-cpp` | `DADAO::<def>` 显式引用（自定义选择器 / lowering 发射） | `DADAOISelDAGToDAG.cpp.patch`、`DADAOISelLowering.cpp.patch` |")
    a("| `pseudo` | 伪指令（`*_PSEUDO`）的 TableGen 选择模式 / 展开体（`expandPostRAPseudo`）解析到的**实际发射指令**（ISS-327 ①） | `DADAOCodeGen.td.patch`、`DADAOInstrInfo.cpp.patch` |")
    a("| `buildmi` | 任意后端 C++ 补丁中 `BuildMI(...)` 调用里的 `DADAO::<def>` 常量（含帧处理/寄存器分配等 post-ISel 发射，ISS-327 ③） | `DADAO*.cpp.patch` |")
    a("| `synonym` | `.td` def 与记录**编码身份相同但助记符不同**时按编码身份互认（ISS-327 ②） | 全 `.td` 补丁 |")
    a("")
    a(f"现场统计：证据条数 = " +
      " + ".join(f"{k} {v}" for k, v in sorted(st["evidence_kinds"].items())) +
      f"；判「用得上」的记录 **{st['l2_yes']}** 条。")
    a("")
    a("### 提取方法的局限（盲区披露）")
    a("")
    a("- **纯静态**：只读已入库补丁源码，不看构建产物（`.inc`）与运行期；"
      "`multiclass`/类继承经人工写了机械展开规则（`Pat<` 体 + 实例化实参），"
      "若日后新增其它间接引用形式，须同步扩充提取规则。")
    a("- **post-ISel 发射计入 `buildmi`/`pseudo`（ISS-327）**：伪指令展开、帧处理、"
      "寄存器分配等 `BuildMI` 常量也证明「后端确实发射该指令」；辅助列 "
      "`backend_post_isel` 仅保留 `DADAO::<def>` 的普通引用背景，不再作为排除条件。")
    a("- **伪指令展开体共享**：`ADD_PSEUDO`/`SUB_PSEUDO`/`MUL_PSEUDO` 等多条 case 共享"
      "一个展开体（fall-through + 运行期 `Opc` 三元选择），静态提取无法逐条区分 ⇒ "
      "同一展开体覆盖的指令**都**记 `pseudo` 证据（保守：宁多认，不假报「未用」）。")
    a("- **同义名（`synonym`）**：仅当 `.td` def 与记录 `(format, op, ha)` 编码身份相同、"
      "助记符不同时才互认；当前后端未出现此类改名（现场为 0 组，属正常）。")
    a("- **间接引用已覆盖**：`DAG.getNode(DADAOISD::…)` 自定义节点本身不是指令名，"
      "其落地指令由 `Pat` 覆盖（如 `cs.*` / `br.*`）；若某自定义节点的落地指令"
      "**只在 C++ 里 `BuildMI`**，则由 `isel-cpp` 捕获。")
    a("- **`.td` def 无真源记录者不入选**：CodeGen-only 伪指令（`*_PSEUDO`/`GLOBAL_ADDR`/"
      "`JT_ADDR`/`tailjmp_*`）不是 ISA 记录；其证据经 `pseudo`/`synonym` 解析到实际指令；"
      "`tailjmp_*` 与 `jump` 同编码，归入 `jump` 记录的证据。")
    a("- **MC-only 指令**：`fence` 汇编可得但无 ISel 模式 ⇒ 第②层 `no`（属正常，非缺陷）。")
    a("")
    a(f"## 2. 矩阵（全量 {st['total']} 条，按 id 排序）")
    a("")
    a("列：`id` ｜ `mnemonic` ｜ `format` ｜ `scope` ｜ **①汇编器** ｜ **②ISel** ｜ 证据")
    a("（证据格式 `kind:文件:补丁物理行号:def名[:伪指令名]`，可直接 `sed -n '<行号>p' <文件>` 复核；"
      "完整形态行见 TSV 的 `L1_asm` 列）")
    a("")
    a("| id | mnemonic | format | scope | ①汇编器 | ②ISel | 证据 |")
    a("|---|---|---|---|---|---|---|")
    for r in rows:
        ev = r["L2_evidence"].replace("|", "\\|") if r["L2_evidence"] else "—"
        a(f"| `{r['id']}` | `{r['mnemonic']}` | `{r['format']}` | `{r['scope']}` | "
          f"{r['L1_assembler']} | {r['L2_isel']} | {ev} |")
    a("")
    gap = [r for r in rows if r["L2_isel"] == "no"]
    a(f"## 3. 缺口汇总（未被 ISel 使用，{len(gap)} 条）")
    a("")
    a("候选优化面（供后续里程碑参考）。按性质分四类（现场统计）：")
    a("")
    a(f"1. **真缺口·候补优化面**（`scope != excluded`，且后端 ISel/post-ISel 均未引用，"
      f"且非汇编层/特权族）：**{len(st['gap_true'])}** 条 —— ISA 有、后端一次都没发射，最有价值。")
    a(f"2. **真缺口·汇编层/特权族**（同上但 `format ∈ {{crrr, ciii}}` 或助记符 ∈ "
      f"{{fence, swym}}，机械判据）：**{len(st['gap_asm'])}** 条 —— 经 cfx 访问/内联汇编/占位语义使用，"
      "不经 ISel 选入属预期。")
    a(f"3. **仅 post-ISel 引用**（伪指令展开/帧/寄存器分配会发射，非 ISel 选入）：**{len(st['gap_post'])}** 条。")
    if st["gap_excluded"]:
        a(f"4. **`scope: excluded` 未实现**（汇编器拒绝、执行 ILLI）：**{len(st['gap_excluded'])}** 条 —— 不在本期范围。")
    a("")
    for idx, (title, group) in enumerate(
            (("真缺口·候补优化面", st["gap_true"]),
             ("真缺口·汇编层/特权族", st["gap_asm"]),
             ("仅 post-ISel 引用", st["gap_post"]),
             ("scope: excluded（未实现）", st["gap_excluded"])), 1):
        a(f"### 3.{idx} {title}（{len(group)} 条）")
        a("")
        if not group:
            a("（无）")
            a("")
            continue
        a("| id | mnemonic | format | scope |")
        a("|---|---|---|---|")
        for r in group:
            a(f"| `{r['id']}` | `{r['mnemonic']}` | `{r['format']}` | `{r['scope']}` |")
        a("")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# --check
# ---------------------------------------------------------------------------
def verify_evidence(rows: list[dict], errors: list[str]) -> int:
    """逐条证据回读补丁物理行，确认「该行确实引用该 def」。

    口径：证据行号 = **def 名 token 所在行**（`Pat<...>` 体可为多行，
    故不要求该行含 `Pat` 关键字；token 落在哪个 `Pat<`/实例化体里由
    提取阶段保证，`--check` 的逐字节比对会整体重派生复核）。
    """
    n = 0
    cache: dict[str, list[str]] = {}
    for r in rows:
        if not r["L2_evidence"]:
            continue
        for item in r["L2_evidence"].split(";"):
            parts = item.split(":")
            kind, fname, line_s, defname = parts[:4]
            via = parts[4] if len(parts) > 4 else None
            line = int(line_s)
            if fname not in cache:
                cache[fname] = (BACKEND_DIR / fname).read_text(encoding="utf-8").split("\n")
            src = cache[fname]
            n += 1
            if not (1 <= line <= len(src)):
                errors.append(f"证据行越界: {item}")
                continue
            if defname not in src[line - 1] and not (via and via in src[line - 1]):
                errors.append(f"证据行不含 def 名 {defname}/伪指令 {via}: {item} "
                              f"→ {src[line - 1].strip()[:80]}")
    return n


def cross_check_lit(rows: list[dict], errors: list[str]) -> int:
    """第①层与现有 lit 全量档口径一致：每条可汇编记录的行文本出现在对应 gen-*.s。"""
    if not LIT_GEN_DIR.is_dir():
        errors.append(f"lit 全量档目录缺失: {LIT_GEN_DIR}（先跑 generate_lit_vectors.py）")
        return 0
    files = {p.name: set(l.rstrip("\n") for l in p.read_text(encoding="utf-8").splitlines()
                         if l.strip() and not l.startswith("@@"))
             for p in sorted(LIT_GEN_DIR.glob("gen-*.s"))}
    n = 0
    for r in rows:
        if r["L1_assembler"] != "accept":
            continue  # 反例（excluded）在 gen-excluded.s 中以注释形式存
        fn = f"gen-{r['format']}.s"
        n += 1
        if r["L1_asm"] not in files.get(fn, set()):
            errors.append(f"lit 口径不一致: {r['id']} 的 {fn} 中缺行 {r['L1_asm']!r}")
    return n


def load_backend_patches() -> dict[str, tuple[str, list[int]]]:
    """重建后端补丁树全部 ``*.patch``（键 = 相对 DADAO 目录的路径）。

    取证只走**已跟踪**的补丁源；``.work/source/**`` 是未跟踪检出，不能作证据面。
    """
    return {
        str(p.relative_to(BACKEND_DIR)): reconstruct_patch(p.read_text(encoding="utf-8"))
        for p in sorted(BACKEND_DIR.rglob("*.patch"))
    }


def frem_proof(patches: dict[str, tuple[str, list[int]]]) -> tuple[list[str], int]:
    """``frem`` 未接 ``forem``/``ftrem`` 的现场证明（INFRA-103t）。

    返回 ``(接线证据列表, remainder intrinsic 模式行数)``；空列表 = 未接线。
    证据项形如 ``<补丁文件>:<补丁物理行号>``，可直接 ``sed -n '<N>p'`` 复核。
    """
    hits: list[str] = []
    n_intr = 0
    for fname, (text, raw_map) in sorted(patches.items()):
        for m in FREM_WIRED_RE.finditer(text):
            hits.append(f"{fname}:{line_of(text, m.start(), raw_map)} -> {m.group(1)}")
        n_intr += sum(1 for line in text.split("\n")
                      if REMAINDER_INTRINSIC_RE.search(line))
    return hits, n_intr


def cmd_check(args) -> int:
    rows, st = build_matrix(Path(args.opcodes), resolve_llvm_mc(args.llvm_mc))
    errors: list[str] = []

    # 结构断言：行数/取值/证据可复核 —— 均可达 FAIL。
    if st["l1_other"]:
        errors.append(f"{st['l1_other']} 条记录第①层取值异常（timeout/未知）")
    if st["enc_bad"]:
        errors.append(f"{st['enc_bad']} 条记录编码复核 mismatch")
    bad = [r["id"] for r in rows if not r["L1_assembler"] or not r["L2_isel"]]
    if bad:
        errors.append(f"{len(bad)} 条记录缺两层取值: {bad[:5]}")
    n_ev = verify_evidence(rows, errors)
    n_lit = cross_check_lit(rows, errors)

    # `frem` ↔ `forem`/`ftrem` 边界（INFRA-103t）：取证面 = 已跟踪补丁树，
    # 注入 `(frem ...) -> (forem ...)` 即红（可达 FAIL）。
    frem_hits, n_intr = frem_proof(load_backend_patches())
    if frem_hits:
        errors.append(
            "`frem` 被接到 `forem`/`ftrem`（语义不同，禁止；见 LLVM-126t）: "
            + ", ".join(frem_hits[:5])
        )
    if n_intr != 2:
        errors.append(
            f"`int_dadao_remainder_f32/f64` 模式行数 {n_intr} != 2"
            "（`forem`/`ftrem` 只能经该 intrinsic 触达）"
        )

    want_tsv = render_tsv(rows)
    want_md = render_md(rows, st)
    for path, want in ((Path(args.tsv), want_tsv), (Path(args.md), want_md)):
        if not path.is_file():
            errors.append(f"缺失产物: {path}")
            continue
        got = path.read_text(encoding="utf-8")
        if got != want:
            diff = list(difflib.unified_diff(got.splitlines(), want.splitlines(),
                                             fromfile=str(path), tofile="（真源重派生）",
                                             lineterm="", n=1))[:12]
            errors.append(f"与真源不一致: {path}\n    " + "\n    ".join(diff))
    # 产物内计数 == 真源记录数
    if TSV_DEFAULT == Path(args.tsv):
        body = [l for l in Path(args.tsv).read_text(encoding="utf-8").splitlines() if l][1:]
        if len(body) != st["total"]:
            errors.append(f"TSV 数据行 {len(body)} != 真源记录 {st['total']}")

    print(f"gen_isa_coverage --check: 真源记录 {st['total']}；"
          f"第①层 accept {st['l1_accept']}/reject {st['l1_reject']}；"
          f"第②层 yes {st['l2_yes']}/no {st['gap']}；"
          f"证据行复核 {n_ev}；lit 口径抽查 {n_lit}")
    if errors:
        for e in errors:
            print(f"  FAIL: {e}", file=sys.stderr)
        print(f"gen_isa_coverage --check: FAIL（{len(errors)} 项）", file=sys.stderr)
        return 1
    print("gen_isa_coverage --check: PASS")
    return 0


# ---------------------------------------------------------------------------
# --self-test：三类新增证据源（ISS-327）——每条断言均有可达 FAIL 的构造反例。
# ---------------------------------------------------------------------------
def self_test() -> int:
    ok = True

    def check(name: str, cond: bool, detail: str = "") -> None:
        nonlocal ok
        print(f"[{'PASS' if cond else 'FAIL'}] self-test {name}"
              + (f": {detail}" if detail else ""))
        ok = ok and cond

    # ① 伪指令展开映射（真实补丁，现场解析）：ADD_PSEUDO → add_uo_rd
    patches = {f: reconstruct_patch((BACKEND_DIR / f).read_text(encoding="utf-8"))
               for f in TD_FILES + sorted({p.name for p in BACKEND_DIR.glob("*.cpp.patch")})}
    pmap = extract_pseudo_map(patches)
    check("pseudo-map ADD_PSEUDO→add_uo_rd",
          "add_uo_rd" in pmap.get("ADD_PSEUDO", set()),
          str(sorted(pmap.get("ADD_PSEUDO", set()))[:4]))
    # 反例可判性：把 case 名改掉 ⇒ 映射为空
    fake = {"DADAOInstrInfo.cpp.patch": ("case DADAO::NOT_A_PSEUDO: { return true; }", [1])}
    check("pseudo-map 反例（无展开体 ⇒ 空）",
          extract_pseudo_map(fake) == {})
    defs = [d for f in TD_DEF_FILES for d in parse_instr_defs(*patches[f])]
    defnames = {d["name"] for d in defs}

    # ② 同义名：编码身份相同、助记符不同 ⇒ 记到记录上
    recs = [{"id": "it2ft_orri_rf", "mnemonic": "it2ft", "format": "orri",
             "opc": "0x44", "mask": "0xFFFC0000", "value": "0x44040000"}]
    syn_defs = [{"name": "io2fo_orri_rf", "mnemonic": "io2fo", "format": "orri",
                 "op": "0x44", "ha": "0x01"}]
    recs[0]["ha"] = "0x01"
    syn = build_synonym_map(syn_defs, recs)
    check("synonym（同编码不同名 ⇒ 互认）",
          syn.get("it2ft_orri_rf") == ["io2fo_orri_rf"], str(syn))
    bad_defs = [dict(syn_defs[0], ha="0x02")]
    check("synonym 反例（编码不同 ⇒ 不互认）",
          build_synonym_map(bad_defs, recs) == {})

    # ③ BuildMI opcode 常量（真实补丁）：clmul_o_rd 出现在 InstrInfo.cpp 的 BuildMI
    cpp = sorted({p.name for p in BACKEND_DIR.glob("*.cpp.patch")})
    bmi = extract_buildmi(defnames, pmap, patches, cpp)
    check("buildmi clmul_o_rd", "clmul_o_rd" in bmi,
          str(sorted(bmi.get("clmul_o_rd", set()))[:1]))
    check("buildmi 反例（无 BuildMI 文本 ⇒ 空）",
          extract_buildmi(defnames, pmap,
                          {"x.cpp.patch": ("int f(){return 0;}", [1])}, ["x.cpp.patch"]) == {})

    # ④ `frem` 不得接 `forem`/`ftrem`（INFRA-103t）：真实补丁树为空 + 反例必中
    real_hits, real_intr = frem_proof(load_backend_patches())
    check("frem 未接 forem/ftrem（已跟踪补丁树）", not real_hits, str(real_hits[:3]))
    check("remainder intrinsic 模式 = 2（f32/f64）", real_intr == 2, str(real_intr))
    fake_wire = {"DADAOCodeGen.td.patch": (
        "def : Pat<(frem f64:$a, f64:$b), (forem_orrr_rf f64:$a, f64:$b)>;", [1])}
    fake_hits, _ = frem_proof(fake_wire)
    check("frem 接线反例（注入 forem ⇒ 命中）", len(fake_hits) == 1, str(fake_hits))

    print(f"self-test: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--opcodes", default=str(OPCODES_DEFAULT))
    ap.add_argument("--llvm-mc", default=None,
                    help="llvm-mc 路径（默认取 host toolchain bin / .work/build）")
    ap.add_argument("--tsv", default=str(TSV_DEFAULT))
    ap.add_argument("--md", default=str(MD_DEFAULT))
    ap.add_argument("--check", action="store_true",
                    help="由真源重派生并与已入库产物比对；不一致即非零退出")
    ap.add_argument("--self-test", action="store_true",
                    help="三类证据源（pseudo/synonym/buildmi）的单元自检")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()
    if args.check:
        return cmd_check(args)

    rows, st = build_matrix(Path(args.opcodes), resolve_llvm_mc(args.llvm_mc))
    tsv, md = render_tsv(rows), render_md(rows, st)
    Path(args.tsv).write_text(tsv, encoding="utf-8")
    Path(args.md).write_text(md, encoding="utf-8")
    print(f"gen_isa_coverage: 真源记录 {st['total']}（现场统计）")
    print(f"  第①层 汇编器: accept {st['l1_accept']} / reject {st['l1_reject']}"
          f"{' / 异常 ' + str(st['l1_other']) if st['l1_other'] else ''}"
          f"；编码复核不符 {st['enc_bad']}")
    print(f"  第②层 ISel: yes {st['l2_yes']} / no {st['gap']}"
          f"（证据 " + " + ".join(f"{k}={v}" for k, v in sorted(st["evidence_kinds"].items())) + "）")
    print(f"  缺口: 候补优化面 {len(st['gap_true'])} + 汇编层/特权族 {len(st['gap_asm'])}"
          f" + 仅 post-ISel {len(st['gap_post'])} + excluded {len(st['gap_excluded'])}"
          f" = {st['gap']}")
    print(f"  TSV -> {args.tsv}")
    print(f"  MD  -> {args.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
