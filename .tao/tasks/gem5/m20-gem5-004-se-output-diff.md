# m20-gem5-004: gem5 SE 输出差异（`neural` / `pcompress2`）定位与修复（ISS-362 + ISS-367）

**模块**：gem5
**项目里程碑**：M20
**依赖**：`m16-gem5-026` 完成后再派（同组件写者）；可与 `m20-gem5-003` 串行
**可并行分片**：否（同改 gem5 SE 输出路径；两例合并处理）
**预估**：4–8 h（`pcompress2` 单例历史约 4408 s，长跑另计）
**档位**：大改（复核 ≤60 min）
**状态**：待开始

## 背景（M20 分诊，2026-11-25）

`ISS-362`/`ISS-367` 是同类问题：gem5 SE 跑完但输出与参考不同，qemu 侧通过。
- `ISS-362`：dynamic `MultiSource/Benchmarks/FreeBench/neural`，输出长度相同
  （358 B vs 358 B）但内容不同，首行 `Matrix size is 20x28` 一致。
- `ISS-367`：static `MultiSource/Benchmarks/FreeBench/pcompress2`，gem5 约
  4408 s 跑完、exit=0，但输出与参考不同，qemu 通过，比值 404×。

两例疑似同源（浮点舍入/格式化或 SE 输出通道），合为一个任务定位，避免重复。

## 目标

1. 先取 `neural` 单例（较短）做逐字节 diff，定位首个差异列，再判断是 FP
   语义、printf/格式化还是 SE 输出截断。
2. 期望值以 `neural.reference_output` / 程序语义为 oracle，**不得**用 gem5 或
   qemu 的输出反推；若发现参考输出本身有误，须先登记并停下问主会话。
3. 修复后 `neural` 与 `pcompress2` 输出均与参考逐字节一致（或按契约规定的
   格式差异显式登记 GAP，不得静默放过）。
4. `pcompress2` 单例长跑排节点或主控机空闲窗口；不得与其它 gem5 FS 跑批抢
   资源。

## 验收（逐条贴真实 rc）

1. `neural` 复现：修复前逐字节 diff 非空，给出首个差异列；修复后 `cmp` 为空。
2. `pcompress2` 复现/回归：修复后 `cmp` 为空；给出实际耗时与 rc。
3. 差异归因链：如果是 FP 舍入，引用 `spec/SimRISC-07`/IEEE-754 2019 的对应条；
   如果是格式化/输出，引用 `contract-semihosting` 或 libc 行为；不得只写「改了
   就好」。
4. 至少一条可达 FAIL：回退修复 ⇒ 同一 diff 复现；`cp` + md5 还原后回绿。
5. `check-gem5-decode`、`check-patch-tree` gem5 段 0 problem；长跑日志 + `*_EXIT`。

## 约束

独立 `git worktree`（分支 = `m20-gem5-004`）；不提交 git；只改
`components/gem5/**`、必要测试/探针与本任务书；不改 `spec/`、契约、`Makefile`。
任务书不写构建树/安装树/临时目录路径；证据落在「运行期证据目录内的 `run.sh`」。
