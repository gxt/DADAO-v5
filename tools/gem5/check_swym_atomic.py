#!/usr/bin/env python3
"""``swym N`` cycle-count and interrupt-atomicity probe (m19-gem5-001).

Runs one Vast FS BootROM image on gem5 ``--cpu-type timing --wuming-cycles``
and reports through the semihosting exit code (0 = pass).

Contract checked (``spec/SimRISC-12 §2`` / ``.tao/contracts/contract-isa
§13.1``, user ruling 2026-11-27):

  * total cycles = ``1 + N`` with ``N = immu18[11:0]``.  Measured from
    ``cfx_hart cg8 rc2`` (cycle == ns, 1 GHz) around ``swym 0``/``swym 1``/
    ``swym 4095`` in the same run: the ``swym 0`` delta is the per-instruction
    baseline, so ``d(1) - d(0)`` must be 1 and ``d(4095) - d(0)`` must be 4095
    (self-calibrating: no hand-written absolute cycle count);
  * atomic: a TIMER that expires *inside* the ``swym 4095`` window is not
    taken mid-instruction.  The async entry must land on the instruction
    boundary after the ``swym`` (``cfx_hart cg15 rc2`` == the address right
    after it) and no earlier than ``t0 + 4095``; the handler acks the source,
    records the capture and returns with ``escape cfx_hart``.

Exit codes: 0 pass; 0xD1/0xD2 cycle delta wrong (1 / 4095); 0xD3 the interrupt
was never taken; 0xD4 entry IP is not the boundary after ``swym``; 0xD5 entry
came before the 1 + N window ended; 0xD6 handler entered more than once.
Non-guest gem5 stops (fault/timeout) are reported as failures.

The image is built with the shared Vast probe prelude
(``tools/testcases/arch/node_probe_prelude.py``); gem5 FS is driven through
the QEMU-compatibility shim ``tools/testcases/parity/qemu_gem5_shim.py`` so
this probe uses the same loader/BootROM path as the arch tests.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_REPO = _HERE.parents[2]

for _sub in (("tools", "testcases", "arch"), ("tools", "testcases", "lib"),
             ("tools", "infra")):
    _p = str(_REPO / Path(*_sub))
    if _p not in sys.path:
        sys.path.insert(0, _p)

import node_probe_prelude as P  # noqa: E402

GEM5_DEFAULT = _REPO / ".work/source/gem5/build/DADAO/gem5.opt"
GEM5_CONFIG_DEFAULT = _REPO / ".work/source/gem5/configs/dadao/fs.py"
SHIM = _REPO / "tools/testcases/parity/qemu_gem5_shim.py"
WORK_DEFAULT = _REPO / ".dadao/tests/arch/probes/swym_atomic"

SCRATCH = 0x7FF0_2000      # RAM, inside the prelude's identity map
HANDLER_OFF = 0x800        # body-relative; the body must end before this
HANDLER_ADDR = P.ROM_BASE + HANDLER_OFF

# The timer must expire inside the swym 4095 window but well after the body
# has reached the swym (the setup between t0 and the swym is ~20 instructions).
TIMER_DELAY = 2047

RC_OK = 0
RC_D1 = 0xD1
RC_D2 = 0xD2
RC_NO_ENTRY = 0xD3
RC_BAD_IP = 0xD4
RC_EARLY = 0xD5
RC_REENTRY = 0xD6


# ---------------------------------------------------------------------------
# Instruction encoders (contracts/opcodes.yaml); the prelude covers the rest.
# ---------------------------------------------------------------------------

def swym_n(immu18: int) -> int:
    return 0x4788_0000 | (immu18 & 0x3FFFF)


def or_o(rdhb: int, rdhc: int, rdhd: int) -> int:
    """or.o rdhb, rdhc, rdhd (OPC-octa, ha=0x09) -- rd copy."""
    return (0x40 << 24) | (0x09 << 18) | (rdhb << 12) | (rdhc << 6) | rdhd


def add_o_bbd(rbhb: int, rbhc: int, rdhd: int) -> int:
    """add.o rbhb, rbhc, rdhd (OPC-octa, ha=0x30) -- rb dst."""
    return (0x40 << 24) | (0x30 << 18) | (rbhb << 12) | (rbhc << 6) | rdhd


def sub_o_bbd(rbhb: int, rbhc: int, rdhd: int) -> int:
    """sub.o rbhb, rbhc, rdhd (OPC-octa, ha=0x31): rbHc - rdHd -> rbHb."""
    return (0x40 << 24) | (0x31 << 18) | (rbhb << 12) | (rbhc << 6) | rdhd


def sub_o_dbb(rdhb: int, rbhc: int, rbhd: int) -> int:
    """sub.o rdhb, rbhc, rbhd (OPC-octa, ha=0x33): rbHc - rbHd -> rdHb."""
    return (0x40 << 24) | (0x33 << 18) | (rdhb << 12) | (rbhc << 6) | rbhd


def cmp_uo_rd(rdhb: int, rdhc: int, rdhd: int) -> int:
    """cmp.uo rdhb, rdhc, rdhd (OPC-octa, ha=0x2A): -1/0/1."""
    return (0x40 << 24) | (0x2A << 18) | (rdhb << 12) | (rdhc << 6) | rdhd


def cmp_uo_dbb(rdhb: int, rbhc: int, rbhd: int) -> int:
    """cmp.uo rdhb, rbhc, rbhd (OPC-octa, ha=0x32): -1/0/1."""
    return (0x40 << 24) | (0x32 << 18) | (rdhb << 12) | (rbhc << 6) | rbhd


def build_rom(mutate: str = "none", skip_cycles: bool = False) -> bytes:
    """Build the probe.  `mutate` is the harness self-check knob: it breaks
    one *expectation* (never the DUT) so the corresponding failure path must
    be reached; `skip_cycles` isolates the interrupt phase."""
    seq = P.Seq()

    # rb20 = 0 constant (rd -> rb copies use `add.o rbX, rb20, rdY`).
    seq.e(P.set_zw_rb(20, 0, 0))

    if not skip_cycles:
        # ---- phase 1: total = 1 + N, measured around three swym forms ---
        seq.e(P.cfx2rd(15, 8, 2, 10))       # c0
        seq.e(swym_n(0))
        seq.e(P.cfx2rd(15, 8, 2, 11))       # c1
        seq.e(swym_n(1))
        seq.e(P.cfx2rd(15, 8, 2, 12))       # c2
        seq.e(swym_n(4095))
        seq.e(P.cfx2rd(15, 8, 2, 13))       # c3

        # Copy the counters into rb (add.o rb, rb20=0, rd), then take the
        # differences with sub.o's rd-destination form.
        seq.e(add_o_bbd(1, 20, 10))         # rb1 = c0
        seq.e(add_o_bbd(2, 20, 11))         # rb2 = c1
        seq.e(add_o_bbd(3, 20, 12))         # rb3 = c2
        seq.e(add_o_bbd(4, 20, 13))         # rb4 = c3
        seq.e(sub_o_dbb(8, 2, 1))           # rd8 = d0
        seq.e(sub_o_dbb(9, 3, 2))           # rd9 = d1
        seq.e(sub_o_dbb(10, 4, 3))          # rd10 = d2

        # Publish the deltas for the evidence dump (SCRATCH+24..40).
        seq.e(*P.load_rb(21, SCRATCH))
        seq.e(P.st_o(8, 21, 24), P.st_o(9, 21, 32), P.st_o(10, 21, 40))

        seq.e(or_o(11, 8, 8))               # rd11 = d0 + 1
        seq.e(P.add_si(11, 1))
        seq.b("ne", 9, "fail_d1", 11)
        seq.e(or_o(12, 8, 8))               # rd12 = d0 + 4095
        seq.e(P.add_si(12, 4095))
        seq.b("ne", 10, "fail_d2", 12)

    # ---- phase 2: a TIMER expiring inside swym 4095 ---------------------
    seq.e(P.cfx2rd(15, 8, 2, 5))        # t0
    seq.e(*P.load_rd(6, 3))
    seq.e(P.cfx2rc(15, 15, 14, 6))      # entry run mode = hypv
    seq.e(*P.load_rd(7, HANDLER_ADDR))
    seq.e(P.cfx2rc(15, 15, 15, 7))      # async vector
    seq.e(*P.load_rd(8, 1))
    seq.e(P.cfx2rc(32, 16, 18, 8))      # ack PMEM pending (prelude DMA)
    seq.e(P.cfx2rc(15, 16, 18, 8))      # ack TIMER pending
    seq.e(*P.load_rd(9, 0))
    seq.e(P.cfx2rc(15, 16, 16, 9))      # TIMER source mask: allow
    seq.e(or_o(10, 5, 5))
    seq.e(P.add_si(10, TIMER_DELAY))
    seq.e(P.cfx2rc(15, 16, 1, 10))      # timer_cmp = t0 + 2047
    seq.e(*P.load_rd(11, 1))
    seq.e(P.cfx2rc(15, 16, 0, 11))      # timer_ctrl ENABLE
    seq.e(*P.load_rd(12, 0))
    seq.e(P.cfx2rc(3, 15, 3, 12))       # hmon monitor mask: allow
    seq.e(swym_n(4095))
    seq.mark("after_swym")
    after_swym = P.ROM_BASE + seq.lab["after_swym"] * 4

    # Handler has run (or not) at this point.
    seq.e(*P.load_rb(21, SCRATCH))
    seq.e(P.ld_o(14, 21, 16))           # entry count
    seq.e(*P.load_rd(15, 2 if mutate == "count" else 1))
    seq.b("ne", 14, "fail_count", 15)
    seq.e(P.ld_o(16, 21, 0))            # captured cause_ip
    seq.e(*P.load_rd(17, after_swym + (4 if mutate == "ip" else 0)))
    seq.b("ne", 16, "fail_ip", 17)
    seq.e(P.ld_o(18, 21, 8))            # cycle at entry
    seq.e(or_o(19, 5, 5))
    seq.e(P.add_si(19, 4095 + (100000 if mutate == "window" else 0)))
    seq.e(cmp_uo_rd(20, 18, 19))
    seq.e(*P.load_rd(21, 0xFFFF_FFFF_FFFF_FFFF))
    seq.e(cmp_uo_rd(22, 20, 21))        # 0 <=> entry < t0 + N
    seq.b("z", 22, "fail_early")

    seq.e(*P.exit_seq(RC_OK))
    seq.e(P.jump_rel(0))

    for name, code in (("fail_d1", RC_D1), ("fail_d2", RC_D2),
                       ("fail_count", RC_NO_ENTRY), ("fail_ip", RC_BAD_IP),
                       ("fail_early", RC_EARLY)):
        seq.mark(name)
        seq.e(*P.exit_seq(code))
        seq.e(P.jump_rel(0))
    prog = seq.resolve()

    # Async handler: record the capture, ack the source, return to the
    # instruction boundary after the swym.  It must not touch rd5 (t0).
    handler = []
    handler += [P.cfx2rd(15, 15, 2, 20)]      # prev IP (capture)
    handler += [P.cfx2rd(15, 8, 2, 21)]       # cycle at entry
    handler += P.load_rb(22, SCRATCH)
    handler += [P.st_o(20, 22, 0), P.st_o(21, 22, 8)]
    handler += [P.ld_o(23, 22, 16), P.add_si(23, 1), P.st_o(23, 22, 16)]
    handler += P.load_rd(24, 1)
    handler += [P.cfx2rc(15, 16, 18, 24)]     # ack TIMER (sticky source)
    handler += [P.escape(15, 0)]              # return to cause_ip
    handler += [P.jump_rel(0)]

    return P.build_rom(prog, handlers={HANDLER_OFF: handler})


def run_gem5(rom: bytes, work: Path, gem5: Path, config: Path,
             timeout: int, gem5_args: str = "",
             dump_scratch: str | None = None) -> tuple[int | None, str]:
    work.mkdir(parents=True, exist_ok=True)
    romp = work / "rom.bin"
    romp.write_bytes(rom)
    outdir = work / "gem5-out"
    outdir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PARITY_GEM5"] = str(gem5)
    env["PARITY_GEM5_CONFIG"] = str(config)
    env["PARITY_GEM5_PROFILE"] = "vast"
    env["PARITY_WORK_ROOT"] = str(outdir)
    args = gem5_args or "--cpu-type timing --wuming-cycles"
    if dump_scratch:
        args += f" --dump-mem 0x{SCRATCH:x}:48:{dump_scratch}"
    env["PARITY_GEM5_ARGS"] = args
    cmd = [sys.executable, str(SHIM),
           "-machine", "kaiwu-vast,bootrom-image=%s" % romp,
           "-nographic", "-semihosting-config", "enable=on,target=native"]
    try:
        res = subprocess.run(cmd, cwd=str(_REPO), env=env, timeout=timeout,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True)
    except subprocess.TimeoutExpired:
        return None, "TIMEOUT"
    log = (res.stdout or "") + (res.stderr or "")
    if res.returncode < 0:
        return None, "signal %d\n%s" % (-res.returncode, log)
    return res.returncode & 0xFF, log


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gem5", default=str(GEM5_DEFAULT))
    ap.add_argument("--gem5-config", default=str(GEM5_CONFIG_DEFAULT))
    ap.add_argument("--work-dir", default=str(WORK_DEFAULT))
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--dump-rom", default=None,
                    help="write the generated BootROM image here")
    ap.add_argument("--gem5-args", default="",
                    help="override the fs.py flags (default "
                         "'--cpu-type timing --wuming-cycles'; a negative "
                         "control can drop them so the 1+N window vanishes)")
    ap.add_argument("--dump-scratch", default=None,
                    help="dump the 48-byte scratch: cause_ip, cycle, count, "
                         "d0, d1, d2")
    ap.add_argument("--mutate", default="none",
                    choices=("none", "ip", "window", "count"),
                    help="harness self-check: break one expectation so the "
                         "matching failure path must be reached")
    ap.add_argument("--skip-cycles", action="store_true",
                    help="omit the cycle-delta phase (isolate the interrupt "
                         "assertions)")
    args = ap.parse_args()

    rom = build_rom(mutate=args.mutate, skip_cycles=args.skip_cycles)
    if args.dump_rom:
        Path(args.dump_rom).write_bytes(rom)

    gem5 = Path(args.gem5)
    config = Path(args.gem5_config)
    if not gem5.is_file():
        print(f"[FAIL] gem5 binary missing: {gem5}", file=sys.stderr)
        return 2
    if not config.is_file():
        print(f"[FAIL] gem5 config missing: {config}", file=sys.stderr)
        return 2

    rc, log = run_gem5(rom, Path(args.work_dir), gem5, config, args.timeout,
                       args.gem5_args, args.dump_scratch)
    tail = "\n".join(log.strip().splitlines()[-12:])
    if rc == RC_OK:
        if args.skip_cycles:
            print("[PASS] TIMER entry at the boundary after swym, no earlier "
                  "than t0+N")
        else:
            print("[PASS] swym 0/1/4095 deltas are 1+N; TIMER entry at the "
                  "boundary after swym, no earlier than t0+N")
        print(f"gem5 tail:\n{tail}")
        return 0
    meaning = {
        RC_D1: "swym 1 is not exactly one cycle more than swym 0",
        RC_D2: "swym 4095 is not exactly 4095 cycles more than swym 0",
        RC_NO_ENTRY: "TIMER interrupt was never taken (or taken more than "
                     "once: entry count != 1)",
        RC_BAD_IP: "async entry IP is not the boundary after swym",
        RC_EARLY: "async entry happened before the 1 + N window ended",
        None: "no guest exit (fault/timeout)",
    }.get(rc, f"unexpected guest exit 0x{rc:02x}")
    print(f"[FAIL] {meaning} (guest exit {rc if rc is None else hex(rc)})")
    print(f"gem5 tail:\n{tail}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
