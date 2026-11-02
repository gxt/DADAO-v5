/*
 * TESTCASES-060t -- ftrnd/fornd value matrix (6 modes x value set) and the
 * C-level mapping of floor/ceil/trunc/round/nearbyint.
 *
 * Matrix inputs (per format): ±0.0, ±0.4, ±0.5, ±1.0, ±1.5, ±2.5, ±3.5, ±Inf,
 * qNaN, sNaN, the minimum subnormal and 2^53 (fo) / 2^24 (ft).  The five
 * static directions are executed with rf0[33:32] = RUP on purpose: a static
 * code must ignore the dynamic direction (SimRISC-07 §2.3).  The dynamic code
 * 0x20 runs under all four rf0 directions.
 *
 * The probe prints observations only; `tools/testcases/oracle_rnd.py` computes
 * every expected bit pattern / flag from the spec.  The label of each input is
 * printed too, so a mistyped literal in this file is a hard FAIL (the oracle
 * re-derives the bit pattern from the label) and never a silent pass.
 *
 * The `cmap_*` functions exist so the driver can assert, per function, that
 * the backend selected exactly one ftrnd/fornd and no libcall.
 */
#include "rnd_common.h"

union rnd_u64 {
	double d;
	unsigned long long u;
};

union rnd_u32 {
	float f;
	unsigned int u;
};

/* ── C-level mapping candidates (contract-fp.md §18: floor = 0x10,
 * ceil = 0x08, trunc = 0x04, round = 0x02, nearbyint = 0x20).  They are
 * global (not static) on purpose: the driver disassembles each symbol. ── */
double cmap_floor(double x) { return __builtin_floor(x); }
double cmap_ceil(double x) { return __builtin_ceil(x); }
double cmap_trunc(double x) { return __builtin_trunc(x); }
double cmap_round(double x) { return __builtin_round(x); }
double cmap_nearbyint(double x) { return __builtin_nearbyint(x); }

float cmap_floorf(float x) { return __builtin_floorf(x); }
float cmap_ceilf(float x) { return __builtin_ceilf(x); }
float cmap_truncf(float x) { return __builtin_truncf(x); }
float cmap_roundf(float x) { return __builtin_roundf(x); }
float cmap_nearbyintf(float x) { return __builtin_nearbyintf(x); }

/* ── input tables (labels are the oracle's contract) ── */
static const char *const fo_label[] = {
	"-0", "0", "0.4", "-0.4", "0.5", "-0.5", "1.0", "-1.0", "1.5", "-1.5",
	"2.5", "-2.5", "3.5", "-3.5", "inf", "-inf", "qnan", "snan", "minsub",
	"2^53",
};
static const char *const ft_label[] = {
	"-0", "0", "0.4", "-0.4", "0.5", "-0.5", "1.0", "-1.0", "1.5", "-1.5",
	"2.5", "-2.5", "3.5", "-3.5", "inf", "-inf", "qnan", "snan", "minsub",
	"2^24",
};
#define RND_NIN 20

static const unsigned static_modes[] = { 0x01, 0x02, 0x04, 0x08, 0x10 };
#define RND_NSTATIC 5

static void fo_inputs(unsigned long long *b)
{
	union rnd_u64 u;

	b[0] = 0x8000000000000000ULL;		/* -0 */
	b[1] = 0x0000000000000000ULL;		/* +0 */
	u.d = 0.4;
	b[2] = u.u;
	u.d = -0.4;
	b[3] = u.u;
	u.d = 0.5;
	b[4] = u.u;
	u.d = -0.5;
	b[5] = u.u;
	u.d = 1.0;
	b[6] = u.u;
	u.d = -1.0;
	b[7] = u.u;
	u.d = 1.5;
	b[8] = u.u;
	u.d = -1.5;
	b[9] = u.u;
	u.d = 2.5;
	b[10] = u.u;
	u.d = -2.5;
	b[11] = u.u;
	u.d = 3.5;
	b[12] = u.u;
	u.d = -3.5;
	b[13] = u.u;
	b[14] = 0x7ff0000000000000ULL;		/* +Inf */
	b[15] = 0xfff0000000000000ULL;		/* -Inf */
	b[16] = 0x7ff8000000000000ULL;		/* qNaN (canonical) */
	b[17] = 0x7ff0000000000001ULL;		/* sNaN */
	b[18] = 0x0000000000000001ULL;		/* minimum subnormal */
	u.d = 9007199254740992.0;		/* 2^53 */
	b[19] = u.u;
}

static void ft_inputs(unsigned long long *b)
{
	union rnd_u32 u;

	b[0] = 0x80000000ULL;			/* -0 */
	b[1] = 0x00000000ULL;			/* +0 */
	u.f = 0.4f;
	b[2] = u.u;
	u.f = -0.4f;
	b[3] = u.u;
	u.f = 0.5f;
	b[4] = u.u;
	u.f = -0.5f;
	b[5] = u.u;
	u.f = 1.0f;
	b[6] = u.u;
	u.f = -1.0f;
	b[7] = u.u;
	u.f = 1.5f;
	b[8] = u.u;
	u.f = -1.5f;
	b[9] = u.u;
	u.f = 2.5f;
	b[10] = u.u;
	u.f = -2.5f;
	b[11] = u.u;
	u.f = 3.5f;
	b[12] = u.u;
	u.f = -3.5f;
	b[13] = u.u;
	b[14] = 0x7f800000ULL;			/* +Inf */
	b[15] = 0xff800000ULL;			/* -Inf */
	b[16] = 0x7fc00000ULL;			/* qNaN (canonical) */
	b[17] = 0x7f800001ULL;			/* sNaN */
	b[18] = 0x00000001ULL;			/* minimum subnormal */
	u.f = 16777216.0f;			/* 2^24 */
	b[19] = u.u;
}

static void matrix(const char *fmt, const char *const *label,
		   const unsigned long long *in)
{
	unsigned m, rm, i;

	/* static directions, exercised while rf0[33:32] = RUP (3) */
	for (m = 0; m < RND_NSTATIC; m++)
		for (i = 0; i < RND_NIN; i++)
			rnd_case("MATRIX", fmt, static_modes[m], 3, label[i],
				 in[i]);
	/* dynamic code, all four rf0 directions */
	for (rm = 0; rm < 4; rm++)
		for (i = 0; i < RND_NIN; i++)
			rnd_case("MATRIX", fmt, 0x20, (int)rm, label[i], in[i]);
}

static void cmap(const char *fmt)
{
	static const char *const fn_name[] = {
		"floor", "ceil", "trunc", "round", "nearbyint",
	};
	static const char *const dbl_label[][2] = {
		{ "2.7", "-2.7" }, { "2.3", "-2.3" }, { "2.7", "-2.7" },
		{ "2.5", "-2.5" }, { "2.5", "-0.5" },
	};
	static const double dbl_val[][2] = {
		{ 2.7, -2.7 }, { 2.3, -2.3 }, { 2.7, -2.7 },
		{ 2.5, -2.5 }, { 2.5, -0.5 },
	};
	static const char *const flt_label[][2] = {
		{ "2.7", "-2.7" }, { "2.3", "-2.3" }, { "2.7", "-2.7" },
		{ "2.5", "-2.5" }, { "2.5", "-0.5" },
	};
	static const float flt_val[][2] = {
		{ 2.7f, -2.7f }, { 2.3f, -2.3f }, { 2.7f, -2.7f },
		{ 2.5f, -2.5f }, { 2.5f, -0.5f },
	};
	double (*const dbl_fn[])(double) = {
		cmap_floor, cmap_ceil, cmap_trunc, cmap_round, cmap_nearbyint,
	};
	float (*const flt_fn[])(float) = {
		cmap_floorf, cmap_ceilf, cmap_truncf, cmap_roundf,
		cmap_nearbyintf,
	};
	unsigned k, j;

	rnd_set_rmode(0);	/* nearbyint is judged under RNE */
	rnd_clear_flags();
	for (k = 0; k < 5; k++) {
		for (j = 0; j < 2; j++) {
			if (fmt[0] == 'f' && fmt[1] == 't') {
				volatile float v = flt_val[k][j];
				union rnd_u32 in, out;

				in.f = v;
				out.f = flt_fn[k](v);
				printf("CMAP fmt=%s fn=%s label=%s in=%08x "
				       "out=%08x\n", fmt, fn_name[k],
				       flt_label[k][j], in.u, out.u);
			} else {
				volatile double v = dbl_val[k][j];
				union rnd_u64 in, out;

				in.d = v;
				out.d = dbl_fn[k](v);
				printf("CMAP fmt=%s fn=%s label=%s in=%016llx "
				       "out=%016llx\n", fmt, fn_name[k],
				       dbl_label[k][j], in.u, out.u);
			}
		}
	}
}

int main(void)
{
	unsigned long long in[RND_NIN];
	unsigned long long initial = rnd_rd_rf0();

	printf("INIT rf0=%016llx\n", initial);

	fo_inputs(in);
	matrix("fo", fo_label, in);
	rnd_restore("matrix-fo", initial);

	ft_inputs(in);
	matrix("ft", ft_label, in);
	rnd_restore("matrix-ft", initial);

	cmap("fo");
	cmap("ft");
	rnd_restore("cmap", initial);
	return 0;
}
