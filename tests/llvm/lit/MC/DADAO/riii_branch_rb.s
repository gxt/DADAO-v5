; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
; RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM

; LLVM-049t: riii br.z/br.nz variant selection is driven by the register bank of
; the condition operand, for both symbolic (expression) and numeric offsets.
;   br.z  {rdN}? -> op 0x6A (RD)   br.z  {rbN}? -> op 0x72 (RB)
;   br.nz {rdN}? -> op 0x6B (RD)   br.nz {rbN}? -> op 0x73 (RB)
; Encoding (riii): word = (op<<24) | (reg<<18) | (bytes>>2 & 0x3FFFF)
;
; The symbolic cases exercise the MC AsmParser expression-offset bypass (the
; path fixed by LLVM-049t); the numeric cases exercise MatchInstructionImpl,
; which was already bank-aware.  Both must agree.

; --- symbolic (expression) offsets: all four target Lend at +16/+12/+8/+4 ---
; br.z  {rd8}?, [rb0, Lend] at 0x04: Lend at 0x14 -> 16 bytes >>2 = 4 -> 6a 20 00 04
; OBJ: {{[0-9a-f]+:}} 6a 20 00 04{{.*}}br.z{{.*}}{rd8}?, [rb0, 16]
; ASM: br.z {rd8}?, [rb0, Lend]
br.z {rd8}?, [rb0, Lend]
; br.nz {rd8}?, [rb0, Lend] at 0x08 -> 12 bytes >>2 = 3 -> 6b 20 00 03
; OBJ: {{[0-9a-f]+:}} 6b 20 00 03{{.*}}br.nz{{.*}}{rd8}?, [rb0, 12]
; ASM: br.nz {rd8}?, [rb0, Lend]
br.nz {rd8}?, [rb0, Lend]
; br.z  {rb8}?, [rb0, Lend] at 0x0C -> 8 bytes >>2 = 2 -> 72 20 00 02 (RB variant)
; OBJ: {{[0-9a-f]+:}} 72 20 00 02{{.*}}br.z{{.*}}{rb8}?, [rb0, 8]
; ASM: br.z {rb8}?, [rb0, Lend]
br.z {rb8}?, [rb0, Lend]
; br.nz {rb8}?, [rb0, Lend] at 0x10 -> 4 bytes >>2 = 1 -> 73 20 00 01 (RB variant)
; OBJ: {{[0-9a-f]+:}} 73 20 00 01{{.*}}br.nz{{.*}}{rb8}?, [rb0, 4]
; ASM: br.nz {rb8}?, [rb0, Lend]
br.nz {rb8}?, [rb0, Lend]
Lend: swym 0

; --- numeric offsets: same bank selection, no fixup ---
; br.z {rd16}?, [rb0, 16] -> op 0x6A, reg 16<<18=0x400000, 16>>2=4 -> 6a 40 00 04
; OBJ: {{[0-9a-f]+:}} 6a 40 00 04{{.*}}br.z{{.*}}{rd16}?, [rb0, 16]
; ASM: br.z {rd16}?, [rb0, 16]
br.z {rd16}?, [rb0, 16]
; br.nz {rd16}?, [rb0, 16] -> op 0x6B, reg 16 -> 6b 40 00 04
; OBJ: {{[0-9a-f]+:}} 6b 40 00 04{{.*}}br.nz{{.*}}{rd16}?, [rb0, 16]
; ASM: br.nz {rd16}?, [rb0, 16]
br.nz {rd16}?, [rb0, 16]
; br.z {rb16}?, [rb0, 16] -> op 0x72 (RB), reg 16 -> 72 40 00 04
; OBJ: {{[0-9a-f]+:}} 72 40 00 04{{.*}}br.z{{.*}}{rb16}?, [rb0, 16]
; ASM: br.z {rb16}?, [rb0, 16]
br.z {rb16}?, [rb0, 16]
; br.nz {rb16}?, [rb0, 16] -> op 0x73 (RB), reg 16 -> 73 40 00 04
; OBJ: {{[0-9a-f]+:}} 73 40 00 04{{.*}}br.nz{{.*}}{rb16}?, [rb0, 16]
; ASM: br.nz {rb16}?, [rb0, 16]
br.nz {rb16}?, [rb0, 16]
