; RUN: echo '.word 0x1234'   | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=WORD
; RUN: echo '.octa 0x1'      | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=OCTA
; RUN: echo '.byte 1'        | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=GAS
; RUN: echo '.short 1'       | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=GAS
; RUN: echo '.long 1'        | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=GAS
; RUN: echo '.quad 1'        | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=GAS
; RUN: echo '.align 3'       | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ALIGN
; RUN: echo '.dd.b08 0x1234' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=RANGE
; RUN: echo '.dd.t32 ext'    | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=NARROW

; M4 L1 向量：指导符拒绝（TESTCASES-029t）。
; `spec/Toolchain-01 §7` + `contract-asm §7/§9`：
;  - GAS `.word` 非 DADAO 指导符 → unknown directive；
;  - GAS `.octa`（16 字节）与 DADAO octa（8 字节）不同 → MUST NOT 使用其语义 →
;    unsupported directive（改用 `.dd.o64`）；
;  - GAS `.byte`/`.short`/`.long`/`.quad`（GAS 数据指示符）→ unsupported directive
;    （唯一数据指示符为 `.dd.b08/.w16/.t32/.o64`，`§7.1`）；
;  - `.align`（字节数语义）→ unsupported directive（唯一对齐指示符 `.p2align N`，`§7.2`）；
;  - 值超宽 → 报错（不静默环绕）；
;  - `.dd.b08/w16/t32` 不接受可重定位操作数（地址需 8 字节字段）。
; oracle 依 spec 独立分类，不是转述 llvm-mc 文本。
;
; @category directive
; WORD: unknown directive
; OCTA: unsupported directive
; GAS: unsupported directive
; ALIGN: unsupported directive '.align'
; RANGE: out of range
; NARROW: relocatable operand in

.word 0x1234        ; @dirrej unknown
.octa 0x1           ; @dirrej unsupported
.byte 1             ; @dirrej unsupported
.short 1            ; @dirrej unsupported
.long 1             ; @dirrej unsupported
.quad 1             ; @dirrej unsupported
.align 3            ; @dirrej unsupported
.dd.b08 0x1234      ; @dirrej range
.dd.t32 ext         ; @dirrej reloc-narrow
