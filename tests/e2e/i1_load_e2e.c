/* i1_load_e2e.c — LLVM-077t (M6, ISS-186) end-to-end vector.
 *
 * Freestanding (no libc): crt0 reports `main`'s return value as the guest exit
 * code (low byte; tests/scripts/codegen_crt0.s, contract-semihosting.md §3).
 *
 * Reproduces the ISS-186 shape end to end.  A static global with exactly two
 * stored values (its zero initializer and one constant written by a `noinline`
 * setter) is shrunk to an `i1` by GlobalOpt at -O2 ("shrink-to-bool"), so the
 * read becomes `load i1` + select — the `zextloadi1` DAG node that had no DADAO
 * selection.  There is no GlobalOpt at -O0, so the same source exercises a
 * plain i64 load there; the DADAO lowering must produce the same value either
 * way.
 *
 * The exit code is only the low byte, so this one source is compiled once per
 * BYTE (0..7) and the harness reconstructs the full 64-bit value.  The constant
 * and every expected byte are read from this file (single source of truth) by
 * an independent host Python oracle — none are hard-coded in the harness.
 *
 *   BYTE  which byte of the 64-bit value to return (0 = least significant)
 */

#ifndef BYTE
#define BYTE 0
#endif

#define NOINLINE __attribute__((noinline))

/* Shrink-to-bool source global: zero-initialised, one non-zero constant store. */
static unsigned long g = 0;
NOINLINE static void set_g(void) { g = 0x0549372187237fefUL; }

long main(void) {
  set_g();
  unsigned long a = g; /* -O2: load i1 @g + select (the ISS-186 shape) */
  return (long)((a >> (BYTE * 8)) & 0xff);
}
