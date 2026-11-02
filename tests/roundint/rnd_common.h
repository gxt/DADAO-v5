/*
 * TESTCASES-060t shared probe support: ftrnd/fornd (roundToIntegral).
 *
 * Spec sources (semantics, never QEMU/LLVM output):
 *   spec/SimRISC-07 §2.3  -- six one-hot immu6 modes, rf0[33:32] only for 0x20
 *   .tao/contracts/contract-fp.md §18 -- frozen roundint contract
 *   spec/SimRISC-00 §浮点状态寄存器 -- rf0 write mask: only [33:32] and [4:0]
 *
 * The probes only OBSERVE: every expected value is computed by
 * tools/testcases/oracle_rnd.py from the spec.
 *
 * rf0 programming uses `set.w` (SimRISC-03 immediate constant):
 *   `set.w rf0, wp2, <imm>` programs wyde 2, i.e. rf0[47:32] -> [33:32] is the
 *   rounding mode (the rest of that wyde is SBZ and ignored by the write mask);
 *   `set.w rf0, wp0, 0` clears wyde 0, i.e. the accrued flags [4:0].
 * Reading rf0 uses `rf2rd` (rf0 is legal as a source).
 *
 * rf10/rf11 are used as scratch for the instruction under test; both are in
 * the rf8-rf15 temporary range (contract-abi.md §1.4), and are declared as
 * clobbers so the compiler keeps nothing live there.
 */
#ifndef RND_COMMON_H
#define RND_COMMON_H

#include <stdio.h>

#define RND_RF0_RM_SHIFT 32
#define RND_RF0_FLAGS_MASK 0x1fULL

/* ftrnd (ft, p = 24) / fornd (fo, p = 53): destination in rf11, source rf10.
 * `immu6` must be a literal -> one asm statement per code (the RND_SWITCH
 * macro below keeps the six codes in ONE place). */
#define RND_SWITCH(F)                                                       \
	case 0x01: F("1"); break;                                           \
	case 0x02: F("2"); break;                                           \
	case 0x04: F("4"); break;                                           \
	case 0x08: F("8"); break;                                           \
	case 0x10: F("16"); break;                                          \
	case 0x20: F("32"); break;

static inline unsigned long long rnd_rd_rf0(void)
{
	unsigned long long v;

	__asm__ __volatile__("rf2rd {%[o]}, {rf0}" : [o] "=r"(v));
	return v;
}

static inline void rnd_set_rmode(int rm)
{
	switch (rm & 3) {
	case 0: __asm__ __volatile__("set.w rf0, wp2, 0x0000"); break;
	case 1: __asm__ __volatile__("set.w rf0, wp2, 0x0001"); break;
	case 2: __asm__ __volatile__("set.w rf0, wp2, 0x0002"); break;
	default: __asm__ __volatile__("set.w rf0, wp2, 0x0003"); break;
	}
}

static inline void rnd_clear_flags(void)
{
	__asm__ __volatile__("set.w rf0, wp0, 0x0000");
}

static inline unsigned long long rnd_fo(unsigned long long in, unsigned mode)
{
	unsigned long long out = 0;

#define FO_ASM(code)                                                       \
	__asm__ __volatile__("rd2rf {rf10}, {%[i]}\n\t"                    \
			     "fornd rf11, rf10, " code "\n\t"              \
			     "rf2rd {%[o]}, {rf11}"                        \
			     : [o] "=r"(out)                               \
			     : [i] "r"(in)                                 \
			     : "rf10", "rf11", "memory")
	switch (mode) {
		RND_SWITCH(FO_ASM)
	default:
		break;
	}
#undef FO_ASM
	return out;
}

static inline unsigned long long rnd_ft(unsigned long long in, unsigned mode)
{
	unsigned long long out = 0;

#define FT_ASM(code)                                                       \
	__asm__ __volatile__("rd2rf {rf10}, {%[i]}\n\t"                    \
			     "ftrnd rf11, rf10, " code "\n\t"              \
			     "rf2rd {%[o]}, {rf11}"                        \
			     : [o] "=r"(out)                               \
			     : [i] "r"(in)                                 \
			     : "rf10", "rf11", "memory")
	switch (mode) {
		RND_SWITCH(FT_ASM)
	default:
		break;
	}
#undef FT_ASM
	return out;
}

/* One observed instruction execution: clear the flags, program rf0[33:32],
 * read rf0 before/after, print the full rf0 so the harness can also check the
 * write mask ([63:34] and [21:5] must never change). */
static void rnd_case(const char *group, const char *fmt, unsigned mode,
		     int rmode, const char *label, unsigned long long in)
{
	unsigned long long pre, out, post;

	rnd_set_rmode(rmode);
	rnd_clear_flags();
	pre = rnd_rd_rf0();
	out = (fmt[0] == 'f' && fmt[1] == 't') ? rnd_ft(in, mode)
					      : rnd_fo(in, mode);
	post = rnd_rd_rf0();
	printf("%s fmt=%s mode=0x%02x label=%s in=%016llx out=%016llx "
	       "pre=%016llx post=%016llx rm=%llu\n",
	       group, fmt, mode, label, in, out, pre, post,
	       (pre >> RND_RF0_RM_SHIFT) & 3);
}

/* Restore rf0 to the value captured at entry (mode kept, flags cleared) and
 * assert the read-back, so one group cannot pollute the next. */
static void rnd_restore(const char *group, unsigned long long initial)
{
	unsigned long long want = initial & ~RND_RF0_FLAGS_MASK;
	unsigned long long got;

	rnd_set_rmode((int)((initial >> RND_RF0_RM_SHIFT) & 3));
	rnd_clear_flags();
	got = rnd_rd_rf0();
	printf("RESTORE group=%s expect=%016llx got=%016llx\n", group, want, got);
}

#endif /* RND_COMMON_H */
