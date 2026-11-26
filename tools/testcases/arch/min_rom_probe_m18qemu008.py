#!/usr/bin/env python3
"""min_rom_probe_m18qemu008.py — QEMU-side unit probe for the R3 async-escape
model (`m18-qemu-008`).

Judged against the *spec*, not against the implementation:

  * `spec/DADAO-12` §3.1-§3.6  (cg0-cg3 rc14/rc15, cg5 entry record / escape
    intent, cg15 entry record / pending, `escape` legality and rc11 restore)
  * `.tao/adr/adr-0061-async-source-index-and-mask-ownership.md` R3

Covered capability groups (task-book acceptance 1-3):

  layout   cg5 rc0-rc3 write => CFXREG, rc8-rc11 RW, rc11 resets all-1,
           rc4/rc5 cause fields, reserved rc6/rc7/rc14 => CFXREG;
           cg0-cg3 rc14/rc15 effective, rc8/rc10 => CFXREG;
           cg15 rc0-rc5 write-ignored, rc14 reset 2 / rc15 reset 0, rc14/rc15
           RW, rc6/rc8/rc10/rc13 => CFXREG.
  entry    a synchronous `trap` fills the target cfx's cg5 rc0-rc5 + rc8-rc11
           (rc11 = the pre-entry running-mode monitor's cg15 rc3 word);
           an async entry fills cg15 rc0-rc5 and cfx_hart's own cg5 rc8-rc11
           and leaves cfx_hart cg5 rc0-rc3 untouched.
  escape   normal return (mode/cfx/ip/mask), rc11 restored as one whole word,
           `imms18 != 0` => ILLI, wrong cfxha / unimplemented target cfx /
           privilege escalation => CFXESC, `escape_num` +1.

The body is emitted as instruction words (no assembler), so the probe is
independent of the toolchain's `escape` surface syntax (`m18-llvm-002`).

Observation channel: the final `-d cpu` dump (RD registers + MODE/CFXCODE/PC).
Every case is one QEMU process; a case is PASS only when all its assertions
hold.  Any mismatch exits non-zero (`FAIL`).

Usage:
  DADAO_TEST_PROFILE=vast min_rom_probe_m18qemu008.py --qemu QEMU [--case NAME]
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
HA_HMON = 3
HA_HART = 15
HA_PMEM = 32

CG2 = 2
CG3 = 3
CG4 = 4
CG5 = 5
CG8 = 8
CG15 = 15
CG16 = 16

CFXTRAP = 1 << 0
CFXREG = 1 << 2
CFXESC = 1 << 3
ILLI = 1 << 8

MODE_SUPV = 2
MODE_HYPV = 3

MASK_BASE = 0xFFFFFFFFFFFF7FFF      # hypv monitor mask: only TIMER (bit 15) open
PATTERN_WHOLE = 0x0000000000008000  # 0 where the old mask had 1s and vice versa

# Body-relative byte offsets of the handler blocks (the body stays below 0x400).
OFF_FH_HMON = 0x400
OFF_FH_UMON = 0x500
OFF_FH_HART = 0x600
OFF_ASYNC = 0x700
OFF_UMON_PROG = 0x780

ROM_BASE = P.ROM_BASE

SPEC = "spec/DADAO-12-SEE-主管系统运行环境.md"


class OracleError(Exception):
    pass


def _repo_root():
    # tools/testcases/arch -> repository root
    return os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))


def mode_facts():
    """Derive the `<mode>_switch_run_mode` / `<mode>_excp_vector` slots, the
    switch reset value and the reserved holes of cg0-cg3 from `DADAO-12`
    §3.1-§3.4 (the oracle is the spec table, never a literal here)."""
    path = os.path.join(_repo_root(), SPEC)
    try:
        text = open(path, encoding="utf-8").read()
    except OSError as exc:
        raise OracleError("cannot read %s: %s" % (path, exc))
    cells = {}
    for cg, rc, name, regname, init, _acc, note in re.findall(
            r"^\|\s*([0-3])\s*\|\s*(\d+)\s*\|\s*([^|]*?)\s*\|\s*"
            r"([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*"
            r"([^|]*?)\s*\|",
            text, re.M):
        cells.setdefault(int(cg), []).append(
            (int(rc), name.strip(), regname.strip(), init.strip(), note))
    facts = {}
    for cg in range(4):
        if cg not in cells:
            raise OracleError("spec §3.%d: cg%d table not found" % (cg + 1, cg))
        f = {"switch": None, "vector": None, "init": None,
             "reserved": set(), "vec_low2": False}
        for rc, name, regname, init, note in cells[cg]:
            if "switch_run_mode" in regname:
                f["switch"] = rc
                m = re.match(r"(\d+)", init)
                if not m:
                    raise OracleError("spec §3.%d: switch reset %r" % (cg + 1, init))
                f["init"] = int(m.group(1))
            elif "excp_vector" in regname:
                f["vector"] = rc
                # §3.4 states "写入忽略低 2 位" for hypv; cg0-cg2 carry no such
                # sentence, so the probe must not assert masking there.
                f["vec_low2"] = "低 2 位" in note
            elif name == "reserved":
                f["reserved"].add(rc)
        if None in (f["switch"], f["vector"], f["init"]):
            raise OracleError("spec §3.%d: switch/vector/reset row incomplete"
                              % (cg + 1))
        for rc in (8, 10):
            if rc not in f["reserved"]:
                raise OracleError("spec §3.%d: rc%d must be a reserved hole"
                                  % (cg + 1, rc))
        facts[cg] = f
    return facts


MODE_FACTS = mode_facts()


def addr(seq, label):
    return ROM_BASE + 4 * seq.lab[label]


# ---------------------------------------------------------------------------
# Reusable machine-code blocks
# ---------------------------------------------------------------------------

def fault_handler(ha):
    """Record the first/second fault of `ha` and return past the faulting insn.

    rd25 = fault count, first fault -> rd20/21/22 (cause/info/ip), later ones ->
    rd26/27/28.  Returning past the faulting instruction is legal because
    `cfx_enter` has just rewritten the escape intent for this cfx.
    """
    s = P.Seq()
    s.b("z", 25, "first")
    s.e(P.cfx2rd(ha, CG5, 4, 26))
    s.e(P.cfx2rd(ha, CG5, 5, 27))
    s.e(P.cfx2rd(ha, CG5, 2, 28))
    s.b("z", 0, "ret")                      # rd0 == 0: unconditional
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
    """Return to the body (hmon/hypv) from an in-cfx program of `ha`."""
    s = P.Seq()
    s.e(*P.load_rd(23, MODE_HYPV))
    s.e(P.cfx2rc(ha, CG5, 8, 23))
    s.e(*P.load_rd(23, HA_HMON))
    s.e(P.cfx2rc(ha, CG5, 9, 23))
    s.e(*P.load_rd(23, back_addr))
    s.e(P.cfx2rc(ha, CG5, 10, 23))
    s.e(P.escape(ha, 0))
    return s.resolve()


def body_setup(s):
    """Install the hmon fault handler and the known hypv monitor mask."""
    s.e(*P.load_rd(19, ROM_BASE + OFF_FH_HMON))
    s.e(P.cfx2rc(HA_HMON, CG3, 15, 19))
    s.e(*P.load_rd(10, MASK_BASE))
    s.e(P.cfx2rc(HA_HMON, CG15, 3, 10))
    wr(s, HA_PMEM, CG16, 18, 1)      # ack the prelude's DMA completion


def rd(s, ha, cg, rc, dst):
    s.e(P.cfx2rd(ha, cg, rc, dst))


def wr(s, ha, cg, rc, val, tmp=23):
    s.e(*P.load_rd(tmp, val))
    s.e(P.cfx2rc(ha, cg, rc, tmp))


def umon_case(illegal, obs=(), checks=None, extra=None, pre_obs=()):
    """Body traps into cfx_umon; the umon program runs `illegal` (whose fault
    is recorded in rd20/21/22) and `extra` (if any), then returns to `back`."""
    body = P.Seq()
    body_setup(body)
    for ha, cg, rc, dst in pre_obs:
        rd(body, ha, cg, rc, dst)
    wr(body, HA_UMON, CG3, 15, ROM_BASE + OFF_UMON_PROG)
    body.e(P.trap(HA_UMON, 0x1234))
    body.mark("back")
    for ha, cg, rc, dst in obs:
        rd(body, ha, cg, rc, dst)
    body.e(*P.exit_seq(0))
    back_addr = addr(body, "back")

    prog = P.Seq()
    prog.e(*P.load_rd(23, ROM_BASE + OFF_FH_UMON))
    prog.e(P.cfx2rc(HA_UMON, CG3, 15, 23))
    prog.e(*illegal)
    if extra:
        prog.e(*extra(back_addr))
    prog.e(*ret_prog(HA_UMON, back_addr))
    handlers = {
        OFF_FH_HMON: fault_handler(HA_HMON),
        OFF_FH_UMON: fault_handler(HA_UMON),
        OFF_UMON_PROG: prog.resolve(),
    }
    return P.build_rom(body.resolve(), handlers), checks or {}


# ---------------------------------------------------------------------------
# Cases: return (rom, checks).  A check value may be a plain number, `(">", n)`
# or `("same", N)` (equal to the RD[N] slot).
# ---------------------------------------------------------------------------

def case_cg5_reset_rw():
    # cfx_hmon itself was already entered by the prelude's power->hmon trap, so
    # the *reset* values are observed on cfx_umon (never entered in this run).
    s = P.Seq()
    body_setup(s)
    for rc, dst in ((0, 30), (1, 31), (2, 32), (3, 33), (4, 34), (5, 35),
                    (8, 11), (9, 12), (10, 13), (11, 10)):
        rd(s, HA_UMON, CG5, rc, dst)
    # Escape intent is RW on the current cfx (self access in hypv).
    wr(s, HA_HMON, CG5, 8, MODE_HYPV)
    wr(s, HA_HMON, CG5, 9, 5)
    wr(s, HA_HMON, CG5, 10, 0x123456789ABCDEFD)
    wr(s, HA_HMON, CG5, 11, 0x0123456789ABCDEF)
    rd(s, HA_HMON, CG5, 8, 36)
    rd(s, HA_HMON, CG5, 9, 37)
    rd(s, HA_HMON, CG5, 10, 38)
    rd(s, HA_HMON, CG5, 11, 39)
    s.e(*P.exit_seq(0))
    return P.build_rom(s.resolve(), {OFF_FH_HMON: fault_handler(HA_HMON)}), {
        "rd10": 0xFFFFFFFFFFFFFFFF, "rd11": 0, "rd12": 0, "rd13": 0,
        "rd30": 0, "rd31": 0, "rd32": 0, "rd33": 0, "rd34": 0, "rd35": 0,
        "rd36": MODE_HYPV, "rd37": 5,
        "rd38": 0x123456789ABCDEFD & 0x0000FFFFFFFFFFFF & ~3,
        "rd39": 0x0123456789ABCDEF, "rd25": 0,
    }


def _cg5_ro_case(rc):
    s = P.Seq()
    body_setup(s)
    wr(s, HA_HMON, CG5, rc, 1)
    s.e(*P.exit_seq(0))
    return P.build_rom(s.resolve(), {OFF_FH_HMON: fault_handler(HA_HMON)}), {
        "rd20": CFXREG,
        "rd21": (0x7B << 24) | (HA_HMON << 18) | (CG5 << 12) | (rc << 6) | 23,
        "rd25": 1,
    }


def case_cg5_ro0():
    return _cg5_ro_case(0)


def case_cg5_ro1():
    return _cg5_ro_case(1)


def case_cg5_ro2():
    return _cg5_ro_case(2)


def case_cg5_ro3():
    return _cg5_ro_case(3)


def case_cg5_reserved():
    s = P.Seq()
    body_setup(s)
    rd(s, HA_HMON, CG5, 6, 14)
    rd(s, HA_HMON, CG5, 7, 15)
    s.e(*P.exit_seq(0))
    return P.build_rom(s.resolve(), {OFF_FH_HMON: fault_handler(HA_HMON)}), {
        "rd20": CFXREG,
        "rd21": (0x7A << 24) | (HA_HMON << 18) | (CG5 << 12) | (6 << 6) | 14,
        "rd26": CFXREG,
        "rd27": (0x7A << 24) | (HA_HMON << 18) | (CG5 << 12) | (7 << 6) | 15,
        "rd25": 2,
    }


def case_cg5_rc14():
    s = P.Seq()
    body_setup(s)
    rd(s, HA_HMON, CG5, 14, 14)
    s.e(*P.exit_seq(0))
    return P.build_rom(s.resolve(), {OFF_FH_HMON: fault_handler(HA_HMON)}), {
        "rd20": CFXREG,
        "rd21": (0x7A << 24) | (HA_HMON << 18) | (CG5 << 12) | (14 << 6) | 14,
        "rd25": 1,
    }


def _mode_slots_case(cg):
    """One cg row: rc14 switch round-trip, rc15 vector round-trip, rc8/rc10
    reserved => CFXREG.  Slots/reset/low-2-bit rule are all spec-derived."""
    f = MODE_FACTS[cg]
    sw, vec, init = f["switch"], f["vector"], f["init"]
    other = (init + 1) & 0x3
    # §3.4 states "写入忽略低 2 位" for hypv only; cg0-cg2 say nothing about the
    # low bits, so there the probe writes an already-aligned value and asserts
    # an exact RW round-trip (no implementation-only masking claim).
    raw_vec = 0xFFFFFFFFFFFFFD if f["vec_low2"] else 0xFFFFFFFFFFFFFC
    vec_expect = (raw_vec & ~0x3) if f["vec_low2"] else raw_vec
    s = P.Seq()
    body_setup(s)
    rd(s, HA_UMON, cg, sw, 10)                  # reset value (§3.x init cell)
    wr(s, HA_UMON, cg, sw, other)
    rd(s, HA_UMON, cg, sw, 11)                  # write lands
    wr(s, HA_UMON, cg, sw, init)                # restore
    wr(s, HA_UMON, cg, vec, raw_vec)
    rd(s, HA_UMON, cg, vec, 12)                 # low 2 bits per §3.4 only
    rd(s, HA_UMON, cg, 8, 13)                   # rc8 reserved => CFXREG
    rd(s, HA_UMON, cg, 10, 18)                  # rc10 reserved => CFXREG
    s.e(*P.exit_seq(0))
    info = lambda rc, dst: ((0x7A << 24) | (HA_UMON << 18) |
                            (cg << 12) | (rc << 6) | dst)
    return P.build_rom(s.resolve(), {OFF_FH_HMON: fault_handler(HA_HMON)}), {
        "rd10": init, "rd11": other, "rd12": vec_expect,
        "rd20": CFXREG, "rd21": info(8, 13),
        "rd26": CFXREG, "rd27": info(10, 18),
        "rd25": 2,
    }


def case_mode_slots_cg0():
    return _mode_slots_case(0)


def case_mode_slots_cg1():
    return _mode_slots_case(1)


def case_mode_slots_cg2():
    return _mode_slots_case(2)


def case_mode_slots_cg3():
    return _mode_slots_case(3)


def case_cg15_layout():
    s = P.Seq()
    body_setup(s)
    rd(s, HA_HART, CG15, 14, 10)     # reset 2 (supv)
    rd(s, HA_HART, CG15, 15, 11)     # reset 0
    wr(s, HA_HART, CG15, 14, 1)
    rd(s, HA_HART, CG15, 14, 12)
    wr(s, HA_HART, CG15, 15, 0xFFFFFFFFFFFFFD)
    rd(s, HA_HART, CG15, 15, 13)     # low 2 bits ignored
    wr(s, HA_HART, CG15, 14, MODE_SUPV)
    wr(s, HA_HART, CG15, 15, 0)
    for rc in range(6):            # rc0-rc5 writes: ignored, no exception
        wr(s, HA_HART, CG15, rc, 0xDEADBEEF)
    for rc, dst in ((0, 30), (1, 31), (2, 32), (3, 33), (4, 34), (5, 35)):
        rd(s, HA_HART, CG15, rc, dst)
    s.e(*P.exit_seq(0))
    return P.build_rom(s.resolve(), {OFF_FH_HMON: fault_handler(HA_HMON)}), {
        "rd10": MODE_SUPV, "rd11": 0, "rd12": 1,
        "rd13": 0xFFFFFFFFFFFFFD & 0x0000FFFFFFFFFFFF & ~3,
        "rd30": 0, "rd31": 0, "rd32": 0, "rd33": 0, "rd34": 0, "rd35": 0,
        "rd25": 0,
    }


def _cg15_reserved_case(rc_a, dst_a, rc_b, dst_b, count):
    s = P.Seq()
    body_setup(s)
    rd(s, HA_HART, CG15, rc_a, dst_a)
    rd(s, HA_HART, CG15, rc_b, dst_b)
    s.e(*P.exit_seq(0))
    return P.build_rom(s.resolve(), {OFF_FH_HMON: fault_handler(HA_HMON)}), {
        "rd20": CFXREG,
        "rd21": (0x7A << 24) | (HA_HART << 18) | (CG15 << 12) | (rc_a << 6) | dst_a,
        "rd26": CFXREG,
        "rd27": (0x7A << 24) | (HA_HART << 18) | (CG15 << 12) | (rc_b << 6) | dst_b,
        "rd25": count,
    }


def case_cg15_reserved_a():
    # rc6 list position (was switch) and rc8 (old capture vector) are reserved.
    return _cg15_reserved_case(6, 14, 8, 15, 2)


def case_cg15_reserved_b():
    # rc10 (old capture vector) and rc13 are reserved.
    return _cg15_reserved_case(10, 17, 13, 18, 2)


def case_sync_entry():
    s = P.Seq()
    body_setup(s)
    wr(s, HA_UMON, CG3, 15, ROM_BASE + OFF_UMON_PROG)
    s.mark("trap_ip")
    s.e(P.trap(HA_UMON, 0x1234))
    s.mark("after_trap")
    rd(s, HA_UMON, CG5, 0, 30)
    rd(s, HA_UMON, CG5, 1, 31)
    rd(s, HA_UMON, CG5, 2, 32)
    rd(s, HA_UMON, CG5, 3, 33)
    rd(s, HA_UMON, CG5, 4, 34)
    rd(s, HA_UMON, CG5, 5, 35)
    rd(s, HA_UMON, CG5, 8, 36)
    rd(s, HA_UMON, CG5, 9, 37)
    rd(s, HA_UMON, CG5, 10, 38)
    rd(s, HA_UMON, CG5, 11, 39)
    rd(s, HA_UMON, CG4, 5, 40)      # escape_num
    rd(s, HA_HMON, CG15, 3, 41)      # restored mask
    s.e(*P.exit_seq(0))
    prog = P.Seq()
    prog.e(P.add_si(25, 1))
    prog.e(P.cfx2rd(HA_UMON, CG5, 2, 23))
    prog.e(P.cfx2rd(HA_UMON, CG5, 2, 44))   # entry ip before rc10 is rewritten
    prog.e(P.add_si(23, 4))
    prog.e(P.cfx2rc(HA_UMON, CG5, 10, 23))
    prog.e(P.escape(HA_UMON, 0))
    handlers = {
        OFF_FH_HMON: fault_handler(HA_HMON),
        OFF_UMON_PROG: prog.resolve(),
    }
    return P.build_rom(s.resolve(), handlers), {
        "mymode": MODE_HYPV,
        "mycfx": HA_HMON,
        "rd30": MODE_HYPV, "rd31": HA_HMON,
        "rd32": ROM_BASE + 4 * s.lab["trap_ip"],
        "rd33": MASK_BASE,
        "rd34": CFXTRAP,
        "rd35": (0x7F << 24) | (HA_UMON << 18) | 0x1234,
        "rd44": ROM_BASE + 4 * s.lab["trap_ip"],
        "rd36": MODE_HYPV, "rd37": HA_HMON,
        "rd38": ROM_BASE + 4 * s.lab["trap_ip"] + 4,   # program's rc10 write
        "rd39": MASK_BASE,
        "rd40": 1, "rd41": MASK_BASE,
        "rd25": 1,
    }


def case_escape_imms18():
    rom, _ = umon_case([P.escape(HA_UMON, 1)])
    return rom, {
        "rd20": ILLI,
        "rd21": (0x7E << 24) | (HA_UMON << 18) | 1,
        "rd25": 1,
        "mymode": MODE_HYPV, "mycfx": HA_HMON,
    }


def case_escape_wrong_cfx():
    rom, _ = umon_case([P.escape(HA_HMON, 0)])
    return rom, {
        "rd20": CFXESC,
        "rd21": (0x7E << 24) | (HA_HMON << 18),
        "rd25": 1,
        "mymode": MODE_HYPV, "mycfx": HA_HMON,
    }


def case_escape_unimpl_cfx():
    def set_target(back):
        s = P.Seq()
        s.e(*P.load_rd(23, 6))           # cfx 6: reserved, not implemented
        s.e(P.cfx2rc(HA_UMON, CG5, 9, 23))
        s.e(P.escape(HA_UMON, 0))
        return s.resolve()

    rom, _ = umon_case([P.swym()], extra=set_target)
    return rom, {
        "rd20": CFXESC,
        "rd21": (0x7E << 24) | (HA_UMON << 18),
        "rd25": 1,
        "mymode": MODE_HYPV, "mycfx": HA_HMON,
    }


def case_escape_rc11_restore():
    def write_intent(back):
        s = P.Seq()
        s.e(*P.load_rd(23, MODE_HYPV))
        s.e(P.cfx2rc(HA_UMON, CG5, 8, 23))
        s.e(*P.load_rd(23, HA_HMON))
        s.e(P.cfx2rc(HA_UMON, CG5, 9, 23))
        s.e(*P.load_rd(23, back))
        s.e(P.cfx2rc(HA_UMON, CG5, 10, 23))
        s.e(*P.load_rd(23, PATTERN_WHOLE))
        s.e(P.cfx2rc(HA_UMON, CG5, 11, 23))
        s.e(P.escape(HA_UMON, 0))
        return s.resolve()

    rom, _ = umon_case([P.swym()], pre_obs=[(HA_HMON, CG15, 3, 30)],
                       obs=[(HA_HMON, CG15, 3, 31)], extra=write_intent)
    return rom, {
        "rd30": MASK_BASE,          # before the escape (body_setup)
        "rd31": PATTERN_WHOLE,      # after: rc11 restored as one whole word
        "rd25": 0,                  # no fault: the entry is not a fault
        "mymode": MODE_HYPV, "mycfx": HA_HMON,
    }


def _arm_timer(s):
    s.e(*P.load_rd(13, 0))
    s.e(P.cfx2rc(HA_HART, CG16, 16, 13))     # open the source mask
    s.e(*P.load_rd(13, 1))
    s.e(P.cfx2rc(HA_HART, CG16, 1, 13))      # timer_cmp = 1 (already expired)
    s.e(*P.load_rd(14, 1))
    s.e(P.cfx2rc(HA_HART, CG16, 0, 14))      # ENABLE


def case_async_entry():
    s = P.Seq()
    body_setup(s)
    rd(s, HA_HMON, CG15, 3, 30)              # mask used for the delivery
    wr(s, HA_HART, CG15, 14, MODE_HYPV)      # entry mode: keep hypv (returnable)
    wr(s, HA_HART, CG15, 15, ROM_BASE + OFF_ASYNC)
    _arm_timer(s)
    s.e(P.jump_rel(1))                      # end the TB: deliver at the boundary
    s.mark("after_async")
    rd(s, HA_HART, CG15, 0, 31)
    rd(s, HA_HART, CG15, 1, 32)
    rd(s, HA_HART, CG15, 2, 33)
    rd(s, HA_HART, CG15, 3, 34)
    rd(s, HA_HART, CG15, 4, 35)
    rd(s, HA_HART, CG15, 5, 36)
    rd(s, HA_HART, CG5, 0, 37)              # async writes only rc8-rc11
    rd(s, HA_HART, CG5, 1, 38)
    rd(s, HA_HART, CG5, 2, 39)
    rd(s, HA_HART, CG5, 3, 40)
    rd(s, HA_HART, CG5, 8, 41)
    rd(s, HA_HART, CG5, 9, 42)
    rd(s, HA_HART, CG5, 10, 43)
    rd(s, HA_HART, CG5, 11, 44)
    rd(s, HA_HART, CG4, 4, 45)              # excp_async_num
    rd(s, HA_HART, CG4, 5, 46)              # escape_num
    s.e(*P.exit_seq(0))
    h = P.Seq()
    h.e(P.add_si(25, 1))
    h.e(*P.load_rd(10, 1))
    h.e(P.cfx2rc(HA_HART, CG16, 18, 10))     # ack TIMER before escape
    h.e(P.escape(HA_HART, 0))
    return P.build_rom(s.resolve(), {
        OFF_FH_HMON: fault_handler(HA_HMON),
        OFF_ASYNC: h.resolve(),
    }), {
        "rd25": 1,
        "rd30": MASK_BASE,
        "rd31": MODE_HYPV, "rd32": HA_HMON,
        "rd34": MASK_BASE, "rd35": 1 << 15, "rd36": 0,
        "rd37": 0, "rd38": 0, "rd39": 0, "rd40": 0,
        "rd41": MODE_HYPV, "rd42": HA_HMON,
        "rd43": (">", ROM_BASE),
        "rd44": MASK_BASE,
        "rd45": 1, "rd46": 1,
        "rd33": ("same", 43),               # cg15 prev ip == escape ip
        "mymode": MODE_HYPV, "mycfx": HA_HMON,
    }


def case_async_escalation():
    s = P.Seq()
    body_setup(s)
    # rc14 keeps its reset value 2 (supv): the async entry lands in supv, so the
    # `escape cfx_hart` back to hypv is privilege escalation => CFXESC.
    wr(s, HA_HART, CG15, 15, ROM_BASE + OFF_ASYNC)
    wr(s, HA_HART, CG2, 15, ROM_BASE + OFF_FH_HART)   # supv vector of cfx_hart
    # The CFXESC handler runs in supv; it needs cfx_hart cg5 (DADAO-13 §1:
    # cg_reg_deleg bit = 0 allows, so 0x8 opens every cg except the fixed bit3).
    wr(s, HA_HART, CG3, 12, 0x8)
    _arm_timer(s)
    s.e(P.jump_rel(1))
    s.mark("after_async")
    rd(s, HA_HART, CG4, 4, 30)              # excp_async_num
    s.e(*P.exit_seq(0))
    h = P.Seq()
    h.e(P.add_si(25, 1))
    h.e(*P.load_rd(10, 1))
    h.e(P.cfx2rc(HA_HART, CG16, 18, 10))    # ack TIMER before the illegal escape
    h.e(P.escape(HA_HART, 0))               # illegal: hypv > supv
    # Reached after the CFXESC return (still cfx_hart/supv): read the counter
    # (self access; cg_reg_deleg bit4 = 0 opens it for supv) and exit.
    h.e(P.cfx2rd(HA_HART, CG4, 4, 30))
    h.e(*P.exit_seq(0))
    return P.build_rom(s.resolve(), {
        OFF_FH_HMON: fault_handler(HA_HMON),
        OFF_FH_HART: fault_handler(HA_HART),
        OFF_ASYNC: h.resolve(),
    }), {
        "rd25": 2,                  # 1 async entry + 1 recorded fault
        "rd26": CFXESC,             # second fault of the handler's counter
        "rd27": (0x7E << 24) | (HA_HART << 18),
        "rd30": 1,                  # excp_async_num: one capture
        "mymode": MODE_SUPV, "mycfx": HA_HART,
    }


CASES = {
    "cg5_reset_rw": case_cg5_reset_rw,
    "cg5_ro0": case_cg5_ro0,
    "cg5_ro1": case_cg5_ro1,
    "cg5_ro2": case_cg5_ro2,
    "cg5_ro3": case_cg5_ro3,
    "cg5_reserved": case_cg5_reserved,
    "cg5_rc14": case_cg5_rc14,
    "mode_slots_cg0": case_mode_slots_cg0,
    "mode_slots_cg1": case_mode_slots_cg1,
    "mode_slots_cg2": case_mode_slots_cg2,
    "mode_slots_cg3": case_mode_slots_cg3,
    "cg15_layout": case_cg15_layout,
    "cg15_reserved_a": case_cg15_reserved_a,
    "cg15_reserved_b": case_cg15_reserved_b,
    "sync_entry": case_sync_entry,
    "escape_imms18": case_escape_imms18,
    "escape_wrong_cfx": case_escape_wrong_cfx,
    "escape_unimpl_cfx": case_escape_unimpl_cfx,
    "escape_rc11_restore": case_escape_rc11_restore,
    "async_entry": case_async_entry,
    "async_escalation": case_async_escalation,
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
    """Return the list of failed checks (empty = pass)."""
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
    print("  [%s] %-22s %d check(s)" % ("PASS" if not fails else "FAIL",
                                        name, len(checks)))
    return not fails


def self_test(qemu, workdir):
    """Every observation must be able to fail: run each case, then break each
    expected value one at a time and require the judge to notice."""
    bad = 0
    for name in CASES:
        rom, checks = CASES[name]()
        rc, log = P.run(rom, workdir=os.path.join(workdir, name), qemu=qemu)
        if not isinstance(log, str) or rc != 0:
            print("  [FAIL] %-22s control run did not exit cleanly (%r)"
                  % (name, rc))
            bad += 1
            continue
        got = observe(log)
        if judge(got, checks):
            print("  [FAIL] %-22s control run does not match" % name)
            bad += 1
            continue
        missed = []
        for key, want in checks.items():
            mutant = dict(got)
            if isinstance(want, tuple):
                if want[0] == ">":
                    mutant[key] = want[1] - 1
                else:                       # "same": break the reference
                    mutant[key] = (got[key] or 0) ^ 1
            else:
                mutant[key] = (want ^ 0x5A) if want is not None else 1
            if not judge(mutant, checks):
                missed.append(key)
        # an empty observation must always fail
        if checks and not judge({}, checks):
            missed.append("<all missing>")
        if missed:
            print("  [FAIL] %-22s unreachable FAIL for: %s"
                  % (name, ", ".join(missed)))
            bad += 1
        else:
            print("  [PASS] %-22s %d/%d checks have a reachable FAIL"
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
        print("min_rom_probe_m18qemu008: qemu not found: %s" % qemu,
              file=sys.stderr)
        return 2
    workdir = args.workdir or os.path.join(P.TMP_ROOT, "m18qemu008")
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
            print("  [FAIL] %-22s guest did not exit cleanly (%s)" % (name, log))
            bad += 1
            continue
        got = observe(log)
        if rc != 0:
            print("  [FAIL] %-22s guest exit code %r" % (name, rc))
            bad += 1
        if not report_case(name, got, checks):
            bad += 1
    print("summary: %d case(s), %d failure(s)" % (len(names), bad))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
