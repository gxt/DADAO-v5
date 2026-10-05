; TESTCASES-026t / CodeGen vector: pointer arithmetic (C14 base + offset)
; A runtime (volatile-loaded) offset is added to a base pointer before the access,
; i.e. the intended lowering is base(rb) + offset(rd) (add.o).
;
; IR semantics:
;   off = 20
;   p = &buf[0] + 20
;   p[0] = -85 = 0xAB ; load i8 -> 0xAB
;   r = zext(0xAB) = 171
; Expected guest exit code: 171
define i64 @main() {
entry:
  %buf = alloca [32 x i8], align 8
  %soff = alloca i64, align 8
  store volatile i64 20, i64* %soff, align 8
  %p0 = getelementptr [32 x i8], [32 x i8]* %buf, i64 0, i64 0
  %off = load volatile i64, i64* %soff, align 8
  %p = getelementptr i8, i8* %p0, i64 %off
  store volatile i8 -85, i8* %p, align 1
  %v = load volatile i8, i8* %p, align 1
  %r = zext i8 %v to i64
  ret i64 %r
}
