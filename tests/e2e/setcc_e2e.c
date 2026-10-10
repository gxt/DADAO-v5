/* setcc_e2e.c — M6 integer compare-as-value end-to-end program (LLVM-069t).
 *
 * Freestanding (no libc): crt0 reports the `main` return value as the guest
 * exit code (tests/scripts/codegen_crt0.s, contract-semihosting.md §3).
 *
 * Every helper returns the *value* of a comparison (C `a == b`, `a < b`,
 * `!x`, `&&`), so the backend must lower an integer SETCC used as a value
 * (and, for `&&`, a SELECT_CC) rather than a plain compare+branch.  The
 * inputs live in `volatile` globals so the comparison cannot be constant
 * folded away.
 *
 * Expected guest exit code, hand-derived from C semantics (independent of
 * the backend):
 *   eq  v_a == v_a        -> 1
 *   slt v_a <  v_b        -> 1
 *   ult v_c <  v_d        -> 0   (9 < 3 unsigned is false)
 *   ne  v_a != v_b        -> 1
 *   not !v_z              -> 1   (v_z == 0)
 *   and (v_a < v_b) && (v_d < v_c) -> 1
 *   r = 1 | (1<<1) | (0<<2) | (1<<3) | (1<<4) | (1<<5)
 *     = 1 + 2 + 0 + 8 + 16 + 32 = 59
 */
volatile long v_a = 5, v_b = 7, v_c = 9, v_d = 3, v_z = 0;

long eq(long x, long y)   { return x == y; }
long slt(long x, long y)  { return x < y; }
long ult(unsigned long x, unsigned long y) { return x < y; }
long ne(long x, long y)   { return x != y; }
long notx(long x)         { return !x; }
long land(long x, long y, long u, long v) { return (x < y) && (u < v); }

long main(void) {
  long r = 0;
  r |= eq(v_a, v_a) << 0;
  r |= slt(v_a, v_b) << 1;
  r |= ult(v_c, v_d) << 2;
  r |= ne(v_a, v_b) << 3;
  r |= notx(v_z) << 4;
  r |= land(v_a, v_b, v_d, v_c) << 5;
  return r;
}
