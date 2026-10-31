# INTEG-051t: 统一异步中断仲裁（pending 归目标 cfx，Linux 开发前）

**模块**：integ
**项目里程碑**：M10（Linux 开发前置独立项；M11 未定义，暂挂 M10，待用户确认）
**依赖**：`INTEG-050t`（`cfx_time` + 单 hart `cfx_hart` 定时器，状态 `待开始`；本任务**必须在其 `已验证` 后**开工）
**状态**：待开始

> **开工门槛**：`INTEG-050t` 未 `已验证` 前不得 `/dispatch`。050 交付的是「单来源异步路径 + 两个独立 `bool`」，本任务把这两个 `bool` 换成**目标 cfx 的既有 `cg5 rc5 pending`** 并把投递收成一处仲裁；050 的探针（17 例）、`contract-see` 条目与 QEMU 补丁是本任务的基线。

## 执行环境

**执行环境**：本地（仓库 `DADAO-v5`，050 收尾后从 `master` 新建分支 `INTEG-051t`）。QEMU 走 `.work/source/qemu` → 补丁树 → `make build-qemu` / `make install-host`（见「约束」）。

## 背景

1. **050 的边界（已定）**：`cfx_time`（cfxha 18）与单 hart `cfx_hart`（cfxha 15）定时器只**复用**既有单来源异步路径：`pmem_dma_irq` 同型的 per-source `bool` + `CPU_INTERRUPT_HARD` + `dadao_cpu_exec_interrupt()` 独立分支 + `cfx_enter(async)`。050 明确**不做**跨源仲裁，只留一句「某分支投递后若另一源标志仍置位则不清 `CPU_INTERRUPT_HARD`」的最小补丁。
2. **现状即空洞**：两个 `bool` 各自为政 ⇒ 无统一 pending 视图、无源优先级、被 mask 挡住时**源侧 `bool` 已清**且只在目标 cfx 留 `cg5 rc5 pending`，**mask 解除后没有任何重投触发**（PMEM_DMA 侧 042 探针只验到「记录 pending」）；两源同轮到达的投递顺序纯靠代码书写顺序。
3. **收口方向（2026-10-31 修订：不集中 pending）**：spec §5 本来就把「投不出去」记在**目标 cfx** 的 `cfx_⟨cfxname⟩_excp_pending`（`env->cfx[ci].pending`，`cg5 rc5`）。缺的不是「一张聚合位图」，而是①「谁能把目标 cfx 的 pending 变成一次投递」②「什么时候重新踢一次」。⇒ **pending 留在目标 cfx**，`cfx_hart` **只做仲裁/选择**，不保存跨 cfx 聚合位图。

## 目标（范围）

1. **pending 归目标 cfx（唯一记录）**：`PMEM_DMA(1<<8)` 记在 `cfx_pmem`(17) 的 `cg5 rc5`，`TIMER(1<<10)` 记在 `cfx_hart`(15) 的 `cg5 rc5`；S/H 目标天然分开。**不新增位图、不新增状态字段、不新建 cfx**。
2. **源投递（deposit）**：异步源只置**目标 cfx** 的 pending 位并踢一次 `CPU_INTERRUPT_HARD`（`PMEM_DMA`→`cfx_pmem`，`TIMER`→`cfx_hart`）；不在此处跑 `cfx_enter`，不再维护 per-source `bool`。
3. **仲裁（唯一入口）**：`dadao_cpu_exec_interrupt()` 只调一个仲裁函数；仲裁按**目标 cfxha 升序**（15→17）扫描 pending 位，对第一个能投递的源跑一次 `cfx_enter(async)` 到**其目标 cfx**；`cfx_hart` 只做选择/踢，**不执行目标 handler**。
4. **单层投递**：一次 `exec_interrupt` 至多投递一个源，不嵌套、不做异步帧分离；第二个源在第一个 handler `escape`（全局 mask 恢复）后由踢点再投。
5. **屏蔽语义**：复用 `global_cfx_intr_mask`（当前模式 monitor 总闸）+ `cfx_intr_mask`（当前 cfx 的 `inner_run_mode` 行、**位索引=目标 cfxha**），**不新增 `async_enable`**；mask 只阻止投递，pending 位保留，**解除后补投**。
6. **补投踢点**：`cfx2rc` 通用写（覆盖所有 mask/`excp_cause_mask`/pending 写）、`cfx_hart cg8 rc5` 写（IMASK 释放）、`escape`（全局 mask 恢复）、源事件（DMA 完成、定时器到期）后，若仍有可投候选则重踢 `CPU_INTERRUPT_HARD`。
7. **零回退**：050 探针 17 例、`integ042t`（25 例）与既有 cfx 探针全部保持绿；`cg5 rc5` 的 TIMER bit10 语义不变（050 探针依赖）。
8. **契约与登记**：`contract-see` 补「统一仲裁（测试机约定）」条目并纠正 cfx_pmem 异步句措辞；QEMU `changelog` 1 条；`Makefile`/arch `README.md` 登记新探针。

**明确不做**：不做 IPI；不做多 hart / 多 hart 同步；不做生产 SBI provider；不做嵌套投递/异步帧分离；**不改 `cfx_enter()` 与其掩码判定**；不改 `spec/**`（本任务零 spec 改动，见「预检 5」）；不改 LLVM；不改 `cg7`/两轴权限/tlb_fill/PMEM DMA 传输逻辑；不跑夜跑；不实现（本任务书只立规划）。

## 问题根源

1. **050 的 `exec_interrupt` 是"顺序 if"，不是仲裁**：两源各持 `bool`，同轮到达只能靠"别清 HARD"在下一轮补；无优先级、无统一 pending 视图、无法观测"谁在前"。
2. **mask 后的源事件会丢**：050/042 的路径在 `cfx_enter` 被 mask 挡住时只写目标 cfx 的 `cg5 rc5 pending`，源侧 `bool` 已清；mask 解除时没有代码再看它 ⇒ 永不补投。把 pending 视为**唯一记录**、mask 只用来看"此刻能不能投"，事件与投递才解耦。
3. **掩码公式被复制即漂移**：`cfx_enter` step 3/4/5 已完整实现「inner_cfx_mask / `cfx_intr_mask`+`global_cfx_intr_mask` / `excp_cause_mask`」。若仲裁再写一份"预检查"，两处只要有一处改动就会打架。⇒ 仲裁**只做选择**，掩码判定**唯一真源是 `cfx_enter`**，用其 `entered` 返回值决定"投递成功/保留 pending"。
4. **屏蔽只有两级、没有源内开关**：`global_cfx_intr_mask` + `cfx_intr_mask` 已足够表达"当前上下文能否收这个源"；再引入 `async_enable` 会与 spec §5 step 4 的既有语义重复。

## 已确认设计（用户给定，逐条落纸）

**用户授权原话（首轮派单）**——下列第 2、3 条已被 2026-10-31 修订取代（见「追加裁定」），保留原文以备溯源：

> “在 `/tmp/opencode/INTEG-051t/repo`（分支 `INTEG-051t`，基于 `658b9723`）创建 `INTEG-051t` 任务书：统一异步中断仲裁（Linux 开发前）。只写任务书，不实现。”
> “背景/已确认设计：050 只做 `cfx_time` + 单 hart `cfx_hart` timer，复用单来源异步路径，不做统一仲裁。本任务作为 Linux 开发前的独立项，把 `PMEM_DMA` + `TIMER` 收进统一 per-hart pending/仲裁。”
> “仲裁位置：`cfx_hart` 内置 per-hart pending；**不新建 cfx、不经过 smon/hmon 中转**。”
> “异步源投递：直接进入目标 cfx（`PMEM_DMA`→`cfx_pmem`，`TIMER`→`cfx_hart`）；`cfx_hart` 只做 pending/优先级选择，不执行目标 handler。”
> “目标 cfx 的运行模式由各 mode 行 `switch_run_mode` 固定，不存在 supv/hypv 歧义；仲裁不携带 target_mode。”
> “屏蔽：复用 `global_cfx_intr_mask`（当前模式 monitor 的全局总闸）+ `cfx_intr_mask`（目标 cfx 来源过滤）；**不增加 `async_enable`**。”
> “优先级：多个 pending 同时可投递时，按低 cfxha 优先；单层投递，不做嵌套、不做异步帧分离。”
> “pending 保留：mask 只阻止投递，源仍可置 pending；解除后补投。”
> “不做 IPI/多 hart/多 hart 同步；不做生产 SBI provider。”

**追加裁定（2026-10-31，本轮修订依据，原样落纸）**：

> “**不集中 pending**；pending 留在目标 cfx 的 `cg5 rc5`（现有 `cfx[ci].pending`）。”
> “`cfx_hart` 只做仲裁/选择，不保存跨 cfx 聚合位图。”
> “`PMEM_DMA` pending 在 `cfx_pmem`；`TIMER` pending 在 `cfx_hart`；S/H 目标各自 pending 天然分开。”
> “`cfx_intr_mask` 保持现有语义：当前 cfx 的 `inner_run_mode` 行、按 target cfxha 位过滤。”
> “`global_cfx_intr_mask` 保持当前模式 monitor 总闸；不加 `async_enable`。”
> “目标 cfx 的 `switch_run_mode` 已固定，不携带 target_mode；直接进目标 cfx。”
> “删除「cfx_hart 内置 per-hart 聚合 pending/位图」方案；改为「per-target-cfx pending + cfx_hart 只扫描仲裁」。”

口径落点：

1. **pending 只有一份，且在目标 cfx**：`env->cfx[ci].pending`（`cg5 rc5`）既承担 spec §5 的挂起记录，也承担"源事件已发生、尚未投递"的记录；**不存在第二份位图**。
2. **位索引 = 目标 cfxha**：`cfx_intr_mask` 与 `global_cfx_intr_mask` 判 `1ULL << target`（TIMER 15、PMEM_DMA 17），取**当前 cfx**（`inner_cfx_code`）的 `inner_run_mode` 行 + 当前 mode monitor（`cfx[inner_run_mode & 0x3]`）。这与 `cfx_enter` step 4 现文（`helper.c`：`cur_mask & (1ULL << target)`、`global_mask & (1ULL << target)`）**逐字一致**，也与 §5 伪代码 `1 << temp_cfx_code`（异步时=目标 cfx）一致。首轮稿的「取行口径待确认」**已消除**：不是"源 cfx 15/17 自己的 mask"。
3. **优先级 = 目标 cfxha 升序**：15 先于 17；后续源（IPI 等）沿同一规则。
4. **mask 是投递前过滤，不是丢弃**：被挡的源保留 pending 位；mask 写与 `escape` 都是重踢点。
5. **不新增源内总开关**：`async_enable` 类寄存器/字段一律不出现；TIMER 的 `IMASK` 属定时器自身控制（050 已定），继续作为该源的**本地投递门**（不属两级 mask）。
6. **目标由源决定**：`TIMER` 目标恒 `cfx_hart`(15)、`PMEM_DMA` 目标恒 `cfx_pmem`(17)；运行模式由各 mode 行 `switch_run_mode` 决定，仲裁**不携带 `target_mode`**、不做 mode 推断。
7. **投递成功清 pending 位**：不清则同一源会被反复投递（源事件是边沿）；软件写 `cg5 rc5` 的 0 即「取消」——因只有一份记录，不存在旧稿的"位图还在、cg5 已清"双写。

## 寄存器 / 内部状态

**架构寄存器：零新增**（不新增 cfx、不新增 cg/rc、不改 `DADAO-12`/`DADAO-22`）。复用：

- 目标 cfx 的 `cg5 rc5` `excp_pending`：**唯一**异步 pending 记录（`cfx_hart` bit10 = TIMER、`cfx_pmem` bit8 = PMEM_DMA）；源事件置位、投递成功清位、软件可写 0 取消。
- `cfx0–cfx3` `cg8 rc1` `global_cfx_intr_mask`：当前模式 monitor 的源总闸（位索引=目标 cfxha，1=屏蔽）。
- 当前 cfx 的 `cg0–cg3 rc4` `cfx_intr_mask`（按 `inner_run_mode` 选行）：当前 cfx 的源过滤（1=屏蔽）。
- `cfx_hart cg8 rc4/rc5`（`timer_cmp`/`timer_ctrl`）：`ENABLE`/`IMASK`/`ISTATUS` 语义不变。

**QEMU 内部状态：零新增字段**：

- **不新增** `hart_async_pending`（首轮稿方案已删除）、不新增优先级表、队列、深度计数、`async_enable`。
- 删除 050 的 `bool pmem_dma_irq;` 与 `bool hart_irq;`（其职责由目标 cfx 的 pending 位承担）；`pmem_dma_irq_en`、`hart_timer_*`、`time_base_ns` 等保持。
- 复位：`pending` 已由 `dadao_cfx_reset()` 的 `r->pending = 0` 覆盖，只需删两 `bool` 的复位行。

## 仲裁算法（QEMU 实现）

**候选表（升序，单 hart 唯一实例）**：`{ DADAO_CFXHA_HART(15)=DADAO_CAUSE_TIMER(1<<10), DADAO_CFXHA_PMEM(17)=DADAO_CAUSE_PMEM_DMA(1<<8) }`。

**函数划分（`target/dadao/helper.c`，`#ifndef CONFIG_USER_ONLY`，紧邻 050 的 cfx_hart 段）**：

- `static int dadao_async_lowest(CPUDADAOState *env)`：按候选表升序返回**最低可投候选源 cfxha**，无则 `-1`；判定 =「该源在**其目标 cfx** 的 pending 位为 1」∧「源本地门开」（仅 TIMER：`hart_timer_ctrl & IMASK` 为真 ⇒ 不可投）。**不判两级 mask**（见下）。
- `static void dadao_async_kick(CPUDADAOState *env)`：`if (dadao_async_lowest(env) >= 0) dadao_hart_notify(env_cpu(env));`（复用 050 的 `dadao_hart_notify`：持 BQL 用 `cpu_interrupt`，不持用 `cpu_set_interrupt`）。
- `bool dadao_async_arbitrate(CPUState *cs)`：返回是否**成功投递一次**。
- 删除 `dadao_pmem_dma_deliver()` / `dadao_hart_timer_deliver()`（并入仲裁，保证 async `cfx_enter` 只有一处调用点）。

**`dadao_async_arbitrate()` 步骤**：

```
for (i = 0; i < 2; i++) {                        /* 目标 cfxha 升序: 15, 17 */
    src   = cand[i].src;  cause = cand[i].cause;
    ci    = cfx_idx(src);            if (ci < 0) continue;
    if (!(env->cfx[ci].pending & cause))            continue;   /* 该源无事件 */
    if (src == DADAO_CFXHA_HART &&
        (env->hart_timer_ctrl & DADAO_HART_TIMER_IMASK)) continue;  /* 源本地门 */
    info  = (src == DADAO_CFXHA_HART) ? 0 : env->pmem_dma_status;
    vec   = cfx_enter(env, cause, src, env->pc, info, /*sync=*/false, &entered);
    if (!entered) continue;      /* step 3/4/5 挡住：cfx_enter 已保留 pending，试下一个源 */
    env->cfx[ci].pending &= ~cause;                  /* 投递成功：清唯一记录 */
    env->pc = vec; env->rb[0] = vec;
    return true;                                     /* 单层：一次调用至多投一个 */
}
return false;
```

要点：

- **掩码唯一真源 = `cfx_enter`**：step 3（`inner_cfx_mask`）/ step 4（`cfx_intr_mask` + `global_cfx_intr_mask`，位=目标 cfxha）/ step 5（`excp_cause_mask`）已实现全部判定；仲裁**不复制**掩码公式（首轮稿的 `deliverable()` 预检删除，理由见「问题根源 3」）。
- **被挡的源不阻塞其它源**：§5 是逐事件判定，低 cfxha 被挡而高 cfxha 可投时投高的那个（与首轮「`cand = pending & ~mask` 再取最低」等价）。
- **不成功即无副作用**：`cfx_enter` 被挡时只做 `pending |= cause`（同一位，幂等），不改进程状态。
- **不轮询/不自旋**：被挡后靠踢点重投（见下）。

**`dadao_cpu_exec_interrupt()` 收口**：

```
if (!(interrupt_request & CPU_INTERRUPT_HARD)) return false;
delivered = dadao_async_arbitrate(cs);
cpu_reset_interrupt(cs, CPU_INTERRUPT_HARD);   /* 单层、防自旋；pending 位即重投依据 */
return delivered;
```

- 投递成功后"第二个源"由 `escape` 恢复全局 mask 时踢出（`cfx_enter` 进入帧会把 entry-mode monitor 的 `global_cfx_intr_mask` 置全 1（D9），故帧内必然挡住其它源 ⇒ **结构上不可能嵌套**）。

**源侧改造**：

- DMA 完成（`IRQ_EN=1`）：`env->cfx[cfx_idx(DADAO_CFXHA_PMEM)].pending |= DADAO_CAUSE_PMEM_DMA; dadao_async_kick(env);`；删 `pmem_dma_irq = true`。
- 定时器到期：`ISTATUS` 计算不变；`IMASK=1` ⇒ 只置 `cfx[hart].pending |= TIMER`（不踢）；`IMASK=0` ⇒ 置位 + `kick()`；删 `hart_irq = true`。
- 写 `timer_cmp`：取消旧 deadline、清 `cfx[hart].pending` 的 TIMER 位（050 的"取消"语义），不踢。
- 写 `timer_ctrl` 使 `IMASK=0` 且 `ISTATUS=1`：保留 pending 位（必要时补置）+ `kick()` ⇒ 由仲裁完成投递（050「释放即投递」语义零回退）。

**补投踢点（四类，缺一则"解除后补投"不成立）**：

1. `helper_cfx2rc()` **通用写尾**（`env->pc = pc + 4;` 之前）——覆盖 `cfx_intr_mask`/`global_cfx_intr_mask`/`excp_cause_mask`/`pending` 的全部写；
2. `dadao_hart_reg_write()` 的 `rc4`/`rc5` 写（该分支**早返回、不过通用尾**）：`rc5` 释放 IMASK 时置位 + kick，`rc4` 只清位不踢；
3. `helper_cfx_escape()` step 1 恢复 `global_cfx_intr_mask` 之后；
4. 源事件（DMA 完成、定时器到期）。

（`cfx_pmem cg15` 的早返回分支不改 pending，无需踢；trap 进入把全局 mask 置全 1，不需踢；`cfx_enter` step 8 换 `inner_cfx_mask` 只发生在投递内部。）

## 异常 / 掩码语义

1. **两级 mask 的位索引 = 目标 cfxha**（TIMER 15 / PMEM_DMA 17），0=允许、1=屏蔽；`cfx_intr_mask` 取**当前 cfx**（`inner_cfx_code`）的 `inner_run_mode` 行，`global_cfx_intr_mask` 取 `cfx[inner_run_mode & 0x3]`；判定顺序与结果以 `cfx_enter` step 3/4/5 为准（不另写）。
2. **mask 只阻止投递**：源事件照常置位；仲裁返回 false 时清 `CPU_INTERRUPT_HARD` 但不丢 pending 位。
3. **补投触发点**：见上「四类踢点」。
4. **单记录分工**：pending 既是 spec §5 挂起记录、也是调度依据；硬件置位（源事件）+ 硬件清位（投递成功），软件写 0 = 取消。**无双记录**（首轮稿「位图 vs cg5 双写」风险随之消失）。
5. **同源重复事件合并**：一个 cause 一个 bit（OR 语义，spec 既有）⇒ 屏蔽期两次 DMA 完成 = 解除后 1 次投递；**由寄存器语义直接推出，不需另议**、不做计数队列。
6. **`cause_info`**：TIMER 恒 0；PMEM_DMA = 投递时刻的 `dma_status`（与 050 一致；屏蔽期间若再启动新 DMA 会覆盖 `dma_status` ⇒ 既有单源限制，登记风险，不在本任务快照化）。
7. **不嵌套**：见「仲裁算法」末条（D9 结构保证）。
8. **user-mode**：仲裁/踢/源事件整体 `#ifndef CONFIG_USER_ONLY`；`cfx2rc` 尾部 kick 同样条件编译；`dadao-linux-user` 必须编译通过。

## 接口规范

### 1. `components/qemu/patches/target/dadao/cpu.h.patch`

- 删 `bool pmem_dma_irq;`、`bool hart_irq;`；**不新增任何异步状态字段**（无 `hart_async_pending`、无位图、无 `async_enable`）。
- 声明 `bool dadao_async_arbitrate(CPUState *cs);`；删 `dadao_pmem_dma_deliver` / `dadao_hart_timer_deliver` 的声明（实现并入仲裁）。不改 `helper.h`。

### 2. `.../cpu.c.patch`

- `dadao_cpu_exec_interrupt()`：替换 050 的「PMEM 分支 + TIMER 分支 + 互不清 HARD」为「一次仲裁 + 无条件 `cpu_reset_interrupt`」；注释改写为「pending 归目标 cfx、`cfx_hart` 只仲裁」（删掉 "no unified pending bitmap" 的旧表述）。
- `dadao_cpu_reset_hold()`：删两 `bool` 的复位（`pending` 已由 cfx 复位循环覆盖）。
- `dadao_cpu_realizefn()`：不改（050 的 `dadao_hart_timer_init` / `dadao_pmem_dma_init` 保留）。

### 3. `.../helper.c.patch`

- 新增 `dadao_async_lowest/kick/arbitrate`（紧邻 050 的 cfx_hart 段）；文件头/段注释把 050 的 "no unified pending" 说明改为「pending 归目标 cfx 的 cg5 rc5；cfx_hart 只做选择」。
- 删除 `dadao_pmem_dma_deliver()` / `dadao_hart_timer_deliver()`。
- `dadao_pmem_dma_complete()`：`IRQ_EN` ⇒ `cfx_pmem.pending |= PMEM_DMA` + kick；删 `pmem_dma_irq=true`。
- `dadao_hart_timer_expire()` / `dadao_hart_reg_write()`：见「源侧改造」。
- `helper_cfx2rc()`：通用写尾追加 `dadao_async_kick(env)`；`helper_cfx_escape()`：step 1 之后追加同调用（均 `#ifndef CONFIG_USER_ONLY`）。
- `cfx_enter()`、`cfx_reg_ptr()`、`helper_cfx2rd` 的只读分支、权限门序：**不动**。

### 4. 新探针 `tools/testcases/arch/min_rom_probe_integ051t.py`

布局沿用 `min_rom_probe_integ050t.py`（编码器/`Asm`/`run()`/`observe()`/`bootstrap_rom()` **就地复制**，不改 050 探针）；`--qemu/--only/--list/--doc/--inject`；期望值手推自 `DADAO-12 §5`（两级 mask、pending、位索引=目标 cfx）、`§4.7/§4.9`（cause id/info）、`contract-see` 的仲裁条目。

**bootstrap（在 050 的 5 步之上追加）**：① 同 050 清 `cfx_hmon hypv_switch_cfx_mask` bit15 与 bit18；② hmon 内清 `cfx_hmon hypv_cfx_intr_mask`/`global_cfx_intr_mask` 的 bit15/17、清 cfx_pmem 与 cfx_hart 的 `hypv_cfx_intr_mask` 位；③ 清 cfx_pmem `hypv_excp_cause_mask` bit8、cfx_hart `hypv_excp_cause_mask` bit10；④ 装 cfx_pmem 与 cfx_hart 的 `hypv_excp_vector`（各自 handler 记录 cause/顺序/重入标志到 RAM 状态块后 `escape`）；⑤ 装 `cfx_hmon hypv_excp_vector` 为 **poison**（写 FAIL 退出码）用于「不经过 hmon 中转」断言；⑥ 清 cfx_power 四 mode 的 cfxmem/cfxexe（同 050）。

**用例（14 条，每条须有可达 FAIL 路径）**：

1. `doc_shape`（离线）：`contract-see` 含「统一仲裁」条目（pending 归目标 cfx、位索引=目标 cfxha、低 cfxha 优先、单层、mask 保留/补投、去重）且无 `async_enable`；补丁树无跨 cfx 聚合位图（`hart_async_pending` 不存在）。
2. `pmem_pending_in_pmem`（icount）：`global_cfx_intr_mask` 屏蔽 bit17 期间 DMA 完成 ⇒ `cfx_pmem cg5 rc5` bit8=1、`cfx_hart cg5 rc5` bit8=0；清位后 cfx_pmem handler 恰 1 次、`cause_id=1<<8`、`cause_info=DONE`、bit8=0。
3. `timer_pending_in_hart`（icount）：屏蔽 bit15 期间 TIMER 到期 ⇒ `cfx_hart cg5 rc5` bit10=1、`cfx_pmem cg5 rc5` bit10=0；清位后 cfx_hart handler 恰 1 次、`cause_id=0x400`、`cause_info=0`。
4. `pending_no_cross_cfx`（icount，S/H 不混）：两源分别被屏蔽 ⇒ `cfx_hart.pending` 只含 bit10、`cfx_pmem.pending` 只含 bit8（按位与断言）；先解 bit15 只投 TIMER 且 `cfx_pmem.pending` bit8 原样保留，再解 bit17 投 PMEM。
5. `global_mask_block`（icount）：仅屏蔽 bit15 ⇒ TIMER 不投、DMA 仍投（按源位而非全屏蔽）；清位后 TIMER 补投恰 1 次。
6. `per_cfx_mask_block`（icount）：hmon `hypv_cfx_intr_mask` bit17=1 ⇒ DMA 不投、TIMER 仍投；清位后 DMA 补投恰 1 次。**同例反向断言**：`cfx_pmem` 自己的 `hypv_cfx_intr_mask` bit17 置 1 不影响投递（证明读的是**当前 cfx** 行、位=**目标 cfxha**）。
7. `cause_mask_block`（icount）：cfx_pmem `hypv_excp_cause_mask` bit8=1 ⇒ 不投且 `cfx_pmem.pending` bit8=1；清位后补投恰 1 次（验 `cfx2rc` 通用尾踢点）。
8. `timer_imask_hold`（icount）：`IMASK=1` 到期 ⇒ 不投、`cfx_hart.pending` bit10=1；写 ctrl 释放 ⇒ 恰 1 次、bit10=0（050 语义零回退）。
9. `low_cfxha_first`（icount）：用 `global_cfx_intr_mask` 同时屏蔽 bit15/17 期间积累两源，单次写清 mask ⇒ 到达序列 `[0x400, 0x100]`，各恰 1 次；handler 用 RAM 重入标志断言无嵌套、且第二源在 `escape` 之后到达。
10. `escape_kick`（icount）：进入 cfx_pmem 帧后（全局 mask 全 1）定时器到期 ⇒ 帧内不投；`escape` 后 TIMER 恰 1 次。
11. `direct_target`（icount）：cfx3 的 `hypv_excp_vector` = poison；两源均到达各自目标 handler、poison 未执行；handler 读本 cfx `cg5 rc2` 得到各自 cause；cfx3 `cg4 rc4`（async 计数）前后不变。
12. `no_async_enable`（离线）：补丁树 grep 无 `async_enable`；仲裁无"预检查掩码"副本（结构断言：只有一处 `1ULL << target` 类掩码表达式，且位于 `cfx_enter`）。
13. `dedup_same_source`（默认时钟）：屏蔽期间两次 DMA 完成 ⇒ 解除后恰 1 次投递（单 bit OR 语义）。
14. `pmem_error_info`（默认时钟）：制造 `PA_FAULT` 且 `IRQ_EN=1` ⇒ `cause_id=1<<8`、`cause_info = ERROR|ERR_CODE`。

**观测**：寄存器类用 `-d cpu` 末块；定时器/双源类用 `-icount shift=0` + 程序内自检退出码（0x00 通过，每例独立 FAIL 码），不得以 dump 缺失为由跳过。

### 5. 契约 / 登记

- `.tao/contracts/contract-see.md`：
  - 新增一条**测试机约定**条目：`cfx_hart` **不保存跨 cfx 聚合 pending**；`TIMER(1<<10)` 记在 `cfx_hart` 的 `cg5 rc5`、`PMEM_DMA(1<<8)` 记在 `cfx_pmem` 的 `cg5 rc5`（源事件置位、投递成功清位、软件写 0 即取消）；`dadao_cpu_exec_interrupt()` 每次只投递一个源，按**目标 cfxha 升序**选择，不嵌套；被 `cfx_intr_mask`（当前 cfx 的 `inner_run_mode` 行，**位索引=目标 cfxha**）/`global_cfx_intr_mask`（当前 mode monitor）/`excp_cause_mask`/TIMER `IMASK` 挡住时保留 pending，mask 写、`escape`、新源事件后补投；同源重复事件合并为一次；目标 cfx 直接投递（不经 monitor）；不引入 `async_enable`；`cause_info` 为投递时刻值（DMA 期间再启动会覆盖）。
  - 修正既有 `cfx_pmem` 异步句（现 `contract-see:39`「单 hart 直接投递 `cfx_pmem`」）与两级过滤句（`:50`）：补「pending 归目标 cfx、位索引=目标 cfxha」。
  - 来源标 `[DADAO-12 §5. 异常进入与异常退出][DADAO-12 §4.7 cfx_hart][DADAO-12 §4.9 cfx_pmem][ADR-0045 D3]`。
- `components/qemu/changelog.md`：`## M10` 节末追加 1 条（`- **2026-10-31 \`INTEG-051t\`**` + 摘要 + 执行者 engineer）。
- `Makefile`：`ARCH_CFX_PROBES` 末尾追加 `integ051t`（050 已先行追加 `integ050t`）。
- `tools/testcases/arch/README.md`：表格补 `min_rom_probe_integ051t.py` 一行，`--qemu` 名单补 `integ051t`。

## 修改文件范围

**必改（10 项）**：

1. `components/qemu/patches/target/dadao/cpu.h.patch`
2. `components/qemu/patches/target/dadao/cpu.c.patch`
3. `components/qemu/patches/target/dadao/helper.c.patch`
4. `tools/testcases/arch/min_rom_probe_integ051t.py`（新增）
5. `Makefile`
6. `tools/testcases/arch/README.md`
7. `components/qemu/changelog.md`
8. `.tao/contracts/contract-see.md`
9. 本任务书（完成区 + 状态）
10. `.tao/knowledge/milestones.md`（仅本任务流水行状态）

**条件项（预期不改）**：`tools/testcases/arch/min_rom_probe_integ050t.py`——仅当 050 探针把「两源顺序/掩盖」写死、与仲裁冲突时才动，且**不得放宽断言**；动则须在完成区说明依据。`components/qemu/series` 不改（三份补丁文件已存在，无新增补丁文件）。

**明确不动**：`spec/**`（零改动）、`manifests/**`、`components/llvm-project/**`、`tests/**`（含 `tests/arch*`、`tests/inst/**`）、`.tao/adr/**`、`.tao/knowledge/discussing.md`、`docs/**`、`target/dadao/helper.h`、`target/dadao/translate.c.patch`、**`cfx_enter()`**、权限门序、`cfx_reg_ptr()`。

## 约束

1. **不集中 pending**：pending 只在**目标 cfx** 的 `cg5 rc5`；`cfx_hart` 不得保存跨 cfx 聚合位图/队列；不新建 cfx、不借 `smon`/`hmon` 向量转发（探针用 poison 向量机械断言）。
2. **不新增 `async_enable`/状态字段**：屏蔽只用 `global_cfx_intr_mask` + `cfx_intr_mask`；TIMER 的 `IMASK` 保持 050 语义。
3. **掩码判定不复制**：仲裁不得实现第二份 `cfx_intr_mask`/`global_cfx_intr_mask`/`excp_cause_mask` 判定；一律以 `cfx_enter` 的 `entered` 为准（改判定只改 `cfx_enter`）。
4. **单层、不嵌套**：一次 `exec_interrupt` 至多一次成功的 `cfx_enter`；禁止在同一调用里连续投递两个源；不写异步帧分离。
5. **不丢不重**：mask 只挡投递；投递成功必须清该目标 cfx 的对应 pending 位；不得用轮询/延时伪造投递。
6. **补丁唯一来源**：改 `.work/source/qemu` → 收敛 base+1 → `python3 tools/infra/make_patch.py qemu`；**禁手改补丁**；`make check-patch-tree` + `make check-source-state` 绿。
7. **构建纪律**：只改 `.c/.h` ⇒ `make build-qemu` 增量（估算 1–3 min）+ **必须补跑 `make install-host`**（`ISS-210`）；安装根与构建树 `qemu-system-dadao` md5 必须相同；禁手工 `ninja`/手工 `cp`；若触发 reconfig/全量 ⇒ 停手上报。
8. **临时目录** `/tmp/opencode/INTEG-051t/`；长日志 `.work/log/integ/`；仓库内不得留 `*_tmp*`/`_gate*`/`*.orig`/`*.rej`。
9. **证据**：`.work/evidence/INTEG-051t/run.sh`（`--default`/`--inject`/`--full`）；至少 1 项代码注入「注入→FAIL→还原→绿」，还原用 `cp`+md5，**禁** `git checkout/restore/stash/show`。
10. **零回退**：050 探针、`integ042t` 与既有 cfx 探针逐项贴 `[PASS]`；`cg5 rc5` TIMER bit10 语义不变。
11. **完成区与真实输出逐条对齐**；不提交/push（提交权归 architect）。**不跑夜跑**。

## 验收标准

1. **文件集精确（10 项）**：`git diff --name-only master...HEAD` 仅含上列 10 项 + 条件项（若触发须有说明）；`spec/**`、`tests/**`、`components/llvm-project/**`、`.tao/adr/**` 零改动；越界即 FAIL。
2. **无新增状态**：补丁树 `grep` 对 `hart_async_pending`、`async_enable` 零命中；`pmem_dma_irq`/`hart_irq` 零命中（贴输出）。
3. **pending 归目标且唯一**：`pmem_pending_in_pmem`/`timer_pending_in_hart`/`pending_no_cross_cfx` 三例证明「bit 落在目标 cfx、跨 cfx 位为 0、投递后清零」。
4. **单一仲裁入口**：`dadao_cpu_exec_interrupt()` 只调一次 `dadao_async_arbitrate`（贴片段）；补丁树 async `cfx_enter` 调用点唯一（在 arbitrate 内）；`dadao_*_deliver` 已删（grep 零命中）。
5. **无掩码副本**：仲裁内不含 `cfx_intr_mask`/`global_cfx_intr_mask`/`excp_cause_mask` 的判定表达式（`no_async_enable` 离线断言 + 人工核对片段）。
6. **优先级/单层**：`low_cfxha_first` 到达序列 `[0x400, 0x100]`、各 1 次、无重入；第二源在 `escape` 后到达。
7. **mask 语义**：`global_mask_block`/`per_cfx_mask_block`（含"读当前 cfx 行、位=目标 cfxha"的反向断言）/`cause_mask_block` 各自「屏蔽期不投 + pending 保留 + 解除后恰 1 次补投」；`timer_imask_hold` 与 050 一致（bit10 置/清）。
8. **escape 补投**：`escape_kick` 帧内不投、`escape` 后恰 1 次。
9. **直接目标**：`direct_target` 中 poison（cfx3 向量）未执行、cfx3 async 计数不变、handler 在本 cfx 读到对应 cause ⇒ 不经 monitor 中转。
10. **cause 语义**：TIMER `cause_id=0x400`/`cause_info=0`；PMEM_DMA `cause_id=1<<8`、`cause_info` 为 `dma_status`（含 ERROR 例）。
11. **user-mode 编译**：`make build-qemu` 与 `dadao-linux-user` 目标均编译通过（贴 rc）。
12. **050 零回退**：`min_rom_probe_integ050t.py` 17 例 rc=0（16 runtime + `doc_shape`，逐项）；`integ042t` 25 例 rc=0；`044t/045t/048t/049t/046t/047t/039t/040t` 及 `integ038t–integ049t` 全绿。
13. **新探针**：14 例 rc=0，`--list` 计数一致。
14. **组件闭环**：`check-patch-tree`、`build-qemu`、`install-host`、`check-source-state` 全 rc=0；安装根与构建树 md5 相同。
15. **门控**：L1 `make check`、L2 `make check-modules`、L3 `make check-full` 全绿；既有红项须 A/B（改前同例同红）并登记，不得改 tests 掩盖。
16. **契约/登记**：`contract-see` 条目就位（含 `:39`/`:50` 措辞修正）、`make check-contracts-dir` rc=0；changelog 恰 1 条且 `make check-component-changelog` rc=0；`Makefile`/README 登记就位。
17. **证据**：`run.sh` rc=0；`--inject` 含可达 FAIL（① 优先级反转 ⇒ `low_cfxha_first` FAIL；② 仲裁跳过/绕过掩码判定（直接投递）⇒ `global_mask_block` FAIL；③ pending 写到 `cfx_hart` 而非目标 cfx（跨 cfx 混淆）⇒ `pmem_pending_in_pmem` FAIL），`cp`+md5 还原回绿（贴前后 md5）。
18. **收尾**：完成区 ≤30 行、`**状态**`=`待验收`、`milestones.md` 流水行同步、无临时残留。

## 下发前预检（architect 本轮实测，2026-10-31 修订轮）

1. **任务书内部一致**：目标 8 / 仲裁算法（`lowest`→`kick`→`arbitrate`→`exec_interrupt`）/ 掩码语义 8 条 / 接口规范 5 组 / 文件集 10 项 / 验收 18 条逐条对应；本轮修订裁定 7 条（不集中 pending、cfx_hart 只仲裁、pending 在目标 cfx、`cfx_intr_mask` 语义、global 总闸无 `async_enable`、不携带 target_mode、删除位图方案）逐条落纸。结论：**PASS**。
2. **验证手段前置**：**BLOCKED（依赖未完成）**——`INTEG-050t` 状态 `待开始`；本工作树（`af97197c`）`tools/testcases/arch/` 无 `min_rom_probe_integ050t.py`（`ls | grep integ05` 空，rc=1）；QEMU 补丁树仍是 049t 形态（`cpu.c.patch:480` 的 `exec_interrupt` 只有 PMEM 单分支，注释写 "The only asynchronous source in this model is the cfx_pmem DMA"，无 050 的 `hart_irq`/TIMER 分支，也无 "no unified pending" 段说明）；`Makefile:1457` `ARCH_CFX_PROBES` 不含 `integ050t`/`integ051t`；本工作树无 `.work/`（构建树/安装根/证据目录均不可用）。**替代证据**：主仓库 `INTEG-050t` 工作树（只读对照，非执行依赖）`.work/source/qemu` 已含 `hart_irq`、`dadao_hart_notify`、`dadao_hart_timer_deliver`，且 `dadao_hart_timer_expire()` 的 IMASK 分支**已写 `cfx[hart].pending |= TIMER`**（与本任务的 pending 归目标 cfx 一致）；`helper.c` 的 `cfx_enter` step 4 现文为 `cur_mask & (1ULL << target)` ⇒ 印证「位索引=目标 cfxha」。结论：**静态 PASS / 运行期 BLOCKED**，待 050 `已验证` 后重跑预检 2/3。
3. **验收逐条可跑性**：1/2/3/4/5/6/7/8/9/10/11/12/13/14/16/17 **现在不可跑**（缺 050 探针与构建树）；15（L1/L2/L3）不可跑。本轮**可跑**：`make check-tasks` rc=0（①漏收尾=0、②已立未开工=2 含 050/051）、`make check-contracts-dir` rc=0、`make check-knowledge-refs` rc=2（254 条悬空，全部为 `.work/**`；非 `.work` 悬空 = 0 ⇒ 本工作树无 `.work/` 的环境产物，非本任务引入）。结论：**BLOCKED（原因：050 未验证 + 无构建树），接管时重跑**。
4. **与 `contracts/`、`tests/` 一致**：`contract-see:39`（cfx_pmem 异步句）与 `:50`（两级过滤句）需按本轮口径补「pending 归目标 cfx、位索引=目标 cfxha」（已列文件集 8）；`integ042t` 的 `pmem_dma_masked_pending` 断言「只记 pending、不投递（`asyncn17=0`）」与新方案一致（且此时 pending 是**唯一**记录）；`tests/inst/**` 无 cfx15/17 异步引用（本轮 grep 未命中）。结论：**PASS（含 2 处契约措辞修正）**。
5. **拟改文件 × `spec/` 清单**：命中 **0 册**——统一仲裁是测试机实现约定；`DADAO-12 §5` 只定义「两级过滤 + pending」，未定义机器内部排队/优先级，且其伪代码 step 4 用 `1 << temp_cfx_code`（异步=目标 cfx），与本轮口径一致；`cfx_hart` 不新增寄存器。故**无需 spec 授权**、无 `spec/**` 改动；若执行中发现 `§5` 与本设计冲突（例如规定 pending 必须由软件清、投递不得清位）⇒ **停手登记 BLOCKED**，交用户裁定。

## 风险与已知缺口

1. **依赖未验证**：050 仍在实现中；本任务书引用的行号/符号以其交付形态为准（两 `bool` 将被删、`dadao_*_deliver` 将被并入仲裁）。050 若调整探针或 `contract-see` 条目，开工前重跑预检 2/3。
2. **「投递成功清 pending」是测试机约定**：spec §5 只规定"被挡时置 pending、软件可写 0 清"，未写"投递后硬件清"。不清则边沿事件会被反复投递 ⇒ 必须清；写契约并在完成区标明。若用户要求"投递不清、只由软件清" ⇒ 停手裁定。
3. **pending 唯一 ⇒ 软件清即取消**：包括"源事件已发生、尚未投递"的窗口。该窗口对 guest 不可观测（投递在 guest 指令执行前完成），但须在契约写明。
4. **`cause_info` 时效**：PMEM_DMA 的 `cause_info` 取投递时刻的 `dma_status`；屏蔽期间再启动新传输会覆盖（050 同源限制），本任务不快照化。
5. **踢点覆盖面**：`helper_cfx2rc` 有多处早返回（`cfx_pmem cg15`、`cfx_hart cg8`、`cg7`、`PTWERR`、`tlb_control`），只有「通用写尾 + cg8 自身 kick」两处踢；实现须逐条对照 `cfx_intr_mask`/`global_cfx_intr_mask`/`excp_cause_mask`/`pending` 的所有写点，漏一处则滞留到下一次踢点。
6. **`excp_cause_mask` 与源事件同一位**：被 cause mask 挡住的位与"待投递事件"无法区分；软件在 mask 未解时清位 ⇒ 该事件被取消（按「清即取消」约定），不另设记录。
7. **`IMASK` 与两级 mask 叠加**：两者都挡投递，解除顺序不限；`ISTATUS=1` 不代表已投递（050 已如此），探针不得把 ISTATUS 当投递证据。
8. **`-icount` + QEMUTimer**：050 已按 `shift=0` 设计；若仲裁改动导致 1 ms 级延迟用例失稳，按 050 风险 4 的处置（改用默认虚拟时钟 + 记录依据），不改判据。
9. **user-mode**：新增函数/踢点须 `#ifndef CONFIG_USER_ONLY`，否则 `dadao-linux-user` 编译失败。
10. **项目里程碑归属**：050 记为「不在 M10 通路内」，本任务暂挂 M10；若用户另立 M11（Linux 开发前），改挂即可（不动任务内容）。
11. **门锁/构建**：构建与门控一律经 `make`（`flock`）；若 `build-qemu` 触发 reconfig 或全量（10–30 min）⇒ 停手上报。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 0 轮 architect 规划（提交留痕）

- **档位**：WIP（任务 `待开始`、未实现）；提交信息 `docs: 立 INTEG-051t 异步中断仲裁`。
- **文件集对账**：`git diff --cached --name-only` = 2 项 = 本任务书 + `.tao/knowledge/milestones.md` 流水行（=「修改文件」第 9、10 项）；无漏提/多提/越界；未 `push`、未实现、未跑夜跑。
- **本轮实测（本工作树 `658b9723`，分支 `INTEG-051t`）**：`make check-tasks` rc=0（65 份任务书，①=0、②=2 含 050/051）；`make check-contracts-dir` rc=0；`make check-knowledge-refs` rc=2（252 条 `.work/**` 悬空，改前同红：本工作树无 `.work/`，环境产物、非本任务引入）。
- **调查来源**：`components/qemu/patches/target/dadao/{cpu.h,cpu.c,helper.c}.patch`（049t 形态，`exec_interrupt` 仅 PMEM 分支）+ 主仓库在跑的 050 `.work/source/qemu`（`hart_timer`/`hart_irq`、`helper.c:2049` "no unified pending" 注释）+ `min_rom_probe_integ042t.py`（25 例）+ 主仓库 `min_rom_probe_integ050t.py`（16 runtime + `doc_shape`）。
- **提交号**：本分支 `INTEG-051t` 上 `docs: 立 INTEG-051t 异步中断仲裁`（哈希以 `git log -1` 为准；本条不写死哈希，避免 amend 漂移）。
- **预检结论**：① PASS；② 静态 PASS / 运行期 BLOCKED（050 未验证 + 本工作树无构建树）；③ BLOCKED（同上，接管时重跑）；④ PASS（含 `contract-see:50` 补充）；⑤ 0 册命中、无需 spec 授权。

#### 第 0 轮 architect 修订（2026-10-31，pending 归目标 cfx）

- **用户裁定（原样落纸见「追加裁定」）**：不集中 pending；`cfx_hart` 只仲裁；`PMEM_DMA` pending 在 `cfx_pmem`、`TIMER` 在 `cfx_hart`；`cfx_intr_mask` = 当前 cfx 的 `inner_run_mode` 行、位索引=目标 cfxha；`global_cfx_intr_mask` = 当前模式 monitor 总闸、不加 `async_enable`；目标 cfx 的 `switch_run_mode` 固定、不携带 target_mode。
- **本轮删除/改写**：删「`cfx_hart` 内置 64 位聚合位图 `hart_async_pending`」全部表述（目标 1、寄存器/内部状态、接口规范 §1–§3、约束 1、验收 2/3/4）；删仲裁的 `deliverable()` 掩码预检（掩码唯一真源 = `cfx_enter`，避免公式复制漂移）；删「`cfx_intr_mask` 取行口径待确认」（已定：读当前 cfx 行、位=目标 cfxha，与 `cfx_enter` step 4 现文一致）；删「同源去重待用户确认」（单 bit OR 语义直接推出）。
- **本轮新增**：`dadao_async_lowest/kick/arbitrate` 三函数与候选表；四类踢点（通用写尾 / cg8 rc5 / escape / 源事件）；pending 单记录语义（硬件置位、投递成功清位、软件写 0 取消）；探针用例改为 14 条（目标 cfx pending、S/H 不混、global/per-cfx mask、cause mask 补投、IMASK、低 cfxha 优先、escape、直接目标、无 `async_enable`、去重、ERROR info）。
- **文件集对账**：`git diff --cached --name-only` = 2 项 = 本任务书 + `.tao/knowledge/milestones.md` 流水行；无漏提/多提/越界；未 `push`、未实现、未跑夜跑。
- **本轮实测（本工作树，分支 `INTEG-051t`）**：`make check-tasks` rc=0；`make check-contracts-dir` rc=0；`make check-knowledge-refs` rc=2（254 条悬空，全部 `.work/**`，非 `.work` 悬空 = 0；本工作树无 `.work/`，环境产物）。
- **档位/提交**：WIP（任务仍 `待开始`）；`docs: INTEG-051t pending 归目标 cfx`。
- **是否可派 engineer**：**否**——依赖 `INTEG-050t` 仍 `待开始`；050 `已验证` 后重跑预检 2/3 再 `/dispatch`。

#### 第 1 轮 engineer 自审

#### 第 1 轮 reviewer 验收
