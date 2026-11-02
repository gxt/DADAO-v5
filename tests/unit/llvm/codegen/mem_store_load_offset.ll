; TESTCASES-026t / CodeGen vector: memory (load/store with non-zero element offset)
; Element 1 of an i64 array is at byte offset 8 -> exercises load/store base+imm12.
;
; IR semantics:
;   buf[0] = 100 ; buf[1] = 23
;   r = 100 - 23 = 77
; Expected guest exit code: 77
define i64 @main() {
entry:
  %buf = alloca [2 x i64], align 16
  %p0 = getelementptr [2 x i64], [2 x i64]* %buf, i64 0, i64 0
  %p1 = getelementptr [2 x i64], [2 x i64]* %buf, i64 0, i64 1
  store volatile i64 100, i64* %p0, align 8
  store volatile i64 23, i64* %p1, align 8
  %a = load volatile i64, i64* %p0, align 8
  %b = load volatile i64, i64* %p1, align 8
  %r = sub i64 %a, %b
  ret i64 %r
}
