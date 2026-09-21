# RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
# RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
# RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM

# RA instructions: ld.o / st.o (rrii), ldm.o / stm.o (rrri), rd2ra / ra2rd (orri)
# Encoding per contracts/opcodes.yaml

# --- ld.o ra1, rb2, 0 ---
# op=0x24, ha=1, hb=2, imm12=0
# word = (0x24<<24)|(1<<18)|(2<<12)|0 = 0x24042000
# OBJ: {{[0-9a-f]+:}} 24 04 20 00{{.*}}ld.o{{.*}}ra1, rb2, 0
# ASM: ld.o ra1, rb2, 0
ld.o ra1, rb2, 0

# --- st.o ra1, rb2, 8 ---
# op=0x25, ha=1, hb=2, imm12=8
# word = (0x25<<24)|(1<<18)|(2<<12)|8 = 0x25042008
# OBJ: {{[0-9a-f]+:}} 25 04 20 08{{.*}}st.o{{.*}}ra1, rb2, 8
# ASM: st.o ra1, rb2, 8
st.o ra1, rb2, 8

# --- ldm.o ra1, rb2, rd3, 2 ---
# op=0x3C, ha=1, hb=2, hc=3, hd=2
# word = (0x3C<<24)|(1<<18)|(2<<12)|(3<<6)|2 = 0x3C0420C2
# OBJ: {{[0-9a-f]+:}} 3c 04 20 c2{{.*}}ldm.o{{.*}}ra1, rb2, rd3, 2
# ASM: ldm.o ra1, rb2, rd3, 2
ldm.o ra1, rb2, rd3, 2

# --- stm.o ra1, rb2, rd3, 2 ---
# op=0x3D, ha=1, hb=2, hc=3, hd=2
# word = (0x3D<<24)|(1<<18)|(2<<12)|(3<<6)|2 = 0x3D0420C2
# OBJ: {{[0-9a-f]+:}} 3d 04 20 c2{{.*}}stm.o{{.*}}ra1, rb2, rd3, 2
# ASM: stm.o ra1, rb2, rd3, 2
stm.o ra1, rb2, rd3, 2

# --- rd2ra ra1, rd2, 3 ---
# op=0x40, ha=0x2D, hb=1, hc=2, hd=3
# word = (0x40<<24)|(0x2D<<18)|(1<<12)|(2<<6)|3 = 0x40B41083
# OBJ: {{[0-9a-f]+:}} 40 b4 10 83{{.*}}rd2ra{{.*}}ra1, rd2, 3
# ASM: rd2ra ra1, rd2, 3
rd2ra ra1, rd2, 3

# --- ra2rd rd1, ra2, 3 ---
# op=0x40, ha=0x2E, hb=1, hc=2, hd=3
# word = (0x40<<24)|(0x2E<<18)|(1<<12)|(2<<6)|3 = 0x40B81083
# OBJ: {{[0-9a-f]+:}} 40 b8 10 83{{.*}}ra2rd{{.*}}rd1, ra2, 3
# ASM: ra2rd rd1, ra2, 3
ra2rd rd1, ra2, 3

# === Boundary: ra0 ===

# --- ld.o ra0, rb0, 0 ---
# op=0x24, ha=0, hb=0, imm12=0
# word = (0x24<<24)|0 = 0x24000000
# OBJ: {{[0-9a-f]+:}} 24 00 00 00{{.*}}ld.o{{.*}}ra0, rb0, 0
# ASM: ld.o ra0, rb0, 0
ld.o ra0, rb0, 0

# === Boundary: ra63 ===

# --- st.o ra63, rb63, 0 ---
# op=0x25, ha=63, hb=63, imm12=0
# word = (0x25<<24)|(63<<18)|(63<<12)|0 = 0x25FFF000
# OBJ: {{[0-9a-f]+:}} 25 ff f0 00{{.*}}st.o{{.*}}ra63, rb63, 0
# ASM: st.o ra63, rb63, 0
st.o ra63, rb63, 0

# === Boundary: immu6=0 (runtime ILLI, encoding valid) ===

# --- ldm.o ra0, rb0, rd0, 0 ---
# op=0x3C, ha=0, hb=0, hc=0, hd=0
# word = (0x3C<<24)|0 = 0x3C000000
# OBJ: {{[0-9a-f]+:}} 3c 00 00 00{{.*}}ldm.o{{.*}}ra0, rb0, rd0, 0
# ASM: ldm.o ra0, rb0, rd0, 0
ldm.o ra0, rb0, rd0, 0

# === Boundary: immu6=63 ===

# --- rd2ra ra0, rd0, 63 ---
# op=0x40, ha=0x2D, hb=0, hc=0, hd=63
# word = (0x40<<24)|(0x2D<<18)|(0<<12)|(0<<6)|63 = 0x40B4003F
# OBJ: {{[0-9a-f]+:}} 40 b4 00 3f{{.*}}rd2ra{{.*}}ra0, rd0, 63
# ASM: rd2ra ra0, rd0, 63
rd2ra ra0, rd0, 63

# === Boundary: ra63 + immu6=63 ===

# --- ra2rd rd63, ra63, 63 ---
# op=0x40, ha=0x2E, hb=63, hc=63, hd=63
# word = (0x40<<24)|(0x2E<<18)|(63<<12)|(63<<6)|63 = 0x40BBFFFF
# OBJ: {{[0-9a-f]+:}} 40 bb ff ff{{.*}}ra2rd{{.*}}rd63, ra63, 63
# ASM: ra2rd rd63, ra63, 63
ra2rd rd63, ra63, 63
