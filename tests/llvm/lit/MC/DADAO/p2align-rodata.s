; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t.o
; RUN: %llvm_objdump -h %t.o | %FileCheck %s --check-prefix=SIZE
; RUN: %llvm_objdump -s --section=.rodata %t.o | %FileCheck %s --check-prefix=BYTES

; ISS-182 non-regression: `.p2align` inside a data section (`.rodata`) must still
; use the *value fill* path (MCAsmInfoELF::useCodeAlign() is false for data),
; i.e. zero fill with no `swym 0`.  The fix only changed the code-alignment
; writeNopData() path, so `.rodata` bytes must be unchanged.
;
;   .byte 1                       -> 01 at 0
;   .p2align 3  (align 8)  1..8   -> 00 x7 at 1..7
;   .byte 2                       -> 02 at 8
; Section size = 9 = 0x9.
;
; @category directive

	.rodata
	.byte	1
	.p2align 3
	.byte	2

; SIZE: .rodata 00000009
; BYTES: 01000000 00000000 02
