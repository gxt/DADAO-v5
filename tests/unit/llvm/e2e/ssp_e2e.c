/*
 * Stack-protector end-to-end vector (m14-llvm-002).
 *
 * One source, two links, so the only difference between the control and the
 * trigger run is the number of bytes written into the 16-byte stack buffer:
 *
 *   control  (no -D)         probe_count = 16: the buffer is written exactly
 *                            in full.  The canary the prologue stored still
 *                            matches in the epilogue, so __stack_chk_fail must
 *                            NOT run and the guest exits 0.
 *   trigger  (-DSSP_TRIGGER) probe_count = 32: the same 16-byte buffer is
 *                            overrun by 16 bytes.  The stores past the end must
 *                            land on the canary slot; the epilogue compare then
 *                            fails, __stack_chk_fail runs and the guest exits
 *                            66.
 *
 * ssp_runtime.s supplies the two externals the compiler only declares:
 * __stack_chk_guard (a non-zero .data constant) and __stack_chk_fail (the
 * SYS_EXIT sequence with code 66).  A 0 exit from the trigger, or 66 from the
 * control, therefore means the check did not fire / fired spuriously -- the
 * lit RUN lines assert the exact code with `test $? -eq N`.
 *
 * The buffer is volatile so clang cannot fold the writes away, and the loop
 * bound comes from a volatile global so that at -O2 the loop is neither
 * unrolled nor the array scalarised: an array-shaped local must still be
 * present when the stack protector pass runs, otherwise -fstack-protector-*
 * has nothing to protect and the vector would pass without exercising the
 * check (a constant 32 would additionally let the compiler treat the overrun
 * as UB).
 */

volatile int probe_result;

#ifdef SSP_TRIGGER
volatile int probe_count = 32;
#else
volatile int probe_count = 16;
#endif

__attribute__((noinline)) static int probe(int n)
{
    volatile unsigned char buf[16];
    int i;

    for (i = 0; i < n; i++)
        buf[i] = (unsigned char)(i + 1);

    /* buf[0] = 1, buf[15] = 16 in both runs. */
    return buf[0] + buf[15];
}

int main(void)
{
    probe_result = probe(probe_count);
    return probe_result == 17 ? 0 : 9;
}
