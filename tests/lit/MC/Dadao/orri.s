# RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
# RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
# RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM

# orri format: MISC-octa register+immediate operations
# Encoding: word = (op<<24)|(ha<<18)|(hb<<12)|(hc<<6)|hd
# ha = minor-opcode

# ext.uo rd8, rd0, 1
# op=0x40, ha=0x18(ext.uo), hb=rd8=8, hc=rd0=0, hd=immu6=1
# word = (0x40<<24)|(0x18<<18)|(8<<12)|1 = 0x40608001
# OBJ: {{[0-9a-f]+:}} 40 60 80 01{{.*}}ext.uo{{.*}}rd8, rd0, 1
# ASM: ext.uo rd8, rd0, 1
ext.uo rd8, rd0, 1
