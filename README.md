# DADAO for SimRISC 0.5.1

## 核心任务

基于 `wiki/` 目录下 11 份规范文档，通过系统性自洽性审查（累计修复 180+ 项缺陷），使文档达到可支撑 LLVM 编译器、QEMU 模拟器、Chipyard 仿真器和 Linux 内核开发的完备程度。

## 最终成果

经过多轮审查，当前 11 份文档零硬缺陷，关键修复包括：

- **指令编码**：brrr/brri 位掩码格式新增、编码表三次重构、所有格式后缀补全、andi/divs-rrrr/divu-rrrr/orii 等删除、命名统一（bitmask→bit position / ww→wpN / phymem→pmem / unimp→illi）
- **异常系统**：IALIGN 新增、FPEXCP 移至 1<<32、异常优先级（IALIGN>ILLI>MALIGN>页表>FPEXCP）、精确异常统一、cfx mask 六类型 per-mode 守卫、步骤 3/4 ILLI 重定向到 monitor
- **寄存器**：pending 统一为 cg5 rc5 excp_pending、timer/uart/power 专有 pending 删除、rd0/rb0 行为 AEE/SimRISC 统一、cg 编号修正
- **SBI**：PTBR/PTHI/PAHI 跳转表 rb3 中转修改、ALLOC_PAGE 返回值统一、ptw handler 四处 TODO 替换实现
- **伪代码**：异常进入步骤 1/3/4/5 语义修正、escape 退出步骤 0 cfx mask 检查、自身 cfxcode 忽略守卫

## 当前版本号

- AEE：0.9.2
- ABI：0.9.2
- SEE：0.7.1
- SBI：0.7.1
- HEE：0.1.2
- HBI：0.1.2
- SimRISC：0.5.1

## 开发下一步

1. **LLVM**：基于 `SimRISC-00` 编码表和 `SimRISC-01~04` 指令定义编写 TableGen `.td` 文件，注意 brrr/brri 格式的 bpN 参数
2. **QEMU**：基于 `SEE §5` 异常流程伪代码实现译码和异常路由，基于 `SBI` 实现各 cfx handler
3. **Chipyard**：基于 `SEE §3-4` 寄存器表逐张实现硬件模块，特别关注 cfx mask 六类型多模式守卫
4. **Linux**：基于 `SBI` 函数表编写内核 SBI 调用包装，基于 `AEE/ABI` 编写用户态库
