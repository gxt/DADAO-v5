# m18-linux-013: 用户态异步投递与抢占完整修复（ISS-500，monitor-first）

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-qemu-002`（QEMU monitor-first 仲裁/pending，须先合入）+ `ADR-0059` Accepted + `contract-see`/`ADR-0042`/`ADR-0045` 同步；与 `m18-linux-005` 串行（同写 linux 组件）
**可并行分片**：否
**预估**：3–5 h（monitor-first 复用既有 umon 入口/adopt/`task_pt_regs`/return-to-user 机制，无 early-escape 新机制；标定：同档最近 5 件派单→合入实测中位数）
**档位**：中改（umon 异步入口 + user 行策略 + irqentry 退出工作循环 + 抢占/信号）
**状态**：待开始
**执行环境**：本地（QEMU system `-M kaiwu-vast`）

## 背景

`ISS-500`【P2】：K6 之后用户态**收不到任何异步中断**。直接原因：`dadao_enter_user()` 每次进用户态把 `cfx_umon cg0 rc4` 写 `~0`（全仓无第二处写回），`dadao_user_entry_install()` 开机为 TIMER 打开的 user 行成为死代码。用户态忙循环无 jiffies、无 tick 抢占、无信号投递。用户 2026-11-22 裁定：**参考其它 ISA 完整修复，不追认「用户态不投递」**。

**根本模型**（用户 2026-11-22 明确）：`spec/DADAO-12 §5.2` 已是 **monitor-first**——异步源（TIMER=cfx_hart、PMEM_DMA=cfx_pmem）先入**当前运行模式 monitor**（用户态 → `cfx_umon`、内核态 → `cfx_smon`），mask 两级与 pending（`cg5 rc5`）都在 monitor；contract/adr 原先的 target-first（`TIMER` → `cfx_hart` 行）未及时同步。`m18-linux-004` 的「supv 窗口 + user 行双屏蔽」与 `dadao_async_excp` 的 `cfx_hart` 独立入口都是 target-first 的产物。

monitor-first 使异步帧天然落在 monitor 的 switch-safe 帧上：用户态投递进 `cfx_umon`，**复用现有 umon 入口的捕获/adopt/`task_pt_regs`/return-to-user 机制**，`schedule()` 成为普通内核代码——**不再需要 early-escape**。本任务只改 kernel 路径（`components/linux/patches/**`），QEMU 的 monitor-first 仲裁/pending 迁移由 `m18-qemu-002` 落地（本任务前置）。

## 方案（按 ADR-0059 D1–D3）

1. **umon 异步入口**（D1）：用户态异步投递进 `cfx_umon`（user 行 `cg0 rc10`），与用户 `trap cfx_umon, 0` 同向量同帧；`dadao_umon_excp` 入口按 `excp_cause_id` 区分异步（`1 << 17` = TIMER，`[31:16]` 宏 cause）与同步（CFXTRAP=syscall / CFXMEM 等 fault），异步走本任务的 handler。内核态投递进 `cfx_smon`（supv 行 `cg2 rc10`），supv handler 非调度。
2. **user 行策略 + supv 窗口屏蔽**（D2）：`cfx_umon cg0 rc4` 按源位（bit15 TIMER）打开，`dadao_enter_user()` **去掉 `~0` 写**（保留 `dadao_user_entry_install()` 的开源位或按源位重写）；supv 窗口屏蔽（`cfx_smon cg2 rc4` 经 `arch_local_irq_disable`）**保留**。
3. **irqentry 退出工作循环 + 抢占/信号**（D3）：用户态异步 handler 走 `irqentry_enter(regs)` → `dadao_timer_interrupt()`（`tick_handle_periodic`）→ `irqentry_exit(regs, state)`；`regs->status = user` ⇒ `irqentry_exit` 走 `irqentry_exit_to_user_mode_prepare()` + `exit_to_user_mode()` 消费 `_TIF_NEED_RESCHED`/`_TIF_SIGPENDING`，复用 `entry_common.c` 的 `dadao_exit_tail`。supv 异步 handler 用非调度的 `irq_enter_rcu`/`irq_exit_rcu` + `dadao_timer_interrupt()`。
4. **移除 `cfx_hart` 向量依赖**：`irq.c` 不再装 `cfx_hart` 的 supv/user 向量；`dadao_async_excp`（`cfx_hart` 独立入口）移除或折叠进 monitor 入口。

## 验收（逐条贴真实 rc）

1. **ADR-0059 Accepted**（monitor-first D0–D8）且 `m18-qemu-002` 已合入；实现与 ADR 一致。
2. **时间可见**：用户态忙循环（无 syscall）期间 jiffies 推进——经 `/proc/uptime`（`CONFIG_PROC_FS=y`）或等价内核导出；停 user 行恢复 ⇒ 该断言红。
3. **抢占**：两个 CPU 密集用户任务并发按 tick 轮转（记录切换次数/各自进度）；单任务忙循环 + `alarm()`/`SIGALRM` handler 不靠 syscall 投递。
4. **`ISS-498` 不回归**：连续 **500** 次启动全部进入用户态（无 rc=124/1、无 die-no-vma），两次独立批次；去 supv 行注入作对照。
5. **可达 FAIL ≥3 路**（`cp`+md5 还原 + 重建）：① 去掉 user 行恢复 ⇒ 时间可见红；② 去掉 `irqentry_exit` 工作循环 ⇒ 信号/抢占红；③ 去掉 supv 窗口屏蔽 ⇒ 启动稳定性红（按频率披露）。
6. 不回归：`check-linux-k0`–`k6` 全 rc=0；`check-config-pins`、`check-patch-tree`（linux 段 0 problem）、`check-component-changelog`、`check-knowledge-refs` rc=0；`make check` 与基线逐行相同。
7. `ISS-500` 关闭；完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/linux/patches/**`（`process.c`/`async_trap.S`/`time.c`/`entry_common.c`/`irq.c`/`trap.S` 及必要头）、`components/linux/changelog.md`、`tests/unit/linux/**`、`tools/linux/**`、`.tao/knowledge/issues.yaml`、本任务书。
3. **不改** `spec/`、`.tao/contracts/`（monitor-first + cause 17/18 内容对齐已由架构师同笔完成，本任务不改）、`Makefile`、`components/qemu/**`、`components/musl/**`；语义/契约变更须先经用户确认。
4. 组件补丁经 `make_patch.py linux` 重导；不改版本号；术语「bank = 寄存器组」；大端/64 KiB 页/`IP=当前指令` 口径按 `MEMORY.md`。
5. 禁以「重试直到绿」掩盖竞态；启动稳定性按批次统计并披露频率。
6. 源码还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`；还原后重建。

## 待裁定

- `ADR-0059` 已定：异步 cause 号 = `1<<17`（TIMER）/`1<<18`（PMEM_DMA），落在 `[31:16]` 宏 cause 空间，与 monitor 同步 cause（`RASOF`/`ILLI`）不撞号（用户 2026-11-23 裁定）；kernel 侧 `DADAO_CAUSE_TIMER` 常量相应改 `1<<17`。无未决项阻塞派单。

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
