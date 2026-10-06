; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
; RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM

; iiii format: jump/call instructions (byte offsets, must be %4==0)
; Encoding: word = (op<<24)|((bytes>>2) & 0xFFFFFF)

; jump [rb0, 4]
; op=0x70, bytes=4, field=4>>2=1
; word = (0x70<<24)|1 = 0x70000001
; OBJ: {{[0-9a-f]+:}} 70 00 00 01{{.*}}jump{{.*}}[rb0, 4]
; ASM: jump [rb0, 4]
jump [rb0, 4]

; call [rb0, 4]
; op=0x74, bytes=4, field=4>>2=1
; word = (0x74<<24)|1 = 0x74000001
; OBJ: {{[0-9a-f]+:}} 74 00 00 01{{.*}}call{{.*}}[rb0, 4]
; ASM: call [rb0, 4]
call [rb0, 4]