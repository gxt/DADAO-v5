# RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
# RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
# RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM

# orrr format: MISC-octa register operations
# Encoding: word = (op<<24)|(ha<<18)|(hb<<12)|(hc<<6)|hd
# ha = minor-opcode

# or.o rd8, rd9, rd10
# op=0x40, ha=0x09(or.o), hb=rd8=8, hc=rd9=9, hd=rd10=10
# word = (0x40<<24)|(0x09<<18)|(8<<12)|(9<<6)|10 = 0x4024824A
# OBJ: {{[0-9a-f]+:}} 40 24 82 4a{{.*}}or.o{{.*}}rd8, rd9, rd10
# ASM: or.o rd8, rd9, rd10
or.o rd8, rd9, rd10
