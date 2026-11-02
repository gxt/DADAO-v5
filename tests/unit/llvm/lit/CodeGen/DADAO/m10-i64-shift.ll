; RUN: %llc -march=dadao -O2 -verify-machineinstrs -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-137t: i64 constant shifts use the existing immu6 orri encodings
; (`shl.o` / `shr.uo` / `shr.so`).  Shift by zero is canonically a register
; copy; every other in-range amount must be selected as an immediate and must
; not materialize a shift register.  A variable amount keeps the register form.
; Amounts >= 64 are poison in IR: no out-of-range immediate may be emitted.
; Narrow shifts keep their narrow orri forms (i64 support is a separate branch).

target triple = "dadao-unknown-elf"

define i64 @shl0(i64 %x) {
  %r = shl i64 %x, 0
  ret i64 %r
}

define i64 @shl1(i64 %x) {
  %r = shl i64 %x, 1
  ret i64 %r
}

define i64 @shl31(i64 %x) {
  %r = shl i64 %x, 31
  ret i64 %r
}

define i64 @shl32(i64 %x) {
  %r = shl i64 %x, 32
  ret i64 %r
}

define i64 @shl63(i64 %x) {
  %r = shl i64 %x, 63
  ret i64 %r
}

define i64 @lshr0(i64 %x) {
  %r = lshr i64 %x, 0
  ret i64 %r
}

define i64 @lshr1(i64 %x) {
  %r = lshr i64 %x, 1
  ret i64 %r
}

define i64 @lshr31(i64 %x) {
  %r = lshr i64 %x, 31
  ret i64 %r
}

define i64 @lshr32(i64 %x) {
  %r = lshr i64 %x, 32
  ret i64 %r
}

define i64 @lshr63(i64 %x) {
  %r = lshr i64 %x, 63
  ret i64 %r
}

define i64 @ashr0(i64 %x) {
  %r = ashr i64 %x, 0
  ret i64 %r
}

define i64 @ashr1(i64 %x) {
  %r = ashr i64 %x, 1
  ret i64 %r
}

define i64 @ashr31(i64 %x) {
  %r = ashr i64 %x, 31
  ret i64 %r
}

define i64 @ashr32(i64 %x) {
  %r = ashr i64 %x, 32
  ret i64 %r
}

define i64 @ashr63(i64 %x) {
  %r = ashr i64 %x, 63
  ret i64 %r
}

define i64 @shl_var(i64 %x, i64 %n) {
  %r = shl i64 %x, %n
  ret i64 %r
}

define i64 @lshr_var(i64 %x, i64 %n) {
  %r = lshr i64 %x, %n
  ret i64 %r
}

define i64 @ashr_var(i64 %x, i64 %n) {
  %r = ashr i64 %x, %n
  ret i64 %r
}

; Narrow shift regression: these must still pick the narrow orri, never `*.o`.
define i32 @shl_c_i32(i32 %x) {
  %r = shl i32 %x, 3
  ret i32 %r
}

define i16 @shl_c_i16(i16 %x) {
  %r = shl i16 %x, 3
  ret i16 %r
}

define i8 @shl_c_i8(i8 %x) {
  %r = shl i8 %x, 3
  ret i8 %r
}

; Out-of-range amounts are poison; the selector must not build `immu6` >= 64.
define i64 @shl64(i64 %x) {
  %r = shl i64 %x, 64
  ret i64 %r
}

define i64 @lshr64(i64 %x) {
  %r = lshr i64 %x, 64
  ret i64 %r
}

define i64 @ashr64(i64 %x) {
  %r = ashr i64 %x, 64
  ret i64 %r
}

; CHECK-LABEL: shl0:
; CHECK:         rd2rd
; CHECK-LABEL: shl1:
; CHECK:         shl.o rd{{[0-9]+}}, rd16, 1
; CHECK-NOT:     set.zw
; CHECK-LABEL: shl31:
; CHECK:         shl.o rd{{[0-9]+}}, rd16, 31
; CHECK-NOT:     set.zw
; CHECK-LABEL: shl32:
; CHECK:         shl.o rd{{[0-9]+}}, rd16, 32
; CHECK-NOT:     set.zw
; CHECK-LABEL: shl63:
; CHECK:         shl.o rd{{[0-9]+}}, rd16, 63
; CHECK-NOT:     set.zw
; CHECK-LABEL: lshr0:
; CHECK:         rd2rd
; CHECK-LABEL: lshr1:
; CHECK:         shr.uo rd{{[0-9]+}}, rd16, 1
; CHECK-NOT:     set.zw
; CHECK-LABEL: lshr31:
; CHECK:         shr.uo rd{{[0-9]+}}, rd16, 31
; CHECK-NOT:     set.zw
; CHECK-LABEL: lshr32:
; CHECK:         shr.uo rd{{[0-9]+}}, rd16, 32
; CHECK-NOT:     set.zw
; CHECK-LABEL: lshr63:
; CHECK:         shr.uo rd{{[0-9]+}}, rd16, 63
; CHECK-NOT:     set.zw
; CHECK-LABEL: ashr0:
; CHECK:         rd2rd
; CHECK-LABEL: ashr1:
; CHECK:         shr.so rd{{[0-9]+}}, rd16, 1
; CHECK-NOT:     set.zw
; CHECK-LABEL: ashr31:
; CHECK:         shr.so rd{{[0-9]+}}, rd16, 31
; CHECK-NOT:     set.zw
; CHECK-LABEL: ashr32:
; CHECK:         shr.so rd{{[0-9]+}}, rd16, 32
; CHECK-NOT:     set.zw
; CHECK-LABEL: ashr63:
; CHECK:         shr.so rd{{[0-9]+}}, rd16, 63
; CHECK-NOT:     set.zw
; CHECK-LABEL: shl_var:
; CHECK:         shl.o rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     shl.o rd{{[0-9]+}}, rd16, 1
; CHECK-LABEL: lshr_var:
; CHECK:         shr.uo rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     shr.uo rd{{[0-9]+}}, rd16, 1
; CHECK-LABEL: ashr_var:
; CHECK:         shr.so rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     shr.so rd{{[0-9]+}}, rd16, 1
; CHECK-LABEL: shl_c_i32:
; CHECK:         shl.t rd{{[0-9]+}}, rd16, 3
; CHECK-NOT:     shl.o
; CHECK-LABEL: shl_c_i16:
; CHECK:         shl.w rd{{[0-9]+}}, rd16, 3
; CHECK-NOT:     shl.o
; CHECK-LABEL: shl_c_i8:
; CHECK:         shl.b rd{{[0-9]+}}, rd16, 3
; CHECK-NOT:     shl.o
; CHECK-LABEL: shl64:
; CHECK-NOT:     shl.o
; CHECK-NOT:     set.zw
; CHECK-LABEL: lshr64:
; CHECK-NOT:     shr.uo
; CHECK-NOT:     set.zw
; CHECK-LABEL: ashr64:
; CHECK-NOT:     shr.so
; CHECK-NOT:     set.zw
