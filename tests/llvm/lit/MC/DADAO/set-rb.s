; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
; RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM
; RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=NOPSEUDO

; `set.rb rb, imm64` / `set.rb rb, rs` (ADR-0013 D11; spec/SimRISC-03
; §set.rb).  rb has no set.ow variant, so constants always seed with
; set.zw (fill 0) and correct the other wydes with or.w; all-ones therefore
; needs set.zw + 3x or.w.  Register moves select rd2rb / rb2rb.
;
; rwii encoding: word = (op<<24)|(ha<<18)|((wp&3)<<16)|(immu16)
;   op: or.w(rb)=0x4A, set.zw(rb)=0x4E
; orri block-move encoding: word = (op<<24)|(ha<<18)|(dst<<12)|(src<<6)|count
;   rd2rb: op=0x40 ha=0x35 ; rb2rb: op=0x40 ha=0x34
;
; NOPSEUDO-NOT: set.rb

; set.rb rb1, 0 -> set.zw rb1, wp0, 0x0
; word = 0x4E<<24|1<<18|0<<16|0 = 0x4E040000
; OBJ: {{[0-9a-f]+:}} 4e 04 00 00{{.*}}set.zw{{.*}}rb1, wp0, 0x0
; ASM: set.zw rb1, wp0, 0x0
set.rb rb1, 0

; set.rb rb1, 0x123456789ABC -> set.zw wp2 ; or.w wp1 ; or.w wp0
; set.zw wp2: 0x4E<<24|1<<18|2<<16|0x1234 = 0x4E061234
; or.w   wp1: 0x4A<<24|1<<18|1<<16|0x5678 = 0x4A055678
; or.w   wp0: 0x4A<<24|1<<18|0<<16|0x9abc = 0x4A049ABC
; OBJ: {{[0-9a-f]+:}} 4e 06 12 34{{.*}}set.zw{{.*}}rb1, wp2, 0x1234
; OBJ-NEXT: {{[0-9a-f]+:}} 4a 05 56 78{{.*}}or.w{{.*}}rb1, wp1, 0x5678
; OBJ-NEXT: {{[0-9a-f]+:}} 4a 04 9a bc{{.*}}or.w{{.*}}rb1, wp0, 0x9abc
; ASM: set.zw rb1, wp2, 0x1234
; ASM: or.w rb1, wp1, 0x5678
; ASM: or.w rb1, wp0, 0x9abc
set.rb rb1, 0x123456789ABC

; set.rb rb3, -1 -> set.zw wp3 ; or.w wp2 ; or.w wp1 ; or.w wp0 (all 0xffff)
; set.zw: 0x4E<<24|3<<18|3<<16|0xffff = 0x4E0FFFFF
; or.w  : 0x4A<<24|3<<18|{2,1,0}<<16|0xffff = 0x4A0EFFFF/0x4A0DFFFF/0x4A0CFFFF
; OBJ: {{[0-9a-f]+:}} 4e 0f ff ff{{.*}}set.zw{{.*}}rb3, wp3, 0xffff
; OBJ-NEXT: {{[0-9a-f]+:}} 4a 0e ff ff{{.*}}or.w{{.*}}rb3, wp2, 0xffff
; OBJ-NEXT: {{[0-9a-f]+:}} 4a 0d ff ff{{.*}}or.w{{.*}}rb3, wp1, 0xffff
; OBJ-NEXT: {{[0-9a-f]+:}} 4a 0c ff ff{{.*}}or.w{{.*}}rb3, wp0, 0xffff
; ASM: set.zw rb3, wp3, 0xffff
; ASM: or.w rb3, wp2, 0xffff
; ASM: or.w rb3, wp1, 0xffff
; ASM: or.w rb3, wp0, 0xffff
set.rb rb3, -1

; set.rb rb1, rd7 -> rd2rb {rb1}, {rd7}
; word = 0x40<<24|0x35<<18|1<<12|7<<6|1 = 0x40D411C1
; OBJ: {{[0-9a-f]+:}} 40 d4 11 c1{{.*}}rd2rb{{.*}}{rb1}, {rd7}
; ASM: rd2rb {rb1}, {rd7}
set.rb rb1, rd7

; set.rb rb2, rb7 -> rb2rb {rb2}, {rb7}
; word = 0x40<<24|0x34<<18|2<<12|7<<6|1 = 0x40D021C1
; OBJ: {{[0-9a-f]+:}} 40 d0 21 c1{{.*}}rb2rb{{.*}}{rb2}, {rb7}
; ASM: rb2rb {rb2}, {rb7}
set.rb rb2, rb7
