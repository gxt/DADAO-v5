# RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
# RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
# RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM

# iiii format: jump/call instructions
# Encoding: word = (op<<24)|(imm24 & 0xFFFFFF)

# jump 1
# op=0x70, imm24=1
# word = (0x70<<24)|1 = 0x70000001
# OBJ: {{[0-9a-f]+:}} 70 00 00 01{{.*}}jump{{.*}}1
# ASM: jump 1
jump 1

# call 1
# op=0x74, imm24=1
# word = (0x74<<24)|1 = 0x74000001
# OBJ: {{[0-9a-f]+:}} 74 00 00 01{{.*}}call{{.*}}1
# ASM: call 1
call 1
