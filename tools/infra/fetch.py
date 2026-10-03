#!/usr/bin/env python3
"""Fetch enabled components at their pinned commits.

Two layers keep large upstream repositories from being re-downloaded:

* ``.cache/<name>.git``  -- persistent bare mirror (the object store).
  Cloned with ``git clone --mirror`` (full) or ``git clone --bare --depth 1
  --branch <ref>`` (shallow, when the component sets ``shallow = true`` and
  ``shallow_ref`` in ``manifests/components.lock.toml``).  Afterwards only an
  incremental ``git fetch --prune`` (and only when the pinned commit is still
  missing).
* ``.work/source/<name>`` -- disposable worktree built from the *local*
  mirror (hard links, no network), then detached at the pinned commit.

``.work/`` may be cleaned at any time; rebuilding from ``.cache/`` needs no
network.
"""
from __future__ import annotations

import os
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


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


def sync_mirror(
    mirror: Path,
    repository: str,
    commit: str,
    shallow: bool = False,
    shallow_ref: str = "",
) -> None:
    """Create or incrementally refresh the persistent bare mirror.

    When *shallow* is True and *shallow_ref* is non-empty, the initial clone
    uses ``git clone --bare --depth 1 --branch <ref>`` (ADR-0006 D2 shallow
    bare pre-fill).  This brings only a single commit's worth of objects,
    cutting clone time from minutes to seconds and size from GiB to MiB.

    Limitations of a shallow bare mirror:

    * ``git fetch --prune`` only retrieves objects reachable from the
      tracked ref; fetching arbitrary commits is not supported.
    * Incremental refresh for a *different* pinned commit requires
      ``git fetch --unshallow`` (full history download).
    """
    if not mirror.exists():
        if shallow and shallow_ref:
            run("git", "clone", "--bare", "--depth", "1",
                "--branch", shallow_ref, repository, str(mirror))
            print(f"fetch: mirror {mirror.name} shallow-cloned (ref={shallow_ref})")
        else:
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


def select_source(component: dict) -> tuple[str, str]:
    """Resolve the effective Git URL for *component* following ADR-0005 D2.

    Returns ``(url, label)`` where *label* is a human-readable source name
    (the env-override value, ``source[0]["name"]``, or ``"canonical"``).

    Source selection priority:
    1. Environment variable ``COMPONENT_SOURCE_<NAME>`` (uppercase component
       name) selects by ``source[].name``.  The reserved name ``canonical``
       means use ``repository``.
    2. Otherwise, the first entry in ``source`` (if present).
    3. Otherwise, ``repository``.
    """
    name = component["name"]
    repository = component["repository"]
    sources = component.get("source", [])
    env_key = f"COMPONENT_SOURCE_{name.upper()}"
    env_val = os.environ.get(env_key)

    if env_val is not None:
        if env_val == "canonical":
            return (repository, "canonical")
        for src in sources:
            if src["name"] == env_val:
                return (src["url"], env_val)
        available = [s["name"] for s in sources]
        raise SystemExit(
            f"fetch: {env_key}={env_val!r} does not match any source for "
            f"component {name!r} (available: {available})"
        )

    if sources:
        return (sources[0]["url"], sources[0]["name"])
    return (repository, "canonical")


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

        source_url, src_label = select_source(component)
        shallow = bool(component.get("shallow", False))
        shallow_ref = component.get("shallow_ref", "")
        print(f"fetch: {name} using source '{src_label}' ({source_url})")
        sync_mirror(mirror, source_url, commit,
                    shallow=shallow, shallow_ref=shallow_ref)

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

        # Fetching first (safe: never touches the working tree/HEAD) makes the
        # pinned commit available locally for the ancestor check below, even
        # on a component that was already fetched+patched in a prior run.
        run("git", "fetch", "--no-tags", "origin", commit, cwd=target)

        head = head_of(target)
        if head == commit:
            # With tree-shaped patch sets applied via `git apply` (see
            # spec/Process-01-组件补丁组织与构建编排.md) the worktree is intentionally
            # dirty while HEAD stays on the pinned commit, so this branch is
            # the normal "already fetched + patched" case: leave it alone.
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

        # Only here is `git checkout --detach` about to discard work, so only
        # here must a dirty worktree be refused.
        dirty = subprocess.check_output(
            ["git", "-C", str(target), "status", "--porcelain=v1"], text=True
        )
        if dirty:
            raise SystemExit(f"fetch: {target} is dirty; refusing to overwrite")

        run("git", "checkout", "--detach", commit, cwd=target)
        print(f"fetch: {name} -> {commit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
