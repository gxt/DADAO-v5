; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t.o
; RUN: %llvm_objdump -s --section=.text %t.o | %FileCheck %s --check-prefix=BYTES
; RUN: %llvm_objdump -s --section=.text %t.o | %FileCheck %s --check-prefix=BE

; DADAO data directives .dd.b08/.dd.w16/.dd.t32/.dd.o64 (DADAO-11 §汇编兼容性
; §指导符; contract-asm.md §7).  Widths are 1/2/4/8 bytes and values are emitted
; big-endian (contract-elf.md §1.1).  DADAO's octa is 8 bytes, NOT GAS's 16.
;
; Expected .text content, 15 bytes big-endian:
;   .dd.b08 0x12               -> 12
;   .dd.w16 0x1234             -> 12 34
;   .dd.t32 0x11223344         -> 11 22 33 44
;   .dd.o64 0x1122334455667788 -> 11 22 33 44 55 66 77 88
;
; BYTES: 12123411 22334411 22334455 667788
; A little-endian emitter would produce 34 12 or 88 77 ... instead.
; BE-NOT: 34121122

	.text
	.dd.b08	0x12
	.dd.w16	0x1234
	.dd.t32	0x11223344
	.dd.o64	0x1122334455667788
