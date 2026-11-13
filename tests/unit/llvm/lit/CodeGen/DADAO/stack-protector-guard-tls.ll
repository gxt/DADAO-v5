; `-mstack-protector-guard=tls` must be rejected by the backend, not silently
; served by the global __stack_chk_guard (m14-llvm-002).
;
; RUN: %not %llc -march=dadao -O1 -filetype=asm %s -o %t.s 2>&1 | %FileCheck %s --check-prefix=ERR
; RUN: %not ls %t.s
;
; The front end already refuses the option for dadao
; (clang/lib/Driver/ToolChains/Clang.cpp: RenderSSPOptions), so this vector
; covers the other entry point: a .ll that carries the module flag directly,
; which is what `llc` consumes.  DADAO has no IR stack guard
; (getIRStackGuard() is null), so without an explicit check both the default
; and the "tls" guard mode would take the SelectionDAG path and the "tls" run
; would quietly read the global symbol -- a TLS canary that the ABI does not
; define.  DADAOTargetLowering::insertSSPDeclarations therefore emits a module
; error (fail closed): llc exits non-zero and writes no output file.
;
; The function needs a real array and a volatile access so the stack protector
; pass still sees a protectable object after the -O1 pipeline.

target datalayout = "E-m:e-p:64:64-i64:64-i128:128-n8:16:32:64-S128"
target triple = "dadao-unknown-elf"

!llvm.module.flags = !{!0}
!0 = !{i32 1, !"stack-protector-guard", !"tls"}

; ERR: error: stack protector guard 'tls' is not supported for target DADAO
; ERR-SAME: use -mstack-protector-guard=global
define i8 @tls_guard(i32 %n) #0 {
entry:
  %buf = alloca [16 x i8], align 1
  %p = getelementptr [16 x i8], ptr %buf, i64 0, i64 0
  store volatile i8 1, ptr %p
  %v = load volatile i8, ptr %p
  ret i8 %v
}

attributes #0 = { noinline sspstrong }
