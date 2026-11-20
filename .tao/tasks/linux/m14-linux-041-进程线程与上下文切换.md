# m14-linux-041: 进程/线程与上下文切换 与主流 ISA 差异盘点（只读盘点）

**模块**：linux
**项目里程碑**：M14
**依赖**：无（**只读分析**：不占 linux 写者锁，可与在跑任务并行）
**可并行分片**：是（盘点任务彼此独立、只读）
**预估**：2–3 h
**档位**：小改（只读 + 写结论；不改任何代码）
**状态**：待开始

## 背景（用户 2026-11-20 裁定）

> 「M14，尽量按主流 ISA 的标准流程走」
> 「M14 中增加专门的任务，或者多个任务，分子系统把已经实现的内核代码，逐个和主流 isa 的实现进行对比，找出差异」
> 「是否立刻整改，我来定」

第一批（`m14-linux-036`–`040`，mm/syscall/时间/信号/Kconfig）已交付并形成格式基线：**每条带两侧 `文件:行号` + 影响面 + P0/P1/P2**，覆盖数**现场派生**，抽查用 `sed -n` 贴原文。

## 范围（**只读**，不改代码）

对比对象：仓库 Linux 源树的 `arch/riscv`（主）与 `arch/arm64`（参照）。
本任务只覆盖：`arch/dadao/kernel/process.c`（`copy_thread`/`__switch_to`/`ret_from_fork`/`start_thread`）、`include/asm/processor.h`、`switch_to` 宏、`thread_info`、`kernel/fork` 的 arch 钩子、`exec` 相关；对比 `arch/riscv/kernel/process.c`（主）与 `arch/arm64/kernel/process.c`（参照）。重点：切栈/帧保存范围、`TIF_*` 工作位、`flush_thread`/`release_thread`、`arch_dup_task_struct`、`start_thread` 的 PC/SP 约定。

## 要做

逐个 hook / 机制判定属于哪一类，并给证据：

1. **缺失 hook**：上游有、我们没有；
2. **语义不符**：有但行为不同（返回码 / 副作用 / 加锁 / 顺序 / 何时切栈）；
3. **旁路 vs 通用**：我们自造实现，上游走通用 `kernel/`、`mm/` 路径；
4. **Kconfig 缺口**：缺 `select` / `depends on` 导致通用代码没编进来。

**每条格式**：`arch/dadao/<file>:<line>` ↔ `arch/riscv/<file>:<line>`（必要时补 `arch/arm64`）/ 影响面 / 优先级（**P0** 阻塞在跑任务；**P1** 影响正确性；**P2** 仅形态差异）。

## 验收

1. 结论写进本任务书「盘点结论」段（≤80 行），**每条带两侧 `文件:行号`**；
2. **覆盖现场派生**：列清检查了哪些 hook / 机制及条数（不写死），并写清枚举口径（命令）；
3. **抽查 ≥5 条**：用 `sed -n '<行>p'` 贴两侧原文，**不许凭记忆**；
4. **不改任何代码**：用 `git show --name-only HEAD` 与 `git status -uall` 判「只改了本任务书」（**不要用裸 `git diff`/`git status` 计数**——提交后会变空，`m14-linux-036` 已踩过）；
5. 不占写者锁、不重建、不跑仿真。

## 完成区

（待填）
