# m16-chipyard-013: chipyard 实现差异盘点（对照其它 generator；gewu / wuming × tiny/vast）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：无（**只读分析**：不占 chipyard 写者锁，可与在跑任务并行）
**可并行分片**：是
**预估**：3–4 h
**档位**：小改（只读 + 写结论）
**状态**：待开始

## 背景（用户 2026-11-20 裁定）

M14 做过「内核实现 vs `arch/riscv`/`arch/arm64`」的差异盘点；M16 对 chipyard 做同构的事——**把我们的 generator（`dadao-gewu` / `dadao-wuming`）与其它 generator 逐项对比**。

**用户明确要求**：
- **对照物 = 其它 generator**；
- **`gewu` 主要对照 `rocket`**；
- **`wuming` 也应主要对照 `rocket`**；
- **`tiny` 和 `vast` 都要做**。

## 对照物

- **主参照**：`rocket`（`chipyard/generators/rocket-chip/**`）——它是 chipyard 里最成熟的 RISC-V 核，`wuming`/`gewu` 都从它演化或并列存在。
- **补参照**：`boom`（乱序对照，仅看接口面）、`chipyard` 自身的 `DigitalTop`/`Subsystem` 组装层。
- **wuqing**：**当前仓内不存在**（`components/chipyard/patches/generators/` 只有 `chipyard`/`dadao-gewu`/`dadao-wuming`）⇒ 本盘点不涉及；**将来到位后按同一口径补一份**。

## 范围

- `components/chipyard/patches/generators/dadao-gewu/**`、`dadao-wuming/**`；
- `DadaoConfigs.scala` 里的 `WumingTinyConfig` / `WumingVastConfig`（**两机型都要**）；
- 对照 `generators/rocket-chip/**` 的 `Tile`/`Core`/`TLB`/`PTW`/`Cache`/`PMP`/`Debug`/`Interrupt`。

## 要做（**只读**）

按「同类机制」逐项对照，四类差异：
1. **缺失实现**：rocket 有、我们没有（如 **PMP**、**debug module**、**RoCC 接口**、**多核/一致性**、**L1 D/I cache**、**FPU 的完整 hardfloat 路径**）；
2. **语义不符**：有但做法不同（PTE 格式/端序、TLB 替换策略、A/D 处理、异常码映射、中断控制器接入）；
3. **旁路 / 折衷**：为省事走的近路（如「PA RAM 走 TileLink 从端口、放弃 AXI4+SimDRAM」「外设移出窗口」——**已知且待 ADR**，如实记录不评判）；
4. **配置缺口**：`WumingTinyConfig`/`WumingVastConfig` 相对 rocket 配置缺的通用项（`useVM`/`pgLevels` 的语义、`fragments`/HSJU、`cfx` 的 generator 组织方式）。

**两机型单列**：`WumingTinyConfig`（SRAM、无 MMU/PTW）与 `WumingVastConfig`（PTW/TLB/大存储）分别对照 rocket 的哪个配置（`RocketConfig`/`TinyRocketConfig`/`MediumRocketConfig` 之类），差异在哪。

## 产出格式

每条：`generators/dadao-<x>/<file>:<line>` ↔ `generators/rocket-chip/<file>:<line>` / 分类 / 影响（tiny / vast / 两者）/ 优先级 P0/P1/P2。

## 验收

1. 结论写进本任务书「盘点结论」段（≤80 行）；
2. **覆盖现场派生**：比对了多少个模块 / 机制 / 配置项（现场统计 + 枚举口径）；
3. **抽查 ≥5 条**：两侧 `sed -n` 贴原文（chipyard 源码在组件源树里只读）；
4. **两机型各给一段**：`WumingTinyConfig` / `WumingVastConfig` 各自对照结果；
5. **不改代码**：`git show --name-only HEAD` 只含本任务书；不 elab、不跑仿真。

## 完成区

（待填）
