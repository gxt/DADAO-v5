# RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
# RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
# RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM

# rwii format: wyde-position immediate instructions
# Encoding: word = (op<<24)|(ha<<18)|((wp&3)<<16)|(immu16 & 0xFFFF)
# wp in hb[5:4], immu16 high 4 bits in hb[3:0], mid 6 in hc[5:0], low 6 in hd[5:0]

# set.zw rd8, 0, 0x1234
# op=0x4C, ha=8, wp=0, immu16=0x1234
# hb = (0<<4)|0x1 = 0x01, hc = 0x08, hd = 0x34
# word = (0x4C<<24)|(8<<18)|(0x01<<12)|(0x08<<6)|0x34 = 0x4C201234
# OBJ: {{[0-9a-f]+:}} 4c 20 12 34{{.*}}set.zw{{.*}}rd8, 0, 4660
# ASM: set.zw rd8, 0, 4660
set.zw rd8, 0, 0x1234
