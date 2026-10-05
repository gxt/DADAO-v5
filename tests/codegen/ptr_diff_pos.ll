; TESTCASES-026t / CodeGen vector: pointer difference (C14 sub.o_orrr_dbb, positive)
; Two pointers into the same array are converted to integers and subtracted
; (ptr - ptr).  Both operands are pointer formal parameters, so they live in
; GPRB and the subtraction is selected as the single-instruction RB-RB->RD
; `sub.o_orrr_dbb` (IR semantics: difference of the two absolute addresses).
;
; IR semantics:
;   p = &buf[10] ; q = &buf[3]
;   r = ptrtoint(p) - ptrtoint(q) = 10 - 3 = 7
; Expected guest exit code: 7
define i64 @pdiff(i8* %a, i8* %b) noinline {
entry:
  %x = ptrtoint i8* %a to i64
  %y = ptrtoint i8* %b to i64
  %d = sub i64 %x, %y
  ret i64 %d
}

define i64 @main() {
entry:
  %buf = alloca [16 x i8], align 8
  %p = getelementptr [16 x i8], [16 x i8]* %buf, i64 0, i64 10
  %q = getelementptr [16 x i8], [16 x i8]* %buf, i64 0, i64 3
  %d = call i64 @pdiff(i8* %p, i8* %q)
  ret i64 %d
}
