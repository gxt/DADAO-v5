/*
 * `atomics_e2e` -- compiler-level atomics on the Tiny machine (M13, TESTCASES-050).
 *
 * Layer split (user ruling A, 2026-11-15): the *instruction* layer (lr/sc RMW
 * synthesis order) is carried by `tests/inst/00-isa-design/atomic_rmw.S`
 * (m13-testcases-049); the *compiler* layer -- the value semantics of the
 * `__atomic_*` builtins and the C11 `<stdatomic.h>` wrappers -- is what this
 * guest program executes for real.  Contention behaviour (ABA, mutual-exclusion
 * counters, `a_barrier` observables, `fence` ordering strength) cannot be
 * observed on one hart and is registered as a GAP in `tests/inst/MIGRATION.md`.
 *
 * Contract: `contract-isa.md` `lr`/`sc` (load-reserved / store-conditional) and
 * `spec/SimRISC-12` `fence`; the C-level expectations below are plain C11
 * semantics, not read back from compiler or emulator output.
 *
 * Objects are file-scope, so the optimiser cannot treat them as
 * single-thread-confined and elide the atomic path; every read-modify-write
 * goes through a real `lr`/`sc` retry loop (single hart: the loop succeeds on
 * the first try).
 *
 * Exit code = first failing check number (0 = all pass); the QEMU guest exit
 * code is the test result (same shape as `fma_e2e.c`, which prints nothing:
 * the DADAO e2e programs are freestanding, there is no stdio).  The check
 * numbers are listed next to each block below and in `lit/atomics_e2e.test`.
 *
 * Two regressions that the retired C probes used to carry are kept here as
 * plain assertions (both fixed by LLVM-121t, `ISS-312` / `ISS-313`): the
 * 8-byte `__atomic_store_n` must store the VALUE, not the object address
 * (check 19), and a narrow `compare_exchange` whose compared value has the top
 * bit set must SUCCEED (check 20, `lr.b` zero-extends).
 */
#include <stdatomic.h>
#include <stdint.h>

_Static_assert(_Alignof(_Atomic uint32_t) == 4, "atomic uint32_t must be 4-byte aligned");
_Static_assert(_Alignof(_Atomic uint64_t) == 8, "atomic uint64_t must be 8-byte aligned");

static uint32_t p32;             /* plain object + `__atomic_*` builtins */
static uint64_t p64;
static _Atomic uint32_t a32;     /* C11 <stdatomic.h> objects */
static _Atomic uint64_t a64;
static uint8_t p8;

/* Narrow RMW neighbours: `pre`/`post` sit immediately around the operated
 * field, so a sub-word read-modify-write that wrote the whole word would
 * clobber them.  Each field has its natural alignment (no pointer casts). */
static struct { uint8_t pre, field, post; } sw8;
static struct { uint16_t pre, field, post; } sw16;
static struct { uint32_t pre, field, post; } sw32;

int main(void)
{
    unsigned r32;
    uint64_t r64;
    unsigned exp32;
    uint64_t exp64;
    uint8_t e8;
    int ok;

    /* ---- A. `__atomic_fetch_*`: returns the OLD value, memory gets the new */
    p32 = 100;
    r32 = __atomic_fetch_add(&p32, 5, __ATOMIC_SEQ_CST);
    if (r32 != 100 || p32 != 105)                       /* check 1 */
        return 1;

    p32 = 105;
    r32 = __atomic_fetch_sub(&p32, 10, __ATOMIC_ACQ_REL);
    if (r32 != 105 || p32 != 95)                        /* check 2 */
        return 2;

    p32 = 0xF0;
    r32 = __atomic_fetch_and(&p32, 0x3C, __ATOMIC_SEQ_CST);
    if (r32 != 0xF0 || p32 != 0x30)                     /* check 3 */
        return 3;

    p32 = 0x0F;
    r32 = __atomic_fetch_or(&p32, 0xF0, __ATOMIC_SEQ_CST);
    if (r32 != 0x0F || p32 != 0xFF)                     /* check 4 */
        return 4;

    p32 = 0xFF;
    r32 = __atomic_fetch_xor(&p32, 0x0F, __ATOMIC_SEQ_CST);
    if (r32 != 0xFF || p32 != 0xF0)                     /* check 5 */
        return 5;

    p64 = 0x0000000100000000ULL;          /* high half non-zero: 64-bit carry */
    r64 = __atomic_fetch_add(&p64, 1, __ATOMIC_SEQ_CST);
    if (r64 != 0x0000000100000000ULL || p64 != 0x0000000100000001ULL)
        return 6;                                       /* check 6 */

    /* ---- B. `__atomic_exchange`: returns the old value, memory gets the new */
    p64 = 0x1122334455667788ULL;
    r64 = __atomic_exchange_n(&p64, 0x99AABBCCDDEEFF00ULL, __ATOMIC_SEQ_CST);
    if (r64 != 0x1122334455667788ULL || p64 != 0x99AABBCCDDEEFF00ULL)
        return 7;                                       /* check 7 */

    p32 = 0x0BADF00D;
    r32 = __atomic_exchange_n(&p32, 0x12345678, __ATOMIC_ACQ_REL);
    if (r32 != 0x0BADF00D || p32 != 0x12345678)         /* check 8 */
        return 8;

    /* ---- C. `__atomic_compare_exchange_n`: success and failure paths ------- */
    p32 = 0x1234;                         /* success: store, expected untouched */
    exp32 = 0x1234;
    ok = __atomic_compare_exchange_n(&p32, &exp32, 0x5678, 0, __ATOMIC_SEQ_CST,
                                     __ATOMIC_ACQUIRE);
    if (!ok || p32 != 0x5678 || exp32 != 0x1234)        /* check 9 */
        return 9;

    p32 = 0x1234;                         /* failure: memory MUST stay unchanged */
    exp32 = 0x9999;
    ok = __atomic_compare_exchange_n(&p32, &exp32, 0x5678, 0, __ATOMIC_SEQ_CST,
                                     __ATOMIC_ACQUIRE);
    if (ok || p32 != 0x1234 || exp32 != 0x1234)         /* check 10 */
        return 10;

    p64 = 0x0000000100000002ULL;          /* 8-byte success */
    exp64 = 0x0000000100000002ULL;
    ok = __atomic_compare_exchange_n(&p64, &exp64, 0x0000000300000004ULL, 0,
                                     __ATOMIC_SEQ_CST, __ATOMIC_ACQUIRE);
    if (!ok || p64 != 0x0000000300000004ULL || exp64 != 0x0000000100000002ULL)
        return 11;                                      /* check 11 */

    p64 = 0x0000000100000002ULL;          /* 8-byte failure: memory unchanged */
    exp64 = 0x0000000100000003ULL;
    ok = __atomic_compare_exchange_n(&p64, &exp64, 0x0000000300000004ULL, 0,
                                     __ATOMIC_SEQ_CST, __ATOMIC_ACQUIRE);
    if (ok || p64 != 0x0000000100000002ULL || exp64 != 0x0000000100000002ULL)
        return 12;                                      /* check 12 */

    /* ---- D. sub-word read-modify-write must not clobber the guarded word -- */
    sw8.pre = 0xA5; sw8.post = 0xA5;
    sw8.field = 0x0F;
    r32 = __atomic_fetch_or(&sw8.field, 0xF0u, __ATOMIC_SEQ_CST);
    if (r32 != 0x0F || sw8.field != 0xFF || sw8.pre != 0xA5 || sw8.post != 0xA5)
        return 13;                                      /* check 13 */

    sw16.pre = 0xA5A5; sw16.post = 0xA5A5;
    sw16.field = 0x00FF;
    r32 = __atomic_fetch_or(&sw16.field, 0x0F00u, __ATOMIC_SEQ_CST);
    if (r32 != 0x00FF || sw16.field != 0x0FFF || sw16.pre != 0xA5A5 ||
        sw16.post != 0xA5A5)                            /* check 14 */
        return 14;

    sw32.pre = 0xA5A5A5A5u; sw32.post = 0xA5A5A5A5u;
    sw32.field = 0x0000FFFFu;
    r32 = __atomic_fetch_or(&sw32.field, 0x001E0000u, __ATOMIC_SEQ_CST);
    if (r32 != 0x0000FFFFu || sw32.field != 0x001EFFFFu ||
        sw32.pre != 0xA5A5A5A5u || sw32.post != 0xA5A5A5A5u)
        return 15;                                      /* check 15 */

    /* ---- E. C11 <stdatomic.h> wrappers (type + alignment via _Static_assert) */
    atomic_init(&a32, 41);
    r32 = atomic_fetch_add(&a32, 7);
    if (r32 != 41 || atomic_load(&a32) != 48)           /* check 16 */
        return 16;

    atomic_init(&a64, 0x00000000DEADBEEFULL);
    r64 = atomic_exchange(&a64, 0x00000001CAFEF00DULL);
    if (r64 != 0x00000000DEADBEEFULL || atomic_load(&a64) != 0x00000001CAFEF00DULL)
        return 17;                                      /* check 17 */

    atomic_init(&a32, 0x1111);
    exp32 = 0x1111;
    ok = atomic_compare_exchange_strong(&a32, &exp32, 0x2222);
    if (!ok || atomic_load(&a32) != 0x2222 || exp32 != 0x1111)
        return 18;                                      /* check 18 */

    /* ---- F. retired-probe regressions kept as plain assertions ------------- */
    p64 = 0x1111111111111111ULL;          /* ISS-312: store the VALUE */
    __atomic_store_n(&p64, 0x5566778899AABBCCULL, __ATOMIC_SEQ_CST);
    if (p64 != 0x5566778899AABBCCULL)                   /* check 19 */
        return 19;

    p8 = 0x80;                            /* ISS-313: top-bit-set narrow CAS */
    e8 = 0x80;
    ok = __atomic_compare_exchange_n(&p8, &e8, 0x7F, 0, __ATOMIC_SEQ_CST,
                                     __ATOMIC_ACQUIRE);
    if (!ok || p8 != 0x7F || e8 != 0x80)                /* check 20 */
        return 20;

    return 0;
}
