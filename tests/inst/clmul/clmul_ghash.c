/*
 * TESTCASES-057t -- GHASH (the GF(2^128) multiply of AES-GCM) computed with
 * `clmul.o`, end to end.
 *
 * The field and the bit order (this is the most error-prone point of the
 * whole task, so it is written out here):
 *
 *   * A 16-byte GCM block is a field element of GF(2^128) with the field
 *     polynomial x^128 + x^7 + x^2 + x + 1 and with the *leftmost* bit of the
 *     block being the constant term -- the "reflected" convention of NIST
 *     SP 800-38D §6.3 / the GCM specification.  Multiplication in that
 *     convention shifts right and reduces with 0xe1||0^120.
 *   * `clmul.o` multiplies in the natural polynomial order: bit i of the
 *     register is the coefficient of x^i.
 *
 *   Bridge:  X . Y  =  rev128( clmul128(rev128(X), rev128(Y)) mod P )
 *   where rev128 swaps the two 64-bit halves and bit-reverses each of them
 *   (`rev.o rd, rs, 1`, contract-isa.md §6.4.3).  tools/testcases/
 *   oracle_clmul.py proves this identity against the standard's bit-serial
 *   multiply *and* against the published X_1 of the GCM test vectors, so a
 *   missing/wrong reversal cannot be mistaken for a clmul.o defect.
 *
 * The carry-less product is 128x128 bits, built from four 64x64 `clmul.o`
 * results (lo, cross terms, hi); the 256-bit product is held as two 128-bit
 * halves and reduced by folding the high half down with
 * x^(128+i) = 0x87 * x^i (i = 0..127).
 *
 * The probe only OBSERVES: it prints the inputs it used, every intermediate
 * Y_i and the final GHASH(H,A,C).  tools/testcases/oracle_clmul.py recomputes
 * all of them (bit-serial) and, for the published test vectors, also compares
 * them with the values printed in the GCM specification (McGrew & Viega,
 * Appendix B test cases 1-4 -- the intermediate X_i are published there too).
 */
#include <stdio.h>
#include <stddef.h>
#include <stdint.h>

typedef unsigned __int128 u128;

/* ── bit reversal (rev.o k=1): the GCM <-> natural polynomial bridge ------ */
static unsigned long long rev64(unsigned long long v)
{
	return __builtin_bitreverse64(v);
}

static u128 rev128(u128 v)
{
	unsigned long long hi = (unsigned long long)(v >> 64);
	unsigned long long lo = (unsigned long long)v;

	return ((u128)rev64(lo) << 64) | (u128)rev64(hi);
}

/* ── GF(2)[x] multiply through clmul.o ------------------------------------ */
static u128 clmul_wide(unsigned long long a, unsigned long long b)
{
	return __builtin_dadao_clmul(a, b);
}

/* Reduce a 256-bit carry-less product (given as its low/high 128-bit halves)
 * modulo P = x^128 + x^7 + x^2 + x + 1.
 *
 * The high half is folded down once with x^128 = 0x87 = x^7 + x^2 + x + 1;
 * that product is 135 bits wide, so the seven bits that spill past x^127 are
 * folded a second time (they are then at most x^13).
 */
static u128 gf128_reduce(u128 p_lo, u128 p_hi)
{
	u128 lo = (p_hi << 7) ^ (p_hi << 2) ^ (p_hi << 1) ^ p_hi;
	u128 spill;

	/* bits of the folded product that sit at x^128..x^134 */
	spill = (p_hi >> 121) ^ (p_hi >> 126) ^ (p_hi >> 127);
	return p_lo ^ lo ^ (spill << 7) ^ (spill << 2) ^ (spill << 1) ^ spill;
}

/* 128x128 -> 256 carry-less product as (hi, lo), then reduce mod P. */
static u128 gf128_mul(u128 a, u128 b)
{
	unsigned long long a0 = (unsigned long long)a;
	unsigned long long a1 = (unsigned long long)(a >> 64);
	unsigned long long b0 = (unsigned long long)b;
	unsigned long long b1 = (unsigned long long)(b >> 64);
	u128 lo = clmul_wide(a0, b0);
	u128 mid = clmul_wide(a0, b1) ^ clmul_wide(a1, b0);
	u128 hi = clmul_wide(a1, b1);
	u128 p_lo = lo ^ (mid << 64);
	u128 p_hi = (mid >> 64) ^ hi;

	return gf128_reduce(p_lo, p_hi);
}

/* The GCM multiply: reverse both operands, multiply, reduce, reverse back. */
static u128 ghash_mul(u128 x, u128 y)
{
	return rev128(gf128_mul(rev128(x), rev128(y)));
}

/* ── GHASH (SP 800-38D §6.4) --------------------------------------------- */
static u128 load_be(const unsigned char *p)
{
	u128 v = 0;
	int i;

	for (i = 0; i < 16; i++)
		v = (v << 8) | p[i];
	return v;
}

static u128 ghash(const u128 h, const unsigned char *aad, size_t aad_len,
		  const unsigned char *ct, size_t ct_len, int verbose,
		  const char *label)
{
	u128 y = 0;
	size_t off, idx = 0;
	unsigned char blk[16];

	for (off = 0; off < aad_len; off += 16) {
		size_t n = aad_len - off < 16 ? aad_len - off : 16;
		size_t i;

		for (i = 0; i < 16; i++)
			blk[i] = i < n ? aad[off + i] : 0;
		y = ghash_mul(y ^ load_be(blk), h);
		if (verbose)
			printf("CHAIN %s %d %016llx%016llx\n", label,
			       (int)++idx, (unsigned long long)(y >> 64),
			       (unsigned long long)y);
	}
	for (off = 0; off < ct_len; off += 16) {
		size_t n = ct_len - off < 16 ? ct_len - off : 16;
		size_t i;

		for (i = 0; i < 16; i++)
			blk[i] = i < n ? ct[off + i] : 0;
		y = ghash_mul(y ^ load_be(blk), h);
		if (verbose)
			printf("CHAIN %s %d %016llx%016llx\n", label,
			       (int)++idx, (unsigned long long)(y >> 64),
			       (unsigned long long)y);
	}
	/* len(A) || len(C), in bits (SP 800-38D §6.4 last step). */
	return ghash_mul(y ^ (((u128)(aad_len * 8) << 64) | (ct_len * 8)), h);
}

/* ── case data: published GCM vectors + degenerate field elements --------- */
struct ghash_case {
	const char *label;
	const char *h;
	const char *aad;
	const char *ct;
};

static const struct ghash_case CASES[] = {
	/* GCM specification Appendix B, test cases 1-4 (H, X_i, GHASH). */
	{ "spec_tc1",
	  "66e94bd4ef8a2c3b884cfa59ca342b2e",
	  "",
	  "" },
	{ "spec_tc2",
	  "66e94bd4ef8a2c3b884cfa59ca342b2e",
	  "",
	  "0388dace60b6a392f328c2b971b2fe78" },
	{ "spec_tc3",
	  "b83b533708bf535d0aa6e52980d53b78",
	  "",
	  "42831ec2217774244b7221b784d0d49c"
	  "e3aa212f2c02a4e035c17e2329aca12e"
	  "21d514b25466931c7d8f6a5aac84aa05"
	  "1ba30b396a0aac973d58e091473f5985" },
	{ "spec_tc4",
	  "b83b533708bf535d0aa6e52980d53b78",
	  "feedfacedeadbeeffeedfacedeadbeefabaddad2",
	  "42831ec2217774244b7221b784d0d49c"
	  "e3aa212f2c02a4e035c17e2329aca12e"
	  "21d514b25466931c7d8f6a5aac84aa05"
	  "1ba30b396a0aac973d58e091" },
	/* Degenerate / structural cells (oracle-computed reference). */
	{ "zero_h",
	  "00000000000000000000000000000000",
	  "",
	  "000102030405060708090a0b0c0d0e0f"
	  "101112131415161718191a1b1c1d1e1f" },
	{ "ones_h",
	  "ffffffffffffffffffffffffffffffff",
	  "00112233445566778899aabbccddeeff",
	  "ffeeddccbbaa99887766554433221100"
	  "0f1e2d3c4b5a69788796a5b4c3d2e1f0" },
	{ "one_block",
	  "c0a1d4b6e8f20a3c5d7e9b1f3a5c7e90",
	  "",
	  "deadbeefcafebabe0123456789abcdef" },
	{ "two_blocks",
	  "0123456789abcdeffedcba9876543210",
	  "",
	  "00000000000000000000000000000001"
	  "80000000000000000000000000000000" },
	{ "block_and_half",
	  "66e94bd4ef8a2c3b884cfa59ca342b2e",
	  "aabbccddeeff00112233445566778899001122334455",
	  "111111111111111111111111111111112222222222222222222222" },
};

#define N_CASES ((int)(sizeof(CASES) / sizeof(CASES[0])))

static int hexval(int c)
{
	if (c >= '0' && c <= '9')
		return c - '0';
	if (c >= 'a' && c <= 'f')
		return c - 'a' + 10;
	if (c >= 'A' && c <= 'F')
		return c - 'A' + 10;
	return -1;
}

static size_t hex2bin(const char *hex, unsigned char *out, size_t cap)
{
	size_t n = 0;

	while (hex[0] != '\0') {
		unsigned int byte = (unsigned int)(hexval(hex[0]) << 4 |
						  hexval(hex[1]));

		if (n >= cap)
			return (size_t)-1;
		out[n++] = (unsigned char)byte;
		hex += 2;
	}
	return n;
}

static u128 load_be16(const char *hex)
{
	unsigned char b[16];
	int k;
	u128 v = 0;

	hex2bin(hex, b, sizeof(b));
	for (k = 0; k < 16; k++)
		v = (v << 8) | b[k];
	return v;
}

static void print_hex(const unsigned char *p, size_t n)
{
	size_t k;

	for (k = 0; k < n; k++)
		printf("%02x", p[k]);
}

int main(void)
{
	unsigned char aad[64], ct[64];
	int i;

	for (i = 0; i < N_CASES; i++) {
		const struct ghash_case *c = &CASES[i];
		size_t aad_len = hex2bin(c->aad, aad, sizeof(aad));
		size_t ct_len = hex2bin(c->ct, ct, sizeof(ct));
		u128 h = load_be16(c->h);
		u128 s;

		if (aad_len == (size_t)-1 || ct_len == (size_t)-1) {
			printf("BAD %s hex\n", c->label);
			return 1;
		}
		printf("GIN %s %016llx%016llx ", c->label,
		       (unsigned long long)(h >> 64),
		       (unsigned long long)h);
		if (aad_len == 0)
			printf("- ");
		else {
			print_hex(aad, aad_len);
			printf(" ");
		}
		if (ct_len == 0)
			printf("-\n");
		else {
			print_hex(ct, ct_len);
			printf("\n");
		}
		s = ghash(h, aad, aad_len, ct, ct_len, 1, c->label);
		printf("GOUT %s %016llx%016llx\n", c->label,
		       (unsigned long long)(s >> 64),
		       (unsigned long long)s);
	}
	return 0;
}
