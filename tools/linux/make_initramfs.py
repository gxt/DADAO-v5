#!/usr/bin/env python3
"""make_initramfs.py — build the M14 K0 built-in initramfs (`make linux-initramfs`).

Deliverables (all under `paths.linux_initramfs_dir()`, a disposable runtime
directory; the *record* is the manifest, never a host path):

  init              `/init` shell script (mode 0755) that hands PID 1 to
                    busybox's `sh` applet (K6; m14-linux-031)
  init.musl         the K0 self-written static musl init ELF (mode 0755); it
                    stays in the image (not as `/init`) so the K0/K1-K4
                    user-program evidence keeps a shipped artefact
  initramfs.cpio    `newc` archive, entries in the order below
  manifest.json     per-entry sha256/size + the syscall number set (read by
                    `m14-infra-003`; paths inside are bare names relative to
                    the manifest's own directory)

Image layout (`.tao/tasks/linux/m14-linux-031`; lexicographic entry order):

  .  bin/  bin/busybox  bin/{cat,cp,echo,grep,kill,ls,mkdir,mv,ps,rm,sh}
  dev/  dev/console (c 240 0, the semihosting console)
  init  init.musl  TRAILER!!!

`/init` is a **script**, not a symlink to busybox: applet dispatch is by
`argv[0]`'s basename and `init` is not in the minimal applet set
(`components/busybox/config.min` keeps `CONFIG_INIT` off), so a symlink
`init -> bin/busybox` would die with `init: applet not found` (exit 127).
`binfmt_script` is on in the K0 defconfig (`CONFIG_BINFMT_SCRIPT=y`), and the
script ends in `exec /bin/sh`, so the shell is entered with its own name.

Determinism (acceptance item 2/6): two consecutive runs in the same toolchain
must produce byte-identical outputs.  Enforced by construction —
`SOURCE_DATE_EPOCH=0`, `-ffile-prefix-map`, `--build-id=none`, cpio mtime 0,
uid/gid 0, nlink per entry type, lexicographically ordered entries and
4-byte alignment throughout.  Nothing time-, host- or run-dependent is read
into the outputs.

Syscall numbers are **not** written into the C source: the manifest's
`syscall_numbers` is derived live from the locked kernel tree's
`scripts/syscall.tbl` (`paths.linux_source_dir()`), and cross-checked against
the musl-generated `<bits/syscall.h>` the compiler actually uses, so a drifted
carrier fails the build instead of silently diverging.

Usage:
  python3 tools/linux/make_initramfs.py
  python3 tools/linux/make_initramfs.py --inject mtime|mode|applet   # evidence

`--inject` deliberately breaks one determinism/attribute property so the
evidence script can prove its checks are live: the built archive is re-parsed
and verified by `verify_archive()` before this script reports PASS, so an
injected defect turns the *build itself* red (exit 1).

Requires: `make install-host` (cross clang/ld.lld/llvm-readelf),
`make build-musl` (lib/crt1.o + lib/libc.a) and `make build-busybox`
(`applets.txt` + the static busybox ELF).  Missing prerequisites are a hard
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
from typing import NamedTuple

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

#: applet links the K6 image ships next to `/bin/busybox` (task book
#: `m14-linux-031` §目标 1).  Each one is a relative symlink `-> busybox`;
#: their presence in the built busybox is re-checked against `applets.txt`
#: (the build product of `tools/linux/build_busybox.py`) so a shrunken
#: `config.min` fails here instead of shipping a dangling link.
APPLETS = ("cat", "cp", "echo", "grep", "kill", "ls", "mkdir", "mv", "ps",
           "rm", "sh")
BUSYBOX_LINK = "busybox"

#: `/dev/console` (K6, m18-linux-001): the semihosting console char device
#: registered by `arch/dadao/kernel/semihost_tty.c` at major 240, minor 0.
CONSOLE_DEVICE = ("dev/console", 240, 0)

#: `/init` payload: a script, not a symlink (see the module docstring).
INIT_SCRIPT = (
    b"#!/bin/sh\n"
    b"# DADAO initramfs /init (m14-linux-031; K6 console m18-linux-001): the\n"
    b"# kernel execs this file via binfmt_script; hand PID 1 to busybox's `sh`.\n"
    b"export PATH=/bin\n"
    b"PS1='dadao# '\n"
    b"export PS1\n"
    b"echo \"DADAO initramfs: /init -> busybox sh\"\n"
    b"exec /bin/sh\n"
)

#: the K0 self-written init ELF keeps its own name in the image.
MUSL_INIT_NAME = "init.musl"

CPIO_MAGIC = b"070701"
CPIO_TRAILER = "TRAILER!!!"

#: mode bits per cpio entry kind (S_IFDIR | 0755, S_IFREG | 0755, S_IFLNK | 0777,
#: S_IFCHR | 0600)
MODE_DIR = 0o040755
MODE_FILE = 0o100755
MODE_SYMLINK = 0o120777
MODE_CHARDEV = 0o020600


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


# ── busybox build product (owned by tools/linux/build_busybox.py) ───────────

def _busybox_build_dir() -> Path:
    """`work_root/build/busybox` — the layout `build_busybox.py` writes.

    Derived from the component lock through `paths.py` (same `work_root`), never
    from a literal host path; the two products this task consumes are
    `busybox` (the static ELF) and `applets.txt` (one applet name per line).
    """
    return linux_paths.linux_build_dir().parent / "busybox"


def busybox_product() -> Path:
    product = _busybox_build_dir() / "busybox"
    if not product.is_file():
        raise SetupError(f"{product} not found — run 'make build-busybox' first")
    return product


def busybox_applets() -> set[str]:
    """Applet names the built busybox carries (drift guard for the links)."""
    listing = _busybox_build_dir() / "applets.txt"
    if not listing.is_file():
        raise SetupError(f"{listing} not found — run 'make build-busybox' first")
    names = {line.strip() for line in listing.read_text(encoding="utf-8").splitlines()
             if line.strip()}
    missing = [applet for applet in APPLETS if applet not in names]
    if missing:
        raise CheckError(
            f"built busybox is missing required applet(s) {missing} "
            f"(has: {' '.join(sorted(names))}) — add them to "
            f"components/busybox/config.min and rebuild with 'make build-busybox'")
    return names


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
    # `init` itself is the `/init` script now (m14-linux-031); the K0 ELF keeps
    # its own name in the image so nothing that referenced it goes dangling.
    elf = outdir / MUSL_INIT_NAME

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
    print(f"[PASS] {MUSL_INIT_NAME} ELF: Type={e_type} Machine={e_machine} "
          f"PT_INTERP=absent DYNAMIC=absent")
    print(f"[PASS] init syscall numbers (kernel scripts/syscall.tbl): "
          f"{{{', '.join(f'{k}={v}' for k, v in syscalls.items())}}}")


# ── cpio newc writer ────────────────────────────────────────────────────────

class Entry(NamedTuple):
    """One archive entry; `data` is the file body or the symlink target."""

    name: str
    mode: int
    kind: str                    # "dir" | "file" | "symlink" | "chardev"
    data: bytes
    rdevmajor: int = 0
    rdevminor: int = 0


def image_entries(init_elf: bytes, *, inject: str | None = None) -> list[Entry]:
    """The image contents, in the archive's (lexicographic) order.

    `--inject applet` drops the `bin/sh` link the `/init` script execs, so the
    verification below has a reachable FAIL (evidence only).
    """
    console_name, console_major, console_minor = CONSOLE_DEVICE
    items: list[Entry] = [
        Entry(".", MODE_DIR, "dir", b""),
        Entry("bin", MODE_DIR, "dir", b""),
        Entry("bin/busybox", MODE_FILE, "file", busybox_product().read_bytes()),
        Entry("dev", MODE_DIR, "dir", b""),
        Entry(console_name, MODE_CHARDEV, "chardev", b"",
              console_major, console_minor),
        Entry("init", MODE_FILE, "file", INIT_SCRIPT),
        Entry(MUSL_INIT_NAME, MODE_FILE, "file", init_elf),
    ]
    for applet in APPLETS:
        if inject == "applet" and applet == "sh":
            continue
        items.append(Entry(f"bin/{applet}", MODE_SYMLINK, "symlink",
                           BUSYBOX_LINK.encode()))
    if inject == "mode":
        items = [Entry(e.name, 0o100644, e.kind, e.data)
                 if e.name == "init" else e for e in items]
    return sorted(items, key=lambda entry: entry.name)


def _dir_nlink(entries: list[Entry], name: str) -> int:
    """cpio: a directory's link count is 2 + its immediate subdirectories."""
    prefix = "" if name == "." else name + "/"
    subdirs = sum(
        1 for entry in entries
        if entry.mode == MODE_DIR and entry.name != "."
        and entry.name.startswith(prefix) and "/" not in entry.name[len(prefix):])
    return 2 + subdirs


def _newc_entry(name: str, ino: int, mode: int, data: bytes, *,
                nlink: int, mtime: int = 0, rdevmajor: int = 0,
                rdevminor: int = 0) -> bytes:
    encoded = name.encode() + b"\0"
    header = CPIO_MAGIC + b"".join(
        f"{value:08X}".encode() for value in (
            ino, mode, 0, 0, nlink, mtime, len(data), 0, 0,
            rdevmajor, rdevminor, len(encoded), 0
        ))
    out = bytearray(header)
    out += encoded
    out += b"\0" * (-len(out) % 4)          # header+name pad to 4
    out += data
    out += b"\0" * (-len(data) % 4)         # data pad to 4
    return bytes(out)


def build_cpio(init_elf: bytes, *, inject: str | None = None) -> bytes:
    # --inject mtime: a millisecond-resolution timestamp, so two consecutive
    # runs differ and the determinism check cannot pass by accident.
    mtime = 0 if inject != "mtime" else int(time.time() * 1000) & 0xFFFFFFFF
    entries = image_entries(init_elf, inject=inject)
    encoded = [
        _newc_entry(entry.name, index + 1, entry.mode, entry.data,
                    nlink=(_dir_nlink(entries, entry.name)
                           if entry.kind == "dir" else 1),
                    mtime=mtime, rdevmajor=entry.rdevmajor,
                    rdevminor=entry.rdevminor)
        for index, entry in enumerate(entries)
    ]
    encoded.append(_newc_entry(CPIO_TRAILER, 0, 0, b"", nlink=1, mtime=mtime))
    return b"".join(encoded)


# ── archive reader (verifies the bytes actually written, not the intent) ─────

def parse_newc(data: bytes) -> list[dict]:
    """Parse a `newc` archive into plain dicts (`body` = payload bytes)."""
    parsed: list[dict] = []
    offset = 0
    while True:
        if offset + 110 > len(data):
            raise CheckError(f"newc 在偏移 {offset} 处截断（不足一个 header）")
        header = data[offset:offset + 110]
        if header[:6] != CPIO_MAGIC:
            raise CheckError(f"偏移 {offset} 处不是 newc magic：{header[:6]!r}")
        try:
            fields = [int(header[6 + i * 8:14 + i * 8], 16) for i in range(13)]
        except ValueError as exc:
            raise CheckError(f"newc header 字段非十六进制：{exc}") from exc
        _ino, mode, uid, gid, nlink, mtime, size = fields[:7]
        rdevmajor, rdevminor = fields[9], fields[10]
        namesize, _check = fields[11], fields[12]
        name_start = offset + 110
        name = data[name_start:name_start + namesize - 1].decode("utf-8", "replace")
        body_start = name_start + namesize
        body_start += -body_start % 4
        body = data[body_start:body_start + size]
        if len(body) != size:
            raise CheckError(f"条目 {name!r} 的载荷被截断（{len(body)} != {size}）")
        parsed.append({"name": name, "mode": mode, "uid": uid, "gid": gid,
                       "nlink": nlink, "mtime": mtime, "body": body,
                       "rdevmajor": rdevmajor, "rdevminor": rdevminor})
        offset = body_start + size + (-(body_start + size) % 4)
        if name == CPIO_TRAILER:
            return parsed


def verify_archive(data: bytes, init_elf: bytes, busybox: bytes) -> list[dict]:
    """Re-parse the produced archive and assert the K6 image contract.

    Every failure names the property, so `--inject` produces a real FAIL and
    a drifted image cannot be reported as PASS.
    """
    entries = parse_newc(data)
    names = [entry["name"] for entry in entries]
    if names[-1] != CPIO_TRAILER:
        raise CheckError(f"末条目不是 {CPIO_TRAILER!r}：{names[-1]!r}")
    if names[0] != ".":
        raise CheckError(f"首条目不是 '.'：{names[0]!r}")
    body_names = names[1:-1]
    if body_names != sorted(body_names):
        raise CheckError(f"条目未按字典序排列：{body_names}")

    for entry in entries:
        if (entry["mtime"], entry["uid"], entry["gid"]) != (0, 0, 0):
            raise CheckError(
                f"条目 {entry['name']!r} 不确定：mtime={entry['mtime']} "
                f"uid={entry['uid']} gid={entry['gid']}")

    expected = {".": MODE_DIR, "bin": MODE_DIR, "bin/busybox": MODE_FILE,
                "dev": MODE_DIR, CONSOLE_DEVICE[0]: MODE_CHARDEV,
                "init": MODE_FILE, MUSL_INIT_NAME: MODE_FILE}
    expected.update({f"bin/{applet}": MODE_SYMLINK for applet in APPLETS})
    present = {entry["name"]: entry for entry in entries[:-1]}
    missing = sorted(set(expected) - set(present))
    if missing:
        raise CheckError(f"镜像缺条目 {missing}")
    extra = sorted(set(present) - set(expected))
    if extra:
        raise CheckError(f"镜像含未约定条目 {extra}")
    for name, mode in expected.items():
        if present[name]["mode"] != mode:
            raise CheckError(f"条目 {name!r} 的 mode 为 {present[name]['mode']:o}，"
                             f"应为 {mode:o}")

    console = present[CONSOLE_DEVICE[0]]
    if (console["rdevmajor"], console["rdevminor"]) != CONSOLE_DEVICE[1:]:
        raise CheckError(
            f"{CONSOLE_DEVICE[0]!r} 的设备号为 "
            f"{console['rdevmajor']}:{console['rdevminor']}，"
            f"应为 {CONSOLE_DEVICE[1]}:{CONSOLE_DEVICE[2]}")

    for applet in APPLETS:
        target = present[f"bin/{applet}"]["body"]
        if target != BUSYBOX_LINK.encode():
            raise CheckError(f"applet 链接 bin/{applet} 指向 {target!r}，"
                             f"应为 {BUSYBOX_LINK!r}")

    if not present["init"]["body"].startswith(b"#!") or present["init"]["body"] != INIT_SCRIPT:
        raise CheckError("/init 必须是 `#!` 脚本且与 INIT_SCRIPT 逐字节一致")
    if present[MUSL_INIT_NAME]["body"] != init_elf:
        raise CheckError(f"/{MUSL_INIT_NAME} 载荷不是本次构建的 ELF")
    if present["bin/busybox"]["body"] != busybox:
        raise CheckError("/bin/busybox 载荷与 build-busybox 产物不一致")

    kind_of = {MODE_DIR: "dir", MODE_SYMLINK: "symlink",
               MODE_CHARDEV: "chardev"}
    ordered = [Entry(entry["name"], entry["mode"],
                     kind_of.get(entry["mode"], "file"), entry["body"])
               for entry in entries[:-1]]
    for entry in ordered:
        if entry.mode == MODE_DIR:
            want = _dir_nlink(ordered, entry.name)
            got = present[entry.name]["nlink"]
            if got != want:
                raise CheckError(f"目录 {entry.name!r} 的 nlink 为 {got}，应为 {want}")
    return entries


# ── main ────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="build the M14 initramfs (newc)")
    parser.add_argument("--inject", choices=("mtime", "mode", "applet"),
                       help="evidence only: break determinism/mode/link on purpose")
    args = parser.parse_args()

    try:
        kernel = kernel_syscall_numbers()
        cross_check_numbers(kernel, musl_syscall_numbers(_musl_dir()))
        print(f"[PASS] syscall numbers agree: kernel syscall.tbl == musl bits/syscall.h")
        busybox_applets()
        busybox_bytes = busybox_product().read_bytes()

        outdir = linux_paths.linux_initramfs_dir()
        obj, elf = build_init(outdir)
        check_imports(obj)
        elf_bytes = elf.read_bytes()
        check_elf(elf, kernel)

        cpio = build_cpio(elf_bytes, inject=args.inject)
        entries = verify_archive(cpio, elf_bytes, busybox_bytes)

        init_path = outdir / "init"
        init_path.write_bytes(INIT_SCRIPT)
        init_path.chmod(0o755)
        cpio_path = outdir / "initramfs.cpio"
        cpio_path.write_bytes(cpio)

        manifest_entries = []
        for entry in entries[:-1]:
            record = {"name": entry["name"], "nlink": entry["nlink"],
                      "mode": f"{entry['mode']:07o}",
                      "kind": ("dir" if entry["mode"] == MODE_DIR else
                               "symlink" if entry["mode"] == MODE_SYMLINK else
                               "chardev" if entry["mode"] == MODE_CHARDEV else
                               "file")}
            if record["kind"] != "dir":
                record["size"] = len(entry["body"])
                record["sha256"] = _sha256(entry["body"])
            if record["kind"] == "symlink":
                record["target"] = entry["body"].decode()
            if record["kind"] == "chardev":
                record["rdev"] = [entry["rdevmajor"], entry["rdevminor"]]
            manifest_entries.append(record)

        manifest = {
            "format": 1,
            "init": {"name": "init", "kind": "script",
                     "mode": f"{MODE_FILE:07o}", "size": len(INIT_SCRIPT),
                     "sha256": _sha256(INIT_SCRIPT)},
            "musl_init": {"name": MUSL_INIT_NAME, "size": len(elf_bytes),
                          "sha256": _sha256(elf_bytes)},
            "busybox": {"name": "bin/busybox", "size": len(busybox_bytes),
                        "sha256": _sha256(busybox_bytes),
                        "applets": list(APPLETS)},
            "applet_links": {applet: BUSYBOX_LINK for applet in APPLETS},
            "entries": manifest_entries,
            "cpio": {"name": "initramfs.cpio", "size": len(cpio),
                     "sha256": _sha256(cpio)},
            "syscall_numbers": kernel,
        }
        manifest_path = linux_paths.linux_initramfs_manifest()
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                                 encoding="utf-8")

        print(f"[PASS] /init script ({len(INIT_SCRIPT)} B) -> exec /bin/sh "
              f"(busybox applet sh)")
        print(f"[PASS] image entries ({len(entries) - 1} + TRAILER), "
              f"mode/mtime/uid/gid/order verified")
        print(f"[INFO] busybox  : size={len(busybox_bytes)} "
              f"sha256={manifest['busybox']['sha256']}")
        print(f"[INFO] init.musl: size={len(elf_bytes)} "
              f"sha256={manifest['musl_init']['sha256']}")
        print(f"[INFO] cpio     : size={len(cpio)} sha256={manifest['cpio']['sha256']}")
        print(f"[INFO] manifest : {manifest_path.name} "
              f"({len(manifest_entries)} entry records)")
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
