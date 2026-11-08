#!/usr/bin/env python3
"""Cross-engine chmod-family probe (GEM5-031t).

``chmod_probe.c`` asserts the guest's file-permission rules (``chmod`` through
musl's ``fchmodat``, ``fchmod``, the legacy ``fchmodat``, and ``fchmodat2``
with ``AT_SYMLINK_NOFOLLOW`` / ``AT_EMPTY_PATH``) and prints one line per
assertion.  This driver builds the probe, runs it three ways, and requires every
engine to reproduce the *host*'s lines:

    host     cc + the host kernel -- the oracle (this really is Linux)
    gem5-se  gem5 SE, no redirect (guest paths are host paths)
    qemu     qemu-user, no -L (same view as the host)

Every engine gets its own tree under the work directory: the cases change
modes, so a shared tree would leak one engine's writes into the next.  The
probe's expectations are the constants in its source; this driver never decides
a value, it only diffs the engines against the host and re-checks that each run
ended with ``SUMMARY fails=0``.

Exit status: 0 only when every check passes; 2 on a setup error.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")))
sys.path.insert(0, str(REPO_ROOT / "tools" / "infra"))
import paths as _paths  # noqa: E402

PROBE = Path(__file__).resolve().parent / "chmod_probe.c"

DEFAULT_WORK_DIR = str(_paths.test_artifacts_dir() / "se-chmod")
DEFAULT_MUSL = ".work/source/musl"
DEFAULT_GEM5 = ".work/source/gem5/build/DADAO/gem5.opt"
DEFAULT_SE = ".work/source/gem5/configs/dadao/se.py"
DEFAULT_CLANG = ".dadao/cross-toolchain/bin/clang"
DEFAULT_LDL = ".dadao/cross-toolchain/bin/ld.lld"
DEFAULT_QEMU = ".dadao/cross-toolchain/bin/qemu-dadao"
BUILTINS = (
    ".dadao/cross-toolchain/lib/clang/23/lib/"
    "dadao-unknown-unknown-elf/libclang_rt.builtins.a",
    ".dadao/cross-toolchain/lib/clang/23/lib/"
    "dadao-unknown-unknown-linux/libclang_rt.builtins.a",
)

ASSERTION_RE = re.compile(r"^(PASS|FAIL|SKIP) (\S+) ")
SUMMARY_RE = re.compile(r"^SUMMARY fails=(\d+)$", re.MULTILINE)
# Top-level assertion call sites in the probe source (the live floor for the
# coverage check: an engine may not report fewer lines than the source asserts).
CALL_RE = re.compile(r"^\s+(?:CHECK_RC|check_mode|check_lmode)\(",
                     re.MULTILINE)

failures = 0
checks = 0
floor = 0


class SetupError(RuntimeError):
    pass


def check(name: str, expected, actual) -> None:
    global failures, checks
    checks += 1
    ok = expected == actual
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: "
          f"expected={expected} actual={actual}")
    if not ok:
        failures += 1


def resolve(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else REPO_ROOT / p


def run(cmd: list[str], cwd: Path | None, out: Path, err: Path,
        timeout: int) -> int:
    """Run cmd; return its own exit code (None on timeout -> -1)."""
    with out.open("wb") as stdout, err.open("wb") as stderr:
        try:
            proc = subprocess.run(cmd, cwd=cwd, stdout=stdout, stderr=stderr,
                                  timeout=timeout)
        except subprocess.TimeoutExpired:
            return -1
    return proc.returncode


def make_tree(base: Path, name: str) -> Path:
    """One engine's playground.  The symlinks are created here, not by the
    probe: a guest may not have symlinkat(), and the probe only has to chmod
    through them.  A previous run's tree is removed first (re-runs reuse the
    work directory)."""
    tree = base / name
    shutil.rmtree(tree, ignore_errors=True)
    (tree / "d").mkdir(parents=True, exist_ok=True)
    (tree / "f").write_text("F")
    (tree / "f").chmod(0o644)
    for link, target in (("l", "f"), ("dang", "missing"), ("a", "b"),
                         ("b", "a")):
        os.symlink(target, tree / link)
    return tree


def shared(out: Path) -> list[str]:
    """The assertion lines of one run, in order."""
    if not out.exists():
        return []
    lines = []
    for line in out.read_text(errors="replace").splitlines():
        if ASSERTION_RE.match(line):
            lines.append(line)
    return lines


def evaluate(engine: str, rc: int, out: Path,
             ref: list[str] | None = None) -> None:
    check(f"{engine}-rc", 0, rc)
    text = out.read_text(errors="replace") if out.exists() else ""
    summary = SUMMARY_RE.search(text)
    check(f"{engine}-summary-present", True, summary is not None)
    check(f"{engine}-summary-fails", 0,
          int(summary.group(1)) if summary else -1)
    check(f"{engine}-no-fail", 0,
          sum(1 for line in text.splitlines() if line.startswith("FAIL ")))
    lines = shared(out)
    if ref is None:
        check(f"{engine}-shared-count-floor", True, len(lines) >= floor)
        return
    check(f"{engine}-shared-count", len(ref), len(lines))
    diff = [(want, got) for want, got in zip(ref, lines) if want != got]
    check(f"{engine}-agrees-with-host", 0, len(diff))
    for want, got in diff[:6]:
        print(f"       host:      {want}")
        print(f"       {engine}: {got}")


def main() -> int:
    global floor

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--work-dir", default=DEFAULT_WORK_DIR,
                    help="runtime directory for the trees, binaries and logs")
    ap.add_argument("--musl", default=DEFAULT_MUSL)
    ap.add_argument("--clang", default=DEFAULT_CLANG)
    ap.add_argument("--ldl", default=DEFAULT_LDL)
    ap.add_argument("--qemu", default=DEFAULT_QEMU)
    ap.add_argument("--gem5", default=DEFAULT_GEM5)
    ap.add_argument("--gem5-config", default=DEFAULT_SE)
    ap.add_argument("--timeout", type=int, default=300)
    args = ap.parse_args()

    work = resolve(args.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    floor = len(CALL_RE.findall(PROBE.read_text(errors="replace")))
    musl = resolve(args.musl)
    clang = resolve(args.clang)
    ldl = resolve(args.ldl)
    qemu = resolve(args.qemu)
    gem5 = resolve(args.gem5)
    se = resolve(args.gem5_config)
    builtins = next((resolve(p) for p in BUILTINS if resolve(p).is_file()),
                    None)
    for path, what in ((clang, "clang"), (ldl, "ld.lld"), (qemu, "qemu-dadao"),
                       (gem5, "gem5.opt"), (se, "se.py"),
                       (musl / "lib/libc.a", "libc.a")):
        if not path.is_file():
            raise SetupError(f"{what} not found: {path}")

    host_elf = work / "probe-host"
    rc = run(["cc", "-std=c99", "-D_GNU_SOURCE", "-O1", "-Wall", str(PROBE),
              "-o", str(host_elf)], None, work / "cc-host.out",
             work / "cc-host.err", args.timeout)
    check("host-compile", 0, rc)
    obj = work / "probe.o"
    rc = run([str(clang), "-target", "dadao-unknown-elf", "-nostdinc",
              "-I", str(musl / "arch/dadao"),
              "-I", str(musl / "arch/generic"),
              "-I", str(musl / "obj/include"),
              "-I", str(musl / "include"),
              "-std=c99", "-D_GNU_SOURCE", "-O1", "-Wall", "-c",
              str(PROBE), "-o", str(obj)], None, work / "cc-guest.out",
             work / "cc-guest.err", args.timeout)
    check("guest-compile", 0, rc)
    guest_elf = work / "probe.elf"
    rc = run([str(ldl), "-o", str(guest_elf), str(musl / "lib/crt1.o"),
              str(obj), "--start-group", str(musl / "lib/libc.a"),
              str(builtins), "--end-group"], None, work / "ld.out",
             work / "ld.err", args.timeout)
    check("guest-link", 0, rc)

    # The host is the oracle: run it first and use its lines as the reference.
    host_tree = make_tree(work, "tree-host")
    host_out = work / "host.out"
    rc = run([str(host_elf), str(host_tree)], host_tree, host_out,
             work / "host.err", args.timeout)
    ref = shared(host_out)
    evaluate("host", rc, host_out)
    if not ref:
        raise SetupError("the host run produced no assertion lines")

    # (command, cwd, guest-stdout path, simulator stdout, simulator stderr):
    # gem5 writes the guest's streams to the paths it is given and its own
    # banner/errors to the process streams, so the two must never share a file.
    gem5_tree = make_tree(work, "tree-gem5")
    qemu_tree = make_tree(work, "tree-qemu")
    engine_runs = {
        "gem5-se": (
            [str(gem5), "--outdir", str(work / "m5-plain"), str(se),
             "--binary", str(guest_elf),
             "--guest-stdout", str(work / "gem5-se.out"),
             "--guest-stderr", str(work / "gem5-se.err"),
             "--guest-stdin", "/dev/null",
             "--cwd", str(gem5_tree), "--args", str(gem5_tree)],
            gem5_tree, work / "gem5-se.out",
            work / "gem5-se.sim.out", work / "gem5-se.sim.err"),
        "qemu": (
            [str(qemu), "-R", "4G", str(guest_elf), str(qemu_tree)],
            qemu_tree, work / "qemu.out", work / "qemu.out",
            work / "qemu.err"),
    }
    for engine, (cmd, cwd, out, sim_out, sim_err) in engine_runs.items():
        rc = run(cmd, cwd, sim_out, sim_err, args.timeout)
        evaluate(engine, rc, out, ref)

    print(f"\n{checks - failures}/{checks} checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SetupError as exc:
        print(f"setup error: {exc}", file=sys.stderr)
        sys.exit(2)
