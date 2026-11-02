/*
 * TESTCASES-058t -- Horner polynomial evaluation with fused multiply-add.
 *
 *   p(x) = c[deg]; for i = deg-1 .. 0:  p = fma(p, x, c[i])
 *
 * Degrees 5 and 9 in double, degree 5 in single (format coverage).  The probe
 * prints the data hash and a hash of EVERY intermediate p, so the oracle
 * compares the whole chain bit for bit; the accumulated rf0 flags are also
 * asserted.  Coefficients and x come from the LCG documented in
 * oracle_fma.py; every expectation is derived there from the spec.
 *
 * The two kernels are `noinline` so the driver can assert the instruction mix
 * of each one separately at both -O0 and -O2.
 */
#include "fma_common.h"

__attribute__((noinline))
static unsigned long long horner_d(const double *c, int deg, double x,
				   unsigned long long *h,
				   unsigned long long *pre,
				   unsigned long long *post)
{
	double p = c[deg];
	unsigned long long hash = FMA_FNV_INIT;
	int i;

	fma_clear_flags();
	*pre = fma_rd_rf0();
	for (i = deg - 1; i >= 0; i--) {
		p = fma(p, x, c[i]);
		hash = fma_fnv_u64(hash, fma_bits_d(p));
	}
	*post = fma_rd_rf0_dep(hash);
	*h = hash;
	return fma_bits_d(p);
}

__attribute__((noinline))
static unsigned long long horner_f(const float *c, int deg, float x,
				   unsigned long long *h,
				   unsigned long long *pre,
				   unsigned long long *post)
{
	float p = c[deg];
	unsigned long long hash = FMA_FNV_INIT;
	int i;

	fma_clear_flags();
	*pre = fma_rd_rf0();
	for (i = deg - 1; i >= 0; i--) {
		p = fmaf(p, x, c[i]);
		hash = fma_fnv_u64(hash, fma_bits_f(p));
	}
	*post = fma_rd_rf0_dep(hash);
	*h = hash;
	return fma_bits_f(p);
}

int main(void)
{
	static const int degs_fo[] = { 5, 9 };
	static const int degs_ft[] = { 5 };
	double coef[16], xd;
	float coef_f[16], xf;
	unsigned long long init = fma_rd_rf0();
	unsigned long long data, hash, pre, post, out;
	int d, i;

	printf("INIT rf0=%016llx\n", init);

	for (d = 0; d < (int)(sizeof(degs_fo) / sizeof(degs_fo[0])); d++) {
		int deg = degs_fo[d];

		fma_gen((unsigned int)(0x33333333u + (unsigned)deg), coef,
			deg + 1);
		fma_gen((unsigned int)(0x44444444u + (unsigned)deg), &xd, 1);
		data = FMA_FNV_INIT;
		for (i = 0; i <= deg; i++)
			data = fma_fnv_u64(data, fma_bits_d(coef[i]));
		data = fma_fnv_u64(data, fma_bits_d(xd));
		out = horner_d(coef, deg, xd, &hash, &pre, &post);
		printf("ALG group=horner fmt=fo deg=%d data=%016llx "
		       "hash=%016llx out=%016llx pre=%016llx post=%016llx "
		       "rm=0\n", deg, data, hash, out, pre, post);
	}

	for (d = 0; d < (int)(sizeof(degs_ft) / sizeof(degs_ft[0])); d++) {
		int deg = degs_ft[d];

		fma_gen_f((unsigned int)(0x33333333u + (unsigned)deg), coef_f,
			  deg + 1);
		fma_gen_f((unsigned int)(0x44444444u + (unsigned)deg), &xf, 1);
		data = FMA_FNV_INIT;
		for (i = 0; i <= deg; i++)
			data = fma_fnv_u64(data, fma_bits_f(coef_f[i]));
		data = fma_fnv_u64(data, fma_bits_f(xf));
		out = horner_f(coef_f, deg, xf, &hash, &pre, &post);
		printf("ALG group=horner fmt=ft deg=%d data=%016llx "
		       "hash=%016llx out=%016llx pre=%016llx post=%016llx "
		       "rm=0\n", deg, data, hash, out, pre, post);
	}

	fma_restore("horner", init);
	return 0;
}
