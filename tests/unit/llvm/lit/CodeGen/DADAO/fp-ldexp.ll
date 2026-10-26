;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-126t (ISS-188): `ldexp`/`scalbn` reach the hardware scaleB instruction
; `fosclb`/`ftsclb` -- no libcall, no exponent decomposition loop.
;
; contract-fp.md §5: the instruction computes rfHC * 2^rfHD with rfHD taken as
; an *integer value in an FP register*, so the integer exponent is converted
; once with io2fo (f64) / io2ft (f32), signed (a negative exponent scales
; down):
;   ext.so n32 -> i64; io2fo/io2ft; fosclb/ftsclb        (i32 exponent)
;   io2fo/io2ft; fosclb/ftsclb                           (i64 exponent)
;
; frexp is NOT wired (LLVM expands it without a libcall; out of scope).

declare double @llvm.ldexp.f64.i32(double, i32)
declare float @llvm.ldexp.f32.i32(float, i32)
declare double @llvm.ldexp.f64.i64(double, i64)

define double @ldexp_f64(double %x, i32 %n) {
; CHECK-LABEL: ldexp_f64:
; CHECK-COUNT-1: ext.so
; CHECK-COUNT-1: io2fo
; CHECK-COUNT-1: fosclb
; CHECK-NOT:     call
  %r = call double @llvm.ldexp.f64.i32(double %x, i32 %n)
  ret double %r
}

define float @ldexp_f32(float %x, i32 %n) {
; CHECK-LABEL: ldexp_f32:
; CHECK-COUNT-1: ext.so
; CHECK-COUNT-1: io2ft
; CHECK-COUNT-1: ftsclb
; CHECK-NOT:     call
  %r = call float @llvm.ldexp.f32.i32(float %x, i32 %n)
  ret float %r
}

define double @ldexp_f64_i64(double %x, i64 %n) {
; CHECK-LABEL: ldexp_f64_i64:
; CHECK-COUNT-1: io2fo
; CHECK-COUNT-1: fosclb
; CHECK-NOT:     call
  %r = call double @llvm.ldexp.f64.i64(double %x, i64 %n)
  ret double %r
}
