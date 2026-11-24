#!/usr/bin/env python3
"""musl_sigframe_probe.py — end-to-end signal frame on K5 (`m14-infra-005`).

The musl-side signal frame (arch/dadao/bits/signal.h, 2048 B / four 64-slot
寄存器组, `SA_RESTORER` + `__restore_rt`) is only real if a *musl-linked*
program can install a handler, be interrupted, run it, and come back through
`rt_sigreturn` on the real kernel.  This probe builds exactly that program
(tools/infra/musl_sigframe_probe_user.c) against the freshly built static musl,
puts it in an initramfs as `/init.musl`, boots the K5 kernel on Kaiwu-Vast and
judges what the program prints.  The image enables
CONFIG_DADAO_K5_SYSCALL_SELFTEST, whose U7 half execs `/init.musl` on the real
dispatcher (its shim only routes write()/exit_group() to the console).

Facts judged (each from a `SIGFRAME <key>=<value>` line; a missing line FAILs):

  * the saved register file the handler is handed: `rd[32]`/`rb[32]`/`rf[32]`
    sentinels, `status` = DADAO_STATUS_USER (1), a live `ra[0]` ({RACNT,
    MRPTR}), and `ip` exactly at the label 4 bytes past the `trap` that raised
    the signal;
  * the two restorer entries: `SA_SIGINFO` (→ __restore_rt) and a plain handler
    (→ __restore) both return and the main flow continues;
  * `sigaltstack` + `SA_ONSTACK`: the frame is built inside the alternate
    stack and the handler's own SP proves it;
  * the libc-side sigaltstack floor: musl's wrapper refuses `ss_size` 1024 and
    2375 with ENOMEM before the syscall, while 2376 (the frame size, i.e.
    musl's MINSIGSTKSZ) and 8192 are accepted;
  * header constants: uc_mcontext offset 168, `ip` at 512, MINSIGSTKSZ 2376,
    sigset_t 128 B, SA_RESTORER 0x04000000.

The user program is compiled and linked here (musl's own flags from
tools/linux/make_initramfs.py); the kernel is configured with
CONFIG_INITRAMFS_SOURCE pointing at the probe image and built through
tools/linux/make_vmlinux.py.

Exit status: 0 = every check held; 1 = at least one FAIL; 2 = an input could
not be derived (toolchain, musl build, kernel tree, QEMU, bootrom).
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.linux import make_defconfig as defconfig          # noqa: E402
from tools.linux import make_vmlinux as make_vmlinux         # noqa: E402
from tools.linux import paths as linux_paths                 # noqa: E402
from tools.qemu import k0_boot_probe as k0                   # noqa: E402

TARGET = "dadao-unknown-elf"
SCRATCH = Path(os.environ.get("SIGFRAME_TMP")
               or os.environ.get("DADAO_TMP")
               or "/tmp/opencode/m14-infra-005") / "sigframe-probe"
USER_C = _REPO / "tools" / "infra" / "musl_sigframe_probe_user.c"
TIMEOUT_BUILD = int(os.environ.get("SIGFRAME_BUILD_TIMEOUT", "2400"))
TIMEOUT_QEMU = int(os.environ.get("SIGFRAME_QEMU_TIMEOUT", "180"))
JOBS = os.environ.get("JOBS", "32")


class SetupError(RuntimeError):
    """An input is missing (exit 2)."""


def musl_dir() -> Path:
    return linux_paths.linux_source_dir().parent / "musl"


def tool(name: str) -> Path:
    path = linux_paths.toolchain_bin() / name
    if not path.is_file():
        raise SetupError(f"{path} not found — run 'make install-host'")
    return path


def run(cmd: list) -> subprocess.CompletedProcess:
    proc = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if proc.returncode != 0:
        raise SetupError(f"command failed ({proc.returncode}): "
                         f"{' '.join(str(c) for c in cmd)}\n"
                         f"{(proc.stdout or '')[-2000:]}\n{(proc.stderr or '')[-2000:]}")
    return proc


# ---------------------------------------------------------------------------
# user program + initramfs
# ---------------------------------------------------------------------------

def build_user(scratch: Path) -> Path:
    musl = musl_dir()
    if not (musl / "lib" / "libc.a").is_file():
        raise SetupError(f"{musl}/lib/libc.a not found — run 'make build-musl'")
    scratch.mkdir(parents=True, exist_ok=True)
    obj = scratch / "init-sigframe.o"
    elf = scratch / "init-sigframe.elf"
    include_dirs = ("arch/dadao", "arch/generic", "obj/src/internal",
                    "src/include", "src/internal", "obj/include", "include")
    run([tool("clang"), f"--target={TARGET}", "-O2", "-nostdinc", "-fno-ident",
         *[f"-I{musl / d}" for d in include_dirs],
         "-c", USER_C, "-o", obj])
    builtins = run([tool("clang"), f"--target={TARGET}", "-rtlib=compiler-rt",
                    "-print-libgcc-file-name"]).stdout.strip()
    run([tool("ld.lld"), musl / "lib" / "crt1.o", obj, "--start-group",
         musl / "lib" / "libc.a", builtins, "--end-group",
         "--build-id=none", "-o", elf])
    return elf


CPIO_MAGIC = b"070701"
TRAILER = "TRAILER!!!"
MODE_DIR = 0o040755
MODE_FILE = 0o100755


def _entry(name: str, mode: int, body: bytes) -> bytes:
    ino = 1
    header = (CPIO_MAGIC
              + b"%08x" % ino
              + b"%08x" % mode
              + b"%08x" % 0          # uid
              + b"%08x" % 0          # gid
              + b"%08x" % (2 if mode == MODE_DIR else 1)  # nlink
              + b"%08x" % 0          # mtime
              + b"%08x" % len(body)
              + b"%08x" % 0          # devmajor
              + b"%08x" % 0          # devminor
              + b"%08x" % 0          # rdevmajor
              + b"%08x" % 0          # rdevminor
              + b"%08x" % (len(name.encode()) + 1)
              + b"%08x" % 0)
    data = header + name.encode() + b"\0"
    data += b"\0" * (-len(data) % 4)
    data += body
    data += b"\0" * (-len(data) % 4)
    return data


def build_cpio(elf: Path) -> Path:
    body = _entry(".", MODE_DIR, b"")
    # The probe image reaches user mode through the K5 syscall selftest's
    # `kernel_execve("/init.musl")` (kernel/k5_syscall_selftest.c), so the
    # program ships under that name.
    body += _entry("init.musl", MODE_FILE, elf.read_bytes())
    body += _entry(TRAILER, 0, b"")
    target = SCRATCH / "initramfs.cpio"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)
    return target


# ---------------------------------------------------------------------------
# kernel
# ---------------------------------------------------------------------------

def configure(cpio: Path) -> None:
    config = Path(linux_paths.linux_build_dir()) / ".config"
    if not config.is_file():
        proc = subprocess.run([sys.executable,
                               str(_REPO / "tools" / "linux" / "make_defconfig.py")],
                              capture_output=True, text=True)
        if proc.returncode != 0:
            print((proc.stdout or "")[-2000:], file=sys.stderr)
            print((proc.stderr or "")[-2000:], file=sys.stderr)
            raise SetupError(f"make linux-defconfig rc={proc.returncode}")
    # CONFIG_DADAO_K5_SYSCALL_SELFTEST=y is what makes the boot continue past
    # the K4 boundary and enter user mode with the real dispatcher; its U7 half
    # execs /init.musl and its shim only routes write()/exit_group() to the
    # console, so the program below runs on the production syscall table.
    rc = defconfig.apply_config_lines([
        f'CONFIG_INITRAMFS_SOURCE="{cpio}"',
        "CONFIG_DADAO_K5_SYSCALL_SELFTEST=y",
    ])
    if rc != 0:
        raise SetupError(f"kernel config slice rc={rc}")


def build_kernel() -> Path:
    cmd = [sys.executable, str(_REPO / "tools" / "linux" / "make_vmlinux.py"),
           f"--jobs={JOBS}", "--skip-code-range"]
    proc = subprocess.run(cmd, cwd=str(_REPO), capture_output=True, text=True,
                          timeout=TIMEOUT_BUILD)
    if proc.returncode != 0:
        print((proc.stdout or "")[-4000:], file=sys.stderr)
        print((proc.stderr or "")[-4000:], file=sys.stderr)
        raise SetupError(f"make_vmlinux rc={proc.returncode}")
    return Path(linux_paths.linux_build_dir()) / "vmlinux"


def boot(kernel: Path) -> tuple[int, str]:
    k0.load_contract()
    SCRATCH.mkdir(parents=True, exist_ok=True)
    rom = k0.build_firmware(str(SCRATCH / "bootrom"), name="bootrom_sigframe.bin")
    qemu = str(linux_paths.toolchain_bin() / "qemu-system-dadao")
    if not os.access(qemu, os.X_OK):
        raise SetupError("qemu-system-dadao missing (make install-host)")
    cmd = [qemu, "-machine", f"kaiwu-vast,bootrom-image={rom}", "-nographic",
           "-semihosting-config", "enable=on,target=native", "-kernel", str(kernel)]
    proc = subprocess.Popen(cmd, cwd=str(_REPO), stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)
    try:
        out, err = proc.communicate(timeout=TIMEOUT_QEMU)
        rc = proc.returncode & 0xFF
    except subprocess.TimeoutExpired:
        proc.kill()
        out, err = proc.communicate()
        rc = 124
    text = (err or "") + (out or "")
    (SCRATCH / "console.log").write_text(text, encoding="utf-8")
    return rc, text


# ---------------------------------------------------------------------------
# judging
# ---------------------------------------------------------------------------

class Report:
    def __init__(self) -> None:
        self.total = 0
        self.failed: list[str] = []

    def check(self, name: str, expected, actual) -> None:
        self.total += 1
        ok = expected == actual
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: want={expected!r} got={actual!r}")
        if not ok:
            self.failed.append(name)


def facts(text: str) -> dict[str, str]:
    """Every `SIGFRAME <key>=<value>` line, value as text (hex kept as text)."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        m = re.match(r"SIGFRAME ([\w.\-]+)=(\S+)$", line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def judge(rep: Report, text: str, rc: int) -> None:
    f = facts(text)

    def num(key: str):
        value = f.get(key)
        if value is None:
            return None
        if value.startswith("0x"):
            return int(value, 16)
        if value.lstrip("-").isdigit():
            return int(value)
        return value

    def want(key: str, expected) -> None:
        rep.check(key, expected, num(key))

    # Header geometry: the kernel uapi's numbers, read back from the program.
    want("minsigstksz", 2376)
    want("sigstksz", 8192)
    want("sigmask-off", 40)
    want("sigmask-size", 128)
    want("mc-off", 168)
    want("ip-off", 168 + 512)
    want("rd-off", 168)
    want("ra-off", 168 + 1024)
    want("rf-off", 168 + 1536)
    # mcontext_t is the 2048-byte register file; sigcontext adds the uapi's
    # four reserved words, so the kernel frame is 32 B larger than ours.
    want("frame-size", 168 + 2048)
    want("sa-restorer-flag", 0x04000000)

    # Round 1: the frame image the handler was handed.
    want("handler.rd32", 0x1234)
    want("handler.rb32", 0x5678)
    want("handler.rf32", 0x9abc)
    want("handler.status", 1)          # DADAO_STATUS_USER
    rep.check("handler.ra0-live", True, (num("handler.ra0") or 0) != 0)
    rep.check("handler.ip-present", True, num("handler.ip") is not None)
    rep.check("handler.ip==resume-label", num("resume-label"), num("handler.ip"))
    want("after-handler", "ran")
    want("plain", "ran")
    want("after-plain", "ran")

    # Round 3: alternate stack.
    want("altstack.install", 0)
    want("altstack.insideness", 1)
    rep.check("altstack.sp-present", True, num("altstack.sp") is not None)
    rep.check("handler-sp-in-altstack", True,
              (num("altstack.base") or 0) <= (num("altstack.sp") or 0)
              < (num("altstack.end") or 0))
    rep.check("uc_stack-is-altstack", num("altstack.base"),
              num("handler.altbase"))
    want("after-altstack", 1)

    # Round 4: the libc-side sigaltstack floor.  musl's wrapper rejects
    # ss_size < MINSIGSTKSZ (2376 = the frame size) with ENOMEM in user space,
    # and hands at/above it to the kernel.
    def want_signed(key: str, expected: int) -> None:
        value = num(key)
        if isinstance(value, int) and value >= 1 << 63:
            value -= 1 << 64
        rep.check(key, expected, value)

    want_signed("sigaltstack.1024.rc", -1)
    want("sigaltstack.1024.errno", 12)          # ENOMEM
    want_signed("sigaltstack.2375.rc", -1)
    want("sigaltstack.2375.errno", 12)
    want("sigaltstack.2376.rc", 0)
    want("sigaltstack.8192.rc", 0)
    want("after-bounds", "ran")


    want("done", 1)
    rep.check("boot-exit-status", 0, rc)


def main() -> int:
    try:
        try:
            elf = build_user(SCRATCH)
            cpio = build_cpio(elf)
            configure(cpio)
            kernel = build_kernel()
            rc, text = boot(kernel)
        except subprocess.TimeoutExpired:
            print("musl_sigframe_probe: kernel build timed out (124 is a FAIL)",
                  file=sys.stderr)
            return 1
    except SetupError as exc:
        print(f"musl_sigframe_probe: SETUP ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"[INFO] console: {SCRATCH / 'console.log'}")
    rep = Report()
    judge(rep, text, rc)
    print(f"musl_sigframe_probe: {rep.total - len(rep.failed)}/{rep.total} passed, "
          f"{len(rep.failed)} FAIL")
    return 0 if not rep.failed else 1


if __name__ == "__main__":
    sys.exit(main())
