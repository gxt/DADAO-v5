; TESTCASES-032t / M4 L3 vector -- program "notneg_not", translation unit A (library).
;
; The `not` (bitwise complement) functionality of the deleted `not.o` pseudo is
; expressed with the real 64-bit instruction `xnor.o rd, rc, rd0`, i.e. IR-level
; `xor i64 %x, -1` (complement).  `not` is 64-bit only: the narrow-bit-width
; logic instructions `xnor.b/w/t` were deleted (`SPEC-069t`), so there is no
; 8/16/32-bit `not` to cover.
;
; Coverage:
;   * `.text`        : an exported function called from the other TU.
;   * cross-TU call  : `bitnot64` is undefined in TU B -> R_DADAO_REL26.
;
; IR semantics (host independent oracle):
;   bitnot64(x) = ~x = x xor -1  (64-bit two's complement).

define i64 @bitnot64(i64 %x) noinline {
entry:
  %r = xor i64 %x, -1
  ret i64 %r
}
