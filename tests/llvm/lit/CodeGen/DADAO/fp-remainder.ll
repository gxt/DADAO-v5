;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-126t (user ruling 2026-10-23): `forem`/`ftrem` are IEEE 754 remainder
; (`x - n*y`, n the nearest integer, ties to even -- contract-fp.md §5).  LLVM
; has no `llvm.remainder` intrinsic and LLVM `frem` is *libm fmod* (n truncates
; toward zero, so the remainder keeps the dividend's sign), which is a
; different function: `fmod(5,3)=2` vs `remainder(5,3)=-1`.  The two must never
; be cross-wired, so `forem` is reachable only through
; `__builtin_dadao_remainder` -> `llvm.dadao.remainder.{f64,f32}`, and
; ISD::FREM stays Expand.
;
; One instruction per call, no libcall.

declare double @llvm.dadao.remainder.f64(double, double)
declare float @llvm.dadao.remainder.f32(float, float)

define double @remainder_f64(double %a, double %b) {
; CHECK-LABEL: remainder_f64:
; CHECK-COUNT-1: forem
; CHECK-NOT:     call
  %r = call double @llvm.dadao.remainder.f64(double %a, double %b)
  ret double %r
}

define float @remainder_f32(float %a, float %b) {
; CHECK-LABEL: remainder_f32:
; CHECK-COUNT-1: ftrem
; CHECK-NOT:     call
  %r = call float @llvm.dadao.remainder.f32(float %a, float %b)
  ret float %r
}

; LLVM `frem` (= fmod) must NOT select forem/ftrem.  Its Expand path is the
; generic inline fmod algorithm; the assertion here is negative on purpose.
define double @frem_stays_expand(double %a, double %b) {
; CHECK-LABEL: frem_stays_expand:
; CHECK-NOT:     forem
; CHECK-NOT:     ftrem
  %r = frem double %a, %b
  ret double %r
}
