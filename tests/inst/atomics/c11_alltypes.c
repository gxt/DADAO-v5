/*
 * c11_alltypes.c -- C11 <stdatomic.h> value semantics over every scalar class
 * (TESTCASES-056t, family B).
 *
 * Purpose
 *   Exercise the *whole* C11 atomic API surface the port claims, on a single
 *   thread, so that "value" semantics can be judged without any memory-order
 *   observation: for every (type, operation, memory order) the probe prints the
 *   value the operation returned and the value a later seq_cst load sees.
 *
 * Types (one row per tag, widths are covered by construction)
 *   char, short, int, long            -- signed scalars (width 1/2/4/8)
 *   unsigned, size_t                  -- unsigned scalars (incl. values with
 *                                        bit 31 set, to catch zero/sign mixups)
 *   void *                            -- pointer atomics
 *
 * Operations / orders
 *   load            : relaxed, acquire, seq_cst
 *   store           : relaxed, release, seq_cst
 *   exchange        : relaxed, acquire, release, acq_rel, seq_cst
 *   fetch_add/sub/or/and/xor : same five orders
 *   compare_exchange_strong / _weak : same five orders, success and failure
 *   (a `load` of a negative value per signed type, to catch a stray
 *   zero-extension of the loaded object)
 *
 *   Loads never carry release, stores never carry acquire, and a CAS failure
 *   order is relaxed/acq_rel-free and never stronger than its success order --
 *   the request is rejected by the compiler otherwise, so those cells simply do
 *   not exist (the oracle knows the same cell set; missing/extra lines fail).
 *
 * Oracle (independent, tools/testcases/oracle_atomics.py)
 *   A hand-written C11 value model: for a fresh object initialised to INIT the
 *   operation's return value and the final object value are derived from the
 *   operation alone (add/sub/or/and/xor/mask arithmetic, CAS success vs
 *   failure).  The oracle never runs, links against, or imports the probes.
 *
 * Output (one line per case, stable order-insensitive format)
 *   CASE <tag> <op> <order> ret=<value|na> fin=<value> [exp=<value>]
 *   PTR_A=<addr> PTR_B=<addr>      (the two static objects pointers refer to)
 *   C11_CASES=<number of CASE lines>
 */
#include <stdatomic.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

static int pa, pb;

#define EMIT_S(TAG, OP, ORD, RET, FIN)                                        \
    printf("CASE %s %s %s ret=%lld fin=%lld\n", (TAG), (OP), (ORD),           \
           (long long)(RET), (long long)(FIN))
#define EMIT_U(TAG, OP, ORD, RET, FIN)                                        \
    printf("CASE %s %s %s ret=%llu fin=%llu\n", (TAG), (OP), (ORD),           \
           (unsigned long long)(RET), (unsigned long long)(FIN))
#define EMIT_CAS_S(TAG, OP, ORD, RET, FIN, EXP)                               \
    printf("CASE %s %s %s ret=%d fin=%lld exp=%lld\n", (TAG), (OP), (ORD),    \
           (RET), (long long)(FIN), (long long)(EXP))
#define EMIT_CAS_U(TAG, OP, ORD, RET, FIN, EXP)                               \
    printf("CASE %s %s %s ret=%d fin=%llu exp=%llu\n", (TAG), (OP), (ORD),    \
           (RET), (unsigned long long)(FIN), (unsigned long long)(EXP))
#define EMIT_STORE_S(TAG, ORD, FIN)                                           \
    printf("CASE %s store %s ret=na fin=%lld\n", (TAG), (ORD),                \
           (long long)(FIN))
#define EMIT_STORE_U(TAG, ORD, FIN)                                           \
    printf("CASE %s store %s ret=na fin=%llu\n", (TAG), (ORD),                \
           (unsigned long long)(FIN))

#define SIGNED_LOAD(TAG, T, INIT)                                             \
    do {                                                                      \
        {                                                                     \
            _Atomic T x = (INIT);                                             \
            T r = atomic_load_explicit(&x, memory_order_relaxed);             \
            T f = atomic_load_explicit(&x, memory_order_seq_cst);             \
            EMIT_S(TAG, "load", "relaxed", r, f);                             \
        }                                                                     \
        {                                                                     \
            _Atomic T x = (INIT);                                             \
            T r = atomic_load_explicit(&x, memory_order_acquire);             \
            T f = atomic_load_explicit(&x, memory_order_seq_cst);             \
            EMIT_S(TAG, "load", "acquire", r, f);                             \
        }                                                                     \
        {                                                                     \
            _Atomic T x = (INIT);                                             \
            T r = atomic_load_explicit(&x, memory_order_seq_cst);             \
            EMIT_S(TAG, "load", "seq_cst", r, r);                             \
        }                                                                     \
        {                                                                     \
            _Atomic T x = (T)-1;                                              \
            T r = atomic_load_explicit(&x, memory_order_seq_cst);             \
            EMIT_S(TAG, "load_neg", "seq_cst", r, r);                         \
        }                                                                     \
    } while (0)

#define SIGNED_STORE(TAG, T, INIT)                                            \
    do {                                                                      \
        {                                                                     \
            _Atomic T x = (INIT);                                             \
            atomic_store_explicit(&x, (T)((INIT) + 1),                         \
                                  memory_order_relaxed);                      \
            T f = atomic_load_explicit(&x, memory_order_seq_cst);             \
            EMIT_STORE_S(TAG, "relaxed", f);                            \
        }                                                                     \
        {                                                                     \
            _Atomic T x = (INIT);                                             \
            atomic_store_explicit(&x, (T)((INIT) + 1),                        \
                                  memory_order_release);                      \
            T f = atomic_load_explicit(&x, memory_order_seq_cst);             \
            EMIT_STORE_S(TAG, "release", f);                            \
        }                                                                     \
        {                                                                     \
            _Atomic T x = (INIT);                                             \
            atomic_store_explicit(&x, (T)((INIT) + 1),                        \
                                  memory_order_seq_cst);                      \
            T f = atomic_load_explicit(&x, memory_order_seq_cst);             \
            EMIT_STORE_S(TAG, "seq_cst", f);                            \
        }                                                                     \
    } while (0)

/* One RMW cell: OP is the stdatomic function name, VAL the operand. */
#define SIGNED_RMW1(TAG, T, INIT, OP, ORD, MO, VAL)                           \
    do {                                                                      \
        _Atomic T x = (INIT);                                                 \
        T r = atomic_##OP##_explicit(&x, (T)(VAL), MO);                       \
        T f = atomic_load_explicit(&x, memory_order_seq_cst);                 \
        EMIT_S(TAG, #OP, ORD, r, f);                                          \
    } while (0)

#define SIGNED_CAS_STRONG(TAG, T, INIT, ORD, MO, FO)                          \
    do {                                                                      \
        {                                                                     \
            _Atomic T x = (INIT);                                             \
            T e = (T)(INIT);                                                  \
            int r = atomic_compare_exchange_strong_explicit(                  \
                &x, &e, (T)((INIT) + 1), MO, FO);                             \
            T f = atomic_load_explicit(&x, memory_order_seq_cst);             \
            EMIT_CAS_S(TAG, "compare_exchange_strong_ok", ORD, r, f, e);      \
        }                                                                     \
        {                                                                     \
            _Atomic T x = (INIT);                                             \
            T e = (T)((INIT) + 1);                                            \
            int r = atomic_compare_exchange_strong_explicit(                  \
                &x, &e, (T)((INIT) + 1), MO, FO);                             \
            T f = atomic_load_explicit(&x, memory_order_seq_cst);             \
            EMIT_CAS_S(TAG, "compare_exchange_strong_fail", ORD, r, f, e);    \
        }                                                                     \
    } while (0)

#define SIGNED_CAS_WEAK(TAG, T, INIT, ORD, MO, FO)                            \
    do {                                                                      \
        {                                                                     \
            _Atomic T x = (INIT);                                             \
            T e;                                                              \
            int r;                                                            \
            do {                                                              \
                e = (T)(INIT);                                                \
                r = atomic_compare_exchange_weak_explicit(                    \
                    &x, &e, (T)((INIT) + 1), MO, FO);                         \
            } while (!r);                                                     \
            T f = atomic_load_explicit(&x, memory_order_seq_cst);             \
            EMIT_CAS_S(TAG, "compare_exchange_weak_ok", ORD, r, f, e);        \
        }                                                                     \
        {                                                                     \
            _Atomic T x = (INIT);                                             \
            T e = (T)((INIT) + 1);                                            \
            int r = atomic_compare_exchange_weak_explicit(                    \
                &x, &e, (T)((INIT) + 1), MO, FO);                             \
            T f = atomic_load_explicit(&x, memory_order_seq_cst);             \
            EMIT_CAS_S(TAG, "compare_exchange_weak_fail", ORD, r, f, e);      \
        }                                                                     \
    } while (0)

/* A full signed-type row: every (op, order) cell listed in the file header. */
#define SIGNED_CASES(TAG, T, INIT)                                            \
    do {                                                                      \
        SIGNED_LOAD(TAG, T, INIT);                                            \
        SIGNED_STORE(TAG, T, INIT);                                           \
        SIGNED_RMW1(TAG, T, INIT, exchange, "relaxed", memory_order_relaxed,  \
                    (INIT) + 1);                                              \
        SIGNED_RMW1(TAG, T, INIT, exchange, "acquire", memory_order_acquire,  \
                    (INIT) + 1);                                              \
        SIGNED_RMW1(TAG, T, INIT, exchange, "release", memory_order_release,  \
                    (INIT) + 1);                                              \
        SIGNED_RMW1(TAG, T, INIT, exchange, "acq_rel", memory_order_acq_rel,  \
                    (INIT) + 1);                                              \
        SIGNED_RMW1(TAG, T, INIT, exchange, "seq_cst", memory_order_seq_cst,  \
                    (INIT) + 1);                                              \
        SIGNED_RMW1(TAG, T, INIT, fetch_add, "relaxed", memory_order_relaxed, \
                    1);                                                       \
        SIGNED_RMW1(TAG, T, INIT, fetch_add, "acquire", memory_order_acquire, \
                    1);                                                       \
        SIGNED_RMW1(TAG, T, INIT, fetch_add, "release", memory_order_release, \
                    1);                                                       \
        SIGNED_RMW1(TAG, T, INIT, fetch_add, "acq_rel", memory_order_acq_rel, \
                    1);                                                       \
        SIGNED_RMW1(TAG, T, INIT, fetch_add, "seq_cst", memory_order_seq_cst, \
                    1);                                                       \
        SIGNED_RMW1(TAG, T, INIT, fetch_sub, "relaxed", memory_order_relaxed, \
                    2);                                                       \
        SIGNED_RMW1(TAG, T, INIT, fetch_sub, "acquire", memory_order_acquire, \
                    2);                                                       \
        SIGNED_RMW1(TAG, T, INIT, fetch_sub, "release", memory_order_release, \
                    2);                                                       \
        SIGNED_RMW1(TAG, T, INIT, fetch_sub, "acq_rel", memory_order_acq_rel, \
                    2);                                                       \
        SIGNED_RMW1(TAG, T, INIT, fetch_sub, "seq_cst", memory_order_seq_cst, \
                    2);                                                       \
        SIGNED_RMW1(TAG, T, INIT, fetch_or, "relaxed", memory_order_relaxed,  \
                    5);                                                       \
        SIGNED_RMW1(TAG, T, INIT, fetch_or, "acquire", memory_order_acquire,  \
                    5);                                                       \
        SIGNED_RMW1(TAG, T, INIT, fetch_or, "release", memory_order_release,  \
                    5);                                                       \
        SIGNED_RMW1(TAG, T, INIT, fetch_or, "acq_rel", memory_order_acq_rel,  \
                    5);                                                       \
        SIGNED_RMW1(TAG, T, INIT, fetch_or, "seq_cst", memory_order_seq_cst,  \
                    5);                                                       \
        SIGNED_RMW1(TAG, T, INIT, fetch_and, "relaxed", memory_order_relaxed, \
                    0x0C);                                                    \
        SIGNED_RMW1(TAG, T, INIT, fetch_and, "acquire", memory_order_acquire, \
                    0x0C);                                                    \
        SIGNED_RMW1(TAG, T, INIT, fetch_and, "release", memory_order_release, \
                    0x0C);                                                    \
        SIGNED_RMW1(TAG, T, INIT, fetch_and, "acq_rel", memory_order_acq_rel, \
                    0x0C);                                                    \
        SIGNED_RMW1(TAG, T, INIT, fetch_and, "seq_cst", memory_order_seq_cst, \
                    0x0C);                                                    \
        SIGNED_RMW1(TAG, T, INIT, fetch_xor, "relaxed", memory_order_relaxed, \
                    0x0F);                                                    \
        SIGNED_RMW1(TAG, T, INIT, fetch_xor, "acquire", memory_order_acquire, \
                    0x0F);                                                    \
        SIGNED_RMW1(TAG, T, INIT, fetch_xor, "release", memory_order_release, \
                    0x0F);                                                    \
        SIGNED_RMW1(TAG, T, INIT, fetch_xor, "acq_rel", memory_order_acq_rel, \
                    0x0F);                                                    \
        SIGNED_RMW1(TAG, T, INIT, fetch_xor, "seq_cst", memory_order_seq_cst, \
                    0x0F);                                                    \
        SIGNED_CAS_STRONG(TAG, T, INIT, "relaxed", memory_order_relaxed,      \
                          memory_order_relaxed);                              \
        SIGNED_CAS_STRONG(TAG, T, INIT, "acquire", memory_order_acquire,      \
                          memory_order_acquire);                              \
        SIGNED_CAS_STRONG(TAG, T, INIT, "release", memory_order_release,      \
                          memory_order_relaxed);                              \
        SIGNED_CAS_STRONG(TAG, T, INIT, "acq_rel", memory_order_acq_rel,      \
                          memory_order_acquire);                              \
        SIGNED_CAS_STRONG(TAG, T, INIT, "seq_cst", memory_order_seq_cst,      \
                          memory_order_acquire);                              \
        SIGNED_CAS_WEAK(TAG, T, INIT, "relaxed", memory_order_relaxed,        \
                        memory_order_relaxed);                                \
        SIGNED_CAS_WEAK(TAG, T, INIT, "acquire", memory_order_acquire,        \
                        memory_order_acquire);                                \
        SIGNED_CAS_WEAK(TAG, T, INIT, "release", memory_order_release,        \
                        memory_order_relaxed);                                \
        SIGNED_CAS_WEAK(TAG, T, INIT, "acq_rel", memory_order_acq_rel,        \
                        memory_order_acquire);                                \
        SIGNED_CAS_WEAK(TAG, T, INIT, "seq_cst", memory_order_seq_cst,        \
                        memory_order_acquire);                                \
    } while (0)

#define UNSIGNED_LOAD(TAG, T, INIT)                                           \
    do {                                                                      \
        {                                                                     \
            _Atomic T x = (INIT);                                             \
            T r = atomic_load_explicit(&x, memory_order_relaxed);             \
            T f = atomic_load_explicit(&x, memory_order_seq_cst);             \
            EMIT_U(TAG, "load", "relaxed", r, f);                             \
        }                                                                     \
        {                                                                     \
            _Atomic T x = (INIT);                                             \
            T r = atomic_load_explicit(&x, memory_order_acquire);             \
            T f = atomic_load_explicit(&x, memory_order_seq_cst);             \
            EMIT_U(TAG, "load", "acquire", r, f);                             \
        }                                                                     \
        {                                                                     \
            _Atomic T x = (INIT);                                             \
            T r = atomic_load_explicit(&x, memory_order_seq_cst);             \
            EMIT_U(TAG, "load", "seq_cst", r, r);                             \
        }                                                                     \
    } while (0)

#define UNSIGNED_STORE(TAG, T, INIT)                                          \
    do {                                                                      \
        {                                                                     \
            _Atomic T x = (INIT);                                             \
            atomic_store_explicit(&x, (T)((INIT) + 1),                        \
                                  memory_order_relaxed);                      \
            T f = atomic_load_explicit(&x, memory_order_seq_cst);             \
            EMIT_STORE_U(TAG, "relaxed", f);                            \
        }                                                                     \
        {                                                                     \
            _Atomic T x = (INIT);                                             \
            atomic_store_explicit(&x, (T)((INIT) + 1),                        \
                                  memory_order_release);                      \
            T f = atomic_load_explicit(&x, memory_order_seq_cst);             \
            EMIT_STORE_U(TAG, "release", f);                            \
        }                                                                     \
        {                                                                     \
            _Atomic T x = (INIT);                                             \
            atomic_store_explicit(&x, (T)((INIT) + 1),                        \
                                  memory_order_seq_cst);                      \
            T f = atomic_load_explicit(&x, memory_order_seq_cst);             \
            EMIT_STORE_U(TAG, "seq_cst", f);                            \
        }                                                                     \
    } while (0)

#define UNSIGNED_RMW1(TAG, T, INIT, OP, ORD, MO, VAL)                         \
    do {                                                                      \
        _Atomic T x = (INIT);                                                 \
        T r = atomic_##OP##_explicit(&x, (T)(VAL), MO);                       \
        T f = atomic_load_explicit(&x, memory_order_seq_cst);                 \
        EMIT_U(TAG, #OP, ORD, r, f);                                          \
    } while (0)

#define UNSIGNED_CAS_STRONG(TAG, T, INIT, ORD, MO, FO)                        \
    do {                                                                      \
        {                                                                     \
            _Atomic T x = (INIT);                                             \
            T e = (T)(INIT);                                                  \
            int r = atomic_compare_exchange_strong_explicit(                  \
                &x, &e, (T)((INIT) + 1), MO, FO);                             \
            T f = atomic_load_explicit(&x, memory_order_seq_cst);             \
            EMIT_CAS_U(TAG, "compare_exchange_strong_ok", ORD, r, f, e);      \
        }                                                                     \
        {                                                                     \
            _Atomic T x = (INIT);                                             \
            T e = (T)((INIT) + 1);                                            \
            int r = atomic_compare_exchange_strong_explicit(                  \
                &x, &e, (T)((INIT) + 1), MO, FO);                             \
            T f = atomic_load_explicit(&x, memory_order_seq_cst);             \
            EMIT_CAS_U(TAG, "compare_exchange_strong_fail", ORD, r, f, e);    \
        }                                                                     \
    } while (0)

#define UNSIGNED_CAS_WEAK(TAG, T, INIT, ORD, MO, FO)                          \
    do {                                                                      \
        {                                                                     \
            _Atomic T x = (INIT);                                             \
            T e;                                                              \
            int r;                                                            \
            do {                                                              \
                e = (T)(INIT);                                                \
                r = atomic_compare_exchange_weak_explicit(                    \
                    &x, &e, (T)((INIT) + 1), MO, FO);                         \
            } while (!r);                                                     \
            T f = atomic_load_explicit(&x, memory_order_seq_cst);             \
            EMIT_CAS_U(TAG, "compare_exchange_weak_ok", ORD, r, f, e);        \
        }                                                                     \
        {                                                                     \
            _Atomic T x = (INIT);                                             \
            T e = (T)((INIT) + 1);                                            \
            int r = atomic_compare_exchange_weak_explicit(                    \
                &x, &e, (T)((INIT) + 1), MO, FO);                             \
            T f = atomic_load_explicit(&x, memory_order_seq_cst);             \
            EMIT_CAS_U(TAG, "compare_exchange_weak_fail", ORD, r, f, e);      \
        }                                                                     \
    } while (0)

#define UNSIGNED_CASES(TAG, T, INIT)                                          \
    do {                                                                      \
        UNSIGNED_LOAD(TAG, T, INIT);                                          \
        UNSIGNED_STORE(TAG, T, INIT);                                         \
        UNSIGNED_RMW1(TAG, T, INIT, exchange, "relaxed",                      \
                      memory_order_relaxed, (INIT) + 1);                      \
        UNSIGNED_RMW1(TAG, T, INIT, exchange, "acquire",                      \
                      memory_order_acquire, (INIT) + 1);                      \
        UNSIGNED_RMW1(TAG, T, INIT, exchange, "release",                      \
                      memory_order_release, (INIT) + 1);                      \
        UNSIGNED_RMW1(TAG, T, INIT, exchange, "acq_rel",                      \
                      memory_order_acq_rel, (INIT) + 1);                      \
        UNSIGNED_RMW1(TAG, T, INIT, exchange, "seq_cst",                      \
                      memory_order_seq_cst, (INIT) + 1);                      \
        UNSIGNED_RMW1(TAG, T, INIT, fetch_add, "relaxed",                     \
                      memory_order_relaxed, 1);                               \
        UNSIGNED_RMW1(TAG, T, INIT, fetch_add, "acquire",                     \
                      memory_order_acquire, 1);                               \
        UNSIGNED_RMW1(TAG, T, INIT, fetch_add, "release",                     \
                      memory_order_release, 1);                               \
        UNSIGNED_RMW1(TAG, T, INIT, fetch_add, "acq_rel",                     \
                      memory_order_acq_rel, 1);                               \
        UNSIGNED_RMW1(TAG, T, INIT, fetch_add, "seq_cst",                     \
                      memory_order_seq_cst, 1);                               \
        UNSIGNED_RMW1(TAG, T, INIT, fetch_sub, "relaxed",                     \
                      memory_order_relaxed, 2);                               \
        UNSIGNED_RMW1(TAG, T, INIT, fetch_sub, "acquire",                     \
                      memory_order_acquire, 2);                               \
        UNSIGNED_RMW1(TAG, T, INIT, fetch_sub, "release",                     \
                      memory_order_release, 2);                               \
        UNSIGNED_RMW1(TAG, T, INIT, fetch_sub, "acq_rel",                     \
                      memory_order_acq_rel, 2);                               \
        UNSIGNED_RMW1(TAG, T, INIT, fetch_sub, "seq_cst",                     \
                      memory_order_seq_cst, 2);                               \
        UNSIGNED_RMW1(TAG, T, INIT, fetch_or, "relaxed",                      \
                      memory_order_relaxed, 5);                               \
        UNSIGNED_RMW1(TAG, T, INIT, fetch_or, "acquire",                      \
                      memory_order_acquire, 5);                               \
        UNSIGNED_RMW1(TAG, T, INIT, fetch_or, "release",                      \
                      memory_order_release, 5);                               \
        UNSIGNED_RMW1(TAG, T, INIT, fetch_or, "acq_rel",                      \
                      memory_order_acq_rel, 5);                               \
        UNSIGNED_RMW1(TAG, T, INIT, fetch_or, "seq_cst",                      \
                      memory_order_seq_cst, 5);                               \
        UNSIGNED_RMW1(TAG, T, INIT, fetch_and, "relaxed",                     \
                      memory_order_relaxed, 0x0C);                            \
        UNSIGNED_RMW1(TAG, T, INIT, fetch_and, "acquire",                     \
                      memory_order_acquire, 0x0C);                            \
        UNSIGNED_RMW1(TAG, T, INIT, fetch_and, "release",                     \
                      memory_order_release, 0x0C);                            \
        UNSIGNED_RMW1(TAG, T, INIT, fetch_and, "acq_rel",                     \
                      memory_order_acq_rel, 0x0C);                            \
        UNSIGNED_RMW1(TAG, T, INIT, fetch_and, "seq_cst",                     \
                      memory_order_seq_cst, 0x0C);                            \
        UNSIGNED_RMW1(TAG, T, INIT, fetch_xor, "relaxed",                     \
                      memory_order_relaxed, 0x0F);                            \
        UNSIGNED_RMW1(TAG, T, INIT, fetch_xor, "acquire",                     \
                      memory_order_acquire, 0x0F);                            \
        UNSIGNED_RMW1(TAG, T, INIT, fetch_xor, "release",                     \
                      memory_order_release, 0x0F);                            \
        UNSIGNED_RMW1(TAG, T, INIT, fetch_xor, "acq_rel",                     \
                      memory_order_acq_rel, 0x0F);                            \
        UNSIGNED_RMW1(TAG, T, INIT, fetch_xor, "seq_cst",                     \
                      memory_order_seq_cst, 0x0F);                            \
        UNSIGNED_CAS_STRONG(TAG, T, INIT, "relaxed", memory_order_relaxed,    \
                            memory_order_relaxed);                            \
        UNSIGNED_CAS_STRONG(TAG, T, INIT, "acquire", memory_order_acquire,    \
                            memory_order_acquire);                            \
        UNSIGNED_CAS_STRONG(TAG, T, INIT, "release", memory_order_release,    \
                            memory_order_relaxed);                            \
        UNSIGNED_CAS_STRONG(TAG, T, INIT, "acq_rel", memory_order_acq_rel,    \
                            memory_order_acquire);                            \
        UNSIGNED_CAS_STRONG(TAG, T, INIT, "seq_cst", memory_order_seq_cst,    \
                            memory_order_acquire);                            \
        UNSIGNED_CAS_WEAK(TAG, T, INIT, "relaxed", memory_order_relaxed,      \
                          memory_order_relaxed);                              \
        UNSIGNED_CAS_WEAK(TAG, T, INIT, "acquire", memory_order_acquire,      \
                          memory_order_acquire);                              \
        UNSIGNED_CAS_WEAK(TAG, T, INIT, "release", memory_order_release,      \
                          memory_order_relaxed);                              \
        UNSIGNED_CAS_WEAK(TAG, T, INIT, "acq_rel", memory_order_acq_rel,      \
                          memory_order_acquire);                              \
        UNSIGNED_CAS_WEAK(TAG, T, INIT, "seq_cst", memory_order_seq_cst,      \
                          memory_order_acquire);                              \
    } while (0)

#define PTR_EMIT(OP, ORD, RET, FIN)                                           \
    printf("CASE pointer %s %s ret=%llx fin=%llx\n", (OP), (ORD),             \
           (unsigned long long)(uintptr_t)(RET),                              \
           (unsigned long long)(uintptr_t)(FIN))
#define PTR_CAS_EMIT(OP, ORD, RET, FIN, EXP)                                  \
    printf("CASE pointer %s %s ret=%d fin=%llx exp=%llx\n", (OP), (ORD),      \
           (RET), (unsigned long long)(uintptr_t)(FIN),                       \
           (unsigned long long)(uintptr_t)(EXP))

#define PTR_LOAD(ORD, MO)                                                     \
    do {                                                                      \
        _Atomic(void *) x;                                                    \
        void *r, *f;                                                          \
        atomic_init(&x, (void *)&pa);                                         \
        r = atomic_load_explicit(&x, MO);                                     \
        f = atomic_load_explicit(&x, memory_order_seq_cst);                   \
        PTR_EMIT("load", ORD, r, f);                                          \
    } while (0)

#define PTR_STORE(ORD, MO)                                                    \
    do {                                                                      \
        _Atomic(void *) x;                                                    \
        void *f;                                                              \
        atomic_init(&x, (void *)&pa);                                         \
        atomic_store_explicit(&x, (void *)&pb, MO);                           \
        f = atomic_load_explicit(&x, memory_order_seq_cst);                   \
        printf("CASE pointer store %s ret=na fin=%llx\n", (ORD),              \
               (unsigned long long)(uintptr_t)(f));                           \
    } while (0)

/* exchange + the four CAS variants, all with one (success, failure) order. */
#define PTR_RMW(ORD, MO, FO)                                                  \
    do {                                                                      \
        {                                                                     \
            _Atomic(void *) x;                                                \
            void *r, *f;                                                      \
            atomic_init(&x, (void *)&pa);                                     \
            r = atomic_exchange_explicit(&x, (void *)&pb, MO);                \
            f = atomic_load_explicit(&x, memory_order_seq_cst);               \
            PTR_EMIT("exchange", ORD, r, f);                                  \
        }                                                                     \
        {                                                                     \
            _Atomic(void *) x;                                                \
            void *e = (void *)&pa;                                            \
            void *f;                                                          \
            int r;                                                            \
            atomic_init(&x, (void *)&pa);                                     \
            r = atomic_compare_exchange_strong_explicit(&x, &e, (void *)&pb,  \
                                                        MO, FO);              \
            f = atomic_load_explicit(&x, memory_order_seq_cst);               \
            PTR_CAS_EMIT("compare_exchange_strong_ok", ORD, r, f, e);         \
        }                                                                     \
        {                                                                     \
            _Atomic(void *) x;                                                \
            void *e = (void *)&pb;                                            \
            void *f;                                                          \
            int r;                                                            \
            atomic_init(&x, (void *)&pa);                                     \
            r = atomic_compare_exchange_strong_explicit(&x, &e, (void *)&pb,  \
                                                        MO, FO);              \
            f = atomic_load_explicit(&x, memory_order_seq_cst);               \
            PTR_CAS_EMIT("compare_exchange_strong_fail", ORD, r, f, e);       \
        }                                                                     \
        {                                                                     \
            _Atomic(void *) x;                                                \
            void *e;                                                          \
            void *f;                                                          \
            int r;                                                            \
            atomic_init(&x, (void *)&pa);                                     \
            do {                                                              \
                e = (void *)&pa;                                              \
                r = atomic_compare_exchange_weak_explicit(&x, &e, (void *)&pb,\
                                                          MO, FO);            \
            } while (!r);                                                     \
            f = atomic_load_explicit(&x, memory_order_seq_cst);               \
            PTR_CAS_EMIT("compare_exchange_weak_ok", ORD, r, f, e);           \
        }                                                                     \
        {                                                                     \
            _Atomic(void *) x;                                                \
            void *e = (void *)&pb;                                            \
            void *f;                                                          \
            int r;                                                            \
            atomic_init(&x, (void *)&pa);                                     \
            r = atomic_compare_exchange_weak_explicit(&x, &e, (void *)&pb,    \
                                                      MO, FO);                \
            f = atomic_load_explicit(&x, memory_order_seq_cst);               \
            PTR_CAS_EMIT("compare_exchange_weak_fail", ORD, r, f, e);         \
        }                                                                     \
    } while (0)

/* ---- shared objects (the real cross-thread path) ---------------------------
 * The per-type matrix above uses automatic objects, which the optimiser may
 * promote/thread through registers; the cells below touch file-scope objects
 * from a noinline function so the C11 store/RMW really is compiled as an
 * atomic access to memory other threads can see.  See the file header for the
 * two measured backend defects these cells expose.
 */
static _Atomic char sg_char;
static _Atomic short sg_short;
static _Atomic int sg_int;
static _Atomic long sg_long;
static _Atomic unsigned sg_unsigned;
static _Atomic size_t sg_size_t;
static _Atomic(void *) sg_ptr;
static _Atomic int sg_rmw = 100; /* non-atomic static init; RMW controls */

__attribute__((noinline)) static void shared_store_char(char v)
{
    atomic_store_explicit(&sg_char, v, memory_order_release);
}
__attribute__((noinline)) static void shared_store_short(short v)
{
    atomic_store_explicit(&sg_short, v, memory_order_release);
}
__attribute__((noinline)) static void shared_store_int(int v)
{
    atomic_store_explicit(&sg_int, v, memory_order_release);
}
__attribute__((noinline)) static void shared_store_long(long v)
{
    atomic_store_explicit(&sg_long, v, memory_order_release);
}
__attribute__((noinline)) static void shared_store_unsigned(unsigned v)
{
    atomic_store_explicit(&sg_unsigned, v, memory_order_release);
}
__attribute__((noinline)) static void shared_store_size_t(size_t v)
{
    atomic_store_explicit(&sg_size_t, v, memory_order_release);
}
__attribute__((noinline)) static void shared_store_ptr(void *v)
{
    atomic_store_explicit(&sg_ptr, v, memory_order_release);
}
__attribute__((noinline)) static int shared_exchange_int(int v)
{
    return atomic_exchange_explicit(&sg_rmw, v, memory_order_seq_cst);
}
__attribute__((noinline)) static int shared_fetch_add_int(int v)
{
    return atomic_fetch_add_explicit(&sg_rmw, v, memory_order_seq_cst);
}
__attribute__((noinline)) static int shared_cas_int(int expected, int v)
{
    int e = expected;
    return atomic_compare_exchange_strong_explicit(
        &sg_rmw, &e, v, memory_order_seq_cst, memory_order_acquire);
}

int main(void)
{
    SIGNED_CASES("char", char, 10);
    SIGNED_CASES("short", short, 1000);
    SIGNED_CASES("int", int, 100000);
    SIGNED_CASES("long", long, 10000000000L);
    UNSIGNED_CASES("unsigned", unsigned, 2000000000u);
    UNSIGNED_CASES("size_t", size_t, (size_t)3000000000u);

    /* ---- shared-object cells -------------------------------------------------
     * store_shared : the semantics are `fin == the stored value`; the measured
     *                backend defect stores the *address* instead (oracle marks
     *                these XFAIL with defect `atomic-store-address`).
     * exchange/fetch_add/cas on sg_rmw : the RMW path (lr/sc loop) is correct,
     *                these are required-to-pass controls on a shared object.
     */
    shared_store_char(42);
    printf("SCASE char store_shared release addr=%llx ret=na fin=%lld\n",
           (unsigned long long)(uintptr_t)&sg_char,
           (long long)atomic_load_explicit(&sg_char, memory_order_seq_cst));
    shared_store_short(4321);
    printf("SCASE short store_shared release addr=%llx ret=na fin=%lld\n",
           (unsigned long long)(uintptr_t)&sg_short,
           (long long)atomic_load_explicit(&sg_short, memory_order_seq_cst));
    shared_store_int(424242);
    printf("SCASE int store_shared release addr=%llx ret=na fin=%lld\n",
           (unsigned long long)(uintptr_t)&sg_int,
           (long long)atomic_load_explicit(&sg_int, memory_order_seq_cst));
    shared_store_long(4242424242L);
    printf("SCASE long store_shared release addr=%llx ret=na fin=%lld\n",
           (unsigned long long)(uintptr_t)&sg_long,
           (long long)atomic_load_explicit(&sg_long, memory_order_seq_cst));
    shared_store_unsigned(2100000000u);
    printf("SCASE unsigned store_shared release addr=%llx ret=na fin=%llu\n",
           (unsigned long long)(uintptr_t)&sg_unsigned,
           (unsigned long long)atomic_load_explicit(&sg_unsigned,
                                                    memory_order_seq_cst));
    shared_store_size_t((size_t)3100000000u);
    printf("SCASE size_t store_shared release addr=%llx ret=na fin=%llu\n",
           (unsigned long long)(uintptr_t)&sg_size_t,
           (unsigned long long)atomic_load_explicit(&sg_size_t,
                                                    memory_order_seq_cst));
    shared_store_ptr((void *)&pb);
    printf("SCASE pointer store_shared release addr=%llx ret=na fin=%llx\n",
           (unsigned long long)(uintptr_t)&sg_ptr,
           (unsigned long long)(uintptr_t)atomic_load_explicit(
               &sg_ptr, memory_order_seq_cst));
    printf("SCASE int exchange_shared seq_cst addr=0 ret=%lld fin=%lld\n",
           (long long)shared_exchange_int(777),
           (long long)atomic_load_explicit(&sg_rmw, memory_order_seq_cst));
    printf("SCASE int fetch_add_shared seq_cst addr=0 ret=%lld fin=%lld\n",
           (long long)shared_fetch_add_int(5),
           (long long)atomic_load_explicit(&sg_rmw, memory_order_seq_cst));
    printf("SCASE int cas_shared seq_cst addr=0 ret=%d fin=%lld\n",
           shared_cas_int(782, 900),
           (long long)atomic_load_explicit(&sg_rmw, memory_order_seq_cst));

    /* ---- narrow-CAS edge values -------------------------------------------------
     * `lr.{b,w,t}` zero-extends the loaded value (DADAOInstrInfo.td), while the
     * compared value is an i64 promoted from i8/i16/i32: for a value whose
     * bit (width*8-1) is set the promotion is a *sign* extension, so the two
     * 64-bit operands of the `br.ne` differ even when the 32-bit values are
     * equal.  Kept as explicit cases, marked XFAIL by the oracle (see
     * oracle_atomics.KNOWN_DEFECT_CASES) so the signature is measured rather
     * than assumed; the 8-byte `long` case is the control that must pass.
     */
    {   _Atomic int x = -1; int e = -1; int r =
            atomic_compare_exchange_strong_explicit(&x, &e, 0,
                memory_order_seq_cst, memory_order_acquire);
        int f = atomic_load_explicit(&x, memory_order_seq_cst);
        EMIT_CAS_S("int", "compare_exchange_edge_ok", "seq_cst", r, f, e); }
    {   _Atomic char x = -1; char e = -1; int r =
            atomic_compare_exchange_strong_explicit(&x, &e, 0,
                memory_order_seq_cst, memory_order_acquire);
        char f = atomic_load_explicit(&x, memory_order_seq_cst);
        EMIT_CAS_S("char", "compare_exchange_edge_ok", "seq_cst", r, f, e); }
    {   _Atomic short x = -1000; short e = -1000; int r =
            atomic_compare_exchange_strong_explicit(&x, &e, 0,
                memory_order_seq_cst, memory_order_acquire);
        short f = atomic_load_explicit(&x, memory_order_seq_cst);
        EMIT_CAS_S("short", "compare_exchange_edge_ok", "seq_cst", r, f, e); }
    {   _Atomic long x = -1; long e = -1; int r =
            atomic_compare_exchange_strong_explicit(&x, &e, 0,
                memory_order_seq_cst, memory_order_acquire);
        long f = atomic_load_explicit(&x, memory_order_seq_cst);
        EMIT_CAS_S("long", "compare_exchange_edge_control", "seq_cst", r, f, e); }
    {   _Atomic unsigned x = 0x80000000u; unsigned e = 0x80000000u; int r =
            atomic_compare_exchange_strong_explicit(&x, &e, 0,
                memory_order_seq_cst, memory_order_acquire);
        unsigned f = atomic_load_explicit(&x, memory_order_seq_cst);
        EMIT_CAS_U("unsigned", "compare_exchange_edge_ok", "seq_cst", r, f, e); }
    {   _Atomic unsigned char x = 200; unsigned char e = 200; int r =
            atomic_compare_exchange_strong_explicit(&x, &e, 0,
                memory_order_seq_cst, memory_order_acquire);
        unsigned char f = atomic_load_explicit(&x, memory_order_seq_cst);
        EMIT_CAS_U("uchar", "compare_exchange_edge_ok", "seq_cst",
                   r, f, e); }
    {   _Atomic unsigned short x = 40000; unsigned short e = 40000; int r =
            atomic_compare_exchange_strong_explicit(&x, &e, 0,
                memory_order_seq_cst, memory_order_acquire);
        unsigned short f = atomic_load_explicit(&x, memory_order_seq_cst);
        EMIT_CAS_U("ushort", "compare_exchange_edge_ok", "seq_cst",
                   r, f, e); }

    printf("PTR_A=%llx\n", (unsigned long long)(uintptr_t)&pa);
    printf("PTR_B=%llx\n", (unsigned long long)(uintptr_t)&pb);
    PTR_LOAD("relaxed", memory_order_relaxed);
    PTR_LOAD("acquire", memory_order_acquire);
    PTR_LOAD("seq_cst", memory_order_seq_cst);
    PTR_STORE("relaxed", memory_order_relaxed);
    PTR_STORE("release", memory_order_release);
    PTR_STORE("seq_cst", memory_order_seq_cst);
    PTR_RMW("relaxed", memory_order_relaxed, memory_order_relaxed);
    PTR_RMW("acquire", memory_order_acquire, memory_order_acquire);
    PTR_RMW("release", memory_order_release, memory_order_relaxed);
    PTR_RMW("acq_rel", memory_order_acq_rel, memory_order_acquire);
    PTR_RMW("seq_cst", memory_order_seq_cst, memory_order_acquire);
    return 0;
}
