; UNSUPPORTED: true
; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
; RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=DEF
; RUN: %llvm_mc --triple=dadao-unknown-elf -multiple-to-single -filetype=obj %s -o %t.opt
; RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t.opt | %FileCheck %s --check-prefix=OPT

; M4 L1 向量：`-multiple-to-single` 选项开/关对照（TESTCASES-029t）。
; `spec/Toolchain-01 §8`（DADAO-11 §汇编器选项）：多寄存器指令转换为一系列
; 单寄存器指令，**助记符不变**；关闭时（默认）保持多寄存器形态。
; 期望值：默认形态的编码由 opcodes.yaml 独立派生（count = 组内元素数）；
; 展开形态由 spec §8 + §4.2 独立派生（每元素一条、偏移随元素宽度步进并复原）。
; oracle 对 `@enc` 独立重算编码，对 `@mts` 独立重算展开序列。
;
; @category option

; --- 默认（关）：多寄存器 / 块移动保持单条，count = 元素数 ---
ldm.o {rd8:rd10}, [rb2, rd1]   ; @enc 38202043
stm.b {rd8:rd9}, [rb3, rd2]    ; @enc 30203082
ra2rd {rd8:rd10}, {ra1:ra3}    ; @enc 40b88043

; --- 开：展开为单寄存器序列（助记符不变）---
; ldm.o 元素宽 8：元素间 +8，末条复原 -(n-1)*8
ldm.o {rd8:rd10}, [rb2, rd1]   ; @mts ldm.o {rd8}, [rb2, rd1] ; add.si rd1, 8 ; ldm.o {rd9}, [rb2, rd1] ; add.si rd1, 8 ; ldm.o {rd10}, [rb2, rd1] ; add.si rd1, -16
; stm.b 元素宽 1：元素间 +1，末条复原 -(n-1)*1
stm.b {rd8:rd9}, [rb3, rd2]    ; @mts stm.b {rd8}, [rb3, rd2] ; add.si rd2, 1 ; stm.b {rd9}, [rb3, rd2] ; add.si rd2, -1
; orri 块移动：每元素一条，无偏移寄存器
ra2rd {rd8:rd10}, {ra1:ra3}    ; @mts ra2rd {rd8}, {ra1} ; ra2rd {rd9}, {ra2} ; ra2rd {rd10}, {ra3}
ft2fo {rf4:rf6}, {rf8:rf10}    ; @mts ft2fo {rf4}, {rf8} ; ft2fo {rf5}, {rf9} ; ft2fo {rf6}, {rf10}
