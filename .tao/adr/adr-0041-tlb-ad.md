# ADR-0041: TLB 与 A/D 维护

**状态**：Proposed
**日期**：2026-10-29
**关联**：ADR-0040（PTE）；`spec/DADAO-12` §2.2.5/§4.6；任务（Step 3，待立）

## Context（背景）

旧设计有独立的 `cfx_tlb`（cfx5），按 64 个 PTBR 划分 TLB 集合，并有 `tlb_enable`/`tlb_exist`。ADR-0039 已改为单 PTBR，ADR-0040 已定义 PTE 与页权限；TLB 需要合并进 `cfx_ptw`，并定义 A/D 的硬件维护方式。

## Decision（决策）

- **D1 合并**：`cfx_tlb` 合并进 `cfx_ptw`；cfx5 释放；TLB 异常作为 ptw 异常子集，不再有独立 TLB 异常入口。
- **D2 ASID**：使用独立 `ptw_tlb_asid`；TLB 按 VA/ASID/页大小匹配，不按 64 个 PTBR 集合索引。
- **D3 操作**：
  - `CLEAN`：回写 A/D，保留条目；
  - `FLUSH`：回写 A/D 并删除条目；
  - `INVALID`：只删除、不回写；
  - 作用域：all / ASID / VA / range；单 VA 是 range 的特殊情况。
- **D4 A/D dirty**：TLB 条目记录 `A_local/D_local` 与 `A_dirty/D_dirty`；fill 时若 PTE A/D 为 0 则置 dirty；evict/flush 只对 dirty 位做**原子 OR** 回写，不整 PTE 覆盖；回写后清 dirty。
- **D5 软件负责失效**：不设 `tlb_enable`/`tlb_exist`；PTBR/`ptw_enable` 开启即启用 TLB；写 PTBR/切 ASID 不自动 flush；PTW 关闭时 TLB bypass，重新开启由软件决定是否清空。
- **D6 正常操作不异常**：CLEAN/FLUSH/INVALID 正常完成不产生异常；非法编码/操作数才 CFXREG/ILLI。
- **D7 回写失败**：页表页必须可写；A/D 回写失败必须报异常，不能静默丢弃。

## Rationale（理由）

单 PTBR 后，按 64 集合划分 TLB 已无意义；ASID 足以区分地址空间。A/D 用 dirty 位回写而不是每次访存原子写 PTE，减少页表写放大；但软件清 A/D 后必须显式失效，硬件不猜。

## Consequences（影响）

- `cfx5` 可释放给其他 cfx；`cfx_tlb` 寄存器/异常原因删除或并入 `cfx_ptw`。
- Step 2 的页表步进需为 Step 3 预留 A/D dirty 结构；Step 2 不验证 A/D 更新。
- OS 进程切换必须显式 invalidate；不能依赖写 PTBR 自动失效。

## 状态说明

TLB 的 ASID 宽度、命令编码、寄存器布局仍需在 Step 3 落地前确认；本 ADR 先冻结行为语义。
