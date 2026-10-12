#!/bin/sh
# Give gem5 the headers and shared Python library from the project-local SDK.
set -eu
repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
GEM5_DEPS="$repo_root/.work/deps/gem5/root/usr"
case " $* " in
    *' --ldflags '*|*' --includes '*)
        printf '%s\n' "-I${GEM5_DEPS}/include/python$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")') -L${GEM5_DEPS}/lib/$(gcc -dumpmachine) -lpython$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")') -ldl -lm"
        ;;
    *' --embed '*) exit 0 ;;
    *) exec "${GEM5_DEPS}/bin/python$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')-config" "$@" ;;
esac
