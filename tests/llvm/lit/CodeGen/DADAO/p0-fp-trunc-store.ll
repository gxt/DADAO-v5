;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-088t (ISS-193 (d)): storing a truncated `double` as a `float` (C
; `*p = (float)x` / `*(float *)&out = d`).  The expected lowering is derived
; from the contracts, not from the backend:
;
;   * `fptrunc f64 -> f32` is the hardware format conversion `fo2ft`
;     (contract-fp.md §2 "convert_ff");
;   * a 4-byte float store uses the RF 4-byte store `st.t` (contract-fp.md §11
;     "rf_mem": `ld.t`/`st.t` ... `ld.o`/`st.o` 4B/8B).
;
; Regression guard: the (f32<-f64) TRUNCSTORE action is legal by default, so
; DAGCombiner folds `store (fptrunc f64)` into an unselectable truncating store
; ("Cannot select: ... trunc to f32").  The backend marks the action Expand
; (DADAOISelLowering constructor), which disables the fold and lets the fptrunc
; reach ISel as FP_ROUND -> fo2ft + plain st.t.
;

; CHECK-LABEL: trunc_store:
; CHECK:         fo2ft
; CHECK:         st.t
define void @trunc_store(double %x, ptr %p) {
  %t = fptrunc double %x to float
  store float %t, ptr %p
  ret void
}

; A plain f32 store is unaffected: `st.t` with no conversion.
; CHECK-LABEL: store_f32:
; CHECK-NOT:     fo2ft
; CHECK:         st.t
define void @store_f32(float %x, ptr %p) {
  store float %x, ptr %p
  ret void
}

; A plain f64 store is unaffected: `st.o` (8-byte, RF bank).
; CHECK-LABEL: store_f64:
; CHECK-NOT:     fo2ft
; CHECK:         st.o
define void @store_f64(double %x, ptr %p) {
  store double %x, ptr %p
  ret void
}
