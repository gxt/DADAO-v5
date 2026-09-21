# RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
# RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
# RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM

# rrii format: store instructions
# Encoding: word = (op<<24)|(ha<<18)|(hb<<12)|(imm12 & 0xFFF)

# st.b rd0, rb1, 1
# op=0x18, ha=0, hb=1, imm12=1 → hc=0, hd=1
# word = (0x18<<24)|(1<<12)|1 = 0x18001001
# OBJ: {{[0-9a-f]+:}} 18 00 10 01{{.*}}st.b{{.*}}rd0, rb1, 1
# ASM: st.b rd0, rb1, 1
st.b rd0, rb1, 1
