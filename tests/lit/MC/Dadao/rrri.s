# RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
# RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
# RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM

# rrri format: multiple load/store instructions
# Encoding: word = (op<<24)|(ha<<18)|(hb<<12)|(hc<<6)|hd

# ldm.ub rd8, rb0, rd1, 2
# op=0x28, ha=8, hb=0, hc=1, hd=2
# word = (0x28<<24)|(8<<18)|(1<<6)|2 = 0x28200042
# OBJ: {{[0-9a-f]+:}} 28 20 00 42{{.*}}ldm.ub{{.*}}rd8, rb0, rd1, 2
# ASM: ldm.ub rd8, rb0, rd1, 2
ldm.ub rd8, rb0, rd1, 2
