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
  3. recorded toolchain stamp == current toolchain stamp (content identity:
     GNU build-id, ``sha256`` fallback; mtime/size/ctime are NOT part of it --
     INFRA-101t, ISS-263.  A stamp in the retired ``mtime=`` format is stale
     once and says ``stamp format migrated``)
  4. recorded source stamp     == current source digest
  5. installed libc.so sha256   == build libc.so sha256
  6. ``ld-musl-dadao.so.1`` is a symlink to ``libc.so`` resolving to it
  7. recorded compiler-rt builtins digest == the archive on disk now (ISS-293:
     musl links ``libc.so`` with that archive and hides its members, so a stale
     archive is baked into the DSO while every static test keeps passing)

Applicability: L1 must stay usable on a fresh checkout and in static-only
workflows, so a missing build tree, or a build tree/sysroot with no shared
product at all, prints SKIP and exits 0.  Once a shared product exists, every
check above is enforced (a missing stamp is a failure, not a skip: an
unprovable product must not pass).

``--self-test`` drives the same ``run_checks`` on a temp tree: tool mtime-only
change => green, tool content change => red, legacy stamp => red + ``migrated``,
tampered install copy => red, and every file restored by ``cp``/md5 accounting.

Cost: ~1.3 s (content digest of the ~2700-file musl tree).  L1 by the
docs/Process-07 criterion (static provenance check, runs no tested semantics).
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_musl as bm  # noqa: E402
import paths  # noqa: E402
import toolchain_id as tid  # noqa: E402

REMEDY = "run 'make build-musl-shared JOBS=8' (it rebuilds and reinstalls)"


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_checks(build_so: Path, inst_so: Path, link: Path, stored_tc: str | None,
               current_tc: str, stored_src: str | None, current_src: str,
               stored_b: str | None, current_b: str) -> int:
    """Print every check and return the number of failures.

    All inputs are explicit so ``--self-test`` can drive this on a temp tree
    without touching the repository (the same code path as the real run).
    """
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
        return failed + 1

    # 3: the objects/link were produced by this clang/ld.lld.  The criterion is
    # the tool's content identity (build-id) only -- INFRA-101t: a deterministic
    # relink keeps the bytes and moves the mtime, which must stay green.
    legacy_tc = stored_tc is not None and bm.stamp_is_legacy(stored_tc)
    if stored_tc is None:
        check("toolchain stamp recorded", "recorded", "missing", False)
    elif legacy_tc:
        print("check-musl-freshness: stamp format migrated -- the recorded "
              "toolchain stamp used the retired mtime= proxy (it proves nothing "
              "about content); rebuild once to record build-id")
        check("toolchain stamp == current clang/ld.lld", "equal",
              "legacy mtime= stamp (migrated)", False)
    else:
        same_tc = stored_tc.strip() == current_tc.strip()
        check("toolchain stamp == current clang/ld.lld", "equal",
              "equal" if same_tc else "different", same_tc)

    # 4: the objects/link were produced from these musl inputs.
    check("source stamp recorded", "recorded",
          "missing" if stored_src is None else "recorded", stored_src is not None)
    check("source stamp == current musl tree", current_src,
          stored_src if stored_src is not None else "missing",
          stored_src == current_src)

    # 7: the DSO embedded the compiler-rt builtins archive that is on disk now
    # (ISS-293).  Neither stamp above can see this one: the archive is a *link*
    # input of libc.so (LIBCC, --exclude-libs=ALL), not a compile input.
    check("builtins stamp recorded", "recorded",
          "missing" if stored_b is None else "recorded", stored_b is not None)
    check("builtins stamp == current compiler-rt archive", current_b,
          stored_b if stored_b is not None else "missing", stored_b == current_b)

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
          str(target) if is_link else "not-a-symlink",
          is_link and str(target) == bm.SONAME)
    check(f"{bm.LDSO_NAME} resolves to installed {bm.SONAME}", "yes",
          "yes" if resolves else "no", resolves)

    if failed:
        print(f"check-musl-freshness: {failed} check(s) failed")
    return failed


def self_test() -> int:
    """Baseline + injections on a temp tree; every expectation can fail.

    The injected toolchain is built with ``toolchain_id.test_elf_with_build_id``,
    so the real ``toolchain_stamp()`` code path runs end to end: a pure mtime
    change on the tool must keep the stamp (and the gate) green, while a content
    change must move it.  Files are restored with ``cp``/md5 accounting, never
    via git.
    """
    import os
    import shutil
    import tempfile

    print("check-musl-freshness --self-test (baseline + 6 injections)")
    tmp_root = Path("/tmp/opencode/INFRA-101t")
    tmp_root.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="musl-freshness-selftest-",
                                 dir=str(tmp_root)))
    bad = 0
    try:
        tool_dir = root / "bin"
        tool_dir.mkdir()
        bid_a = bytes.fromhex("de2e20d7e585817e19924fa5b26746ca5099cb59")
        bid_b = bytes.fromhex("585596725c4908cd13d42a9b4303dbfc77ec6a55")
        legacy_clang = tool_dir / "clang"
        legacy_clang.write_bytes(tid.test_elf_with_build_id(bid_a))
        (tool_dir / "ld.lld").write_bytes(tid.test_elf_with_build_id(bid_a))

        build_lib = root / "build" / "lib"
        sysroot_lib = root / "sysroot" / "lib"
        build_lib.mkdir(parents=True)
        sysroot_lib.mkdir(parents=True)
        build_so = build_lib / bm.SONAME
        inst_so = sysroot_lib / bm.SONAME
        link = sysroot_lib / bm.LDSO_NAME
        build_so.write_bytes(b"LIBC-BUILD\n")
        shutil.copyfile(build_so, inst_so)
        link.symlink_to(bm.SONAME)

        src_ok = "source-digest-A"
        builtins_ok = "builtins-digest-A"
        tc_ok = bm.toolchain_stamp(tool_dir)

        def run(stored_tc=tc_ok, current_tc=None, stored_src=src_ok,
                current_src=src_ok, stored_b=builtins_ok,
                current_b=builtins_ok):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = run_checks(build_so, inst_so, link, stored_tc,
                                current_tc if current_tc is not None else tc_ok,
                                stored_src, current_src, stored_b, current_b)
            return rc, buf.getvalue()

        def verdict(name: str, expected_rc: str, rc: int, out: str = "",
                    must_contain: str | None = None) -> None:
            nonlocal bad
            ok = (rc == 0) if expected_rc.startswith("0") else (rc >= 1)
            if ok and must_contain is not None and must_contain not in out:
                ok = False
            bad += 0 if ok else 1
            extra = f" contains={must_contain!r}" if must_contain else ""
            print(f"[{'PASS' if ok else 'FAIL'}] self-test {name}: "
                  f"expected={expected_rc}{extra} actual={rc}")

        def md5(p: Path) -> str:
            return hashlib.md5(p.read_bytes()).hexdigest()

        # 0: clean baseline must be green.
        rc, _ = run()
        verdict("baseline", "0 failures", rc)

        # 1: tool mtime moves, bytes stay => the stamp (and the gate) stay green.
        #    This is the INFRA-101t criterion: mtime is not identity.
        st = legacy_clang.stat()
        os.utime(legacy_clang, ns=(st.st_atime_ns, st.st_mtime_ns + 999_000_000))
        tc_touched = bm.toolchain_stamp(tool_dir)
        rc, _ = run(current_tc=tc_touched)
        verdict("inject-1 (tool mtime only)", "0 failures", rc)

        # 2: tool content changes (same size, different build-id) => red.
        clang_md5 = md5(legacy_clang)
        legacy_clang.write_bytes(tid.test_elf_with_build_id(bid_b))
        tc_changed = bm.toolchain_stamp(tool_dir)
        rc, _ = run(current_tc=tc_changed)
        verdict("inject-2 (tool content changed)", ">=1 failure", rc)
        legacy_clang.write_bytes(tid.test_elf_with_build_id(bid_a))
        restored = md5(legacy_clang) == clang_md5
        print(f"[{'PASS' if restored else 'FAIL'}] self-test inject-2 restore: "
              f"expected=md5 {clang_md5} actual={md5(legacy_clang)}")
        bad += 0 if restored else 1

        # 3: legacy mtime= stamp => stale AND says "migrated" (one rebuild).
        legacy_text = ("clang -> /x/clang size=1 mtime=2 clang version 23\n"
                       "ld.lld -> /x/ld.lld size=1 mtime=2 LLD 23\n")
        rc, out = run(stored_tc=legacy_text)
        verdict("inject-3 (legacy mtime= stamp)", ">=1 failure", rc, out,
                "migrated")

        # 4: installed copy content tampered => red (pre-existing assertion).
        inst_md5 = md5(inst_so)
        inst_so.write_bytes(b"LIBC-TAMPERED\n")
        rc, _ = run()
        verdict("inject-4 (tampered installed copy)", ">=1 failure", rc)
        inst_so.write_bytes(b"LIBC-BUILD\n")
        restored = md5(inst_so) == inst_md5
        print(f"[{'PASS' if restored else 'FAIL'}] self-test inject-4 restore: "
              f"expected=md5 {inst_md5} actual={md5(inst_so)}")
        bad += 0 if restored else 1

        # 5: source / builtins digests differ => red (unchanged assertions).
        rc, _ = run(stored_src="source-digest-B")
        verdict("inject-5 (source digest changed)", ">=1 failure", rc)
        rc, _ = run(stored_b="builtins-digest-B")
        verdict("inject-6 (builtins digest changed)", ">=1 failure", rc)

        # green again after restoring every recorded identity.
        rc, _ = run()
        verdict("restore (all identities current)", "0 failures", rc)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    print(f"check-musl-freshness: --self-test "
          f"{'PASS' if bad == 0 else 'FAIL'} ({bad} unexpected outcome(s))")
    return 0 if bad == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="check-musl-freshness")
    ap.add_argument("--self-test", action="store_true",
                    help="baseline + injected counter-examples in a temp tree")
    args = ap.parse_args()
    if args.self_test:
        return self_test()

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

    failed = run_checks(build_so, inst_so, link, bm.read_stamp(),
                        bm.toolchain_stamp(), bm.read_source_stamp(),
                        bm.source_stamp(), bm.read_builtins_stamp(),
                        bm.builtins_digest())
    if failed:
        print(f"check-musl-freshness: FAIL ({failed} check(s)) -- {REMEDY}")
        return 1
    print("check-musl-freshness: PASS (installed libc.so built from the current "
          "musl sources + toolchain)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
