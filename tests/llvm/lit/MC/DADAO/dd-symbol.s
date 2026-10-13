; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t.o
; RUN: %llvm_readobj --sections %t.o | %FileCheck %s --check-prefix=SEC
; RUN: %llvm_readobj -r --expand-relocs %t.o | %FileCheck %s --check-prefix=REL
; RUN: %llvm_readobj -r --expand-relocs %t.o | %FileCheck %s --check-prefix=ADD

; A relocatable 8-byte data item (.dd.o64 <sym>) is an absolute address, so it
; carries R_DADAO_ABS48 (an absolute relocation, not instruction-specific;
; ADR-0019 §D2).  The addend carries the source-level +A (SHT_RELA).
;
; SEC: Name: .rela.text
; SEC: Type: SHT_RELA (0x4)
; SEC-NOT: Type: SHT_REL (0x9)
;
; REL: Offset: 0x0
; REL: Type: R_DADAO_ABS48 (0)
; REL: Symbol: ext
; REL: Offset: 0x8
;
; ADD: Addend: 0x8

	.text
	.dd.o64	ext
	.dd.o64	ext+8
