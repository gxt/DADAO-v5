@@ CFI end-to-end probe (m14-llvm-004).
@@
@@ A hand-written function with .cfi_startproc/.cfi_endproc and a few CFI state
@@ directives must assemble, link through the shared crt0 + Tiny linker script
@@ and still run: CFI directives describe unwind state, they must not change
@@ code semantics.  The program returns 0 (all checks pass) in rd8, which
@@ minimal_crt0 turns into the semihosting SYS_EXIT status.
@@
@@ The .eh_frame section is an orphan for the Tiny script (which has no DISCARD
@@ rule for it), so it must survive linking and show up in the linked image --
@@ that is what makes `.eh_frame` linkability observable here.
	.text
	.globl	main
	.type	main,%function
main:
	.cfi_startproc
	.cfi_def_cfa rb1, 8
	add.si	rd8, 0
	.cfi_def_cfa_offset 16
	.cfi_def_cfa_register rb2
	.cfi_offset rb2, -8
	.cfi_offset rf8, -8
	.cfi_offset ra63, -8
	swym	0
	.cfi_endproc
	.size	main, .-main
	ret	rd0, 0
