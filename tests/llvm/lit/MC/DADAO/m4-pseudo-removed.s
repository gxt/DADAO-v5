; UNSUPPORTED: true
; RUN: echo 'nop'          | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=UNREC
; RUN: echo 'return'       | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=UNREC
; RUN: echo 'not.o rd1, rd2' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=UNREC
; RUN: echo 'neg.o rd1, rd2' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=UNREC
; RUN: echo 'not.b rd1, rd2' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=UNREC
; RUN: echo 'neg.b rd1, rd2' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=UNREC
; RUN: echo 'not.w rd1, rd2' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=UNREC
; RUN: echo 'neg.w rd1, rd2' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=UNREC
; RUN: echo 'not.t rd1, rd2' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=UNREC
; RUN: echo 'neg.t rd1, rd2' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=UNREC

; M4 L1 向量：被删伪指令（TESTCASES-029t）。
; `spec/Toolchain-01 §6.2`（ADR-0013 D11）：`nop`/`return`/`not.{b,w,t,o}`/
; `neg.{b,w,t,o}` 共 10 条**不再实现**，须报 `unrecognized instruction mnemonic`。
; 需要相应功能时直接书写真实指令（`swym 0` / `ret rd0, 0` / `xnor.o` / `sub.sX`）；
; 其**替代功能**向量归 TESTCASES-032t，本文件只测「被删即拒绝」。
; oracle 独立验证：这些助记符不在 `contracts/opcodes.yaml` 且属 spec §6.2 删除集。
;
; @category pseudo
; UNREC: error: unrecognized instruction mnemonic

nop              ; @rej unrecognized
return           ; @rej unrecognized
not.o rd1, rd2   ; @rej unrecognized
not.b rd1, rd2   ; @rej unrecognized
not.w rd1, rd2   ; @rej unrecognized
not.t rd1, rd2   ; @rej unrecognized
neg.o rd1, rd2   ; @rej unrecognized
neg.b rd1, rd2   ; @rej unrecognized
neg.w rd1, rd2   ; @rej unrecognized
neg.t rd1, rd2   ; @rej unrecognized
