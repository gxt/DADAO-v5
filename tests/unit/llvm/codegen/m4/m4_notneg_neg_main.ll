; TESTCASES-032t / M4 L3 vector -- program "notneg_neg", translation unit B (main).
;
; Coverage:
;   * cross-TU direct call : `call i64 @neg8/16/32/64(...)` -> R_DADAO_REL26.
;   * `.text`              : @main.
;   * size/sign sensitive  : every width's INT_MIN negation wraps to the same
;                            bit pattern (0x80..) and is sign-extended to i64;
;                            the 8-bit `0x80` case is the sign-extension
;                            boundary.  `neg 0` -> 0.
;
; IR semantics (host independent oracle, 64-bit two's complement):
;   a = neg8(128)              ; trunc 0x80; 0-0x80 = 0x80; sext -> -128
;                              ;   = 0xFFFFFFFFFFFFFF80   (INT8_MIN)
;   b = neg16(32768)           ; = 0xFFFFFFFFFFFF8000   (INT16_MIN)
;   c = neg32(2147483648)      ; = 0xFFFFFFFF80000000   (INT32_MIN)
;   d = neg64(-9223372036854775808) ; = 0x8000000000000000 (INT64_MIN)
;   e = neg64(0)               ; = 0                    (neg 0)
;   g = neg8(64)               ; 0xC0; sext -> 0xFFFFFFFFFFFFFFC0
;   x5 = a^b^c^d^e^g           ; = 0x800000007FFF8040
;   fold(x5) = ((x5 * 11400714819323198485) >> 57) & 0x7F = 0x08
;   -> returns 8 (in 0x00..0x7F).
;
;   The multiplicative fold mixes all 64 bits of `x5` into the 7-bit exit code,
;   so a wrong bit (including a wrong sign extension or a wrong INT_MIN
;   negation) changes the observed exit code.

declare i64 @neg8(i64)
declare i64 @neg16(i64)
declare i64 @neg32(i64)
declare i64 @neg64(i64)

define i64 @main() noinline {
entry:
  %a = call i64 @neg8(i64 128)
  %b = call i64 @neg16(i64 32768)
  %c = call i64 @neg32(i64 2147483648)
  %d = call i64 @neg64(i64 -9223372036854775808)
  %e = call i64 @neg64(i64 0)
  %g = call i64 @neg8(i64 64)
  %x1 = xor i64 %a, %b
  %x2 = xor i64 %x1, %c
  %x3 = xor i64 %x2, %d
  %x4 = xor i64 %x3, %e
  %x5 = xor i64 %x4, %g
  %m = mul i64 %x5, 11400714819323198485
  %r = lshr i64 %m, 57
  ret i64 %r
}
