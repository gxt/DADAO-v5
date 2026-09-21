# RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
# RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
# RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM

# orri format: register bank operations (rb2rd, rd2rd)
# Encoding: word = (op<<24)|(ha<<18)|(hb<<12)|(hc<<6)|hd
# ha = minor-opcode

# rb2rd rd8, rb9, 2
# op=0x40, ha=0x36(rb2rd), hb=rd8=8, hc=rb9=9, hd=immu6=2
# word = (0x40<<24)|(0x36<<18)|(8<<12)|(9<<6)|2 = 0x40D88242
# OBJ: {{[0-9a-f]+:}} 40 d8 82 42{{.*}}rb2rd{{.*}}rd8, rb9, 2
# ASM: rb2rd rd8, rb9, 2
rb2rd rd8, rb9, 2

# rd2rd rd8, rd1, 1
# op=0x40, ha=0x2C(rd2rd), hb=rd8=8, hc=rd1=1, hd=immu6=1
# word = (0x40<<24)|(0x2C<<18)|(8<<12)|(1<<6)|1 = 0x40B08041
# OBJ: {{[0-9a-f]+:}} 40 b0 80 41{{.*}}rd2rd{{.*}}rd8, rd1, 1
# ASM: rd2rd rd8, rd1, 1
rd2rd rd8, rd1, 1
