; RUN: %llc -march=dadao -O2 -verify-machineinstrs -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-128t (M9): narrow (i32/i16/i8) bit counts reuse the i64 instructions.
;
; i64 is the only legal DADAO integer type, so a narrow ctlz/cttz/ctpop is
; promoted by the type legalizer and then re-uses the i64 `ctlz`/`cttz`/`ctpop`
; instruction with `hd = 63` (DADAOCodeGen.td).  The promotion supplies the
; narrow-width semantics exactly:
;
;   * ctlz iN -> ctlz(zext to i64) - (64 - N)   -- zero gives 64 - (64-N) = N;
;   * cttz iN -> cttz(zext to i64 | 1 << N)     -- the inserted bit keeps the
;     result at N for a zero input instead of 64;
;   * ctpop iN -> ctpop(zext to i64)           -- the mask bounds the count.
;
; This file replaces `p0-cttz.ll` (LLVM-079t), whose premise -- "the ISA has no
; bit-scan / population-count instruction" -- was superseded by SPEC-143t.
; Each function below is 3-6 instructions and stays libcall-free.

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

; --- i32: zero-extend, then the i64 instruction -----------------------------
; CHECK-LABEL: ctlz32:
; CHECK:         and.o rd{{[0-9]+}}, rd16, rd{{[0-9]+}}
; CHECK:         ctlz rd{{[0-9]+}}, rd{{[0-9]+}}, 63
; CHECK:         add.si rd8, -32
; CHECK-NOT:     call
define i32 @ctlz32(i32 %x) {
  %r = call i32 @llvm.ctlz.i32(i32 %x, i1 false)
  ret i32 %r
}

; The OR inserts bit 32 so cttz(0) stays 32: without it the i64 instruction
; would answer 64 for a narrow zero.
; CHECK-LABEL: cttz32:
; CHECK:         set.zw rd{{[0-9]+}}, wp{{[0-9]+}}, 0x1
; CHECK-NEXT:    or.o rd{{[0-9]+}}, rd16, rd{{[0-9]+}}
; CHECK-NEXT:    cttz rd8, rd{{[0-9]+}}, 63
; CHECK-NOT:     call
define i32 @cttz32(i32 %x) {
  %r = call i32 @llvm.cttz.i32(i32 %x, i1 false)
  ret i32 %r
}

; CHECK-LABEL: ctpop32:
; CHECK:         and.o rd{{[0-9]+}}, rd16, rd{{[0-9]+}}
; CHECK:         ctpop rd8, rd{{[0-9]+}}, 63
; CHECK-NOT:     mul.uo
define i32 @ctpop32(i32 %x) {
  %r = call i32 @llvm.ctpop.i32(i32 %x)
  ret i32 %r
}

; --- i16 --------------------------------------------------------------------
; CHECK-LABEL: ctlz16:
; CHECK:         and.o rd{{[0-9]+}}, rd16, rd{{[0-9]+}}
; CHECK:         ctlz rd{{[0-9]+}}, rd{{[0-9]+}}, 63
; CHECK:         add.si rd8, -48
define i16 @ctlz16(i16 %x) {
  %r = call i16 @llvm.ctlz.i16(i16 %x, i1 false)
  ret i16 %r
}

; CHECK-LABEL: cttz16:
; CHECK:         or.o rd{{[0-9]+}}, rd16, rd{{[0-9]+}}
; CHECK-NEXT:    cttz rd8, rd{{[0-9]+}}, 63
define i16 @cttz16(i16 %x) {
  %r = call i16 @llvm.cttz.i16(i16 %x, i1 false)
  ret i16 %r
}

; CHECK-LABEL: ctpop16:
; CHECK:         and.o rd{{[0-9]+}}, rd16, rd{{[0-9]+}}
; CHECK:         ctpop rd8, rd{{[0-9]+}}, 63
define i16 @ctpop16(i16 %x) {
  %r = call i16 @llvm.ctpop.i16(i16 %x)
  ret i16 %r
}

; --- i8 ---------------------------------------------------------------------
; CHECK-LABEL: ctlz8:
; CHECK:         and.o rd{{[0-9]+}}, rd16, rd{{[0-9]+}}
; CHECK:         ctlz rd{{[0-9]+}}, rd{{[0-9]+}}, 63
; CHECK:         add.si rd8, -56
define i8 @ctlz8(i8 %x) {
  %r = call i8 @llvm.ctlz.i8(i8 %x, i1 false)
  ret i8 %r
}

; CHECK-LABEL: cttz8:
; CHECK:         set.zw rd{{[0-9]+}}, wp{{[0-9]+}}, 0x100
; CHECK-NEXT:    or.o rd{{[0-9]+}}, rd16, rd{{[0-9]+}}
; CHECK-NEXT:    cttz rd8, rd{{[0-9]+}}, 63
define i8 @cttz8(i8 %x) {
  %r = call i8 @llvm.cttz.i8(i8 %x, i1 false)
  ret i8 %r
}

; CHECK-LABEL: ctpop8:
; CHECK:         and.o rd{{[0-9]+}}, rd16, rd{{[0-9]+}}
; CHECK:         ctpop rd8, rd{{[0-9]+}}, 63
define i8 @ctpop8(i8 %x) {
  %r = call i8 @llvm.ctpop.i8(i8 %x)
  ret i8 %r
}
