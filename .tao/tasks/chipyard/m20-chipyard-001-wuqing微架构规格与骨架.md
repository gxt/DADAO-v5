# m20-chipyard-001: wuqing 微架构规格与 generator 骨架

**模块**：chipyard
**项目里程碑**：M20
**依赖**：`m16-chipyard-010`（I-Cache）、`m19-chipyard-001`（FPGA 资源实测反推参数）
**可并行分片**：否
**预估**：5–7 天
**档位**：大改
**状态**：待开始

## 背景

`discussing.md` 记：chipyard 侧只有 `WumingTinyConfig`，**`wuqing` 的 RTL 为零**；用户 2026-11-20 定「gem5 Minor 与 wuqing 一起开发、对比验证」，且 **golden = wuming RTL**。本任务**先规格后代码**：规格没定不写 RTL。

## 目标

1. `dadao-wuqing` 微架构规格：流水级、发射宽度、乱序窗口、访存队列、异常精确度；每节标出处或明确「设计选择」；
2. generator 骨架：可 elaborate，可跑 3 条指令（`add.si` / `ld.o` / 分支）；
3. **资源与 Genesys2 预算对账**：445 块 RAMB36，含 cache 256 KiB / 512 KiB 两案（`discussing.md` 的 47%–61% 估算是纸面值，须用 M19 实测校正）。

## 验收（逐条贴真实 rc）

1. FIRRTL 生成 + 仿真跑通 3 条指令；
2. 规格里每个参数都能与资源预算对账（不允许「大约」）；
3. **可达 FAIL ≥2 路**：① 去掉旁路 ⇒ 依赖例结果错/挂死；② 资源估算与综合报告偏差 >20% ⇒ 红；
4. `check-patch-tree` chipyard 段 0 问题、`check-component-changelog` rc=0。

## 约束

独立 `git worktree`；**不提交 git**；不得改动 wuming 现有路径（wuqing 是新增 generator）；术语「寄存器组」；完成区不写具体 `.work/**` 路径。
