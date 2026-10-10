;
; RUN: %llc -march=dadao -O2 -verify-machineinstrs -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-073t (M6, ISS-176 / G2): 64x64 multiply high half.
;
; DADAO's `mul.uo rdha, rdhb, rdhc, rdhd` produces the full 128-bit product
; (contract-isa.md §6.1.4: rdha:rdhb = rdhc x rdhd, rdha = high, rdhb = low), so
; ISD::MULHU (one result: the high half) is `mul.uo dst, rd0, a, b` -- the low
; half goes to the hardwired-zero rd0 -- and ISD::UMUL_LOHI (two results: low,
; high) is a plain `mul.uo {high, low}, a, b`.
;
; The asm printer renders the two rrrr destinations as `{rdhi, rdlo}`.  The
; structural expectations below are derived from the ISA (which half is rdha,
; which is rdhb) and from the ISD::UMUL_LOHI result order (low, high), not from
; the emitted text.
;

; --- MULHU with a register operand (the u128 -> u64 shift path) --------------
; `(unsigned __int128)a*b >> 64` selects the high half only.
; CHECK-LABEL: mulhu_reg:
; CHECK: mul.uo {rd{{[1-9][0-9]*}}, rd0}, rd{{[0-9]+}}, rd{{[0-9]+}}
define i64 @mulhu_reg(i64 %a, i64 %b) {
  %ae = zext i64 %a to i128
  %be = zext i64 %b to i128
  %p = mul i128 %ae, %be
  %h = lshr i128 %p, 64
  %r = trunc i128 %h to i64
  ret i64 %r
}

; --- MULHU with a constant operand (unsigned division by a constant) ---------
; `x / 3` is lowered by TargetLowering::BuildUDIV to a magic-constant multiply
; whose high half is needed; the constant is materialised into a GPRD register
; (CONST_WYDE) first, so the same high-half multiply is selected.
; CHECK-LABEL: udiv3:
; CHECK: set.ow
; CHECK: mul.uo {rd{{[1-9][0-9]*}}, rd0}, rd{{[0-9]+}}, rd{{[0-9]+}}
define i64 @udiv3(i64 %x) {
  %d = udiv i64 %x, 3
  ret i64 %d
}

; --- the G2 minimal reproduction: (a*b)/3 -----------------------------------
; The i64 product (low half, high discarded to rd0) feeds the magic-constant
; divide, which needs the high half again.
; CHECK-LABEL: muldiv3:
; CHECK: mul.uo {rd0, rd{{[1-9][0-9]*}}}, rd{{[0-9]+}}, rd{{[0-9]+}}
; CHECK: mul.uo {rd{{[1-9][0-9]*}}, rd0}, rd{{[0-9]+}}, rd{{[0-9]+}}
define i64 @muldiv3(i64 %a, i64 %b) {
  %m = mul i64 %a, %b
  %d = udiv i64 %m, 3
  ret i64 %d
}

; --- UMUL_LOHI: the full 128-bit product (aha-mont64 mulul64) ----------------
; Both halves are used, so the whole product is kept and selected to a single
; `mul.uo` with two real destinations (neither is rd0).  ISD::UMUL_LOHI's result
; order is (low, high) while mul.uo's defs are (high, low), so the operand order
; is swapped by the pseudo expansion.
; CHECK-LABEL: umul128_xor:
; CHECK: mul.uo {rd{{[1-9][0-9]*}}, rd{{[1-9][0-9]*}}}, rd{{[0-9]+}}, rd{{[0-9]+}}
define i64 @umul128_xor(i64 %a, i64 %b) {
  %ae = zext i64 %a to i128
  %be = zext i64 %b to i128
  %p = mul i128 %ae, %be
  %lo = trunc i128 %p to i64
  %hi = lshr i128 %p, 64
  %h = trunc i128 %hi to i64
  %x = xor i64 %lo, %h
  ret i64 %x
}
