; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-116t (M9; ADR-0032 D4 as amended 2026-10-19): the ISA has one
; single-direction rotate, `rol.o` (010-001 orrr / 011-001 orri).
;   * ISD::ROTL is selected directly: constant amount -> one `rol.o` (orri),
;     variable amount -> one `rol.o` (orrr);
;   * ISD::ROTR is custom-lowered to `rol(x, (64-n) mod 64)`: a constant
;     amount folds to the one-instruction immediate form, a variable amount
;     costs one negation (`sub.o rd, rd0, n`) plus one `rol.o`.
; LLVM-099t used `Expand` for both directions (no rotate instruction then);
; the measured Expand cost was 5 instructions (constant) / 7 (variable).
;
; Narrow i32/i16/i8 rotates are expanded to i64 shifts by
; DAGTypeLegalizer::PromoteIntRes_ROT before ISel (no sub-registers), so the
; narrow `rol.t/w/b` encodings stay MC-only; the checks below pin that down.

target triple = "dadao-unknown-elf"

declare i64 @llvm.fshl.i64(i64, i64, i64)
declare i64 @llvm.fshr.i64(i64, i64, i64)
declare i32 @llvm.fshr.i32(i32, i32, i32)
declare i16 @llvm.fshr.i16(i16, i16, i16)
declare i8  @llvm.fshr.i8(i8, i8, i8)

define i64 @rotl_imm(i64 %x) {
  %r = call i64 @llvm.fshl.i64(i64 %x, i64 %x, i64 8)
  ret i64 %r
}

define i64 @rotl_var(i64 %x, i64 %n) {
  %r = call i64 @llvm.fshl.i64(i64 %x, i64 %x, i64 %n)
  ret i64 %r
}

define i64 @rotl_zero(i64 %x) {
  %r = call i64 @llvm.fshl.i64(i64 %x, i64 %x, i64 0)
  ret i64 %r
}

define i64 @rotr_imm(i64 %x) {
  %r = call i64 @llvm.fshr.i64(i64 %x, i64 %x, i64 8)
  ret i64 %r
}

define i64 @rotr_var(i64 %x, i64 %n) {
  %r = call i64 @llvm.fshr.i64(i64 %x, i64 %x, i64 %n)
  ret i64 %r
}

define i64 @rotr_63(i64 %x) {
  %r = call i64 @llvm.fshr.i64(i64 %x, i64 %x, i64 63)
  ret i64 %r
}

define i32 @rotr_i32(i32 %x) {
  %r = call i32 @llvm.fshr.i32(i32 %x, i32 %x, i32 3)
  ret i32 %r
}

define i16 @rotr_i16(i16 %x, i16 %n) {
  %r = call i16 @llvm.fshr.i16(i16 %x, i16 %x, i16 %n)
  ret i16 %r
}

define i8 @rotr_i8(i8 %x) {
  %r = call i8 @llvm.fshr.i8(i8 %x, i8 %x, i8 3)
  ret i8 %r
}

; Constant rotate-left: one immediate `rol.o`.
; CHECK-LABEL: rotl_imm:
; CHECK: rol.o rd{{[0-9]+}}, rd{{[0-9]+}}, 8

; Variable rotate-left: one register-form `rol.o` (amount taken modulo 64).
; CHECK-LABEL: rotl_var:
; CHECK: rol.o rd{{[0-9]+}}, rd{{[0-9]+}}, rd{{[0-9]+}}

; Rotate by 0 is folded to a register copy.
; CHECK-LABEL: rotl_zero:
; CHECK: rd2rd

; rotate-right 8 == rotate-left 56: one immediate `rol.o`.
; CHECK-LABEL: rotr_imm:
; CHECK: rol.o rd{{[0-9]+}}, rd{{[0-9]+}}, 56

; Variable rotate-right: `sub.o rd, rd0, n` (two's-complement negation gives
; (-n) mod 64) followed by one register-form `rol.o`.
; CHECK-LABEL: rotr_var:
; CHECK: sub.so {rd0, rd{{[0-9]+}}}, rd0, rd{{[0-9]+}}
; CHECK-NEXT: rol.o rd{{[0-9]+}}, rd{{[0-9]+}}, rd{{[0-9]+}}

; rotate-right 63 == rotate-left 1.
; CHECK-LABEL: rotr_63:
; CHECK: rol.o rd{{[0-9]+}}, rd{{[0-9]+}}, 1

; Narrow rotates are type-legalized to i64 shifts; no rol.t/w/b is selected.
; CHECK-LABEL: rotr_i32:
; CHECK-NOT: rol.
; CHECK-LABEL: rotr_i16:
; CHECK-NOT: rol.
; CHECK-LABEL: rotr_i8:
; CHECK-NOT: rol.
