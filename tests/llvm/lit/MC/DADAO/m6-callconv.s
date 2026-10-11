; M6 L1 MC vector (TESTCASES-036t): calling-convention symbol/reloc encodings.
;
; The complete integer calling convention (LLVM-062t) does not add new
; instruction encodings; its L1 surface is the *relocation* system the ABI
; relies on: a direct call / tail jump to a function is an R_DADAO_REL26
; (contract-elf.md §2.2), a function-pointer / absolute address is built with
; set.zw + or.w (R_DADAO_ABS48, §3.1), and the conditional branches are the
; R_DADAO_REL20 (riii) / R_DADAO_REL14 (rrii) forms.
;
; Every expectation below is annotated inline and re-derived from
; contracts/opcodes.yaml (encoding) and contract-elf.md §2.2 (reloc type) by
; tools/testcases/validate_m6_vectors.py -- an independent oracle that never
; invokes llvm-mc / llvm-readobj.
;
;   ; @enc <8hex>        the 4-byte big-endian instruction word (immediate = 0
;                        because the value is supplied by the relocation)
;   ; @reloc <NAME>      the R_DADAO_* relocation the assembler must emit
;
; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t.o
; RUN: %llvm_readobj -r --expand-relocs %t.o | %FileCheck %s --check-prefix=REL
; RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t.o | %FileCheck %s --check-prefix=OBJ

; The target lives in another section so the assembler must emit a relocation
; (an in-section label would be resolved in place).
; REL: Offset: 0x0
; REL: Type: R_DADAO_REL26 (1)
; REL: Symbol: target
; REL: Offset: 0x4
; REL: Type: R_DADAO_REL26 (1)
; REL: Offset: 0x8
; REL: Type: R_DADAO_REL20 (2)
; REL: Offset: 0xC
; REL: Type: R_DADAO_REL14 (3)
; REL: Offset: 0x10
; REL: Type: R_DADAO_ABS48 (0)
; REL: Offset: 0x14
; REL: Type: R_DADAO_ABS48 (0)

; OBJ: {{[0-9a-f]+:}} 74 00 00 00{{.*}}call [rb0,
; OBJ: {{[0-9a-f]+:}} 70 00 00 00{{.*}}jump [rb0,
; OBJ: {{[0-9a-f]+:}} 68 20 00 00{{.*}}br.n {rd8}?, [rb0,
; OBJ: {{[0-9a-f]+:}} 6e 20 90 00{{.*}}br.eq {rd8, rd9}?, [rb0,
; OBJ: {{[0-9a-f]+:}} 4c 20 00 00{{.*}}set.zw rd8, wp0,
; OBJ: {{[0-9a-f]+:}} 48 21 00 00{{.*}}or.w rd8, wp1,

	.text
	.globl	_start
_start:
	call	[rb0, target]                  ; @enc 74000000 @reloc R_DADAO_REL26
	jump	[rb0, target]                  ; @enc 70000000 @reloc R_DADAO_REL26
	br.n	{rd8}?, [rb0, target]          ; @enc 68200000 @reloc R_DADAO_REL20
	br.eq	{rd8, rd9}?, [rb0, target]     ; @enc 6e209000 @reloc R_DADAO_REL14
	set.zw	rd8, wp0, target               ; @enc 4c200000 @reloc R_DADAO_ABS48
	or.w	rd8, wp1, target               ; @enc 48210000 @reloc R_DADAO_ABS48

	.section	.data
	.globl	target
target:
	.dd.o64	0
