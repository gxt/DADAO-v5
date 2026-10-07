#!/usr/bin/env python3
"""Validate the committed DADAO LLVM instruction defs against opcodes.yaml.

真源（sources of truth，二者均为真源，脚本只做交叉校验）:
  - contracts/opcodes.yaml
      —— 编码真源（由 tools/spec/generate_opcodes.py 从 spec/ 生成）。
  - components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOInstrInfo.td.patch
      —— 实际被 LLVM 编译的指令定义（DADAOInstrInfo.td）真源。默认即校验此
         提交物（仓库内、无需 .work/source 检出，故可作为 make check 门控）；
         也可用 --td 指向任意 .td 文件（例如 .work/source 下的工作副本）。

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
  2. coverage：每条 scope:m3 记录（M3 CodeGen 指令）也须有匹配的 .td def。
  3. no orphan：每个 .td def 恰映射到一条 opcodes.yaml 记录
     （可捕获凭空编码与注入的 mnemonic/op 漂移）。
  4. mapping：join key 在两侧均唯一（无歧义映射）。
  5. non-m1 policy：.td 中的非 m1 def 仅限显式 allow-list
     （scope:m3，以及 MC 层仍需的个别 scope:excluded，如 fence）。
  6. format：.td 中 m1 def 用到的格式类集合 == scope:m1 记录的格式集合。

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
TD_PATCH_DEFAULT = (
    REPO / "components" / "llvm-project" / "patches" / "llvm" / "lib"
    / "Target" / "DADAO" / "DADAOInstrInfo.td.patch"
)

# TableGen format class -> opcodes.yaml `format` string.
FMT_BY_CLASS = {
    "DADAORrrr": "rrrr", "DADAORrri": "rrri", "DADAORrii": "rrii",
    "DADAORiii": "riii", "DADAOIiii": "iiii", "DADAORwii": "rwii",
    "DADAOOrrr": "orrr", "DADAOOrri": "orri", "DADAOOiii": "oiii",
    # Privileged cfx formats (LLVM-060t): MC-only .td defs (scope: excluded).
    "DADAOCrrr": "crrr", "DADAOCiii": "ciii",
}

# Non-m1 records that are intentionally defined in DADAOInstrInfo.td:
#   - scope:m3  -> M3 CodeGen instructions (ADR-0012 D9.1); LLVM-only, not M1.
#   - scope:excluded -> still needed by the MC layer (assemble/disassemble) even
#     though execution traps with ILLI.  SPEC-039t moved `fence` out of M1 but
#     kept its def so llvm-mc can assemble it (see tests/llvm/lit/MC/DADAO/oiii.s).
#     LLVM-060t likewise defines the four privileged cfx instructions
#     (crrr/ciii) while they are still scope:excluded; SPEC-115t re-scopes them
#     to m1 and removes them from this allow-list.
MC_ONLY_EXCLUDED_IDS = frozenset({
    "fence_oiii_imm",
    "trap_ciii_cfx",
    "escape_ciii_cfx",
    "cfx2rc_crrr_cfx",
    "cfx2rd_crrr_cfx",
})

# Documented sample of the explicit id -> .td def-name mapping, checked by
# --self-test (the legacy names are not derivable from the id, so we assert a
# few known correspondences against the actual joined data).
SAMPLE_MAPPINGS = {
    "ld.ub_rrii_rd": "ld_ub_rd",
    "add.si_riii_rd": "add_si_rd",
    "sub.o_orrr_dbb": "sub_o_dbb",
    "rb2rb_orri_rb": "rb2rb",
    "fence_oiii_imm": "fence",
}

# Instruction def: `def NAME : DADAO<class><"mnemonic"> { ... }`.
DEF_PATTERN = re.compile(
    r'^def (\w+) : (DADAO\w+)<([^>]+)>\s*\{([^}]*)\}',
    re.MULTILINE | re.DOTALL,
)


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


def load_td_text(td_arg: str | None) -> tuple[str, str]:
    """Return (td_text, source_label)."""
    if td_arg:
        p = Path(td_arg)
        return p.read_text(), str(p)
    return parse_patch(TD_PATCH_DEFAULT.read_text()), str(TD_PATCH_DEFAULT)


def parse_td_defs(td_text: str) -> list[dict]:
    """Parse instruction defs: def NAME : DADAO...<"mnemonic"> { ... }."""
    defs = []
    for m in DEF_PATTERN.finditer(td_text):
        name, classname, params, body = m.groups()
        fmt = FMT_BY_CLASS.get(classname)
        if fmt is None:
            continue  # operand / asm-operand-class defs
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
                    rec.get("op"), rec.get("ha"))


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

    td_text, td_label = load_td_text(args.td)
    defs = parse_td_defs(td_text)

    m1 = [r for r in records if r.get("scope") == "m1"]
    m3 = [r for r in records if r.get("scope") == "m3"]

    print("=== Validation: DADAOInstrInfo.td vs contracts/opcodes.yaml ===")
    print(f"opcodes.yaml     : {args.opcodes}")
    print(f"instruction defs : {td_label}")
    print(f"records total    : {len(records)}")
    print(f"M1 records       : {len(m1)}  (baseline derived from opcodes.yaml)")
    print(f"M3 records       : {len(m3)}")
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
        if hits[0].get("scope") != "m1":
            non_m1_defs.append((d["name"], hits[0]["id"], hits[0].get("scope")))
    if orphan == 0:
        print(f"PASS: orphan — 全部 {len(defs)} 个 .td def 各有唯一 opcodes 记录")
    else:
        print(f"FAIL: orphan — {orphan} 个 .td def 未匹配到唯一记录")

    # Check 5: non-m1 defs limited to the declared allow-list.
    bad_non_m1 = []
    for name, rid, scope in non_m1_defs:
        if scope == "m3":
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

    id_to_def = build_id_to_def(defs, rec_idx)

    if args.self_test:
        print("\n=== self-test: explicit id -> def-name mapping ===")
        for rid, expected in SAMPLE_MAPPINGS.items():
            actual = id_to_def.get(rid)
            if actual == expected:
                print(f"PASS self-test: {rid} -> {actual}")
            else:
                errors.append(f"self-test mapping {rid}: 期望 {expected}，实际 {actual}")
                print(f"FAIL self-test: {rid} -> {actual}（期望 {expected}）")

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
