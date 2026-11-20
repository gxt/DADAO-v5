@@ RUN: %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o /dev/null 2>&1 | %FileCheck %s

@@ LLVM-062t / ISS-043: an out-of-range PC-relative branch target must be
@@ rejected with a diagnostic, not silently truncated to the immediate field.
@@ The riii branch (br.n) has an 18-bit signed word displacement (+/-131071 words
@@ = +/-524284 bytes); a target 600000 bytes away does not fit.
@@
@@ The target is a *local* label on purpose (see branch-range-12.s): a
@@ linker-visible target becomes a relocation (ISS-482) whose range is checked by
@@ the linker (contract-elf.md §3.2).
	.text
	br.n {rd8}?, [rb0, L]
	.space 600000
L:

@@ CHECK: error: branch/jump target out of range for a 18-bit PC-relative immediate
