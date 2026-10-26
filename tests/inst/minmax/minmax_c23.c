/*
 * TESTCASES-059t -- C23 minimum/maximum (NaN propagating) and the C-level
 * mappings of llvm.minnum / llvm.minimumnum.
 *
 *   c23_*   __builtin_elementwise_minimum/maximum -> llvm.minimum/maximum
 *           (any NaN input returns the canonical qNaN; -0 < +0 otherwise).
 *           The backend must expand this to fomin/fomax + a NaN select with
 *           NO libcall (LLVM-124t); the driver asserts that per symbol.
 *   num_*   __builtin_fminimum_num/fmaximum_num -> llvm.minimumnum
 *           (minimumNumber semantics: one NaN -> the number).
 *   cmap_*  C fmin/fmax/fminf/fmaxf -> llvm.minnum (same number semantics).
 *
 * The probe prints observations only; the oracle derives every expected bit
 * pattern and flag from the spec (value + NV/NX on two separate axes).
 */
#include "minmax_common.h"

#include <math.h>
#include <string.h>

/* ── exported functions (disassembled by the driver) ── */
double mm_c23_minimum_f64(double a, double b)
{
	return __builtin_elementwise_minimum(a, b);
}

double mm_c23_maximum_f64(double a, double b)
{
	return __builtin_elementwise_maximum(a, b);
}

float mm_c23_minimum_f32(float a, float b)
{
	return __builtin_elementwise_minimum(a, b);
}

float mm_c23_maximum_f32(float a, float b)
{
	return __builtin_elementwise_maximum(a, b);
}

double mm_c23_minimum_num_f64(double a, double b)
{
	return __builtin_fminimum_num(a, b);
}

double mm_c23_maximum_num_f64(double a, double b)
{
	return __builtin_fmaximum_num(a, b);
}

float mm_c23_minimum_num_f32(float a, float b)
{
	return __builtin_fminimum_numf(a, b);
}

float mm_c23_maximum_num_f32(float a, float b)
{
	return __builtin_fmaximum_numf(a, b);
}

double mm_c_fmin(double a, double b) { return fmin(a, b); }
double mm_c_fmax(double a, double b) { return fmax(a, b); }
float mm_c_fminf(float a, float b) { return fminf(a, b); }
float mm_c_fmaxf(float a, float b) { return fmaxf(a, b); }

/* ── function ids: group, operation and expected NaN rule ── */
enum {
	FN_C23_MIN, FN_C23_MAX,
	FN_NUM_MIN, FN_NUM_MAX,
	FN_CMAP_MIN, FN_CMAP_MAX,
	FN_COUNT
};

static const char *const FN_GROUP[FN_COUNT] = {
	"c23", "c23", "num", "num", "cmap", "cmap",
};
static const char *const FN_OP[FN_COUNT] = {
	"min", "max", "min", "max", "min", "max",
};
static const char *const FN_KIND[FN_COUNT] = {
	"propagate", "propagate", "number", "number", "number", "number",
};

static unsigned long long call_f64(int fn, unsigned long long a,
				   unsigned long long b)
{
	union mm_u64 x, y, o;

	x.u = a;
	y.u = b;
	switch (fn) {
	case FN_C23_MIN:  o.d = mm_c23_minimum_f64(x.d, y.d); break;
	case FN_C23_MAX:  o.d = mm_c23_maximum_f64(x.d, y.d); break;
	case FN_NUM_MIN:  o.d = mm_c23_minimum_num_f64(x.d, y.d); break;
	case FN_NUM_MAX:  o.d = mm_c23_maximum_num_f64(x.d, y.d); break;
	case FN_CMAP_MIN: o.d = mm_c_fmin(x.d, y.d); break;
	case FN_CMAP_MAX: o.d = mm_c_fmax(x.d, y.d); break;
	default:          o.u = 0; break;
	}
	return o.u;
}

static unsigned long long call_f32(int fn, unsigned long long a,
				   unsigned long long b)
{
	union mm_u32 x, y, o;

	x.u = (unsigned int)a;
	y.u = (unsigned int)b;
	switch (fn) {
	case FN_C23_MIN:  o.f = mm_c23_minimum_f32(x.f, y.f); break;
	case FN_C23_MAX:  o.f = mm_c23_maximum_f32(x.f, y.f); break;
	case FN_NUM_MIN:  o.f = mm_c23_minimum_num_f32(x.f, y.f); break;
	case FN_NUM_MAX:  o.f = mm_c23_maximum_num_f32(x.f, y.f); break;
	case FN_CMAP_MIN: o.f = mm_c_fminf(x.f, y.f); break;
	case FN_CMAP_MAX: o.f = mm_c_fmaxf(x.f, y.f); break;
	default:          o.u = 0; break;
	}
	return o.u;
}

static const struct {
	const char *name;
	unsigned long long ft;
	unsigned long long fo;
} VALUES[] = {
	{ "0",       0x00000000ULL, 0x0000000000000000ULL },
	{ "-0",      0x80000000ULL, 0x8000000000000000ULL },
	{ "1.0",     0x3F800000ULL, 0x3FF0000000000000ULL },
	{ "-1.0",    0xBF800000ULL, 0xBFF0000000000000ULL },
	{ "2.0",     0x40000000ULL, 0x4000000000000000ULL },
	{ "-2.0",    0xC0000000ULL, 0xC000000000000000ULL },
	{ "inf",     0x7F800000ULL, 0x7FF0000000000000ULL },
	{ "-inf",    0xFF800000ULL, 0xFFF0000000000000ULL },
	{ "qnan",    0x7FC00000ULL, 0x7FF8000000000000ULL },
	{ "-qnan",   0xFFC00000ULL, 0xFFF8000000000000ULL },
	{ "snan",    0x7F800001ULL, 0x7FF0000000000001ULL },
	{ "minsub",  0x00000001ULL, 0x0000000000000001ULL },
	{ "maxsub",  0x007FFFFFULL, 0x000FFFFFFFFFFFFFULL },
};
#define MM_NVALUES ((int)(sizeof(VALUES) / sizeof(VALUES[0])))

static const struct {
	const char *name;
	const char *a;
	const char *b;
} PAIRS[] = {
	{ "ordered_p1_p2",       "1.0",   "2.0" },
	{ "ordered_m2_p1",       "-2.0",  "1.0" },
	{ "ordered_p2_m1",       "2.0",   "-1.0" },
	{ "zeros_p0_m0",         "0",     "-0" },
	{ "zeros_m0_p0",         "-0",    "0" },
	{ "zeros_p0_p0",         "0",     "0" },
	{ "zeros_m0_m0",         "-0",    "-0" },
	{ "equal_p1_p1",         "1.0",   "1.0" },
	{ "equal_m1_m1",         "-1.0",  "-1.0" },
	{ "single_qnan_left",    "qnan",  "1.0" },
	{ "single_qnan_right",   "1.0",   "qnan" },
	{ "single_mqnan_left",   "-qnan", "1.0" },
	{ "single_snan_left",    "snan",  "1.0" },
	{ "single_snan_right",   "1.0",   "snan" },
	{ "double_qnan",         "qnan",  "qnan" },
	{ "double_mqnan_qnan",   "-qnan", "qnan" },
	{ "double_snan_qnan",    "snan",  "qnan" },
	{ "double_qnan_snan",    "qnan",  "snan" },
	{ "inf_pinf_p1",         "inf",   "1.0" },
	{ "inf_minf_pinf",       "-inf",  "inf" },
	{ "sub_vs_p0",           "minsub", "0" },
	{ "sub_pair",            "minsub", "maxsub" },
};
#define MM_NPAIRS ((int)(sizeof(PAIRS) / sizeof(PAIRS[0])))

static unsigned long long value_bits(const char *fmt, const char *name)
{
	int i;

	for (i = 0; i < MM_NVALUES; i++)
		if (strcmp(VALUES[i].name, name) == 0)
			return (fmt[1] == 't') ? VALUES[i].ft : VALUES[i].fo;
	printf("UNKNOWN value=%s fmt=%s\n", name, fmt);
	return 0;
}

int main(void)
{
	const char *fmts[] = { "ft", "fo" };
	unsigned long long initial;
	int f, fn, p;

	initial = mm_rd_rf0();
	printf("INIT rf0=%016llx\n", initial);

	for (f = 0; f < 2; f++) {
		for (fn = 0; fn < FN_COUNT; fn++) {
			for (p = 0; p < MM_NPAIRS; p++) {
				unsigned long long a, b, pre, out, post;

				a = value_bits(fmts[f], PAIRS[p].a);
				b = value_bits(fmts[f], PAIRS[p].b);
				mm_clear_rf0();
				pre = mm_rd_rf0();
				out = (f == 0) ? call_f32(fn, a, b)
					       : call_f64(fn, a, b);
				post = mm_rd_rf0();
				printf("OBS group=%s fmt=%s op=%s kind=%s "
				       "label=%s a=%016llx b=%016llx "
				       "c=0000000000000000 out=%016llx "
				       "pre=%016llx post=%016llx\n",
				       FN_GROUP[fn], fmts[f], FN_OP[fn],
				       FN_KIND[fn], PAIRS[p].name,
				       a, b, out, pre, post);
			}
		}
	}
	mm_restore("c23");
	return 0;
}
