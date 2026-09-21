# RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
# RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
# RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM

# rrii format: ALU compare instructions
# Encoding: word = (op<<24)|(ha<<18)|(hb<<12)|(imm12 & 0xFFF)

# cmp.ui rd8, rd0, 1
# op=0x5C, ha=8, hb=0, immu12=1 → hc=0, hd=1
# word = (0x5C<<24)|(8<<18)|1 = 0x5C200001
# OBJ: {{[0-9a-f]+:}} 5c 20 00 01{{.*}}cmp.ui{{.*}}rd8, rd0, 1
# ASM: cmp.ui rd8, rd0, 1
cmp.ui rd8, rd0, 1

# cmp.si rd8, rd0, 1
# op=0x5D, ha=8, hb=0, imms12=1 → hc=0, hd=1
# word = (0x5D<<24)|(8<<18)|1 = 0x5D200001
# OBJ: {{[0-9a-f]+:}} 5d 20 00 01{{.*}}cmp.si{{.*}}rd8, rd0, 1
# ASM: cmp.si rd8, rd0, 1
cmp.si rd8, rd0, 1
