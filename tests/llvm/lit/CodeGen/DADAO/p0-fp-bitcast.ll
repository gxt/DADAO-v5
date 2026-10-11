;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-079t (P0 ISel gap 3): `bitcast double <-> i64` (C `union`/type punning,
; and the middle step of the generic fabs/copysign expansion).  The expected
; instructions come from contract-fp.md §12 "rf_move":
;
;   * `rd2rf` copies 64 bits RD -> RF unchanged (f64 from i64);
;   * `rf2rd` copies 64 bits RF -> RD unchanged (i64 from f64).
;
; Both are block moves with no numeric conversion, i.e. exactly a bitcast.

; CHECK-LABEL: d_to_i:
; CHECK:         rf2rd
define i64 @d_to_i(double %a) {
  %r = bitcast double %a to i64
  ret i64 %r
}

; CHECK-LABEL: i_to_d:
; CHECK:         rd2rf
define double @i_to_d(i64 %a) {
  %r = bitcast i64 %a to double
  ret double %r
}
