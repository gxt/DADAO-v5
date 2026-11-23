# ADR-0061: 异步中断模型修订（掩码归 monitor、源索引统一 cfxha、cg9 精简为软件只读）

**状态**：Accepted（2026-11-23；用户确认"统一"并批准派发 `m18-spec-004`；D5 掩码更名、D6 pending 跟随源事件、D12 版本按本 ADR 草案执行，spec-004 复核时如与预期不符再改）；2026-11-23 R2 裁定修订 cg9 为捕获缓冲、`escape` 不再异步返回，见「R2 修订」段
**日期**：2026-11-23
**关联**：`ADR-0060`（Accepted；本 ADR 取代其 D2/D3 的 cg9 表与释放语义、D6 的掩码归属、D7 的「保留 cause 17/18」；D0/D1/D4/D5/D9 继续有效并 Super­sede 记录待 Accepted 后追加）；`ADR-0059`（已 Superseded）；`m18-spec-002`、`m18-qemu-004`、`m16-chipyard-021`、`m16-chipyard-020`；`ISS-500`、`ISS-498`

## Context（背景）

`ADR-0060`（hart-first）落地后，在 `m16-chipyard-020/021` 复核与模型讨论中暴露三处结构问题（用户 2026-11-23 逐条指出）：

1. **两套位索引 + 职责混淆**：`async_pending` 位 = 源 cause id（`1<<17`/`1<<18`），五个来源掩码位 = 源 cfxha（15/32）；`async_cause_id` 与 `async_pending` 的职责被混用，导致把「同一界面上多个源」误建模成「按 cfxha 串行投递两帧」。
2. **掩码归属错位**：异步来源掩码全在 `cfx_hart cg9`，运行模式无法"自己管自己能不能被打断"；而规范里原有的 `<mode>_cfx_intr_mask`（`cfx0`–`cfx3` 的 `cg0–cg3 rc4`）与 monitor 的 `global_cfx_intr_mask`（`cg8 rc1`）退化成僵尸字段——`trap` 还在保存/恢复后者（`§5.2` 第 5 步、`§5.3`），但它已"不参与投递判定"。
3. **"内容"兼作"有效位"**：`async_cause_id != 0` 同时表示"本帧有哪些源"和"帧是否有效"，于是 `§5.2（四）` 要求"释放帧应在 `escape` 之前"、`§5.3` 又判 `cause_id == 0 ⇒ CFXESC`，构成死循环；同时"清中断源"与"清帧"被混为一谈（各 ISA 的通行做法是：源在源处清除，帧由返回动作结束）。

## Decision（决策）

### D1 投递模型（沿用 ADR-0060 D0/D1）

所有异步源统一投递 `cfx_hart`（cfxha 15）的 **supv 单向量**（`cg9` 的 `excp_vector` + `switch_run_mode`=2）；pending/per-hart 单归处、不迁移。**不改**（向量投递模型沿用 ADR-0060；"无嵌套"由 R2 改为"嵌套由软件处理"，见 D4）。

### D2 源身份 = 源 cfxha（取消宏 cause）

- `async_pending` 与帧内源集合的**位索引统一为源 cfxha**（TIMER=15、PMEM_DMA=32），与掩码同索引。
- **取消** `1<<17`（TIMER）/`1<<18`（PMEM_DMA）两个宏 cause：异步不再有独立 cause 编号，**源即身份**；异常原因表里这两行改为"异步源标识（不占 `excp_cause_id`）"。
- **约束**：一个源 cfx 至多一个异步 cause；同源内的差异（DONE/ERROR、`ISTATUS`）回源 cfx 寄存器区分。

### D3 捕获缓冲（每次进入覆盖，一帧多源）

同一指令边界上，所有"pending 且被放行"的源**一次性**进入 cg9：`async_src_frame` = 这些位的并集，`async_src_pending` 扣除这些位；`excp_async_num` 每次进入 +1（与源个数无关）。不允许把同一 IP 的多个源拆成两次串行投递。

cg9 **只是异步进入瞬间的捕获缓冲**：每次异步进入 `cfx_hart` 都**整体覆盖** cg9，硬件**不因 `src_frame != 0` 拒绝进入或只置 pending**，也不存在"帧活动期"或 `frame_valid`。是否投递**只由当前运行模式 monitor 的掩码**决定（见 D5）。

### D4 入口流程与系统态策略

- `async_src_frame`（原 `async_cause_id` 更名）与 `async_src_pending`（原 `async_pending` 更名）一律 **HW 写 / SW 只读**，是**只读信息**，不承担"有效/释放"语义；`async_prev_run_mode`/`async_prev_cfx_code`/`async_cause_ip` 保持 HW/RW（"重建现场"用）。
- **入口流程**：异步进 hart 后，软件在**关中断窗口**把 cg9（`async_prev_*`/`async_cause_ip`/`async_src_frame`）+ GPR 拷到本任务 `task_pt_regs`，随后进入 `cfx_smon`（`trap cfx_smon` 或等价 handoff）。
- **`cfx_smon` 是普通系统态**：临界区屏蔽中断，正常运行允许中断；smon 中再来的 async 照常进 hart、覆盖 cg9，软件把它当**新的捕获**，**嵌套由软件自行处理**（必要时软件保存/恢复 cg5）。
- **用户态 async 与系统态 async 的区别只在处理方式**：用户态切内核栈 + 信号/调度；系统态在 kernel 栈直接处理 / 设 `need_resched`。
- cg9 捕获后被软件搬运完毕即**丢弃**，不再承担"活动帧/返回帧"角色；无"软件写 0 释放帧"路径，也无 `frame_valid`。

### D5 来源掩码归 monitor

- `cfx0` umon / `cfx1` jmon / `cfx2` smon / `cfx3` hmon 的 **`cg8 rc1`** 改为"**本运行模式的异步来源掩码**"：位 = 源 cfxha，`0=允许`、`1=屏蔽`，**复位初值全 1**（默认不放行）；建议更名 `cfx_<monitor>_async_intr_mask`。
- **删除** `cfx_hart cg9` 的五个掩码（原 `rc8`–`rc12`）；**删除**所有 cfx 的 `<mode>_cfx_intr_mask`（`cg0–cg3 rc4`）。
- `trap`/`escape` **不再保存/恢复**该掩码（它是策略，不是现场）；`§5.2` 第 5 步与 `§5.3` 对应句子删除。
- 投递时按**当前运行模式**取该模式 monitor 的掩码求值（取代"按到达时选行"）。

### D6 pending 语义：跟随源事件，不锁存、不计数

`async_pending` 表达"该源当前有未投递事件"：投递时由硬件清位；源在源 cfx 被 ack（`timer_cmp` 重装 / `dma_status` W1C）后自动落位。软件不写，也不依赖它计数（事件是幂等的，这正是异步 pending 的常规语义）。

### D7 `cfx_hart cg9` 精简为 7 槽，表移入 `§4.7`

| cg | rc | 字段 | 宽度 | 访问 | 说明 |
|----|----|------|------|------|------|
| 9 | 0 | `async_prev_run_mode` | 2b | HW/RW | 异步前运行模式 |
| 9 | 1 | `async_prev_cfx_code` | 6b | HW/RW | 异步前当前 cfx |
| 9 | 2 | `async_cause_ip` | 48b | HW/RW | 下一条指令地址（已提交的 `rb0`） |
| 9 | 3 | `async_src_frame` | 64b | HW/RO | 本次进入捕获到的源集合，位 = 源 cfxha（只读信息，无有效位） |
| 9 | 4 | `async_src_pending` | 64b | HW/RO | 未投递源集合，位 = 源 cfxha |
| 9 | 5 | `async_excp_vector` | 48b | RW | supv 异步向量（4B 对齐） |
| 9 | 6 | `async_switch_run_mode` | 2b | RW | 固定 supv（2） |
| 9 | 7–15 | reserved | — | — | 访问 ⇒ `CFXREG` |

- 删除 `async_saved_global_intr_mask`（掩码已不在 `cfx_hart`）。
- `src_frame`/`src_pending` 无任何 valid/clear 语义（硬件每次进入覆盖、软件只读）；`prev_*`/`cause_ip` 为 RW。
- 寄存器表从 `§3.9`（通用寄存器章节）**移到 `§4.7 cfx_hart`**。

### D8 异步不带 `cause_info`

`cfx_hart` 只记"哪些源"；handler 按帧内位回**源 cfx** 读寄存器（TIMER→`cfx_hart cg8 rc5`、PMEM_DMA→`cfx_pmem cg15 rc4`）或调用该 cfx 的系统功能。`§4.9` 去掉"`cause_info` 携带 `dma_status`"。

### D9 `escape` 编码不变，异步返回改走 smon→umon（R2 修订）

`escape imms18=2` **不再用于异步返回**：cg9 捕获后被软件搬运完毕即**丢弃**，返回用户走 smon/umon 正常路径。`escape` 编码本身不变——`imms18[1]` 帧选择位保留给未来/兼容（合法 `{0,1,2}`、`3` ⇒ `ILLI`、汇编层 `imms20 ∈ {0,4,8}`），sync/cg5 继续。

### D10 精确点写死

异步在指令边界识别，被中断指令**已提交**（`rb0` 已更新；`call` 已写 `ra63`、`ret` 已弹栈）；`async_cause_ip` = 提交后的 `rb0`（跳转即目标），软件据此重建返回现场、不重放（R2：不再由 `escape` 异步返回，见 D9）。`§5` 明写，并补"跳转后到期"向量。

### D11 文档结构

第 5 章新增**"异步中断进入与退出"专节**（来源过滤、捕获缓冲字段、一帧多源、mask/pending、入口搬运、系统态嵌套策略、返回、计数）；`§5.2`/`§5.3` 只保留同步并指向该节。

### D12 版本（沿用 ADR-0060 D9，待确认）

保持 `0.8.0-rc`（内容改、不升号），`spec/.manifests.toml` 只重算受影响册。

## Alternatives（被否方案）

- **串行投递多源**：pending 已能表达"还有事"；同一 IP 开两帧会把一次进入拆成两次上下文开销，且要求 spec 定义优先级（现 `§5` 的"低编号 cfxha 优先"）。
- **掩码留在 `cfx_hart`**：模式无法自管；且任何模式想屏蔽自己都要先获得 `cfx_hart` 访问权。
- **`cause_id`/`src_frame` 软件可写清除**：与捕获缓冲模型矛盾（源集合是硬件只读快照）；须另立 `frame_live` 位；用户裁定采用"硬件写、软件只读 + cg9 捕获后丢弃、`escape` 不异步返回"。
- **取消 `imms18[1]` 改 LIFO 隐含选择**：需新增"`cfx_hart` 有同步帧也挡异步"规则；用户裁定 `escape` 编码不变、异步返回改走 smon→umon（R2）。

## Consequences（影响）

- **spec/契约**：`DADAO-12 §1`（异常分流表述）、`§3.1–§3.4`（删 rc4）、`§3.6`（cause 表去 17/18）、`§3.9`→`§4.7`（cg9 七槽）、`§4.9`（去 cause_info）、`§5`（新增异步专节、`§5.2/§5.3` 收窄）、变更记录；`contract-see §3/§6.1.1/§6.3/§6.4`、`contract-isa`（escape 引用改名）、`contract-cfx-aliases`（regname 改名/删除）、`DADAO-22`（changelog 一条）、`DADAO-23`（若有引用）。
- **已合入代码需再修订（R2）**：`m18-spec-004`（已验证，按 R2 改写 `§5`/`§4.7`/`escape` 语义）、`m18-qemu-005`（已验证，按 R2 改 cg9 捕获/覆盖、去 `src_frame != 0` 防重入、`escape` 不异步返回）、RTL（`m16-chipyard-024` cfx_hart cg9 捕获缓冲 + 仲裁；`cfx0–3` 的 `cg8 rc1` 真掩码）。
- **在跑/在排任务需改写（R2）**：`m18-testcases-003`（探针迁新模型 + `escape` cg9 向量，按 R2 改）、`m18-linux-022`（内核异步新模型：入口搬 cg9+GPR 到 `task_pt_regs`、smon 嵌套、`escape` 不异步返回）。
- **测试**：新模型下"捕获缓冲覆盖""mask 在 monitor""smon 嵌套"各有新向量；旧探针的 `pending 17/18`、`五掩码`、`cause_id 写 0`、`escape 异步返回` 断言全部失效。

## 裁定记录（用户 2026-11-23）

- 掩码归 monitor（M）：✅
- 统一 cfxha 位、取消 `1<<17`/`1<<18` 宏 cause：✅
- 清中断源归源 cfx，"清"不从 `cfx_hart cg9` 角度设计：✅
- `src_frame`/`src_pending` 硬件写、软件只读：✅
- 掩码初值全 1：✅
- `escape` 暂不改：✅
- D5 掩码更名 `cfx_<monitor>_async_intr_mask` / D6 pending 跟随源事件 / D12 版本仍 `0.8.0-rc`：随本轮"统一"确认，按草案执行（2026-11-23）。
- 落地：`m18-spec-004`（已派单）→ `m18-qemu-005` / `m16-chipyard-024` → `m18-linux-021` 改写。

## R2 修订（2026-11-23，用户裁定）

用户裁定**修订 ADR-0061 即可**（不新立 ADR）。原话摘要与变更：

- **cg9 是捕获缓冲**：cg9 不再当"活动帧/返回帧"，只是**异步进入瞬间的捕获缓冲**；每次异步进入 `cfx_hart` 都**覆盖** cg9，硬件**不因 `src_frame != 0` 拒绝或只置 pending**，也不需要 `frame_valid` 或软件清 `src_frame`（见 D3/D4/D7）。
- **入口流程**：异步进 hart → 软件在**关中断窗口**把 cg9 + GPR 拷到本任务 `task_pt_regs` → 进入 `cfx_smon`（`trap cfx_smon`/等价 handoff）（见 D4）。
- **`cfx_smon` 是普通系统态**：临界区屏蔽中断，正常运行时允许中断；smon 中再来的 async 照常进 hart、覆盖 cg9，软件把它当新捕获并自行处理嵌套（必要时软件保存/恢复 cg5）；用户态 async 与系统态 async 的区别只在处理方式（用户态切内核栈、信号/调度；系统态在 kernel 栈直接处理/设 `need_resched`）（见 D4）。
- **`escape imms18=2` 不再异步返回**：cg9 捕获后丢弃，返回用户走 smon/umon 正常路径；`escape` 编码本身不变（sync/cg5 继续，`imms18[1]` 保留给未来/兼容）（见 D9）。
- **影响**：`m18-qemu-005`/`m18-spec-004`/`m18-testcases-003`/`m18-linux-022` 需再修订；**不新立 ADR**；状态保持 Accepted，版本仍 `0.8.0-rc`（不升号）。

