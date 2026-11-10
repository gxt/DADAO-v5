#!/usr/bin/env python3
"""m12-chipyard-008 memory sweep: `tests/inst` load/store vectors on the core.

The vector YAML in ``tests/inst/base/mem-{rd,rb,ra}.yaml`` is the independent
oracle (``spec/SimRISC-01``): each case carries its own expected register and
memory state.  This tool turns every case into DADAO assembly, links it into a
``+loadmem=`` ELF image for the chipyard ``WumingTinyConfig`` harness, and
writes the expected result bytes so the core output can be compared
byte-exactly.  The QEMU ``dadao-tiny`` harness
(``tools/testcases/lib/run_qemu_test.py``) runs the same vectors, so "same as
QEMU" means "both match the shared expectation".

Subcommands
-----------
``list``
    Print every covered case and the live counts (recomputed from the YAML).

``emit OUTDIR``
    Emit and assemble/link, into ``OUTDIR``:

      * ``mem_sweep.elf`` / ``.raw`` / ``mem_expect.bin`` / ``mem.json``
        one straight-line program covering every non-fault case.  The result
        bytes are the expected register values (rd/rb/ra, dumped in manifest
        order) followed by the expected memory words (read back with an
        unsigned load of the case's access width);
      * ``memfault_<key>.elf`` / ``.raw`` + ``mem_faults.json``
        one small program per fault case: it prints ``PRE``, executes the
        faulting encoding and prints ``POST``.  The hmon handler skips the
        instruction (``escape ... +4``), so POST is reached and the run exits
        0; the core trace carries the ``excp cause=...`` line that identifies
        the raised fault;
      * ``residue.elf`` / ``residue_expect.bin``
        precise-fault probe: MALIGN and CFXMEM loads/stores must leave the
        destination register and the target memory untouched;
      * ``endian.elf`` / ``endian_expect.bin``
        byte-order probe: every store width is read back byte by byte and
        every load width is checked for the correct zero/sign extension;
      * ``semisemi.elf`` / ``semisemi_expect.bin``
        semihosting end-to-end probe: the guest fills and then *copies* a
        1280-byte buffer with ld.o/st.o and hands the copy to ``SYS_WRITE0``.

Layout (all inside the Tiny SRAM window): ``ENTRY`` holds a one-word
``jump rb0, rd0, +0x1000`` trampoline, the program body lives at
``ENTRY+0x1000``, so the vectors can name ``@ENTRY`` as a data address and a
store case may clobber the trampoline without breaking the run.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "chipyard"))
sys.path.insert(0, str(ROOT / "tools" / "infra"))
sys.path.insert(0, str(ROOT / "tools" / "testcases" / "lib"))

import yaml  # noqa: E402

import inst_sweep as sweep  # noqa: E402
import machine_profile  # noqa: E402

PROFILE = machine_profile.load("tiny")
ENTRY = sweep.ENTRY
BUF = sweep.BUF
EXITBLOCK = sweep.EXITBLOCK
CODE = ENTRY + 0x1000
DUMP = ENTRY + 0x7800
SEMIHOST_TAG = sweep.SEMIHOST_TAG
SYS_WRITE0 = sweep.SYS_WRITE0
SYS_EXIT = sweep.SYS_EXIT

MEM_FILES = (
    "tests/inst/base/mem-rd.yaml",
    "tests/inst/base/mem-rb.yaml",
    "tests/inst/base/mem-ra.yaml",
)

# Shared scratch registers (same set the m12-005 sweep reserves).
WR_PTR = sweep.WR_PTR
ZERO_RB = sweep.ZERO_RB
TMP_RD = sweep.TMP_RD
SEMI_RD = sweep.SEMI_RD
TMP_RB = sweep.TMP_RB
TMP2_RD = 15

# contracts/opcodes.yaml opcodes for the memory families.
LD_OPC = {"ub": 0x10, "uw": 0x11, "ut": 0x12, "sb": 0x13, "sw": 0x14, "st": 0x15,
          "o_rd": 0x20, "o_rb": 0x22, "o_ra": 0x24}
ST_OPC = {"b": 0x18, "w": 0x19, "t": 0x1A,
          "o_rd": 0x21, "o_rb": 0x23, "o_ra": 0x25}
LD_U_OPC = {1: 0x10, 2: 0x11, 4: 0x12, 8: 0x20}   # unsigned load by byte width


def as_int(v):
    return sweep.as_int(v)


def enc_mem(opc, reg, rb, off):
    return (opc << 24) | (reg << 18) | (rb << 12) | (off & 0xFFF)


def enc_jump_rrii(rbha, rdhb, imms12):
    """jump rbHA, rdHB, imms12 -> target = rb + rd + (imms12 << 2)."""
    return (0x71 << 24) | (rbha << 18) | (rdhb << 12) | (imms12 & 0xFFF)


def enc_br_nz_rb(rbha, imms18):
    """br.nz rbHA, imms18 -> target = rb0 + (imms18 << 2)."""
    return (0x73 << 24) | (rbha << 18) | (imms18 & 0x3FFFF)


def width_bytes(case):
    """Access width in bytes from the mnemonic (b/w/t/o suffix)."""
    mnemonic = case.get("mnemonic") or ""
    width = mnemonic.split(".")[-1][-1]
    return {"b": 1, "w": 2, "t": 4, "o": 8}[width]


def load_ra(num, value):
    """`ra` has no immediate form: put the value in memory and `ld.o` it."""
    words = sweep.load_rd(TMP_RD, value)
    words += sweep.load_rb(TMP_RB, DUMP)
    words.append(enc_mem(ST_OPC["o_rd"], TMP_RD, TMP_RB, 0))
    words.append(enc_mem(LD_OPC["o_ra"], num, TMP_RB, 0))
    return words


def dump_reg(bank, num):
    """Append the register value to the result buffer (WR_PTR advances)."""
    if bank == "rd":
        words = [enc_mem(ST_OPC["o_rd"], num, WR_PTR, 0)]
    elif bank == "rb":
        # sub.o dbb copies an rb register into rd without a store/load round
        # trip (m12-005 path, independent of the memory unit).
        words = [sweep.enc_sub_o_dbb(15, num, ZERO_RB),
                 enc_mem(ST_OPC["o_rd"], 15, WR_PTR, 0)]
    else:  # ra
        words = [enc_mem(ST_OPC["o_ra"], num, WR_PTR, 0)]
    return words + [sweep.enc_add_si_rb(WR_PTR, 8)]


def dump_mem(addr, nbytes):
    """Read `nbytes` at `addr` with the matching unsigned load and buffer it."""
    words = sweep.load_rb(TMP_RB, addr)
    words.append(enc_mem(LD_U_OPC[nbytes], TMP_RD, TMP_RB, 0))
    words.append(enc_mem(ST_OPC["o_rd"], TMP_RD, WR_PTR, 0))
    return words + [sweep.enc_add_si_rb(WR_PTR, 8)]


def load_inputs(case):
    """Set the input registers and memory entries of one case.

    Memory entries are written with a store of the *case's* access width, like
    the QEMU harness (`build_test_binary.derive_memory_width`): the vector value
    is the datum the instruction is supposed to observe at that address, so for
    a byte access only the low byte belongs in memory.
    """
    words = []
    inp = case.get("input_state") or {}
    for name, val in sorted((inp.get("rd") or {}).items(), key=lambda kv: int(kv[0][2:])):
        words += sweep.load_rd(int(name[2:]), as_int(val))
    for name, val in sorted((inp.get("rb") or {}).items(), key=lambda kv: int(kv[0][2:])):
        words += sweep.load_rb(int(name[2:]), as_int(val))
    for name, val in sorted((inp.get("ra") or {}).items(), key=lambda kv: int(kv[0][2:])):
        words += load_ra(int(name[2:]), as_int(val))
    nbytes = width_bytes(case)
    store_opc = ST_OPC[{1: "b", 2: "w", 4: "t", 8: "o_rd"}[nbytes]]
    for entry in inp.get("memory") or []:
        addr = as_int(entry["address"])
        val = as_int(entry["value"]) & ((1 << (8 * nbytes)) - 1)
        words += sweep.load_rb(TMP_RB, addr)
        words += sweep.load_rd(TMP_RD, val)
        words.append(enc_mem(store_opc, TMP_RD, TMP_RB, 0))
    return words


def check_scratch(cases):
    for case in cases:
        for bank in ("rd", "rb"):
            regs = dict(case.get("input_state", {}).get(bank) or {})
            regs.update((case.get("expected_state") or {}).get(bank) or {})
            for name in regs:
                num = int(name[2:])
                if bank == "rd" and num in (TMP_RD, TMP2_RD, SEMI_RD):
                    raise SystemExit(
                        f"mem_sweep: case {case.get('id')} uses rd{num}, reserved")
                if bank == "rb" and num in (WR_PTR, TMP_RB, ZERO_RB, SEMI_RD):
                    raise SystemExit(
                        f"mem_sweep: case {case.get('id')} uses rb{num}, reserved")


def load_cases():
    out = []
    for rel in MEM_FILES:
        for idx, case in enumerate(yaml.safe_load((ROOT / rel).read_text())):
            out.append({"file": rel, "index": idx, "case": case})
    return out


def build_sweep(cases):
    check_scratch([c["case"] for c in cases])
    # One-word trampoline at ENTRY: jump rb0, rd0, +0x1000 (target = IP + 4*imm).
    words = [enc_jump_rrii(0, 0, (CODE - ENTRY) >> 2)]
    words += [0] * (((CODE - ENTRY) >> 2) - len(words))  # pad up to CODE
    words += sweep.asm_prelude()
    words += sweep.load_rb(WR_PTR, BUF)
    expected = bytearray()
    manifest = []
    for entry in cases:
        case = machine_profile.resolve_case(entry["case"], PROFILE)
        if case.get("expected_fault"):
            continue
        words += load_inputs(case)
        words.append(int(str(case["encoding"]["word"]), 16))
        st = case.get("expected_state") or {}
        regs = []
        for bank in ("rd", "rb", "ra"):
            for name in sorted((st.get(bank) or {}), key=lambda n: int(n[2:])):
                regs.append((bank, int(name[2:])))
        mems = [(as_int(m["address"]), width_bytes(case))
                for m in (st.get("memory") or [])]
        offset = len(expected)
        for bank, num in regs:
            words += dump_reg(bank, num)
            expected += as_int(st[bank][f"{bank}{num}"]).to_bytes(8, "big")
        for addr, nbytes in mems:
            words += dump_mem(addr, nbytes)
            value = None
            for m in st["memory"]:
                if as_int(m["address"]) == addr:
                    value = as_int(m["value"])
            expected += (value & ((1 << (8 * nbytes)) - 1)).to_bytes(8, "big")
        manifest.append({
            "file": entry["file"], "index": entry["index"], "id": case["id"],
            "format": case.get("format"), "class": case["class"],
            "regs": [f"{b}{n}" for b, n in regs],
            "mem": [f"0x{a:x}/{w}" for a, w in mems],
            "offset": offset, "bytes": len(regs) * 8 + len(mems) * 8,
        })
    nbytes = len(expected)
    words += sweep.asm_print_buffer(nbytes)
    words += sweep.asm_sys_exit(0)
    return words, bytes(expected), manifest, nbytes


# ---------------------------------------------------------------------------
# Precise-fault residue probe and byte-order / semihosting probes
# ---------------------------------------------------------------------------
def build_residue():
    """MALIGN/CFXMEM loads and stores must not modify their destination.

    Layout: SENT at ENTRY+0x200 holds 0x1122334455667788.
    rd1 = 0xAAAA, rd2 = 0xBBBB.
      1. st.w rd1, [rb3, 1]  -> MALIGN, memory unchanged
      2. ld.uw rd1, [rb3, 1] -> MALIGN, rd1 unchanged
      3. st.o rd1, [rb4, 0]  -> CFXMEM (rb4 = 0), nothing written
      4. ld.o rd2, [rb4, 0]  -> CFXMEM, rd2 unchanged
    The hmon handler skips each faulting instruction, so the dump follows.
    """
    sent_addr = ENTRY + 0x200
    words = [enc_jump_rrii(0, 0, (CODE - ENTRY) >> 2)]
    words += [0] * (((CODE - ENTRY) >> 2) - len(words))
    words += sweep.asm_prelude()
    words += sweep.load_rb(WR_PTR, BUF)
    words += sweep.load_rb(3, sent_addr)
    words += sweep.load_rb(4, 0)
    words += sweep.load_rd(1, 0x1122334455667788)
    words.append(enc_mem(ST_OPC["o_rd"], 1, 3, 0))     # sentinel
    words += sweep.load_rd(1, 0xAAAA)
    words += sweep.load_rd(2, 0xBBBB)
    words.append(enc_mem(ST_OPC["w"], 1, 3, 1))        # MALIGN store
    words.append(enc_mem(LD_OPC["uw"], 1, 3, 1))       # MALIGN load
    words.append(enc_mem(ST_OPC["o_rd"], 1, 4, 0))     # CFXMEM store
    words.append(enc_mem(LD_OPC["o_rd"], 2, 4, 0))     # CFXMEM load
    words += dump_reg("rd", 1)
    words += dump_reg("rd", 2)
    words += dump_mem(sent_addr, 8)
    words += sweep.asm_print_buffer(24)
    words += sweep.asm_sys_exit(0)
    expected = (0xAAAA).to_bytes(8, "big") + (0xBBBB).to_bytes(8, "big") + \
        (0x1122334455667788).to_bytes(8, "big")
    return words, bytes(expected)


def build_endian():
    """Store/load every width and observe the bytes in address order.

    Data area `D = ENTRY+0x300` (8-byte aligned):
      D+0x00  st.o 0x0123456789ABCDEF        -> 01 23 45 67 89 AB CD EF
      D+0x08  st.o 0 then st.t @+4 DEADBEEF  -> 00 00 00 00 DE AD BE EF
      D+0x10  st.o 0 then st.w @+2 BEEF      -> 00 00 BE EF 00 00 00 00
      D+0x18  st.o 0 then st.b @+7 5A        -> 00 00 00 00 00 00 00 5A
      D+0x20  store 0x80 then ld.ub / ld.sb
      D+0x28  store 0x8000 then ld.uw / ld.sw
      D+0x30  store 0x80000000 then ld.ut / ld.st
      D+0x38  store 0x8000000000000000 then ld.o
    Each observed byte is written to the result buffer as an 8-byte big-endian
    word (the byte value zero-extended); each loaded value is buffered whole.
    """
    D = ENTRY + 0x300
    words = [enc_jump_rrii(0, 0, (CODE - ENTRY) >> 2)]
    words += [0] * (((CODE - ENTRY) >> 2) - len(words))
    words += sweep.asm_prelude()
    words += sweep.load_rb(WR_PTR, BUF)
    words += sweep.load_rb(3, D)

    expected = bytearray()

    def store_octa(off, value):
        nonlocal words
        words += sweep.load_rd(1, value)
        words.append(enc_mem(ST_OPC["o_rd"], 1, 3, off))

    # ---- stores: byte-level layout -------------------------------------
    store_octa(0x00, 0x0123456789ABCDEF)
    store_octa(0x08, 0)
    words += sweep.load_rd(1, 0xDEADBEEF)
    words.append(enc_mem(ST_OPC["t"], 1, 3, 0x0C))
    store_octa(0x10, 0)
    words += sweep.load_rd(1, 0xBEEF)
    words.append(enc_mem(ST_OPC["w"], 1, 3, 0x12))
    store_octa(0x18, 0)
    words += sweep.load_rd(1, 0x5A)
    words.append(enc_mem(ST_OPC["b"], 1, 3, 0x1F))
    layout = (bytes([0x01, 0x23, 0x45, 0x67, 0x89, 0xAB, 0xCD, 0xEF]) +
              bytes([0, 0, 0, 0, 0xDE, 0xAD, 0xBE, 0xEF]) +
              bytes([0, 0, 0xBE, 0xEF, 0, 0, 0, 0]) +
              bytes([0, 0, 0, 0, 0, 0, 0, 0x5A]))
    words, exp = _byte_dump(words, D, layout)
    expected += exp

    # ---- loads: zero vs sign extension of each width's top bit ---------
    # Each probe stores with the *matching* width so the probe value sits at
    # the probed address (an octa store would leave the probe byte at the other
    # end of the big-endian word).
    probes = [
        (0x20, ST_OPC["b"], 0x80, LD_OPC["ub"], 0x0000000000000080),
        (0x20, ST_OPC["b"], 0x80, LD_OPC["sb"], 0xFFFFFFFFFFFFFF80),
        (0x28, ST_OPC["w"], 0x8000, LD_OPC["uw"], 0x0000000000008000),
        (0x28, ST_OPC["w"], 0x8000, LD_OPC["sw"], 0xFFFFFFFFFFFF8000),
        (0x30, ST_OPC["t"], 0x80000000, LD_OPC["ut"], 0x0000000080000000),
        (0x30, ST_OPC["t"], 0x80000000, LD_OPC["st"], 0xFFFFFFFF80000000),
        (0x38, ST_OPC["o_rd"], 0x8000000000000000, LD_OPC["o_rd"], 0x8000000000000000),
    ]
    for off, store_opc, stored, opc, want in probes:
        words += sweep.load_rd(1, stored)
        words.append(enc_mem(store_opc, 1, 3, off))
        words.append(enc_mem(opc, TMP_RD, 3, off))
        words.append(enc_mem(ST_OPC["o_rd"], TMP_RD, WR_PTR, 0))
        words.append(sweep.enc_add_si_rb(WR_PTR, 8))
        expected += want.to_bytes(8, "big")

    nbytes = len(expected)
    words += sweep.asm_print_buffer(nbytes)
    words += sweep.asm_sys_exit(0)
    return words, bytes(expected)


def _byte_dump(words, addr, raw):
    out = bytearray()
    words = list(words)
    for i, value in enumerate(raw):
        words += sweep.load_rb(TMP_RB, addr + i)
        words.append(enc_mem(LD_OPC["ub"], TMP_RD, TMP_RB, 0))
        words.append(enc_mem(ST_OPC["o_rd"], TMP_RD, WR_PTR, 0))
        words.append(sweep.enc_add_si_rb(WR_PTR, 8))
        out += int(value).to_bytes(8, "big")
    return words, bytes(out)


def build_semisemi():
    """Guest fills 1280 bytes, copies them with ld.o/st.o, SYS_WRITE0 the copy."""
    src = ENTRY + 0x10000
    dst = ENTRY + 0x14000
    pattern = 1280
    words = [enc_jump_rrii(0, 0, (CODE - ENTRY) >> 2)]
    words += [0] * (((CODE - ENTRY) >> 2) - len(words))
    words += sweep.asm_prelude()

    # Fill source: 160 stores of the 8-byte pattern "DADAOv5s" (no NUL byte).
    words += sweep.load_rd(5, 0x444144414F763573)  # "DADAOv5s"
    words += sweep.load_rb(20, src)
    words += sweep.load_rb(21, pattern // 8)
    fill_loop = len(words)
    words.append(enc_mem(ST_OPC["o_rd"], 5, 20, 0))
    words.append(sweep.enc_add_si_rb(20, 8))
    words.append(sweep.enc_add_si_rb(21, -1))
    branch_at = len(words)
    words.append(enc_br_nz_rb(21, fill_loop - branch_at))

    # Copy source -> destination with the core's octa load/store path.
    words += sweep.load_rb(20, src)
    words += sweep.load_rb(22, dst)
    words += sweep.load_rb(21, pattern // 8)
    copy_loop = len(words)
    words.append(enc_mem(LD_OPC["o_rd"], 5, 20, 0))
    words.append(enc_mem(ST_OPC["o_rd"], 5, 22, 0))
    words.append(sweep.enc_add_si_rb(20, 8))
    words.append(sweep.enc_add_si_rb(22, 8))
    words.append(sweep.enc_add_si_rb(21, -1))
    branch_at = len(words)
    words.append(enc_br_nz_rb(21, copy_loop - branch_at))

    # Terminate the printed string, hand the copy to SYS_WRITE0.
    words += sweep.load_rb(23, dst + pattern)
    words.append(enc_mem(ST_OPC["b"], 0, 23, 0))     # st.b rd0 writes 0
    words += sweep.asm_write0(dst)
    words += sweep.asm_sys_exit(0)
    block = (0x444144414F763573).to_bytes(8, "big") * (pattern // 8)
    return words, block


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def cmd_list(_args):
    cases = load_cases()
    for entry in cases:
        case = entry["case"]
        print(f"{entry['file']}:{entry['index']}  {case['id']}  {case.get('format')}  "
              f"{case['class']}  fault={case.get('expected_fault')}")
    faults = [c for c in cases if c["case"].get("expected_fault")]
    print(f"covered={len(cases)} semantic_set={len(cases) - len(faults)} "
          f"fault_cases={len(faults)}")
    return 0


def cmd_emit(args):
    outdir = Path(args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    tb = sweep.toolchain_bin(args.toolchain_bin)
    cases = load_cases()

    sem = [c for c in cases if not c["case"].get("expected_fault")]
    words, expected, manifest, nbytes = build_sweep(sem)
    sweep.assemble(words, outdir, "mem_sweep", tb)
    (outdir / "mem_expect.bin").write_bytes(expected)
    (outdir / "mem.json").write_text(json.dumps(
        {"bytes": nbytes, "cases": manifest}, indent=1) + "\n")

    faults = []
    for entry in cases:
        fault = entry["case"].get("expected_fault")
        if fault:
            case = machine_profile.resolve_case(entry["case"], PROFILE)
            faults.append({
                "key": f"{Path(entry['file']).stem}_{entry['index']}",
                "fault": fault,
                "word": case["encoding"]["word"],
                "case": case,
            })
    meta = []
    for f in faults:
        fwords = sweep.build_fault(f["case"], f["word"])
        sweep.assemble(fwords, outdir, f"memfault_{f['key']}", tb)
        meta.append({"key": f["key"], "fault": f["fault"], "word": f["word"],
                     "elf": f"memfault_{f['key']}.elf"})
    (outdir / "mem_faults.json").write_text(json.dumps(meta, indent=1) + "\n")

    rwords, rexpect = build_residue()
    sweep.assemble(rwords, outdir, "residue", tb)
    (outdir / "residue_expect.bin").write_bytes(rexpect)

    ewords, eexpect = build_endian()
    sweep.assemble(ewords, outdir, "endian", tb)
    (outdir / "endian_expect.bin").write_bytes(eexpect)

    swords, sexpect = build_semisemi()
    sweep.assemble(swords, outdir, "semisemi", tb)
    (outdir / "semisemi_expect.bin").write_bytes(sexpect)

    print(f"emit: outdir={outdir}")
    print(f"emit: covered={len(cases)} semantic_set={len(sem)} "
          f"fault_images={len(faults)} dumped_bytes={nbytes}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_list = sub.add_parser("list")
    p_list.set_defaults(func=cmd_list)
    p_emit = sub.add_parser("emit")
    p_emit.add_argument("outdir")
    p_emit.add_argument("--toolchain-bin", default=None)
    p_emit.set_defaults(func=cmd_emit)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
