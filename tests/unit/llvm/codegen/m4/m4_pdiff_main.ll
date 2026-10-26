; TESTCASES-030t / M4 L3 vector -- program "cross_tu_pdiff", TU B (main).
;
; Coverage:
;   * cross-TU direct call : `call i64 @pdiff(...)` -> R_DADAO_REL26.
;   * cross-TU global      : @buf (defined in TU A) is addressed here -> ABS48.
;   * pointer difference   : both signs, computed in 64-bit two's complement.
;   * size/sign sensitive  : the negative difference is 0xFFFFFFFFFFFFFFF9;
;                            only its low 7 bits survive (0x79 = 121).
;
; IR semantics (host independent oracle):
;   p = &buf[10] ; q = &buf[3]
;   d = pdiff(p, q) = 10 - 3 = 7
;   e = pdiff(q, p) = 3 - 10 = -7 = 0xFFFFFFFFFFFFFFF9 (raw 64-bit)
;   m = e & 127 = 0x79 = 121
;   r = d ^ m  = 0x07 ^ 0x79 = 0x7E = 126.
;
;   Exit channel (ADR-0004 D3): the guest exit code is the low byte of @main's
;   return value, so 126 lands safely in 0x00..0x7F.

@buf = external global [16 x i8], align 8

declare i64 @pdiff(i8*, i8*)

define i64 @main() noinline {
entry:
  %p = getelementptr [16 x i8], [16 x i8]* @buf, i64 0, i64 10
  %q = getelementptr [16 x i8], [16 x i8]* @buf, i64 0, i64 3
  %d = call i64 @pdiff(i8* %p, i8* %q)
  %e = call i64 @pdiff(i8* %q, i8* %p)
  %m = and i64 %e, 127
  %r = xor i64 %d, %m
  ret i64 %r
}
