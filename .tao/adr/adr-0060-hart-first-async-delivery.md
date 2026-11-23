# ADR-0060: 异步中断投递改为 hart-first（统一进 `cfx_hart` + 新增 `cg9` 异步现场）

**状态**：Accepted（**部分被 `ADR-0061` 取代**：D2 的 `cg9` 表、D3 的释放/返回语义、D6 的掩码归属、D7 的「保留 cause 17/18」由 `ADR-0061` 改写；D0/D1/D4/D5/D9 继续有效）
**日期**：2026-11-23
**关联**：`ADR-0059`（monitor-first，已 Accepted，本 ADR 推翻并 Superseded）；`m18-qemu-002`（monitor-first QEMU，reviewer Accepted，**不合入**，留作参考分支）；`m18-qemu-003`（旧异步探针迁 monitor-first，同步标记被取代）；`spec/DADAO-12 §5.2`、`§3.6`（cg5）、`§3.1–§3.4`（cg0–cg3 rc4 异步 mask）、`§3.7`（cg6）、`§4.7`（cfx_hart）、`§4.9`（cfx_pmem）；`contract-see §3/§6.3/§6.4`；`ADR-0045 D3/D9`、`ADR-0042 D7.4`、`ADR-0056`（cause 分层）；`ISS-500`、`ISS-498`

## Context（背景）与推翻理由

`ADR-0059`（monitor-first）已于 2026-11-23 Accepted，并据此把 `spec/DADAO-12`（SEE）/`DADAO-22`（SBI）升到 `0.8.0-rc`、异步 cause 号定为 `1<<17`（TIMER）/`1<<18`（PMEM_DMA）、`contract-see` 与 QEMU（`m18-qemu-002`）按 monitor-first 对齐。**用户 2026-11-23 裁定推翻 monitor-first，改 hart-first**。理由与现状：

1. **模型代价不对称**：monitor-first 把异步帧落在「当前运行模式 monitor」（U/J/S/H → umon/jmon/smon/hmon），mask 两级、pending、帧分散在四个 monitor 里；同一 hart 的异步中断会因「当时运行在哪个模式」而落进**四个不同 cfx** 的现场，`pending 不随模式切换迁移`（ADR-0059 D9）这一口径正是为缝合这种分裂而额外追加的。hart-first 把所有异步源统一进 **`cfx_hart`（cfxha 15，per-hart）**，现场/屏蔽/pending 单一归处，模型更简单、更贴合「cfx_hart 管理 hart」的定位。
2. **内核路径简化**：monitor-first 下内核要在 `cfx_umon`/`cfx_smon` 两套 monitor 入口里按 `excp_cause_id` 区分同步/异步（ADR-0059 D1/D3），且 supv 窗口屏蔽、user 行策略都要分别处置；hart-first 下异步只有 **`cfx_hart` 的 supv 单向量 + 单帧**，与同步异常（仍走 monitor）彻底分流，`irqentry`/调度/抢占路径不再需要「monitor 帧内不得 schedule」这类特例。
3. **软件可控性**：新增 `cg9`（`cfx_hart` 专有）把异步现场做成**软件可快照/释放/重建**的寄存器组（`async_cause_id != 0` 即有效帧），不再依赖 monitor 帧的保存/恢复语义。

### 推翻范围与处置（不删历史）

- **`ADR-0059`**：整体 Superseded（monitor-first 投递模型作废；其中**异步 cause 号 17/18、mask 位索引=来源 cfxha 这两条口径保留**，其余 D0/D1/D2/D3/D9 作废）。本 ADR 落定后由主会话在 ADR-0059 头部追加 Superseded 标记（不在本笔改）。
- **`m18-qemu-002`**（monitor-first QEMU 仲裁/pending 迁移）：已 reviewer Accepted 但**不合入 master**，保留分支作参考（hart-first QEMU 任务可对照其仲裁/补投骨架改目标）。
- **`m18-qemu-003`**（旧异步探针迁 monitor-first）：**同步标记被取代**（不删代码历史），旧异步探针改由 hart-first 任务迁到 `cfx_hart`/`cg9`。

### 事实 vs 推断

**事实**（spec 真源）：
- `cfx_hart` = cfxha **15**（per-hart，`cfx0–cfx15` per-hart）；`cfx_pmem` = cfxha **32**（per-system）。[DADAO-12 §1]
- 异步 cause 已定：`1<<17` = TIMER（源 `cfx_hart`）、`1<<18` = PMEM_DMA（源 `cfx_pmem`），落在 `[31:16]` 宏 cause 空间、跨 cfx 全局编号、与 `[15:0]` 同步 one-hot 互斥。[DADAO-12 §3.6（二）]
- 两级 mask 的**位索引 = 来源 cfxha**（TIMER=15、PMEM_DMA=32），**不是** cause 位（17/18）。[contract-see §6.3]
- `cfx_hart` 现用 `cg8`（hart 管理：hart_id/cycle/insn/timer_cmp/timer_ctrl，rc0–rc7）；`cg9` 当前**未定义**（新增）。
- `cg6` = 暂存寄存器（scratch，每 cfx ≥2 个、rc0 起连续），现内核 `async_trap.S` 已用 `cfx_hart` 的 cg6 scratch 做 GPR 捕获（`DADAO_GPR_SAVE cfx_hart`），并用 per-hart 软件变量 `dadao_user_stack_top` 做用户态切栈。[DADAO-12 §3.7]
- `escape`（现有指令）语义基于 **cg5 异常帧**（`excp_cause_id=0` 即无有效帧），`cfxha` 必须=当前 cfx。[DADAO-12 §5.3]

**推断**：
- 「hart-first 使 pending 随 hart 单一归处、无需迁移口径」是模型推论，须在 spec/contract 同步任务里用探针验证（pending 记 `cfx_hart cg9 rc5`，跨模式切换不丢、任务退出丢弃依赖源重触发）。
- `escape` 复用 + frame selector（bit1）对 `imms18` 的占用会改变 `escape` 的合法编码集合（`imms18 ∈ {0,1,2}`，`3` ⇒ ILLI），须在 spec/工具链/QEMU/RTL/gem5/测试同步落点（见 D4/D6）。

## Decision（决策）

### D0 投递模型 = hart-first（统一进 `cfx_hart`）

所有异步源（TIMER=`cfx_hart`、PMEM_DMA=`cfx_pmem`）投递到**同一个 `cfx_hart`（cfxha 15）**，**不再是 per-mode monitor 入口**。mask（`async_*_intr_mask`）、delivery pending（`async_pending`）、异常现场（`async_prev_*`/`async_cause_*`/`async_saved_global_intr_mask`）**全部在 `cfx_hart`**，落在**新增 `cg9`**（见 D2）。**否** monitor-first（ADR-0059 作废）；**否** target-first（旧 contract/QEMU/kernel 口径，早已被 ADR-0059 否）。

### D1 异步入口 = `cfx_hart` 的 **supv 单向量**

异步投递进 `cfx_hart` 的 **supv 行**，向量取 `cfx_hart cg9 rc6`（`async_excp_vector`），目标模式取 `cg9 rc7`（`async_switch_run_mode`，**固定 supv=2**）。**单异步向量 + 单异步帧**，与同步异常（仍走当前运行模式 monitor、`cg5` 帧）**彻底分流**；handler 不再按 `excp_cause_id` 在 monitor 帧里区分同步/异步。`cfx_hart` 不再装用户态/user 行异步向量（原 monitor-first 的 umon/smon `<mode>_excp_vector` 不参与异步）。

### D2 `cfx_hart cg9` 寄存器表（用户已确认最终版）

> 无 `async_ctrl`、无 `async_sp`、无 `cause_info`、无 `async_src`、无 scratch、无 nest_depth。
> **有效帧判据** = `async_cause_id != 0`；**from_user** = `async_prev_run_mode == user`（rc0）。
> `async_prev_run_mode` 取 2b（0=user/1=jail/2=supv/3=hypv）；`async_prev_cfx_code` 取 6b（cfxha）；`async_cause_ip`/`async_excp_vector` 取 48b（核内地址，4B 对齐落盘，低 2 位忽略）。

| cg | rc | 寄存器名 | 宽度 | 访问 | 说明 |
|----|----|---------|------|------|------|
| 9 | 0 | async_prev_run_mode | 2b | HW/RW | 异步前运行模式；硬件进入时写，软件可写（快照/重建用） |
| 9 | 1 | async_prev_cfx_code | 6b | HW/RW | 异步前当前 cfx 编号；硬件进入时写，软件可写 |
| 9 | 2 | async_cause_ip | 48b | HW/RW | 异步下一条指令地址；硬件进入时写，软件可写 |
| 9 | 3 | async_cause_id | 64b | HW/RW | 异步 cause id（`1<<17`/`1<<18`）；**非零 = 有效帧**；软件写 0 释放帧 |
| 9 | 4 | async_saved_global_intr_mask | 64b | HW/RW | 进入时保存的 `async_global_intr_mask`（供返回恢复） |
| 9 | 5 | async_pending | 64b | RW | 待处理异步位图（一个位图足够；**位 = 源 cause id `1<<17`(TIMER)/`1<<18`(PMEM_DMA)**，非 cfxha 位），写 0 清位 |
| 9 | 6 | async_excp_vector | 48b | RW | supv 异步向量入口；4B 对齐（写低 2 位忽略） |
| 9 | 7 | async_switch_run_mode | 2b | RW | 固定 supv（2） |
| 9 | 8 | async_global_intr_mask | 64b | RW | 全局异步来源掩码（位索引 = 来源 cfxha 15/32，0=允许/1=屏蔽） |
| 9 | 9 | async_user_intr_mask | 64b | RW | user 运行期异步来源掩码（位索引 = 来源 cfxha） |
| 9 | 10 | async_jail_intr_mask | 64b | RW | jail 运行期异步来源掩码 |
| 9 | 11 | async_supv_intr_mask | 64b | RW | supv 运行期异步来源掩码 |
| 9 | 12 | async_hypv_intr_mask | 64b | RW | hypv 运行期异步来源掩码 |
| 9 | 13–15 | reserved | — | — | 保留；访问触发 `CFXREG` |

- **mask 位索引 = 来源 cfxha**（TIMER=15、PMEM_DMA=32），**不是** cause 位 17/18（与 ADR-0059 口径一致，保留）。`0=允许`、`1=屏蔽`。
- **P1 pending 位 ≠ mask 位**：`async_pending` 的位 = 源 **cause id**（`1<<17`/`1<<18`）；五个 mask 的位索引 = 来源 **cfxha**（15/32）。两者不混用（已定，见裁定记录 P1）。
- 五个 mask 都在 `cg9`（`rc8`–`rc12`），**不再有 monitor 的 `<mode>_cfx_intr_mask`/`global_cfx_intr_mask` 承担异步**（monitor 侧那两个字段的异步用途作废，其去留归 spec 同步任务，见 D6/D9）。

### D3 异步语义（进入 / 无嵌套 / 释放重建 / 返回）

- **进入**：硬件写 `cg9`（`async_prev_run_mode`/`async_prev_cfx_code`/`async_cause_ip`/`async_cause_id`），保存 `async_global_intr_mask` → `async_saved_global_intr_mask` 并**置全 1**，切 `async_switch_run_mode`（supv），跳 `async_excp_vector`。
- **无嵌套**：`async_cause_id != 0`（帧活动期）到达的新事件**只置 `async_pending`**，不再次进入（硬件不支持嵌套，由软件处理）。
- **软件可管**：软件可**快照**整组 cg9（含 mask），**写 0 释放帧**（`async_cause_id=0` + `async_pending` 清位），或**重建**现场（改写 `async_prev_*`/`async_cause_ip`）后返回。
- **返回**：用 **`escape cfx_hart, [excp_cause_ip, imms18]`** 复用现有 `escape`，经 **frame selector 位（bit1）** 选 `cg9` 帧（bit1=1，偏移恒 0）——从 `cg9` 恢复 `async_prev_run_mode`/`async_prev_cfx_code`/`async_cause_ip` 并恢复 `async_saved_global_intr_mask`（见 D4）。
- **pending 模式切换不迁移**：`async_pending` 记在 `cfx_hart`（per-hart 单归处），跨模式（user↔supv）切换**不搬移**（hart-first 下归处唯一，天然无迁移问题）；任务退出时 pending 丢弃、依赖源重触发。
- **cause 号**：`1<<17`（TIMER）/`1<<18`（PMEM_DMA）沿用，落在 `[31:16]` 宏 cause 空间。

### D4 返回 = 复用 `escape` + frame selector 位（bit1）（方案 B，不新增 opcode）

**不新增 `async_escape` 指令**。复用现有 `escape` 指令，在其 `imms18` 增加 **frame selector 位 = bit1**：

- **bit0** 仍是偏移（0 / +4）；
- **bit1** = 0 选 `cg5`（同步异常帧），= 1 选 `cg9`（异步现场）；
- **`cg9` 只允许偏移 0**（异步 `excp_cause_ip` 已是下一条指令地址，`+4` 会多跳一条）⇒ 编码约束：`imms18 = 0` = cg5 偏移 0；`imms18 = 1` = cg5 偏移 +4；`imms18 = 2` = cg9 偏移 0；`imms18 = 3` ⇒ `ILLI`；
- **`imms18[17:2]` 仍 SBZ**（非零 ⇒ `ILLI`，同现有 escape 语义）；
- **`cfxha` 仍必须 = 当前 cfx**（帧/目标错误 ⇒ `CFXESC`，同现有 escape）。

选 `cg9` 时帧有效判据 = `async_cause_id != 0`；返回 cfx/mode/IP 取自 `cg9` 的 `async_prev_cfx_code`/`async_prev_run_mode`/`async_cause_ip`，并恢复 `async_saved_global_intr_mask`。选 `cg5` 时语义不变（沿用 cg5 escape）。**影响面**：spec（`§5.1`/`§5.3` escape 编码与语义）、工具链（汇编器 escape 编码 `imms18` 合法性）、QEMU、RTL、gem5、测试（escape 合法/非法编码向量）都须同步 bit1 语义。

### D5 `cg6` GPR staging = 入口 cfx 的 `cg6 rc0/rc1`（C1）；不引入 async 上下文指针

- **C1（GPR staging 上下文）= 入口 cfx 的 `cg6 rc0/rc1`**：hart-first 下入口 cfx = `cfx_hart`，故 GPR staging 用 **`cfx_hart cg6 rc0/rc1`**（暂存寄存器），与现有 `async_trap.S` 的 `DADAO_GPR_SAVE cfx_hart` 一致，沿用即可。
- **不引入 async 上下文指针**（不在 cg9 里放 `async_sp`/上下文指针寄存器）。
- **用户态切栈继续用 per-hart 软件变量**（`dadao_user_stack_top` 类）：异步在 user 运行期到达时，handler 用 `async_prev_run_mode == user`（`cg9 rc0`）判 from_user，切到该 hart 的 per-hart 软件变量指向的内核栈，再 adopt 进 `task_pt_regs`（沿用现有 umon 入口机制）。

### D6 软硬件影响面

- **spec `DADAO-12`**：`§5.2` 异步段由 monitor-first 改 hart-first（投递目标=`cfx_hart`、单 supv 向量）；`§3.6` 不动 cg5，但新增 `§3.x`（`cfx_hart` `cg9` 寄存器表，见 D2）；`§3.1–§3.4` 的 `rc4`（`<mode>_cfx_intr_mask`）与 `cfx0–cfx3` `cg8 rc1`（`global_cfx_intr_mask`）的**异步用途作废**（去留/是否标 reserved 待 spec 任务定）；`§4.7`（cfx_hart）加 cg9；`§4.9`（cfx_pmem）异步投递目标改 `cfx_hart`；`§5.1`/`§5.3` escape 增 frame selector（bit1）语义。
- **contract-see**：`§3` 统一异步仲裁、`§6.3` 异步内核入口、`§6.4` IE 单旋钮三段改 hart-first（入口=`cfx_hart cg9`、旋钮=`cfx_hart cg9 rc8/rc11`）；escape 返回 cfx 段补 frame selector 口径。
- **QEMU**（`components/qemu`）：仲裁/pending/两级 mask 迁到 `cfx_hart cg9`（对照 `m18-qemu-002` 骨架改目标）；cause 17/18 常量沿用；escape `imms18` bit1 frame selector 接线；`min_rom_probe_integ051t`、K2/K5 异步探针更新。
- **chipyard RTL**（`GewuFile`）：`cfx_hart` 增 `cg9`（16 rc 异步现场 + mask）、异步仲裁/pending 迁 `cfx_hart`、escape bit1 frame selector 实现。
- **gem5**（`node_cfx`）：同 QEMU，`cfx_hart cg9` + hart-first 仲裁/pending + escape bit1 frame selector。
- **kernel**（`components/linux`）：异步入口（`cfx_hart cg9 rc6` supv 单向量）、返回（`escape` bit1 选 cg9 帧）、`async_pending` 补投/调度、GPR staging（cg6 rc0/rc1）、from_user 切栈（`dadao_user_stack_top`）。
- **工具链/汇编**：escape 编码 `imms18` 合法集合改为 `{0,1,2}`（`3` ⇒ ILLI），`imms18[17:2]` SBZ 不变，汇编器/反汇编同步。
- **测试/探针**：旧异步探针（`min_rom_probe_async_094t`/`integ050t`）迁 hart-first（原 `m18-qemu-003` 被取代后并入 hart-first 任务）；新增 cg9 现场/无嵌套/软件释放重建探针；escape 合法/非法编码向量（bit1=0/1，`imms18=3` ⇒ ILLI）。
- **版本**：保持 `0.8.0-rc`（内容改、不升号，见 D9）。

### D7 与 ADR-0059 / m18-qemu-002 / m18-qemu-003 的关系

- **ADR-0059 → Superseded**：monitor-first 投递模型作废；**保留**「cause 17/18」与「mask 位索引 = 来源 cfxha」两条；其余（D0/D1/D2/D3/D9）作废。Superseded 标记由主会话在本 ADR Accepted 后追加，本笔不改 ADR-0059 正文。
- **m18-qemu-002 → 不合入、留参考分支**：hart-first QEMU 任务对照其仲裁/补投/探针骨架，改投递目标为 `cfx_hart cg9`。
- **m18-qemu-003 → 被取代**：旧探针迁移并入 hart-first 任务。

### D8 任务分解建议（只列，不创建任务文件）

1. **spec/contract 同步**（`spec` + `.tao/contracts/` 同笔）：`§5.2`/`§3.x`（cg9）/`§4.7`/`§4.9`/`§5.1`/`§5.3`（escape bit1）+ `contract-see §3/§6.3/§6.4`；版本保持 `0.8.0-rc`，`spec/.manifests.toml` 只重算受影响册。
2. **QEMU hart-first**（`qemu`）：仲裁/pending/两级 mask 迁 `cfx_hart cg9`、escape bit1 frame selector 接线、探针/归档更新。依赖 1；对照 `m18-qemu-002` 参考分支。
3. **kernel hart-first/cg9**（`linux`）：异步入口/返回/调度 + GPR staging + from_user 切栈。依赖 2。
4. **RTL**（`chipyard`）：`cfx_hart cg9` + 异步仲裁/pending + escape bit1。依赖 1；等 M16 当前批次收口后另立。
5. **gem5**（`gem5`）：同 RTL。依赖 1；等 M16 收口后另立。
6. **旧探针迁移**（`testcases`）：`min_rom_probe_async_094t`/`integ050t` 迁 hart-first。依赖 2。

- **依赖与写者串行**：1（spec/contract）是 2/4/5 的前置；2 是 3/6 的前置；QEMU（2）与 RTL/gem5（4/5）**同改异步仲裁语义**，QEMU 先行、RTL/gem5 等 M16 当前批次（`m16-qemu-003`、`m16-testcases-009`）收口后另立；`components/qemu` 与 `components/linux` 各自单写者；`spec/`+`.tao/contracts/` 由架构师同笔。

### D9 版本（已定：保持 0.8.0-rc，不升号）

**版本保持 `0.8.0-rc`（内容改、不升号）**：hart-first 虽是不兼容语义变更，但用户 2026-11-23 裁定**本次只改内容、不升版本号**。`spec/.manifests.toml` 只**重算受影响册**（`DADAO-12`/`DADAO-22`）的锁哈希，不升 `0.9.0`；`contract-see` 的版本/来源指针**不变**（版本号仍随上游册 `DADAO-12` 为 `0.8.0-rc`）。

## Rationale（理由）

- **为什么 hart-first 是正解**：异步现场/屏蔽/pending 单一归处（`cfx_hart`，per-hart），消除 monitor-first 的「四 monitor 分裂 + pending 不迁移」缝合口径；异步与同步彻底分流（hart 帧 vs monitor 帧），内核调度/抢占不再需要「monitor 帧内不得 schedule」特例。
- **为什么否 monitor-first**：四 monitor 入口 + 两级 mask + pending 分裂，内核要在 umon/smon 两套入口区分同步/异步，复杂度高且 `pending 不迁移` 口径是被迫缝合。
- **为什么否 target-first**：旧 contract/QEMU/kernel 口径，与 spec 冲突（已在 ADR-0059 否掉，沿用）。
- **为什么 cg9 独立于 cg5、返回复用 escape + frame selector**：cg5 是「同步异常帧」、cg9 是「异步现场」，帧数据分家；但返回指令不新增 opcode，而是在 `escape` 的 `imms18` 加一个 frame selector 位（bit1）复用现有指令，既能选帧、又不占新编码空间、不破坏 `escape` 的 SBZ/`cfxha=当前 cfx` 既有约束。
- **为什么 C1 用入口 cfx cg6 rc0/rc1、不引入上下文指针**：现有 `async_trap.S` 已用 `cfx_hart` cg6 scratch 捕获 GPR，hart-first 下入口 cfx 就是 `cfx_hart`，沿用最省；异步现场寄存器（cg9）保持「纯现场+mask」语义，不塞软件栈指针，栈指针继续走 per-hart 软件变量（`dadao_user_stack_top` 类）。

## Consequences（影响）

- 异步现场/屏蔽/pending 从 monitor 迁 `cfx_hart cg9`：spec §5.2/§3.x/§4.7/§4.9/§5.1/§5.3、contract-see、QEMU、RTL、gem5、kernel、工具链、测试探针全链同步。
- monitor 的 `<mode>_cfx_intr_mask`（cg0–3 rc4）与 `global_cfx_intr_mask`（cg8 rc1）失去异步用途（去留待 spec 任务定）。
- `escape` 复用 + frame selector 位（bit1）：`imms18` 合法集合改为 `{0,1,2}`（`3` ⇒ ILLI），不新增 opcode。
- `m18-qemu-002` 不合入、留参考分支；`m18-qemu-003` 被取代；`ADR-0059` Superseded。
- 版本保持 `0.8.0-rc`（不升号；`spec/.manifests.toml` 只重算受影响册）。

## 裁定记录（用户 2026-11-23 逐条确认，转 Accepted）

- **hart-first**：推翻 monitor-first（ADR-0059），异步统一进 `cfx_hart`（cfxha 15），新增 `cg9` 专用于异步现场，所有异步相关寄存器都在 cg9；硬件不支持嵌套、由软件处理 —— ✅ 确认。
- **cg9 寄存器表**：D2 表 16 项（rc0–rc12 + rc13–15 reserved）最终版逐项确认（无 `async_ctrl`/`async_sp`/`cause_info`/`async_src`/scratch/nest_depth；有效 = `cause_id != 0`；from_user = `prev_run_mode == user`）—— ✅ 确认。
- **C1**：GPR staging = 入口 cfx 的 `cg6 rc0/rc1`（hart-first 下即 `cfx_hart cg6 rc0/rc1`），不引入 async 上下文指针，用户态切栈继续 per-hart 软件变量（`dadao_user_stack_top` 类）—— ✅ 确认。
- **P1（pending 位）**：`async_pending` 位 = 源 **cause id**（`1<<17` TIMER / `1<<18` PMEM_DMA）；五个 mask 仍用来源 **cfxha**（15/32），两者不混用 —— ✅ 确认。
- **版本**：保持 `0.8.0-rc`（内容改、不升号）；`spec/.manifests.toml` 只重算受影响册；contract 版本指针不变 —— ✅ 确认。
- **B（escape 复用 + frame selector）**：不新增 `async_escape` opcode；在 `escape` 的 `imms18` 增 frame selector 位 = **bit1**（bit0 仍偏移；bit1=0 选 cg5、=1 选 cg9；cg9 只允许偏移 0 ⇒ `imms18 ∈ {0,1}` = cg5 0/+4、`imms18=2` = cg9 0、`imms18=3` ⇒ ILLI；`imms18[17:2]` SBZ；`cfxha` 仍 = 当前 cfx）—— ✅ 确认。
- **mask 全在 cg9**：`async_global_intr_mask` + 四个 per-mode mask 在 cg9；monitor 的 `<mode>_cfx_intr_mask`/`global_cfx_intr_mask` 异步用途作废（去留归 spec 任务）—— ✅ 确认。
- **RTL/gem5 节奏**：QEMU 先行，RTL/gem5 等 M16 当前批次收口后另立任务 —— ✅ 确认。
- **qemu-002/003 处置**：`m18-qemu-002`（monitor-first，reviewer Accepted）不合入、留参考分支；`m18-qemu-003` 同步标记被取代（不删代码历史）—— ✅ 确认。
- **pending 不迁移**：`async_pending` 跨模式切换不迁移、任务退出丢弃、依赖源重触发（hart-first 下归处唯一，实际无迁移动作）—— ✅ 确认。

## 实施注记

- **ADR-0059 Superseded 标记**：由主会话在本 ADR Accepted 后追加（保留 cause 17/18 与 mask 位索引=来源 cfxha 两条口径）；本笔不改 ADR-0059 正文。
- **m18-qemu-002 分支**：保留不合入，作 hart-first QEMU 任务的对照骨架。
- **m18-qemu-003**：被取代，旧异步探针迁移并入 hart-first 任务。
- **spec/contract/任务书/实现/版本**：本 ADR 只记决策，不改任何上述文件、不改版本号（版本保持 `0.8.0-rc`）。

## 状态说明

2026-11-23 起草（Proposed）→ 同日 Accepted：用户逐条确认 hart-first 投递模型、cg9 寄存器表、C1（cg6 GPR staging）、P1（pending 位 = cause id）、版本保持 `0.8.0-rc`、B（escape 复用 + frame selector bit1）、mask 全在 cg9、RTL/gem5 节奏、qemu-002/003 处置、pending 不迁移（裁定摘要见「裁定记录」）。
