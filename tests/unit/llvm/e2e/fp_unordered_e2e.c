/*
 * FP unordered-family predicate end-to-end vector (LLVM-084t, ISS-193 (a)).
 *
 * Exercises the predicates the DADAO backend gained in LLVM-084t:
 *
 *   isnan(x)    -> fcmp uno (SETUO)              : foqcmp + cmp.si + cs.p
 *   isinf(x)    -> fcmp oeq (fabs x), +Inf (SETOEQ, already supported)
 *   isfinite(x) -> fcmp one (fabs x), +Inf (SETONE)
 *
 * over NaN / +Inf / -Inf / +0.0 / -0.0 / finite inputs, in both the value and
 * the branch (BR_CC) form, for f64 (foqcmp) and f32 (ftqcmp).  Each failing
 * case returns a distinct non-zero guest exit code (0 = everything correct).
 *
 * The inputs are `volatile` so clang cannot constant-fold the operations away.
 * The expected results follow from IEEE-754 and the C <math.h> semantics of
 * isnan/isinf/isfinite -- they are NOT read back from any toolchain output.
 */

volatile double d_nan = __builtin_nan("");
volatile double d_inf = __builtin_inf();
volatile double d_ninf = -__builtin_inf();
volatile double d_zero = 0.0;
volatile double d_nzero = -0.0;
volatile double d_one = 1.0;

volatile float f_nan = __builtin_nanf("");
volatile float f_inf = __builtin_inff();
volatile float f_one = 1.0f;

int main(void)
{
    /* isnan (SETUO / fcmp uno): unordered iff the operand is a NaN. */
    if (__builtin_isnan(d_nan) != 1)
        return 1;
    if (__builtin_isnan(d_inf) != 0)
        return 2;
    if (__builtin_isnan(d_ninf) != 0)
        return 3;
    if (__builtin_isnan(d_zero) != 0)
        return 4;
    if (__builtin_isnan(d_nzero) != 0)
        return 5;
    if (__builtin_isnan(d_one) != 0)
        return 6;

    /* isinf (SETOEQ of |x| against +Inf; ordered and equal). */
    if (__builtin_isinf(d_inf) != 1)
        return 7;
    if (__builtin_isinf(d_ninf) != 1)
        return 8;
    if (__builtin_isinf(d_nan) != 0)
        return 9;
    if (__builtin_isinf(d_zero) != 0)
        return 10;

    /* isfinite (SETONE of |x| against +Inf; ordered and not equal). */
    if (__builtin_isfinite(d_one) != 1)
        return 11;
    if (__builtin_isfinite(d_zero) != 1)
        return 12;
    if (__builtin_isfinite(d_nzero) != 1)
        return 13;
    if (__builtin_isfinite(d_inf) != 0)
        return 14;
    if (__builtin_isfinite(d_ninf) != 0)
        return 15;
    if (__builtin_isfinite(d_nan) != 0)
        return 16;

    /* Branch (BR_CC) forms of the same predicates. */
    if (!__builtin_isnan(d_nan))
        return 17;
    if (__builtin_isnan(d_one))
        return 18;
    if (!__builtin_isfinite(d_one))
        return 19;
    if (__builtin_isfinite(d_inf))
        return 20;

    /* f32 path (ftqcmp). */
    if (__builtin_isnan(f_nan) != 1)
        return 21;
    if (__builtin_isnan(f_one) != 0)
        return 22;
    if (!__builtin_isinf(f_inf))
        return 23;
    if (__builtin_isfinite(f_inf))
        return 24;
    if (!__builtin_isfinite(f_one))
        return 25;

    return 0;
}
