#!/usr/bin/env python3
"""Module-level gate runner: ``make check-module COMPONENT=<c> TASK_ID=<id>``.

One task tests one component against **its own** source/build/install trees
(m20-infra-004, user ruling 2026-11-28):

  * source  = ``<work_root>/private/<id>/source/<source_component>``
  * build   = ``<work_root>/private/<id>/build/<component>`` (LLVM_BUILD /
              QEMU_BUILD / GEM5_BUILD, see ``tools/infra/module_gates.toml``)
  * install = ``<work_root>/private/<id>/install`` (exported as
              ``DADAO_INSTALL_ROOT``; prepared by ``install-host-private``)
  * lock    = ``<work_root>/private/<id>/gate.lock`` — a module run serializes
              with itself, not with shared L2/L3 runs.

The component -> gate mapping is **data** (``tools/infra/module_gates.toml``).
Every target it names must exist in the Makefile; a typo is rc=2 (fail-closed),
never a silently empty run.

Safety checks (each has a reachable FAIL):
  1. the install root must not be the shared root (or inside it) — module gates
     may not read the shared install root;
  2. the component's own tool (llvm-mc for llvm, qemu-system-dadao for qemu)
     must be a real file in the private root, not an inherited symlink;
  3. the shared root's binary md5s must be identical before and after the run.

Usage:
    python3 tools/infra/check_module.py validate
    python3 tools/infra/check_module.py run --component <c> --task-id <id>
Exit: 0 = all gates green, 2 = usage/mapping/install-root refusal, else gate rc.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MAKEFILE = REPO / "Makefile"
MODULE_GATES = REPO / "tools" / "infra" / "module_gates.toml"
COMPONENT_MANIFEST = REPO / "manifests" / "components.lock.toml"
INSTALL_MANIFEST = REPO / "manifests" / "install-dirs.lock.toml"

# The binary each component owns in the private install root.  The other tool is
# inherited as a symlink by design (mirror), so "owned" is what we assert.
OWNED_TOOL = {"llvm": "llvm-mc", "qemu": "qemu-system-dadao"}
ALL_TOOLS = ("llvm-mc", "qemu-system-dadao")
SHARED_MD5_FILES = (
    "cross-toolchain/bin/llvm-mc",
    "cross-toolchain/bin/qemu-system-dadao",
    "host-tools/bin/lli",
    "cross-toolchain/share/dadao/cfx-aliases.txt",
)


def load_mapping() -> dict:
    with MODULE_GATES.open("rb") as stream:
        return tomllib.load(stream)


def work_root() -> str:
    with COMPONENT_MANIFEST.open("rb") as stream:
        return tomllib.load(stream).get("work_root", ".work")


def shared_root() -> Path:
    with INSTALL_MANIFEST.open("rb") as stream:
        sdk = tomllib.load(stream)["sdk_dir"]
    return (REPO / sdk).resolve()


def makefile_targets() -> set[str]:
    """Target names really defined by the Makefile (literal + .PHONY + gate-locked).

    ``GATE_LOCKED_TARGETS`` members only get a generated rule via ``$(eval)``, so
    they are collected from the variable (and from ``.PHONY``) rather than from a
    literal ``name:`` line.
    """
    # Join backslash-continued lines first: .PHONY and GATE_LOCKED_TARGETS are
    # spread over several physical lines.
    text = MAKEFILE.read_text(encoding="utf-8").replace("\\\n", " ")
    names: set[str] = set()
    for line in text.splitlines():
        if line.startswith((" ", "\t", "#")):
            continue
        match = re.match(r"^([A-Za-z0-9_./%+-]+)\s*:(?!=)", line)
        if match:
            names.add(match.group(1))
    for match in re.finditer(r"^\.PHONY:(.*)$", text, re.MULTILINE):
        names.update(match.group(1).split())
    for match in re.finditer(r"^GATE_LOCKED_TARGETS\s*=\s*(.*)$", text, re.MULTILINE):
        names.update(match.group(1).split())
    names.update(f"_locked-{n}" for n in list(names))
    return names


def validate(mapping: dict) -> list[str]:
    problems: list[str] = []
    if mapping.get("format") != 1:
        problems.append(f"module_gates.toml: format must be 1, got {mapping.get('format')!r}")
    components = mapping.get("component")
    if not isinstance(components, dict) or not components:
        return problems + ["module_gates.toml: no [component.<name>] sections"]
    targets = makefile_targets()
    for name, section in sorted(components.items()):
        for key in ("gates", "prereqs"):
            for target in section.get(key, []):
                if target not in targets:
                    problems.append(
                        f"[component.{name}] {key}: target {target!r} is not defined in Makefile")
        if section.get("gates") and not section.get("build_var"):
            problems.append(f"[component.{name}] has gates but no build_var")
        if section.get("build_var") and not section.get("source_component"):
            problems.append(f"[component.{name}] has build_var but no source_component")
    return problems


def md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def shared_snapshot(shared: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for rel in SHARED_MD5_FILES:
        path = shared / rel
        snapshot[rel] = md5(path) if path.is_file() else "MISSING"
    return snapshot


def refuse(message: str) -> None:
    print(f"check-module: ERROR: {message}", file=sys.stderr)
    raise SystemExit(2)


def run_make(target: str, env: dict) -> int:
    cmd = ["make", "--no-print-directory", target]
    print(f"[check-module] $ {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd, cwd=str(REPO), env=env)
    print(f"[check-module] target={target} rc={result.returncode}", flush=True)
    return result.returncode


def cmd_validate() -> int:
    problems = validate(load_mapping())
    if problems:
        for problem in problems:
            print(f"check-module-gates: FAIL: {problem}", file=sys.stderr)
        return 2
    mapping = load_mapping()
    count = sum(len(s.get("gates", [])) for s in mapping["component"].values())
    print(f"check-module-gates: PASS — {len(mapping['component'])} components, "
          f"{count} gate targets, all defined in Makefile")
    return 0


def cmd_run(component: str, task_id: str) -> int:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", task_id or ""):
        refuse(f"invalid TASK_ID {task_id!r} (use [A-Za-z0-9._-]+)")

    mapping = load_mapping()
    problems = validate(mapping)
    if problems:
        for problem in problems:
            print(f"check-module: FAIL: {problem}", file=sys.stderr)
        return 2
    section = mapping["component"].get(component)
    if section is None:
        refuse(f"unknown COMPONENT {component!r}; known: {', '.join(sorted(mapping['component']))}")
    gates = section.get("gates", [])
    if not gates:
        refuse(
            f"COMPONENT={component} has no module gates in tools/infra/module_gates.toml; "
            "run its platform leg on demand (see the task book's mapping section)")

    private_root = (REPO / work_root() / "private" / task_id).resolve()
    source_root = private_root / "source"
    source_component = private_root / "source" / section["source_component"]
    build_dir = private_root / "build" / component
    default_install = private_root / "install"
    shared = shared_root()

    if not source_component.is_dir():
        refuse(f"private source tree {source_component} missing — run "
               f"`tools/infra/private_source.sh {section['source_component']} {task_id}` first")
    if not build_dir.is_dir():
        refuse(f"private build tree {build_dir} missing — build the component into it first")
    if not default_install.is_dir():
        refuse(f"private install root {default_install} missing — run "
               f"`make install-host-private COMPONENT={component} TASK_ID={task_id}` first")

    env_install = os.environ.get("DADAO_INSTALL_ROOT")
    if env_install:
        if not Path(env_install).is_absolute():
            refuse(f"DADAO_INSTALL_ROOT={env_install!r} is not absolute")
        install = Path(env_install).resolve()
    else:
        install = default_install
    if install == shared or shared in install.parents:
        refuse(
            f"install root {install} is the shared root (or inside it): module gates "
            "must run against the task's private root; unset DADAO_INSTALL_ROOT or "
            f"point it at {default_install}")
    if install != default_install:
        print(f"[check-module] WARNING: using non-default install root {install}",
              file=sys.stderr)

    owned = install / "cross-toolchain/bin" / OWNED_TOOL[component]
    if not owned.is_file() or owned.is_symlink():
        refuse(f"{owned} is not a private regular file — run install-host-private again")
    for tool in ALL_TOOLS:
        if not (install / "cross-toolchain/bin" / tool).is_file():
            refuse(f"tool {tool} missing from the private install root {install}")

    before = shared_snapshot(shared)
    missing_shared = [rel for rel, value in before.items() if value == "MISSING"]
    if missing_shared:
        refuse(f"shared install root {shared} is incomplete: {', '.join(missing_shared)}")
    print(f"[check-module] component={component} task={task_id}")
    print(f"  source:  {source_root}")
    print(f"  build:   {build_dir}")
    print(f"  install: {install}")
    print(f"  gates:   {', '.join(gates)}")
    print(f"  prereqs: {', '.join(section.get('prereqs', [])) or '-'}")
    for tool in ALL_TOOLS:
        path = install / "cross-toolchain/bin" / tool
        owner = "owned" if tool == OWNED_TOOL[component] else "inherited"
        print(f"  {tool}: {path} realpath={path.resolve()} md5={md5(path)} ({owner})")

    env = dict(os.environ)
    env["DADAO_INSTALL_ROOT"] = str(install)
    env["DADAO_MODULE_INSTALL_ROOT"] = str(install)
    env["DADAO_SOURCE_ROOT"] = str(source_root)
    env[section["build_var"]] = str(build_dir)
    env["GATE_LOCK"] = str(private_root / "gate.lock")
    # A nested make would otherwise try to reuse this make's jobserver fds.
    env.pop("MAKEFLAGS", None)
    env.pop("MFLAGS", None)

    failures: list[str] = []
    for target in section.get("prereqs", []):
        if run_make(target, env) != 0:
            failures.append(target)
            break
    if not failures:
        for target in gates:
            if run_make(target, env) != 0:
                failures.append(target)

    after = shared_snapshot(shared)
    print("[check-module] private tool paths after the run:")
    for tool in ALL_TOOLS:
        path = install / "cross-toolchain/bin" / tool
        print(f"  {tool}: {path} md5={md5(path)}")
    for rel, value in before.items():
        marker = "PASS" if after[rel] == value else "FAIL"
        print(f"  shared {rel}: before={value} after={after[rel]} [{marker}]")
        if after[rel] != value:
            failures.append(f"shared {rel} changed")

    if failures:
        print(f"check-module: FAIL — {', '.join(failures)}", file=sys.stderr)
        return 1
    print(f"check-module: PASS — {component} gates green against {install}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("validate")
    run = sub.add_parser("run")
    run.add_argument("--component", required=True)
    run.add_argument("--task-id", required=True)
    args = ap.parse_args(argv)
    if args.command == "validate":
        return cmd_validate()
    return cmd_run(args.component, args.task_id)


if __name__ == "__main__":
    raise SystemExit(main())
