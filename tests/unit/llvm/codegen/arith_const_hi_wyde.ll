; TESTCASES-026t / CodeGen vector: arithmetic (C12 high-wyde constant materialisation)
; The 64-bit constant occupies all four 16-bit wydes, forcing a set.zw/or.w sequence.
;
; IR semantics:
;   v  = 0xFEDCBA9876543210
;   hi = lshr v, 56      = 0xFE = 254
;   lo = and v, 255      = 0x10 = 16
;   r  = and (xor hi, lo), 127 = 254 ^ 16 = 238 -> 238 & 127 = 0x6E = 110
; The outer mask is 127 so the guest exit code stays in 0x00..0x7F (ISS-147).
; Expected guest exit code: 110  (in 0x00..0x7F)
define i64 @main() {
entry:
  %s = alloca i64, align 8
  store volatile i64 u0xFEDCBA9876543210, i64* %s, align 8
  %v = load volatile i64, i64* %s, align 8
  %hi = lshr i64 %v, 56
  %lo = and i64 %v, 255
  %x = xor i64 %hi, %lo
  %r = and i64 %x, 127
  ret i64 %r
}
