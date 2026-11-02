/* DADAO clang target builtin `__builtin_dadao_clmul` (LLVM-122t).
 *
 * ADR-0035: `clmul.o {rdHA, rdHB}, rdHC, rdHD` is a GF(2) 64x64 -> 128
 * carry-less multiply.  The builtin takes two `unsigned long long` and returns
 * `unsigned __int128`; the backend carries the i128 result as the instruction's
 * two destinations, so the emitted code is one `clmul.o` with no shift/or
 * joining the halves.
 */
unsigned __int128 clmul_builtin(unsigned long long a, unsigned long long b) {
  return __builtin_dadao_clmul(a, b);
}

/* The builtin is typed `unsigned __int128(unsigned long long, unsigned long
 * long)`, so an incompatible argument is a normal hard diagnostic (the RUN
 * line that compiles this function with `-DBAD_ARG` expects exactly that). */
#ifdef BAD_ARG
struct S {
  int a;
};
unsigned __int128 clmul_bad(struct S s) { return __builtin_dadao_clmul(s, s); }
#endif
