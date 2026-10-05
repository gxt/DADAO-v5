; TESTCASES-026t / CodeGen vector: arithmetic (C12 constant materialisation, negative operand)
; Inputs live in volatile stack slots so -O2 cannot fold the whole program to a constant.
;
; IR semantics:
;   a = -5        (negative constant -> set.ow / high-wyde materialisation)
;   b = 3
;   c = add a, b  = -2
;   d = sub b, a  = 8
;   e = xor c, d  = -10          (xor keeps both add and sub alive)
;   r = and e, 255 = 246
; Expected guest exit code (i64 return of @main): 246  (in 0..255)
define i64 @main() {
entry:
  %sa = alloca i64, align 8
  %sb = alloca i64, align 8
  store volatile i64 -5, i64* %sa, align 8
  store volatile i64 3, i64* %sb, align 8
  %a = load volatile i64, i64* %sa, align 8
  %b = load volatile i64, i64* %sb, align 8
  %c = add i64 %a, %b
  %d = sub i64 %b, %a
  %e = xor i64 %c, %d
  %r = and i64 %e, 255
  ret i64 %r
}
