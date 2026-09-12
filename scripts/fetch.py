#!/usr/bin/env python3
"""Fetch enabled components at their pinned commits.

Two layers keep large upstream repositories from being re-downloaded:

* ``.cache/<name>.git``  -- persistent bare mirror (the object store).
  Cloned once with ``git clone --mirror``; afterwards only an incremental
  ``git fetch --prune`` (and only when the pinned commit is still missing).
* ``.work/source/<name>`` -- disposable worktree built from the *local*
  mirror (hard links, no network), then detached at the pinned commit.

``.work/`` may be cleaned at any time; rebuilding from ``.cache/`` needs no
network.
"""
from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args: str, cwd: Path | None = None) -> None:
    subprocess.run(args, cwd=cwd, check=True)


def has_commit(repo: Path, commit: str) -> bool:
    """True when ``commit`` is present in ``repo``'s object database."""
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


def sync_mirror(mirror: Path, repository: str, commit: str) -> None:
    """Create or incrementally refresh the persistent bare mirror."""
    if not mirror.exists():
        run("git", "clone", "--mirror", repository, str(mirror))
        print(f"fetch: mirror {mirror.name} cloned")
        return
    if has_commit(mirror, commit):
        # The pinned commit is already in the local object store: nothing to
        # download. This is what lets a cleaned .work/ be rebuilt offline and
        # keeps re-running `make fetch` from touching the network.
        print(f"fetch: mirror {mirror.name} already has {commit[:12]}; skipping fetch")
        return
    run("git", "-C", str(mirror), "fetch", "--prune")
    print(f"fetch: mirror {mirror.name} updated (incremental)")


def main() -> int:
    with (ROOT / "manifests/components.lock.toml").open("rb") as stream:
        manifest = tomllib.load(stream)
    work_root = ROOT / manifest.get("work_root", ".work")
    source_root = work_root / "source"
    mirror_root = ROOT / ".cache"
    enabled = [c for c in manifest.get("component", []) if c.get("enabled")]
    if not enabled:
        print("fetch: no components enabled; accept baseline ADRs first")
        return 0

    source_root.mkdir(parents=True, exist_ok=True)
    mirror_root.mkdir(parents=True, exist_ok=True)
    for component in enabled:
        name = component["name"]
        commit = component["commit"]
        mirror = mirror_root / f"{name}.git"
        target = source_root / name

        sync_mirror(mirror, component["repository"], commit)

        if target.exists() and not (target / ".git").exists():
            raise SystemExit(
                f"fetch: {target} exists but is not a git worktree; refusing to touch it"
            )

        if not target.exists():
            run("git", "clone", "--no-checkout", str(mirror), str(target))
            # A `--no-checkout` clone's HEAD points at the mirror's default
            # branch tip, not the pinned commit -- and that tip is usually a
            # *descendant* of the pin, so the "already patched" ancestor check
            # below would false-positive and skip the checkout entirely,
            # leaving the working tree empty and HEAD on the wrong commit.
            # There cannot be any patch commits applied yet in a clone this
            # same call just created, so go straight to the pinned commit.
            run("git", "fetch", "--no-tags", "origin", commit, cwd=target)
            run("git", "checkout", "--detach", commit, cwd=target)
            print(f"fetch: {name} -> {commit}")
            continue

        dirty = subprocess.check_output(
            ["git", "-C", str(target), "status", "--porcelain=v1"], text=True
        )
        if dirty:
            raise SystemExit(f"fetch: {target} is dirty; refusing to overwrite")

        # Fetching first (safe: never touches the working tree/HEAD) makes the
        # pinned commit available locally for the ancestor check below, even
        # on a component that was already fetched+patched in a prior run.
        run("git", "fetch", "--no-tags", "origin", commit, cwd=target)

        head = head_of(target)
        if head == commit:
            print(f"fetch: {name} already at {commit}")
            continue
        is_patched = subprocess.run(
            ["git", "-C", str(target), "merge-base", "--is-ancestor", commit, "HEAD"],
        ).returncode == 0
        if is_patched:
            # HEAD already has the pinned commit as an ancestor -- i.e. this
            # working tree has the patch series' commits applied on top
            # (apply_series.py's job), not a bare fresh checkout.
            # `git checkout --detach <pinned commit>` below is *destructive*
            # in this case: it silently discards every one of those applied
            # commits whenever the working tree happens to be clean. Leave an
            # already-patched component alone.
            print(
                f"fetch: {name} HEAD ({head[:12]}) already has {commit[:12]} as an "
                "ancestor (patches applied on top) -- leaving it alone"
            )
            continue

        run("git", "checkout", "--detach", commit, cwd=target)
        print(f"fetch: {name} -> {commit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
