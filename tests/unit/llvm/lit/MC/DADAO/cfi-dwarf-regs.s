@@ DADAO DWARF register numbering + CFI (m14-llvm-004).
@@
@@ Before this task DADAO had no DwarfRegNum table, so
@@ MCRegisterInfo::getDwarfRegNum() answered -1 for every register and the
@@ generic CIE emitter aborted on the first .cfi_startproc:
@@   MCDwarf.cpp: Assertion `RAReg <= 255 && "DWARF 2 encodes
@@   return_address_register in one byte"' failed.
@@ A table alone is not enough: the .eh_frame CIE is always version 1, whose
@@ return_address_register is a single byte, so the CFI numbers must fit 0..255
@@ AND the return-address register must be a real one.  DADAO keeps the return
@@ address on the RegRAS hardware stack (top slot ra63), so the CIE must name
@@ ra63 = 255 -- not rbsp (the stack pointer, 65).
@@
@@ The four banks tile 0..255 exactly once (each bank owns 64 numbers because
@@ they are disjoint register files): rd#i -> i, rb#i -> 64+i, rf#i -> 128+i,
@@ ra#i -> 192+i.  The ABI alias rbsp shares rb1's 65 (DwarfRegAlias, no extra
@@ slot).  MCDwarf.cpp's CIE uses getDwarfRegNum(RA, /*isEH=*/true) and the
@@ .cfi_* directives go through the EH flavour too, so the single-number
@@ DwarfRegNum form (which feeds both flavours) is what makes this work.
@@
@@ dwarfdump resolves a CFI register operand back to a name through that same
@@ table, so the FDE below prints `rb1`/`rb2`/`rf8`/`ra63` instead of the raw
@@ numbers: the name round-trip is the readable form of the mapping.  The one
@@ operand dwarfdump always prints numerically is the CIE return-address column
@@ (255 = ra63).
@@
@@ .eh_frame FDE addresses use DW_EH_PE_absptr here: DADAO has no 32-bit
@@ PC-relative data relocation (instruction-field REL26/20/14 only), so the
@@ default pcrel|sdata4 field could not be relocated.  Hence the 8-byte
@@ R_DADAO_ABS48 relocation in .rela.eh_frame below.
@@
@@ llvm-dwarfdump cannot always apply R_DADAO_ABS48 on a .o (see the note in
@@ dwarf64-default.s), so its output is captured with `|| true` and every
@@ assertion runs on the captured text.

@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t.o
@@ RUN: %llvm_readobj --sections %t.o | %FileCheck %s --check-prefix=SEC
@@ RUN: %llvm_objdump -r %t.o | %FileCheck %s --check-prefix=REL
@@ RUN: %llvm_dwarfdump --debug-frame -v %t.o > %t.dump 2>&1 || true
@@ RUN: %FileCheck %s --check-prefix=CIE < %t.dump
@@ RUN: %FileCheck %s --check-prefix=FDE < %t.dump
@@ RUN: %FileCheck %s --check-prefix=CFA < %t.dump

@@ The same source through the driver / cc1as path must not abort either.
@@ RUN: %clang --target=dadao-unknown-elf -c %s -o %t.cc1as.o
@@ RUN: %llvm_dwarfdump --debug-frame %t.cc1as.o > %t.cc1as.dump 2>&1 || true
@@ RUN: %FileCheck %s --check-prefix=CIE < %t.cc1as.dump

@@ An unknown register name stays a parse error (rc != 0), never an abort.
@@ RUN: echo -e '.text\n.cfi_startproc\n.cfi_offset nosuchreg, -8\n.cfi_endproc' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=BADREG

@@ .debug_frame (DWARF64 via -g) must agree with .eh_frame on the RA column.
@@ RUN: echo -e '.text\ndbg:\n.cfi_sections .debug_frame\n.cfi_startproc\n.cfi_def_cfa_offset 16\nswym\t0\n.cfi_endproc' | %llvm_mc --triple=dadao-unknown-elf -g -filetype=obj -o %t.dbg.o
@@ RUN: %llvm_dwarfdump --debug-frame -v %t.dbg.o > %t.dbg.dump 2>&1 || true
@@ RUN: %FileCheck %s --check-prefix=CIE-DBG < %t.dbg.dump

@@ .eh_frame exists on the default (non -g) path.
@@ SEC: Name: .eh_frame

@@ The FDE address field is a relocated 8-byte absolute pointer (offset and
@@ symbol vary with CIE size, so only the type is pinned).
@@ REL: RELOCATION RECORDS FOR [.eh_frame]
@@ REL-NEXT: OFFSET
@@ REL-NEXT: {{[0-9a-f]+}} R_DADAO_ABS48

@@ The EH CIE is version 1; its one-byte return-address column names ra63 (255).
@@ CIE: Version: 1
@@ CIE: Return address column: 255

@@ ... and the FDE really covers the function.
@@ FDE: FDE cie=
@@ FDE: pc=

@@ CFI directive operands come back as the expected DWARF numbers: 65 (rb1),
@@ 66 (rb2), 136 (rf8) and 255 (ra63).  dwarfdump prints the register *name*
@@ when it can resolve the number through this target's table, otherwise the
@@ bare `reg<N>`; both spellings are accepted so the check pins the number.
@@ CFA: DW_CFA_def_cfa: {{(rb1|reg65)}} +8
@@ CFA: DW_CFA_def_cfa_offset: +16
@@ CFA: DW_CFA_def_cfa_register: {{(rb2|reg66)}}
@@ CFA: DW_CFA_offset_extended: {{(rb2|reg66)}} -8
@@ CFA: DW_CFA_offset_extended: {{(rf8|reg136)}} -8
@@ CFA: DW_CFA_offset_extended: {{(ra63|reg255)}} -8

@@ The .debug_frame CIE carries the same RA column as the EH one (DWARF64 => version 4).
@@ CIE-DBG: Version: 4
@@ CIE-DBG: Return address column: 255

@@ BADREG: error:
@@ BADREG-NEXT: .cfi_offset nosuchreg, -8

	.text
	.globl	cfi_probe
	.type	cfi_probe,%function
cfi_probe:
	.cfi_startproc
	.cfi_def_cfa rb1, 8
	.cfi_def_cfa_offset 16
	.cfi_def_cfa_register rb2
	.cfi_offset rb2, -8
	.cfi_offset rf8, -8
	.cfi_offset ra63, -8
	swym	0
	.cfi_endproc
	.size	cfi_probe, .-cfi_probe
	ret	rd0, 0
