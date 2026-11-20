@@ RUN: %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o /dev/null 2>&1 | %FileCheck %s

@@ LLVM-062t / ISS-043: an out-of-range PC-relative branch target must be
@@ rejected with a diagnostic, not silently truncated to the immediate field.
@@ The rrii branch (br.eq) has a 12-bit signed word displacement (+/-2047 words
@@ = +/-8188 bytes); a target 12000 bytes away does not fit.
@@
@@ The target is a *local* label on purpose: a local label is folded in the
@@ assembler, so the range is known here.  A linker-visible (global/weak) target
@@ is recorded as a relocation instead (ISS-482) and its range is the linker's
@@ link-time error (contract-elf.md §3.2; covered end-to-end by mcmodel.test).
	.text
	br.eq {rd8, rd9}?, [rb0, L]
	.space 12000
L:

@@ CHECK: error: branch/jump target out of range for a 12-bit PC-relative immediate
