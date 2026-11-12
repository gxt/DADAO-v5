#!/usr/bin/env bash
set -euo pipefail

root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
work_root=${TMPDIR:-/tmp}/opencode/RTL-004t
lock_file="$work_root/rtl-negative.lock"

mkdir -p "$work_root"
if ! command -v flock >/dev/null 2>&1; then
  echo "rtl-tree-negative: flock(2) command is unavailable" >&2
  exit 69
fi

exec 9>"$lock_file"
if ! flock -n 9; then
  echo "rtl-tree-negative: another run holds $lock_file" >&2
  exit 75
fi

work=$(mktemp -d "$work_root/rtl-negative.XXXXXX")

cleanup() {
  if [[ -n "${work:-}" && -d "$work" ]]; then
    rm -rf "$work"
  fi
}
trap cleanup EXIT INT TERM HUP

python3 "$root/tools/rtl/check_rtl_tree.py" > "$work/baseline.log" 2>&1
echo "NEGATIVE BASELINE: PASS"

prepare_repo() {
  local repo=$1

  mkdir -p "$repo/rtl/dadao" "$repo/tools/rtl"
  cp "$root/rtl/dadao/build.sbt" "$repo/rtl/dadao/build.sbt"
  cp -a "$root/rtl/dadao/project" "$repo/rtl/dadao/project"
  cp -a "$root/rtl/dadao/src" "$repo/rtl/dadao/src"
  cp "$root/tools/rtl/check_rtl_tree.py" \
    "$repo/tools/rtl/check_rtl_tree.py"
}

run_negative() {
  local label=$1
  local relative=$2
  local sed_expression=$3
  local repo="$work/$label"
  local log="$work/$label.log"

  prepare_repo "$repo"
  sed -i "$sed_expression" "$repo/$relative"
  set +e
  python3 "$repo/tools/rtl/check_rtl_tree.py" > "$log" 2>&1
  local rc=$?
  set -e

  if [[ $rc -eq 0 ]]; then
    echo "NEGATIVE FAIL (unexpected pass): $label" >&2
    cat "$log" >&2
    return 1
  fi
  echo "NEGATIVE OK: $label exit=$rc"
  head -n 4 "$log"
}

elaborator=rtl/dadao/src/main/scala/dadao/DADAOElaborator.scala
config=rtl/dadao/src/main/scala/dadao/DADAOConfig.scala
tile=rtl/dadao/src/main/scala/dadao/DADAOTile.scala

run_negative \
  "elaborator-without-tile" \
  "$elaborator" \
  's/new DADAOTile(/DADAOTilePlaceholder(/'

run_negative \
  "config-without-tile" \
  "$config" \
  's/class WithDADAOTile/class WithDADAOTileDisabled/'

run_negative \
  "tile-class-renamed" \
  "$tile" \
  's/class DADAOTile(/class DADAOTileRenamed(/'

echo "EXIT=0"
