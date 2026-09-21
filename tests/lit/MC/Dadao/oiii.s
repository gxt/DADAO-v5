# RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
# RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
# RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM

# oiii format: minor-opcode + immediate instructions (illi, fence)
# Encoding: word = (op<<24)|(ha<<18)|(imm18 & 0x3FFFF)

# illi 0
# op=0x00, ha=0x00(illi), imm18=0
# word = (0x00<<24)|(0x00<<18)|0 = 0x00000000
# OBJ: {{[0-9a-f]+:}} 00 00 00 00{{.*}}illi{{.*}}0
# ASM: illi 0
illi 0
