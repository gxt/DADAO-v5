@@ RUN: echo 'escape cfx_umon, 0'                  | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=SECOND
@@ RUN: echo 'escape cfx_umon, 4'                  | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=SECOND
@@ RUN: echo 'escape cfx_umon, 8'                  | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=SECOND
@@ RUN: echo 'escape cfx_umon, [excp_cause_ip, 0]' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=SECOND
@@ RUN: echo 'escape cfx_hart, [excp_cause_ip, 4]' | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=SECOND
@@ RUN: echo 'escape cfx0, [excp_cause_ip, 8]'     | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=SECOND
@@ RUN: echo 'escape cfx_umon, sym'                | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=SECOND
@@ RUN: echo 'escape cfx_umon 4'                   | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=TRAILING

@@ m18-llvm-002 反例：`escape` 只接受 `cfxHA` 一个操作数（SimRISC-11 §3 /
@@ DADAO-12 §5.1，m18-spec-007）。任何第二个操作数——旧的 `0/4/8` 立即数或
@@ `[excp_cause_ip, …]` 形式——MUST 硬报错（非零退出），并提示改用
@@ `escape cfxHA`、返回点写 `cg5 rc10`。不得静默忽略以维持旧二进制兼容
@@ （旧的 +0/+4 与 cg9 帧选择编码已作废）。
@@
@@ 不带逗号的尾随记号同样 MUST 拒绝（不得当作第二个操作数静默吞掉）。

@@ SECOND: escape takes no second operand; use 'escape cfxHA' and set the return point with 'cg5 rc10'
@@ TRAILING: unexpected token after 'escape cfxHA'
