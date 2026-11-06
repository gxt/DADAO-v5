#!/usr/bin/env python3
"""gem5 syscall-emulation run path for the tset drivers (GEM5-021t).

The tset drivers (``tset/libc-test``, ``tset/llvm-ts``, ``tset/embench``) own
their corpus enumeration, build lines and oracles.  This module only swaps the
*engine* that runs an already-built static ELF:

    qemu  : ``qemu-dadao <elf>``                      (QEMU user mode)
    gem5-se: ``gem5.opt --outdir <d> <se.py> --binary <elf> [--args ...]``

Nothing here decides a case's expected value -- the expectation still comes
from the corpus (the case's own t_status / verify_benchmark / reference
output).  The module only answers "could the SE platform run this image, and
if not, which capability stopped it".

gem5 SE is deliberately narrower than qemu-user (GEM5-014t):

* **static ET_EXEC only**: the SE loader rejects ``ET_DYN`` (static PIE /
  shared object) and any image carrying ``PT_INTERP`` (ADR-0048 D4, static
  first).  Such an image is reported ``BLOCKED`` from the ELF facts, without
  starting gem5;
* **the implemented syscall set only**: an unimplemented number is a gem5
  ``fatal`` (``DADAO SE: syscall N not implemented``), i.e. host-side
  evidence that the case never reached its own verdict -> ``BLOCKED``, never
  ``PASS`` and never a ``FAIL`` of the case;
* a non-guest simulation end (``--max-insts``, panic) is not a guest status:
  the configuration script exits 125 and the driver must not read that as the
  guest's code.

All host-side products (m5out, guest stdout/stderr, the simulator log) live
under the caller's per-case runtime directory; none of them is written into
the repository.
"""

from __future__ import annotations

import os
import re
import shlex
import shutil
import struct
import subprocess
import sys
import time

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:                                     # reap gem5 children on external signals
    import proc_reap                     # noqa: E402
except ImportError:                      # pragma: no cover - always present
    proc_reap = None

# Defaults follow the other drivers: a repo-relative runtime location, never an
# absolute host path (the component source tree is built by `make build-gem5`).
DEFAULT_GEM5 = ".work/source/gem5/build/DADAO/gem5.opt"
DEFAULT_SE_CONFIG = ".work/source/gem5/configs/dadao/se.py"
DEFAULT_MUSL = ".work/source/musl"

ENGINES = ("qemu", "gem5-se")

EXIT_CAUSE_GUEST = "exiting with last active thread context"
NON_GUEST_EXIT = 125

ELF_MAGIC = b"\x7fELF"
ELFCLASS64, ELFDATA2MSB = 2, 2
ET_EXEC, ET_DYN = 2, 3
PT_LOAD, PT_INTERP = 1, 3

_SYSCALL_FATAL_RE = re.compile(
    r"DADAO SE: syscall (\d+) not implemented(?: \(pc=([^)]*)\))?")
_FATAL_RE = re.compile(r"^\s*(?:\S+:\d+: )?fatal: (.*)$", re.MULTILINE)
_MAX_INSTS_RE = re.compile(r"max_insts", re.IGNORECASE)

# Capability buckets for the gap inventory.  The key is the *guest* syscall
# name as defined by the locked musl port
# (`arch/dadao/bits/syscall.h.in`); an unknown number falls into "other".
_SYSCALL_CAPABILITY = {
    "brk": "heap/VMA (brk)",
    "mmap": "heap/VMA (mmap)",
    "munmap": "heap/VMA (munmap)",
    "mremap": "heap/VMA (mremap)",
    "madvise": "heap/VMA (madvise)",
    "shmat": "SysV IPC",
    "shmdt": "SysV IPC",
    "shmget": "SysV IPC",
    "shmctl": "SysV IPC",
    "msgget": "SysV IPC",
    "msgsnd": "SysV IPC",
    "msgrcv": "SysV IPC",
    "msgctl": "SysV IPC",
    "semget": "SysV IPC",
    "semop": "SysV IPC",
    "semctl": "SysV IPC",
    "clone": "threads/futex",
    "clone3": "threads/futex",
    "futex": "threads/futex",
    "set_robust_list": "threads/futex",
    "get_robust_list": "threads/futex",
    "rseq": "threads/futex",
    "rt_sigaction": "signals",
    "rt_sigprocmask": "signals",
    "rt_sigreturn": "signals",
    "sigaltstack": "signals",
    "kill": "signals",
    "tkill": "signals",
    "tgkill": "signals",
    "openat": "file I/O",
    "openat2": "file I/O",
    "open": "file I/O",
    "read": "file I/O",
    "pread64": "file I/O",
    "write": "console/stdout (implemented)",
    "writev": "console/stdout (implemented)",
    "lseek": "file I/O",
    "close": "file I/O",
    "fstat": "file I/O",
    "newfstatat": "file I/O",
    "statx": "file I/O",
    "getdents64": "file I/O",
    "readlinkat": "file I/O",
    "access": "file I/O",
    "unlinkat": "file I/O",
    "mkdirat": "file I/O",
    "ioctl": "console/stdout (implemented)",
    "clock_gettime": "time/clocks",
    "gettimeofday": "time/clocks",
    "clock_nanosleep": "time/clocks",
    "nanosleep": "time/clocks",
    "times": "time/clocks",
    "getitimer": "time/clocks",
    "setitimer": "time/clocks",
    "set_tid_address": "process startup (implemented)",
    "set_tls": "process startup (implemented)",
    "exit": "process startup (implemented)",
    "exit_group": "process startup (implemented)",
    "getpid": "process info",
    "getppid": "process info",
    "gettid": "process info",
    "getuid": "process info",
    "geteuid": "process info",
    "getgid": "process info",
    "getegid": "process info",
    "uname": "process info",
    "getcwd": "process info",
    "pipe": "IPC/socket/pipe",
    "pipe2": "IPC/socket/pipe",
    "socket": "IPC/socket/pipe",
    "socketpair": "IPC/socket/pipe",
    "bind": "IPC/socket/pipe",
    "connect": "IPC/socket/pipe",
    "listen": "IPC/socket/pipe",
    "accept": "IPC/socket/pipe",
    "accept4": "IPC/socket/pipe",
    "sendto": "IPC/socket/pipe",
    "recvfrom": "IPC/socket/pipe",
    "sendmsg": "IPC/socket/pipe",
    "recvmsg": "IPC/socket/pipe",
    "shutdown": "IPC/socket/pipe",
    "setsockopt": "IPC/socket/pipe",
    "getsockopt": "IPC/socket/pipe",
    "getsockname": "IPC/socket/pipe",
    "getpeername": "IPC/socket/pipe",
    "execve": "process creation/exec",
    "execveat": "process creation/exec",
    "fork": "process creation/exec",
    "vfork": "process creation/exec",
    "wait4": "process creation/exec",
    "waitid": "process creation/exec",
    "killpg": "process creation/exec",
    "prlimit64": "resource limits",
    "getrlimit": "resource limits",
    "setrlimit": "resource limits",
    "utimensat": "file I/O",
    "utimes": "file I/O",
    "futimesat": "file I/O",
    "statfs": "file I/O",
    "fstatfs": "file I/O",
    "dup": "file I/O",
    "dup3": "file I/O",
    "fcntl": "file I/O",
    "fsync": "file I/O",
    "fdatasync": "file I/O",
    "getdents": "file I/O",
    "chdir": "file I/O",
    "fchdir": "file I/O",
    "mkdir": "file I/O",
    "mkdirat": "file I/O",
    "rmdir": "file I/O",
    "rename": "file I/O",
    "renameat": "file I/O",
    "chmod": "file I/O",
    "fchmod": "file I/O",
    "chown": "file I/O",
    "fchown": "file I/O",
    "umask": "file I/O",
    "readlink": "file I/O",
    "symlinkat": "file I/O",
    "getrandom": "random",
    "sched_getaffinity": "scheduling",
    "sched_setaffinity": "scheduling",
    "setpriority": "scheduling",
    "getpriority": "scheduling",
    "arch_prctl": "process startup/TLS",
    "prctl": "process info",
    "sysinfo": "process info",
}
_CAPABILITY_OTHER = "other"


# ---------------------------------------------------------------------------
# engine / path helpers
# ---------------------------------------------------------------------------
def abspath(path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(_REPO_ROOT, path)


def default_gem5() -> str:
    return abspath(os.environ.get("GEM5_SE_BIN") or DEFAULT_GEM5)


def default_se_config() -> str:
    return abspath(os.environ.get("GEM5_SE_CONFIG") or DEFAULT_SE_CONFIG)


def syscall_names(musl_root: str):
    """``{number: name}`` from the locked musl port's syscall header.

    Parsed live from ``<musl>/arch/dadao/bits/syscall.h.in`` (the port's own
    ``#define __NR_<name> <n>`` lines); a missing tree yields an empty map so a
    gap report degrades to the bare number instead of guessing a name.
    """
    path = os.path.join(musl_root, "arch", "dadao", "bits", "syscall.h.in")
    names = {}
    try:
        with open(path, "r", errors="replace") as fh:
            for line in fh:
                m = re.match(r"#define\s+__NR_(\w+)\s+(\d+)\s*$", line)
                if m:
                    names.setdefault(int(m.group(2)), m.group(1))
    except OSError:
        return {}
    return names


def capability_for(nr, names):
    name = names.get(nr)
    if not name:
        return _CAPABILITY_OTHER
    return _SYSCALL_CAPABILITY.get(name, _CAPABILITY_OTHER)


# ---------------------------------------------------------------------------
# ELF facts (independent of gem5 / qemu)
# ---------------------------------------------------------------------------
def elf_header(path: str):
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:4] != ELF_MAGIC:
        raise ValueError(f"{path}: not an ELF file")
    if data[4] != ELFCLASS64 or data[5] != ELFDATA2MSB:
        raise ValueError(f"{path}: expected ELFCLASS64/ELFDATA2MSB, got "
                         f"class={data[4]} data={data[5]}")
    (e_type,) = struct.unpack_from(">H", data, 16)
    (e_phoff,) = struct.unpack_from(">Q", data, 32)
    (e_phentsize, e_phnum) = struct.unpack_from(">HH", data, 54)
    phdrs = []
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        p_type, _flags, p_offset, p_vaddr, _paddr, p_filesz, _memsz, _align = \
            struct.unpack_from(">IIQQQQQQ", data, off)
        phdrs.append(dict(type=p_type, offset=p_offset, vaddr=p_vaddr,
                          filesz=p_filesz))
        if p_type == PT_INTERP:
            phdrs[-1]["interp"] = data[p_offset:p_offset + p_filesz]
    return dict(e_type=e_type, phdrs=phdrs)


def static_gate(path: str):
    """Return a BLOCKED reason when the image is not a static ``ET_EXEC``.

    This is the driver-level statement of the SE loader's own rule
    (GEM5-014t §4): ``ET_DYN`` and ``PT_INTERP`` are refused, not silently
    attempted.  ``None`` means "the SE engine may run it".
    """
    try:
        hdr = elf_header(path)
    except (OSError, ValueError) as exc:
        return f"not a loadable DADAO ELF: {exc}"
    if hdr["e_type"] == ET_DYN:
        return ("ET_DYN (static PIE / shared object): gem5 SE loads only "
                "ET_EXEC (GEM5-014t §4)")
    if hdr["e_type"] != ET_EXEC:
        return (f"e_type={hdr['e_type']}: gem5 SE loads only ET_EXEC "
                f"(GEM5-014t §4)")
    for ph in hdr["phdrs"]:
        if ph["type"] == PT_INTERP:
            interp = ph.get("interp", b"").decode("utf-8", "replace").rstrip("\0")
            return (f"PT_INTERP {interp!r}: dynamic linking is not modelled "
                    f"by gem5 SE (ADR-0048 D4 static first)")
    return None


# ---------------------------------------------------------------------------
# running
# ---------------------------------------------------------------------------
def _read_bytes(path: str) -> bytes:
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except OSError:
        return b""


def run_gem5_se(elf, outdir, *, gem5, config, timeout, argv=(),
                stdin_path=None, cwd=None, max_insts=0):
    """Run one ELF on gem5 SE; return the raw observation dict.

    Guest fd 1/2 are redirected to files inside ``outdir`` (the simulator's
    own banner would otherwise be mixed into guest stdout), so a case that
    writes nothing is distinguishable from a case that never ran.
    """
    os.makedirs(outdir, exist_ok=True)
    m5out = os.path.join(outdir, "m5out")
    guest_out = os.path.join(outdir, "guest.stdout")
    guest_err = os.path.join(outdir, "guest.stderr")
    sim_log = os.path.join(outdir, "sim.log")
    shutil.rmtree(m5out, ignore_errors=True)
    for path in (guest_out, guest_err, sim_log):
        if os.path.exists(path):
            try:
                os.unlink(path)
            except OSError:
                pass

    cmd = [gem5, "--outdir", m5out, config, "--binary", elf,
           "--guest-stdout", guest_out, "--guest-stderr", guest_err,
           "--guest-stdin", stdin_path or os.devnull]
    if argv:
        cmd += ["--args", " ".join(shlex.quote(a) for a in argv)]
    if cwd:
        cmd += ["--cwd", cwd]
    if max_insts:
        cmd += ["--max-insts", str(max_insts)]

    timed_out = False
    rc = None
    started = time.monotonic()
    with open(sim_log, "wb") as log:
        try:
            if proc_reap is not None:
                proc = proc_reap.run_tracked(cmd, timeout=timeout,
                                             stdout=log, stderr=subprocess.STDOUT,
                                             stdin=subprocess.DEVNULL)
            else:                        # pragma: no cover
                proc = subprocess.run(cmd, stdout=log,
                                      stderr=subprocess.STDOUT,
                                      stdin=subprocess.DEVNULL, timeout=timeout)
            rc = proc.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
    seconds = time.monotonic() - started

    log_text = _read_bytes(sim_log).decode("utf-8", "replace")
    exit_cause = None
    m = re.search(r"^GEM5_EXIT_CAUSE=(.*)$", log_text, re.MULTILINE)
    if m:
        exit_cause = m.group(1).strip()
    non_guest = (exit_cause != EXIT_CAUSE_GUEST) or (rc == NON_GUEST_EXIT)

    return dict(elf=elf, cmd=cmd, rc=rc, timed_out=timed_out,
                seconds=round(seconds, 2), m5out=m5out, sim_log=sim_log,
                stdout=_read_bytes(guest_out), stderr=_read_bytes(guest_err),
                sim_text=log_text, exit_cause=exit_cause,
                non_guest=bool(non_guest))


def gap_evidence(run, musl_root):
    """Root-cause evidence for a run that never reached the guest's verdict.

    Returns ``dict(capability, evidence, syscall, syscall_name)`` or ``None``.
    """
    names = syscall_names(musl_root)
    m = _SYSCALL_FATAL_RE.search(run.get("sim_text") or "")
    if m:
        nr = int(m.group(1))
        name = names.get(nr)
        label = f"{nr} ({name})" if name else str(nr)
        pc = f", pc={m.group(2)}" if m.group(2) else ""
        return dict(
            capability=capability_for(nr, names),
            kind="syscall-not-implemented",
            syscall=nr,
            syscall_name=name,
            evidence=(f"gem5 fatal: DADAO SE: syscall {label} not implemented"
                      f"{pc}"),
        )
    m = _FATAL_RE.search(run.get("sim_text") or "")
    if m:
        line = m.group(0).strip()
        kind = "max-insts" if _MAX_INSTS_RE.search(line) else "gem5-fatal"
        return dict(capability=("simulator limit" if kind == "max-insts"
                                else "simulator/loader"),
                    kind=kind, syscall=None, syscall_name=None,
                    evidence=line)
    return None


def evaluate(elf, outdir, *, gem5, config, timeout, musl_root, argv=(),
             stdin_path=None, cwd=None, max_insts=0):
    """Run the SE path and normalise the outcome.

    Returned dict:

    * ``status``  ``"BLOCKED"`` when the platform (not the case) stopped it,
                  else ``None`` -- the caller applies the corpus oracle;
    * ``exit``    the guest exit status when the guest really exited;
    * ``reason``  human-readable evidence for a BLOCKED status;
    * ``gap``     the capability bucket (see :func:`gap_evidence`);
    * ``stdout``/``stderr`` bytes captured by the SE platform.
    """
    result = dict(status=None, exit=None, reason="", gap=None,
                  stdout=b"", stderr=b"", seconds=0.0, cmd=[],
                  sim_log=None, m5out=None, timed_out=False,
                  exit_cause=None)
    gate = static_gate(elf)
    if gate:
        result.update(status="BLOCKED", reason=gate,
                      gap=dict(capability="loader/ELF modality",
                               kind="elf-modality", syscall=None,
                               syscall_name=None, evidence=gate))
        return result

    run = run_gem5_se(elf, outdir, gem5=gem5, config=config, timeout=timeout,
                      argv=argv, stdin_path=stdin_path, cwd=cwd,
                      max_insts=max_insts)
    result.update(stdout=run["stdout"], stderr=run["stderr"],
                  seconds=run["seconds"], cmd=run["cmd"],
                  sim_log=run["sim_log"], m5out=run["m5out"],
                  timed_out=run["timed_out"], exit_cause=run["exit_cause"])
    if run["timed_out"]:
        result.update(status="BLOCKED",
                      reason=f"timeout after {timeout}s (SE, not a verdict)",
                      gap=dict(capability="time budget",
                               kind="timeout", syscall=None,
                               syscall_name=None,
                               evidence=f"no guest exit within {timeout}s"))
        return result
    if run["rc"] is None:
        result.update(status="BLOCKED",
                      reason="gem5 did not return an exit code",
                      gap=dict(capability="simulator/loader",
                               kind="no-exit-code", syscall=None,
                               syscall_name=None,
                               evidence="gem5 exited without an exit status"))
        return result
    gap = gap_evidence(run, musl_root)
    if gap:
        result.update(status="BLOCKED", reason=gap["evidence"], gap=gap)
        return result
    if run["non_guest"]:
        cause = run["exit_cause"] or "(no GEM5_EXIT_CAUSE)"
        result.update(
            status="BLOCKED",
            reason=(f"non-guest simulation end ({cause}), rc={run['rc']}: "
                    f"not a guest status"),
            gap=dict(capability="simulator/loader", kind="non-guest-exit",
                     syscall=None, syscall_name=None,
                     evidence=f"EXIT_CAUSE={cause} rc={run['rc']}"))
        return result
    result.update(exit=run["rc"])
    return result
