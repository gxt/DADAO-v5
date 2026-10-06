; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
; RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM

; `set.rd rd, rs` register move (ADR-0013 D11; spec/SimRISC-03 §set.rd).
; Expands to a single block move selected from the source register bank:
;   rs in rb -> rb2rd ; rs in rf -> rf2rd ; rs in ra -> ra2rd ; rs in rd -> rd2rd
;
; orri block-move encoding: word = (op<<24)|(ha<<18)|(dst<<12)|(src<<6)|count
;   (ha = opx; count = 1 for a single-register move)
;   rb2rd: op=0x40 ha=0x36 ; rf2rd: op=0x40 ha=0x3E ; ra2rd: op=0x40 ha=0x2E
;   rd2rd: op=0x40 ha=0x2C

; set.rd rd5, rb3 -> rb2rd {rd5}, {rb3}
; word = 0x40<<24|0x36<<18|5<<12|3<<6|1 = 0x40D850C1
; OBJ: {{[0-9a-f]+:}} 40 d8 50 c1{{.*}}rb2rd{{.*}}{rd5}, {rb3}
; ASM: rb2rd {rd5}, {rb3}
set.rd rd5, rb3

; set.rd rd2, rf7 -> rf2rd {rd2}, {rf7}
; word = 0x40<<24|0x3E<<18|2<<12|7<<6|1 = 0x40F821C1
; OBJ: {{[0-9a-f]+:}} 40 f8 21 c1{{.*}}rf2rd{{.*}}{rd2}, {rf7}
; ASM: rf2rd {rd2}, {rf7}
set.rd rd2, rf7

; set.rd rd8, rd3 -> rd2rd {rd8}, {rd3}
; word = 0x40<<24|0x2C<<18|8<<12|3<<6|1 = 0x40B080C1
; OBJ: {{[0-9a-f]+:}} 40 b0 80 c1{{.*}}rd2rd{{.*}}{rd8}, {rd3}
; ASM: rd2rd {rd8}, {rd3}
set.rd rd8, rd3

; set.rd rd4, ra10 -> ra2rd {rd4}, {ra10}
; word = 0x40<<24|0x2E<<18|4<<12|10<<6|1 = 0x40B84281
; OBJ: {{[0-9a-f]+:}} 40 b8 42 81{{.*}}ra2rd{{.*}}{rd4}, {ra10}
; ASM: ra2rd {rd4}, {ra10}
set.rd rd4, ra10
