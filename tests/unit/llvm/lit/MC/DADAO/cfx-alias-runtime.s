@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t.o
@@ RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t.o | %FileCheck %s --check-prefix=DEFAULT
@@ RUN: echo '# format=1' > %t.table
@@ RUN: echo 'scalar cfx_umon 0 canonical' >> %t.table
@@ RUN: echo 'reg cfx_renamed_hart_cycle 15 8 2 1 canonical' >> %t.table
@@ RUN: env DADAO_CFX_ALIAS_FILE=%t.table %llvm_objdump -d --triple=dadao-unknown-elf %t.o | %FileCheck %s --check-prefix=RENAMED
@@ RUN: echo 'cfx2rd cfx_renamed_hart_cycle, rd7' | env DADAO_CFX_ALIAS_FILE=%t.table %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o %t.renamed.o
@@ RUN: env DADAO_CFX_ALIAS_FILE=%t.table %llvm_objdump -d --triple=dadao-unknown-elf %t.renamed.o | %FileCheck %s --check-prefix=RENAMED-ASM
@@ RUN: echo 'cfx2rd cfx_hart_cycle, rd7' | env DADAO_CFX_ALIAS_FILE=%t.table %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=OLDNAME
@@ RUN: echo 'trap cfx_umon, 5' | env DADAO_CFX_ALIAS_FILE=%t.none %llvm_mc --triple=dadao-unknown-elf --dadao-cfx-alias=%t.table -filetype=obj -o %t.opt.o
@@ RUN: echo 'trap cfx_umon, 0' | env DADAO_CFX_ALIAS_FILE=%t.none %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=NOTABLE-ASM
@@ RUN: echo 'trap cfx0, 0' | env DADAO_CFX_ALIAS_FILE=%t.none %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o %t.naked.o
@@ RUN: env DADAO_CFX_ALIAS_FILE=%t.none %llvm_objdump -d --triple=dadao-unknown-elf %t.naked.o | %FileCheck %s --check-prefix=NOTABLE-OBJ

@@ LLVM-135t：cfx 别名是**运行时数据**（`share/dadao/cfx-aliases.txt`），
@@ 汇编器（名字 -> 编码）与 MCInstPrinter（编码 -> 名字）共用同一张表。
@@
@@ 本用例证三件事（**均不重建 LLVM**，同一二进制只换数据文件）：
@@   1. 默认表（安装根 `<exe>/../share/dadao/`）：名字汇编 + 名字反汇编；
@@   2. `DADAO_CFX_ALIAS_FILE` 指向改名表：反汇编立即打印新名、汇编接受新名、
@@      旧名不再被接受；显式 `--dadao-cfx-alias=` 优先于环境变量；
@@   3. 表缺失：**汇编用名字 ⇒ 非零 + 明确报错**；**反汇编 ⇒ 裸回退 `cfx<HA>` 且 exit 0**。

@@ --- 1. 默认表：%s 用名字汇编，反汇编回名字 ---
@@ DEFAULT: cfx2rd cfx_hart_cycle, rd1
@@ DEFAULT: trap cfx_umon, 0
cfx2rd cfx_hart_cycle, rd1
trap cfx_umon, 0

@@ --- 2a. 改名表（cfx_hart_cycle -> cfx_renamed_hart_cycle）：同一 .o 打印新名 ---
@@ RENAMED: cfx2rd cfx_renamed_hart_cycle, rd1
@@ RENAMED-NOT: cfx2rd cfx_hart_cycle,
@@ RENAMED: trap cfx_umon, 0

@@ --- 2b. 改名表：新名可汇编，反汇编回新名 ---
@@ RENAMED-ASM: cfx2rd cfx_renamed_hart_cycle, rd7

@@ --- 2c. 改名表：旧名（表里已无）不再是合法别名 ⇒ 汇编硬报错 ---
@@ OLDNAME: error:

@@ --- 2d. 显式 --dadao-cfx-alias= 优先于 DADAO_CFX_ALIAS_FILE（后者指向不存在的文件） ---
@@ （RUN 行成功即证明；见上）

@@ --- 3a. 缺表 + 用名字：汇编非零退出并给出明确原因 ---
@@ NOTABLE-ASM: error: cannot resolve 'cfx_umon':

@@ --- 3b. 缺表 + 反汇编：裸回退 `cfx<HA>`，exit 0 ---
@@ NOTABLE-OBJ: trap cfx0, 0
@@ NOTABLE-OBJ-NOT: trap cfx_umon
