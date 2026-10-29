/*
 * barrier_probe.c -- structural assertion for musl's a_barrier (TESTCASES-056t,
 * family E).
 *
 * Purpose
 *   `a_barrier()` is the only memory barrier the musl port provides, and a
 *   compiler-only barrier (the pre-INFRA-100t `__asm__ __volatile__("" ::: "memory")`)
 *   is indistinguishable from a hardware `fence` at run time on a single hart:
 *   "the program ran and saw the right values" cannot prove it.  So the claim
 *   is judged *structurally*: the number of `fence` instructions in the
 *   generated assembly/object must equal the number of a_barrier call sites in
 *   this source (derived live by the oracle, never a constant), and the fence
 *   immediate must be the full-barrier encoding the port installs (0xFFF).
 *
 * Independent oracle (tools/testcases/oracle_atomics.py)
 *   barrier_expected() counts `a_barrier();` occurrences in this file's text.
 *   The driver compares that count with the `fence` count of `clang -S` and of
 *   `llvm-objdump -d` for BOTH link modes.  If a_barrier degraded to an empty
 *   asm statement the fence count becomes 0 and the assertion goes red (that is
 *   the injected counter-example in the evidence script).
 *
 * Runtime part (observation only, NOT a hard criterion)
 *   `store(data); a_barrier(); store(flag)` followed by the matching read
 *   sequence: a read that sees flag must also see data.  qemu-user executes one
 *   guest hart on one host thread with a sequentially consistent host memory
 *   model, so this observation is *insensitive* -- passing it is not evidence
 *   that the barrier exists (hence the structural check above).  Insensitive is
 *   not equivalent; the driver records the numbers as an observation.
 *
 * Output
 *   BARRIER_RUNTIME_ROUNDS, BARRIER_RUNTIME_MISMATCH, BARRIER_DATA0/3.
 *   The a_barrier site count is NOT printed: it is the oracle's job to derive
 *   it from this source text (a constant in the probe would be self-certifying).
 */
#include <atomic_arch.h>
#include <stdio.h>

static volatile int data[8];
static volatile int flag[8];

/* One call site per function, no macro: the source count below is literal. */
__attribute__((noinline)) static void w0(void)
{
    data[0] = 101;
    a_barrier();
    flag[0] = 101;
}

__attribute__((noinline)) static void w1(void)
{
    data[1] = 102;
    a_barrier();
    flag[1] = 102;
}

__attribute__((noinline)) static void w2(void)
{
    data[2] = 103;
    a_barrier();
    flag[2] = 103;
}

__attribute__((noinline)) static void w3(void)
{
    data[3] = 104;
    a_barrier();
    flag[3] = 104;
}

int main(void)
{
    int i, mismatches = 0;
    const int rounds = 20000;
    volatile int seen_data, seen_flag;

    w0();
    w1();
    w2();
    w3();

    for (i = 0; i < rounds; i++) {
        data[4] = i + 1;
        a_barrier();
        flag[4] = i + 1;
        seen_flag = flag[4];
        seen_data = data[4];
        a_barrier();
        if (seen_flag != i + 1 || seen_data != i + 1)
            mismatches++;
    }

    printf("BARRIER_RUNTIME_ROUNDS=%d\n", rounds);
    printf("BARRIER_RUNTIME_MISMATCH=%d\n", mismatches);
    printf("BARRIER_DATA0=%d\n", data[0]);
    printf("BARRIER_DATA3=%d\n", data[3]);
    return 0;
}
