; TESTCASES-026t / CodeGen vector: memory (C13 big-endian narrow i16/i32 load + extension)
; A 64-bit value is stored once; i16/i32 lanes are read at non-zero byte offsets.
; Big-endian: i32 @4 = 0x55667788; i16 @0 = 0x1122; i16 @6 = 0x7788.
; Sign extension is made observable in the 0..255 exit channel by extracting the
; replicated sign bits with a logical shift right (see mem_narrow_be_bytes.ll).
;
; IR semantics (big-endian memory):
;   store i64 u0x1122334455667788 -> bytes = 11 22 33 44 55 66 77 88
;   h0 = zext(load i16 @0) = 0x1122 ; a = (h0 >> 8) & 255 = 0x11 = 17   (ld.uw, offset 0)
;   h6 = zext(load i16 @6) = 0x7788 ; b = h6 & 255       = 0x88 = 136   (ld.uw, offset 6)
;   w4 = zext(load i32 @4) = 0x55667788 ; c = (w4 >> 24) & 255 = 0x55 = 85 (ld.ut, offset 4)
;   store i16 -300 @2 ; n = sext(load i16 @2) = -300 ; nhi = (n >> 16) & 255 = 255 (ld.sw, offset 2)
;   store i32 -70000 @0 ; s = sext(load i32 @0) = -70000 ; shi = (s >> 32) & 255 = 255 (ld.st, offset 0)
;   r = (a + b + c + nhi + shi) & 255 = (17 + 136 + 85 + 255 + 255) & 255 = 236
; Expected guest exit code: 236
define i64 @main() {
entry:
  %buf = alloca [8 x i8], align 8
  %q = bitcast [8 x i8]* %buf to i64*
  store volatile i64 u0x1122334455667788, i64* %q, align 8
  %p0 = getelementptr [8 x i8], [8 x i8]* %buf, i64 0, i64 0
  %p2 = getelementptr [8 x i8], [8 x i8]* %buf, i64 0, i64 2
  %p4 = getelementptr [8 x i8], [8 x i8]* %buf, i64 0, i64 4
  %p6 = getelementptr [8 x i8], [8 x i8]* %buf, i64 0, i64 6
  %h0p = bitcast i8* %p0 to i16*
  %h6p = bitcast i8* %p6 to i16*
  %w4p = bitcast i8* %p4 to i32*
  %n2p = bitcast i8* %p2 to i16*
  %s0p = bitcast i8* %p0 to i32*
  %h0 = load volatile i16, i16* %h0p, align 2
  %h6 = load volatile i16, i16* %h6p, align 2
  %w4 = load volatile i32, i32* %w4p, align 4
  %h0z = zext i16 %h0 to i64
  %h6z = zext i16 %h6 to i64
  %w4z = zext i32 %w4 to i64
  %a = lshr i64 %h0z, 8
  %a8 = and i64 %a, 255
  %b = and i64 %h6z, 255
  %c = lshr i64 %w4z, 24
  %c8 = and i64 %c, 255
  store volatile i16 -300, i16* %n2p, align 2
  %n = load volatile i16, i16* %n2p, align 2
  %d = sext i16 %n to i64
  %dhi = lshr i64 %d, 16
  %dhi8 = and i64 %dhi, 255
  %t1 = add i64 %a8, %b
  %t2 = add i64 %t1, %c8
  %t3 = add i64 %t2, %dhi8
  store volatile i32 -70000, i32* %s0p, align 4
  %s = load volatile i32, i32* %s0p, align 4
  %e = sext i32 %s to i64
  %ehi = lshr i64 %e, 32
  %ehi8 = and i64 %ehi, 255
  %t4 = add i64 %t3, %ehi8
  %r = and i64 %t4, 255
  ret i64 %r
}
