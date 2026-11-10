#!/usr/bin/env python3
"""check_log — m12-chipyard-019 log oracle for the chipyard Tiny case.

Reads the ``+verbose`` harness log of ``tools/chipyard/excp/app.S`` and checks
it against values that come from the *outside* of the run:

  * cause ids / `cause_info` semantics from `spec/Machine-v5 §4.4` and
    `spec/DADAO-13 §2`;
  * faulting instruction addresses from the ELF symbols (`llvm-nm`);
  * instruction words (the `cause_info` of ILLI/UNDI/CFXREG/CFXTRAP) from the
    ELF disassembly (`llvm-objdump`);
  * cg7 space descriptors from `style` (§3.8: `start = base - (cfxha << 42)`).

Checks, all of which must pass:
  1. exactly one hmon entry per expected event, in program order;
  2. the three-register frame (cg5 rc2/rc3/rc4) read by the handler for every
     entry, with the spec `cause_id` / `cause_ip` / `cause_info`;
  3. the escape offset: +4 for the skip classes, 0 for IALIGN after the
     handler rewrote `excp_cause_ip` to `(ip & ~3) + 4`;
  4. the register-group read-backs (cfx_hmon / cfx_power cg3/cg5/cg7);
  5. the cg3-only-in-hypv pair: CFXREG in `supv`, success in `hypv`.

Usage:
  check_log.py --log LOG --app-elf APP --power-elf POWER \
               --nm llvm-nm --objdump llvm-objdump
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys

ENTRY = 0xFFFF_FF01_0100
HMON_BASE = 0x0FFF_0000_0000
BOOTROM_BASE = 0xFFFF_FFFF_0000
RAM_BASE = 0xFFFF_FF00_0000
BOOT_MAGIC = 0x30001

CAUSE = {
    "CFXTRAP": 1 << 0,
    "CFXMEM": 1 << 1,
    "CFXREG": 1 << 2,
    "CFXESC": 1 << 3,
    "ILLI": 1 << 8,
    "UNDI": 1 << 9,
    "MALIGN": 1 << 12,
    "IALIGN": 1 << 13,
}

EXCP_RE = re.compile(
    r"WumingCore: excp cause=0x([0-9a-f]+) cause_ip=0x([0-9a-f]+) "
    r"info=0x([0-9a-f]+) vector=0x([0-9a-f]+)")
ESC_RE = re.compile(
    r"WumingCore: escape ip=0x([0-9a-f]+) frame=0x([0-9a-f]+) "
    r"cause_ip=0x([0-9a-f]+) target=0x([0-9a-f]+) mode=(\d+)")
CFX2_RE = re.compile(
    r"WumingCore: cfx2 ip=0x([0-9a-f]+) ha=\s*(\d+) cg=\s*(\d+) rc=\s*(\d+) "
    r"write=(\d) ok=(\d) mode=(\d) data=0x([0-9a-f]+) wdata=0x([0-9a-f]+)")

PASS = 0
FAIL = 0


def ok(name, expected, actual):
    global PASS
    PASS += 1
    print("  [PASS] %s | expected=%s actual=%s" % (name, expected, actual))


def bad(name, expected, actual):
    global FAIL
    FAIL += 1
    print("  [FAIL] %s | expected=%s actual=%s" % (name, expected, actual))


def eq(name, expected, actual):
    if expected == actual:
        ok(name, hex(expected) if isinstance(expected, int) else expected,
           hex(actual) if isinstance(actual, int) else actual)
    else:
        bad(name, hex(expected) if isinstance(expected, int) else expected,
            hex(actual) if isinstance(actual, int) else actual)


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


def read_symbols(nm, path):
    syms = {}
    for line in run([nm, path]).splitlines():
        parts = line.split()
        if len(parts) == 3:
            syms[parts[2]] = int(parts[0], 16)
    return syms


def read_words(objdump, path):
    words = {}
    for line in run([objdump, "-d", path]).splitlines():
        m = re.match(r"\s*([0-9a-f]+): ((?:[0-9a-f]{2} ){4})", line)
        if m:
            words[int(m.group(1), 16)] = int(m.group(2).replace(" ", ""), 16)
    return words


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--app-elf", required=True)
    ap.add_argument("--power-elf", required=True)
    ap.add_argument("--nm", default="llvm-nm")
    ap.add_argument("--objdump", default="llvm-objdump")
    args = ap.parse_args()

    log = open(args.log, errors="replace").read().splitlines()
    sym = read_symbols(args.nm, args.app_elf)
    psym = read_symbols(args.nm, args.power_elf)
    word = read_words(args.objdump, args.app_elf)
    pword = read_words(args.objdump, args.power_elf)

    # The power stub's `trap cfx_hmon, <boot_magic>`: opcode 0x7F, immu18 = magic.
    traps = [a for a, w in pword.items()
             if (w >> 24) == 0x7F and (w & 0x3FFFF) == BOOT_MAGIC]
    if len(traps) != 1:
        bad("power stub has exactly one CFXTRAP handoff", 1, len(traps))
        traps = traps[:1] or [0]
    handoff_ip = traps[0] & 0xFFFF_FFFF_FFFF
    handoff_info = pword.get(handoff_ip, 0)

    def at(name):
        if name not in sym:
            bad("app symbol %s" % name, "present", "missing")
            return 0
        return sym[name]

    # ---- expected hmon entries, in program order -------------------------
    tgt = [at("ialign_tgt0"), at("ialign_tgt1"), at("ialign_tgt2")]
    expected = [("CFXTRAP", handoff_ip, handoff_info)]
    for name in ("f_cg8_hmon", "f_cg8_power"):
        a = at(name)
        expected.append(("CFXREG", a, word.get(a, 0)))
    for name, addr in (("f_malign0", RAM_BASE + 1), ("f_malign1", RAM_BASE + 4),
                       ("f_malign2", RAM_BASE + 2)):
        expected.append(("MALIGN", at(name), addr))
    for name in ("f_illi0", "f_illi1", "f_illi2"):
        a = at(name)
        expected.append(("ILLI", a, word.get(a, 0)))
    for name in ("f_undi0", "f_undi1", "f_undi2"):
        a = at(name)
        expected.append(("UNDI", a, word.get(a, 0)))
    for name, addr in (("f_mem0", 0x10_0000_0000),
                       ("f_mem1", 0xFFFF_FF80_0000),
                       ("f_mem2", HMON_BASE + 0x10000)):
        expected.append(("CFXMEM", at(name), addr))
    for i, off in enumerate((1, 2, 3)):
        expected.append(("IALIGN", tgt[i] + off, tgt[i] + off))
    expected.append(("CFXREG", at("f_cg3_supv"), word.get(at("f_cg3_supv"), 0)))

    # ---- parse the log ---------------------------------------------------
    excp, esc, cfx2 = [], [], []
    for i, line in enumerate(log):
        m = EXCP_RE.search(line)
        if m:
            excp.append((int(m.group(1), 16), int(m.group(2), 16),
                         int(m.group(3), 16), int(m.group(4), 16)))
            continue
        m = ESC_RE.search(line)
        if m:
            esc.append((int(m.group(1), 16), int(m.group(2), 16),
                        int(m.group(3), 16), int(m.group(4), 16),
                        int(m.group(5))))
            continue
        m = CFX2_RE.search(line)
        if m:
            cfx2.append(dict(ip=int(m.group(1), 16), ha=int(m.group(2)),
                             cg=int(m.group(3)), rc=int(m.group(4)),
                             write=int(m.group(5)), ok=int(m.group(6)),
                             mode=int(m.group(7)), data=int(m.group(8), 16),
                             wdata=int(m.group(9), 16)))

    eq("hmon entries (handoff + 18 synchronous)", len(expected), len(excp))

    # frame reads: the handler reads cg5 rc2/rc3/rc4 at the top of every entry
    frames = [c for c in cfx2 if c["ha"] == 3 and c["cg"] == 5 and
              c["write"] == 0 and c["rc"] in (2, 3, 4)]
    eq("frame reads (3 per entry)", 3 * len(expected), len(frames))
    groups = [frames[i:i + 3] for i in range(0, len(frames), 3)]
    for i, g in enumerate(groups):
        if [c["rc"] for c in g] != [2, 3, 4]:
            bad("frame read order of entry %d" % i, "[2, 3, 4]",
                str([c["rc"] for c in g]))

    # ---- per-entry checks ------------------------------------------------
    # The program ends with the forged-frame escape (a guest-written frame
    # leaves hypv), which is not an exception entry: it sits between the IALIGN
    # entries and the cg3-in-supv CFXREG entry.
    land = at("land_supv")
    forged_at = len(expected) - 1
    for i, (cls, ip, info) in enumerate(expected):
        got = excp[i] if i < len(excp) else (0, 0, 0, 0)
        eq("entry %d cause id (%s)" % (i, cls), CAUSE[cls], got[0])
        eq("entry %d cause_ip" % i, ip, got[1])
        eq("entry %d cause_info" % i, info, got[2])
        eq("entry %d vector = hmon base" % i, HMON_BASE, got[3])
        if i < len(groups):
            eq("entry %d frame cause_id" % i, CAUSE[cls], groups[i][0]["data"])
            eq("entry %d frame cause_ip" % i, ip, groups[i][1]["data"])
            eq("entry %d frame cause_info" % i, info, groups[i][2]["data"])
        # the matching escape, in order
        e_idx = i if i < forged_at else i + 1
        if e_idx < len(esc):
            e = esc[e_idx]
            if cls == "IALIGN":
                eq("escape %d is offset 0 on the aligned word" % i,
                   (ip & ~3) + 4, e[3])
                eq("escape %d rewritten cause_ip" % i, (ip & ~3) + 4, e[2])
            else:
                eq("escape %d target = cause_ip + 4" % i, ip + 4, e[3])
                eq("escape %d cause_ip unchanged" % i, ip, e[2])
            eq("escape %d mode = hypv" % i, 3, e[4])
    eq("escape lines (entries + forged frame)", len(expected) + 1, len(esc))
    if forged_at < len(esc):
        f = esc[forged_at]
        eq("forged escape runs in hypv (pre-escape mode)", 3, f[4])
        eq("forged escape target", land, f[3])
        eq("forged escape uses escape +4 on a written cause_ip", land - 4, f[2])

    # IALIGN: the handler rewrote excp_cause_ip through cfx2rc (RW register)
    for i, off in enumerate((1, 2, 3)):
        want = (tgt[i] & ~3) + 4
        hit = any(c["ha"] == 3 and c["cg"] == 5 and c["rc"] == 3 and
                  c["write"] == 1 and c["wdata"] == want for c in cfx2)
        if hit:
            ok("IALIGN %d handler wrote excp_cause_ip" % i, hex(want), hex(want))
        else:
            bad("IALIGN %d handler wrote excp_cause_ip" % i, hex(want), "absent")

    # Tiny stays in hypv: every synchronous entry sets excp_prev_run_mode = 3
    prev = [c for c in cfx2 if c["ha"] == 3 and c["cg"] == 5 and
            c["rc"] == 0 and c["write"] == 1 and c["wdata"] == 3]
    eq("handler forces excp_prev_run_mode = 3 (sync entries)",
       len(expected) - 1, len(prev))

    # ---- cg3 is hypv-only: the (case, counter-example) pair --------------
    supv = [c for c in cfx2 if c["ip"] == at("f_cg3_supv")]
    hypv = [c for c in cfx2 if c["ip"] == at("land_after") + 4]
    if supv and hypv:
        eq("cg3 access in supv is rejected", 0, supv[0]["ok"])
        eq("cg3 access in supv reports mode 2", 2, supv[0]["mode"])
        eq("cg3 access in hypv succeeds", 1, hypv[0]["ok"])
        eq("cg3 access in hypv reports mode 3", 3, hypv[0]["mode"])
        eq("cg3 read-back value", HMON_BASE, hypv[0]["data"])
    else:
        bad("cg3 supv/hypv pair present", "2 records", str(len(supv) + len(hypv)))

    # ---- register-group read-backs ---------------------------------------
    reads = [(c["ha"], c["cg"], c["rc"], c["write"],
              c["wdata"] if c["write"] else c["data"], c["ok"])
             for c in cfx2 if c["ha"] in (3, 63)]
    wanted = [
        ("hmon excp_vector reset", (3, 3, 10, 0, HMON_BASE, 1)),
        ("hmon excp_vector write +3", (3, 3, 10, 1, HMON_BASE + 3, 1)),
        ("hmon switch_run_mode reset", (3, 3, 8, 0, 3, 1)),
        ("hmon switch_run_mode write ignored", (3, 3, 8, 1, 0, 1)),
        ("hmon cfxtrap mask reset", (3, 3, 0, 0, 0x7FFF_FFFF_FFFF_FFF7, 1)),
        ("hmon cfx_intr_mask reset", (3, 3, 4, 0, 0xFFFF_FFFF_FFFF_FFFF, 1)),
        ("hmon cfxmem mask RW", (3, 3, 1, 1, 0x0F0F, 1)),
        ("hmon cg7 desc / SRAM", (3, 7, 0, 0, 0x3, 1)),
        ("hmon cg7 start", (3, 7, 1, 0, HMON_BASE - (3 << 42), 1)),
        ("hmon cg7 size", (3, 7, 2, 0, 0x1_0000, 1)),
        ("hmon cg7 attr / RWX", (3, 7, 3, 0, 0x7, 1)),
        ("hmon cg7 block 1 absent", (3, 7, 4, 0, 0x0, 1)),
        ("power cg7 desc / ROM", (63, 7, 0, 0, 0x5, 1)),
        ("power cg7 start", (63, 7, 1, 0, BOOTROM_BASE - (63 << 42), 1)),
        ("power cg7 size", (63, 7, 2, 0, 0x1_0000, 1)),
        ("power cg7 attr / RX", (63, 7, 3, 0, 0x5, 1)),
        ("power excp_vector = BootROM", (63, 3, 10, 0, BOOTROM_BASE, 1)),
        ("power cfxtrap mask reset", (63, 3, 0, 0, 0xFFFF_FFFF_FFFF_FFF7, 1)),
        ("hmon cg8 rc1 unimplemented", (3, 8, 1, 0, None, 0)),
        ("power cg8 rc1 unimplemented", (63, 8, 1, 0, None, 0)),
    ]
    pos = 0
    for name, want in wanted:
        found = -1
        for j in range(pos, len(reads)):
            got = reads[j]
            if want[4] is None:
                if got[:4] == want[:4] and got[5] == want[5]:
                    found = j
                    break
            elif got == want:
                found = j
                break
        if found >= 0:
            ok(name, "present", "present")
            pos = found + 1
        else:
            bad(name, "present", "absent")

    # no core-bug sink may fire
    faults = [l for l in log if "WumingCore: fault " in l]
    eq("no FAULT sink entry", 0, len(faults))

    print("\ncheck_log: PASS=%d FAIL=%d" % (PASS, FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
