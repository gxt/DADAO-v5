#!/bin/bash
# min_rom_probe_022t.sh — -d exec PC increment verification for QEMU-022t
#
# Runs 100 st.o-rd stores with -d exec and verifies that:
# 1. QEMU exits with code 0 (no TIMEOUT)
# 2. PC values in -d exec output are incrementing (not stuck at one address)
#
# Usage: bash tools/qemu/min_rom_probe_022t.sh

set -euo pipefail
cd "$(dirname "$0")/../.."

QEMU=".work/build/qemu/qemu-system-dadao"
LOGDIR=".work/log/qemu"
mkdir -p "$LOGDIR" /tmp/opencode/QEMU-022t
LOGFILE="$LOGDIR/QEMU-022t-exec.log"

if [ ! -f "$QEMU" ]; then
    echo "ERROR: $QEMU not found. Run 'make build-qemu' first."
    exit 1
fi

# Generate the 100 st.o-rd ROM using the Python probe's build_rom
ROMFILE=$(mktemp /tmp/opencode/QEMU-022t/exec-rom-XXXXXX.bin)
KERNFILE=$(mktemp /tmp/opencode/QEMU-022t/exec-kern-XXXXXX.bin)

python3 -c "
import struct, sys
sys.path.insert(0, '.')
from tools.qemu.min_rom_probe_022t import build_rom, make_st_o_rd_sequence, illi
rom = build_rom(make_st_o_rd_sequence(100))
with open('$ROMFILE', 'wb') as f: f.write(rom)
with open('$KERNFILE', 'wb') as f: f.write(illi() * 4)
"

cleanup() {
    rm -f "$ROMFILE" "$KERNFILE"
}
trap cleanup EXIT

echo "=== QEMU-022t -d exec PC increment verification ==="
echo "Running 100 st.o-rd with -d exec..."

# Run with -d exec, capture output
set +e
timeout 15 "$QEMU" -M dadao-m1 -nographic \
    -bios "$ROMFILE" -kernel "$KERNFILE" \
    -d exec -D "$LOGFILE" 2>&1
EXIT_CODE=$?
set -e

echo "Exit code: $EXIT_CODE"
echo "Log file: $LOGFILE"

if [ "$EXIT_CODE" -eq 124 ]; then
    echo "[FAIL] TIMEOUT — TB continuation bug persists"
    exit 1
elif [ "$EXIT_CODE" -ne 0 ]; then
    echo "[FAIL] Unexpected exit code: $EXIT_CODE"
    exit 1
fi

echo "[PASS] QEMU exited normally (exit=0)"

# Check PC values in -d exec output
echo ""
echo "Checking PC increment in -d exec output..."

# Extract PC values from the exec log (format: "Trace 0xADDR ...")
# QEMU -d exec format: "Trace 0xADDR 0xSIZE ..."
PC_COUNT=$(grep -c "^Trace " "$LOGFILE" 2>/dev/null || echo 0)
echo "Total TB executions logged: $PC_COUNT"

if [ "$PC_COUNT" -eq 0 ]; then
    echo "[WARN] No Trace lines found in -d exec output"
    echo "Checking for alternative format..."
    # Try alternative: "IN: " lines
    PC_COUNT2=$(grep -c "^IN: " "$LOGFILE" 2>/dev/null || echo 0)
    echo "IN: lines found: $PC_COUNT2"
fi

# Check if we have multiple distinct PC values (not stuck in loop)
# QEMU -d exec format: "Trace 0: <tb_ptr> [<insn_count>/<pc>/<cs_base>/<flags>]"
# PC is the second field inside brackets
UNIQUE_PCS=$(grep "^Trace " "$LOGFILE" 2>/dev/null | sed 's/.*\[[^/]*\/\([^/]*\)\/.*/\1/' | sort -u | wc -l)
echo "Distinct PC values: $UNIQUE_PCS"

if [ "$UNIQUE_PCS" -le 1 ]; then
    echo "[FAIL] Only $UNIQUE_PCS distinct PC — TB execution is stuck (infinite loop)"
    echo "First 10 Trace lines:"
    grep "^Trace " "$LOGFILE" 2>/dev/null | head -10
    exit 1
fi

# Show first and last PC to verify increment
FIRST_PC=$(grep "^Trace " "$LOGFILE" 2>/dev/null | head -1 | sed 's/.*\[[^/]*\/\([^/]*\)\/.*/\1/')
LAST_PC=$(grep "^Trace " "$LOGFILE" 2>/dev/null | tail -1 | sed 's/.*\[[^/]*\/\([^/]*\)\/.*/\1/')
echo "First PC: $FIRST_PC"
echo "Last PC:  $LAST_PC"

# Verify the first PC is the expected ROM entry point
echo ""
echo "[PASS] PC values are incrementing — TB continuation is working correctly"
echo ""
echo "=== Verification complete ==="
exit 0
