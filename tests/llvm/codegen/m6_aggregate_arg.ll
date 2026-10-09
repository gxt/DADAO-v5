; LLVM-062t / M6 CodeGen vector: aggregate arguments.
;   * `sum_small` takes a 16-byte { i64, i64 } by value: it fits <= 64 bytes, so
;     it is split into two 8-byte chunks passed in the RD bank (rd16, rd17);
;   * `sum_big` takes a 72-byte struct byval (> 64 bytes): it is passed
;     indirectly as a pointer (the caller copies it to the stack and passes the
;     address in the RB bank, rb16).
; Both callees are noinline so the aggregate ABI is exercised, not folded away.
;
; IR semantics:
;   small = {40, 2};  sum_small(small) = 40 + 2 = 42
;   big.field[8] = 9; sum_big(big)      = 9
;   main: r = (42 + 9) & 127 = 51
; Expected guest exit code: 51
%Small = type { i64, i64 }
%Big = type { i64, i64, i64, i64, i64, i64, i64, i64, i64 }

define i64 @sum_small(%Small %s) noinline {
entry:
  %a = extractvalue %Small %s, 0
  %b = extractvalue %Small %s, 1
  %r = add i64 %a, %b
  ret i64 %r
}

define i64 @sum_big(ptr byval(%Big) %p) noinline {
entry:
  %e = getelementptr %Big, ptr %p, i64 0, i32 8
  %v = load i64, ptr %e, align 8
  ret i64 %v
}

define i64 @main() {
entry:
  %sa = alloca i64, align 8
  %sb = alloca i64, align 8
  store volatile i64 40, ptr %sa, align 8
  store volatile i64 2, ptr %sb, align 8
  %a = load volatile i64, ptr %sa, align 8
  %b = load volatile i64, ptr %sb, align 8
  %s0 = insertvalue %Small undef, i64 %a, 0
  %s1 = insertvalue %Small %s0, i64 %b, 1
  %r1 = call i64 @sum_small(%Small %s1)

  %big = alloca %Big, align 8
  %e = getelementptr %Big, ptr %big, i64 0, i32 8
  store volatile i64 9, ptr %e, align 8
  %r2 = call i64 @sum_big(ptr byval(%Big) %big)

  %t = add i64 %r1, %r2
  %m = and i64 %t, 127
  ret i64 %m
}
