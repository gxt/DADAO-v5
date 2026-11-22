#!/usr/bin/env python3
"""make_ldso_image.py — dynamic-linkage runtime closure on system Linux.

What this closes (task ``m18-infra-002``, contract ``contract-dynlink.md``):

  * kernel side: ``PT_INTERP`` = ``/lib/ld-musl-dadao.so.1`` (§6.1) is honoured
    by ``binfmt_elf`` on the DADAO kernel, the interpreter is loaded from the
    initramfs, and control is handed to musl's ldso with the auxv the loader
    needs (§6.2/§6.3);
  * loader side: ldso self-relocates, maps/relocates ``libc.so`` (§5),
    sets up TLS/errno (§7), and returns to user mode in the program;
  * program side: ``printf`` + ``malloc``/``free`` + ``write`` produce the
    expected bytes and the expected process status.

Two images are built (both are *runtime* artefacts under the kernel build
tree's sibling ``ldso-image/``; the record is ``manifest.json``):

  ``core``   ``/init`` **is** the dynamic executable (ELF with ``PT_INTERP``
             and ``DT_NEEDED=libc.so``), so PID 1's status is the program's
             status: the whole chain kernel→ldso→libc→return has one
             attributable exit code.  It exercises ``printf``, ``malloc``/
             ``free``, ``write``, a ``__thread`` variable (dynamic TLS) and
             ``errno``.
  ``probes`` ``/init`` is a *static* musl launcher that forks/execs one
             dynamic program per capability so a crash or a timeout of one
             probe cannot take the others with it: ``pthread_create/join``,
             ``dlopen`` of a real DSO, dynamic TLS in a pthread.  Every probe
             prints its own verdict; a failing probe is a **recorded boundary**
             (layer named), not a harness failure.

The static ``/init`` launcher is compiled against ``lib/libc.a`` from the same
musl tree (the static line is unchanged, see ``build_musl.py``), so no busybox
or shell is needed: the core image is ``/init`` + ``/lib/*``; the probes image
adds ``/tests/*`` (one dynamic program per capability) and a real DSO.

Kernel image: the shared out-of-tree build tree is re-configured with every
``CONFIG_DADAO_*`` probe pinned off (``config_pins.CONFIG_PINS``, the same
complete set as ``check_k6.py``; a new symbol cannot silently leak into this
image), ``CONFIG_DADAO_K6_SHELL=y`` so ``kernel_init()`` reaches the
initramfs, and ``CONFIG_INITRAMFS_SOURCE`` pointing at this image.  The line is
restored to the K6 archive's canonical path afterwards (always, success or not),
so the shared tree does not keep this image and a later ``check-linux-k6``
cannot boot it by accident.

Evidence FAIL paths (``--inject``; the source tree is never modified — the
injection is applied to a *copy* in this tool's build dir, and the real
artefact's md5 is printed before/after):

  ``interp``  relink ``/init`` with ``-dynamic-linker /lib/ld-musl-dadao.so.1.missing``
              (the image does not ship that path) ⇒ the kernel cannot load the
              interpreter and PID 1 never runs ⇒ boot fails;
  ``symbol``  ship a copy of ``libc.so`` whose ``.dynsym`` entry named ``printf``
              has ``st_name = 0`` ⇒ ldso cannot resolve ``printf`` for the
              executable ⇒ loader error / early exit, not rc 42.

Usage:
  python3 tools/linux/make_ldso_image.py                 # core image + boot + judge
  python3 tools/linux/make_ldso_image.py --case probes    # capability matrix
  python3 tools/linux/make_ldso_image.py --inject interp  # evidence FAIL path
  python3 tools/linux/make_ldso_image.py --no-boot        # image/ELF checks only

Exit status: 0 = built and judged PASS; 1 = a check FAILED; 2 = setup error
(toolchain / musl build / kernel tree missing).  For ``--case probes`` the exit
status is 0 when the harness ran and every probe produced a verdict; a probe
that is unsupported is reported as ``[BOUNDARY]`` (never silently skipped).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.infra import build_musl as musl_elf          # noqa: E402
from tools.linux import config_pins                      # noqa: E402
from tools.linux import make_defconfig as defconfig      # noqa: E402
from tools.linux import make_initramfs as newc           # noqa: E402
from tools.linux import paths as linux_paths             # noqa: E402
from tools.qemu import k0_boot_probe as k0               # noqa: E402

TARGET = "dadao-unknown-elf"
SONAME = "libc.so"
LDSO_NAME = "ld-musl-dadao.so.1"
DYNAMIC_LINKER = f"/lib/{LDSO_NAME}"

JOBS = os.environ.get("JOBS", "32")
BOOT_TIMEOUT = int(os.environ.get("LDSO_BOOT_TIMEOUT", "180"))
#: A broken loader path panics and the machine then simply idles; the
#: injection only has to observe "no 42", so a shorter liveness budget is used.
INJECT_TIMEOUT = int(os.environ.get("LDSO_INJECT_TIMEOUT", "60"))

#: Every ``CONFIG_DADAO_*`` symbol of the Kconfig fragment, for *this* image
#: (same complete set as ``check_k6.py``: production boot, no probe owns the
#: continuation).  ``check-config-pins`` C3 compares the key set with the
#: Kconfig source, so a new symbol cannot be forgotten here.
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

#: K6 continuation symbol lives in ``arch/dadao/Kconfig`` (not the debug
#: fragment), so it is not part of the pin set; kept as a name, never as an
#: inline ``CONFIG_DADAO_X=v`` list element (``check-config-pins`` C4).
K6_SHELL_LINE = "CONFIG_DADAO_K6_SHELL=y"

#: /dev entries: the semihosting console (240:0, K6 register) plus the two
#: character devices musl's stdio may touch.
DEVICES = {
    "dev/console": (240, 0),
    "dev/null": (1, 3),
    "dev/zero": (1, 5),
}

#: Core program: printf + malloc/free + write + dynamic TLS + errno.  The
#: return value is 42 only when every checked property held, so the QEMU
#: process status alone says whether the whole chain worked.
CORE_C = r"""
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static __thread int tls_value = 7;

int main(void)
{
    char *buf = malloc(64);
    int malloc_ok = 0;
    if (buf) {
        snprintf(buf, 64, "malloc-%d", 1234);
        malloc_ok = (strcmp(buf, "malloc-1234") == 0);
        free(buf);
    }

    tls_value += 35;
    int tls_ok = (tls_value == 42);

    errno = 0;
    ssize_t bad = write(-1, "x", 1);
    int errno_ok = (bad == -1 && errno == EBADF);

    printf("LDSO-PRINTF=%d\n", 42);
    printf("LDSO-MALLOC=%d\n", malloc_ok);
    printf("LDSO-TLS=%d\n", tls_ok);
    printf("LDSO-ERRNO=%d\n", errno_ok);
    fflush(NULL);
    write(1, "LDSO-WRITE=ok\n", 14);

    int code = (malloc_ok && tls_ok && errno_ok) ? 42 : 9;
    printf("LDSO-EXIT=%d\n", code);   /* the guest-side exit code, in-band */
    return code;
}
"""

#: Static launcher for the probes image: PID 1 forks/execs each probe, waits,
#: and prints one ``PROBE <name> exit=<n> sig=<n>`` line per probe.  An alarm
#: in the child bounds a wedged probe; a crashing probe only kills its child.
LAUNCHER_C = r"""
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

static const char *probes[] = {
    "/tests/probe_pthread",
    "/tests/probe_dlopen",
    0
};

int main(void)
{
    int i;
    for (i = 0; probes[i]; i++) {
        const char *path = probes[i];
        const char *name = strrchr(path, '/') + 1;
        pid_t pid = fork();
        if (pid == 0) {
            char *argv[] = { (char *)path, 0 };
            char *envp[] = { 0 };
            alarm(30);
            execve(path, argv, envp);
            _exit(120);
        }
        if (pid < 0) {
            printf("PROBE %s fork-failed\n", name);
            continue;
        }
        int status = 0;
        if (waitpid(pid, &status, 0) < 0) {
            printf("PROBE %s wait-failed\n", name);
            continue;
        }
        if (WIFEXITED(status))
            printf("PROBE %s exit=%d sig=0\n", name, WEXITSTATUS(status));
        else
            printf("PROBE %s exit=-1 sig=%d\n", name,
                   WIFSIGNALED(status) ? WTERMSIG(status) : -1);
        fflush(NULL);
    }
    printf("LDSO-PROBES-DONE\n");
    fflush(NULL);
    return 0;
}
"""

PTHREAD_C = r"""
#include <pthread.h>
#include <stdio.h>

static __thread int tls_seen = -1;
static int worker_ran;

static void *worker(void *arg)
{
    (void)arg;
    tls_seen = 5;               /* per-thread TLS in the new thread */
    worker_ran = 1;
    return (void *)0x2a;
}

int main(void)
{
    pthread_t thread;
    void *ret = 0;
    int rc = pthread_create(&thread, 0, worker, 0);
    if (rc != 0) {
        printf("PTHREAD create-error=%d\n", rc);
        return 2;
    }
    rc = pthread_join(thread, &ret);
    int main_tls = (tls_seen == -1);
    printf("PTHREAD join=%d ret=%ld main-tls-intact=%d\n",
           rc, (long)ret, main_tls);
    return (rc == 0 && ret == (void *)0x2a && worker_ran && main_tls) ? 0 : 3;
}
"""

DLOPEN_C = r"""
#include <dlfcn.h>
#include <stdio.h>

int main(void)
{
    void *handle = dlopen("/lib/libdlprobe.so", RTLD_NOW);
    if (!handle) {
        printf("DLOPEN self-error=%s\n", dlerror());
        return 2;
    }
    int (*value)(void) = (int (*)(void))dlsym(handle, "dlprobe_value");
    if (!value) {
        printf("DLOPEN dlsym-error=%s\n", dlerror());
        return 3;
    }
    int got = value();
    printf("DLOPEN value=%d\n", got);
    dlclose(handle);
    return (got == 1234) ? 0 : 4;
}
"""

DLPROBE_C = r"""
/* A real DSO for dlopen: no libc dependency, one exported function. */
int dlprobe_value(void)
{
    return 1234;
}
"""

#: Expected marker lines of the core image (exactly once each).
CORE_MARKERS = ("LDSO-PRINTF=42", "LDSO-MALLOC=1", "LDSO-TLS=1",
                "LDSO-ERRNO=1", "LDSO-WRITE=ok", "LDSO-EXIT=42")
CORE_EXIT = 42

#: Probes image: (program, expected verdict line).  A probe whose line is
#: missing is a harness failure; a probe that exits non-zero / dies by signal
#: prints a different line and is a *recorded capability boundary*.
PROBES = (("probe_pthread", "PROBE probe_pthread exit=0 sig=0"),
          ("probe_dlopen", "PROBE probe_dlopen exit=0 sig=0"))

#: Dynamic tags the contract's tag set may carry but this build does not emit
#: (§5: RPATH/RUNPATH are in musl's consumed set; v5 states no such tag).
DT_RPATH = 15
DT_RUNPATH = 29
DT_VERSYM = musl_elf.DT_VERSYM
DT_VERDEF = musl_elf.DT_VERDEF
DT_VERNEED = musl_elf.DT_VERNEED

#: Failure text the kernel/loader print when the chain breaks (used by the
#: injection checks as positive evidence that the expected layer failed).
LOADER_FAILURE_RE = re.compile(
    r"(Kernel panic|No working init found|Failed to execute|"
    r"Error relocating|symbol not found|Segmentation fault|Illegal instruction)")


class SetupError(RuntimeError):
    """Missing prerequisite (exit 2)."""


class CheckError(RuntimeError):
    """A built artefact / boot violates a required property (exit 1)."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def md5_file(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# paths / toolchain
# ---------------------------------------------------------------------------

def image_root() -> Path:
    """Disposable runtime root (sibling of the kernel build tree)."""
    return linux_paths.linux_build_dir().parent / "ldso-image"


def build_root() -> Path:
    return image_root() / "build"


def image_dir() -> Path:
    return image_root() / "image"


def image_cpio() -> Path:
    return image_dir() / "initramfs.cpio"


def image_manifest() -> Path:
    return image_dir() / "manifest.json"


def musl_dir() -> Path:
    musl = linux_paths.linux_source_dir().parent / "musl"
    for rel in ("lib/crt1.o", "lib/libc.a", f"lib/{SONAME}"):
        if not (musl / rel).is_file():
            raise SetupError(f"{musl / rel} not found — run "
                             f"'make build-musl-shared' first")
    return musl


def tool(name: str) -> Path:
    path = linux_paths.toolchain_bin() / name
    if not path.is_file():
        raise SetupError(f"{path} not found — run 'make install-host' first")
    return path


def builtins_archive() -> Path:
    clang = tool("clang")
    proc = subprocess.run(
        [str(clang), f"--target={TARGET}", "-rtlib=compiler-rt",
         "-print-libgcc-file-name"],
        capture_output=True, text=True)
    path = Path(proc.stdout.strip())
    if proc.returncode != 0 or not path.is_file():
        raise SetupError(f"target builtins archive not found (clang rc="
                         f"{proc.returncode}) — run 'make install-host'")
    return path


def include_flags(musl: Path) -> list[str]:
    """The *public* musl headers only.

    A consumer of ``libc.so`` must not see musl's internal headers: they spell
    ``errno`` as ``___errno_location`` and ``stdout`` as ``__stdout_FILE``,
    which are internal aliases the shared library does not export (the link
    fails with "undefined hidden symbol").  ``arch/<triple>/bits`` and
    ``arch/generic/bits`` provide the hand-written ``bits/`` headers,
    ``obj/include`` the generated ones and ``include`` the public headers.
    """
    return [f"-I{musl / 'arch' / 'dadao'}", f"-I{musl / 'arch' / 'generic'}",
            f"-I{musl / 'obj' / 'include'}", f"-I{musl / 'include'}"]


def run(cmd: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess:
    proc = subprocess.run([str(c) for c in cmd], cwd=cwd,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True)
    if proc.returncode != 0:
        raise CheckError(f"command failed (rc={proc.returncode}): "
                         f"{' '.join(str(c) for c in cmd)}\n{proc.stdout}")
    return proc


# ---------------------------------------------------------------------------
# program build
# ---------------------------------------------------------------------------

def compile_program(name: str, source: str, musl: Path, *, pic: bool = False) -> Path:
    src = build_root() / f"{name}.c"
    obj = build_root() / f"{name}.o"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text(source)
    cmd = [tool("clang"), f"--target={TARGET}", "-O1", "-nostdinc",
           "-ffile-prefix-map=" + str(_REPO) + "=.",
           *include_flags(musl), "-c", str(src), "-o", str(obj)]
    if pic:
        cmd.insert(3, "-fPIC")
    run(cmd, cwd=_REPO)
    return obj


def link_dynamic(name: str, obj: Path, musl: Path, *,
                 interpreter: str = DYNAMIC_LINKER) -> Path:
    """ET_EXEC + PT_INTERP + DT_NEEDED=libc.so (contract §6.1)."""
    elf = build_root() / name
    run([tool("ld.lld"), musl / "lib" / "crt1.o", obj, musl / "lib" / SONAME,
         "-dynamic-linker", interpreter, "-o", elf], cwd=_REPO)
    elf.chmod(0o755)
    return elf


def link_static(name: str, obj: Path, musl: Path) -> Path:
    elf = build_root() / name
    run([tool("ld.lld"), musl / "lib" / "crt1.o", obj,
         "--start-group", musl / "lib" / "libc.a", builtins_archive(),
         "--end-group", "-o", elf], cwd=_REPO)
    elf.chmod(0o755)
    return elf


def link_shared(name: str, obj: Path) -> Path:
    """A minimal ET_DYN DSO (no libc) for the dlopen probe."""
    elf = build_root() / name
    run([tool("ld.lld"), "-shared", "--hash-style=gnu", "-soname", name,
         obj, "-o", elf], cwd=_REPO)
    return elf


# ---------------------------------------------------------------------------
# ELF assertions (reuse build_musl's parser; expectations from the contract)
# ---------------------------------------------------------------------------

def check_dynamic_program(elf: Path, interpreter: str = DYNAMIC_LINKER) -> list[tuple[str, str, str, bool]]:
    info = musl_elf.parse_elf(elf)
    types = {p["type"] for p in info["phdrs"]}
    tags = dict(info["dynamic"] or [])
    needed = [musl_elf.dyn_string_at(info, tags, value)
              for tag, value in (info["dynamic"] or []) if tag == musl_elf.DT_NEEDED]
    raw = musl_elf.interp_bytes(info)
    want = interpreter.encode() + b"\0"
    return [
        ("dynamic program parses", "no parse error",
         info["parse_error"] or "no parse error", info["parse_error"] is None),
        ("ELF class 64", "2", str(info["ei_class"]), info["ei_class"] == 2),
        ("big-endian", "2", str(info["ei_data"]), info["ei_data"] == 2),
        ("e_machine EM_DADAO", "0x0da0", f"0x{info['e_machine']:04x}",
         info["e_machine"] == musl_elf.EM_DADAO),
        ("PT_INTERP present", "present", "present" if musl_elf.PT_INTERP in types
         else "absent", musl_elf.PT_INTERP in types),
        ("PT_INTERP bytes", repr(want), f"{raw!r} ({len(raw)} B)", raw == want),
        ("PT_DYNAMIC present", "present",
         "present" if musl_elf.PT_DYNAMIC in types else "absent",
         musl_elf.PT_DYNAMIC in types),
        ("DT_NEEDED = libc.so", [SONAME], str(needed), needed == [SONAME]),
        ("no DT_RPATH/DT_RUNPATH", "absent",
         str([t for t in (DT_RPATH, DT_RUNPATH) if t in tags]),
         not any(t in tags for t in (DT_RPATH, DT_RUNPATH))),
    ]


def check_shared_library(so: Path) -> list[tuple[str, str, str, bool]]:
    """The contract §5 shape of libc.so (rulings 6/7: GNU hash, no version/RELR)."""
    info = musl_elf.parse_elf(so)
    tags = dict(info["dynamic"] or [])
    soname = musl_elf.dyn_string(info, tags, musl_elf.DT_SONAME)
    version_sections = sorted(s for s in info["sections"] if s.startswith(".gnu.version"))
    version_tags = sorted(t for t in (DT_VERSYM, DT_VERDEF, DT_VERNEED) if t in tags)
    return [
        ("libc.so is ET_DYN", "3", str(info["e_type"]), info["e_type"] == musl_elf.ET_DYN),
        ("libc.so big-endian", "2", str(info["ei_data"]), info["ei_data"] == 2),
        ("libc.so EM_DADAO", "0x0da0", f"0x{info['e_machine']:04x}",
         info["e_machine"] == musl_elf.EM_DADAO),
        ("libc.so DT_SONAME", SONAME, soname or "absent", soname == SONAME),
        ("libc.so DT_GNU_HASH", "present",
         "present" if musl_elf.DT_GNU_HASH in tags else "absent",
         musl_elf.DT_GNU_HASH in tags),
        ("libc.so no DT_HASH", "absent",
         "present" if musl_elf.DT_HASH in tags else "absent",
         musl_elf.DT_HASH not in tags),
        ("libc.so no DT_RELR", "absent",
         "present" if musl_elf.DT_RELR in tags else "absent",
         musl_elf.DT_RELR not in tags),
        ("libc.so no DT_RELRSZ", "absent",
         "present" if musl_elf.DT_RELRSZ in tags else "absent",
         musl_elf.DT_RELRSZ not in tags),
        ("libc.so no version tags", "absent", str(version_tags), not version_tags),
        ("libc.so no .gnu.version* sections", "absent", str(version_sections),
         not version_sections),
        ("libc.so no DT_RPATH/DT_RUNPATH", "absent",
         str([t for t in (DT_RPATH, DT_RUNPATH) if t in tags]),
         not any(t in tags for t in (DT_RPATH, DT_RUNPATH))),
    ]


def check_static_program(elf: Path) -> list[tuple[str, str, str, bool]]:
    info = musl_elf.parse_elf(elf)
    types = {p["type"] for p in info["phdrs"]}
    return [
        ("static launcher ET_EXEC", "2", str(info["e_type"]), info["e_type"] == 2),
        ("static launcher no PT_INTERP", "absent",
         "present" if musl_elf.PT_INTERP in types else "absent",
         musl_elf.PT_INTERP not in types),
        ("static launcher no PT_DYNAMIC", "absent",
         "present" if musl_elf.PT_DYNAMIC in types else "absent",
         musl_elf.PT_DYNAMIC not in types),
    ]


# ---------------------------------------------------------------------------
# injection helpers (applied to COPIES; the build tree is not modified)
# ---------------------------------------------------------------------------

DYNSYM = 11


def strip_dynamic_symbol(so: Path, symbol: str) -> Path:
    """Copy of @so whose ``.dynsym`` entry @symbol has ``st_name = 0``.

    ldso resolves an import by comparing the name in the hash chain with the
    string in ``.dynstr``; a zeroed name makes the symbol unfindable, so a
    program that imports it fails during relocation.  The bytes around the
    change are re-read and asserted, so an injection that did not apply is an
    error instead of a false PASS.
    """
    data = bytearray(so.read_bytes())
    order = ">" if data[5] == 2 else "<"
    e_shoff = struct.unpack_from(order + "Q", data, 0x28)[0]
    e_shentsize, e_shnum, _shstrndx = struct.unpack_from(order + "HHH", data, 0x3A)
    sections = []
    for index in range(e_shnum):
        off = e_shoff + index * e_shentsize
        sh_name, sh_type = struct.unpack_from(order + "II", data, off)
        sh_offset, sh_size, sh_link = struct.unpack_from(order + "QQI", data, off + 0x18)
        sections.append({"name": sh_name, "type": sh_type, "offset": sh_offset,
                         "size": sh_size, "link": sh_link})
    dynsym = next((s for s in sections if s["type"] == DYNSYM), None)
    if dynsym is None:
        raise CheckError(f"{so}: no .dynsym section")
    strtab = sections[dynsym["link"]]
    hits = 0
    for index in range(dynsym["size"] // 24):
        sym = dynsym["offset"] + index * 24
        st_name = struct.unpack_from(order + "I", data, sym)[0]
        end = data.find(b"\0", strtab["offset"] + st_name)
        name = data[strtab["offset"] + st_name:end].decode("latin-1")
        if name == symbol:
            data[sym:sym + 4] = b"\0\0\0\0"
            hits += 1
    if hits != 1:
        raise CheckError(f"{so}: expected exactly one .dynsym entry named "
                         f"{symbol!r}, found {hits}")
    out = build_root() / f"{so.name}.nostrip-{symbol}"
    out.write_bytes(bytes(data))
    # Re-read through the same parser: the symbol must be gone from .dynsym.
    names = dynamic_symbol_names(out)
    if symbol in names:
        raise CheckError(f"injection did not remove {symbol!r} from {out}")
    print(f"[INJECT] {symbol}: one .dynsym entry renamed, copy={out} "
          f"md5={md5_file(out)}")
    return out


def dynamic_symbol_names(so: Path) -> set[str]:
    data = so.read_bytes()
    order = ">" if data[5] == 2 else "<"
    e_shoff = struct.unpack_from(order + "Q", data, 0x28)[0]
    e_shentsize, e_shnum, _ = struct.unpack_from(order + "HHH", data, 0x3A)
    sections = []
    for index in range(e_shnum):
        off = e_shoff + index * e_shentsize
        sh_name, sh_type = struct.unpack_from(order + "II", data, off)
        sh_offset, sh_size, sh_link = struct.unpack_from(order + "QQI", data, off + 0x18)
        sections.append({"type": sh_type, "offset": sh_offset,
                         "size": sh_size, "link": sh_link})
    dynsym = next((s for s in sections if s["type"] == DYNSYM), None)
    if dynsym is None:
        return set()
    strtab = sections[dynsym["link"]]
    names = set()
    for index in range(dynsym["size"] // 24):
        st_name = struct.unpack_from(order + "I", data,
                                     dynsym["offset"] + index * 24)[0]
        if not st_name:
            continue
        end = data.find(b"\0", strtab["offset"] + st_name)
        names.add(data[strtab["offset"] + st_name:end].decode("latin-1"))
    return names


# ---------------------------------------------------------------------------
# cpio image (newc writer imported from make_initramfs.py — one format)
# ---------------------------------------------------------------------------

def dir_nlink(entries: list[newc.Entry], name: str) -> int:
    prefix = "" if name == "." else name + "/"
    subdirs = sum(
        1 for entry in entries
        if (entry.mode & 0o170000) == 0o040000 and entry.name != "."
        and entry.name.startswith(prefix) and "/" not in entry.name[len(prefix):])
    return 2 + subdirs


def build_cpio(entries: list[newc.Entry]) -> bytes:
    encoded = [
        newc._newc_entry(entry.name, index + 1, entry.mode, entry.data,
                         nlink=(dir_nlink(entries, entry.name)
                                if entry.kind == "dir" else 1),
                         mtime=0, rdevmajor=entry.rdevmajor,
                         rdevminor=entry.rdevminor)
        for index, entry in enumerate(entries)
    ]
    encoded.append(newc._newc_entry(newc.CPIO_TRAILER, 0, 0, b"", nlink=1, mtime=0))
    return b"".join(encoded)


def verify_archive(cpio: bytes, expected: dict[str, tuple[int, bytes]]) -> list[dict]:
    """Re-parse the archive and assert every entry (payload, mode, order)."""
    parsed = newc.parse_newc(cpio)
    names = [entry["name"] for entry in parsed]
    if names[-1] != newc.CPIO_TRAILER:
        raise CheckError(f"last cpio entry is {names[-1]!r}")
    if names[0] != ".":
        raise CheckError(f"first cpio entry is {names[0]!r}")
    body = names[1:-1]
    if body != sorted(body):
        raise CheckError("cpio entries are not in lexicographic order")
    present = {entry["name"]: entry for entry in parsed[:-1]}
    missing = sorted(set(expected) - set(present))
    if missing:
        raise CheckError(f"image is missing entries {missing}")
    extra = sorted(set(present) - set(expected))
    if extra:
        raise CheckError(f"image has unexpected entries {extra}")
    for name, (mode, payload) in expected.items():
        entry = present[name]
        if entry["mode"] != mode:
            raise CheckError(f"{name!r} mode {entry['mode']:o} != {mode:o}")
        if payload is not None and entry["body"] != payload:
            raise CheckError(f"{name!r} payload is not the built artefact")
        if (entry["mtime"], entry["uid"], entry["gid"]) != (0, 0, 0):
            raise CheckError(f"{name!r} is not deterministic")
    return parsed


# ---------------------------------------------------------------------------
# images
# ---------------------------------------------------------------------------

def core_entries(dynamic: bytes, so_bytes: bytes) -> list[newc.Entry]:
    items = [
        newc.Entry(".", newc.MODE_DIR, "dir", b""),
        newc.Entry("dev", newc.MODE_DIR, "dir", b""),
        newc.Entry("init", newc.MODE_FILE, "file", dynamic),
        newc.Entry("lib", newc.MODE_DIR, "dir", b""),
        newc.Entry(f"lib/{SONAME}", newc.MODE_FILE, "file", so_bytes),
        newc.Entry(f"lib/{LDSO_NAME}", newc.MODE_SYMLINK, "symlink",
                   SONAME.encode()),
    ]
    for name, (major, minor) in DEVICES.items():
        items.append(newc.Entry(name, newc.MODE_CHARDEV, "chardev", b"",
                                major, minor))
    return sorted(items, key=lambda entry: entry.name)


def probes_entries(launcher: bytes, programs: dict[str, bytes], so: bytes,
                   dso: bytes) -> list[newc.Entry]:
    items = [
        newc.Entry(".", newc.MODE_DIR, "dir", b""),
        newc.Entry("dev", newc.MODE_DIR, "dir", b""),
        newc.Entry("init", newc.MODE_FILE, "file", launcher),
        newc.Entry("lib", newc.MODE_DIR, "dir", b""),
        newc.Entry(f"lib/{SONAME}", newc.MODE_FILE, "file", so),
        newc.Entry(f"lib/{LDSO_NAME}", newc.MODE_SYMLINK, "symlink",
                   SONAME.encode()),
        newc.Entry("lib/libdlprobe.so", newc.MODE_FILE, "file", dso),
        newc.Entry("tests", newc.MODE_DIR, "dir", b""),
    ]
    for name, payload in programs.items():
        items.append(newc.Entry(f"tests/{name}", newc.MODE_FILE, "file", payload))
    for name, (major, minor) in DEVICES.items():
        items.append(newc.Entry(name, newc.MODE_CHARDEV, "chardev", b"",
                                major, minor))
    return sorted(items, key=lambda entry: entry.name)


def build_image(case: str, inject: str | None) -> dict:
    musl = musl_dir()
    so_path = musl / "lib" / SONAME
    so_md5_before = md5_file(so_path)
    print(f"[INFO] libc.so md5 before image: {so_md5_before}")

    so_bytes = so_path.read_bytes()
    if inject == "symbol":
        # The injection is applied to a COPY (never to the build tree); the
        # original file's md5 is asserted again after the image is written.
        so_bytes = strip_dynamic_symbol(so_path, "printf").read_bytes()

    if case == "core":
        interpreter = DYNAMIC_LINKER if inject != "interp" else DYNAMIC_LINKER + ".missing"
        obj = compile_program("dyn_core", CORE_C, musl)
        dynamic = link_dynamic("dyn_core", obj, musl, interpreter=interpreter)
        checks = check_dynamic_program(dynamic, interpreter)
        checks += check_shared_library(so_path)
        report_checks(checks, "core ELF")
        entries = core_entries(dynamic.read_bytes(), so_bytes)
        expected = {
            ".": (newc.MODE_DIR, None), "dev": (newc.MODE_DIR, None),
            "init": (newc.MODE_FILE, dynamic.read_bytes()),
            "lib": (newc.MODE_DIR, None),
            f"lib/{SONAME}": (newc.MODE_FILE, so_bytes),
            f"lib/{LDSO_NAME}": (newc.MODE_SYMLINK, SONAME.encode()),
        }
        for name, _rdev in DEVICES.items():
            expected[name] = (newc.MODE_CHARDEV, None)
        programs = {"init": dynamic}
        markers = CORE_MARKERS
        want_exit = CORE_EXIT
    elif case == "probes":
        launcher_obj = compile_program("ldso_launcher", LAUNCHER_C, musl)
        launcher = link_static("ldso_launcher", launcher_obj, musl)
        report_checks(check_static_program(launcher), "probes launcher ELF")
        programs = {}
        for name, source in (("probe_pthread", PTHREAD_C),
                             ("probe_dlopen", DLOPEN_C)):
            obj = compile_program(name, source, musl, pic=True)
            elf = link_dynamic(name, obj, musl)
            report_checks(check_dynamic_program(elf), f"{name} ELF")
            programs[name] = elf.read_bytes()
        dso_obj = compile_program("libdlprobe", DLPROBE_C, musl, pic=True)
        dso = link_shared("libdlprobe.so", dso_obj)
        report_checks(check_shared_program(dso), "libdlprobe.so ELF")
        entries = probes_entries(launcher.read_bytes(), programs, so_bytes,
                                 dso.read_bytes())
        expected = {
            ".": (newc.MODE_DIR, None), "dev": (newc.MODE_DIR, None),
            "init": (newc.MODE_FILE, launcher.read_bytes()),
            "lib": (newc.MODE_DIR, None),
            f"lib/{SONAME}": (newc.MODE_FILE, so_bytes),
            f"lib/{LDSO_NAME}": (newc.MODE_SYMLINK, SONAME.encode()),
            "lib/libdlprobe.so": (newc.MODE_FILE, dso.read_bytes()),
            "tests": (newc.MODE_DIR, None),
        }
        for name, payload in programs.items():
            expected[f"tests/{name}"] = (newc.MODE_FILE, payload)
        for name, _rdev in DEVICES.items():
            expected[name] = (newc.MODE_CHARDEV, None)
        markers = ("LDSO-PROBES-DONE",)
        want_exit = 0
    else:
        raise SetupError(f"unknown case {case!r}")

    cpio = build_cpio(entries)
    verify_archive(cpio, expected)
    image_dir().mkdir(parents=True, exist_ok=True)
    image_cpio().write_bytes(cpio)
    manifest = {
        "format": 1,
        "case": case,
        "inject": inject,
        "dynamic_linker": DYNAMIC_LINKER,
        "libc_so": {"md5": md5_file(so_path), "sha256": sha256_bytes(so_bytes)},
        "cpio": {"name": image_cpio().name, "size": len(cpio),
                 "sha256": sha256_bytes(cpio)},
        "entries": [{"name": entry.name, "mode": f"{entry.mode:07o}",
                     "sha256": sha256_bytes(entry.data),
                     "size": len(entry.data)}
                    for entry in entries],
        "markers": list(markers),
        "expected_exit": want_exit,
    }
    image_manifest().write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                                encoding="utf-8")
    print(f"[PASS] image ({case}{'/' + inject if inject else ''}): "
          f"{len(entries)} entries, {len(cpio)} B "
          f"sha256={manifest['cpio']['sha256'][:12]}")
    if md5_file(so_path) != so_md5_before:
        raise CheckError(f"{so_path} changed while building the image "
                         f"({so_md5_before} -> {md5_file(so_path)})")
    return manifest


def check_shared_program(dso: Path) -> list[tuple[str, str, str, bool]]:
    info = musl_elf.parse_elf(dso)
    return [
        ("libdlprobe ET_DYN", "3", str(info["e_type"]), info["e_type"] == 3),
        ("libdlprobe e_machine", "0x0da0", f"0x{info['e_machine']:04x}",
         info["e_machine"] == musl_elf.EM_DADAO),
    ]


# ---------------------------------------------------------------------------
# kernel + boot
# ---------------------------------------------------------------------------

def kernel_config(cpio: Path) -> int:
    build = linux_paths.linux_build_dir()
    if not (build / ".config").is_file():
        rc = subprocess.call([sys.executable,
                              str(_REPO / "tools" / "linux" / "make_defconfig.py"),
                              "--jobs", JOBS])
        if rc != 0:
            return rc
    lines = config_pins.config_lines(CONFIG_PINS) + [
        K6_SHELL_LINE,
        f'CONFIG_INITRAMFS_SOURCE="{cpio}"',
    ]
    return defconfig.apply_config_lines(lines)


def restore_k6_initramfs() -> None:
    """Point the shared build tree back at the K6 image (always).

    The line is restored to its **canonical path even when the archive does not
    exist yet**: leaving this image's path behind made ``check-linux-k6`` boot
    the ldso image (its own ``make_initramfs.py`` step builds the K6 archive but
    does not set ``CONFIG_INITRAMFS_SOURCE``, which it expects the tree to carry
    already).  A missing archive is printed as a warning; the next K6 image
    build creates it, and a kernel build in between fails loudly instead of
    silently embedding the wrong rootfs.
    """
    k6_cpio = linux_paths.linux_initramfs_dir() / "initramfs.cpio"
    rc = defconfig.apply_config_lines([f'CONFIG_INITRAMFS_SOURCE="{k6_cpio}"'])
    state = "present" if k6_cpio.is_file() else "not built yet"
    print(f"[INFO] shared build tree: CONFIG_INITRAMFS_SOURCE -> K6 image "
          f"({k6_cpio}, {state}, rc={rc})", flush=True)


def build_kernel() -> int:
    return subprocess.call(
        [sys.executable, str(_REPO / "tools" / "linux" / "make_vmlinux.py"),
         "--jobs", JOBS, "--skip-code-range"])


def firmware() -> str:
    k0.load_contract()
    if not k0.ABI:
        raise SetupError("the boot contract is empty — cannot build the bootrom")
    scratch = image_root() / "scratch"
    scratch.mkdir(parents=True, exist_ok=True)
    return k0.build_firmware(str(scratch / "bootrom"), name="bootrom_ldso.bin")


def boot(tag: str, timeout: int = BOOT_TIMEOUT) -> tuple[int, str, list[str]]:
    vmlinux = linux_paths.linux_build_dir() / "vmlinux"
    if not vmlinux.is_file():
        raise SetupError(f"{vmlinux} missing — the kernel build did not produce it")
    qemu = linux_paths.toolchain_bin() / "qemu-system-dadao"
    if not os.access(qemu, os.X_OK):
        raise SetupError(f"{qemu} missing — run 'make install-host'")
    cmd = [str(qemu), "-machine", f"kaiwu-vast,bootrom-image={firmware()}",
           "-display", "none", "-serial", "none",
           "-chardev", "stdio,id=semi",
           "-semihosting-config", "enable=on,target=native,chardev=semi",
           "-kernel", str(vmlinux)]
    try:
        proc = subprocess.run(cmd, cwd=str(_REPO), stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, timeout=timeout)
        rc = proc.returncode
        text = (proc.stdout or "") + (proc.stderr or "")
        reason = "guest-exit"
    except subprocess.TimeoutExpired as exc:
        rc = 124
        out = exc.stdout or ""
        if isinstance(out, bytes):
            out = out.decode(errors="replace")
        text = out
        reason = "host-timeout"
    (build_root() / f"console-{tag}.log").write_text(text, encoding="utf-8")
    print(f"[INFO] boot {tag}: qemu rc={rc} ({reason}); "
          f"console={build_root() / ('console-' + tag + '.log')}")
    return rc, text, cmd


def judge(case: str, manifest: dict, rc: int, text: str,
          inject: str | None) -> list[tuple[str, str, str, bool]]:
    checks: list[tuple[str, str, str, bool]] = []
    if inject:
        # The chain must break *and* the break must be attributable.
        checks.append((f"inject {inject}: boot did not return the expected "
                       f"status", f"!= {CORE_EXIT}", str(rc), rc != CORE_EXIT))
        hit = LOADER_FAILURE_RE.search(text)
        checks.append((f"inject {inject}: failure names the loader/kernel stage",
                       "panic/No working init/loader error", hit.group(0) if hit else "no marker",
                       hit is not None))
        if inject == "symbol":
            checks.append(("inject symbol: the missing symbol is named",
                           "printf", "printf" if "printf" in text else "absent",
                           "printf" in text))
        return checks

    checks.append(("kernel executed /init as init", "Run /init as init process",
                   "present" if "Run /init as init process" in text else "absent",
                   "Run /init as init process" in text))
    checks.append(("QEMU process status == program exit", manifest["expected_exit"],
                   str(rc), rc == manifest["expected_exit"]))
    for marker in manifest["markers"]:
        count = len([line for line in text.splitlines() if marker in line])
        checks.append((f"output marker {marker}", 1, count, count == 1))
    bad = LOADER_FAILURE_RE.findall(text)
    checks.append(("no loader/kernel failure text", [], sorted(set(bad)),
                   not bad))
    if case == "probes":
        for name, ok_line in PROBES:
            line = next((ln for ln in text.splitlines()
                         if f"PROBE {name} " in ln), None)
            checks.append((f"probe {name} produced a verdict", True, line is not None,
                           line is not None))
            if line is not None and line.strip() != ok_line:
                print(f"[BOUNDARY] {name}: {line.strip()} "
                      f"(layer evidence: console lines around it)")
    return checks


def report_checks(checks: list[tuple[str, str, str, bool]], label: str) -> None:
    failed = 0
    for name, expected, actual, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}: {name} | "
              f"expect={expected} actual={actual}")
        if not ok:
            failed += 1
    if failed:
        raise CheckError(f"{failed}/{len(checks)} {label} checks failed")


# ---------------------------------------------------------------------------
# qemu-user (best effort; a qemu-component gap is recorded, not hidden)
# ---------------------------------------------------------------------------

def qemu_user_probe(case: str) -> None:
    """Run the dynamic program under ``qemu-dadao`` with a guest root.

    Best-effort by task book: a gap here belongs to the qemu component and must
    not block the system-Linux delivery.  Both outcomes print evidence.
    """
    qemu = linux_paths.toolchain_bin() / "qemu-dadao"
    if not os.access(qemu, os.X_OK):
        print("[BOUNDARY] qemu-user: qemu-dadao missing (make install-host)")
        return
    root = image_dir() / "guest-root"
    if root.exists():
        shutil.rmtree(root)
    (root / "lib").mkdir(parents=True)
    musl = musl_dir()
    shutil.copy2(musl / "lib" / SONAME, root / "lib" / SONAME)
    os.symlink(SONAME, root / "lib" / LDSO_NAME)
    if case == "core":
        program = build_root() / "dyn_core"
    else:
        program = build_root() / "probe_pthread"
    try:
        proc = subprocess.run([str(qemu), "-L", str(root), str(program)],
                              capture_output=True, text=True, timeout=120)
        out = (proc.stdout or "") + (proc.stderr or "")
        print(f"[BOUNDARY] qemu-user case={case} rc={proc.returncode} "
              f"output={out.strip()[:400]!r}")
    except subprocess.TimeoutExpired:
        print(f"[BOUNDARY] qemu-user case={case} rc=124 (host timeout)")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--case", choices=("core", "probes"), default="core")
    parser.add_argument("--inject", choices=("interp", "symbol"),
                        help="evidence only: break the chain on purpose")
    parser.add_argument("--no-boot", action="store_true",
                        help="build the image and assert the ELFs, do not boot")
    parser.add_argument("--qemu-user", action="store_true",
                        help="also try the program under qemu-dadao (best effort)")
    args = parser.parse_args()
    if args.inject and args.case != "core":
        parser.error("--inject only applies to --case core")

    try:
        manifest = build_image(args.case, args.inject)
        if args.qemu_user:
            qemu_user_probe(args.case)
        if args.no_boot:
            print("make_ldso_image: PASS (image only)")
            return 0
        rc = kernel_config(image_cpio())
        if rc != 0:
            raise SetupError(f"kernel config slice did not apply (rc={rc})")
        timeout = INJECT_TIMEOUT if args.inject else BOOT_TIMEOUT
        try:
            rc = build_kernel()
            if rc != 0:
                raise SetupError(f"kernel build failed (rc={rc})")
            boot_rc, text, _cmd = boot(f"{args.case}-{args.inject or 'ok'}",
                                       timeout=timeout)
        finally:
            restore_k6_initramfs()
        checks = judge(args.case, manifest, boot_rc, text, args.inject)
        report_checks(checks, "boot")
        print(f"make_ldso_image: PASS ({args.case}"
              f"{'/' + args.inject if args.inject else ''})")
        return 0
    except SetupError as exc:
        print(f"make_ldso_image: SETUP ERROR: {exc}", file=sys.stderr)
        return 2
    except CheckError as exc:
        print(f"make_ldso_image: FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
