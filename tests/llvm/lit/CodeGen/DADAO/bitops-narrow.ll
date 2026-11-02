; RUN: %llc -march=dadao -O2 -verify-machineinstrs -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-127t (M9): narrow (i32/i16/i8) bit counts are ONE instruction.
;
; The `immu6 hd` operand of ctlz/cttz/ctpop is the *valid-bit upper bound*
; (contract-isa.md §6.4.4), so `hd = 7/15/31` makes the instruction operate
; exactly on an i8/i16/i32 -- including the defined all-zero result W for
; ctlz/cttz and 0 for ctpop.  Since LLVM-127t the narrow integer types are
; legal, so the nodes reach ISel at their own width and select these patterns
; directly (DADAOCodeGen.td).  The only other instruction below is the
; i64 -> i32 `ext.uo` that canonicalises the returned value.
;
; LLVM-128t implemented the i64 forms (hd = 63) and promoted the narrow types
; (3-6 instructions); this file used to describe that promotion and now pins
; the 1-instruction narrow forms (the `hd = 31/15/7` half of ISS-187).

target triple = "dadao-unknown-elf"

declare i32 @llvm.ctlz.i32(i32, i1 immarg)
declare i32 @llvm.cttz.i32(i32, i1 immarg)
declare i32 @llvm.ctpop.i32(i32)
declare i16 @llvm.ctlz.i16(i16, i1 immarg)
declare i16 @llvm.cttz.i16(i16, i1 immarg)
declare i16 @llvm.ctpop.i16(i16)
declare i8 @llvm.ctlz.i8(i8, i1 immarg)
declare i8 @llvm.cttz.i8(i8, i1 immarg)
declare i8 @llvm.ctpop.i8(i8)

; --- i32: hd = 31 ------------------------------------------------------------
; CHECK-LABEL: ctlz32:
; CHECK:         ctlz rd{{[0-9]+}}, rd16, 31
; CHECK-NOT:     and.o
; CHECK-NOT:     add.si
; CHECK-NOT:     call
define i32 @ctlz32(i32 %x) {
  %r = call i32 @llvm.ctlz.i32(i32 %x, i1 false)
  ret i32 %r
}

; The all-zero result is exactly 32 with hd = 31 (no OR of an artificial bit is
; needed, unlike the old promoted form).
; CHECK-LABEL: cttz32:
; CHECK:         cttz rd{{[0-9]+}}, rd16, 31
; CHECK-NOT:     or.o
; CHECK-NOT:     call
define i32 @cttz32(i32 %x) {
  %r = call i32 @llvm.cttz.i32(i32 %x, i1 false)
  ret i32 %r
}

; CHECK-LABEL: ctpop32:
; CHECK:         ctpop rd{{[0-9]+}}, rd16, 31
; CHECK-NOT:     mul.uo
; CHECK-NOT:     call
define i32 @ctpop32(i32 %x) {
  %r = call i32 @llvm.ctpop.i32(i32 %x)
  ret i32 %r
}

; --- i16: hd = 15 ------------------------------------------------------------
; CHECK-LABEL: ctlz16:
; CHECK:         ctlz rd{{[0-9]+}}, rd16, 15
; CHECK-NOT:     and.o
; CHECK-NOT:     add.si
define i16 @ctlz16(i16 %x) {
  %r = call i16 @llvm.ctlz.i16(i16 %x, i1 false)
  ret i16 %r
}

; CHECK-LABEL: cttz16:
; CHECK:         cttz rd{{[0-9]+}}, rd16, 15
; CHECK-NOT:     or.o
define i16 @cttz16(i16 %x) {
  %r = call i16 @llvm.cttz.i16(i16 %x, i1 false)
  ret i16 %r
}

; CHECK-LABEL: ctpop16:
; CHECK:         ctpop rd{{[0-9]+}}, rd16, 15
define i16 @ctpop16(i16 %x) {
  %r = call i16 @llvm.ctpop.i16(i16 %x)
  ret i16 %r
}

; --- i8: hd = 7 --------------------------------------------------------------
; CHECK-LABEL: ctlz8:
; CHECK:         ctlz rd{{[0-9]+}}, rd16, 7
; CHECK-NOT:     and.o
; CHECK-NOT:     add.si
define i8 @ctlz8(i8 %x) {
  %r = call i8 @llvm.ctlz.i8(i8 %x, i1 false)
  ret i8 %r
}

; CHECK-LABEL: cttz8:
; CHECK:         cttz rd{{[0-9]+}}, rd16, 7
; CHECK-NOT:     or.o
define i8 @cttz8(i8 %x) {
  %r = call i8 @llvm.cttz.i8(i8 %x, i1 false)
  ret i8 %r
}

; CHECK-LABEL: ctpop8:
; CHECK:         ctpop rd{{[0-9]+}}, rd16, 7
define i8 @ctpop8(i8 %x) {
  %r = call i8 @llvm.ctpop.i8(i8 %x)
  ret i8 %r
}

; bswap16 is one `rev.w k = 8` now that i16 is legal (it used to be promoted to
; rev.o + shr.uo); bswap8 is an identity and folds away.
declare i16 @llvm.bswap.i16(i16)
; CHECK-LABEL: bswap16:
; CHECK:         rev.w rd{{[0-9]+}}, rd16, 8
; CHECK-NOT:     rev.o
; CHECK-NOT:     shr.uo
define i16 @bswap16(i16 %x) {
  %r = call i16 @llvm.bswap.i16(i16 %x)
  ret i16 %r
}
