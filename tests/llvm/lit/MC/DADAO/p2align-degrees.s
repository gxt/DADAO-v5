; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t.o
; RUN: %llvm_objdump -h %t.o | %FileCheck %s --check-prefix=SIZE
; RUN: %llvm_objdump -s --section=.text %t.o | %FileCheck %s --check-prefix=BYTES

; ISS-182 regression, all four `.p2align` degrees inside `.text`, each preceded
; by a one-byte `.dd.b08` so every padding count is non-multiple-of-4.
;
; Offset trace (all offsets are byte offsets in `.text`):
;   .dd.b08 1                       -> 01 at 0
;   .p2align 1  (align 2)  1..2   -> 00 at 1
;   .dd.b08 2                       -> 02 at 2
;   .p2align 2  (align 4)  3..4   -> 00 at 3
;   .dd.b08 3                       -> 03 at 4
;   .p2align 3  (align 8)  5..8   -> 00 00 00 at 5..7
;   .dd.b08 4                       -> 04 at 8
;   .p2align 4  (align 16) 9..16  -> 00 00 00 + swym 0 (0x77880000) at 9..15
;   .dd.b08 5                       -> 05 at 16
; Section size = 17 = 0x11; the `.dd.b08 5` lands exactly on the 16-byte boundary.
;
; @category directive

	.text
	.dd.b08	1
	.p2align 1
	.dd.b08	2
	.p2align 2
	.dd.b08	3
	.p2align 3
	.dd.b08	4
	.p2align 4
	.dd.b08	5

; SIZE: .text 00000011
; BYTES: 01000200 03000000 04000000 77880000
; BYTES: 05
