/*
 * TESTCASES-059t shared probe support: ftmin/ftmax/fomin/fomax
 * (IEEE 754-2019 minimumNumber / maximumNumber).
 *
 * Spec sources (semantics, never QEMU/LLVM output):
 *   spec/SimRISC-07 §2.4  -- the six boundary rules of minimumNumber/maximumNumber
 *   .tao/contracts/contract-fp.md §19 -- frozen minmax contract
 *   spec/SimRISC-00 §浮点状态寄存器 -- rf0 write mask: only [33:32] and [4:0]
 *
 * The probes only OBSERVE: every expected value / flag comes from
 * tools/testcases/oracle_minmax.py, which derives it from the spec.
 *
 * rf0 programming uses `set.w`:
 *   `set.w rf0, wp2, 0x0000` -> rf0[33:32] = RNE (min/max ignores it, but the
 *   test keeps it deterministic); `set.w rf0, wp0, 0` clears the accrued
 *   flags [4:0].  Reading rf0 uses `rf2rd` (rf0 is a legal source).
 *
 * rf10/rf11/rf12 are used as scratch for the instruction under test; they are
 * in the rf8-rf15 temporary range (contract-abi.md §1.4) and are declared as
 * clobbers so the compiler keeps nothing live there.
 */
#ifndef MINMAX_COMMON_H
#define MINMAX_COMMON_H

#include <stdio.h>

#define MM_RF0_FLAGS_MASK 0x1fULL
#define MM_RF0_RESET 0x7FF800007FC00000ULL

union mm_u64 {
	double d;
	unsigned long long u;
};

union mm_u32 {
	float f;
	unsigned int u;
};

static inline unsigned long long mm_rd_rf0(void)
{
	unsigned long long v;

	__asm__ __volatile__("rf2rd {%[o]}, {rf0}" : [o] "=r"(v));
	return v;
}

static inline void mm_clear_rf0(void)
{
	__asm__ __volatile__("set.w rf0, wp2, 0x0000");
	__asm__ __volatile__("set.w rf0, wp0, 0x0000");
}

/* ── instructions under test (immediates are mnemonics, not operands) ── */
static inline unsigned long long mm_ftmin(unsigned long long a,
					  unsigned long long b)
{
	unsigned long long o;

	__asm__ __volatile__("rd2rf {rf10}, {%[a]}\n\t"
			     "rd2rf {rf11}, {%[b]}\n\t"
			     "ftmin rf12, rf10, rf11\n\t"
			     "rf2rd {%[o]}, {rf12}"
			     : [o] "=r"(o)
			     : [a] "r"(a), [b] "r"(b)
			     : "rf10", "rf11", "rf12", "memory");
	return o;
}

static inline unsigned long long mm_ftmax(unsigned long long a,
					  unsigned long long b)
{
	unsigned long long o;

	__asm__ __volatile__("rd2rf {rf10}, {%[a]}\n\t"
			     "rd2rf {rf11}, {%[b]}\n\t"
			     "ftmax rf12, rf10, rf11\n\t"
			     "rf2rd {%[o]}, {rf12}"
			     : [o] "=r"(o)
			     : [a] "r"(a), [b] "r"(b)
			     : "rf10", "rf11", "rf12", "memory");
	return o;
}

static inline unsigned long long mm_fomin(unsigned long long a,
					  unsigned long long b)
{
	unsigned long long o;

	__asm__ __volatile__("rd2rf {rf10}, {%[a]}\n\t"
			     "rd2rf {rf11}, {%[b]}\n\t"
			     "fomin rf12, rf10, rf11\n\t"
			     "rf2rd {%[o]}, {rf12}"
			     : [o] "=r"(o)
			     : [a] "r"(a), [b] "r"(b)
			     : "rf10", "rf11", "rf12", "memory");
	return o;
}

static inline unsigned long long mm_fomax(unsigned long long a,
					  unsigned long long b)
{
	unsigned long long o;

	__asm__ __volatile__("rd2rf {rf10}, {%[a]}\n\t"
			     "rd2rf {rf11}, {%[b]}\n\t"
			     "fomax rf12, rf10, rf11\n\t"
			     "rf2rd {%[o]}, {rf12}"
			     : [o] "=r"(o)
			     : [a] "r"(a), [b] "r"(b)
			     : "rf10", "rf11", "rf12", "memory");
	return o;
}

/* dispatch by format / operation (the probe prints `op=min|max`) */
static inline unsigned long long mm_exec(const char *fmt, const char *op,
					 unsigned long long a,
					 unsigned long long b)
{
	if (fmt[1] == 't')
		return op[1] == 'i' ? mm_ftmin(a, b) : mm_ftmax(a, b);
	return op[1] == 'i' ? mm_fomin(a, b) : mm_fomax(a, b);
}

/* One observed instruction execution; prints the full rf0 before/after so
 * the oracle can also check the write mask. */
static inline void mm_obs(const char *group, const char *fmt, const char *op,
		   const char *kind, const char *label,
		   unsigned long long a, unsigned long long b)
{
	unsigned long long pre, out, post;

	mm_clear_rf0();
	pre = mm_rd_rf0();
	out = mm_exec(fmt, op, a, b);
	post = mm_rd_rf0();
	printf("OBS group=%s fmt=%s op=%s kind=%s label=%s a=%016llx b=%016llx "
	       "c=0000000000000000 out=%016llx pre=%016llx post=%016llx\n",
	       group, fmt, op, kind, label, a, b, out, pre, post);
}

/* Restore assertion: after clearing, rf0 must read back the reset value
 * (mode 0 + flags 0 + read-only qNaN fields). */
static inline void mm_restore(const char *group)
{
	unsigned long long got;

	mm_clear_rf0();
	got = mm_rd_rf0();
	printf("RESTORE group=%s expect=%016llx got=%016llx\n",
	       group, (unsigned long long)MM_RF0_RESET, got);
}

#endif /* MINMAX_COMMON_H */
