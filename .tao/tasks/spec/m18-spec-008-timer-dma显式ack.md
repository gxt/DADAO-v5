# m18-spec-008: timer/DMA 显式中断 ack（讨论稿）

**模块**：spec
**项目里程碑**：M18
**依赖**：`m18-spec-007`（0.8.0 出口帧）、`ADR-0061 R3`
**可并行分片**：否
**预估**：待定（讨论完成后再标定）
**档位**：中改（异步源 ack 语义 + 三实现）
**状态**：**讨论中（不派发）**
**执行环境**：本地

## 背景

现行 `contract-see §3`/`DADAO-12 §4.7`/`§4.9` 把“中断 ack”定义成两个**副作用**：`TIMER` = 重写 `timer_cmp`；`PMEM_DMA` = `dma_status` 的 `DONE/ERROR` W1C。没有第一类的“ack 操作”，导致：

- 投递即清 `pending`，漏 ack 不留下可检测状态（timer tick 静默停摆）；
- `ISTATUS` 是派生条件（`cmp<=now && ENABLE`），ack 与 re-arm 绑死；`ENABLE=0` 时前置检查失败（内核 `die`）；
- DMA 的 ack 与状态清除、`ERR_CODE` 读取耦合；`BUSY=1` 时 W1C 被忽略；
- ack 没有幂等定义。

用户 2026-11-26 裁定：**A（显式 ack）**。

## 已确定（用户拍板）

1. **走 A：显式 ack**。
2. **当前只有两个异步源**：`TIMER`（源 cfxha 15）、`PMEM_DMA`（源 cfxha 32）。`IPI` 是 `cfx_hart` 的**同步** cause（`1<<8`、单 hart 无发送方，未接异步投递）；`UART`（cfxha 62）无异步路径。
3. **A1：ack 放在源侧，每位 W1C**：
   - `TIMER`：`ISTATUS` 改**粘滞锁存**，W1C 即 ack；`timer_cmp` 只负责 re-arm，不再兼作 ack；
   - `PMEM_DMA`：`DONE`/`ERROR` 的 W1C 定义为 ack；明确 ack 前再次 DONE 的语义；`ERR_CODE` 只在 `ERROR` ack 时清；
   - 内核按 `cg9 rc4`（本次源集合）逐源 ack；不新增 hart 的集中 ack 寄存器。

4. **用户 2026-11-26 追加方向**：**每个中断源都有自己的 `pending`/`mask`/`ack` 寄存器**（源侧自洽，不再把 pending 集中在 `cfx_hart cg9 rc5`、mask 集中在每模式 monitor `cg8 rc1`）。待讨论：mask 是否**取代** monitor 掩码、pending 是否改为 ack 才清、`cg9 rc4 src_frame` 是否随之删除、源侧寄存器如何统一。

5. **用户 2026-11-26 明确 timer 布局**：`TIMER` 移到 **`cfx_hart cg10`**：`rc0` = timer ctrl、`rc1` = timer cmp、`rc13` = ack（W1C）、`rc14` = mask、`rc15` = pending。三个独立寄存器（ack/mask/pending），不再与 `cg8` 混放；`cg9` 的集中 pending/src_frame 与 monitor `cg8 rc1` 掩码的最终去留待定。DMA 的对应布局待定。

6. **用户 2026-11-26 澄清**：
   - `cg9 rc4`（本次源集合）与 `rc5`（pending 汇总）**保留**，作为聚合视图，避免 handler 逐个读源；不是冗余。
   - **源 mask 与 `*mon` 的 mask 不冲突、互不替代**：源 mask 是设备自己的 gate，monitor `cg8 rc1` 是运行模式 gate，两者独立（投递同时受两者约束）。
   - **`escape` 语义不变**：`rc11` 仍整字写目标运行模式 monitor 的 `cg8 rc1`；与源 mask 无关。

7. **用户 2026-11-26 再澄清**：
   - `pending` 语义：**事件置位、ack（源 `rc13` W1C）才清、投递不清**；handler 必须在 `escape` 前 ack 已投递源，想延后就保持该源 mask 关闭。
   - **monitor mask 是每个 monitor cfx（cfx0–3）各自的 64 位寄存器**，位 = 源 cfxha（15/32）。
   - **源 mask 是源自己的事件位图**：不是“一个源一位”，而是“该源的子事件位”——`TIMER` 现在只有一个 `cmp`，所以只有 bit0 有效；将来扩展成两个 `cmp`，就低 2 位有效。源 `pending`/`ack` 同构（按子事件位）。

8. **用户 2026-11-26 定布局**：
   - 中断源统一接口在 **`cg16`**：`rc16` = **mask**、`rc17` = **pending**、`rc18` = **ack（W1C）**（2026-11-26 用户订正顺序）；三个独立寄存器，位 = 该源子事件（当前均只有 bit0 有效）。
   - `TIMER`（`cfx_hart`）：`cg16 rc0` = timer ctrl（**只留 bit0 `ENABLE`**；`IMASK` 由 `rc16` 取代、`ISTATUS` 由 `rc17` 取代）、`rc1` = timer cmp；中断面 `rc16/17/18`（原拟 `cg10` 作废）。
   - `PMEM_DMA`（`cfx_pmem`）：中断面也搬到 `cg16 rc16/17/18`；DMA 引擎寄存器仍留 `cg15`。**子事件合并为一位**（B：`DONE|ERROR` 合并成 bit0“传输结束”），ERR_CODE/DONE/ERROR 细节仍由 cg15 `dma_status` 区分；对外接口与 timer 一致，内部各自解释。
   - `cg9 rc4/rc5` 仍为 hart 级聚合（bit = 源 cfxha）；monitor mask 仍为每 cfx 64 位（`cg8 rc1`）；`escape` 不变。

## 待裁定（逐条讨论）

1. `ISTATUS` 置位条件：**到期边沿置位**（每个 armed deadline 只置一次，之后不重复）还是 `cmp<=now` 的持续电平？前者才使 ack 有意义。
2. `ENABLE=0` 是否清 `ISTATUS`，还是只 gate 投递？
3. ack 后未 re-arm（`cmp` 仍在过去）时，`ISTATUS` 是否立即重置（防风暴规则）。
4. DMA：ack 前再次 `DONE` 的合并/计数语义；`DONE` 与 `ERROR` 同时置位时的 ack 顺序；`BUSY=1` 时 ack 的处理。
5. ack 幂等：条件已消失/已 ack 时 W1C 是否 no-op（建议是，内核不得 die）。
6. ack 与 `pending` 的关系：投递仍清 pending；ack 只清源事件（或 ack 也清 pending 残留？）。
7. 内核侧改动面（`time.c` 的 ack 路径、`dadao_async_ack_sources`、K2 探针）。
8. QEMU/RTL/gem5/IDL 的同步任务与顺序；版本是否随 0.8.0（已定版）另起。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：
