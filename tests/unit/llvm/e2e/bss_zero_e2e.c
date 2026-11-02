/* bss_zero_e2e.c — prove minimal_crt0 clears .bss itself (TESTCASES-091t).
 *
 * The array is a global with no initializer, so it lands in .bss.  The raw/ELF
 * loaders do NOT zero .bss; only minimal_crt0's explicit clear makes these
 * values zero.  main() returns 0 only when every element was cleared.
 */
static volatile unsigned long bss_probe[16] __attribute__((used));

long main(void)
{
    for (unsigned long i = 0; i < 16; i++) {
        if (bss_probe[i] != 0)
            return 1;
    }
    return 0;
}
