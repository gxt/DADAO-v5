; RUN: %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o /dev/null 2>&1 | %FileCheck %s

; LLVM-045t / ISS-128: the wyde position must be an explicit wpN token.
; Bare numeric 0-3 is rejected (Error level) for every rwii mnemonic.
set.zw rb1, 1, 0xffff

; CHECK: error: invalid operand for instruction
; CHECK: set.zw rb1, 1, 0xffff

set.ow rd2, 0, 1

; CHECK: error: invalid operand for instruction
; CHECK: set.ow rd2, 0, 1

or.w rd3, 3, 0x1

; CHECK: error: invalid operand for instruction
; CHECK: or.w rd3, 3, 0x1

andn.w rb4, 2, 0x1

; CHECK: error: invalid operand for instruction
; CHECK: andn.w rb4, 2, 0x1
