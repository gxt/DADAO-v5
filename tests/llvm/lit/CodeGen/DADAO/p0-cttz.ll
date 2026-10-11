;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-079t (P0 ISel gap 5): `i64 cttz` (picolibc `test-fread-fwrite.c`
; `llvm.cttz.i64`).  The DADAO ISA has *no* bit-scan / population-count
; instruction (`contracts/opcodes.yaml` carries no cttz/ctlz/ctpop op), so the
; backend marks the operation Explicitly `Expand` and LLVM's generic software
; expansion is used (TargetLowering::expandCTTZ -> CTPOP of `~x & (x - 1)`,
; TargetLowering::expandCTPOP).  That sequence bottoms out in ordinary i64
; `xnor`/`and`/`sub`/`shr`/`mul` operations the backend already selects
; (contract-isa.md §6.1/§6.3/§6.4), so there is *no* libcall and no constant
; pool -- both of which this freestanding target lacks.
;
; The checks therefore assert the structural outcome, derived from the ISA:
;   * no `call` (a libcall like __cttzdi2/__popcountdi2 would be unlinkable);
;   * the popcount expansion's final multiply selects `mul.uo`
;     (contract-isa.md §6.1.4 "mul.uo").

; CHECK-LABEL: cttz64:
; CHECK-NOT:     call
; CHECK:         mul.uo
define i64 @cttz64(i64 %x) {
  %r = call i64 @llvm.cttz.i64(i64 %x, i1 false)
  ret i64 %r
}

; The zero-poison flavour (what `__builtin_ctz` with a known-nonzero operand
; produces) uses the same expansion.
; CHECK-LABEL: cttz64_zp:
; CHECK-NOT:     call
; CHECK:         mul.uo
define i64 @cttz64_zp(i64 %x) {
  %r = call i64 @llvm.cttz.i64(i64 %x, i1 true)
  ret i64 %r
}

declare i64 @llvm.cttz.i64(i64, i1 immarg)
