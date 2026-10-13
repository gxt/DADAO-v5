; TESTCASES-030t / M4 L3 vector -- program "cross_tu_pdiff", TU A (buffer + callee).
;
; Coverage:
;   * `.bss`   : @buf is a non-constant zero-initialised array -> NOBITS.
;   * cross-TU : @buf is addressed from TU B (R_DADAO_ABS48 across TUs) and
;                @pdiff is called from TU B (R_DADAO_REL26).
;   * sign     : @pdiff does a full 64-bit two's-complement pointer difference;
;                the negative result is the raw value 0xFFFFFFFFFFFFFFF9.
;
; IR semantics (host independent oracle):
;   pdiff(a, b) = (i64)a - (i64)b   (full 64-bit signed wraparound)

@buf = global [16 x i8] zeroinitializer, align 8

define i64 @pdiff(i8* %a, i8* %b) noinline {
entry:
  %x = ptrtoint i8* %a to i64
  %y = ptrtoint i8* %b to i64
  %d = sub i64 %x, %y
  ret i64 %d
}
