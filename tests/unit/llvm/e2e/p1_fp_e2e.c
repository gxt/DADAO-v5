/*
 * P1 FP sign-codegen end-to-end vector (LLVM-080t).
 *
 * Exercises the double-precision P1 class that lowers to an *inline* ISA
 * instruction -- `fabs`/`copysign` via `fosgnj` (contract-fp.md §7: sgnj(a, b)
 * = copySign(a, b)) -- and returns a distinct non-zero guest exit code per
 * failing case (0 = everything correct).
 *
 * The P1 *libcall* classes (floor/ceil/trunc/round/rint/nearbyint, fmin/fmax)
 * need picolibc's out-of-line math routines at link time and are covered by the
 * evidence runner (<taskdir> picolibc test-floor/test-ceil/test-round on QEMU)
 * and by the CodeGen vectors tests/unit/llvm/lit/CodeGen/DADAO/p1-fp-*.ll.
 *
 * All inputs are `volatile` so clang cannot constant-fold the operations away;
 * the `fosgnj`/`rd2rf` sequence then actually runs on the guest.  Expected
 * values follow from IEEE-754 / copySign semantics -- they are not read back
 * from llc.
 */

volatile double vpos  = 2.5;
volatile double vneg  = -1.5;
volatile double vnegz = -0.0;
volatile double vposz = 0.0;

int main(void)
{
    /* copysign(magnitude, sign): the sign of the second operand is copied. */
    if (__builtin_copysign(vpos, vneg) != -2.5)
        return 1;
    if (__builtin_copysign(vneg, vpos) != 1.5)
        return 2;

    /* fabs clears the sign bit (x and -x map to the same magnitude). */
    if (__builtin_fabs(vneg) != 1.5)
        return 3;
    if (__builtin_fabs(vpos) != 2.5)
        return 4;

    /* copysign of a zero magnitude keeps the copied sign on the zero. */
    if (!(__builtin_copysign(vposz, vnegz) == 0.0))
        return 5;

    /* Signed-zero identity: copysign(+0, -0) is -0 (bit pattern 0x8000...). */
    {
        union { double d; unsigned long long u; } r;
        r.d = __builtin_copysign(vposz, vnegz);
        if (r.u != 0x8000000000000000ULL)
            return 6;
    }

    return 0;
}
