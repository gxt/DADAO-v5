; LLVM-062t / M6 CodeGen vector: multiple return values.
; `pair` returns {i64, i64}; per contract-abi.md §6.1 the two values travel in
; rd8 and rd9 (first value at index 8, next +1 in the same bank).  The callee is
; noinline so the aggregate return is not scalarized away.
;
; IR semantics:
;   pair(a, b) = { a + b, a - b }
;   main: p = pair(50, 8) = {58, 42}; r = 58 - 42 = 16 -> &127 = 16
; Expected guest exit code: 16
define { i64, i64 } @pair(i64 %a, i64 %b) noinline {
entry:
  %s = add i64 %a, %b
  %d = sub i64 %a, %b
  %r0 = insertvalue { i64, i64 } undef, i64 %s, 0
  %r1 = insertvalue { i64, i64 } %r0, i64 %d, 1
  ret { i64, i64 } %r1
}

define i64 @main() {
entry:
  %sa = alloca i64, align 8
  %sb = alloca i64, align 8
  store volatile i64 50, ptr %sa, align 8
  store volatile i64 8, ptr %sb, align 8
  %a = load volatile i64, ptr %sa, align 8
  %b = load volatile i64, ptr %sb, align 8
  %p = call { i64, i64 } @pair(i64 %a, i64 %b)
  %x = extractvalue { i64, i64 } %p, 0
  %y = extractvalue { i64, i64 } %p, 1
  %r = sub i64 %x, %y
  %m = and i64 %r, 127
  ret i64 %m
}
