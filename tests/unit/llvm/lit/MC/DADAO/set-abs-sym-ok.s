@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
@@ RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
@@ RUN: %llvm_readobj -r %t | %FileCheck %s --check-prefix=REL

@@ `ISS-430` (m20-llvm-003): a single symbol equated by `.set` to a
@@ same-section label difference is an Absolute symbol.  Once the layout is
@@ final the assembler folds the equate to a plain number, so every value
@@ operand must encode it exactly like the numeric literal with the same
@@ value, with no relocation and no "symbol difference" diagnostic.  The
@@ written-difference forms stay rejected (`symdiff-imm-err.s` /
@@ `symdiff-addr-err.s`); the literal encodings below are pinned
@@ independently by `basic-encoding.s` / `symdiff-addr-ok.s`.
@@
@@ VD = L1 - L0 = 8 bytes (L0 = 0x0, L1 = 0x8).
@@
@@ set.zw rb1, wp0, VD -> op 0x4E | ha(rb1)=1<<18 | wp0<<16 | 0x0008
@@ OBJ: {{[0-9a-f]+:}} 4e 04 00 08{{.*}}set.zw{{.*}}rb1, wp0, 0x8
@@ ld.o rb4, [rb2, VD] -> ABS12 base-relative byte offset 8
@@ OBJ: {{[0-9a-f]+:}} 22 10 20 08{{.*}}ld.o{{.*}}rb4, [rb2, 8]
@@ ld.o rb5, [rb0, VD] -> REL12 with a constant operand (byte offset 8)
@@ OBJ: {{[0-9a-f]+:}} 22 14 00 08{{.*}}ld.o{{.*}}rb5, [rb0, 8]
@@ jump [rb0, VD] -> PCRel_24 word offset 8>>2 = 2
@@ OBJ: {{[0-9a-f]+:}} 70 00 00 02{{.*}}jump{{.*}}[rb0, 8]
@@ br.z rb1, [rb0, VD] -> PCRel_18 word offset 2
@@ OBJ: {{[0-9a-f]+:}} 72 04 00 02{{.*}}br.z{{.*}}rb1{{.*}}[rb0, 8]
@@ An equate to an *address* is not folded to a number: it keeps its symbol
@@ and resolves in place as a target.  ADDR = L1 = 0x8, the jump sits at
@@ 0x1C => displacement 8 - 28 = -20, word offset -5 = 0xFFFFFB.
@@ OBJ: {{[0-9a-f]+:}} 70 ff ff fb{{.*}}jump{{.*}}[rb0, -20]
@@ A negative equated value is a displacement like any numeric literal:
@@ VN = L0 - L1 = -8 => word offset -2 = 0xFFFFFE.
@@ OBJ: {{[0-9a-f]+:}} 70 ff ff fe{{.*}}jump{{.*}}[rb0, -8]
@@ The equate may carry a constant of its own: VO = (L1 - L0) + 4 = 12
@@ => word offset 3.
@@ OBJ: {{[0-9a-f]+:}} 72 04 00 03{{.*}}br.z{{.*}}rb1{{.*}}[rb0, 12]
@@ The remaining PC-relative field widths take the same value: br.eq
@@ (PCRel_12, word offset 2) and call (PCRel_24, word offset 2).
@@ OBJ: {{[0-9a-f]+:}} 6e 20 90 02{{.*}}br.eq{{.*}}[rb0, 8]
@@ OBJ: {{[0-9a-f]+:}} 74 00 00 02{{.*}}call{{.*}}[rb0, 8]
@@
@@ None of these forms may leave a relocation behind.
@@ REL-NOT: R_DADAO

	.text
L0:
	swym	0
	swym	0
L1:
	.set	VD, L1 - L0
	set.zw	rb1, wp0, VD
	ld.o	rb4, [rb2, VD]
	ld.o	rb5, [rb0, VD]
	jump	[rb0, VD]
	br.z	rb1, [rb0, VD]
	.set	ADDR, L1
	jump	[rb0, ADDR]
	.set	VN, L0 - L1
	jump	[rb0, VN]
	.set	VO, (L1 - L0) + 4
	br.z	rb1, [rb0, VO]
	br.eq	{rd8, rd9}?, [rb0, VD]
	call	[rb0, VD]
