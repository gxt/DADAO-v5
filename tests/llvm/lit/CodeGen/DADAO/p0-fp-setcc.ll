;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-079t (P0 ISel gap 2): an FP comparison whose result is *used as a value*
; (C `a == b`, `a <= 0.0`, `isnan(x)`) survives as an FP-operand SETCC.  The
; expected instructions come from the contracts:
;
;   * the FP compare is the quiet compare `foqcmp` (f64) / `ftqcmp` (f32),
;     writing -1/0/1 for ordered results (contract-fp.md §8 "compare");
;   * the 0/1 boolean is the `cs.z` conditional assignment (`cond == 0` picks
;     `true`), the same cs.n/z/p used by the integer setcc path
;     (contract-isa.md §6.5, contract-fp.md §10).
;
; `oeq` -> cond == 0 -> cs.z ; `<` -> cond < 0 -> cs.n ; `!=` -> cs.z with the
; arms swapped.

; CHECK-LABEL: setcc_oeq:
; CHECK:         foqcmp
; CHECK:         cs.z
define i64 @setcc_oeq(double %a, double %b) {
  %c = fcmp oeq double %a, %b
  %z = zext i1 %c to i64
  ret i64 %z
}

; CHECK-LABEL: setcc_olt:
; CHECK:         foqcmp
; CHECK:         cs.n
define i64 @setcc_olt(double %a, double %b) {
  %c = fcmp olt double %a, %b
  %z = zext i1 %c to i64
  ret i64 %z
}

; `x <= 0.0` (the picolibc `setule` shape): unordered-or-less is
; `uge(0.0, x)` => cs.n with the arms swapped.
; CHECK-LABEL: setcc_ule_zero:
; CHECK:         foqcmp
; CHECK:         cs.n
define i64 @setcc_ule_zero(double %a) {
  %c = fcmp ule double %a, 0.0
  %z = zext i1 %c to i64
  ret i64 %z
}

; `x != 0.0` (the picolibc `setune ConstantFP:f64<0.0>` shape) -> cs.z with the
; arms swapped.
; CHECK-LABEL: setcc_ne_zero:
; CHECK:         foqcmp
; CHECK:         cs.z
define i64 @setcc_ne_zero(double %a) {
  %c = fcmp une double %a, 0.0
  %z = zext i1 %c to i64
  ret i64 %z
}

; f32 uses the ft compare (contract-fp.md §8: ftqcmp).
; CHECK-LABEL: setcc_f32_ne:
; CHECK:         ftqcmp
; CHECK:         cs.z
define i64 @setcc_f32_ne(float %a, float %b) {
  %c = fcmp une float %a, %b
  %z = zext i1 %c to i64
  ret i64 %z
}
