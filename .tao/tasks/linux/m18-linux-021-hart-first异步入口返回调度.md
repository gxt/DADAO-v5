# m18-linux-021: 内核 hart-first 异步入口/返回/调度（cfx_hart cg9）

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-qemu-004`（QEMU hart-first/cg9）已验证；`m18-llvm-001`（汇编器支持 `escape ..., 8`）
**可并行分片**：否
**预估**：3–5 h（标定：同档最近 5 件派单→合入实测中位 86 min；本任务为内核异步入口/返回/调度 + K2/K5 探针，取 2–3× 中位）
**档位**：大改（内核异常入口/调度）
**状态**：已作废（2026-11-23，`ADR-0061` 改写异步模型；本任务不再验收，替代任务 `m18-linux-022`）
**执行环境**：本地（QEMU system `-M kaiwu-vast`）

## 背景

`m18-qemu-004` 已把 QEMU 异步投递改为 hart-first：所有异步源进 `cfx_hart`，现场/mask/pending 在 `cg9`，`escape imms18=2` 选 cg9。内核仍按 monitor-first/旧异步路径（`async_trap.S` 以 `cfx_hart` 向量 + `irq_enter_rcu`、无 cg9），K2/K5 内核镜像门控与新 QEMU 不匹配。

## 目标

1. **入口**：异步入口固定 `cfx_hart cg9 rc6`（supv）；捕获 GPR 到任务 `task_pt_regs`；按 cg9 `prev_run_mode`/`from_user` 判是否切任务内核栈；用户态用 `dadao_user_stack_top`。
2. **现场/返回**：保存/恢复 cg9 现场（`prev_run_mode`/`prev_cfx`/`cause_ip`/`cause_id`/saved global mask）；返回用 `escape imms18=2`（cg9）；无帧/释放路径按 `DADAO-12 §5.3`；不得清 `cause_id` 后误返回。
3. **调度**：用户态异步走 `irqentry_enter/exit` + return-to-user work loop（`_TIF_NEED_RESCHED`/信号）；内核态异步不调度（沿用 `irq_enter_rcu/irq_exit_rcu`）；`pending` 在 cg9 rc5（位 cause 17/18），mask 位源 cfxha 15/32。
4. **探针**：K2 irq/time、K5 异步探针适配 hart-first；`tests/unit/linux/{k2_irq_probe,k2_time_probe}.py` 的期望与 QEMU 同步；新增/保留可达 FAIL。
5. **用户态时间可见/抢占**：按 ADR-0060 D6，用父进程 `/proc/uptime` 采样 + 子进程忙循环，另加 `alarm/SIGALRM` 交叉；500 次启动稳定性。

## 验收（逐条贴真实 rc）

1. 用户态异步投递进 `cfx_hart cg9`；`cause_id` 17/18、pending cg9、mask 位 15/32 有探针证据；`escape imms18=2` 返回正确。
2. 用户态忙循环期间 `jiffies` 推进（父进程采样 `/proc/uptime` 差值 ≈ 墙钟）；`alarm/SIGALRM` 不靠 syscall 投递；两个 CPU 密集任务按 tick 轮转。
3. 连续 **500** 次启动全部进入用户态（无 `ISS-498` 回归）；无 `die-no-vma`/panic。
4. **可达 FAIL ≥3 路**（`cp`+md5 还原+重建）：① 仍投 monitor/旧向量 ⇒ 入口断言红；② 不恢复 cg9 saved mask ⇒ 返回红；③ 去掉 `irqentry_exit` 工作循环 ⇒ 抢占/信号红。
5. 不回归：`check-linux-k0`–`k6` 全 rc=0；`check-config-pins`/`check-patch-tree` linux 段 0 problem/`check-component-changelog`/`check-knowledge-refs` rc=0；`make check` 与基线逐行相同。
6. K2/K5 内核镜像门控由红转绿（此前 QEMU hart-first 已使旧镜像必红）。
7. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/linux/patches/**`（异步入口/返回/调度）、`components/linux/changelog.md`、`tests/unit/linux/**`（K2/K5 探针）、`tools/linux/**`（仅必要）、本任务书。
3. 不改 `spec/`、`.tao/contracts/`、`Makefile`、`components/qemu|musl|busybox/**`；不改版本号。
4. 组件补丁经 `make_patch.py linux` 重导；还原 `cp`+md5；还原后重建；术语「bank = 寄存器组」；时间口径按 `ADR-0058`。
5. 不把「测试改期望」当内核修复；内核行为按 spec/ADR-0060，不反向改契约。

## 待裁定

无（若发现 cg9 语义与 spec 冲突，停下写「待裁定」）。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

### 第 1 轮 engineer 自审
（工程师自审意见、问题、判决及 finding 处置）

### 第 1 轮 reviewer 验收
（审查者独立重跑记录、约束核验、判决）
