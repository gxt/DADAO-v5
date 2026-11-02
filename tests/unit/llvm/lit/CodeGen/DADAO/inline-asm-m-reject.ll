;
; RUN: not %llc -march=dadao -O2 -filetype=asm %s -o - 2>&1 | %FileCheck %s
;
; LLVM-119t / ISS-197: unsupported memory constraints must *diagnose*, not crash.
;
; `"V"` (non-offsettable memory) is classified as C_Memory by the generic
; TargetLowering::getConstraintType, but InlineAsm::ConstraintCode has no `V`
; member, so the generic path first trips SelectionDAGBuilder's
; "Failed to convert memory constraint code to constraint id" assertion — i.e.
; a SIGABRT instead of an error message.  DADAO addresses are always
; `[rb, imms12]` (offsettable), so `V` is genuinely unsupported and the target
; reports C_Unknown: the ordinary "unknown asm constraint" diagnostic names the
; constraint and the compile fails with rc=1.
;
; A plain `"m"` operand in the same position selects and prints normally (see
; inline-asm-m.ll); this file pins only the reject path.
; CHECK: unknown asm constraint 'V'
define void @v_input(ptr %p) {
entry:
  call void asm sideeffect "", "*V"(ptr elementtype(i64) %p)
  ret void
}
