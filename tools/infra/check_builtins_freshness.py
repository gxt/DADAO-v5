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
  2. build-tree clang   <llvm-build>/lib/clang/<ver>/<resource-rel>
                        (what ``.work/build/llvm/bin/clang`` links: probed live
                        via ``-print-libgcc-file-name``; nothing else refreshes
                        it -- the ``clang/<ver>/`` half used to be dropped by
                        ``build-builtins``, ISS-301)
  3. install root       <host-toolchain>/lib/clang/<ver>/<resource-rel>
                        (``make install-host``)

Checks (each printed with expected/actual and its own verdict):
  1. build product present
  2. build-tree clang copy present        (skipped when no LLVM build tree)
  3. installed copy present               (skipped when the install root has no
                                           clang resource dir at all)
  4. build-tree clang copy sha256 == build product
  5. installed copy     sha256 == build product
  6. the **sidecar** ``<build-dir>/.dadao-builtins-toolchain`` (written by
     ``make build-builtins``) records the clang/ld.lld *content identity* the
     archive was built by, and that identity == the tools on disk now
     (GNU build-id; ``sha256`` fallback).  mtime is NOT a criterion
     (INFRA-101t: a deterministic relink keeps the bytes and moves the mtime).
  7. the build product still is the archive whose sha256 the sidecar recorded
  8. every archive member's bytes == its ``.c.o`` in the build tree (catches a
     partial rebuild, where the archive looks fresh but some members were
     produced by the older compiler -- content, not member mtimes, ISS-210)

Applicability: L1 must stay usable on a fresh checkout, so a missing clang /
build tree with no builtins product anywhere prints SKIP and exits 0.  Once a
product exists, every check above is enforced: an unprovable product must not
pass, and an archive without a sidecar (built before INFRA-101t) is stale once.

Cost: ~0.2 s (one ``-print-libgcc-file-name`` probe + a few hashes + two ELF
note reads).

Remedy: ``make build-builtins`` (rebuild with the current clang + re-stage into
the build-tree resource dir), then ``make install-host`` for the install root.

``--self-test`` drives the same ``run_checks`` on a temp tree with synthetic
ELF tools (real build-id notes): tool mtime-only change => green, tool content
change => red, tampered sidecar => red, tampered copy / member => red, and every
mutation is restored with ``cp``/md5 accounting (no git).
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
import toolchain_id  # noqa: E402

DEFAULT_BUILD_DIR = ".work/build/compiler-rt-builtins"
LLVM_BUILD_REL = Path(".work") / "build" / "llvm"
TARGET = "dadao-unknown-elf"
# The CMake target name of the builtins archive inside the compiler-rt
# standalone build tree (upstream naming; the directory holds every .c.o).
BUILTINS_OBJ_DIR = Path("CMakeFiles") / "clang_rt.builtins-dadao.dir"
# Sidecar written by Makefile::build-builtins next to the build product: the
# producer identity of *this* archive (INFRA-101t).
SIDECAR_NAME = ".dadao-builtins-toolchain"

REMEDY = ("run 'make build-builtins' (rebuild with the current clang + stage "
          "into the LLVM build tree), then 'make install-host'")


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clang_resource_paths(clang: Path) -> tuple[str, str] | None:
    """``(<ver>, "lib/<triple>/libclang_rt.builtins.a")`` as the driver looks it up.

    Mirrors ``Makefile::BUILTINS_RESOURCE_PATH``: the single source of truth for
    where the archive lives inside a resource dir, probed live (never
    hardcoded, so an upstream layout change cannot drift this gate).  The same
    probe feeds ``Makefile::BUILTINS_BUILD_DST`` / ``BUILTINS_ARCHIVE_DST``.
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


def archive_entries(archive: Path) -> list[tuple[str, bytes]]:
    """``(member name, member bytes)`` of a SysV/GNU ``ar`` archive.

    The archive is written in *deterministic* mode (``ar D``, LLVM's default),
    so member header timestamps are 0 and cannot be used for staleness; the
    bytes can (they are the ``.c.o`` files the compiler wrote).
    """
    data = archive.read_bytes()
    if not data.startswith(b"!<arch>\n"):
        raise ValueError("not an ar archive")
    longnames = b""
    entries: list[tuple[str, bytes]] = []
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
                name = (longnames[off:end].decode("ascii", "replace")
                        .rstrip("/"))
            else:
                name = raw.rstrip("/")
            entries.append((name, body))
        pos += 60 + size + (size & 1)
    return entries


def run_checks(clang: Path, build_archive: Path, res_archive: Path | None,
               inst_archive: Path | None, obj_dir: Path | None,
               ld_lld: Path | None, sidecar: Path) -> int:
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

    # 6: the archive must have been produced by the compiler/linker on disk now.
    #    Criterion = content identity (build-id), recorded by build-builtins in
    #    the sidecar.  mtime is deliberately excluded (INFRA-101t).
    recorded, recorded_archive = toolchain_id.read_sidecar(sidecar)
    check("producer sidecar recorded", "present",
          "present" if recorded else f"missing ({sidecar})", bool(recorded))
    for tool, tool_path in (("clang", clang), ("ld.lld", ld_lld)):
        if tool_path is None or not tool_path.is_file():
            check(f"{tool} identity recordable", "present",
                  f"missing ({tool_path})", False)
            continue
        kind, value = toolchain_id.content_id(tool_path)
        got = recorded.get(tool)
        check(f"recorded {tool} identity == current", f"{kind}={value}",
              "=".join(got) if got else "missing",
              got == (kind, value))

    # 7: the archive still is the one the sidecar describes (content, not mtime).
    check("build product == sha256 recorded when built",
          recorded_archive or "missing", build_hash,
          recorded_archive == build_hash)

    # 8: per-member content -- a partial rebuild can leave the archive "fresh"
    #    while some members were produced by the older compiler (ISS-210).
    #    Members are resolved back to the build-tree .c.o files; objects that
    #    are not members of the archive are irrelevant.
    try:
        entries = archive_entries(build_archive)
    except ValueError as exc:
        check("archive member list readable", "readable",
              f"unreadable ({exc})", False)
        return failed
    members = [name for name, _ in entries]
    resolved = [(name, obj_dir / name) for name in members] if obj_dir else []
    resolved = [(name, p) for name, p in resolved if p.is_file()]
    if not resolved:
        skip("per-member content", "no builtins object files in the build tree")
    else:
        live = {name: hashlib.sha256(body).hexdigest() for name, body in entries}
        stale = [name for name, p in resolved
                 if live.get(name) != sha256_of(p)]
        check(f"every archive member == its .c.o bytes "
              f"({len(resolved)}/{len(members)} members live)",
              "0 stale", f"{len(stale)} stale", not stale)
        if stale:
            print(f"       stale: {', '.join(stale[:8])}"
                  f"{' ...' if len(stale) > 8 else ''}")
    return failed


def self_test() -> int:
    """Baseline + injections, each with its own reachable FAIL.

    The temp tree lives outside the repository; the tools are synthetic ELFs
    carrying real ``NT_GNU_BUILD_ID`` notes, so ``content_id`` takes the build-id
    path (not the sha256 fallback).  Every mutation is restored by ``cp``/md5
    accounting (no git), and the "only the mtime moved" case must stay green.
    """
    import os
    import shutil
    import tempfile
    import time

    print("check-builtins-freshness --self-test (baseline + 6 injections, "
          "build-id criterion)")
    tmp_root = Path("/tmp/opencode/INFRA-101t")
    tmp_root.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="builtins-freshness-selftest-",
                                 dir=str(tmp_root)))
    total_fail = 0
    try:
        tool_dir = root / "bin"
        objdir = root / "build" / BUILTINS_OBJ_DIR
        build = root / "build" / "lib" / "dadao-unknown-unknown-elf" / \
            "libclang_rt.builtins.a"
        res = root / "llvm" / "lib" / "clang" / "23" / "lib" / \
            "dadao-unknown-unknown-elf" / "libclang_rt.builtins.a"
        inst = root / "inst" / "lib" / "clang" / "23" / "lib" / \
            "dadao-unknown-unknown-elf" / "libclang_rt.builtins.a"
        for d in (tool_dir, build.parent, objdir, res.parent, inst.parent):
            d.mkdir(parents=True, exist_ok=True)
        bid_a = bytes.fromhex("de2e20d7e585817e19924fa5b26746ca5099cb59")
        bid_b = bytes.fromhex("585596725c4908cd13d42a9b4303dbfc77ec6a55")
        clang = tool_dir / "clang"
        ld_lld = tool_dir / "ld.lld"
        clang.write_bytes(toolchain_id.test_elf_with_build_id(bid_a))
        ld_lld.write_bytes(toolchain_id.test_elf_with_build_id(bid_b))
        for name in ("a.c.o", "b.c.o"):
            (objdir / name).write_bytes(b"OBJECT-" + name.encode())
        subprocess.run(["ar", "rcs", str(build), "a.c.o", "b.c.o"],
                       cwd=objdir, check=True)
        shutil.copyfile(build, res)
        shutil.copyfile(build, inst)
        sidecar = root / "build" / SIDECAR_NAME
        toolchain_id.write_sidecar(sidecar, tool_dir, ("clang", "ld.lld"), build)

        t0 = time.time_ns() - 10_000_000_000
        os.utime(clang, ns=(t0, t0))
        os.utime(ld_lld, ns=(t0, t0))
        for p in (build, objdir / "a.c.o", objdir / "b.c.o"):
            os.utime(p, ns=(t0 + 1_000_000_000, t0 + 1_000_000_000))
        os.utime(res, ns=(t0 + 2_000_000_000, t0 + 2_000_000_000))
        os.utime(inst, ns=(t0 + 2_000_000_000, t0 + 2_000_000_000))

        def run() -> int:
            return run_checks(clang, build, res, inst, objdir, ld_lld, sidecar)

        def md5(p: Path) -> str:
            return hashlib.md5(p.read_bytes()).hexdigest()

        def verdict(name: str, expected_rc: str, rc: int) -> None:
            nonlocal total_fail
            ok = rc == 0 if expected_rc.startswith("0") else rc >= 1
            total_fail += 0 if ok else 1
            print(f"[{'PASS' if ok else 'FAIL'}] self-test {name}: "
                  f"expected={expected_rc} actual={rc}")

        def restore(name: str, p: Path, backup: bytes, want: str) -> None:
            nonlocal total_fail
            p.write_bytes(backup)
            ok = md5(p) == want
            total_fail += 0 if ok else 1
            print(f"[{'PASS' if ok else 'FAIL'}] self-test {name} restore: "
                  f"expected=md5 {want} actual={md5(p)}")

        # 0: clean baseline must be green.
        verdict("baseline", "0 failures", run())

        # 1: clang mtime moves past every archive/member while the bytes stay
        #    => must stay green (the old mtime ordering is gone, INFRA-101t).
        os.utime(clang, ns=(t0 + 3_000_000_000, t0 + 3_000_000_000))
        verdict("inject-1 (clang mtime newer, bytes same)", "0 failures", run())
        os.utime(clang, ns=(t0, t0))

        # 2: clang content changes (different build-id) => red.
        backup = clang.read_bytes()
        backup_md5 = md5(clang)
        clang.write_bytes(toolchain_id.test_elf_with_build_id(bid_b))
        verdict("inject-2 (clang content changed)", ">=1 failure", run())
        restore("inject-2", clang, backup, backup_md5)

        # 3: sidecar records a different build-id => red, then restore.
        sc_backup = sidecar.read_bytes()
        sc_md5 = md5(sidecar)
        text = sidecar.read_text().replace(f"build-id={bid_a.hex()}",
                                           f"build-id={bid_b.hex()}")
        sidecar.write_text(text)
        verdict("inject-3 (sidecar build-id tampered)", ">=1 failure", run())
        restore("inject-3", sidecar, sc_backup, sc_md5)

        # 4: tampered installed copy (content) must be red.
        inst_backup = inst.read_bytes()
        inst_md5 = md5(inst)
        inst.write_bytes(inst_backup + b"tamper\n")
        verdict("inject-4 (tampered installed copy)", ">=1 failure", run())
        restore("inject-4", inst, inst_backup, inst_md5)

        # 5: one member's content differs from its .c.o (partial rebuild shape).
        obj_backup = (objdir / "b.c.o").read_bytes()
        obj_md5 = md5(objdir / "b.c.o")
        (objdir / "b.c.o").write_bytes(b"OBJECT-b.c.o-RETIRED-ENCODING")
        verdict("inject-5 (member bytes != .c.o)", ">=1 failure", run())
        restore("inject-5", objdir / "b.c.o", obj_backup, obj_md5)

        # 6: legacy archive with no sidecar => stale (one rebuild).
        sidecar.unlink()
        verdict("inject-6 (no sidecar)", ">=1 failure", run())
        sidecar.write_bytes(sc_backup)
        ok = md5(sidecar) == sc_md5
        total_fail += 0 if ok else 1
        print(f"[{'PASS' if ok else 'FAIL'}] self-test inject-6 restore: "
              f"expected=md5 {sc_md5} actual={md5(sidecar)}")
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
    ld_lld = llvm_build / "bin" / "ld.lld"
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
    print(f"                            producer sidecar "
          f"{build_dir / SIDECAR_NAME}")
    print(f"                            resource rel   {ver}/{resource_rel}")
    if inst_archive is not None:
        print(f"                            installed copy {inst_archive}")
    failed = run_checks(clang, build_archive, res_archive, inst_archive,
                        build_dir / BUILTINS_OBJ_DIR, ld_lld,
                        build_dir / SIDECAR_NAME)
    if failed:
        print(f"check-builtins-freshness: FAIL ({failed} check(s)) -- {REMEDY}")
        return 1
    print("check-builtins-freshness: PASS (every consumer copy is the archive "
          "the current clang built)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
