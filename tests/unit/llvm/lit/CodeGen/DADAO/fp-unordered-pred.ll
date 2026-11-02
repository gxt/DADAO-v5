;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-084t (ISS-193 (a)): the FP unordered-family predicates.  Before this the
; DADAO FP branch/select lowering rejected every predicate outside the plain
; 4-way sign test (unordered / ordered / ordered-not-equal / unordered-or-equal)
; with `report_fatal_error`, which is why `isnan`/`isfinite` and the 30 picolibc
; sources that use them could not compile.
;
; Contract basis (all expected instructions are existing ISA instructions):
;   * the FP compare is the quiet compare `foqcmp` (f64) / `ftqcmp` (f32); it
;     writes -1/0/1 for ordered results and a *positive* qNaN for unordered
;     (contract-fp.md §8 "compare");
;   * the qNaN the compare writes for a NaN operand, read as an integer, is
;     larger than the ordered results -1/0/1, so `cmp.si rd, rd, 1`
;     (contract-isa.md §6.2) separates ordered (rd <= 1) from unordered (rd > 1);
;   * ordered-not-equal / unordered-or-equal combine that ordered flag with the
;     equal/not-equal flag through cs.n/z/p (contract-fp.md §10, contract-isa.md
;     §6.5) and and.o / or.o (contract-isa.md §6.1).

; isnan(x, y) = fcmp uno (SETUO): unordered => the compare value > 1 => cs.p.
; CHECK-LABEL: fp_uno_v:
; CHECK:         foqcmp
; CHECK:         cmp.si
; CHECK:         cs.p
define i64 @fp_uno_v(double %a, double %b) {
  %c = fcmp uno double %a, %b
  %z = zext i1 %c to i64
  ret i64 %z
}

; fcmp ord (SETO) is the complement: ordered => rd <= 1 => cs.p with the arms
; swapped.
; CHECK-LABEL: fp_ord_v:
; CHECK:         foqcmp
; CHECK:         cmp.si
; CHECK:         cs.p
define i64 @fp_ord_v(double %a, double %b) {
  %c = fcmp ord double %a, %b
  %z = zext i1 %c to i64
  ret i64 %z
}

; fcmp one (SETONE) = ordered && unequal: an and.o of the ordered flag (cs.p on
; rd vs 1) and the not-equal flag (cs.z on rd vs 0).
; CHECK-LABEL: fp_one_v:
; CHECK:         foqcmp
; CHECK:         cs.z
; CHECK:         cmp.si
; CHECK:         cs.p
; CHECK:         and.o
define i64 @fp_one_v(double %a, double %b) {
  %c = fcmp one double %a, %b
  %z = zext i1 %c to i64
  ret i64 %z
}

; fcmp ueq (SETUEQ) = unordered || equal: an or.o of the unordered flag
; (cs.p on rd vs 1) and the equal flag (cs.z on rd vs 0).
; CHECK-LABEL: fp_ueq_v:
; CHECK:         foqcmp
; CHECK:         cs.z
; CHECK:         cmp.si
; CHECK:         cs.p
; CHECK:         or.o
define i64 @fp_ueq_v(double %a, double %b) {
  %c = fcmp ueq double %a, %b
  %z = zext i1 %c to i64
  ret i64 %z
}

; f32 uses the ft compare (contract-fp.md §8: ftqcmp).
; CHECK-LABEL: fp_uno_f32:
; CHECK:         ftqcmp
; CHECK:         cmp.si
; CHECK:         cs.p
define i64 @fp_uno_f32(float %a, float %b) {
  %c = fcmp uno float %a, %b
  %z = zext i1 %c to i64
  ret i64 %z
}

; The branch form tests the same flag with br.np (rd <= 0 <=> ordered => branch
; to the false block).
; CHECK-LABEL: fp_uno_br:
; CHECK:         foqcmp
; CHECK:         cmp.si
; CHECK:         br.np
define i64 @fp_uno_br(double %a, double %b) {
  %c = fcmp uno double %a, %b
  br i1 %c, label %t, label %f
t:
  ret i64 1
f:
  ret i64 0
}

; The "don't care if unordered" cond codes (ISDOpcodes.h) reach the FP path when
; the DAG knows the operands are ordered (here `fmul nnan`); they lower to their
; ordered counterpart, so `fcmp oge` on an nnan value becomes setge => a single
; foqcmp + cs.p (no extra test).  This is the dcvt.c shape.
; CHECK-LABEL: fp_ge_nnan:
; CHECK:         foqcmp
; CHECK:         cs.p
; CHECK-NOT:     cmp.si
define i64 @fp_ge_nnan(double %a) {
  %m = fmul nnan double %a, 1.0e-1
  %c = fcmp oge double %m, 1.0e+0
  %z = zext i1 %c to i64
  ret i64 %z
}
