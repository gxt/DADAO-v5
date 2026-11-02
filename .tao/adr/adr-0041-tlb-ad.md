# ADR-0041: TLB 与 A/D 维护

**状态**：Accepted
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
- **D3.1 正交语义**：匹配条件为 `(ASID match) AND (address match)`；操作、ASID、地址范围三个维度独立。`all` 忽略 start/size；`VA` 只匹配包含 start 的条目，size 忽略；`range` 匹配与 `[start,start+size)` 相交的条目，size=0 → CFXREG；`addr_scope=11` → CFXREG。G 条目（G=1）在 ASID 维度绕过匹配：`asid_any=1` 包含 G；`asid_any=0` 只处理 G=0 且 ASID 匹配的条目，**不碰 G**。
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
- **D8 命中与填充**：
  - TLB 条目保存 ASID、VA、页大小、PPN、HSJU、R/W/X、SPF/GPF、G、A/D；
  - 命中不重读 PTE，按 ADR-0040 D8 同序检查 `SPF/GPF → HSJU → R/W/X`；
  - miss 走页表步进，只有 PTE 有效且全部检查通过后才填充；缺页/权限失败不填 TLB、不更新 A/D；
  - 替换/组相联/全相联属实现，替换 dirty 条目按 D4 回写。
- **D9 G（Global）**：`G=1` 的 TLB 条目跨 ASID 复用；`G=0` 按 ASID 匹配。失效时 `asid_any=1` 包含 G，`asid_any=0` 跳过 G；软件必须保证 G 页在所有地址空间的映射一致。
- **D10 PTWERR**：A/D 回写失败使用异常原因 **`PTWERR = 1 << 7`**，目标 `cfx_ptw`，不可屏蔽；`cause_info` = 出错的 PTE PA；`CLEAN/FLUSH` 失败保留条目，不静默丢 A/D；`INVALID` 不写回，不受影响。
- **D11 嵌套异常**：`escape`/`inner_cfx_code` 是 M5 遗留，不在本 ADR 改；Step 3 只保证 ptw 异常入口不被无意破坏，另登 issue 复核。
- **D7 回写失败**：页表页必须可写；A/D 回写失败必须报 `PTWERR`，不能静默丢弃。

## Rationale（理由）

单 PTBR 后，按 64 集合划分 TLB 已无意义；ASID 足以区分地址空间。A/D 用 dirty 位回写而不是每次访存原子写 PTE，减少页表写放大；但软件清 A/D 后必须显式失效，硬件不猜。

## Consequences（影响）

- `cfx5` 可释放给其他 cfx；`cfx_tlb` 寄存器/异常原因删除或并入 `cfx_ptw`。
- Step 2 的页表步进需为 Step 3 预留 A/D dirty 结构；Step 2 不验证 A/D 更新。
- OS 进程切换必须显式 invalidate；不能依赖写 PTBR 自动失效。
- TLB 条目增加 G bypass；`PTWERR` 占用 cause bit7，Step 3 需同步 spec/QEMU/测试。

## 状态说明

ASID 16 位、cg12 布局、操作/范围/ASID 正交编码、G 位、A/D dirty 与 PTWERR 已确认；本 ADR 接受。Step 3 落地实现与验证；嵌套 escape 不在本 ADR 范围。
