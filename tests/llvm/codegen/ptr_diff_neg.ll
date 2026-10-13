; TESTCASES-026t / CodeGen vector: pointer difference (C14 sub.o_orrr_dbb, negative)
; Same as ptr_diff_pos but with the operand order swapped, so the raw result is
; the negative 64-bit two's-complement value -7 (0xFFFFFFFFFFFFFFF9).  It is
; masked with 127 only to keep the guest exit code in 0x00..0x7F (ISS-147),
; clear of the machine-fault range 0x80..0xFF.
;
; IR semantics:
;   p = &buf[10] ; q = &buf[3]
;   d = ptrtoint(q) - ptrtoint(p) = 3 - 10 = -7     (raw 64-bit: 0xFFFFFFFFFFFFFFF9)
;   r = d & 127 = 0x79 = 121
; Expected guest exit code: 121
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
  %d = call i64 @pdiff(i8* %q, i8* %p)
  %r = and i64 %d, 127
  ret i64 %r
}
