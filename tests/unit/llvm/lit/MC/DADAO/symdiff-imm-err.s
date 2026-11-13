@@ RUN: %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR
@@ RUN: %not %clang --target=dadao-unknown-elf -c %S/symdiff-imm-err.c -o /dev/null 2>&1 | %FileCheck %s --check-prefix=CLANG

@@ A symbol *difference* (`A - B`) used as an instruction immediate has no
@@ relocation form: an ELF relocation carries one symbol plus a constant
@@ addend, so the value can never be recovered at link time.  ISS-424: the
@@ assembler used to fold the difference (same-section labels) and then drop
@@ the folded value in the ABS48 applyFixup, i.e. it wrote a *silent* 0 with
@@ no diagnostic; a difference on an instruction with no symbol-operand design
@@ aborted with report_fatal_error.  Both are now a hard error at the operand,
@@ naming the replacement (absolute constant, or run-time IP via aip.si/rb2rb).
@@
@@ The same MC parser backs the clang integrated assembler, so `clang -c` with
@@ inline assembly must report it identically (CLANG prefix).
@@
@@ ERR: error: cannot use a symbol difference ('A - B') as an instruction immediate: there is no relocation form for it; use an absolute constant, or compute the IP at run time (aip.si / rb2rb)
@@ ERR-NEXT: {{.*}}aip.si{{.*}}rb1, . - _start
@@ ERR: error: cannot use a symbol difference ('A - B') as an instruction immediate
@@ ERR-NEXT: {{.*}}set.zw{{.*}}rb1, L1 - L0
@@ ERR: error: cannot use a symbol difference ('A - B') as an instruction immediate
@@ ERR-NEXT: {{.*}}set.zw{{.*}}rb2, wp0, L1 - L0
@@ ERR: error: cannot use a symbol difference ('A - B') as an instruction immediate
@@ ERR-NEXT: {{.*}}add.si{{.*}}rb3, . - _start
@@ ERR: error: cannot use a symbol difference ('A - B') as an instruction immediate
@@ ERR-NEXT: {{.*}}add.si{{.*}}rb4, rb4, . - _start
@@ ERR: error: cannot use a symbol difference ('A - B') as an instruction immediate
@@ ERR-NEXT: {{.*}}set.zw{{.*}}rb5, wp0, VD
@@ ERR: error: cannot use a symbol difference ('A - B') as an instruction immediate
@@ ERR-NEXT: {{.*}}set.zw{{.*}}rb6, wp0, . - other
@@
@@ CLANG: error: cannot use a symbol difference ('A - B') as an instruction immediate
@@ CLANG: compute the IP at run time (aip.si / rb2rb)

	.text
	.globl	_start
_start:
	aip.si	rb1, . - _start
L0:
	swym	0
L1:
	set.zw	rb1, L1 - L0
	set.zw	rb2, wp0, L1 - L0
	add.si	rb3, . - _start
	add.si	rb4, rb4, . - _start
	.set	VD, L1 - L0
	set.zw	rb5, wp0, VD
	set.zw	rb6, wp0, . - other
	.section	.data
other:
	.dd.b08	0
