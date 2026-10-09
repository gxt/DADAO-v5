; M6 CodeGen vector (TESTCASES-036t): FP arithmetic (RF) end-to-end.
; The f64 S2D1 operations lower to the hardware FP instructions (fomul/fodiv/
; foadd), the FP compare lowers to foqcmp feeding a `br.*` (contract-fp.md
; §2/§5; LLVM-066t).  This is the L3 execution vector: the computed double
; must actually be produced and the branch taken.
;
; The inputs live in `alloca` slots read with volatile loads so llc cannot
; constant-fold the computation away; the result comparison stays an
; `fcmp` + branch (the backend has no FP setcc-as-value).
;
; IR semantics:
;   a = 3.0, b = 2.0
;   m = a * b = 6.0 ; d = a / b = 1.5 ; s = m + d = 7.5
;   s > 6.0  -> 42   (IEEE-754 double arithmetic)
; Expected guest exit code: 42

define i64 @main() {
entry:
  %pa = alloca double, align 8
  %pb = alloca double, align 8
  store volatile double 3.0, ptr %pa, align 8
  store volatile double 2.0, ptr %pb, align 8
  %a = load volatile double, ptr %pa, align 8
  %b = load volatile double, ptr %pb, align 8
  %m = fmul double %a, %b
  %d = fdiv double %a, %b
  %s = fadd double %m, %d
  %c = fcmp ogt double %s, 6.0
  br i1 %c, label %t, label %f
t:
  ret i64 42
f:
  ret i64 7
}
