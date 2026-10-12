#!/bin/sh
# Run SCons for gem5, using a project-local Ubuntu SDK when present.
set -eu
repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
src="${GEM5_SRC:-$repo_root/.work/source/gem5}"
if [ ! -f "$src/SConstruct" ]; then
    echo "run-scons: missing gem5 source at $src; run make fetch-gem5" >&2
    exit 2
fi
GEM5_DEPS="$repo_root/.work/deps/gem5/root/usr"
if [ -x "$GEM5_DEPS/bin/scons" ]; then
    export GEM5_DEPS
    export PATH="$GEM5_DEPS/bin:$PATH"
    export PYTHONPATH="$GEM5_DEPS/lib/python3/dist-packages${PYTHONPATH:+:$PYTHONPATH}"
    export CPATH="$GEM5_DEPS/include${CPATH:+:$CPATH}"
    export LIBRARY_PATH="$GEM5_DEPS/lib/$(gcc -dumpmachine)${LIBRARY_PATH:+:$LIBRARY_PATH}"
    export PYTHON_CONFIG="$repo_root/tools/gem5/python-config-local.sh"
fi
cd "$src"
exec timeout 3600 scons "$@"
