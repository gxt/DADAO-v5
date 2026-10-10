;
; RUN: %llc -march=dadao -O2 -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-070t (M6, ISS-180 / G6): the DADAO target has no tail-call instruction
; -- every `call` pushes a return address on the RegRAS (`ra63`;
; contract-abi.md §2.3), and there is no tail-jump form that would reuse the
; caller's return address.  A `tail call` lowered as a plain `call` therefore
; makes the callee return to the instruction *after* the call; when the call is
; the caller's last instruction that is the callee's own entry (or the next
; function), a silent infinite loop.
;
; The backend must decline the tail-call form (TargetLowering::LowerCall clears
; CallLoweringInfo::IsTailCall) and emit an ordinary call followed by a real
; return.  This test fails -- `warm` would end after `call` with no `ret` --
; if the tail-call form is ever emitted again.
;
target triple = "dadao-unknown-elf"

declare void @body(i32)

; CHECK-LABEL: warm:
; The call is emitted normally (return address pushed) ...
; CHECK: call {{.*}}body
; ... and the caller returns to *its* caller -- it must not fall through into
; the next function / back into itself.
; CHECK-NEXT: ret

define void @warm(i32 %heat) {
entry:
  tail call void @body(i32 1)
  ret void
}
