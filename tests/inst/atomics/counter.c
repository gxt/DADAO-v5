/*
 * counter.c -- contended mutex counter (TESTCASES-056t, family A).
 *
 * Purpose
 *   The smallest end-to-end shadow of ISS-294: N threads each take a
 *   PTHREAD_MUTEX_INITIALIZER mutex and increment one shared `long`, M times
 *   per thread.  A mutex that is not mutually exclusive (musl `a_cas` was
 *   load/compare/store before INFRA-100t) loses updates, and a lock that never
 *   releases (or a spin that never converges) hangs until the caller's timeout.
 *
 * Parameters (never compiled in)
 *   argv[1] = N (threads), argv[2] = M (iterations per thread).  Defaults
 *   (4, 250000) are only the documented reproduction size of ISS-294; the
 *   driver always passes both explicitly and derives the expectation from the
 *   same numbers, so a smaller size cannot silently pass under a constant.
 *
 * Oracle (independent, in tools/testcases/oracle_atomics.py)
 *   COUNT must be exactly N*M, and the second, independent bookkeeping --
 *   each thread's own private slot, incremented outside the critical section
 *   and summed by the parent -- must also be exactly N*M.  Neither number is
 *   produced by the C code as an expectation: the probe prints raw
 *   observations only.
 *
 * Output (one key per line, parsed by the driver)
 *   COUNTER_THREADS=<N>
 *   COUNTER_ITERS=<M>
 *   COUNTER_COUNT=<shared counter after all joins>
 *   COUNTER_SUM=<sum of the per-thread private slots>
 *   COUNTER_RC=<0 if every thread was created and joined, else a bitmask>
 */
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>

#define MAX_THREADS 64

static long shared_count;
static pthread_mutex_t mu = PTHREAD_MUTEX_INITIALIZER;
static long own[MAX_THREADS];

struct worker_arg {
    int idx;
    long iters;
};

static void *worker(void *p)
{
    struct worker_arg *a = p;
    long i, n = 0;

    for (i = 0; i < a->iters; i++) {
        pthread_mutex_lock(&mu);
        shared_count++;
        pthread_mutex_unlock(&mu);
        n++;
    }
    own[a->idx] = n;
    return 0;
}

int main(int argc, char **argv)
{
    int nthreads, i, rc = 0;
    long iters, sum = 0;
    pthread_t tid[MAX_THREADS];
    struct worker_arg arg[MAX_THREADS];
    int created[MAX_THREADS];

    nthreads = (argc > 1) ? atoi(argv[1]) : 4;
    iters = (argc > 2) ? atol(argv[2]) : 250000;
    if (nthreads < 1 || nthreads > MAX_THREADS || iters < 0) {
        fprintf(stderr, "usage: %s [N<=%d] [M>=0]\n", argv[0], MAX_THREADS);
        return 2;
    }

    for (i = 0; i < nthreads; i++) {
        arg[i].idx = i;
        arg[i].iters = iters;
        created[i] = (pthread_create(&tid[i], 0, worker, &arg[i]) == 0);
        if (!created[i])
            rc |= 1 << i;
    }
    for (i = 0; i < nthreads; i++)
        if (created[i] && pthread_join(tid[i], 0) != 0)
            rc |= 1 << i;

    for (i = 0; i < nthreads; i++)
        sum += own[i];

    printf("COUNTER_THREADS=%d\n", nthreads);
    printf("COUNTER_ITERS=%ld\n", iters);
    printf("COUNTER_COUNT=%ld\n", shared_count);
    printf("COUNTER_SUM=%ld\n", sum);
    printf("COUNTER_RC=%d\n", rc);
    return 0;
}
