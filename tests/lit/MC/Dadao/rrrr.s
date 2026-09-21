# RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
# RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
# RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM

# rrrr format: four-register arithmetic
# Encoding: word = (op<<24)|(ha<<18)|(hb<<12)|(hc<<6)|hd

# add.uo rd8, rd9, rd10, rd11
# op=0x50, ha=8, hb=9, hc=10, hd=11
# word = (0x50<<24)|(8<<18)|(9<<12)|(10<<6)|11 = 0x5020928B
# OBJ: {{[0-9a-f]+:}} 50 20 92 8b{{.*}}add.uo{{.*}}rd8, rd9, rd10, rd11
# ASM: add.uo rd8, rd9, rd10, rd11
add.uo rd8, rd9, rd10, rd11

# add.so rd8, rd9, rd10, rd11
# op=0x51, ha=8, hb=9, hc=10, hd=11
# word = (0x51<<24)|(8<<18)|(9<<12)|(10<<6)|11 = 0x5120928B
# OBJ: {{[0-9a-f]+:}} 51 20 92 8b{{.*}}add.so{{.*}}rd8, rd9, rd10, rd11
# ASM: add.so rd8, rd9, rd10, rd11
add.so rd8, rd9, rd10, rd11
