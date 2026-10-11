/* large_const_cmp_e2e.c — LLVM-071t (M6, G1) end-to-end vector.
 *
 * Freestanding (no libc): crt0 reports the `main` return value as the guest
 * exit code (tests/scripts/codegen_crt0.s, contract-semihosting.md §3).
 *
 * Compares a runtime value against constants at and beyond the cmp* 12-bit
 * immediate boundary (simm12 max = +2047 / immu12 max = 4095) so the backend
 * must materialise the constant into a register and use the register-register
 * compare rather than rejecting the program.  Both value compares (setcc /
 * select_cc) and a branch-on-compare are exercised, signed and unsigned.
 *
 * Expected guest exit code is the number of true predicates, hand-derived from
 * C semantics (independent of the backend); the inputs are `volatile` so the
 * comparisons cannot be constant-folded away:
 *   lt5000(v_a=4999)          -> 1
 *   lt5000(v_b=5000)          -> 0
 *   lt2047(v_b)               -> 0   (5000 < 2047 is false)
 *   lt_neg2049(v_n=-2050)     -> 1
 *   ge5000(v_b)               -> 1
 *   ult4096(u_a=4095)         -> 1
 *   neq7000(v_b)              -> 1
 *   branch_lt5000(v_a)        -> 1
 *   branch_lt5000(v_b)        -> 0
 *   sum                       -> 6
 */

volatile long v_a = 4999;
volatile long v_b = 5000;
volatile long v_n = -2050;
volatile unsigned long u_a = 4095;

long lt5000(long a)          { return a < 5000; }
long lt2047(long a)          { return a < 2047; }
long lt_neg2049(long a)      { return a < -2049; }
long ge5000(long a)          { return a >= 5000; }
long ult4096(unsigned long a){ return a < 4096u; }
long neq7000(long a)         { return a != 7000; }

/* Branch on a large-constant comparison (br(icmp)). */
long branch_lt5000(long a) {
  if (a < 5000)
    return 1;
  return 0;
}

long main(void) {
  long r = 0;
  r += lt5000(v_a);
  r += lt5000(v_b);
  r += lt2047(v_b);
  r += lt_neg2049(v_n);
  r += ge5000(v_b);
  r += ult4096(u_a);
  r += neq7000(v_b);
  r += branch_lt5000(v_a);
  r += branch_lt5000(v_b);
  return r;
}
