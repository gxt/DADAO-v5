# RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
# RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
# RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM

# Test basic DADAO instruction encoding and fixup behavior.
# Encoding formula: word = (op<<24)|(ha<<18)|(hb<<12)|(hc<<6)|hd

# add.si rd8, 1 (riii format, op=0x59, ra=8, imm18=1)
# word = 0x59<<24 | 8<<18 | 1 = 0x59200001
# OBJ: {{[0-9a-f]+:}} 59 20 00 01{{.*}}add.si{{.*}}rd8, 1
# ASM: add.si rd8, 1
add.si rd8, 1

# add.si rb1, 1 (riii format, op=0x5B, ra=1, imm18=1)
# word = 0x5B<<24 | 1<<18 | 1 = 0x5B040001
# OBJ: {{[0-9a-f]+:}} 5b 04 00 01{{.*}}add.si{{.*}}rb1, 1
# ASM: add.si rb1, 1
add.si rb1, 1

# add.si rd8, -1 (riii format, op=0x59, ra=8, imms18=-1)
# imms18 = -1 → 0x3FFFF (18-bit two's complement)
# hb = 0x3FFFF>>12 = 0x3F, hc = (0x3FFFF>>6)&0x3F = 0x3F, hd = 0x3F
# word = 0x59<<24 | 8<<18 | 0x3FFFF = 0x5923FFFF
# OBJ: {{[0-9a-f]+:}} 59 23 ff ff{{.*}}add.si{{.*}}rd8, -1
# ASM: add.si rd8, -1
add.si rd8, -1

# Forward branch at non-zero offset
# swym 0 at offset 0x0C: 0x77000000
# br.n rd0, L1 at offset 0x10: L1 at 0x14
#   imms = (0x14 - 0x10) >> 2 = 1
#   word = 0x68<<24 | 1 = 0x68000001
# L1: swym 0 at offset 0x14: 0x77000000
swym 0
br.n rd0, L1
L1: swym 0

# Backward branch
# L2: swym 0 at offset 0x18: 0x77000000
# br.n rd0, L2 at offset 0x1C: L2 at 0x18
#   imms = (0x18 - 0x1C) >> 2 = -1 = 0x3FFFF (18-bit signed)
#   word = 0x68<<24 | 0x3FFFF = 0x6803FFFF
L2: swym 0
br.n rd0, L2
