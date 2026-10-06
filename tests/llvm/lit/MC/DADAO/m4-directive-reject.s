; UNSUPPORTED: true
; RUN: echo '.word 0x1234'   | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=WORD
; RUN: echo '.octa 0x1'      | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=OCTA
; RUN: echo '.dd.b08 0x1234' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=RANGE
; RUN: echo '.dd.t32 ext'    | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=NARROW

; M4 L1 向量：指导符拒绝（TESTCASES-029t）。
; `spec/Toolchain-01 §7` + `contract-asm §7/§9`：
;  - GAS `.word` 非 DADAO 指导符 → unknown directive；
;  - GAS `.octa`（16 字节）与 DADAO octa（8 字节）不同 → MUST NOT 使用其语义 →
;    unsupported directive（改用 `.dd.o64`）；
;  - 值超宽 → 报错（不静默环绕）；
;  - `.dd.b08/w16/t32` 不接受可重定位操作数（地址需 8 字节字段）。
; oracle 依 spec 独立分类，不是转述 llvm-mc 文本。
;
; @category directive
; WORD: unknown directive
; OCTA: unsupported directive
; RANGE: out of range
; NARROW: relocatable operand in

.word 0x1234        ; @dirrej unknown
.octa 0x1           ; @dirrej unsupported
.dd.b08 0x1234      ; @dirrej range
.dd.t32 ext         ; @dirrej reloc-narrow
