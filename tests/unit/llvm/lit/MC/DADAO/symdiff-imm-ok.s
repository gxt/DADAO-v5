@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
@@ RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
@@ RUN: %llvm_readobj -r %t | %FileCheck %s --check-prefix=REL

@@ Non-regression half of m14-llvm-005 (`ISS-424`): the symbol-difference
@@ rejection must not disturb the immediates that *are* representable.
@@
@@ Pure numeric immediate (immu16) encodes as before:
@@ `set.zw rb1, wp0, 16`: op 0x4E | ha(rb1)=1<<18 | wp0<<16 | 0x0010.
@@ OBJ: {{[0-9a-f]+:}} 4e 04 00 10{{.*}}set.zw{{.*}}rb1, wp0, 0x10
@@ An absolute symbolic constant plus a constant (`ENTRY + const`) still folds
@@ at parse time -- no relocation, one symbol only, so it is not a difference:
@@ OBJ: {{[0-9a-f]+:}} 4c 08 10 10{{.*}}set.zw{{.*}}rd2, wp0, 0x1010
@@ A relocatable symbol plus a constant still becomes one R_DADAO_ABS48 record
@@ (field left 0 for the linker; addend carries +0x20):
@@ OBJ: {{[0-9a-f]+:}} 49 0d 00 00{{.*}}andn.w{{.*}}rd3, wp1, 0x0
@@ A same-section label difference in a load/store *displacement* (imms12,
@@ ABS12) is resolved in place by the assembler (L1-L0 = 4, unchanged):
@@ OBJ: {{[0-9a-f]+:}} 22 10 20 04{{.*}}ld.o{{.*}}rb4, [rb2, 4]
@@ A forward absolute symbol (`.set` after use) resolves the ABS48 fixup in the
@@ assembler; the wyde selected by wp is written, not the 0 placeholder:
@@ OBJ: {{[0-9a-f]+:}} 4e 14 12 34{{.*}}set.zw{{.*}}rb5, wp0, 0x1234
@@ OBJ: {{[0-9a-f]+:}} 4e 19 00 12{{.*}}set.zw{{.*}}rb6, wp1, 0x12
@@ A plain symbol operand (no difference) still goes to a relocation:
@@ OBJ: {{[0-9a-f]+:}} 5a 1c 00 00{{.*}}aip.si{{.*}}rb7, 0
@@ OBJ: {{[0-9a-f]+:}} 4e 20 00 00{{.*}}set.zw{{.*}}rb8, wp0, 0x0
@@
@@ REL: R_DADAO_ABS48 target 0x20
@@ REL: R_DADAO_PCREL_HI target 0x0
@@ REL: R_DADAO_ABS48 target 0x0
@@

	.text
L0:
	swym	0
L1:
	set.zw	rb1, wp0, 16
	.set	ENTRY, 0x1000
	set.zw	rd2, wp0, ENTRY + 0x10
	.globl	target
target:
	andn.w	rd3, wp1, target + 0x20
	ld.o	rb4, [rb2, L1 - L0]
	set.zw	rb5, wp0, FW
	.set	FW, 0x1234
	set.zw	rb6, wp1, FW2
	.set	FW2, 0x123456
	aip.si	rb7, target
	set.zw	rb8, wp0, target
