;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-079t (P0 ISel gap 1): `fpext (load f32)` (e.g. picolibc `(double)x`
; where `x` is a `volatile float`).  The expected lowering is derived from the
; contracts, not from the old backend:
;
;   * a 4-byte float load uses the RF 4-byte load `ld.t` (contract-fp.md §11
;     "rf_mem": `ld.t`/`st.t` ... `ld.o`/`st.o` 4B/8B);
;   * `fpext f32 -> f64` is the hardware format conversion `ft2fo`
;     (contract-fp.md §2 "convert_ff").
;
; Regression guard: DAGCombiner::visitFP_EXTEND folds `fpext (load f32)` into a
; *widening* any-extend load to f64 whenever the (f64<-f32) EXTLOAD action is
; legal (the default).  That node is unselectable here, and an any-extending
; load is not the fpext the IR asked for, so the backend marks the extension
; illegal (DADAOISelLowering constructor) and the load+fpext pair survives.

; CHECK-LABEL: load_f32_to_f64:
; CHECK:         ld.t
; CHECK:         ft2fo
define double @load_f32_to_f64(ptr %p) {
  %v = load volatile float, ptr %p
  %r = fpext float %v to double
  ret double %r
}

; A plain (non-extending) f64 load is unaffected: `ld.o` into the RF bank.
; CHECK-LABEL: load_f64:
; CHECK:         ld.o
define double @load_f64(ptr %p) {
  %v = load volatile double, ptr %p
  ret double %v
}
