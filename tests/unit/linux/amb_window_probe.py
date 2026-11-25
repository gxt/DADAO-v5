#!/usr/bin/env python3
"""amb_window_probe.py — asynchronous delivery *inside* the umon return window
(`m18-linux-024`).

What this gate is for
---------------------
A delivery taken while the kernel is in the middle of a return stub resumes at
the next instruction with the *whole* interrupted register file.  The earlier
software return ended with `set.rb rb3, 0; jump [rb3, rd3, 0]`, so `rb3` came
back as 0; the umon/smon return stubs use `rb3` as their frame base, and a
delivery in their `reopen -> escape` window therefore made the interrupted
`ldm.o {rb1:rb2}, [rb3, rd1]` read from address `0x208` (`va=0x208` -> die).
The natural rate is ~1/475 boots, which is too rare to judge a fix by.

The window is *level-triggered*: the source is only delivered when the run
mode's mask allows it, so a tick that arrives while the return stub has the
mask closed is delivered at the first instruction boundary after the stub
re-opens it.  This gate turns that into a deterministic instrument: it moves
the re-open to just before the register restore and holds it open for one tick
period, so every return takes a delivery inside the window.  The image and the
program are the same one `m45_entry_probe.py` uses (a user task that traps and
returns in a loop), so the window is walked dozens of times per boot.

Cases (each is a source injection on top of the *current* tree; every edit is
restored by `cp` + md5):

  baseline                no edit; must boot green (the instrument itself is
                          not what makes a boot fail)
  window                  the umon window pin (`trap.S`); must stay green —
                          **the fix**: the resume is an `escape` and occupies
                          no register
  window-no-escape        the window pin plus a software-jump resume (no
                          `escape`): the interrupted cfx is never restored; must
                          go RED (protection route 2)
                          (`set.rb rb3, 0; jump [rb3, rd3, 0]`); must go RED
                          with the `va=0x208` die (protection route 1)
  nested                  the same instrument inside the new return trampoline
                          (a delivery inside the trampoline's own window); must
                          stay green
  nested-no-chain         the nested instrument plus removal of the entry's
                          "interrupted cfx is the trampoline" guard; must go
                          RED (protection route 2: the nested pass resolves
                          the outer resume)

Exit: 0 = every case met its expectation (and every restoration matched md5);
1 = a case did not; 2 = an input could not be derived (source/build missing).

Side effect that must not leak: the probe builds m45 images, and m45's slice
pins `CONFIG_INITRAMFS_SOURCE=""` (that image must not run an initramfs) in the
*shared* build tree.  The line is snapshotted before the first build and
restored in `main()`'s `finally` by running the defconfig generator
(`tools/linux/make_defconfig.py`); the snapshot is only what the restore is
asserted against (the symbol must read the cpio path afterwards, never `""`).
Without that, the next K5/K6 gate inherits an empty rootfs (`/init.musl`
ENOENT, "No working init found") — m18-linux-024 round 3.

This module deliberately declares **no** `CONFIG_PINS`: it holds no config
slice of its own (it reuses m45's `CONFIG_PINS` + `NO_INITRAMFS` through
`m45.build_image()`), and `check-config-pins`'s C2 rule — "any script that
calls `apply_config_lines()` declares `CONFIG_PINS`" — is why the restore goes
through the generator command instead of `apply_config_lines()`.
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
m45.SCRATCH = Path("/tmp/opencode/m18-linux-024/check-linux-amb")

TRAP_S = "arch/dadao/kernel/trap.S"
ASYNC_S = "arch/dadao/kernel/async_trap.S"


#: The two umon return tails (syscall + retry) share this sequence verbatim:
#: mask the source, restore the file, then re-open.  The pin moves the re-open
#: in front of the restore and holds it open.
UMON_TAIL = (
    "\tset.rd\trd2, (1 << 15) | (1 << 32)\n"
    "\tcfx2rd\tcfx_smon, cg8, rc1, rd3\n"
    "\tor.o\trd2, rd2, rd3\n"
    "\tcfx2rc\tcfx_smon, cg8, rc1, rd2\n"
    "\tDADAO_GPR_RESTORE_AT_KEEP_RD23_RB345\n"
    "\tset.rb\trb4, dadao_supv_saved_mask\n"
    "\tld.o\trd2, [rb4, 0]\n"
    "\tcfx2rc\tcfx_smon, cg8, rc1, rd2\n"
)

JUMP_TAIL = (
    "\t/* 4. The two scratch registers, from the region. */\n"
    "\tld.o\trd2, [rb3, DADAO_ASYNC_RESUME_RD2]\n"
    "\tld.o\trb3, [rb3, DADAO_ASYNC_RESUME_RB3]\n"
    "\n"
    "\t/* 5. Register-free resume. */\n"
    "\tescape\tcfx_jmon, [excp_cause_ip, 0]\n"
)

TRAMP_OPEN = (
    "\t/* 3. Re-open the source word the entry masked. */\n"
    "\tld.o\trd2, [rb3, DADAO_ASYNC_RESUME_MASK]\n"
    "\tcfx2rc\tcfx_smon, cg8, rc1, rd2\n"
)

CHAIN_GUARD = (
    "\tset.rb\trb4, dadao_async_prev_cfx\n"
    "\tld.o\trd2, [rb4, 0]\n"
    "\tset.rd\trd3, DADAO_CFX_JMON\n"
    "\tbr.eq\t{rd2, rd3}?, [rb0, .Lasync_region_done]\n"
)


#: A tick is *due* when `cfx_hart cg8 rc5` (`timer_ctrl`) has ISTATUS set
#: (bit 2, spec/DADAO-12 §4.7) — the same signal `kernel/time.c` acks, and it
#: is evaluated regardless of the source mask.
WAIT_TICK = (
    "\tset.rd\trd3, (1 << 2)\n"
    "{tag}:\n"
    "\tcfx2rd\tcfx_hart, cg8, rc5, rd2\n"
    "\tand.o\trd2, rd2, rd3\n"
    "\tbr.z\t{{rd2}}?, [rb0, {tag}]\n"
)

#: `~((1 << 15) | (1 << 32))`: open both source bits whatever the inherited
#: word carried (`dadao_supv_saved_mask` is the word the *entry* captured, and
#: a user return normally carries it masked).
OPEN_SOURCES = (
    "\tset.rb\trb4, dadao_supv_saved_mask\n"
    "\tld.o\trd2, [rb4, 0]\n"
    "\tset.rd\trd3, 0xfffffffeffff7fff\n"
    "\tand.o\trd2, rd2, rd3\n"
    "\tcfx2rc\tcfx_smon, cg8, rc1, rd2\n"
)


def _wait(tag: str) -> str:
    return WAIT_TICK.format(tag=tag)


def umon_pin() -> str:
    """The umon window pin: wait (masked) until a tick is due, then open the
    source *here*, so the delivery is taken at the first boundary of the
    register restore on every return.  One label per expansion (the tail
    appears twice)."""
    out = []
    for tag in ("a", "b"):
        out.append(
            "\tset.rd\trd2, (1 << 15) | (1 << 32)\n"
            "\tcfx2rd\tcfx_smon, cg8, rc1, rd3\n"
            "\tor.o\trd2, rd2, rd3\n"
            "\tcfx2rc\tcfx_smon, cg8, rc1, rd2\n"
            "\t/* AMB probe: wait for a due tick with the source masked, then\n"
            "\t * open it before the register restore: the delivery is taken at\n"
            "\t * the first boundary of the restore. */\n"
            + _wait(f".Lamb_window_{tag}")
            + OPEN_SOURCES
            + "\tDADAO_GPR_RESTORE_AT_KEEP_RD23_RB345\n"
        )
    return out


def tramp_pin() -> str:
    """A delivery inside the trampoline's own window.

    The trampoline runs as `cfx_jmon` and the kernel does not open
    `cfx_hart`'s rows to that source (nothing in production reads them from
    here), so this instrument spins for a *fixed* count — long enough for one
    timer tick (10 ms period; the count is a probe knob, not a contract) —
    while the source mask is still closed, and then re-opens: the delivery is
    taken at the next instruction, inside the trampoline.

    Only a pass whose *interrupted* context is `cfx_umon`/`cfx_smon` spins:
    that is the probe phase (a boot-time delivery runs as `cfx_hmon`, and a
    nested pass reports `cfx_jmon` — spinning there again would nest for
    ever and turn the instrument into a boot-time cost)."""
    return (
        "\t/* AMB probe: only the probe phase's outermost pass spins (a\n"
        "\t * nested pass would nest again for ever), and it waits about one\n"
        "\t * tick period with the source masked so the nested delivery lands\n"
        "\t * in this window. */\n"
        "\tset.rb\trb3, dadao_async_prev_cfx\n"
        "\tld.o\trd2, [rb3, 0]\n"
        "\tbr.z\t{rd2}?, [rb0, .Lamb_tramp_do]\n"
        "\tset.rd\trd3, DADAO_CFX_SMON\n"
        "\tbr.eq\t{rd2, rd3}?, [rb0, .Lamb_tramp_do]\n"
        "\tjump\t[rb0, .Lamb_tramp_skip]\n"
        ".Lamb_tramp_do:\n"
        "\tset.rd\trd3, 0x100000\n"
        ".Lamb_tramp_wait:\n"
        "\tadd.si\trd3, -1\n"
        "\tbr.nz\t{rd3}?, [rb0, .Lamb_tramp_wait]\n"
        ".Lamb_tramp_skip:\n"
        "\tset.rb\trb3, dadao_async_save\n"
        + TRAMP_OPEN
    )


#: case -> (expect_green, window_instrument, edits, boots)
#: `window_instrument` means the case saturates the delivery window on purpose:
#: it then judges "the user task completed, no die, deliveries happened in the
#: window" instead of the full m45 case set (the instrument starves the
#: user-mode delivery case by construction — the unpinned `baseline` is what
#: keeps that one honest).
CASES: dict[str, tuple[bool, bool, list, int]] = {
    "baseline": (True, False, [], 2),
    "window": (True, True, [(TRAP_S, [(UMON_TAIL, umon_pin, 2)])], 2),
    "window-clobber-rb3": (False, True, [
        (TRAP_S, [(UMON_TAIL, umon_pin, 2)]),
        (ASYNC_S, [(JUMP_TAIL, (
            "\t/* AMB probe: the resume tail writes a register the interrupted\n"
            "\t * context owns (`rb3`) — the pre-m18-linux-024 mechanism. */\n"
            "\tld.o\trd2, [rb3, DADAO_ASYNC_RESUME_RD2]\n"
            "\tld.o\trb3, [rb3, DADAO_ASYNC_RESUME_RB3]\n"
            "\tset.rb\trb3, 0\n"
            "\tescape\tcfx_jmon, [excp_cause_ip, 0]\n"))]),
    ], 2),
    "window-no-escape": (False, True, [
        (TRAP_S, [(UMON_TAIL, umon_pin, 2)]),
        (ASYNC_S, [(JUMP_TAIL, (
            "\t/* AMB probe: resume by software jump instead of `escape` (the\n"
            "\t * interrupted cfx is never restored). */\n"
            "\tld.o\trd2, [rb3, DADAO_ASYNC_RESUME_RD2]\n"
            "\tld.o\trd3, [rb3, DADAO_ASYNC_RESUME_IP]\n"
            "\tset.rb\trb3, 0\n"
            "\tjump\t[rb3, rd3, 0]\n"))]),
    ], 1),
    "nested": (True, True, [(ASYNC_S, [(TRAMP_OPEN, tramp_pin)])], 2),
    "nested-no-chain": (False, True, [
        (ASYNC_S, [(TRAMP_OPEN, tramp_pin),
                   (CHAIN_GUARD, "\t/* AMB probe: chain guard removed. */\n")]),
    ], 5),
}

DIE_RE = re.compile(r"^dadao: (?:die|unrecoverable)", re.MULTILINE)
PF_RE = re.compile(r"^K3 pf: .*va=(\S+)", re.MULTILINE)
IRQ_RE = re.compile(r"^M45 selftest: sig_calls=\S+ irq_user=(\d+) "
                    r"irq_kernel=(\d+)", re.MULTILINE)
ITERS_RE = re.compile(r"^M45 selftest: iters=(\d+)", re.MULTILINE)


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
        else:
            pass


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


#: The one symbol m45's build slice changes in the shared build tree.
INITRAMFS_SYMBOL = "CONFIG_INITRAMFS_SOURCE"
EMPTY_INITRAMFS = f'{INITRAMFS_SYMBOL}=""'


def shared_initramfs_line() -> str | None:
    """The shared `.config`'s `CONFIG_INITRAMFS_SOURCE=` line (None if absent)."""
    cfg = m45.build_dir() / ".config"
    if not cfg.is_file():
        return None
    for line in cfg.read_text(encoding="utf-8").splitlines():
        if line.startswith(INITRAMFS_SYMBOL + "="):
            return line
    return None


def restore_shared_config(rep: Report, saved: str | None) -> None:
    """Put the shared build tree's `CONFIG_INITRAMFS_SOURCE` back.

    `m45.build_image()` pins it to "" so the probe image does not hand the
    machine to an initramfs; the build tree is *shared*, so a K5/K6 gate that
    runs next would boot an empty rootfs (`/init.musl` ENOENT, "No working init
    found").  The restore is **always** the defconfig generator's own command
    (`tools/linux/make_defconfig.py`): this probe holds no config slice of its
    own — it reuses m45's `CONFIG_PINS` + `NO_INITRAMFS` through
    `m45.build_image()` — and `check-config-pins`'s C2 rule requires any script
    that calls `apply_config_lines()` to declare `CONFIG_PINS`, which this one
    must not (a second, drifting slice is exactly what C2 exists to prevent).
    The snapshot is only an *assertion* input: after the generator the symbol
    must be the cpio path, never `""`.
    """
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
    """Apply (file, [(old, new, count)]); False if an anchor is not unique."""
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
                text = text.replace(old, repl, 1)
            else:
                # One label per expansion: the replacement is a callable.
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


def boot_verdict(text: str, rc: int, window: bool) -> tuple[bool, str]:
    """One boot -> (green, why).

    A boot is green when the machine reached the end of the probe program
    without a die or a page fault on the way.  With the window instrument in
    place the m45 case set is judged separately: the instrument saturates the
    window, so its own criteria are "the user task completed" and "deliveries
    landed in the window" (the unpinned `baseline` keeps the full case set).
    """
    died = DIE_RE.search(text) is not None
    pf = PF_RE.search(text)
    exitrow = "M45 exit: child=" in text
    done = "M45 selftest: probe cases done" in text
    irq = IRQ_RE.search(text)
    iters = ITERS_RE.search(text)
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
    if not window and not done:
        why.append("no probe-cases-done")
    if window:
        kernel = int(irq.group(2)) if irq else 0
        want = int(iters.group(1)) if iters else 0
        why.append(f"irq_kernel={kernel}/{want}")
        if kernel < want:
            why.append("window-not-fired")
    green = (not died and pf is None and rc != 124 and exitrow
             and (window or (done and rc == 0))
             and (not window or (irq is not None and iters is not None
                                 and int(irq.group(2)) >= int(iters.group(1)))))
    return green, ",".join(why) or "ok"


def run_case(rep: Report, case: str, boots: int) -> None:
    expect_green, window, edits, case_boots = CASES[case]
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
        for i in range(1, boots + 1):
            run_rc, text = m45.boot(f"amb-{case}-{i}", rom)
            green, why = boot_verdict(text, run_rc, window)
            greens += green
            reds += not green
            print(f"[INFO] {case} boot {i}: {'green' if green else 'RED'} "
                  f"({why}, async={text.count('K2 async user')})", flush=True)
        if expect_green:
            rep.check(f"{case}: {boots} 次启动全绿", greens == boots,
                      boots, greens)
        else:
            rep.check(f"{case}: 保护缺失 ⇒ 至少一次红", reds >= 1, ">=1", reds)
    finally:
        for path, (blob, before) in backups.items():
            # Real criterion: the bytes as they are *now* (after this case's
            # injections) differ, the pre-injection snapshot is written back,
            # and the file's md5 then equals the snapshot again.  (The earlier
            # form passed a literal `True` as the verdict, so it could not
            # fail — m18-linux-024 round 3 review.)
            injected = md5(path)
            path.write_bytes(blob)
            restored = md5(path)
            ok = restored == before
            rep.check(f"{case}: 还原 {path.name}（cp + md5）", ok, before,
                      f"{restored} (注入后 {injected})")


def soak(rep: Report, count: int, jobs: int) -> None:
    """Boot the unmodified (baseline) image `count` times, `jobs` at a time.

    The natural window is rare (~1/475 boots), so the no-regression claim is
    "the same image, many boots, no die and no stall" — judged per boot, with
    no retry.
    """
    from concurrent.futures import ThreadPoolExecutor

    rom = m45.firmware()
    rc, snap = m45.build_image("amb:soak")
    rep.check("soak: 镜像可构建", rc == 0 and snap is not None, 0, rc)
    if snap is None:
        return

    def one(i: int) -> tuple[int, bool, str]:
        run_rc, text = m45.boot(f"soak-{i}", rom)
        green, why = boot_verdict(text, run_rc, False)
        return i, green, why

    reds = 0
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        for i, green, why in pool.map(one, range(1, count + 1)):
            if not green:
                reds += 1
                print(f"[FAIL] soak boot {i}: RED ({why})", flush=True)
            elif i % 250 == 0:
                print(f"[INFO] soak {i}/{count} boots, 0 red", flush=True)
    rep.check(f"soak: {count} 次启动 0 红（{jobs} 并发）", reds == 0, 0, reds)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case", action="append", default=[], choices=sorted(CASES))
    ap.add_argument("--boots", type=int, default=0,
                    help="boots per case (default: the case's own count)")
    ap.add_argument("--soak", type=int, default=0,
                    help="boot the baseline image N times (no case injection)")
    ap.add_argument("--jobs", type=int, default=12,
                    help="parallel boots for --soak (default 12)")
    ap.add_argument("--list", action="store_true", help="list the cases")
    args = ap.parse_args()
    if args.list:
        for name, (green, _win, _edits, boots) in CASES.items():
            print(f"{name:20s} expect={'green' if green else 'RED'} boots={boots}")
        return 0

    rep = Report()
    # Snapshot the one symbol this probe's build slices change in the *shared*
    # build tree, so the next command does not inherit an empty rootfs.
    saved_initramfs = shared_initramfs_line()
    try:
        if args.soak:
            print(f"\n=== soak: {args.soak} boots, {args.jobs} in parallel ===",
                  flush=True)
            soak(rep, args.soak, args.jobs)
        cases = args.case or ([] if args.soak else sorted(CASES))
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
