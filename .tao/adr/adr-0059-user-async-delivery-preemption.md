# ADR-0059: 用户态异步投递与抢占完整修复（monitor-first 对齐 + 内核路径）

**状态**：Accepted
**日期**：2026-11-22（R2：monitor-first 重写）／2026-11-23（R3：异步 cause 号 17/18；R4：版本 0.8.0-rc + 逐条裁定落地）
**关联**：`ISS-500`、`ISS-498`（`m18-linux-004`）；`m18-linux-013`、`m18-qemu-002`；`spec/DADAO-12 §5.2（三）（四）（五）`、`§3.6`（cg5）、`§3.1/§3.3`（mask 行）、`§4.7/§4.9`（TIMER/PMEM_DMA）；`contract-see §3/§6.3/§6.4`；`ADR-0045 D3/D9`、`ADR-0042 D7.4`；`m14-spec-009`

## Context（背景）

`ISS-500`【P2】：K6 之后用户态**收不到任何异步中断**。直接原因：`dadao_enter_user()` 每次进用户态把 `cfx_umon cg0 rc4` 写 `~0`（全仓无第二处写回），`dadao_user_entry_install()` 开机为 TIMER 打开的 user 行成为死代码。用户态忙循环无 jiffies、无 tick 抢占、无信号投递。用户 2026-11-22 裁定：**参考其它 ISA 完整修复，不追认「用户态不投递」**。

### 根本原因（R2 澄清）：spec 是 monitor-first，contract/adr/QEMU/kernel 是 target-first

用户 2026-11-22 明确：**spec 已经改好，就是 monitor-first；contract/adr 没有及时更新**。这是本 ADR R2 的核心前提。spec 真源（`§5.2`）：

- **（三）步骤 3**：异步中断来源过滤查**当前运行模式 monitor** 的 `cfx_<monitor>_<mode>_cfx_intr_mask`（`cg0–3 rc4`）与 `cfx_<monitor>_global_cfx_intr_mask`（`cg8 rc1`），**位索引 = 中断来源 cfxha**；任一为 1 则不投递、置 **monitor** 的 `excp_pending`（`cg5 rc5`）。
- **（四）**：异步中断**先进入当前运行模式 monitor**，不直接进入源 cfx；monitor 拥有屏蔽/pending/分发决策，可自行处理并 `escape`，也可 `trap` 到源 cfx；处理期间新事件置 pending、不嵌套 monitor。
- **（五）** 伪代码：`async_intr ⇒ temp_cfx_code = temp_monitor_code`，mask/pending 都在 monitor。

而当前 `contract-see §3/§6.3`、QEMU `helper.c`（`dadao_async_sources`/`dadao_async_arbitrate` 投递到 `cfx_hart`/`cfx_pmem`、pending 记目标 cfx）、kernel（`irq.c` 装 `cfx_hart` 的 supv/user 向量）都是 **target-first**。`m18-linux-004` 之所以被迫「supv 窗口 + user 行双屏蔽」，正是 target-first 下异步帧落在 `cfx_hart`、handler 内不能 `schedule()` 的后果。

### 事实 vs 推断

**事实**：

- spec `§5.2`（三）（四）（五）为 monitor-first（如上）；`§3.6` `cg5 rc5 excp_pending` RW、`rc0/rc1/rc3` RW、`rc2/rc4` HW（软件不可写）。
- monitor 自身同步原因表（`§4.1 cfx_umon`，`§4.3 cfx_smon` 同构）只含 `[15:0]` 同步 cause（`1<<8 = ILLI`、`1<<10 = RASOF`）；**异步源 cause 号已定（用户 2026-11-23）**：`1<<17` = TIMER（`§4.7`）、`1<<18` = PMEM_DMA（`§4.9`），落在 `[31:16]` 宏 cause 空间、跨 cfx 全局编号，与 `[15:0]` 同步 cause 不撞号。
- `m18-linux-004` 注入：只去 user 行屏蔽 ⇒ 200/200 绿；两行都去 ⇒ 4/200 未进用户态。supv 窗口屏蔽被证明必要；user 行屏蔽必要性未复现。
- 现有 umon 入口（kernel `trap.S`/`process.c`/`entry_common.c`）已具备：捕获进 `task_pt_regs(current)`（`dadao_umon_adopt`）、阻塞 syscall 可 sleep、return-to-user 工作循环（`dadao_trap_exit` 走 `irqentry_exit_to_user_mode_prepare`）。

**推断**：

- 「jiffies 滞后」是从 mask 状态 + 契约推出，未端到端实测（D6 门控补）。
- monitor-first 下「同步/异步共享 monitor 向量、按 `excp_cause_id` 区分」依赖 `[31:16]` 宏 cause（17/18）与 `[15:0]` 同步 one-hot 的互斥，已由 17/18 裁定成立。

## Decision（决策）

### D0 投递模型 = monitor-first（spec 真源）

采用 spec 的 **monitor-first**：异步源（TIMER=cfx_hart、PMEM_DMA=cfx_pmem）先入**当前运行模式 monitor**（U/J/S/H → umon/jmon/smon/hmon），mask 两级、pending（`cg5 rc5`）都在 monitor。**否 target-first**（旧 contract/QEMU/kernel 口径）；**否 H3 硬件帧栈**（LIFO 只解同 cfx 嵌套、不解跨任务调度，RTL 面最大）。monitor-first 使「可切换的帧」问题**随模型消解**（见 D3），不再是需要额外机制去解决的目标。

### D1 异步入口 = monitor 的 `<mode>_excp_vector`

用户态异步投递进 `cfx_umon`（user 行，`cg0 rc10`），**复用现有 umon 入口的捕获/adopt/`task_pt_regs`/return-to-user 机制**；内核态（supv）投递进 `cfx_smon`（supv 行，`cg2 rc10`）。**同步与异步共享同一 monitor 向量、同一帧**（`§5.2` 步骤 1/7），handler 按 `excp_cause_id` 区分。`irq.c` 不再装 `cfx_hart` 的向量；`dadao_async_excp` 的独立 `cfx_hart` 入口移除或折叠进 monitor 入口。

### D2 mask/pending 在 monitor；user 行策略；supv 窗口屏蔽保留；内核态不调度

- 两级 mask（`<mode>_cfx_intr_mask` + `global_cfx_intr_mask`）与 delivery pending（`cg5 rc5`）都按**当前运行模式 monitor**；mask 位索引 = **来源 cfxha**（TIMER=15、PMEM_DMA=32），pending 位 = 源 cause id（**`1<<17`/`1<<18`**，`[31:16]` 宏 cause 空间，与 `[15:0]` 同步 cause 不撞号）。
- **user 行策略**：`cfx_umon cg0 rc4` 按源位（bit15 TIMER）打开，`dadao_enter_user()` **永不写 `~0`**（去掉该行屏蔽）；supv 窗口屏蔽（`cfx_smon cg2 rc4`，经 `arch_local_irq_disable`）**保留**，覆盖「用户寄存器已恢复、`trap` 未执行」的窗口。
- **内核态（supv）不调度**：supv 异步 handler 走非调度的 `irq_enter_rcu`/`irq_exit_rcu` + `dadao_timer_interrupt()`，不在 monitor 帧内 `schedule()`；抢占/信号只在返回用户态时消费（D3）。

### D3 用户态 handler = `irqentry_enter/exit` + return-to-user work loop

用户态投递进 umon 后，frame 落在本任务 `task_pt_regs`，与阻塞 syscall 同一帧不变量（umon 单帧 + 捕获进内存 + escape 前写回 `rc0/rc1/rc3`）⇒ **该帧天然可跨任务 schedule**。handler 走 `irqentry_enter(regs)` → `dadao_timer_interrupt()`（`tick_handle_periodic`）→ `irqentry_exit(regs, state)`：因 `regs->status = user`，`irqentry_exit` 走 `irqentry_exit_to_user_mode_prepare()` + `exit_to_user_mode()` 消费 `_TIF_NEED_RESCHED`/`_TIF_SIGPENDING`（抢占/信号），复用 `entry_common.c` 既有 tail。**不再需要 early-escape**——monitor-first 下异步帧本来就是 switch-safe 的 umon 帧。

### D4 是否需要 H1（帧完全软件可管）：M18 不需要，列为未来可选

R1 曾以「early escape」为主路径，根源是 target-first 下异步帧落在 `cfx_hart`（`rc2/rc4` HW 只读 + 保存的 global mask 是内部单槽，帧不可重建/不可 park）。monitor-first 已使 M18 无需该机制。**H1**（`rc2 cause_id`/`rc4 cause_info` 改 supv 可写、保存的 global mask 变软件可见帧字段）**不纳入 M18**，列为未来可选改进（使软件可 spill/fill 帧，进一步对齐 RISC-V/ARM64/x86 的软件栈帧模型）；若采纳须另立 spec/RTL/QEMU 任务并逐条确认。

### D5 影响面与排队

- **QEMU（`m18-qemu-002`）**：仲裁改为投递当前 mode monitor、pending 迁 monitor `cg5 rc5`、两级 mask 按 monitor（位 = 源 cfxha）、同源 OR/补投、单层投递；更新 `min_rom_probe_integ051t`、K2/K5 异步探针、`tests/arch/vast-arch-inventory.md`、QEMU changelog。
- **kernel（`m18-linux-013`）**：umon 异步入口（D1）、user 行策略（D2）、irqentry exit 工作循环 + 抢占/信号（D3）；去掉 `~0` 写、去掉 `cfx_hart` 向量依赖。
- **RTL（chipyard `GewuFile`）/ gem5（`node_cfx`）**：**QEMU 先行，RTL/gem5 等 M16 当前批次收口后另立任务**（本 ADR 只列影响面，不立任务）。
- **contract**：`contract-see §3/§6.3/§6.4` 已按 monitor-first 对齐（本 ADR 同笔）；`ADR-0042 D7.4`、`ADR-0045 D3/D9` 已加修订记。
- **排队（不得与 M16 写者冲突）**：`m16-qemu-002`（影子 D-Cache，正在跑，同改 `helper.c/cpu.c/cpu.h`）→ `m18-qemu-002` → `m16-qemu-003`（cfx5 命令，依赖 `m18-qemu-002`）→ `m16-testcases-009`。`m18-qemu-002` **必须在 `m16-qemu-003` 之前合入**，且**不得与 `m16-qemu-002` 并发写 `components/qemu`**；M16 的 003/009 基于新模型重跑。

### D6 门控/探针

1. **时间可见（A+B）**：父进程采样 `/proc/uptime` + 子进程忙循环（无 syscall），观测 jiffies 推进；另用 `alarm()`/`SIGALRM` 交叉证据。
2. **抢占**：两个 CPU 密集用户任务按 tick 轮转（记录切换次数/进度）；单任务忙循环 + `alarm()`/`SIGALRM` handler 不靠 syscall 投递。
3. **`ISS-498` 不回归**：连续 500 次启动全进用户态（无 rc=124/1、无 die-no-vma），两独立批次；去 supv 行作对照。
4. **可达 FAIL ≥3**：① 去 user 行 ⇒ ①红；② 去 `irqentry_exit` 工作循环 ⇒ ②红；③ 去 supv 屏蔽 ⇒ ③红（按频率披露）。
5. **QEMU 侧（`m18-qemu-002`）**：monitor-first 仲裁/pending 迁移后既有 M16 cfx5/cache 代表集不回归、K2/K5 异步探针更新且可达 FAIL。
6. **不回归**：`check-linux-k0`–`k6`、`check-config-pins`、`check-patch-tree`（linux/qemu 段 0 problem）、`check-component-changelog`、`check-knowledge-refs`、`make check` 与基线逐行相同。

### D7 版本号/契约同步

**版本 0.8.0-rc 已定（2026-11-23 用户裁定）**：monitor-first + 异步 cause 17/18 为**不兼容语义变更**，`spec/DADAO-12`（SEE）/`DADAO-22`（SBI）同升 **0.8.0-rc**（`y+1`，SEE↔SBI 互锁）；`contract-see` 版本/来源行、`contract-cache`/`contract-tlb` 来源行、`spec/.manifests.toml` 锁哈希同笔同步。

### D8 分阶段

**先 QEMU + kernel user 路径，RTL/gem5 后续**：

- **阶段 1（QEMU）**：`m18-qemu-002` 落地 monitor-first 仲裁/pending（先行，解除 M16 003/009 的前置）。
- **阶段 2（kernel）**：`m18-linux-013` 落地 umon 异步入口 + user 行 + irqentry work loop（抢占/信号）；可再拆「先时间可见（只开 user 行，复用现有 umon 捕获）、再做抢占/信号」两小步。
- **阶段 3（后续，另立任务）**：RTL/gem5 的 monitor-first 同步 + cause 17/18、H1（帧软件可管）可选改进——等 M16 当前批次（`m16-qemu-003`、`m16-testcases-009`）收口后另立。

## Rationale（理由）

- **为什么 monitor-first 是正解**：spec 已定；它让异步帧落在 monitor（umon/smon），而 monitor 帧本就是 switch-safe 的软件帧（`task_pt_regs` + escape 前写回），`schedule()` 成为普通内核代码，不需要任何 early-escape 特例。
- **为什么否 target-first**：它是 contract/adr/QEMU/kernel 的旧口径，与 spec 冲突，且是 `ISS-500`/`ISS-498` 双屏蔽与 early-escape 复杂度的根源。
- **为什么否 H3**：LIFO 帧栈只解嵌套、不解跨任务调度；monitor-first 已解本问题，无需硬件改动。
- **为什么 supv 窗口屏蔽保留、user 行打开**：`m18-linux-004` 注入只证明 supv 行必要；user 行屏蔽必要性未复现，且打开它是 monitor-first 用户态投递的前提。

## Consequences（影响）

- 用户态 tick 抢占/信号恢复；`ISS-500` 关闭；`ISS-498` 由 500 次启动门控守住。
- QEMU 仲裁/pending 迁移（`m18-qemu-002`）是 M16 003/009 的前置，须尽早做、不得与 `m16-qemu-002` 并发写 `components/qemu`。
- kernel 侧 `irq.c`/`async_trap.S` 的 `cfx_hart` 向量安装与独立异步入口被移除/折叠。
- RTL/gem5 同步与 H1 为后续（不立任务）。

## 裁定记录（用户 2026-11-23 逐条确认，转 Accepted）

- **D0**：monitor-first 作为唯一投递模型（否 target-first/H3），spec 为真源 —— ✅ 确认。
- **D3**：内核态异步不调度（supv 异步 handler 用非调度的 `irq_enter_rcu`/`irq_exit_rcu`，抢占/信号只在返回用户态时消费）—— ✅ 确认。
- **D6**：门控/探针 = **A+B**（父进程采样 `/proc/uptime` + 子进程忙循环，另用 `alarm()`/`SIGALRM` 交叉证据）—— ✅ 确认。
- **cause 号**：`1<<17`（TIMER）/`1<<18`（PMEM_DMA），`[31:16]` 宏 cause 空间 —— ✅ 确认。
- **版本**：**0.8.0-rc**（SEE/SBI 互锁同升，`y+1`，不兼容语义变更）—— ✅ 确认。
- **RTL/gem5 节奏**：**QEMU 先行，RTL/gem5 等 M16 当前批次收口后另立任务** —— ✅ 确认。

## 实施注记

- **RTL/gem5 后续任务**：chipyard `GewuFile`、gem5 `node_cfx` 的 monitor-first 仲裁/pending 迁移与 cause 17/18 同步，待 M16 当前批次（`m16-qemu-003`、`m16-testcases-009`）收口后另立任务；本 ADR 不立任务，只列影响面（D5/D8）。

## 状态说明

2026-11-22 R2：用户裁定 spec 已是 monitor-first、contract/adr 未及时同步，按 monitor-first 重写本 ADR（R1 的 early-escape 方案作废）。2026-11-23 R3：用户裁定异步 cause 号改 **17/18**。2026-11-23 R4：用户逐条确认 D0/D3/D6/cause/版本/RTL 节奏，状态转 **Accepted**；版本 **0.8.0-rc**（SEE/SBI 互锁）随本 ADR 提交。随后派 `m18-qemu-002`（QEMU，先行）与 `m18-linux-013`（kernel）。
