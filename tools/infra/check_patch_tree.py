#!/usr/bin/env python3
"""Check a component's tree-shaped patch set against spec/Process-01-组件补丁组织与构建编排.md.

Assertions (all fail-closed):

  1. every patch contains exactly one ``diff --git`` entry
  2. target paths are globally unique across the patch set
     (this is what enforces "one file, one patch" and "a new file's patch is
     its final state")
  3. ``series`` and the ``patches/`` tree agree in both directions,
     and the series is sorted lexicographically
  4. the whole set applies cleanly to the pinned base commit (checked against a
     temporary index, so the caller's worktree is not touched); skipped with a
     notice when ``.work/source/<name>`` is absent
  5. ``patches/`` is a pure mirror of the upstream tree: every file under it is
     ``<upstream-relative-path>.patch`` (the manifest list lives outside, at
     ``components/<name>/series``)
  6. content consistency: after applying the full patch set to the base commit
     via a scratch index, every affected path's blob must equal the
     corresponding file in ``.work/source/<name>``; mismatch means the patches
     do not reproduce the worktree (e.g. hand-edited ``@@`` hunk headers)
  7. (E6) ``.work/source/<name>`` worktree is clean (``git status --porcelain``
     is empty)
  8. (E6) HEAD is the pinned base plus **exactly one** commit
     (``git rev-list --count <base>..HEAD == 1``)
  9. (E6) that commit's net diff (``git diff <base> HEAD``, per path with the
     ``index`` line normalized) equals the patch set, path by path

Assertion 6 compares the *patched index* against the *worktree*; assertion 9
compares the *HEAD commit* against the *patch set*.  Both are needed: 6 catches
patches that do not reproduce the worktree, 9 catches a local commit that does
not correspond to the patch set.

``--source-state`` (E7) exposes assertions 7 and 8 alone as a module self-check
to be run before and after touching a component: it prints HEAD / commit count /
cleanliness and exits non-zero unless the E1 invariant holds.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIFF_GIT = re.compile(r"^diff --git a/(.+?) b/(.+)$")
# Same normalization as tools/infra/make_patch.py::_normalize_index.
INDEX_LINE = re.compile(r"^index [0-9a-f]+\.\.[0-9a-f]+.*$", re.MULTILINE)


def load_manifest() -> dict:
    with (ROOT / "manifests/components.lock.toml").open("rb") as stream:
        return tomllib.load(stream)


def series_entries(series_path: Path) -> list[str]:
    return [
        line.strip()
        for line in series_path.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def patch_targets(patch: Path) -> tuple[int, list[str]]:
    """Return (number of diff --git entries, target paths)."""
    entries = 0
    targets: list[str] = []
    for line in patch.read_text(encoding="utf-8", errors="replace").splitlines():
        match = DIFF_GIT.match(line)
        if match:
            entries += 1
            targets.append(match.group(2))
    return entries, targets


def normalize_index(text: str) -> str:
    """Strip ``index`` lines so ``core.abbrev`` differences do not cause noise."""
    return INDEX_LINE.sub("", text)


def git(*args: str, cwd: Path, env: dict | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        text=True,
        check=check,
        env=env,
    )


def source_state(source: Path, base: str) -> tuple[bool, int, str]:
    """Return ``(clean, commit_count, porcelain)`` for *source* against *base*.

    This is the shared E1/E7 primitive: assertions ⑦ and ⑧ and the
    ``--source-state`` self-check all read their verdict from here.
    """
    porcelain = git("status", "--porcelain", cwd=source).stdout
    clean = not porcelain.strip()
    count = git("rev-list", "--count", f"{base}..HEAD", cwd=source, check=False)
    count_value = int(count.stdout.strip() or "0") if count.returncode == 0 else -1
    return clean, count_value, porcelain


def check_source_invariant(name: str, component: dict, errors: list[str], source: Path) -> None:
    """Assertions ⑦ (clean) and ⑧ (base + exactly 1 commit)."""
    clean, count, porcelain = source_state(source, component["commit"])
    if not clean:
        errors.append(
            f"{name}: assertion ⑦: worktree is not clean (git status --porcelain):\n{porcelain.rstrip()}"
        )
    if count != 1:
        errors.append(
            f"{name}: assertion ⑧: HEAD is base+{count} (expected exactly 1 commit)"
        )


def check_commit_matches_patches(
    name: str,
    component: dict,
    entries: list[str],
    patches_dir: Path,
    errors: list[str],
    source: Path,
) -> None:
    """Assertion ⑨: ``git diff <base> HEAD`` equals the patch set, per path."""
    base = component["commit"]
    if source_state(source, base)[1] != 1:
        # ⑧ already reported the wrong count; a net diff comparison is only
        # meaningful for exactly one commit.
        return
    commit_paths = set(
        git("diff", "--name-only", base, "HEAD", cwd=source).stdout.splitlines()
    )
    patch_paths = {entry[: -len(".patch")] for entry in entries}
    for extra in sorted(commit_paths - patch_paths):
        errors.append(
            f"{name}: assertion ⑨: {extra} changed by HEAD but absent from the patch set"
        )
    for missing in sorted(patch_paths - commit_paths):
        errors.append(
            f"{name}: assertion ⑨: {missing} in the patch set but not changed by HEAD"
        )
    for entry in entries:
        rel = entry[: -len(".patch")]
        if rel not in commit_paths:
            continue
        patch_text = normalize_index((patches_dir / entry).read_text(encoding="utf-8", errors="replace"))
        head_text = normalize_index(
            git("diff", base, "HEAD", "--", rel, cwd=source).stdout
        )
        if patch_text != head_text:
            errors.append(
                f"{name}: assertion ⑨: {rel}: HEAD diff differs from {entry} "
                "(local commit does not match the patch set)"
            )


def check_component(name: str, component: dict, errors: list[str]) -> None:
    series_path = ROOT / component["patch_series"]
    patches_dir = ROOT / component["patch_dir"]
    if not series_path.exists():
        errors.append(f"{name}: missing series {series_path.relative_to(ROOT)}")
        return

    entries = series_entries(series_path)
    if not entries:
        errors.append(f"{name}: series is empty")
        return
    if entries != sorted(entries):
        errors.append(f"{name}: series is not sorted lexicographically")

    # assertion 3 (forward): every listed patch exists, and no extra files.
    listed = set()
    for item in entries:
        patch = patches_dir / item
        if not patch.is_file():
            errors.append(f"{name}: series lists missing patch {item}")
            continue
        listed.add(patch.resolve())
    on_disk = {p.resolve() for p in patches_dir.rglob("*.patch")}
    for extra in sorted(on_disk - listed):
        errors.append(f"{name}: patch not listed in series: {extra.relative_to(ROOT)}")

    # assertion 5: patches/ is a pure mirror -- every file is `<upstream>.patch`.
    for path in sorted(patches_dir.rglob("*")):
        if path.is_file() and not path.name.endswith(".patch"):
            errors.append(
                f"{name}: non-patch file under patches/: {path.relative_to(ROOT)}"
            )

    # assertions 1 & 2.
    seen: dict[str, str] = {}
    for item in entries:
        patch = patches_dir / item
        if not patch.is_file():
            continue
        count, targets = patch_targets(patch)
        if count != 1:
            errors.append(
                f"{name}: {item} contains {count} diff --git entries (expected exactly 1)"
            )
        for target in targets:
            if target in seen:
                errors.append(
                    f"{name}: target path {target} touched by both {seen[target]} and {item}"
                )
            else:
                seen[target] = item
        expected_name = f"{targets[0]}.patch" if count == 1 else None
        if expected_name is not None and item != expected_name:
            errors.append(
                f"{name}: {item} does not match its target path (expected {expected_name})"
            )

    source = ROOT / ".work" / "source" / name
    if not (source / ".git").exists():
        print(
            f"check-patch-tree: {name}: source worktree absent; "
            "skipping apply check and assertions ⑦⑧⑨"
        )
        return

    # assertions 7, 8, 9 (E6): HEAD/worktree state vs the patch set.
    check_source_invariant(name, component, errors, source)
    check_commit_matches_patches(name, component, entries, patches_dir, errors, source)

    # assertion 4: apply cleanly to the pinned base, using a scratch index.
    commit = component["commit"]
    with tempfile.TemporaryDirectory() as scratch:
        env = dict(os.environ)
        env["GIT_INDEX_FILE"] = str(Path(scratch) / "index")
        subprocess.run(
            ["git", "-C", str(source), "read-tree", commit],
            env=env, check=True, capture_output=True,
        )
        args = ["git", "-C", str(source), "apply", "--cached", "--check"]
        args += [str(patches_dir / item) for item in entries]
        result = subprocess.run(args, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            errors.append(
                f"{name}: patch set does not apply cleanly to base {commit[:12]}: "
                f"{result.stderr.strip()}"
            )
            return  # skip assertion 6 if patches don't apply

        # assertion 6: content consistency -- apply patches to scratch index,
        # then compare each affected path's blob with .work/source.
        # Re-apply with --cached (not just --check) to actually populate the index.
        subprocess.run(
            ["git", "-C", str(source), "read-tree", commit],
            env=env, check=True, capture_output=True,
        )
        apply_args = ["git", "-C", str(source), "apply", "--cached"]
        apply_args += [str(patches_dir / item) for item in entries]
        apply_result = subprocess.run(apply_args, env=env, capture_output=True, text=True)
        if apply_result.returncode != 0:
            # Should not happen since --check passed above, but be defensive.
            errors.append(
                f"{name}: scratch apply failed (assertion 6 skipped): "
                f"{apply_result.stderr.strip()}"
            )
            return

        # Collect all affected target paths from patches.
        affected_paths: list[str] = []
        for item in entries:
            patch = patches_dir / item
            if not patch.is_file():
                continue
            _count, targets = patch_targets(patch)
            affected_paths.extend(targets)

        for target_path in affected_paths:
            # Read blob from scratch index.
            idx_result = subprocess.run(
                ["git", "-C", str(source), "cat-file", "-p", f":{target_path}"],
                env=env, capture_output=True, text=True,
            )
            work_file = source / target_path
            if idx_result.returncode != 0:
                # File exists in scratch index but cat-file failed.
                errors.append(
                    f"{name}: assertion ⑥: cannot read :{target_path} from scratch index"
                )
                continue
            if not work_file.exists():
                errors.append(
                    f"{name}: assertion ⑥: {target_path} exists in patched index "
                    f"but missing from .work/source"
                )
                continue
            idx_content = idx_result.stdout
            work_content = work_file.read_text(encoding="utf-8", errors="replace")
            if idx_content != work_content:
                errors.append(
                    f"{name}: assertion ⑥: {target_path}: patched-index blob "
                    f"differs from .work/source (patch does not reproduce worktree)"
                )


def run_source_state(enabled: list[dict]) -> int:
    """E7: report the E1 invariant (clean + base+1) for each enabled component."""
    failed = False
    for component in enabled:
        name = component["name"]
        source = ROOT / ".work" / "source" / name
        if not (source / ".git").exists():
            print(f"check-patch-tree --source-state: {name}: source worktree absent; skipped")
            continue
        clean, count, porcelain = source_state(source, component["commit"])
        head = git("rev-parse", "HEAD", cwd=source).stdout.strip()
        ok = clean and count == 1
        verdict = "OK" if ok else "FAIL"
        print(
            f"check-patch-tree --source-state: {name}: {verdict} "
            f"HEAD={head[:12]} count={count} clean={clean}"
        )
        if porcelain.strip():
            print(f"check-patch-tree --source-state: {name}: dirty paths:")
            for line in porcelain.rstrip().splitlines():
                print(f"  {line}")
        if not ok:
            failed = True
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check component patch sets against spec/Process-01."
    )
    parser.add_argument(
        "--source-state",
        action="store_true",
        help="only report the E1 invariant (clean + base+1) for each component",
    )
    args = parser.parse_args()

    manifest = load_manifest()
    enabled = [c for c in manifest.get("component", []) if c.get("enabled")]
    if not enabled:
        print("check-patch-tree: no components enabled")
        return 0

    if args.source_state:
        return run_source_state(enabled)

    errors: list[str] = []
    total = 0
    for component in enabled:
        series_path = ROOT / component["patch_series"]
        if series_path.exists():
            total += len(series_entries(series_path))
        check_component(component["name"], component, errors)

    for error in errors:
        print(f"check-patch-tree: {error}", file=sys.stderr)
    if errors:
        print(f"check-patch-tree: {len(errors)} problem(s)", file=sys.stderr)
        return 1
    print(f"check-patch-tree: {len(enabled)} component(s), {total} patches OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
