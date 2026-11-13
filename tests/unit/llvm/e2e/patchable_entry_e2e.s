@@ patchable_entry_e2e.s -- m14-llvm-003 end-to-end vector.
@@
@@ `main` is written by hand (the compiler-generated slots live in the C object)
@@ and calls `patched` from tests/unit/llvm/e2e/patchable_entry.c, which is
@@ compiled with `-fpatchable-function-entry=2`.  `patched(41) == 0`, so the
@@ process exit code (the semihosting SYS_EXIT report of rd8) is 0 iff:
@@   * the two `swym 0` slots in front of `patched` are legal, executable words
@@     (a zero/UNDI byte or a wrong slot size traps);
@@   * the call/return path into a function whose entry is a patchable sled works;
@@   * `__patchable_function_entries` links into the image without disturbing
@@     the program (an unhandled SHF_LINK_ORDER orphan section would either be
@@     dropped with a diagnostic or corrupt the layout).
@@
@@ No `.cfi_*` directives on purpose: the DWARF/CFI coverage for the sled belongs
@@ to m14-llvm-004.
@@ `globl main` because crt0 (tests/shared/crt0/minimal_crt0.s) calls it.

	.text
	.globl	main
	.type	main,%function
main:
	set.zw	rd16, wp0, 41		@@ argument: 41
	call	[rb0, patched]		@@ rd8 = patched(41) = 0
	ret	rd0, 0
	.size	main, .-main

	.section	".note.GNU-stack","",%progbits
