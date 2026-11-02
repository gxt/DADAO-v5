;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-126t (ISS-188): `llvm.is.fpclass` / C `fpclassify` is the hardware
; classification `focls`/`ftcls` plus a mask test -- no comparisons, no reorder.
;
; contract-fp.md §9: the instruction writes a 10-bit one-hot class word in
; rd[9:0] with bit order
;   0 sNaN, 1 qNaN, 2 -Inf, 3 -Normal, 4 -Subnormal, 5 -Zero,
;   6 +Zero, 7 +Subnormal, 8 +Normal, 9 +Inf
; which is exactly LLVM's FPClassTest (SPEC-156t aligned it), so the lowering
; masks the class word directly:
;   * multi-class mask: `focls` + `and` (the mask constant is the LLVM
;     FPClassTest value -- 504 = all finite, 3 = NaN) + zero test;
;   * single-class mask: the one-hot class word is compared with the mask, so
;     there is no `and` for it (only the trailing zext `and` with 1).
; `fpclassify(x)` (C five classes) is a compile-time constant mapping to these
; masks, so it folds to the same sequence.

declare i1 @llvm.is.fpclass.f64(double, i32)
declare i1 @llvm.is.fpclass.f32(float, i32)

; single class: negative infinity (bit 2)
define i64 @cls_neginf(double %x) {
; CHECK-LABEL: cls_neginf:
; CHECK-COUNT-1: focls
; CHECK-COUNT-1: cmp.ui
; CHECK-NOT:     call
  %r = call i1 @llvm.is.fpclass.f64(double %x, i32 4)
  %z = zext i1 %r to i64
  ret i64 %z
}

; single class: positive infinity (bit 9)
define i64 @cls_posinf(double %x) {
; CHECK-LABEL: cls_posinf:
; CHECK-COUNT-1: focls
; CHECK-COUNT-1: cmp.ui
; CHECK-NOT:     call
  %r = call i1 @llvm.is.fpclass.f64(double %x, i32 512)
  %z = zext i1 %r to i64
  ret i64 %z
}

; two classes: NaN (sNaN | qNaN = 3) -- multi-bit mask, one AND
define i64 @cls_nan(double %x) {
; CHECK-LABEL: cls_nan:
; CHECK-COUNT-1: focls
; CHECK:         and.o
; CHECK-NOT:     call
  %r = call i1 @llvm.is.fpclass.f64(double %x, i32 3)
  %z = zext i1 %r to i64
  ret i64 %z
}

; C fpclassify's FP_FINITE: normal | subnormal | zero (504), f64 and f32
define i64 @cls_finite(double %x) {
; CHECK-LABEL: cls_finite:
; CHECK-COUNT-1: focls
; CHECK-NOT:     call
  %r = call i1 @llvm.is.fpclass.f64(double %x, i32 504)
  %z = zext i1 %r to i64
  ret i64 %z
}

define i64 @cls_finite_f32(float %x) {
; CHECK-LABEL: cls_finite_f32:
; CHECK-COUNT-1: ftcls
; CHECK-NOT:     call
  %r = call i1 @llvm.is.fpclass.f32(float %x, i32 504)
  %z = zext i1 %r to i64
  ret i64 %z
}

; FP_SUBNORMAL (positive and negative, 0x90) and FP_ZERO (0x60): the masks
; keep the LLVM bit positions untouched.
define i64 @cls_subnormal(double %x) {
; CHECK-LABEL: cls_subnormal:
; CHECK:         focls
; CHECK-NOT:     call
  %r = call i1 @llvm.is.fpclass.f64(double %x, i32 144)
  %z = zext i1 %r to i64
  ret i64 %z
}

define i64 @cls_zero(double %x) {
; CHECK-LABEL: cls_zero:
; CHECK:         focls
; CHECK-NOT:     call
  %r = call i1 @llvm.is.fpclass.f64(double %x, i32 96)
  %z = zext i1 %r to i64
  ret i64 %z
}
