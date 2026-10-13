/* fp_hfa.c — M6 HFA (homogeneous floating-point aggregate) end-to-end program.
 *
 * Exercises FP argument/return registers for a `{double,double}` aggregate
 * (contract-abi.md §6.4: HFA <= 64B travels in the RF bank).  `mkd` builds an
 * aggregate whose fields are passed in rf16/rf17 and returned in rf8/rf9;
 * `ddsum` receives the aggregate the same way.  The comparison stays an
 * fcmp + branch (no FP setcc-as-value).
 *
 *   mkdouble(1.5, 2.5) -> {1.5, 2.5}; sum = 4.0 > 3.0 -> exit 42
 */

struct dd {
  double a;
  double b;
};

struct dd mkdouble(double a, double b) {
  struct dd r;
  r.a = a;
  r.b = b;
  return r;
}

double ddsum(struct dd v) { return v.a + v.b; }

volatile long g_out;

long main(void) {
  struct dd v = mkdouble(1.5, 2.5);
  double s = ddsum(v);
  if (s > 3.0)
    g_out = 42;
  else
    g_out = 7;
  return g_out;
}
