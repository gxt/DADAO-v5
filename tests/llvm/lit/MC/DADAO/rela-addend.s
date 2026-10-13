; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t.o
; RUN: %llvm_readobj -r --expand-relocs %t.o | %FileCheck %s

; r_addend carries the source-level addend A explicitly (SHT_RELA).
;   ABS48: value = S + A        (contract-elf.md §3.1, ADR-0019 §D3)
;   REL*:  field = (S + A - P) >> 2  (no -4, contract-elf.md §3.1)
; A = 0x15/0x16 for the two ABS48 slices, 0x4/0x8/0xC for the REL* records.

; CHECK: Type: R_DADAO_ABS48 (0)
; CHECK: Addend: 0x15
; CHECK: Type: R_DADAO_ABS48 (0)
; CHECK: Addend: 0x16
; CHECK: Type: R_DADAO_REL26 (1)
; CHECK: Addend: 0x4
; CHECK: Type: R_DADAO_REL20 (2)
; CHECK: Addend: 0x8
; CHECK: Type: R_DADAO_REL14 (3)
; CHECK: Addend: 0xC

	.text
	.globl	_start
_start:
	set.zw	rd8, wp0, ext+21
	or.w	rd8, wp1, ext+22
	call	[rb0, ext+4]
	br.nz	{rd8}?, [rb0, other+8]
	br.eq	{rd8, rd9}?, [rb0, other+12]

	.section	.data
	.globl	ext
ext:
	.dd.o64	0
	.globl	other
other:
	.dd.o64	0
