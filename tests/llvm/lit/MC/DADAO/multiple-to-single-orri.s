; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
; RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=DEF
; RUN: %llvm_mc --triple=dadao-unknown-elf -multiple-to-single -filetype=obj %s -o %t.opt
; RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t.opt | %FileCheck %s --check-prefix=OPT

; `-multiple-to-single` for the orri block moves / FP format conversions
; (contract-asm.md §4.2; spec/DADAO-11 §汇编器选项).  Each `{start:end}` group
; is split into single-register instructions of the same mnemonic.  Without the
; option the instructions are emitted unchanged (default).

; Default: block move / conversion kept as one multi-register instruction.
; DEF: ra2rd {rd8:rd10}, {ra1:ra3}
; DEF: ft2fo {rf4:rf6}, {rf8:rf10}

; With -multiple-to-single: one instruction per element (count = 1).
; OPT: ra2rd {rd8}, {ra1}
; OPT-NEXT: ra2rd {rd9}, {ra2}
; OPT-NEXT: ra2rd {rd10}, {ra3}
; OPT: ft2fo {rf4}, {rf8}
; OPT-NEXT: ft2fo {rf5}, {rf9}
; OPT-NEXT: ft2fo {rf6}, {rf10}

	.text
	ra2rd {rd8:rd10}, {ra1:ra3}
	ft2fo {rf4:rf6}, {rf8:rf10}
