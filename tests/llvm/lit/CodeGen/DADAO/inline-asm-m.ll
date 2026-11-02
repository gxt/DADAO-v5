;
; RUN: %llc -march=dadao -O2 -verify-machineinstrs -filetype=asm %s -o - | %FileCheck %s
;
; LLVM-119t / ISS-197 / ISS-222(2): inline-asm *memory* operands.
;
; Before this change the target had no `SelectInlineAsmMemoryOperand` override,
; so SelectionDAGISel::SelectInlineAsmMemoryOperands hit
;   report_fatal_error("Could not match memory address.  Inline asm failure!")
; and the compiler aborted (`llc` rc=134 / SIGABRT, `clang -c` rc=1 with a
; crash backtrace) for *every* `"m"`, `"=m"`, `"+m"`, `"=&m"` operand.  The
; printer side had the mirror problem: AsmPrinter::PrintAsmMemoryOperand's
; default returns "unsupported", which turns `$0` into an empty string.
;
; The address form is the ISA one (contract-isa.md §3.1.1, C13/C14):
;   ld.*/st.*  rd, [rb, imms12]        -- base in the RB (address) bank
; so a memory operand must select to (GPRB base, simm12 offset) and print as
; `[rb, off]`.  The checks below pin that text; the operand is derived from the
; ISA, not from the emitted output.  A frame index in the base position is
; resolved by PrologEpilogInserter (DADAORegisterInfo::eliminateFrameIndex),
; which is why the stack cases carry a real (negative) frame offset.
;
; `%llc ... -verify-machineinstrs` also proves the two machine operands per
; memory operand are laid out the way the printer and PEI expect.

; --- "+m" on a stack slot: one address, referenced twice --------------------
; CHECK-LABEL: stack_tied:
; CHECK: ld.o rd5, [rb{{[0-9]+}}, {{-?[0-9]+}}]
; CHECK: st.o rd5, [rb{{[0-9]+}}, {{-?[0-9]+}}]
define i64 @stack_tied() {
entry:
  %x = alloca i64, align 8
  store i64 10, ptr %x, align 8
  call void asm sideeffect "ld.o rd5, $0\0A\09add.si rd5, 5\0A\09st.o rd5, $0", "=*m,*m,~{rd5},~{memory}"(ptr elementtype(i64) %x, ptr elementtype(i64) %x)
  %r = load i64, ptr %x, align 8
  ret i64 %r
}

; --- "=m" output on a stack slot --------------------------------------------
; CHECK-LABEL: stack_out:
; CHECK: st.o rd5, [rb{{[0-9]+}}, {{-?[0-9]+}}]
define void @stack_out() {
entry:
  %x = alloca i64, align 8
  call void asm sideeffect "st.o rd5, $0", "=*m,~{rd5},~{memory}"(ptr elementtype(i64) %x)
  ret void
}

; --- "m" input on a stack slot ----------------------------------------------
; CHECK-LABEL: stack_in:
; CHECK: ld.o rd5, [rb{{[0-9]+}}, {{-?[0-9]+}}]
define void @stack_in() {
entry:
  %x = alloca i64, align 8
  store i64 3, ptr %x, align 8
  call void asm sideeffect "ld.o rd5, $0", "*m,~{rd5},~{memory}"(ptr elementtype(i64) %x)
  ret void
}

; --- "&m" (early clobber) output on a stack slot ----------------------------
; CHECK-LABEL: stack_early_clobber:
; CHECK: st.o rd5, [rb{{[0-9]+}}, {{-?[0-9]+}}]
define void @stack_early_clobber() {
entry:
  %x = alloca i64, align 8
  call void asm sideeffect "st.o rd5, $0", "=*&m,~{rd5},~{memory}"(ptr elementtype(i64) %x)
  ret void
}

; --- "m" input on a global: the address is materialised into RB ------------
; CHECK-LABEL: global_in:
; CHECK: ld.o rd5, [rb{{[0-9]+}}, 0]
define void @global_in() {
entry:
  call void asm sideeffect "ld.o rd5, $0", "*m,~{rd5},~{memory}"(ptr elementtype(i64) @g)
  ret void
}

; --- "m" input on a *constant* array element: the offset folds into imms12 --
; CHECK-LABEL: array_elem_const:
; CHECK: ld.o rd5, [rb{{[0-9]+}}, {{-?[0-9]+}}]
define void @array_elem_const() {
entry:
  %a = alloca [4 x i64], align 8
  %e = getelementptr [4 x i64], ptr %a, i64 0, i64 2
  call void asm sideeffect "ld.o rd5, $0", "*m,~{rd5},~{memory}"(ptr elementtype(i64) %e)
  ret void
}

; --- "m" input on a variable-index array element: base comes from add.o ----
; CHECK-LABEL: array_elem_var:
; CHECK: add.o
; CHECK: ld.o rd5, [rb{{[0-9]+}}, 0]
define void @array_elem_var(i64 %i) {
entry:
  %a = alloca [4 x i64], align 8
  %e = getelementptr [4 x i64], ptr %a, i64 0, i64 %i
  call void asm sideeffect "ld.o rd5, $0", "*m,~{rd5},~{memory}"(ptr elementtype(i64) %e)
  ret void
}

; --- "m" input on a dereferenced pointer argument --------------------------
; CHECK-LABEL: ptr_deref:
; CHECK: ld.o rd5, [rb{{[0-9]+}}, 0]
define void @ptr_deref(ptr %p) {
entry:
  call void asm sideeffect "ld.o rd5, $0", "*m,~{rd5},~{memory}"(ptr elementtype(i64) %p)
  ret void
}

; --- "p" (address) operand: same memory-class address form ------------------
; CHECK-LABEL: ptr_constraint:
; CHECK: ld.o rd5, [rb{{[0-9]+}}, 0]
define void @ptr_constraint(ptr %p) {
entry:
  call void asm sideeffect "ld.o rd5, $0", "p,~{rd5},~{memory}"(ptr %p)
  ret void
}

@g = global i64 7, align 8
