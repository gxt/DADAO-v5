---
name: omt-dadao-consist
description: Use when reviewing DADAO.wiki or DADAO-v5/wiki specification documents for self-consistency, checking for hard defects that would block LLVM/QEMU/Chipyard/Linux implementation, or preparing ISA specs for production development
---

# DADAO 自洽性审查

## Overview

对 DADAO 规范文档（11 份 .md 文件）进行系统性自洽性审查，采用逐文档流水线检查法覆盖四条开发者路径（LLVM→QEMU→Chipyard→Linux），共 13 类检查项。

## When to Use

- 用户要求"评估自洽性"、"检查 wiki 一致性"、"看看有没有错误"
- 用户准备基于 wiki 开发 LLVM/QEMU/Chipyard/Linux
- 编码表或指令文档有较大变更后

## 审查原则

- **只查硬缺陷**：会导致编码错误、行为错误、定义矛盾的缺陷
- **不查 TODO**：SBI 中的 TODO 不是缺陷
- **代码风格需要一致**：注释措辞、格式偏好

## 逐文档流水线检查法

模拟四类开发者按四种阅读路径逐文档检查：

### 路径 1：LLVM 开发者

1. 读 SimRISC-00 编码表 → 逐条读 SimRISC-01/02/03/04 → 提取每条指令格式和操作数
2. 检查每条指令的格式声明与编码表是否一致
3. 检查每条指令的汇编语法中操作数个数与格式是否匹配
4. 检查指令命名一致性（wpN 无 ww 残留、illi 无 unimp 残留、pmem 无 phymem 残留、setzw/setow/orw/andnw 有点号）
5. 检查删除项是否彻底清除（andi/pushra/popra/orii）
6. 检查每条指令格式后缀（rrrr/rrii/riii 等）与描述文档中的操作数个数是否一致，特别是示例代码中的参数个数

### 路径 2：QEMU 开发者

1. 读 SEE §1 cfxcode 分配表 → §3 寄存器表 → §4 各 cfx 异常表 → §5 异常流程
2. 读 SBI → 每个 cfx 的函数表和 handler 代码
3. 检查异常路由逻辑：FPEXCP 位号一致（1<<32）、跨类别优先级（IALIGN > ILLI/UNDI > MALIGN > 页表 > FPEXCP）
4. 检查 cfx mask 检查点守卫完整（步骤 1/3/4/escape 步骤 0 均有 `!= inner_cfx_code`）
5. 检查伪代码与文本描述一致（步骤 1 路由、步骤 3/4 ILLI 重定向到 monitor、步骤 5 pending）
6. 检查 pending 引用统一为 `excp_pending`

### 路径 3：Linux 内核开发者

1. 读 ABI 调用约定 → 读 SBI 系统调用接口
2. 检查 SBI 各函数入参/出参是否清晰
3. 检查函数表 immu18 编号与 dispatch 代码 breq 链一致
4. 检查各 cfx 初始化代码 clear mask 位 = cfxcode

### 路径 4：Chipyard 开发者

1. 逐张 SEE 寄存器表检查 cg/rc 是否连续
2. 检查每张表列完整（cg/rc/名称/regname/初始值/访问/说明）
3. 检查初始值 `—` 项是否合理（仅 RO 硬件设定或保留行）
4. 检查计数文本与表列匹配（如"6 个寄存器"但表有 7 行）

## 13 类检查清单

### 1. 指令编码完整性
每条指令格式声明与编码表一致、格式后缀补全、删除项清零

### 2. 命名一致性
bpN/brrr/brri/shlu/shrs/shru/extz/exts/wpN/illi/pmem/setrd/setrb/setrf（无点号形式）无旧名残留

### 3. 异常路由自洽性
FPEXCP 位号、优先级、cfx mask 守卫、伪代码/文本一致

### 4. 异常原因表完整性
所有 cfx 的 excp_cause_info 列有值、不可屏蔽标记正确

### 5. 寄存器定义完整性
表列完整、cg/rc 无冲突、初始值合理

### 6. 寄存器计数匹配
描述文字中的寄存器个数与表格行数一致

### 7. SBI 接口一致性
函数表编号与 dispatch 一致、入参/出参与 SEE 匹配

### 8. SBI 初始化代码正确性
各 cfx 的 clear mask 位 = cfxcode

### 9. 指令语义完整性
每条指令的 size 后缀行为明确（高位填充规则）、ext.hd 约束完整、除法规则完整

### 10. 跨文档引用一致性
SEE↔SBI、HEE↔HBI、AEE↔ABI 配对文档定义匹配、编码格式交叉引用一致

### 11. 版本号一致性
各组件对版本一致、GET_VERSION 返回值正确

### 12. 代码块闭合
所有 ``` 配对正确

### 13. 特权模型一致性
SimRISC-04 与 SEE 对 cfx 指令的 user/jail 模式可执行性一致

## 执行流程

1. 读取全部 11 个 .md 文件
2. 按四条路径和 13 类清单逐一核查
3. 只输出发现的硬缺陷，每项标注文件名、行号、原文、严重程度
4. 不输出"通过"项
