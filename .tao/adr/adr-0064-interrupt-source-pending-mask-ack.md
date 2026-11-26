# ADR-0064: 中断源 pending/mask/ack 归源、显式 W1C ack

**状态**：Accepted（2026-11-26；用户逐条裁定 A：源侧 pending/mask/ack、`cg16` 统一中断面、`cfx_hart` 捕获组 `cg9`→`cg15`、monitor 掩码 `cg8 rc1`→`cg15 rc3`、版本升 `0.8.1-rc`）
**日期**：2026-11-26
**关联**：`ADR-0061`（Accepted；其 **D5（mask 唯一归 monitor）与 D6（pending 由投递清除）由本 ADR 取代**，**R3 的出口帧 `cg5 rc8`–`rc11` / 异步 `escape` 继续有效**；本 ADR 不改 `adr-0061` 原文，只在其状态/关联行加取代指针）；`ADR-0042 D7`（`cfx_pmem` DMA 的异步源）；`ADR-0062`（扁平 cause 位图，不受影响）；`ADR-0060`（hart-first，沿用）；`m18-spec-008`（本 ADR 的正文落地）
**规范落点**：`spec/DADAO-12 §1`/`§3.1`–`§3.6`/`§4.1`–`§4.4`/`§4.7`/`§4.9`/`§5.1`–`§5.4`、`spec/DADAO-22 §7`/`§9`、`.tao/contracts/contract-see.md`、`contract-cfx-aliases`（重生成）

## Context（背景）

现行（0.8.0）把“中断 ack”定义成两个**副作用**：`TIMER` 靠重写 `timer_cmp` 清除条件，`PMEM_DMA` 靠 `dma_status` 的 `DONE`/`ERROR` W1C；同时：

1. **pending 不落在可检测状态**：异步进入即清 `cfx_hart cg9 rc5`，漏 ack 不留下可查询的状态（timer tick 可静默停摆）；`ISTATUS` 是 `cmp<=now && ENABLE` 的派生条件，不是粘滞锁存。
2. **ack 与 re-arm / 状态清除耦合**：timer 的 ack 与写新 deadline 绑死；DMA 的 ack 与 `dma_status` 清除、`ERR_CODE` 读取耦合，且 `BUSY=1` 时 W1C 被忽略；ack 没有幂等定义。
3. **mask 位置单一**：monitor 的 `cg8 rc1` 是唯一来源 gate，源设备没有自己的子事件 gate；`EXIT`/`ESCAPE` 恢复掩码与设备自身策略混在一起。

用户 2026-11-26 裁定：**A（显式 ack）**，并追加“每个中断源都有自己的 `pending`/`mask`/`ack`”。

## Decision（决策）

### D1 源侧统一中断面 `cg16`

每个中断源在**自身 cfx** 的 `cg16` 提供三个独立寄存器（位 = 该源**子事件**）：

| rc | 寄存器 | 语义 |
|----|--------|------|
| 16 | `mask` | `1=屏蔽`、`0=允许`；复位全 1；保留位读 0/写忽略 |
| 17 | `pending` | 事件置位；**只有 ack 才清**；异步进入不清；复位 0；RO |
| 18 | `ack` | W1C：写 1 清 `pending` 对应位；读 0；对已清位写 1 为 no-op；保留位写 1 忽略 |

- `cg16` 只在 `cfx_hart` 与 `cfx_pmem` 实现；其它 cfx 访问 `cg16` ⇒ `CFXREG`。
- `mask`/`ack` 的写权限按各 cfx 的 `<mode>_cfxreg` 两轴矩阵放行（默认只 supv/hypv，平台可按需放开 user/jail）；`pending` 只读。

### D2 各源布局

- **`TIMER`（`cfx_hart cg16`）**：`rc0 = timer_ctrl`（**只留 bit0 `ENABLE`**；原 `IMASK`/`ISTATUS` 删除，位按保留读 0/写忽略）、`rc1 = timer_cmp`；中断面 `rc16/17/18`。删除 `cg8 rc4`/`rc5` 的 timer 定义（归 reserved ⇒ `CFXREG`）。
- **`PMEM_DMA`（`cfx_pmem cg16`）**：中断面 `rc16/17/18`；**子事件合并为 bit0“传输结束”**（`DONE` 或 `ERROR`），`ERR_CODE`/`DONE`/`ERROR` 细节仍由 `cg15 dma_status` 区分。删除 `dma_ctrl` 的 `IRQ_EN`（该位按保留位读 0/写忽略），`dma_ctrl` 只剩 `START`（自清）与 `DIR`。`cg15` 仍是 DMA 引擎寄存器。

### D3 pending 与 ack 语义

- 源事件到达即置源 `pending` 对应位；**异步进入不清**；只有源 `ack` 的 W1C 才清；事件幂等、不计数。
- `TIMER`：到期**边沿**置位（每个已 arm 的 deadline 只置一次）；`ENABLE=0` 时到期不置位；`ENABLE` 0→1 且 `cfx_time_value >= timer_cmp` 时立即置位一次（使能即检）；写 `timer_cmp` 只重新 arm、**不清 pending**。
- `PMEM_DMA`：传输结束时置 bit0；ack 前多次完成合并为 bit0（不计数）。
- `dma_status` 的 `DONE`/`ERROR`/`ERR_CODE` 仍由 `dma_status` 自己的 W1C 清；`cg16 rc18` **只清中断 pending**，两者对象不同（软件可先 ack 中断，再按需清 status）。

### D4 异步进入判定（逐源、合并）

在指令边界逐源判定，全部满足才放行：

1. `(源 pending & ~源 mask) != 0`；
2. 当前运行模式 monitor 的 `cg15 rc3[源 cfxha] == 0`；
3. `TIMER` 还要求 `ENABLE=1`。

所有放行源**合并成一次异步进入**：`cfx_hart cg15 rc4` = 本次源 cfxha 位集合；`cg15 rc5` = **原始 pending 汇总**（位 = 源 cfxha，源 pending 非 0 即置、全清即落）；`excp_async_num` 每次进入 +1。进入**不清**源 pending，也不清 `rc5`。

### D5 `cfx_hart` 捕获组 `cg9` → `cg15`

- `cg15`：`rc0` prev run mode、`rc1` prev cfx code、`rc2` prev ip、`rc3` prev intr mask、`rc4` 本次源集合、`rc5` 原始 pending 汇总、`rc14` switch run mode、`rc15` vector；`rc6`–`rc13` reserved。
- `cg9` 在 `cfx_hart` 归 reserved（访问 ⇒ `CFXREG`）；其它 cfx 的 `cg9`（如 `cfx_ptw`）不受影响。
- 异步进入只写 `cg15 rc0`–`rc4` 与 hart `cg5 rc8`–`rc11`；不写 `cg15 rc5`、不写 hart `cg5 rc0`–`rc3`。

### D6 monitor 掩码 `cg8 rc1` → `cg15 rc3`

- 四个 monitor（`umon`/`jmon`/`smon`/`hmon`）的 `async_intr_mask` 迁到 `cg15 rc3`：64 位、位 = 源 cfxha、`1=屏蔽`/`0=允许`、复位全 1；`cg8 rc1` 归 reserved（访问 ⇒ `CFXREG`）。
- 源 `mask` 与 monitor 掩码**互不替代**：源 mask 是设备自己的 gate，monitor 掩码是运行模式 gate，异步进入同时受两者约束。

### D7 `escape` 与术语

- `escape` 语义不变，但 `cg5 rc11` 的写入目标改为目标模式 monitor 的 `cg15 rc3`；`cg5 rc3`（prev intr mask）快照同一寄存器。
- 取消“投递 / delivery pending / 投递即清”提法，统一称“**事件 / 异步进入 / ack**”；spec/契约现行正文按此清理（历史变更记录可保留旧词）。

### D8 版本

`spec/DADAO-12`（SEE）与 `spec/DADAO-22`（SBI）册头同升 **`0.8.1-rc`**（SEE↔SBI 互锁）；`contract-see` 同步；`SimRISC` 不变（ISA 编码未动）。别名表/opcodes/legality 由仓库工具重生成，ISA 编码不变。

## Alternatives（被否方案）

- **保留“ack = 重写 cmp / dma_status W1C”副作用**：ack 与 re-arm/状态清除耦合，`ENABLE=0` 时无法只清 pending，且漏 ack 无可检测状态。
- **pending 集中在 `cfx_hart`**：源无法自洽表达子事件；多个源共用一个位图时 ack 语义只能按源粒度，无法扩展同源多子事件。
- **mask 只保留 monitor 层**：设备无法独立屏蔽自己的子事件；monitor 行也无法表达“源内哪个子事件”。
- **DMA 保留 `IRQ_EN`**：与源 `cg16 rc16` mask 功能重复，两处 gate 易漂移。
- **`cg16` 子事件按源一位**：用户明确源内是“子事件位图”（TIMER 当前 bit0，将来可扩到多 cmp），不是“一源一位”。

## Consequences（影响）

- **spec/契约**：`DADAO-12 §1`/`§3.1`–`§3.6`/`§4.1`–`§4.4`/`§4.7`/`§4.9`/`§5.1`–`§5.4`；`DADAO-22 §7`/`§9`；`contract-see §2`/`§3`/`§4`/`§6`；`contract-cfx-aliases` 重生成；`spec/.manifests.toml` 重算 SEE/SBI 哈希。
- **实现侧（本 ADR 不改代码）**：QEMU/RTL/gem5/IDL/汇编器/内核仍按 0.8.0 的 `cg9`/`cg8 rc1`/`IRQ_EN`/`ISTATUS`，跨实现门控预期红，按波 2 后续任务逐项改；测试向量与探针同步前不得视为实现合规。
- **兼容性**：不兼容的寄存器位置与 ack 语义变更，故升 `0.8.1-rc`（`0.8.0` 已发布保持不动）。
