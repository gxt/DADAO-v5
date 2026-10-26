;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-080t (P1 FP sign, INTEG-033k §裁定汇总 #6) and LLVM-126t (f32 forms):
; copysign/fabs/fneg use the ISA sign-injection instructions, not the generic
; bit-manipulation expansion.
;
; contract-fp.md §7 "sign": `sgnj` computes copySign(rfHC, rfHD) -- take every
; bit of rfHC except the sign and combine it with the sign bit of rfHD;
; `sgnn` does the same with the sign bit inverted.
; Therefore:
;   * copysign(a, b) = `sgnj(a, b)`;
;   * fneg(x)        = `sgnn(x, x)`  (contract-fp.md §7: rfHC == rfHD);
;   * fabs(x)        = `sgnj(x, +0.0)` with the all-zero bit pattern moved
;     RD->RF by `rd2rf {rfN}, {rd0}` (rd0 is hardwired zero), i.e. exactly two
;     instructions (the zero sign source + the injection).
;
; The f32 forms use the ft instructions (`ftsgnj`/`ftsgnn`); before LLVM-126t
; they fell back to a bit-mask sequence (fabs/copysign) and even a libcall
; (fneg).  No constant pool, no libcall.

declare double @llvm.copysign.f64(double, double)
declare double @llvm.fabs.f64(double)
declare float @llvm.copysign.f32(float, float)
declare float @llvm.fabs.f32(float)

define double @f_copysign(double %a, double %b) {
; CHECK-LABEL: f_copysign:
; CHECK-COUNT-1: fosgnj
; CHECK-NOT:     call
  %r = call double @llvm.copysign.f64(double %a, double %b)
  ret double %r
}

define double @f_fabs(double %a) {
; CHECK-LABEL: f_fabs:
; CHECK-COUNT-1: rd2rf
; CHECK-COUNT-1: fosgnj
; CHECK-NOT:     call
  %r = call double @llvm.fabs.f64(double %a)
  ret double %r
}

define double @f_neg(double %a) {
; CHECK-LABEL: f_neg:
; CHECK-COUNT-1: fosgnn
; CHECK-NOT:     call
  %r = fneg double %a
  ret double %r
}

define float @f32_copysign(float %a, float %b) {
; CHECK-LABEL: f32_copysign:
; CHECK-COUNT-1: ftsgnj
; CHECK-NOT:     call
  %r = call float @llvm.copysign.f32(float %a, float %b)
  ret float %r
}

define float @f32_fabs(float %a) {
; CHECK-LABEL: f32_fabs:
; CHECK-COUNT-1: rd2rf
; CHECK-COUNT-1: ftsgnj
; CHECK-NOT:     call
  %r = call float @llvm.fabs.f32(float %a)
  ret float %r
}

define float @f32_neg(float %a) {
; CHECK-LABEL: f32_neg:
; CHECK-COUNT-1: ftsgnn
; CHECK-NOT:     call
  %r = fneg float %a
  ret float %r
}
