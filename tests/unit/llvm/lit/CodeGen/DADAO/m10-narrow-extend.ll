; RUN: %llc -march=dadao -O2 -verify-machineinstrs -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-132t: only an exact i64 extension consumer may select a producer whose
; ISA variant already writes the requested canonical high bits.  Mismatched
; directions remain explicit ext.so/ext.uo; ABI-only extensions are tested in
; abi-narrow-extend.ll and are intentionally not folded.

target triple = "dadao-unknown-elf"

; CHECK-LABEL: sext_add32:
; CHECK:         add.st rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     ext.{{s|u}}o
define i64 @sext_add32(i32 %a, i32 %b) {
  %r = add i32 %a, %b
  %e = sext i32 %r to i64
  ret i64 %e
}

; CHECK-LABEL: zext_add32:
; CHECK:         add.ut rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     ext.{{s|u}}o
define i64 @zext_add32(i32 %a, i32 %b) {
  %r = add i32 %a, %b
  %e = zext i32 %r to i64
  ret i64 %e
}

; CHECK-LABEL: sext_sub32:
; CHECK:         sub.st rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     ext.{{s|u}}o
define i64 @sext_sub32(i32 %a, i32 %b) {
  %r = sub i32 %a, %b
  %e = sext i32 %r to i64
  ret i64 %e
}

; CHECK-LABEL: zext_sub32:
; CHECK:         sub.ut rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     ext.{{s|u}}o
define i64 @zext_sub32(i32 %a, i32 %b) {
  %r = sub i32 %a, %b
  %e = zext i32 %r to i64
  ret i64 %e
}

; CHECK-LABEL: sext_mul32:
; CHECK:         mul.st rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     ext.{{s|u}}o
define i64 @sext_mul32(i32 %a, i32 %b) {
  %r = mul i32 %a, %b
  %e = sext i32 %r to i64
  ret i64 %e
}

; CHECK-LABEL: zext_mul32:
; CHECK:         mul.ut rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     ext.{{s|u}}o
define i64 @zext_mul32(i32 %a, i32 %b) {
  %r = mul i32 %a, %b
  %e = zext i32 %r to i64
  ret i64 %e
}

; CHECK-LABEL: zext_udiv32:
; CHECK:         div.ut rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     ext.{{s|u}}o
define i64 @zext_udiv32(i32 %a, i32 %b) {
  %r = udiv i32 %a, %b
  %e = zext i32 %r to i64
  ret i64 %e
}

; CHECK-LABEL: zext_urem32:
; CHECK:         rem.ut rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     ext.{{s|u}}o
define i64 @zext_urem32(i32 %a, i32 %b) {
  %r = urem i32 %a, %b
  %e = zext i32 %r to i64
  ret i64 %e
}

; CHECK-LABEL: sext_sdiv32:
; CHECK:         div.st rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     ext.{{s|u}}o
define i64 @sext_sdiv32(i32 %a, i32 %b) {
  %r = sdiv i32 %a, %b
  %e = sext i32 %r to i64
  ret i64 %e
}

; CHECK-LABEL: sext_srem32:
; CHECK:         rem.st rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     ext.{{s|u}}o
define i64 @sext_srem32(i32 %a, i32 %b) {
  %r = srem i32 %a, %b
  %e = sext i32 %r to i64
  ret i64 %e
}

; CHECK-LABEL: zext_shl32:
; CHECK:         shl.t rd{{[0-9]+}}, rd16, rd{{[0-9]+}}
; CHECK-NOT:     ext.{{s|u}}o
define i64 @zext_shl32(i32 %a, i32 %b) {
  %r = shl i32 %a, %b
  %e = zext i32 %r to i64
  ret i64 %e
}

; CHECK-LABEL: zext_lshr32:
; CHECK:         shr.ut rd{{[0-9]+}}, rd16, rd{{[0-9]+}}
; CHECK-NOT:     ext.{{s|u}}o
define i64 @zext_lshr32(i32 %a, i32 %b) {
  %r = lshr i32 %a, %b
  %e = zext i32 %r to i64
  ret i64 %e
}

; CHECK-LABEL: sext_ashr32:
; CHECK:         shr.st rd{{[0-9]+}}, rd16, rd{{[0-9]+}}
; CHECK-NOT:     ext.{{s|u}}o
define i64 @sext_ashr32(i32 %a, i32 %b) {
  %r = ashr i32 %a, %b
  %e = sext i32 %r to i64
  ret i64 %e
}

; CHECK-LABEL: sext_add16:
; CHECK:         add.sw rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     ext.{{s|u}}o
define i64 @sext_add16(i16 %a, i16 %b) {
  %r = add i16 %a, %b
  %e = sext i16 %r to i64
  ret i64 %e
}

; CHECK-LABEL: zext_add16:
; CHECK:         add.uw rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     ext.{{s|u}}o
define i64 @zext_add16(i16 %a, i16 %b) {
  %r = add i16 %a, %b
  %e = zext i16 %r to i64
  ret i64 %e
}

; CHECK-LABEL: sext_sub16:
; CHECK:         sub.sw rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     ext.{{s|u}}o
define i64 @sext_sub16(i16 %a, i16 %b) {
  %r = sub i16 %a, %b
  %e = sext i16 %r to i64
  ret i64 %e
}

; CHECK-LABEL: zext_sub16:
; CHECK:         sub.uw rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     ext.{{s|u}}o
define i64 @zext_sub16(i16 %a, i16 %b) {
  %r = sub i16 %a, %b
  %e = zext i16 %r to i64
  ret i64 %e
}

; CHECK-LABEL: sext_mul16:
; CHECK:         mul.sw rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     ext.{{s|u}}o
define i64 @sext_mul16(i16 %a, i16 %b) {
  %r = mul i16 %a, %b
  %e = sext i16 %r to i64
  ret i64 %e
}

; CHECK-LABEL: zext_mul16:
; CHECK:         mul.uw rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     ext.{{s|u}}o
define i64 @zext_mul16(i16 %a, i16 %b) {
  %r = mul i16 %a, %b
  %e = zext i16 %r to i64
  ret i64 %e
}

; CHECK-LABEL: zext_udiv16:
; CHECK:         div.uw rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     ext.{{s|u}}o
define i64 @zext_udiv16(i16 %a, i16 %b) {
  %r = udiv i16 %a, %b
  %e = zext i16 %r to i64
  ret i64 %e
}

; CHECK-LABEL: zext_urem16:
; CHECK:         rem.uw rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     ext.{{s|u}}o
define i64 @zext_urem16(i16 %a, i16 %b) {
  %r = urem i16 %a, %b
  %e = zext i16 %r to i64
  ret i64 %e
}

; CHECK-LABEL: sext_sdiv16:
; CHECK:         div.sw rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     ext.{{s|u}}o
define i64 @sext_sdiv16(i16 %a, i16 %b) {
  %r = sdiv i16 %a, %b
  %e = sext i16 %r to i64
  ret i64 %e
}

; CHECK-LABEL: sext_srem16:
; CHECK:         rem.sw rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     ext.{{s|u}}o
define i64 @sext_srem16(i16 %a, i16 %b) {
  %r = srem i16 %a, %b
  %e = sext i16 %r to i64
  ret i64 %e
}

; CHECK-LABEL: zext_shl16:
; CHECK:         shl.w rd{{[0-9]+}}, rd16, rd{{[0-9]+}}
; CHECK-NOT:     ext.{{s|u}}o
define i64 @zext_shl16(i16 %a, i16 %b) {
  %r = shl i16 %a, %b
  %e = zext i16 %r to i64
  ret i64 %e
}

; CHECK-LABEL: zext_lshr16:
; CHECK:         shr.uw rd{{[0-9]+}}, rd16, rd{{[0-9]+}}
; CHECK-NOT:     ext.{{s|u}}o
define i64 @zext_lshr16(i16 %a, i16 %b) {
  %r = lshr i16 %a, %b
  %e = zext i16 %r to i64
  ret i64 %e
}

; CHECK-LABEL: sext_ashr16:
; CHECK:         shr.sw rd{{[0-9]+}}, rd16, rd{{[0-9]+}}
; CHECK-NOT:     ext.{{s|u}}o
define i64 @sext_ashr16(i16 %a, i16 %b) {
  %r = ashr i16 %a, %b
  %e = sext i16 %r to i64
  ret i64 %e
}

; CHECK-LABEL: sext_add8:
; CHECK:         add.sb rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     ext.{{s|u}}o
define i64 @sext_add8(i8 %a, i8 %b) {
  %r = add i8 %a, %b
  %e = sext i8 %r to i64
  ret i64 %e
}

; CHECK-LABEL: zext_add8:
; CHECK:         add.ub rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     ext.{{s|u}}o
define i64 @zext_add8(i8 %a, i8 %b) {
  %r = add i8 %a, %b
  %e = zext i8 %r to i64
  ret i64 %e
}

; CHECK-LABEL: sext_sub8:
; CHECK:         sub.sb rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     ext.{{s|u}}o
define i64 @sext_sub8(i8 %a, i8 %b) {
  %r = sub i8 %a, %b
  %e = sext i8 %r to i64
  ret i64 %e
}

; CHECK-LABEL: zext_sub8:
; CHECK:         sub.ub rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     ext.{{s|u}}o
define i64 @zext_sub8(i8 %a, i8 %b) {
  %r = sub i8 %a, %b
  %e = zext i8 %r to i64
  ret i64 %e
}

; CHECK-LABEL: sext_mul8:
; CHECK:         mul.sb rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     ext.{{s|u}}o
define i64 @sext_mul8(i8 %a, i8 %b) {
  %r = mul i8 %a, %b
  %e = sext i8 %r to i64
  ret i64 %e
}

; CHECK-LABEL: zext_mul8:
; CHECK:         mul.ub rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     ext.{{s|u}}o
define i64 @zext_mul8(i8 %a, i8 %b) {
  %r = mul i8 %a, %b
  %e = zext i8 %r to i64
  ret i64 %e
}

; CHECK-LABEL: zext_udiv8:
; CHECK:         div.ub rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     ext.{{s|u}}o
define i64 @zext_udiv8(i8 %a, i8 %b) {
  %r = udiv i8 %a, %b
  %e = zext i8 %r to i64
  ret i64 %e
}

; CHECK-LABEL: zext_urem8:
; CHECK:         rem.ub rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     ext.{{s|u}}o
define i64 @zext_urem8(i8 %a, i8 %b) {
  %r = urem i8 %a, %b
  %e = zext i8 %r to i64
  ret i64 %e
}

; CHECK-LABEL: sext_sdiv8:
; CHECK:         div.sb rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     ext.{{s|u}}o
define i64 @sext_sdiv8(i8 %a, i8 %b) {
  %r = sdiv i8 %a, %b
  %e = sext i8 %r to i64
  ret i64 %e
}

; CHECK-LABEL: sext_srem8:
; CHECK:         rem.sb rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     ext.{{s|u}}o
define i64 @sext_srem8(i8 %a, i8 %b) {
  %r = srem i8 %a, %b
  %e = sext i8 %r to i64
  ret i64 %e
}

; CHECK-LABEL: zext_shl8:
; CHECK:         shl.b rd{{[0-9]+}}, rd16, rd{{[0-9]+}}
; CHECK-NOT:     ext.{{s|u}}o
define i64 @zext_shl8(i8 %a, i8 %b) {
  %r = shl i8 %a, %b
  %e = zext i8 %r to i64
  ret i64 %e
}

; CHECK-LABEL: zext_lshr8:
; CHECK:         shr.ub rd{{[0-9]+}}, rd16, rd{{[0-9]+}}
; CHECK-NOT:     ext.{{s|u}}o
define i64 @zext_lshr8(i8 %a, i8 %b) {
  %r = lshr i8 %a, %b
  %e = zext i8 %r to i64
  ret i64 %e
}

; CHECK-LABEL: sext_ashr8:
; CHECK:         shr.sb rd{{[0-9]+}}, rd16, rd{{[0-9]+}}
; CHECK-NOT:     ext.{{s|u}}o
define i64 @sext_ashr8(i8 %a, i8 %b) {
  %r = ashr i8 %a, %b
  %e = sext i8 %r to i64
  ret i64 %e
}

; Direction mismatches must retain the explicit extension.
; CHECK-LABEL: zext_ashr32:
; CHECK:         shr.st rd{{[0-9]+}}, rd16, rd{{[0-9]+}}
; CHECK:         ext.uo rd{{[0-9]+}}, rd{{[0-9]+}}, 31
define i64 @zext_ashr32(i32 %a, i32 %b) {
  %r = ashr i32 %a, %b
  %e = zext i32 %r to i64
  ret i64 %e
}

; CHECK-LABEL: sext_lshr32:
; CHECK:         shr.ut rd{{[0-9]+}}, rd16, rd{{[0-9]+}}
; CHECK:         ext.so rd{{[0-9]+}}, rd{{[0-9]+}}, 31
define i64 @sext_lshr32(i32 %a, i32 %b) {
  %r = lshr i32 %a, %b
  %e = sext i32 %r to i64
  ret i64 %e
}

; A non-target producer is not treated as canonical merely because its result
; type is narrow.
; CHECK-LABEL: zext_and32:
; CHECK:         ext.uo rd{{[0-9]+}}, rd{{[0-9]+}}, 31
define i64 @zext_and32(i32 %a, i32 %b) {
  %r = and i32 %a, %b
  %e = zext i32 %r to i64
  ret i64 %e
}
