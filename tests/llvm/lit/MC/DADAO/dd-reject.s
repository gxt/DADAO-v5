; RUN: echo '.octa 0x1' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=OCTA
; RUN: echo '.word 0x1234' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=WORD
; RUN: echo '.dd.b08 0x1234' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=RANGE
; RUN: echo '.dd.t32 ext' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=NARROW

; Rejection consistency (contract-asm.md §7/§9):
;  - GAS `.octa` is a 16-byte octa; DADAO's octa is 8 bytes, so GAS semantics
;    MUST NOT be used -> explicitly rejected (use .dd.o64).
;  - `.word` is not a DADAO directive -> unknown directive (unchanged).
;  - a value that overflows the directive width is an error (no silent wrap).
;  - a relocatable operand of .dd.b08/.dd.w16/.dd.t32 is rejected: a DADAO
;    address needs the 8-byte .dd.o64 field.
;
; OCTA: unsupported directive '.octa'
; WORD: unknown directive
; RANGE: out of range
; NARROW: relocatable operand in
