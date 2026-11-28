#!/usr/bin/env python3
"""m18_supv_exit_intent_probe.py — supv exit-intent rewrite (ISS-m18-014).

`m18-linux-029` showed that `cfx_umon cg5` is one shared frame: a task that
slept in the C half finds the four exit-intent words overwritten by the next
entry, and `escape cfx_umon` then returns to the wrong mode/IP.  The supv
return path (`DADAO_TRAP_RESTORE_AND_ESCAPE` -> `escape cfx_smon`) has the same
single frame, so `m18-linux-031` rewrites rc8/rc9/rc10/rc11 there too.

This probe is the deterministic oracle for that rewrite.  A K2 probe image
(`tests/unit/linux/m18_supv_exit_intent_probe_kernel.patch`, applied to the
runtime source tree only) adds P13: its report callback — i.e. code running in
the supv C half — writes the four words exactly as another task's supv entry
would (rc8=user, rc9=reserved cfx, rc10=a landing, rc11=0) and returns.  The
return path must replace all four from this task's frame and the live mask:

  * base                     -> P13 PASS, boot continues to the K2 final case;
  * revert the whole rewrite -> CFXESC die 0x82;
  * delete the rc8 write     -> escapes to user at a kernel ip (CFXPERM
                                landing, exit 0xed);
  * delete the rc9 write     -> CFXESC die 0x82;
  * delete the rc10 write    -> the boot's K1 PTW probe retries itself and
                                dies on the hit budget (0xf): the return
                                address is needed before K2 too;
  * delete the rc11 write    -> P13 FAIL mask (expected live, got 0), 0xef.

Every injection backs up the source file and restores it with ``cp`` + md5
(never ``git checkout``); the base image is rebuilt and re-run green after
each one.  ``--inject all`` does the five injections in order and also proves
the two rc9/whole-revert signatures are the same CFXESC segment only by the
console line, not by exit code alone.

Exit status: 0 = every requested run judged PASS; 1 = a run FAILED; 2 = setup.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.linux import config_pins                    # noqa: E402
from tools.linux import make_defconfig as defconfig   # noqa: E402
from tools.linux import paths as linux_paths          # noqa: E402
from tools.qemu import k0_boot_probe as k0            # noqa: E402

JOBS = os.environ.get("JOBS", "32")
TIMEOUT_BUILD = int(os.environ.get("M18SE_BUILD_TIMEOUT", "600"))
TIMEOUT_QEMU = int(os.environ.get("M18SE_QEMU_TIMEOUT", "120"))

PASS_LINE = "K2 probe P13: exit-intent PASS "
FAIL_LINE = "K2 probe P13: FAIL "
WRONG_IP_LINE = "K2 probe P13: WRONG-IP "
USER_LINE = "K2 probe P13: USER-MODE "

#: The complete DADAO symbol set for this image (the K2 probe image).
CONFIG_PINS = {
    "CONFIG_DADAO_K1_EARLY_STOP": "n",
    "CONFIG_DADAO_K2_EARLY_STOP": "y",
    "CONFIG_DADAO_K2_TIME_STOP": "n",
    "CONFIG_DADAO_K2_TIME_CASE": "n",
    "CONFIG_DADAO_K2_IRQ_TEST": "n",
    "CONFIG_DADAO_K2_TRAP_SELFTEST": "y",
    "CONFIG_DADAO_K2_SELFTEST_REENTRY": "n",
    "CONFIG_DADAO_K2_SELFTEST_CFXTRAP": "n",
    "CONFIG_DADAO_K2_SELFTEST_CFXESC": "n",
    "CONFIG_DADAO_K2_SELFTEST_UNKNOWN": "n",
    "CONFIG_DADAO_K4_STACK_SELFTEST": "0",
    "CONFIG_DADAO_K4_COW_SELFTEST": "0",
    "CONFIG_DADAO_K4_SELFTEST": "n",
    "CONFIG_DADAO_K4_SWITCH_SELFTEST": "n",
    "CONFIG_DADAO_K4_KTHREAD_SELFTEST": "n",
    "CONFIG_DADAO_K5_SYSCALL_SELFTEST": "n",
    "CONFIG_DADAO_K5_CLONE_SELFTEST": "n",
    "CONFIG_DADAO_K5_FUTEX_SELFTEST": "n",
    "CONFIG_DADAO_M45_ENTRY_SELFTEST": "n",
    "CONFIG_DADAO_K5_SIGNAL_SELFTEST": "n",
    "CONFIG_DADAO_K5_CLOCK_SELFTEST": "n",
    "CONFIG_DADAO_K5_PAGESZ_SELFTEST": "n",
}

PROBE_PATCH = Path(__file__).with_name("m18_supv_exit_intent_probe_kernel.patch")
SOURCE = Path(linux_paths.linux_source_dir())
TRAP_S = "arch/dadao/kernel/trap.S"
K2_C = "arch/dadao/kernel/k2_selftest.c"

#: The rewrite block in the delivered `trap.S` (rc10 is deliberately last).
RC8 = "\tset.rd\trd2, DADAO_MODE_SUPV\n\tcfx2rc\tcfx_smon, cg5, rc8, rd2\n"
RC9 = ("\trb2rd\trd2, rb33, 1\t\t\t/* the entry's prev cfx code */\n"
       "\tcfx2rc\tcfx_smon, cg5, rc9, rd2\n")
RC11 = "\tcfx2rd\tcfx_smon, cg15, rc3, rd2\n\tcfx2rc\tcfx_smon, cg5, rc11, rd2\n"
RC10 = ("\tld.o\trd2, [rb3, PT_IP]\t\t/* this task's resume address */\n"
        "\t.if \\skip\n\tadd.si\trd2, DADAO_INSN_BYTES\n\t.endif\n"
        "\tcfx2rc\tcfx_smon, cg5, rc10, rd2\n")
REVERT = ("\t.if \\skip\n\tld.o\trd2, [rb3, PT_IP]\n"
          "\tadd.si\trd2, DADAO_INSN_BYTES\n"
          "\tcfx2rc\tcfx_smon, cg5, rc10, rd2\n\t.endif\n")

INJECTIONS = {
    "revert": (None, "die mode=2 code=0x82", "CFXESC: no word is rewritten"),
    "no-rc8": (RC8, USER_LINE, "escaped to user (CFXPERM landing)"),
    "no-rc9": (RC9, "die mode=2 code=0x82", "CFXESC: reserved target cfx"),
    "no-rc10": (RC10, "die mode=2 code=0xf",
                "K1 PTW probe retries itself (hit budget)"),
    "no-rc11": (RC11, FAIL_LINE, "target row mask 0, not the live word"),
}


def md5(path: Path) -> str:
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def run(cmd: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                          timeout=timeout)


def build() -> int:
    rc = defconfig.apply_config_lines(config_pins.config_lines(CONFIG_PINS))
    if rc != 0:
        print(f"[FAIL] config slice rc={rc}", file=sys.stderr)
        return rc
    proc = run([sys.executable, str(_REPO / "tools/linux/make_vmlinux.py"),
                f"--jobs={JOBS}", "--skip-code-range"], _REPO, TIMEOUT_BUILD)
    if proc.returncode != 0:
        print((proc.stdout or "")[-2000:], file=sys.stderr)
        print((proc.stderr or "")[-2000:], file=sys.stderr)
    return proc.returncode


def boot(qemu: str, tag: str, scratch: Path) -> tuple[int, str]:
    k0.load_contract()
    k0.WORK = str(scratch / f"bootrom-{tag}")
    rom = k0.build_firmware(k0.WORK)
    kernel = Path(linux_paths.linux_build_dir()) / "vmlinux"
    rc, _blocks, err, _log = k0.run_qemu(qemu, rom, str(kernel), tag,
                                         dfilter="0x0+0x4",
                                         timeout=TIMEOUT_QEMU)
    return (124 if rc is None else rc), (err or "")


class Judge:
    def __init__(self) -> None:
        self.fails: list[str] = []

    def check(self, name: str, expected, actual) -> None:
        ok = expected == actual
        print(f"  [{'PASS' if ok else 'FAIL'}] {name} | 期望={expected} 实际={actual}",
              flush=True)
        if not ok:
            self.fails.append(name)


def judge_base(rc: int, text: str, j: Judge) -> None:
    j.check("base: P13 PASS line", 1, text.count(PASS_LINE))
    j.check("base: no P13 failure line", 0, text.count(FAIL_LINE)
            + text.count(WRONG_IP_LINE) + text.count(USER_LINE))
    j.check("base: K2 final case still reached", 1,
            text.count("K2 probe P3: unregistered page fault"))
    j.check("base: usual K2 terminal (PTWMEM die 0xe4)", 1,
            text.count("die mode=2 code=0xe4"))


def judge_inject(kind: str, rc: int, text: str, j: Judge) -> None:
    needle = INJECTIONS[kind][1]
    j.check(f"{kind}: expected terminal signature", 1, text.count(needle))
    j.check(f"{kind}: P13 PASS line absent", 0, text.count(PASS_LINE))
    if kind in ("no-rc11",):
        j.check(f"{kind}: no wrong-ip/user landing", 0,
                text.count(WRONG_IP_LINE) + text.count(USER_LINE))


def inject_trap(src: Path, kind: str, scratch: Path) -> tuple[Path, str]:
    """Back up trap.S (cp), apply @kind's text change, return backup+md5."""
    path = src / TRAP_S
    backup = scratch / f"trap.S.{kind}.pre"
    shutil.copy2(path, backup)
    digest = md5(path)
    text = path.read_text()
    if kind == "revert":
        # Replace the whole rewrite block with the pre-031 rc10-only tail.
        start = text.index(RC8)
        end = text.index(RC10) + len(RC10)
        text = text[:start] + REVERT + text[end:]
    elif kind == "no-rc10":
        text = text.replace(RC10, "")
    else:
        frag = {"no-rc8": RC8, "no-rc9": RC9, "no-rc11": RC11}[kind]
        if text.count(frag) != 1:
            raise SystemExit(f"inject: {kind} fragment not unique ({text.count(frag)})")
        text = text.replace(frag, "")
    path.write_text(text)
    return backup, digest


def restore(path: Path, backup: Path, digest: str) -> None:
    shutil.copy2(backup, path)
    # `copy2` keeps the backup's old mtime; the kernel build is timestamp
    # driven, so without this the object built from the injected source would
    # be reused and the "restored" run would silently test the injection.
    os.utime(path, None)
    got = md5(path)
    if got != digest:
        raise SystemExit(f"restore: md5 mismatch for {path}: {got} != {digest}")
    print(f"  [PASS] restore {path.name} md5={got}", flush=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--qemu", default=os.environ.get("M18SE_QEMU", k0.DEFAULT_QEMU))
    ap.add_argument("--inject", choices=["none", "all", *INJECTIONS], default="none")
    ap.add_argument("--tag", default="")
    args = ap.parse_args(argv)

    if not (SOURCE / TRAP_S).is_file():
        print(f"m18_supv_exit_intent_probe: SETUP: {SOURCE / TRAP_S} missing; "
              f"run `make fetch` + `apply_series.py --component linux`", file=sys.stderr)
        return 2
    if not PROBE_PATCH.is_file():
        print(f"m18_supv_exit_intent_probe: SETUP: {PROBE_PATCH} missing", file=sys.stderr)
        return 2

    qemu = str(Path(args.qemu).resolve())
    if not Path(qemu).is_file():
        print(f"m18_supv_exit_intent_probe: SETUP: qemu {qemu} missing", file=sys.stderr)
        return 2
    print(f"[STAT] qemu={qemu} md5={md5(Path(qemu))}", flush=True)
    print(f"[STAT] source={SOURCE}", flush=True)

    scratch = Path(tempfile.mkdtemp(prefix="m18se-"))
    k2c = SOURCE / K2_C
    k2c_backup = scratch / "k2_selftest.c.pre"
    shutil.copy2(k2c, k2c_backup)
    k2c_md5 = md5(k2c)
    trap_delivered = scratch / "trap.S.delivered"
    shutil.copy2(SOURCE / TRAP_S, trap_delivered)
    trap_md5 = md5(trap_delivered)

    j = Judge()
    try:
        # Apply the probe image (test-only; restored before returning).
        proc = run(["git", "apply", str(PROBE_PATCH)], SOURCE, 60)
        if proc.returncode != 0:
            print(proc.stderr, file=sys.stderr)
            return 2
        if md5(k2c) == k2c_md5:
            print("[FAIL] probe patch did not change K2 source", file=sys.stderr)
            return 2

        if args.inject == "none":
            j.check("base: build rc", 0, build())
            rc, text = boot(qemu, (args.tag or "base").replace("/", "_"), scratch)
            judge_base(rc, text, j)
        else:
            kinds = list(INJECTIONS) if args.inject == "all" else [args.inject]
            for kind in kinds:
                # Start each injection from the clean delivered source.
                if md5(SOURCE / TRAP_S) != trap_md5:
                    shutil.copy2(trap_delivered, SOURCE / TRAP_S)
                    os.utime(SOURCE / TRAP_S, None)
                backup, digest = inject_trap(SOURCE, kind, scratch)
                j.check(f"{kind}: build rc", 0, build())
                rc, text = boot(qemu, f"{args.tag}-{kind}".strip("-"), scratch)
                judge_inject(kind, rc, text, j)
                restore(SOURCE / TRAP_S, backup, digest)
            # Green again on the restored source.
            j.check("after restores: build rc", 0, build())
            rc, text = boot(qemu, f"{args.tag}-restored".strip("-"), scratch)
            judge_base(rc, text, j)
    finally:
        # cp + md5 back to the delivered source (never git checkout).
        shutil.copy2(k2c_backup, k2c)
        os.utime(k2c, None)
        if md5(k2c) != k2c_md5:
            print("[FAIL] k2_selftest.c restore md5 mismatch", file=sys.stderr)
            j.fails.append("k2 restore")
        if md5(SOURCE / TRAP_S) != trap_md5:
            shutil.copy2(trap_delivered, SOURCE / TRAP_S)
            os.utime(SOURCE / TRAP_S, None)
        if md5(SOURCE / TRAP_S) != trap_md5:
            print("[FAIL] trap.S is not the delivered content", file=sys.stderr)
            j.fails.append("trap.S restore")

    if j.fails:
        print(f"\nm18_supv_exit_intent_probe: FAIL ({len(j.fails)}): "
              + "; ".join(j.fails), file=sys.stderr)
        return 1
    print("\nm18_supv_exit_intent_probe: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
