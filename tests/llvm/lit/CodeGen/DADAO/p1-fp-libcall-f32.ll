;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-087t (ISS-193 (b)): f32 fmin/fmax libcalls -- the DADAO ISA has no
; min/max instruction for either width (`contracts/opcodes.yaml`, scope `fp`),
; so `fminnum`/`fmaxnum` on f32 lower to an out-of-line call to the standard C
; routine of the same name: RTLIB::FMAX_F32 -> `fmaxf`
; (DADAOSubtarget::initLibcallLoweringInfo; picolibc supplies those symbols).
; The expected symbol names are the C library names mandated by the RTLIB enum,
; NOT read back from the backend.  The addend keeps the call out of tail
; position (a bare `return fminf(a, b)` would be a `jump fminf`).
;
; The f32 *rounding* intrinsics no longer live here: since LLVM-125t they
; select the one-instruction `ftrnd` form (see p1-fp-rounding-f32.ll).
;

declare float @llvm.minnum.f32(float, float)
declare float @llvm.maxnum.f32(float, float)

define float @f_fmin(float %a, float %b) {
; CHECK-LABEL: f_fmin:
; CHECK: call [rb0, fminf]
  %r = call float @llvm.minnum.f32(float %a, float %b)
  %s = fadd float %r, 1.000000e+00
  ret float %s
}

define float @f_fmax(float %a, float %b) {
; CHECK-LABEL: f_fmax:
; CHECK: call [rb0, fmaxf]
  %r = call float @llvm.maxnum.f32(float %a, float %b)
  %s = fadd float %r, 1.000000e+00
  ret float %s
}
