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

; RUN 行所需的 FileCheck 模式：`llvm-objdump -s --section=.text` 的完整
; `.text` 字节（大端）。与各 `@dir` 的独立派生字节一致；`.dd.o64 ext` 为
; 未解析的 `R_DADAO_ABS48` 重定位，其字段在目标文件中预置为 0。
; CHECK: 12123411 22334411 22334455 667788ff
; CHECK: ff000000 07000000 13000000 00000000
; CHECK: 0020 00
