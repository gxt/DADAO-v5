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

Submodule mirrors
-----------------
A component may also pin the submodules of its checkout with
``submodule_lock = "manifests/<name>.toml"`` (currently only chipyard).  Every
entry marked ``lite = true`` (the upstream minimal build set) or
``dadao_extra = true`` (needed by this repository on top of that set, e.g. the
``riscv-isa-sim`` source that provides fesvr) is a *required* submodule and gets
its own bare mirror at ``.cache/submodules/<sanitized-path>.git``
(``generators/testchipip`` -> ``generators__testchipip.git`` -- derived from the
full path, never the basename, so two ``utils`` submodules cannot collide).

Mirrors are created on the master only, by an explicit
``fetch.py --populate-submodules`` (needs the network; retried).  Build nodes
must never reach GitHub: for them a missing mirror is a hard error that points
at ``sync_cache.py``.  Once the mirror exists the submodule is initialized
with its ``submodule.<path>.url`` rewritten to the local mirror, then checked
out at the pinned commit.  A submodule already at the pinned commit -- or at a
clean commit **on top of** it, which is what applying a submodule patch set
leaves behind (docs/Process-01 §14) -- is left alone, so re-running ``make
fetch`` is a no-op and never discards a local patch commit.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHA1 = re.compile(r"^[0-9a-f]{40}$")
SUBMODULE_MIRROR_DIR = "submodules"


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


def sanitize_submodule_path(path: str) -> str:
    """Derive the mirror name of a submodule from its path (deterministic).

    ``generators/testchipip`` -> ``generators__testchipip``.  The whole path is
    used, not the basename: nested submodules in different parents (e.g. the
    several ``fixedpoint`` / ``cde`` copies) must not share one mirror.
    """
    clean = path.strip("/")
    if not clean or clean != path:
        raise SystemExit(f"fetch: invalid submodule path {path!r}")
    return clean.replace("/", "__")


def load_submodule_lock(relpath: str, component: str) -> list[dict]:
    """Read the required (``lite`` or ``dadao_extra``) entries of a lock."""
    path = ROOT / relpath
    if not path.is_file():
        raise SystemExit(f"fetch: {component}: submodule_lock {relpath} does not exist")
    try:
        with path.open("rb") as stream:
            data = tomllib.load(stream)
    except tomllib.TOMLDecodeError as exc:
        raise SystemExit(f"fetch: cannot parse {relpath}: {exc}") from exc
    entries: list[dict] = []
    for entry in data.get("submodule", []):
        if not (entry.get("lite") or entry.get("dadao_extra")):
            continue
        spath = entry.get("path", "")
        url = entry.get("url", "")
        commit = entry.get("commit", "")
        if not spath or not url or not SHA1.fullmatch(commit):
            raise SystemExit(
                f"fetch: {relpath}: required submodule {spath!r} needs a full "
                "path/url/commit"
            )
        entries.append({"path": spath, "url": url, "commit": commit})
    if not entries:
        raise SystemExit(
            f"fetch: {relpath}: no lite = true / dadao_extra = true submodule"
        )
    return entries


def submodule_mirror(mirror_root: Path, submodule_path: str) -> Path:
    return mirror_root / SUBMODULE_MIRROR_DIR / (
        sanitize_submodule_path(submodule_path) + ".git"
    )


def missing_mirror_error(component: str, sub_path: str, mirror: Path) -> str:
    return (
        f"fetch: {component}: submodule {sub_path}: mirror {mirror} is missing\n"
        "       build nodes must not clone from GitHub; copy .cache/submodules "
        "from the master first\n"
        "       (master: python3 tools/infra/sync_cache.py --hosts <node> "
        "--repo <node repo>; or populate it here with "
        "`fetch.py --populate-submodules` while online)"
    )


def clone_mirror(mirror: Path, url: str, retries: int, label: str) -> None:
    """``git clone --mirror`` with a small, recorded retry budget."""
    attempts = max(1, retries)
    last_rc = 0
    for attempt in range(1, attempts + 1):
        proc = subprocess.run(["git", "clone", "--mirror", url, str(mirror)])
        if proc.returncode == 0:
            print(f"fetch: submodule mirror {label} cloned (attempt {attempt}/{attempts})")
            return
        last_rc = proc.returncode
        print(
            f"fetch: submodule mirror {label} clone failed "
            f"(attempt {attempt}/{attempts}, rc={last_rc})"
        )
        shutil.rmtree(mirror, ignore_errors=True)
    raise SystemExit(
        f"fetch: cannot clone submodule mirror {mirror} from {url} "
        f"after {attempts} attempt(s), last rc={last_rc}"
    )


def prepare_submodule_mirror(
    component: str,
    entry: dict,
    mirror_root: Path,
    populate: bool,
    retries: int,
) -> Path:
    """Make sure the required submodule's bare mirror holds the pinned commit."""
    mirror = submodule_mirror(mirror_root, entry["path"])
    commit = entry["commit"]
    if not mirror.exists():
        if not populate:
            raise SystemExit(missing_mirror_error(component, entry["path"], mirror))
        mirror.parent.mkdir(parents=True, exist_ok=True)
        clone_mirror(mirror, entry["url"], retries, mirror.name)
    if has_commit(mirror, commit):
        print(f"fetch: submodule mirror {mirror.name} has {commit[:12]}")
        return mirror
    if populate:
        attempts = max(1, retries)
        for attempt in range(1, attempts + 1):
            rc = subprocess.run(["git", "-C", str(mirror), "fetch", "--prune"]).returncode
            if rc == 0 or has_commit(mirror, commit):
                break
            print(
                f"fetch: submodule mirror {mirror.name} fetch failed "
                f"(attempt {attempt}/{attempts}, rc={rc})"
            )
    if not has_commit(mirror, commit):
        raise SystemExit(
            f"fetch: {component}: submodule {entry['path']}: mirror {mirror} "
            f"lacks pinned commit {commit}\n"
            "       the mirror is stale; re-sync .cache/submodules from the "
            "master, or refresh it online with `fetch.py --populate-submodules`"
        )
    print(f"fetch: submodule mirror {mirror.name} updated")
    return mirror


def submodule_worktree(target: Path, sub_path: str) -> Path:
    return target / sub_path


def rev_parse(repo: Path) -> str:
    """``rev-parse HEAD`` that tolerates an unpopulated/broken repository."""
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    )
    return proc.stdout.strip() if proc.returncode == 0 else ""


def submodule_ready(target: Path, sub_path: str, commit: str) -> tuple[bool, str]:
    """``(ready, detail)`` for one checked-out submodule.

    Ready means the submodule must be left alone, namely either

    * ``HEAD == commit`` (the pinned snapshot), or
    * ``HEAD`` is **ahead of** ``commit`` and clean -- the state
      ``apply_series.py`` leaves behind after applying that submodule's patch
      set: its own local ``base+1`` commit (docs/Process-01 §14).  Checking the
      pinned commit out over it would silently discard that commit, exactly
      like the top-level rule in ``sync_component``.

    An empty/broken module git dir (e.g. an aborted clone leaves only
    ``.git/modules/<path>`` without any object) is reported as not ready
    instead of raising, so the next step can seed it from the local mirror.
    """
    work = submodule_worktree(target, sub_path)
    if not (work / ".git").exists():
        return False, "not checked out"
    head = rev_parse(work)
    if not head:
        return False, "HEAD unreadable (empty or damaged checkout)"
    if head != commit:
        ancestor = subprocess.run(
            ["git", "-C", str(work), "merge-base", "--is-ancestor", commit, "HEAD"],
            capture_output=True,
            text=True,
        ).returncode == 0
        if not ancestor:
            return False, f"HEAD {head[:12]} != {commit[:12]}"
        dirty = subprocess.run(
            ["git", "-C", str(work), "status", "--porcelain=v1"],
            capture_output=True,
            text=True,
        )
        if dirty.returncode != 0 or dirty.stdout.strip():
            return False, f"HEAD {head[:12]} is ahead of {commit[:12]} but dirty"
        return True, f"locally patched HEAD {head[:12]} (base {commit[:12]})"
    return True, head


def init_component_submodules(
    component: str,
    target: Path,
    entries: list[dict],
    mirror_root: Path,
    populate: bool,
    retries: int,
) -> None:
    """Check out every required (``lite`` / ``dadao_extra``) submodule from the
    local mirrors."""
    # Refuse before touching anything if a mirror is missing: a partial init
    # would leave the checkout in a state the next run has to repair.
    mirrors = {
        entry["path"]: prepare_submodule_mirror(
            component, entry, mirror_root, populate, retries
        )
        for entry in entries
    }
    for entry in entries:
        sub_path, commit = entry["path"], entry["commit"]
        # ``resolve()`` keeps the URL recorded in .git/config stable when the
        # repository is driven through a worktree whose .cache is a symlink.
        mirror = mirrors[sub_path].resolve()
        ready, detail = submodule_ready(target, sub_path, commit)
        if ready:
            print(
                f"fetch: {component} submodule {sub_path} already initialized "
                f"({detail})"
            )
            continue
        work = submodule_worktree(target, sub_path)
        run("git", "-C", str(target), "submodule", "init", "--", sub_path)
        run(
            "git",
            "-C",
            str(target),
            "config",
            f"submodule.{sub_path}.url",
            str(mirror),
        )
        if (work / ".git").exists():
            dirty = subprocess.run(
                ["git", "-C", str(work), "status", "--porcelain=v1"],
                capture_output=True, text=True,
            )
            if dirty.returncode == 0 and dirty.stdout.strip():
                raise SystemExit(
                    f"fetch: {component} submodule {sub_path} is at {detail} "
                    "and dirty; refusing to overwrite local changes"
                )
            # Reused module: point its origin at the local mirror and seed the
            # object store from it, so nothing that follows can go online.
            subprocess.run(
                ["git", "-C", str(work), "config", "remote.origin.url", str(mirror)],
                stdout=subprocess.DEVNULL,
            )
            run("git", "-C", str(work), "fetch", "--no-tags", str(mirror), commit)
            # Checked out here rather than by ``submodule update``: an
            # interrupted clone leaves ``.git/modules/<path>`` without any
            # HEAD, and update then dies with "unable to find current
            # revision".  The commit objects are already seeded above, so a
            # direct detached checkout reaches the same state update would.
            run("git", "-C", str(work), "checkout", "--detach", commit)
        else:
            # git >= 2.38 refuses the ``file`` transport for submodule clones
            # (``transport 'file' not allowed``); reading a submodule straight
            # out of the local mirror is exactly what a build node must do, so
            # the permission is granted for this one command, not globally.
            run(
                "git", "-c", "protocol.file.allow=always", "-C", str(target),
                "submodule", "update", "--init", "--checkout", "--", sub_path,
            )
        head = rev_parse(work)
        if head != commit:
            raise SystemExit(
                f"fetch: {component} submodule {sub_path}: HEAD {head} after "
                f"update, expected {commit}"
            )
        print(f"fetch: {component} submodule {sub_path} -> {commit}")


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


def sync_component(component: dict, source_root: Path, mirror_root: Path) -> Path:
    """Mirror + worktree for one component; returns the worktree path."""
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
        return target

    # Fetching first (safe: never touches the working tree/HEAD) makes the
    # pinned commit available locally for the ancestor check below, even
    # on a component that was already fetched+patched in a prior run.
    run("git", "fetch", "--no-tags", "origin", commit, cwd=target)

    head = head_of(target)
    if head == commit:
        # HEAD is exactly the pinned base commit.  Under commit-based patch
        # application (E5, see docs/Process-01-组件补丁组织与构建编排.md)
        # applying the series creates a local base+1 commit, so a clean
        # worktree at base means "already fetched, not yet patched" (this
        # is also the fresh-clone state).  Either way there is nothing to
        # do here: leave it alone.
        print(f"fetch: {name} already at {commit}")
        return target
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
        return target

    # Only here is `git checkout --detach` about to discard work, so only
    # here must a dirty worktree be refused.
    dirty = subprocess.check_output(
        ["git", "-C", str(target), "status", "--porcelain=v1"], text=True
    )
    if dirty:
        raise SystemExit(f"fetch: {target} is dirty; refusing to overwrite")

    run("git", "checkout", "--detach", commit, cwd=target)
    print(f"fetch: {name} -> {commit}")
    return target


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="mirror the pinned components/submodules into .cache/ and "
                    "build their .work/source worktrees (offline after the first run)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--populate-submodules",
        action="store_true",
        help="create/refresh missing .cache/submodules/*.git mirrors from their "
             "upstream URLs (network; master only). Without it a missing "
             "submodule mirror is a hard error pointing at sync_cache.py",
    )
    parser.add_argument(
        "--submodule-retries",
        type=int,
        default=3,
        help="clone/fetch attempts per submodule mirror (default: 3)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
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
        target = sync_component(component, source_root, mirror_root)
        lock = component.get("submodule_lock")
        if lock:
            init_component_submodules(
                name,
                target,
                load_submodule_lock(lock, name),
                mirror_root,
                populate=args.populate_submodules,
                retries=args.submodule_retries,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
