/*
 * TESTCASES-057t -- `clmul.o` instruction-level matrix.
 *
 * `clmul.o {rdHA, rdHB}, rdHC, rdHD` is a carry-less 64x64 -> 128 multiply
 * (contract-isa.md `clmul.o_rrrr_rd`, ADR-0035 D2/D4): rdHA holds the high 64
 * bits, rdHB the low 64 bits, and a single side may be `rd0` to discard that
 * half.  There is no `clmulh`/`clmulr` instruction; the compiler reaches it
 * three ways (LLVM-122t):
 *
 *   * generic  `llvm.clmul.i64`        -> low half only   (clmul_ir.ll)
 *   * private  `llvm.dadao.clmul.hi`   -> high half only  (clmul_ir.ll)
 *   * private  `llvm.dadao.clmul`      -> both halves     (clmul_ir.ll)
 *   * builtin  `__builtin_dadao_clmul` -> `unsigned __int128` (here)
 *
 * All three exits are observed for every cell: the low half (generic
 * intrinsic), the high half (`.hi` intrinsic) and the composed 128-bit value
 * (the builtin), plus the `{lo, hi}` pair of the both-halves intrinsic.  That
 * is what catches a high/low swap on any single path.
 *
 * The probe only OBSERVES.  Every expected value is computed by
 * tools/testcases/oracle_clmul.py from GF(2)[x] polynomial arithmetic; the
 * oracle also re-derives each expectation from the operands printed here, so a
 * mistyped literal below is a hard failure rather than a silently matching
 * pair.
 *
 * Boundary cells (design §A): 0, 1, the top bit, (1<<63)*(1<<63) (the only
 * cell whose product reaches bit 126), all-ones x all-ones, single-bit pairs
 * (1<<k)*(1<<m) == 1<<(k+m), plus MIN_RANDOM splitmix64 cells with the fixed
 * seed 0xC1A50577 (reproducible; the drawn operands are printed, so the oracle
 * derives the expectation from them).
 */
#include <stdio.h>
#include <stdint.h>

typedef unsigned __int128 u128;

/* tests/clmul/clmul_ir.ll -- the paths with no C spelling. */
extern unsigned long long clmul_generic_lo(unsigned long long,
                                           unsigned long long);
extern unsigned long long clmul_intr_hi(unsigned long long,
                                        unsigned long long);
extern unsigned long long clmul_pair_lo(unsigned long long,
                                        unsigned long long);
extern unsigned long long clmul_pair_hi(unsigned long long,
                                        unsigned long long);

struct clmul_case {
	const char *label;
	unsigned long long a;
	unsigned long long b;
};

static const struct clmul_case EDGES[] = {
	{ "zero_zero", 0, 0 },
	{ "zero_top", 0, 1ULL << 63 },
	{ "one_zero", 1, 0 },
	{ "one_one", 1, 1 },
	{ "one_top", 1, 1ULL << 63 },
	{ "top_top", 1ULL << 63, 1ULL << 63 },
	{ "top_one", 1ULL << 63, 1 },
	{ "zero_bit", 1ULL, 1ULL << 63 },
	{ "all_all", ~0ULL, ~0ULL },
	{ "all_one", ~0ULL, 1 },
	{ "all_top", ~0ULL, 1ULL << 63 },
	{ "msb_pair", 0x8000000000000001ULL, 0x8000000000000001ULL },
	{ "alt_alt", 0xAAAAAAAAAAAAAAAAULL, 0x5555555555555555ULL },
	{ "low_high", 0x0123456789ABCDEFULL, 0xFEDCBA9876543210ULL },
	{ "bit_0_0", 1ULL << 0, 1ULL << 0 },
	{ "bit_1_62", 1ULL << 1, 1ULL << 62 },
	{ "bit_31_32", 1ULL << 31, 1ULL << 32 },
	{ "bit_62_63", 1ULL << 62, 1ULL << 63 },
	{ "bit_63_63", 1ULL << 63, 1ULL << 63 },
	{ "bit_63_0", 1ULL << 63, 1ULL },
};
#define N_EDGES ((int)(sizeof(EDGES) / sizeof(EDGES[0])))

/* splitmix64 with the fixed seed the oracle documents (RANDOM_SEED). */
static unsigned long long sm_state = 0xC1A50577ULL;

static unsigned long long splitmix64(void)
{
	unsigned long long z = (sm_state += 0x9E3779B97F4A7C15ULL);

	z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
	z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
	return z ^ (z >> 31);
}

/* rev.o rd, rs, 1 (bit reverse) -- the GCM bit-order bridge, not the
 * instruction under test here; the oracle judges it as well so a broken
 * reversal cannot be mistaken for a clmul defect. */
static unsigned long long rev64(unsigned long long v)
{
	return __builtin_bitreverse64(v);
}

static void emit(const char *label, unsigned long long a,
		 unsigned long long b)
{
	unsigned long long lo = clmul_generic_lo(a, b);   /* llvm.clmul   */
	unsigned long long hi = clmul_intr_hi(a, b);      /* dadao.clmul.hi */
	unsigned long long plo = clmul_pair_lo(a, b);     /* dadao.clmul  */
	unsigned long long phi = clmul_pair_hi(a, b);
	u128 wide = __builtin_dadao_clmul(a, b);          /* i128 form    */
	unsigned long long whi = (unsigned long long)(wide >> 64);
	unsigned long long wlo = (unsigned long long)wide;

	printf("EDGE %s %016llx %016llx %016llx %016llx %016llx %016llx\n",
	       label, a, b, lo, hi, whi, wlo);
	printf("PAIR %s %016llx %016llx\n", label, plo, phi);
}

int main(void)
{
	static const struct {
		const char *label;
		unsigned long long in;
	} REV[] = {
		{ "zero", 0 },
		{ "all", ~0ULL },
		{ "pattern", 0x0123456789ABCDEFULL },
		{ "top", 1ULL << 63 },
		{ "low", 1 },
		{ "rev_self", 0xF7B3D591E6A2C480ULL },
	};
	int i;
	char label[32];

	for (i = 0; i < (int)(sizeof(REV) / sizeof(REV[0])); i++)
		printf("REV %s %016llx %016llx\n", REV[i].label, REV[i].in,
		       rev64(REV[i].in));

	for (i = 0; i < N_EDGES; i++)
		emit(EDGES[i].label, EDGES[i].a, EDGES[i].b);

	/* 64 randomised cells, seed 0xC1A50577 (splitmix64). */
	for (i = 0; i < 64; i++) {
		unsigned long long a = splitmix64();
		unsigned long long b = splitmix64();

		snprintf(label, sizeof(label), "rand_%02d", i);
		emit(label, a, b);
	}
	return 0;
}
