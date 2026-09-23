#!/usr/bin/env python3
"""Fetch reference repositories declared in ``manifests/references.lock.toml``.

Same two-layer scheme as ``fetch.py``, but references are read-only inputs
whose worktrees live at the manifest ``path`` (e.g. ``.dadao/DADAO-0628``):

* ``.cache/refs/<id>.git`` -- persistent bare mirror.
* ``<path>``               -- disposable worktree, built from the local mirror
  and detached at the locked ``head``.

Idempotent: a reference whose worktree already sits at ``head`` is skipped
without touching the network. Removing the worktree (or all of ``.work/``)
rebuilds it from the local mirror with no download.
"""
from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run(*args: str, cwd: Path | None = None) -> None:
    subprocess.run(args, cwd=cwd, check=True)


def has_commit(repo: Path, commit: str) -> bool:
    return subprocess.run(
        ["git", "-C", str(repo), "cat-file", "-e", f"{commit}^{{commit}}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0


def head_of(repo: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def main() -> int:
    with (ROOT / "manifests/references.lock.toml").open("rb") as stream:
        manifest = tomllib.load(stream)
    references = manifest.get("reference", [])
    if not references:
        print("fetch-refs: no references declared")
        return 0

    mirror_root = ROOT / ".cache" / "refs"
    mirror_root.mkdir(parents=True, exist_ok=True)
    for reference in references:
        ident = reference["id"]
        head = reference["head"]
        target = ROOT / reference["path"]
        mirror = mirror_root / f"{ident}.git"

        if target.exists() and not (target / ".git").exists():
            raise SystemExit(
                f"fetch-refs: {target} exists but is not a git worktree; refusing to touch it"
            )
        if target.exists():
            if head_of(target) == head:
                print(f"fetch-refs: {ident} already at {head[:12]}; skipping")
                continue
            dirty = subprocess.check_output(
                ["git", "-C", str(target), "status", "--porcelain=v1"], text=True
            )
            if dirty:
                raise SystemExit(f"fetch-refs: {target} is dirty; refusing to overwrite")

        if not mirror.exists():
            run("git", "clone", "--mirror", reference["repository"], str(mirror))
            print(f"fetch-refs: mirror {mirror.name} cloned")
        elif has_commit(mirror, head):
            # The locked head is already in the local object store: rebuild the
            # worktree from the mirror without any network access.
            print(f"fetch-refs: mirror {mirror.name} already has {head[:12]}; skipping fetch")
        else:
            run("git", "-C", str(mirror), "fetch", "--prune")
            print(f"fetch-refs: mirror {mirror.name} updated (incremental)")

        if not target.exists():
            run("git", "clone", "--no-checkout", str(mirror), str(target))
        run("git", "fetch", "--no-tags", "origin", head, cwd=target)
        run("git", "checkout", "--detach", head, cwd=target)
        print(f"fetch-refs: {ident} -> {head}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
