@@ RUN: echo 'escape cfx0, [excp_cause_ip, 2]'       | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=SECOND
@@ RUN: echo 'escape cfx0, [excp_cause_ip, 6]'       | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=SECOND
@@ RUN: echo 'escape cfx0, [excp_cause_ip, 12]'      | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=SECOND
@@ RUN: echo 'escape cfx0, [excp_cause_ip, -4]'      | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=SECOND
@@ RUN: echo 'escape cfx0, [excp_cause_ip, 524288]'  | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=SECOND
@@ RUN: echo 'escape cfx0, [excp_cause_ip, sym]'     | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=SECOND
@@ RUN: echo 'escape cfx0, [rb0, 4]'                 | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=SECOND
@@ RUN: echo 'trap cfx_smon, 262144'                 | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=IMM
@@ RUN: echo 'trap 2, 1'                             | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=OPERAND
@@ RUN: echo 'cfx2rd cfx0, 5, 3, rd2'                | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=OPERAND
@@ RUN: echo 'cfx2rd cfx_pmem_start, rd2'              | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=SUBSCRIPT
@@ RUN: echo 'cfx2rd cfx_pmem_start[64], rd2'          | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=SUBSCRIPT
@@ RUN: echo 'cfx2rd cfx_nosuch, rd2'                | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=OPERAND

@@ LLVM-060t / m18-llvm-002 反例：trap/escape/cfx2rd/cfx2rc 的非法书写 MUST
@@ 硬报错（非零退出）。
@@ escape 只接受 `cfxHA` 一个操作数（m18-spec-007）：任何旧的偏移/基址写法
@@ （`[excp_cause_ip, N]`、非常量、错基址）都落入「第二操作数」拒绝路径。
@@ cfxha/cg/rc 只接受 `cfx<ha>`/`cfx_<name>`/`cg<N>`/`rc<N>` 记号，裸数字 MUST 拒绝；
@@ 数组寄存器（ADR-0017 D10）MUST 带单下标且下标在别名表名称列范围内。

@@ SECOND: escape takes no second operand; use 'escape cfxHA' and set the return point with 'cg5 rc10'
@@ IMM: immediate out of range for 'trap'
@@ OPERAND: invalid operand for instruction
@@ SUBSCRIPT: cfx register
