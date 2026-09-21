# RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
# RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
# RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM

# riii format: ret instruction
# Encoding: word = (op<<24)|(ha<<18)|(imm18 & 0x3FFFF)

# ret rd0, 0
# op=0x76, ha=0, imms18=0
# word = (0x76<<24)|0 = 0x76000000
# OBJ: {{[0-9a-f]+:}} 76 00 00 00{{.*}}ret{{.*}}rd0, 0
# ASM: ret rd0, 0
ret rd0, 0
