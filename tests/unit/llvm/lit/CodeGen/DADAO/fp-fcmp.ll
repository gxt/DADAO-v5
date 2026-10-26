;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-126t (ISS-188): all twelve `fcmp` conditions reach the hardware FP
; compare `foqcmp`/`ftqcmp` -- one compare instruction per condition, no
; libcall.  contract-fp.md §8: the compare writes -1/0/1 for ordered results
; and a *positive* qNaN for unordered, so the ordered/unordered predicates that
; are not a plain sign/zero test (UNO, ORD, ONE) add one integer `cmp.si`
; against 1; everything else is one compare + one `cs.*` conditional
; assignment (contract-isa.md §6.5).
;
; The predicates below are the complete LLVM set:
;   ordered:   oeq ogt oge olt ole one ord
;   unordered: ueq ugt uge ult ule une uno
;
; ±0: `oeq` on -0.0/+0.0 is true because the hardware compares the IEEE values
; (not the bit patterns), and `uno`/`ord` are decided from the compare result,
; so no +/-0 special case is needed.

define i64 @cmp_oeq(double %a, double %b) {
; CHECK-LABEL: cmp_oeq:
; CHECK-COUNT-1: foqcmp
; CHECK-NOT:     call
  %c = fcmp oeq double %a, %b
  %r = zext i1 %c to i64
  ret i64 %r
}

define i64 @cmp_ogt(double %a, double %b) {
; CHECK-LABEL: cmp_ogt:
; CHECK-COUNT-1: foqcmp
; CHECK-NOT:     call
  %c = fcmp ogt double %a, %b
  %r = zext i1 %c to i64
  ret i64 %r
}

define i64 @cmp_oge(double %a, double %b) {
; CHECK-LABEL: cmp_oge:
; CHECK-COUNT-1: foqcmp
; CHECK-NOT:     call
  %c = fcmp oge double %a, %b
  %r = zext i1 %c to i64
  ret i64 %r
}

define i64 @cmp_olt(double %a, double %b) {
; CHECK-LABEL: cmp_olt:
; CHECK-COUNT-1: foqcmp
; CHECK-NOT:     call
  %c = fcmp olt double %a, %b
  %r = zext i1 %c to i64
  ret i64 %r
}

define i64 @cmp_ole(double %a, double %b) {
; CHECK-LABEL: cmp_ole:
; CHECK-COUNT-1: foqcmp
; CHECK-NOT:     call
  %c = fcmp ole double %a, %b
  %r = zext i1 %c to i64
  ret i64 %r
}

define i64 @cmp_one(double %a, double %b) {
; CHECK-LABEL: cmp_one:
; CHECK-COUNT-1: foqcmp
; CHECK-COUNT-1: cmp.si
; CHECK-NOT:     call
  %c = fcmp one double %a, %b
  %r = zext i1 %c to i64
  ret i64 %r
}

define i64 @cmp_ord(double %a, double %b) {
; CHECK-LABEL: cmp_ord:
; CHECK-COUNT-1: foqcmp
; CHECK-COUNT-1: cmp.si
; CHECK-NOT:     call
  %c = fcmp ord double %a, %b
  %r = zext i1 %c to i64
  ret i64 %r
}

define i64 @cmp_ueq(double %a, double %b) {
; CHECK-LABEL: cmp_ueq:
; CHECK-COUNT-1: foqcmp
; CHECK-NOT:     call
  %c = fcmp ueq double %a, %b
  %r = zext i1 %c to i64
  ret i64 %r
}

define i64 @cmp_ugt(double %a, double %b) {
; CHECK-LABEL: cmp_ugt:
; CHECK-COUNT-1: foqcmp
; CHECK-NOT:     call
  %c = fcmp ugt double %a, %b
  %r = zext i1 %c to i64
  ret i64 %r
}

define i64 @cmp_uge(double %a, double %b) {
; CHECK-LABEL: cmp_uge:
; CHECK-COUNT-1: foqcmp
; CHECK-NOT:     call
  %c = fcmp uge double %a, %b
  %r = zext i1 %c to i64
  ret i64 %r
}

define i64 @cmp_ult(double %a, double %b) {
; CHECK-LABEL: cmp_ult:
; CHECK-COUNT-1: foqcmp
; CHECK-NOT:     call
  %c = fcmp ult double %a, %b
  %r = zext i1 %c to i64
  ret i64 %r
}

define i64 @cmp_ule(double %a, double %b) {
; CHECK-LABEL: cmp_ule:
; CHECK-COUNT-1: foqcmp
; CHECK-NOT:     call
  %c = fcmp ule double %a, %b
  %r = zext i1 %c to i64
  ret i64 %r
}

define i64 @cmp_une(double %a, double %b) {
; CHECK-LABEL: cmp_une:
; CHECK-COUNT-1: foqcmp
; CHECK-NOT:     call
  %c = fcmp une double %a, %b
  %r = zext i1 %c to i64
  ret i64 %r
}

define i64 @cmp_uno(double %a, double %b) {
; CHECK-LABEL: cmp_uno:
; CHECK-COUNT-1: foqcmp
; CHECK-COUNT-1: cmp.si
; CHECK-NOT:     call
  %c = fcmp uno double %a, %b
  %r = zext i1 %c to i64
  ret i64 %r
}

; The f32 form uses ftqcmp with the same predicate mapping.
define i64 @cmp_f32_uno(float %a, float %b) {
; CHECK-LABEL: cmp_f32_uno:
; CHECK-COUNT-1: ftqcmp
; CHECK-COUNT-1: cmp.si
; CHECK-NOT:     call
  %c = fcmp uno float %a, %b
  %r = zext i1 %c to i64
  ret i64 %r
}

define i64 @cmp_f32_oeq(float %a, float %b) {
; CHECK-LABEL: cmp_f32_oeq:
; CHECK-COUNT-1: ftqcmp
; CHECK-NOT:     call
  %c = fcmp oeq float %a, %b
  %r = zext i1 %c to i64
  ret i64 %r
}

; Branch form (LowerBR_CC): one compare + one br.*, no libcall.
define i64 @cmp_branch(double %a, double %b) {
; CHECK-LABEL: cmp_branch:
; CHECK-COUNT-1: foqcmp
; CHECK-NOT:     call
entry:
  %c = fcmp olt double %a, %b
  br i1 %c, label %yes, label %no
yes:
  ret i64 1
no:
  ret i64 0
}
