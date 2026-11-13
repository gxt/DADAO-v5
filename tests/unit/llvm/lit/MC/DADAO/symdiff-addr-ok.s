@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
@@ RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
@@ RUN: %llvm_readobj -r %t | %FileCheck %s --check-prefix=REL

@@ Non-regression + `.set` half of m14-llvm-006.  The unified symbol-difference
@@ judgement must keep the representable cases byte-for-byte unchanged and
@@ must accept a single symbol whose equated value is a same-section label
@@ difference (`ISS-430`): the assembler folds it to a constant.
@@
@@ `ld.o rb4, [rb2, L1 - L0]`: base-relative displacement `L1 - L0 = 4`
@@ (non-regression from `m14-llvm-005`; imms12 holds the byte offset):
@@ OBJ: {{[0-9a-f]+:}} 22 10 20 04{{.*}}ld.o{{.*}}rb4, [rb2, 4]
@@ `.set VD, L1 - L0` makes VD the absolute value 4; `set.zw` encodes it
@@ (op 0x4E | ha(rb9)=9<<2=0x24 | wp0<<16 | 0x0004):
@@ OBJ: {{[0-9a-f]+:}} 4e 24 00 04{{.*}}set.zw{{.*}}rb9, wp0, 0x4
@@ The same equated symbol works as a base-relative displacement (ABS12):
@@ OBJ: {{[0-9a-f]+:}} 22 14 20 04{{.*}}ld.o{{.*}}rb5, [rb2, 4]
@@ A bare same-section symbol target still resolves in place: `jump` at 0x10,
@@ L1 at 4 => displacement -12, imms24 = -3 = 0xFFFFFD (op 0x70):
@@ OBJ: {{[0-9a-f]+:}} 70 ff ff fd{{.*}}jump{{.*}}[rb0, -12]
@@ A numeric branch offset is still encoded as written (op 0x72 | {rb5}? 0x17 |
@@ imms18 = -0x420>>2 = -0x108 => 0x3FEF8):
@@ OBJ: {{[0-9a-f]+:}} 72 17 fe f8{{.*}}br.z{{.*}}rb5{{.*}}[rb0, -1056]
@@
@@ None of these foldable forms may leave a relocation behind (a symbol-0
@@ relocation with the difference as addend was the m14-llvm-006 bug):
@@ REL-NOT: R_DADAO

	.text
	.globl	_start
_start:
L0:
	swym	0
L1:
	ld.o	rb4, [rb2, L1 - L0]
	.set	VD, L1 - L0
	set.zw	rb9, wp0, VD
	.set	VD2, L1 - L0
	ld.o	rb5, [rb2, VD2]
	jump	[rb0, L1]
	br.z	{rb5}?, [rb0, -0x420]
