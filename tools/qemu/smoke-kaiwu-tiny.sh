#!/bin/bash
# Minimal load-rule smoke test for the DADAO Kaiwu-Tiny machine
# (m19-qemu-001; spec/Kaiwu §1.1/§6.2: 8 KiB BootROM + 256 KiB SRAM).
#
# Verifies:
#   * qemu-system-dadao exists and -M ? shows kaiwu-tiny / kaiwu-vast;
#   * a bootrom image that is not exactly 8 KiB is rejected by name
#     (load-stage error, non-zero exit);
#   * an exactly 8 KiB bootrom image plus a raw -kernel is accepted: the
#     machine starts (kept paused with -S, so no guest instruction runs and
#     the check does not depend on firmware contents).
#
# NOTE: This script is NOT included in `make check`; it is a standalone smoke
# test. Gate-blind: changes here do not block `make check` green.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
QEMU_BIN="${SCRIPT_DIR}/../../.work/build/qemu/qemu-system-dadao"
TMPDIR=$(mktemp -d /tmp/opencode/m19-qemu-001-smoke.XXXXXX)
trap "rm -rf $TMPDIR" EXIT

pass=0
fail=0
check() {
    local name="$1" want="$2" got="$3"
    if [ "$want" = "$got" ]; then
        echo "PASS: $name (expected $want, got $got)"
        pass=$((pass + 1))
    else
        echo "FAIL: $name (expected $want, got $got)"
        fail=$((fail + 1))
    fi
}

echo "=== DADAO Tiny load-rule smoke test (8 KiB BootROM) ==="

if [ ! -x "$QEMU_BIN" ]; then
    echo "FAIL: $QEMU_BIN not found or not executable"
    echo "      Run 'make build-qemu' first"
    exit 1
fi

MACHINE_LIST=$("$QEMU_BIN" -M ? 2>&1 || true)
for machine in kaiwu-tiny kaiwu-vast; do
    if echo "$MACHINE_LIST" | grep -q "$machine"; then
        check "machine $machine listed" "0" "0"
    else
        check "machine $machine listed" "0" "1"
    fi
done

# Fixtures: an 8 KiB ROM, two wrong sizes, and an 8-byte raw application.
dd if=/dev/zero of="$TMPDIR/rom8k.bin"  bs=8192 count=1 status=none
dd if=/dev/zero of="$TMPDIR/rom8k1.bin" bs=8193 count=1 status=none
dd if=/dev/zero of="$TMPDIR/rom64k.bin" bs=65536 count=1 status=none
dd if=/dev/zero of="$TMPDIR/app.bin"    bs=8 count=1 status=none

expect_reject() {
    local name="$1" rom="$2"
    set +e
    "$QEMU_BIN" -machine kaiwu-tiny -bios "$rom" -kernel "$TMPDIR/app.bin" \
        -display none -nographic >"$TMPDIR/$name.out" 2>&1
    local rc=$?
    set -e
    check "$name rejected (rc)" "1" "$rc"
    if grep -q "exceeds the ROM region size limit" "$TMPDIR/$name.out"; then
        check "$name names the size rule" "0" "0"
    else
        check "$name names the size rule" "0" "1"
    fi
}

expect_reject "rom-8193" "$TMPDIR/rom8k1.bin"
expect_reject "rom-64KiB" "$TMPDIR/rom64k.bin"

# Exactly 8 KiB is accepted: start paused (-S), confirm the process stays up,
# then terminate it ourselves.
"$QEMU_BIN" -machine "kaiwu-tiny,bootrom-image=$TMPDIR/rom8k.bin" \
    -kernel "$TMPDIR/app.bin" -display none -nographic -S \
    >"$TMPDIR/accept.out" 2>&1 &
pid=$!
sleep 1
if kill -0 "$pid" 2>/dev/null; then
    check "8 KiB bootrom + raw kernel accepted" "0" "0"
    kill "$pid" 2>/dev/null || true
    wait "$pid" 2>/dev/null || true
else
    wait "$pid" 2>/dev/null || true
    check "8 KiB bootrom + raw kernel accepted" "0" "1"
    cat "$TMPDIR/accept.out"
fi

echo ""
echo "=== summary: $pass passed, $fail failed ==="
[ "$fail" -eq 0 ]
