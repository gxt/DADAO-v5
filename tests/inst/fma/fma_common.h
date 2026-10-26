/*
 * TESTCASES-058t shared probe support: ftfma/fofma (fusedMultiplyAdd).
 *
 * Spec sources (semantics, never QEMU/LLVM output):
 *   spec/SimRISC-07 §2.5  -- exact product, ONE rounding, special values
 *   .tao/contracts/contract-fp.md §20 -- frozen fma contract
 *   spec/SimRISC-00 §浮点状态寄存器 -- rf0 write mask: only [33:32] and [4:0]
 *
 * The probes only OBSERVE: every expected value / flag is derived by
 * tools/testcases/oracle_fma.py from the spec.  Nothing here judges.
 *
 * rf0 programming uses `set.w`:
 *   `set.w rf0, wp2, 0x000N` -> rf0[33:32] = N (0 RNE, 1 RTZ, 2 RDN, 3 RUP);
 *   `set.w rf0, wp0, 0`      -> clear the accrued flags [4:0].
 * Reading rf0 uses `rf2rd` (rf0 is a legal source).
 *
 * rf10-rf13 are the temporary range (contract-abi.md §1.4); they are declared
 * as clobbers so the compiler keeps nothing live there.
 */
#ifndef FMA_COMMON_H
#define FMA_COMMON_H

#include <math.h>
#include <stdint.h>
#include <stdio.h>

#define FMA_RF0_FLAGS_MASK 0x1fULL
#define FMA_RF0_RESET 0x7FF800007FC00000ULL
#define FMA_FNV_INIT 14695981039346656037ULL
#define FMA_FNV_PRIME 1099511628211ULL

union fma_u64 {
	double d;
	unsigned long long u;
};

union fma_u32 {
	float f;
	unsigned int u;
};

/* ── rf0 (FCSR) access ────────────────────────────────────────────────── */
static inline unsigned long long fma_rd_rf0(void)
{
	unsigned long long v;

	__asm__ __volatile__("rf2rd {%[o]}, {rf0}" : [o] "=r"(v) : : "memory");
	return v;
}

/* Read rf0 but force ``dep`` to be computed first: without this the compiler
 * may hoist the read above a straight-line FMA loop (the FP results have no
 * data dependency on the asm) and the accrued flags would read as 0. */
static inline unsigned long long fma_rd_rf0_dep(unsigned long long dep)
{
	unsigned long long v;

	__asm__ __volatile__("rf2rd {%[o]}, {rf0}"
			     : [o] "=r"(v) : [d] "r"(dep) : "memory");
	return v;
}

/* Make an operand opaque to the optimiser: `fma(const, const, const)` would
 * otherwise be constant-folded at -O2 (the builtin is `const`), so the guest
 * would never execute the fused instruction under test. */
static inline unsigned long long fma_hide(unsigned long long v)
{
	__asm__("" : "+r"(v));
	return v;
}

static inline void fma_set_mode(int rm)
{
	switch (rm & 3) {
	case 0:
		__asm__ __volatile__("set.w rf0, wp2, 0x0000" : : : "memory");
		break;
	case 1:
		__asm__ __volatile__("set.w rf0, wp2, 0x0001" : : : "memory");
		break;
	case 2:
		__asm__ __volatile__("set.w rf0, wp2, 0x0002" : : : "memory");
		break;
	default:
		__asm__ __volatile__("set.w rf0, wp2, 0x0003" : : : "memory");
		break;
	}
}

static inline void fma_clear_flags(void)
{
	__asm__ __volatile__("set.w rf0, wp0, 0x0000" : : : "memory");
}

/* ── instruction under test (asm path: exactly one ftfma/fofma) ───────── */
static inline unsigned long long fma_asm(const char *fmt, unsigned long long a,
					 unsigned long long b,
					 unsigned long long c)
{
	unsigned long long o;

	if (fmt[1] == 't')
		__asm__ __volatile__("rd2rf {rf10}, {%[a]}\n\t"
				     "rd2rf {rf11}, {%[b]}\n\t"
				     "rd2rf {rf12}, {%[c]}\n\t"
				     "ftfma rf13, rf10, rf11, rf12\n\t"
				     "rf2rd {%[o]}, {rf13}"
				     : [o] "=r"(o)
				     : [a] "r"(a), [b] "r"(b), [c] "r"(c)
				     : "rf10", "rf11", "rf12", "rf13", "memory");
	else
		__asm__ __volatile__("rd2rf {rf10}, {%[a]}\n\t"
				     "rd2rf {rf11}, {%[b]}\n\t"
				     "rd2rf {rf12}, {%[c]}\n\t"
				     "fofma rf13, rf10, rf11, rf12\n\t"
				     "rf2rd {%[o]}, {rf13}"
				     : [o] "=r"(o)
				     : [a] "r"(a), [b] "r"(b), [c] "r"(c)
				     : "rf10", "rf11", "rf12", "rf13", "memory");
	return o;
}

/* ── bit patterns <-> C values ────────────────────────────────────────── */
static inline unsigned long long fma_bits_d(double x)
{
	union fma_u64 u;

	u.d = x;
	return u.u;
}

static inline unsigned long long fma_bits_f(float x)
{
	union fma_u32 u;

	u.f = x;
	return (unsigned long long)u.u;
}

static inline double fma_val_d(unsigned long long bits)
{
	union fma_u64 u;

	u.u = bits;
	return u.d;
}

static inline float fma_val_f(unsigned long long bits)
{
	union fma_u32 u;

	u.u = (unsigned int)bits;
	return u.f;
}

/* ── the C library-name path: `fma`/`fmaf` (must become fofma/ftfma) ──── */
static inline unsigned long long fma_c(const char *fmt, unsigned long long a,
				       unsigned long long b,
				       unsigned long long c)
{
	a = fma_hide(a);
	b = fma_hide(b);
	c = fma_hide(c);
	if (fmt[1] == 't')
		return fma_bits_f(fmaf(fma_val_f(a), fma_val_f(b),
				       fma_val_f(c)));
	return fma_bits_d(fma(fma_val_d(a), fma_val_d(b), fma_val_d(c)));
}

/* ── the WRONG sequence: round(a*b) then add (volatile blocks fusion) ─── */
static inline unsigned long long fma_two_step(const char *fmt,
					      unsigned long long a,
					      unsigned long long b,
					      unsigned long long c)
{
	a = fma_hide(a);
	b = fma_hide(b);
	c = fma_hide(c);
	if (fmt[1] == 't') {
		volatile float prod = fma_val_f(a) * fma_val_f(b);

		return fma_bits_f(prod + fma_val_f(c));
	} else {
		volatile double prod = fma_val_d(a) * fma_val_d(b);

		return fma_bits_d(prod + fma_val_d(c));
	}
}

/* ── `acc += a * b`: the frontend contracts this to llvm.fmuladd ──────── */
static inline unsigned long long fma_contract(const char *fmt,
					      unsigned long long a,
					      unsigned long long b,
					      unsigned long long c)
{
	a = fma_hide(a);
	b = fma_hide(b);
	c = fma_hide(c);
	if (fmt[1] == 't') {
		float acc = fma_val_f(c);

		acc += fma_val_f(a) * fma_val_f(b);
		return fma_bits_f(acc);
	} else {
		double acc = fma_val_d(c);

		acc += fma_val_d(a) * fma_val_d(b);
		return fma_bits_d(acc);
	}
}

/* ── observation printers ─────────────────────────────────────────────── */
static inline void fma_obs_asm(const char *group, const char *fmt,
			       const char *label, unsigned long long a,
			       unsigned long long b, unsigned long long c,
			       int rm)
{
	unsigned long long pre, out, post;

	fma_set_mode(rm);
	fma_clear_flags();
	pre = fma_rd_rf0();
	out = fma_asm(fmt, a, b, c);
	post = fma_rd_rf0();
	printf("OBS group=%s fmt=%s label=%s a=%016llx b=%016llx c=%016llx "
	       "out=%016llx pre=%016llx post=%016llx rm=%d\n",
	       group, fmt, label, a, b, c, out, pre, post,
	       (int)((pre >> 32) & 3));
}

static inline void fma_obs_disc(const char *label, const char *fmt,
				unsigned long long a, unsigned long long b,
				unsigned long long c, int rm)
{
	unsigned long long pre, out, post, step;

	fma_set_mode(rm);
	fma_clear_flags();
	pre = fma_rd_rf0();
	out = fma_c(fmt, a, b, c);
	post = fma_rd_rf0();
	step = fma_two_step(fmt, a, b, c);
	printf("OBS group=disc fmt=%s label=%s a=%016llx b=%016llx c=%016llx "
	       "out=%016llx step=%016llx pre=%016llx post=%016llx rm=%d\n",
	       fmt, label, a, b, c, out, step, pre, post,
	       (int)((pre >> 32) & 3));
}

static inline void fma_obs_c(const char *group, const char *fmt,
			     const char *label, unsigned long long a,
			     unsigned long long b, unsigned long long c, int rm)
{
	unsigned long long pre, out, post;

	fma_set_mode(rm);
	fma_clear_flags();
	pre = fma_rd_rf0();
	out = fma_c(fmt, a, b, c);
	post = fma_rd_rf0();
	printf("OBS group=%s fmt=%s label=%s a=%016llx b=%016llx c=%016llx "
	       "out=%016llx pre=%016llx post=%016llx rm=%d\n",
	       group, fmt, label, a, b, c, out, pre, post,
	       (int)((pre >> 32) & 3));
}

static inline void fma_obs_contract(const char *label, const char *fmt,
				    unsigned long long a, unsigned long long b,
				    unsigned long long c, int rm)
{
	unsigned long long pre, out, post, step;

	fma_set_mode(rm);
	fma_clear_flags();
	pre = fma_rd_rf0();
	out = fma_contract(fmt, a, b, c);
	post = fma_rd_rf0();
	step = fma_two_step(fmt, a, b, c);
	printf("OBS group=contract fmt=%s label=%s a=%016llx b=%016llx "
	       "c=%016llx out=%016llx step=%016llx pre=%016llx post=%016llx "
	       "rm=%d\n", fmt, label, a, b, c, out, step, pre, post,
	       (int)((pre >> 32) & 3));
}

/* Restore rf0 (mode kept, flags cleared) and print the read-back so one
 * group cannot silently pollute the next. */
static inline void fma_restore(const char *group, unsigned long long initial)
{
	unsigned long long want = initial & ~FMA_RF0_FLAGS_MASK;
	unsigned long long got;

	fma_set_mode((int)((initial >> 32) & 3));
	fma_clear_flags();
	got = fma_rd_rf0();
	printf("RESTORE group=%s expect=%016llx got=%016llx\n", group, want, got);
}

/* ── FNV-1a over a 64-bit observation (probe and oracle must agree) ───── */
static inline unsigned long long fma_fnv_u64(unsigned long long h,
					     unsigned long long v)
{
	int i;

	for (i = 0; i < 8; i++) {
		h ^= (v >> (8 * i)) & 0xff;
		h *= FMA_FNV_PRIME;
	}
	return h;
}

/* ── deterministic data: value = (int32)u / 2^31 (exact in binary64) ──── */
static inline unsigned int fma_lcg(unsigned int u)
{
	return u * 1664525u + 1013904223u;
}

static inline double fma_ratio(unsigned int u)
{
	return (double)(int32_t)u / 2147483648.0;
}

static inline void fma_gen(unsigned int seed, double *out, int n)
{
	unsigned int u = seed;
	int i;

	for (i = 0; i < n; i++) {
		u = fma_lcg(u);
		out[i] = fma_ratio(u);
	}
}

static inline void fma_gen_f(unsigned int seed, float *out, int n)
{
	unsigned int u = seed;
	int i;

	for (i = 0; i < n; i++) {
		u = fma_lcg(u);
		out[i] = (float)fma_ratio(u);
	}
}

#endif /* FMA_COMMON_H */
