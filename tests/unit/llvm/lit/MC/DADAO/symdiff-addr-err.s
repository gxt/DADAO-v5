@@ RUN: %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR

@@ Error half of m14-llvm-006: a symbol difference in a branch/address operand
@@ has no encoding.  An ELF relocation carries one symbol plus a constant
@@ addend, so `A - B` cannot be recovered at link time:
@@   * PC-relative forms lose the target address when the difference folds to a
@@     constant; permuting it in place would jump to a wrong address, and a
@@     relocation would name symbol 0 with the difference as addend (before this
@@     task: a silent `R_DADAO_REL26`/`REL20` against symbol 0).
@@   * a cross-section difference never folds and keeps both symbols, which a
@@     single relocation cannot carry either.
@@ Both are hard errors at the operand, with role-specific wording; the single
@@ symbol `VD` (equated to a difference) is named as such, never called a
@@ written-out symbol difference.
@@
@@ Same-section difference as a jump/branch target:
@@ ERR: error: cannot use a symbol difference ('A - B') as a branch/jump target: there is no relocation form for it; use a single symbol or an absolute constant
@@ ERR-NEXT: {{.*}}jump{{.*}}[rb1, L1 - _start]
@@ ERR: error: cannot use a symbol difference ('A - B') as a branch/jump target: there is no relocation form for it; use a single symbol or an absolute constant
@@ ERR-NEXT: {{.*}}br.z{{.*}}[rb0, L1 - _start]
@@ Same-section difference as a PC-relative load offset (base rb0 => REL12):
@@ ERR: error: cannot use a symbol difference ('A - B') as a PC-relative address offset: there is no relocation form for it; use a single symbol or an absolute constant
@@ ERR-NEXT: {{.*}}ld.o{{.*}}[rb0, L1 - _start]
@@ Cross-section difference: jump target and base-relative displacement (ABS12):
@@ ERR: error: cannot use a symbol difference ('A - B') as a branch/jump target: there is no relocation form for it; use a single symbol or an absolute constant
@@ ERR-NEXT: {{.*}}jump{{.*}}[rb1, L1 - other]
@@ ERR: error: cannot use a symbol difference ('A - B') as a base-relative displacement: there is no relocation form for it; use a single symbol or an absolute constant
@@ ERR-NEXT: {{.*}}ld.o{{.*}}[rb2, L1 - other]
@@ An equated symbol whose value is an unresolvable difference is named:
@@ ERR: error: cannot use 'VD' (its value is a symbol difference ('A - B')) as an instruction immediate: there is no relocation form for it; use an absolute constant, or compute the IP at run time (aip.si / rb2rb)
@@ ERR-NEXT: {{.*}}set.zw{{.*}}rb5, wp0, VD

	.text
	.globl	_start
_start:
	swym	0
L1:
	jump	[rb1, L1 - _start]
	br.z	rb1, [rb0, L1 - _start]
	ld.o	rb4, [rb0, L1 - _start]
	jump	[rb1, L1 - other]
	ld.o	rb4, [rb2, L1 - other]
	.set	VD, L1 - other
	set.zw	rb5, wp0, VD
	.section	.data
other:
	.dd.b08	0
