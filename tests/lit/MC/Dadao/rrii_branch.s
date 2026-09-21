# RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
# RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
# RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM

# rrii format: register-pair branch instructions
# Encoding: word = (op<<24)|(ha<<18)|(hb<<12)|(imm12 & 0xFFF)

# br.eq rd8, rd0, 4
# op=0x6E, ha=rd8=8, hb=rd0=0, imms12=4 → hc=0, hd=4
# word = (0x6E<<24)|(8<<18)|4 = 0x6E200004
# OBJ: {{[0-9a-f]+:}} 6e 20 00 04{{.*}}br.eq{{.*}}rd8, rd0, 4
# ASM: br.eq rd8, rd0, 4
br.eq rd8, rd0, 4
