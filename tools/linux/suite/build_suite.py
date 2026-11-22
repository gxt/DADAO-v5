#!/usr/bin/env python3
"""build_suite.py — cross-build the whitelisted kselftest programs (m18-linux-005).

The kernel source tree is treated as read-only: the suite builds from a *suite
copy* of ``tools/testing/selftests`` under the runtime suite root, and the
adaptation patches (``tests/unit/linux/suite/patches/kselftest``) are applied to
that copy only.  Nothing here writes into ``.work/source/linux``.

Link model: the DADAO guest has a static musl ``libc.a`` and no loader in the
image yet (``m18-infra-002`` builds the dynamic-loader path), so every program is
linked **static** through a generated ``cc`` wrapper: musl's own headers,
``crt1.o`` and ``libc.a`` plus the target builtins archive.  A program that
cannot be built this way is reported per case with its compiler output — it is
never silently dropped and never replaced by a static stand-in for a case that
really needs a shared object.

Inputs: ``tests/unit/linux/suite/suite.yaml`` (case list), the locked kernel
tree (headers + selftests), ``make install-host`` (cross clang/ld.lld).

Outputs (all under ``suite_paths.suite_root()``):

  cc-static.sh        the cross-CC wrapper
  hdrs/include        kernel uapi headers (``make headers_install``)
  src/tree/           selftests copy (+ symlinks for ``top_srcdir`` siblings)
  build/<dir>/<prog>  per-case binaries
  build-report.json   per case: build rc, log path, binary sha256, patches

Usage:
  python3 tools/linux/suite/build_suite.py [--only ID ...]

Exit status: 0 = every case built; 1 = at least one case failed to build;
2 = setup error (missing toolchain / source tree / suite definition).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.linux import make_defconfig as defconfig  # noqa: E402
from tools.linux import paths as linux_paths        # noqa: E402
from tools.linux.suite import suite_cases           # noqa: E402
from tools.linux.suite import suite_paths           # noqa: E402

#: Every ``CONFIG_DADAO_*`` symbol of ``Kconfig.debug`` pinned off: the suite
#: image is a production boot, so no milestone probe may run inside it
#: (``check-config-pins`` C3 requires the key set to equal the Kconfig set).
CONFIG_PINS = {
    "CONFIG_DADAO_K1_EARLY_STOP": "n",
    "CONFIG_DADAO_K2_EARLY_STOP": "n",
    "CONFIG_DADAO_K2_TIME_STOP": "n",
    "CONFIG_DADAO_K2_TIME_CASE": "n",
    "CONFIG_DADAO_K2_IRQ_TEST": "n",
    "CONFIG_DADAO_K2_TRAP_SELFTEST": "n",
    "CONFIG_DADAO_K2_SELFTEST_REENTRY": "n",
    "CONFIG_DADAO_K2_SELFTEST_CFXTRAP": "n",
    "CONFIG_DADAO_K2_SELFTEST_CFXESC": "n",
    "CONFIG_DADAO_K2_SELFTEST_UNKNOWN": "n",
    "CONFIG_DADAO_K4_STACK_SELFTEST": "0",
    "CONFIG_DADAO_K4_COW_SELFTEST": "0",
    "CONFIG_DADAO_K4_SELFTEST": "n",
    "CONFIG_DADAO_K4_SWITCH_SELFTEST": "n",
    "CONFIG_DADAO_K4_KTHREAD_SELFTEST": "n",
    "CONFIG_DADAO_K5_SYSCALL_SELFTEST": "n",
    "CONFIG_DADAO_K5_CLONE_SELFTEST": "n",
    "CONFIG_DADAO_K5_FUTEX_SELFTEST": "n",
    "CONFIG_DADAO_M45_ENTRY_SELFTEST": "n",
    "CONFIG_DADAO_K5_SIGNAL_SELFTEST": "n",
    "CONFIG_DADAO_K5_CLOCK_SELFTEST": "n",
    "CONFIG_DADAO_K5_PAGESZ_SELFTEST": "n",
}

TARGET = "dadao-unknown-elf"
ARCH = "dadao"

#: selftests root files the per-directory Makefiles include or expect.
ROOT_FILES = ("lib.mk", "kselftest.h", "kselftest_harness.h", "Makefile")
ROOT_DIRS = ("kselftest",)

#: ``top_srcdir`` siblings the selftest Makefiles include from, provided as
#: symlinks to the read-only kernel tree (they are never written).
TREE_SIBLINGS = ("scripts", "arch", "mm", "include", "tools/include")


class SetupError(RuntimeError):
    """Missing prerequisite (exit 2)."""


def _tool(name: str) -> Path:
    path = linux_paths.toolchain_bin() / name
    if not path.is_file():
        raise SetupError(f"{path} not found — run 'make install-host' first")
    return path


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def musl_dir() -> Path:
    """The cross musl tree (headers + ``libc.a`` + ``crt1.o``)."""
    musl = linux_paths.linux_source_dir().parent / "musl"
    for rel in ("lib/crt1.o", "lib/libc.a"):
        if not (musl / rel).is_file():
            raise SetupError(f"{musl / rel} not found — run 'make build-musl' first")
    return musl


def write_cc_wrapper() -> Path:
    """Generate the static-musl cross-CC wrapper (runtime artefact).

    The installed ``clang`` has no default target triple and the guest libc is
    musl from the component build tree, so both the target flag and the
    headers/libraries are named here explicitly.  Compile-only invocations
    (``-c``/``-E``/``-S``) skip the link half; everything else links ``static``
    with ``crt1.o`` + ``libc.a`` + the target builtins archive.
    """
    clang = _tool("clang")
    musl = musl_dir()
    builtins = subprocess.run(
        [str(clang), f"--target={TARGET}", "-rtlib=compiler-rt",
         "-print-libgcc-file-name"],
        capture_output=True, text=True)
    if builtins.returncode != 0 or not Path(builtins.stdout.strip()).is_file():
        raise SetupError("cannot resolve the target builtins archive — "
                         "run 'make install-host'")
    includes = " ".join(f'-I"{musl / d}"' for d in (
        "arch/dadao", "arch/generic", "obj/src/internal",
        "src/include", "src/internal", "obj/include", "include"))
    body = (
        "#!/bin/sh\n"
        "# Generated by tools/linux/suite/build_suite.py (runtime artefact).\n"
        f'CLANG="{clang}"\n'
        f'MUSL="{musl}"\n'
        f'BUILTINS="{builtins.stdout.strip()}"\n'
        f'INC="{includes}"\n'
        'for a in "$@"; do\n'
        '  case "$a" in\n'
        '    -c|-E|-S) exec "$CLANG" --target=' + TARGET + ' -fintegrated-as '
        '$INC "$@";;\n'
        '  esac\n'
        'done\n'
        'exec "$CLANG" --target=' + TARGET + ' -fintegrated-as $INC '
        '-static -nostdlib "$MUSL/lib/crt1.o" "$@" '
        '-Wl,--start-group -L"$MUSL/lib" -lc "$BUILTINS" -Wl,--end-group\n'
    )
    path = suite_paths.cc_wrapper()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_file() or path.read_text(encoding="utf-8") != body:
        path.write_text(body, encoding="utf-8")
    path.chmod(0o755)
    return path


def install_headers() -> None:
    """``make headers_install`` into ``<suite>/hdrs`` (kernel uapi headers)."""
    cmd, _variables = defconfig.kernel_make_base()
    prefix = suite_paths.headers_dir()
    prefix.mkdir(parents=True, exist_ok=True)
    done = prefix / "include" / "linux" / "futex.h"
    proc = subprocess.run(
        cmd + ["headers_install", f"INSTALL_HDR_PATH={prefix}"],
        capture_output=True, text=True)
    if proc.returncode != 0 or not done.is_file():
        raise SetupError(
            "make headers_install failed (rc="
            f"{proc.returncode}); log tail:\n{proc.stdout[-2000:]}{proc.stderr[-2000:]}")
    print(f"[PASS] headers_install: {done.relative_to(suite_paths.suite_root())}")


def refresh_copy(cases: list[suite_cases.Case]) -> Path:
    """Re-create the suite copy of ``tools/testing/selftests``.

    Only the shared root files plus the top-level directories the case list
    names are copied (the full upstream tree is ~41 MiB, almost all of it
    unrelated).  The copy is re-created on every build so a stale patched file
    can never survive.
    """
    source = linux_paths.linux_source_dir() / "tools" / "testing" / "selftests"
    if not source.is_dir():
        raise SetupError(f"{source} not found — run 'make fetch' first")
    dest = suite_paths.selftests_copy()
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for name in ROOT_FILES:
        if not (source / name).is_file():
            raise SetupError(f"{source / name} missing from the locked kernel tree")
        shutil.copy2(source / name, dest / name)
    for name in ROOT_DIRS:
        if not (source / name).is_dir():
            raise SetupError(f"{source / name} missing from the locked kernel tree")
        shutil.copytree(source / name, dest / name, symlinks=True)
    tops = {case.top for case in cases} | _patch_tops()
    for top in sorted(tops):
        if not (source / top).is_dir():
            raise SetupError(f"selftests target {top!r} not in the locked kernel tree")
        shutil.copytree(source / top, dest / top, symlinks=True)

    # `top_srcdir` (= the selftests ../../..) must still resolve to a tree that
    # carries the kernel-side includes the Makefiles add with -I $(top_srcdir).
    tree = suite_paths.tree_dir()
    for rel in TREE_SIBLINGS:
        link = tree / rel
        target = linux_paths.linux_source_dir() / rel
        if not target.exists():
            raise SetupError(f"{target} missing from the locked kernel tree")
        link.parent.mkdir(parents=True, exist_ok=True)
        if link.is_symlink() or link.is_file():
            link.unlink()
        elif link.exists():
            shutil.rmtree(link)
        link.symlink_to(target)
    usr = tree / "usr"
    if usr.is_symlink() or usr.is_file():
        usr.unlink()
    elif usr.exists():
        shutil.rmtree(usr)
    usr.symlink_to(suite_paths.headers_dir())
    return dest


def _patch_tops() -> set[str]:
    """Top-level selftests directories the adaptation patches touch.

    A boot that runs only one case still has to copy (and patch) every file the
    patch series names, otherwise the series could apply only for some boots and
    the same source would produce different binaries.
    """
    if not suite_cases.PATCH_MANIFEST.is_file():
        return set()
    manifest = suite_cases.load_patch_manifest()
    tops: set[str] = set()
    for patch in manifest["patches"]:
        for entry in patch["files"]:
            tops.add(str(entry["path"]).split("/", 1)[0])
    return tops


def apply_patches(copy: Path) -> list[dict]:
    """Apply the ``manifest.yaml`` patch series to the copy, in manifest order.

    The manifest is the single list of patches — the directory is *not* globbed
    on its own: an unregistered ``*.patch`` (present in the directory but absent
    from the manifest) or a registered file that disappeared is a setup error,
    so the two can never diverge silently.  Each patch is also checked against
    its recorded ``sha256`` and against the per-file before/after hashes of the
    chain, which catches a stale patch before a wrong binary is built.
    """
    if not suite_cases.PATCH_DIR.is_dir():
        return []
    manifest, unregistered, missing_files, order_mismatch = \
        suite_cases.verify_patch_set()
    if unregistered:
        raise SetupError(f"adaptation patch(es) not in manifest.yaml: {unregistered}")
    if missing_files:
        raise SetupError(f"manifest lists patch(es) missing from the directory: "
                         f"{missing_files}")
    if order_mismatch:
        raise SetupError(f"manifest patch order is not the file-name order: "
                         f"{order_mismatch}")

    applied: list[dict] = []
    for patch in manifest["patches"]:
        path = suite_cases.PATCH_DIR / patch["file"]
        digest = _sha256_file(path)
        if digest != patch["sha256"]:
            raise SetupError(f"adaptation patch {path.name} sha256 {digest[:12]} "
                             f"!= manifest {str(patch['sha256'])[:12]}")
        drifted = [entry["path"] for entry in patch["files"]
                   if _sha256_file(copy / entry["path"]) != entry["upstream_sha256"]]
        if drifted:
            raise SetupError(f"adaptation patch {path.name}: input file(s) {drifted} "
                             f"do not match the manifest's upstream_sha256")
        proc = subprocess.run(
            ["git", "apply", "--whitespace=nowarn", "-p1", str(path)],
            cwd=str(copy), capture_output=True, text=True)
        if proc.returncode != 0:
            raise SetupError(
                f"adaptation patch {path.name} does not apply to the suite copy "
                f"(rc={proc.returncode}): {proc.stderr.strip()}")
        for entry in patch["files"]:
            got = _sha256_file(copy / entry["path"])
            if got != entry["patched_sha256"]:
                raise SetupError(
                    f"adaptation patch {path.name}: {entry['path']} hash {got[:12]} "
                    f"!= manifest patched_sha256 {str(entry['patched_sha256'])[:12]}")
        applied.append({"patch": path.name, "sha256": digest,
                        "files": [entry["path"] for entry in patch["files"]]})
    return applied


def _run_target(copy: Path, case: suite_cases.Case, wrapper: Path) -> dict:
    """Build one program through its directory's kselftest Makefile."""
    out_dir = suite_paths.build_dir() / case.dir
    out_dir.mkdir(parents=True, exist_ok=True)
    binary = out_dir / case.prog
    log = suite_paths.log_dir() / f"build-{case.id}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "make", "-C", str(copy / case.dir),
        f"OUTPUT={out_dir}",
        f"KHDR_INCLUDES=-isystem {suite_paths.headers_dir() / 'include'}",
        f"ARCH={ARCH}",
        f"CC={wrapper}",
        str(binary),
    ]
    env = dict(os.environ)
    env.pop("MAKEFLAGS", None)
    with log.open("wb") as stream:
        rc = subprocess.call(cmd, cwd=str(copy), stdout=stream,
                             stderr=subprocess.STDOUT, env=env)
    record = {
        "id": case.id,
        "cmd": " ".join(cmd),
        "rc": rc,
        "log": str(log),
        "binary": str(binary),
        "sha256": _sha256_file(binary) if binary.is_file() else None,
        "size": binary.stat().st_size if binary.is_file() else None,
    }
    if rc != 0 or record["sha256"] is None:
        tail = log.read_text(encoding="utf-8", errors="replace").splitlines()[-12:]
        record["error"] = "\n".join(tail)
        print(f"[FAIL] build {case.id}: rc={rc} (log {log.name})")
    else:
        print(f"[PASS] build {case.id}: {record['size']} B sha256={record['sha256'][:12]}")
    return record


def build_all(only: list[str] | None = None,
              cases: list[suite_cases.Case] | None = None) -> dict:
    cases = list(cases) if cases is not None else suite_cases.load_cases()
    if only:
        wanted = set(only)
        unknown = wanted - {case.id for case in cases}
        if unknown:
            raise SetupError(f"unknown case id(s) {sorted(unknown)}")
        cases = [case for case in cases if case.id in wanted]

    wrapper = write_cc_wrapper()
    install_headers()
    copy = refresh_copy(cases)
    patches = apply_patches(copy)
    print(f"[INFO] suite copy: {copy} ({len(cases)} case(s), "
          f"{len(patches)} adaptation patch(es))")

    records = [_run_target(copy, case, wrapper) for case in cases]
    report = {
        "format": 1,
        "toolchain": {"cc": str(wrapper), "target": TARGET, "arch": ARCH,
                      "link": "static musl (libc.a + crt1.o + builtins)"},
        "headers": str(suite_paths.headers_dir() / "include"),
        "patches": patches,
        "cases": records,
    }
    path = suite_paths.suite_root() / "build-report.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    failed = [record["id"] for record in records if record["rc"] != 0]
    print(f"[INFO] build report: {path.name} "
          f"({len(records) - len(failed)}/{len(records)} built)")
    return {"report": report, "failed": failed}


def main() -> int:
    parser = argparse.ArgumentParser(description="cross-build the kselftest suite")
    parser.add_argument("--only", action="append", default=[],
                        help="build only these case ids (repeatable; evidence)")
    args = parser.parse_args()
    try:
        result = build_all(args.only or None)
    except SetupError as exc:
        print(f"build_suite: SETUP ERROR: {exc}", file=sys.stderr)
        return 2
    if result["failed"]:
        print(f"build_suite: FAIL: {len(result['failed'])} case(s) did not build: "
              f"{result['failed']}", file=sys.stderr)
        return 1
    print("build_suite: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
