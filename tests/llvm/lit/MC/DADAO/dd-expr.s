; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t.o
; RUN: %llvm_objdump -s --section=.text %t.o | %FileCheck %s

; .dd.* accept full constant expressions and comma-separated value lists
; (contract-asm.md §2.4/§7).  Values are written big-endian at the fixed
; directive width; negative values are sign-extended into the field.
;
;   .dd.t32 1+2*3, 0x10  -> 00 00 00 07 / 00 00 00 10
;   .dd.w16 -1           -> ff ff
;
; CHECK: 00000007 00000010 ffff

	.text
	.dd.t32	1+2*3, 0x10
	.dd.w16	-1
