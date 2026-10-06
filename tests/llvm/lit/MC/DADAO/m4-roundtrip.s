; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM
; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s -o %t.s
; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %t.s -o %t2
; RUN: cmp %t %t2

; M4 L1 向量：汇编 ↔ 反汇编往返（TESTCASES-029t）。
; `spec/Toolchain-01 §10`（ADR-0013 D3）：
;  - `汇编 → 反汇编` 得到**语义等价**文本（允许规范化：空白统一、大小写、
;    `{}` 内单寄存器不带冒号）；
;  - `反汇编 → 汇编` 产生**逐字节相同**编码。
; 不调用反汇编器即可独立校验的部分：任一等价书写必派生出**同一编码**。
; oracle 对 `@enc` 独立重算字节、对 `@norm` 独立重算两种书写的编码并断言相等；
; `cmp %t %t2`（真往返）现由 lit 执行（INTEG-016t 接入门控）。
;
; @category roundtrip

; 真实指令编码（独立派生自 opcodes.yaml）
add.uo {rd8, rd9}, rd10, rd11      ; @enc 5020928b
or.o rd8, rd9, rd10                ; @enc 4024824a
ld.ub rd8, [rb2, 1]                ; @enc 10202001
ret rd8, 6                         ; @enc 76200006
jump [rb0, 8]                      ; @enc 70000002

; 等价书写的规范化（§10「允许规范化，如空白的统一」）
add.uo {rd8, rd9}, rd10, rd11      ; @norm add.uo {rd8,rd9},rd10,rd11
ld.ub rd8, [rb2, 1]                ; @norm ld.ub  rd8,[rb2,1]
set.zw rd8, wp0, 0xffff            ; @norm set.zw  rd8,wp0,0xffff

; RUN 行所需的 FileCheck 模式：`-filetype=asm` 输出的语义等价文本（规范化后）。
; ASM: add.uo {rd8, rd9}, rd10, rd11
; ASM: or.o rd8, rd9, rd10
; ASM: ld.ub rd8, [rb2, 1]
; ASM: ret rd8, 6
; ASM: jump [rb0, 8]
; ASM: add.uo {rd8, rd9}, rd10, rd11
; ASM: ld.ub rd8, [rb2, 1]
; ASM: set.zw rd8, wp0, 0xffff
