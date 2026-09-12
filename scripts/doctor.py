#!/usr/bin/env python3
"""Host environment self-check for the DADAO-v5 build.

Tools are grouped in three tiers:

* ``required``  -- needed on every host regardless of build path;
* ``native``    -- needed only for a native (host) build;
* ``container`` -- Docker, the fallback when the native toolchain is absent.

Exit status is 0 when at least one build path is usable, 1 otherwise.
"""
from __future__ import annotations

import shutil
import subprocess

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


def version(command: list[str]) -> str:
    """Return the first line of ``command`` output, or a fallback marker."""
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


def main() -> int:
    missing_required = report("required", REQUIRED)
    missing_native = report("native", NATIVE)

    docker = shutil.which("docker") is not None
    docker_detail = version(["docker", "--version"]) if docker else ""
    print("container")
    print(f"  {'docker':10} {'OK' if docker else 'MISSING':8} {docker_detail}")

    if missing_required:
        print(f"doctor: FAIL; missing required tools: {', '.join(missing_required)}")
        return 1
    if missing_native and not docker:
        print("doctor: FAIL; native tools incomplete and Docker unavailable")
        return 1
    mode = "native" if not missing_native else "container"
    print(f"doctor: PASS ({mode} build path available)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
