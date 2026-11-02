/*
 * LLVM-123t: `fofma`/`ftfma` single-rounding end-to-end vector.
 *
 * Contract: contract-fp.md §fma = SimRISC-07 §2.5 -- `fofma rfHA, rfHB, rfHC,
 * rfHD` computes rfHA <- rfHB * rfHC + rfHD with ONE rounding.  This file
 * distinguishes that from the two-step `a*b + c` (fmul + fadd, two roundings)
 * with inputs whose exact result is representable:
 *
 *   f64: a = b = 1 + 2^-52, c = -(1 + 2^-51)
 *        exact a*b + c = 2^-104   (fused, exactly representable)
 *        round(a*b) + c = 0       (a*b rounds to 1 + 2^-51)
 *
 *   f32: a = b = 1 + 2^-23, c = -(1 + 2^-22)
 *        exact a*b + c = 2^-46    (fused, exactly representable)
 *        roundf(a*b) + c = 0
 *
 * The expected values follow from IEEE-754 arithmetic (single rounding of an
 * exact result), not from reading back compiler output.  The `volatile`
 * intermediates force the two-step path to round separately: without them the
 * compiler would be free to contract `a*b + c` into the same fused operation.
 *
 * main() returns 0 when every check passes, a distinct non-zero code otherwise
 * (the QEMU guest exit code is the test result).
 */

double fma(double, double, double);
float fmaf(float, float, float);

/* Exactly one `fofma` (the C library-name path: clang knows `fma`). */
double fma_d(double a, double b, double c) { return fma(a, b, c); }

/* Exactly one `ftfma`. */
float fma_f(float a, float b, float c) { return fmaf(a, b, c); }

int main(void) {
    union { double d; unsigned long long u; } fused, split, want_fused;
    union { float f; unsigned int u; } fusedf, splitf, want_fusedf;
    volatile double a = 0x1.0000000000001p+0;  /* 1 + 2^-52 */
    volatile double c = -0x1.0000000000002p+0; /* -(1 + 2^-51) */
    volatile float af = 0x1.000002p+0f;        /* 1 + 2^-23 */
    volatile float cf = -0x1.000004p+0f;       /* -(1 + 2^-22) */
    volatile double prod;
    volatile float prodf;

    /* fused: one rounding, the exact product-sum is representable. */
    fused.d = __builtin_fma(a, a, c);
    want_fused.d = 0x1p-104;
    if (fused.u != want_fused.u)
        return 1;

    /* two-step: round(a*a) == 1 + 2^-51, so the difference cancels. */
    prod = a * a;
    split.d = prod + c;
    if (split.u != 0)
        return 2;

    /* the two paths must actually differ (this is the single-rounding claim). */
    if (fused.u == split.u)
        return 3;

    /* f32, same shape through the C library name `fmaf` -> ftfma. */
    fusedf.f = fmaf(af, af, cf);
    want_fusedf.f = 0x1p-46f;
    if (fusedf.u != want_fusedf.u)
        return 4;

    prodf = af * af;
    splitf.f = prodf + cf;
    if (splitf.u != 0)
        return 5;

    if (fusedf.u == splitf.u)
        return 6;

    /* the double helper must take the fused path too (one fofma, no fomul). */
    fused.d = fma_d(a, a, c);
    if (fused.u != want_fused.u)
        return 7;

    return 0;
}
