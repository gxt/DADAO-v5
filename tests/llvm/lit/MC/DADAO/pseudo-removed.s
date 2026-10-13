; RUN: echo 'nop' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s
; RUN: echo 'return' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s
; RUN: echo 'not.o rd1, rd2' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s
; RUN: echo 'neg.o rd1, rd2' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s
; RUN: echo 'not.b rd1, rd2' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s
; RUN: echo 'neg.b rd1, rd2' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s
; RUN: echo 'ret rd0' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=RET
; RUN: echo 'ret' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=RET

; Deleted pseudo-instructions (ADR-0013 D11): nop, return, not.* and neg.*
; are no longer provided and MUST be rejected as unknown mnemonics (write
; `swym 0`, `ret rd0, 0`, `xnor.o`, `sub.sX` instead).  `ret` keeps its
; explicit two-operand form: there is no no-operand variant.
;
; CHECK: error: unrecognized instruction mnemonic
; RET: error: invalid operand for instruction
