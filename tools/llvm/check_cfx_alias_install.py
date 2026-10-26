#!/usr/bin/env python3
"""cfx alias runtime-table install gate (LLVM-135t).

The assembler and the MCInstPrinter read the cfx alias names from
``<exe-dir>/../share/dadao/cfx-aliases.txt`` at run time, so a **stale or
missing copy** silently changes what assembly accepts and what disassembly
prints -- without any build failure.  This gate makes that a hard failure:

1. the source table ``contracts/cfx-aliases.txt`` exists, is non-empty and
   starts with the ``# format=1`` header;
2. the build-tree copy ``.work/build/llvm/share/dadao/cfx-aliases.txt`` is
   byte-identical to the source (that is what the build-tree llvm-mc reads);
3. the install-root copy
   ``.dadao/cross-toolchain/share/dadao/cfx-aliases.txt`` is byte-identical
   to the source (that is what the gates/executors read, ADR-0016 D9).

Byte identity is compared by sha256, not mtime: ``install-cfx-aliases`` only
rewrites a copy when the source table changed, and mtimes are meaningless
across two `atomic-install` calls.

Usage
-----
  tools/llvm/check_cfx_alias_install.py                  # real tree
  tools/llvm/check_cfx_alias_install.py --self-test      # fixtures: green + red
  tools/llvm/check_cfx_alias_install.py --source P --build-tree P --install P

Exit code: 0 only when every check passes.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "infra"))
import paths  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SOURCE_REL = Path("contracts") / "cfx-aliases.txt"
BUILD_COPY_REL = Path(".work") / "build" / "llvm" / "share" / "dadao" / "cfx-aliases.txt"
FORMAT_LINE = "# format=1"


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class Report:
    def __init__(self) -> None:
        self.failures = 0
        self.checks = 0

    def check(self, name: str, expected: str, actual: str, ok: bool) -> bool:
        self.checks += 1
        if not ok:
            self.failures += 1
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: expected={expected} "
              f"actual={actual}")
        return ok


def default_install_copy() -> Path:
    return paths.host_toolchain_dir() / "share" / "dadao" / "cfx-aliases.txt"


def audit(source: Path, build_copy: Path, install_copy: Path) -> int:
    rep = Report()
    print("=" * 72)
    print("check-cfx-alias-install -- runtime cfx alias table copies (LLVM-135t)")
    print(f"  source      : {source}")
    print(f"  build tree  : {build_copy}")
    print(f"  install root: {install_copy}")
    print("=" * 72)

    src_ok = source.is_file()
    rep.check("source table exists", "regular file", str(src_ok), src_ok)
    if not src_ok:
        print(f"FAIL: {source} is missing -- regenerate with "
              f"'python3 tools/llvm/gen_cfx_alias_table.py'")
        return 1

    first = source.read_text(encoding="utf-8").splitlines()
    header_ok = bool(first) and first[0] == FORMAT_LINE
    rep.check("source header", repr(FORMAT_LINE),
              repr(first[0] if first else "<empty>"), header_ok)

    src_sha = sha256_of(source)
    for label, path in (("build-tree copy", build_copy),
                        ("install-root copy", install_copy)):
        if not rep.check(f"{label} exists", "regular file",
                         str(path.is_file()), path.is_file()):
            if label == "install-root copy":
                print("  hint: run 'make install-cfx-aliases' (it only copies)")
            else:
                print("  hint: run 'make install-cfx-aliases' (it only copies)")
            continue
        rep.check(f"{label} sha256 == source", src_sha, sha256_of(path),
                  sha256_of(path) == src_sha)

    print("-" * 72)
    if rep.failures:
        print(f"check-cfx-alias-install: FAIL ({rep.failures}/{rep.checks} checks)")
        return 1
    print(f"check-cfx-alias-install: PASS ({rep.checks} checks)")
    return 0


def self_test() -> int:
    """Fixtures: a good tree must pass; each injected defect must fail."""
    body = (f"{FORMAT_LINE}\n"
            "scalar cfx_umon 0 canonical\n"
            "reg cfx_umon_cfx_id 0 4 0 1 canonical\n")

    def write_tree(base: Path) -> tuple[Path, Path, Path]:
        src = base / "contracts" / "cfx-aliases.txt"
        build = base / "build" / "share" / "dadao" / "cfx-aliases.txt"
        install = base / "install" / "share" / "dadao" / "cfx-aliases.txt"
        for path in (src, build, install):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
        return src, build, install

    def green(base: Path) -> tuple[Path, Path, Path]:
        return write_tree(base)

    def install_drift(base: Path) -> tuple[Path, Path, Path]:
        src, build, install = write_tree(base)
        install.write_text(install.read_text().replace("cfx_umon ", "cfx_umonx "),
                           encoding="utf-8")
        return src, build, install

    def build_missing(base: Path) -> tuple[Path, Path, Path]:
        src, build, install = write_tree(base)
        build.unlink()
        return src, build, install

    def source_missing(base: Path) -> tuple[Path, Path, Path]:
        src, build, install = write_tree(base)
        src.unlink()
        return src, build, install

    def no_header(base: Path) -> tuple[Path, Path, Path]:
        src, build, install = write_tree(base)
        for path in (src, build, install):
            path.write_text("scalar cfx_umon 0 canonical\n", encoding="utf-8")
        return src, build, install

    cases = [
        ("green tree", 0, green),
        ("install copy differs", 1, install_drift),
        ("build copy missing", 1, build_missing),
        ("source table missing", 1, source_missing),
        ("missing format header", 1, no_header),
    ]

    failed = 0
    with tempfile.TemporaryDirectory(prefix="cfx-alias-gate-") as tmp:
        root = Path(tmp)
        for name, expected_rc, setup in cases:
            print(f"\n--- self-test case: {name} (expect rc={expected_rc}) ---")
            src, build, install = setup(root / name.replace(" ", "-"))
            rc = audit(src, build, install)
            ok = rc == expected_rc
            failed += 0 if ok else 1
            print(f"[{'PASS' if ok else 'FAIL'}] self-test '{name}': "
                  f"expected rc={expected_rc} actual rc={rc}")

        print("-" * 72)
        if failed:
            print(f"check-cfx-alias-install --self-test: FAIL ({failed} cases)")
            return 1
        print(f"check-cfx-alias-install --self-test: PASS ({len(cases)} cases)")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default=str(ROOT / SOURCE_REL))
    ap.add_argument("--build-tree", default=str(ROOT / BUILD_COPY_REL))
    ap.add_argument("--install", default=None,
                    help="install-root copy (default: <host-toolchain>/share/dadao/cfx-aliases.txt)")
    ap.add_argument("--self-test", action="store_true",
                    help="run the green/red fixtures instead of the real tree")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()

    install = Path(args.install) if args.install else default_install_copy()
    return audit(Path(args.source), Path(args.build_tree), install)


if __name__ == "__main__":
    raise SystemExit(main())
