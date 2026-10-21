;
; RUN: %llc -march=dadao -O2 -verify-machineinstrs -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-122t (ADR-0035): `clmul.o {rdHA, rdHB}, rdHC, rdHD` (rrrr, op 0x56) is a
; GF(2) carry-less 64x64 -> 128 multiply with rdHA = high 64 bits and
; rdHB = low 64 bits, exactly like mul.uo/mul.so.  Every compiler-visible shape
; is one instruction (ADR-0035 D4: no separate clmulh/clmulr):
;
;   * low half only  -> `clmul.o {rd0, dst}, a, b`   (generic `llvm.clmul`)
;   * high half only -> `clmul.o {dst, rd0}, a, b`   (`llvm.dadao.clmul.hi`)
;   * both halves    -> `clmul.o {hi, lo}, a, b`     (`llvm.dadao.clmul`)
;
; Half binding is asserted *semantically*, not by pinning the pair text: a
; single-i64 return always lands in rd8 (contract-abi.md §4.4), so the function
; that returns only the low half must put rd8 in the rdhb (second) position,
; and the one returning only the high half must put rd8 in the rdha (first)
; position.  The both-halves form then has to agree with both.

declare i64 @llvm.clmul.i64(i64, i64)
declare {i64, i64} @llvm.dadao.clmul(i64, i64)
declare i64 @llvm.dadao.clmul.hi(i64, i64)
declare i128 @llvm.dadao.clmul.wide(i64, i64)

; --- generic llvm.clmul: low 64 bits, one instruction ------------------------
; `TargetLoweringBase` expands ISD::CLMUL by default (a bit-by-bit sequence of
; 14 mul.uo + and/or); the DADAO lowering marks i64 CLMUL Legal, so the module
; must not contain the expansion.
; CHECK-LABEL: clmul_lo:
; CHECK: clmul.o {rd0, rd8}, rd16, rd17
; CHECK-NOT: clmul.o
; CHECK-NOT: mul.uo
define i64 @clmul_lo(i64 %a, i64 %b) {
  %r = call i64 @llvm.clmul.i64(i64 %a, i64 %b)
  ret i64 %r
}

; --- private intrinsic, high half only --------------------------------------
; CHECK-LABEL: clmul_hi:
; CHECK: clmul.o {rd8, rd0}, rd16, rd17
; CHECK-NOT: clmul.o
define i64 @clmul_hi(i64 %a, i64 %b) {
  %r = call i64 @llvm.dadao.clmul.hi(i64 %a, i64 %b)
  ret i64 %r
}

; --- private intrinsic, both halves: one instruction, two destinations -------
; CHECK-LABEL: clmul_pair:
; CHECK: clmul.o {
; CHECK-NOT: clmul.o
define i64 @clmul_pair(i64 %a, i64 %b) {
  %p = call {i64, i64} @llvm.dadao.clmul(i64 %a, i64 %b)
  %lo = extractvalue {i64, i64} %p, 0
  %hi = extractvalue {i64, i64} %p, 1
  %x = xor i64 %lo, %hi
  ret i64 %x
}

; Half binding, observed through the return register (rd8):
; CHECK-LABEL: clmul_pair_lo:
; CHECK: clmul.o {rd{{[0-9]+}}, rd8}, rd16, rd17
; CHECK-NOT: clmul.o
define i64 @clmul_pair_lo(i64 %a, i64 %b) {
  %p = call {i64, i64} @llvm.dadao.clmul(i64 %a, i64 %b)
  %lo = extractvalue {i64, i64} %p, 0
  ret i64 %lo
}

; CHECK-LABEL: clmul_pair_hi:
; CHECK: clmul.o {rd8, rd{{[0-9]+}}}, rd16, rd17
; CHECK-NOT: clmul.o
define i64 @clmul_pair_hi(i64 %a, i64 %b) {
  %p = call {i64, i64} @llvm.dadao.clmul(i64 %a, i64 %b)
  %hi = extractvalue {i64, i64} %p, 1
  ret i64 %hi
}

; --- i128 form (what __builtin_dadao_clmul emits) --------------------------
; The i128 result is split by the type legalizer into the instruction's two
; destinations (high half in rd8, low half in rd9 -- the multi-part return
; order of contract-abi.md §4.4); nothing joins the halves again.
; CHECK-LABEL: clmul_wide:
; CHECK: clmul.o {rd8, rd9}, rd16, rd17
; CHECK-NOT: clmul.o
; CHECK-NOT: shl
; CHECK-NOT: or.
define i128 @clmul_wide(i64 %a, i64 %b) {
  %r = call i128 @llvm.dadao.clmul.wide(i64 %a, i64 %b)
  ret i128 %r
}

; CHECK-LABEL: clmul_wide_lo:
; CHECK: clmul.o {rd{{[0-9]+}}, rd8}, rd16, rd17
; CHECK-NOT: clmul.o
define i64 @clmul_wide_lo(i64 %a, i64 %b) {
  %r = call i128 @llvm.dadao.clmul.wide(i64 %a, i64 %b)
  %t = trunc i128 %r to i64
  ret i64 %t
}

; CHECK-LABEL: clmul_wide_hi:
; CHECK: clmul.o {rd8, rd{{[0-9]+}}}, rd16, rd17
; CHECK-NOT: clmul.o
define i64 @clmul_wide_hi(i64 %a, i64 %b) {
  %r = call i128 @llvm.dadao.clmul.wide(i64 %a, i64 %b)
  %h = lshr i128 %r, 64
  %t = trunc i128 %h to i64
  ret i64 %t
}
