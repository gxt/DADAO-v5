;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-079t (P0 ISel gap 4): a `select` whose arms are FP and whose condition is
; an integer comparison (`d = (n < 0) ? t : f`, the picolibc `select_cc
; ... Constant:i64<0> ... setlt` shape).  Expected instructions from the
; contracts:
;
;   * the integer compare writes -1/0/1 into an rd register: `cmp.si` for a
;     signed predicate with a 12-bit signed immediate, `cmp.ui` for ==/!= with
;     a 12-bit unsigned immediate (contract-isa.md §6.2);
;   * the two FP arms are chosen by the rd-conditioned `cs.n`/`cs.z` conditional
;     assignment onto an rf destination (contract-fp.md §10, contract-isa.md
;     §6.5): `n < 0` -> cond < 0 -> cs.n, `n == 0` -> cond == 0 -> cs.z.
;
; The plain `cs.*_rd` / `DADAOFPSelCC` patterns only match integer arms or an FP
; compare, so this mixed case is what the new DADAOCS f64 patterns cover.

; CHECK-LABEL: sel_i_lt:
; CHECK:         cmp.si
; CHECK:         cs.n
define double @sel_i_lt(i64 %n, double %t, double %f) {
  %c = icmp slt i64 %n, 0
  %r = select i1 %c, double %t, double %f
  ret double %r
}

; CHECK-LABEL: sel_i_eq:
; CHECK:         cmp.ui
; CHECK:         cs.z
define double @sel_i_eq(i64 %n, double %t, double %f) {
  %c = icmp eq i64 %n, 0
  %r = select i1 %c, double %t, double %f
  ret double %r
}

; An FP compare selecting FP arms routes through the same cs.* path (foqcmp +
; cs.n, contract-fp.md §8/§10) now that f64 SELECT_CC is custom.
; CHECK-LABEL: sel_fp_lt:
; CHECK:         foqcmp
; CHECK:         cs.n
define double @sel_fp_lt(double %a, double %b, double %t, double %f) {
  %c = fcmp olt double %a, %b
  %r = select i1 %c, double %t, double %f
  ret double %r
}

; A plain `select` (no compare) with FP arms is a cs.z test on the boolean.
; CHECK-LABEL: sel_bool:
; CHECK:         cs.z
define double @sel_bool(i64 %c, double %t, double %f) {
  %b = trunc i64 %c to i1
  %r = select i1 %b, double %t, double %f
  ret double %r
}
