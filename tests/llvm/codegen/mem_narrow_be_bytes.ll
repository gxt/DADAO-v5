; TESTCASES-026t / CodeGen vector: memory (C13 big-endian narrow byte load + sign extension)
; A 64-bit value is stored once, then read back byte-by-byte at explicit byte offsets.
; Big-endian layout: offset 0 holds the most-significant byte (0x01), offset 7 the least (0x08).
; The byte at offset 3 is overwritten with -2 to exercise a sign-extended byte load (ld.sb).
; The sign of the loaded byte is made *observable in the 0..255 exit channel* by
; extracting the sign bits with a logical right shift (a plain low-byte mask would
; not distinguish sign- from zero-extension, since they agree modulo 256).
;
; IR semantics (big-endian memory):
;   store i64 u0x0102030405060708 -> bytes[0..7] = 01 02 03 04 05 06 07 08
;   store i8 -2 at offset 3       -> bytes[3] = 0xFE
;   b0  = zext(load i8 @0) = 0x01 = 1                 (ld.ub, offset 0)
;   b7  = zext(load i8 @7) = 0x08 = 8                 (ld.ub, offset 7)
;   s3  = sext(load i8 @3) = -2 = 0xFFFFFFFFFFFFFFFE   (ld.sb, offset 3)
;   shi = (s3 >> 8) & 255  = 0xFF = 255                (sign bits observable)
;   r   = (b0*10 + b7*100 + shi) & 255 = (10 + 800 + 255) & 255 = 41
; Expected guest exit code: 41
define i64 @main() {
entry:
  %buf = alloca [8 x i8], align 8
  %q = bitcast [8 x i8]* %buf to i64*
  store volatile i64 u0x0102030405060708, i64* %q, align 8
  %p0 = getelementptr [8 x i8], [8 x i8]* %buf, i64 0, i64 0
  %p3 = getelementptr [8 x i8], [8 x i8]* %buf, i64 0, i64 3
  %p7 = getelementptr [8 x i8], [8 x i8]* %buf, i64 0, i64 7
  store volatile i8 -2, i8* %p3, align 1
  %b0 = load volatile i8, i8* %p0, align 1
  %b7 = load volatile i8, i8* %p7, align 1
  %s3 = load volatile i8, i8* %p3, align 1
  %b0z = zext i8 %b0 to i64
  %b7z = zext i8 %b7 to i64
  %s3s = sext i8 %s3 to i64
  %shi = lshr i64 %s3s, 8
  %shi8 = and i64 %shi, 255
  %t1 = mul i64 %b0z, 10
  %t2 = mul i64 %b7z, 100
  %t3 = add i64 %t1, %t2
  %t4 = add i64 %t3, %shi8
  %r = and i64 %t4, 255
  ret i64 %r
}
