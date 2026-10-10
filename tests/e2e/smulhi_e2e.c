/* smulhi_e2e.c — LLVM-076t (M6, ISS-185) end-to-end vector.
 *
 * Freestanding (no libc): crt0 reports `main`'s return value as the guest exit
 * code (low byte; tests/scripts/codegen_crt0.s, contract-semihosting.md §3).
 *
 * Exercises the 64x64 *signed* high-half multiply that ISS-185 was about.  The
 * DADAO `mul.so` instruction produces the full 128-bit signed product
 * (contract-isa.md §6.1.4: rdha:rdhb = rdhc x rdhd), so both the high half
 * (`mulhs`) and the whole signed product (`smul_lohi`) are selectable natively.
 * Because the exit code is only the low byte, this one source is compiled once
 * per BYTE (0..7) and the harness reconstructs the full 64-bit result.  Expected
 * values are computed from the inputs by an independent host big-integer oracle
 * (host Python signed integers) — none are hard-coded here.
 *
 * The input tables hold the two's-complement bit patterns of the signed 64-bit
 * operands (`long a = (long)IN_A[CASE]`); the harness reads them straight out
 * of this file (single source of truth) and reinterprets them as signed.
 *
 * Compile-time selectors (all default to 0):
 *   MODE  0 = lo            (low half of the 128-bit product)
 *         1 = hi            (high half; mulhs)
 *         2 = a*b / C       (C a non-power-of-two divisor -> signed magic-const
 *                            multiply, i.e. mulhs of the 64-bit product)
 *         3 = hi - lo       (uses both halves -> keeps the 128-bit product;
 *                            NON-COMMUTATIVE, so a high/low half swap changes
 *                            the result — lessons §8.46)
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

/* Boundary inputs (two's complement): -1, 2^63-1, -2^63, cross-2^32, mixed. */
static volatile unsigned long IN_A[] = {
    0xffffffffffffffffUL, /* 1  -1                 */
    0x7fffffffffffffffUL, /* 2  2^63-1             */
    0x8000000000000000UL, /* 3  -2^63              */
    0x0000000100000001UL, /* 4  2^32+1             */
    0x0000000100000001UL, /* 5  2^32+1             */
    0x123456789abcdef0UL, /* 6  0x123456789abcdef0 */
    0x7fffffffffffffffUL, /* 7  2^63-1             */
    0x8000000000000000UL, /* 8  -2^63              */
    0x0000000000000003UL, /* 9  3                  */
    0x0000000100000003UL, /* 10 2^32+3             */
};
static volatile unsigned long IN_B[] = {
    0xffffffffffffffffUL, /* 1  -1  (a*b = 1)                    */
    0x7fffffffffffffffUL, /* 2  2^63-1  ((2^63-1)^2)             */
    0x8000000000000000UL, /* 3  -2^63   ((-2^63)^2 = 2^126)      */
    0x0000000100000001UL, /* 4  2^32+1  ((2^32+1)^2)             */
    0xfffffffeffffffffUL, /* 5  -(2^32+1)                        */
    0x89abcdef01234568UL, /* 6  -0x76543210fedcba98              */
    0x8000000000000000UL, /* 7  -2^63  ((2^63-1)(-2^63))         */
    0x7fffffffffffffffUL, /* 8  2^63-1 ((-2^63)(2^63-1))         */
    0xfffffffffffffff9UL, /* 9  -7                               */
    0xfffffffffffffffbUL, /* 10 -5                               */
};

/* Non-power-of-two divisor for MODE 2 (all cases share it). */
static volatile long DIVISOR = 3;

long main(void) {
  long a = (long)IN_A[CASE];
  long b = (long)IN_B[CASE];
  unsigned long r;

#if MODE == 0
  r = (unsigned long)(signed __int128)a * b; /* low 64 bits */
#elif MODE == 1
  r = (unsigned long)(((signed __int128)a * b) >> 64); /* high half (mulhs) */
#elif MODE == 2
  {
    long t = a * b; /* 64-bit product (wraps; machine semantics) */
    r = (unsigned long)(t / DIVISOR); /* sdiv-by-constant -> mulhs of magic */
  }
#else
  {
    signed __int128 p = (signed __int128)a * b;
    unsigned long lo = (unsigned long)p;
    unsigned long hi = (unsigned long)(p >> 64);
    r = hi - lo; /* NON-COMMUTATIVE (lessons §8.46) */
  }
#endif

  return (long)((r >> (BYTE * 8)) & 0xff);
}
