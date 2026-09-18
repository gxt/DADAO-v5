# RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o %t.o < %s
# RUN: readelf -x .text %t.o | %FileCheck %s

# Test basic DADAO instruction encoding and fixup behavior.

# Test 1: add.si rd8, 1 (riii format, op=0x59, ra=8, imm18=1)
# Encoding: 0x59<<24 | 8<<18 | 1 = 0x59200001
add.si rd8, 1

# Test 2: add.si rb1, 1 (riii format, op=0x5B, ra=1, imm18=1)
# Encoding: 0x5B<<24 | 1<<18 | 1 = 0x5B040001
add.si rb1, 1

# Test 3: Forward branch at non-zero offset
# swym 0 at offset 8: 0x77000000
# br.n rd0, L1 at offset 12: L1 is at offset 16
#   imms = (16 - 12) >> 2 = 1
#   Encoding: 0x68<<24 | 0<<18 | 1 = 0x68000001
# L1: swym 0 at offset 16: 0x77000000
swym 0
br.n rd0, L1
L1: swym 0

# Test 4: Backward branch
# L2: swym 0 at offset 20: 0x77000000
# br.n rd0, L2 at offset 24: L2 is at offset 20
#   imms = (20 - 24) >> 2 = -1 = 0x3FFFF (18-bit signed)
#   Encoding: 0x68<<24 | 0<<18 | 0x3FFFF = 0x6803FFFF
L2: swym 0
br.n rd0, L2

# CHECK: Hex dump of section '.text':
# CHECK: 0x00000000 59200001 5b040001 77000000 68000001
# CHECK: 0x00000010 77000000 77000000 6803ffff
