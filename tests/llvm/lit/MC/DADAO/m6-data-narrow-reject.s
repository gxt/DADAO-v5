; RUN: echo '.byte ext'  | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=NARROW
; RUN: echo '.short ext' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=NARROW
; RUN: echo '.long ext'  | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=NARROW

; A relocatable operand in a 1/2/4-byte data field would need a data relocation,
; but a DADAO address is 48-bit and there is no data relocation narrower than the
; 8-byte R_DADAO_ABS48 (ADR-0019 §D8 forbids ABS32).  LLVM-065t / ISS-161: this
; used to be emitted as a *silent* 0 with no relocation; it is now an explicit
; assembler error (no truncation, no wrap, no silent 0; contract-elf.md §3.2).
; Use `.quad`/`.dd.o64` for an 8-byte absolute data address.
;
; NARROW: relocatable operand in a 1/2/4-byte data field
