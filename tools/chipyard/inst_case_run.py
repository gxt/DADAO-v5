#!/usr/bin/env python3
"""Drive a `tests/inst` vector file on the chipyard `WumingTinyConfig` core.

The vector YAML is the independent oracle: every case carries its own
`input_state` and `expected_state`, and the expected bytes are taken from the
YAML, never from QEMU or from the RTL.

For each case the tool builds one image:

    [trampoline] set.zw/jump to CODE
    [CODE]       asm prelude (stack pointer, request buffer)
                 input_state: rd/rb/rf constants, 8-byte memory words
                 the case's `sequence` words
                 dump every register the case's `expected_state` names
                 SYS_WRITEC the dumped bytes, SYS_EXIT 0

so the bytes the guest prints *are* the comparison: the same image is run on
the chipyard harness (`+loadmem=`) and on QEMU (`-kernel <raw>`), and both are
compared with the YAML expectation.  Fault cases become the usual
`PRE\n`/`POST\n` marker image: a core that treated the encoding as a NOP would
reach `POST` and exit 0.

Usage:
    inst_case_run.py list VECTOR.yaml [...]
    inst_case_run.py emit OUTDIR VECTOR.yaml [...]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "chipyard"))
sys.path.insert(0, str(ROOT / "tools" / "infra"))

import fp_sweep as S  # noqa: E402
import inst_sweep as sweep  # noqa: E402

ENTRY = sweep.ENTRY
CODE = S.CODE
IMAGE_LIMIT = S.IMAGE_LIMIT

# The fault classes `excp cause` prints as one-hot bits (spec/Machine-v5 §4.4).
FAULT_BITS = {"CFXMEM": 1, "CFXREG": 2, "ILLI": 8, "UNDI": 9,
              "RASOF": 10, "RASUF": 11, "MALIGN": 12, "IALIGN": 13}


def as_int(v):
    if isinstance(v, int):
        return v
    return int(str(v), 0)


def resolve_addr(v):
    """`@ENTRY+0x100000` / `@ENTRY` / a plain number."""
    if isinstance(v, int):
        return v
    s = str(v)
    m = re.fullmatch(r"@ENTRY([+-])(0x[0-9a-fA-F]+|\d+)", s)
    if m:
        off = int(m.group(2), 0)
        return ENTRY + off if m.group(1) == "+" else ENTRY - off
    if s == "@ENTRY":
        return ENTRY
    return int(s, 0)


def load_cases(paths):
    out = []
    for p in paths:
        for i, case in enumerate(yaml.safe_load(Path(p).read_text())):
            out.append({"file": Path(p).name, "index": i, "case": case})
    return out


DUMP_ORDER = ("rd", "rb", "rf", "memory")


def setup_words(inp):
    words = []
    for bank in ("rd", "rb"):
        for name, val in sorted((inp.get(bank) or {}).items()):
            idx = int(name[2:])
            v = as_int(val) if not str(val).startswith("@") else resolve_addr(val)
            words += (sweep.load_rd if bank == "rd" else sweep.load_rb)(idx, v)
    for name, val in sorted((inp.get("rf") or {}).items()):
        words += S.load_rf(int(name[2:]), as_int(val))
    for mem in inp.get("memory") or []:
        words += S.store_word(resolve_addr(mem["address"]), as_int(mem["value"]))
    return words


def dump_rb(num):
    """No rb -> rd move instruction is needed: `sub.o` dbb writes rd = rb - 0."""
    return [sweep.enc_sub_o_dbb(sweep.TMP_RD, num, sweep.ZERO_RB)] + \
        S.dump_rd(sweep.TMP_RD)


def dump_words(state):
    """Dump the registers/memory named in `expected_state`, in a fixed order."""
    words = []
    wants = []
    for key in DUMP_ORDER:
        entries = state.get(key)
        if not entries:
            continue
        for name, val in sorted(entries.items()):
            if key == "memory":
                words += S.dump_mem_word(resolve_addr(name))
            elif key == "rf":
                words += S.dump_rf(int(name[2:]))
            elif key == "rd":
                words += S.dump_rd(int(name[2:]))
            else:
                words += dump_rb(int(name[2:]))
            wants.append(as_int(val))
    return words, wants


def build_case(case):
    """Words + expected bytes for one semantic case."""
    words = [(0x71 << 24) | ((CODE - ENTRY) >> 2)]
    words += [0] * (((CODE - ENTRY) >> 2) - len(words))
    words += S.asm_prelude()
    words += sweep.load_rb(S.WR_PTR, S.BUF)
    words += setup_words(case.get("input_state") or {})
    for w in case.get("sequence") or [case["encoding"]["word"]]:
        words.append(as_int(w))
    dwords, wants = dump_words(case.get("expected_state") or {})
    words += dwords
    expected = bytearray()
    for v in wants:
        expected += (v & ((1 << 64) - 1)).to_bytes(8, "big")
    if len(words) * 4 > IMAGE_LIMIT:
        raise SystemExit(f"inst_case_run: image too large ({len(words) * 4} B)")
    words += S.asm_print_buffer(len(expected))
    words += S.asm_sys_exit(0)
    return words, bytes(expected)


def build_fault(case):
    words = S.asm_prelude()
    words += sweep.asm_write0(ENTRY + 0x400)
    words += setup_words(case.get("input_state") or {})
    words.append(as_int(case["encoding"]["word"]))
    words += sweep.asm_write0(ENTRY + 0x408)
    words += S.asm_sys_exit(0)
    if len(words) * 4 > 0x400:
        raise SystemExit("inst_case_run: fault program does not fit below 0x400")
    words += [0] * ((0x400 - len(words) * 4) // 4)
    words += [0x5052450A, 0x00000000, 0x504F5354, 0x0A000000]  # "PRE\n\0POST\n\0"
    return words


def cmd_list(args):
    total = sem = fault = 0
    for entry in load_cases(args.vectors):
        c = entry["case"]
        total += 1
        if c.get("expected_fault"):
            fault += 1
        else:
            sem += 1
        print(f"{entry['file']}:{entry['index']} {c.get('id')} "
              f"{c.get('class')} fault={c.get('expected_fault')}")
    print(f"cases={total} semantic={sem} fault={fault}")
    return 0


def cmd_emit(args):
    outdir = Path(args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    tb = sweep.toolchain_bin(args.toolchain_bin)
    manifest = []
    for entry in load_cases(args.vectors):
        c = entry["case"]
        stem = f"{Path(entry['file']).stem}_{entry['index']}"
        if c.get("expected_fault"):
            words = build_fault(c)
            elf, raw = sweep.assemble(words, outdir, stem, tb)
            manifest.append({"case": stem, "id": c.get("id"), "fault":
                             c["expected_fault"],
                             "cause": 1 << FAULT_BITS[c["expected_fault"]],
                             "elves": [elf.name], "raws": [raw.name],
                             "expect": [], "bytes": 0})
            continue
        words, expected = build_case(c)
        elf, raw = sweep.assemble(words, outdir, stem, tb)
        (outdir / f"{stem}_expect.bin").write_bytes(expected)
        manifest.append({"case": stem, "id": c.get("id"), "fault": None,
                         "elves": [elf.name], "raws": [raw.name],
                         "expect": [f"{stem}_expect.bin"],
                         "bytes": len(expected),
                         "notes": c.get("notes")})
    (outdir / "cases.json").write_text(json.dumps(manifest, indent=1) + "\n")
    n_sem = sum(1 for m in manifest if not m["fault"])
    print(f"emit: outdir={outdir} semantic={n_sem} "
          f"fault={len(manifest) - n_sem} bytes={sum(m['bytes'] for m in manifest)}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list")
    p.add_argument("vectors", nargs="+")
    p.set_defaults(fn=cmd_list)
    p = sub.add_parser("emit")
    p.add_argument("outdir")
    p.add_argument("vectors", nargs="+")
    p.add_argument("--toolchain-bin", default=None)
    p.set_defaults(fn=cmd_emit)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
