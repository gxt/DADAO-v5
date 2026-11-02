; LLVM-140t / CodeGen runtime vector: narrow canonical extension of a narrow
; `sub 0, x` whose *extend result is itself narrow* (i32 or i16), i.e. the
; operand of the extend is a narrow negation widened only part-way.  Before the
; fix the DADAO ISel built the `ext.*` node with result type i64 and
; ReplaceNode()d it into the narrow extend node, tripping the
; SelectionDAG::ReplaceAllUsesWith type assertion at -O2 (McCat/18-imp
; L_canny.c, function dfilter: `%conv13 = sub i16 0, %0` truncated from an i32,
; then `sext i16 -> i32`).
;
; Each case truncates a volatile-loaded i32 to i8/i16, negates it at that
; width, widens it (sext or zext) back to i32/i16 and compares against an
; *independently derived* expected value, also volatile-loaded so that neither
; the IR optimizer nor the DAG combiner can fold the negation away (a constant
; comparison makes InstCombine rewrite the whole expression, which is why the
; expectation is data).  The expected values come from LLVM IR semantics:
; wrap the negation at the narrow width, then sign-/zero-extend from it.  They
; cover the sign bit, max, and truncation boundaries, both directions, both
; widths (i16->i32, i8->i32, i8->i16).
;
; @main returns the number of mismatches (masked to 7 bits), so a wrong
; extension direction, width or a missing negation makes the guest exit code
; non-zero.  Expected guest exit code: 0.
target triple = "dadao-unknown-elf"

define i64 @main() {
entry:
  ; x = 0x1 -> n16 = 0xffff -> sext i32 = -1
  %x0_s = alloca i32, align 4
  %exp0_s = alloca i32, align 4
  store volatile i32 1, ptr %x0_s, align 4
  store volatile i32 -1, ptr %exp0_s, align 4
  %x0 = load volatile i32, ptr %x0_s, align 4
  %exp0 = load volatile i32, ptr %exp0_s, align 4
  %t0 = trunc i32 %x0 to i16
  %n0 = sub i16 0, %t0
  %e0 = sext i16 %n0 to i32
  %c0 = icmp ne i32 %e0, %exp0
  %z0 = zext i1 %c0 to i32

  ; x = 0x8000 -> n16 = 0x8000 -> sext i32 = -32768
  %x1_s = alloca i32, align 4
  %exp1_s = alloca i32, align 4
  store volatile i32 32768, ptr %x1_s, align 4
  store volatile i32 -32768, ptr %exp1_s, align 4
  %x1 = load volatile i32, ptr %x1_s, align 4
  %exp1 = load volatile i32, ptr %exp1_s, align 4
  %t1 = trunc i32 %x1 to i16
  %n1 = sub i16 0, %t1
  %e1 = sext i16 %n1 to i32
  %c1 = icmp ne i32 %e1, %exp1
  %z1 = zext i1 %c1 to i32

  ; x = 0x7fff -> n16 = 0x8001 -> sext i32 = -32767
  %x2_s = alloca i32, align 4
  %exp2_s = alloca i32, align 4
  store volatile i32 32767, ptr %x2_s, align 4
  store volatile i32 -32767, ptr %exp2_s, align 4
  %x2 = load volatile i32, ptr %x2_s, align 4
  %exp2 = load volatile i32, ptr %exp2_s, align 4
  %t2 = trunc i32 %x2 to i16
  %n2 = sub i16 0, %t2
  %e2 = sext i16 %n2 to i32
  %c2 = icmp ne i32 %e2, %exp2
  %z2 = zext i1 %c2 to i32

  ; x = 0x12345678 -> n16 = 0xa988 -> sext i32 = -22136
  %x3_s = alloca i32, align 4
  %exp3_s = alloca i32, align 4
  store volatile i32 305419896, ptr %x3_s, align 4
  store volatile i32 -22136, ptr %exp3_s, align 4
  %x3 = load volatile i32, ptr %x3_s, align 4
  %exp3 = load volatile i32, ptr %exp3_s, align 4
  %t3 = trunc i32 %x3 to i16
  %n3 = sub i16 0, %t3
  %e3 = sext i16 %n3 to i32
  %c3 = icmp ne i32 %e3, %exp3
  %z3 = zext i1 %c3 to i32

  ; x = 0x1 -> n16 = 0xffff -> zext i32 = 65535
  %x4_s = alloca i32, align 4
  %exp4_s = alloca i32, align 4
  store volatile i32 1, ptr %x4_s, align 4
  store volatile i32 65535, ptr %exp4_s, align 4
  %x4 = load volatile i32, ptr %x4_s, align 4
  %exp4 = load volatile i32, ptr %exp4_s, align 4
  %t4 = trunc i32 %x4 to i16
  %n4 = sub i16 0, %t4
  %e4 = zext i16 %n4 to i32
  %c4 = icmp ne i32 %e4, %exp4
  %z4 = zext i1 %c4 to i32

  ; x = 0x8000 -> n16 = 0x8000 -> zext i32 = 32768
  %x5_s = alloca i32, align 4
  %exp5_s = alloca i32, align 4
  store volatile i32 32768, ptr %x5_s, align 4
  store volatile i32 32768, ptr %exp5_s, align 4
  %x5 = load volatile i32, ptr %x5_s, align 4
  %exp5 = load volatile i32, ptr %exp5_s, align 4
  %t5 = trunc i32 %x5 to i16
  %n5 = sub i16 0, %t5
  %e5 = zext i16 %n5 to i32
  %c5 = icmp ne i32 %e5, %exp5
  %z5 = zext i1 %c5 to i32

  ; x = 0x12345678 -> n16 = 0xa988 -> zext i32 = 43400
  %x6_s = alloca i32, align 4
  %exp6_s = alloca i32, align 4
  store volatile i32 305419896, ptr %x6_s, align 4
  store volatile i32 43400, ptr %exp6_s, align 4
  %x6 = load volatile i32, ptr %x6_s, align 4
  %exp6 = load volatile i32, ptr %exp6_s, align 4
  %t6 = trunc i32 %x6 to i16
  %n6 = sub i16 0, %t6
  %e6 = zext i16 %n6 to i32
  %c6 = icmp ne i32 %e6, %exp6
  %z6 = zext i1 %c6 to i32

  ; x = 0x1 -> n8 = 0xff -> sext i32 = -1
  %x7_s = alloca i32, align 4
  %exp7_s = alloca i32, align 4
  store volatile i32 1, ptr %x7_s, align 4
  store volatile i32 -1, ptr %exp7_s, align 4
  %x7 = load volatile i32, ptr %x7_s, align 4
  %exp7 = load volatile i32, ptr %exp7_s, align 4
  %t7 = trunc i32 %x7 to i8
  %n7 = sub i8 0, %t7
  %e7 = sext i8 %n7 to i32
  %c7 = icmp ne i32 %e7, %exp7
  %z7 = zext i1 %c7 to i32

  ; x = 0x80 -> n8 = 0x80 -> sext i32 = -128
  %x8_s = alloca i32, align 4
  %exp8_s = alloca i32, align 4
  store volatile i32 128, ptr %x8_s, align 4
  store volatile i32 -128, ptr %exp8_s, align 4
  %x8 = load volatile i32, ptr %x8_s, align 4
  %exp8 = load volatile i32, ptr %exp8_s, align 4
  %t8 = trunc i32 %x8 to i8
  %n8 = sub i8 0, %t8
  %e8 = sext i8 %n8 to i32
  %c8 = icmp ne i32 %e8, %exp8
  %z8 = zext i1 %c8 to i32

  ; x = 0x7f -> n8 = 0x81 -> sext i32 = -127
  %x9_s = alloca i32, align 4
  %exp9_s = alloca i32, align 4
  store volatile i32 127, ptr %x9_s, align 4
  store volatile i32 -127, ptr %exp9_s, align 4
  %x9 = load volatile i32, ptr %x9_s, align 4
  %exp9 = load volatile i32, ptr %exp9_s, align 4
  %t9 = trunc i32 %x9 to i8
  %n9 = sub i8 0, %t9
  %e9 = sext i8 %n9 to i32
  %c9 = icmp ne i32 %e9, %exp9
  %z9 = zext i1 %c9 to i32

  ; x = 0x80 -> n8 = 0x80 -> zext i32 = 128
  %x10_s = alloca i32, align 4
  %exp10_s = alloca i32, align 4
  store volatile i32 128, ptr %x10_s, align 4
  store volatile i32 128, ptr %exp10_s, align 4
  %x10 = load volatile i32, ptr %x10_s, align 4
  %exp10 = load volatile i32, ptr %exp10_s, align 4
  %t10 = trunc i32 %x10 to i8
  %n10 = sub i8 0, %t10
  %e10 = zext i8 %n10 to i32
  %c10 = icmp ne i32 %e10, %exp10
  %z10 = zext i1 %c10 to i32

  ; x = 0x12345681 -> n8 = 0x7f -> zext i32 = 127
  %x11_s = alloca i32, align 4
  %exp11_s = alloca i32, align 4
  store volatile i32 305419905, ptr %x11_s, align 4
  store volatile i32 127, ptr %exp11_s, align 4
  %x11 = load volatile i32, ptr %x11_s, align 4
  %exp11 = load volatile i32, ptr %exp11_s, align 4
  %t11 = trunc i32 %x11 to i8
  %n11 = sub i8 0, %t11
  %e11 = zext i8 %n11 to i32
  %c11 = icmp ne i32 %e11, %exp11
  %z11 = zext i1 %c11 to i32

  ; x = 0x80 -> n8 = 0x80 -> sext i16 = -128
  %x12_s = alloca i32, align 4
  %exp12_s = alloca i16, align 2
  store volatile i32 128, ptr %x12_s, align 4
  store volatile i16 -128, ptr %exp12_s, align 2
  %x12 = load volatile i32, ptr %x12_s, align 4
  %exp12 = load volatile i16, ptr %exp12_s, align 2
  %t12 = trunc i32 %x12 to i8
  %n12 = sub i8 0, %t12
  %e12 = sext i8 %n12 to i16
  %c12 = icmp ne i16 %e12, %exp12
  %z12 = zext i1 %c12 to i32

  ; x = 0x80 -> n8 = 0x80 -> zext i16 = 128
  %x13_s = alloca i32, align 4
  %exp13_s = alloca i16, align 2
  store volatile i32 128, ptr %x13_s, align 4
  store volatile i16 128, ptr %exp13_s, align 2
  %x13 = load volatile i32, ptr %x13_s, align 4
  %exp13 = load volatile i16, ptr %exp13_s, align 2
  %t13 = trunc i32 %x13 to i8
  %n13 = sub i8 0, %t13
  %e13 = zext i8 %n13 to i16
  %c13 = icmp ne i16 %e13, %exp13
  %z13 = zext i1 %c13 to i32
  ; --- mismatch count, masked to 7 bits (no machine-fault exit code) ---
  %m0 = add i32 %z0, %z1
  %m1 = add i32 %m0, %z2
  %m2 = add i32 %m1, %z3
  %m3 = add i32 %m2, %z4
  %m4 = add i32 %m3, %z5
  %m5 = add i32 %m4, %z6
  %m6 = add i32 %m5, %z7
  %m7 = add i32 %m6, %z8
  %m8 = add i32 %m7, %z9
  %m9 = add i32 %m8, %z10
  %m10 = add i32 %m9, %z11
  %m11 = add i32 %m10, %z12
  %m12 = add i32 %m11, %z13
  %m64 = zext i32 %m12 to i64
  %r = and i64 %m64, 127
  ret i64 %r
}
