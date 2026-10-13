;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-080t (P1 FP rounding, INTEG-033k §裁定汇总 #6): the DADAO ISA has no
; rounding-direction instruction.  `contracts/opcodes.yaml` (scope `fp`, 60
; instructions) carries only convert / arith / root / sign / compare / classify
; -- there is no floor/ceil/trunc/round/rint/nearbyint or fmin/fmax.  These DAG
; nodes therefore reach LegalizeDAG with a non-Legal action and lower to an
; out-of-line call to the standard C math routine of the same name
; (DADAOSubtarget::initLibcallLoweringInfo registers RTLIB::FLOOR_F64 ->
; `floor`, etc.; picolibc supplies those symbols).  The expected symbol names
; are the C library names mandated by the RTLIB enum, NOT read back from the
; backend.
;
; Each function feeds the result into an FP addend before returning so the
; libcall is not in tail position (a bare `return floor(x)` would be a
; `jump floor`); the call itself is what this test pins.

declare double @llvm.floor.f64(double)
declare double @llvm.ceil.f64(double)
declare double @llvm.trunc.f64(double)
declare double @llvm.round.f64(double)
declare double @llvm.rint.f64(double)
declare double @llvm.nearbyint.f64(double)

define double @f_floor(double %x) {
; CHECK-LABEL: f_floor:
; CHECK: call [rb0, floor]
  %r = call double @llvm.floor.f64(double %x)
  %s = fadd double %r, 1.000000e+00
  ret double %s
}

define double @f_ceil(double %x) {
; CHECK-LABEL: f_ceil:
; CHECK: call [rb0, ceil]
  %r = call double @llvm.ceil.f64(double %x)
  %s = fadd double %r, 1.000000e+00
  ret double %s
}

define double @f_trunc(double %x) {
; CHECK-LABEL: f_trunc:
; CHECK: call [rb0, trunc]
  %r = call double @llvm.trunc.f64(double %x)
  %s = fadd double %r, 1.000000e+00
  ret double %s
}

define double @f_round(double %x) {
; CHECK-LABEL: f_round:
; CHECK: call [rb0, round]
  %r = call double @llvm.round.f64(double %x)
  %s = fadd double %r, 1.000000e+00
  ret double %s
}

define double @f_rint(double %x) {
; CHECK-LABEL: f_rint:
; CHECK: call [rb0, rint]
  %r = call double @llvm.rint.f64(double %x)
  %s = fadd double %r, 1.000000e+00
  ret double %s
}

define double @f_nearbyint(double %x) {
; CHECK-LABEL: f_nearbyint:
; CHECK: call [rb0, nearbyint]
  %r = call double @llvm.nearbyint.f64(double %x)
  %s = fadd double %r, 1.000000e+00
  ret double %s
}
