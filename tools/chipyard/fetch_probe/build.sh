#!/usr/bin/env bash
# Build the m12-chipyard-018 fetch-port probe bench.
#
#   bash tools/chipyard/fetch_probe/build.sh BUILDDIR [SRCDIR]
#
# BUILDDIR  where the Verilator model and the executable are written
# SRCDIR    the elaborated core RTL (gen-collateral of the WumingTinyConfig
#           harness); defaults to the harness build tree
#
# The bench drives the *generated* WumingCore, so it must be built after
# `make verilog CONFIG=WumingTinyConfig`.
set -u
set -o pipefail

ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
BUILD=${1:?usage: build.sh BUILDDIR [SRCDIR]}
SRC=${2:-$ROOT/.work/source/chipyard/sims/verilator/generated-src/chipyard.harness.TestHarness.WumingTinyConfig/gen-collateral}
HERE=$ROOT/tools/chipyard/fetch_probe
VERILATOR=${VERILATOR:-$ROOT/.work/source/chipyard/.conda-env/bin/verilator}

if [ ! -x "$VERILATOR" ]; then
    echo "build.sh: verilator not found at $VERILATOR" >&2
    exit 2
fi
if [ ! -f "$SRC/WumingCore.sv" ]; then
    echo "build.sh: $SRC/WumingCore.sv is missing (run 'make verilog CONFIG=WumingTinyConfig')" >&2
    exit 2
fi

mkdir -p "$BUILD"
cd "$BUILD" || exit 2
"$VERILATOR" --cc --exe --build -Wno-fatal -Wno-lint --top-module WumingCore \
    -Mdir "$BUILD/obj_dir" -o "$BUILD/VWumingCore" \
    --CFLAGS "-O2 -std=c++17" \
    "$SRC/WumingCore.sv" "$SRC/WumingALU.sv" "$SRC/WumingDecoder.sv" \
    "$SRC/WumingRegFile.sv" "$HERE/tb_fetch_probe.cpp"
rc=$?
if [ $rc -ne 0 ]; then
    echo "build.sh: verilator build failed (rc=$rc)" >&2
    exit $rc
fi
echo "build.sh: bench at $BUILD/VWumingCore"
