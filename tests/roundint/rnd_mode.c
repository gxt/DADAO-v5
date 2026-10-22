/*
 * TESTCASES-060t -- ftrnd/fornd mode sensitivity.
 *
 * Group A: the dynamic code 0x20 under all four rf0[33:32] directions
 * (00 RNE, 01 RTZ, 10 RDN, 11 RUP) on 2.5, -2.5, 1.5, -0.5 -- inputs chosen
 * to distinguish the directions under IEEE 754 roundToIntegral.
 * Group B: the five static directions under the same four rf0 values: a static
 * code must ignore rf0[33:32] (SimRISC-07 §2.3) -- the oracle asserts the four
 * observations are identical.
 *
 * After every rf0-programmed group the probe restores rf0 to the value read at
 * entry and prints RESTORE expect/got, so pollution of later probes is
 * observable (not assumed).
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

static const char *const mode_label[] = { "2.5", "-2.5", "1.5", "-0.5" };
#define RND_NMODE 4

/* dynamic code 0x20: the four rf0[33:32] settings, then the static group */
static void dynamic_group(const char *fmt, const unsigned long long *in,
			  unsigned long long initial)
{
	unsigned rm, i;
	char group[32];

	for (rm = 0; rm < 4; rm++) {
		for (i = 0; i < RND_NMODE; i++)
			rnd_case("MODE", fmt, 0x20, (int)rm, mode_label[i],
				 in[i]);
		snprintf(group, sizeof(group), "dyn-%s-rm%u", fmt, rm);
		rnd_restore(group, initial);
	}
}

static void static_group(const char *fmt, const unsigned long long *in,
			 unsigned long long initial)
{
	static const unsigned modes[] = { 0x01, 0x02, 0x04, 0x08, 0x10 };
	unsigned m, rm, i;
	char group[32];

	for (m = 0; m < 5; m++) {
		for (rm = 0; rm < 4; rm++)
			for (i = 0; i < 2; i++)
				rnd_case("MODE", fmt, modes[m], (int)rm,
					 mode_label[i], in[i]);
		snprintf(group, sizeof(group), "static-%s-%02x", fmt,
			 modes[m]);
		rnd_restore(group, initial);
	}
}

int main(void)
{
	unsigned long long in_fo[RND_NMODE], in_ft[RND_NMODE];
	unsigned long long initial = rnd_rd_rf0();
	union rnd_u64 d;
	union rnd_u32 f;

	printf("INIT rf0=%016llx\n", initial);

	d.d = 2.5;
	in_fo[0] = d.u;
	d.d = -2.5;
	in_fo[1] = d.u;
	d.d = 1.5;
	in_fo[2] = d.u;
	d.d = -0.5;
	in_fo[3] = d.u;

	f.f = 2.5f;
	in_ft[0] = f.u;
	f.f = -2.5f;
	in_ft[1] = f.u;
	f.f = 1.5f;
	in_ft[2] = f.u;
	f.f = -0.5f;
	in_ft[3] = f.u;

	dynamic_group("fo", in_fo, initial);
	dynamic_group("ft", in_ft, initial);
	static_group("fo", in_fo, initial);
	static_group("ft", in_ft, initial);

	rnd_restore("mode-end", initial);
	return 0;
}
