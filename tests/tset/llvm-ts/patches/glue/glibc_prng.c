/*
 * glibc_prng.c -- test glue (TESTCASES-080t): a portable implementation of
 * glibc's `srandom()`/`random()` pair.
 *
 * Why this file exists
 * --------------------
 * Two llvm-test-suite programs produce their whole output from `random()`:
 *
 *   * MultiSource/Applications/obsequi -- init.c:63 `srandom(1)` then
 *     init.c:66 seeds its Zobrist tables with `random()`;
 *   * MultiSource/Benchmarks/Ptrdist/ft -- graph.c:43 `#define GET_WEIGHT
 *     (random() + 1) % MAX_WEIGHT`; ft.c:86 only calls `srandom()` when a third
 *     argv is given, and its CMake RUN_OPTIONS stop at two arguments, so the
 *     program uses the generator's *default* state.
 *
 * The C standard does not specify the `random()` algorithm, so the output of
 * these programs is libc-defined.  Upstream's reference outputs pin **glibc's**
 * generator (verified on this host: an `-O2` gcc build of the unmodified corpus
 * reproduces them byte for byte), while musl's `random()` is a different
 * generator.  The reference is therefore unreachable with musl's own generator
 * even though the program's semantics are fine.
 *
 * This translation unit is compiled with the same clang/target and linked into
 * those two cases only (see `CASE_PRNG_GLUE` in
 * `tools/testcases/tset/llvm-ts/run_llvm_ts_user.py`).  It defines
 * `random()`/`srandom()` with glibc's exact algorithm, so `libc.a`'s own
 * `random.o` is not pulled in and the reference stays a byte-exact oracle.
 * Nothing is relaxed: a mismatch is still a `fail`.
 *
 * The algorithm (glibc stdlib/random_r.c, TYPE_3: degree 31, separation 3):
 *
 *   srandom(s):  if s == 0 then s = 1
 *                state[0] = s
 *                state[i] = (16807 * state[i-1]) mod 2147483647  (i = 1..30)
 *                fptr = 3, rptr = 0
 *   random():    state[fptr] += state[rptr]   (mod 2^32, 31-bit result)
 *                result = state[fptr] >> 1
 *                advance fptr and rptr, both wrapping at 31
 *
 * glibc's initial (unseeded) state is exactly `srandom(1)`, so the lazy
 * initialisation below matches `ft`'s use of the default state.
 *
 * Verified on the host against glibc itself (`patches/glue/verify_glibc_prng.py`):
 * the unseeded default state and seeds 0, 1, 2, 7, 12345, 2147483647 and
 * 4294967295 all give the host glibc's `random()` values for 100 draws.
 */

#include <stdint.h>
#include <stdlib.h>   /* the target libc's own prototypes for random()/
			 srandom(): including it makes the compiler check that
			 these definitions match the ABI the caller sees */

#define PRNG_DEG 31
#define PRNG_SEP 3
#define PRNG_MASK 0x7fffffffU

static int32_t prng_state[PRNG_DEG];
static int prng_fptr = PRNG_SEP;
static int prng_rptr = 0;
static int prng_ready = 0;

static void prng_seed(unsigned int seed);
static long prng_next(void);

static void prng_seed(unsigned int seed)
{
	int i;
	int32_t word;

	if (seed == 0)
		seed = 1;                 /* glibc: "We must make sure the seed is
					     not 0.  Take arbitrarily 1 in this case." */
	prng_state[0] = (int32_t)seed;
	word = (int32_t)seed;
	for (i = 1; i < PRNG_DEG; i++) {
		/* Glibc's Schrage form of (16807 * word) mod 2147483647; the
		 * 64-bit product stays exact in long. */
		long hi = (long)word / 127773L;
		long lo = (long)word % 127773L;
		long next = 16807L * lo - 2836L * hi;

		if (next < 0)
			next += 2147483647L;
		word = (int32_t)next;
		prng_state[i] = word;
	}
	prng_fptr = PRNG_SEP;
	prng_rptr = 0;
	/* glibc's __srandom_r discards rand_deg * 10 = 310 values after
	 * seeding ("kc *= 10; while (--kc >= 0) __random_r(...)").  Without
	 * this warm-up the sequence is the textbook BSD one, not glibc's. */
	for (i = 0; i < PRNG_DEG * 10; i++)
		(void)prng_next();
	prng_ready = 1;
}

void srandom(unsigned int seed)
{
	prng_seed(seed);
}

static long prng_next(void)
{
	uint32_t val;

	val = (uint32_t)prng_state[prng_fptr] + (uint32_t)prng_state[prng_rptr];
	prng_state[prng_fptr] = (int32_t)val;
	/* Same pointer advance as glibc's __random_r (fptr wraps => state). */
	if (++prng_fptr >= PRNG_DEG) {
		prng_fptr = 0;
		++prng_rptr;
	} else {
		++prng_rptr;
		if (prng_rptr >= PRNG_DEG)
			prng_rptr = 0;
	}
	return (long)((val >> 1) & PRNG_MASK);
}

long random(void)
{
	if (!prng_ready)
		prng_seed(1);            /* glibc's unseeded default state */
	return prng_next();
}
