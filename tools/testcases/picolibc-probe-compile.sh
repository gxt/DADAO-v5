#!/usr/bin/env bash
# picolibc-probe compile harness (measurement only; writes only under $OUT).
# Canonical location: tools/testcases/ (LLVM-080t rework; previously only under the
# gitignored .work/log/testcases/).  No `cd`: every read/write is $OUT- or repo-qualified.
CLANG=/mnt/tao/DADAO-v5/.dadao/cross-toolchain/bin/clang
T=/mnt/tao/DADAO-v5/.work/source/picolibc
OUT=/tmp/opencode/picolibc-probe
mkdir -p "$OUT"
: > "$OUT/picolibc.h"   # stub for picolibc.h.in
COMMON="-I$OUT -I$T/libc/include -I$T/libc/include/machine -I$T/libc/include/bits -I$T/test -I$T/test/testsuite/include -I$T/libos/semihost/common -D__IEEE_BIG_ENDIAN"

TSV="$OUT/compile.tsv"
: > "$TSV"

classify() {
  local outfile="$1"
  if grep -q "Cannot select" "$outfile"; then echo "BACKEND_CANNOT_SELECT"; return; fi
  if grep -q "error in backend" "$outfile"; then echo "BACKEND_OTHER"; return; fi
  if grep -q "PLEASE submit a bug report" "$outfile"; then echo "CC_CRASH"; return; fi
  if grep -q "file not found" "$outfile"; then echo "MISSING_HDR"; return; fi
  if grep -q "error:" "$outfile"; then echo "FRONTEND_ERR"; return; fi
  echo "OTHER"
}

probe_dir() {
  local cat="$1"; shift
  for d in "$@"; do
    for f in "$T/$d"/*.c; do
      [ -e "$f" ] || continue
      local dir; dir=$(dirname "$f")
      local errf="$OUT/.err"
      timeout 60 "$CLANG" -target dadao-unknown-elf -ffreestanding -fno-builtin -O2 \
         $COMMON -I"$dir" -c "$f" -o /dev/null >"$errf" 2>&1
      local rc=$?
      local cls first
      if [ $rc -eq 0 ]; then cls="OK"; else cls=$(classify "$errf"); fi
      first=$(grep -m1 -E "error:|Cannot select|PLEASE submit" "$errf" | sed -E 's/^.*(error: |fatal error: )/\1/' | cut -c1-110)
      printf '%s\t%s\t%s\t%s\t%s\n' "$cat" "${f#$T/}" "$rc" "$cls" "$first" >> "$TSV"
      # full log (bounded)
      { echo "===== [$cls rc=$rc] ${f#$T/}"; head -40 "$errf"; } >> "$OUT/probe-full.log"
    done
  done
}

probe_dir libc-testsuite  test/libc-testsuite
probe_dir semihost        test/semihost
probe_dir test-ctype      test/test-ctype
probe_dir test-iconv      test/test-iconv
probe_dir test-libdl      test/test-libdl
probe_dir test-math       test/test-math
probe_dir test-monetary   test/test-monetary
probe_dir test-posix      test/test-posix
probe_dir test-stdio      test/test-stdio
probe_dir test-stdlib     test/test-stdlib
probe_dir test-string     test/test-string
probe_dir top-level       test
probe_dir testsuite       test/testsuite/newlib.iconv test/testsuite/newlib.locale test/testsuite/newlib.math test/testsuite/newlib.search test/testsuite/newlib.stdio test/testsuite/newlib.stdlib test/testsuite/newlib.string test/testsuite/newlib.time test/testsuite/newlib.wctype

echo "DONE total=$(wc -l < "$TSV")"
