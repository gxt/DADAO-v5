;
; RUN: %llc -march=dadao -O0 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-062t / M6: an indirect call (function pointer in a register) must lower
; to the rrii `call` form `call [rbha, rdhb, imms12]` with the target address in
; GPRB and rdhb = rd0, imm = 0 (contract-isa.md §8.5), not a direct call.
;
; CHECK-LABEL: go:
; CHECK:         call [rb{{[0-9]+}}, rd0, 0]
define i64 @add3(i64 %a, i64 %b, i64 %c) noinline {
  %s1 = add i64 %a, %b
  %s2 = add i64 %s1, %c
  ret i64 %s2
}

define i64 @go(ptr %f) {
  %r = call i64 %f(i64 1, i64 2, i64 3)
  ret i64 %r
}
