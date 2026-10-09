;
; RUN: %llc -march=dadao -O0 -stop-after=finalize-isel %s -o - | %FileCheck %s
;
; LLVM-062t / M6: return registers are rd8 (integer/scalar), rb8 (pointer) and
; rf8 (float), i.e. the low end of each bank's return range rd8..rd15 /
; rb8..rb15 (contract-abi.md §6.1, spec DADAO-21 §返回值).  Multiple return
; values fill their own bank from index 8 upward (K = 8 per bank).
;
; CHECK-LABEL: name:{{ +}}iret
; CHECK:         RET_PSEUDO implicit $rd8
define i64 @iret(i64 %x) {
  ret i64 %x
}

; CHECK-LABEL: name:{{ +}}pret
; CHECK:         RET_PSEUDO implicit $rb8
define ptr @pret(ptr %p) {
  ret ptr %p
}

; A 2-element aggregate return fills rd8 and rd9 (declaration order, same bank).
; CHECK-LABEL: name:{{ +}}mret
; CHECK:         RET_PSEUDO implicit $rd8, implicit $rd9
define { i64, i64 } @mret(i64 %a, i64 %b) {
  %r0 = insertvalue { i64, i64 } undef, i64 %a, 0
  %r1 = insertvalue { i64, i64 } %r0, i64 %b, 1
  ret { i64, i64 } %r1
}
