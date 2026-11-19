# 项目里程碑

> **项目里程碑 = M17**（M17 台账的唯一断言；`check-milestones-fresh` 按本断言把任务号路由到本页；M12–M16 各另有分册）

> **本页只维护 M17 任务台账**：历史任务见 `.tao/archive/`；当前讨论/规划见 `.tao/knowledge/discussing.md`。

> **M17 定位（用户 2026-11-19 裁定）**：**Kaiwu-Vast 上 RTL（chipyard）**——把测试机从 `WumingTinyConfig`（SRAM、无 MMU）扩到 Vast（TLB + PTW + cache + 大存储/地址图）。同步要求：**gem5 侧 Vast 的 TLB 与本里程碑的 RTL 保持一致**（见 `m17-gem5-001`）。
> **用户已定口径（2026-11-19）**：**只设一级 TLB、分 I/D**（I/D 分离是**设计**不是实现细节）；**普通页 16 条 = 2 组 × 8 路、不设 sectored**；**超页 4 条全相联 + LRU**；**无特殊条目**（rocket 的 special entry 是为 PMP，DADAO 无 PMP）；**I-TLB 无 dirty 位**（参考 rocket 的 `instruction` 参数）；**gem5 与 chipyard 在这些方面保持统一**（含组相联设置与超页个数）。

本页分三张**任务表**，**表位置 = 任务状态**（不另设状态列）：

| 表 | 收录 | 列 |
| --- | --- | --- |
| 待开始（未开工） | 尚未派单的 `待开始` | `编号` / `预估时间` / `一句改动` |
| 进行中（已派单） | 已派单未合并：`待开始`（实现中）、`待验收`、`待返工` | `编号` / `派单时间` / `预估时间` / `一句改动` |
| 已验证 | `已验证` | `编号` / `完成时间` / `一句改动` |

## 待开始（未开工）

| 编号 | 预估时间 | 一句改动 |
| --- | --- | --- |
| m17-chipyard-001 | 2–3 天 | Vast 核参数与地址通路（`useVM`/PTBR·ASID·`ptw_enable`/`cfx_ptw` 寄存器面/地址路由） |
| m17-chipyard-002 | 2–3 天 | PTW 两级步查（64 KiB 页 + 512 MiB 超页、大端 PTE、HSJU/frags、A/D 本地+回写） |
| m17-chipyard-003 | 1–2 天 | I/D TLB（2×8 + 4 超页 FA/LRU、I 无 D 位）+ `cfx_ptw_tlb_control` 双表失效 |
| m17-chipyard-004 | 3–5 天 | D-Cache（64 KiB 页/块分离、MBUS 接入；周期基线另标） |
| m17-chipyard-005 | 2–3 天 | I-Cache + Vast 大存储与地址图（4 MiB ROM / 2 GiB RAM / hmon·smon·pmem） |
| m17-chipyard-006 | 1–2 天 | Vast 收口门控（QEMU/gem5/RTL 三方差分） |
| m17-gem5-001 | 1–2 天 | gem5 Vast TLB 改造：I/D 双表、2 组×8 路、4 超页 FA/LRU、双表失效、A/D OR 合并 |

## 进行中（已派单：待开始 / 待验收 / 待返工）

| 编号 | 派单时间 | 预估时间 | 一句改动 |
| --- | --- | --- | --- |

## 已验证

| 编号 | 完成时间 | 一句改动 |
| --- | --- | --- |
