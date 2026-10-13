;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-071t (M6, G1 / ISS-175): a compare against a constant that does NOT fit
; the cmp* 12-bit immediate (contract-isa.md §6.2.1: cmp.si imms12 /
; cmp.ui immu12) must not be rejected; it is compiled by materialising the
; constant into a GPRD register (CONST_WYDE -> set.zw/or.w, C12) and comparing
; with the register-register form cmp.so/cmp.uo (§6.2.2).  A constant that does
; fit still uses the immediate form, which must not regress.
;
; The predicates below are derived from the contract, not the implementation:
; signed -> cmp.so/cmp.si, unsigned -> cmp.uo/cmp.ui, large -> materialise + reg
; form, small -> immediate form; setcc/select_cc -> cs.n/cs.p (§6.5).

; --- select/setcc (i64 compare result) --------------------------------------

; Signed, 5000 > 2047 (simm12 max): materialise + cmp.so.
; CHECK-LABEL: setcc_slt_big:
; CHECK:         set.zw
; CHECK:         cmp.so
; CHECK:         cs.n
define i64 @setcc_slt_big(i64 %a) {
  %c = icmp slt i64 %a, 5000
  %z = zext i1 %c to i64
  ret i64 %z
}

; Unsigned, 8192 > 4095 (immu12 max): materialise + cmp.uo.
; CHECK-LABEL: setcc_ult_big:
; CHECK:         set.zw
; CHECK:         cmp.uo
; CHECK:         cs.n
define i64 @setcc_ult_big(i64 %a) {
  %c = icmp ult i64 %a, 8192
  %z = zext i1 %c to i64
  ret i64 %z
}

; Signed, 2047 == simm12 max: still the immediate form, no materialisation.
; CHECK-LABEL: setcc_slt_small:
; CHECK-NOT:     set.zw
; CHECK:         cmp.si
; CHECK:         cs.n
define i64 @setcc_slt_small(i64 %a) {
  %c = icmp slt i64 %a, 2047
  %z = zext i1 %c to i64
  ret i64 %z
}

; select_cc with a large constant condition: materialise + cmp.so + cs.p.
; CHECK-LABEL: sel_sgt_big:
; CHECK:         set.zw
; CHECK:         cmp.so
; CHECK:         cs.p
define i64 @sel_sgt_big(i64 %a, i64 %t, i64 %f) {
  %c = icmp sgt i64 %a, 5000
  %r = select i1 %c, i64 %t, i64 %f
  ret i64 %r
}

; --- branch on a large constant compare (br(icmp)) --------------------------

; CHECK-LABEL: br_eq_big:
; CHECK:         set.zw
; CHECK:         cmp.so
; CHECK:         br.nz
define void @br_eq_big(i64 %a, ptr %p) {
  %c = icmp eq i64 %a, 7000
  br i1 %c, label %t, label %f
t:
  store i64 1, ptr %p
  ret void
f:
  store i64 0, ptr %p
  ret void
}
