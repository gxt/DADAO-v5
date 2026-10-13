;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-069t (M6): integer compare-as-value and select lowering.  A comparison
; whose result is *used as a value* (C `a == b`, `a < b`, `!x`, `?:`, `&&`/`||`)
; must lower to a cmp* (`contract-isa.md` §6.2) followed by a cs.* conditional
; assignment (§6.5), never a plain compare+branch.
;
;   cmp.so / cmp.si : signed compare  (result -1/0/1)
;   cmp.uo / cmp.ui : unsigned compare
;   cs.n / cs.z / cs.p : cond < 0 / == 0 / > 0 conditional assign
;
; The predicate -> test mapping is derived from the contract, not the
; implementation: `<` tests cond < 0 (cs.n), `>` cond > 0 (cs.p),
; `==`/`!=` cond == 0 (cs.z); `<=` / `>=` reuse a `>` / `<` test with the
; arms swapped (still cs.p / cs.n).  Signed predicates use cmp.so, unsigned
; cmp.uo.
;

; --- setcc used as a value (icmp + zext to the 0/1 i64 result) --------------

; CHECK-LABEL: p_eq:
; CHECK:         cmp.so
; CHECK:         cs.z
define i64 @p_eq(i64 %a, i64 %b) {
  %c = icmp eq i64 %a, %b
  %z = zext i1 %c to i64
  ret i64 %z
}

; CHECK-LABEL: p_ne:
; CHECK:         cmp.so
; CHECK:         cs.z
define i64 @p_ne(i64 %a, i64 %b) {
  %c = icmp ne i64 %a, %b
  %z = zext i1 %c to i64
  ret i64 %z
}

; CHECK-LABEL: p_slt:
; CHECK:         cmp.so
; CHECK:         cs.n
define i64 @p_slt(i64 %a, i64 %b) {
  %c = icmp slt i64 %a, %b
  %z = zext i1 %c to i64
  ret i64 %z
}

; CHECK-LABEL: p_sle:
; CHECK:         cmp.so
; CHECK:         cs.p
define i64 @p_sle(i64 %a, i64 %b) {
  %c = icmp sle i64 %a, %b
  %z = zext i1 %c to i64
  ret i64 %z
}

; CHECK-LABEL: p_sgt:
; CHECK:         cmp.so
; CHECK:         cs.p
define i64 @p_sgt(i64 %a, i64 %b) {
  %c = icmp sgt i64 %a, %b
  %z = zext i1 %c to i64
  ret i64 %z
}

; CHECK-LABEL: p_sge:
; CHECK:         cmp.so
; CHECK:         cs.n
define i64 @p_sge(i64 %a, i64 %b) {
  %c = icmp sge i64 %a, %b
  %z = zext i1 %c to i64
  ret i64 %z
}

; CHECK-LABEL: p_ult:
; CHECK:         cmp.uo
; CHECK:         cs.n
define i64 @p_ult(i64 %a, i64 %b) {
  %c = icmp ult i64 %a, %b
  %z = zext i1 %c to i64
  ret i64 %z
}

; CHECK-LABEL: p_ule:
; CHECK:         cmp.uo
; CHECK:         cs.p
define i64 @p_ule(i64 %a, i64 %b) {
  %c = icmp ule i64 %a, %b
  %z = zext i1 %c to i64
  ret i64 %z
}

; CHECK-LABEL: p_ugt:
; CHECK:         cmp.uo
; CHECK:         cs.p
define i64 @p_ugt(i64 %a, i64 %b) {
  %c = icmp ugt i64 %a, %b
  %z = zext i1 %c to i64
  ret i64 %z
}

; CHECK-LABEL: p_uge:
; CHECK:         cmp.uo
; CHECK:         cs.n
define i64 @p_uge(i64 %a, i64 %b) {
  %c = icmp uge i64 %a, %b
  %z = zext i1 %c to i64
  ret i64 %z
}

; --- select_cc (ternary) lowering -------------------------------------------

; CHECK-LABEL: sel_slt:
; CHECK:         cmp.so
; CHECK:         cs.n
define i64 @sel_slt(i64 %a, i64 %b, i64 %t, i64 %f) {
  %c = icmp slt i64 %a, %b
  %r = select i1 %c, i64 %t, i64 %f
  ret i64 %r
}

; CHECK-LABEL: sel_ult:
; CHECK:         cmp.uo
; CHECK:         cs.n
define i64 @sel_ult(i64 %a, i64 %b, i64 %t, i64 %f) {
  %c = icmp ult i64 %a, %b
  %r = select i1 %c, i64 %t, i64 %f
  ret i64 %r
}

; `>=` reuses a `<` test with the arms swapped (cs.n).
; CHECK-LABEL: sel_sge:
; CHECK:         cmp.so
; CHECK:         cs.n
define i64 @sel_sge(i64 %a, i64 %b, i64 %t, i64 %f) {
  %c = icmp sge i64 %a, %b
  %r = select i1 %c, i64 %t, i64 %f
  ret i64 %r
}

; A constant arm is materialised into GPRD and selected by the same pattern.
; CHECK-LABEL: sel_const:
; CHECK:         cmp.so
; CHECK:         set.zw
; CHECK:         cs.n
define i64 @sel_const(i64 %a, i64 %b) {
  %c = icmp slt i64 %a, %b
  %r = select i1 %c, i64 11, i64 22
  ret i64 %r
}

; A `select` with a non-setcc condition (cond != 0) is a cs.z test.
; CHECK-LABEL: sel_noncc:
; CHECK:         cs.z
define i64 @sel_noncc(i64 %a, i64 %t, i64 %f) {
  %c = trunc i64 %a to i1
  %r = select i1 %c, i64 %t, i64 %f
  ret i64 %r
}
