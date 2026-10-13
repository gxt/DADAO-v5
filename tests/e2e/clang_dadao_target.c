/* Minimal freestanding C translation unit for the DADAO clang target lit test
 * (LLVM-063t).  It only exercises the integer/pointer ABI surface the DADAO
 * backend supports: no headers, no libc, no floating point, no varargs. */

long clang_add3(long a, long b, long c) { return a + b + c; }

long clang_load(long *p) { return p[1]; }

struct pair {
  long a;
  long b;
};

/* <=64-byte aggregates are passed/returned by value: the return lands in
 * rd8/rd9, the argument in rd16/rd17 (contract-abi §6.1/§6.4). */
struct pair clang_mkpair(long a, long b) {
  struct pair p;
  p.a = a;
  p.b = b;
  return p;
}

long clang_pairsum(struct pair *p) { return p->a + p->b; }

long clang_pairval(struct pair p) { return p.a + p.b; }
