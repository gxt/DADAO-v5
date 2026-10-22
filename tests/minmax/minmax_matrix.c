/*
 * TESTCASES-059t -- ftmin/ftmax/fomin/fomax semantic matrix.
 *
 * Every boundary rule of spec/SimRISC-07 §2.4 is exercised per format and per
 * operation: ordered (both directions), equal same-sign, the four ±0
 * combinations, one qNaN (left/right), one -qNaN, one sNaN (left/right), two
 * NaNs (q/q, -q/q, s/q, q/s), ±Inf and subnormals.  Each observation prints
 * the result *and* the full rf0 before/after, so the oracle asserts the value
 * and the flags (NV/NX) on two separate axes.
 *
 * The probe prints observations only; `tools/testcases/oracle_minmax.py`
 * computes every expected bit pattern and flag from the spec.  The pair label
 * is printed too, and the oracle re-derives both operands from it: a mistyped
 * literal is a hard FAIL, never a silent pass.
 */
#include "minmax_common.h"

#include <string.h>

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
	const char *ops[] = { "min", "max" };
	unsigned long long initial;
	int f, o, p;

	initial = mm_rd_rf0();
	printf("INIT rf0=%016llx\n", initial);

	for (f = 0; f < 2; f++) {
		for (o = 0; o < 2; o++) {
			for (p = 0; p < MM_NPAIRS; p++) {
				unsigned long long a, b;

				a = value_bits(fmts[f], PAIRS[p].a);
				b = value_bits(fmts[f], PAIRS[p].b);
				mm_obs("matrix", fmts[f], ops[o], "number",
				       PAIRS[p].name, a, b);
			}
		}
	}
	mm_restore("matrix");
	return 0;
}
