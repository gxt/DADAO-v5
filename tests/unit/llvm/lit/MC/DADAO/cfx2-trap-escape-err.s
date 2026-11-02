@@ RUN: echo 'escape cfx0, [excp_cause_ip, 2]'       | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=OFFSET
@@ RUN: echo 'escape cfx0, [excp_cause_ip, 6]'       | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=OFFSET
@@ RUN: echo 'escape cfx0, [excp_cause_ip, 8]'       | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=OFFSET
@@ RUN: echo 'escape cfx0, [excp_cause_ip, -4]'      | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=OFFSET
@@ RUN: echo 'escape cfx0, [excp_cause_ip, 524288]'  | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=OFFSET
@@ RUN: echo 'escape cfx0, [excp_cause_ip, sym]'     | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=NONCONST
@@ RUN: echo 'escape cfx0, [rb0, 4]'                 | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=BASE
@@ RUN: echo 'trap cfx_smon, 262144'                 | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=IMM
@@ RUN: echo 'trap 2, 1'                             | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=OPERAND
@@ RUN: echo 'cfx2rd cfx0, 5, 3, rd2'                | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=OPERAND
@@ RUN: echo 'cfx2rd cfx_pmem_start, rd2'              | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=SUBSCRIPT
@@ RUN: echo 'cfx2rd cfx_pmem_start[64], rd2'          | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=SUBSCRIPT
@@ RUN: echo 'cfx2rd cfx_nosuch, rd2'                | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=OPERAND

@@ LLVM-060t 反例：trap/escape/cfx2rd/cfx2rc 的非法书写 MUST 硬报错（非零退出）。
@@ escape 汇编层 imms20 须为常量且只允许 0 或 4（Toolchain-01 §3.2）；
@@ cfxha/cg/rc 只接受 `cfx<ha>`/`cfx_<name>`/`cg<N>`/`rc<N>` 记号，裸数字 MUST 拒绝；
@@ 数组寄存器（ADR-0017 D10）MUST 带单下标且下标在别名表名称列范围内。

@@ OFFSET: escape offset must be 0 or 4
@@ NONCONST: escape offset must be a constant
@@ BASE: escape base must be 'excp_cause_ip'
@@ IMM: immediate out of range for 'trap'
@@ OPERAND: invalid operand for instruction
@@ SUBSCRIPT: cfx register
