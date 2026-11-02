;
; RUN: %llc -march=dadao -O2 -code-model=large -filetype=asm %s -o - | %FileCheck %s
; RUN: %llc -march=dadao -O2 -code-model=small -filetype=asm %s -o - | %FileCheck %s --check-prefix=SMALL
; RUN: %not --crash %llc -march=dadao -O2 -code-model=medium -filetype=asm %s -o /dev/null 2>&1 | %FileCheck %s --check-prefix=REJECT
;
; LLVM-131t (ADR-0036 D1/D2/D5): code model `default` (CodeModel::Small) versus
; `large`.
;
; The direct call/jump form reaches its target through a 24-bit PC-relative
; word offset (R_DADAO_REL26, contract-elf.md §3.1) => +/-32 MiB.  Under
; `large`, a call/jump target that is not an import is therefore materialized
; as an absolute 48-bit address (the fixed 3-slice ABS48 sequence `set.zw` +
; 2x `or.w`) in an RB register and reached through the indirect forms
; `call [rb, rd0, 0]` / `jump [rb, rd0, 0]` (contract-isa.md §8.3/§8.5).
; `small` (== the default) keeps the PC-relative forms.
;
; A tail-jump materializes into a *call-clobbered* RB register (GPRBTC): the
; epilogue is emitted immediately before the terminating jump, so a
; callee-saved base would be clobbered by its restore.
;
; `medium` / `kernel` / `tiny` have no DADAO meaning and must fail loudly
; rather than be lowered as one of the two real models (ADR-0036 D2).
target triple = "dadao-unknown-elf"

declare i64 @callee(i64)

; CHECK-LABEL: call_large:
; CHECK: set.zw rb{{[0-9]+}}, wp0, callee
; CHECK: or.w rb{{[0-9]+}}, wp1, callee
; CHECK: or.w rb{{[0-9]+}}, wp2, callee
; CHECK: call [rb{{[0-9]+}}, rd0, 0]
; CHECK-NOT: call [rb0,
define i64 @call_large(i64 %x) {
entry:
  %r = call i64 @callee(i64 %x)
  ret i64 %r
}

; A tail call becomes an indirect `jump` to the materialized address.  Its base
; register must be call-clobbered (rb4-rb31): the epilogue runs between the
; materialization and the jump.
; CHECK-LABEL: tail_large:
; CHECK: set.zw rb{{[0-9]+}}, wp0, callee
; CHECK: or.w rb{{[0-9]+}}, wp1, callee
; CHECK: or.w rb{{[0-9]+}}, wp2, callee
; CHECK: jump [rb{{[0-9]+}}, rd0, 0]
define i64 @tail_large(i64 %x) {
entry:
  %r = tail call i64 @callee(i64 %x)
  ret i64 %r
}

; SMALL-LABEL: call_small:
; SMALL: call [rb0, callee]
; SMALL-NOT: rd0, 0]
define i64 @call_small(i64 %x) {
entry:
  %r = call i64 @callee(i64 %x)
  ret i64 %r
}

; SMALL-LABEL: tail_small:
; SMALL: jump [rb0, callee]
define i64 @tail_small(i64 %x) {
entry:
  %r = tail call i64 @callee(i64 %x)
  ret i64 %r
}

; A compiler-generated libcall has no GlobalValue in the call: it arrives as an
; ISD::ExternalSymbol (`memcpy`).  It takes the same absolute form as any other
; callee under the static relocation model -- in a statically resolved image
; there is nothing to import, so the linker is free to place the routine
; anywhere and a PC-relative call could overflow.
; SMALL: call [rb0, memcpy]
; CHECK-LABEL: copy64:
; CHECK: set.zw rb{{[0-9]+}}, wp0, memcpy
; CHECK: or.w rb{{[0-9]+}}, wp1, memcpy
; CHECK: or.w rb{{[0-9]+}}, wp2, memcpy
; CHECK: call [rb{{[0-9]+}}, rd0, 0]
declare void @llvm.memcpy.p0.p0.i64(ptr, ptr, i64, i1)
define void @copy64(ptr %d, ptr %s) {
entry:
  call void @llvm.memcpy.p0.p0.i64(ptr %d, ptr %s, i64 64, i1 false)
  ret void
}

; REJECT: DADAO: unsupported code model
