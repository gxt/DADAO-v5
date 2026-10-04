; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
; RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM

; Wyde-position operand tests (LLVM-013t; tightened by LLVM-045t / ISS-128):
; wp0/wp1/wp2/wp3 tokens are the required syntax and are encoded verbatim.
; Bare numeric 0-3 is rejected — see wpn_err_bare_num.s.
; wp4 and other invalid tokens → error.
; wp in hb[5:4]; immu16 in hb[3:0]:hc:hd.
; rwii format: word = (op<<24)|(ra<<18)|((wp<<4)|(imm16>>12))<<12|((imm16>>6)&0x3F)<<6|(imm16&0x3F)

; --- wp0-wp3 with imm16=0xFFFF ---

; OBJ: {{[0-9a-f]+:}} 4e 04 ff ff{{.*}}set.zw{{.*}}rb1, wp0, 0xffff
; ASM: set.zw rb1, wp0, 0xffff
set.zw rb1, wp0, 0xffff

; OBJ: {{[0-9a-f]+:}} 4e 05 ff ff{{.*}}set.zw{{.*}}rb1, wp1, 0xffff
; ASM: set.zw rb1, wp1, 0xffff
set.zw rb1, wp1, 0xffff

; OBJ: {{[0-9a-f]+:}} 4e 06 ff ff{{.*}}set.zw{{.*}}rb1, wp2, 0xffff
; ASM: set.zw rb1, wp2, 0xffff
set.zw rb1, wp2, 0xffff

; OBJ: {{[0-9a-f]+:}} 4e 07 ff ff{{.*}}set.zw{{.*}}rb1, wp3, 0xffff
; ASM: set.zw rb1, wp3, 0xffff
set.zw rb1, wp3, 0xffff

; --- wp0-wp3 with different imm16 (0x00FF = 255) ---

; OBJ: {{[0-9a-f]+:}} 4e 04 00 ff{{.*}}set.zw{{.*}}rb1, wp0, 0xff
; ASM: set.zw rb1, wp0, 0xff
set.zw rb1, wp0, 0x00ff

; OBJ: {{[0-9a-f]+:}} 4e 05 00 ff{{.*}}set.zw{{.*}}rb1, wp1, 0xff
; ASM: set.zw rb1, wp1, 0xff
set.zw rb1, wp1, 0x00ff

; OBJ: {{[0-9a-f]+:}} 4e 06 00 ff{{.*}}set.zw{{.*}}rb1, wp2, 0xff
; ASM: set.zw rb1, wp2, 0xff
set.zw rb1, wp2, 0x00ff

; OBJ: {{[0-9a-f]+:}} 4e 07 00 ff{{.*}}set.zw{{.*}}rb1, wp3, 0xff
; ASM: set.zw rb1, wp3, 0xff
set.zw rb1, wp3, 0x00ff
