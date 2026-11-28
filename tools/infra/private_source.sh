#!/usr/bin/env bash
# Create/refresh a task's PRIVATE component source tree and apply its patch set.
#
# Why (m20-infra-003, user ruling 2026-11-28): the shared checkout
# <work_root>/source/<component> is written only by the merge action (main
# session).  A task must apply/export/build in its own tree, so that
# "shared tree == master patch set" stays true and check-patch-tree ⑥/⑨ do not
# drift because a task wrote the shared tree.
#
# Usage:
#   tools/infra/private_source.sh <component> <task-id>
#
# Creates <work_root>/private/<task-id>/source/<component> from
# .cache/<component>.git (git clone --shared, checked out at the manifest base),
# initialises the declared submodules from their local mirrors, then runs
#   apply_series.py --component <component> --source <tree>
# (idempotent: an already converged tree is left alone).
#
# It only PRINTS the variables to export -- it never edits your shell.  Re-running
# with the same arguments reuses the tree and re-applies idempotently.
set -euo pipefail

usage() {
  echo "usage: tools/infra/private_source.sh <component> <task-id>" >&2
  exit 2
}

if [ "$#" -ne 2 ]; then
  usage
fi

COMPONENT=$1
TASK_ID=$2
PYTHON=${PYTHON:-python3}

case "$TASK_ID" in
  *[!A-Za-z0-9._-]*|'')
    echo "private-source: invalid task-id '$TASK_ID' (use [A-Za-z0-9._-]+)" >&2
    exit 2
    ;;
esac

REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)

# Manifest is the single source of truth for the base commit and work root.
# shellcheck disable=SC2046
read -r WORK_ROOT BASE SHARED_ROOT < <(
  "$PYTHON" - "$REPO" "$COMPONENT" <<'PY'
import sys
import tomllib
from pathlib import Path

repo = Path(sys.argv[1])
name = sys.argv[2]
with (repo / "manifests/components.lock.toml").open("rb") as stream:
    manifest = tomllib.load(stream)
component = next((c for c in manifest.get("component", []) if c.get("name") == name), None)
if component is None:
    raise SystemExit(f"private-source: unknown component {name!r}")
if not component.get("enabled"):
    raise SystemExit(f"private-source: component {name!r} is not enabled")
commit = component.get("commit", "")
if len(commit) != 40:
    raise SystemExit(f"private-source: component {name!r} has no pinned 40-char commit")
work_root = manifest.get("work_root", ".work")
print(work_root, commit, f"{work_root}/source")
PY
) || exit $?

PRIVATE_ROOT="$REPO/$WORK_ROOT/private/$TASK_ID"
PRIVATE_SOURCE="$PRIVATE_ROOT/source/$COMPONENT"
PRIVATE_BUILD="$PRIVATE_ROOT/build/$COMPONENT"
MIRROR="$REPO/.cache/$COMPONENT.git"

# Refuse any target that resolves into the shared root (symlinks included).
"$PYTHON" - "$PRIVATE_SOURCE" "$REPO/$SHARED_ROOT" <<'PY'
import sys
from pathlib import Path

target = Path(sys.argv[1]).resolve()
shared = Path(sys.argv[2]).resolve()
if target == shared or shared in target.parents:
    raise SystemExit(
        f"private-source: refusing to create the private tree inside the "
        f"shared root {shared}: {target}"
    )
PY

if [ ! -d "$MIRROR" ]; then
  echo "private-source: missing mirror $MIRROR — run 'make fetch' on the controller first" >&2
  exit 1
fi

if [ -e "$PRIVATE_SOURCE" ] && [ ! -d "$PRIVATE_SOURCE/.git" ]; then
  echo "private-source: $PRIVATE_SOURCE exists but is not a git worktree; refusing to touch it" >&2
  exit 1
fi

mkdir -p "$PRIVATE_ROOT/source" "$PRIVATE_BUILD"

if [ ! -d "$PRIVATE_SOURCE/.git" ]; then
  echo "private-source: cloning $MIRROR -> $PRIVATE_SOURCE (base ${BASE:0:12})"
  git clone --shared --no-checkout "$MIRROR" "$PRIVATE_SOURCE"
  git -C "$PRIVATE_SOURCE" checkout --detach "$BASE"
else
  echo "private-source: reusing $PRIVATE_SOURCE"
fi

# Submodule components (chipyard): check out the declared submodules from the
# local mirrors, reusing fetch.py's implementation (no second copy of that
# logic).  A component without submodule_lock is a no-op here.
"$PYTHON" - "$REPO" "$COMPONENT" "$PRIVATE_SOURCE" <<'PY' || exit $?
import sys
from pathlib import Path

repo = Path(sys.argv[1])
name = sys.argv[2]
source = Path(sys.argv[3])
sys.path.insert(0, str(repo / "tools" / "infra"))
import fetch  # noqa: E402
import tomllib  # noqa: E402

with (repo / "manifests/components.lock.toml").open("rb") as stream:
    manifest = tomllib.load(stream)
component = next(c for c in manifest.get("component", []) if c.get("name") == name)
lock = component.get("submodule_lock")
if lock:
    entries = fetch.load_submodule_lock(lock, name)
    fetch.init_component_submodules(
        name, source, entries, repo / ".cache", populate=False, retries=3
    )
PY

echo "private-source: applying the manifest patch set into the private tree"
"$PYTHON" "$REPO/tools/infra/apply_series.py" --component "$COMPONENT" --source "$PRIVATE_SOURCE"

cat <<EOF

private-source: ready (shared tree untouched).
  export DADAO_SOURCE_ROOT="$PRIVATE_ROOT/source"
EOF

case "$COMPONENT" in
  linux)
    cat <<EOF
  export DADAO_LINUX_SOURCE="$PRIVATE_SOURCE"
  export DADAO_LINUX_BUILD="$PRIVATE_BUILD"
EOF
    ;;
esac

cat <<EOF

Suggested build commands (Makefile derives QEMU_SRC/GEM5_SRC/LLVM_SRC from
DADAO_SOURCE_ROOT; the *_BUILD variables are private so shared build trees are
not overwritten):
  make build-qemu QEMU_BUILD="$PRIVATE_ROOT/build/qemu" JOBS=32
  make build-gem5 GEM5_BUILD="$PRIVATE_ROOT/build/gem5" JOBS=32
  make build-mc LLVM_BUILD="$PRIVATE_ROOT/build/llvm" JOBS=32

Apply/export in this tree:
  python3 tools/infra/apply_series.py --component $COMPONENT --source "$PRIVATE_SOURCE"
  python3 tools/infra/make_patch.py $COMPONENT --source "$PRIVATE_SOURCE"

NOTE: the musl/picolibc/busybox builds and the chipyard test harness still
resolve the shared .work/source/<c> directly; their private-tree override is not
part of m20-infra-003 (see the task's completion notes).  Apply/export in this
private tree works; build those components from a private worktree instead.
EOF
