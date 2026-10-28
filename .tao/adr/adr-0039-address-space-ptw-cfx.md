# ADR-0039: 地址空间、PTW/PTE 与 CFX 核内空间

**状态**：Proposed（待逐条确认；未 Accepted）
**日期**：2026-10-28
**关联**：`spec/DADAO-12-SEE`、`spec/DADAO-13-HEE`、`contracts/cfx-aliases.txt`、`QEMU` ptw/TLB、`TESTCASES-*` 地址空间向量

> **决策来源（用户 2026-10-28，经主会话问答）**：CPU 地址 48 位；高 6 位 0 为内存窗口；VA 42 位；一个 PTBR；PA 56；删除 `pahi/pthi`；PTE 增加 HMON/SMON；删除 ptw 的 user/jail/supv/hypv perm 寄存器；SPF 移到 `[15:8]`；cfx 1–63 核内空间；cfx 0 无内部空间；考虑合并 `cfx_tlb` 到 `cfx_ptw`。
> **ADR 不承载规范正文**：具体位域/寄存器表由 `spec/DADAO-12` 与 contracts 落笔。

## Context

- 原设计：48 位 VA，高 6 位选 64 个 PTBR；`pahi/pthi` 拼 PA 高 16 位；PTE 高位放 SPF/GPF；`cfx_ptw_user/jail/supv/hypv_perm` 控 PTBR 访问。
- 用户决定：PA 实际只到 48 位（`pahi/pthi` 失效），改为 PA56；PTBR 只保留 1 个；VA 42 位；高 6 位 0 为内存窗口，1–63 为 cfx 核内空间；cfx 1–63 各有 42 位内部空间，cfx 0 无。
- 目标：简化地址翻译、让 cfx 内部空间与页表空间不重叠、把运行模式下沉到 PTE。

## Decision（草案，逐条待确认）

- **D1 — 地址分区**：CPU 地址 48 位；`[47:42] == 0` 为内存窗口（PTW/pmem）；`1..63` 为 cfx 1–63 核内空间；cfx 0 无内部空间。
- **D2 — VA/PTBR**：内存窗口 VA 42 位；**1 个 PTBR**；删除 64 项 PTBR 数组与 `ptbr_enable` 位图（是否保留一个 enable 位见 D3）。
- **D3 — 高 6 位 0 的两种模式**：高 6 位 0 是**内存窗口**；`ptw_enable=0` 时直接访问 pmem（物理），`=1` 时走 PTW。**不把 ptw/pmem 改名为 cfx0**；ptw 仍是控制 cfx，pmem 仍是资源。
- **D4 — PA**：物理地址 56 位；删除 `pahi/pthi`；PTBR 基址/PTE PA 均按 56 位。
- **D5 — PTE 布局**：
  - L1 next-level：`[55:16]` PA/PPN 合并；`[15:8]` 保留；`[7:0]` flags。
  - L1 superpage：`[55:16]` PA；`[15:8]` SPF（8 个小超页）；`[7:0]` flags。
  - L2：`[55:16]` PA；`[15:8]` GPF；`[7:0]` flags。
  - `[63:62]` HMON/SMON；`[61:56]` 保留。
- **D6 — HMON/SMON 权限（页级）**：
  - `00`：普通用户页（按 R/W/X）；
  - `01`：仅 smon（supv）可访问，非 smon ⇒ NSPERM；
  - `10`：仅 hmon 可访问，非 hmon ⇒ NHPERM；
  - `11`：hmon+supv（或保留，待确认）。
  - **NSPERM/NHPERM 保留**；NUPERM/NJPERM 是否保留/仅保留编码待确认。
- **D7 — 删除 perm 寄存器**：删除 `cfx_ptw_user/jail/supv/hypv_perm`；PTBR 访问不再按模式判权，由 PTE HMON/SMON 判页级权限。
- **D8 — CFX 核内空间权限**：cfx 1–63 各 42 位内部空间；user/supv/hypv 的访问需**逐 cfx 模式权限**（控制寄存器配置；默认拒绝；控制寄存器本身 S/H only）。
- **D9 — TLB**：考虑把 `cfx_tlb` 合并到 `cfx_ptw`（同一 cfx 提供页表步进 + TLB 管理）；TLB 异常仍为 ptw 异常子集；小页/小超页的 GPF/SPF 需在 TLB 条目中保留。
- **D10 — 同步范围**：DADAO-12/13、contracts/cfx-aliases、生成器、QEMU ptw/TLB、lit/向量、spec 锁 sha/changelog/版本；不立额外 ADR，以本 ADR 为决策源。

## Open questions（未决，阻塞 Accepted）

1. HMON/SMON 的 `11` 是 hmon+supv、非法，还是保留？hmon 访问 SMON=1 的内核页是否允许？
2. NUPERM/NJPERM 是否保留异常编码（jail 未设计，位保留）？
3. `ptw_enable` 是一个全局位还是每 cfx/每窗口？高 6 位 0 直接 pmem 的物理地址宽度/范围？
4. cfx 1–63 的 user/supv/hypv 权限寄存器放在哪里、粒度（cfx/偏移）、默认值。
5. `cfx_tlb` 合并与否；若合并，`cfxha 5` 是否释放/保留。
6. SPF 的“小超页”大小/对齐（当前超页 512MiB、片段 64MiB？）。
7. PTE `[63:62]` 的 HMON/SMON 优先级、与 R/W/X 的检查顺序。
8. 42 位 VA 下 user/kernel 的地址划分、`TASK_SIZE`/`PAGE_OFFSET`。

## Consequences

- 地址翻译/页表/QEMU/测试需要整体同步；现有 48 位/64 PTBR/pahi/pthi 用例全部失效。
- 页级 HMON/SMON 取代 PTBR perm；user/kernel 隔离依赖 PTE 位，必须补全访问矩阵。
- 高 6 位 0 的 direct pmem 模式解决 boot；但需定义 `ptw_enable` 时序与初始页表。
- 若不合并 TLB，则 ptw/tlb 两个 cfx 的异常/接口继续保持；合并则简化 HBI/别名，但 ptw 变重。
