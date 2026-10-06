; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
; RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=DEF
; RUN: %llvm_mc --triple=dadao-unknown-elf -multiple-to-single -filetype=obj %s -o %t.opt
; RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t.opt | %FileCheck %s --check-prefix=OPT

; `-multiple-to-single` for the rrri multi-register loads/stores
; (spec/DADAO-11 §汇编器选项; contract-asm.md §8).  With the option each
; `{start:end}` group is expanded into single-register instructions that keep
; the same mnemonic; the offset register is advanced by the element width
; (o=8, b=1) with add.si and restored at the end.  Without the option the
; multi-register instruction is emitted unchanged (default).

; Default: the multi-register encodings are untouched.
; DEF: ldm.o {rd8:rd10}, [rb2, rd1]
; DEF: stm.b {rd8:rd9}, [rb3, rd2]

; With -multiple-to-single: expanded, mnemonic unchanged.
; OPT: ldm.o {rd8}, [rb2, rd1]
; OPT-NEXT: add.si rd1, 8
; OPT-NEXT: ldm.o {rd9}, [rb2, rd1]
; OPT-NEXT: add.si rd1, 8
; OPT-NEXT: ldm.o {rd10}, [rb2, rd1]
; OPT-NEXT: add.si rd1, -16
; OPT: stm.b {rd8}, [rb3, rd2]
; OPT-NEXT: add.si rd2, 1
; OPT-NEXT: stm.b {rd9}, [rb3, rd2]
; OPT-NEXT: add.si rd2, -1

	.text
	ldm.o {rd8:rd10}, [rb2, rd1]
	stm.b {rd8:rd9}, [rb3, rd2]
