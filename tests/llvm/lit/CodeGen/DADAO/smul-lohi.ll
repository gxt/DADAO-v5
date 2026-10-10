;
; RUN: %llc -march=dadao -O2 -verify-machineinstrs -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-076t (M6, ISS-185): 64x64 signed multiply high half / full product.
;
; DADAO's `mul.so rdha, rdhb, rdhc, rdhd` produces the full 128-bit signed
; product (contract-isa.md §6.1.4: rdha:rdhb = rdhc x rdhd, rdha = high 64,
; rdhb = low 64), so ISD::MULHS (one result: the high half) is
; `mul.so dst, rd0, a, b` -- the low half goes to the hardwired-zero rd0 -- and
; ISD::SMUL_LOHI (two results: low, high) is a plain `mul.so {high, low}, a, b`.
;
; The asm printer renders the two rrrr destinations as `{rdhi, rdlo}`.  The
; structural expectations below are derived from the ISA (which half is rdha,
; which is rdhb) and from the ISD::SMUL_LOHI result order (low, high), not from
; the emitted text.  The *semantics* (which half really is the high half) are
; checked by the non-commutative oracle in .work/evidence/LLVM-076t/run.sh --
; an even/odd or XOR merge would be insensitive to a half swap (lessons §8.46).

; --- MULHS with a register operand (the i128 -> i64 arithmetic-shift path) ----
; `((__int128)a * b) >> 64` selects the signed high half only.
; CHECK-LABEL: mulhs_reg:
; CHECK: mul.so {rd{{[1-9][0-9]*}}, rd0}, rd{{[0-9]+}}, rd{{[0-9]+}}
define i64 @mulhs_reg(i64 %a, i64 %b) {
  %ae = sext i64 %a to i128
  %be = sext i64 %b to i128
  %p = mul i128 %ae, %be
  %h = ashr i128 %p, 64
  %r = trunc i128 %h to i64
  ret i64 %r
}

; --- MULHS with a constant operand (signed division by a constant) ----------
; `x / 3` is lowered by TargetLowering::BuildSDIV to a magic-constant multiply
; whose signed high half is needed; the constant is materialised into a GPRD
; register (CONST_WYDE) first, so the same high-half multiply is selected.
; CHECK-LABEL: sdiv3:
; CHECK: set.zw
; CHECK: mul.so {rd{{[1-9][0-9]*}}, rd0}, rd{{[0-9]+}}, rd{{[0-9]+}}
define i64 @sdiv3(i64 %x) {
  %d = sdiv i64 %x, 3
  ret i64 %d
}

; --- the ISS-185 minimal reproduction: (a*b)/3 (signed) ----------------------
; The i64 product (low half, high discarded to rd0) feeds the magic-constant
; divide, which needs the signed high half again.  The low 64 bits of a signed
; product equal those of the unsigned one, so the 64-bit `mul` is `mul.uo`.
; CHECK-LABEL: muldiv3:
; CHECK: mul.uo {rd0, rd{{[1-9][0-9]*}}}, rd{{[0-9]+}}, rd{{[0-9]+}}
; CHECK: mul.so {rd{{[1-9][0-9]*}}, rd0}, rd{{[0-9]+}}, rd{{[0-9]+}}
define i64 @muldiv3(i64 %a, i64 %b) {
  %m = mul i64 %a, %b
  %d = sdiv i64 %m, 3
  ret i64 %d
}

; --- SMUL_LOHI: the full 128-bit product ------------------------------------
; Both halves are used, so the whole signed product is kept and selected to a
; single `mul.so` with two real destinations (neither is rd0).  ISD::SMUL_LOHI's
; result order is (low, high) while mul.so's defs are (high, low), so the
; operand order is swapped by the pseudo expansion.
; NOTE the merge is `hi - lo` (non-commutative, lessons §8.46): a `lo ^ hi`
; would be insensitive to a high/low swap and could not detect the bug.
; CHECK-LABEL: smul128_delta:
; CHECK: mul.so {rd{{[1-9][0-9]*}}, rd{{[1-9][0-9]*}}}, rd{{[0-9]+}}, rd{{[0-9]+}}
define i64 @smul128_delta(i64 %a, i64 %b) {
  %ae = sext i64 %a to i128
  %be = sext i64 %b to i128
  %p = mul i128 %ae, %be
  %lo = trunc i128 %p to i64
  %shi = ashr i128 %p, 64
  %hi = trunc i128 %shi to i64
  %x = sub i64 %hi, %lo
  ret i64 %x
}
