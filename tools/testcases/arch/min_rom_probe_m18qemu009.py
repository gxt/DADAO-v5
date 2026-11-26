#!/usr/bin/env python3
"""min_rom_probe_m18qemu009.py — QEMU-side unit probe for the per-source
pending/mask/ack model (`m18-qemu-009`, `DADAO-12` 0.8.1-rc / `ADR-0064`).

Judged against the spec, never against the implementation:

  * `spec/DADAO-12` §3.6 / §4.1-§4.4 / §4.7 / §4.9 / §5.4
  * `.tao/adr/adr-0064-interrupt-source-pending-mask-ack.md`

Covered capability groups (task-book acceptance 1-5):

  layout      `cfx_hart cg15` async capture (rc0-rc5 HW/RO, rc14/rc15 RW,
              rc6-rc13 => CFXREG); `cfx_hart cg9` => CFXREG; monitor
              `cg15 rc3` async mask (reset all-1, RW) and `cg8 rc1` => CFXREG;
              `cfx_hart cg16` timer face (rc0 ctrl bit0 only, rc1
              cmp, rc16 mask, rc17 pending, rc18 ack); `cfx_pmem cg16` DMA
              face; `cfx_hart cg8 rc4/rc5` => CFXREG; `cg16` is CFXREG on
              other cfx.
  timer       pending is sticky (ack-only), `ENABLE` gates event creation,
              `ENABLE` 0->1 checks the deadline immediately, writing cmp only
              re-arms, ack is idempotent and reserved bits are ignored.
  entry       async entry does NOT clear source pending; it captures
              `cg15 rc4` = source cfxha bits, `rc5` = raw pending summary,
              and increments `excp_async_num` once per entry; monitor mask
              gates the whole source.
  multi       TIMER + PMEM_DMA pending in the same instruction boundary merge
              into one capture (bitmap union), then per-source ack clears.
  dma         `DONE|ERROR` merges into cg16 pending bit0; `cg16 rc18` ack
              clears pending only, `dma_status` keeps its own W1C; `dma_ctrl`
              bit2 is reserved (read 0 / write ignored), no IRQ_EN.
  escape      `escape cfxHA` restores the target mode monitor's `cg15 rc3`
              from `cg5 rc11` as one whole word.

The body is emitted as instruction words (no assembler), so the probe is
independent of the toolchain's `escape` syntax.

Observation channel: the final `-d cpu` dump (RD registers + MODE/CFXCODE).
Every case is one QEMU process; a case is PASS only when all its assertions
hold.  Any mismatch exits non-zero (`FAIL`).

Usage:
  DADAO_TEST_PROFILE=vast min_rom_probe_m18qemu009.py --qemu QEMU [--case NAME]
"""

import argparse
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import node_probe_prelude as P  # noqa: E402

HA_UMON = 0
HA_JMON = 1
HA_SMON = 2
HA_HMON = 3
HA_HART = 15
HA_PMEM = 32

CG2 = 2
CG3 = 3
CG4 = 4
CG5 = 5
CG8 = 8
CG9 = 9
CG15 = 15
CG16 = 16

CFXREG = 1 << 2
CFXESC = 1 << 3
ILLI = 1 << 8

MODE_SUPV = 2
MODE_HYPV = 3

ALL1 = 0xFFFFFFFFFFFFFFFF
MASK_TIMER_ONLY = 0xFFFFFFFFFFFF7FFF       # bit15 open, bit32 masked
MASK_BOTH_OPEN = 0xFFFFFFFEFFFF7FFF        # bit15 and bit32 open
MASK_PATTERN = 0x0123456789ABCDEF

OFF_FH_HMON = 0x400
OFF_HMON_PROG = 0x600
OFF_ASYNC = 0x700

ROM_BASE = P.ROM_BASE
SPEC = "spec/DADAO-12-SEE-主管系统运行环境.md"


class OracleError(Exception):
    pass


def _repo_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))


def _read_spec():
    path = os.path.join(_repo_root(), SPEC)
    try:
        return open(path, encoding="utf-8").read()
    except OSError as exc:
        raise OracleError("cannot read %s: %s" % (path, exc))


def spec_facts():
    """Derive the register slots/access/reset facts this probe asserts.

    The oracle is the spec table; a mismatch means the probe must be updated,
    not that the implementation is right.
    """
    text = _read_spec()
    facts = {}

    # cfx_hart cg15 async capture table.
    cg15 = {}
    for rc, name, regname, init, access, note in re.findall(
            r"^\|\s*15\s*\|\s*(\d+)\s*\|\s*([^|]*?)\s*\|\s*"
            r"(cfx_hart_async_[a-z_]+)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|"
            r"\s*([^|]*?)\s*\|",
            text, re.M):
        cg15[regname] = (int(rc), access.strip(), init.strip(), note.strip())
    want = {
        "cfx_hart_async_prev_run_mode": (0, "HW/RO"),
        "cfx_hart_async_prev_cfx_code": (1, "HW/RO"),
        "cfx_hart_async_cause_ip": (2, "HW/RO"),
        "cfx_hart_async_prev_intr_mask": (3, "HW/RO"),
        "cfx_hart_async_src_frame": (4, "HW/RO"),
        "cfx_hart_async_src_pending": (5, "HW/RO"),
        "cfx_hart_async_switch_run_mode": (14, "RW"),
        "cfx_hart_async_excp_vector": (15, "RW"),
    }
    for reg, (rc, access) in want.items():
        if reg not in cg15 or cg15[reg][0] != rc or cg15[reg][1] != access:
            raise OracleError("spec §4.7: %s must be rc%d %s (%r)"
                              % (reg, rc, access, cg15.get(reg)))
    if cg15["cfx_hart_async_switch_run_mode"][2] != "2":
        raise OracleError("spec §4.7: async_switch_run_mode reset 2 missing")
    facts["cg15"] = cg15

    # Four monitor rows: cg15 rc3 async mask, cg8 rc1 reserved.
    mask_rows = re.findall(
        r"^\|\s*15\s*\|\s*3\s*\|\s*async intr mask\s*\|\s*"
        r"cfx_(umon|jmon|smon|hmon)_async_intr_mask\s*\|\s*([^|]*?)\s*\|"
        r"\s*([^|]*?)\s*\|", text, re.M)
    if sorted(n for n, _, _ in mask_rows) != ["hmon", "jmon", "smon", "umon"]:
        raise OracleError("spec §4.1-§4.4: cg15 rc3 mask rows not found")
    for name, init, access in mask_rows:
        if init.strip() != "全1" or access.strip() != "RW":
            raise OracleError("spec §4.%s: cg15 rc3 must be 全1/RW"
                              % name)
    if not re.search(r"`cg8 rc1` 归 reserved", text):
        raise OracleError("spec §4.1-§4.4: cg8 rc1 must be reserved")
    facts["mask_reset"] = ALL1

    # cfx_hart cg16 timer face.
    timer_rows = {}
    for rc, name, regname, init, access, note in re.findall(
            r"^\|\s*16\s*\|\s*(\d+)\s*\|\s*([^|]*?)\s*\|\s*"
            r"(cfx_hart_timer_[a-z_]+)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|"
            r"\s*([^|]*?)\s*\|",
            text, re.M):
        timer_rows[regname] = (int(rc), name.strip(), init.strip(),
                               access.strip(), note.strip())
    for reg, rc, acc, init in (
            ("cfx_hart_timer_ctrl", 0, "RW", "0"),
            ("cfx_hart_timer_cmp", 1, "RW", "0"),
            ("cfx_hart_timer_mask", 16, "RW", "全1"),
            ("cfx_hart_timer_pending", 17, "RO", "0"),
            ("cfx_hart_timer_ack", 18, "RW", "0")):
        if reg not in timer_rows:
            raise OracleError("spec §4.7: %s row not found" % reg)
        got = timer_rows[reg]
        if got[0] != rc or got[3] != acc or got[2] != init:
            raise OracleError("spec §4.7: %s must be rc%d %s reset %s, is %r"
                              % (reg, rc, acc, init, got))
    if "bit0=ENABLE" not in timer_rows["cfx_hart_timer_ctrl"][4]:
        raise OracleError("spec §4.7: timer ctrl must define only ENABLE")
    facts["timer_mask_reset"] = 1

    # cfx_pmem cg16 DMA face and dma_ctrl bit2 reservation.
    pmem_rows = {}
    for rc, name, regname, init, access, note in re.findall(
            r"^\|\s*16\s*\|\s*(\d+)\s*\|\s*([^|]*?)\s*\|\s*"
            r"(cfx_pmem_[a-z_]+)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|"
            r"\s*([^|]*?)\s*\|",
            text, re.M):
        pmem_rows[regname] = (int(rc), name.strip(), init.strip(),
                              access.strip(), note.strip())
    for reg, rc, acc, init in (
            ("cfx_pmem_dma_mask", 16, "RW", "全1"),
            ("cfx_pmem_dma_pending", 17, "RO", "0"),
            ("cfx_pmem_dma_ack", 18, "RW", "0")):
        if reg not in pmem_rows:
            raise OracleError("spec §4.9: %s row not found" % reg)
        got = pmem_rows[reg]
        if got[0] != rc or got[3] != acc or got[2] != init:
            raise OracleError("spec §4.9: %s must be rc%d %s reset %s, is %r"
                              % (reg, rc, acc, init, got))
    if "`DONE` 或 `ERROR`" not in pmem_rows["cfx_pmem_dma_pending"][4]:
        raise OracleError("spec §4.9: DMA pending sub-event must be DONE|ERROR")
    if "bit2 及以下保留（读 0/写忽略）" not in text:
        raise OracleError("spec §4.9: dma_ctrl bit2 reserved rule not found")
    if re.search(r"IRQ_EN", text):
        raise OracleError("spec §4.9: IRQ_EN must be removed")
    if not re.search(r"ack 才清|只有 `cg16 rc18` 的 W1C 才清", text):
        raise OracleError("spec: ack-only pending rule not found")
    facts["pmem_mask_reset"] = 1
    return facts


FACTS = spec_facts()


def addr(seq, label):
    return ROM_BASE + 4 * seq.lab[label]


# ---------------------------------------------------------------------------
# Reusable machine-code blocks
# ---------------------------------------------------------------------------

def body_setup(s, mask=MASK_PATTERN):
    """Install the hmon fault handler, set the hmon async mask and clear the
    pending bits left by the prelude's PMEM DMA.

    ``mask=None`` leaves the hmon async mask at its reset value so a case can
    assert the reset all-ones value directly (no write-then-read)."""
    s.e(*P.load_rd(19, ROM_BASE + OFF_FH_HMON))
    s.e(P.cfx2rc(HA_HMON, CG3, 15, 19))
    if mask is not None:
        wr(s, HA_HMON, CG15, 3, mask)
    wr(s, HA_PMEM, CG16, 18, 1)      # ack the prelude DMA completion
    wr(s, HA_HART, CG16, 18, 1)      # timer starts clean
    # Let a cfx_hart async handler reach cfx_pmem's cg16 (source cfxha 15 is
    # otherwise denied by cfx_pmem's reset cfxreg row).  Keep cfx_hmon itself
    # allowed (bit3 = 0, as at reset).
    wr(s, HA_PMEM, CG3, 2, 0xFFFFFFFFFFFFFFF7 & ~(1 << HA_HART), tmp=12)


def fault_handler(ha):
    """Record the first two faults of `ha` and return past the faulting insn."""
    s = P.Seq()
    s.b("z", 25, "first")
    s.e(P.cfx2rd(ha, CG5, 4, 26))
    s.e(P.cfx2rd(ha, CG5, 5, 27))
    s.e(P.cfx2rd(ha, CG5, 2, 28))
    s.b("z", 0, "ret")
    s.mark("first")
    s.e(P.cfx2rd(ha, CG5, 4, 20))
    s.e(P.cfx2rd(ha, CG5, 5, 21))
    s.e(P.cfx2rd(ha, CG5, 2, 22))
    s.mark("ret")
    s.e(P.add_si(25, 1))
    s.e(P.cfx2rd(ha, CG5, 2, 23))
    s.e(P.add_si(23, 4))
    s.e(P.cfx2rc(ha, CG5, 10, 23))
    s.e(P.escape(ha, 0))
    return s.resolve()


def ret_prog(ha, back_addr):
    s = P.Seq()
    s.e(*P.load_rd(23, MODE_HYPV))
    s.e(P.cfx2rc(ha, CG5, 8, 23))
    s.e(*P.load_rd(23, HA_HMON))
    s.e(P.cfx2rc(ha, CG5, 9, 23))
    s.e(*P.load_rd(23, back_addr))
    s.e(P.cfx2rc(ha, CG5, 10, 23))
    s.e(*P.load_rd(23, ALL1))
    s.e(P.cfx2rc(ha, CG5, 11, 23))
    s.e(P.escape(ha, 0))
    return s.resolve()


def rd(s, ha, cg, rc, dst):
    s.e(P.cfx2rd(ha, cg, rc, dst))


def wr(s, ha, cg, rc, val, tmp=23):
    s.e(*P.load_rd(tmp, val))
    s.e(P.cfx2rc(ha, cg, rc, tmp))


def _arm_timer(s, cmp_val=0, enable=1):
    wr(s, HA_HART, CG16, 16, 0, tmp=12)            # open the source mask
    wr(s, HA_HART, CG16, 1, cmp_val, tmp=13)       # timer_cmp
    wr(s, HA_HART, CG16, 0, enable, tmp=14)        # ctrl.ENABLE


def _dma_error(s):
    wr(s, HA_PMEM, CG15, 2, 0, tmp=12)             # dma_size = 0 => SIZE
    wr(s, HA_PMEM, CG15, 3, 1, tmp=12)             # START


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------

def case_hart_layout():
    s = P.Seq()
    body_setup(s, None)                      # leave every monitor mask at reset
    # Reset value is sampled before any write: all four monitors read all-1.
    rd(s, HA_UMON, CG15, 3, 38)
    rd(s, HA_JMON, CG15, 3, 39)
    rd(s, HA_SMON, CG15, 3, 40)
    rd(s, HA_HMON, CG15, 3, 41)
    for idx, rc in enumerate((0, 1, 2, 3, 4, 5, 14, 15)):
        rd(s, HA_HART, CG15, rc, 30 + idx)
    wr(s, HA_HMON, CG15, 3, MASK_PATTERN)
    rd(s, HA_HMON, CG15, 3, 42)
    # cg9 on cfx_hart is reserved now => CFXREG in the current monitor (hmon).
    rd(s, HA_HART, CG9, 0, 47)
    s.e(*P.exit_seq(0))
    return P.build_rom(s.resolve(), {OFF_FH_HMON: fault_handler(HA_HMON)}), {
        "rd25": 1,
        "rd30": 0, "rd31": 0, "rd32": 0, "rd33": 0, "rd34": 0, "rd35": 0,
        "rd36": MODE_SUPV, "rd37": 0,
        "rd38": ALL1, "rd39": ALL1, "rd40": ALL1, "rd41": ALL1,
        "rd42": MASK_PATTERN,
        "rd20": CFXREG,
        "rd21": (0x7A << 24) | (HA_HART << 18) | (CG9 << 12) | 47,
        "mymode": MODE_HYPV,
    }


def case_hart_layout_reserved():
    s = P.Seq()
    body_setup(s)
    rd(s, HA_HMON, CG8, 1, 30)               # old mask => CFXREG (1st fault)
    rd(s, HA_HART, CG8, 4, 31)               # old timer_cmp => CFXREG (2nd)
    s.e(*P.exit_seq(0))
    return P.build_rom(s.resolve(), {OFF_FH_HMON: fault_handler(HA_HMON)}), {
        "rd25": 2,
        "rd20": CFXREG,
        "rd21": (0x7A << 24) | (HA_HMON << 18) | (CG8 << 12) | (1 << 6) | 30,
        "rd26": CFXREG,
        "rd27": (0x7A << 24) | (HA_HART << 18) | (CG8 << 12) | (4 << 6) | 31,
    }


def case_source_layout():
    s = P.Seq()
    body_setup(s)
    rd(s, HA_PMEM, CG16, 16, 30)
    rd(s, HA_PMEM, CG16, 17, 31)
    rd(s, HA_PMEM, CG16, 18, 32)
    wr(s, HA_PMEM, CG16, 16, 0)
    rd(s, HA_PMEM, CG16, 16, 33)
    wr(s, HA_PMEM, CG16, 17, 1)              # pending RO => CFXREG
    s.e(*P.exit_seq(0))
    return P.build_rom(s.resolve(), {OFF_FH_HMON: fault_handler(HA_HMON)}), {
        "rd30": 1, "rd31": 0, "rd32": 0, "rd33": 0,
        "rd25": 1,
        "rd20": CFXREG,
        "rd21": (0x7B << 24) | (HA_PMEM << 18) | (CG16 << 12) | (17 << 6) | 23,
    }


def case_other_cfx_cg16():
    s = P.Seq()
    body_setup(s)
    rd(s, HA_SMON, CG16, 16, 30)            # only hart/pmem implement cg16
    s.e(*P.exit_seq(0))
    return P.build_rom(s.resolve(), {OFF_FH_HMON: fault_handler(HA_HMON)}), {
        "rd25": 1,
        "rd20": CFXREG,
        "rd21": (0x7A << 24) | (HA_SMON << 18) | (CG16 << 12) | (16 << 6) | 30,
    }


def case_timer_semantics():
    s = P.Seq()
    body_setup(s)
    rd(s, HA_HART, CG16, 0, 30)
    rd(s, HA_HART, CG16, 16, 31)
    rd(s, HA_HART, CG16, 17, 32)
    # cmp=1 while ENABLE=0: no event.
    wr(s, HA_HART, CG16, 1, 1, tmp=13)
    rd(s, HA_HART, CG16, 17, 33)
    # ENABLE 0->1 with cmp already in the past: immediate pending.
    wr(s, HA_HART, CG16, 0, 1, tmp=14)
    rd(s, HA_HART, CG16, 17, 34)
    # Writing cmp only re-arms; it must not clear pending.
    wr(s, HA_HART, CG16, 1, 1000, tmp=13)
    rd(s, HA_HART, CG16, 17, 35)
    rd(s, HA_HART, CG16, 1, 36)
    # Ack clears, is idempotent, reads 0; reserved bits in the ack are ignored.
    wr(s, HA_HART, CG16, 18, 1, tmp=14)
    rd(s, HA_HART, CG16, 17, 37)
    wr(s, HA_HART, CG16, 18, ALL1, tmp=14)
    rd(s, HA_HART, CG16, 17, 38)
    rd(s, HA_HART, CG16, 18, 39)
    # Mask reset all-1, RW, high bits read 0.
    wr(s, HA_HART, CG16, 16, 0, tmp=14)
    rd(s, HA_HART, CG16, 16, 40)
    wr(s, HA_HART, CG16, 16, ALL1, tmp=14)
    rd(s, HA_HART, CG16, 16, 41)
    # ctrl reserved bits: write 0xFE reads bit0 only.
    wr(s, HA_HART, CG16, 0, 0xFE, tmp=14)
    rd(s, HA_HART, CG16, 0, 42)
    s.e(*P.exit_seq(0))
    return P.build_rom(s.resolve(), {OFF_FH_HMON: fault_handler(HA_HMON)}), {
        "rd30": 0, "rd31": 1, "rd32": 0,
        "rd33": 0, "rd34": 1, "rd35": 1, "rd36": 1000,
        "rd37": 0, "rd38": 0, "rd39": 0,
        "rd40": 0, "rd41": 1, "rd42": 0,
    }


def case_async_pending_survives():
    """One TIMER capture: pending is not cleared by entry; cg15 rc4/rc5 show
    the source bit; the handler acks explicitly."""
    s = P.Seq()
    body_setup(s, MASK_TIMER_ONLY)
    wr(s, HA_HART, CG15, 14, MODE_HYPV)
    wr(s, HA_HART, CG15, 15, ROM_BASE + OFF_ASYNC)
    _arm_timer(s)
    s.e(P.jump_rel(1))
    s.mark("after_async")
    rd(s, HA_HART, CG4, 4, 30)              # excp_async_num
    rd(s, HA_HART, CG15, 0, 31)
    rd(s, HA_HART, CG15, 1, 32)
    rd(s, HA_HART, CG15, 2, 33)
    rd(s, HA_HART, CG15, 3, 34)
    rd(s, HA_HART, CG15, 4, 35)
    rd(s, HA_HART, CG15, 5, 36)             # after handler ack => 0
    rd(s, HA_HART, CG16, 17, 37)            # after handler ack => 0
    rd(s, HA_HART, CG5, 0, 38)              # async writes only rc8-rc11
    rd(s, HA_HART, CG5, 3, 39)
    rd(s, HA_HART, CG5, 11, 40)
    s.e(*P.exit_seq(0))
    h = P.Seq()
    h.e(P.add_si(25, 1))
    rd(h, HA_HART, CG16, 17, 41)            # before ack: still 1
    rd(h, HA_HART, CG15, 5, 42)             # raw pending summary: 1<<15
    rd(h, HA_HART, CG5, 8, 43)              # escape intent mode
    rd(h, HA_HART, CG5, 9, 44)              # escape intent cfx
    wr(h, HA_HART, CG16, 18, 1)             # ack TIMER
    h.e(P.escape(HA_HART, 0))
    return P.build_rom(s.resolve(), {
        OFF_FH_HMON: fault_handler(HA_HMON),
        OFF_ASYNC: h.resolve(),
    }), {
        "rd25": 1,
        "rd30": 1,
        "rd31": MODE_HYPV, "rd32": HA_HMON,
        "rd34": MASK_TIMER_ONLY, "rd35": 1 << 15, "rd36": 0,
        "rd37": 0, "rd38": 0, "rd39": 0, "rd40": MASK_TIMER_ONLY,
        "rd41": 1, "rd42": 1 << 15,
        "rd43": MODE_HYPV, "rd44": HA_HMON,
        "rd33": (">", ROM_BASE),
        "mymode": MODE_HYPV, "mycfx": HA_HMON,
    }


def case_async_mask_gate():
    """masked pending accumulates without entry; opening the monitor mask
    delivers at the next boundary."""
    s = P.Seq()
    body_setup(s, ALL1)                     # all sources masked
    wr(s, HA_HART, CG15, 14, MODE_HYPV)
    wr(s, HA_HART, CG15, 15, ROM_BASE + OFF_ASYNC)
    _arm_timer(s)
    s.e(P.jump_rel(1))
    s.mark("after_blocked")
    rd(s, HA_HART, CG4, 4, 30)              # no entry yet
    rd(s, HA_HART, CG16, 17, 31)            # pending accumulated
    wr(s, HA_HMON, CG15, 3, MASK_TIMER_ONLY)
    s.e(P.jump_rel(1))
    s.mark("after_open")
    rd(s, HA_HART, CG4, 4, 32)
    rd(s, HA_HART, CG16, 17, 33)            # handler acked
    s.e(*P.exit_seq(0))
    h = P.Seq()
    h.e(P.add_si(25, 1))
    wr(h, HA_HART, CG16, 18, 1)
    h.e(P.escape(HA_HART, 0))
    return P.build_rom(s.resolve(), {
        OFF_FH_HMON: fault_handler(HA_HMON),
        OFF_ASYNC: h.resolve(),
    }), {
        "rd25": 1,
        "rd30": 0, "rd31": 1,
        "rd32": 1, "rd33": 0,
    }


def case_multi_source():
    """TIMER + PMEM_DMA pending at one boundary merge into one capture."""
    s = P.Seq()
    body_setup(s, ALL1)                     # blocked while both events arrive
    wr(s, HA_HART, CG15, 14, MODE_HYPV)
    wr(s, HA_HART, CG15, 15, ROM_BASE + OFF_ASYNC)
    wr(s, HA_PMEM, CG16, 16, 0, tmp=12)     # open DMA source mask (mode gate shut)
    _arm_timer(s)                           # timer pending (mode gate still shut)
    _dma_error(s)                           # DONE|ERROR event => pending bit0
    rd(s, HA_HART, CG16, 17, 39)            # debug: timer pending before open
    rd(s, HA_PMEM, CG16, 17, 40)            # debug: dma pending before open
    wr(s, HA_HMON, CG15, 3, MASK_BOTH_OPEN) # one capture carries both sources
    s.e(P.jump_rel(1))
    s.mark("after_async")
    rd(s, HA_HART, CG4, 4, 30)
    rd(s, HA_HART, CG15, 4, 31)             # union: bits 15|32
    rd(s, HA_HART, CG15, 5, 32)             # after acks => 0
    rd(s, HA_PMEM, CG16, 17, 33)            # 0
    rd(s, HA_HART, CG16, 17, 34)            # 0
    rd(s, HA_PMEM, CG15, 4, 35)             # status still has ERROR
    s.e(*P.exit_seq(0))
    h = P.Seq()
    h.e(P.add_si(25, 1))
    rd(h, HA_HART, CG15, 4, 41)
    rd(h, HA_HART, CG15, 5, 42)
    rd(h, HA_HART, CG16, 17, 43)
    rd(h, HA_PMEM, CG16, 17, 44)
    h.e(*P.load_rd(12, 1))
    h.e(P.cfx2rc(HA_HART, CG16, 18, 12))
    h.e(P.cfx2rc(HA_PMEM, CG16, 18, 12))
    h.e(P.escape(HA_HART, 0))
    return P.build_rom(s.resolve(), {
        OFF_FH_HMON: fault_handler(HA_HMON),
        OFF_ASYNC: h.resolve(),
    }), {
        "rd25": 1,
        "rd30": 1,
        "rd31": (1 << 15) | (1 << 32),
        "rd32": 0, "rd33": 0, "rd34": 0,
        "rd35": (1 << 2) | (1 << 3),         # ERROR | ERR_CODE.SIZE
        "rd39": 1, "rd40": 1,               # both pending before the gate opens
        "rd41": (1 << 15) | (1 << 32),
        "rd42": (1 << 15) | (1 << 32),
        "rd43": 1, "rd44": 1,
    }


def case_dma_ack_vs_status():
    s = P.Seq()
    body_setup(s)
    # dma_ctrl: reset 0; bit2 is reserved (write ignored, read 0); DIR is RW.
    rd(s, HA_PMEM, CG15, 3, 30)
    wr(s, HA_PMEM, CG15, 3, 4, tmp=12)
    rd(s, HA_PMEM, CG15, 3, 31)
    wr(s, HA_PMEM, CG15, 3, 2, tmp=12)
    rd(s, HA_PMEM, CG15, 3, 32)
    # START-time ERROR sets cg16 pending bit0.
    _dma_error(s)
    rd(s, HA_PMEM, CG16, 17, 33)
    rd(s, HA_PMEM, CG15, 4, 34)
    # cg16 rc18 ack clears only pending; dma_status keeps ERROR.
    wr(s, HA_PMEM, CG16, 18, 1, tmp=12)
    rd(s, HA_PMEM, CG16, 17, 35)
    rd(s, HA_PMEM, CG15, 4, 36)
    # dma_status W1C clears ERROR/ERR_CODE on its own.
    wr(s, HA_PMEM, CG15, 4, 4, tmp=12)
    rd(s, HA_PMEM, CG15, 4, 37)
    # Ack is idempotent.
    wr(s, HA_PMEM, CG16, 18, 1, tmp=12)
    rd(s, HA_PMEM, CG16, 17, 38)
    s.e(*P.exit_seq(0))
    return P.build_rom(s.resolve(), {OFF_FH_HMON: fault_handler(HA_HMON)}), {
        "rd30": 0, "rd31": 0, "rd32": 2,
        "rd33": 1,
        "rd34": (1 << 2) | (1 << 3),         # ERROR | ERR_CODE.SIZE
        "rd35": 0,
        "rd36": (1 << 2) | (1 << 3),         # ack did not clear dma_status
        "rd37": 0, "rd38": 0,
    }


def case_escape_rc11_cg15():
    """escape restores the target monitor's cg15 rc3 from cg5 rc11."""
    s = P.Seq()
    body_setup(s, ALL1)
    wr(s, HA_HMON, CG3, 15, ROM_BASE + OFF_HMON_PROG)
    s.e(P.trap(HA_HMON, 0x1234))
    s.mark("back")
    rd(s, HA_HMON, CG15, 3, 30)
    rd(s, HA_HMON, CG5, 11, 31)
    s.e(*P.exit_seq(0))
    back = addr(s, "back")
    prog = P.Seq()
    wr(prog, HA_HMON, CG5, 8, MODE_HYPV)
    wr(prog, HA_HMON, CG5, 9, HA_HMON)
    wr(prog, HA_HMON, CG5, 10, back)
    wr(prog, HA_HMON, CG5, 11, MASK_PATTERN)
    prog.e(P.escape(HA_HMON, 0))
    return P.build_rom(s.resolve(), {
        OFF_FH_HMON: fault_handler(HA_HMON),
        OFF_HMON_PROG: prog.resolve(),
    }), {
        "rd30": MASK_PATTERN,
        "rd31": MASK_PATTERN,
        "mymode": MODE_HYPV, "mycfx": HA_HMON,
    }


def _reserved_case(accesses):
    """Every `accesses[i] = (ha, cg, rc, dst)` raises CFXREG.

    The shared fault handler records the first two faults (rd20..rd22 and
    rd26..rd28), so each generated case carries one or two accesses."""
    s = P.Seq()
    body_setup(s)
    for ha, cg, rc, dst in accesses:
        rd(s, ha, cg, rc, dst)
    s.e(*P.exit_seq(0))
    checks = {"rd25": len(accesses), "mymode": MODE_HYPV}
    for i, (ha, cg, rc, dst) in enumerate(accesses):
        info = (0x7A << 24) | (ha << 18) | (cg << 12) | (rc << 6) | dst
        if i == 0:
            checks["rd20"] = CFXREG
            checks["rd21"] = info
        else:
            checks["rd26"] = CFXREG
            checks["rd27"] = info
    return P.build_rom(s.resolve(), {OFF_FH_HMON: fault_handler(HA_HMON)}), checks


def case_reserved_cg15_a():
    return _reserved_case([(HA_HART, CG15, 6, 30), (HA_HART, CG15, 7, 31)])


def case_reserved_cg15_b():
    return _reserved_case([(HA_HART, CG15, 8, 30), (HA_HART, CG15, 9, 31)])


def case_reserved_cg15_c():
    return _reserved_case([(HA_HART, CG15, 10, 30), (HA_HART, CG15, 11, 31)])


def case_reserved_cg15_d():
    return _reserved_case([(HA_HART, CG15, 12, 30), (HA_HART, CG15, 13, 31)])


def case_reserved_cg8_5():
    return _reserved_case([(HA_HART, CG8, 5, 30), (HA_HART, CG8, 1, 31)])


def case_source_mask_gate():
    """The source `cg16 rc16` mask gates events independently of the monitor
    `cg15 rc3` mask: with TIMER allowed by the running-mode monitor but still
    masked at the source, the event only sets pending; opening the source mask
    enters at the next boundary."""
    s = P.Seq()
    body_setup(s, MASK_TIMER_ONLY)           # monitor allows TIMER (bit15 open)
    wr(s, HA_HART, CG15, 14, MODE_HYPV)
    wr(s, HA_HART, CG15, 15, ROM_BASE + OFF_ASYNC)
    # cg16 rc16 is still reset all-1: arm the timer with the source masked.
    wr(s, HA_HART, CG16, 1, 0, tmp=13)
    wr(s, HA_HART, CG16, 0, 1, tmp=14)
    s.e(P.jump_rel(1))
    s.mark("after_blocked")
    rd(s, HA_HART, CG4, 4, 30)               # no entry yet
    rd(s, HA_HART, CG16, 17, 31)             # event pending at the source
    wr(s, HA_HART, CG16, 16, 0, tmp=14)      # open the source mask
    s.e(P.jump_rel(1))
    s.mark("after_open")
    rd(s, HA_HART, CG4, 4, 32)               # one entry
    rd(s, HA_HART, CG16, 17, 33)             # handler acked
    s.e(*P.exit_seq(0))
    h = P.Seq()
    h.e(P.add_si(25, 1))
    wr(h, HA_HART, CG16, 18, 1)
    h.e(P.escape(HA_HART, 0))
    return P.build_rom(s.resolve(), {
        OFF_FH_HMON: fault_handler(HA_HMON),
        OFF_ASYNC: h.resolve(),
    }), {
        "rd25": 1,
        "rd30": 0, "rd31": 1,
        "rd32": 1, "rd33": 0,
    }


def case_dma_merge_two_completions():
    """Two DMA completions before ack merge into `cg16 rc17` bit0 (not
    counted); the cg16 ack clears only pending, `dma_status` keeps its own
    W1C state."""
    s = P.Seq()
    body_setup(s)
    wr(s, HA_PMEM, CG16, 16, 0, tmp=12)      # open DMA source mask
    _dma_error(s)                            # first completion: ERROR|SIZE
    rd(s, HA_PMEM, CG16, 17, 30)             # bit0
    wr(s, HA_PMEM, CG15, 4, 4, tmp=12)       # dma_status W1C: clear ERROR
    rd(s, HA_PMEM, CG15, 4, 31)              # 0
    _dma_error(s)                            # second completion, not acked yet
    rd(s, HA_PMEM, CG16, 17, 32)             # still bit0 (merged, not counted)
    wr(s, HA_PMEM, CG16, 18, 1, tmp=12)      # ack only the interrupt pending
    rd(s, HA_PMEM, CG16, 17, 33)             # 0
    rd(s, HA_PMEM, CG15, 4, 34)              # ERROR|ERR_CODE still latched
    s.e(*P.exit_seq(0))
    return P.build_rom(s.resolve(), {OFF_FH_HMON: fault_handler(HA_HMON)}), {
        "rd30": 1, "rd31": 0, "rd32": 1, "rd33": 0,
        "rd34": (1 << 2) | (1 << 3),
    }


CASES = {
    "hart_layout": case_hart_layout,
    "hart_layout_reserved": case_hart_layout_reserved,
    "source_layout": case_source_layout,
    "other_cfx_cg16": case_other_cfx_cg16,
    "timer_semantics": case_timer_semantics,
    "async_pending_survives": case_async_pending_survives,
    "async_mask_gate": case_async_mask_gate,
    "multi_source": case_multi_source,
    "dma_ack_vs_status": case_dma_ack_vs_status,
    "escape_rc11_cg15": case_escape_rc11_cg15,
    "reserved_cg15_a": case_reserved_cg15_a,
    "reserved_cg15_b": case_reserved_cg15_b,
    "reserved_cg15_c": case_reserved_cg15_c,
    "reserved_cg15_d": case_reserved_cg15_d,
    "reserved_cg8_5": case_reserved_cg8_5,
    "source_mask_gate": case_source_mask_gate,
    "dma_merge_two_completions": case_dma_merge_two_completions,
}


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def _lasthex(log, pat):
    m = None
    for m in re.finditer(pat, log):
        pass
    return int(m.group(1), 16) if m else None


def _lastdec(log, pat):
    m = None
    for m in re.finditer(pat, log):
        pass
    return int(m.group(1), 10) if m else None


def observe(log):
    o = {}
    for n in range(64):
        o["rd%d" % n] = _lasthex(log, r"RD\[%02d\]: ([0-9a-f]+)" % n)
    o["mymode"] = _lastdec(log, r"MODE: ([0-9]+)")
    o["mycfx"] = _lastdec(log, r"CFXCODE: ([0-9]+)")
    o["pc"] = _lasthex(log, r"PC: ([0-9a-f]+)")
    return o


def judge(got, checks):
    fails = []
    for key, want in checks.items():
        act = got.get(key)
        if isinstance(want, tuple):
            kind = want[0]
            if kind == ">":
                ok = act is not None and act > want[1]
            elif kind == "same":
                ref = got.get("rd%d" % want[1])
                ok = act is not None and ref is not None and act == ref
            else:
                raise SystemExit("bad predicate %r" % (want,))
            shown = repr(want)
        else:
            ok = act == want
            shown = "0x%x" % want if want is not None else "None"
        if not ok:
            fails.append("%s: expected %s actual %s"
                         % (key, shown,
                            "None" if act is None else "0x%x" % act))
    return fails


def report_case(name, got, checks):
    fails = judge(got, checks)
    for f in fails:
        print("    FAIL %s" % f)
    print("  [%s] %-24s %d check(s)" % ("PASS" if not fails else "FAIL",
                                        name, len(checks)))
    return not fails


def self_test(qemu, workdir):
    """Every observation must have a reachable FAIL (mutate one at a time)."""
    bad = 0
    for name in CASES:
        rom, checks = CASES[name]()
        rc, log = P.run(rom, workdir=os.path.join(workdir, name), qemu=qemu)
        if not isinstance(log, str) or rc != 0:
            print("  [FAIL] %-24s control run did not exit cleanly (%r)"
                  % (name, rc))
            bad += 1
            continue
        got = observe(log)
        if judge(got, checks):
            print("  [FAIL] %-24s control run does not match" % name)
            bad += 1
            continue
        missed = []
        for key, want in checks.items():
            mutant = dict(got)
            if isinstance(want, tuple):
                if want[0] == ">":
                    mutant[key] = want[1]
                else:
                    mutant[key] = (got[key] or 0) ^ 1
            else:
                mutant[key] = (want ^ 0x5A) if want is not None else 1
            if not judge(mutant, checks):
                missed.append(key)
        if checks and not judge({}, checks):
            missed.append("<all missing>")
        if missed:
            print("  [FAIL] %-24s unreachable FAIL for: %s"
                  % (name, ", ".join(missed)))
            bad += 1
        else:
            print("  [PASS] %-24s %d/%d checks have a reachable FAIL"
                  % (name, len(checks), len(checks)))
    print("self-test: %s" % ("PASS" if bad == 0 else "FAIL (%d)" % bad))
    return 0 if bad == 0 else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--qemu")
    ap.add_argument("--case")
    ap.add_argument("--workdir")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    qemu = args.qemu or P.default_qemu()
    if not os.path.isfile(qemu):
        print("min_rom_probe_m18qemu009: qemu not found: %s" % qemu,
              file=sys.stderr)
        return 2
    workdir = args.workdir or os.path.join(P.TMP_ROOT, "m18qemu009")
    names = [args.case] if args.case else list(CASES)
    if args.case and args.case not in CASES:
        print("unknown case %r (have: %s)" % (args.case, ", ".join(CASES)),
              file=sys.stderr)
        return 2

    if args.self_test:
        return self_test(qemu, os.path.join(workdir, "selftest"))

    bad = 0
    for name in names:
        rom, checks = CASES[name]()
        rc, log = P.run(rom, workdir=os.path.join(workdir, name), qemu=qemu)
        if not isinstance(log, str):
            print("  [FAIL] %-24s guest did not exit cleanly (%s)" % (name, log))
            bad += 1
            continue
        got = observe(log)
        if rc != 0:
            print("  [FAIL] %-24s guest exit code %r" % (name, rc))
            bad += 1
        if not report_case(name, got, checks):
            bad += 1
    print("summary: %d case(s), %d failure(s)" % (len(names), bad))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
