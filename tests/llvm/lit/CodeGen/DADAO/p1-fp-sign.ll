;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-080t (P1 FP sign, INTEG-033k §裁定汇总 #6): double-precision
; copysign/fabs use the ISA sign-injection instruction `fosgnj`, not the generic
; bit-manipulation expansion.
;
; contract-fp.md §7 "sign": `sgnj` computes copySign(rfHC, rfHD) -- take every
; bit of rfHC except the sign and combine it with the sign bit of rfHD.
; Therefore copysign(a, b) is exactly `fosgnj` with the magnitude source `a` and
; the sign source `b` (contract-fp.md §7: "sgnj 实现 copySign(rfHC, rfHD)").
;
; fabs(x) = `fosgnj(x, +0.0)`: the sign-operand register holds the all-zero
; double bit pattern (moved RD->RF with `rd2rf {rfN}, {rd0}`, rd0 = hardwired
; zero), so the copied sign bit is 0 and the result is the magnitude of x
; (contract-fp.md §7); DADAOCodeGen.td matches `fabs` directly (FABS f64 is
; Legal).  No constant pool is used.

declare double @llvm.copysign.f64(double, double)
declare double @llvm.fabs.f64(double)

define double @f_copysign(double %a, double %b) {
; CHECK-LABEL: f_copysign:
; CHECK: fosgnj
  %r = call double @llvm.copysign.f64(double %a, double %b)
  ret double %r
}

define double @f_fabs(double %a) {
; CHECK-LABEL: f_fabs:
; CHECK: rd2rf
; CHECK: fosgnj
  %r = call double @llvm.fabs.f64(double %a)
  ret double %r
}
