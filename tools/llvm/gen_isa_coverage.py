#!/usr/bin/env python3
"""gen_isa_coverage.py — ISA↔后端覆盖矩阵（生成式，两层分列）。

真源（**只读**）：``contracts/opcodes.yaml``（全部记录，不做人工挑拣）。

两层口径
--------
1. **第①层「汇编器可受理」**：逐条记录取其**规范操作数形态**（由
   ``tools/testcases/generate_lit_vectors.py`` 的 ``build_case`` 机械派生，
   与现有 lit 全量档 ``tests/llvm/lit/MC/DADAO-gen/gen-*.s`` **同一口径、
   同一行文本**），喂 ``llvm-mc``：记录受理/拒绝；受理时再独立比对
   「llvm-mc 产出编码 == 真源派生编码」（``word``）。
2. **第②层「ISel 用得上」**：**机械提取**（非人工判读）后端补丁树
   ``components/llvm-project/patches/llvm/lib/Target/DADAO/`` 中的：
   - ``pat``：TableGen ``Pat<...>`` DAG 体内出现的指令 def 名；
   - ``pat-args``：``def``/``defm`` 实例化的 Pat 类实参（含 ``multiclass``
     经 ``defm`` 传入的指令）；
   - ``isel-cpp``：``DADAOISelDAGToDAG.cpp`` / ``DADAOISelLowering.cpp`` 中以
     ``DADAO::<def>`` 显式引用的指令。
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
LIT_GEN_DIR = REPO / "tests/llvm/lit/MC/DADAO-gen"
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
# crrr/ciii/crii 为特权 cfx 族（经 cfx 访问/cfx2rd 读出），fence/swym 为占位/屏障。
ASM_LEVEL_FORMATS = frozenset({"crrr", "ciii", "crii"})
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
    return (r["mnemonic"], r["format"], int(r["op"], 16), rec_ha(r))


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
def extract_evidence(defnames: set[str], patches: dict[str, tuple[str, list[int]]]) -> dict[str, set]:
    """返回 def 名 → {(kind, 文件名, 补丁物理行号)}。"""
    ev: dict[str, set] = collections.defaultdict(set)

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
                if tm.group(0) in defnames:
                    ev[tm.group(0)].add(("pat", fname, line_of(text, base + tm.start(), raw)))
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
                    if tk.group(0) in defnames:
                        ev[tk.group(0)].add(("pat-args", fname,
                                             line_of(text, base + tk.start(), raw)))

    # (c) ISel C++ 显式引用
    for fname in ISEL_CPP_FILES:
        text, raw = patches[fname]
        for m in CPP_REF_RE.finditer(text):
            tok = m.group(1)
            if tok in defnames:
                ev[tok].add(("isel-cpp", fname, line_of(text, m.start(), raw)))
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


def build_matrix(opcodes: Path, llvm_mc: Path) -> tuple[list[dict], dict]:
    recs = yaml.safe_load(opcodes.read_text(encoding="utf-8"))
    if not isinstance(recs, list) or not recs:
        raise SystemExit(f"ERROR: {opcodes}: 顶层必须是列表且非空")

    patches = {f: reconstruct_patch((BACKEND_DIR / f).read_text(encoding="utf-8"))
               for f in TD_FILES + ISEL_CPP_FILES + POST_ISEL_FILES}

    defs = [d for f in TD_DEF_FILES for d in parse_instr_defs(*patches[f])]
    defnames = {d["name"] for d in defs}
    id2defs = build_def_map(defs, recs)
    ev_by_def = extract_evidence(defnames, patches)
    post_by_def = extract_post_isel(defnames, patches)
    cases = load_cases(recs)
    l1 = run_layer1(recs, cases, llvm_mc)

    rows = []
    for rec in recs:
        rid = rec["id"]
        ds = id2defs.get(rid, [])
        evidence = set()
        post = set()
        for d in ds:
            for (kind, fname, ln) in ev_by_def.get(d, ()):
                evidence.add((kind, fname, ln, d))
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
            "L2_evidence": ";".join("%s:%s:%d:%s" % (k, f, ln, d)
                                    for (k, f, ln, d) in sorted(evidence)) if evidence else "",
            "_evidence": sorted(evidence),
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
      "（与现有 lit 全量档 `tests/llvm/lit/MC/DADAO-gen/gen-*.s` **同一口径、同一行文本**；"
      "本工具不另立操作数拼装逻辑）。")
    a("- 受理后**另做编码复核**：由对象 `.text` 取 4 字节大端字，要求"
      "「按真源 `(word & mask) == value` 唯一命中本记录」且等于真源派生编码"
      "（`L1_encoding = ok / mismatch`）。这一列把第①层钉在真源上，而非只看 `llvm-mc` 自洽。")
    a(f"- 现场统计：`accept` **{st['l1_accept']}** / `reject` **{st['l1_reject']}**"
      f"{(' / 异常 ' + str(st['l1_other'])) if st['l1_other'] else ''}；"
      f"编码复核不符 **{st['enc_bad']}**。")
    a("- `scope: excluded` 且后端未实现者（`cfxld`/`cfxst`/`lr_*`/`sc_*`）由汇编器"
      "**显式拒绝**（`reject`），与 `tests/llvm/lit/MC/DADAO-gen/gen-excluded.s` 的反例同口径。")
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
    a("- **post-ISel 不计入第②层**：伪指令展开（`DADAOInstrInfo::expandPostRAPseudo`）、"
      "分支松弛、帧处理、寄存器分配 `copyPhysReg` 等发射的指令，其引用点在 "
      "`DADAOInstrInfo.cpp` / `DADAOFrameLowering.cpp` / `DADAORegisterInfo.cpp`——"
      "**不属于 ISel**，单列为辅助列 `backend_post_isel`（仅作背景，不参与第②层判定）。")
    a("- **间接引用已覆盖**：`DAG.getNode(DADAOISD::…)` 自定义节点本身不是指令名，"
      "其落地指令由 `Pat` 覆盖（如 `cs.*` / `br.*`）；若某自定义节点的落地指令"
      "**只在 C++ 里 `BuildMI`**，则由 `isel-cpp` 捕获。")
    a("- **`.td` def 无真源记录者不入选**：CodeGen-only 伪指令（`*_PSEUDO`/`GLOBAL_ADDR`/"
      "`JT_ADDR`/`tailjmp_*`）不是 ISA 记录；`tailjmp_*` 与 `jump` 同编码，"
      "归入 `jump` 记录的证据。")
    a("- **MC-only 指令**：`fence` 汇编可得但无 ISel 模式 ⇒ 第②层 `no`（属正常，非缺陷）。")
    a("")
    a(f"## 2. 矩阵（全量 {st['total']} 条，按 id 排序）")
    a("")
    a("列：`id` ｜ `mnemonic` ｜ `format` ｜ `scope` ｜ **①汇编器** ｜ **②ISel** ｜ 证据")
    a("（证据格式 `kind:文件:补丁物理行号:def名`，可直接 `sed -n '<行号>p' <文件>` 复核；"
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
    a(f"2. **真缺口·汇编层/特权族**（同上但 `format ∈ {{crrr, ciii, crii}}` 或助记符 ∈ "
      f"{{fence, swym}}，机械判据）：**{len(st['gap_asm'])}** 条 —— 经 cfx 访问/内联汇编/占位语义使用，"
      "不经 ISel 选入属预期。")
    a(f"3. **仅 post-ISel 引用**（伪指令展开/帧/寄存器分配会发射，非 ISel 选入）：**{len(st['gap_post'])}** 条。")
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
            kind, fname, line_s, defname = item.split(":")
            line = int(line_s)
            if fname not in cache:
                cache[fname] = (BACKEND_DIR / fname).read_text(encoding="utf-8").split("\n")
            src = cache[fname]
            n += 1
            if not (1 <= line <= len(src)):
                errors.append(f"证据行越界: {item}")
                continue
            if defname not in src[line - 1]:
                errors.append(f"证据行不含 def 名 {defname}: {item} → {src[line - 1].strip()[:80]}")
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
    args = ap.parse_args(argv)

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
