#!/usr/bin/env python3
"""Install one component's artifacts into a task-private install root.

Why (m20-infra-004, user ruling 2026-11-28): a module gate must read the
binaries built from *that task's* source tree, not the shared install root.
The consumer side is a single absolute path per tool (``$(HOST_TOOLCHAIN_BIN)/
llvm-mc``), so the private root is a **full symlink mirror** of the shared root:
entries the component does not own are ``ln -s`` back to the shared root (they
are only read), the component's own artifacts are real files written here.

The mirror deliberately does **not** inherit ``tests/`` (test artifacts) or
``writers/`` (writer-guard state): gates must write those into the private root
(the Makefile derives both from ``$(SDK_DIR)``, i.e. ``DADAO_INSTALL_ROOT``).

Guards:
  * the target root is compared by resolved path with the shared root; writing
    the shared root is refused (rc=2) unless ``DADAO_SHARED_INSTALL_OWNER`` is a
    non-empty token (the caller's self-attestation "I am the only writer";
    merge action only).  Same style as m20-infra-003's
    ``DADAO_SHARED_SOURCE_OWNER``.
  * ``--task-id`` is restricted to ``[A-Za-z0-9._-]+`` so it cannot escape
    ``<work_root>/private/``.

Owned artifacts are installed from the build tree named on the command line
(the Makefile passes its live ``HOST_LLVM_TOOLS``/``HOST_LLVM_TOOL_SYMLINKS``,
so the tool list has one source of truth).  Large files are hard-linked when
the filesystem allows it (a private directory entry, not a symlink; falls back
to a copy across devices).

Usage (the Makefile target passes all component inputs):
    make install-host-private COMPONENT=llvm|qemu TASK_ID=<id>
Exit: 0 = installed, 2 = usage/guard refusal, 1 = install failure.
"""
from __future__ import annotations

import argparse
import errno
import os
import re
import shutil
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
INSTALL_MANIFEST = REPO / "manifests" / "install-dirs.lock.toml"
COMPONENT_MANIFEST = REPO / "manifests" / "components.lock.toml"
TOKEN_ENV = "DADAO_SHARED_INSTALL_OWNER"
PRIVATE_ONLY = ("tests", "writers")  # never inherited from the shared root

LIT_LAUNCHER = """#!/usr/bin/env python3
# DADAO install-root lit launcher (INFRA-047t): the lit package is installed in ../share/lit
import os
import sys

_prefix = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_prefix, "share", "lit"))

from lit.main import main

if __name__ == "__main__":
    main()
"""


def fail(message: str, code: int = 1) -> None:
    print(f"install-host-private: {message}", file=sys.stderr)
    raise SystemExit(code)


def shared_install_root() -> Path:
    """The shared SDK root, from the manifest (never from ``DADAO_INSTALL_ROOT``)."""
    with INSTALL_MANIFEST.open("rb") as stream:
        sdk = tomllib.load(stream)["sdk_dir"]
    return (REPO / sdk).resolve()


def work_root() -> str:
    with COMPONENT_MANIFEST.open("rb") as stream:
        return tomllib.load(stream).get("work_root", ".work")


def _remove(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)
    elif path.exists():  # pragma: no cover - sockets/fifos are not expected here
        path.unlink()


def _symlink(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    _remove(dst)
    os.symlink(src, dst)


def _place_file(src: Path, dst: Path) -> None:
    """Install ``src`` at ``dst`` as a real directory entry (hardlink or copy).

    ``src`` may be a symlink in the build tree (``bin/clang -> clang-NN``);
    resolve it first so the private entry is a real executable, not a second
    symlink whose target does not exist under the private root (`cp -L`
    semantics in ``install-host``).
    """
    if not src.is_file():
        fail(f"missing build product {src}")
    src = src.resolve()
    dst.parent.mkdir(parents=True, exist_ok=True)
    _remove(dst)
    tmp = dst.with_name(f"{dst.name}.tmp.{os.getpid()}")
    _remove(tmp)
    try:
        os.link(src, tmp)
    except OSError as exc:
        if exc.errno not in (errno.EXDEV, errno.EPERM, errno.EMLINK, errno.EACCES):
            raise
        shutil.copy2(src, tmp)
    os.replace(tmp, dst)


def _place_dir(src: Path, dst: Path) -> None:
    if not src.is_dir():
        fail(f"missing build directory {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    _remove(dst)
    tmp = dst.with_name(f"{dst.name}.tmp.{os.getpid()}")
    _remove(tmp)
    shutil.copytree(src, tmp, symlinks=True)
    os.replace(tmp, dst)


def _place_symlink(target: str, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    _remove(dst)
    os.symlink(target, dst)


def mirror_shared(shared: Path, root: Path, owned: set[str]) -> int:
    """Mirror ``shared`` into ``root``: owned entries skipped, the rest symlinked."""

    def is_owned(rel: str) -> bool:
        return rel in owned

    def has_owned_below(rel: str) -> bool:
        prefix = f"{rel}/" if rel else ""
        return any(o != rel and o.startswith(prefix) for o in owned)

    count = 0

    def walk(rel: str) -> None:
        nonlocal count
        src = shared / rel if rel else shared
        dst = root / rel if rel else root
        if is_owned(rel):
            return  # the component writes this entry below
        if not src.is_dir() or src.is_symlink():
            _symlink(src, dst)
            count += 1
            return
        if has_owned_below(rel):
            dst.mkdir(parents=True, exist_ok=True)
            for child in sorted(src.iterdir()):
                if not rel and child.name in PRIVATE_ONLY:
                    continue
                walk(f"{rel}/{child.name}" if rel else child.name)
        else:
            _symlink(src, dst)
            count += 1

    walk("")
    return count


def owned_paths(args: argparse.Namespace) -> set[str]:
    """Install-root-relative paths this component owns (files and directories)."""
    owned: set[str] = set()
    if args.component == "qemu":
        owned.update({
            "cross-toolchain/bin/qemu-system-dadao",
            "cross-toolchain/bin/qemu-dadao",
        })
        return owned

    # llvm: everything `install-host` stages from LLVM_BUILD/COMPILER_RT_BUILD
    # (see the HOST_LLVM_TOOLS / HOST_LLVM_TOOL_SYMLINKS variables in Makefile).
    for tool in args.llvm_tools:
        owned.add(f"cross-toolchain/bin/{tool}")
    owned.add("cross-toolchain/bin/lld")
    for pair in args.llvm_symlinks:
        owned.add(f"cross-toolchain/bin/{pair.split(':', 1)[0]}")
    owned.add("cross-toolchain/bin/llvm-lit")
    owned.add("cross-toolchain/share/lit")
    owned.add(f"cross-toolchain/lib/clang/{args.clang_ver}/include")
    owned.add(f"cross-toolchain/lib/clang/{args.builtins_rel}")
    owned.add("cross-toolchain/share/dadao/cfx-aliases.txt")
    owned.add("host-tools/bin/lli")
    return owned


def install_llvm(args: argparse.Namespace, root: Path) -> list[str]:
    steps: list[str] = []
    build = Path(args.llvm_build).resolve()
    for tool in args.llvm_tools:
        _place_file(build / "bin" / tool, root / "cross-toolchain/bin" / tool)
        steps.append(f"bin/{tool}")
    _place_file(build / "bin/lld", root / "cross-toolchain/bin/lld")
    steps.append("bin/lld")
    for pair in args.llvm_symlinks:
        link, target = pair.split(":", 1)
        _place_symlink(target, root / "cross-toolchain/bin" / link)
        steps.append(f"bin/{link} -> {target}")
    launcher = root / "cross-toolchain/bin/llvm-lit"
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text(LIT_LAUNCHER, encoding="utf-8")
    launcher.chmod(0o755)
    steps.append("bin/llvm-lit")
    # Same shape and refresh as `install-host`: it wipes <prefix>/share/lit and
    # re-copies, so <prefix>/share/lit/lit is the package the launcher puts on
    # sys.path (a single `lit` level would not import).
    lit_dir = root / "cross-toolchain/share/lit"
    _remove(lit_dir)
    _place_dir(Path(args.lit_src).resolve(), lit_dir / "lit")
    steps.append("share/lit/lit")
    _place_dir(Path(args.clang_headers).resolve(),
               root / f"cross-toolchain/lib/clang/{args.clang_ver}/include")
    steps.append("lib/clang/<ver>/include")
    _place_file(Path(args.builtins_src).resolve(),
                root / f"cross-toolchain/lib/clang/{args.builtins_rel}")
    steps.append("lib/clang/<ver>/lib/.../builtins.a")
    _place_file(Path(args.cfx_src).resolve(),
                root / "cross-toolchain/share/dadao/cfx-aliases.txt")
    steps.append("share/dadao/cfx-aliases.txt")
    _place_file(build / "bin/lli", root / "host-tools/bin/lli")
    steps.append("host-tools/bin/lli")
    return steps


def install_qemu(args: argparse.Namespace, root: Path) -> list[str]:
    build = Path(args.qemu_build).resolve()
    steps = []
    for tool in ("qemu-system-dadao", "qemu-dadao"):
        _place_file(build / tool, root / "cross-toolchain/bin" / tool)
        steps.append(f"bin/{tool}")
    return steps


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--component", choices=("llvm", "qemu"),
                    help="required unless --print-root")
    ap.add_argument("--task-id", required=True)
    ap.add_argument("--install-root", default=None,
                    help="default: <work_root>/private/<task-id>/install")
    ap.add_argument("--shared-root", default=None,
                    help="shared root to mirror (default: manifest sdk_dir); "
                         "test/sandbox knob only")
    ap.add_argument("--llvm-build", default=".work/build/llvm")
    ap.add_argument("--qemu-build", default=".work/build/qemu")
    ap.add_argument("--llvm-tools", default="")
    ap.add_argument("--llvm-symlinks", default="")
    ap.add_argument("--clang-ver", default="")
    ap.add_argument("--clang-headers", default="")
    ap.add_argument("--builtins-src", default="")
    ap.add_argument("--builtins-rel", default="")
    ap.add_argument("--lit-src", default="")
    ap.add_argument("--cfx-src", default="")
    ap.add_argument("--print-root", action="store_true")
    args = ap.parse_args(argv)
    args.llvm_tools = args.llvm_tools.split()
    args.llvm_symlinks = args.llvm_symlinks.split()

    if not re.fullmatch(r"[A-Za-z0-9._-]+", args.task_id):
        fail(f"invalid --task-id {args.task_id!r} (use [A-Za-z0-9._-]+)", 2)

    shared = (Path(args.shared_root).resolve() if args.shared_root
              else shared_install_root())
    root = (Path(args.install_root).resolve() if args.install_root
            else (REPO / work_root() / "private" / args.task_id / "install").resolve())

    if args.print_root:
        print(root)
        return 0
    if not args.component:
        fail("--component is required (llvm|qemu)", 2)

    if not shared.is_dir():
        fail(f"shared install root {shared} does not exist", 2)

    if shared in root.parents:
        # A root *inside* the shared root would mirror the shared tree into
        # itself; no token can make that meaningful.
        fail(f"private install root {root} must not be inside the shared root {shared}", 2)
    writes_shared = root == shared
    token = os.environ.get(TOKEN_ENV, "").strip()
    if writes_shared and not token:
        fail(
            f"refusing to install into the shared install root {root}: a task "
            "may not write it; set "
            f"{TOKEN_ENV}=<non-empty token> only if this process is the sole "
            "writer (merge action: main-session), or use the default private "
            "root (omit --install-root)", 2)

    if args.component == "llvm":
        missing = [name for name, value in {
            "--llvm-tools": args.llvm_tools,
            "--clang-ver": args.clang_ver,
            "--clang-headers": args.clang_headers,
            "--builtins-src": args.builtins_src,
            "--builtins-rel": args.builtins_rel,
            "--lit-src": args.lit_src,
            "--cfx-src": args.cfx_src,
        }.items() if not value or (isinstance(value, str) and not value.strip())]
        if missing:
            fail(f"llvm install needs {', '.join(missing)} (the Makefile target "
                 "passes them; run it via make, not directly)", 2)
        if not args.builtins_rel.startswith(f"{args.clang_ver}/lib/"):
            fail(f"--builtins-rel {args.builtins_rel!r} is not "
                 f"{args.clang_ver}/lib/... (probe the build-tree clang first)", 2)

    owned = owned_paths(args)
    parent = root.parent
    parent.mkdir(parents=True, exist_ok=True)

    if root == shared:
        # Token holder (merge action): install owned files in place, keep the
        # rest of the shared root untouched.
        steps = install_llvm(args, root) if args.component == "llvm" else install_qemu(args, root)
        mirrored = 0
    else:
        staging = parent / f"{root.name}.new.{os.getpid()}"
        _remove(staging)
        staging.mkdir(parents=True)
        mirrored = mirror_shared(shared, staging, owned)
        for name in PRIVATE_ONLY:
            (staging / name).mkdir(parents=True, exist_ok=True)
        steps = install_llvm(args, staging) if args.component == "llvm" else install_qemu(args, staging)
        _remove(root)
        os.replace(staging, root)

    print(f"install-host-private: component={args.component} task={args.task_id}")
    print(f"  shared root (read-only mirror source): {shared}")
    print(f"  private install root: {root}")
    print(f"  inherited symlinks: {mirrored}; owned artifacts: {len(steps)}")
    for step in steps:
        print(f"    + {step}")
    if writes_shared:
        print(f"  NOTE: wrote the shared root under {TOKEN_ENV} (merge action)")
    print("install-host-private: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
