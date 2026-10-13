; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
; RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s
; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM

; M4 L1 向量：伪指令展开（`set.rd`/`set.rb`/`set.ft`/`set.fo`）（TESTCASES-029t）。
; 权威源 = ``spec/Toolchain-01-汇编语言.md §6``（`ADR-0013 D11`）。
; 期望值（展开 + 各真实指令编码）由 `tools/testcases/validate_mc_vectors.py`
; 从 `contracts/opcodes.yaml`（编码身份）与 `spec §6.1`（展开规则）独立派生。
; 下方 `CHECK`/`ASM` 检查行为 RUN 行所需的 FileCheck 模式，与之对应的期望为
; 同行 `@exp` 的独立派生展开序列（INTEG-016t 接入门控）。
;
; @category pseudo

; --- set.rd rd, imm64：最少指令数（set.zw/set.ow + or.w/andn.w）---
set.rd rd1, 0                    ; @exp set.zw rd1, wp0, 0x0
; CHECK: set.zw rd1, wp0, 0x0
; ASM: set.zw rd1, wp0, 0x0
set.rd rd5, 42                   ; @exp set.zw rd5, wp0, 0x2a
; CHECK: set.zw rd5, wp0, 0x2a
; ASM: set.zw rd5, wp0, 0x2a
set.rd rd6, 0x1234ABCD           ; @exp set.zw rd6, wp1, 0x1234 ; or.w rd6, wp0, 0xabcd
; CHECK: set.zw rd6, wp1, 0x1234
; CHECK: or.w rd6, wp0, 0xabcd
; ASM: set.zw rd6, wp1, 0x1234
; ASM: or.w rd6, wp0, 0xabcd
set.rd rd2, -1                   ; @exp set.ow rd2, wp0, 0xffff
; CHECK: set.ow rd2, wp0, 0xffff
; ASM: set.ow rd2, wp0, 0xffff
set.rd rd4, ~(1<<5)              ; @exp set.ow rd4, wp0, 0xffdf
; CHECK: set.ow rd4, wp0, 0xffdf
; ASM: set.ow rd4, wp0, 0xffdf
set.rd rd8, 0x12340000FFFFFFFF   ; @exp set.ow rd8, wp3, 0x1234 ; andn.w rd8, wp2, 0xffff
; CHECK: set.ow rd8, wp3, 0x1234
; CHECK: andn.w rd8, wp2, 0xffff
; ASM: set.ow rd8, wp3, 0x1234
; ASM: andn.w rd8, wp2, 0xffff

; --- set.rd rd, rs：按源寄存器组选块移动 ---
set.rd rd5, rb3                  ; @exp rb2rd {rd5}, {rb3}
; CHECK: rb2rd {rd5}, {rb3}
; ASM: rb2rd {rd5}, {rb3}
set.rd rd8, rd3                  ; @exp rd2rd {rd8}, {rd3}
; CHECK: rd2rd {rd8}, {rd3}
; ASM: rd2rd {rd8}, {rd3}
set.rd rd4, ra10                 ; @exp ra2rd {rd4}, {ra10}
; CHECK: ra2rd {rd4}, {ra10}
; ASM: ra2rd {rd4}, {ra10}
set.rd rd2, rf7                  ; @exp rf2rd {rd2}, {rf7}
; CHECK: rf2rd {rd2}, {rf7}
; ASM: rf2rd {rd2}, {rf7}

; --- set.rb rb, imm64：rb 无 set.ow 变体 ---
set.rb rb1, 0                    ; @exp set.zw rb1, wp0, 0x0
; CHECK: set.zw rb1, wp0, 0x0
; ASM: set.zw rb1, wp0, 0x0
set.rb rb1, 0x123456789ABC       ; @exp set.zw rb1, wp2, 0x1234 ; or.w rb1, wp1, 0x5678 ; or.w rb1, wp0, 0x9abc
; CHECK: set.zw rb1, wp2, 0x1234
; CHECK: or.w rb1, wp1, 0x5678
; CHECK: or.w rb1, wp0, 0x9abc
; ASM: set.zw rb1, wp2, 0x1234
; ASM: or.w rb1, wp1, 0x5678
; ASM: or.w rb1, wp0, 0x9abc
set.rb rb3, -1                   ; @exp set.zw rb3, wp3, 0xffff ; or.w rb3, wp2, 0xffff ; or.w rb3, wp1, 0xffff ; or.w rb3, wp0, 0xffff
; CHECK: set.zw rb3, wp3, 0xffff
; CHECK: or.w rb3, wp2, 0xffff
; CHECK: or.w rb3, wp1, 0xffff
; CHECK: or.w rb3, wp0, 0xffff
; ASM: set.zw rb3, wp3, 0xffff
; ASM: or.w rb3, wp2, 0xffff
; ASM: or.w rb3, wp1, 0xffff
; ASM: or.w rb3, wp0, 0xffff

; --- set.rb rb, rs ---
set.rb rb1, rd7                  ; @exp rd2rb {rb1}, {rd7}
; CHECK: rd2rb {rb1}, {rd7}
; ASM: rd2rb {rb1}, {rd7}
set.rb rb2, rb7                  ; @exp rb2rb {rb2}, {rb7}
; CHECK: rb2rb {rb2}, {rb7}
; ASM: rb2rb {rb2}, {rb7}

; --- set.ft rf, imm32：2 条 set.w（高 32 位不动）---
set.ft rf1, 0x3F800000           ; @exp set.w rf1, wp1, 0x3f80 ; set.w rf1, wp0, 0x0
; CHECK: set.w rf1, wp1, 0x3f80
; CHECK: set.w rf1, wp0, 0x0
; ASM: set.w rf1, wp1, 0x3f80
; ASM: set.w rf1, wp0, 0x0
set.ft rf1, 0                    ; @exp set.w rf1, wp1, 0x0 ; set.w rf1, wp0, 0x0
; CHECK: set.w rf1, wp1, 0x0
; CHECK: set.w rf1, wp0, 0x0
; ASM: set.w rf1, wp1, 0x0
; ASM: set.w rf1, wp0, 0x0

; --- set.ft / set.fo rf, rs ---
set.ft rf1, rd5                  ; @exp rd2rf {rf1}, {rd5}
; CHECK: rd2rf {rf1}, {rd5}
; ASM: rd2rf {rf1}, {rd5}
set.ft rf1, rf2                  ; @exp ft2ft {rf1}, {rf2}
; CHECK: ft2ft {rf1}, {rf2}
; ASM: ft2ft {rf1}, {rf2}

; --- set.fo rf, imm64：4 条 set.w ---
set.fo rf1, 0x3FF0000000000000   ; @exp set.w rf1, wp3, 0x3ff0 ; set.w rf1, wp2, 0x0 ; set.w rf1, wp1, 0x0 ; set.w rf1, wp0, 0x0
; CHECK: set.w rf1, wp3, 0x3ff0
; CHECK: set.w rf1, wp2, 0x0
; CHECK: set.w rf1, wp1, 0x0
; CHECK: set.w rf1, wp0, 0x0
; ASM: set.w rf1, wp3, 0x3ff0
; ASM: set.w rf1, wp2, 0x0
; ASM: set.w rf1, wp1, 0x0
; ASM: set.w rf1, wp0, 0x0
set.fo rf2, rf7                  ; @exp fo2fo {rf2}, {rf7}
; CHECK: fo2fo {rf2}, {rf7}
; ASM: fo2fo {rf2}, {rf7}
set.fo rf3, rd9                  ; @exp rd2rf {rf3}, {rd9}
; CHECK: rd2rf {rf3}, {rd9}
; ASM: rd2rf {rf3}, {rd9}
