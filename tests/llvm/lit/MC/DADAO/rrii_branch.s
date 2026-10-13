; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
; RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM

; rrii format: register-pair branch instructions (byte offsets, must be %4==0)
; Encoding: word = (op<<24)|(ha<<18)|(hb<<12)|(bytes>>2 & 0xFFF)

; br.eq {rd8, rd0}?, [rb0, 16]
; op=0x6E, ha=rd8=8, hb=rd0=0, bytes=16, field=16>>2=4
; word = (0x6E<<24)|(8<<18)|4 = 0x6E200004
; OBJ: {{[0-9a-f]+:}} 6e 20 00 04{{.*}}br.eq{{.*}}{rd8, rd0}?, [rb0, 16]
; ASM: br.eq {rd8, rd0}?, [rb0, 16]
br.eq {rd8, rd0}?, [rb0, 16]