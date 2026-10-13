; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
; RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM

; oiii format: opx + immediate instructions (fence, swym)
; Encoding: word = (op<<24)|(ha<<18)|(imm18 & 0x3FFFF)

; fence 0
; op=0x77, ha=0x00(fence), imm18=0
; word = (0x77<<24)|(0x00<<18)|0 = 0x77000000
; OBJ: {{[0-9a-f]+:}} 77 00 00 00{{.*}}fence{{.*}}0
; ASM: fence 0
fence 0

; swym 0
; op=0x77, ha=0x22(swym), imm18=0
; word = (0x77<<24)|(0x22<<18)|0 = 0x77880000
; OBJ: {{[0-9a-f]+:}} 77 88 00 00{{.*}}swym{{.*}}0
; ASM: swym 0
swym 0

; swym 42
; op=0x77, ha=0x22(swym), imm18=42=0x2A
; word = (0x77<<24)|(0x22<<18)|0x2A = 0x7788002A
; OBJ: {{[0-9a-f]+:}} 77 88 00 2a{{.*}}swym{{.*}}42
; ASM: swym 42
swym 42
