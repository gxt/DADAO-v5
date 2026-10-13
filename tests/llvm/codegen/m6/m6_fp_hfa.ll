; M6 CodeGen vector (TESTCASES-036t): HFA (homogeneous floating-point
; aggregate) argument/return ABI.
; A `{double, double}` aggregate is an HFA <= 64 bytes, so it travels entirely
; in the RF bank: the two fields are passed in rf16/rf17 and returned in
; rf8/rf9 (contract-abi.md §6.1/§6.4, SPEC-127t/LLVM-066t).  Both callees are
; noinline so the aggregate ABI is exercised instead of being folded away.
; The L2 register shape is asserted by tests/llvm/lit/CodeGen/DADAO/fp-codegen.ll.
;
; IR semantics:
;   mk(1.5, 2.5) = {1.5, 2.5}
;   sum(v) = v.0 + v.1 = 4.0
;   4.0 > 3.0 -> 42
; Expected guest exit code: 42

%dd = type { double, double }

define %dd @mk(double %a, double %b) noinline {
entry:
  %r0 = insertvalue %dd undef, double %a, 0
  %r1 = insertvalue %dd %r0, double %b, 1
  ret %dd %r1
}

define double @sum(%dd %v) noinline {
entry:
  %a = extractvalue %dd %v, 0
  %b = extractvalue %dd %v, 1
  %s = fadd double %a, %b
  ret double %s
}

define i64 @main() {
entry:
  %v = call %dd @mk(double 1.5, double 2.5)
  %s = call double @sum(%dd %v)
  %c = fcmp ogt double %s, 3.0
  br i1 %c, label %t, label %f
t:
  ret i64 42
f:
  ret i64 7
}
