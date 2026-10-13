/* fp_codegen.c — M6 FP/RF codegen end-to-end program (LLVM-066t).
 *
 * Freestanding (no libc): a small floating-point computation whose result
 * selects the value returned from `main`; crt0 reports that value as the
 * guest exit code (tests/scripts/codegen_crt0.s, contract-semihosting.md §3).
 *
 * The inputs live in `volatile` globals so the computation cannot be
 * constant-folded away and the comparison stays a real fcmp + branch (the
 * backend supports FP compare+branch, not FP setcc-as-value).
 *
 *   a * b + a / b = 3.0 * 2.0 + 3.0 / 2.0 = 7.5  > 6.0  -> exit 42
 */

volatile double g_a = 3.0;
volatile double g_b = 2.0;
volatile long g_out;

long main(void) {
  double a = g_a;
  double b = g_b;
  double r = a * b + a / b;
  if (r > 6.0)
    g_out = 42;
  else
    g_out = 7;
  return g_out;
}
