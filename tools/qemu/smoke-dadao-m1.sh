#!/bin/bash
# Minimal smoke test for DADAO M1 target skeleton.
# Verifies: qemu-system-dadao exists, -M ? shows dadao-m1,
# and boot triggers ILLI (exit code 0x88) because all instructions
# are unimplemented in the skeleton.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
QEMU_BIN="${SCRIPT_DIR}/../../.work/build/qemu/qemu-system-dadao"
TMPDIR=$(mktemp -d /tmp/opencode/QEMU-003t-smoke.XXXXXX)
trap "rm -rf $TMPDIR" EXIT

echo "=== DADAO M1 Smoke Test ==="

# Check binary exists
if [ ! -x "$QEMU_BIN" ]; then
    echo "FAIL: $QEMU_BIN not found or not executable"
    echo "      Run 'make build-qemu' first"
    exit 1
fi
echo "PASS: qemu-system-dadao found"

# Check -M ? shows dadao-m1
MACHINE_LIST=$("$QEMU_BIN" -M ? 2>&1)
if echo "$MACHINE_LIST" | grep -q "dadao-m1"; then
    echo "PASS: dadao-m1 found in machine list"
else
    echo "FAIL: dadao-m1 not in machine list"
    echo "      Output: $MACHINE_LIST"
    exit 1
fi

# Create minimal ROM and kernel binaries (zeroed, 8 bytes each)
# ROM: all zeros at 0xffff_ffff_0000 → first instruction is 0x00000000
#      = illi 0 (opcode 0, minor-opcode 0, immu18=0) → ILLI
# Kernel: all zeros at 0xffff_0000_0000 (won't be reached, ROM ILLI happens first)
dd if=/dev/zero of="$TMPDIR/rom.bin" bs=1 count=8 2>/dev/null
dd if=/dev/zero of="$TMPDIR/test.bin" bs=1 count=8 2>/dev/null

echo ""
echo "=== Boot test: expect ILLI exit code (0x88 = 136) ==="
echo "Command: $QEMU_BIN -machine dadao-m1 -bios $TMPDIR/rom.bin -kernel $TMPDIR/test.bin -display none -nographic"

set +e
"$QEMU_BIN" \
    -machine dadao-m1 \
    -bios "$TMPDIR/rom.bin" \
    -kernel "$TMPDIR/test.bin" \
    -display none \
    -nographic \
    2>"$TMPDIR/stderr.txt"
EXIT_CODE=$?
set -e

echo "Exit code: $EXIT_CODE (expected: 136 = 0x88)"
echo "stderr:"
cat "$TMPDIR/stderr.txt" | head -20

if [ "$EXIT_CODE" -eq 136 ]; then
    echo ""
    echo "=== PASS: ILLI exit code (0x88) confirmed ==="
    exit 0
else
    echo ""
    echo "=== FAIL: unexpected exit code $EXIT_CODE (expected 136) ==="
    exit 1
fi
