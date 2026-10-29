# ADR-0041: TLB 与 A/D 维护

**状态**：Proposed
**日期**：2026-10-29
**关联**：ADR-0040（PTE）；`spec/DADAO-12` §2.2.5/§4.6；任务（Step 3，待立）

## Context（背景）

旧设计有独立的 `cfx_tlb`（cfx5），按 64 个 PTBR 划分 TLB 集合，并有 `tlb_enable`/`tlb_exist`。ADR-0039 已改为单 PTBR，ADR-0040 已定义 PTE 与页权限；TLB 需要合并进 `cfx_ptw`，并定义 A/D 的硬件维护方式。

## Decision（决策）

- **D1 合并**：`cfx_tlb` 合并进 `cfx_ptw`；cfx5 释放；TLB 异常作为 ptw 异常子集，不再有独立 TLB 异常入口。
- **D2 ASID**：16 位 `cfx_ptw_tlb_asid[15:0]`，复位 0，所有值可用；TLB 按 VA/ASID/页大小匹配，不按 64 个 PTBR 集合索引。
- **D3 接口**：复用 `cfx_ptw` cg12，不新增 TLB 寄存器块：
  - rc0 `cfx_ptw_tlb_control`：
    - `[1:0]` 操作：`00=none`、`01=clean`、`10=invalid`、`11=flush`（bit0=写回 A/D，bit1=删除条目）；
    - `[3:2]` 地址范围：`00=all`、`01=VA`、`10=range`、`11=reserved`；
    - `bit4`：`ASID_ANY`（1=所有 ASID，0=匹配 rc1）；
    - 其余保留。
  - rc1 `cfx_ptw_tlb_asid`；
  - rc2 `cfx_ptw_tlb_addr_start`；
  - rc3 `cfx_ptw_tlb_addr_size`。
- **D3.1 正交语义**：匹配条件为 `(ASID match) AND (address match)`；操作、ASID、地址范围三个维度独立。`all` 忽略 start/size；`VA` 只匹配包含 start 的条目，size 忽略；`range` 匹配与 `[start,start+size)` 相交的条目，size=0 → CFXREG；`addr_scope=11` → CFXREG。
- **D3.2 操作语义**：
  - `CLEAN`：回写 A/D，保留条目；
  - `INVALID`：只删除、不回写；
  - `FLUSH`：回写 A/D 并删除；写回失败时**不删除该条目**并报异常；
  - `00` 为 no-op，不报异常；命令写同步执行，无完成状态寄存器。
- **D4 A/D dirty**：TLB 条目记录 `A_local/D_local` 与 `A_dirty/D_dirty`：
  - fill：`A_local=PTE.A`、`D_local=PTE.D`、`A_dirty=D_dirty=0`；fill 本身不产生 dirty；
  - 读/取指命中且权限通过：若 `A_local=0` → `A_local=1, A_dirty=1`；
  - 写命中且权限通过：若 `A_local=0` → `A_local=1, A_dirty=1`；若 `D_local=0` → `D_local=1, D_dirty=1`；
  - 缺页/权限失败：不更新 A/D；
  - evict/CLEAN/FLUSH：只把 dirty 位做**原子 OR** 回写 PTE，保留其他字段；回写后清 dirty；CLEAN 保留条目，FLUSH 删除条目，INVALID 不写回直接删除；FLUSH 写回失败不删除该条目并报异常；
  - 页表页必须可写；OS 清 A/D 后必须显式 invalidate。
- **D5 软件负责失效**：不设 `tlb_enable`/`tlb_exist`；PTBR/`ptw_enable` 开启即启用 TLB；写 PTBR、写 ASID 都不自动 flush；PTW 关闭时 TLB bypass，重新开启由软件决定是否清空。
- **D6 正常操作不异常**：CLEAN/FLUSH/INVALID 正常完成不产生异常；非法编码/操作数才 CFXREG/ILLI。
- **D7 回写失败**：页表页必须可写；A/D 回写失败必须报异常，不能静默丢弃。

## Rationale（理由）

单 PTBR 后，按 64 集合划分 TLB 已无意义；ASID 足以区分地址空间。A/D 用 dirty 位回写而不是每次访存原子写 PTE，减少页表写放大；但软件清 A/D 后必须显式失效，硬件不猜。

## Consequences（影响）

- `cfx5` 可释放给其他 cfx；`cfx_tlb` 寄存器/异常原因删除或并入 `cfx_ptw`。
- Step 2 的页表步进需为 Step 3 预留 A/D dirty 结构；Step 2 不验证 A/D 更新。
- OS 进程切换必须显式 invalidate；不能依赖写 PTBR 自动失效。

## 状态说明

ASID 16 位、cg12 布局、操作/范围/ASID 正交编码已确认；Step 3 落地时只需补实现与验证，不再改接口。A/D 回写的异常/原子细节仍按 D4/D7 在 Step 3 验证。
