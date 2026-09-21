# RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
# RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
# RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM

# rrii format: load instructions
# Encoding: word = (op<<24)|(ha<<18)|(hb<<12)|(hc<<6)|hd
# hc = imm12>>6, hd = imm12&0x3F

# ld.ub rd8, rb0, 1
# op=0x10, ha=8, hb=0, imm12=1 → hc=0, hd=1
# word = (0x10<<24)|(8<<18) | 1 = 0x10200001
# OBJ: {{[0-9a-f]+:}} 10 20 00 01{{.*}}ld.ub{{.*}}rd8, rb0, 1
# ASM: ld.ub rd8, rb0, 1
ld.ub rd8, rb0, 1

# ld.sb rd1, rb2, -1
# op=0x13, ha=1, hb=2, imms12=-1 (0xFFF) → hc=0x3F, hd=0x3F
# word = (0x13<<24)|(1<<18)|(2<<12)|(0x3F<<6)|0x3F = 0x13042FFF
# OBJ: {{[0-9a-f]+:}} 13 04 2f ff{{.*}}ld.sb{{.*}}rd1, rb2, -1
# ASM: ld.sb rd1, rb2, -1
ld.sb rd1, rb2, -1
