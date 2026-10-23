;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-126t (ISS-188): `llvm.canonicalize` is the identity on this target.
; There is no x87-style excess precision and every FP operation already
; produces an IEEE canonical result, so canonicalisation must not touch the
; value.  The generic expansion is `x * 1.0` (constant materialisation +
; `fomul`), which is both larger and *less* faithful: it quietens an sNaN and
; can raise NV/NX for no semantic reason.  The lowering returns the operand
; unchanged, so no `fo2fo`/`fomul` and no libcall are emitted.

declare double @llvm.canonicalize.f64(double)
declare float @llvm.canonicalize.f32(float)

define double @canonicalize_f64(double %a, double %b) {
; CHECK-LABEL: canonicalize_f64:
; CHECK-COUNT-1: foadd
; CHECK-NOT:     fomul
; CHECK-NOT:     fo2fo
; CHECK-NOT:     call
  %c = call double @llvm.canonicalize.f64(double %a)
  %r = fadd double %c, %b
  ret double %r
}

define float @canonicalize_f32(float %a, float %b) {
; CHECK-LABEL: canonicalize_f32:
; CHECK-COUNT-1: ftadd
; CHECK-NOT:     ftmul
; CHECK-NOT:     ft2ft
; CHECK-NOT:     call
  %c = call float @llvm.canonicalize.f32(float %a)
  %r = fadd float %c, %b
  ret float %r
}

; canonicalize of a plain returned argument: the only instruction is the
; unavoidable return move, never an arithmetic canonicalisation.
define double @canonicalize_ret(double %a) {
; CHECK-LABEL: canonicalize_ret:
; CHECK-NOT:     fomul
; CHECK-NOT:     call
  %c = call double @llvm.canonicalize.f64(double %a)
  ret double %c
}
