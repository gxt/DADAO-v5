#!/usr/bin/env python3
"""Min ROM probe for INFRA-082t stage A1: the `umon` (SBI_UMON_SYSCALL) service
of the `dadao-m1` machine (ISS-216 execution landing point).

Spec sources (every expectation is derived by hand from spec/ + contracts/ and
never from the QEMU implementation -- contract-syscall §5):
  - spec/DADAO-22-SBI §2: `umon` (cfx0) is the *user-mode* exception entry;
    the syscall dispatch entry is `immu18 = 0` (SBI_UMON_SYSCALL) with
    `rd15 = nr` in and `rd8 = result` out.
  - .tao/contracts/contract-syscall.md §1.1 (number in `rd15`, RISC-V Linux
    numbering) / §2 (entry, return resumes at `excp_cause_ip + 4`, i.e. where
    `escape cfxha, [excp_cause_ip, 4]` would land) / §3 (data arguments
    `rd16-rd31`, address arguments `rb16-rb31`, result `rd8`) / §4 (errno =
    *negative* `rd8`, user decision 2026-10-14, option A) / §6 (QEMU is the
    host-side syscall forwarding layer of the kernel-less model; the halting
    protocols of Machine-01 §5.5 / ADR-0004 D3 must not be mixed into it).
  - Syscall numbers and errno values: the pinned RISC-V Linux uapi
    (`asm-generic/unistd.h`, `asm-generic/errno.h`) --
    write 64, writev 66, exit 93, exit_group 94, set_tid_address 96, brk 214;
    EIO 5, EBADF 9, EINVAL 22, ENOSYS 38.
  - spec/Machine-01 §4 (trap/escape and the two pre-existing routes of §4.3),
    §6 (bootrom hands off to user mode; `-bios` + raw `-kernel` path B).

Observation channels (independent of each other):
  * QEMU stdout / stderr          -> the bytes the guest wrote (write/writev).
  * QEMU process exit code        -> `exit` / `exit_group` status (host $?).
  * QEMU `-d cpu` register dump   -> `rd8` result, run mode, cfx0 trap/sync
                                     counters (last dump block).
  * QEMU `-d guest_errors` log    -> the explicit "not implemented" report.

Cases (each has a reachable FAIL path; the comparisons are proved live by the
`--inject` self-check):
  umon_write_stdout        write(1) served; rd8 = count; exit_group -> $?
  umon_write_stderr        write(2) goes to the host stderr stream
  umon_writev_stdout       writev(2) gathers both iovecs (64-bit BE iovecs)
  umon_writev_einval       iovcnt > IOV_MAX => -EINVAL
  umon_set_tid_address     set_tid_address(96) -> rd8 = the machine's tid
  umon_enosys_unknown_nr   unknown number => -ENOSYS + explicit guest error
  umon_enosys_known_nr     known-but-unimplemented number => -ENOSYS
  umon_ebadf_fd            unsupported fd => -EBADF
  umon_exit_plain          exit (93) also halts with the guest's status
  handoff_not_served       hypv `trap cfx0, 0` (bootrom hand-off) still takes
                           the DADAO-12 §5 vector route (no service, no counter)
  umon_over_guest_vector   user syscall is served even when a guest umon vector
                           is installed (documented QEMU-as-monitor decision)
  jmon_not_served          `trap cfx1, 0` is *not* served => ILLI redirect
  semihost_still_ok        the semihosting tag route (decode short-circuit) is
                           unchanged in the same machine

Usage:
  min_rom_probe_082t.py             # run all checks
  min_rom_probe_082t.py --only NAME # run one check
  min_rom_probe_082t.py --list
  min_rom_probe_082t.py --inject    # corrupt every expectation (must FAIL)

Exit code: 0 iff every requested check passed, non-zero otherwise.
"""

import argparse
import os
import re
import struct
import subprocess
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_QEMU = os.path.join(_REPO, ".work/build/qemu/qemu-system-dadao")
QEMU = DEFAULT_QEMU
WORKDIR = "/tmp/opencode/INFRA-082t/probe"
TIMEOUT = 10

ROM_BASE = 0xFFFF_FFFF_0000
RAM_BASE = 0xFC00_0000_0000
TAG = 0x30000                       # immu18[17:16] == 2'b11 => semihosting

UMON = 0                            # cfxha 0 (`umon`)
SBI_UMON_SYSCALL = 0                # immu18 = 0 (DADAO-22 §2)
SBI_JMON_SYSCALL = 0

NR_write = 64
NR_writev = 66
NR_exit = 93
NR_exit_group = 94
NR_set_tid_address = 96

# The machine has one process (no kernel/scheduler), so the thread id returned
# by set_tid_address(2) is the fixed DADAO_UMON_TID of the service.
UMON_TID = 1

ENOSYS = 38
EBADF = 9
EINVAL = 22

ADP_STOPPED_APPLICATION_EXIT = 0x20026

# Boot ROM: the hand-off program, plus two guest-side umon handlers.
H_UMON = ROM_BASE + 0x200           # cfx0 cg0 (user) excp_vector: exit 0xEE
H_ILLI = ROM_BASE + 0x300           # ILLI-redirect target:           exit 0x77

# App (RAM) data layout; the code starts at RAM_BASE (path B entry).
K_MSG_A1 = 0x400
K_MSG_E2 = 0x410
K_BUF_V1 = 0x420
K_BUF_V2 = 0x430
K_TIDPTR = 0x440
K_IOV = 0x500


# ---------------------------------------------------------------------------
# Encoders (contracts/opcodes.yaml; same wyde sequences as min_rom_probe_046t)
# ---------------------------------------------------------------------------

def set_zw_rd(rd, wp, imm): return (0x4C << 24) | (rd << 18) | (wp << 16) | (imm & 0xFFFF)
def or_w_rd(rd, wp, imm):   return (0x48 << 24) | (rd << 18) | (wp << 16) | (imm & 0xFFFF)
def set_zw_rb(rb, wp, imm): return (0x4E << 24) | (rb << 18) | (wp << 16) | (imm & 0xFFFF)
def or_w_rb(rb, wp, imm):   return (0x4A << 24) | (rb << 18) | (wp << 16) | (imm & 0xFFFF)
def ld_o(rd, rb, off):      return (0x20 << 24) | (rd << 18) | (rb << 12) | (off & 0xFFF)
def st_o(rd, rb, off):      return (0x21 << 24) | (rd << 18) | (rb << 12) | (off & 0xFFF)
def cfx2rc(ha, cg, rc, rd): return (0x7B << 24) | (ha << 18) | (cg << 12) | (rc << 6) | rd
def cfx2rd(ha, cg, rc, rd): return (0x7A << 24) | (ha << 18) | (cg << 12) | (rc << 6) | rd
def trap(ha, immu18):       return (0x7F << 24) | (ha << 18) | (immu18 & 0x3FFFF)
def escape(ha, imms18):     return (0x7E << 24) | (ha << 18) | (imms18 & 0x3FFFF)
def jump_iiii(imms24):      return (0x70 << 24) | (imms24 & 0xFFFFFF)
def swym():                 return 0x77880000


def load_rd(rd, val):
    """rd = val via set.zw + or.w (wyde-by-wyde construction)."""
    out = [set_zw_rd(rd, 0, val & 0xFFFF)]
    for wp in (1, 2, 3):
        x = (val >> (16 * wp)) & 0xFFFF
        if x:
            out.append(or_w_rd(rd, wp, x))
    return out


def set_addr(rb, addr):
    """rb = addr (48-bit) via set.zw (word 3) + or.w (words 2..0)."""
    ws = [set_zw_rb(rb, 3, (addr >> 48) & 0xFFFF)]
    for wp in (2, 1, 0):
        x = (addr >> (16 * wp)) & 0xFFFF
        if x:
            ws.append(or_w_rb(rb, wp, x))
    return ws


def exit_seq(code):
    """Report `code` through semihosting SYS_EXIT (Machine-01 §5.3/§5.5).

    rb16 = argument block {reason, code}; rd16 = 0x18; `trap` with the
    semihosting tag.  Used by the *guest* handlers and by the semihosting
    non-regression case -- never by the umon service cases, which exit through
    the syscall path (contract-syscall §6: the protocols must not be mixed).
    """
    return ([jump_iiii(1)]
            + [set_zw_rb(16, 0, 0x0000), or_w_rb(16, 1, 0x00FF),
               or_w_rb(16, 0, 0xF000), or_w_rb(16, 2, 0xFC00)]
            + load_rd(8, ADP_STOPPED_APPLICATION_EXIT) + [st_o(8, 16, 0)]
            + load_rd(9, code) + [st_o(9, 16, 8)]
            + load_rd(16, 0x18) + [trap(0, TAG)])


def words_to_bytes(ws):
    return b"".join(struct.pack(">I", x & 0xFFFFFFFF) for x in ws)


def build_rom(prog, handlers=None):
    """prog at ROM offset 0; handlers = {byte offset: word list}; pad to 0x400."""
    rom = bytearray(words_to_bytes(prog))
    for off in sorted(handlers or {}):
        while len(rom) < off:
            rom += words_to_bytes([swym()])
        rom += words_to_bytes(handlers[off])
    while len(rom) < 0x400:
        rom += words_to_bytes([swym()])
    return bytes(rom)


def build_kernel(data):
    """Flat RAM image loaded at RAM_BASE; data = {offset: bytes}."""
    end = max((off + len(blob) for off, blob in data.items()), default=0)
    buf = bytearray(end + 0x20)
    for off, b in data.items():
        buf[off:off + len(b)] = b
    return bytes(buf)


# ---------------------------------------------------------------------------
# Guest programs
# ---------------------------------------------------------------------------

def bootrom(umon_user_vector):
    """ROM (hypv): configure cfx0, then hand off to the app in user mode.

    Machine-01 §6 / tests/scripts/bootrom.S: cfx_umon cg3 (hypv) switches the
    run mode to user and enters the app; cfx_umon cg0 (user) gets the guest
    handler (when a case wants one), cleared masks and `switch_run_mode = user`.
    """
    prog = []
    prog += load_rd(22, RAM_BASE)
    prog += [cfx2rc(UMON, 3, 8, 0)]      # cg3/hypv switch_run_mode = user
    prog += [cfx2rc(UMON, 3, 9, 0)]      # cg3/hypv switch_cfx_mask = 0
    prog += [cfx2rc(UMON, 3, 10, 22)]    # cg3/hypv excp_vector = app entry
    prog += load_rd(22, umon_user_vector)
    prog += [cfx2rc(UMON, 0, 8, 0)]      # cg0/user switch_run_mode = user
    prog += [cfx2rc(UMON, 0, 10, 22)]    # cg0/user excp_vector = handler
    prog += [cfx2rc(UMON, 0, 6, 0)]      # cg0/user trap_mask = allow
    prog += [cfx2rc(UMON, 0, 1, 0)]      # global_cfx_mask[user] = allow
    prog += [trap(UMON, SBI_UMON_SYSCALL)]   # hypv -> user hand-off
    return prog


def sys_call(nr, args):
    """Set rd15 = nr, then the data/address arguments, then `trap cfx0, 0`.

    contract-syscall §3: the nth argument goes to the nth slot of its bank --
    data arguments rd16, rd17, ... and address arguments rb16, rb17, ...
    """
    prog = load_rd(15, nr)
    rdi = 16
    rbi = 16
    for kind, value in args:
        if kind == "d":
            prog += load_rd(rdi, value)
            rdi += 1
        else:
            prog += set_addr(rbi, value)
            rbi += 1
    prog += [trap(UMON, SBI_UMON_SYSCALL)]
    return prog


def umon_exit_group(code):
    return sys_call(NR_exit_group, [("d", code)])


def app_write(fd, msg_off, length, exit_code):
    return (sys_call(NR_write, [("d", fd), ("a", RAM_BASE + msg_off),
                                ("d", length)])
            + umon_exit_group(exit_code))


def app_writev(iov_off, cnt, exit_code):
    return (sys_call(NR_writev, [("d", 1), ("a", RAM_BASE + iov_off),
                                 ("d", cnt)])
            + umon_exit_group(exit_code))


def kernel(prog, data=()):
    blobs = {0: words_to_bytes(prog)}
    for off, blob in data:
        blobs[off] = blob
    return build_kernel(blobs)


def blk(*vals):
    return b"".join(struct.pack(">Q", v & 0xFFFFFFFFFFFFFFFF) for v in vals)


# ---------------------------------------------------------------------------
# Case model
# ---------------------------------------------------------------------------

CASES = []


def case(name, desc):
    def deco(fn):
        CASES.append((name, desc, fn))
        return fn
    return deco


@case("umon_write_stdout", "write(1, ...) served; rd8 = count; exit_group -> $?")
def _write_stdout():
    exp = {"exit": 0x2A, "stdout_has": b"A1\n", "rd8": 3, "mode": 0, "trapn0": 1}
    return (build_rom(bootrom(0)),
            kernel(app_write(1, K_MSG_A1, 3, 0x2A), [(K_MSG_A1, b"A1\n")]),
            exp)


@case("umon_write_stderr", "write(2, ...) reaches the host stderr stream")
def _write_stderr():
    exp = {"exit": 0x2B, "stderr_has": b"E2\n", "stdout_absent": b"E2\n",
           "rd8": 3}
    return (build_rom(bootrom(0)),
            kernel(app_write(2, K_MSG_E2, 3, 0x2B), [(K_MSG_E2, b"E2\n")]),
            exp)


@case("umon_writev_stdout", "writev(2) gathers both 64-bit BE iovecs")
def _writev_stdout():
    iov = blk(RAM_BASE + K_BUF_V1, 2) + blk(RAM_BASE + K_BUF_V2, 3)
    exp = {"exit": 0x2C, "stdout_has": b"V1V2\n", "rd8": 5}
    return (build_rom(bootrom(0)),
            kernel(app_writev(K_IOV, 2, 0x2C),
                   [(K_BUF_V1, b"V1"), (K_BUF_V2, b"V2\n"), (K_IOV, iov)]),
            exp)


@case("umon_writev_einval", "iovcnt > IOV_MAX (1024) => -EINVAL in rd8")
def _writev_einval():
    exp = {"exit": 0x2D, "rd8": (1 << 64) - EINVAL}
    return build_rom(bootrom(0)), kernel(app_writev(K_IOV, 1025, 0x2D)), exp


@case("umon_set_tid_address",
      "set_tid_address(96) served; rd8 = the machine's single-process tid")
def _set_tid_address():
    # tidptr = rb16 (a pointer argument; contract-syscall §3).  There is no
    # thread-exit hook to clear it in the kernel-less model, so the service
    # answers with the fixed DADAO_UMON_TID instead of -ENOSYS (musl calls this
    # unconditionally during startup: src/env/__init_tls.c, __init_tp).
    app = (sys_call(NR_set_tid_address, [("a", RAM_BASE + K_TIDPTR)])
           + umon_exit_group(0x3E))
    exp = {"exit": 0x3E, "rd8": UMON_TID,
           "log_absent": "umon syscall 96 not implemented"}
    return build_rom(bootrom(0)), kernel(app), exp


@case("umon_enosys_unknown_nr", "unknown number => -ENOSYS (+ guest error log)")
def _enosys_unknown():
    app = (sys_call(0x1234, []) + umon_exit_group(0x5A))
    exp = {"exit": 0x5A, "rd8": (1 << 64) - ENOSYS,
           "log_has": "umon syscall 4660 not implemented"}
    return build_rom(bootrom(0)), kernel(app), exp


@case("umon_enosys_known_nr", "in-table but unimplemented number => -ENOSYS")
def _enosys_known():
    app = (sys_call(63, [("d", 0), ("a", RAM_BASE + K_MSG_A1), ("d", 1)])
           + umon_exit_group(0x5B))
    exp = {"exit": 0x5B, "rd8": (1 << 64) - ENOSYS}
    return build_rom(bootrom(0)), kernel(app, [(K_MSG_A1, b"A1\n")]), exp


@case("umon_ebadf_fd", "fd without a host stream => -EBADF (no silent success)")
def _ebadf():
    exp = {"exit": 0x5C, "rd8": (1 << 64) - EBADF}
    return (build_rom(bootrom(0)),
            kernel(app_write(3, K_MSG_A1, 3, 0x5C), [(K_MSG_A1, b"A1\n")]),
            exp)


@case("umon_exit_plain", "exit (93) halts with the guest's status")
def _exit_plain():
    app = sys_call(NR_exit, [("d", 0x07)])
    exp = {"exit": 0x07}
    return build_rom(bootrom(0)), kernel(app), exp


@case("handoff_not_served",
      "hypv `trap cfx0, 0` (bootrom hand-off) keeps the §5 vector route")
def _handoff():
    # The app does no syscall at all: it leaves through semihosting SYS_EXIT,
    # so cfx0.trap_num == 1 can only come from the hand-off trap and the run
    # mode of the last dump block can only be user.
    app = exit_seq(0x42)
    exp = {"exit": 0x42, "mode": 0, "trapn0": 1, "syncn0": 0}
    return build_rom(bootrom(0)), kernel(app), exp


@case("umon_over_guest_vector",
      "user syscall served even with a guest umon vector installed")
def _over_guest_vector():
    # The guest handler installed at cfx0 cg0 rc10 would exit 0xEE; the served
    # call must win (QEMU is the kernel-less model's umon monitor).
    exp = {"exit": 0x2E, "stdout_has": b"A1\n", "rd8": 3}
    return (build_rom(bootrom(H_UMON), {0x200: exit_seq(0xEE)}),
            kernel(app_write(1, K_MSG_A1, 3, 0x2E), [(K_MSG_A1, b"A1\n")]),
            exp)


@case("jmon_not_served",
      "`trap cfx1, 0` is not a umon syscall => ILLI redirect to the umon vector")
def _jmon():
    # cfx1 is legal but its user instruction-type trap mask is still set, so
    # the trap raises ILLI, which redirects to the current-mode monitor (cfx0)
    # and runs the guest handler installed at cfx0 cg0 rc10 => exit 0x77.
    app = ([trap(1, SBI_JMON_SYSCALL)] + umon_exit_group(0x99))
    exp = {"exit": 0x77, "syncn0": 1}
    return build_rom(bootrom(H_ILLI), {0x300: exit_seq(0x77)}), kernel(app), exp


@case("semihost_still_ok",
      "the semihosting tag route is unchanged in the same machine")
def _semihost():
    exp = {"exit": 0x3C}
    return build_rom(bootrom(0)), kernel(exit_seq(0x3C)), exp


# ---------------------------------------------------------------------------
# Runner + observation
# ---------------------------------------------------------------------------

def run(rom, kern, qemu=QEMU, timeout=TIMEOUT):
    os.makedirs(WORKDIR, exist_ok=True)
    rp = os.path.join(WORKDIR, "rom.bin")
    kp = os.path.join(WORKDIR, "kernel.bin")
    lp = os.path.join(WORKDIR, "cpu.log")
    with open(rp, "wb") as f:
        f.write(rom)
    with open(kp, "wb") as f:
        f.write(kern)
    if os.path.exists(lp):
        os.remove(lp)

    cmd = [qemu, "-M", "dadao-m1", "-nographic", "-monitor", "none",
           "-bios", rp, "-kernel", kp,
           "-d", "cpu,guest_errors", "-D", lp,
           "-semihosting-config", "enable=on,target=native"]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None
    log = ""
    if os.path.exists(lp):
        with open(lp, "r", errors="replace") as f:
            log = f.read()
    return {
        "exit": r.returncode & 0xFF,
        "stdout": r.stdout,
        "stderr": r.stderr,
        "log": log,
    }


def _lasthex(log, pat):
    m = None
    for x in re.finditer(pat, log, re.MULTILINE):
        m = x
    return int(m.group(1), 16) if m else None


def observe(obs):
    """Extract the observable values from the LAST dump block of the log."""
    log = obs["log"]
    obs["rd8"] = _lasthex(log, r"RD\[08\]: ([0-9a-f]+)")
    obs["mode"] = _lasthex(log, r"^MODE: (\d+)$")
    obs["trapn0"] = _lasthex(log, r"CFX00 ID:[^\n]* TRAPN:([0-9a-f]+)")
    obs["syncn0"] = _lasthex(log, r"CFX00 ID:[^\n]* SYNCN:([0-9a-f]+)")
    return obs


def verify(exp, obs, inject=False):
    """Return the list of failed expectations (empty == pass)."""
    exp = dict(exp)
    if inject:
        # Corrupt every expectation so each comparison must fire.
        for k in ("rd8", "mode", "trapn0", "syncn0", "escn0"):
            if k in exp:
                exp[k] = (exp[k] + 1) & 0xFFFFFFFFFFFFFFFF if k == "rd8" \
                    else (exp[k] + 1) % 4
        if "exit" in exp:
            exp["exit"] = (exp["exit"] + 1) & 0xFF
        for k in ("stdout_has", "stderr_has", "log_has"):
            if k in exp:
                exp[k] = b"\x00INJECTED" if isinstance(exp[k], bytes) else "\x00injected"
        if "stdout_absent" in exp:
            # Turn the absence expectation into a presence one so that the
            # comparison stays live under --inject as well.
            exp["stdout_has"] = exp.pop("stdout_absent")
        if "log_absent" in exp:
            exp["log_has"] = exp.pop("log_absent")

    bad = []
    if "exit" in exp and obs["exit"] != exp["exit"]:
        bad.append("exit: expected %d (0x%x), actual %d"
                   % (exp["exit"], exp["exit"], obs["exit"]))
    if "stdout_has" in exp and exp["stdout_has"] not in obs["stdout"]:
        bad.append("stdout: expected to contain %r, actual %r"
                   % (exp["stdout_has"], obs["stdout"]))
    if "stdout_absent" in exp and exp["stdout_absent"] and \
            exp["stdout_absent"] in obs["stdout"]:
        bad.append("stdout: expected NOT to contain %r" % (exp["stdout_absent"],))
    if "stderr_has" in exp and exp["stderr_has"] not in obs["stderr"]:
        bad.append("stderr: expected to contain %r, actual %r"
                   % (exp["stderr_has"], obs["stderr"]))
    if "log_has" in exp and exp["log_has"] not in obs["log"]:
        bad.append("log: expected to contain %r" % (exp["log_has"],))
    if "log_absent" in exp and exp["log_absent"] and \
            exp["log_absent"] in obs["log"]:
        bad.append("log: expected NOT to contain %r" % (exp["log_absent"],))
    for key in ("rd8", "mode", "trapn0", "syncn0", "escn0"):
        if key not in exp:
            continue
        got = obs.get(key)
        if got is None:
            bad.append("%s: not observed in the -d cpu dump" % key)
        elif got != exp[key]:
            bad.append("%s: expected %d (0x%x), actual %d (0x%x)"
                       % (key, exp[key], exp[key], got, got))
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--qemu", default=DEFAULT_QEMU)
    ap.add_argument("--only", action="append", default=[])
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--inject", action="store_true",
                    help="corrupt every expectation (all checks must FAIL)")
    args = ap.parse_args()

    global QEMU
    QEMU = args.qemu

    if args.list:
        for name, desc, _ in CASES:
            print("%-24s %s" % (name, desc))
        return 0

    if not os.path.isfile(QEMU):
        print("min_rom_probe_082t: ERROR: qemu not found: %s" % QEMU)
        return 2

    selected = [c for c in CASES if not args.only or c[0] in args.only]
    if args.only and len(selected) != len(args.only):
        print("min_rom_probe_082t: ERROR: unknown case in --only")
        return 2

    total = 0
    failed = 0
    for name, desc, fn in selected:
        rom, kern, exp = fn()
        obs = run(rom, kern)
        total += 1
        if obs is None:
            print("FAIL %-24s qemu timeout after %ds" % (name, TIMEOUT))
            failed += 1
            continue
        obs = observe(obs)
        bad = verify(exp, obs, inject=args.inject)
        if bad:
            failed += 1
            print("FAIL %-24s %s" % (name, desc))
            for b in bad:
                print("       - %s" % b)
            print("       observed: exit=%d rd8=0x%x mode=%s trapn0=%s syncn0=%s "
                  "stdout=%r stderr=%r"
                  % (obs["exit"], obs["rd8"] or 0, obs["mode"], obs["trapn0"],
                     obs["syncn0"], obs["stdout"][-60:], obs["stderr"][-60:]))
        else:
            print("PASS %-24s %s" % (name, desc))

    print("min_rom_probe_082t: %d/%d checks passed" % (total - failed, total))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
