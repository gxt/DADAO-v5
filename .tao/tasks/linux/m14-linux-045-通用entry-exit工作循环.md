# m14-linux-045: 通用 entry/exit 工作循环（`TIF_*` 消费 + syscall enter/exit + irqentry 接线）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-044`（`select GENERIC_IRQ_ENTRY` 必须先编进来）；`m14-linux-027` 拆出本任务
**可并行分片**：否（linux 单写者）
**预估**：4–6 h
**档位**：大改
**状态**：待开始

## 背景（盘点结论，用户 2026-11-20 批准）

五份只读盘点（037/039/040/041/042）**独立指向同一根因**：

- `arch_do_signal_or_restart` 在 `arch/dadao` **全树无调用点**（generic 在 `kernel/entry/common.c:13` 是 `__weak` 空桩、唯一调用点 `:66` 不可达）⇒ **不报链接错，静默不投递**；
- `TIF_SIGPENDING` / `TIF_NEED_RESCHED` / `_TIF_WORK_MASK` **只有定义与注释、无消费者**（`039` 实测）；
- `syscall_enter_from_user_mode` / `syscall_exit_to_user_mode` 在 `arch/dadao` 引用 **0**（`037` #13，10 个工作项全为 0）；
- `syscall_work` 字段是死代码（只有播种清零，`040` ①-22）。

后果：信号、`SIGCHLD`、`exit_group`、抢占、audit/ptrace/seccomp **静默失效**。

## 要做

1. **返回用户态前的工作循环**：在用户态返回路径上按上游形态消费 `_TIF_WORK_MASK`（至少 `TIF_NEED_RESCHED`、`TIF_SIGPENDING`、`TIF_NOTIFY_RESUME`），逐位判、逐位清；
2. **syscall enter/exit**：接上 `syscall_enter_from_user_mode()` / `syscall_exit_to_user_mode()`（或按本端口分发结构给出等价实现，**必须在任务书说明为什么不能直接用通用函数**）；
3. **`arch_do_signal_or_restart`** 接线：本任务只负责**调用到它**；信号的实际投递与帧由 `m14-linux-046` 实现（未实现前 `get_signal()` 返回无信号即返回）；
4. **`irqentry_*`**：`044` 选上 `GENERIC_IRQ_ENTRY` 后，在异步入口接 `irqentry_enter_*`/`irqentry_exit_*` 或 `irq_enter_rcu`/`irq_exit_rcu` + `set_irq_regs`；
5. **`user_mode()`**：根因是 `struct pt_regs` 无模式位（`039`/`042`）。**方案二选一并写清理由**：① 按分发路由事实判定（umon 交接 = 用户态，035 已用此法）；② 新增 `prev_mode` 帧位（**属帧布局/契约变更，须用户裁定后才可做**）。

## 验收（逐条贴真实 rc）

1. **抢占生效**：`TIF_NEED_RESCHED` 置位后能触发 `schedule()`（给实测：长循环任务被切走）；
2. **`TIF_SIGPENDING` 可达 `get_signal()`**：置位后能走到信号分发点（此时无信号帧，允许「无 handler ⇒ `do_exit`」）；
3. **`in_hardirq()`/`get_irq_regs()` 在中断内正确**（配合 044 已选的 `GENERIC_IRQ_ENTRY`）；
4. **不回归**：k0 130 / k1 112 / k2 170 / k3 263 / k4 五探针 / k5（syscall 104 / clone 97 / futex 174）；
5. **可达 FAIL ≥2 路**：① 去掉 `TIF_NEED_RESCHED` 消费 ⇒ 第 1 条红；② 去掉 `arch_do_signal_or_restart` 调用 ⇒ 第 2 条红（`cp`+md5 还原 + 重建）；
6. `check-patch-tree` linux 段 0 问题；合并态（`Process-07 §5a`）。

## 完成区

（待填）
