# ADR-0039: 地址空间、PTW/PTE、TLB 与 CFX 核内空间

**状态**：Proposed（2026-10-28/29 讨论已汇总；未 Accepted，spec 未改）
**日期**：2026-10-29
**关联**：`spec/DADAO-12-SEE`、`spec/DADAO-13-HEE`、`contracts/cfx-aliases.txt`、QEMU ptw/TLB、`TESTCASES-*`

> **决策来源（用户 2026-10-28/29，经主会话问答）**：48 位 CPU 地址；高 6 位 0 只走 PTW；VA42；单 PTBR；PA56；删 `pahi/pthi`；PTE 用 HSJU 四位掩码；A/D 硬件；TLB 合并进 `cfx_ptw`；cfxld/cfxst 用寄存器传参；cfx0 保留 `umon`。
> **ADR 不承载规范正文**：寄存器表/位域由 `spec/DADAO-12` 与 contracts 落笔。

## Context

- 原设计：48 位 VA，高 6 位选 64 个 PTBR；`pahi/pthi` 拼 PA 高 16 位；PTE 高位放 SPF/GPF；`cfx_ptw_*_perm` 控 PTBR 访问；`cfx_tlb` 独立。
- 新目标：让地址翻译/页表空间与 cfx 核内空间不重叠；简化 PTBR/TLB；把运行模式下沉到 PTE；DMA 用 PA。

## Decision（已确认项）

- **D1 — 地址分区**：CPU 地址 48 位；`[47:42]==0` 为内存窗口（PTW）；`1..63` 为 cfx 1–63 核内空间；cfx0 = `umon`，无内部空间；cfx1–63 各 42 位内部空间。
- **D2 — VA/PTBR**：内存窗口 VA = 42 位；**单 PTBR**，只存 PPN[55:16]（40 位，64KiB 对齐）；无数组、无 valid 位、无 `ptbr_enable` 位图。
- **D3 — PTW 开关**：`ptw_enable=0` 时高 6 位 0 的 CPU 访存**直接异常，不直通 pmem**；`ptw_enable=1` 才按 PTBR 翻译。更新顺序：`ptw_enable=0 → 写 PTBR → fence → TLB invalid → ptw_enable=1`。
- **D4 — PA/PPN**：PA 56 位；删除 `pahi/pthi`；PTE 存 **PPN**，不存完整 PA；`PA = PPN + offset`。
- **D5 — PTE 布局**：
  - L1 next-level：`[63:56]` 保留；`[55:16]` PPN（L2 表）；`[15:1]` 保留；`[0]` P=1；**无 HSJU/RWX/A/D**。
  - L1 superpage：`[63:60]` HSJU；`[59:56]` 保留；`[55:29]` PPN（PA[55:29]）；`[28:16]` 0；`[15:8]` SPF；`[7:0]` flags。
  - L2 普通页：`[63:60]` HSJU；`[59:56]` 保留；`[55:16]` PPN；`[15:8]` GPF；`[7:0]` flags。
  - flags：`P=bit0`、`SP=bit1`、`D=bit2`、`A=bit3`、`bit4 保留`、`X=bit5`、`W=bit6`、`R=bit7`；`SP=1` 仅 L1 superpage。
- **D6 — HSJU 四位掩码**：H=63、S=62、J=61、U=60；当前模式对应位为 1 才可访问；RWX 与模式位正交；NUPERM/NJPERM/NSPERM/NHPERM 保留。典型页：user `U+S`、kernel `S`、hmon `H`、jail `J+S`（具体策略见 Open）。
- **D7 — A/D 与 TLB**：A/D 由硬件维护；TLB fill 读 PTE，TLB 条目记录 `A_local/D_local` 与 `A_dirty/D_dirty`；evict/显式 flush 时对 PTE 原子 OR；OS 清 A/D 后必须 TLB invalidate。
- **D8 — TLB 操作术语**：`CLEAN`=回写 A/D 保留条目；`FLUSH`=回写 A/D + invalidate；`INVALID`=只 invalidate、不回写（A/D 丢）。作用域：all / ASID / VA / range；单 VA 含在 range；**不需要 page_size 操作数**（硬件按条目自身页大小匹配）；正常 invalid/flush 不产生异常。
- **D9 — TLB 合并**：`cfx_tlb` 合并进 `cfx_ptw`；`cfx5` 释放；ASID 独立寄存器；不设 `tlb_enable/tlb_exist`（PTBR 开启即 TLB 开启）；**不做硬件自动 flush**，由软件 invalidate。
- **D10 — 异常路由**：ILLI/UNDI/RASOF/RASUF/IALIGN/MALIGN → **当前模式 cfx**（umon/jmon/smon/hmon）；MALIGN 在有效地址算出后、访存前；ldm/stm 在首传前；DMA 对齐不占 MALIGN。页表异常 → `cfx_ptw`（运行模式 supv）。NSPERM/NHPERM 保留。
- **D11 — DMA 异常**：DMA 同步/异步错误用 **`CFXDMA`**，cause info 带方向、内部地址、PA、size、source（CFX/PMEM）；`CFXREG` 只给非法 cfx 寄存器访问，`ILLI/UNDI` 只给编码。
- **D12 — cfxld/cfxst**：`cfxld/cfxst cfxha, rb_internal, rd_pa, rd_size`；内部地址用 rb，PA56/size 用 rd；PA 物理地址、不经过 PTW/TLB；异步；无 imm、无 DMA 配置寄存器；错误 `CFXDMA`；完成后 `fence cfx`。outstanding 数量为实现细节。
- **D13 — 直接 ld/st**：cfx 内部存储可直接 ld/st（high6=cfx + offset）；不经过 cfxld/cfxst；大小按 4 字节倍数可配、无上限；cfx0 无内部空间。
- **D14 — 启动骨架**：power 内 ROM+SRAM；hmon 小 SRAM 负责启动期同步异常，不碰 pmem；复位 hypv，不跳 hmon，初始化后交 supv；页表在 pmem；PTW 默认关；第一张页表用 cfxld/cfxst + PA 写入，再设 PTBR/ptw_enable。
- **D15 — HEE 范围**：不做完整 HEE；只保留 power/hmon 的启动、同步异常、资源交接；不得把页表/SRAM 混用。
- **D16 — 同步范围**：DADAO-12/13、contracts/cfx-aliases、生成器、QEMU ptw/TLB、lit/向量、spec 锁 sha/changelog/版本；以本 ADR 为决策源。

## Open questions（阻塞 Accepted/spec）

1. cfx1–63 的 user/supv/hypv 访问权限：控制寄存器位置、粒度（cfx/偏移）、默认值、控制寄存器本身仅 S/H。
2. 启动闭环细节：power/hmon SRAM 布局/大小、cfx_pmem 的 SRAM/DMA、第一张页表的保留区、PTBR+ptw_enable 时序、hmon 启动异常。
3. HEE 最小职责/所有权：hmon 与 power 的边界，哪些资源归 HEE，哪些交 SEE。
4. DMA 组织：每 cfx 本地 DMA vs 共享后端 vs 独立 `cfx_dma`。
5. U/S 页策略：user 页是否必须 `U+S`、kernel `S`、jail `J+S`；hmon 能否访问 `S` 页；NUPERM/NJPERM 是否保留编码。
6. 小超页/SPF 的最终尺寸/对齐；GPF 与 superpage/L2 的边界。
7. cfx4/cfx5 命名与 reserved 口径；TLB 接口的 ASID 宽度/命令编码。
8. 42 位 VA 下 user/kernel 地址划分（`TASK_SIZE/PAGE_OFFSET`）。
9. spec/QEMU/tests 落地、arch 覆盖、最终全量/夜跑。

## Consequences

- 现有 48 位/64 PTBR/pahi/pthi/perm 寄存器用例全部失效。
- 页级 HSJU 取代 PTBR perm；user/kernel 隔离依赖 PTE 位组合，必须先定 Open 5。
- 页表只在 pmem；启动必须靠 cfxld/cfxst + PA 写第一张页表，PTW 默认关。
- TLB 合并后 ptw 变重，但 cfx5 释放、接口/别名减少。
- 本 ADR 未 Accepted 前不改 `spec/`；Open 1–5 定完后按本 ADR 落 SEE。
