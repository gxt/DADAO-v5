;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s --implicit-check-not=io2fo --implicit-check-not=it2ft
;
; LLVM-126t (ISS-188): `ldexp`/`scalbn` reach the hardware scaleB instruction
; `fosclb`/`ftsclb` -- no libcall, no exponent decomposition loop.
;
; contract-fp.md §5: the instruction computes rfHC * 2^rdHD with rdHD taken as a
; *signed 64-bit integer in an RD register* (rd0 = exponent 0; LLVM-142t), so
; no FP->int/int->FP exponent conversion (io2fo/it2ft) is emitted.  An i32
; exponent is sign-extended into the RD register:
;   ext.so n32 -> rd; fosclb/ftsclb rf, rf, rd           (i32 exponent)
;   fosclb/ftsclb rf, rf, rd                             (i64 exponent)
;
; frexp is NOT wired (LLVM expands it without a libcall; out of scope).

declare double @llvm.ldexp.f64.i32(double, i32)
declare float @llvm.ldexp.f32.i32(float, i32)
declare double @llvm.ldexp.f64.i64(double, i64)

define double @ldexp_f64(double %x, i32 %n) {
; CHECK-LABEL: ldexp_f64:
; CHECK-COUNT-1: ext.so
; CHECK-COUNT-1: fosclb {{rf[0-9]+, rf[0-9]+, rd[0-9]+}}
; CHECK-NOT:     call
  %r = call double @llvm.ldexp.f64.i32(double %x, i32 %n)
  ret double %r
}

define float @ldexp_f32(float %x, i32 %n) {
; CHECK-LABEL: ldexp_f32:
; CHECK-COUNT-1: ext.so
; CHECK-COUNT-1: ftsclb {{rf[0-9]+, rf[0-9]+, rd[0-9]+}}
; CHECK-NOT:     call
  %r = call float @llvm.ldexp.f32.i32(float %x, i32 %n)
  ret float %r
}

define double @ldexp_f64_i64(double %x, i64 %n) {
; CHECK-LABEL: ldexp_f64_i64:
; CHECK-NOT:     ext.so
; CHECK-COUNT-1: fosclb {{rf[0-9]+, rf[0-9]+, rd[0-9]+}}
; CHECK-NOT:     call
  %r = call double @llvm.ldexp.f64.i64(double %x, i64 %n)
  ret double %r
}
