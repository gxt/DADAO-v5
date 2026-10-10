/* selectcc_e2e.c — M6 integer select_cc end-to-end program (LLVM-069t).
 *
 * Freestanding (no libc): crt0 reports the `main` return value as the guest
 * exit code (tests/scripts/codegen_crt0.s, contract-semihosting.md §3).
 *
 * Ternary `?:` with a signed and an unsigned condition.  At -O2 the
 * if-conversion turns the selecting branches into SELECT_CC, i.e. exactly the
 * form that used to crash the backend; the same program is also run at -O0
 * (branch form).  The inputs live in `volatile` globals so nothing folds away.
 *
 * Expected guest exit code, hand-derived from C semantics:
 *   sel_s(v_a, v_b) = (5  <  7 ) ? 11 : 22 = 11
 *   sel_s(v_c, v_d) = (9  <  3 ) ? 11 : 22 = 22
 *   sel_u(v_c, v_d) = (9u <  3u) ? 33 : 44 = 44
 *   sel_u(v_d, v_c) = (3u <  9u) ? 33 : 44 = 33
 *   r = (sel_s(a,b)==11) | (sel_s(c,d)==22)<<1 |
 *       (sel_u(c,d)==44)<<2 | (sel_u(d,c)==33)<<3
 *     = 1 | 2 | 4 | 8 = 15
 */
volatile long v_a = 5, v_b = 7, v_c = 9, v_d = 3;

long sel_s(long x, long y) { return x < y ? 11 : 22; }
long sel_u(unsigned long x, unsigned long y) { return x < y ? 33 : 44; }

long main(void) {
  long r = 0;
  r |= (sel_s(v_a, v_b) == 11) << 0;
  r |= (sel_s(v_c, v_d) == 22) << 1;
  r |= (sel_u(v_c, v_d) == 44) << 2;
  r |= (sel_u(v_d, v_c) == 33) << 3;
  return r;
}
