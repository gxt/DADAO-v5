#!/usr/bin/env python3
"""Push this checkout's ``.cache/`` to build nodes and verify the pinned commits.

Why
---
Nodes cannot reach the public internet reliably, so every component bare
repository (``.cache/<name>.git``) has to come from the master.  A one-off full
copy goes stale: when the master fetches a new component or commit the node
keeps the old objects, and a later ``make fetch`` on the node tries the network
and appears to hang instead of saying "cache is stale".

This tool fixes that in one command:

1. **incremental sync** -- ``rsync -a`` of ``.cache/`` (bare repositories are
   append-only, so the second run only moves the delta).  ``--delete`` is
   deliberately *not* used: a node may legitimately hold objects (or reference
   worktrees) the master does not, and silently deleting them is worse than a
   leftover file.  ``--dry-run`` prints the plan and writes nothing.
2. **per-commit verification** -- for every enabled component in
   ``manifests/components.lock.toml`` run
   ``git -C <cache>/<name>.git cat-file -e <commit>^{commit}`` on the node;
   any missing commit fails the node with a "cache stale, re-run sync" hint.
   The same check covers the submodule mirrors of a component that declares
   ``submodule_lock``: for every ``lite = true`` entry the node must hold
   ``<cache>/submodules/<sanitized-path>.git`` with the pinned commit, because
   ``fetch.py`` refuses to clone those from GitHub on a build node.

Node inventory
--------------
There is deliberately no built-in node list: ``--hosts a,b`` wins, then the
``DADAO_NODES`` environment variable; with neither the command fails and says
how to supply it.  Every transport uses ``ssh -o BatchMode=yes`` so a missing
key fails loudly instead of prompting.  ``--jobs`` bounds how many nodes are
processed at once.

``--repo`` is the **node-side** repository root (absolute, or starting with
``~/``); the node cache is derived as ``<repo>/.cache``.  A ``~/`` prefix is
resolved against the node's ``$HOME`` first, because rsync needs a real
absolute path on the remote side.  ``--local`` skips ssh and treats ``--repo``
as a local directory (self-test only); the local source cache is always this
checkout's own ``.cache/``.

Calling premise
---------------
Do not run ``make fetch`` on the master (or the node) while a sync is in
flight.  Object files that already exist are immutable, but a pack file being
written in place can be copied half-finished.  rsync reports such a run as a
partial transfer (rc 23/24); this tool keeps that non-zero and tells you to
re-run once ``fetch.py`` is idle -- it never hides it with ``--delete``.

Exit status is 0 only when every node synced and verified; the final summary
always prints ``host -> rc``.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import os
import re
import shlex
import subprocess
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LOCAL_CACHE = REPO_ROOT / ".cache"
SSH_OPTS = ("-o", "BatchMode=yes", "-o", "ConnectTimeout=10")
RSYNC_SSH = "ssh " + " ".join(SSH_OPTS)
TRANSFERRED_RE = re.compile(r"Total transferred:\s*([\d,]+)\s+bytes")
# A dry run sends no file data, so rsync prints only the planned file size.
PLANNED_RE = re.compile(r"Total transferred file size:\s*([\d,]+)\s+bytes")
PARTIAL_RSYNC_CODES = {23, 24}  # partial transfer / vanished source files


class NodeError(Exception):
    """A node failed before or during the sync/verify round trip."""

    def __init__(self, message: str, rc: int = 1) -> None:
        super().__init__(message)
        self.rc = rc


def fail(message: str, rc: int = 2) -> None:
    print(f"sync_cache.py: ERROR: {message}", file=sys.stderr)
    raise SystemExit(rc)


def resolve_hosts(args: argparse.Namespace) -> list[str]:
    raw = args.hosts if args.hosts else os.environ.get("DADAO_NODES", "")
    hosts: list[str] = []
    for token in re.split(r"[,\s]+", raw or ""):
        if token and token not in hosts:
            hosts.append(token)
    if not hosts:
        fail(
            "no nodes given; pass --hosts a,b (or set DADAO_NODES). "
            "There is no built-in node list."
        )
    for host in hosts:
        if host.startswith("-"):
            fail(f"refusing host that looks like an option: {host}")
    return hosts


def require_repo(args: argparse.Namespace) -> None:
    repo = args.repo
    if not repo:
        fail("--repo PATH is required (the node-side repository root)")
    if repo != "~" and not repo.startswith("~/") and not repo.startswith("/"):
        fail(
            f"--repo must be absolute or start with '~/' (got {repo!r}); "
            "a relative path has no meaning on the node"
        )


def submodule_mirror_name(path: str) -> str:
    """Mirror directory name of a submodule path (must match ``fetch.py``)."""
    clean = path.strip("/")
    if not clean or clean != path:
        fail(f"invalid submodule path {path!r}")
    return clean.replace("/", "__")


def load_submodules() -> list[tuple[str, str, str]]:
    """``(path, mirror-name, commit)`` for every required (lite) submodule."""
    manifest = REPO_ROOT / "manifests" / "components.lock.toml"
    try:
        data = tomllib.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        fail(f"cannot read {manifest}: {exc}")
    found: list[tuple[str, str, str]] = []
    for comp in data.get("component", []):
        lock = comp.get("submodule_lock")
        if not comp.get("enabled") or not lock:
            continue
        lock_path = REPO_ROOT / lock
        try:
            lock_data = tomllib.loads(lock_path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError) as exc:
            fail(f"cannot read {lock_path}: {exc}")
        for entry in lock_data.get("submodule", []):
            if not entry.get("lite"):
                continue
            path = entry.get("path", "")
            commit = entry.get("commit", "")
            if not path or not commit:
                fail(f"{lock}: lite submodule {path!r} has no path/commit")
            found.append((path, submodule_mirror_name(path), commit))
    return found


def load_components() -> list[tuple[str, str]]:
    manifest = REPO_ROOT / "manifests" / "components.lock.toml"
    try:
        data = tomllib.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        fail(f"cannot read {manifest}: {exc}")
    components = []
    for comp in data.get("component", []):
        if not comp.get("enabled"):
            continue
        if not comp.get("commit"):
            fail(f"{manifest}: enabled component {comp.get('name')!r} has no pinned commit")
        components.append((comp["name"], comp["commit"]))
    if not components:
        fail(f"{manifest}: no enabled component has a pinned commit; nothing to verify")
    return components


def ssh_argv(host: str, script: str) -> list[str]:
    return ["ssh", *SSH_OPTS, host, script]


def remote_home(host: str) -> str:
    """Ask the node for ``$HOME`` (read-only) so a ``~/`` path can be joined."""
    proc = subprocess.run(
        ssh_argv(host, 'printf %s "$HOME"'),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise NodeError(
            f"cannot read remote $HOME: {proc.stderr.strip() or 'ssh failed'}",
            rc=proc.returncode or 1,
        )
    home = proc.stdout.strip()
    if not home.startswith("/"):
        raise NodeError(f"remote $HOME is not absolute: {home!r}")
    return home


def cache_path(host: str, repo: str, local: bool) -> str:
    """Return the node cache directory derived from *repo* (absolute)."""
    if local:
        base = str(Path(repo).expanduser().resolve())
    elif repo == "~" or repo.startswith("~/"):
        home = remote_home(host)
        rest = repo[1:].lstrip("/")
        base = f"{home}/{rest}" if rest else home
    else:
        base = repo
    return base.rstrip("/") + "/.cache"


def sync_argv(host: str, dest: str, dry_run: bool, local: bool) -> list[str]:
    argv = ["rsync", "-a", "--stats"]
    if dry_run:
        argv.append("-n")
    if not local:
        argv += ["-e", RSYNC_SSH]
    target = dest if local else f"{host}:{shlex.quote(dest)}"
    return [*argv, f"{LOCAL_CACHE}/", target.rstrip("/") + "/"]


def ensure_dir(host: str, dest: str, local: bool) -> None:
    """Create the cache directory (rsync only creates its last component)."""
    argv = ["mkdir", "-p", dest]
    if not local:
        argv = ssh_argv(host, f"mkdir -p {shlex.quote(dest)}")
    proc = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise NodeError(
            f"cannot create remote cache directory: {proc.stderr.strip() or 'mkdir failed'}",
            rc=proc.returncode or 1,
        )


def run_sync(host: str, dest: str, dry_run: bool, local: bool) -> subprocess.CompletedProcess:
    return subprocess.run(
        sync_argv(host, dest, dry_run, local),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "LC_ALL": "C"},
    )


def transferred_bytes(stdout: str) -> int | None:
    match = TRANSFERRED_RE.search(stdout) or PLANNED_RE.search(stdout)
    return int(match.group(1).replace(",", "")) if match else None


def verify_script(
    dest: str,
    components: list[tuple[str, str]],
    submodules: list[tuple[str, str, str]],
) -> str:
    """Build the node-side check: one ``cat-file -e`` per pinned commit."""
    lines = [
        "set -u",
        f"cache={shlex.quote(dest)}",
        'if ! command -v git >/dev/null 2>&1; then',
        '  printf "FAIL git: not installed\\n"',
        "  exit 1",
        "fi",
        "fail=0",
    ]
    for name, commit in components:
        lines += [
            f'if [ ! -d "$cache"/{shlex.quote(name)}.git ]; then',
            f'  printf "FAIL {name}: missing bare repository\\n"',
            "  fail=1",
            f'elif git -C "$cache"/{shlex.quote(name)}.git cat-file -e '
            f"{shlex.quote(commit + '^{commit}')} 2>/dev/null; then",
            f'  printf "PASS {name} {commit}\\n"',
            "else",
            f'  printf "FAIL {name} {commit}: 缓存过期，请重新同步 (cache stale, re-run sync)\\n"',
            "  fail=1",
            "fi",
        ]
    for path, mirror_name, commit in submodules:
        repo = f'"$cache"/submodules/{mirror_name}.git'
        lines += [
            f'if [ ! -d {repo} ]; then',
            f'  printf "FAIL submodule {path}: missing bare mirror '
            f'.cache/submodules/{mirror_name}.git\\n"',
            "  fail=1",
            f'elif git -C {repo} cat-file -e '
            f"{shlex.quote(commit + '^{commit}')} 2>/dev/null; then",
            f'  printf "PASS submodule {path} {commit}\\n"',
            "else",
            f'  printf "FAIL submodule {path} {commit}: 缓存过期，请重新同步 '
            f'(cache stale, re-run sync)\\n"',
            "  fail=1",
            "fi",
        ]
    lines.append('exit "$fail"')
    return "\n".join(lines) + "\n"


def run_verify(
    host: str,
    dest: str,
    components: list[tuple[str, str]],
    submodules: list[tuple[str, str, str]],
    local: bool,
) -> subprocess.CompletedProcess:
    script = verify_script(dest, components, submodules)
    argv = ["bash", "-c", script] if local else ssh_argv(host, script)
    return subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace")


def process_host(
    args: argparse.Namespace,
    host: str,
    components: list[tuple[str, str]],
    submodules: list[tuple[str, str, str]],
) -> tuple[int, list[str]]:
    lines: list[str] = []
    try:
        dest = cache_path(host, args.repo, args.local)
        lines.append(f"cache: {dest}")
        if not args.dry_run:
            ensure_dir(host, dest, args.local)
        sync = run_sync(host, dest, args.dry_run, args.local)
        size = transferred_bytes(sync.stdout)
        size_text = f"{size}" if size is not None else "unknown"
        lines.append(f"rsync rc={sync.returncode} total_transferred={size_text} bytes")
        if sync.stderr.strip():
            lines += [f"rsync stderr: {line}" for line in sync.stderr.strip().splitlines()]
        if sync.returncode != 0:
            if sync.returncode in PARTIAL_RSYNC_CODES:
                lines.append(
                    "partial transfer: sources changed while copying; "
                    "re-run once `make fetch` is idle (no --delete fallback)"
                )
            lines.append("sync failed; verification skipped")
            return sync.returncode, lines
        if args.dry_run:
            lines.append(f"dry-run: would verify {len(components)} component(s):")
            lines += [f"  {name} {commit}" for name, commit in components]
            lines.append(
                f"dry-run: would verify {len(submodules)} required submodule(s):"
            )
            lines += [f"  {path} {commit}" for path, _mirror, commit in submodules]
            return 0, lines
        verify = run_verify(host, dest, components, submodules, args.local)
        lines += [line for line in verify.stdout.splitlines() if line.strip()]
        if verify.stderr.strip():
            lines += [f"verify stderr: {line}" for line in verify.stderr.strip().splitlines()]
        if verify.returncode != 0:
            lines.append("cache verification FAILED; re-run the sync on this node")
        return verify.returncode, lines
    except NodeError as exc:
        lines.append(f"ERROR: {exc}")
        return exc.rc or 1, lines
    except OSError as exc:
        lines.append(f"ERROR: {type(exc).__name__}: {exc}")
        return 127, lines


def parallel(
    args: argparse.Namespace,
    components: list[tuple[str, str]],
    submodules: list[tuple[str, str, str]],
):
    hosts = args.resolved_hosts
    workers = max(1, min(args.jobs, len(hosts)))
    results: dict[str, tuple[int, list[str]]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(process_host, args, host, components, submodules): host
            for host in hosts
        }
        for future in concurrent.futures.as_completed(futures):
            host = futures[future]
            results[host] = future.result()
    return [(host, *results[host]) for host in hosts]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--hosts", help="comma/space separated node list (default: $DADAO_NODES)")
    parser.add_argument("--repo", default="", help="node-side repository root (required; absolute or ~/...)")
    parser.add_argument("--dry-run", action="store_true", help="print the rsync plan and the components to verify; write nothing")
    parser.add_argument("--jobs", type=int, default=8, help="parallel nodes (default: 8)")
    parser.add_argument("--local", action="store_true", help="treat --repo as a local directory instead of ssh (self-test only)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    args.resolved_hosts = resolve_hosts(args)
    require_repo(args)
    if args.local and len(args.resolved_hosts) > 1:
        fail("--local writes one destination per label; pass a single host")
    if not LOCAL_CACHE.is_dir():
        fail(f"local cache not found: {LOCAL_CACHE} (run `make fetch` first)")
    components = load_components()
    submodules = load_submodules()

    rows = parallel(args, components, submodules)
    worst = 0
    for host, rc, lines in rows:
        print(f"=== {host} rc={rc} ===")
        for line in lines:
            print(f"  {line}")
        if rc != 0:
            worst = 1
    print("host -> rc")
    for host, rc, _lines in rows:
        verdict = "PASS" if rc == 0 else "FAIL"
        print(f"  {host} -> {rc} ({verdict})")
    print(f"overall rc={worst}")
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
