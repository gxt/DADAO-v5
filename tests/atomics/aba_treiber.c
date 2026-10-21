/*
 * aba_treiber.c -- Treiber stack with version-tagged head (TESTCASES-056t, family D).
 *
 * Purpose
 *   Stress the compare-and-swap contract the atomic port rests on: a CAS that
 *   observes "still the same head" must also observe "still the same
 *   *version*".  The head is one 64-bit word, `{version:16, pointer:48}`, and
 *   every successful push/pop bumps the version, so the classic ABA (A popped,
 *   B pushed, A pushed again -- same pointer, new stack state) changes the
 *   packed word: the CAS fails and the operation retries.
 *
 *   Phase 1: T threads each push K distinct nodes and pop concurrently, so the
 *   stack is contended in both directions; whatever is left is drained.  Each
 *   node is pushed exactly once (a node's `next` is written before it becomes
 *   reachable and never again), which keeps the probe free of any atomic
 *   *store* -- a family this batch measures as defective (DEF-1 below).
 *   Phase 2: the deterministic ABA replay on two drained nodes.
 *
 * Invariants (all hard; the oracle derives them from the parameters)
 *   (1) no duplication / no loss: every node's pop count is exactly 1 and the
 *       total is T*K (the drain included);
 *   (2) the stack is empty after the drain phase;
 *   (3) every popped node is one of ours and its payload (magic, value) is
 *       intact -- no wild pointer and no torn node;
 *   (4) the tagged head detects the deterministic ABA replay
 *       (`ABA_TAGGED=cas_rejected`): a stale packed snapshot must not be
 *       accepted after the head returned to the same pointer with a new
 *       version.  This is what makes "same-value write" detection unnecessary
 *       for the stack invariants.
 *
 * Platform limit (disclosed, never counted as PASS)
 *   qemu's `sc` compares the whole guarded 8-byte *value* (QEMU-067t), so a
 *   concurrent write that restores the same bytes leaves the word unchanged
 *   and no implementation built on it can observe that write.  The probe
 *   prints `ABA_NOTE same_value_write=undetectable ...`; the driver records it
 *   as a note (SKIP), never as a passing check.
 *
 * Parameters: argv[1] = threads T (default 4), argv[2] = pushes per thread K
 *   (default 10000).
 *
 * Oracle (independent, tools/testcases/oracle_atomics.py)
 *   pushes == pops == T*K, every node popped exactly once, node count = T*K,
 *   empty final, no node mismatch, no bad node, tagged ABA rejected.
 *
 * Output
 *   ABA_THREADS, ABA_ITER, ABA_NODES, ABA_PUSHES, ABA_POPS, ABA_EMPTY_FINAL,
 *   ABA_NODE_MISMATCH, ABA_BAD_NODE, ABA_PTR_FITS, ABA_CREATED, ABA_TAGGED,
 *   ABA_TAGGED_HEAD_OK, ABA_EMPTY_MISSES, ABA_NOTE
 */
#include <pthread.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#define VER_SHIFT 48
#define PTR_MASK 0x0000FFFFFFFFFFFFULL
#define NODE_MAGIC 0xDADA0000A5A5ULL

struct node {
    struct node *next; /* written before publication, never modified after */
    unsigned long magic;
    int value;
    long pops;
};

struct worker {
    int tid;
    int iters;
    struct node *nodes; /* this worker's K nodes, pushed exactly once each */
    long pushes;
    long empty_misses;
};

static _Atomic uintptr_t head;
static long bad_node;
/* Pool bounds for the payload check (pop() must only ever return a node of
 * this probe, with its original value). */
static struct node *pool_base;
static long pool_count;

static uintptr_t pack(unsigned ver, struct node *p)
{
    return ((uintptr_t)(ver & 0xFFFF) << VER_SHIFT) | (uintptr_t)p;
}

static struct node *unpack(uintptr_t v)
{
    return (struct node *)(v & PTR_MASK);
}

static void push(struct node *n)
{
    struct node *oldp;
    uintptr_t old, new;

    for (;;) {
        old = atomic_load_explicit(&head, memory_order_relaxed);
        oldp = unpack(old);
        n->next = oldp;
        new = pack((unsigned)(old >> VER_SHIFT) + 1, n);
        if (atomic_compare_exchange_weak_explicit(&head, &old, new,
                                                  memory_order_acq_rel,
                                                  memory_order_relaxed))
            return;
    }
}

static struct node *pop(void)
{
    struct node *p, *nextp;
    uintptr_t old, new;

    for (;;) {
        old = atomic_load_explicit(&head, memory_order_acquire);
        p = unpack(old);
        if (!p)
            return 0;
        nextp = p->next;
        new = pack((unsigned)(old >> VER_SHIFT) + 1, nextp);
        if (atomic_compare_exchange_weak_explicit(&head, &old, new,
                                                  memory_order_acq_rel,
                                                  memory_order_acquire))
            return p;
    }
}

static void check_popped(struct node *p)
{
    if (p->magic != NODE_MAGIC)
        bad_node++;
    else if (p < pool_base || p >= pool_base + pool_count)
        bad_node++;
    else if (p->value != (int)(p - pool_base))
        bad_node++;
}

static void *worker_main(void *arg)
{
    struct worker *w = arg;
    int i;
    struct node *q;

    for (i = 0; i < w->iters; i++) {
        w->pushes++;
        push(&w->nodes[i]);
        q = pop();
        if (q) {
            check_popped(q);
            q->pops++;
        } else {
            w->empty_misses++;
        }
    }
    return 0;
}

int main(int argc, char **argv)
{
    int nthreads, iters, i, ok, created;
    long pushes = 0, pops = 0, mismatch = 0, ptr_over, misses = 0;
    struct node *all;
    struct worker *w;
    pthread_t *tid;
    uintptr_t snap, expected;
    int cas_accepted, tagged_ok, empty_final;

    nthreads = (argc > 1) ? atoi(argv[1]) : 4;
    iters = (argc > 2) ? atoi(argv[2]) : 10000;
    if (nthreads < 1 || iters < 2) {
        fprintf(stderr, "usage: %s [T>=1] [K>=2]\n", argv[0]);
        return 2;
    }

    all = calloc((size_t)nthreads * iters, sizeof *all);
    w = calloc((size_t)nthreads, sizeof *w);
    tid = calloc((size_t)nthreads, sizeof *tid);
    if (!all || !w || !tid) {
        fprintf(stderr, "out of memory\n");
        return 2;
    }
    pool_base = all;
    pool_count = (long)nthreads * iters;
    ptr_over = 0;
    for (i = 0; i < nthreads * iters; i++) {
        all[i].magic = NODE_MAGIC;
        all[i].value = i;
        if ((uintptr_t)&all[i] & ~PTR_MASK)
            ptr_over++;
    }
    printf("ABA_PTR_FITS=%d\n", ptr_over == 0 ? 1 : 0);
    if (ptr_over) {
        /* The packed head cannot hold this address: fail loudly, never
         * silently truncate. */
        printf("ABA_THREADS=%d\nABA_ITER=%d\nABA_NODES=%d\n", nthreads, iters,
               nthreads * iters);
        printf("ABA_PUSHES=0\nABA_POPS=0\nABA_EMPTY_FINAL=0\n");
        printf("ABA_NODE_MISMATCH=0\nABA_BAD_NODE=0\nABA_CREATED=0\n");
        printf("ABA_TAGGED=untested\nABA_TAGGED_HEAD_OK=0\n");
        printf("ABA_EMPTY_MISSES=0\n");
        return 3;
    }

    for (i = 0; i < nthreads; i++) {
        w[i].tid = i;
        w[i].iters = iters;
        w[i].nodes = &all[(size_t)i * iters];
    }
    created = 0;
    ok = 0;
    for (i = 0; i < nthreads; i++) {
        if (pthread_create(&tid[i], 0, worker_main, &w[i]) == 0) {
            created++;
            ok |= 1 << i;
        }
    }
    for (i = 0; i < nthreads; i++)
        if (ok & (1 << i))
            pthread_join(tid[i], 0);

    /* Drain whatever is left (concurrent push/pop need not end empty).  The
     * pool has exactly T*K nodes, so a drain that needs more iterations means
     * pop() stopped making progress: fail explicitly instead of hanging. */
    {
        int drained = 0;
        for (;;) {
            struct node *q = pop();
            if (!q)
                break;
            check_popped(q);
            q->pops++;
            if (++drained > nthreads * iters) {
                printf("ABA_DRAIN_OVERFLOW=1\n");
                break;
            }
        }
    }
    /* An empty stack keeps its version in the packed word: test the
     * pointer half, not the whole word. */
    empty_final = (unpack(atomic_load_explicit(&head, memory_order_acquire)) == 0);

    for (i = 0; i < nthreads * iters; i++) {
        pops += all[i].pops;
        if (all[i].pops != 1)
            mismatch++;
    }
    for (i = 0; i < nthreads; i++) {
        pushes += w[i].pushes;
        misses += w[i].empty_misses;
    }

    /* Deterministic ABA replay on two drained nodes: A pushed+popped, B
     * pushed+popped, A pushed again.  `snap` still names A but with an old
     * version, so the CAS must be rejected; an implementation that compared
     * only the pointer would accept it and hand out a node a concurrent
     * observer already consumed. */
    {
        struct node *qa = &all[0], *qb = &all[1];

        push(qa);
        snap = atomic_load_explicit(&head, memory_order_acquire);
        (void)pop();
        push(qb);
        (void)pop();
        push(qa);
        expected = snap;
        cas_accepted = atomic_compare_exchange_strong_explicit(
            &head, &expected, pack(0, qb), memory_order_acq_rel,
            memory_order_acquire);
        tagged_ok = (!cas_accepted && unpack(atomic_load(&head)) == qa);
        printf("ABA_TAGGED=%s\n",
               cas_accepted ? "cas_accepted" : "cas_rejected");
    }

    printf("ABA_THREADS=%d\n", nthreads);
    printf("ABA_ITER=%d\n", iters);
    printf("ABA_NODES=%d\n", nthreads * iters);
    printf("ABA_PUSHES=%ld\n", pushes);
    printf("ABA_POPS=%ld\n", pops);
    printf("ABA_EMPTY_FINAL=%d\n", empty_final ? 1 : 0);
    printf("ABA_NODE_MISMATCH=%ld\n", mismatch);
    printf("ABA_BAD_NODE=%ld\n", bad_node);
    printf("ABA_CREATED=%d\n", created);
    printf("ABA_TAGGED_HEAD_OK=%d\n", tagged_ok ? 1 : 0);
    printf("ABA_EMPTY_MISSES=%ld\n", misses);
    printf("ABA_NOTE same_value_write=undetectable: sc compares the whole "
           "aligned 8-byte word value (QEMU-067t), so a concurrent write that "
           "restores the same bytes is invisible to any lr/sc-based "
           "implementation; the version tag covers pointer ABA, not "
           "same-value writes\n");
    return 0;
}
