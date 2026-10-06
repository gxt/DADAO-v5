; TESTCASES-026t / CodeGen vector: call (direct call/ret + integer return value)
; The callee is noinline and its operands come from volatile loads, so the call is
; not inlined and not constant-folded. Return value travels in rd31 (C5).
;
; IR semantics:
;   add3(x, y, z) = x + y + z
;   main: 2 + 3 + 4 = 9
; Expected guest exit code: 9
define i64 @add3(i64 %x, i64 %y, i64 %z) noinline {
entry:
  %t = add i64 %x, %y
  %r = add i64 %t, %z
  ret i64 %r
}

define i64 @main() {
entry:
  %sa = alloca i64, align 8
  %sb = alloca i64, align 8
  %sc = alloca i64, align 8
  store volatile i64 2, i64* %sa, align 8
  store volatile i64 3, i64* %sb, align 8
  store volatile i64 4, i64* %sc, align 8
  %a = load volatile i64, i64* %sa, align 8
  %b = load volatile i64, i64* %sb, align 8
  %c = load volatile i64, i64* %sc, align 8
  %r = call i64 @add3(i64 %a, i64 %b, i64 %c)
  ret i64 %r
}
