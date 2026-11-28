#!/usr/bin/env python3
"""m18_async_ret_probe.py — `cg15 rc2` on a `ret` boundary matches spec §5.4.

`ISS-m18-011` hypothesised that QEMU's asynchronous precise point
(`cfx_hart cg15 rc2`, "the committed instruction's successor; a jump's target",
`spec/DADAO-12 §5.4` / §5 "精确异常") might disagree with the kernel at a
`ret`.  This probe measures that directly on the machine the kernel runs on: a
static musl program spends its whole life in a direct `call`/`ret` pair, so the
timer tick samples the boundary round after round, and the kernel prints the
captured `cg15 rc2` as `K2 async user: frame_ip=…` for every entry.

Judged facts (each has a reachable FAIL):

  * `leaf` really contains a `ret` (a function the compiler inlined or turned
    into a tail `jump` would make the measurement vacuous);
  * at least one captured `frame_ip` is a `call`+4 return site — the sampler
    did observe the instruction after a committed `ret`;
  * **no** captured `frame_ip` is `leaf`'s `ret` address or `ret`+4: spec
    §5.4 says the return point is the *committed successor* (the call site),
    never the `ret` itself or its fall-through;
  * the program finished (`RET end`, rc == 0).

Exit status: 0 = built and every check passed; 1 = a check failed; 2 = setup.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tests.unit.linux import m18_async_return_probe as base  # noqa: E402
from tools.linux import config_pins as pins                      # noqa: E402
from tools.linux import paths as linux_paths                    # noqa: E402

TARGET = "dadao-unknown-elf"
JOBS = os.environ.get("JOBS", "32")
TIMEOUT_QEMU = int(os.environ.get("M18R_QEMU_TIMEOUT", "40"))
N = int(os.environ.get("M18R_N", "20000000"))

CONFIG_PINS = {
    "CONFIG_DADAO_K1_EARLY_STOP": "n",
    "CONFIG_DADAO_K2_EARLY_STOP": "n",
    "CONFIG_DADAO_K2_TIME_STOP": "n",
    "CONFIG_DADAO_K2_TIME_CASE": "n",
    "CONFIG_DADAO_K2_IRQ_TEST": "n",
    "CONFIG_DADAO_K2_TRAP_SELFTEST": "n",
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

RET_C = r"""
#include <stdio.h>
#include <stdint.h>

static volatile unsigned long sink;

__attribute__((noinline)) static unsigned long leaf(unsigned long x)
{
    sink = x;              /* side effect: no inline, no tail call */
    return x + 1;
}

int main(void)
{
    unsigned long acc = 0, i;

    setvbuf(stdout, 0, _IONBF, 0);
    printf("RET begin n=%lu\n", (unsigned long)@N@UL);
    for (i = 0; i < @N@UL; i++)
        acc = leaf(acc);   /* call site + ret boundary, sampled by the tick */
    printf("RET end acc=%lu\n", acc);
    return 0;
}
""".replace("@N@", str(N))


class SetupError(base.SetupError):
    pass


def image_root() -> Path:
    return linux_paths.linux_build_dir().parent / "async-ret-image"


def build_root() -> Path:
    return image_root() / "build"


def image_dir() -> Path:
    return image_root() / "image"


def image_cpio() -> Path:
    return image_dir() / "initramfs.cpio"


def build_program() -> Path:
    musl = base.musl_dir()
    build_root().mkdir(parents=True, exist_ok=True)
    src = build_root() / "ret_init.c"
    obj = build_root() / "ret_init.o"
    elf = build_root() / "ret_init"
    src.write_text(RET_C)
    base.run([base.tool("clang"), f"--target={TARGET}", "-O1", "-nostdinc",
              "-ffile-prefix-map=" + str(_REPO) + "=.",
              *base.include_flags(musl), "-c", str(src), "-o", str(obj)], cwd=_REPO)
    base.run([base.tool("ld.lld"), musl / "lib" / "crt1.o", obj,
              "--start-group", musl / "lib" / "libc.a", base.builtins_archive(),
              "--end-group", "-o", str(elf)], cwd=_REPO)
    elf.chmod(0o755)
    return elf


def disassemble(elf: Path) -> str:
    proc = subprocess.run([str(base.tool("llvm-objdump")), "-d", "--no-show-raw-insn",
                           str(elf)], capture_output=True, text=True)
    if proc.returncode != 0:
        raise SetupError(f"llvm-objdump failed (rc={proc.returncode}): {proc.stdout}")
    return proc.stdout


def boundaries(elf: Path) -> dict:
    """Return leaf's ret address, its +4, and every call+4 return site."""
    text = disassemble(elf)
    func = None
    leaf_ret = None
    ret_sites: set[int] = set()
    for line in text.splitlines():
        m = re.match(r"^([0-9a-f]+) <([^>]+)>:", line.strip())
        if m:
            func = m.group(2)
            continue
        m = re.match(r"^\s*([0-9a-f]+):\s+(\S+)(.*)$", line)
        if not m:
            continue
        addr = int(m.group(1), 16)
        mnem = m.group(2)
        if mnem.startswith("call"):
            ret_sites.add(addr + 4)
        if func == "leaf" and mnem.startswith("ret"):
            leaf_ret = addr
    return {"leaf_ret": leaf_ret, "ret_sites": ret_sites}


def build_image(elf: Path) -> dict:
    cpio = base.build_cpio(elf.read_bytes())
    image_dir().mkdir(parents=True, exist_ok=True)
    image_cpio().write_bytes(cpio)
    if not (linux_paths.linux_build_dir() / ".config").is_file():
        rc = subprocess.call([sys.executable,
                              str(_REPO / "tools" / "linux" / "make_defconfig.py"),
                              "--jobs", JOBS], cwd=str(_REPO))
        if rc != 0:
            raise SetupError(f"make_defconfig failed (rc={rc})")
    previous = base.current_initramfs_source()
    lines = list(pins.config_lines(CONFIG_PINS))
    lines += [base.K6_SHELL_LINE, f'CONFIG_INITRAMFS_SOURCE="{image_cpio()}"']
    if base.defconfig.apply_config_lines(lines) != 0:
        raise SetupError("applying the image config slice failed")
    try:
        build = subprocess.call(
            [sys.executable, str(_REPO / "tools" / "linux" / "make_vmlinux.py"),
             "--jobs", JOBS, "--skip-code-range"], cwd=str(_REPO))
    finally:
        restore = previous if previous else str(
            linux_paths.linux_initramfs_dir() / "initramfs.cpio")
        base.defconfig.apply_config_lines([f'CONFIG_INITRAMFS_SOURCE="{restore}"'])
    if build != 0:
        raise SetupError(f"kernel build failed (rc={build})")
    manifest = {"program": {"sha256": hashlib.sha256(elf.read_bytes()).hexdigest()}}
    (image_dir() / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def boot(tag: str, qemu: str) -> tuple[int, str]:
    vmlinux = linux_paths.linux_build_dir() / "vmlinux"
    if not vmlinux.is_file():
        raise SetupError(f"{vmlinux} missing")
    cmd = [qemu, "-machine", f"kaiwu-vast,bootrom-image={base.firmware()}",
           "-display", "none", "-serial", "none",
           "-chardev", "stdio,id=semi",
           "-semihosting-config", "enable=on,target=native,chardev=semi",
           "-kernel", str(vmlinux)]
    try:
        proc = subprocess.run(cmd, cwd=str(_REPO), stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, timeout=TIMEOUT_QEMU)
        rc = proc.returncode & 0xFF
        text = (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired as exc:
        rc = 124
        out = exc.stdout or ""
        if isinstance(out, bytes):
            out = out.decode(errors="replace")
        text = out
    log = image_root() / "log"
    log.mkdir(parents=True, exist_ok=True)
    (log / f"{tag}.log").write_text(text, encoding="utf-8")
    return rc, text


def samples(text: str) -> list[int]:
    return [int(m, 16) for m in re.findall(r"K2 async user: frame_ip=0x([0-9a-f]+)", text)]


def judge(elf: Path, rc: int, text: str) -> list[tuple[str, str, str, bool]]:
    b = boundaries(elf)
    ips = samples(text)
    ret = b["leaf_ret"]
    checks = []
    checks.append(("leaf has a ret instruction", "1", str(ret is not None),
                   ret is not None))
    checks.append(("captured async entries", ">=1", str(len(ips)), len(ips) >= 1))
    hit_ret_site = any(ip in b["ret_sites"] for ip in ips)
    checks.append(("sampled a call+4 return site (coverage)", ">=1",
                   str(sum(1 for ip in ips if ip in b["ret_sites"])), hit_ret_site))
    if ret is not None:
        bad = [ip for ip in ips if ip in (ret, ret + 4)]
        checks.append((f"no sample at ret({ret:#x})/ret+4", "0", str(len(bad)),
                       not bad))
    checks.append(("RET end", 1, text.count("RET end"), text.count("RET end") == 1))
    checks.append(("qemu rc", "0", str(rc), rc == 0))
    return checks


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--boots", type=int, default=1)
    ap.add_argument("--tag", default="ret")
    ap.add_argument("--qemu", default=None)
    ap.add_argument("--build-only", action="store_true")
    args = ap.parse_args()
    try:
        elf = build_root() / "ret_init"
        if not args.build_only:
            elf = build_program()
            build_image(elf)
        else:
            if not elf.is_file():
                raise SetupError(f"{elf} missing — run without --build-only first")
        qemu = args.qemu or base.default_qemu()
        print(f"[INFO] qemu={qemu} md5={hashlib.md5(Path(qemu).read_bytes()).hexdigest()}")
        failed = 0
        for i in range(args.boots):
            tag = f"{args.tag}-{i + 1}"
            rc, text = boot(tag, qemu)
            checks = judge(elf, rc, text)
            bad = 0
            for name, expected, actual, ok in checks:
                print(f"  [{'PASS' if ok else 'FAIL'}] {tag}: {name} | "
                      f"期望={expected} 实际={actual}")
                bad += 0 if ok else 1
            b = boundaries(elf)
            print(f"[INFO] {tag}: qemu rc={rc}; {len(checks) - bad}/{len(checks)} "
                  f"checks passed; leaf_ret={b['leaf_ret'] and hex(b['leaf_ret'])}; "
                  f"samples={len(samples(text))}; log {image_root() / 'log' / (tag + '.log')}")
            failed += bad
        if failed:
            print(f"m18_async_ret_probe: FAIL ({failed} check(s))")
            return 1
        print(f"m18_async_ret_probe: PASS ({args.boots}/{args.boots} boots)")
        return 0
    except base.SetupError as exc:
        print(f"m18_async_ret_probe: SETUP ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
