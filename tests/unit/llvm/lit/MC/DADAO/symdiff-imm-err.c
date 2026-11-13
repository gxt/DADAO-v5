/* m14-llvm-005 (`ISS-424`): `clang -c` inline-assembly coverage for
   symdiff-imm-err.s.  The clang integrated assembler uses the same MC parser,
   so a symbol difference used as an instruction immediate must be rejected
   there too (never a silent 0).  A same-TU `_start` label is defined so the
   subtraction is between two *defined* symbols -- the case the MC expression
   parser itself accepts and that used to fold to 0. */
__asm__(".text\n.globl _start\n_start:\n");

void f(void) { __asm__ volatile("set.zw rb1, wp0, . - _start"); }
