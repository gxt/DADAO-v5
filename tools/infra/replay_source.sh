#!/usr/bin/env bash
# Replay a component's master patch set into the SHARED source tree.
#
# This is the merge action's tool (main session), not a task tool:
#   merge components/<c>/patches -> tools/infra/replay_source.sh <component>
# so that ".work/source/<c> == master patch set" remains an invariant
# (m20-infra-003, user ruling 2026-11-28).
#
# Steps per component (and per declared submodule patch set):
#   1. git reset --hard <manifest base>
#   2. apply_series.py --component <component>   (DADAO_SHARED_SOURCE_OWNER=main-session)
#   3. check_patch_tree.py --source-state <component>
#
# Usage:
#   tools/infra/replay_source.sh <component>
#
# Any step failing stops the replay with its own exit code.  Tasks must never
# run this: use tools/infra/private_source.sh <component> <task-id> instead.
set -euo pipefail

usage() {
  echo "usage: tools/infra/replay_source.sh <component>" >&2
  exit 2
}

if [ "$#" -ne 1 ]; then
  usage
fi

COMPONENT=$1
PYTHON=${PYTHON:-python3}
REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)

# shellcheck disable=SC2046
read -r WORK_ROOT BASE < <(
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
    raise SystemExit(f"replay-source: unknown component {name!r}")
if not component.get("enabled"):
    raise SystemExit(f"replay-source: component {name!r} is not enabled")
if component.get("patchless"):
    raise SystemExit(f"replay-source: component {name!r} is patchless; nothing to replay")
commit = component.get("commit", "")
if len(commit) != 40:
    raise SystemExit(f"replay-source: component {name!r} has no pinned 40-char commit")
print(manifest.get("work_root", ".work"), commit)
PY
) || exit $?

SHARED_ROOT="$REPO/$WORK_ROOT/source"
SOURCE="$SHARED_ROOT/$COMPONENT"

# Replay writes the shared root only.  A DADAO_SOURCE_ROOT override that points
# elsewhere is a private tree and must not be reset by the merge tool.
if [ -n "${DADAO_SOURCE_ROOT:-}" ]; then
  "$PYTHON" - "$REPO" "${DADAO_SOURCE_ROOT}" "$SHARED_ROOT" <<'PY'
import sys
from pathlib import Path

repo = Path(sys.argv[1])
override = Path(sys.argv[2])
override = override if override.is_absolute() else repo / override
if override.resolve() != Path(sys.argv[3]).resolve():
    raise SystemExit(
        f"replay-source: DADAO_SOURCE_ROOT={override} is not the shared root "
        f"{sys.argv[3]}; refusing to reset a private tree"
    )
PY
fi

if [ ! -d "$SOURCE/.git" ]; then
  echo "replay-source: missing shared source $SOURCE — run 'make fetch' first" >&2
  exit 1
fi

# Submodule patch sets have their own base: reset them too, or apply_series
# refuses a stale base+1 whose content no longer matches the new patch set.
SUBS=$(
  "$PYTHON" - "$REPO" "$COMPONENT" <<'PY'
import sys
from pathlib import Path

repo = Path(sys.argv[1])
name = sys.argv[2]
sys.path.insert(0, str(repo / "tools" / "infra"))
import submodule_patches  # noqa: E402
import tomllib  # noqa: E402

with (repo / "manifests/components.lock.toml").open("rb") as stream:
    manifest = tomllib.load(stream)
component = next(c for c in manifest.get("component", []) if c.get("name") == name)
for entry in submodule_patches.patch_sets(component):
    print(entry["path"], submodule_patches.base_commit(component, entry["path"]), sep="\t")
PY
) || exit $?
while IFS=$'\t' read -r SUB_PATH SUB_BASE; do
  [ -n "$SUB_PATH" ] || continue
  SUB_SRC="$SOURCE/$SUB_PATH"
  # 子模块的 .git 是**文件**（gitlink），不是目录 ⇒ 用 -e 判存在。
  if [ ! -e "$SUB_SRC/.git" ]; then
    echo "replay-source: $COMPONENT submodule $SUB_PATH is not checked out — run 'make fetch' first" >&2
    exit 1
  fi
  echo "replay-source: reset --hard $SUB_PATH ${SUB_BASE:0:12}"
  git -C "$SUB_SRC" reset --hard "$SUB_BASE"
done <<< "$SUBS"

echo "replay-source: reset --hard $COMPONENT ${BASE:0:12}"
git -C "$SOURCE" reset --hard "$BASE"

echo "replay-source: applying master patch set (shared-tree credential)"
DADAO_SHARED_SOURCE_OWNER=main-session \
  "$PYTHON" "$REPO/tools/infra/apply_series.py" --component "$COMPONENT"

echo "replay-source: checking E1 for $COMPONENT"
"$PYTHON" "$REPO/tools/infra/check_patch_tree.py" --source-state "$COMPONENT"

echo "replay-source: OK: shared $COMPONENT tree == master patch set"
