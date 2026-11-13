@@ RUN: %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR

@@ m14-llvm-005 (`ISS-424`) companion: an ABS48 fixup that the assembler itself
@@ resolves must patch the 16-bit wyde selected by the instruction's
@@ wyde-position (never leave the 0 placeholder, never truncate).
@@ A resolved value that does not fit the 48-bit DADAO address space is an
@@ explicit error -- a truncated wyde would be a silently wrong immediate.
@@
@@ ERR: error: absolute address 0x1000000000000 does not fit in the 48-bit DADAO address space
@@ ERR-NEXT: {{.*}}set.zw{{.*}}rb7, wp0, BIG

	.text
	set.zw	rb7, wp0, BIG
	.set	BIG, 0x1000000000000
