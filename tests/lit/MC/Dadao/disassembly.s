# RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o %t.o < %s
# RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t.o | %FileCheck %s

# Test DADAO disassembly for all major format classes.
# Encoding formula: word = (op<<24)|(ha<<18)|(hb<<12)|(hc<<6)|hd (contract-isa.md §2.1)
# Register banks: RD rd0=0..rd63=63, RB rb0=0..rb63=63

#--- rrii format ---

# ld.ub rd8, rb0, 1
# op=0x10, ha=rd8=8, hb=rb0=0, imms12=1 → hc=0, hd=1
# word = (0x10<<24)|(8<<18)|(0<<12)|(0<<6)|1 = 0x10200001
# CHECK: 0: 10 20 00 01 {{.*}}ld.ub{{.*}}rd8, rb0, 1
ld.ub rd8, rb0, 1

# ld.sb rd1, rb2, -1
# op=0x13, ha=rd1=1, hb=rb2=2, imms12=-1 (0xFFF)
# hc = 0xFFF>>6 = 0x3F, hd = 0xFFF&0x3F = 0x3F
# word = (0x13<<24)|(1<<18)|(2<<12)|(0x3F<<6)|0x3F = 0x13042FFF
# CHECK: 4: 13 04 2f ff {{.*}}ld.sb{{.*}}rd1, rb2, -1
ld.sb rd1, rb2, -1

#--- rrri format ---

# ldm.ub rd8, rb0, rd1, 2
# op=0x28, ha=rd8=8, hb=rb0=0, hc=rd1=1, hd=immu6=2
# word = (0x28<<24)|(8<<18)|(0<<12)|(1<<6)|2 = 0x28200042
# CHECK: 8: 28 20 00 42 {{.*}}ldm.ub{{.*}}rd8, rb0, rd1, 2
ldm.ub rd8, rb0, rd1, 2

#--- rrrr format ---

# add.uo rd8, rd9, rd10, rd11
# op=0x50, ha=rd8=8, hb=rd9=9, hc=rd10=10, hd=rd11=11
# word = (0x50<<24)|(8<<18)|(9<<12)|(10<<6)|11 = 0x5020928B
# CHECK: c: 50 20 92 8b {{.*}}add.uo{{.*}}rd8, rd9, rd10, rd11
add.uo rd8, rd9, rd10, rd11

#--- riii format ---

# add.si rd8, 1
# op=0x59, ha=rd8=8, imms18=1 → hb=0, hc=0, hd=1
# word = (0x59<<24)|(8<<18)|(0<<12)|(0<<6)|1 = 0x59200001
# CHECK: 10: 59 20 00 01 {{.*}}add.si{{.*}}rd8, 1
add.si rd8, 1

# add.si rd8, -1
# op=0x59, ha=rd8=8, imms18=-1 (0x3FFFF)
# hb = 0x3FFFF>>12 = 0x3F, hc = (0x3FFFF>>6)&0x3F = 0x3F, hd = 0x3FFFF&0x3F = 0x3F
# word = (0x59<<24)|(8<<18)|(0x3F<<12)|(0x3F<<6)|0x3F = 0x5923FFFF
# CHECK: 14: 59 23 ff ff {{.*}}add.si{{.*}}rd8, -1
add.si rd8, -1

#--- iiii format ---

# swym 0
# op=0x77, imm24=0 → ha=0, hb=0, hc=0, hd=0
# word = (0x77<<24)|0 = 0x77000000
# CHECK: 18: 77 00 00 00 {{.*}}swym{{.*}}0
swym 0

# swym 42
# op=0x77, imm24=42=0x2A → ha=0, hb=0, hc=0, hd=0x2A
# word = (0x77<<24)|0x2A = 0x7700002A
# CHECK: 1c: 77 00 00 2a {{.*}}swym{{.*}}42
swym 42

#--- rwii format ---

# set.zw rd8, 0, 0x1234
# op=0x4C, ha=rd8=8, wp=0, immu16=0x1234
# immu16=0x1234=0001_0010_0011_0100b
# hb{5:4}=wp=0, hb{3:0}=imm16[15:12]=0x1, hc=imm16[11:6]=0x08, hd=imm16[5:0]=0x34
# hb = (0<<4)|0x1 = 0x01
# word = (0x4C<<24)|(8<<18)|(0x01<<12)|(0x08<<6)|0x34 = 0x4C201234
# CHECK: 20: 4c 20 12 34 {{.*}}set.zw{{.*}}rd8, 0, 4660
set.zw rd8, 0, 0x1234

#--- orrr format (MISC-octa) ---

# or.o rd8, rd9, rd10
# op=0x40, ha=0x09(or.o), hb=rd8=8, hc=rd9=9, hd=rd10=10
# word = (0x40<<24)|(0x09<<18)|(8<<12)|(9<<6)|10 = 0x4024824A
# CHECK: 24: 40 24 82 4a {{.*}}or.o{{.*}}rd8, rd9, rd10
or.o rd8, rd9, rd10

#--- orri format (MISC-octa) ---

# rb2rd rd8, rb9, 2
# op=0x40, ha=0x36(rb2rd), hb=rd8=8, hc=rb9=9, hd=immu6=2
# word = (0x40<<24)|(0x36<<18)|(8<<12)|(9<<6)|2 = 0x40D88242
# CHECK: 28: 40 d8 82 42 {{.*}}rb2rd{{.*}}rd8, rb9, 2
rb2rd rd8, rb9, 2

#--- oiii format ---

# illi 0
# op=0x00, ha=0x00(illi), imm18=0 → hb=0, hc=0, hd=0
# word = (0x00<<24)|(0x00<<18)|0 = 0x00000000
# CHECK: 2c: 00 00 00 00 {{.*}}illi{{.*}}0
illi 0

#--- Branch instructions (immediate form) ---

# br.n rd0, 4 (immediate form)
# This is the IMMEDIATE form: operand is imms18 field value (4 bytes units)
# op=0x68, ha=rd0=0, imms18=4 → hb=0, hc=0, hd=4
# word = (0x68<<24)|(0<<18)|(0<<12)|(0<<6)|4 = 0x68000004
# Note: NOT (target-current)>>2 - that's only for label form with fixup
# CHECK: 30: 68 00 00 04 {{.*}}br.n{{.*}}rd0, 4
br.n rd0, 4

#--- Branch instructions (label form, demonstrates fixup) ---

# br.n rd0, label (label form, forward branch)
# At offset 0x34, target is at 0x3C (label)
# imms = (0x3C - 0x34) >> 2 = 8 >> 2 = 2
# op=0x68, ha=rd0=0, imms18=2 → hb=0, hc=0, hd=2
# word = (0x68<<24)|2 = 0x68000002
# Note: llvm-objdump shows the raw imms18 value (2), not byte offset
# CHECK: 34: 68 00 00 02 {{.*}}br.n{{.*}}rd0, 2
br.n rd0, label
swym 0
label:
swym 0

#--- Control flow ---

# ret rd0, 0
# op=0x76, ha=rd0=0, imms18=0 → hb=0, hc=0, hd=0
# word = (0x76<<24)|0 = 0x76000000
# CHECK: 40: 76 00 00 00 {{.*}}ret{{.*}}rd0, 0
ret rd0, 0
