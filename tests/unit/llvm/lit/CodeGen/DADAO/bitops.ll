; RUN: %llc -march=dadao -O2 -verify-machineinstrs -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-128t (M9): bit scan / population count / whole-word reversal.
;
; The ISA carries three bit-count instructions (ADR-0012 D11, contract-isa.md
; §6.4.4) and four per-block reversal instructions (D10, §6.4.3).  Their
; `immu6` operand is a *width parameter*, not an amount:
;
;   ctlz/cttz/ctpop rd, rs, hd   valid bits = rdHC[hd:0]; all-zero field gives
;                                hd+1 for ctlz/cttz (so hd = 63 makes the
;                                instruction exactly LLVM's defined i64
;                                `ctlz`/`cttz`, including 0 -> 64) and 0 for
;                                ctpop;
;   rev.o rd, rs, k              reverse the 8-bit elements of the 64-bit
;                                block (k = 8 -> bswap64), or the bit order
;                                (k = 1 -> bitreverse64); rev.t k = 8 is
;                                bswap32.
;
; Before this task the backend expanded all of them (LLVM-079t/LLVM-097t,
; `clz` = 10 instructions, `bswap64` = 7, `ctpop` = mul.uo-based), so the
; CHECK-NOT lines pin the instruction counts down to one.

target triple = "dadao-unknown-elf"

declare i64 @llvm.ctlz.i64(i64, i1 immarg)
declare i64 @llvm.cttz.i64(i64, i1 immarg)
declare i64 @llvm.ctpop.i64(i64)
declare i64 @llvm.bswap.i64(i64)
declare i32 @llvm.bswap.i32(i32)
declare i64 @llvm.bitreverse.i64(i64)

; --- i64 bit scan / popcount: one instruction, hd = 63 -----------------------
; CHECK-LABEL: ctlz64:
; CHECK:         ctlz rd8, rd16, 63
; CHECK-NOT:     ctlz rd
define i64 @ctlz64(i64 %x) {
  %r = call i64 @llvm.ctlz.i64(i64 %x, i1 false)
  ret i64 %r
}

; CHECK-LABEL: cttz64:
; CHECK:         cttz rd8, rd16, 63
; CHECK-NOT:     cttz rd
define i64 @cttz64(i64 %x) {
  %r = call i64 @llvm.cttz.i64(i64 %x, i1 false)
  ret i64 %r
}

; CHECK-LABEL: ctpop64:
; CHECK:         ctpop rd8, rd16, 63
; CHECK-NOT:     ctpop rd
; CHECK-NOT:     mul.uo
define i64 @ctpop64(i64 %x) {
  %r = call i64 @llvm.ctpop.i64(i64 %x)
  ret i64 %r
}

; --- zero input is *defined* (64 / 64), not poison ---------------------------
; The volatile alloca keeps the 0 out of the DAG folder, so the instruction --
; and therefore its hd = 63 width -- is what decides the zero result at run
; time (64 per §6.4.4).  With hd = 31 these checks fail.
; CHECK-LABEL: ctlz64_zero:
; CHECK:         ctlz rd8, rd{{[0-9]+}}, 63
; CHECK-NOT:     ctlz rd
define i64 @ctlz64_zero() {
  %slot = alloca i64
  store volatile i64 0, ptr %slot
  %z = load volatile i64, ptr %slot
  %r = call i64 @llvm.ctlz.i64(i64 %z, i1 false)
  ret i64 %r
}

; CHECK-LABEL: cttz64_zero:
; CHECK:         cttz rd8, rd{{[0-9]+}}, 63
; CHECK-NOT:     cttz rd
define i64 @cttz64_zero() {
  %slot = alloca i64
  store volatile i64 0, ptr %slot
  %z = load volatile i64, ptr %slot
  %r = call i64 @llvm.cttz.i64(i64 %z, i1 false)
  ret i64 %r
}

; --- byte swap: rev.o k = 8 (i64) and rev.t k = 8 (i32) ----------------------
; CHECK-LABEL: bswap64:
; CHECK:         rev.o rd8, rd16, 8
; CHECK-NOT:     rev.o
define i64 @bswap64(i64 %x) {
  %r = call i64 @llvm.bswap.i64(i64 %x)
  ret i64 %r
}

; Since LLVM-127t i32 is a legal type, `bswap i32` is selected directly by the
; `rev.t k = 8` pattern (one instruction); the following `ext.uo` is only the
; i32 -> i64 canonical zero-extension of the returned value.  Neither `rev.o`
; nor `shr.uo` may appear.
; CHECK-LABEL: bswap32:
; CHECK:         rev.t rd{{[0-9]+}}, rd16, 8
; CHECK-NOT:     rev.t
; CHECK-NOT:     rev.o
; CHECK-NOT:     shr.uo
define i32 @bswap32(i32 %x) {
  %r = call i32 @llvm.bswap.i32(i32 %x)
  ret i32 %r
}

; --- 64-bit bit reversal: rev.o k = 1 ---------------------------------------
; CHECK-LABEL: bitreverse64:
; CHECK:         rev.o rd8, rd16, 1
; CHECK-NOT:     rev.o
define i64 @bitreverse64(i64 %x) {
  %r = call i64 @llvm.bitreverse.i64(i64 %x)
  ret i64 %r
}

; The zero-poison flavour (what `__builtin_clzll`/`ctzll` emit) selects the
; same instruction: a poison result may be any value, and §6.4.4 defines 64.
; CHECK-LABEL: ctlz64_zp:
; CHECK:         ctlz rd8, rd16, 63
define i64 @ctlz64_zp(i64 %x) {
  %r = call i64 @llvm.ctlz.i64(i64 %x, i1 true)
  ret i64 %r
}

; CHECK-LABEL: cttz64_zp:
; CHECK:         cttz rd8, rd16, 63
define i64 @cttz64_zp(i64 %x) {
  %r = call i64 @llvm.cttz.i64(i64 %x, i1 true)
  ret i64 %r
}
