#!/usr/bin/env python3
"""Build gem5 with the DADAO ISA (B0 skeleton).

Exit codes:
  0  gem5.opt built (``build/DADAO/gem5.opt`` under the gem5 worktree)
  1  build failed or the worktree is not prepared (apply-series missing)
  2  build dependency missing (scons not on PATH) -- BLOCKED, not a pass
"""
from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def tail(path: Path, lines: int = 80) -> str:
    try:
        data = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    return "\n".join(data[-lines:])


def strip_ccache(value: str, default: str) -> str:
    """Return the real compiler command, dropping an existing ccache prefix.

    ``CC``/``CXX`` are consumed by gem5's SCons as *one* argv element, so a
    value like ``ccache g++`` cannot be handed over directly; the wrapper
    scripts take that role instead.
    """
    parts = [part for part in shlex.split(value) if Path(part).name != "ccache"]
    return " ".join(parts) if parts else default


def find_ccache() -> tuple[str | None, bool]:
    """Locate ccache on PATH; return ``(path or None, is_executable)``.

    ``shutil.which`` skips non-executable files, but a ccache that exists yet
    cannot be run must be reported as an error rather than silently ignored.
    """
    found = shutil.which("ccache")
    if found:
        return found, True
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if not entry:
            continue
        candidate = Path(entry) / "ccache"
        if candidate.is_file():
            return str(candidate), os.access(candidate, os.X_OK)
    return None, False


def write_ccache_wrappers(wrapper_dir: Path, ccache: str,
                          compilers: dict) -> dict:
    """Write ``ccache-cc``/``ccache-cxx`` shims, return their paths.

    Each shim is a single executable file so gem5's ``readCommand([CXX, ...])``
    works.  Existing shims are replaced wholesale (no stale contents).
    """
    wrapper_dir.mkdir(parents=True, exist_ok=True)
    wrappers = {}
    for var, (real, name) in compilers.items():
        argv = [shlex.quote(ccache)]
        argv.extend(shlex.quote(part) for part in shlex.split(real))
        script = "#!/bin/sh\nexec " + " ".join(argv) + ' "$@"\n'
        path = wrapper_dir / name
        if path.is_symlink() or path.exists():
            path.unlink()
        path.write_text(script, encoding="utf-8")
        path.chmod(0o755)
        if not os.access(path, os.X_OK):
            raise OSError(f"ccache wrapper {path} is not executable")
        wrappers[var] = path
    return wrappers


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path,
                        default=Path(".work/source/gem5"))
    parser.add_argument("--build", type=Path,
                        default=Path(".work/build/gem5"))
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--scons", default=os.environ.get("SCONS", "scons"))
    parser.add_argument("--no-ccache", action="store_true",
                        help="do not wrap CC/CXX with ccache")
    parser.add_argument("--ccache-dir", default=None,
                        help="ccache directory (default: ccache global default)")
    args = parser.parse_args()

    source = args.source if args.source.is_absolute() else ROOT / args.source
    build_link = args.build if args.build.is_absolute() else ROOT / args.build
    if not (source / "SConstruct").exists():
        print(f"build-gem5: {source}/SConstruct is missing; "
              "run `make fetch`/`make apply-series` first", file=sys.stderr)
        return 1
    if not (source / "build_opts/DADAO").exists():
        print(f"build-gem5: {source}/build_opts/DADAO is missing; "
              "the GEM5-004t patch series is not applied", file=sys.stderr)
        return 1

    scons = args.scons
    scons_path = shutil.which(scons) if os.sep not in scons else scons
    if not scons_path or not os.path.exists(scons_path):
        print("build-gem5: BLOCKED -- scons is not available on PATH.",
              file=sys.stderr)
        print("  install it (e.g. `python3 -m venv .work/venv && "
              ".work/venv/bin/pip install scons`) and rerun with "
              "SCONS=.work/venv/bin/scons", file=sys.stderr)
        return 2

    log_dir = ROOT / ".work/log/gem5"
    log_dir.mkdir(parents=True, exist_ok=True)
    log = log_dir / "GEM5-004t-build.log"
    # Run *inside* the source tree: gem5 computes its build directory from
    # os.getcwd(), and `scons -C` is not equivalent here (it leaves the
    # target path anchored at the launch directory).
    cmd = [scons_path, "build/DADAO/gem5.opt", f"-j{args.jobs}"]
    env = os.environ.copy()
    # gem5's SCons runs `readCommand([CXX, '--version'])`, i.e. CC/CXX must be
    # a single executable -- never a "ccache g++" command string.  Wrap ccache
    # in a shim script under gem5's build dir instead (runtime artifact).
    compilers = {}
    for var, default, name in (("CC", "gcc", "ccache-cc"),
                               ("CXX", "g++", "ccache-cxx")):
        compilers[var] = (strip_ccache(env.get(var, default), default), name)
    ccache, ccache_ok = find_ccache()
    use_ccache = not args.no_ccache and ccache is not None
    wrapper_dir = source / "build" / "ccache-bin"
    wrappers = {}
    if use_ccache:
        if not ccache_ok:
            print(f"build-gem5: ccache at {ccache} is not executable",
                  file=sys.stderr)
            return 1
        try:
            wrappers = write_ccache_wrappers(wrapper_dir, ccache, compilers)
        except OSError as exc:
            print(f"build-gem5: failed to create ccache wrappers: {exc}",
                  file=sys.stderr)
            return 1
        for var, path in wrappers.items():
            env[var] = str(path)
            print(f"build-gem5: {var}={path} "
                  f"(real={compilers[var][0]}, ccache={ccache})")
        if args.ccache_dir:
            env["CCACHE_DIR"] = str(Path(args.ccache_dir).expanduser())
    else:
        # No ccache: keep the real compiler, dropping any inherited ccache
        # prefix so the plain build path still works.
        for var, (real, _name) in compilers.items():
            if var in env and env[var] != real:
                env[var] = real
    ccache_dir = env.get("CCACHE_DIR", "ccache default (global cache)")
    print(f"build-gem5: log: {log.relative_to(ROOT)}")
    print(f"build-gem5: ccache: {'on' if use_ccache else 'off'}"
          + (f" (dir={ccache_dir})" if use_ccache else ""))
    print("build-gem5: run (cwd=%s): %s" %
          (source.relative_to(ROOT), " ".join(cmd)))
    with log.open("w", encoding="utf-8") as stream:
        proc = subprocess.run(cmd, cwd=source, stdout=stream,
                              stderr=subprocess.STDOUT, env=env)
    print(tail(log, 40))
    if proc.returncode != 0:
        print(f"build-gem5: FAILED rc={proc.returncode}; full log: "
              f"{log.relative_to(ROOT)}", file=sys.stderr)
        return 1

    binary = source / "build/DADAO/gem5.opt"
    if not binary.exists():
        print(f"build-gem5: scons returned 0 but {binary} is missing",
              file=sys.stderr)
        return 1

    # GEM5_BUILD is the conventional .work/build location; keep a stable link
    # to gem5's own build directory (gem5 insists on <src>/build/<variant>).
    if build_link.exists() or build_link.is_symlink():
        if not build_link.is_symlink():
            print(f"build-gem5: note: {build_link} exists and is not a "
                  "symlink; leaving it untouched")
        else:
            build_link.unlink()
    if not build_link.exists():
        build_link.parent.mkdir(parents=True, exist_ok=True)
        build_link.symlink_to((source / "build").relative_to(
            build_link.parent))
    print(f"build-gem5: PASS ({binary.relative_to(ROOT)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
