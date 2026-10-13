; M6 CodeGen vector (TESTCASES-036t): large-frame addressing forms.
; `big1` has a ~60000-byte frame, whose object offset exceeds the 12-bit
; load/store immediate but fits the 18-bit `add.si` (form 2: rb2rb + add.si);
; `big2` has a ~200000-byte frame, whose offset exceeds the 18-bit `add.si`,
; so the constant is materialised with set.zw/or.w and folded with add.o
; (form 3).  (ADR-0018 C7 D4 rev. 2026-10-08; ISS-138 closed by LLVM-064t.)
;
; The L2 structural shapes (form 1/2/3 selection) are asserted by
; tests/llvm/lit/CodeGen/DADAO/m6-large-frame.ll; this program is the L3
; execution vector: it must actually run and return the right value.
;
; IR semantics:
;   big1(): store i8 1 into mid[0]; load it back -> 1
;   big2(): store i8 1 into big[0]; load it back -> 1
;   main:  r = (big1() + big2()) & 127 = (1 + 1) & 127 = 2
; Expected guest exit code: 2

define i64 @big1() noinline {
entry:
  %mid = alloca [60000 x i8], align 8
  store volatile i8 1, ptr %mid, align 1
  %r = load volatile i8, ptr %mid, align 1
  %e = zext i8 %r to i64
  ret i64 %e
}

define i64 @big2() noinline {
entry:
  %big = alloca [200000 x i8], align 8
  store volatile i8 1, ptr %big, align 1
  %r = load volatile i8, ptr %big, align 1
  %e = zext i8 %r to i64
  ret i64 %e
}

define i64 @main() {
entry:
  %a = call i64 @big1()
  %b = call i64 @big2()
  %t = add i64 %a, %b
  %m = and i64 %t, 127
  ret i64 %m
}
