; LLVM-138t / CodeGen runtime vector: narrow integer canonical
; extension folding (i8/i16/i32 producer consumed by an exact i64 sext/zext).
;
; Each case computes one narrow operation on volatile-loaded operands (so the
; producer survives to instruction selection) and compares its 64-bit extended
; result with a constant derived here from LLVM IR semantics: wrap at the
; narrow width, then sign- or zero-extend.  Values sit on i8/i16/i32 sign-bit,
; max and overflow boundaries; all seven arithmetic/div/rem ops and all three
; shifts appear in both canonical directions.  Shift amounts are volatile
; values so the register-form narrow shift is selected (amount DAG type i64).
;
; @main returns the number of mismatches (0 iff all 16 results match), so a
; wrong canonical direction or a missing/wrong extension makes the guest exit
; code non-zero.  Expected guest exit code: 0.
target triple = "dadao-unknown-elf"

define i64 @main() {
entry:
  %a0_s = alloca i8, align 1
  %b0_s = alloca i8, align 1
  store volatile i8 127, i8* %a0_s, align 1
  store volatile i8 127, i8* %b0_s, align 1
  %a0 = load volatile i8, i8* %a0_s, align 1
  %b0 = load volatile i8, i8* %b0_s, align 1
  %r0 = add i8 %a0, %b0
  %e0 = sext i8 %r0 to i64
  %c0 = icmp eq i64 %e0, u0xFFFFFFFFFFFFFFFE
  %z0 = zext i1 %c0 to i64
  %a1_s = alloca i8, align 1
  %b1_s = alloca i8, align 1
  store volatile i8 127, i8* %a1_s, align 1
  store volatile i8 127, i8* %b1_s, align 1
  %a1 = load volatile i8, i8* %a1_s, align 1
  %b1 = load volatile i8, i8* %b1_s, align 1
  %r1 = add i8 %a1, %b1
  %e1 = zext i8 %r1 to i64
  %c1 = icmp eq i64 %e1, u0x00000000000000FE
  %z1 = zext i1 %c1 to i64
  %a2_s = alloca i16, align 2
  %b2_s = alloca i16, align 2
  store volatile i16 32767, i16* %a2_s, align 2
  store volatile i16 1, i16* %b2_s, align 2
  %a2 = load volatile i16, i16* %a2_s, align 2
  %b2 = load volatile i16, i16* %b2_s, align 2
  %r2 = add i16 %a2, %b2
  %e2 = zext i16 %r2 to i64
  %c2 = icmp eq i64 %e2, u0x0000000000008000
  %z2 = zext i1 %c2 to i64
  %a3_s = alloca i32, align 4
  %b3_s = alloca i32, align 4
  store volatile i32 0, i32* %a3_s, align 4
  store volatile i32 5, i32* %b3_s, align 4
  %a3 = load volatile i32, i32* %a3_s, align 4
  %b3 = load volatile i32, i32* %b3_s, align 4
  %r3 = sub i32 %a3, %b3
  %e3 = sext i32 %r3 to i64
  %c3 = icmp eq i64 %e3, u0xFFFFFFFFFFFFFFFB
  %z3 = zext i1 %c3 to i64
  %a4_s = alloca i16, align 2
  %b4_s = alloca i16, align 2
  store volatile i16 1, i16* %a4_s, align 2
  store volatile i16 32768, i16* %b4_s, align 2
  %a4 = load volatile i16, i16* %a4_s, align 2
  %b4 = load volatile i16, i16* %b4_s, align 2
  %r4 = sub i16 %a4, %b4
  %e4 = zext i16 %r4 to i64
  %c4 = icmp eq i64 %e4, u0x0000000000008001
  %z4 = zext i1 %c4 to i64
  %a5_s = alloca i32, align 4
  %b5_s = alloca i32, align 4
  store volatile i32 2147483648, i32* %a5_s, align 4
  store volatile i32 4294967295, i32* %b5_s, align 4
  %a5 = load volatile i32, i32* %a5_s, align 4
  %b5 = load volatile i32, i32* %b5_s, align 4
  %r5 = mul i32 %a5, %b5
  %e5 = sext i32 %r5 to i64
  %c5 = icmp eq i64 %e5, u0xFFFFFFFF80000000
  %z5 = zext i1 %c5 to i64
  %a6_s = alloca i16, align 2
  %b6_s = alloca i16, align 2
  store volatile i16 65535, i16* %a6_s, align 2
  store volatile i16 3, i16* %b6_s, align 2
  %a6 = load volatile i16, i16* %a6_s, align 2
  %b6 = load volatile i16, i16* %b6_s, align 2
  %r6 = mul i16 %a6, %b6
  %e6 = zext i16 %r6 to i64
  %c6 = icmp eq i64 %e6, u0x000000000000FFFD
  %z6 = zext i1 %c6 to i64
  %a7_s = alloca i8, align 1
  %b7_s = alloca i8, align 1
  store volatile i8 200, i8* %a7_s, align 1
  store volatile i8 7, i8* %b7_s, align 1
  %a7 = load volatile i8, i8* %a7_s, align 1
  %b7 = load volatile i8, i8* %b7_s, align 1
  %r7 = udiv i8 %a7, %b7
  %e7 = zext i8 %r7 to i64
  %c7 = icmp eq i64 %e7, u0x000000000000001C
  %z7 = zext i1 %c7 to i64
  %a8_s = alloca i32, align 4
  %b8_s = alloca i32, align 4
  store volatile i32 4294967295, i32* %a8_s, align 4
  store volatile i32 7, i32* %b8_s, align 4
  %a8 = load volatile i32, i32* %a8_s, align 4
  %b8 = load volatile i32, i32* %b8_s, align 4
  %r8 = urem i32 %a8, %b8
  %e8 = zext i32 %r8 to i64
  %c8 = icmp eq i64 %e8, u0x0000000000000003
  %z8 = zext i1 %c8 to i64
  %a9_s = alloca i8, align 1
  %b9_s = alloca i8, align 1
  store volatile i8 128, i8* %a9_s, align 1
  store volatile i8 3, i8* %b9_s, align 1
  %a9 = load volatile i8, i8* %a9_s, align 1
  %b9 = load volatile i8, i8* %b9_s, align 1
  %r9 = sdiv i8 %a9, %b9
  %e9 = sext i8 %r9 to i64
  %c9 = icmp eq i64 %e9, u0xFFFFFFFFFFFFFFD6
  %z9 = zext i1 %c9 to i64
  %a10_s = alloca i16, align 2
  %b10_s = alloca i16, align 2
  store volatile i16 35536, i16* %a10_s, align 2
  store volatile i16 7, i16* %b10_s, align 2
  %a10 = load volatile i16, i16* %a10_s, align 2
  %b10 = load volatile i16, i16* %b10_s, align 2
  %r10 = srem i16 %a10, %b10
  %e10 = sext i16 %r10 to i64
  %c10 = icmp eq i64 %e10, u0xFFFFFFFFFFFFFFFB
  %z10 = zext i1 %c10 to i64
  %a11_s = alloca i8, align 1
  %b11_s = alloca i8, align 1
  store volatile i8 64, i8* %a11_s, align 1
  store volatile i8 1, i8* %b11_s, align 1
  %a11 = load volatile i8, i8* %a11_s, align 1
  %b11 = load volatile i8, i8* %b11_s, align 1
  %r11 = shl i8 %a11, %b11
  %e11 = zext i8 %r11 to i64
  %c11 = icmp eq i64 %e11, u0x0000000000000080
  %z11 = zext i1 %c11 to i64
  %a12_s = alloca i32, align 4
  %b12_s = alloca i32, align 4
  store volatile i32 1073741824, i32* %a12_s, align 4
  store volatile i32 1, i32* %b12_s, align 4
  %a12 = load volatile i32, i32* %a12_s, align 4
  %b12 = load volatile i32, i32* %b12_s, align 4
  %r12 = shl i32 %a12, %b12
  %e12 = zext i32 %r12 to i64
  %c12 = icmp eq i64 %e12, u0x0000000080000000
  %z12 = zext i1 %c12 to i64
  %a13_s = alloca i16, align 2
  %b13_s = alloca i16, align 2
  store volatile i16 32768, i16* %a13_s, align 2
  store volatile i16 4, i16* %b13_s, align 2
  %a13 = load volatile i16, i16* %a13_s, align 2
  %b13 = load volatile i16, i16* %b13_s, align 2
  %r13 = lshr i16 %a13, %b13
  %e13 = zext i16 %r13 to i64
  %c13 = icmp eq i64 %e13, u0x0000000000000800
  %z13 = zext i1 %c13 to i64
  %a14_s = alloca i8, align 1
  %b14_s = alloca i8, align 1
  store volatile i8 128, i8* %a14_s, align 1
  store volatile i8 1, i8* %b14_s, align 1
  %a14 = load volatile i8, i8* %a14_s, align 1
  %b14 = load volatile i8, i8* %b14_s, align 1
  %r14 = ashr i8 %a14, %b14
  %e14 = sext i8 %r14 to i64
  %c14 = icmp eq i64 %e14, u0xFFFFFFFFFFFFFFC0
  %z14 = zext i1 %c14 to i64
  %a15_s = alloca i32, align 4
  %b15_s = alloca i32, align 4
  store volatile i32 2147483648, i32* %a15_s, align 4
  store volatile i32 31, i32* %b15_s, align 4
  %a15 = load volatile i32, i32* %a15_s, align 4
  %b15 = load volatile i32, i32* %b15_s, align 4
  %r15 = ashr i32 %a15, %b15
  %e15 = sext i32 %r15 to i64
  %c15 = icmp eq i64 %e15, u0xFFFFFFFFFFFFFFFF
  %z15 = zext i1 %c15 to i64
  %m0 = add i64 %z0, %z1
  %m1 = add i64 %m0, %z2
  %m2 = add i64 %m1, %z3
  %m3 = add i64 %m2, %z4
  %m4 = add i64 %m3, %z5
  %m5 = add i64 %m4, %z6
  %m6 = add i64 %m5, %z7
  %m7 = add i64 %m6, %z8
  %m8 = add i64 %m7, %z9
  %m9 = add i64 %m8, %z10
  %m10 = add i64 %m9, %z11
  %m11 = add i64 %m10, %z12
  %m12 = add i64 %m11, %z13
  %m13 = add i64 %m12, %z14
  %m14 = add i64 %m13, %z15
  %bad = sub i64 16, %m14
  ret i64 %bad
}

