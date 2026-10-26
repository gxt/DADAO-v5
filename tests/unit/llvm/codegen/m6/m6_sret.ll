; LLVM-062t / M6 CodeGen vector: aggregate return via hidden sret pointer.
; `fill` returns a 9 x i64 struct (> 8 return slots = 64 bytes), so
; CanLowerReturn is false (contract-abi.md §6.1: at most K=8 per bank) and the
; whole return is demoted to a hidden sret pointer passed as the first address
; argument in rb16; the caller reads the result back from its own stack slot.
;
; IR semantics:
;   fill(x) = { x, x, x, x, x, x, x, x, x }   (9 fields)
;   main: s = fill(3); r = s.field[8] & 127 = 3
; Expected guest exit code: 3
%Big = type { i64, i64, i64, i64, i64, i64, i64, i64, i64 }

define %Big @fill(i64 %x) noinline {
entry:
  %v0 = insertvalue %Big undef, i64 %x, 0
  %v1 = insertvalue %Big %v0, i64 %x, 1
  %v2 = insertvalue %Big %v1, i64 %x, 2
  %v3 = insertvalue %Big %v2, i64 %x, 3
  %v4 = insertvalue %Big %v3, i64 %x, 4
  %v5 = insertvalue %Big %v4, i64 %x, 5
  %v6 = insertvalue %Big %v5, i64 %x, 6
  %v7 = insertvalue %Big %v6, i64 %x, 7
  %v8 = insertvalue %Big %v7, i64 %x, 8
  ret %Big %v8
}

define i64 @main() {
entry:
  %sx = alloca i64, align 8
  store volatile i64 3, ptr %sx, align 8
  %x = load volatile i64, ptr %sx, align 8
  %s = call %Big @fill(i64 %x)
  %e = extractvalue %Big %s, 8
  %m = and i64 %e, 127
  ret i64 %m
}
