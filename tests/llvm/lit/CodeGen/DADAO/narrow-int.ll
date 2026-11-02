; RUN: %llc -march=dadao -O2 -verify-machineinstrs -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-127t (M9): narrow integer types are legal, so the ISA's 8/16/32-bit
; instructions are selected directly (contract-isa.md §10/§11/§12).
;
;   add/sub/mul.{sb,sw,st}      one destination, result sign-extended
;   div/rem.{ub,uw,ut,sb,sw,st} signedness from the node (udiv/sdiv...)
;   shl.{b,w,t} shr.{ub,uw,ut,sb,sw,st}
;   cmp.{sb,sw,st,ub,uw,ut}     -> i64 {-1,0,1}, then cs.* normalisation
;   ext.uo / ext.so             explicit zero/sign extension, one instruction
;
; The narrow result has no defined upper half; every 64-bit consumer extends it
; explicitly (contract-abi.md §4.2).  ADD/SUB/MUL are sign-agnostic in LLVM, so
; they use the `.s*` form (low N bits are the result, high half canonical sign
; extension); UDIV/UREM use `.u*` and SDIV/SREM `.s*`.
;
; Since ADR-0037 D1 an unsigned narrow compare writes -1 as 64-bit all-ones
; (contract-isa.md §10.2/§11.2/§12.2), i.e. the same {-1,0,1} value as the
; signed forms, so no `ext.so` normalisation is needed before the sign tests
; (LLVM-134t removed the redundant extension).  See cmp-u-branch.ll for the
; consumer-side assertions (sign-family branch, never a zero test).
;
; Below every arithmetic/shift/compare case is ONE instruction plus the
; return-value extension; the 64-bit control case at the bottom still uses the
; 128-bit `add.uo {rd0, ...}` form.

target triple = "dadao-unknown-elf"

; --- i32 arithmetic ---------------------------------------------------------
; CHECK-LABEL: add32:
; CHECK:         add.st rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     add.uo
; CHECK-NOT:     ext.so
define i32 @add32(i32 %a, i32 %b) {
  %r = add i32 %a, %b
  ret i32 %r
}

; CHECK-LABEL: sub32:
; CHECK:         sub.st rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     sub.uo
define i32 @sub32(i32 %a, i32 %b) {
  %r = sub i32 %a, %b
  ret i32 %r
}

; mul32 is the single-destination `mul.st`, not the 128-bit `mul.uo {rd0, ...}`.
; CHECK-LABEL: mul32:
; CHECK:         mul.st rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     mul.uo
define i32 @mul32(i32 %a, i32 %b) {
  %r = mul i32 %a, %b
  ret i32 %r
}

; CHECK-LABEL: udiv32:
; CHECK:         div.ut rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     div.uo
define i32 @udiv32(i32 %a, i32 %b) {
  %r = udiv i32 %a, %b
  ret i32 %r
}

; CHECK-LABEL: sdiv32:
; CHECK:         div.st rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     div.so
define i32 @sdiv32(i32 %a, i32 %b) {
  %r = sdiv i32 %a, %b
  ret i32 %r
}

; CHECK-LABEL: urem32:
; CHECK:         rem.ut rd{{[0-9]+}}, rd16, rd17
define i32 @urem32(i32 %a, i32 %b) {
  %r = urem i32 %a, %b
  ret i32 %r
}

; CHECK-LABEL: srem32:
; CHECK:         rem.st rd{{[0-9]+}}, rd16, rd17
define i32 @srem32(i32 %a, i32 %b) {
  %r = srem i32 %a, %b
  ret i32 %r
}

; --- i16 / i8 arithmetic ----------------------------------------------------
; CHECK-LABEL: add16:
; CHECK:         add.sw rd{{[0-9]+}}, rd16, rd17
define i16 @add16(i16 %a, i16 %b) {
  %r = add i16 %a, %b
  ret i16 %r
}

; CHECK-LABEL: add8:
; CHECK:         add.sb rd{{[0-9]+}}, rd16, rd17
define i8 @add8(i8 %a, i8 %b) {
  %r = add i8 %a, %b
  ret i8 %r
}

; CHECK-LABEL: mul16:
; CHECK:         mul.sw rd{{[0-9]+}}, rd16, rd17
define i16 @mul16(i16 %a, i16 %b) {
  %r = mul i16 %a, %b
  ret i16 %r
}

; CHECK-LABEL: mul8:
; CHECK:         mul.sb rd{{[0-9]+}}, rd16, rd17
define i8 @mul8(i8 %a, i8 %b) {
  %r = mul i8 %a, %b
  ret i8 %r
}

; --- shifts: register amount (orrr) and constant amount (orri) --------------
; The DAG shift amount is i64 (the target shift-amount type), so the i32 amount
; is zero-extended first; the shift itself is one instruction.
; CHECK-LABEL: shl32:
; CHECK:         shl.t rd{{[0-9]+}}, rd16, rd{{[0-9]+}}
; CHECK-NOT:     shl.o
define i32 @shl32(i32 %a, i32 %b) {
  %r = shl i32 %a, %b
  ret i32 %r
}

; CHECK-LABEL: srl32:
; CHECK:         shr.ut rd{{[0-9]+}}, rd16, rd{{[0-9]+}}
define i32 @srl32(i32 %a, i32 %b) {
  %r = lshr i32 %a, %b
  ret i32 %r
}

; CHECK-LABEL: sra32:
; CHECK:         shr.st rd{{[0-9]+}}, rd16, rd{{[0-9]+}}
define i32 @sra32(i32 %a, i32 %b) {
  %r = ashr i32 %a, %b
  ret i32 %r
}

; Constant amounts fold to the one-instruction immediate form.
; CHECK-LABEL: shlc32:
; CHECK:         shl.t rd{{[0-9]+}}, rd16, 3
; CHECK-NOT:     set.zw
define i32 @shlc32(i32 %a) {
  %r = shl i32 %a, 3
  ret i32 %r
}

; CHECK-LABEL: srac32:
; CHECK:         shr.st rd{{[0-9]+}}, rd16, 7
; CHECK-NOT:     set.zw
define i32 @srac32(i32 %a) {
  %r = ashr i32 %a, 7
  ret i32 %r
}

; --- compares ---------------------------------------------------------------
; Signed: cmp.st writes full-width -1/0/1, cs.n tests the sign directly.
; CHECK-LABEL: cmp_slt:
; CHECK:         cmp.st rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     cmp.so
; CHECK-NOT:     ext.so
define i32 @cmp_slt(i32 %a, i32 %b) {
  %c = icmp slt i32 %a, %b
  %r = zext i1 %c to i32
  ret i32 %r
}

; Unsigned: since ADR-0037 D1 cmp.ut already writes -1 as 64-bit all-ones, the
; value cs.n tests directly; no `ext.so` normalisation is emitted (LLVM-134t).
; CHECK-LABEL: cmp_ult:
; CHECK:         cmp.ut rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     ext.so
; CHECK-NOT:     cmp.uo
define i32 @cmp_ult(i32 %a, i32 %b) {
  %c = icmp ult i32 %a, %b
  %r = zext i1 %c to i32
  ret i32 %r
}

; Branch form: same instructions, then a br.nn on the cmp result.
; CHECK-LABEL: br_slt:
; CHECK:         cmp.st rd{{[0-9]+}}, rd16, rd17
; CHECK:         br.nn
define i32 @br_slt(i32 %a, i32 %b) {
  %c = icmp slt i32 %a, %b
  br i1 %c, label %t, label %f
t:
  ret i32 1
f:
  ret i32 0
}

; CHECK-LABEL: br_ult:
; CHECK:         cmp.ut rd{{[0-9]+}}, rd16, rd17
; CHECK-NOT:     ext.so
; CHECK:         br.nn
define i32 @br_ult(i32 %a, i32 %b) {
  %c = icmp ult i32 %a, %b
  br i1 %c, label %t, label %f
t:
  ret i32 1
f:
  ret i32 0
}

; --- extensions / truncations: one ext.* each -------------------------------
; CHECK-LABEL: zext64:
; CHECK:         ext.uo rd8, rd16, 31
; CHECK-NOT:     and.o
define i64 @zext64(i32 %a) {
  %r = zext i32 %a to i64
  ret i64 %r
}

; CHECK-LABEL: sext64:
; CHECK:         ext.so rd8, rd16, 31
define i64 @sext64(i32 %a) {
  %r = sext i32 %a to i64
  ret i64 %r
}

; `zext(trunc x)` is folded by DAGCombine into a width mask on the i64 value;
; the mask patterns turn that into the same one-instruction ext.uo.
; CHECK-LABEL: z32:
; CHECK:         ext.uo rd8, rd16, 31
; CHECK-NOT:     and.o
define i64 @z32(i64 %x) {
  %t = trunc i64 %x to i32
  %r = zext i32 %t to i64
  ret i64 %r
}

; CHECK-LABEL: z16:
; CHECK:         ext.uo rd8, rd16, 15
; CHECK-NOT:     and.o
define i64 @z16(i64 %x) {
  %t = trunc i64 %x to i16
  %r = zext i16 %t to i64
  ret i64 %r
}

; CHECK-LABEL: z8:
; CHECK:         ext.uo rd8, rd16, 7
; CHECK-NOT:     and.o
define i64 @z8(i64 %x) {
  %t = trunc i64 %x to i8
  %r = zext i8 %t to i64
  ret i64 %r
}

; `sext(trunc x)` is `sign_extend_inreg`, one ext.so from the width bit.
; CHECK-LABEL: s32:
; CHECK:         ext.so rd8, rd16, 31
define i64 @s32(i64 %x) {
  %t = trunc i64 %x to i32
  %r = sext i32 %t to i64
  ret i64 %r
}

; CHECK-LABEL: s16:
; CHECK:         ext.so rd8, rd16, 15
define i64 @s16(i64 %x) {
  %t = trunc i64 %x to i16
  %r = sext i16 %t to i64
  ret i64 %r
}

; CHECK-LABEL: s8:
; CHECK:         ext.so rd8, rd16, 7
define i64 @s8(i64 %x) {
  %t = trunc i64 %x to i8
  %r = sext i8 %t to i64
  ret i64 %r
}

; --- i64 control: unchanged ------------------------------------------------
; CHECK-LABEL: add64:
; CHECK:         add.uo {rd0, rd8}, rd16, rd17
define i64 @add64(i64 %a, i64 %b) {
  %r = add i64 %a, %b
  ret i64 %r
}
