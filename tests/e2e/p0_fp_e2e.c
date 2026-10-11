/*
 * P0 FP/bit-codegen end-to-end vector (LLVM-079t).
 *
 * Exercises all five P0 ISel classes the backend gained and returns a distinct
 * non-zero guest exit code per failing class (0 = everything correct):
 *
 *   gap 1  f32 -> f64 "anyext" load      (fpext of a loaded float; ft2fo)
 *   gap 2  FP compare used as a value    (foqcmp + cs.z/n/p)
 *   gap 3  f64 <-> i64 bitcast           (rd2rf / rf2rd)
 *   gap 4  integer compare selecting f64 (cmp.si/ui + cs.n/z onto rf)
 *   gap 5  i64 cttz                      (generic expansion; no libcall)
 *
 * All inputs are `volatile` so clang cannot constant-fold the operations away,
 * the comparison/select results are consumed as *values* (not immediately as
 * branch conditions) so the value forms survive to ISel, and the expected
 * values follow from IEEE-754 / two's-complement semantics -- they are not
 * read back from llc.
 *
 * The companion codegen vectors in tests/llvm/lit/CodeGen/DADAO/p0-*.ll pin the
 * exact instructions; this test pins the runtime behaviour.
 */

typedef unsigned long long u64;
typedef long long i64;

volatile float  vf = 2.5f;
volatile double vd = 6.25;
volatile double va = 1.5;
volatile double vc = 0.125;
volatile i64    nneg = -1;
volatile i64    npos = 1;
volatile u64    vctz = 0x100;
volatile u64    vone = 1;       /* cttz input */
volatile u64    sink;           /* forces the cttz result to be materialised */

static double pick(i64 n, double t, double f) { return n < 0 ? t : f; }

int main(void)
{
    /* gap 1: (double)2.5f + 0.5 == 3.0; the addend is exact, so the sum is
       representable and the result is required by IEEE-754 alone. */
    if ((double)vf + 0.5 != 3.0)
        return 1;

    /* gap 2: the two FP comparisons are combined as *values*
       (6.25 <= 0.0 is false, 6.25 != 0.0 is true, 6.25 > 0.0 is true). */
    int c = (vd <= 0.0) + (vd != 0.0) + (vd > 0.0);
    if (c != 2)
        return 2;
    if ((vc < va) + (vc == va) + (vc > va) != 1)
        return 3;

    /* gap 3: bitcast f64 <-> i64 keeps the 64 bits unchanged
       (1.5 == 0x3FF8000000000000 as an IEEE-754 double). */
    if (__builtin_bit_cast(u64, va) != 0x3FF8000000000000ULL)
        return 4;
    if (__builtin_bit_cast(double, __builtin_bit_cast(u64, va)) != 1.5)
        return 5;

    /* gap 4: an integer comparison selects between two FP values, combined in
       FP arithmetic (pick(-1) = 10.0, pick(1) = 20.0 -> 30.0). */
    if (pick(nneg, 10.0, 20.0) + pick(npos, 10.0, 20.0) != 30.0)
        return 6;

    /* gap 5: cttz of a power of two / of one.  The result is written to a
       volatile sink first so InstCombine cannot rewrite `cttz(x) == C` into a
       mask comparison and the actual cttz lowering runs. */
    sink = __builtin_ctzll(vctz);
    if (sink != 8)
        return 7;
    sink = __builtin_ctzll(vone);
    if (sink != 0)
        return 8;

    return 0;
}
