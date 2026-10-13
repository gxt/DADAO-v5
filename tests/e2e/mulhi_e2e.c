/* mulhi_e2e.c — LLVM-073t (M6, ISS-176 / G2) end-to-end vector.
 *
 * Freestanding (no libc): crt0 reports `main`'s return value as the guest exit
 * code (low byte; tests/scripts/codegen_crt0.s, contract-semihosting.md §3).
 *
 * Exercises the 64x64 high-half multiply that G2 was about.  The DADAO `mul.uo`
 * instruction produces the full 128-bit product (contract-isa.md §6.1.4:
 * rdha:rdhb = rdhc x rdhd), so both the high half (`mulhu`) and the whole
 * product (`umul_lohi`) are selectable natively.  Because the exit code is only
 * the low byte, this one source is compiled once per BYTE (0..7) and the
 * harness reconstructs the full 64-bit result.  Expected values are computed
 * from the inputs by an independent host big-integer oracle — none are
 * hard-coded here.
 *
 * Compile-time selectors (all default to 0):
 *   MODE  0 = a*b            (low half)
 *         1 = (a*b) >> 64   (high half, 128-bit product)
 *         2 = a*b / C       (C a non-power-of-two divisor -> mulhu by magic const)
 *         3 = lo ^ hi       (uses both halves -> keeps the 128-bit product)
 *   CASE  index into the boundary input table
 *   BYTE  which byte of the 64-bit result to return (0 = least significant)
 */

#ifndef MODE
#define MODE 0
#endif
#ifndef CASE
#define CASE 0
#endif
#ifndef BYTE
#define BYTE 0
#endif

/* Boundary inputs: 2^64-1, cross-2^32, 2^63, and mixed large values. */
static volatile unsigned long IN_A[] = {
    0xffffffffffffffffUL, /* 1  2^64-1        */
    0xffffffffffffffffUL, /* 2  2^64-1        */
    0x0000000100000000UL, /* 3  2^32          */
    0x0000000100000001UL, /* 4  2^32+1        */
    0x8000000000000000UL, /* 5  2^63          */
    0x00000000ffffffffUL, /* 6  2^32-1        */
    0x123456789abcdef0UL, /* 7  large mixed   */
    0x8000000000000000UL, /* 8  2^63          */
    0x0000000000000003UL, /* 9  small         */
    0x0000000100000003UL, /* 10 2^32+3        */
};
static volatile unsigned long IN_B[] = {
    0xffffffffffffffffUL, /* 1  (2^64-1)^2        */
    0x0000000000000001UL, /* 2  (2^64-1)*1        */
    0x0000000100000000UL, /* 3  2^32 * 2^32       */
    0x0000000100000001UL, /* 4  (2^32+1)^2        */
    0x8000000000000000UL, /* 5  2^63 * 2^63       */
    0xffffffffffffffffUL, /* 6  (2^32-1)(2^64-1)  */
    0xfedcba9876543210UL, /* 7  large mixed       */
    0xffffffffffffffffUL, /* 8  2^63 (2^64-1)     */
    0xaaaaaaaaaaaaaaaaUL, /* 9  alternating bits  */
    0x0000000000000005UL, /* 10 1 * 5 (2^32+3)    */
};

/* Non-power-of-two divisor for MODE 2 (all cases share it). */
static volatile unsigned long DIVISOR = 3;

long main(void) {
  unsigned long a = IN_A[CASE];
  unsigned long b = IN_B[CASE];
  unsigned long r;

#if MODE == 0
  r = a * b; /* low 64 bits (wraps) */
#elif MODE == 1
  r = (unsigned long)(((unsigned __int128)a * b) >> 64);
#elif MODE == 2
  r = a * b / DIVISOR; /* udiv-by-constant -> mulhu with the magic constant */
#else
  {
    unsigned __int128 p = (unsigned __int128)a * b;
    unsigned long lo = (unsigned long)p;
    unsigned long hi = (unsigned long)(p >> 64);
    r = lo ^ hi; /* uses both halves, so the full product is kept */
  }
#endif

  return (long)((r >> (BYTE * 8)) & 0xff);
}
