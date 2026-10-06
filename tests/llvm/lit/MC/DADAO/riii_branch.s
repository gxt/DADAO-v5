; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
; RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM

; riii format: conditional branch instructions (byte offsets, must be %4==0)
; Encoding: word = (op<<24)|(ha<<18)|(bytes>>2 & 0x3FFFF)

; br.n {rd0}?, [rb0, 16]
; op=0x68, ha=0, bytes=16, field=16>>2=4
; word = (0x68<<24)|4 = 0x68000004
; OBJ: {{[0-9a-f]+:}} 68 00 00 04{{.*}}br.n{{.*}}{rd0}?, [rb0, 16]
; ASM: br.n {rd0}?, [rb0, 16]
br.n {rd0}?, [rb0, 16]

; br.nn {rd0}?, [rb0, 16]
; op=0x69, ha=0, bytes=16, field=16>>2=4
; word = (0x69<<24)|4 = 0x69000004
; OBJ: {{[0-9a-f]+:}} 69 00 00 04{{.*}}br.nn{{.*}}{rd0}?, [rb0, 16]
; ASM: br.nn {rd0}?, [rb0, 16]
br.nn {rd0}?, [rb0, 16]

; br.z {rd0}?, [rb0, 16]
; op=0x6A, ha=0, bytes=16, field=16>>2=4
; word = (0x6A<<24)|4 = 0x6A000004
; OBJ: {{[0-9a-f]+:}} 6a 00 00 04{{.*}}br.z{{.*}}{rd0}?, [rb0, 16]
; ASM: br.z {rd0}?, [rb0, 16]
br.z {rd0}?, [rb0, 16]

; br.nz {rd0}?, [rb0, 16]
; op=0x6B, ha=0, bytes=16, field=16>>2=4
; word = (0x6B<<24)|4 = 0x6B000004
; OBJ: {{[0-9a-f]+:}} 6b 00 00 04{{.*}}br.nz{{.*}}{rd0}?, [rb0, 16]
; ASM: br.nz {rd0}?, [rb0, 16]
br.nz {rd0}?, [rb0, 16]

; br.p {rd0}?, [rb0, 16]
; op=0x6C, ha=0, bytes=16, field=16>>2=4
; word = (0x6C<<24)|4 = 0x6C000004
; OBJ: {{[0-9a-f]+:}} 6c 00 00 04{{.*}}br.p{{.*}}{rd0}?, [rb0, 16]
; ASM: br.p {rd0}?, [rb0, 16]
br.p {rd0}?, [rb0, 16]

; br.np {rd0}?, [rb0, 16]
; op=0x6D, ha=0, bytes=16, field=16>>2=4
; word = (0x6D<<24)|4 = 0x6D000004
; OBJ: {{[0-9a-f]+:}} 6d 00 00 04{{.*}}br.np{{.*}}{rd0}?, [rb0, 16]
; ASM: br.np {rd0}?, [rb0, 16]
br.np {rd0}?, [rb0, 16]

; br.n {rd0}?, [rb0, 12] (concrete byte offset)
; bytes = 12, field = 12>>2 = 3
; word = (0x68<<24)|3 = 0x68000003
; OBJ: {{[0-9a-f]+:}} 68 00 00 03{{.*}}br.n{{.*}}{rd0}?, [rb0, 12]
; ASM: br.n {rd0}?, [rb0, 12]
br.n {rd0}?, [rb0, 12]