#!/usr/bin/env python3
"""Host environment self-check for the DADAO-v5 build.

Tools are grouped in three tiers:

* ``required``  -- needed on every host regardless of build path;
* ``native``    -- needed only for a native (host) build;
* ``container`` -- Docker, the fallback when the native toolchain is absent.

Component build dependencies (LLVM / QEMU) are checked separately and
reported as a fourth tier.  When any required build dep is missing the
overall verdict is FAIL; install suggestions are printed but **nothing
is installed automatically**.

Exit status is 0 when at least one build path is usable *and* all
enabled-component build deps are present, 1 otherwise.
"""
from __future__ import annotations

import os
import shutil
import subprocess

# ---- existing tool tiers (unchanged) ---------------------------------------

REQUIRED = {
    "git": ["git", "--version"],
    "make": ["make", "--version"],
    "cmake": ["cmake", "--version"],
    "python3": ["python3", "--version"],
}
NATIVE = {
    "ninja": ["ninja", "--version"],
    "clang": ["clang", "--version"],
}

# ---- component build-dependency definitions ---------------------------------

# Minimum cmake version required by LLVM 23.x.
_CMAKE_MIN_VERSION = (3, 20)

# Packages verified via ``pkg-config --exists <pkg>``.
# ``install`` holds a distro hint shown when the package is missing.
_QEMU_PKGS: dict[str, str] = {
    "pkg-config": "sudo apt install pkg-config",
    "glib-2.0":   "sudo apt install libglib2.0-dev",
    "pixman-1":   "sudo apt install libpixman-1-dev",
    "zlib":       "sudo apt install zlib1g-dev",
}

# libfdt needs special handling: Ubuntu's libfdt-dev does *not* ship
# libfdt.pc, so we fall back to checking the header file directly.
_LIBFDT_HEADER = "/usr/include/fdt.h"
_LIBFDT_INSTALL = "sudo apt install libfdt-dev"


def version(command: list[str]) -> str:
    """Return the first line of *command* output, or a fallback marker."""
    try:
        output = subprocess.check_output(
            command, text=True, stderr=subprocess.STDOUT
        )
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"
    return output.splitlines()[0] if output else "available"


def report(tier: str, tools: dict[str, list[str]]) -> list[str]:
    """Print one tool tier and return the names that are missing."""
    print(tier)
    missing: list[str] = []
    for name, command in tools.items():
        present = shutil.which(name) is not None
        detail = version(command) if present else ""
        print(f"  {name:10} {'OK' if present else 'MISSING':8} {detail}")
        if not present:
            missing.append(name)
    return missing


# ---- component build-dependency helpers -------------------------------------

def _cmake_version_ok() -> tuple[bool, str]:
    """Return (pass, detail) checking cmake >= _CMAKE_MIN_VERSION."""
    if not shutil.which("cmake"):
        return False, "cmake not found"
    try:
        out = subprocess.check_output(
            ["cmake", "--version"], text=True, stderr=subprocess.STDOUT
        )
    except (OSError, subprocess.CalledProcessError):
        return False, "cmake --version failed"
    # First line: "cmake version X.Y.Z"
    for tok in out.splitlines()[0].split():
        if tok[0:1].isdigit():
            parts = tok.split(".")
            try:
                ver = (int(parts[0]), int(parts[1]))
            except (ValueError, IndexError):
                return False, f"cannot parse version: {tok}"
            ok = ver >= _CMAKE_MIN_VERSION
            return ok, tok
    return False, "version not found in cmake output"


def _check_cpp_compiler() -> tuple[bool, str, str]:
    """Return (pass, compiler_name, detail) for a C++ compiler."""
    for name in ("g++", "clang++"):
        path = shutil.which(name)
        if path:
            detail = version([name, "--version"])
            return True, name, detail
    return False, "", ""


def _pkg_exists(pkg: str) -> bool:
    """Return True when ``pkg-config --exists <pkg>`` exits 0."""
    if not shutil.which("pkg-config"):
        return False
    try:
        subprocess.check_call(
            ["pkg-config", "--exists", pkg],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def _check_component_deps() -> list[str]:
    """Check build dependencies for enabled components.

    Returns a list of ``"<pkg> (<install-hint>)"`` strings for *missing*
    deps.  Prints a ``component-deps`` section to stdout.
    """
    print("component-deps")
    missing: list[str] = []

    # -- LLVM ---------------------------------------------------------------
    cmake_ok, cmake_detail = _cmake_version_ok()
    required_str = f"{_CMAKE_MIN_VERSION[0]}.{_CMAKE_MIN_VERSION[1]}"
    status = "OK" if cmake_ok else "FAIL"
    print(f"  {'cmake':10} {status:8} {cmake_detail} (need >= {required_str})")
    if not cmake_ok:
        missing.append(f"cmake >= {required_str} (sudo apt install cmake)")

    ninja_present = shutil.which("ninja") is not None
    print(f"  {'ninja':10} {'OK' if ninja_present else 'MISSING':8}")
    if not ninja_present:
        missing.append("ninja (sudo apt install ninja-build)")

    cpp_ok, cpp_name, cpp_detail = _check_cpp_compiler()
    print(f"  {'c++':10} {'OK' if cpp_ok else 'MISSING':8} {cpp_detail}")
    if not cpp_ok:
        missing.append("C++ compiler (sudo apt install g++ or clang)")

    # -- QEMU ---------------------------------------------------------------
    for pkg, install in _QEMU_PKGS.items():
        ok = _pkg_exists(pkg)
        print(f"  {pkg:10} {'OK' if ok else 'MISSING':8}")
        if not ok:
            missing.append(f"{pkg} ({install})")

    # libfdt -- Ubuntu's libfdt-dev lacks a .pc; check header fallback.
    if _pkg_exists("libfdt"):
        print(f"  {'libfdt':10} {'OK':8} (pkg-config)")
    elif os.path.isfile(_LIBFDT_HEADER):
        print(f"  {'libfdt':10} {'OK':8} (header fallback: {_LIBFDT_HEADER})")
    else:
        print(f"  {'libfdt':10} {'MISSING':8}")
        missing.append(f"libfdt ({_LIBFDT_INSTALL})")

    return missing


# ---- main entry point -------------------------------------------------------

def main() -> int:
    missing_required = report("required", REQUIRED)
    missing_native = report("native", NATIVE)

    docker = shutil.which("docker") is not None
    docker_detail = version(["docker", "--version"]) if docker else ""
    print("container")
    print(f"  {'docker':10} {'OK' if docker else 'MISSING':8} {docker_detail}")

    # Component build-dep checks (run regardless of existing-tier verdict).
    missing_deps = _check_component_deps()

    if missing_required:
        print(f"doctor: FAIL; missing required tools: {', '.join(missing_required)}")
        return 1
    if missing_native and not docker:
        print("doctor: FAIL; native tools incomplete and Docker unavailable")
        return 1
    if missing_deps:
        print(f"doctor: FAIL; missing component build dependencies:")
        for dep in missing_deps:
            print(f"  - {dep}")
        return 1

    mode = "native" if not missing_native else "container"
    print(f"doctor: PASS ({mode} build path available)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
