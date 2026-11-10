# m12-chipyard-021: hmon 按「最小保存-跳转」算法重做 + power 写默认返回地址

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m12-chipyard-008`（同一组件单写者，须串行）；`m12-chipyard-019` 已合入
**可并行分片**：否（单核实现，单写者）
**状态**：待开始

## 用户裁定（2026-11-11，原话）

> 「hmon本身不应该产生退出码，hmon在测试环境下的代码应该是：保存两个临时寄存器，读取excp cause id/excp cause ip/excp cause info三个寄存器的内容，分别存储在hmon的sram的固定位置，然后从sram的另一固定位置取出异常返回地址（由测试框架程序事先写好），将其存入excp cause ip，然后恢复那两个临时寄存器，然后escape即可；余下的应该hmon测试框架程序要处理的事情。」
> 追加：「放在低地址；紧跟着代码区后面，8字节对齐」「只需要一个临时寄存器，rd63」「跳转到 0x30」「ld/st 支持负立即数」「刚才的代码里忘了写恢复 rd63 的指令了」

完整算法见 `.tao/knowledge/refs/m12-006-cycle-design.md §11`。

## 背景

`m12-chipyard-019` 的 hmon 当前做了三件新设计里**不应有**的事：

- CFXTRAP 的 magic 校验（`hmon_cfxtrap` 分支，失败则 park）
- IALIGN 特判（把 `excp_cause_ip` 改成 `(ip & ~3) + 4`）
- 其余四类统一 `escape +4`（策略判断）

新设计下 hmon **只做「保存现场 → 跳到框架指定地址」**，所有策略（跳过/重入/退出码）归测试框架。

## 目标

1. **重写 `tests/shared/bootrom/tiny/hmon.S`** 为 `§11` 的 6 步序列：
   - 入口 `0x00`：`st.o rd63, [rb0, 8]`
   - 入口 `0x04`：`jump [rb0, 0x30]`
   - `0x30` 起：读 `cg5 rc2/rc3/rc4` 分别存 `0x10/0x18/0x20`；从 `0x28` 取返回地址写入 `cg5 rc3`；从 `0x08` 恢复 `rd63`；`escape cfx_hmon, [excp_cause_ip, 0]`
   - **删除**：magic 校验、IALIGN 特判、`+4` 策略、park 循环
2. **power stub**：`trap cfx_hmon` **之前**把默认返回地址写入 `hmon_base + 0x28`
   - 默认值 = power stub 中 `trap` 的下一条指令地址（即原 `+4` 语义），保证 `CFXTRAP` 移交仍返回 stub
   - 同时约定「框架未覆盖时的 abort 兜底」：若框架从未写 `0x28`，power 的默认值仍然有效（不会跳飞）
3. **布局常量化**：`tests/arch/hmon/tiny_hmon_layout.inc` 与构建器统一 `0x08/0x10/0x18/0x20/0x28/0x30`
4. **同步受影响的断言**：
   - `tests/arch/hmon/expected.yaml`（019 时代的 handler 行为：magic park、IALIGN 改写、+4）
   - `tools/gem5/check_tiny_hmon.py`（同上）
   - QEMU 侧若有对应断言，同步
5. **回归**：273 例逐字节一致；Tiny 44/44。

## 非范围

- **不做** `tests/inst` 的 fault 类期望值迁移（退出码口径）——另立 testcases 任务
- 不改 `cfx` 寄存器语义（019 已定）
- 不改 FP/访存/控制流

## 验收标准

1. **handler 行为**：构造用例证明「异常后跳到 `0x28` 里写的地址」——框架写 A 地址就跳 A、写 B 就跳 B；**hmon 不再做任何 +4/对齐/magic 判断**
2. **三个现场值**：`0x10/0x18/0x20` 与 `cg5 rc2/rc3/rc4` 逐值相等（构造五类异常各 1 例）
3. **`rd63` 恢复**：异常返回后 `rd63` 与进入前相同（用例断言）
4. **默认返回地址**：power 写入的值 = stub 中 `trap` 之后那条指令地址；`CFXTRAP` 移交闭环不回归
5. **删除项确认**：`grep` 无 magic 校验/park/IALIGN 特判残留代码（文档注释可保留说明）
6. 273 例 md5 不变；Tiny 44/44；Verilator 构建 rc=0（主控机）
7. `apply-series`/`check-source-state`/`check-patch-tree`（chipyard）/L1/L2 rc=0
8. 一键证据脚本（含可达 FAIL 注入）
9. 完成区 ≤30 行、无运行期路径；**「修改文件」与 `git status` 逐项对账**（`ISS-377`）

## 说明

- 必须在独立 `git worktree` 内作业（`ISS-368`）；不占用 207/208。
- 组件单写者：等 `m12-chipyard-008` 合并后再开工。
- 随本任务同步更新 `tests/arch/hmon/` 与 gem5 checker，属**必要连带**（不是越界），须在完成区列明。
- 若发现「`rd63` 被应用当作活值使用」的场景（跨异常保留），**停下登记**——需要与框架约定。

## 硬约束（子代理必读）

1. 必须在独立 `git worktree` 内作业（分支名 = 任务号），禁改主工作树。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；「修改文件」须与 `git status` 对账。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需要裁定写进任务书并返回主会话。
6. 复杂命令输出留存运行期日志目录。
7. 一键证据脚本；反例注入须「注入→FAIL→还原（`cp`+md5）→回绿」。
8. 不得写入未经主会话转达的用户裁定；自定事项写「自决」。
9. 命令作用域 = workdir（仓库根），用相对路径。

## 审阅记录

（待填）
