# m18-linux-022: 内核异步新模型（掩码归 monitor、源位图、一帧多源）

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-spec-004` + `m18-qemu-005` 合入（替代已作废的 `m18-linux-021`）
**可并行分片**：否（同改 `components/linux`）
**预估**：3–5 h
**档位**：大改（内核异常入口/调度，复核 ≤60 min）
**状态**：待开始
**执行环境**：本地（QEMU system `-M kaiwu-vast`）

> **R2 修订（2026-11-23，ADR-0061）**：`cg9` 为捕获缓冲，入口在关中断窗口搬运到 `task_pt_regs` 后进 `cfx_smon`；smon 按普通系统态处理，嵌套由软件处理；`escape imms18=2` 不再异步返回。本任务按 R2 重写入口/返回/调度，旧 cg9 escape 方案作废。

## 背景

`ADR-0061`：异步源以 cfxha 标识（TIMER 15、PMEM_DMA 32），pending/帧内位同索引；掩码在**当前运行模式 monitor** 的 `cg8 rc1`（`cfx0` umon / `cfx1` jmon / `cfx2` smon / `cfx3` hmon，复位全 1）；`cg9` 七槽，`src_frame`/`src_pending` 只读；同一界面多源**一次捕获**；`cg9` 为捕获缓冲、每次进入覆盖；`escape imms18[1]=1` 不再异步返回（cg9 非返回帧 ⇒ `CFXESC`）；异步**无 cause_info**，细节回源 cfx 读。原 `m18-linux-021` 按旧口径（掩码在 cg9、位 17/18、`cause_id`），已作废。

## 要做

1. **入口**：固定 `cfx_hart cg9 rc5 excp_vector`（supv）；GPR 捕获到 `cfx_hart cg6`（`DADAO_GPR_SAVE`）→ `task_pt_regs`；按 `rc0 prev_run_mode` 判 from_user 并切内核栈（per-hart `dadao_user_stack_top`）。
2. **放行**：内核初始化写 `cfx2 smon cg8 rc1` 的 bit15/bit32 = 0（内核态可被打断策略）；用户态被抢占需要 `cfx0 umon cg8 rc1` 允许对应源——按调度策略设置并在 `task` 切换/用户态入口维护；复位全 1 ⇒ 不写就永远不投递。
3. **一帧多源**：读 `rc3 src_frame` 位图，逐位处理（timer/`dma`）；**一次进入只算一次**（`excp_async_num` 由硬件计），不得按源二次进入。
4. **源细节/ack**：TIMER 读 `cfx_hart cg8 rc5 timer_ctrl`（`ISTATUS`）并重装 `timer_cmp`；PMEM_DMA 读 `cfx_pmem cg15 rc4 dma_status`（W1C）；ack 后 pending 自动落，**不要**写 `src_pending`/`src_frame`。
5. **入口/返回**：关中断窗口内把 `cg9`（`rc0–rc4`）与 GPR 搬到本任务 `task_pt_regs`；随后 `trap cfx_smon`（handoff）在 smon 普通系统态处理/调度；用户返回走 smon/umon 正常路径。**不再使用 `escape imms18=2` 返回异步**；`imms18=2` 按 R2 ⇒ `CFXESC`。smon 内再来的 async 由软件处理嵌套（必要时保存/恢复 cg5）。
6. **调度**：用户态异步走 `irqentry_enter/exit` + return-to-user work loop（`_TIF_NEED_RESCHED`/信号）；内核态异步不调度（`irq_enter_rcu/irq_exit_rcu`）。
7. **探针**：K2 irq/time、K5 异步探针改新口径；`tests/unit/linux/{k2_irq_probe,k2_time_probe}.py` 期望同步；保留可达 FAIL。
8. **抢占可见**：`/proc/uptime` 采样 + 忙循环 + `alarm/SIGALRM` 交叉；500 次启动稳定性。
9. **清理旧常量**：删除内核对 cause 17/18 与 `cg9 rc8–rc12` 掩码的依赖。

## 不做

- 不改 QEMU/RTL/spec（各自任务）；
- 不做多核/IPI；
- 不改 `escape` 编码。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出；
- 不写运行期路径；术语"寄存器组"；失败路径短 timeout（ISS-522）。

## 验证

运行期证据目录内的 `run.sh`：

1. 用户态 tick 抢占：`/proc/uptime` 前进、500 次启动无停摆；
2. 内核态 tick：irq 计数递增、不调度；
3. 同帧多源：构造 timer+DMA 同时到达（或用可控源）⇒ 一次进入、两位都处理、计数 +1；
4. 掩码生效：复位全 1 时无投递；写 smon/umon 后按预期投递；连续两次 async 覆盖 cg9；smon 调度期间允许 async（嵌套由软件处理）；
5. `escape imms18=2` 不再作为异步返回（应 CFXESC）；`trap cfx_smon` handoff 有终结/返回路径；
6. **可达 FAIL ≥2**：注入"掩码写 cg9"、"去掉 trap cfx_smon handoff" ⇒ 红；`cp`+md5 还原回绿；
6. `check-linux-k6`（或对应门控）、`check-tests-index`、`check-tasks` 记录 rc。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
