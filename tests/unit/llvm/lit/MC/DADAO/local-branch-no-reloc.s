@@ Local labels must keep the assembler's in-place resolution: they cannot be
@@ interposed, so a PC-relative branch/call to a same-section STB_LOCAL /
@@ temporary symbol is folded into the immediate and adds NO relocation
@@ (ISS-482; the rule is "linker-visible" only -- forcing a relocation here
@@ would bloat every local loop and break the raw-bin M1 pipeline,
@@ contract-elf.md §6.1.1/§6.3).
@@
@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t.o
@@ RUN: %llvm_readobj --sections %t.o | %FileCheck %s --check-prefix=SEC
@@ RUN: %llvm_objdump -d %t.o | %FileCheck %s --check-prefix=DIS
@@
@@ SEC-NOT: .rela.text
@@
@@ The offsets confirm the fixups really were resolved in place:
@@   [0x00] br.n   imms18 = (0xc - 0x0) >> 2 = 3 words  -> printed as 12 bytes
@@   [0x04] call   imms24 = (0xc - 0x4) >> 2 = 2 words  -> printed as 8 bytes
@@ DIS: br.n {{.*}}[rb0, 12]
@@ DIS: call [rb0, 8]

	.text
	.globl	_start
_start:
	br.n	{rd1}?, [rb0, Llocal]
	call	[rb0, Llocal]
	swym	0
Llocal:
	swym	0
