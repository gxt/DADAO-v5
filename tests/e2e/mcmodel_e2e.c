/* mcmodel_e2e.c -- code-model end-to-end test (LLVM-131t; ADR-0036 D1/D5/D6).
 *
 * Built twice by tests/e2e/lit/mcmodel.test: once with `-mcmodel=default` and
 * once with `-mcmodel=large`.  The input is volatile, so the computation
 * cannot be constant-folded away and every step crosses a real call.  The
 * guest exit code is 0 only when all three calls returned the right value:
 *
 *   21 --twice--> add3(21, 21) = 42 --+1--> 43
 *
 * Under `large` each of those calls is an indirect `call [rb, rd0, 0]` whose
 * target address comes from the fixed ABS48 materialization (`set.zw` + 2x
 * `or.w`, R_DADAO_ABS48) instead of a PC-relative `call [rb0, sym]`; the lit
 * test asserts the instruction forms and the runnable image asserts that the
 * result is unchanged.
 *
 * Exit code: 0 = PASS, 1 = a call returned a wrong value.
 */

static volatile long input = 21;

__attribute__((noinline)) static long add3(long a, long b) { return a + b; }

__attribute__((noinline)) static long twice(long x) { return add3(x, x); }

__attribute__((noinline)) static long helper(long x) { return twice(x) + 1; }

int main(void) {
  long v = helper(input);
  return v == 43 ? 0 : 1;
}
