; RUN: echo '.octa 0x1' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=OCTA
; RUN: echo '.word 0x1234' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=WORD
; RUN: echo '.byte 1' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=GAS
; RUN: echo '.short 1' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=GAS
; RUN: echo '.long 1' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=GAS
; RUN: echo '.quad 1' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=GAS
; RUN: echo '.align 3' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ALIGN
; RUN: echo '.dd.b08 0x1234' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=RANGE
; RUN: echo '.dd.t32 ext' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=NARROW
; The accepted spellings must assemble cleanly (rc=0).
; RUN: echo '.dd.b08 1' | %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null
; RUN: echo '.dd.w16 1' | %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null
; RUN: echo '.dd.t32 1' | %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null
; RUN: echo '.dd.o64 1' | %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null
; RUN: echo '.p2align 3' | %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null

; Rejection/acceptance consistency (contract-asm.md §7/§9):
;  - GAS `.octa` is a 16-byte octa; DADAO's octa is 8 bytes, so GAS semantics
;    MUST NOT be used -> explicitly rejected (use .dd.o64).
;  - GAS `.byte`/`.short`/`.long`/`.quad` are explicitly rejected; the ONLY
;    data directives are `.dd.b08`/`.dd.w16`/`.dd.t32`/`.dd.o64` (§7.1).
;  - `.word` is not a DADAO directive -> unknown directive (unchanged).
;  - `.align` uses byte-count semantics, conflicting with GAS's 2^N -> rejected;
;    the only alignment directive is `.p2align N` (§7.2).
;  - a value that overflows the directive width is an error (no silent wrap).
;  - a relocatable operand of .dd.b08/.dd.w16/.dd.t32 is rejected: a DADAO
;    address needs the 8-byte .dd.o64 field.
;
; OCTA: unsupported directive '.octa'
; WORD: unknown directive
; GAS: unsupported directive
; ALIGN: unsupported directive '.align'
; RANGE: out of range
; NARROW: relocatable operand in
