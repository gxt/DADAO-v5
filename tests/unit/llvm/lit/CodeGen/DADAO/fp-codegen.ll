;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-066t (M6): FP/RF codegen.  Contracts: contract-abi.md §4/§6 (FP
; argument registers rf16..rf31, FP return registers rf8..rf15, HFA via RF),
; contract-fp.md §2/§5/§8 (format conversion, S2D1 arithmetic, compare).
;
;   * `double f(double, double)` -> args rf16/rf17, return rf8;
;     the f64 S2D1 ops select fo{add,sub,mul,div};
;   * an HFA `{double,double}` -> return rf8/rf9, args rf16/rf17;
;   * fptosi -> fo2io, sitofp -> io2fo;
;   * fcmp -> foqcmp (result in rd, feeding br.*).
;

; CHECK-LABEL: fp_arith:
; CHECK:         fodiv rf{{[0-9]+}}, rf16, rf17
; CHECK:         fomul rf{{[0-9]+}}, rf16, rf17
; CHECK:         foadd rf8,
define double @fp_arith(double %a, double %b) {
  %m = fmul double %a, %b
  %d = fdiv double %a, %b
  %s = fadd double %m, %d
  ret double %s
}

; CHECK-LABEL: fp_to_i:
; CHECK:         fo2io {rd8}, {rf16}
define i64 @fp_to_i(double %a) {
  %i = fptosi double %a to i64
  ret i64 %i
}

; CHECK-LABEL: i_to_fp:
; CHECK:         io2fo {rf8}, {rd16}
define double @i_to_fp(i64 %a) {
  %f = sitofp i64 %a to double
  ret double %f
}

; CHECK-LABEL: fp_cmp:
; CHECK:         foqcmp rd{{[0-9]+}}, rf16, rf17
define double @fp_cmp(double %a, double %b, double %x, double %y) {
  %c = fcmp olt double %a, %b
  br i1 %c, label %t, label %f
t:
  ret double %x
f:
  ret double %y
}

; CHECK-LABEL: mkpair:
; CHECK-DAG:     fo2fo {rf8},
; CHECK-DAG:     fo2fo {rf9},
define { double, double } @mkpair(double %a, double %b) {
  %1 = insertvalue { double, double } undef, double %a, 0
  %2 = insertvalue { double, double } %1, double %b, 1
  ret { double, double } %2
}

; RF callee-saved registers (rf32..rf63, contract-abi.md §1.4) are used for
; values live across a call and must be spilled/restored (getCalleeSavedRegs
; agrees with the generated CSR_RegMask).
; CHECK-LABEL: csr_fp:
; CHECK-DAG:     st.o rf32, [rb1, {{[0-9]+}}]
; CHECK-DAG:     ld.o rf32, [rb1, {{[0-9]+}}]
declare void @clobber(double)
define double @csr_fp(double %a, double %b, double %c, double %d,
                      double %e, double %f, double %g, double %h) {
  %1 = fadd double %a, %b
  %2 = fadd double %c, %d
  %3 = fadd double %e, %f
  %4 = fadd double %g, %h
  call void @clobber(double %1)
  %5 = fadd double %1, %2
  %6 = fadd double %3, %4
  %7 = fadd double %5, %6
  ret double %7
}
