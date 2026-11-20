# 项目里程碑

> **项目里程碑 = M20**（M20 台账的唯一断言；`check-milestones-fresh` 按本断言把任务号路由到本页；M12–M19 各另有分册；M21 暂缓）

> **本页只维护 M20 任务台账**：历史任务见 `.tao/archive/`；当前讨论/规划见 `.tao/knowledge/discussing.md`。

> **M20 定位（用户 2026-11-20）**：**gem5 Minor 与 chipyard wuqing 一起开发、对比验证**。**golden = wuming RTL**——Minor 与 wuqing 各自先对齐 wuming，两边都稳了再做直接对比（否则谁都不成熟时无法归因）。
> **前置**：`m17-idl-003` 的逐指令 trace 格式可用；`m16-chipyard-010`（I-Cache）完成；`m19-chipyard-001` 的资源实测反推 wuqing 参数。
> **收口判据（草案）**：Minor 与 wuqing 各 ≥20 例与 wuming trace 逐指令一致；wuqing 规格与资源预算对账；Minor 周期重标后 `check-wuming-cycles` 仍绿。
> **后续（未拆，见 `discussing.md`）**：Minor 周期表重标（不搬 Timing 的 264 行）；wuqing 上板（M20 尾段或 M21）；随机指令流生成器（TestRIG 式，属 M17 侧产物）。

本页分三张**任务表**，**表位置 = 任务状态**（不另设状态列）：

| 表 | 收录 | 列 |
| --- | --- | --- |
| 待开始（未开工） | 尚未派单的 `待开始` | `编号` / `预估时间` / `一句改动` |
| 进行中（已派单） | 已派单未合并：`待开始`（实现中）、`待验收`、`待返工` | `编号` / `派单时间` / `预估时间` / `一句改动` |
| 已验证 | `已验证` | `编号` / `完成时间` / `一句改动` |

## 待开始（未开工）

| 编号 | 预估时间 | 一句改动 |
| --- | --- | --- |
| m20-gem5-001 | 4–6 天 | gem5 Minor 接入（`initiateAcc`/`completeAcc` + `ldm/stm` 微操作 + trace；与 wuming 对拍 ≥20 例） |
| m20-chipyard-001 | 5–7 天 | wuqing 微架构规格 + generator 骨架（规格先行；资源与 Genesys2 预算对账） |

## 进行中（已派单：待开始 / 待验收 / 待返工）

| 编号 | 派单时间 | 预估时间 | 一句改动 |
| --- | --- | --- | --- |

## 已验证

| 编号 | 完成时间 | 一句改动 |
| --- | --- | --- |
