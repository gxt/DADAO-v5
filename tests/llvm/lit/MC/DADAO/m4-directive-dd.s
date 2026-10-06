; UNSUPPORTED: true
; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t.o
; RUN: %llvm_objdump -s --section=.text %t.o | %FileCheck %s

; M4 L1 向量：`.dd.*` 数据指导符（TESTCASES-029t）。
; `spec/Toolchain-01 §7`（DADAO-11 §汇编兼容性）：`.dd.b08`/`.dd.w16`/`.dd.t32`/
; `.dd.o64` = 1/2/4/8 字节；`contract-elf §1.1`：数据大端序。
; 常量表达式按 §2.4 求值；`.dd.o64 <sym>` 为 48 位地址 → `R_DADAO_ABS48`
; 重定位（`contract-elf §2.2`，`ADR-0019 D2`）。
; oracle 从 spec §7 宽度 + 大端规则独立重算字节；符号 → 检查 `ABS48`。
;
; @category directive

.dd.b08 0x12                      ; @dir 12
.dd.w16 0x1234                    ; @dir 1234
.dd.t32 0x11223344                ; @dir 11223344
.dd.o64 0x1122334455667788        ; @dir 1122334455667788

; 负值按字段宽度补码（大端）
.dd.w16 -1                        ; @dir ffff

; 常量表达式（§2.4）
.dd.t32 1+2*3                     ; @dir 00000007
.dd.t32 (1 << 4) | 3              ; @dir 00000013

; 符号 → 48 位绝对地址重定位
.dd.o64 ext                       ; @dir ABS48
