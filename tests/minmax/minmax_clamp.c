/*
 * TESTCASES-059t -- clamp integration: `min(max(x, lo), hi)` in the two
 * forms the backend can emit, plus an integer min/max control.
 *
 *   CLAMP   a 1k-iteration loop over IEEE boundary values (both formats),
 *           using the C `fmin`/`fmax` builtins (minimumNumber semantics);
 *   MAT4    4x4 element-wise min/max with a NaN row and a ±0/Inf row;
 *   INTCMP  `min(max(x,lo),hi)` on exactly representable integers, compared
 *           with the integer min/max control (same clamp shape, no FP path).
 *
 * The probe prints observations only; `tools/testcases/oracle_minmax.py`
 * derives the expected value and flags (NV is sticky across the two
 * instructions; NX is never set by min/max).
 */
#include "minmax_common.h"

#include <math.h>

/* the symbols are disassembled by the driver: one fomax/fomin pair each */
__attribute__((noinline)) static double mm_clamp_f64(double x, double lo,
						     double hi)
{
	return fmin(fmax(x, lo), hi);
}

__attribute__((noinline)) static float mm_clamp_f32(float x, float lo,
						    float hi)
{
	return fminf(fmaxf(x, lo), hi);
}

static void clamp_obs(const char *fmt, const char *label,
		      unsigned long long a, unsigned long long b,
		      unsigned long long c)
{
	unsigned long long pre, out, post;

	mm_clear_rf0();
	pre = mm_rd_rf0();
	if (fmt[1] == 't') {
		union mm_u32 x, lo, hi, o;

		x.u = (unsigned int)a;
		lo.u = (unsigned int)b;
		hi.u = (unsigned int)c;
		o.f = mm_clamp_f32(x.f, lo.f, hi.f);
		out = o.u;
	} else {
		union mm_u64 x, lo, hi, o;

		x.u = a;
		lo.u = b;
		hi.u = c;
		o.d = mm_clamp_f64(x.d, lo.d, hi.d);
		out = o.u;
	}
	post = mm_rd_rf0();
	printf("OBS group=clamp fmt=%s op=clamp kind=number label=%s "
	       "a=%016llx b=%016llx c=%016llx out=%016llx pre=%016llx "
	       "post=%016llx\n",
	       fmt, label, a, b, c, out, pre, post);
}

static unsigned long long lcg_state = 0x9E3779B97F4A7C15ULL;

static unsigned long long lcg_next(void)
{
	lcg_state = lcg_state * 6364136223846793005ULL + 1442695040888963407ULL;
	return lcg_state;
}

/* A finite random value: exponent kept in a safe range, random sign/mantissa. */
static unsigned long long random_bits(const char *fmt)
{
	unsigned long long r = lcg_next();

	if (fmt[1] == 't')
		return ((r & 0x80000000ULL) |
			((unsigned long long)(100 + (r % 40)) << 23) |
			(r & 0x007FFFFFULL));
	return ((r & 0x8000000000000000ULL) |
		((unsigned long long)(900 + (r % 120)) << 52) |
		(r & 0x000FFFFFFFFFFFFFULL));
}

#define MM_CLAMP_N 500           /* per format -> 1000 clamp iterations */

int main(void)
{
	static const unsigned long long ft_special[16] = {
		0x00000000ULL, 0x80000000ULL,             /* +0, -0 */
		0x7FC00000ULL, 0x7F800001ULL,             /* qNaN, sNaN */
		0x7F800000ULL, 0xFF800000ULL,             /* +Inf, -Inf */
		0x00000001ULL, 0x007FFFFFULL,             /* subnormals */
		0x3F800000ULL, 0xBF800000ULL,             /* ±1 */
		0x40000000ULL, 0xC0000000ULL,             /* ±2 */
		0x7FC00001ULL, 0xFF800002ULL,             /* payload qNaN/sNaN */
		0x3F000000ULL, 0xBF000000ULL,             /* ±0.5 */
	};
	static const unsigned long long fo_special[16] = {
		0x0000000000000000ULL, 0x8000000000000000ULL,
		0x7FF8000000000000ULL, 0x7FF0000000000001ULL,
		0x7FF0000000000000ULL, 0xFFF0000000000000ULL,
		0x0000000000000001ULL, 0x000FFFFFFFFFFFFFULL,
		0x3FF0000000000000ULL, 0xBFF0000000000000ULL,
		0x4000000000000000ULL, 0xC000000000000000ULL,
		0x7FF8000000000001ULL, 0x7FF0000000000002ULL,
		0x3FE0000000000000ULL, 0xBFE0000000000000ULL,
	};
	static const unsigned long long ft_lo[8] = {
		0xC0000000ULL, 0x80000000ULL, 0x00000000ULL, 0xBF800000ULL,
		0x7FC00000ULL, 0xFF800000ULL, 0x00000001ULL, 0xC0400000ULL,
	};
	static const unsigned long long ft_hi[8] = {
		0x40000000ULL, 0x00000000ULL, 0x40400000ULL, 0x7F800000ULL,
		0x7F800001ULL, 0x3F800000ULL, 0x007FFFFFULL, 0x40800000ULL,
	};
	static const unsigned long long fo_lo[8] = {
		0xC000000000000000ULL, 0x8000000000000000ULL,
		0x0000000000000000ULL, 0xBFF0000000000000ULL,
		0x7FF8000000000000ULL, 0xFFF0000000000000ULL,
		0x0000000000000001ULL, 0xC008000000000000ULL,
	};
	static const unsigned long long fo_hi[8] = {
		0x4000000000000000ULL, 0x0000000000000000ULL,
		0x4008000000000000ULL, 0x7FF0000000000000ULL,
		0x7FF0000000000001ULL, 0x3FF0000000000000ULL,
		0x000FFFFFFFFFFFFFULL, 0x4010000000000000ULL,
	};
	static const unsigned long long mat4_a[2][16] = {
		{
			0x3F800000ULL, 0x40000000ULL, 0x40400000ULL, 0x40800000ULL,
			0xBF800000ULL, 0xC0000000ULL, 0xC0400000ULL, 0xC0800000ULL,
			0x00000000ULL, 0x80000000ULL, 0x7F800000ULL, 0xFF800000ULL,
			0x7FC00000ULL, 0x7F800001ULL, 0x3F800000ULL, 0x80000000ULL,
		},
		{
			0x3FF0000000000000ULL, 0x4000000000000000ULL,
			0x4008000000000000ULL, 0x4010000000000000ULL,
			0xBFF0000000000000ULL, 0xC000000000000000ULL,
			0xC008000000000000ULL, 0xC010000000000000ULL,
			0x0000000000000000ULL, 0x8000000000000000ULL,
			0x7FF0000000000000ULL, 0xFFF0000000000000ULL,
			0x7FF8000000000000ULL, 0x7FF0000000000001ULL,
			0x3FF0000000000000ULL, 0x8000000000000000ULL,
		},
	};
	static const unsigned long long mat4_b[2][16] = {
		{
			0x40400000ULL, 0x40000000ULL, 0x3F800000ULL, 0x00000000ULL,
			0xC0400000ULL, 0xBF800000ULL, 0xC0000000ULL, 0x80000000ULL,
			0x80000000ULL, 0x00000000ULL, 0xFF800000ULL, 0x7F800000ULL,
			0x7F800001ULL, 0x7FC00000ULL, 0x80000000ULL, 0x3F800000ULL,
		},
		{
			0x4008000000000000ULL, 0x4000000000000000ULL,
			0x3FF0000000000000ULL, 0x0000000000000000ULL,
			0xC008000000000000ULL, 0xBFF0000000000000ULL,
			0xC000000000000000ULL, 0x8000000000000000ULL,
			0x8000000000000000ULL, 0x0000000000000000ULL,
			0xFFF0000000000000ULL, 0x7FF0000000000000ULL,
			0x7FF0000000000001ULL, 0x7FF8000000000000ULL,
			0x8000000000000000ULL, 0x3FF0000000000000ULL,
		},
	};
	const char *fmts[] = { "ft", "fo" };
	unsigned long long initial;
	int f, i, r, c;

	initial = mm_rd_rf0();
	printf("INIT rf0=%016llx\n", initial);

	/* ── CLAMP: 1k iterations over boundary + random values ── */
	for (f = 0; f < 2; f++) {
		for (i = 0; i < MM_CLAMP_N; i++) {
			unsigned long long a, b, cc;
			char label[16];

			if (i < 16)
				a = (f == 0) ? ft_special[i] : fo_special[i];
			else
				a = random_bits(fmts[f]);
			if (f == 0) {
				b = ft_lo[i % 8];
				cc = ft_hi[(i / 8) % 8];
			} else {
				b = fo_lo[i % 8];
				cc = fo_hi[(i / 8) % 8];
			}
			snprintf(label, sizeof(label), "c%03d", i);
			clamp_obs(fmts[f], label, a, b, cc);
		}
	}

	/* ── MAT4: 4x4 element-wise min / max ── */
	for (f = 0; f < 2; f++) {
		for (r = 0; r < 4; r++) {
			for (c = 0; c < 4; c++) {
				char label[16];

				snprintf(label, sizeof(label), "r%dc%d", r, c);
				mm_obs("mat4", fmts[f], "min", "number", label,
				       mat4_a[f][r * 4 + c], mat4_b[f][r * 4 + c]);
				mm_obs("mat4", fmts[f], "max", "number", label,
				       mat4_a[f][r * 4 + c], mat4_b[f][r * 4 + c]);
			}
		}
	}

	/* ── INTCMP: integer min/max control ── */
	for (f = 0; f < 2; f++) {
		for (i = -21; i <= 21; i++) {
			const int lo = -5, hi = 5;
			unsigned long long a, b, cc, pre, out, post;
			int iout = (i < lo) ? lo : ((i > hi) ? hi : i);
			char label[16];

			if (f == 0) {
				union mm_u32 u;

				u.f = (float)i;  a = u.u;
				u.f = (float)lo; b = u.u;
				u.f = (float)hi; cc = u.u;
				mm_clear_rf0();
				pre = mm_rd_rf0();
				u.f = mm_clamp_f32((float)i, (float)lo, (float)hi);
				out = u.u;
			} else {
				union mm_u64 u;

				u.d = (double)i;  a = u.u;
				u.d = (double)lo; b = u.u;
				u.d = (double)hi; cc = u.u;
				mm_clear_rf0();
				pre = mm_rd_rf0();
				u.d = mm_clamp_f64((double)i, (double)lo,
						   (double)hi);
				out = u.u;
			}
			post = mm_rd_rf0();
			snprintf(label, sizeof(label), "i%d", i);
			printf("OBS group=intcmp fmt=%s op=clamp kind=number "
			       "label=%s a=%016llx b=%016llx c=%016llx "
			       "out=%016llx pre=%016llx post=%016llx "
			       "xi=%d loi=%d hii=%d iout=%d\n",
			       fmts[f], label, a, b, cc, out, pre, post,
			       i, lo, hi, iout);
		}
	}

	mm_restore("clamp");
	return 0;
}
