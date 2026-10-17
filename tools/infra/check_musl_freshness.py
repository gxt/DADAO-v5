#!/usr/bin/env python3
"""check-musl-freshness -- the installed musl shared library must be the one
built from the musl sources and toolchain that are on disk right now.

Why this exists (ISS-258, 2026-10-17): ``ISS-249`` changed the syscall
argument-bank protocol in *both* carriers (musl's ``__dadao_argmask`` stub and
QEMU's ``dadao_argmask`` decoder).  QEMU was rebuilt and reinstalled; the
installed ``libc.so`` was not, so every dynamic executable died inside musl's
ldso (``RELRO protection failed``, guest exit 127) while every static test kept
passing.  The toolchain stamp in ``build_musl.py`` could not see it: the
compiler was unchanged.  This gate makes the invariant mechanical:

    musl sources or toolchain changed  =>  libc.so must be rebuilt and
                                           reinstalled, or this check fails.

Checks (each printed with expected/actual and its own verdict):
  1. build product ``lib/libc.so`` exists in the musl build tree
  2. installed ``<sysroot>/lib/libc.so`` exists
  3. recorded toolchain stamp == current toolchain stamp
  4. recorded source stamp     == current source digest
  5. installed libc.so sha256   == build libc.so sha256
  6. ``ld-musl-dadao.so.1`` is a symlink to ``libc.so`` resolving to it

Applicability: L1 must stay usable on a fresh checkout and in static-only
workflows, so a missing build tree, or a build tree/sysroot with no shared
product at all, prints SKIP and exits 0.  Once a shared product exists, every
check above is enforced (a missing stamp is a failure, not a skip: an
unprovable product must not pass).

Cost: ~1.3 s (content digest of the ~2700-file musl tree).  L1 by the
docs/Process-07 criterion (static provenance check, runs no tested semantics).
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_musl as bm  # noqa: E402
import paths  # noqa: E402

REMEDY = "run 'make build-musl-shared JOBS=8' (it rebuilds and reinstalls)"


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if not bm.MUSL_SRC.is_dir():
        print(f"check-musl-freshness: SKIP (no musl build tree at "
              f"{bm.MUSL_SRC}; nothing to compare -- run 'make fetch "
              f"apply-series' then 'make build-musl-shared JOBS=8')")
        return 0

    syslib = paths.target_sysroot_dir() / "lib"
    build_so = bm.MUSL_SRC / "lib" / bm.SONAME
    inst_so = syslib / bm.SONAME
    link = syslib / bm.LDSO_NAME

    if not build_so.is_file() and not inst_so.exists():
        print("check-musl-freshness: SKIP (no shared product in the build tree "
              "or the sysroot; the static line only)")
        return 0

    failed = 0

    def check(name: str, expected: str, actual: str, ok: bool) -> None:
        nonlocal failed
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: expected={expected} "
              f"actual={actual}")
        if not ok:
            failed += 1

    # 1/2: both ends of the copy must exist.
    check("build product lib/libc.so present", "present",
          "present" if build_so.is_file() else "absent", build_so.is_file())
    check("installed lib/libc.so present", "present",
          "present" if inst_so.exists() else "absent", inst_so.exists())
    if not (build_so.is_file() and inst_so.exists()):
        print(f"check-musl-freshness: FAIL -- {REMEDY}")
        return 1

    # 3: the objects/link were produced by this clang/ld.lld.
    stored_tc = bm.read_stamp()
    current_tc = bm.toolchain_stamp()
    if stored_tc is None:
        check("toolchain stamp recorded", "recorded", "missing", False)
    else:
        check("toolchain stamp == current clang/ld.lld",
              "equal", "equal" if stored_tc.strip() == current_tc.strip()
              else "different", stored_tc.strip() == current_tc.strip())

    # 4: the objects/link were produced from these musl inputs.
    stored_src = bm.read_source_stamp()
    current_src = bm.source_stamp()
    check("source stamp recorded", "recorded",
          "missing" if stored_src is None else "recorded", stored_src is not None)
    check("source stamp == current musl tree", current_src,
          stored_src if stored_src is not None else "missing",
          stored_src == current_src)

    # 5: the installed copy is byte-identical to the build product.
    build_hash = sha256_of(build_so)
    inst_hash = sha256_of(inst_so)
    check("installed libc.so == build libc.so (sha256)", build_hash, inst_hash,
          build_hash == inst_hash)

    # 6: the contract path resolves to that same file.
    is_link = link.is_symlink()
    target = link.readlink() if is_link else None
    resolves = is_link and link.resolve() == inst_so.resolve()
    check(f"{bm.LDSO_NAME} symlink -> {bm.SONAME}", bm.SONAME,
          str(target) if is_link else "not-a-symlink", is_link and str(target) == bm.SONAME)
    check(f"{bm.LDSO_NAME} resolves to installed {bm.SONAME}", "yes",
          "yes" if resolves else "no", resolves)

    if failed:
        print(f"check-musl-freshness: FAIL ({failed} check(s)) -- {REMEDY}")
        return 1
    print("check-musl-freshness: PASS (installed libc.so built from the current "
          "musl sources + toolchain)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
