#!/usr/bin/env python3
"""m12-chipyard-010 sweep: bit manipulation, atomics and the rest of the
integer instruction set, driven from the ``tests/inst`` vector YAMLs.

The vectors are the independent oracle (spec/SimRISC-04 §1.5/§2.2,
spec/SimRISC-08/09/10, spec/SimRISC-11 §5, spec/SimRISC-12, spec/SimRISC-02):
every case carries its own expected architectural state.  This tool turns the
cases into DADAO assembly, links them into ``+loadmem=`` ELF images for the
chipyard ``WumingTinyConfig`` harness and into raw kernels for QEMU
``dadao-tiny`` (same code, same expected bytes), and writes the expected result
bytes so the core, QEMU and the YAML can be compared byte-exactly.

Groups (each emits its own image, so a failure is localised):

``bitops``
    ``bitcnt/bitcnt.yaml`` (ctpop/ctlz/cttz), ``rol/rol.yaml`` (rol.o/.t/.w/.b),
    ``rev/rev.yaml`` (rev.o/.t/.w/.b), ``clmul/clmul.yaml`` (clmul.o).
``atomics``
    ``atomics/atomics-lrsc.yaml`` + ``atomics/sc-rd0.yaml`` (lr/sc, 24 forms,
    ``sc`` rd0 legality) and ``atomics/atomics-fence.yaml`` (fence), plus
    ``base/misc.yaml``'s ``swym`` cases and the reserved-encoding vectors
    (``base/reserved.yaml``).  Also emits three dedicated reservation probes
    (exception entry clears it, an intervening same-hart store makes ``sc``
    fail, and the failed ``sc`` clears the reservation).
``intfill``
    the remaining integer families: wyde/byte arithmetic, compare and shifts,
    ``cs.*`` conditional assignment, the register-block copies and ``swym``'s
    no-op form.

Subcommands
-----------
``list``
    Print every covered case and the live counts (recomputed from the YAML).
``emit OUTDIR``
    Emit, assemble and link, into ``OUTDIR`` per group:
      ``<group>.elf`` / ``.raw`` / ``<group>_expect.bin`` / ``<group>.json``;
      ``fault_<group>_<key>.elf`` / ``.raw`` + ``faults_<group>.json``.
"""
from __future__ import annotations

import argparse
import json
import struct
import subprocess
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
CODE = ENTRY + 0x1000
# The result buffer and the SYS_EXIT block sit far above the code (the SRAM
# window is 8 MiB), so a group image is never limited by the dump area.
BUF = ENTRY + 0x40000
EXITBLOCK = ENTRY + 0x50000
IMAGE_LIMIT = BUF - ENTRY

WR_PTR = sweep.WR_PTR
ZERO_RB = sweep.ZERO_RB
TMP_RD = sweep.TMP_RD
TMP2_RD = 15
SEMI_RD = sweep.SEMI_RD
TMP_RB = sweep.TMP_RB
DUMP = ENTRY + 0x300

FAULT_DATA_OFF = 0x400
PRE_BLOCK = ENTRY + FAULT_DATA_OFF
POST_BLOCK = ENTRY + FAULT_DATA_OFF + 8

MEM_LD_OPC = {1: 0x10, 2: 0x11, 4: 0x12, 8: 0x20}  # unsigned load by byte width
MEM_ST_OPC = {1: 0x18, 2: 0x19, 4: 0x1A, 8: 0x21}  # store by byte width
LD_O_RD = 0x20
ST_O_RD = 0x21
LD_O_RB = 0x22
ST_O_RB = 0x23
LD_O_RA = 0x24
ST_O_RA = 0x25

WIDTH_TOKENS = {"b": 1, "w": 2, "t": 4, "o": 8}
FAULT_BITS = {"CFXMEM": 1, "CFXREG": 2, "ILLI": 8, "UNDI": 9,
              "RASOF": 10, "RASUF": 11, "MALIGN": 12, "IALIGN": 13}

# ---- covered groups ------------------------------------------------------
# Explicit id lists: an id that is not emitted by the decoder (or a new vector
# added to the file under an unimplemented id) must never slip through silently
# -- the live counts below are recomputed from the YAML on every run.
BITOP_FILES = (
    "tests/inst/bitcnt/bitcnt.yaml",
    "tests/inst/rol/rol.yaml",
    "tests/inst/rev/rev.yaml",
    "tests/inst/clmul/clmul.yaml",
)

ATOMIC_FILES = (
    "tests/inst/atomics/atomics-lrsc.yaml",
    "tests/inst/atomics/atomics-fence.yaml",
    "tests/inst/atomics/sc-rd0.yaml",
    "tests/inst/base/misc.yaml",
    "tests/inst/base/reserved.yaml",
)
ATOMIC_IDS = {
    # lr: 12 forms (nn/an/ar x b/w/t/o), sc: 12 forms (nn/nr/ar x b/w/t/o)
    *[f"lr.{w}.{seq}_orrr_rd" for w in "bwto" for seq in ("nn", "an", "ar")],
    *[f"sc.{w}.{seq}_orrr_rd" for w in "bwto" for seq in ("nn", "nr", "ar")],
    "fence_ciii_cfx", "swym_oiii_imm",
}

INTFILL_FILES = (
    "tests/inst/base/reg-arith.yaml",
    "tests/inst/base/reg-compare.yaml",
    "tests/inst/base/reg-shift-extend.yaml",
    "tests/inst/base/reg-cond-assign.yaml",
    "tests/inst/base/reg-imm-block.yaml",
)
INTFILL_IDS = {
    # wyde/byte arithmetic (tetra/octa already run in the m12-005/008 sweeps)
    *[f"{op}.{sfx}_orrr_rd" for op in ("add", "sub", "mul", "div", "rem")
      for sfx in ("uw", "sw", "ub", "sb")],
    # wyde/byte compare
    *[f"cmp.{sfx}_orrr_rd" for sfx in ("uw", "sw", "ub", "sb")],
    # wyde/byte shifts and rotates (register + immediate forms)
    *[f"{op}.{s}_orrr_rd" for op in ("shl", "rol", "shr") for s in ("w", "b")],
    *[f"{op}.{sfx}_orrr_rd" for op in ("shr",) for sfx in ("uw", "sw", "ub", "sb")],
    *[f"{op}.{s}_orri_rd" for op in ("shl", "rol", "shr") for s in ("w", "b")],
    *[f"{op}.{sfx}_orri_rd" for op in ("shr",) for sfx in ("uw", "sw", "ub", "sb")],
    # conditional assignment
    "cs.eq_rrrr_rd", "cs.ne_rrrr_rd", "cs.n_rrrr_rd", "cs.p_rrrr_rd",
    "cs.z_rrrr_rd",
    # register-block copies
    "rd2rd_orri_rd", "ra2rd_orri_ra", "rd2ra_orri_ra", "rb2rb_orri_rb",
    "rd2rb_orri_rb", "rb2rd_orri_rb",
}

GROUPS = {
    "bitops": (BITOP_FILES, None),          # every case in these files
    "atomics": (ATOMIC_FILES, ATOMIC_IDS),
    "intfill": (INTFILL_FILES, INTFILL_IDS),
}


def as_int(v):
    return v if isinstance(v, int) else int(str(v), 16)


def width_bytes(case):
    """Access width in bytes from the mnemonic (b/w/t/o, incl. .uw/.sb forms)."""
    parts = (case.get("mnemonic") or "").split(".")
    for p in parts[1:]:
        if p in WIDTH_TOKENS:
            return WIDTH_TOKENS[p]
        if len(p) == 2 and p[0] in "us" and p[1] in WIDTH_TOKENS:
            return WIDTH_TOKENS[p[1]]
    raise SystemExit(f"bit_sweep: cannot derive an access width from "
                     f"{case.get('mnemonic')!r} ({case.get('id')})")


def asm_print_buffer(nbytes):
    """SYS_WRITEC one byte at a time from BUF (the result buffer)."""
    words = sweep.load_rb(SEMI_RD, BUF)
    words.append(sweep.enc_set_zw_rd(SEMI_RD, 0, sweep.SYS_WRITEC))
    for _ in range(nbytes):
        words.append(sweep.enc_trap(0, sweep.SEMIHOST_TAG | sweep.SYS_WRITEC))
        words.append(sweep.enc_add_si_rb(SEMI_RD, 1))
    return words


def asm_sys_exit(code):
    words = sweep.load_rb(SEMI_RD, EXITBLOCK)
    words += sweep.load_rd(15, sweep.ADP_STOPPED_APPLICATION_EXIT)
    words.append(sweep.enc_st_o_rd(15, SEMI_RD, 0))
    words += sweep.load_rd(15, code)
    words.append(sweep.enc_st_o_rd(15, SEMI_RD, 8))
    words.append(sweep.enc_set_zw_rd(SEMI_RD, 0, sweep.SYS_EXIT))
    words.append(sweep.enc_trap(0, sweep.SEMIHOST_TAG | sweep.SYS_EXIT))
    return words


def enc_mem(opc, reg, rb, off):
    return (opc << 24) | (reg << 18) | (rb << 12) | (off & 0xFFF)


def enc_jump_rrii(rbha, rdhb, imms12):
    return (0x71 << 24) | (rbha << 18) | (rdhb << 12) | (imms12 & 0xFFF)


def enc_br_nz_rb(rbha, imms18):
    return (0x73 << 24) | (rbha << 18) | (imms18 & 0x3FFFF)


def load_ra(num, value):
    """`ra` has no immediate form: stage through memory and `ld.o`-ra."""
    words = sweep.load_rd(TMP_RD, value)
    words += sweep.load_rb(TMP_RB, DUMP)
    words.append(enc_mem(ST_O_RD, TMP_RD, TMP_RB, 0))
    words.append(enc_mem(LD_O_RA, num, TMP_RB, 0))
    return words


def dump_reg(bank, num):
    if bank == "rd":
        words = [enc_mem(ST_O_RD, num, WR_PTR, 0)]
    elif bank == "rb":
        words = [sweep.enc_sub_o_dbb(TMP_RD, num, ZERO_RB),
                 enc_mem(ST_O_RD, TMP_RD, WR_PTR, 0)]
    else:  # ra
        words = [enc_mem(ST_O_RA, num, WR_PTR, 0)]
    return words + [sweep.enc_add_si_rb(WR_PTR, 8)]


def dump_mem(addr, nbytes):
    words = sweep.load_rb(TMP_RB, addr)
    words.append(enc_mem(MEM_LD_OPC[nbytes], TMP_RD, TMP_RB, 0))
    words.append(enc_mem(ST_O_RD, TMP_RD, WR_PTR, 0))
    return words + [sweep.enc_add_si_rb(WR_PTR, 8)]


def load_inputs(case):
    """Set the input registers and memory entries of one case."""
    words = []
    inp = case.get("input_state") or {}
    for name, val in sorted((inp.get("rd") or {}).items(), key=lambda kv: int(kv[0][2:])):
        words += sweep.load_rd(int(name[2:]), as_int(val))
    for name, val in sorted((inp.get("rb") or {}).items(), key=lambda kv: int(kv[0][2:])):
        words += sweep.load_rb(int(name[2:]), as_int(val))
    for name, val in sorted((inp.get("ra") or {}).items(), key=lambda kv: int(kv[0][2:])):
        words += load_ra(int(name[2:]), as_int(val))
    if inp.get("memory"):
        nbytes = width_bytes(case)
        store_opc = MEM_ST_OPC[nbytes]
        mask = (1 << (8 * nbytes)) - 1
        for entry in inp["memory"]:
            addr = as_int(entry["address"])
            val = as_int(entry["value"]) & mask
            words += sweep.load_rb(TMP_RB, addr)
            words += sweep.load_rd(TMP_RD, val)
            words.append(enc_mem(store_opc, TMP_RD, TMP_RB, 0))
    return words


def check_scratch(cases):
    for case in cases:
        for bank in ("rd", "rb"):
            regs = dict((case.get("input_state") or {}).get(bank) or {})
            regs.update((case.get("expected_state") or {}).get(bank) or {})
            for name in regs:
                num = int(name[2:])
                if bank == "rd" and num in (TMP_RD, TMP2_RD, SEMI_RD, 8):
                    raise SystemExit(
                        f"bit_sweep: case {case.get('id')} uses rd{num}, reserved")
                if bank == "rb" and num in (WR_PTR, TMP_RB, ZERO_RB, SEMI_RD):
                    raise SystemExit(
                        f"bit_sweep: case {case.get('id')} uses rb{num}, reserved")


def load_cases(group, files, ids):
    out = []
    for rel in files:
        for idx, case in enumerate(yaml.safe_load((ROOT / rel).read_text())):
            if ids is not None and case.get("id") not in ids:
                continue
            if case.get("status") == "deferred":
                continue
            out.append({"file": rel, "index": idx, "case": case})
    return out


def case_regs(case):
    st = case.get("expected_state") or {}
    regs = []
    for bank in ("rd", "rb", "ra"):
        for name in sorted((st.get(bank) or {}), key=lambda n: int(n[2:])):
            if name in ("rd0", "rb0"):
                continue
            regs.append((bank, int(name[2:])))
    return regs


def case_mem(case):
    st = case.get("expected_state") or {}
    mem = st.get("memory") or []
    if not mem:
        return []
    nbytes = width_bytes(case)
    out = []
    for m in mem:
        addr = as_int(m["address"])
        if addr not in [a for a, _ in out]:
            out.append((addr, nbytes))
    return out


def build_sweep(cases):
    check_scratch([c["case"] for c in cases])
    # A one-word trampoline keeps the vectors able to name `@ENTRY` as a data
    # address while the program body lives at CODE.
    words = [enc_jump_rrii(0, 0, (CODE - ENTRY) >> 2)]
    words += [0] * (((CODE - ENTRY) >> 2) - len(words))
    words += sweep.asm_prelude()
    words += sweep.load_rb(WR_PTR, BUF)
    expected = bytearray()
    manifest = []
    for entry in cases:
        case = machine_profile.resolve_case(entry["case"], PROFILE)
        if case.get("expected_fault"):
            continue
        words += load_inputs(case)
        for word in case.get("sequence") or [case["encoding"]["word"]]:
            words.append(int(str(word), 16))
        st = case.get("expected_state") or {}
        regs = case_regs(case)
        mems = case_mem(case)
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
            "seq_len": len(case.get("sequence") or [1]),
            "regs": [f"{b}{n}" for b, n in regs],
            "mem": [f"0x{a:x}/{w}" for a, w in mems],
            "offset": offset, "bytes": len(regs) * 8 + len(mems) * 8,
        })
    nbytes = len(expected)
    words += asm_print_buffer(nbytes)
    words += asm_sys_exit(0)
    return words, bytes(expected), manifest, nbytes


def build_fault(case, word):
    words = sweep.asm_prelude()
    words += sweep.asm_write0(PRE_BLOCK)
    words += load_inputs(case)
    words.append(int(str(word), 16))
    words += sweep.asm_write0(POST_BLOCK)
    words += asm_sys_exit(0)
    if len(words) * 4 > FAULT_DATA_OFF:
        raise SystemExit("bit_sweep: fault program does not fit below the marker block")
    words += [0] * ((FAULT_DATA_OFF - len(words) * 4) // 4)
    words += [0x5052450A, 0x00000000, 0x504F5354, 0x0A000000]  # "PRE\n\0POST\n\0"
    return words


# ---------------------------------------------------------------------------
# Dedicated reservation probes (spec/SimRISC-12 §1.1)
# ---------------------------------------------------------------------------
LR_O_NN = 0x47000000   # lr.o.nn   rdHC, [rbHD]
SC_O_NN = 0x47400000   # sc.o.nn   rdHB, rdHC, [rbHD]


def enc_lr_o_nn(rd, rb):
    return LR_O_NN | (rd << 6) | rb


def enc_sc_o_nn(rd, rc, rb):
    return SC_O_NN | (rd << 12) | (rc << 6) | rb


def enc_st_o(rd, rb, off=0):
    return (0x21 << 24) | (rd << 18) | (rb << 12) | (off & 0xFFF)


def build_resv_probes():
    """Three probes for the reservation rules the vectors cannot express."""
    A = ENTRY + 0x2000
    images = {}

    # (a) exception entry between `lr` and `sc` must clear the reservation.
    words = [enc_jump_rrii(0, 0, (CODE - ENTRY) >> 2)]
    words += [0] * (((CODE - ENTRY) >> 2) - len(words))
    words += sweep.asm_prelude()
    words += sweep.load_rb(WR_PTR, BUF)
    words += sweep.load_rb(4, A)
    words += sweep.load_rd(1, 0x1111222233334444)
    words.append(enc_st_o(1, 4))                     # seed the word
    words.append(enc_lr_o_nn(2, 4))                  # reservation taken
    # An all-zero instruction word is a reserved encoding (UNDI): entering the
    # monitor must clear the reservation.
    words.append(0x00000000)
    words.append(enc_sc_o_nn(5, 1, 4))               # must fail: rd5 = 1
    words += dump_reg("rd", 5)
    words += dump_mem(A, 8)
    words += asm_print_buffer(16)
    words += asm_sys_exit(0)
    images["resv_clear_on_exception"] = (words, (1).to_bytes(8, "big") +
                                         (0x1111222233334444).to_bytes(8, "big"))

    # (b) a same-hart store that changes the word makes `sc` fail (spurious
    # failure, which the spec allows and QEMU implements via the word value).
    words = [enc_jump_rrii(0, 0, (CODE - ENTRY) >> 2)]
    words += [0] * (((CODE - ENTRY) >> 2) - len(words))
    words += sweep.asm_prelude()
    words += sweep.load_rb(WR_PTR, BUF)
    words += sweep.load_rb(4, A)
    words += sweep.load_rd(1, 0x1111222233334444)
    words.append(enc_st_o(1, 4))
    words.append(enc_lr_o_nn(2, 4))
    words += sweep.load_rd(6, 0x5555666677778888)
    words.append(enc_st_o(6, 4))                     # word changed in between
    words.append(enc_sc_o_nn(5, 1, 4))               # must fail: rd5 = 1
    words += dump_reg("rd", 5)
    words += dump_mem(A, 8)
    words += asm_print_buffer(16)
    words += asm_sys_exit(0)
    images["resv_word_changed"] = (words, (1).to_bytes(8, "big") +
                                   (0x5555666677778888).to_bytes(8, "big"))

    # (c) a successful `sc` clears the reservation: the second `sc` must fail
    # and must not write.
    words = [enc_jump_rrii(0, 0, (CODE - ENTRY) >> 2)]
    words += [0] * (((CODE - ENTRY) >> 2) - len(words))
    words += sweep.asm_prelude()
    words += sweep.load_rb(WR_PTR, BUF)
    words += sweep.load_rb(4, A)
    words += sweep.load_rd(1, 0x1111222233334444)
    words.append(enc_st_o(1, 4))
    words.append(enc_lr_o_nn(2, 4))
    words += sweep.load_rd(1, 0xAAAABBBBCCCCDDDD)
    words.append(enc_sc_o_nn(5, 1, 4))               # succeeds: rd5 = 0
    words += sweep.load_rd(1, 0x1234123412341234)
    words.append(enc_sc_o_nn(6, 1, 4))               # fails: rd6 = 1
    words += dump_reg("rd", 5)
    words += dump_reg("rd", 6)
    words += dump_mem(A, 8)
    words += asm_print_buffer(24)
    words += asm_sys_exit(0)
    images["resv_consumed"] = (words, (0).to_bytes(8, "big") +
                               (1).to_bytes(8, "big") +
                               (0xAAAABBBBCCCCDDDD).to_bytes(8, "big"))
    return images


# ---------------------------------------------------------------------------
# Cycle probe: one of each new instruction, back to back
# ---------------------------------------------------------------------------
def build_timing():
    """A short program with one of every new instruction shape.

    The evidence script reads the core's ``exec ... cycle=`` trace and reports
    the measured cost of each instruction (cycle(next exec) - cycle(this
    exec)); nothing is estimated.
    """
    A = ENTRY + 0x2000
    words = [enc_jump_rrii(0, 0, (CODE - ENTRY) >> 2)]
    words += [0] * (((CODE - ENTRY) >> 2) - len(words))
    words += sweep.asm_prelude()
    words += sweep.load_rb(WR_PTR, BUF)
    words += sweep.load_rb(4, A)
    words += sweep.load_rd(1, 0x8123456789ABCDEF)
    words += sweep.load_rd(5, 0x0123456789ABCDEF)
    words += sweep.load_rd(6, A)
    words.append(enc_st_o(6, 4))                     # seed [A]
    marks = []

    def mark(name, ws):
        marks.append({"name": name, "index": len(words)})
        return ws

    words += mark("add.si (fast path)", [sweep.enc_add_si_rb(2, 1)])
    words += mark("ctpop", [0x479410BF])             # ctpop rd2, rd1, 63
    words += mark("ctlz", [0x479810BF])
    words += mark("cttz", [0x479C10BF])
    words += mark("rev.o k=8", [0x40301088])         # rev.o rd2, rd1, 8
    words += mark("rol.o orri", [0x40641083])
    words += mark("clmul.o", [0x56C44005])           # clmul.o {rd3,rd4}, rd1, rd5
    words += mark("fence", [0x79000000])
    words += mark("swym 0", [0x47880000])
    words += mark("cs.z", [0x6201440D])              # cs.z rd1, rd2, rd3, rd4
    words += mark("rd2rd x8", [(0x40B00000 | (24 << 12) | (32 << 6) | 8)])
    words += mark("lr.o.nn", [enc_lr_o_nn(2, 4)])
    words += mark("sc.o.nn (hit)", [enc_sc_o_nn(5, 1, 4)])
    words += mark("sc.o.nn (miss)", [enc_sc_o_nn(5, 1, 4)])
    words += mark("fence (mask)", [0x79000FFF])
    words += asm_sys_exit(0)
    return words, marks


# ---------------------------------------------------------------------------
# Assemble / link
# ---------------------------------------------------------------------------
LDS = """ENTRY(_start)
PHDRS {{ image PT_LOAD FLAGS(7); }}
SECTIONS
{{
  . = 0x{entry:x};
  .text : {{ *(.text .text.*) }} : image
  /DISCARD/ : {{ *(.note.GNU-stack) *(.comment) }}
}}
"""


def assemble(words, outdir, stem, tb):
    src = outdir / f"{stem}.S"
    lds = outdir / f"{stem}.lds"
    obj = outdir / f"{stem}.o"
    elf = outdir / f"{stem}.elf"
    raw0 = outdir / f"{stem}.flat"
    raw = outdir / f"{stem}.raw"
    lds.write_text(LDS.format(entry=ENTRY))
    lines = [".text", ".globl _start", "_start:"]
    lines += [".dd.t32 0x%08x" % w for w in words]
    src.write_text("\n".join(lines) + "\n")
    subprocess.run([str(tb / "llvm-mc"), "--triple=dadao-unknown-elf", "-filetype=obj",
                    str(src), "-o", str(obj)], check=True)
    subprocess.run([str(tb / "ld.lld"), "-T", str(lds), str(obj), "-o", str(elf)], check=True)
    subprocess.run([str(tb / "llvm-objcopy"), "-O", "binary", str(elf), str(raw0)], check=True)
    data = raw0.read_bytes()
    if len(data) > IMAGE_LIMIT:
        raise SystemExit(f"bit_sweep: {stem} code {len(data)} B exceeds {IMAGE_LIMIT} B")
    raw.write_bytes(b"\x00" * sweep.RAW_PREFIX + data)
    return elf, raw


def cmd_list(_args):
    total = 0
    for group, (files, ids) in GROUPS.items():
        cases = load_cases(group, files, ids)
        sem = [c for c in cases if not c["case"].get("expected_fault")]
        faults = [c for c in cases if c["case"].get("expected_fault")]
        total += len(cases)
        print(f"{group}: covered={len(cases)} semantic={len(sem)} "
              f"fault={len(faults)}")
        for entry in cases:
            case = entry["case"]
            print(f"  {entry['file']}:{entry['index']}  {case.get('id')}  "
                  f"{case.get('class')}  fault={case.get('expected_fault')}")
    print(f"total={total}")
    return 0


def cmd_emit(args):
    outdir = Path(args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    tb = sweep.toolchain_bin(args.toolchain_bin)

    summary = {}
    for group, (files, ids) in GROUPS.items():
        cases = load_cases(group, files, ids)
        sem = [c for c in cases if not c["case"].get("expected_fault")]
        words, expected, manifest, nbytes = build_sweep(sem)
        elf, raw = assemble(words, outdir, group, tb)
        (outdir / f"{group}_expect.bin").write_bytes(expected)
        (outdir / f"{group}.json").write_text(json.dumps(
            {"bytes": nbytes, "cases": manifest}, indent=1) + "\n")

        faults = []
        for entry in cases:
            case = machine_profile.resolve_case(entry["case"], PROFILE)
            if case.get("expected_fault") in FAULT_BITS:
                faults.append({
                    "key": f"{Path(entry['file']).stem}_{entry['index']}",
                    "id": case["id"],
                    "fault": case["expected_fault"],
                    "cause": 1 << FAULT_BITS[case["expected_fault"]],
                    "word": case["encoding"]["word"],
                    "case": case,
                })
        for entry in yaml.safe_load((ROOT / "tests/inst/base/reserved.yaml").read_text()):
            if entry.get("encoding", {}).get("reserved") and entry.get("expected_fault") == "UNDI":
                faults.append({
                    "key": "reserved_" + entry["encoding"]["word"][2:],
                    "id": "reserved",
                    "fault": "UNDI",
                    "cause": 1 << FAULT_BITS["UNDI"],
                    "word": entry["encoding"]["word"],
                    "case": {"input_state": {}},
                })
        fault_meta = []
        for f in faults:
            fwords = build_fault(f["case"], f["word"])
            fel, fraw = assemble(fwords, outdir, f"fault_{group}_{f['key']}", tb)
            fault_meta.append({"key": f["key"], "id": f["id"], "fault": f["fault"],
                               "cause": f["cause"], "word": f["word"],
                               "elf": fel.name, "raw": fraw.name})
        (outdir / f"faults_{group}.json").write_text(
            json.dumps(fault_meta, indent=1) + "\n")

        if group == "bitops":
            twords, tmarks = build_timing()
            tel, traw = assemble(twords, outdir, "timing", tb)
            (outdir / "timing.json").write_text(json.dumps(
                {"entry": ENTRY, "marks": tmarks}, indent=1) + "\n")

        if group == "atomics":
            probes = []
            for name, (pwords, pexp) in build_resv_probes().items():
                pel, praw = assemble(pwords, outdir, name, tb)
                (outdir / f"{name}_expect.bin").write_bytes(pexp)
                probes.append({"name": name, "elf": pel.name, "raw": praw.name,
                               "expect": f"{name}_expect.bin"})
            (outdir / "probes.json").write_text(json.dumps(probes, indent=1) + "\n")

        summary[group] = {"covered": len(cases), "semantic": len(sem),
                          "faults": len(faults), "dumped_bytes": nbytes}
        print(f"emit: {group} covered={len(cases)} semantic={len(sem)} "
              f"fault_images={len(faults)} dumped_bytes={nbytes}")
    print(f"emit: outdir={outdir} total={sum(v['covered'] for v in summary.values())}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
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
