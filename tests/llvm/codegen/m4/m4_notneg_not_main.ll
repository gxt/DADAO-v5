; TESTCASES-032t / M4 L3 vector -- program "notneg_not", translation unit B (main).
;
; Coverage:
;   * cross-TU direct call : `call i64 @bitnot64(...)` -> R_DADAO_REL26.
;   * `.text`              : @main.
;   * boundary cases       : `not 0` -> -1 (0xFFFF...FFFF) and `not -1` -> 0,
;                            plus a general 64-bit pattern.
;
; IR semantics (host independent oracle, 64-bit two's complement):
;   a = bitnot64(0)        = ~0        = 0xFFFFFFFFFFFFFFFF
;   b = bitnot64(-1)       = ~(-1)     = 0
;   c = bitnot64(0x0102030405060708)   = 0xFEFDFCFBFAF9F8F7
;   y = a ^ b ^ c          = 0x0102030405060708
;   fold(y) = ((y * 11400714819323198485) >> 57) & 0x7F = 0x6C
;   -> returns 108 (in 0x00..0x7F).
;
;   The multiplicative fold mixes all 64 bits of `y` into the 7-bit exit code,
;   so a wrong bit in a `~` result - and in particular a wrong complement
;   (`xor 0` instead of `xor -1`) - changes the observed exit code.

declare i64 @bitnot64(i64)

define i64 @main() noinline {
entry:
  %a = call i64 @bitnot64(i64 0)
  %b = call i64 @bitnot64(i64 -1)
  %c = call i64 @bitnot64(i64 72623859790382856)
  %x = xor i64 %a, %b
  %y = xor i64 %x, %c
  %m = mul i64 %y, 11400714819323198485
  %r = lshr i64 %m, 57
  ret i64 %r
}
