# m20-gem5-001: gem5 Minor 接入（访存两阶段 + 块传送微操作 + trace）

**模块**：gem5
**项目里程碑**：M20
**依赖**：`m17-idl-003`（trace 格式与 golden）、`m16-gem5-006`（访存时序）
**可并行分片**：否
**预估**：4–6 天
**档位**：大改
**状态**：待开始

## 背景

`m16-gem5-001` 已记：`TimingSimpleCPU` 未实现 `readMem()`，DADAO 的 `ld/st` 在其上直接 panic ⇒ Minor 必须实现完整的 `initiateAcc`/`completeAcc` 两阶段；`ldm/stm` 要按 `m16-gem5-005` 已定的计拍口径做微操作展开。用户 2026-11-20 定 **golden = wuming RTL**。

## 目标

1. `--cpu-type minor` 可跑 DADAO：访存两阶段、`ldm/stm` 微操作；
2. 逐指令 trace 与 `m17-idl-003` **同格式**（同一个消费方）；
3. 与 wuming RTL 对拍 ≥20 例（同镜像、同内存初始值）。

## 验收（逐条贴真实 rc）

1. 272 镜像子集（≥20）与 wuming 的逐指令 trace 一致（寄存器/内存/异常三类字段都要比）；
2. **可达 FAIL ≥3 路**：① 去掉 `completeAcc` 提交 ⇒ 访存例红；② `ldm` 微操作少一拍 ⇒ 计数红；③ trace 顺序错 ⇒ 比对红；
3. `check-gem5-decode`、`check-wuming-cycles`、`check-patch-tree` gem5 段真实 rc；
4. `--source-state`/补丁导出纪律按 `docs/Process-01`（组件补丁树）。

## 约束

独立 `git worktree`；**不提交 git**；**周期表不搬** Timing 的 264 行（Minor 流水线要重标，另立任务）；术语「寄存器组」；完成区不写具体 `.work/**` 路径。
