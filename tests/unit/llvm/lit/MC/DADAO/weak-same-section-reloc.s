@@ A PC-relative reference to a *linker-visible* symbol defined in the same
@@ section must still be recorded as a relocation: the definition is
@@ interposable at link time (a strong definition in another object overrides a
@@ weak one), so the displacement must not be folded in place (ISS-482,
@@ contract-elf.md §3.3).
@@
@@ This is the assembler-level root cause of the clang reproduction: without
@@ `-ffunction-sections` a weak definition and its caller land in the same
@@ `.text`, and the call used to be fixed up locally -- the external strong
@@ definition never took over.
@@
@@ Coverage of the PC-relative fixup kinds that can be folded in the assembler
@@ (the shared branch in evaluateFixup): PCRel_24 (call -> REL26), PCRel_18
@@ (br.n* -> REL20), and REL12 (ld/st with base rb0 -> R_DADAO_REL12).  The
@@ absolute kinds (ABS12/ABS48) and the PC-relative hi/lo pair were already
@@ always relocations; ABS12 is asserted here as the control.  Local labels
@@ (STB_LOCAL / temporary symbols) keep the in-place fast path, covered by
@@ local-branch-no-reloc.s.
@@
@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t.o
@@ RUN: %llvm_readobj -r --expand-relocs %t.o | %FileCheck %s --check-prefix=REL
@@
@@ REL: Relocations [
@@ REL:   Section ({{[0-9]+}}) .rela.text {
@@ REL:     Offset: 0x8
@@ REL:     Type: R_DADAO_REL26 (1)
@@ REL:     Symbol: weak_hook
@@ REL:     Offset: 0xC
@@ REL:     Type: R_DADAO_REL26 (1)
@@ REL:     Symbol: strong_fn
@@ REL:     Offset: 0x10
@@ REL:     Type: R_DADAO_REL20 (2)
@@ REL:     Symbol: strong_fn
@@ REL:   }
@@ REL:   Section ({{[0-9]+}}) .rela.data {
@@ REL:     Offset: 0x8
@@ REL:     Type: R_DADAO_REL12 (4)
@@ REL:     Symbol: weak_slot
@@ REL:     Offset: 0xC
@@ REL:     Type: R_DADAO_ABS12 (5)
@@ REL:     Symbol: weak_slot
@@ REL:   }
@@ REL: ]

	.text
	.weak	weak_hook
weak_hook:
	ret	rd0, 0
	.globl	strong_fn
strong_fn:
	ret	rd0, 0
	.globl	caller
caller:
	call	[rb0, weak_hook]
	call	[rb0, strong_fn]
	br.nz	{rd8}?, [rb0, strong_fn]
	ret	rd0, 0

	.data
	.weak	weak_slot
weak_slot:
	.dd.o64	0
	.globl	reader
reader:
	ld.o	rd8, [rb0, weak_slot]
	ld.o	rd8, [rb9, weak_slot]
