#!/usr/bin/env python3
"""Min ROM probe for QEMU-047t: the M5 SEE bootrom (build + load + handoff).

Runs the bootrom loaded with `-bios` and a flat sample application loaded with
`-kernel` (ADR-0004 D2.3 path B) and checks, from the QEMU `-d cpu` register
dump plus the process exit code, that:

  * the bootrom is loaded at the boot ROM base and the reset PC is unchanged
    (0xffff_ffff_0000 = cfx_power_hypv_excp_vector);
  * the bootrom's initial cfx configuration took effect (cfx_umon/cfx_power
    exception vectors, switch_run_mode=user, global cfx mask cleared);
  * the bootrom handed off hypv -> user at the application entry;
  * supv is never entered this version;
  * the bootrom supplies the application stack in RAM@0;
  * the application reaches the configured user exception vector (handler);
  * the application exits with code 0.

Spec sources (expectations derived by hand from spec/ + ADRs, never from the
QEMU implementation):
  - spec/Machine-01-测试机运行环境.md §2 (modes: hypv/user; bootrom -> user,
    no supv), §3 (cfx vectors/masks), §4 (trap/escape), §5 (SYS_EXIT),
    §6 (load/bootrom).
  - .tao/adr/adr-0020-see-semihosting.md D12 (new bootrom: `-bios`, unchanged
    reset vector, hypv -> user) and .tao/adr/adr-0004-test-machine.md R1 (the
    `-bios` bootrom path), R3 (RAM base -> 0; C1 dual mapping), D1/D2.1
    (memory map, reset values), D2.3 (raw-bin dual-image path B).
  - .tao/knowledge/contract-see.md §1/§2/§3/§4 and contract-semihosting.md §5.

Observation channel: `-d cpu` dumps the CPU state (incl. MODE/CFXCODE and the
cfx register file) at each translated-block boundary; the last block (and every
intermediate one) is parsed here.  The guest exit code is the process `$?`.

Usage:
  min_rom_probe_047t.py                 # run all checks
  min_rom_probe_047t.py --only NAME     # run one check (used by run.sh --inject)
  min_rom_probe_047t.py --list

Exit code: 0 iff every requested check passed, non-zero otherwise.
"""

import argparse
import os
import re
import subprocess
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_QEMU = os.path.join(_REPO, ".work/build/qemu/qemu-system-dadao")
DEFAULT_BOOTROM = os.path.join(_REPO, ".dadao/tests/bootrom/bootrom.bin")
DEFAULT_APP = os.path.join(_REPO, ".dadao/tests/bootrom/bootrom_app.bin")
WORKDIR = "/tmp/opencode/QEMU-047t"
TIMEOUT = 10

# Memory map / handoff constants (from the firmware sources + ADRs above).
ROM_BASE = 0xFFFF_FFFF_0000            # boot ROM base, reset PC (ADR-0004 D1/D2.1)
APP_ENTRY = 0x0000_0000_0000           # legacy RAM base = path-B entry (ADR-0004 D2.2)
HANDLER = 0xFFFF_FFFF_0200             # bootrom user exception handler (ROM + 0x200)
RAM0_STACK = 0x0000_0000_00F0_0000     # bootrom SP in RAM@0 (RAM@0 + 15 MiB)
EXIT_PASS = 0x00

QEMU = DEFAULT_QEMU
BOOTROM = DEFAULT_BOOTROM
APP = DEFAULT_APP


# ---------------------------------------------------------------------------
# `-d cpu` dump parsing: split into per-TB blocks and extract the fields we need.
# ---------------------------------------------------------------------------

def _parse_blocks(log):
    blocks = []
    cur = None
    for line in log.splitlines():
        m = re.match(r"^PC: ([0-9a-fA-F]+)", line)
        if m:
            if cur is not None:
                blocks.append(cur)
            cur = {"pc": int(m.group(1), 16), "lines": [line]}
            continue
        if cur is not None:
            cur["lines"].append(line)
    if cur is not None:
        blocks.append(cur)

    for b in blocks:
        txt = "\n".join(b["lines"])
        b["mode"] = _hex(txt, r"^MODE: (\d+)")
        b["cfxcode"] = _hex(txt, r"^CFXCODE: (\d+)")
        b["gcm0"] = _hex(txt, r"^GVER0:.*GCM0: ([0-9a-fA-F]+)")
        b["rb01"] = _hex(txt, r"RB\[01\]: ([0-9a-fA-F]+)")
        for ha in (0, 63):
            for md in (0, 3):
                b["cfx%d_m%d" % (ha, md)] = _cfx_mlines(txt, ha, md)
    return blocks


def _hex(txt, pat):
    m = re.search(pat, txt, re.M)
    return int(m.group(1), 16) if m else None


def _cfx_mlines(txt, ha, mode):
    """Return the `CFX<ha> M<mode> ...` field dict for one block."""
    m = re.search(r"^CFX%02d M%d (.*)$" % (ha, mode), txt, re.M)
    if not m:
        return None
    body = m.group(1)

    def f(name):
        mm = re.search(name + r":([0-9a-fA-F]+)", body)
        return int(mm.group(1), 16) if mm else None

    return {
        "swmode": f("SWMODE"),
        "swmask": f("SWMASK"),
        "vec": f("VEC"),
        "trapmask": f("TRAPMASK"),
    }


def run(bootrom, app):
    os.makedirs(WORKDIR, exist_ok=True)
    lp = os.path.join(WORKDIR, "cpu.log")
    cmd = [QEMU, "-M", "dadao-m1", "-nographic",
           "-bios", bootrom, "-kernel", app,
           "-semihosting-config", "enable=on,target=native",
           "-d", "cpu", "-D", lp]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=TIMEOUT, text=True)
    except subprocess.TimeoutExpired:
        return None, None
    with open(lp) as f:
        log = f.read()
    return (r.returncode & 0xFF), log


# ---------------------------------------------------------------------------
# Check model
# ---------------------------------------------------------------------------

CASES = []   # (name, desc, checker(blocks, exit_code) -> (ok, detail))


def case(name, desc):
    def deco(fn):
        CASES.append((name, desc, fn))
        return fn
    return deco


def _first(blocks, pred):
    for b in blocks:
        if pred(b):
            return b
    return None


@case("reset_pc", "reset PC == boot ROM base 0xffff_ffff_0000")
def _reset_pc(blocks, rc):
    if not blocks:
        return False, "no CPU dump blocks"
    ok = blocks[0]["pc"] == ROM_BASE
    return ok, "first block PC=0x%x (exp 0x%x)" % (blocks[0]["pc"], ROM_BASE)


@case("bootrom_handoff_vector",
      "bootrom set cfx_umon hypv excp_vector = app entry")
def _bootrom_handoff_vector(blocks, rc):
    b = _first(blocks, lambda b: b["cfx0_m3"] and b["cfx0_m3"]["vec"] == APP_ENTRY)
    if b is None:
        got = [hex(b2["cfx0_m3"]["vec"]) for b2 in blocks if b2["cfx0_m3"]]
        return False, "cfx0 hypv VEC never == 0x%x (seen %s)" % (APP_ENTRY, got[:3])
    return True, "cfx0 M3 VEC=0x%x at PC=0x%x" % (APP_ENTRY, b["pc"])


@case("cfx0_hypv_switch_user", "cfx_umon hypv switch_run_mode = user (0)")
def _cfx0_hypv_switch_user(blocks, rc):
    b = _first(blocks, lambda b: b["cfx0_m3"] and b["cfx0_m3"]["swmode"] == 0)
    return (b is not None), ("cfx0 M3 SWMODE=0 seen" if b else "cfx0 M3 SWMODE never 0")


@case("cfx0_user_vector", "cfx_umon user excp_vector = handler 0xffff_ffff_0200")
def _cfx0_user_vector(blocks, rc):
    b = _first(blocks, lambda b: b["cfx0_m0"] and b["cfx0_m0"]["vec"] == HANDLER)
    if b is None:
        got = [hex(b2["cfx0_m0"]["vec"]) for b2 in blocks if b2["cfx0_m0"]]
        return False, "cfx0 user VEC never == 0x%x (seen %s)" % (HANDLER, got[:3])
    return True, "cfx0 M0 VEC=0x%x" % HANDLER


@case("cfx0_user_switch_user", "cfx_umon user switch_run_mode = user (0)")
def _cfx0_user_switch_user(blocks, rc):
    b = _first(blocks, lambda b: b["cfx0_m0"] and b["cfx0_m0"]["swmode"] == 0)
    return (b is not None), ("cfx0 M0 SWMODE=0 seen" if b else "cfx0 M0 SWMODE never 0")


@case("cfx0_user_trapmask_cleared",
      "bootrom cleared cfx_umon user trap cfx mask (instruction-type mask, 0 = allow)")
def _cfx0_user_trapmask_cleared(blocks, rc):
    b = _first(blocks, lambda b: b["cfx0_m0"] and b["cfx0_m0"]["trapmask"] == 0)
    return (b is not None), ("cfx0 M0 TRAPMASK=0 seen" if b else "cfx0 M0 TRAPMASK never 0")


@case("gcm_user_cleared", "bootrom cleared cfx_umon user global_cfx_mask (GCM0 -> 0)")
def _gcm_user_cleared(blocks, rc):
    b = _first(blocks, lambda b: b["gcm0"] == 0)
    return (b is not None), ("GCM0=0 seen" if b else "GCM0 never 0")


@case("cfx63_user_vector", "cfx_power user excp_vector = handler 0xffff_ffff_0200")
def _cfx63_user_vector(blocks, rc):
    b = _first(blocks, lambda b: b["cfx63_m0"] and b["cfx63_m0"]["vec"] == HANDLER)
    if b is None:
        got = [hex(b2["cfx63_m0"]["vec"]) for b2 in blocks if b2["cfx63_m0"]]
        return False, "cfx63 user VEC never == 0x%x (seen %s)" % (HANDLER, got[:3])
    return True, "cfx63 M0 VEC=0x%x" % HANDLER


@case("hypv_to_user", "bootrom handed off to app entry in user mode (MODE=0, CFXCODE=0)")
def _hypv_to_user(blocks, rc):
    b = _first(blocks, lambda b: b["pc"] == APP_ENTRY)
    if b is None:
        return False, "no block at app entry 0x%x" % APP_ENTRY
    ok = b["mode"] == 0 and b["cfxcode"] == 0
    return ok, "PC=0x%x MODE=%s CFXCODE=%s" % (b["pc"], b["mode"], b["cfxcode"])


@case("no_supv", "supv is never entered this version (no block MODE == 2)")
def _no_supv(blocks, rc):
    bad = [b["pc"] for b in blocks if b["mode"] == 2]
    return (not bad), ("no MODE=2 block" if not bad else "MODE=2 at %s" % [hex(x) for x in bad[:3]])


@case("stack_in_ram0", "app entry SP (rb1) points into RAM@0")
def _stack_in_ram0(blocks, rc):
    b = _first(blocks, lambda b: b["pc"] == APP_ENTRY)
    if b is None:
        return False, "no block at app entry 0x%x" % APP_ENTRY
    ok = b["rb01"] == RAM0_STACK
    return ok, "rb1=0x%x (exp 0x%x)" % (b["rb01"], RAM0_STACK)


@case("handler_reached", "app trap entered the configured user vector (handler) in user mode")
def _handler_reached(blocks, rc):
    b = _first(blocks, lambda b: b["pc"] == HANDLER and b["mode"] == 0)
    return (b is not None), ("PC=0x%x MODE=0 seen" % HANDLER if b else "handler PC never reached in user mode")


@case("app_exit_0", "bootrom+app end-to-end exit code == 0")
def _app_exit_0(blocks, rc):
    return (rc == EXIT_PASS), "exit=0x%x (exp 0x00)" % (rc if rc is not None else -1)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def main():
    global QEMU, BOOTROM, APP
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--qemu", default=None)
    ap.add_argument("--bootrom", default=None)
    ap.add_argument("--app", default=None)
    args = ap.parse_args()
    if args.qemu:
        QEMU = args.qemu
    if args.bootrom:
        BOOTROM = args.bootrom
    if args.app:
        APP = args.app

    if args.list:
        for n, d, _ in CASES:
            print(n, "-", d)
        return 0

    for p in (QEMU, BOOTROM, APP):
        if not os.path.isfile(p):
            print("[FAIL] missing file: %s" % p)
            return 2

    rc, log = run(BOOTROM, APP)
    if rc is None:
        print("[FAIL] QEMU timed out")
        return 2
    blocks = _parse_blocks(log)

    selected = [(n, d, fn) for (n, d, fn) in CASES if args.only is None or n == args.only]
    if not selected:
        print("[FAIL] no case named %r" % args.only)
        return 1

    all_ok = True
    for name, desc, fn in selected:
        ok, detail = fn(blocks, rc)
        print("[%s] %-24s %s -> %s" % ("PASS" if ok else "FAIL", name, desc, detail))
        if not ok:
            all_ok = False
    print("RESULT: %s" % ("PASS" if all_ok else "FAIL"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
