;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-124t (M9; contract-fp.md §minmax = SimRISC-07 §2.4): the ISA's
; `ftmin`/`ftmax`/`fomin`/`fomax` ARE IEEE 754-2019
; minimumNumber/maximumNumber -- single NaN (qNaN or sNaN) returns the other
; operand, double NaN returns the canonical qNaN, an sNaN input raises NV,
; `-0 < +0`, no rounding -- so the LLVM nodes with exactly that semantics
; select ONE instruction, with no compare sequence and no libcall:
;
;   llvm.minnum / llvm.maxnum            (FMINNUM/FMAXNUM, Custom)
;       -> FMINNUM_IEEE/FMAXNUM_IEEE     -> fomin / fomax   (1 instruction)
;   llvm.minimumnum / llvm.maximumnum    (FMINIMUMNUM/...)
;       ->                                  fomin / fomax   (1 instruction)
;   f32 variants                           -> ftmin / ftmax (1 instruction)
;
; `llvm.minimum`/`llvm.maximum` are the NaN-*propagating* 754-2019 forms and
; the ISA has no such instruction (contract-fp.md §minmax 负向约束), so they
; stay `Expand`: LLVM derives them from FMINNUM_IEEE/FMAXNUM_IEEE plus a SETUO
; NaN select.  That expansion is 9 instructions here (foqcmp to get the
; unordered flag, cmp.si + cs.p to materialise the flag, the fomin itself, and
; a 2-instruction canonical-qNaN constant + cs.z to select it) -- asserted
; below by one fomin plus exactly one foqcmp/cs.p/cs.z and no libcall.
;
; Because the hardware already orders `-0 < +0`, the expansion must NOT add the
; `SETOEQ` signed-zero fixup LLVM emits for targets whose min/max cannot tell
; the zeros apart (`MinMaxMustRespectOrderedZero`): that fixup re-compares with
; SETOEQ (a SECOND foqcmp) and classifies the zero with an `andn.w`/`set.ow`
; mask sequence, so the COUNT-1 foqcmp and the CHECK-NOT andn.w below are its
; reachable counter-example.
;
; These instructions are still `scope: excluded` in contracts/opcodes.yaml, so
; execution ILLIs until SPEC-160t flips them; selection is implemented here so
; the flip needs no CodeGen change.

declare double @llvm.minnum.f64(double, double)
declare double @llvm.maxnum.f64(double, double)
declare double @llvm.minimumnum.f64(double, double)
declare double @llvm.maximumnum.f64(double, double)
declare double @llvm.minimum.f64(double, double)
declare double @llvm.maximum.f64(double, double)
declare float @llvm.minnum.f32(float, float)
declare float @llvm.maxnum.f32(float, float)
declare float @llvm.minimumnum.f32(float, float)

; --- minnum / maxnum: one `fomin` / `fomax`, nothing else in the body ---
; The CHECK-NOT of a lowercase-starting line brackets the two positive matches,
; so "one instruction" is asserted as a *total*, not just as a mnemonic count
; (the `@@ %bb.0:` block comment does not start with a lowercase letter).
define double @f64_minnum(double %a, double %b) {
; CHECK-LABEL: f64_minnum:
; CHECK-NOT: {{^[a-z]}}
; CHECK: fomin rf{{[0-9]+}}, rf{{[0-9]+}}, rf{{[0-9]+}}
; CHECK-NOT: {{^[a-z]}}
; CHECK: ret rd0, 0
  %r = call double @llvm.minnum.f64(double %a, double %b)
  ret double %r
}

define double @f64_maxnum(double %a, double %b) {
; CHECK-LABEL: f64_maxnum:
; CHECK-NOT: {{^[a-z]}}
; CHECK: fomax rf{{[0-9]+}}, rf{{[0-9]+}}, rf{{[0-9]+}}
; CHECK-NOT: {{^[a-z]}}
; CHECK: ret rd0, 0
  %r = call double @llvm.maxnum.f64(double %a, double %b)
  ret double %r
}

; --- minimumnum / maximumnum: the same two instructions ---
define double @f64_minimumnum(double %a, double %b) {
; CHECK-LABEL: f64_minimumnum:
; CHECK-NOT: {{^[a-z]}}
; CHECK: fomin rf{{[0-9]+}}, rf{{[0-9]+}}, rf{{[0-9]+}}
; CHECK-NOT: {{^[a-z]}}
; CHECK: ret rd0, 0
  %r = call double @llvm.minimumnum.f64(double %a, double %b)
  ret double %r
}

define double @f64_maximumnum(double %a, double %b) {
; CHECK-LABEL: f64_maximumnum:
; CHECK-NOT: {{^[a-z]}}
; CHECK: fomax rf{{[0-9]+}}, rf{{[0-9]+}}, rf{{[0-9]+}}
; CHECK-NOT: {{^[a-z]}}
; CHECK: ret rd0, 0
  %r = call double @llvm.maximumnum.f64(double %a, double %b)
  ret double %r
}

; --- f32: the ft forms (ftmin / ftmax) ---
define float @f32_minnum(float %a, float %b) {
; CHECK-LABEL: f32_minnum:
; CHECK-NOT: {{^[a-z]}}
; CHECK: ftmin rf{{[0-9]+}}, rf{{[0-9]+}}, rf{{[0-9]+}}
; CHECK-NOT: {{^[a-z]}}
; CHECK: ret rd0, 0
  %r = call float @llvm.minnum.f32(float %a, float %b)
  ret float %r
}

define float @f32_maxnum(float %a, float %b) {
; CHECK-LABEL: f32_maxnum:
; CHECK-NOT: {{^[a-z]}}
; CHECK: ftmax rf{{[0-9]+}}, rf{{[0-9]+}}, rf{{[0-9]+}}
; CHECK-NOT: {{^[a-z]}}
; CHECK: ret rd0, 0
  %r = call float @llvm.maxnum.f32(float %a, float %b)
  ret float %r
}

define float @f32_minimumnum(float %a, float %b) {
; CHECK-LABEL: f32_minimumnum:
; CHECK-NOT: {{^[a-z]}}
; CHECK: ftmin rf{{[0-9]+}}, rf{{[0-9]+}}, rf{{[0-9]+}}
; CHECK-NOT: {{^[a-z]}}
; CHECK: ret rd0, 0
  %r = call float @llvm.minimumnum.f32(float %a, float %b)
  ret float %r
}

; --- minimum / maximum: fomin/fomax + SETUO NaN select, no libcall ---
define double @f64_minimum(double %a, double %b) {
; CHECK-LABEL: f64_minimum:
; CHECK-NOT: set.ow
; CHECK-NOT: andn.w
; CHECK-NOT: call
; CHECK-COUNT-1: foqcmp
; CHECK-COUNT-1: cs.p
; CHECK-COUNT-1: fomin rf{{[0-9]+}}, rf{{[0-9]+}}, rf{{[0-9]+}}
; CHECK-COUNT-1: cs.z
; CHECK-NOT: set.ow
; CHECK-NOT: andn.w
; CHECK-NOT: call
  %r = call double @llvm.minimum.f64(double %a, double %b)
  ret double %r
}

define double @f64_maximum(double %a, double %b) {
; CHECK-LABEL: f64_maximum:
; CHECK-NOT: set.ow
; CHECK-NOT: andn.w
; CHECK-NOT: call
; CHECK-COUNT-1: foqcmp
; CHECK-COUNT-1: cs.p
; CHECK-COUNT-1: fomax rf{{[0-9]+}}, rf{{[0-9]+}}, rf{{[0-9]+}}
; CHECK-COUNT-1: cs.z
; CHECK-NOT: set.ow
; CHECK-NOT: andn.w
; CHECK-NOT: call
  %r = call double @llvm.maximum.f64(double %a, double %b)
  ret double %r
}
