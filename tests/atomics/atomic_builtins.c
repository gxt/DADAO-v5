/*
 * atomic_builtins.c -- GCC `__atomic_*` builtins over every access width
 * (TESTCASES-056t, family C).
 *
 * Purpose
 *   Prove that the *builtin* family -- not only the C11 wrappers -- is lowered
 *   to the backend's lr/sc + fence sequence, with the right value semantics at
 *   each access width.  The link-time half of the claim (no `__atomic_*` in the
 *   undefined-symbol table, i.e. no libatomic call) is asserted by the driver
 *   with llvm-nm on the compiled object and on the linked image.
 *
 * Matrix
 *   widths   {1, 2, 4, 8} bytes (uint8_t/uint16_t/uint32_t/uint64_t)
 *   builtins __atomic_load_n, store_n, exchange_n, fetch_add, fetch_sub,
 *            fetch_and, fetch_or, fetch_xor, compare_exchange_n
 *   orders   __ATOMIC_{RELAXED, ACQUIRE, RELEASE, ACQ_REL, SEQ_CST}
 *   compare_exchange_n : success (expected == object) and failure
 *                        (expected != object) variants
 *
 * Sub-word safety (1/2 bytes, and 4 bytes on an 8-byte word)
 *   Each operation works on one field of a 24-byte buffer filled with 0xA5 and
 *   is followed by a neighbour check: every byte outside [field, field+width)
 *   must still be 0xA5 (`neigh=1`).  Read-modify-write at a narrow width must
 *   not clobber the rest of the guarded word (the backend synthesises narrow
 *   RMW from lr/sc plus masking).
 *
 * Known narrowing defect (measured, not assumed)
 *   `lr.{b,w,t}` zero-extends, while the i64 promoted comparison operand of a
 *   narrow cmpxchg is sign-extended for values with the top bit set, so
 *   `compare_exchange_n` on 1/2/4-byte objects always *fails* for such a
 *   value.  Those cells are emitted as `op=compare_exchange_edge` and the
 *   oracle marks them XFAIL (see oracle_atomics.KNOWN_DEFECT); the 8-byte edge
 *   case is the control that must pass.  Nothing here counts them as PASS.
 *
 * Oracle (independent, tools/testcases/oracle_atomics.py)
 *   Pure Python value model for each (width, builtin, order); no component
 *   product is imported and no expectation is read back from this program.
 *
 * Output
 *   BUILTIN w=<bytes> op=<name> order=<order> ret=<value|na> fin=<value> neigh=<0|1> [exp=<value>]
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static const int mo[5] = {__ATOMIC_RELAXED, __ATOMIC_ACQUIRE, __ATOMIC_RELEASE,
                          __ATOMIC_ACQ_REL, __ATOMIC_SEQ_CST};
static const char *const mon[5] = {"relaxed", "acquire", "release", "acq_rel",
                                   "seq_cst"};

/* Every byte outside the operated field must keep the 0xA5 fill. */
static int neigh_ok(const unsigned char *buf, unsigned width)
{
    unsigned i;

    for (i = 0; i < 8; i++)
        if (buf[i] != 0xA5)
            return 0;
    for (i = 8 + width; i < 24; i++)
        if (buf[i] != 0xA5)
            return 0;
    return 1;
}

#define B_NUM(W, OP, ORD, RET, FIN, NEIGH)                                    \
    printf("BUILTIN w=%u op=%s order=%s ret=%llu fin=%llu neigh=%d\n",         \
           (unsigned)(W), (OP), (ORD), (unsigned long long)(RET),              \
           (unsigned long long)(FIN), (NEIGH))
#define B_NARET(W, OP, ORD, FIN, NEIGH)                                       \
    printf("BUILTIN w=%u op=%s order=%s ret=na fin=%llu neigh=%d\n",           \
           (unsigned)(W), (OP), (ORD), (unsigned long long)(FIN), (NEIGH))
#define B_CAS(W, OP, ORD, RET, FIN, EXP, NEIGH)                               \
    printf("BUILTIN w=%u op=%s order=%s ret=%d fin=%llu exp=%llu neigh=%d\n",  \
           (unsigned)(W), (OP), (ORD), (RET), (unsigned long long)(FIN),       \
           (unsigned long long)(EXP), (NEIGH))

/* One width row: all nine builtins x five orders (+ the two edge cells). */
#define BUILTIN_WIDTH(W, T, INIT, ARG)                                        \
    do {                                                                      \
        int i;                                                                \
        T r, v, e;                                                            \
        unsigned char *p;                                                     \
        _Alignas(8) unsigned char buf[24];                                    \
        for (i = 0; i < 5; i++) {                                             \
            memset(buf, 0xA5, sizeof buf);                                    \
            p = buf + 8;                                                      \
            *(T *)p = (T)(INIT);                                              \
            r = __atomic_load_n((T *)p, mo[i]);                               \
            v = *(T *)p;                                                      \
            B_NUM(W, "load_n", mon[i], r, v, neigh_ok(buf, (W)));             \
            memset(buf, 0xA5, sizeof buf);                                    \
            p = buf + 8;                                                      \
            *(T *)p = (T)(INIT);                                              \
            __atomic_store_n((T *)p, (T)(ARG), mo[i]);                        \
            v = *(T *)p;                                                      \
            B_NARET(W, "store_n", mon[i], v, neigh_ok(buf, (W)));             \
            memset(buf, 0xA5, sizeof buf);                                    \
            p = buf + 8;                                                      \
            *(T *)p = (T)(INIT);                                              \
            r = __atomic_exchange_n((T *)p, (T)(ARG), mo[i]);                 \
            v = *(T *)p;                                                      \
            B_NUM(W, "exchange_n", mon[i], r, v, neigh_ok(buf, (W)));         \
            memset(buf, 0xA5, sizeof buf);                                    \
            p = buf + 8;                                                      \
            *(T *)p = (T)(INIT);                                              \
            r = __atomic_fetch_add((T *)p, (T)1, mo[i]);                      \
            v = *(T *)p;                                                      \
            B_NUM(W, "fetch_add", mon[i], r, v, neigh_ok(buf, (W)));          \
            memset(buf, 0xA5, sizeof buf);                                    \
            p = buf + 8;                                                      \
            *(T *)p = (T)(INIT);                                              \
            r = __atomic_fetch_sub((T *)p, (T)2, mo[i]);                      \
            v = *(T *)p;                                                      \
            B_NUM(W, "fetch_sub", mon[i], r, v, neigh_ok(buf, (W)));          \
            memset(buf, 0xA5, sizeof buf);                                    \
            p = buf + 8;                                                      \
            *(T *)p = (T)(INIT);                                              \
            r = __atomic_fetch_and((T *)p, (T)(ARG), mo[i]);                  \
            v = *(T *)p;                                                      \
            B_NUM(W, "fetch_and", mon[i], r, v, neigh_ok(buf, (W)));          \
            memset(buf, 0xA5, sizeof buf);                                    \
            p = buf + 8;                                                      \
            *(T *)p = (T)(INIT);                                              \
            r = __atomic_fetch_or((T *)p, (T)(ARG), mo[i]);                   \
            v = *(T *)p;                                                      \
            B_NUM(W, "fetch_or", mon[i], r, v, neigh_ok(buf, (W)));           \
            memset(buf, 0xA5, sizeof buf);                                    \
            p = buf + 8;                                                      \
            *(T *)p = (T)(INIT);                                              \
            r = __atomic_fetch_xor((T *)p, (T)(ARG), mo[i]);                  \
            v = *(T *)p;                                                      \
            B_NUM(W, "fetch_xor", mon[i], r, v, neigh_ok(buf, (W)));          \
            memset(buf, 0xA5, sizeof buf);                                    \
            p = buf + 8;                                                      \
            *(T *)p = (T)(INIT);                                              \
            e = (T)(INIT);                                                    \
            r = (T)__atomic_compare_exchange_n((T *)p, &e, (T)(ARG), 0,      \
                                               mo[i], __ATOMIC_ACQUIRE);      \
            v = *(T *)p;                                                      \
            B_CAS(W, "compare_exchange_ok", mon[i], (int)r, v, e,            \
                  neigh_ok(buf, (W)));                                        \
            memset(buf, 0xA5, sizeof buf);                                    \
            p = buf + 8;                                                      \
            *(T *)p = (T)(INIT);                                              \
            e = (T)(ARG);                                                     \
            r = (T)__atomic_compare_exchange_n((T *)p, &e, (T)(ARG), 0,      \
                                               mo[i], __ATOMIC_ACQUIRE);      \
            v = *(T *)p;                                                      \
            B_CAS(W, "compare_exchange_fail", mon[i], (int)r, v, e,          \
                  neigh_ok(buf, (W)));                                        \
        }                                                                     \
        /* narrowing edge: object and expected share a top-bit-set value */   \
        memset(buf, 0xA5, sizeof buf);                                        \
        p = buf + 8;                                                          \
        *(T *)p = (T)((unsigned long long)(INIT) |                            \
                      ((unsigned long long)1 << (8 * (W) - 1)));              \
        e = *(T *)p;                                                          \
        r = (T)__atomic_compare_exchange_n((T *)p, &e, (T)0, 0,              \
                                           __ATOMIC_SEQ_CST,                  \
                                           __ATOMIC_ACQUIRE);                  \
        v = *(T *)p;                                                          \
        B_CAS(W, "compare_exchange_edge", "seq_cst", (int)r, v, e,            \
              neigh_ok(buf, (W)));                                            \
    } while (0)

/* ---- shared-object cells (the real cross-thread path) ---------------------
 * The matrix above works on an automatic buffer, which the optimiser may see
 * as thread-local; these cells touch file-scope objects from a noinline
 * function.  Measured backend defect: an 8-byte-destination `__atomic_store_n`
 * stores the *address* instead of the value (see the file header); the loads
 * below are the required-to-pass controls.
 */
static uint8_t gb1 = 0x11;
static uint16_t gb2 = 0x1122;
static uint32_t gb4 = 0x11223344;
static uint64_t gb8 = 0x1122334455667788ULL;

__attribute__((noinline)) static void shared_store1(uint8_t v)
{
    __atomic_store_n(&gb1, v, __ATOMIC_RELEASE);
}
__attribute__((noinline)) static void shared_store2(uint16_t v)
{
    __atomic_store_n(&gb2, v, __ATOMIC_RELEASE);
}
__attribute__((noinline)) static void shared_store4(uint32_t v)
{
    __atomic_store_n(&gb4, v, __ATOMIC_RELEASE);
}
__attribute__((noinline)) static void shared_store8(uint64_t v)
{
    __atomic_store_n(&gb8, v, __ATOMIC_RELEASE);
}

int main(void)
{
    BUILTIN_WIDTH(1, uint8_t, 0x11, 0x22);
    BUILTIN_WIDTH(2, uint16_t, 0x1122, 0x3344);
    BUILTIN_WIDTH(4, uint32_t, 0x11223344, 0x55667788);
    BUILTIN_WIDTH(8, uint64_t, 0x1122334455667788ULL,
                  0x5566778899AABBCCULL);
    printf("SBUILTIN w=1 op=load_n addr=%llx ret=%llu fin=%llu\n",
           (unsigned long long)(uintptr_t)&gb1,
           (unsigned long long)__atomic_load_n(&gb1, __ATOMIC_SEQ_CST),
           (unsigned long long)__atomic_load_n(&gb1, __ATOMIC_SEQ_CST));
    printf("SBUILTIN w=2 op=load_n addr=%llx ret=%llu fin=%llu\n",
           (unsigned long long)(uintptr_t)&gb2,
           (unsigned long long)__atomic_load_n(&gb2, __ATOMIC_SEQ_CST),
           (unsigned long long)__atomic_load_n(&gb2, __ATOMIC_SEQ_CST));
    printf("SBUILTIN w=4 op=load_n addr=%llx ret=%llu fin=%llu\n",
           (unsigned long long)(uintptr_t)&gb4,
           (unsigned long long)__atomic_load_n(&gb4, __ATOMIC_SEQ_CST),
           (unsigned long long)__atomic_load_n(&gb4, __ATOMIC_SEQ_CST));
    printf("SBUILTIN w=8 op=load_n addr=%llx ret=%llu fin=%llu\n",
           (unsigned long long)(uintptr_t)&gb8,
           (unsigned long long)__atomic_load_n(&gb8, __ATOMIC_SEQ_CST),
           (unsigned long long)__atomic_load_n(&gb8, __ATOMIC_SEQ_CST));
    shared_store1(0x22);
    printf("SBUILTIN w=1 op=store_n addr=%llx fin=%llu\n",
           (unsigned long long)(uintptr_t)&gb1,
           (unsigned long long)__atomic_load_n(&gb1, __ATOMIC_SEQ_CST));
    shared_store2(0x3344);
    printf("SBUILTIN w=2 op=store_n addr=%llx fin=%llu\n",
           (unsigned long long)(uintptr_t)&gb2,
           (unsigned long long)__atomic_load_n(&gb2, __ATOMIC_SEQ_CST));
    shared_store4(0x55667788);
    printf("SBUILTIN w=4 op=store_n addr=%llx fin=%llu\n",
           (unsigned long long)(uintptr_t)&gb4,
           (unsigned long long)__atomic_load_n(&gb4, __ATOMIC_SEQ_CST));
    shared_store8(0x5566778899AABBCCULL);
    printf("SBUILTIN w=8 op=store_n addr=%llx fin=%llu\n",
           (unsigned long long)(uintptr_t)&gb8,
           (unsigned long long)__atomic_load_n(&gb8, __ATOMIC_SEQ_CST));
    return 0;
}
