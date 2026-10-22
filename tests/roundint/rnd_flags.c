/*
 * TESTCASES-060t -- ftrnd/fornd exception flags (rf0[4:0]).
 *
 * Assertions (SimRISC-07 §4.3 / contract-fp.md §18):
 *   1. the five static directions NEVER set NX, even for inexact inputs;
 *   2. the dynamic code 0x20 sets NX iff the input is not already integral
 *      (finite); an integral input sets no flag;
 *   3. qNaN never sets NV; sNaN always sets NV (in every mode);
 *   4. Inf sets nothing; DZ/OF/UF are never set by roundToIntegral.
 *
 * The probe clears rf0[4:0] itself before every execution and prints the full
 * rf0 before/after, so "the test cleared the flags" is itself asserted by the
 * oracle (pre-flags must read 0), and rf0[63:34]/[21:5] must stay unchanged.
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

static const unsigned static_modes[] = { 0x01, 0x02, 0x04, 0x08, 0x10 };
static const unsigned all_modes[] = { 0x01, 0x02, 0x04, 0x08, 0x10, 0x20 };
#define RND_NSTATIC 5
#define RND_NALL 6

static void set_inputs(const char *fmt, unsigned long long *in,
		       unsigned long long big)
{
	union rnd_u64 d;
	union rnd_u32 f;
	int is_ft = (fmt[0] == 'f' && fmt[1] == 't');
	unsigned i = 0;

	if (is_ft) {
		f.f = 1.5f;  in[i++] = f.u;	/* inexact -> NX only for 0x20 */
		f.f = 0.5f;  in[i++] = f.u;
		f.f = -0.5f; in[i++] = f.u;
		f.f = 1.0f;  in[i++] = f.u;	/* already integral */
		f.f = -1.0f; in[i++] = f.u;
		f.f = 0.0f;  in[i++] = f.u;
		f.f = -0.0f; in[i++] = f.u;
	} else {
		d.d = 1.5;  in[i++] = d.u;
		d.d = 0.5;  in[i++] = d.u;
		d.d = -0.5; in[i++] = d.u;
		d.d = 1.0;  in[i++] = d.u;
		d.d = -1.0; in[i++] = d.u;
		d.d = 0.0;  in[i++] = d.u;
		d.d = -0.0; in[i++] = d.u;
	}
	in[i++] = big;			/* 2^24 (ft) / 2^53 (fo) */
	in[i++] = 0x0000000000000001ULL;	/* minsub: not integral, NX */
	in[i++] = is_ft ? 0x7fc00000ULL : 0x7ff8000000000000ULL; /* qNaN */
	in[i++] = is_ft ? 0x7f800001ULL : 0x7ff0000000000001ULL; /* sNaN */
	in[i++] = is_ft ? 0x7f800000ULL : 0x7ff0000000000000ULL; /* +Inf */
}
#define RND_NFLAG 12

static const char *const flag_label_fo[] = {
	"1.5", "0.5", "-0.5", "1.0", "-1.0", "0", "-0", "2^53", "minsub",
	"qnan", "snan", "inf",
};
static const char *const flag_label_ft[] = {
	"1.5", "0.5", "-0.5", "1.0", "-1.0", "0", "-0", "2^24", "minsub",
	"qnan", "snan", "inf",
};

int main(void)
{
	unsigned long long in[RND_NFLAG];
	unsigned long long initial = rnd_rd_rf0();
	unsigned m, rm, i;
	union rnd_u64 d;
	union rnd_u32 f;
	unsigned long long big_fo, big_ft;

	printf("INIT rf0=%016llx\n", initial);

	d.d = 9007199254740992.0;
	big_fo = d.u;
	f.f = 16777216.0f;
	big_ft = f.u;

	/* 1. static directions: never NX, even for inexact inputs.  Exercised
	 *    with rf0[33:32] = RUP so a stray dynamic read shows up. */
	set_inputs("fo", in, big_fo);
	for (m = 0; m < RND_NSTATIC; m++)
		for (i = 0; i < RND_NFLAG; i++)
			rnd_case("FLAGS", "fo", static_modes[m], 3,
				 flag_label_fo[i], in[i]);
	rnd_restore("flags-static-fo", initial);

	set_inputs("ft", in, big_ft);
	for (m = 0; m < RND_NSTATIC; m++)
		for (i = 0; i < RND_NFLAG; i++)
			rnd_case("FLAGS", "ft", static_modes[m], 3,
				 flag_label_ft[i], in[i]);
	rnd_restore("flags-static-ft", initial);

	/* 2. dynamic code: all six modes x two rf0 directions, so the NX rule
	 *    is exercised for inexact and exact inputs. */
	for (rm = 0; rm < 2; rm++) {
		set_inputs("fo", in, big_fo);
		for (i = 0; i < RND_NFLAG; i++)
			rnd_case("FLAGS", "fo", 0x20, (int)rm,
				 flag_label_fo[i], in[i]);
		set_inputs("ft", in, big_ft);
		for (i = 0; i < RND_NFLAG; i++)
			rnd_case("FLAGS", "ft", 0x20, (int)rm,
				 flag_label_ft[i], in[i]);
	}
	rnd_restore("flags-dyn", initial);

	/* 3. NaN classes in every mode (NV must follow the input class, never
	 *    the mode). */
	set_inputs("fo", in, big_fo);
	for (m = 0; m < RND_NALL; m++)
		for (i = 9; i < 11; i++)
			rnd_case("FLAGS", "fo", all_modes[m],
				 all_modes[m] == 0x20 ? 0 : 3,
				 flag_label_fo[i], in[i]);
	set_inputs("ft", in, big_ft);
	for (m = 0; m < RND_NALL; m++)
		for (i = 9; i < 11; i++)
			rnd_case("FLAGS", "ft", all_modes[m],
				 all_modes[m] == 0x20 ? 0 : 3,
				 flag_label_ft[i], in[i]);
	rnd_restore("flags-nan", initial);

	rnd_restore("flags-end", initial);
	return 0;
}
