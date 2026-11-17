#!/usr/bin/env python3
"""make_initramfs.py — build the M14 K0 built-in initramfs (`make linux-initramfs`).

Deliverables (all under `paths.linux_initramfs_dir()`, a disposable runtime
directory; the *record* is the manifest, never a host path):

  init              static musl init ELF for `dadao-unknown-elf` (mode 0755)
  initramfs.cpio    `newc` archive: `.` (dir) + `init` (file 0755) + TRAILER
  manifest.json     sha256/size of both + the syscall number set (read by
                    `m14-infra-003`; paths inside are bare names relative to
                    the manifest's own directory)

Determinism (acceptance item 2/6): two consecutive runs in the same toolchain
must produce byte-identical outputs.  Enforced by construction —
`SOURCE_DATE_EPOCH=0`, `-ffile-prefix-map`, `--build-id=none`, cpio mtime 0,
uid/gid 0, nlink per entry type, lexicographically ordered data entries and
4-byte alignment throughout.  Nothing time-, host- or run-dependent is read
into the outputs.

Syscall numbers are **not** written into the C source: the manifest's
`syscall_numbers` is derived live from the locked kernel tree's
`scripts/syscall.tbl` (`paths.linux_source_dir()`), and cross-checked against
the musl-generated `<bits/syscall.h>` the compiler actually uses, so a drifted
carrier fails the build instead of silently diverging.

Usage:
  python3 tools/linux/make_initramfs.py
  python3 tools/linux/make_initramfs.py --inject mtime|mode   # evidence only

`--inject` deliberately breaks one determinism/attribute property so the
evidence script can prove its checks are live (it must make the checks FAIL).

Requires: `make install-host` (cross clang/ld.lld/llvm-readelf) and
`make build-musl` (lib/crt1.o + lib/libc.a).  Missing prerequisites are a hard
error (exit 2), never a silent downgrade.

Exit status: 0 = built and self-checked; 1 = check failed; 2 = setup error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from tools.linux import paths as linux_paths  # noqa: E402

# m14-testcases-006 移动后 `tests/linux/init` → `tests/shared/init`（m14-linux-016
# 顺带修正：这里仍是旧路径，K0 门控的 initramfs 增量构建因此报 rc=1）。
INIT_SOURCE = _REPO_ROOT / "tests" / "shared" / "init" / "init.c"
TARGET = "dadao-unknown-elf"

#: syscall names the MVP init is scoped to (`.tao/contracts/contract-syscall.md`
#: §1.1; value comes from the kernel table, never from this list).
SYSCALL_NAMES = ("write", "getpid", "brk", "exit_group")

#: libc entry points init.o may reference.  `___errno_location` is compiler
#: generated (the `errno` macro); `syscall`/`write`/`getpid`/`_Exit` are the
#: musl API calls the source makes.  Anything else means init grew a new
#: dependency (open/mmap/execve/stdio/malloc …) and must fail loudly.
ALLOWED_IMPORTS = {"_Exit", "___errno_location", "getpid", "syscall", "write"}

CPIO_MAGIC = b"070701"
CPIO_TRAILER = "TRAILER!!!"


class SetupError(RuntimeError):
    """Missing prerequisite / unusable input (exit 2)."""


class CheckError(RuntimeError):
    """A built artifact violates a required property (exit 1)."""


# ── toolchain helpers ───────────────────────────────────────────────────────

def _tool(name: str) -> Path:
    path = linux_paths.toolchain_bin() / name
    if not path.is_file():
        raise SetupError(f"{path} not found — run 'make install-host' first")
    return path


def _run(cmd: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    proc = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        raise CheckError(
            f"command failed (rc={proc.returncode}): {' '.join(str(c) for c in cmd)}\n"
            f"{proc.stdout}{proc.stderr}")
    return proc


def _musl_dir() -> Path:
    # work_root/source/musl — derived from the component lock, not a literal.
    musl = linux_paths.linux_source_dir().parent / "musl"
    for rel in ("lib/crt1.o", "lib/libc.a"):
        if not (musl / rel).is_file():
            raise SetupError(f"{musl / rel} not found — run 'make build-musl' first")
    return musl


def _musl_include_flags(musl: Path) -> list[str]:
    dirs = ("arch/dadao", "arch/generic", "obj/src/internal",
            "src/include", "src/internal", "obj/include", "include")
    return [f"-I{musl / d}" for d in dirs]


def _builtins_archive(clang: Path) -> Path:
    proc = _run([clang, f"--target={TARGET}", "-rtlib=compiler-rt",
                 "-print-libgcc-file-name"])
    path = Path(proc.stdout.strip())
    if not path.is_file():
        raise SetupError(f"target builtins archive not found at {path} — run 'make install-host'")
    return path


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ── syscall numbers (live from the locked kernel tree) ──────────────────────

_TBL_RE = re.compile(r"^(\d+)\s+\w+\s+(\w+)\b")


def kernel_syscall_numbers() -> dict[str, int]:
    tbl = linux_paths.linux_source_dir() / "scripts" / "syscall.tbl"
    if not tbl.is_file():
        raise SetupError(
            f"{tbl} not found — the locked kernel source tree is the number-table "
            f"source of truth (run 'make fetch' first)")
    numbers: dict[str, int] = {}
    for line in tbl.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = _TBL_RE.match(line)
        if not match:
            continue
        nr, name = int(match.group(1)), match.group(2)
        numbers.setdefault(name, nr)
    missing = [name for name in SYSCALL_NAMES if name not in numbers]
    if missing:
        raise CheckError(f"kernel scripts/syscall.tbl is missing {missing}")
    return {name: numbers[name] for name in SYSCALL_NAMES}


def musl_syscall_numbers(musl: Path) -> dict[str, int]:
    """Numbers from the musl-generated header the compiler actually sees."""
    header = musl / "obj" / "include" / "bits" / "syscall.h"
    if not header.is_file():
        raise SetupError(f"{header} not found — run 'make build-musl' first")
    text = header.read_text(encoding="utf-8", errors="replace")
    found: dict[str, int] = {}
    for name in SYSCALL_NAMES:
        match = re.search(rf"^#define\s+SYS_{name}\s+(\d+)\s*$", text, re.M)
        if not match:
            raise CheckError(f"SYS_{name} not defined in {header}")
        found[name] = int(match.group(1))
    return found


def cross_check_numbers(kernel: dict[str, int], musl: dict[str, int]) -> None:
    if kernel != musl:
        diff = {n: (kernel[n], musl[n]) for n in kernel if kernel[n] != musl[n]}
        raise CheckError(
            "syscall number disagreement between the locked kernel table and the "
            f"musl header (name: kernel/musl): {diff}")


# ── init build ──────────────────────────────────────────────────────────────

def build_init(outdir: Path) -> tuple[Path, Path]:
    clang = _tool("clang")
    ld_lld = _tool("ld.lld")
    musl = _musl_dir()
    outdir.mkdir(parents=True, exist_ok=True)
    obj = outdir / "init.o"
    elf = outdir / "init"

    env = dict(os.environ)
    env["SOURCE_DATE_EPOCH"] = "0"  # no build-time stamping
    _run([clang, f"--target={TARGET}", "-O2", "-nostdinc", "-fno-ident",
          f"-ffile-prefix-map={_REPO_ROOT}=.",
          *_musl_include_flags(musl), "-c", INIT_SOURCE, "-o", obj], env=env)

    _run([ld_lld, musl / "lib" / "crt1.o", obj,
          "--start-group", musl / "lib" / "libc.a", _builtins_archive(clang),
          "--end-group", "--build-id=none", "-o", elf])
    elf.chmod(0o755)
    return obj, elf


def check_imports(obj: Path) -> None:
    proc = _run([_tool("llvm-nm"), "-u", obj])
    imports = {line.split()[-1] for line in proc.stdout.splitlines() if line.strip()}
    extra = imports - ALLOWED_IMPORTS
    if extra:
        raise CheckError(
            f"init.o references unexpected libc entry point(s) {sorted(extra)}; "
            f"allowed = {sorted(ALLOWED_IMPORTS)}")
    missing = {name for name in ("write", "getpid", "syscall", "_Exit") if name not in imports}
    if missing:
        raise CheckError(f"init.o does not reference the expected musl API {sorted(missing)}")
    print(f"[PASS] init.o libc surface: {sorted(imports)} ⊆ {sorted(ALLOWED_IMPORTS)}")


def check_elf(elf: Path, syscalls: dict[str, int]) -> None:
    """ET_EXEC / EM_DADAO / no PT_INTERP / no dynamic section (acceptance 1)."""
    readelf = _tool("llvm-readelf")
    head = _run([readelf, "-h", elf]).stdout
    segs = _run([readelf, "-l", elf]).stdout
    dyn = _run([readelf, "-d", elf]).stdout

    def field(label: str) -> str:
        for line in head.splitlines():
            if label in line:
                return line.split(":", 1)[1].strip()
        raise CheckError(f"llvm-readelf -h: '{label}' not found")

    e_type, e_machine = field("Type:"), field("Machine:")
    if not e_type.startswith("EXEC"):
        raise CheckError(f"init is not ET_EXEC (Type: {e_type})")
    if e_machine != "da0":
        raise CheckError(f"init is not EM_DADAO (Machine: {e_machine})")
    if "INTERP" in segs:
        raise CheckError("init has a PT_INTERP segment (must be a static executable)")
    if "Dynamic section" in dyn or "NEEDED" in dyn:
        raise CheckError("init has a dynamic section / DT_NEEDED (must be statically linked)")
    print(f"[PASS] init ELF: Type={e_type} Machine={e_machine} "
          f"PT_INTERP=absent DYNAMIC=absent")
    print(f"[PASS] init syscall numbers (kernel scripts/syscall.tbl): "
          f"{{{', '.join(f'{k}={v}' for k, v in syscalls.items())}}}")


# ── cpio newc writer ────────────────────────────────────────────────────────

def _newc_entry(name: str, ino: int, mode: int, data: bytes, *,
                nlink: int, mtime: int = 0) -> bytes:
    encoded = name.encode() + b"\0"
    header = CPIO_MAGIC + b"".join(
        f"{value:08X}".encode() for value in (
            ino, mode, 0, 0, nlink, mtime, len(data), 0, 0, 0, 0, len(encoded), 0
        ))
    out = bytearray(header)
    out += encoded
    out += b"\0" * (-len(out) % 4)          # header+name pad to 4
    out += data
    out += b"\0" * (-len(data) % 4)         # data pad to 4
    return bytes(out)


def build_cpio(init_elf: bytes, *, inject: str | None = None) -> bytes:
    mode = 0o100755 if inject != "mode" else 0o100644
    # --inject mtime: a millisecond-resolution timestamp, so two consecutive
    # runs differ and the determinism check cannot pass by accident.
    mtime = 0 if inject != "mtime" else int(time.time() * 1000) & 0xFFFFFFFF
    entries = [
        _newc_entry(".", 1, 0o040755, b"", nlink=2, mtime=mtime),
        _newc_entry("init", 2, mode, init_elf, nlink=1, mtime=mtime),
        _newc_entry(CPIO_TRAILER, 0, 0, b"", nlink=1, mtime=mtime),
    ]
    return b"".join(entries)


# ── main ────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="build the M14 initramfs (newc)")
    parser.add_argument("--inject", choices=("mtime", "mode"),
                       help="evidence only: break determinism/mode on purpose")
    args = parser.parse_args()

    try:
        kernel = kernel_syscall_numbers()
        cross_check_numbers(kernel, musl_syscall_numbers(_musl_dir()))
        print(f"[PASS] syscall numbers agree: kernel syscall.tbl == musl bits/syscall.h")

        outdir = linux_paths.linux_initramfs_dir()
        obj, elf = build_init(outdir)
        check_imports(obj)
        elf_bytes = elf.read_bytes()
        check_elf(elf, kernel)

        cpio = build_cpio(elf_bytes, inject=args.inject)
        cpio_path = outdir / "initramfs.cpio"
        cpio_path.write_bytes(cpio)

        manifest = {
            "format": 1,
            "init": {"name": "init", "size": len(elf_bytes),
                     "sha256": _sha256(elf_bytes)},
            "cpio": {"name": "initramfs.cpio", "size": len(cpio),
                     "sha256": _sha256(cpio)},
            "syscall_numbers": kernel,
        }
        manifest_path = linux_paths.linux_initramfs_manifest()
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                                 encoding="utf-8")

        print(f"[INFO] init     : size={len(elf_bytes)} sha256={manifest['init']['sha256']}")
        print(f"[INFO] cpio     : size={len(cpio)} sha256={manifest['cpio']['sha256']}")
        print(f"[INFO] manifest : {manifest_path.name}")
        print("make_initramfs: PASS")
        return 0
    except SetupError as exc:
        print(f"make_initramfs: SETUP ERROR: {exc}", file=sys.stderr)
        return 2
    except CheckError as exc:
        print(f"make_initramfs: FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
