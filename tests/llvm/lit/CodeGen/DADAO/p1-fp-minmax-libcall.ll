;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-080t (P1 FP min/max, INTEG-033k §裁定汇总 #6): the DADAO ISA has no
; fmin/fmax instruction (`contracts/opcodes.yaml` scope `fp`).  llvm.minnum.f64
; / llvm.maxnum.f64 lower to a call to the C library routine of the same name
; (RTLIB::FMIN_F64 -> `fmin`, RTLIB::FMAX_F64 -> `fmax`;
; DADAOSubtarget::initLibcallLoweringInfo; picolibc supplies fmin/fmax).
;
; The addend keeps the call out of tail position (see p1-fp-round-libcall.ll).

declare double @llvm.minnum.f64(double, double)
declare double @llvm.maxnum.f64(double, double)

define double @f_fmin(double %a, double %b) {
; CHECK-LABEL: f_fmin:
; CHECK: call [rb0, fmin]
  %r = call double @llvm.minnum.f64(double %a, double %b)
  %s = fadd double %r, 1.000000e+00
  ret double %s
}

define double @f_fmax(double %a, double %b) {
; CHECK-LABEL: f_fmax:
; CHECK: call [rb0, fmax]
  %r = call double @llvm.maxnum.f64(double %a, double %b)
  %s = fadd double %r, 1.000000e+00
  ret double %s
}
