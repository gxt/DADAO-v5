#!/usr/bin/env python3
"""Apply each enabled component's tree-shaped patch set with ``git apply``.

See ``docs/Process-01-组件补丁组织与构建编排.md`` (v5 spec, effective 2026-09-23).

``git apply`` is the only supported application path; authorship and commit
messages are deliberately **not** preserved inside the patches (the patch set
carries the change, not a history).  After a full application the tool does
commit locally (see below) so that the worktree stays clean and the checkout
satisfies the E1 invariant:

    .work/source/<name> is clean and sits at ``base + exactly 1 commit``.

E5 (apply side):

* accepting HEAD is relaxed to ``HEAD in {base, base+1 and that commit's content
  == patches}``; anything else is refused;
* after applying the patch set the tool runs ``git add -A`` and
  ``git commit -m "dadao: <component> patch series"``.  Identity comes from the
  existing environment/repository -- no local ``user.name``/``user.email`` is
  configured, and no ``GIT_AUTHOR_DATE``/``GIT_COMMITTER_DATE`` is set;
* re-running is idempotent: when HEAD is already ``base+1`` and its content
  matches the patch set, no second commit is produced;
* the local commit exists only to keep the worktree clean; it is **never**
  pushed upstream.

§7.x (per-patch idempotence): each patch is checked individually with
``git apply --check --reverse``.  If a patch is already applied, it is
skipped entirely (no ``git apply``, no mtime change).  Only patches that
are not yet applied get ``git apply``.

``patchless`` components (manifest flag, ADR-0024 D1) carry no patch set —
``manifest_check.py`` rejects ``patch_dir``/``patch_series`` for them — so
they are skipped explicitly (``component=<name>: patchless, skip``) instead
of raising ``KeyError``; same guard as ``check_patch_tree.py``.

Submodule patch sets (§14, rev. 2026-11-09)
-------------------------------------------
A component may declare ``[[component.submodule_patch]]`` entries (see
``tools/infra/submodule_patches.py``).  For each of them this tool

1. applies that entry's series inside the submodule worktree
   (``<source>/<submodule path>``), whose base is the commit pinned for the
   same path in the component's ``submodule_lock`` -- the submodule gets its
   **own** ``base+1`` local commit, exactly like a top-level component;
2. after all submodule sets are applied, records the resulting submodule HEADs
   as gitlink updates in the component's **own** local commit, so the parent
   worktree is clean too and ``git status`` does not report the submodule as
   modified.

Step 2 is what keeps the two invariants compatible: E1 for the component
requires a clean worktree, and a submodule commit necessarily moves the parent
gitlink.  Top-level and submodule patch sets therefore do not interfere: each
is applied, verified and committed in its own repository, and the parent only
records the resulting submodule commit.  When the component's patch set is
changed later, the documented E5 recovery (§7 补注) applies to the *parent*:
``git reset --hard <base>``, then re-run this tool (the submodule commits are
already ``base+1`` and are skipped idempotently).
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import tomllib
from pathlib import Path

import submodule_patches

ROOT = Path(__file__).resolve().parents[2]


def load_manifest() -> dict:
    with (ROOT / "manifests/components.lock.toml").open("rb") as stream:
        return tomllib.load(stream)


def git(
    *args: str,
    cwd: Path,
    check: bool = True,
    env: dict | None = None,
) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        text=True,
        check=check,
        env=env,
    )


def worktree_clean(source: Path) -> bool:
    return not git("status", "--porcelain", cwd=source).stdout.strip()


def commit_count(source: Path, base: str) -> int:
    result = git("rev-list", "--count", f"{base}..HEAD", cwd=source, check=False)
    if result.returncode != 0:
        return -1
    return int(result.stdout.strip() or "0")


def read_series(patches_dir: Path, series_path: Path) -> list[Path]:
    """Read one series file into the ordered list of patch paths."""
    return [
        patches_dir / line.strip()
        for line in series_path.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def expected_tree(
    source: Path,
    base: str,
    patch_paths: list[Path],
    gitlinks: dict[str, str] | None = None,
) -> str:
    """Tree hash obtained by applying *patch_paths* to *base* in a scratch index.

    *gitlinks* (``{submodule path: commit}``) are recorded in the same scratch
    index with ``git update-index --cacheinfo 160000,...`` -- that is what the
    parent commit of a component with submodule patch sets must contain.
    """
    with tempfile.TemporaryDirectory() as scratch:
        env = dict(os.environ)
        env["GIT_INDEX_FILE"] = str(Path(scratch) / "index")
        git("read-tree", base, cwd=source, env=env)
        if patch_paths:
            git("apply", "--cached", *[str(p) for p in patch_paths], cwd=source, env=env)
        for path, commit in (gitlinks or {}).items():
            git(
                "update-index", "--add", "--cacheinfo", f"160000,{commit},{path}",
                cwd=source, env=env,
            )
        return git("write-tree", cwd=source, env=env).stdout.strip()


def head_matches_patches(
    source: Path,
    base: str,
    patch_paths: list[Path],
    gitlinks: dict[str, str] | None = None,
) -> bool:
    """True iff HEAD == base + 1 commit whose tree equals the patched base tree."""
    if commit_count(source, base) != 1:
        return False
    head_tree = git("rev-parse", "HEAD^{tree}", cwd=source).stdout.strip()
    return head_tree == expected_tree(source, base, patch_paths, gitlinks)


def apply_patch_set(
    label: str,
    source: Path,
    base: str,
    patches: list[Path],
    gitlinks: dict[str, str] | None = None,
) -> None:
    """Apply one series inside *source* (E5) and converge to ``base+1``.

    *label* is the name used in messages and in the commit subject:
    ``<component>`` for the top level, ``<component>/<submodule path>`` for a
    submodule patch set.  *gitlinks* is only ever non-empty for the parent of a
    component that declares submodule patch sets.
    """
    head = git("rev-parse", "HEAD", cwd=source).stdout.strip()
    if head == base:
        pass  # not applied yet; fall through to the per-patch loop
    elif head_matches_patches(source, base, patches, gitlinks):
        # E5 idempotence: already applied as base+1 with matching content.
        if not worktree_clean(source):
            raise SystemExit(
                f"apply-series: {label} HEAD is already base+1 and matches the "
                "patch set, but the worktree is dirty; refusing (E1/E2)"
            )
        print(f"apply-series: {label} already applied (base+1, matches patches); skipped")
        return
    else:
        raise SystemExit(
            f"apply-series: {label} HEAD ({head[:12]}) is neither base "
            f"({base[:12]}) nor base+1 matching the patch set; refusing to apply"
        )

    if not patches and not gitlinks:
        print(f"apply-series: {label} has an empty series")
        return

    # §7.x: per-patch idempotence
    skipped = 0
    applied = 0
    for patch in patches:
        # Check if already applied (reverse check)
        if git("apply", "--check", "--reverse", str(patch), cwd=source, check=False).returncode == 0:
            skipped += 1
            continue
        # Not yet applied: forward check then apply
        result = git("apply", "--check", str(patch), cwd=source, check=False)
        if result.returncode != 0:
            raise SystemExit(
                f"apply-series: {label}: patch does not apply cleanly: "
                f"{patch.relative_to(ROOT)}\n{result.stderr.strip()}"
            )
        git("apply", str(patch), cwd=source)
        applied += 1

    # E5: commit so the worktree ends clean at base+1.  Refuse to commit
    # anything that is not exactly the patch set (plus the recorded submodule
    # commits, for a component that carries submodule patch sets).
    git("add", "-A", cwd=source)
    staged_tree = git("write-tree", cwd=source).stdout.strip()
    want_tree = expected_tree(source, base, patches, gitlinks)
    if staged_tree != want_tree:
        git("reset", "-q", cwd=source)
        raise SystemExit(
            f"apply-series: {label}: worktree after applying patches does not "
            "equal the patch set; refusing to commit"
        )
    git("commit", "-q", "-m", f"dadao: {label} patch series", cwd=source)

    print(
        f"apply-series: {label} {applied} applied, {skipped} skipped (already applied); "
        f"committed 'dadao: {label} patch series'"
    )


def main() -> int:
    manifest = load_manifest()
    enabled = [c for c in manifest.get("component", []) if c.get("enabled")]
    if not enabled:
        print("apply-series: no components enabled")
        return 0

    source_root = ROOT / manifest.get("work_root", ".work") / "source"
    for component in enabled:
        name = component["name"]
        if component.get("patchless"):
            # Reference-only component (ADR-0024 D1): explicitly carries no v5
            # patch set, so there is nothing to apply.  `manifest_check.py`
            # rejects patch_dir/patch_series for this component, hence the
            # guards below must not read them.  Same handling as
            # check_patch_tree.py (`patchless; skipped`) — never silent.
            print(f"apply-series: component={name}: patchless, skip")
            continue
        base = component["commit"]
        source = source_root / name
        if not (source / ".git").exists():
            raise SystemExit(f"apply-series: missing source {source}; run make fetch")

        # Submodule patch sets first: the parent gitlink recorded below is the
        # submodule HEAD *after* its own series has been applied and committed.
        submodule_sets = submodule_patches.patch_sets(component)
        for entry in submodule_sets:
            sub_path = entry["path"]
            sub_source = submodule_patches.worktree(source, sub_path)
            if not (sub_source / ".git").exists():
                raise SystemExit(
                    f"apply-series: {name}: submodule {sub_path} is not checked "
                    "out; run make fetch"
                )
            apply_patch_set(
                f"{name}/{sub_path}",
                sub_source,
                submodule_patches.base_commit(component, sub_path),
                read_series(ROOT / entry["patch_dir"], ROOT / entry["patch_series"]),
            )

        gitlinks = {
            entry["path"]: git(
                "rev-parse", "HEAD",
                cwd=submodule_patches.worktree(source, entry["path"]),
            ).stdout.strip()
            for entry in submodule_sets
        }
        patches = (
            read_series(ROOT / component["patch_dir"], ROOT / component["patch_series"])
            if component.get("patch_series")
            else []
        )
        apply_patch_set(name, source, base, patches, gitlinks)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
