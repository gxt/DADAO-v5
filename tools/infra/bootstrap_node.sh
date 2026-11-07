#!/usr/bin/env bash
# bootstrap_node.sh — idempotently bring a DADAO-v5 build node from a bare
# checkout to a green `make check`.
#
# The script never installs packages and never contacts GitHub directly: the
# repository is sourced from a local git bundle or an existing local checkout
# (see --bundle / --source-repo), and components are fetched from the local
# `.cache/*.git` mirrors by `make fetch`.
#
# Step order is deliberate:
#   1 preflight   2 git identity   3 repository sync   4 make fetch
#   5 make apply-series (must precede install-host)   6 compiler-rt build tree
#   7 make install-host   8 make check
#
# Step 6 needs the build-tree clang; when the host LLVM build tree is still
# absent that step builds it with `make build-mc build-lld` first (install-host
# cannot bootstrap its own compiler-rt dependency).  Both calls are idempotent.
#
# Every step prints `[step N] ...` and `rc=`.  A failing step stops the run and
# shows the last 40 log lines.  `--dry-run` prints the commands only.
#
# Usage:
#   tools/infra/bootstrap_node.sh [options]
#
# Options:
#   --repo-dir PATH     repository to bootstrap (default: the checkout holding
#                       this script)
#   --bundle PATH       local git bundle to clone/fetch from (no network)
#   --source-repo PATH  existing local repository to clone/fetch from
#   --git-name NAME     git user.name  (fallback: $DADAO_GIT_NAME)
#   --git-email EMAIL   git user.email (fallback: $DADAO_GIT_EMAIL)
#   --jobs N            make -j N (default: 8, matching the repo default)
#   --dry-run           print planned commands, execute nothing
#   -h, --help          show this help and exit 0
#
# Node identity (host names, accounts, keys, known_hosts) is deliberately not
# part of this script; it comes from the calling environment.

set -uo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_REPO_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"

REPO_DIR="$DEFAULT_REPO_DIR"
BUNDLE=""
SOURCE_REPO=""
GIT_NAME_ARG=""
GIT_EMAIL_ARG=""
JOBS="${JOBS:-8}"
DRY_RUN=0

usage() {
  awk 'NR > 1 && /^set -uo pipefail/ { exit } NR > 1 { sub(/^# ?/, ""); print }' "${BASH_SOURCE[0]}"
}

die() {
  printf 'bootstrap_node: ERROR: %s\n' "$*" >&2
  exit 2
}

say() {
  printf '%s\n' "$*"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --repo-dir)       [ "$#" -ge 2 ] || die "--repo-dir needs a value"; REPO_DIR="$2"; shift 2 ;;
    --bundle)         [ "$#" -ge 2 ] || die "--bundle needs a value"; BUNDLE="$2"; shift 2 ;;
    --source-repo)    [ "$#" -ge 2 ] || die "--source-repo needs a value"; SOURCE_REPO="$2"; shift 2 ;;
    --git-name)       [ "$#" -ge 2 ] || die "--git-name needs a value"; GIT_NAME_ARG="$2"; shift 2 ;;
    --git-email)      [ "$#" -ge 2 ] || die "--git-email needs a value"; GIT_EMAIL_ARG="$2"; shift 2 ;;
    --jobs)           [ "$#" -ge 2 ] || die "--jobs needs a value"; JOBS="$2"; shift 2 ;;
    --dry-run)        DRY_RUN=1; shift ;;
    -h|--help)        usage; exit 0 ;;
    *)                die "unknown argument: $1 (try --help)" ;;
  esac
done

[ -n "$JOBS" ] || die "--jobs must not be empty"

# compiler-rt standalone configuration: all knobs live here (one place).
# COMPILER_RT_TARGET must be passed as both *_COMPILER_TARGET and in the
# per-language flags: the standalone project() probe sees clang's default
# triple (`unknown`) before the target flag is applied.
COMPILER_RT_TARGET="dadao-unknown-elf"
LLVM_BUILD="$REPO_DIR/.work/build/llvm"
COMPILER_RT_BUILD="$REPO_DIR/.work/build/compiler-rt-builtins"
COMPILER_RT_SRC="$REPO_DIR/.work/source/llvm-project/compiler-rt/lib/builtins"
LOG_DIR="$REPO_DIR/.work/log/infra/INFRA-130t"

COMPILER_RT_CMAKE=(
  cmake -G Ninja
  -S "$COMPILER_RT_SRC"
  -B "$COMPILER_RT_BUILD"
  -DCMAKE_C_COMPILER="$LLVM_BUILD/bin/clang"
  -DCMAKE_CXX_COMPILER="$LLVM_BUILD/bin/clang++"
  -DCMAKE_C_COMPILER_TARGET="$COMPILER_RT_TARGET"
  -DCMAKE_CXX_COMPILER_TARGET="$COMPILER_RT_TARGET"
  -DCMAKE_C_FLAGS="--target=$COMPILER_RT_TARGET"
  -DCMAKE_CXX_FLAGS="--target=$COMPILER_RT_TARGET"
  -DCMAKE_ASM_FLAGS="--target=$COMPILER_RT_TARGET"
  -DCOMPILER_RT_DEFAULT_TARGET_ONLY=ON
  -DLLVM_ENABLE_PER_TARGET_RUNTIME_DIR=ON
  -DLLVM_CMAKE_DIR="$LLVM_BUILD/lib/cmake/llvm"
  -DCMAKE_BUILD_TYPE=Release
  -DCMAKE_AR="$(command -v ar 2>/dev/null || true)"
  -DCMAKE_RANLIB="$(command -v ranlib 2>/dev/null || true)"
  -DCMAKE_NM="$(command -v nm 2>/dev/null || true)"
)

step_header() {
  printf '[step %s] %s\n' "$1" "$2"
}

# run_logged STEP LOG_SUFFIX COMMAND...
# Runs COMMAND with output captured to $LOG_DIR/INFRA-130t-bootstrap-<suffix>.log
# and returns its exit status; on failure prints the last 40 log lines.
run_logged() {
  local step="$1" suffix="$2"
  shift 2
  local log="$LOG_DIR/INFRA-130t-bootstrap-${suffix}.log"
  mkdir -p "$LOG_DIR"
  printf '### %s\n' "$*" >"$log"
  printf '[step %s] cmd: %s\n' "$step" "$*"
  "$@" >>"$log" 2>&1
  local rc=$?
  if [ "$rc" -ne 0 ]; then
    printf '[step %s] rc=%s\n' "$step" "$rc"
    printf '[step %s] last 40 log lines (%s):\n' "$step" "$log"
    tail -n 40 "$log" | sed 's/^/  /'
    return "$rc"
  fi
  printf '[step %s] rc=0\n' "$step"
  return 0
}

# ---------------------------------------------------------------- dry run
if [ "$DRY_RUN" -eq 1 ]; then
  step_header 1 "preflight: report missing tools/packages (dry-run: not probed)"
  say '[step 1] rc=0 (dry-run)'
  step_header 2 "git identity: configure user.name/user.email when unset (dry-run)"
  say '[step 2] expected command: git config --global user.name <name> / git config --global user.email <email>'
  say '[step 2] rc=0 (dry-run)'
  step_header 3 "repository sync: clone/fetch from --bundle or --source-repo (dry-run)"
  if [ -n "$BUNDLE" ]; then
    say "[step 3] expected command: git clone|fetch -- $BUNDLE"
  elif [ -n "$SOURCE_REPO" ]; then
    say "[step 3] expected command: git clone|fetch -- $SOURCE_REPO"
  else
    say "[step 3] expected command: git -C $REPO_DIR rev-parse --git-dir (existing checkout)"
  fi
  say '[step 3] rc=0 (dry-run)'
  step_header 4 "fetch components from .cache/*.git"
  say "[step 4] make -C $REPO_DIR -j $JOBS fetch"
  say '[step 4] rc=0 (dry-run)'
  step_header 5 "apply the ordered patch series (must precede install-host)"
  say "[step 5] make -C $REPO_DIR -j $JOBS apply-series"
  say '[step 5] rc=0 (dry-run)'
  step_header 6 "configure the compiler-rt builtins build tree when absent"
  say '[step 6] configure only when build.ninja is absent; build-tree clang is created first when missing'
  say "[step 6] fallback when $LLVM_BUILD/bin/clang is absent: make -C $REPO_DIR -j $JOBS build-mc build-lld"
  printf '[step 6] cmake-command:'
  printf ' %q' "${COMPILER_RT_CMAKE[@]}"
  printf '\n'
  say '[step 6] rc=0 (dry-run)'
  step_header 7 "install the host toolchain"
  say "[step 7] make -C $REPO_DIR -j $JOBS install-host"
  say '[step 7] rc=0 (dry-run)'
  step_header 8 "run the L1 gate"
  say "[step 8] make -C $REPO_DIR -j $JOBS check"
  say '[step 8] rc=0 (dry-run)'
  exit 0
fi

[ -d "$REPO_DIR" ] || die "repository directory not found: $REPO_DIR"

# ---------------------------------------------------------------- step 1: preflight
step_header 1 "preflight: report missing tools and -dev packages (nothing is installed)"
MISSING=()
TOOLS=(git cmake ninja scons ccache bison flex python3 make ar ranlib nm)
for tool in "${TOOLS[@]}"; do
  if command -v "$tool" >/dev/null 2>&1; then
    say "[step 1] tool $tool: ok"
  else
    say "[step 1] tool $tool: MISSING"
    MISSING+=("$tool")
  fi
done

DEV_OK=0
for pkg in glib-2.0 pixman-1 zlib; do
  if command -v pkg-config >/dev/null 2>&1 && pkg-config --exists "$pkg"; then
    say "[step 1] dev $pkg: ok"
  else
    say "[step 1] dev $pkg: MISSING"
    DEV_OK=1
  fi
done
if command -v cc >/dev/null 2>&1; then
  if printf '#include <libfdt.h>\nint main(void){return 0;}\n' | cc -x c -fsyntax-only - >/dev/null 2>&1; then
    say "[step 1] dev libfdt: ok"
  else
    say "[step 1] dev libfdt: MISSING"
    DEV_OK=1
  fi
else
  say '[step 1] dev libfdt: UNKNOWN (cc not on PATH)'
  DEV_OK=1
fi

if [ "${#MISSING[@]}" -ne 0 ] || [ "$DEV_OK" -ne 0 ]; then
  say "[step 1] rc=2"
  say '[step 1] pending install list (install these, then re-run bootstrap):'
  for tool in "${MISSING[@]}"; do
    case "$tool" in
      ninja)            say '  - ninja-build' ;;
      ar|ranlib|nm)     say '  - binutils' ;;
      make)             say '  - make' ;;
      *)                say "  - $tool" ;;
    esac
  done
  [ "$DEV_OK" -ne 0 ] && say '  - pkg-config libglib2.0-dev libpixman-1-dev zlib1g-dev libfdt-dev'
  command -v cc >/dev/null 2>&1 || say '  - build-essential'
  exit 2
fi
say '[step 1] rc=0'

# ---------------------------------------------------------------- step 2: git identity
step_header 2 "git identity"
CURRENT_NAME="$(git -C "$REPO_DIR" config user.name 2>/dev/null || true)"
CURRENT_EMAIL="$(git -C "$REPO_DIR" config user.email 2>/dev/null || true)"
if [ -n "$CURRENT_NAME" ] && [ -n "$CURRENT_EMAIL" ]; then
  say "[step 2] already configured (user.name=$CURRENT_NAME)"
  say '[step 2] rc=0'
else
  NAME="${GIT_NAME_ARG:-${DADAO_GIT_NAME:-}}"
  EMAIL="${GIT_EMAIL_ARG:-${DADAO_GIT_EMAIL:-}}"
  if [ -z "$NAME" ] || [ -z "$EMAIL" ]; then
    say '[step 2] rc=2'
    say '[step 2] git identity missing: pass --git-name/--git-email or set DADAO_GIT_NAME/DADAO_GIT_EMAIL'
    exit 2
  fi
  run_logged 2 identity git -C "$REPO_DIR" config --global user.name "$NAME" || exit $?
  run_logged 2 identity-email git -C "$REPO_DIR" config --global user.email "$EMAIL" || exit $?
fi

# ---------------------------------------------------------------- step 3: repository sync
step_header 3 "repository sync (local bundle or existing repository; never direct GitHub)"
if [ -n "$BUNDLE" ]; then
  if git -C "$REPO_DIR" rev-parse --git-dir >/dev/null 2>&1; then
    run_logged 3 sync git -C "$REPO_DIR" fetch "$BUNDLE" || exit $?
  else
    run_logged 3 sync git clone "$BUNDLE" "$REPO_DIR" || exit $?
  fi
  say '[step 3] note: fetch only; selecting the working ref is left to the caller'
elif [ -n "$SOURCE_REPO" ]; then
  if git -C "$REPO_DIR" rev-parse --git-dir >/dev/null 2>&1; then
    run_logged 3 sync git -C "$REPO_DIR" fetch "$SOURCE_REPO" || exit $?
  else
    run_logged 3 sync git clone "$SOURCE_REPO" "$REPO_DIR" || exit $?
  fi
  say '[step 3] note: fetch only; selecting the working ref is left to the caller'
else
  if ! git -C "$REPO_DIR" rev-parse --git-dir >/dev/null 2>&1; then
    say '[step 3] rc=2'
    say '[step 3] not a git repository: pass --bundle PATH or --source-repo PATH'
    exit 2
  fi
  say "[step 3] using existing repository at $REPO_DIR"
  say '[step 3] rc=0'
fi

# ---------------------------------------------------------------- step 4: fetch
step_header 4 "fetch components from local .cache mirrors"
run_logged 4 fetch make -C "$REPO_DIR" -j "$JOBS" fetch || exit $?

# ---------------------------------------------------------------- step 5: apply-series
step_header 5 "apply ordered patch series (must run before install-host)"
run_logged 5 apply-series make -C "$REPO_DIR" -j "$JOBS" apply-series || exit $?

# ---------------------------------------------------------------- step 6: compiler-rt
step_header 6 "compiler-rt builtins build tree"
if [ -f "$COMPILER_RT_BUILD/build.ninja" ]; then
  say "[step 6] already configured at $COMPILER_RT_BUILD"
  say '[step 6] rc=0'
else
  if [ ! -x "$LLVM_BUILD/bin/clang" ] || [ ! -x "$LLVM_BUILD/bin/clang++" ]; then
    say '[step 6] build-tree clang is absent; building the host LLVM first'
    say '[step 6] (install-host cannot bootstrap its own compiler-rt dependency)'
    run_logged 6 llvm make -C "$REPO_DIR" -j "$JOBS" build-mc build-lld || exit $?
  fi
  run_logged 6 compiler-rt "${COMPILER_RT_CMAKE[@]}" || exit $?
fi

# ---------------------------------------------------------------- step 7: install-host
step_header 7 "install the host toolchain"
run_logged 7 install-host make -C "$REPO_DIR" -j "$JOBS" install-host || exit $?

# ---------------------------------------------------------------- step 8: check
step_header 8 "run the L1 gate"
run_logged 8 check make -C "$REPO_DIR" -j "$JOBS" check || exit $?

say '[bootstrap_node] all steps completed'
exit 0
