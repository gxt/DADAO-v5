;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-126t (ISS-188): the FCSR rounding-mode accessors read/write
; rf0[33:32] -- the only place the hardware keeps the dynamic rounding mode.
;
; contract-fp.md §1: rf0[33:32] is 00 RNE, 01 RTZ, 10 RDN, 11 RUP; FLT_ROUNDS
; (what llvm.get/set.rounding use) is 0 RTZ, 1 RNE, 2 RUP, 3 RDN, i.e. the
; hardware encoding with bit 0 inverted.
;
;   get.rounding:  rf2rd {rd}, {rf0}; shr 32; and 3; xor 1
;   set.rounding (constant): one `set.w {rf0}, wp2, hw`.  wp2 is bits [47:32],
;     so the FCSR write mask restricts the write to rf0[33:32] and the accrued
;     exception flags in rf0[4:0] are untouched.
;   set.rounding (dynamic): read the FCSR, clear [33:32], merge (mode & 3) ^ 1
;     and write back with rd2rf; flags preserved the same way.
;
; There is no libcall in either direction.

declare i32 @llvm.get.rounding()
declare void @llvm.set.rounding(i32)

define i32 @get_rounding() {
; CHECK-LABEL: get_rounding:
; CHECK-COUNT-1: rf2rd
; CHECK-COUNT-1: shr.uo
; CHECK-COUNT-1: xor.o
; CHECK-NOT:     call
  %r = call i32 @llvm.get.rounding()
  ret i32 %r
}

; FLT_ROUNDS 0 (toward zero) -> hardware 01 (RTZ)
define void @set_rtz() {
; CHECK-LABEL: set_rtz:
; CHECK-COUNT-1: set.w rf0, wp2, 0x1
; CHECK-NOT:     call
  call void @llvm.set.rounding(i32 0)
  ret void
}

; FLT_ROUNDS 1 (nearest-even) -> hardware 00 (RNE)
define void @set_rne() {
; CHECK-LABEL: set_rne:
; CHECK-COUNT-1: set.w rf0, wp2, 0x0
; CHECK-NOT:     call
  call void @llvm.set.rounding(i32 1)
  ret void
}

; FLT_ROUNDS 2 (upward) -> hardware 11 (RUP)
define void @set_rup() {
; CHECK-LABEL: set_rup:
; CHECK-COUNT-1: set.w rf0, wp2, 0x3
; CHECK-NOT:     call
  call void @llvm.set.rounding(i32 2)
  ret void
}

; FLT_ROUNDS 3 (downward) -> hardware 10 (RDN)
define void @set_rdn() {
; CHECK-LABEL: set_rdn:
; CHECK-COUNT-1: set.w rf0, wp2, 0x2
; CHECK-NOT:     call
  call void @llvm.set.rounding(i32 3)
  ret void
}

; dynamic mode: read-modify-write, flags kept
define void @set_dynamic(i32 %m) {
; CHECK-LABEL: set_dynamic:
; CHECK-COUNT-1: rf2rd
; CHECK-COUNT-1: rd2rf
; CHECK-NOT:     call
  call void @llvm.set.rounding(i32 %m)
  ret void
}

; set then get in one function: both sides of rf0[33:32]
define i32 @roundtrip(i32 %m) {
; CHECK-LABEL: roundtrip:
; CHECK-COUNT-1: rf2rd
; CHECK-COUNT-1: rd2rf
; CHECK-NOT:     call
  call void @llvm.set.rounding(i32 %m)
  %r = call i32 @llvm.get.rounding()
  ret i32 %r
}
