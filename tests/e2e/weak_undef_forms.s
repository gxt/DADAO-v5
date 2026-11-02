@@ Every PC-relative branch class against an *undefined weak* symbol
@@ (LLVM-085t / ISS-194).  The linker must resolve the reference to the place
@@ itself instead of reporting `R_DADAO_REL26/20/14 out of range`: a self-loop,
@@ i.e. displacement 0.  REL26 sites that are `call` are additionally rewritten
@@ to the non-calling `jump` opcode so no RegRAS entry is pushed for a callee
@@ that cannot pop it (contracts/opcodes.yaml: call_iiii_ra op 0x74,
@@ jump_iiii_rb op 0x70).
@@
@@ Run through `%ld` and inspect with `%llvm_objdump` (see lit/weak_undef.test).
	.text
	.globl	_start
_start:
	jump	[rb0, weak_jump]	@@ R_DADAO_REL26 -> jump [rb0, 0]
	call	[rb0, weak_call]	@@ R_DADAO_REL26 -> jump [rb0, 0] (opcode rewritten)
	call	[rb0, hidden_weak]	@@ hidden undefined weak: same handling (lld turns
					@@ the binding of a hidden undefined symbol into a
					@@ local one, so this must not be missed)
	ret	rd0, 0

	.globl	main
main:
	br.z	{rb16}?, [rb0, weak_br]	@@ R_DADAO_REL20 -> br.z   ..., [rb0, 0]
	br.eq	{rd8, rd9}?, [rb0, weak_breq]	@@ R_DADAO_REL14 -> br.eq ..., [rb0, 0]
	ret	rd8, 0

	.weak	weak_jump
	.weak	weak_call
	.weak	weak_br
	.weak	weak_breq
	.weak	hidden_weak
	.hidden	hidden_weak
