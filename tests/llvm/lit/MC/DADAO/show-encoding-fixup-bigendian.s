@@ Regression lock for ISS-232 (LLVM-132t): MCFixupKindInfo::TargetOffset is
@@ expressed in the bit order the asm streamer uses for the --show-encoding
@@ comment.  On this big-endian target that order is MSB-first inside the
@@ 32-bit instruction word, so a field sitting in the low N bits starts at
@@ offset 32-N (imms12 -> 20, imms18 -> 14).  The old offset 0 put the marker
@@ on the opcode / register bits, and the streamer then aborted on
@@ `assert(Bit == 0 && "Encoder wrote into fixed up bit!")` whenever those bits
@@ were nonzero -- i.e. for every `ld.o rbN, [rbN, %pcrel_lo(...)]` with
@@ rbN >= 4 (`rb4` is what `clang -S` emits for a low-half address).
@@
@@ The expected markers are the imms12 / imms18 fields themselves (contract-elf
@@ §2.2 field widths; contract-isa.md §2.3 field placement), not values taken
@@ from the implementation: imms12 is the low nibble of byte 2 plus byte 3,
@@ imms18 is the low two bits of byte 1 plus bytes 2-3, and whole-word fixups
@@ keep the full-word marker.

@@ RUN: %llvm_mc --triple=dadao-unknown-elf -show-encoding %s > /dev/null 2>&1
@@ RUN: %llvm_mc --triple=dadao-unknown-elf -show-encoding %s 2>&1 | %FileCheck %s

@@ The low half must assemble and display for every base register, including
@@ the ones the old offset-0 mapping used to abort on.  `rb1` (the case that
@@ happened to work) stays green.

@@ CHECK:      ld.o rb1, [rb1, %pcrel_lo(.Lhi0)]{{.*}}@@ encoding: [0x22,0x04,0b0001AAAA,A]
@@ CHECK-NEXT: @@   fixup A - offset: 0, value: %pcrel_lo(.Lhi0), kind: DADAO_FK_PCREL_LO
@@ CHECK:      ld.o rb4, [rb4, %pcrel_lo(.Lhi0)]{{.*}}@@ encoding: [0x22,0x10,0b0100AAAA,A]
@@ CHECK-NEXT: @@   fixup A - offset: 0, value: %pcrel_lo(.Lhi0), kind: DADAO_FK_PCREL_LO
@@ CHECK:      ld.o rb8, [rb8, %pcrel_lo(.Lhi0)]{{.*}}@@ encoding: [0x22,0x20,0b1000AAAA,A]
@@ CHECK-NEXT: @@   fixup A - offset: 0, value: %pcrel_lo(.Lhi0), kind: DADAO_FK_PCREL_LO
@@ CHECK:      ld.o rb16, [rb16, %pcrel_lo(.Lhi0)]{{.*}}@@ encoding: [0x22,0x41,0b0000AAAA,A]
@@ CHECK-NEXT: @@   fixup A - offset: 0, value: %pcrel_lo(.Lhi0), kind: DADAO_FK_PCREL_LO
@@ CHECK:      ld.o rb32, [rb32, %pcrel_lo(.Lhi0)]{{.*}}@@ encoding: [0x22,0x82,0b0000AAAA,A]
@@ CHECK-NEXT: @@   fixup A - offset: 0, value: %pcrel_lo(.Lhi0), kind: DADAO_FK_PCREL_LO
@@ CHECK:      ld.o rb63, [rb63, %pcrel_lo(.Lhi0)]{{.*}}@@ encoding: [0x22,0xff,0b1111AAAA,A]
@@ CHECK-NEXT: @@   fixup A - offset: 0, value: %pcrel_lo(.Lhi0), kind: DADAO_FK_PCREL_LO

@@ The 18-bit high half moves from the opcode bytes (old offset 0) to the
@@ imms18 field: low two bits of byte 1 + bytes 2-3.
@@ CHECK:      aip.si rb4, %pcrel_hi(extg){{.*}}@@ encoding: [0x5a,0b000100AA,A,A]
@@ CHECK-NEXT: @@   fixup A - offset: 0, value: %pcrel_hi(extg), kind: DADAO_FK_PCREL_HI

@@ Whole-word fixups keep offset 0 and mark all four bytes.
@@ CHECK:      br.n {rd0}?, [rb0, extg]{{.*}}@@ encoding: [0x68'A',A,A,A]
@@ CHECK-NEXT: @@   fixup A - offset: 0, value: extg, kind: DADAO_FK_PCRel_18
@@ CHECK:      jump [rb2, rb3, extg]{{.*}}@@ encoding: [0x71'A',0x08'A',0x30'A',A]
@@ CHECK-NEXT: @@   fixup A - offset: 0, value: extg, kind: DADAO_FK_PCRel_12
@@ CHECK:      call [rb0, extg]{{.*}}@@ encoding: [0x74'A',A,A,A]
@@ CHECK-NEXT: @@   fixup A - offset: 0, value: extg, kind: DADAO_FK_PCRel_24
@@ CHECK:      ld.o rd1, [rb0, extg]{{.*}}@@ encoding: [0x20'A',0x04'A',A,A]
@@ CHECK-NEXT: @@   fixup A - offset: 0, value: extg, kind: DADAO_FK_REL12

	.text
.Lhi0:
	ld.o	rb1, [rb1, %pcrel_lo(.Lhi0)]
	ld.o	rb4, [rb4, %pcrel_lo(.Lhi0)]
	ld.o	rb8, [rb8, %pcrel_lo(.Lhi0)]
	ld.o	rb16, [rb16, %pcrel_lo(.Lhi0)]
	ld.o	rb32, [rb32, %pcrel_lo(.Lhi0)]
	ld.o	rb63, [rb63, %pcrel_lo(.Lhi0)]
	aip.si	rb4, %pcrel_hi(extg)
	br.n	{rd0}?, [rb0, extg]
	jump	rb2, rb3, extg
	call	[rb0, extg]
	ld.o	rd1, [rb0, extg]
