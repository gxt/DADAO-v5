;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-121t (ADR-0034 D2; SimRISC-11 §4.1): ordering -> `fence` lowering.
;
; DADAO has no atomic load/store instruction forms and no `__atomic_*`
; runtime, so AtomicExpandPass (enabled by the DADAO pass config) splits every
; atomic access into a plain access plus an explicit barrier, and the backend
; maps the IR ordering to the 18-bit `fm|pred|succ` immediate:
;
;   acquire           -> pred R,       succ R|W        = 0x043 (67)
;   release           -> pred R|W,     succ W          = 0x0C2 (194)
;   acq_rel / seq_cst -> pred R|W|I|O, succ R|W|I|O    = 0x3CF (975)
;   monotonic/unordered -> no fence at all
;
; The expected immediates come from ADR-0034 D2's constant table, not from the
; compiler output.  The position of each fence (before a release store, after
; an acquire load) is the generic AtomicExpandPass scheme, asserted explicitly.
;

; An acquire load is a plain `ld.ut` followed by the acquire fence.
define i32 @ld_acquire(ptr %p) {
; CHECK-LABEL: ld_acquire:
; CHECK: ld.ut rd{{[0-9]+}}, [rb{{[0-9]+}}, 0]
; CHECK-NEXT: fence 67
; CHECK-NEXT: ret
  %v = load atomic i32, ptr %p acquire, align 4
  ret i32 %v
}

; A release store is the release fence followed by a plain `st.t`.
define void @st_release(ptr %p, i32 %v) {
; CHECK-LABEL: st_release:
; CHECK: fence 194
; CHECK: st.t rd{{[0-9]+}}, [rb{{[0-9]+}}, 0]
; CHECK-NEXT: ret
  store atomic i32 %v, ptr %p release, align 4
  ret void
}

; seq_cst load: acquire side gets the full barrier.
define i32 @ld_seq_cst(ptr %p) {
; CHECK-LABEL: ld_seq_cst:
; CHECK: ld.ut rd{{[0-9]+}}, [rb{{[0-9]+}}, 0]
; CHECK-NEXT: fence 975
  %v = load atomic i32, ptr %p seq_cst, align 4
  ret i32 %v
}

; seq_cst store: the default scheme brackets it with a leading and a trailing
; full barrier (release side before, acquire side after).
define void @st_seq_cst(ptr %p, i32 %v) {
; CHECK-LABEL: st_seq_cst:
; CHECK: fence 975
; CHECK: st.t rd{{[0-9]+}}, [rb{{[0-9]+}}, 0]
; CHECK-NEXT: fence 975
  store atomic i32 %v, ptr %p seq_cst, align 4
  ret void
}

; A relaxed (monotonic) access must not emit any barrier at all.
define i32 @ld_relaxed(ptr %p) {
; CHECK-LABEL: ld_relaxed:
; CHECK-NOT: fence
; CHECK: ld.ut rd{{[0-9]+}}, [rb{{[0-9]+}}, 0]
; CHECK-NOT: fence
; CHECK: ret
  %v = load atomic i32, ptr %p monotonic, align 4
  ret i32 %v
}

; Standalone fences: one instruction each, with the table's immediate.
define void @fence_acq() {
; CHECK-LABEL: fence_acq:
; CHECK: fence 67
  fence acquire
  ret void
}

define void @fence_rel() {
; CHECK-LABEL: fence_rel:
; CHECK: fence 194
  fence release
  ret void
}

define void @fence_acq_rel() {
; CHECK-LABEL: fence_acq_rel:
; CHECK: fence 975
  fence acq_rel
  ret void
}

define void @fence_seq_cst() {
; CHECK-LABEL: fence_seq_cst:
; CHECK: fence 975
  fence seq_cst
  ret void
}

;; NOTE: `fence monotonic` / `fence unordered` are not valid IR (the verifier
;; rejects them), so the "monotonic emits nothing" branch of the mapping is
;; covered by @ld_relaxed above rather than by a standalone fence.
