;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-087t (ISS-193 (b)): the f32 counterpart of the LLVM-080t P1 rounding /
; min-max libcalls.  The DADAO ISA has no rounding-direction or fmin/fmax
; instruction for either width (`contracts/opcodes.yaml`, scope `fp`), so the
; f32 DAG nodes (`ffloor`/`fceil`/`ftrunc`/`fround`/`frint`/`fnearbyint`/
; `fminnum`/`fmaxnum`) lower to an out-of-line call to the standard C routine of
; the same name: RTLIB::FLOOR_F32 -> `floorf`, ..., RTLIB::FMAX_F32 -> `fmaxf`
; (DADAOSubtarget::initLibcallLoweringInfo; picolibc supplies those symbols).
; The expected symbol names are the C library names mandated by the RTLIB enum,
; NOT read back from the backend.  The addend keeps the call out of tail
; position (a bare `return floorf(x)` would be a `jump floorf`).
;

declare float @llvm.floor.f32(float)
declare float @llvm.ceil.f32(float)
declare float @llvm.trunc.f32(float)
declare float @llvm.round.f32(float)
declare float @llvm.rint.f32(float)
declare float @llvm.nearbyint.f32(float)
declare float @llvm.minnum.f32(float, float)
declare float @llvm.maxnum.f32(float, float)

define float @f_floor(float %x) {
; CHECK-LABEL: f_floor:
; CHECK: call [rb0, floorf]
  %r = call float @llvm.floor.f32(float %x)
  %s = fadd float %r, 1.000000e+00
  ret float %s
}

define float @f_ceil(float %x) {
; CHECK-LABEL: f_ceil:
; CHECK: call [rb0, ceilf]
  %r = call float @llvm.ceil.f32(float %x)
  %s = fadd float %r, 1.000000e+00
  ret float %s
}

define float @f_trunc(float %x) {
; CHECK-LABEL: f_trunc:
; CHECK: call [rb0, truncf]
  %r = call float @llvm.trunc.f32(float %x)
  %s = fadd float %r, 1.000000e+00
  ret float %s
}

define float @f_round(float %x) {
; CHECK-LABEL: f_round:
; CHECK: call [rb0, roundf]
  %r = call float @llvm.round.f32(float %x)
  %s = fadd float %r, 1.000000e+00
  ret float %s
}

define float @f_rint(float %x) {
; CHECK-LABEL: f_rint:
; CHECK: call [rb0, rintf]
  %r = call float @llvm.rint.f32(float %x)
  %s = fadd float %r, 1.000000e+00
  ret float %s
}

define float @f_nearbyint(float %x) {
; CHECK-LABEL: f_nearbyint:
; CHECK: call [rb0, nearbyintf]
  %r = call float @llvm.nearbyint.f32(float %x)
  %s = fadd float %r, 1.000000e+00
  ret float %s
}

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
