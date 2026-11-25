/* futex_probe.c -- gem5 SE futex details probe (ISS-345 / m20-gem5-002).
 *
 * The same C source runs on three engines and must print the same assertion
 * lines: the host kernel (the oracle: this really is Linux), gem5 SE, and
 * qemu-user.  The assertions pin the three details fixed by m20-gem5-002:
 *
 *   - FUTEX_UNLOCK_PI from a non-owner is -EPERM and leaves the word alone
 *     (kernel/futex/pi.c: __futex_unlock_pi);
 *   - FUTEX_REQUEUE / FUTEX_CMP_REQUEUE return the number of waiters woken
 *     plus the number requeued, and reject a negative nr_wake/nr_requeue with
 *     -EINVAL without touching any waiter (kernel/futex/requeue.c);
 *   - the timeout / invalid-timespec wait paths still return -ETIMEDOUT and
 *     -EINVAL (the branches where the simulator used to leak a waiter).
 *
 * The waiter leak itself is a host-side allocation and cannot be observed from
 * the guest; the driver measures the simulator's peak RSS over `leak` loops to
 * cover it (see check_se_futex.py).
 *
 * Modes (argv[1]):
 *   (none) | check   run every assertion, print PASS/FAIL per line + SUMMARY
 *   leak N           N invalid/expired waits (no thread parks)
 *   wake N           N FUTEX_WAKE calls (same syscall volume, no waiter)
 */
/* The driver passes -D_GNU_SOURCE for the host/guest compilers. */
#include <errno.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>

/* asm-generic linux/futex.h values; musl does not ship linux/ headers. */
#define FUTEX_WAIT 0
#define FUTEX_WAKE 1
#define FUTEX_REQUEUE 3
#define FUTEX_CMP_REQUEUE 4
#define FUTEX_UNLOCK_PI 7
#define FUTEX_WAIT_BITSET 9
#define FUTEX_PRIVATE_FLAG 128
#define FUTEX_BITSET_MATCH_ANY 0xffffffffu

/* A waiter that is never woken must not hang the probe: it times out, reports
 * a failure through the woken counter, and the process still exits. */
#define WAIT_TIMEOUT_MS 5000

static int failures;
static int checks;

static void
check(const char *name, int ok, long want, long got)
{
    checks++;
    if (ok) {
        printf("PASS %s want=%ld got=%ld\n", name, want, got);
    } else {
        printf("FAIL %s want=%ld got=%ld\n", name, want, got);
        failures++;
    }
}

/* futex(2) has one prototype: (uaddr, op, val, val2/timeout, uaddr2, val3).
 *
 * The 4th slot is a timespec pointer for WAIT and a plain count for REQUEUE,
 * but either way the DADAO argument mask marks that position as an *address*
 * (futex = 0x19): musl's public syscall() reads each variadic argument with
 * the type the mask dictates, and the DADAO ABI passes pointers and integers
 * in different register banks.  Passing the count slot as a `long` would make
 * the two sides disagree, so it is always handed over as a pointer-sized
 * value; only the callee decides whether it is a pointer or a number. */
static long
f_futex(int *uaddr, long op, long val, void *slot4, int *uaddr2, long val3)
{
    return syscall(SYS_futex, (void *)uaddr, op, val, slot4, (void *)uaddr2,
                   val3);
}

static long
f_wait(int *uaddr, int op, int val, const struct timespec *ts, int val3)
{
    return f_futex(uaddr, op, val, (void *)ts, NULL, val3);
}

struct wait_arg
{
    int *word;
    int *arrived;
    int *woke;
};

static void *
waiter(void *arg)
{
    struct wait_arg *a = (struct wait_arg *)arg;
    struct timespec rel;

    __atomic_fetch_add(a->arrived, 1, __ATOMIC_SEQ_CST);
    for (;;) {
        rel.tv_sec = WAIT_TIMEOUT_MS / 1000;
        rel.tv_nsec = (long)(WAIT_TIMEOUT_MS % 1000) * 1000000L;
        long r = f_wait(a->word, FUTEX_WAIT, 0, &rel, 0);
        if (r == 0) {
            __atomic_fetch_add(a->woke, 1, __ATOMIC_SEQ_CST);
            return NULL;
        }
        if (errno == EAGAIN || errno == EINTR)
            continue; /* a changed word or a signal: wait again */
        return NULL;  /* ETIMEDOUT (or an error): not woken */
    }
}

static void
start_waiters(pthread_t *t, struct wait_arg *a, int n, int *word,
              int *arrived, int *woke)
{
    for (int i = 0; i < n; i++) {
        a[i].word = word;
        a[i].arrived = arrived;
        a[i].woke = woke;
        if (pthread_create(&t[i], NULL, waiter, &a[i]) != 0) {
            printf("FAIL waiter.create idx=%d\n", i);
            failures++;
        }
    }
}

/* Wait until every waiter has set its "about to enter futex" flag, then give
 * them time to actually park.  The flag alone has a small window; the sleep is
 * what makes the subsequent wake/requeue counts deterministic on all engines. */
static void
wait_parked(int *arrived, int n)
{
    for (int i = 0; i < 4000; i++) {
        if (__atomic_load_n(arrived, __ATOMIC_SEQ_CST) >= n)
            break;
        usleep(1000);
    }
    usleep(100000);
}

static void
join_waiters(pthread_t *t, int n)
{
    for (int i = 0; i < n; i++)
        pthread_join(t[i], NULL);
}

static void
test_unlock_pi_nonowner(void)
{
    int word = 0x3ffffff0; /* FUTEX_TID_MASK value that cannot be our tid */

    long r = f_futex(&word, FUTEX_UNLOCK_PI, 0, 0, NULL, 0);
    check("unlock_pi.nonowner-rc", r == -1 && errno == EPERM, -EPERM,
          r == -1 ? -errno : r);
    check("unlock_pi.nonowner-word", word == 0x3ffffff0, 0x3ffffff0, word);

    /* The owner path keeps working: the word carries our own tid. */
    long tid = syscall(SYS_gettid);
    int owned = (int)tid;
    r = f_futex(&owned, FUTEX_UNLOCK_PI, 0, 0, NULL, 0);
    check("unlock_pi.owner-rc", r == 0, 0, r);
    check("unlock_pi.owner-word", owned == 0, 0, owned);
}

static void
test_requeue_sum(void)
{
    int a = 0, b = 0, arrived = 0, woke = 0;
    pthread_t t[3];
    struct wait_arg w[3];

    start_waiters(t, w, 3, &a, &arrived, &woke);
    wait_parked(&arrived, 3);

    long r = f_futex(&a, FUTEX_REQUEUE, 1, (void *)(uintptr_t)1, &b, 0);
    check("requeue.sum-rc", r == 2, 2, r);

    long wa = f_futex(&a, FUTEX_WAKE, 1, 0, NULL, 0);
    long wb = f_futex(&b, FUTEX_WAKE, 1, 0, NULL, 0);
    check("requeue.sum-wake-a", wa == 1, 1, wa);
    check("requeue.sum-wake-b", wb == 1, 1, wb);

    join_waiters(t, 3);
    check("requeue.sum-woken", woke == 3, 3, woke);
}

static void
test_requeue_negative(void)
{
    int a = 0, b = 0, arrived = 0, woke = 0;
    pthread_t t[2];
    struct wait_arg w[2];

    start_waiters(t, w, 2, &a, &arrived, &woke);
    wait_parked(&arrived, 2);

    /* nr_wake = -1: EINVAL, and the rejected call must not wake anybody. */
    long r = f_futex(&a, FUTEX_REQUEUE, -1, (void *)(uintptr_t)1, &b, 0);
    check("requeue.neg-wake-rc", r == -1 && errno == EINVAL, -EINVAL,
          r == -1 ? -errno : r);
    long wa = f_futex(&a, FUTEX_WAKE, 2, 0, NULL, 0);
    long wb = f_futex(&b, FUTEX_WAKE, 2, 0, NULL, 0);
    check("requeue.neg-wake-still-a", wa == 2, 2, wa);
    check("requeue.neg-wake-none-b", wb == 0, 0, wb);

    join_waiters(t, 2);
    check("requeue.neg-wake-woken", woke == 2, 2, woke);
}

static void
test_requeue_negative_count(void)
{
    int a = 0, b = 0, arrived = 0, woke = 0;
    pthread_t t[1];
    struct wait_arg w[1];

    start_waiters(t, w, 1, &a, &arrived, &woke);
    wait_parked(&arrived, 1);

    /* nr_requeue (the 4th slot) = -1: EINVAL, nobody moved or woken. */
    long r = f_futex(&a, FUTEX_REQUEUE, 1, (void *)(intptr_t)-1, &b, 0);
    check("requeue.neg-count-rc", r == -1 && errno == EINVAL, -EINVAL,
          r == -1 ? -errno : r);
    long wa = f_futex(&a, FUTEX_WAKE, 1, 0, NULL, 0);
    long wb = f_futex(&b, FUTEX_WAKE, 1, 0, NULL, 0);
    check("requeue.neg-count-still-a", wa == 1, 1, wa);
    check("requeue.neg-count-none-b", wb == 0, 0, wb);

    join_waiters(t, 1);
    check("requeue.neg-count-woken", woke == 1, 1, woke);
}

static void
test_cmp_requeue(void)
{
    int a = 0, b = 0, arrived = 0, woke = 0;
    pthread_t t[3];
    struct wait_arg w[3];

    start_waiters(t, w, 2, &a, &arrived, &woke);
    wait_parked(&arrived, 2);

    /* val3 mismatch: -EAGAIN and the waiters stay on the source futex. */
    long r = f_futex(&a, FUTEX_CMP_REQUEUE, 1, (void *)(uintptr_t)1, &b, 1);
    check("cmp_requeue.mismatch-rc", r == -1 && errno == EAGAIN, -EAGAIN,
          r == -1 ? -errno : r);
    long wa = f_futex(&a, FUTEX_WAKE, 2, 0, NULL, 0);
    check("cmp_requeue.mismatch-still-a", wa == 2, 2, wa);

    join_waiters(t, 2);
    check("cmp_requeue.mismatch-woken", woke == 2, 2, woke);

    /* Matching val3 on a fresh group: 1 woken + 1 requeued = 2, one stays. */
    a = b = 0;
    arrived = woke = 0;
    start_waiters(t, w, 3, &a, &arrived, &woke);
    wait_parked(&arrived, 3);

    r = f_futex(&a, FUTEX_CMP_REQUEUE, 1, (void *)(uintptr_t)1, &b, 0);
    check("cmp_requeue.sum-rc", r == 2, 2, r);
    wa = f_futex(&a, FUTEX_WAKE, 1, 0, NULL, 0);
    long wb = f_futex(&b, FUTEX_WAKE, 1, 0, NULL, 0);
    check("cmp_requeue.sum-wake-a", wa == 1, 1, wa);
    check("cmp_requeue.sum-wake-b", wb == 1, 1, wb);

    join_waiters(t, 3);
    check("cmp_requeue.sum-woken", woke == 3, 3, woke);
}

static void
test_wait_timeouts(void)
{
    int a = 0;
    struct timespec rel = {0, 50 * 1000 * 1000}; /* 50 ms, relative */
    long r = f_wait(&a, FUTEX_WAIT, 0, &rel, 0);
    check("wait.relative-timeout-rc", r == -1 && errno == ETIMEDOUT,
          -ETIMEDOUT, r == -1 ? -errno : r);
    check("wait.relative-timeout-word", a == 0, 0, a);

    /* An absolute deadline in the past exercises the "already expired"
     * early-return branch (no waiter may be allocated there). */
    struct timespec past = {0, 1};
    a = 0;
    r = f_wait(&a, FUTEX_WAIT_BITSET, 0, &past, FUTEX_BITSET_MATCH_ANY);
    check("wait.expired-rc", r == -1 && errno == ETIMEDOUT, -ETIMEDOUT,
          r == -1 ? -errno : r);

    /* A malformed relative timeout is EINVAL (the other early return). */
    struct timespec bad = {0, 1000000000L};
    a = 0;
    r = f_wait(&a, FUTEX_WAIT, 0, &bad, 0);
    check("wait.bad-timespec-rc", r == -1 && errno == EINVAL, -EINVAL,
          r == -1 ? -errno : r);
}

/* One invalid-or-expired wait that must return immediately.  Both branches are
 * the ones that used to allocate (and leak) a FutexWaiter. */
static int
leak_iteration(int *word, int i)
{
    struct timespec ts;
    long r;

    if (i & 1) {
        ts.tv_sec = 0;
        ts.tv_nsec = 1; /* absolute CLOCK_MONOTONIC deadline in the past */
        r = f_wait(word, FUTEX_WAIT_BITSET, 0, &ts, FUTEX_BITSET_MATCH_ANY);
        return r == -1 && errno == ETIMEDOUT;
    }
    ts.tv_sec = 0;
    ts.tv_nsec = 1000000000L; /* nsec >= 1e9: EINVAL */
    r = f_wait(word, FUTEX_WAIT, 0, &ts, 0);
    return r == -1 && errno == EINVAL;
}

static int
run_check(void)
{
    test_unlock_pi_nonowner();
    test_requeue_sum();
    test_requeue_negative();
    test_requeue_negative_count();
    test_cmp_requeue();
    test_wait_timeouts();

    printf("SUMMARY checks=%d fails=%d\n", checks, failures);
    return failures == 0 ? 0 : 1;
}

static int
run_leak(long n)
{
    int word = 0;
    int bad = 0;

    for (long i = 0; i < n; i++) {
        if (!leak_iteration(&word, (int)i))
            bad++;
    }
    checks = (int)n;
    failures = bad;
    if (bad != 0)
        printf("FAIL leak.immediate-return bad=%d of %ld\n", bad, n);
    else
        printf("PASS leak.immediate-return n=%ld\n", n);
    printf("SUMMARY checks=%ld fails=%d\n", n, bad);
    return bad == 0 ? 0 : 1;
}

static int
run_wake(long n)
{
    int word = 0;
    long bad = 0;

    for (long i = 0; i < n; i++) {
        if (f_futex(&word, FUTEX_WAKE, 1, 0, NULL, 0) != 0)
            bad++;
    }
    checks = (int)n;
    failures = (int)bad;
    if (bad != 0)
        printf("FAIL wake.empty bad=%ld of %ld\n", bad, n);
    else
        printf("PASS wake.empty n=%ld\n", n);
    printf("SUMMARY checks=%ld fails=%ld\n", n, bad);
    return bad == 0 ? 0 : 1;
}

int
main(int argc, char **argv)
{
    setvbuf(stdout, NULL, _IONBF, 0);

    if (argc >= 3 && strcmp(argv[1], "leak") == 0)
        return run_leak(strtol(argv[2], NULL, 0));
    if (argc >= 3 && strcmp(argv[1], "wake") == 0)
        return run_wake(strtol(argv[2], NULL, 0));
    return run_check();
}
