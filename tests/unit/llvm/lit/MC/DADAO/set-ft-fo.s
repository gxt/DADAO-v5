@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
@@ RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM
@@ RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=NOPSEUDO

@@ `set.ft rf, imm32` / `set.fo rf, imm64` and their register forms
@@ (ADR-0013 D11; spec/SimRISC-03 §set.ft/set.fo).
@@   set.ft imm32 -> 2x set.w (low tetra); it must NOT touch the high 32 bits,
@@                   so even imm 0 uses 2x set.w (no rd2rf).
@@   set.fo imm64 -> rd2rf rf, rd0 (rd0 is constant zero) zeroes the whole octa,
@@                   then one set.w per NON-ZERO wyde (k of them, high-to-low):
@@                   k <= 3 -> 1 + k instructions (k == 0 -> just the rd2rf);
@@                   k == 4 -> 4x set.w instead (the rd0 scheme would need 5).
@@   set.ft/f.o rf, rs -> rd2rf (rs in rd) / rf2rf (rs in rf).
@@                          An RF source is a full 64-bit bit copy.
@@
@@ rwii encoding: word = (op<<24)|(ha<<18)|((wp&3)<<16)|(immu16) ; set.w op=0x4F
@@ orri block-move encoding: word = (op<<24)|(ha<<18)|(dst<<12)|(src<<6)|count
@@   rd2rf: op=0x40 ha=0x3D ; rf2rf: op=0x40 ha=0x3C
@@
@@ NOPSEUDO-NOT: set.ft
@@ NOPSEUDO-NOT: set.fo

@@ set.ft rf1, 0x3F800000 -> set.w rf1, wp1, 0x3f80 ; set.w rf1, wp0, 0x0
@@ set.w wp1: 0x4F<<24|1<<18|1<<16|0x3f80 = 0x4F053F80
@@ set.w wp0: 0x4F<<24|1<<18|0<<16|0x0    = 0x4F040000
@@ OBJ: {{[0-9a-f]+:}} 4f 05 3f 80{{.*}}set.w{{.*}}rf1, wp1, 0x3f80
@@ OBJ-NEXT: {{[0-9a-f]+:}} 4f 04 00 00{{.*}}set.w{{.*}}rf1, wp0, 0x0
@@ ASM: set.w rf1, wp1, 0x3f80
@@ ASM: set.w rf1, wp0, 0x0
set.ft rf1, 0x3F800000

@@ set.fo rf1, 0 -> rd2rf {rf1}, {rd0}（k=0：1 条）
@@ word = 0x40<<24|0x3D<<18|1<<12|0<<6|1 = 0x40F41001
@@ OBJ: {{[0-9a-f]+:}} 40 f4 10 01{{.*}}rd2rf{{.*}}{rf1}, {rd0}
@@ ASM: rd2rf {rf1}, {rd0}
set.fo rf1, 0

@@ set.fo rf2, 0x3FF0000000000000 -> rd2rf + set.w wp3 only（k=1，高半非零；2 条）
@@ rd2rf: 0x40F42001 ; set.w wp3 (ha=2): 0x4F0B3FF0
@@ OBJ-NEXT: {{[0-9a-f]+:}} 40 f4 20 01{{.*}}rd2rf{{.*}}{rf2}, {rd0}
@@ OBJ-NEXT: {{[0-9a-f]+:}} 4f 0b 3f f0{{.*}}set.w{{.*}}rf2, wp3, 0x3ff0
@@ ASM: rd2rf {rf2}, {rd0}
@@ ASM-NEXT: set.w rf2, wp3, 0x3ff0
set.fo rf2, 0x3FF0000000000000

@@ set.fo rf3, 0x12345678 -> rd2rf + wp1/wp0（k=2；3 条，零 wyde 不写）
@@ OBJ-NEXT: {{[0-9a-f]+:}} 40 f4 30 01{{.*}}rd2rf{{.*}}{rf3}, {rd0}
@@ OBJ-NEXT: {{[0-9a-f]+:}} 4f 0d 12 34{{.*}}set.w{{.*}}rf3, wp1, 0x1234
@@ OBJ-NEXT: {{[0-9a-f]+:}} 4f 0c 56 78{{.*}}set.w{{.*}}rf3, wp0, 0x5678
@@ ASM: rd2rf {rf3}, {rd0}
@@ ASM-NEXT: set.w rf3, wp1, 0x1234
@@ ASM-NEXT: set.w rf3, wp0, 0x5678
set.fo rf3, 0x12345678

@@ set.fo rf4, 0x123456789ABC -> rd2rf + wp2/wp1/wp0（k=3，与 4×set.w 并列；4 条）
@@ OBJ-NEXT: {{[0-9a-f]+:}} 40 f4 40 01{{.*}}rd2rf{{.*}}{rf4}, {rd0}
@@ OBJ-NEXT: {{[0-9a-f]+:}} 4f 12 12 34{{.*}}set.w{{.*}}rf4, wp2, 0x1234
@@ OBJ-NEXT: {{[0-9a-f]+:}} 4f 11 56 78{{.*}}set.w{{.*}}rf4, wp1, 0x5678
@@ OBJ-NEXT: {{[0-9a-f]+:}} 4f 10 9a bc{{.*}}set.w{{.*}}rf4, wp0, 0x9abc
@@ ASM: rd2rf {rf4}, {rd0}
@@ ASM-NEXT: set.w rf4, wp2, 0x1234
@@ ASM-NEXT: set.w rf4, wp1, 0x5678
@@ ASM-NEXT: set.w rf4, wp0, 0x9abc
set.fo rf4, 0x123456789ABC

@@ set.fo rf5, 0x123456789ABCDEF0 -> 4x set.w（k=4；4 条，不出现 rd2rf）
@@ OBJ-NEXT: {{[0-9a-f]+:}} 4f 17 12 34{{.*}}set.w{{.*}}rf5, wp3, 0x1234
@@ OBJ-NEXT: {{[0-9a-f]+:}} 4f 16 56 78{{.*}}set.w{{.*}}rf5, wp2, 0x5678
@@ OBJ-NEXT: {{[0-9a-f]+:}} 4f 15 9a bc{{.*}}set.w{{.*}}rf5, wp1, 0x9abc
@@ OBJ-NEXT: {{[0-9a-f]+:}} 4f 14 de f0{{.*}}set.w{{.*}}rf5, wp0, 0xdef0
@@ ASM: set.w rf5, wp3, 0x1234
@@ ASM-NEXT: set.w rf5, wp2, 0x5678
@@ ASM-NEXT: set.w rf5, wp1, 0x9abc
@@ ASM-NEXT: set.w rf5, wp0, 0xdef0
set.fo rf5, 0x123456789ABCDEF0

@@ set.ft rf1, 0 -> 2x set.w (high 32 bits untouched)
@@ OBJ: {{[0-9a-f]+:}} 4f 05 00 00{{.*}}set.w{{.*}}rf1, wp1, 0x0
@@ OBJ-NEXT: {{[0-9a-f]+:}} 4f 04 00 00{{.*}}set.w{{.*}}rf1, wp0, 0x0
@@ ASM: set.w rf1, wp1, 0x0
@@ ASM: set.w rf1, wp0, 0x0
set.ft rf1, 0

@@ set.fo rf4, 0 -> rd2rf {rf4}, {rd0}
@@ word = 0x40<<24|0x3D<<18|4<<12|0<<6|1 = 0x40F44001
@@ OBJ: {{[0-9a-f]+:}} 40 f4 40 01{{.*}}rd2rf{{.*}}{rf4}, {rd0}
@@ ASM: rd2rf {rf4}, {rd0}
set.fo rf4, 0

@@ set.ft rf1, rd5 -> rd2rf {rf1}, {rd5}
@@ word = 0x40<<24|0x3D<<18|1<<12|5<<6|1 = 0x40F41141
@@ OBJ: {{[0-9a-f]+:}} 40 f4 11 41{{.*}}rd2rf{{.*}}{rf1}, {rd5}
@@ ASM: rd2rf {rf1}, {rd5}
set.ft rf1, rd5

@@ set.ft rf1, rf2 -> rf2rf {rf1}, {rf2}
@@ word = 0x40<<24|0x3C<<18|1<<12|2<<6|1 = 0x40F01081
@@ OBJ: {{[0-9a-f]+:}} 40 f0 10 81{{.*}}rf2rf{{.*}}{rf1}, {rf2}
@@ ASM: rf2rf {rf1}, {rf2}
set.ft rf1, rf2

@@ set.fo rf2, rf7 -> rf2rf {rf2}, {rf7}
@@ word = 0x40<<24|0x3C<<18|2<<12|7<<6|1 = 0x40F021C1
@@ OBJ: {{[0-9a-f]+:}} 40 f0 21 c1{{.*}}rf2rf{{.*}}{rf2}, {rf7}
@@ ASM: rf2rf {rf2}, {rf7}
set.fo rf2, rf7
