/*
 * TESTCASES-058t -- ftfma/fofma instruction-level matrix (single rounding,
 * special values, rf0 flags, the four rounding modes).
 *
 * Every boundary rule of spec/SimRISC-07 §2.5 / contract-fp.md §20 is
 * exercised per format:
 *   disc      the single-rounding discriminators: the fused `fma()` value
 *             (C path), the asm value (`discasm`) and the two-step
 *             `round(a*b)+c` value, all in one run;
 *   special   qNaN / sNaN (every position), 0xInf with qNaN addend (NV),
 *             Inf+(-Inf) (NV), same-sign Inf, Inf addend, exact-zero sign
 *             under RNE/RDN, overflow (OF|NX) / RZ (max finite), exact and
 *             inexact subnormals, underflow to zero, NX, ties under all four
 *             rf0[33:32] directions (positive and negative values);
 *   cpath     the C library name `fma()`/`fmaf()` end-to-end;
 *   contract  `acc += a*b` (frontend contraction to llvm.fmuladd).
 *
 * The probe prints observations only; tools/testcases/oracle_fma.py computes
 * every expected bit pattern and flag from the spec and re-derives the
 * operands from the labels, so a mistyped literal is a hard FAIL.
 */
#include "fma_common.h"

struct fma_case {
	const char *label;
	const char *fmt;
	unsigned long long a;
	unsigned long long b;
	unsigned long long c;
	int rm;
};

static const struct fma_case DISC[] = {
	{ "ft_spec", "ft", 0x000000003F800001ULL, 0x000000003F7FFFFEULL, 0x00000000BF800000ULL, 0 },
	{ "ft_square", "ft", 0x000000003F800001ULL, 0x000000003F800001ULL, 0x00000000BF800002ULL, 0 },
	{ "ft_both", "ft", 0x000000003F800001ULL, 0x000000003F800001ULL, 0x00000000BF800001ULL, 0 },
	{ "fo_spec", "fo", 0x3FF0000000000001ULL, 0x3FEFFFFFFFFFFFFEULL, 0xBFF0000000000000ULL, 0 },
	{ "fo_square", "fo", 0x3FF0000000000001ULL, 0x3FF0000000000001ULL, 0xBFF0000000000002ULL, 0 },
	{ "fo_both", "fo", 0x3FEFFFFFFFFFFFF8ULL, 0x3FEFFFFFFFFFFFF8ULL, 0xBFF0000000000000ULL, 0 },
};
#define N_DISC ((int)(sizeof(DISC) / sizeof(DISC[0])))

static const struct fma_case SPECIAL[] = {
	{ "qnan_a", "ft", 0x000000007FC00000ULL, 0x000000003F800000ULL, 0x000000003F800000ULL, 0 },
	{ "qnan_a", "fo", 0x7FF8000000000000ULL, 0x3FF0000000000000ULL, 0x3FF0000000000000ULL, 0 },
	{ "qnan_c", "ft", 0x000000003F800000ULL, 0x000000003F800000ULL, 0x000000007FC00000ULL, 0 },
	{ "qnan_c", "fo", 0x3FF0000000000000ULL, 0x3FF0000000000000ULL, 0x7FF8000000000000ULL, 0 },
	{ "snan_a", "ft", 0x000000007F800001ULL, 0x000000003F800000ULL, 0x000000003F800000ULL, 0 },
	{ "snan_a", "fo", 0x7FF0000000000001ULL, 0x3FF0000000000000ULL, 0x3FF0000000000000ULL, 0 },
	{ "snan_c", "ft", 0x000000003F800000ULL, 0x000000003F800000ULL, 0x000000007F800001ULL, 0 },
	{ "snan_c", "fo", 0x3FF0000000000000ULL, 0x3FF0000000000000ULL, 0x7FF0000000000001ULL, 0 },
	{ "zeroxinf_qnan", "ft", 0x0000000000000000ULL, 0x000000007F800000ULL, 0x000000007FC00000ULL, 0 },
	{ "zeroxinf_qnan", "fo", 0x0000000000000000ULL, 0x7FF0000000000000ULL, 0x7FF8000000000000ULL, 0 },
	{ "inf_minus_inf", "ft", 0x000000007F800000ULL, 0x000000003F800000ULL, 0x00000000FF800000ULL, 0 },
	{ "inf_minus_inf", "fo", 0x7FF0000000000000ULL, 0x3FF0000000000000ULL, 0xFFF0000000000000ULL, 0 },
	{ "inf_same", "ft", 0x000000007F800000ULL, 0x0000000040000000ULL, 0x000000007F800000ULL, 0 },
	{ "inf_same", "fo", 0x7FF0000000000000ULL, 0x4000000000000000ULL, 0x7FF0000000000000ULL, 0 },
	{ "inf_c", "ft", 0x000000003F800000ULL, 0x0000000040000000ULL, 0x00000000FF800000ULL, 0 },
	{ "inf_c", "fo", 0x3FF0000000000000ULL, 0x4000000000000000ULL, 0xFFF0000000000000ULL, 0 },
	{ "zero_rne", "ft", 0x000000003F800000ULL, 0x000000003F800000ULL, 0x00000000BF800000ULL, 0 },
	{ "zero_rne", "fo", 0x3FF0000000000000ULL, 0x3FF0000000000000ULL, 0xBFF0000000000000ULL, 0 },
	{ "zero_rdn", "ft", 0x000000003F800000ULL, 0x000000003F800000ULL, 0x00000000BF800000ULL, 2 },
	{ "zero_rdn", "fo", 0x3FF0000000000000ULL, 0x3FF0000000000000ULL, 0xBFF0000000000000ULL, 2 },
	{ "zeroprod_negzero", "ft", 0x0000000000000000ULL, 0x000000003F800000ULL, 0x0000000080000000ULL, 2 },
	{ "zeroprod_negzero", "fo", 0x0000000000000000ULL, 0x3FF0000000000000ULL, 0x8000000000000000ULL, 2 },
	{ "ovf_rne", "ft", 0x000000007F7FFFFFULL, 0x0000000040000000ULL, 0x0000000000000000ULL, 0 },
	{ "ovf_rne", "fo", 0x7FEFFFFFFFFFFFFFULL, 0x4000000000000000ULL, 0x0000000000000000ULL, 0 },
	{ "ovf_rtz", "ft", 0x000000007F7FFFFFULL, 0x0000000040000000ULL, 0x0000000000000000ULL, 1 },
	{ "ovf_rtz", "fo", 0x7FEFFFFFFFFFFFFFULL, 0x4000000000000000ULL, 0x0000000000000000ULL, 1 },
	{ "sub_exact", "ft", 0x0000000000000001ULL, 0x000000003F800000ULL, 0x0000000000000000ULL, 0 },
	{ "sub_exact", "fo", 0x0000000000000001ULL, 0x3FF0000000000000ULL, 0x0000000000000000ULL, 0 },
	{ "sub_inexact", "ft", 0x0000000000000001ULL, 0x000000003FC00000ULL, 0x0000000000000000ULL, 0 },
	{ "sub_inexact", "fo", 0x0000000000000001ULL, 0x3FF8000000000000ULL, 0x0000000000000000ULL, 0 },
	{ "sub_to_zero", "ft", 0x0000000000000001ULL, 0x0000000000000001ULL, 0x000000003F800000ULL, 0 },
	{ "sub_to_zero", "fo", 0x0000000000000001ULL, 0x0000000000000001ULL, 0x3FF0000000000000ULL, 0 },
	{ "nx_normal", "ft", 0x000000003F800001ULL, 0x000000003F800001ULL, 0x0000000000000000ULL, 0 },
	{ "nx_normal", "fo", 0x3FF0000000000001ULL, 0x3FF0000000000001ULL, 0x0000000000000000ULL, 0 },
	{ "tie_rne", "ft", 0x000000003F800001ULL, 0x000000003F800000ULL, 0x0000000033800000ULL, 0 },
	{ "tie_rne", "fo", 0x3FF0000000000001ULL, 0x3FF0000000000000ULL, 0x3CA0000000000000ULL, 0 },
	{ "tie_rtz", "ft", 0x000000003F800001ULL, 0x000000003F800000ULL, 0x0000000033800000ULL, 1 },
	{ "tie_rtz", "fo", 0x3FF0000000000001ULL, 0x3FF0000000000000ULL, 0x3CA0000000000000ULL, 1 },
	{ "tie_rdn", "ft", 0x000000003F800001ULL, 0x000000003F800000ULL, 0x0000000033800000ULL, 2 },
	{ "tie_rdn", "fo", 0x3FF0000000000001ULL, 0x3FF0000000000000ULL, 0x3CA0000000000000ULL, 2 },
	{ "tie_rup", "ft", 0x000000003F800001ULL, 0x000000003F800000ULL, 0x0000000033800000ULL, 3 },
	{ "tie_rup", "fo", 0x3FF0000000000001ULL, 0x3FF0000000000000ULL, 0x3CA0000000000000ULL, 3 },
	{ "negtie_rdn", "ft", 0x00000000BF800001ULL, 0x000000003F800000ULL, 0x00000000B3800000ULL, 2 },
	{ "negtie_rdn", "fo", 0xBFF0000000000001ULL, 0x3FF0000000000000ULL, 0xBCA0000000000000ULL, 2 },
	{ "negtie_rup", "ft", 0x00000000BF800001ULL, 0x000000003F800000ULL, 0x00000000B3800000ULL, 3 },
	{ "negtie_rup", "fo", 0xBFF0000000000001ULL, 0x3FF0000000000000ULL, 0xBCA0000000000000ULL, 3 },
};
#define N_SPECIAL ((int)(sizeof(SPECIAL) / sizeof(SPECIAL[0])))

static const struct fma_case CPATH[] = {
	{ "c_disc_ft", "ft", 0x000000003F800001ULL, 0x000000003F800001ULL, 0x00000000BF800000ULL, 0 },
	{ "c_basic_ft", "ft", 0x000000003FC00000ULL, 0x0000000040000000ULL, 0x00000000BF800000ULL, 0 },
	{ "c_disc_fo", "fo", 0x3FF0000000000001ULL, 0x3FF0000000000001ULL, 0xBFF0000000000002ULL, 0 },
	{ "c_basic_fo", "fo", 0x3FF8000000000000ULL, 0x4000000000000000ULL, 0xBFF0000000000000ULL, 0 },
};
#define N_CPATH ((int)(sizeof(CPATH) / sizeof(CPATH[0])))

static const struct fma_case CONTRACT[] = {
	{ "contract_disc_ft", "ft", 0x000000003F800001ULL, 0x000000003F800001ULL, 0x00000000BF800002ULL, 0 },
	{ "contract_basic_ft", "ft", 0x0000000040000000ULL, 0x0000000040400000ULL, 0x0000000041200000ULL, 0 },
	{ "contract_disc_fo", "fo", 0x3FF0000000000001ULL, 0x3FF0000000000001ULL, 0xBFF0000000000002ULL, 0 },
	{ "contract_basic_fo", "fo", 0x4000000000000000ULL, 0x4008000000000000ULL, 0x4024000000000000ULL, 0 },
};
#define N_CONTRACT ((int)(sizeof(CONTRACT) / sizeof(CONTRACT[0])))

/* The C path through dedicated (noinline) symbols, plus a two-step control
 * symbol.  The driver asserts the instruction mix of each symbol: sel_fma must
 * hold one fofma + one ftfma and no fomul/foadd/rf2rf, while sel_two_step must
 * hold fomul+foadd (so a silent "0 two-step instructions" counter cannot pass
 * for the right reason). */
volatile unsigned long long fma_sink;

__attribute__((noinline))
static unsigned long long sel_fma(const char *fmt, unsigned long long a,
				  unsigned long long b, unsigned long long c)
{
	a = fma_hide(a);
	b = fma_hide(b);
	c = fma_hide(c);
	if (fmt[1] == 't')
		return fma_bits_f(fmaf(fma_val_f(a), fma_val_f(b),
				       fma_val_f(c)));
	return fma_bits_d(fma(fma_val_d(a), fma_val_d(b), fma_val_d(c)));
}

__attribute__((noinline))
static unsigned long long sel_two_step(const char *fmt, unsigned long long a,
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

int main(void)
{
	unsigned long long init = fma_rd_rf0();
	int i;

	printf("INIT rf0=%016llx\n", init);

	for (i = 0; i < N_DISC; i++) {
		fma_obs_disc(DISC[i].label, DISC[i].fmt, DISC[i].a, DISC[i].b,
			     DISC[i].c, DISC[i].rm);
		fma_obs_asm("discasm", DISC[i].fmt, DISC[i].label, DISC[i].a,
			    DISC[i].b, DISC[i].c, DISC[i].rm);
	}
	for (i = 0; i < N_SPECIAL; i++)
		fma_obs_asm("special", SPECIAL[i].fmt, SPECIAL[i].label,
			    SPECIAL[i].a, SPECIAL[i].b, SPECIAL[i].c,
			    SPECIAL[i].rm);
	for (i = 0; i < N_CPATH; i++)
		fma_obs_c("cpath", CPATH[i].fmt, CPATH[i].label, CPATH[i].a,
			  CPATH[i].b, CPATH[i].c, CPATH[i].rm);
	for (i = 0; i < N_CONTRACT; i++)
		fma_obs_contract(CONTRACT[i].label, CONTRACT[i].fmt,
				 CONTRACT[i].a, CONTRACT[i].b, CONTRACT[i].c,
				 CONTRACT[i].rm);

	for (i = 0; i < N_DISC; i++) {
		unsigned long long pre, out, post, step;

		fma_set_mode(DISC[i].rm);
		fma_clear_flags();
		pre = fma_rd_rf0();
		out = sel_fma(DISC[i].fmt, DISC[i].a, DISC[i].b, DISC[i].c);
		post = fma_rd_rf0();
		step = fma_two_step(DISC[i].fmt, DISC[i].a, DISC[i].b,
				    DISC[i].c);
		printf("OBS group=csel fmt=%s label=%s a=%016llx b=%016llx "
		       "c=%016llx out=%016llx step=%016llx pre=%016llx "
		       "post=%016llx rm=%d\n", DISC[i].fmt, DISC[i].label,
		       DISC[i].a, DISC[i].b, DISC[i].c, out, step, pre, post,
		       (int)((pre >> 32) & 3));
		/* Keep the control symbol alive and executed. */
		fma_sink += sel_two_step(DISC[i].fmt, DISC[i].a, DISC[i].b,
					 DISC[i].c);
	}

	fma_restore("edges", init);
	return 0;
}
