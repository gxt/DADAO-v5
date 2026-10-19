#!/usr/bin/env python3
"""check-builtins-freshness -- the compiler-rt builtins archive that the
toolchain actually consumes must be the one built by the clang on disk now.

Why this exists (ISS-293, 2026-10-19): ``ADR-0032`` moved the ``shl`` encoding
(``LLVM-116t``/``QEMU-064t``).  The compiler-rt builtins archive was *not*
rebuilt afterwards: every copy of it still carried the retired encoding
``40 50 51 46`` (``ha=0x14``) and the new ``qemu-dadao`` decoded that as
undefined => guest SIGILL on any TF libcall.  Nothing in the build system could
see it -- ninja does not track the compiler *binary* as a source of the
objects, and the archive is a plain copy target of ``install-host`` (which
happily re-copies a stale archive).  The invariant this gate makes mechanical:

    the build-tree clang changed  =>  the builtins archive must be rebuilt
                                      (and re-staged into every consumer copy)

Consumer copies checked (all three are real link inputs):
  1. build product      <build-dir>/<resource-rel>            (compiler-rt tree)
  2. build-tree clang   <llvm-build>/<resource-rel>           (what
     ``.work/build/llvm/bin/clang`` links: probed live via
     ``-print-libgcc-file-name``; nothing else refreshes it)
  3. install root       <host-toolchain>/lib/clang/<ver>/<resource-rel>
     (``make install-host``)

Checks (each printed with expected/actual and its own verdict):
  1. build product present
  2. build-tree clang copy present        (skipped when no LLVM build tree)
  3. installed copy present               (skipped when the install root has no
                                           clang resource dir at all)
  4. build-tree clang copy sha256 == build product
  5. installed copy     sha256 == build product
  6. build archive not older than the build-tree clang binary
  7. no object in the builtins target dir older than that clang   (catches a
     partial rebuild, where the archive mtime alone looks fresh)

Applicability: L1 must stay usable on a fresh checkout, so a missing clang /
build tree with no builtins product anywhere prints SKIP and exits 0.  Once a
product exists, every check above is enforced (: an unprovable product must not
pass).

Cost: ~0.1 s (one ``-print-libgcc-file-name`` probe + a few stats/hashes).

Remedy: ``make build-builtins`` (rebuild with the current clang + re-stage into
the build-tree resource dir), then ``make install-host`` for the install root.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

DEFAULT_BUILD_DIR = ".work/build/compiler-rt-builtins"
LLVM_BUILD_REL = Path(".work") / "build" / "llvm"
TARGET = "dadao-unknown-elf"
# The CMake target name of the builtins archive inside the compiler-rt
# standalone build tree (upstream naming; the directory holds every .c.o).
BUILTINS_OBJ_DIR = Path("CMakeFiles") / "clang_rt.builtins-dadao.dir"

REMEDY = ("run 'make build-builtins' (rebuild with the current clang + stage "
          "into the LLVM build tree), then 'make install-host'")


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clang_resource_paths(clang: Path) -> tuple[str, str] | None:
    """``(<ver>, "lib/<triple>/libclang_rt.builtins.a")`` as the driver looks it up.

    Mirrors ``Makefile::BUILTINS_RESOURCE_PATH``: the single source of truth for
    where the archive lives inside a resource dir, probed live (never
    hardcoded, so an upstream layout change cannot drift this gate).
    """
    try:
        res = subprocess.run(
            [str(clang), f"--target={TARGET}", "-rtlib=compiler-rt",
             "-print-libgcc-file-name"],
            capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if res.returncode != 0:
        return None
    out = res.stdout.strip()
    marker = "/lib/clang/"
    if marker not in out:
        return None
    parts = out.split(marker, 1)[1].split("/", 1)     # <ver> / <lib/...>
    if len(parts) != 2 or not parts[1].startswith("lib/"):
        return None
    return parts[0], parts[1]


def archive_members(archive: Path) -> list[str]:
    """Member file names of a SysV/GNU ``ar`` archive (symbol table skipped).

    The archive is written in *deterministic* mode (``ar D``, LLVM's default),
    so member header timestamps are 0 and cannot be used for staleness; only
    the names matter -- they map back to the ``.c.o`` files in the build tree.
    """
    data = archive.read_bytes()
    if not data.startswith(b"!<arch>\n"):
        raise ValueError("not an ar archive")
    longnames = b""
    names: list[str] = []
    pos = 8
    while pos + 60 <= len(data):
        hdr = data[pos:pos + 60]
        if hdr[58:60] != b"`\n":
            raise ValueError(f"bad member header at offset {pos}")
        raw = hdr[0:16].decode("ascii", "replace").rstrip()
        size = int(hdr[48:58].decode("ascii").strip() or "0")
        body = data[pos + 60:pos + 60 + size]
        if raw == "//":
            longnames = body
        elif raw not in ("/", "/SYM64/"):
            if raw.startswith("/") and raw[1:].isdigit():
                off = int(raw[1:])
                end = longnames.find(b"\n", off)
                names.append(longnames[off:end].decode("ascii", "replace")
                             .rstrip("/"))
            else:
                names.append(raw)
        pos += 60 + size + (size & 1)
    return names


def run_checks(clang: Path, build_archive: Path, res_archive: Path | None,
               inst_archive: Path | None, obj_dir: Path | None) -> int:
    """Print every check and return the number of failures.

    All paths are explicit so ``--self-test`` can drive this on a temp tree
    without touching the repository (the same code path as the real run).
    """
    failed = 0

    def check(name: str, expected: str, actual: str, ok: bool) -> None:
        nonlocal failed
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: expected={expected} "
              f"actual={actual}")
        if not ok:
            failed += 1

    def skip(name: str, why: str) -> None:
        print(f"[SKIP] {name}: {why}")

    have_build = build_archive.is_file()
    check("build product archive present", "present",
          "present" if have_build else "absent", have_build)
    if not have_build:
        return failed + 1

    build_hash = sha256_of(build_archive)

    if res_archive is None:
        skip("build-tree clang copy", "no LLVM build tree / no resource dir")
    else:
        have_res = res_archive.is_file()
        check("build-tree clang copy present", "present",
              "present" if have_res else "absent", have_res)
        if have_res:
            res_hash = sha256_of(res_archive)
            check("build-tree clang copy == build product (sha256)",
                  build_hash, res_hash, res_hash == build_hash)

    if inst_archive is None:
        skip("installed copy", "no install-root clang resource dir")
    else:
        have_inst = inst_archive.is_file()
        check("installed copy present", "present",
              "present" if have_inst else "absent", have_inst)
        if have_inst:
            inst_hash = sha256_of(inst_archive)
            check("installed copy == build product (sha256)", build_hash,
                  inst_hash, inst_hash == build_hash)

    # 6: the archive must not predate the compiler that (re)built the objects.
    clang_ns = clang.stat().st_mtime_ns
    arch_ns = build_archive.stat().st_mtime_ns
    check("build archive not older than build-tree clang",
          f"mtime >= {clang_ns}", f"mtime {arch_ns}", arch_ns >= clang_ns)

    # 7: per-object staleness -- a partial rebuild can leave the archive newer
    # than clang while some of its members were produced by the older compiler
    # (the ISS-210 shape).  Members are resolved back to the build-tree .c.o
    # files; objects that are not members of the archive are irrelevant.
    try:
        members = archive_members(build_archive)
    except ValueError as exc:
        check("archive member list readable", "readable",
              f"unreadable ({exc})", False)
        return failed
    resolved = [(m, obj_dir / m) for m in members] if obj_dir else []
    resolved = [(m, p) for m, p in resolved if p.is_file()]
    if not resolved:
        skip("per-object staleness", "no builtins object files in the build tree")
    else:
        stale = [m for m, p in resolved if p.stat().st_mtime_ns < clang_ns]
        check(f"every archive member object newer than clang "
              f"({len(resolved)}/{len(members)} members live)",
              "0 stale", f"{len(stale)} stale", not stale)
        if stale:
            print(f"       stale: {', '.join(stale[:8])}"
                  f"{' ...' if len(stale) > 8 else ''}")
    return failed


def self_test() -> int:
    """Baseline PASS + four injections, each with its own reachable FAIL.

    The temp tree lives outside the repository; every mutation is restored by
    ``cp``/``utime`` + md5 accounting (no git), and the "only the mtime moved"
    case must stay green (ISS-263: a byte-identical copy is not staleness).
    """
    import shutil
    import subprocess
    import tempfile
    import time

    print("check-builtins-freshness --self-test (baseline + 4 injections)")
    tmp_root = Path("/tmp/opencode/builtins-freshness")
    tmp_root.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="builtins-freshness-selftest-",
                                 dir=str(tmp_root)))
    total_fail = 0
    try:
        clang = root / "bin" / "clang"
        objdir = root / "build" / BUILTINS_OBJ_DIR
        build = root / "build" / "lib" / "dadao-unknown-unknown-elf" / \
            "libclang_rt.builtins.a"
        res = root / "llvm" / "lib" / "clang" / "23" / "lib" / \
            "dadao-unknown-unknown-elf" / "libclang_rt.builtins.a"
        inst = root / "inst" / "lib" / "clang" / "23" / "lib" / \
            "dadao-unknown-unknown-elf" / "libclang_rt.builtins.a"
        for d in (clang.parent, build.parent, objdir, res.parent, inst.parent):
            d.mkdir(parents=True, exist_ok=True)
        clang.write_bytes(b"fake clang\n")
        for name in ("a.c.o", "b.c.o"):
            (objdir / name).write_bytes(b"OBJECT-" + name.encode())
        subprocess.run(["ar", "rcs", str(build), "a.c.o", "b.c.o"],
                       cwd=objdir, check=True)
        shutil.copyfile(build, res)
        shutil.copyfile(build, inst)

        t0 = time.time_ns() - 10_000_000_000
        os.utime(clang, ns=(t0, t0))
        for p in (build, objdir / "a.c.o", objdir / "b.c.o"):
            os.utime(p, ns=(t0 + 1_000_000_000, t0 + 1_000_000_000))
        os.utime(res, ns=(t0 + 2_000_000_000, t0 + 2_000_000_000))
        os.utime(inst, ns=(t0 + 2_000_000_000, t0 + 2_000_000_000))

        def run() -> int:
            return run_checks(clang, build, res, inst, objdir)

        def md5(p: Path) -> str:
            return hashlib.md5(p.read_bytes()).hexdigest()

        def verdict(name: str, expected_rc: str, rc: int) -> None:
            nonlocal total_fail
            ok = rc == 0 if expected_rc.startswith("0") else rc >= 1
            total_fail += 0 if ok else 1
            print(f"[{'PASS' if ok else 'FAIL'}] self-test {name}: "
                  f"expected={expected_rc} actual={rc}")

        # 0: clean baseline must be green.
        verdict("baseline", "0 failures", run())

        # 1: tampered installed copy (content) must be red.
        backup = inst.read_bytes()
        backup_md5 = md5(inst)
        inst.write_bytes(backup + b"tamper\n")
        verdict("inject-1 (tampered installed copy)", ">=1 failure", run())
        inst.write_bytes(backup)
        restored = md5(inst) == backup_md5
        total_fail += 0 if restored else 1
        print(f"[{'PASS' if restored else 'FAIL'}] self-test inject-1 restore: "
              f"expected=md5 {backup_md5} actual={md5(inst)}")

        # 2: only the mtime of the installed copy moves (byte-identical) =>
        #    must NOT turn red (ISS-263).
        os.utime(inst, ns=(t0 + 5_000_000_000, t0 + 5_000_000_000))
        verdict("inject-2 (mtime-only bump on installed copy)", "0 failures",
                run())

        # 3: clang newer than the archive and its members => red.
        os.utime(clang, ns=(t0 + 3_000_000_000, t0 + 3_000_000_000))
        verdict("inject-3 (clang newer than archive)", ">=1 failure", run())

        # 4a: clang back to the baseline instant => green again.
        os.utime(clang, ns=(t0, t0))
        verdict("inject-4a (archive + members fresh again)", "0 failures",
                run())
        # 4b: one *member* object older than clang while the archive itself is
        #     newer => exactly one stale member.
        os.utime(objdir / "b.c.o", ns=(t0 - 1_000_000_000, t0 - 1_000_000_000))
        verdict("inject-4b (one stale member object)", ">=1 failure", run())
    finally:
        shutil.rmtree(root, ignore_errors=True)

    print(f"check-builtins-freshness: --self-test "
          f"{'PASS' if total_fail == 0 else 'FAIL'} "
          f"({total_fail} unexpected outcome(s))")
    return 0 if total_fail == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="check-builtins-freshness")
    ap.add_argument("--build-dir", default=DEFAULT_BUILD_DIR,
                    help="compiler-rt builtins build tree (Makefile passes "
                         "COMPILER_RT_BUILD)")
    ap.add_argument("--self-test", action="store_true",
                    help="baseline + injected counter-examples in a temp tree")
    args = ap.parse_args()
    if args.self_test:
        return self_test()

    root = paths.repo_root()
    llvm_build = root / LLVM_BUILD_REL
    clang = llvm_build / "bin" / "clang"
    build_dir = root / args.build_dir

    if not clang.is_file():
        print(f"check-builtins-freshness: SKIP (no build-tree clang at "
              f"{clang}; run 'make build-mc' first)")
        return 0

    rel = clang_resource_paths(clang)
    if rel is None:
        print(f"check-builtins-freshness: FAIL -- cannot resolve the builtins "
              f"path from '{clang} --target={TARGET} -rtlib=compiler-rt "
              f"-print-libgcc-file-name'.  {REMEDY}")
        return 1
    ver, resource_rel = rel

    build_archive = build_dir / resource_rel
    res_archive = llvm_build / "lib" / "clang" / ver / resource_rel
    inst_root = paths.host_toolchain_dir() / "lib" / "clang"
    inst_archive = (inst_root / ver / resource_rel) if inst_root.is_dir() else None

    if not build_archive.is_file() and (inst_archive is None
                                       or not inst_archive.is_file()):
        print(f"check-builtins-freshness: SKIP (no builtins archive in the "
              f"build tree or the install root; {REMEDY})")
        return 0

    print(f"check-builtins-freshness: build product {build_archive}")
    print(f"                            build-tree clang {clang}")
    print(f"                            resource rel   {ver}/{resource_rel}")
    if inst_archive is not None:
        print(f"                            installed copy {inst_archive}")
    failed = run_checks(clang, build_archive, res_archive, inst_archive,
                        build_dir / BUILTINS_OBJ_DIR)
    if failed:
        print(f"check-builtins-freshness: FAIL ({failed} check(s)) -- {REMEDY}")
        return 1
    print("check-builtins-freshness: PASS (every consumer copy is the archive "
          "the current clang built)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
