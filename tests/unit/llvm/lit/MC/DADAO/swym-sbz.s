@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
@@ RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
@@ RUN: echo 'swym 4096'   | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=SBZ
@@ RUN: echo 'swym 262143' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=SBZ

@@ `swym` immu18 SBZ (SimRISC-12 §2; contracts/opcodes.yaml `swym_oiii_imm`):
@@   word = (0x47 << 24) | (0x22 << 18) | immu18
@@   immu18[11:0] = N (idle delay, 0..4095); immu18[17:12] is SBZ.
@@ A value above 4095 therefore sets SBZ bits and encodes an architectural
@@ ILLI word: the assembler MUST reject it (no masking/truncation, and no
@@ silent wrap to a low-12-bit delay), and a hand-crafted word MUST decode
@@ as `<unknown>`.
@@
@@ 4096   = 0x01000 ⇒ immu18[12] = 1    ⇒ word 0x47881000
@@ 262143 = 0x3FFFF ⇒ immu18[17:12]=0x3F ⇒ word 0x478BFFFF

@@ SBZ: swym: reserved encoding
@@ SBZ-SAME: immu18[17:12]

@@ --- hand-crafted SBZ words decode as ILLI ---
@@ OBJ: {{[0-9a-f]+:}} 47 88 10 00{{.*}}<unknown>
	.dd.t32 0x47881000
@@ OBJ: {{[0-9a-f]+:}} 47 8b ff ff{{.*}}<unknown>
	.dd.t32 0x478BFFFF
