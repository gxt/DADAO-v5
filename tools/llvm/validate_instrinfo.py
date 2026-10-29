#!/usr/bin/env python3
"""Validate the committed DADAO LLVM instruction defs against opcodes.yaml.

真源（sources of truth，二者均为真源，脚本只做交叉校验）:
  - contracts/opcodes.yaml
      —— 编码真源（由 tools/spec/generate_opcodes.py 从 spec/ 生成）。
  - components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOInstrInfo*.td.patch
      —— 实际被 LLVM 编译的指令定义真源：`DADAOInstrInfo.td`（M1/M3/M8/M9 与
         MC-only excluded）**与 `DADAOInstrInfoFP.td`（scope: fp，ISS-320）**。
         默认即校验这两个提交物（仓库内、无需 .work/source 检出，故可作为
         make check 门控）；也可用 --td 指向任意单个 .td 文件（例如 .work/source
         下的工作副本）。

命名映射（显式定义）:
  `.td` 的 def 名是 **legacy 标识符**，被 DADAO CodeGen 直接引用
  （如 DADAOInstrInfo.cpp 用 DADAO::rb2rb / DADAO::rd2rd），无法由 opcodes.yaml
  的 `id`（`{mnemonic}_{format}_{feature}`，如 `ld.ub_rrii_rd`）反推——旧
  `insn` 字段是手工命名的（如 `ld.ub-rd` → `ld_ub_rd`）。因此本校验器在两份
  真源之间用 **编码身份** 做显式 join：

      join key = (mnemonic, format, op, ha)

  该 key 在两侧均唯一（见 Check 4）。opcodes.yaml 的 `id`（用 `_`）与 `.td` 的
  def 名均通过此共享 key 解析；两侧的 mnemonic 字符串都用 `.`。

Checks
  1. baseline：每条 scope:m1 记录恰有一个匹配的 .td def
     （计数由 opcodes.yaml 派生，绝无硬编码 178/152）。
  2. coverage：每条 scope:m3（M3 CodeGen 指令）/ scope:fp（FP 记录；
     ISS-320）/ scope:m8（新增 ISA 指令，ADR-0012 D10 / SPEC-142t）/
     scope:m9 记录也须有匹配的 .td def。
  3. no orphan：每个 .td def 恰映射到一条 opcodes.yaml 记录
     （可捕获凭空编码与注入的 mnemonic/op 漂移）。
  4. mapping：join key 在两侧均唯一（无歧义映射）。
  5. non-m1 policy：.td 中的非 m1/fp def 仅限显式 allow-list
     （scope:m3、scope:m8、scope:m9，以及 MC 层仍需的个别 scope:excluded）。
  6. format：.td 中 m1 def 用到的格式类集合 == scope:m1 记录的格式集合
     （fp 同口径另加一条，ISS-320）。

退出码 0 当且仅当全部检查通过。

用法:
    python3 tools/llvm/validate_instrinfo.py
    python3 tools/llvm/validate_instrinfo.py --td /path/to/DADAOInstrInfo.td
    python3 tools/llvm/validate_instrinfo.py --opcodes /tmp/opcodes.yaml
    python3 tools/llvm/validate_instrinfo.py --dump-map
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
OPCODES_DEFAULT = REPO / "contracts" / "opcodes.yaml"
TD_PATCH_DIR = (
    REPO / "components" / "llvm-project" / "patches" / "llvm" / "lib"
    / "Target" / "DADAO"
)
# 全部指令 def 真源补丁（ISS-320：FP `.td` 此前未纳入）。
# glob 而非写死文件名：新增 `DADAOInstrInfo*.td.patch` 自动纳入覆盖。
TD_PATCH_GLOB = "DADAOInstrInfo*.td.patch"
TD_PATCH_DEFAULT = TD_PATCH_DIR / "DADAOInstrInfo.td.patch"

# TableGen format class -> opcodes.yaml `format` string.
FMT_BY_CLASS = {
    "DADAORrrr": "rrrr", "DADAORrri": "rrri", "DADAORrii": "rrii",
    "DADAORiii": "riii", "DADAOIiii": "iiii", "DADAORwii": "rwii",
    "DADAOOrrr": "orrr", "DADAOOrri": "orri", "DADAOOiii": "oiii",
    # Privileged cfx formats (LLVM-060t): .td defs for trap/escape/cfx2rd/cfx2rc.
    # SPEC-115t re-scoped these four to scope:m1, so their defs are now plain M1
    # defs (not MC-only-excluded); the crrr/ciii format mapping stays required.
    "DADAOCrrr": "crrr", "DADAOCiii": "ciii",
    # lr.* (ADR-0034 D3/D5; LLVM-121t): same encoded fields as orrr, but hb is
    # the fixed rd0 so the assembly form has two operands.
    "DADAOLROrrr": "orrr",
}

# Non-m1 records that are intentionally defined in DADAOInstrInfo.td:
#   - scope:m3  -> M3 CodeGen instructions (ADR-0012 D9.1); LLVM-only, not M1.
#   - scope:m8  -> new ISA instructions (ADR-0012 D10 / SPEC-142t).
#   - scope:m9  -> `rol` (ADR-0032 D4 as amended 2026-10-19 / LLVM-116t).
#   - scope:excluded -> still needed by the MC layer (assemble/disassemble) even
#     though execution traps with ILLI.
#     LLVM-060t defined the four privileged cfx instructions (crrr/ciii) while
#     they were scope:excluded; SPEC-115t re-scoped them to m1, so they are no
#     longer in this allow-list and now satisfy the M1 baseline check directly.
MC_ONLY_EXCLUDED_IDS = frozenset({
    # ftfma/fofma (SPEC-158t): 已由 `excluded` 转入 `fp`，由 FP 覆盖检查
    # （66/66）承接，不再列入本 allow-list。
    # clmul.o (ADR-0035 D7 / LLVM-122t): encoding and semantics are fixed, the
    # execution side is QEMU-068t, but the record stays scope:excluded until the
    # SPEC-155t flip; the MC layer assembles/disassembles it (and CodeGen
    # selects it through the CLMUL_*_PSEUDO pseudos).
    "clmul.o_rrrr_rd",
    # lr/sc (ADR-0034 D3-D5; LLVM-121t): 24 scope:excluded records that the MC
    # layer assembles/disassembles and that CodeGen selects for the atomic
    # CAS/RMW loops.  List generated from the width x ordering sets of D3/D4
    # (lr: nn/an/ar, sc: nn/nr/ar) -- count derived in the script's output.
    "lr.b.nn_orrr_rd",
    "lr.b.an_orrr_rd",
    "lr.b.ar_orrr_rd",
    "sc.b.nn_orrr_rd",
    "sc.b.nr_orrr_rd",
    "sc.b.ar_orrr_rd",
    "lr.w.nn_orrr_rd",
    "lr.w.an_orrr_rd",
    "lr.w.ar_orrr_rd",
    "sc.w.nn_orrr_rd",
    "sc.w.nr_orrr_rd",
    "sc.w.ar_orrr_rd",
    "lr.t.nn_orrr_rd",
    "lr.t.an_orrr_rd",
    "lr.t.ar_orrr_rd",
    "sc.t.nn_orrr_rd",
    "sc.t.nr_orrr_rd",
    "sc.t.ar_orrr_rd",
    "lr.o.nn_orrr_rd",
    "lr.o.an_orrr_rd",
    "lr.o.ar_orrr_rd",
    "sc.o.nn_orrr_rd",
    "sc.o.nr_orrr_rd",
    "sc.o.ar_orrr_rd",
})


# Instruction def header: `def NAME : DADAO<class><"mnemonic"> {`.
# 体按**整行 `}`** 收尾（不用 `[^}]*`：def 体注释里会出现 `{rfN}` 之类的花括号，
# 例如 FP `ft2fo` 的 earlyclobber 注释——用 `[^}]*` 会把体截断、丢掉 `let op`，
# 导致该记录被误判为「无 def」（ISS-320 实测）。
DEF_HDR = re.compile(r'^def (\w+) : (DADAO\w+)<([^>]+)>\s*\{')


def parse_patch(td_patch_text: str) -> str:
    """Reconstruct a new-file patch's added content (strip diff header)."""
    lines = td_patch_text.splitlines()
    out = []
    started = False
    for line in lines:
        if not started:
            if line.startswith("@@"):
                started = True
            continue
        # New-file hunks: content lines start with '+'.  Accept context lines
        # (' ') too for robustness.
        if line.startswith("+"):
            out.append(line[1:])
        elif line.startswith(" "):
            out.append(line[1:])
    return "\n".join(out) + "\n"


def load_td_sources(td_arg: str | None) -> list[tuple[str, str]]:
    """Return [(td_text, source_label), ...].

    --td 给定时以该纯 `.td` 为主文件；其**另一半真源**（FP `.td`）仍从提交补丁
    取（除非被覆盖的就是 FP 文件本身）——否则 FP 覆盖断言会因缺文件而假红。
    默认校验全部 `DADAOInstrInfo*.td.patch`（含 FP `.td`，ISS-320）。
    """
    if td_arg:
        p = Path(td_arg)
        sources = [(p.read_text(), str(p))]
        fp_patches = [q for q in sorted(TD_PATCH_DIR.glob(TD_PATCH_GLOB))
                      if "InstrInfoFP" in q.name]
        if "InstrInfoFP" not in p.name:
            sources += [(parse_patch(q.read_text()), str(q)) for q in fp_patches]
        return sources
    patches = sorted(TD_PATCH_DIR.glob(TD_PATCH_GLOB))
    if not patches:
        raise SystemExit(f"ERROR: 未找到任何 {TD_PATCH_DIR / TD_PATCH_GLOB}")
    return [(parse_patch(p.read_text()), str(p)) for p in patches]


def parse_td_defs(td_text: str) -> list[dict]:
    """Parse instruction defs line-wise: header line then body up to a lone `}`."""
    defs = []
    lines = td_text.split("\n")
    i = 0
    while i < len(lines):
        m = DEF_HDR.match(lines[i])
        if not m:
            i += 1
            continue
        name, classname, params = m.groups()
        body_lines = []
        i += 1
        while i < len(lines) and lines[i].strip() != "}":
            body_lines.append(lines[i])
            i += 1
        i += 1
        fmt = FMT_BY_CLASS.get(classname)
        if fmt is None:
            continue  # operand / asm-operand-class defs
        body = "\n".join(body_lines)
        mn = re.search(r'"([^"]+)"', params)
        op = re.search(r'let op = (0x[0-9A-Fa-f]+)', body)
        ha = re.search(r'let ha = (0x[0-9A-Fa-f]+)', body)
        defs.append({
            "name": name,
            "format": fmt,
            "mnemonic": mn.group(1) if mn else None,
            "op": op.group(1).lower() if op else None,
            "ha": ha.group(1).lower() if ha else None,
        })
    return defs


def join_key(mnemonic: str | None, fmt: str | None,
             op: str | None, ha: str | None) -> tuple:
    """Explicit join key between opcodes.yaml records and .td defs."""
    return (mnemonic, fmt, (op or "").lower(), (ha or "").lower() or None)


def rec_key(rec: dict) -> tuple:
    return join_key(rec.get("mnemonic"), rec.get("format"),
                    rec.get("opc"), rec.get("ha"))


def def_key(d: dict) -> tuple:
    return join_key(d.get("mnemonic"), d.get("format"), d.get("op"),
                    d.get("ha"))


def index_by_key(items, keyfn) -> tuple[dict, list]:
    idx: dict[tuple, list] = defaultdict(list)
    for it in items:
        idx[keyfn(it)].append(it)
    dups = {k: v for k, v in idx.items() if len(v) > 1}
    return idx, dups


def build_id_to_def(defs: list[dict], rec_idx: dict) -> dict:
    """Explicit opcodes.yaml id -> .td def-name mapping (resolved by join key)."""
    mapping = {}
    for d in defs:
        hits = rec_idx.get(def_key(d), [])
        if len(hits) == 1:
            mapping[hits[0]["id"]] = d["name"]
    return mapping


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--opcodes", default=str(OPCODES_DEFAULT),
                    help="path to opcodes.yaml (default: contracts/opcodes.yaml)")
    ap.add_argument("--td", default=None,
                    help="path to a plain .td file (default: reconstruct from the "
                         "committed DADAOInstrInfo.td.patch)")
    ap.add_argument("--dump-map", action="store_true",
                    help="print the resolved id -> def-name mapping")
    ap.add_argument("--self-test", action="store_true",
                    help="also assert the documented sample id -> def-name mappings")
    args = ap.parse_args(argv)

    with open(args.opcodes) as f:
        records = yaml.safe_load(f)
    if not isinstance(records, list):
        print(f"FAIL: {args.opcodes}: 顶层必须是列表", file=sys.stderr)
        return 1

    td_sources = load_td_sources(args.td)
    defs = [d for text, _label in td_sources for d in parse_td_defs(text)]

    m1 = [r for r in records if r.get("scope") == "m1"]
    fp = [r for r in records if r.get("scope") == "fp"]
    m3 = [r for r in records if r.get("scope") == "m3"]
    m8 = [r for r in records if r.get("scope") == "m8"]
    m9 = [r for r in records if r.get("scope") == "m9"]

    print("=== Validation: DADAOInstrInfo.td vs contracts/opcodes.yaml ===")
    print(f"opcodes.yaml     : {args.opcodes}")
    print("instruction defs :")
    for text, label in td_sources:
        print(f"  - {label}  ({len(parse_td_defs(text))} defs)")
    print(f"records total    : {len(records)}")
    print(f"M1 records       : {len(m1)}  (baseline derived from opcodes.yaml)")
    print(f"FP records       : {len(fp)}  (ISS-320)")
    print(f"M3 records       : {len(m3)}")
    print(f"M8 records       : {len(m8)}")
    print(f"M9 records       : {len(m9)}")
    print(f".td instr defs   : {len(defs)}")
    print()

    errors: list[str] = []

    rec_idx, rec_dups = index_by_key(records, rec_key)
    def_idx, def_dups = index_by_key(defs, def_key)

    # Check 4: unambiguous mapping (unique join keys on both sides).
    if rec_dups:
        for k, v in rec_dups.items():
            errors.append(f"opcodes.yaml join key 非唯一 {k}: "
                          f"{[r['id'] for r in v]}")
    if def_dups:
        for k, v in def_dups.items():
            errors.append(f".td join key 非唯一 {k}: "
                          f"{[d['name'] for d in v]}")
    if rec_dups or def_dups:
        print("FAIL: mapping — join key 非唯一（见上）")
    else:
        print("PASS: mapping — join key (mnemonic, format, op, ha) 在两侧均唯一")

    # Check 1: baseline — every M1 record has exactly one matching def.
    matched_m1 = 0
    for r in m1:
        hits = def_idx.get(rec_key(r), [])
        if len(hits) != 1:
            errors.append(f"M1 记录 {r['id']} 的 .td def 数 = {len(hits)}"
                          f"（期望 1；key={rec_key(r)}）")
        else:
            matched_m1 += 1
    if matched_m1 == len(m1):
        print(f"PASS: baseline — {len(m1)}/{len(m1)} 条 M1 记录各有唯一 .td def")
    else:
        print(f"FAIL: baseline — {matched_m1}/{len(m1)} 条 M1 记录匹配到 .td def")

    # Check 1b: every FP record has exactly one matching def (ISS-320).
    matched_fp = 0
    for r in fp:
        hits = def_idx.get(rec_key(r), [])
        if len(hits) != 1:
            errors.append(f"FP 记录 {r['id']} 的 .td def 数 = {len(hits)}"
                          f"（期望 1；key={rec_key(r)}）")
        else:
            matched_fp += 1
    if matched_fp == len(fp):
        print(f"PASS: coverage — {len(fp)}/{len(fp)} 条 FP 记录各有唯一 .td def")
    else:
        print(f"FAIL: coverage — {matched_fp}/{len(fp)} 条 FP 记录匹配到 .td def")

    # Check 2: every M3 record has exactly one matching def.
    matched_m3 = 0
    for r in m3:
        hits = def_idx.get(rec_key(r), [])
        if len(hits) != 1:
            errors.append(f"M3 记录 {r['id']} 的 .td def 数 = {len(hits)}（期望 1）")
        else:
            matched_m3 += 1
    if matched_m3 == len(m3):
        print(f"PASS: coverage — {len(m3)}/{len(m3)} 条 M3 记录各有唯一 .td def")
    else:
        print(f"FAIL: coverage — {matched_m3}/{len(m3)} 条 M3 记录匹配到 .td def")

    # Check 2b: every M8 record (new ISA instructions, ADR-0012 D10) has exactly
    # one matching def — they are MC-layer instructions (SPEC-142t phase B).
    matched_m8 = 0
    for r in m8:
        hits = def_idx.get(rec_key(r), [])
        if len(hits) != 1:
            errors.append(f"M8 记录 {r['id']} 的 .td def 数 = {len(hits)}（期望 1）")
        else:
            matched_m8 += 1
    if matched_m8 == len(m8):
        print(f"PASS: coverage — {len(m8)}/{len(m8)} 条 M8 记录各有唯一 .td def")
    else:
        print(f"FAIL: coverage — {matched_m8}/{len(m8)} 条 M8 记录匹配到 .td def")

    # Check 2c: every M9 record (`rol`, ADR-0032 D4 as amended) has exactly one matching def.
    matched_m9 = 0
    for r in m9:
        hits = def_idx.get(rec_key(r), [])
        if len(hits) != 1:
            errors.append(f"M9 记录 {r['id']} 的 .td def 数 = {len(hits)}（期望 1）")
        else:
            matched_m9 += 1
    if matched_m9 == len(m9):
        print(f"PASS: coverage — {len(m9)}/{len(m9)} 条 M9 记录各有唯一 .td def")
    else:
        print(f"FAIL: coverage — {matched_m9}/{len(m9)} 条 M9 记录匹配到 .td def")

    # Check 3: no orphans — every def maps to exactly one record.
    orphan = 0
    non_m1_defs = []
    for d in defs:
        hits = rec_idx.get(def_key(d), [])
        if len(hits) != 1:
            errors.append(f".td def {d['name']} 无唯一 opcodes 记录"
                          f"（命中 {len(hits)}；key={def_key(d)}）")
            orphan += 1
            continue
        if hits[0].get("scope") not in ("m1", "fp"):
            non_m1_defs.append((d["name"], hits[0]["id"], hits[0].get("scope")))
    if orphan == 0:
        print(f"PASS: orphan — 全部 {len(defs)} 个 .td def 各有唯一 opcodes 记录")
    else:
        print(f"FAIL: orphan — {orphan} 个 .td def 未匹配到唯一记录")

    # Check 5: non-m1/fp（M1 与 FP 走 baseline 覆盖）defs limited to allow-list.
    bad_non_m1 = []
    for name, rid, scope in non_m1_defs:
        if scope in ("m3", "m8", "m9"):
            continue
        if scope == "excluded" and rid in MC_ONLY_EXCLUDED_IDS:
            continue
        bad_non_m1.append((name, rid, scope))
    missing_mc_only = [rid for rid in MC_ONLY_EXCLUDED_IDS
                       if rid not in {r for _, r, _ in non_m1_defs}]
    if not bad_non_m1 and not missing_mc_only:
        print(f"PASS: non-m1 — {len(non_m1_defs)} 个非 m1 def 均在 allow-list"
              f"（{[(n, s) for n, _, s in non_m1_defs]}）")
    else:
        for name, rid, scope in bad_non_m1:
            errors.append(f".td def {name} 属 scope:{scope}（id={rid}），不在 allow-list")
        for rid in missing_mc_only:
            errors.append(f"allow-list 中的 MC-only excluded 记录 {rid} 未在 .td 中定义")
        print("FAIL: non-m1 — 非 m1 def 超出 allow-list（见上）")

    # Check 6: formats used by m1 defs == formats present in scope:m1.
    m1_def_fmts = set()
    rec_fmt_by_key = {rec_key(r): r.get("format") for r in m1}
    for d in defs:
        if def_key(d) in rec_fmt_by_key:
            m1_def_fmts.add(d["format"])
    m1_rec_fmts = {r.get("format") for r in m1}
    if m1_def_fmts == m1_rec_fmts:
        print(f"PASS: format — m1 def 格式类集合 == M1 记录格式集合: {sorted(m1_rec_fmts)}")
    else:
        errors.append(f"format 集合不一致: def={sorted(m1_def_fmts)} "
                      f"record={sorted(m1_rec_fmts)}")
        print("FAIL: format — 格式类集合不一致（见上）")

    # Check 6b: formats used by fp defs == formats present in scope:fp (ISS-320).
    fp_rec_fmts = {r.get("format") for r in fp}
    fp_def_fmts = {d["format"] for d in defs if def_key(d) in {rec_key(r) for r in fp}}
    if fp_def_fmts == fp_rec_fmts:
        print(f"PASS: format — fp def 格式类集合 == FP 记录格式集合: {sorted(fp_rec_fmts)}")
    else:
        errors.append(f"fp format 集合不一致: def={sorted(fp_def_fmts)} "
                      f"record={sorted(fp_rec_fmts)}")
        print("FAIL: format — fp 格式类集合不一致（见上）")

    id_to_def = build_id_to_def(defs, rec_idx)

    if args.self_test:
        # Derived, never hardcoded: an earlier literal table went stale twice
        # (`shl.u*` -> `shl.*`, then `ror` -> `rol`) and turned a rename into a
        # mysterious self-test failure.  Everything below is recomputed from
        # opcodes.yaml + the committed .td on every run (counts printed live).
        print("\n=== self-test: derived id -> def-name mapping ===")
        checked = [r for r in records
                   if r.get("scope") in ("m1", "fp", "m3", "m8", "m9")]
        def_by_name = {d["name"]: d for d in defs}
        covered = sum(1 for r in checked if r["id"] in id_to_def)
        if covered == len(checked):
            print(f"PASS self-test: coverage {covered}/{len(checked)} "
                  f"(m1+fp+m3+m8+m9, derived)")
        else:
            missing = [r["id"] for r in checked if r["id"] not in id_to_def]
            errors.append(f"self-test coverage {covered}/{len(checked)}: {missing[:5]}")
            print(f"FAIL self-test: coverage {covered}/{len(checked)}")

        # Structural check: the mapped def's join key must equal the record's.
        key_bad = []
        for r in checked:
            name = id_to_def.get(r["id"])
            d = def_by_name.get(name) if name else None
            if d is None or def_key(d) != rec_key(r):
                key_bad.append((r["id"], name))
        if not key_bad:
            print(f"PASS self-test: join key matches for all {len(checked)} records")
        else:
            errors.append(f"self-test join-key mismatch: {key_bad[:5]}")
            print(f"FAIL self-test: join-key mismatch {key_bad[:5]}")

        # Derivable subset (live): where the .td uses the conventional
        # `<mnemonic>_<format>` def name, the mapping must point exactly there.
        derivable = []
        for r in checked:
            natural = (r["mnemonic"] + "_" + r["format"]).replace(".", "_").replace("-", "_")
            if natural in def_by_name:
                derivable.append((r["id"], natural))
                if id_to_def.get(r["id"]) != natural:
                    errors.append(f"self-test derived name {r['id']}: "
                                  f"expected {natural}, got {id_to_def.get(r['id'])}")
        if derivable and not any("derived name" in e for e in errors):
            print(f"PASS self-test: {len(derivable)} derivable `<mnemonic>_<format>` "
                  f"def names all map exactly (e.g. {derivable[:3]})")
        if not derivable:
            errors.append("self-test derivable-name subset is empty (vacuous)")
            print("FAIL self-test: derivable-name subset is empty")

    if args.dump_map:
        print("\n=== id -> def-name mapping ===")
        for rid in sorted(id_to_def):
            print(f"{rid} -> {id_to_def[rid]}")

    print(f"\n=== Result: {len(errors)} errors ===")
    for e in errors:
        print(f"  ERROR: {e}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
