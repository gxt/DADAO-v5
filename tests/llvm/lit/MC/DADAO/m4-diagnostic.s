; UNSUPPORTED: true
; RUN: echo 'add.si rd8, 131072'      | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=RANGE
; RUN: echo 'cmp.ui rd8, rd9, 4096'   | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=UI
; RUN: echo 'jump [rb0, 6]'           | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ALIGN
; RUN: echo 'br.eq {rd8, rd0}?, [rb0, 6]' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ALIGN
; RUN: echo 'ret rd0, 5'              | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=RD0NZ
; RUN: echo '#include <x>'            | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=HASH

; M4 L1 向量：诊断（TESTCASES-029t）。
; `spec/Toolchain-01 §9`（ADR-0013 D3/D9）：
;  - 立即数越界 MUST 报错（非静默环绕）：`imms18`/`immu12` 范围见
;    `contract-asm-list.md`「立即数范围速查」；
;  - 地址类立即数须 `%4==0`（§2.4，字节偏移右移 2 位写入编码）；
;  - `ret rd0, 非0` 违规（opcodes.yaml `ret_riii_ra` legality）；
;  - `#` 为 C 预处理器指令符，纯汇编无条件非法（`AllowAdditionalComments=false`）。
; oracle 独立校验「确实违反」再由向量标注 token；范围/对齐均从
; `contracts/opcodes.yaml` 的字段位宽独立重算。
;
; @category diagnostic
; RANGE: immediate out of range
; UI: immediate out of range
; ALIGN: must be a multiple of 4 bytes
; RD0NZ: error
; HASH: error

add.si rd8, 131072                 ; @err imms18
cmp.ui rd8, rd9, 4096              ; @err immu12
jump [rb0, 6]                      ; @err align4
br.eq {rd8, rd0}?, [rb0, 6]        ; @err align4
ret rd0, 5                         ; @err rd0-nonzero
# not a comment                     ; @err illegal-token
