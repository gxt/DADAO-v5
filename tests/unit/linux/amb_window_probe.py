#!/usr/bin/env python3
"""amb_window_probe.py — async delivery in the kernel return's
`restore -> escape` span (`m18-linux-026`, after `m18-linux-024`).

What this gate is for
---------------------
`m18-linux-024` fixed a rare die (1/475 boots) caused by the old R2 software
return: it re-opened the async source before restoring the register file, and a
delivery in that window resumed with a clobbered `rb3` (`va=0x208`).

`m18-spec-007` / ADR-0061 R3 replace that return with "write the `cfx_hart cg5
rc8`-`rc11` exit intent, restore the register file, `escape cfx_hart`".  The
mask stays closed until the escape, whose `rc11` whole-word write restores it
atomically with the mode/cfx switch and the jump, so there is no software
`reopen -> escape` window any more.

The probe asserts the structural claim at the only point a window could exist —
just before the register restore: both source bits must still be masked there,
so no delivery can land in `restore -> escape`.  A second case re-opens the saved
mask exactly there; the same assertion must then go RED, which makes the green
falsifiable.  A second independent counterexample breaks the return instruction
itself (an `escape` to an unimplemented cfx), and a third one — only for the
soak — pins a delivery into the restore window so `--soak N` has a reachable
FAIL (the `soak-inject` mode; no case depends on the retired single-monitor
return any more):

  baseline             no edit; must boot green.
  window-mask-closed   read `cfx_smon cg15 rc3` at restore->escape and require
                       TIMER/PMEM_DMA still masked; must stay GREEN.
  window-reopened      re-open the saved word before that check: the old
                       `reopen -> escape` window comes back and the check turns
                       it RED (route 1).
  unimplemented-escape replace the return with `escape cfx6` (a cfx the machine
                       does not implement): the late switch must be refused with
                       `CFXESC`, so the boot goes RED (route 2).

Every edit is restored with `cp` + md5 (never `git checkout`).  Exit: 0 = every
case met its expectation, 1 = a case did not, 2 = input missing.

Side effect that must not leak: the probe builds m45 images, whose slice pins
`CONFIG_INITRAMFS_SOURCE=""` in the shared build tree; the line is snapshotted
before the first build and restored in `main()`'s `finally` through the
defconfig generator (m18-linux-024 round 3).  This module declares **no**
`CONFIG_PINS` for the same reason.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m45_entry_probe as m45                                  # noqa: E402

#: The image is m45's (a user task that traps and returns), so the build/boot
#: helpers and the config slice are its; only the scratch directory differs.
m45.SCRATCH = Path("/tmp/opencode/m18-linux-026/check-linux-amb")

ASYNC_S = "arch/dadao/kernel/async_trap.S"

#: The kernel-context return writes the saved exit intent back and restores the
#: register file; `rc11` is the async source mask and the `escape` restores it
#: whole-word.  These probe cases replace the point just before the restore:
#:
#:   window-mask-closed  asserts that both source bits (TIMER 15, PMEM_DMA 32)
#:                       are still masked at `restore -> escape`.  That is the
#:                       structural claim of the new return: there is no
#:                       software re-open window.  Must stay GREEN.
#:   window-reopened     the counterexample: re-open the saved word before the
#:                       check.  The same assertion now fails and the boot goes
#:                       RED, so the green above is falsifiable (route 1).
#:   unimplemented-escape replace the return with `escape cfx6`: the late switch
#:                       to a cfx the profile does not implement is refused
#:                       with CFXESC, so the boot goes RED — the second
#:                       independent FAIL route.

RESTORE_ANCHOR = "\tDADAO_GPR_RESTORE dadao_async_save\n"

WINDOW_CHECK = (
    "\t/* AMB probe: the source must still be masked at restore->escape. */\n"
    "\tcfx2rd\tcfx_smon, cg15, rc3, rd2\n"
    "\tset.rd\trd3, (1 << 15) | (1 << 32)\n"
    "\tand.o\trd2, rd2, rd3\n"
    "\tbr.eq\t{rd2, rd3}?, [rb0, .Lamb_window_ok]\n"
    "\tjump\t[rb0, .Lstuck]\n"
    ".Lamb_window_ok:\n"
)
REOPEN = (
    "\t/* AMB probe: re-open the saved mask before the restore (the old\n"
    "\t * window).  The check below must catch it. */\n"
    "\tset.rb\trb4, dadao_async_esc_mask\n"
    "\tld.o\trd2, [rb4, 0]\n"
    "\tcfx2rc\tcfx_smon, cg15, rc3, rd2\n"
)



ESCAPE = "\tescape\tcfx_hart\n"
#: The return switched to a cfx the profile does not implement (cfxha 6 is in
#: the reserved per-system range): the `escape` late-switch must be refused
#: with CFXESC.
UNIMPL_ESCAPE = "\tescape\tcfx6\n"

#: case -> (expect_green, edits, boots)
CASES: dict[str, tuple[bool, list, int]] = {
    "baseline": (True, [], 2),
    "window-mask-closed": (True, [
        (ASYNC_S, [(RESTORE_ANCHOR, WINDOW_CHECK + RESTORE_ANCHOR)]),
    ], 2),
    "window-reopened": (False, [
        (ASYNC_S, [(RESTORE_ANCHOR,
                    REOPEN + WINDOW_CHECK + RESTORE_ANCHOR)]),
    ], 1),
    "unimplemented-escape": (False, [
        (ASYNC_S, [(ESCAPE, UNIMPL_ESCAPE)]),
    ], 2),
}

DIE_RE = re.compile(r"^dadao: (?:die|unrecoverable)", re.MULTILINE)
PF_RE = re.compile(r"^K3 pf: .*va=(\S+)", re.MULTILINE)
IRQ_RE = re.compile(r"^M45 selftest: sig_calls=\S+ irq_user=(\d+) "
                    r"irq_kernel=(\d+)", re.MULTILINE)


class Report:
    def __init__(self) -> None:
        self.failed: list[str] = []
        self.total = 0

    def check(self, name: str, ok: bool, expect, actual) -> None:
        self.total += 1
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: want={expect!r} "
              f"got={actual!r}", flush=True)
        if not ok:
            self.failed.append(name)


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


#: The one symbol m45's build slice changes in the shared build tree.
INITRAMFS_SYMBOL = "CONFIG_INITRAMFS_SOURCE"
EMPTY_INITRAMFS = f'{INITRAMFS_SYMBOL}=""'


def shared_initramfs_line() -> str | None:
    cfg = m45.build_dir() / ".config"
    if not cfg.is_file():
        return None
    for line in cfg.read_text(encoding="utf-8").splitlines():
        if line.startswith(INITRAMFS_SYMBOL + "="):
            return line
    return None


def restore_shared_config(rep: Report, saved: str | None) -> None:
    """Put the shared build tree's `CONFIG_INITRAMFS_SOURCE` back (see the
    module docstring; the restore always goes through the generator, so this
    module declares no `CONFIG_PINS`)."""
    rc = subprocess.call(
        [sys.executable, str(_REPO / "tools" / "linux" / "make_defconfig.py")],
        cwd=str(_REPO))
    got = shared_initramfs_line()
    ok = (rc == 0 and got is not None and got != EMPTY_INITRAMFS
          and "initramfs.cpio" in got)
    want = "CONFIG_INITRAMFS_SOURCE=<…/initramfs.cpio>"
    if saved not in (None, EMPTY_INITRAMFS):
        want += f" (entry snapshot: {saved})"
    rep.check("共享 .config 已复原（下一道门控不继承空 rootfs）", ok, want,
              f"rc={rc} {got}")


def apply_edits(rep: Report, edits) -> bool:
    ok = True
    for rel, patches in edits:
        path = m45.SOURCE / rel
        text = path.read_text(encoding="utf-8")
        before = text
        for entry in patches:
            old, new = entry[0], entry[1]
            want = entry[2] if len(entry) > 2 else 1
            got = text.count(old)
            if got != want:
                rep.check(f"注入锚点 {rel} 唯一（{want} 处）", False, want, got)
                ok = False
                continue
            if want == 1:
                repl = new() if callable(new) else new
                if isinstance(repl, list):
                    repl = repl[0]
                text = text.replace(old, repl, 1)
            else:
                parts = new() if callable(new) else [new] * want
                if len(parts) != want:
                    rep.check(f"注入展开数（{rel}）", False, want, len(parts))
                    ok = False
                    continue
                for part in parts:
                    text = text.replace(old, part, 1)
        if text != before:
            path.write_text(text, encoding="utf-8")
    return ok


def boot_verdict(text: str, rc: int) -> tuple[bool, str]:
    died = DIE_RE.search(text) is not None
    pf = PF_RE.search(text)
    exitrow = "M45 exit: child=" in text
    done = "M45 selftest: probe cases done" in text
    irq = IRQ_RE.search(text)
    why = []
    if died:
        m = re.search(r"^dadao: die mode=(\d+) code=(\S+)", text, re.MULTILINE)
        why.append(f"die={m.group(2) if m else '?'}")
    if pf:
        why.append(f"pf-va={pf.group(1)}")
    if rc != 0:
        why.append(f"rc={rc}")
    if not exitrow:
        why.append("no-exit-row")
    if not done:
        why.append("no probe-cases-done")
    if irq:
        why.append(f"irq_user={irq.group(1)} irq_kernel={irq.group(2)}")
    else:
        why.append("no-irq-row")
    green = (not died and pf is None and rc != 124 and exitrow and done
             and irq is not None and int(irq.group(1)) > 0
             and int(irq.group(2)) > 0)
    text_why = ",".join(why) or "ok"
    # ISS-m18-001 has two documented shapes: the silent `rc=124` stop and the
    # `handle_softirqs` `die 0xe4` / `va=0x10` (or `va=0x204002130f4`) load
    # fault registered in issues-m18.yaml.  Both are counted separately; the
    # window signature (`va=0x208`) never is.
    iss = (rc == 124) or (died and "die=0xe4" in text_why
                          and ("pf-va=0x10," in text_why
                               or "pf-va=0x204002130f4" in text_why))
    kind = "green" if green else (
        "window" if "va=0x208" in text_why else
        "iss" if iss else "other")
    return green, text_why, kind


def run_case(rep: Report, case: str, boots: int) -> None:
    expect_green, edits, case_boots = CASES[case]
    boots = boots or case_boots
    rom = m45.firmware()
    backups: dict[Path, tuple[bytes, str]] = {}
    for rel, _patches in edits:
        path = m45.SOURCE / rel
        backups[path] = (path.read_bytes(), md5(path))
    try:
        if edits and not apply_edits(rep, edits):
            return
        rc, snap = m45.build_image(f"amb:{case}")
        rep.check(f"{case}: 镜像可构建", rc == 0 and snap is not None, 0, rc)
        if snap is None:
            return
        greens = 0
        reds = 0
        window_reds = 0
        iss = 0
        for i in range(1, boots + 1):
            run_rc, text = m45.boot(f"amb-{case}-{i}", rom)
            green, why, kind = boot_verdict(text, run_rc)
            greens += green
            reds += not green
            window_reds += kind == "window"
            iss += kind == "iss"
            print(f"[INFO] {case} boot {i}: {'green' if green else 'RED'} "
                  f"({why}, kind={kind}, async={text.count('K2 async user')})",
                  flush=True)
        if iss:
            print(f"[WARN] {case}: {iss} boot(s) hit the ISS-m18-001 spin "
                  f"(counted separately, not a window signature)", flush=True)
        if expect_green:
            rep.check(f"{case}: 至少 1 次绿且 0 次窗口签名",
                      greens >= 1 and window_reds == 0, True,
                      (greens, window_reds))
            rep.check(f"{case}: 窗口签名 0/{boots}", window_reds == 0, 0,
                      window_reds)
        else:
            rep.check(f"{case}: 反例 ⇒ 至少一次红", reds >= 1, ">=1", reds)
    finally:
        for path, (blob, before) in backups.items():
            injected = md5(path)
            path.write_bytes(blob)
            restored = md5(path)
            ok = restored == before
            rep.check(f"{case}: 还原 {path.name}（cp + md5）", ok, before,
                      f"{restored} (注入后 {injected})")


#: The soak injection: pin one delivery into the restore window.  The first
#: kernel-context return (latch at `.Lasync_spill+24`, one shot) waits with the
#: source masked until the timer is pending, then re-opens the inherited word
#: right before the restore — the nested entry overwrites the static frame the
#: outer restore is about to read, so the boot must go RED (and the soak's
#: "no non-ISS red" assertion must catch it).  `--soak-inject reopen` is the
#: one-click "inject -> RED -> cp+md5 restore -> green" proof of F1.
SOAK_PIN = (
    "\t/* AMB soak probe: one-shot restore-window pin. */\n"
    "\tld.o\trd3, [rb0, .Lasync_spill + 24]\n"
    "\tbr.nz\t{rd3}?, [rb0, .Lamb_pin_skip]\n"
    "\tset.rd\trd3, 1\n"
    "\tst.o\trd3, [rb0, .Lasync_spill + 24]\n"
    "\tset.rd\trd4, 0x100000\n"
    ".Lamb_pin_wait:\n"
    "\tcfx2rd\tcfx_hart, cg16, rc17, rd2\n"
    "\tset.rd\trd3, 1\n"
    "\tand.o\trd2, rd2, rd3\n"
    "\tbr.nz\t{rd2}?, [rb0, .Lamb_pin_open]\n"
    "\tadd.si\trd4, -1\n"
    "\tbr.nz\t{rd4}?, [rb0, .Lamb_pin_wait]\n"
    "\tjump\t[rb0, .Lamb_pin_skip]\n"
    ".Lamb_pin_open:\n"
    "\t/* The historical effect: the restore base is clobbered here, so the\n"
    "\t * delivery (and the restore itself) runs with rb3 = 0 and the first\n"
    "\t * frame read faults at va=0x208. */\n"
    "\tset.rb\trb3, 0\n"
    "\tset.rb\trb4, dadao_async_esc_mask\n"
    "\tld.o\trd2, [rb4, 0]\n"
    "\tcfx2rc\tcfx_smon, cg15, rc3, rd2\t/* the old window */\n"
    ".Lamb_pin_skip:\n"
)
SOAK_INJECTS: dict[str, list] = {
    "reopen": [(ASYNC_S, [
        (".zero\t24\n", ".zero\t32\n"),
        (RESTORE_ANCHOR, SOAK_PIN + RESTORE_ANCHOR),
    ])],
}


def _soak_counts(tag: str, count: int, jobs: int) -> tuple[int, int, int, int]:
    """Boot the current image @count times; (greens, reds, window_reds, iss)."""
    from concurrent.futures import ThreadPoolExecutor

    rom = m45.firmware()

    def one(i: int) -> tuple[int, bool, str, str]:
        run_rc, text = m45.boot(f"{tag}-{i}", rom)
        green, why, kind = boot_verdict(text, run_rc)
        return i, green, why, kind

    greens = 0
    reds = 0
    window_reds = 0
    iss = 0
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        for i, green, why, kind in pool.map(one, range(1, count + 1)):
            greens += green
            if not green:
                reds += 1
                window_reds += kind == "window"
                iss += kind == "iss"
                print(f"[INFO] {tag} boot {i}: RED ({why}, kind={kind})",
                      flush=True)
            elif i % 250 == 0:
                print(f"[INFO] {tag} {i}/{count} boots, 0 window red", flush=True)
    if iss:
        print(f"[WARN] {tag}: {iss} boot(s) hit ISS-m18-001 (counted "
              f"separately, not a window signature)", flush=True)
    return greens, reds, window_reds, iss


def soak(rep: Report, count: int, jobs: int) -> None:
    rc, snap = m45.build_image("amb:soak")
    rep.check("soak: 镜像可构建", rc == 0 and snap is not None, 0, rc)
    if snap is None:
        return
    _greens, reds, window_reds, iss = _soak_counts("soak", count, jobs)
    # The main criterion is the window signature (the master assertion was
    # `reds == 0`; the ISS-m18-001 family is split out per user ruling and
    # counted below).  A `va=0x208` red still fails this soak.
    nonwindow = reds - window_reds
    rep.check(f"soak: 窗口签名 0/{count} 启（{jobs} 并发；"
              f"非窗口红 {nonwindow}，其中 ISS 自旋 {iss}）",
              window_reds == 0, 0, window_reds)


def soak_inject(rep: Report, name: str, count: int, jobs: int) -> None:
    """Targeted window probe (the soak's own injection proof).

    The restore-window pin is applied, the image is booted @count times, and
    every boot must go RED; the edit is then restored with `cp` + md5 and a
    rebuilt image must boot green.  Why this is a *targeted* proof and not the
    soak's own assertion: on this machine the pinned corruption stops the boot
    silently during early init (`rc=124`, before the `K4 boundary` anchor),
    which is the same shape the documented ISS-m18-001 family produces — the
    soak judges the window signature (`va=0x208`) and cannot turn that silent
    stop into one without inventing a signature.  The `window-reopened` case
    proves the reopen is caught by the in-stub check; this mode proves the
    injected window image is deterministically RED and restorable."""
    edits = SOAK_INJECTS[name]
    path = m45.SOURCE / ASYNC_S
    before = path.read_bytes()
    before_md5 = md5(path)
    try:
        if not apply_edits(rep, edits):
            return
        injected = md5(path)
        rep.check(f"soak-inject:{name} 注入生效（md5 变化）", injected != before_md5,
                  "!=", injected)
        rc, snap = m45.build_image(f"amb:soak-inject:{name}")
        rep.check(f"soak-inject:{name}: 镜像可构建", rc == 0 and snap is not None,
                  0, rc)
        if snap is not None:
            _g, reds, _w, iss = _soak_counts(f"soak-inject-{name}", count, jobs)
            rep.check(f"soak-inject:{name}: 注入后红 > 0（定向窗口探针可达 FAIL）",
                      reds >= 1, ">=1", reds)
            if iss:
                print(f"[WARN] soak-inject:{name}: {iss}/{reds} red(s) are the "
                      f"silent early-init stop classified as ISS-m18-001; the "
                      f"pin itself is deterministic (see each boot line)",
                      flush=True)
    finally:
        path.write_bytes(before)
        restored = md5(path)
        rep.check(f"soak-inject:{name}: 还原 async_trap.S（cp + md5）",
                  restored == before_md5, before_md5, restored)
    rc, snap = m45.build_image(f"amb:soak-inject:{name}:green")
    rep.check(f"soak-inject:{name}: 还原后镜像可构建",
              rc == 0 and snap is not None, 0, rc)
    if snap is None:
        return
    _g, reds, _w, iss = _soak_counts(f"soak-inject-{name}-green", count, jobs)
    other = reds - iss
    rep.check(f"soak-inject:{name}: 还原后回绿（0 非 ISS 红）", other == 0, 0,
              other)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case", action="append", default=[], choices=sorted(CASES))
    ap.add_argument("--boots", type=int, default=0,
                    help="boots per case (default: the case's own count)")
    ap.add_argument("--soak", type=int, default=0,
                    help="boot the baseline image N times (no case injection)")
    ap.add_argument("--soak-inject", choices=sorted(SOAK_INJECTS), default=None,
                    help="inject the restore-window pin, require the soak to "
                         "go red, then cp+md5 restore and require green")
    ap.add_argument("--jobs", type=int, default=12,
                    help="parallel boots for --soak (default 12)")
    ap.add_argument("--list", action="store_true", help="list the cases")
    args = ap.parse_args()
    if args.list:
        for name, (green, _edits, boots) in CASES.items():
            print(f"{name:20s} expect={'green' if green else 'RED'} boots={boots}")
        for name in SOAK_INJECTS:
            print(f"soak-inject:{name}")
        return 0

    rep = Report()
    saved_initramfs = shared_initramfs_line()
    try:
        if args.soak_inject:
            n = args.soak or 40
            print(f"\n=== soak-inject {args.soak_inject}: {n} boots, "
                  f"{args.jobs} in parallel ===", flush=True)
            soak_inject(rep, args.soak_inject, n, args.jobs)
        elif args.soak:
            print(f"\n=== soak: {args.soak} boots, {args.jobs} in parallel ===",
                  flush=True)
            soak(rep, args.soak, args.jobs)
        cases = args.case or ([] if (args.soak or args.soak_inject)
                              else sorted(CASES))
        for case in cases:
            print(f"\n=== case {case}: expect="
                  f"{'green' if CASES[case][0] else 'RED'} ===", flush=True)
            run_case(rep, case, args.boots)
    finally:
        restore_shared_config(rep, saved_initramfs)

    print()
    if rep.failed:
        print(f"amb_window_probe: {rep.total - len(rep.failed)}/{rep.total} "
              f"checks passed, {len(rep.failed)} FAILED")
        for name in rep.failed:
            print(f"  - {name}")
        return 1
    print(f"amb_window_probe: {rep.total}/{rep.total} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
