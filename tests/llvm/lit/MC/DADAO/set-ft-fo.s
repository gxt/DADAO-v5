; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
; RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM
; RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=NOPSEUDO

; `set.ft rf, imm32` / `set.fo rf, imm64` and their register forms
; (ADR-0013 D11; spec/SimRISC-03 §set.ft/set.fo).
;   set.ft imm32 -> 2x set.w (low tetra); it must NOT touch the high 32 bits,
;                   so even imm 0 uses 2x set.w (no rd2rf).
;   set.fo imm64 -> imm 0 is materialized from rd0 (always 0) with one rd2rf;
;                   otherwise 4x set.w cover the full octa.
;   set.ft/f.o rf, rs -> rd2rf (rs in rd) / ft2ft, fo2fo (rs in rf).
;
; rwii encoding: word = (op<<24)|(ha<<18)|((wp&3)<<16)|(immu16) ; set.w op=0x4F
; orri block-move encoding: word = (op<<24)|(ha<<18)|(dst<<12)|(src<<6)|count
;   rd2rf: op=0x40 ha=0x3D ; ft2ft: op=0x44 ha=0x02 ; fo2fo: op=0x44 ha=0x0A
;
; NOPSEUDO-NOT: set.ft
; NOPSEUDO-NOT: set.fo

; set.ft rf1, 0x3F800000 -> set.w rf1, wp1, 0x3f80 ; set.w rf1, wp0, 0x0
; set.w wp1: 0x4F<<24|1<<18|1<<16|0x3f80 = 0x4F053F80
; set.w wp0: 0x4F<<24|1<<18|0<<16|0x0    = 0x4F040000
; OBJ: {{[0-9a-f]+:}} 4f 05 3f 80{{.*}}set.w{{.*}}rf1, wp1, 0x3f80
; OBJ-NEXT: {{[0-9a-f]+:}} 4f 04 00 00{{.*}}set.w{{.*}}rf1, wp0, 0x0
; ASM: set.w rf1, wp1, 0x3f80
; ASM: set.w rf1, wp0, 0x0
set.ft rf1, 0x3F800000

; set.fo rf1, 0x3FF0000000000000 -> 4x set.w (wp3/wp2/wp1/wp0)
; set.w wp3: 0x4F<<24|1<<18|3<<16|0x3ff0 = 0x4F073FF0
; set.w wp2: 0x4F060000 ; set.w wp1: 0x4F050000 ; set.w wp0: 0x4F040000
; OBJ: {{[0-9a-f]+:}} 4f 07 3f f0{{.*}}set.w{{.*}}rf1, wp3, 0x3ff0
; OBJ-NEXT: {{[0-9a-f]+:}} 4f 06 00 00{{.*}}set.w{{.*}}rf1, wp2, 0x0
; OBJ-NEXT: {{[0-9a-f]+:}} 4f 05 00 00{{.*}}set.w{{.*}}rf1, wp1, 0x0
; OBJ-NEXT: {{[0-9a-f]+:}} 4f 04 00 00{{.*}}set.w{{.*}}rf1, wp0, 0x0
; ASM: set.w rf1, wp3, 0x3ff0
; ASM: set.w rf1, wp2, 0x0
; ASM: set.w rf1, wp1, 0x0
; ASM: set.w rf1, wp0, 0x0
set.fo rf1, 0x3FF0000000000000

; set.ft rf1, 0 -> 2x set.w (high 32 bits untouched)
; OBJ: {{[0-9a-f]+:}} 4f 05 00 00{{.*}}set.w{{.*}}rf1, wp1, 0x0
; OBJ-NEXT: {{[0-9a-f]+:}} 4f 04 00 00{{.*}}set.w{{.*}}rf1, wp0, 0x0
; ASM: set.w rf1, wp1, 0x0
; ASM: set.w rf1, wp0, 0x0
set.ft rf1, 0

; set.fo rf4, 0 -> rd2rf {rf4}, {rd0}
; word = 0x40<<24|0x3D<<18|4<<12|0<<6|1 = 0x40F44001
; OBJ: {{[0-9a-f]+:}} 40 f4 40 01{{.*}}rd2rf{{.*}}{rf4}, {rd0}
; ASM: rd2rf {rf4}, {rd0}
set.fo rf4, 0

; set.ft rf1, rd5 -> rd2rf {rf1}, {rd5}
; word = 0x40<<24|0x3D<<18|1<<12|5<<6|1 = 0x40F41141
; OBJ: {{[0-9a-f]+:}} 40 f4 11 41{{.*}}rd2rf{{.*}}{rf1}, {rd5}
; ASM: rd2rf {rf1}, {rd5}
set.ft rf1, rd5

; set.ft rf1, rf2 -> ft2ft {rf1}, {rf2}
; word = 0x44<<24|0x02<<18|1<<12|2<<6|1 = 0x44081081
; OBJ: {{[0-9a-f]+:}} 44 08 10 81{{.*}}ft2ft{{.*}}{rf1}, {rf2}
; ASM: ft2ft {rf1}, {rf2}
set.ft rf1, rf2

; set.fo rf2, rf7 -> fo2fo {rf2}, {rf7}
; word = 0x44<<24|0x0A<<18|2<<12|7<<6|1 = 0x442821C1
; OBJ: {{[0-9a-f]+:}} 44 28 21 c1{{.*}}fo2fo{{.*}}{rf2}, {rf7}
; ASM: fo2fo {rf2}, {rf7}
set.fo rf2, rf7
