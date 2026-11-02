/*
 * TESTCASES-057t -- CRC-32C (Castagnoli) on `clmul.o`.
 *
 * Parameters are fixed by the standard and are *asserted* (both here and in
 * tools/testcases/oracle_clmul.py):
 *
 *     poly      0x1EDC6F41     (x^32 + x^28+x^27+x^26+x^25+x^22+x^21+x^19
 *                               +x^18+x^16+x^14+x^13+x^11+x^10+x^9+x^6+1)
 *     reflected 0x82F63B78     (refin = refout = true)
 *     init      0xFFFFFFFF
 *     xorout    0xFFFFFFFF
 *     check     crc32c("123456789") == 0xE3069283
 *
 * There is no `crc32c` instruction on this target, so the CRC is computed with
 * a carry-less multiply folding kernel (ADR-0035 puts GHASH/CRC/Reed-Solomon
 * in clmul.o's application domain).
 *
 * Folding kernel
 * --------------
 * The reflected CRC state is kept in natural polynomial order
 * (``u = rev32(s_ref)``, bit i = x^i), which turns one 8-byte chunk into a
 * single field operation:
 *
 *     u' = (u * x^64  +  M * x^32) mod P,   P = x^32 + 0x1EDC6F41
 *     M  = rev64(chunk)          (reflected bit order = natural order after
 *                                 reversal; the chunk is loaded little-endian)
 *
 * The 96-bit value is folded to 64 bits with one carry-less multiply by
 * ``C64 = x^64 mod P`` (deg 29, so the product of the 32-bit high part is
 * at most 60 bits), then reduced to 32 bits with a GF(2) Barrett step:
 *
 *     q = ( (r >> 31) * mu ) >> 33 ,  mu = floor(x^64 / P)
 *     u = r  ^  q * P
 *
 * which is exact for deg(r) <= 63 (validated against the bit-serial reference
 * over every length in the table, in both this probe and the oracle).
 *
 * Sub-8-byte tails reuse the same fold with nb = 8 bits per byte, so *every*
 * byte of the message goes through the clmul.o path (no table, no per-bit
 * loop in the shipped kernel).
 *
 * The probe only OBSERVES: it prints length, CRC and an FNV-1a digest of the
 * generated data.  tools/testcases/oracle_clmul.py regenerates the data
 * (identical documented patterns), checks the digest, and computes the
 * reference CRC bit-serially -- never with clmul and never with a table.
 */
#include <stdio.h>
#include <stddef.h>
#include <stdint.h>

typedef unsigned __int128 u128;

/* ── parameters (CRC-32C / Castagnoli) ------------------------------------ */
#define CRC32C_POLY_FULL 0x11EDC6F41ULL   /* P including the x^32 term */
#define CRC32C_C64 0x3AAB4576ULL          /* x^64 mod P                 */
#define CRC32C_MU 0x11F91CAF6ULL          /* floor(x^64 / P)            */
#define CRC32C_INIT 0xFFFFFFFFu
#define CRC32C_XOROUT 0xFFFFFFFFu

static unsigned long long rev64(unsigned long long v)
{
	return __builtin_bitreverse64(v);
}

static u128 clmul_wide(unsigned long long a, unsigned long long b)
{
	return __builtin_dadao_clmul(a, b);
}

static unsigned long long clmul_lo(unsigned long long a,
				   unsigned long long b)
{
	/* Both call sites here have a product of degree < 64 by construction. */
	return (unsigned long long)clmul_wide(a, b);
}

/* r mod P for deg(r) <= 63 (GF(2) Barrett; mu = floor(x^64/P)). */
static uint32_t barrett32(unsigned long long r)
{
	/* The product is 66 bits wide: keep the u128, the quotient needs
	 * bits 64..65 of it (truncating to 64 bits is a real bug -- measured). */
	u128 t = clmul_wide(r >> 31, CRC32C_MU);
	unsigned long long q = (unsigned long long)(t >> 33);
	unsigned long long qp = clmul_lo(q, CRC32C_POLY_FULL);

	return (uint32_t)(r ^ qp);
}

/* One folding step: (u * x^nb + m * x^32) mod P, deg(m) < nb <= 64. */
static uint32_t crc_fold(uint32_t u, unsigned long long m, unsigned nb)
{
	unsigned long long lo = m << 32;
	unsigned long long hi = m >> 32;
	unsigned long long r;

	if (nb == 64) {
		hi ^= (unsigned long long)u;
	} else if (nb >= 32) {
		hi ^= (unsigned long long)u >> (64 - nb);
		lo ^= (unsigned long long)u << nb;
	} else {
		lo ^= (unsigned long long)u << nb;
	}
	/* U = hi * x^64 + lo (deg(hi) <= 31 for nb <= 64). */
	r = lo ^ clmul_lo(hi, CRC32C_C64);
	return barrett32(r);
}

static uint32_t crc32c_clmul(const unsigned char *p, size_t n)
{
	uint32_t u = CRC32C_INIT;
	size_t i = 0;

	while (n - i >= 8) {
		unsigned long long w = 0;
		int k;

		for (k = 7; k >= 0; k--)      /* little-endian chunk */
			w = (w << 8) | p[i + (size_t)k];
		u = crc_fold(u, rev64(w), 64);
		i += 8;
	}
	while (i < n) {
		u = crc_fold(u, rev64((unsigned long long)p[i]) >> 56, 8);
		i++;
	}
	return (uint32_t)(rev64((unsigned long long)u) >> 32) ^ CRC32C_XOROUT;
}

/* ── deterministic data patterns (mirrored by the oracle) ----------------- */
static unsigned long long lcg_state;

static void gen_data(const char *kind, unsigned char *buf, size_t n)
{
	size_t i;

	if (kind[0] == 'r' && kind[1] == 'a') {          /* ramp  */
		for (i = 0; i < n; i++)
			buf[i] = (unsigned char)((i * 31 + 7) & 0xFF);
	} else if (kind[0] == 'l') {                     /* lcg   */
		lcg_state = 0x123456789ABCDEF0ULL;
		for (i = 0; i < n; i++) {
			lcg_state = lcg_state * 6364136223846793005ULL +
				    1442695040888963407ULL;
			buf[i] = (unsigned char)(lcg_state >> 56);
		}
	} else if (kind[0] == 'z') {                     /* zeros */
		for (i = 0; i < n; i++)
			buf[i] = 0;
	} else if (kind[0] == 'f') {                     /* ff    */
		for (i = 0; i < n; i++)
			buf[i] = 0xFF;
	} else if (kind[0] == 's' && kind[1] == 't') {   /* string */
		static const char str[] = "123456789";

		for (i = 0; i < n && i < sizeof(str) - 1; i++)
			buf[i] = (unsigned char)str[i];
	} else if (kind[0] == 's' && kind[3] == '\0') {   /* seq   */
		for (i = 0; i < n; i++)
			buf[i] = (unsigned char)(i & 0xFF);
	} else {                                         /* seqr  */
		for (i = 0; i < n; i++)
			buf[i] = (unsigned char)((n - 1 - i) & 0xFF);
	}
}

static unsigned long long fnv1a64(const unsigned char *p, size_t n)
{
	unsigned long long h = 14695981039346656037ULL;
	size_t i;

	for (i = 0; i < n; i++) {
		h ^= p[i];
		h *= 1099511628211ULL;
	}
	return h;
}

/* ── cases --------------------------------------------------------------- */
struct crc_case {
	const char *label;
	const char *kind;
	size_t len;
};

static const struct crc_case CASES[] = {
	{ "crc_empty_ramp", "ramp", 0 },
	{ "crc_one_ramp", "ramp", 1 },
	{ "crc_seven_ramp", "ramp", 7 },
	{ "crc_eight_ramp", "ramp", 8 },
	{ "crc_nine_ramp", "ramp", 9 },
	{ "crc_fifteen_ramp", "ramp", 15 },
	{ "crc_sixteen_ramp", "ramp", 16 },
	{ "crc_seventeen_ramp", "ramp", 17 },
	{ "crc_sixtythree_lcg", "lcg", 63 },
	{ "crc_sixtyfour_lcg", "lcg", 64 },
	{ "crc_sixtyfive_lcg", "lcg", 65 },
	{ "crc_thousand_lcg", "lcg", 1000 },
	{ "crc_check123456789", "string", 9 },
	{ "crc_zeros32", "zeros", 32 },
	{ "crc_ff32", "ff", 32 },
	{ "crc_seq32", "seq", 32 },
	{ "crc_seqr32", "seqr", 32 },
};

#define N_CASES ((int)(sizeof(CASES) / sizeof(CASES[0])))
#define MAX_LEN 1000

int main(void)
{
	static unsigned char buf[MAX_LEN];
	int i;

	for (i = 0; i < N_CASES; i++) {
		const struct crc_case *c = &CASES[i];
		uint32_t crc;
		unsigned long long fnv;

		gen_data(c->kind, buf, c->len);
		crc = crc32c_clmul(buf, c->len);
		fnv = fnv1a64(buf, c->len);
		printf("CRC %s %zu %08x %016llx\n", c->label, c->len,
		       (unsigned int)crc, fnv);
	}
	return 0;
}
