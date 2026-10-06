; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t.o
; RUN: %llvm_readobj -h %t.o | %FileCheck %s --check-prefix=HDR
; RUN: %llvm_readobj --sections %t.o | %FileCheck %s --check-prefix=SEC
; RUN: %llvm_readobj -r %t.o | %FileCheck %s --check-prefix=REL

; M4 relocations (contract-elf.md §2, ADR-0019 §D1/§D2/§D5):
; references to another section produce SHT_RELA (not SHT_REL) records.
; Type numbering: ABS48=0, REL26=1, REL20=2, REL14=3.
;   ABS48 -> set.zw / or.w / andn.w (rwii address construction)
;   REL26 -> call / jump (iiii, imms24)
;   REL20 -> br.n/br.nn/br.z/br.nz/br.p/br.np (riii, imms18)
;   REL14 -> br.eq / br.ne (rrii, imms12)

; HDR: Machine: 0xDA0
; HDR: Flags [ (0x1)

; SEC: Name: .rela.text
; SEC: Type: SHT_RELA (0x4)
; SEC-NOT: Type: SHT_REL (0x9)

; REL: R_DADAO_ABS48 ext 0x0
; REL: R_DADAO_ABS48 ext 0x0
; REL: R_DADAO_ABS48 ext 0x0
; REL: R_DADAO_REL26 ext 0x0
; REL: R_DADAO_REL20 other 0x0
; REL: R_DADAO_REL14 other 0x0

	.text
	.globl	_start
_start:
	set.zw	rd8, wp0, ext
	or.w	rd8, wp1, ext
	or.w	rd8, wp2, ext
	call	[rb0, ext]
	br.nz	{rd8}?, [rb0, other]
	br.eq	{rd8, rd9}?, [rb0, other]

	.section	.data
	.globl	ext
ext:
	.quad	0
	.globl	other
other:
	.quad	0
