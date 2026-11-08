#!/usr/bin/env python3
"""qemu_gem5_shim.py -- translate the QEMU system CLI subset used by the test
drivers into a gem5 FS (`configs/dadao/fs.py`) invocation.

The shim exists so that the existing, unmodified test drivers can run against
gem5 FS without a second driver implementation: the driver keeps emitting the
QEMU argv it already emits, and this shim maps that argv onto gem5.

Supported QEMU subset (ADR-0048 D1/D2; task book §2):

  -M / -machine  dadao-tiny | dadao-vast[,bootrom-image=<path>]
  -bios <path>                     (Tiny flat BootROM)
  -kernel <path>                   (raw or ET_EXEC DADAO ELF)
  -semihosting-config enable=on,target=native[,chardev=<id>][,arg=<s>...]
  -chardev file,id=<id>,path=<host-file>[,input-path=<ignored>]
  -nographic / -display none / -monitor none / -serial none
  -d cpu -D <log>                  -> --trace-cpu <log> (QEMU-compatible dump)
  -dfilter <base+size,...>         post-filter the gem5 dump blocks to the same
                                   PC windows, so the probe's "last block"
                                   observation is byte-for-byte the QEMU one

Everything else -- including `-qmp`, `-S`, `-s` and any option without a gem5
FS equivalent -- is rejected with exit code 2.  Nothing is silently dropped: `-chardev …,input-path=P` is wired
to the gem5 process stdin so `SYS_READC` sees the same bytes as QEMU.

Engine selection (environment, set by the parity driver):

  PARITY_GEM5         gem5.opt path (default .work/source/gem5/build/DADAO/gem5.opt)
  PARITY_GEM5_CONFIG  fs.py path (default .work/source/gem5/configs/dadao/fs.py)
  PARITY_GEM5_PROFILE default profile when -machine omits `profile=` (tiny)
  PARITY_GEM5_BOOTROM default BootROM when -machine omits `bootrom-image=`
  PARITY_WORK_ROOT    root for the per-run gem5 --outdir (default /tmp/opencode/qemu-gem5-parity/shim)

Exit status is the gem5 FS guest exit code.  A non-guest gem5 stop is reported
as 125 (`fs.py` NON_GUEST_EXIT); a shim usage error is 2.
"""

from __future__ import annotations

import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile

USAGE = """usage: qemu_gem5_shim.py [QEMU system argv subset]
  -M|-machine dadao-tiny | dadao-vast[,bootrom-image=PATH]
  -bios PATH | -kernel PATH
  -semihosting-config enable=on,target=native[,chardev=ID][,arg=S]...
  -chardev file,id=ID,path=PATH[,input-path=PATH]
  -nographic | -display none | -monitor none | -serial none
  -d cpu -D LOG
Unsupported (exit 2): -qmp -S -s, unknown options, unknown machine
properties, semihosting target != native, debug items other than `cpu`.
"""

SHIM_ERROR = 2
NON_GUEST_EXIT = 125


class ShimError(Exception):
    """Unsupported / malformed QEMU argv (exit code 2)."""


def _repo_root() -> str:
    return os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))


def _default(path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(_repo_root(), path)


def _split_kv(value: str, what: str) -> list[tuple[str, str]]:
    items = []
    for chunk in value.split(","):
        if not chunk:
            continue
        if "=" in chunk:
            key, val = chunk.split("=", 1)
        else:
            key, val = chunk, ""
        items.append((key.strip(), val))
    if not items:
        raise ShimError(f"{what}: empty value")
    return items


# M12 (`spec/Machine-v5 §1`): the profile is fixed by the machine name; the
# two machines are separate `-M` entries (no `profile=` property).
FIXED_MACHINES = {"dadao-tiny": "tiny", "dadao-vast": "vast"}
# `node` is the pre-M12 spelling of the Vast profile; accepted as an alias
# (environment / legacy callers) until m12-integ-001, never returned.
PROFILE_ALIASES = {"node": "vast"}


def parse_machine(value: str) -> tuple[str | None, str | None, str | None]:
    """Return (profile, bootrom, machine) from `-M/-machine`.

    `machine` is returned only for callers that need the identity; the shim
    accepts `dadao-tiny` and `dadao-vast`.  The profile is implied by the
    machine name, so `profile=` is rejected (the machines are separate types).
    """
    parts = _split_kv(value, "-machine")
    machine = parts[0][0]
    if machine not in FIXED_MACHINES:
        raise ShimError(
            f"-machine: unsupported machine {machine!r} (dadao-tiny or "
            f"dadao-vast)")
    bootrom = None
    for key, val in parts[1:]:
        if key == "bootrom-image":
            bootrom = val
        elif key == "profile":
            raise ShimError(
                f"-machine: {machine} has a fixed profile; drop `profile=` "
                f"(got {val!r})")
        else:
            raise ShimError(f"-machine: unsupported property {key!r}")
    return FIXED_MACHINES[machine], bootrom, machine


def parse_semihosting(value: str) -> dict:
    out = {"enable": "on", "target": "native", "chardev": None, "args": []}
    for key, val in _split_kv(value, "-semihosting-config"):
        if key == "enable":
            if val not in ("on", "off"):
                raise ShimError(f"-semihosting-config: enable={val!r}")
            out["enable"] = val
        elif key == "target":
            if val != "native":
                raise ShimError(
                    f"-semihosting-config: target={val!r} unsupported "
                    f"(only native)")
            out["target"] = val
        elif key == "chardev":
            out["chardev"] = val
        elif key == "arg":
            out["args"].append(val)
        else:
            raise ShimError(f"-semihosting-config: unsupported key {key!r}")
    return out


def parse_chardev(value: str) -> dict:
    out = {"backend": None, "id": None, "path": None, "input_path": None}
    for i, (key, val) in enumerate(_split_kv(value, "-chardev")):
        if i == 0:
            out["backend"] = key
            if val:
                raise ShimError(f"-chardev: malformed backend {key}={val}")
        elif key == "id":
            out["id"] = val
        elif key == "path":
            out["path"] = val
        elif key == "input-path":
            # gem5 FS has no console-input channel.  Explicitly reported, not
            # silently honoured; the READC probe checks must show the gap.
            out["input_path"] = val
        else:
            raise ShimError(f"-chardev: unsupported key {key!r}")
    if out["backend"] != "file":
        raise ShimError(f"-chardev: unsupported backend {out['backend']!r} "
                        f"(only file)")
    if not out["id"] or not out["path"]:
        raise ShimError("-chardev file: id= and path= are required")
    return out


def parse(argv: list[str]) -> dict:
    cfg = {
        "profile": None,
        "bootrom": None,
        "kernel": None,
        "semihost": None,
        "console": None,
        "trace": None,
        "debug_cpu": False,
        "dfilter": [],
        "input_path": None,
    }
    i = 0
    n = len(argv)
    while i < n:
        arg = argv[i]
        if arg in ("-M", "-machine"):
            if i + 1 >= n:
                raise ShimError(f"{arg}: missing value")
            prof, boot, _m = parse_machine(argv[i + 1])
            if cfg["profile"] is not None and prof is not None \
                    and cfg["profile"] != prof:
                raise ShimError("conflicting --profile values")
            cfg["profile"] = prof or cfg["profile"]
            cfg["bootrom"] = boot or cfg["bootrom"]
            i += 2
        elif arg == "-bios":
            if i + 1 >= n:
                raise ShimError("-bios: missing value")
            if cfg["bootrom"] and cfg["bootrom"] != argv[i + 1]:
                raise ShimError("-bios conflicts with -machine bootrom-image")
            cfg["bootrom"] = argv[i + 1]
            i += 2
        elif arg == "-kernel":
            if i + 1 >= n:
                raise ShimError("-kernel: missing value")
            cfg["kernel"] = argv[i + 1]
            i += 2
        elif arg == "-semihosting-config":
            if i + 1 >= n:
                raise ShimError("-semihosting-config: missing value")
            cfg["semihost"] = parse_semihosting(argv[i + 1])
            i += 2
        elif arg == "-chardev":
            if i + 1 >= n:
                raise ShimError("-chardev: missing value")
            ch = parse_chardev(argv[i + 1])
            cfg["console"] = ch["path"]
            if ch["input_path"]:
                cfg["input_path"] = ch["input_path"]
            i += 2
        elif arg in ("-nographic", "-display", "-monitor", "-serial"):
            # `-display/-monitor/-serial` take a value; only `none` accepted.
            if arg == "-nographic":
                i += 1
                continue
            if i + 1 >= n:
                raise ShimError(f"{arg}: missing value")
            if argv[i + 1] not in ("none",):
                raise ShimError(f"{arg} {argv[i + 1]!r}: unsupported "
                                f"(only none)")
            i += 2
        elif arg == "-dfilter":
            if i + 1 >= n:
                raise ShimError("-dfilter: missing value")
            cfg["dfilter"] = _parse_dfilter(argv[i + 1])
            i += 2
        elif arg == "-d":
            if i + 1 >= n:
                raise ShimError("-d: missing value")
            items = [x for x in argv[i + 1].split(",") if x]
            if items != ["cpu"]:
                raise ShimError(f"-d {argv[i + 1]!r}: unsupported debug items "
                                f"(only cpu)")
            cfg["debug_cpu"] = True
            i += 2
        elif arg == "-D":
            if i + 1 >= n:
                raise ShimError("-D: missing value")
            cfg["trace"] = argv[i + 1]
            i += 2
        elif arg in ("-qmp", "-S", "-s"):
            raise ShimError(f"{arg}: no gem5 FS equivalent")
        elif arg.startswith("-"):
            raise ShimError(f"unsupported option {arg!r}")
        else:
            raise ShimError(f"unexpected positional argument {arg!r}")
    if cfg["debug_cpu"] != (cfg["trace"] is not None):
        raise ShimError("-d cpu and -D must be given together")
    return cfg


def build_gem5_argv(cfg: dict, outdir: str, gem5: str, config: str) -> list[str]:
    profile = cfg["profile"] or os.environ.get("PARITY_GEM5_PROFILE", "tiny")
    profile = PROFILE_ALIASES.get(profile, profile)
    if profile not in ("tiny", "vast"):
        raise ShimError(f"profile {profile!r} unsupported")
    bootrom = cfg["bootrom"] or os.environ.get("PARITY_GEM5_BOOTROM")
    if bootrom is None and profile == "vast":
        raise ShimError("vast profile requires a BootROM (-machine "
                        "bootrom-image=... or PARITY_GEM5_BOOTROM)")
    argv = [gem5, "--outdir", outdir, config, "--profile", profile]
    if bootrom:
        argv += ["--bootrom", bootrom]
    if cfg["kernel"]:
        argv += ["--kernel", cfg["kernel"]]
    semi = cfg["semihost"] or {"enable": "on", "target": "native",
                               "chardev": None, "args": []}
    argv += ["--semihost", semi["enable"], "--semihost-system", "native"]
    for value in semi["args"]:
        argv += ["--semihost-arg", value]
    if cfg["console"]:
        argv += ["--console-out", cfg["console"]]
    if cfg["trace"]:
        argv += ["--trace-cpu", cfg["trace"]]
    return argv


def _parse_dfilter(value: str) -> list[tuple[int, int]]:
    """Parse QEMU `-dfilter` windows (`0xBASE+0xSIZE,...`).

    The probes only use the `+` form (see min_rom_probe_integ046t.dfilter).
    Anything else is an explicit usage error rather than a silent no-op.
    """
    windows = []
    for chunk in value.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        m = re.fullmatch(r"(0[xX][0-9a-fA-F]+)\+(0[xX][0-9a-fA-F]+)", chunk)
        if not m:
            raise ShimError(f"-dfilter: unsupported window {chunk!r} "
                            f"(only 0xBASE+0xSIZE)")
        base, size = int(m.group(1), 16), int(m.group(2), 16)
        if size <= 0:
            raise ShimError(f"-dfilter: zero-size window {chunk!r}")
        windows.append((base, size))
    if not windows:
        raise ShimError("-dfilter: empty window list")
    return windows


def _filter_trace(path: str, windows: list[tuple[int, int]]) -> None:
    """Keep only dump blocks whose PC lies in one of ``windows``.

    QEMU's `-dfilter` is an observation filter, not guest semantics.  gem5
    always emits the full trace, so reproducing the filter here is what makes
    the probes' "last block" observation identical on both engines.
    """
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except OSError:
        return
    blocks = []
    current = None
    for line in lines:
        if line.startswith("PC: "):
            if current is not None:
                blocks.append(current)
            current = [line]
        elif current is not None:
            current.append(line)
        # preamble before the first "PC: " is dropped (QEMU does the same)
    if current is not None:
        blocks.append(current)

    def keep(block):
        try:
            pc = int(block[0][4:].strip(), 16)
        except ValueError:
            return False
        return any(base <= pc < base + size for base, size in windows)

    kept = [b for b in blocks if keep(b)]
    with open(path, "w", encoding="utf-8") as fh:
        for block in kept:
            fh.writelines(block)


def _terminate(child: subprocess.Popen) -> None:
    if child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()


def run(argv: list[str]) -> int:
    cfg = parse(argv)
    gem5 = _default(os.environ.get(
        "PARITY_GEM5", ".work/source/gem5/build/DADAO/gem5.opt"))
    config = _default(os.environ.get(
        "PARITY_GEM5_CONFIG", ".work/source/gem5/configs/dadao/fs.py"))
    for path, what in ((gem5, "gem5.opt"), (config, "fs.py")):
        if not os.path.isfile(path):
            print(f"qemu_gem5_shim: ERROR: {what} not found: {path}",
                  file=sys.stderr)
            return SHIM_ERROR
    root = os.environ.get("PARITY_WORK_ROOT", "/tmp/opencode/qemu-gem5-parity/shim")
    os.makedirs(root, exist_ok=True)
    outdir = tempfile.mkdtemp(prefix="gem5-", dir=root)
    cmd = build_gem5_argv(cfg, outdir, gem5, config)
    if cfg["semihost"] and cfg["semihost"]["chardev"]:
        # Only the `semi` chardev is meaningful in the drivers; any other id is
        # still a file chardev and maps to the same console sink.
        pass
    if cfg["console"] and cfg["semihost"] and cfg["semihost"]["chardev"] is None:
        # QEMU would attach the console chardev only if semihosting points at
        # it; the drivers always point at `semi`, so this only happens on an
        # explicitly malformed argv.
        print("qemu_gem5_shim: WARNING: -chardev without "
              "-semihosting-config chardev=; console mapped anyway",
              file=sys.stderr)
    if cfg.get("input_path"):
        print("qemu_gem5_shim: NOTE: -chardev input-path is connected to gem5 "
              "stdin (SYS_READC reads it, matching QEMU chardev file input)",
              file=sys.stderr)
    stdin_fh = None
    if cfg.get("input_path"):
        try:
            stdin_fh = open(cfg["input_path"], "rb")
        except OSError as exc:
            print(f"qemu_gem5_shim: ERROR: cannot open input-path "
                  f"{cfg['input_path']}: {exc}", file=sys.stderr)
            shutil.rmtree(outdir, ignore_errors=True)
            return SHIM_ERROR
    try:
        ch = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              stdin=stdin_fh if stdin_fh is not None
                              else subprocess.DEVNULL)
    except OSError as exc:
        print(f"qemu_gem5_shim: ERROR: cannot start gem5: {exc}",
              file=sys.stderr)
        shutil.rmtree(outdir, ignore_errors=True)
        if stdin_fh is not None:
            stdin_fh.close()
        return SHIM_ERROR

    previous = {}

    def _handler(signum, _frame):
        _terminate(ch)
        raise SystemExit(128 + signum)

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            previous[sig] = signal.signal(sig, _handler)
        except (ValueError, OSError):
            pass
    try:
        stdout, stderr = ch.communicate()
    finally:
        if stdin_fh is not None:
            stdin_fh.close()
        for sig, handler in previous.items():
            try:
                signal.signal(sig, handler)
            except (ValueError, OSError):
                pass
    sys.stdout.buffer.write(stdout)
    sys.stdout.buffer.flush()
    text = stderr.decode("utf-8", errors="replace")
    sys.stderr.write(text)
    sys.stderr.flush()

    rc = ch.returncode
    guest = re.search(r"^GEM5_EXIT_CAUSE=", text, re.MULTILINE) is not None
    if not guest:
        # gem5 did not reach a guest exit (setup/fatal/non-guest stop).  Never
        # let that masquerade as a guest failure code.
        print(f"qemu_gem5_shim: ERROR: gem5 ended without a guest exit "
              f"(rc={rc}); outdir kept at {outdir}", file=sys.stderr)
        return NON_GUEST_EXIT
    if cfg["dfilter"] and cfg["trace"]:
        _filter_trace(cfg["trace"], cfg["dfilter"])
    shutil.rmtree(outdir, ignore_errors=True)
    return rc & 0xFF


def main() -> int:
    argv = sys.argv[1:]
    if not argv or argv in (["-h"], ["--help"]):
        print(USAGE)
        return 0 if argv else SHIM_ERROR
    try:
        return run(argv)
    except ShimError as exc:
        print(f"qemu_gem5_shim: ERROR: {exc}", file=sys.stderr)
        print(USAGE, file=sys.stderr)
        return SHIM_ERROR


if __name__ == "__main__":
    sys.exit(main())
