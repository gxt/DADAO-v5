; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t.o
; RUN: %llvm_objdump -h %t.o | %FileCheck %s --check-prefix=SIZE
; RUN: %llvm_objdump -s --section=.text %t.o | %FileCheck %s --check-prefix=BYTES

; ISS-182 regression: `.p2align` inside the executable section `.text` must
; assemble (rc=0) and the padding must be exactly the bytes needed to reach the
; requested alignment (MCAssembler::writeNopData must emit *exactly* Count
; bytes; the pre-fix code rounded Count up to a multiple of 4 and aborted in
; MCAssembler::writeFragment).
;
; `.text` is a code section, so MCAsmInfoELF::useCodeAlign() selects the
; code-alignment path: the padding is filled through the backend writeNopData().
; A preceding `.dd.b08` leaves the offset 4-unaligned, so the padding count is
; NOT a multiple of 4 -- the case that used to crash.
;
; `.dd.b08 1` at offset 0; `.p2align 3` pads to offset 8 (7 bytes, no trailing
; item).  The first 3 padding bytes are zero-fill to reach the next 4-byte
; boundary; the following 4 bytes are one canonical `swym 0` = 0x77880000
; (contract-isa.md §13.1/§13.3).
;
; @category directive

	.text
	.dd.b08	1
	.p2align 3

; Exact `llvm-objdump -h` size: 1 data byte + 7 padding = 8 (2^3).
; SIZE: .text 00000008
; Exact `llvm-objdump -s --section=.text` bytes (big-endian word groups).
; BYTES: 01000000 77880000
