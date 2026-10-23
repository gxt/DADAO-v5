@@ ABI probe for LLVM-127t / ISS-310.
@@
@@ `ext_reg` / `ext_reg_u` copy the *whole* 64-bit rd16 argument register to the
@@ return register rd8 without any re-extension.  A C caller that follows
@@ contract-abi.md §4.2 therefore hands over a canonical value: sign-extended
@@ for a signed `int` (0xFFFF_FFFF_FFFF_FFFF for -1), zero-extended for an
@@ `unsigned int` (0x0000_0000_FFFF_FFFF for 0xFFFFFFFF).  Before the frontend
@@ fix an `int` argument arrived zero-extended, which this probe observes as
@@ +4294967295 instead of -1.
@@
@@ The two symbols are identical on purpose: the signedness lives in the C
@@ caller's ABI classification, not in the callee.
	.text
	.globl	ext_reg
	.type	ext_reg,%function
ext_reg:
	rd2rd {rd8}, {rd16}
	ret rd0, 0
	.size	ext_reg, .-ext_reg

	.globl	ext_reg_u
	.type	ext_reg_u,%function
ext_reg_u:
	rd2rd {rd8}, {rd16}
	ret rd0, 0
	.size	ext_reg_u, .-ext_reg_u

	.section	".note.GNU-stack","",%progbits
