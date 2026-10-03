#!/usr/bin/env python3
"""Apply each enabled component's tree-shaped patch set with ``git apply``.

See ``spec/Process-01-组件补丁组织与构建编排.md`` (v5 spec, effective 2026-09-23).

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
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import tomllib
from pathlib import Path

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


def expected_tree(source: Path, base: str, patch_paths: list[Path]) -> str:
    """Tree hash obtained by applying *patch_paths* to *base* in a scratch index."""
    with tempfile.TemporaryDirectory() as scratch:
        env = dict(os.environ)
        env["GIT_INDEX_FILE"] = str(Path(scratch) / "index")
        git("read-tree", base, cwd=source, env=env)
        if patch_paths:
            git("apply", "--cached", *[str(p) for p in patch_paths], cwd=source, env=env)
        return git("write-tree", cwd=source, env=env).stdout.strip()


def head_matches_patches(source: Path, base: str, patch_paths: list[Path]) -> bool:
    """True iff HEAD == base + 1 commit whose tree equals the patched base tree."""
    if commit_count(source, base) != 1:
        return False
    head_tree = git("rev-parse", "HEAD^{tree}", cwd=source).stdout.strip()
    return head_tree == expected_tree(source, base, patch_paths)


def main() -> int:
    manifest = load_manifest()
    enabled = [c for c in manifest.get("component", []) if c.get("enabled")]
    if not enabled:
        print("apply-series: no components enabled")
        return 0

    source_root = ROOT / manifest.get("work_root", ".work") / "source"
    for component in enabled:
        name = component["name"]
        base = component["commit"]
        source = source_root / name
        if not (source / ".git").exists():
            raise SystemExit(f"apply-series: missing source {source}; run make fetch")

        patches_dir = ROOT / component["patch_dir"]
        series_path = ROOT / component["patch_series"]
        patches = [
            patches_dir / line.strip()
            for line in series_path.read_text().splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]

        head = git("rev-parse", "HEAD", cwd=source).stdout.strip()
        if head == base:
            pass  # not applied yet; fall through to the per-patch loop
        elif head_matches_patches(source, base, patches):
            # E5 idempotence: already applied as base+1 with matching content.
            if not worktree_clean(source):
                raise SystemExit(
                    f"apply-series: {name} HEAD is already base+1 and matches the "
                    "patch set, but the worktree is dirty; refusing (E1/E2)"
                )
            print(f"apply-series: {name} already applied (base+1, matches patches); skipped")
            continue
        else:
            raise SystemExit(
                f"apply-series: {name} HEAD ({head[:12]}) is neither base "
                f"({base[:12]}) nor base+1 matching the patch set; refusing to apply"
            )

        if not patches:
            print(f"apply-series: {name} has an empty series")
            continue

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
                    f"apply-series: {name}: patch does not apply cleanly: "
                    f"{patch.relative_to(ROOT)}\n{result.stderr.strip()}"
                )
            git("apply", str(patch), cwd=source)
            applied += 1

        # E5: commit so the worktree ends clean at base+1.  Refuse to commit
        # anything that is not exactly the patch set.
        git("add", "-A", cwd=source)
        staged_tree = git("write-tree", cwd=source).stdout.strip()
        want_tree = expected_tree(source, base, patches)
        if staged_tree != want_tree:
            git("reset", "-q", cwd=source)
            raise SystemExit(
                f"apply-series: {name}: worktree after applying patches does not "
                "equal the patch set; refusing to commit"
            )
        git("commit", "-q", "-m", f"dadao: {name} patch series", cwd=source)

        print(
            f"apply-series: {name} {applied} applied, {skipped} skipped (already applied); "
            f"committed 'dadao: {name} patch series'"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
