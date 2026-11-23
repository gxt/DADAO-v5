@@ RUN: echo 'escape cfx_hart, [excp_cause_ip, 1]'   | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=OFFSET
@@ RUN: echo 'escape cfx_hart, [excp_cause_ip, 2]'   | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=OFFSET
@@ RUN: echo 'escape cfx_hart, [excp_cause_ip, 3]'   | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=OFFSET
@@ RUN: echo 'escape cfx_hart, [excp_cause_ip, 5]'   | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=OFFSET
@@ RUN: echo 'escape cfx_hart, [excp_cause_ip, 6]'   | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=OFFSET
@@ RUN: echo 'escape cfx_hart, [excp_cause_ip, 7]'   | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=OFFSET
@@ RUN: echo 'escape cfx_hart, [excp_cause_ip, 12]'   | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=OFFSET
@@ RUN: echo 'escape cfx_hart, [excp_cause_ip, 16]'   | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=OFFSET
@@ RUN: echo 'escape cfx_hart, [excp_cause_ip, -4]'   | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=OFFSET
@@ RUN: echo 'escape cfx_hart, [excp_cause_ip, 524288]' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=OFFSET
@@ RUN: echo 'escape cfx_hart, [excp_cause_ip, sym]'  | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=NONCONST
@@ RUN: echo 'escape cfx_hart, [rb0, 8]'              | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=BASE

@@ m18-llvm-001 反例：escape 帧选择位的**汇编层拒绝**路径。
@@
@@ Toolchain-01 §2.4/§5：汇编层 `imms20` 只接受 {0, 4, 8}。其余值 MUST 硬报错
@@ （非零退出），且不得当成「%4==0 就放行」：1/2/3 是 cg9+偏移组合或非字对齐，
@@ 5/6/7/12/16 会落到 imms18[17:2] 非零 / imms18=3 的架构 ILLI 区。
@@ `8` 本身是**合法**正向值（见 cfx2-escape-frame.s），此处只列非法值。

@@ OFFSET: escape offset must be 0, 4 or 8
@@ NONCONST: escape offset must be a constant
@@ BASE: escape base must be 'excp_cause_ip'
