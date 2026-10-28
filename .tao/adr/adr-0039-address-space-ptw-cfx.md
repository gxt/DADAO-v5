# ADR-0039: 地址空间、PTW/PTE、TLB 与 CFX 核内空间（详细讨论记录）

**状态**：Proposed（2026-10-28/29 讨论已汇总；**未 Accepted**；`spec/` 未改）
**日期**：2026-10-29
**关联**：`spec/DADAO-12-SEE`、`spec/DADAO-13-HEE`、`contracts/cfx-aliases.txt`、QEMU ptw/TLB、`TESTCASES-*`

> 本 ADR 的目标：把已经确认的地址空间/PTE/TLB/启动/DMA 决策**写足**，后续落地时不再重复询问。
> 仍属 Open 的项集中列在文末；Open 未定前不写死 spec。
> ADR 不承载规范正文：最终位域/寄存器表以 `spec/DADAO-12`、contracts 为准。

---

## 1. 地址空间分区

### D1.1 CPU 地址 48 位

- CPU 发出的地址是 **48 位**。
- 高 6 位 `addr[47:42]` 是分区键：
  - `0`：**内存窗口**，走 PTW；
  - `1..63`：对应 **cfx 1–63 的核内地址空间**；
- `cfx0`（`umon`）**没有内部空间**，因为高 6 位 0 被内存窗口占用。

### D1.2 VA / 核内地址 / PA

- 内存窗口的 VA = **42 位**（`VA[41:0]`）；高 6 位固定 0。
- 核内地址 = **48 位** = 高 6 位 cfx + 低 42 位内部偏移。
- 每个 cfx 1–63 的内部空间 = **42 位**（4 TiB 逻辑空间，实际 SRAM/MMIO 可稀疏）。
- 物理地址 PA = **56 位**。

### D1.3 两个地址空间不要混

- `high6=0`：CPU 访存/PTW；**不直通 pmem**。
- `high6=1..63`：cfx 内部寄存器/SRAM/MMIO；直接 `ld/st`。
- 这两者是不同地址空间；不要把 cfx 内部地址当成 PA，也不要把 PA 当成 VA。

---

## 2. PTBR 与 PTW 开关

### D2.1 单 PTBR

- 只有 **1 个 PTBR**，不是 64 项数组。
- PTBR 只存 **PPN[55:16]**（40 位），物理基址 = `PPN << 16`，64 KiB 对齐。
- 无 valid 位；PTBR=0 也是合法物理页表基址（PA 0），是否使用由 `ptw_enable` 决定。
- 删除 `pahi/pthi`；PTE 自己存 PPN，不再有高 16 位拼接。

### D2.2 ptw_enable

- `ptw_enable=0`：`high6=0` 的 CPU 访存**不翻译、直接异常**；不能偷偷直通 pmem。
- `ptw_enable=1`：按 PTBR 走页表。
- 更新顺序：
  ```
  ptw_enable = 0
  写 PTBR（PPN）
  fence
  TLB invalidate
  ptw_enable = 1
  ```
- 取消 `ptbr_enable` 位图；不再有“某个 PTBR 窗口关闭”的概念。

### D2.3 为什么不是 64 个 PTBR

- 64 个 PTBR 与 cfx 高 6 位完全重叠；
- 4 个/多个 PTBR 仍会占 cfx 窗口；
- 单 PTBR + PTE 模式位更简单；
- **不要再提“PTBR 0 预留/CXF0 直通所有 cfx”**，已明确不可行。

---

## 3. PTE 格式

### D3.1 字段总览

- PTE = 64 位。
- 叶子项使用 **HSJU 四位模式掩码**：
  - `H` = bit63（hmon）
  - `S` = bit62（smon/supv）
  - `J` = bit61（jail）
  - `U` = bit60（user）
- `[59:56]` 保留。
- `[55:16]` 或 `[55:29]`：PPN（按页大小）。
- `[15:8]`：SPF 或 GPF。
- `[7:0]`：flags：
  - `P=bit0`
  - `SP=bit1`
  - `D=bit2`
  - `A=bit3`
  - `bit4` 保留
  - `X=bit5`
  - `W=bit6`
  - `R=bit7`

### D3.2 L1 next-level（指向 L2 表）

```
[63:56] 保留
[55:16] PPN（L2 表，64KiB 对齐）
[15:1]  保留
[0]     P
```

- 非叶子项**只需要 P**；不需要 HSJU/RWX/A/D/SP。
- `P=1` 表示 L2 表有效。
- 其它位必须写 0（硬件忽略或保留，按 spec 定）。

### D3.3 L1 superpage（叶子）

```
[63:60] H S J U
[59:56] 保留
[55:29] PPN（PA[55:29]）
[28:16] 0（超页对齐）
[15:8]  SPF
[7:0]   flags（P=1, SP=1, D/A/X/W/R）
```

- 超页 512 MiB 对齐，PA[28:0] 全零，所以 PTE 只存 PPN[55:29]。
- **不要**再写成 `[55:16]` 的 PA；多出的低位是 0。
- SPF 8 位对应 8 个小超页/fragment；具体尺寸见 Open。
- `SP=1` 是区分 next-level 与 superpage 的唯一标志。

### D3.4 L2 普通页（叶子）

```
[63:60] H S J U
[59:56] 保留
[55:16] PPN（PA[55:16]）
[15:8]  GPF
[7:0]   flags（P=1, SP=0, D/A/X/W/R）
```

- 普通页 64 KiB 对齐，PA[15:0] 由 VA offset 提供。
- GPF 8 位对应 8 个 8 KiB fragment。
- `SP=0`。

### D3.5 HSJU 访问规则

- 当前模式对应位为 1 ⇒ 可访问；为 0 ⇒ 对应异常：
  - U=0 → NUPERM
  - J=0 → NJPERM
  - S=0 → NSPERM
  - H=0 → NHPERM
- RWX 与 HSJU 正交。
- 典型页（待 Open 5 最终确认）：
  - 用户页：`U=1, S=1`（内核 `copy_from_user`）
  - 内核页：`S=1`
  - hmon 页：`H=1`
  - jail 页：`J=1, S=1`
  - 共享页可多位组合。
- **不要**再用“HMON/SMON 00 是普通页/01 仅 S/10 仅 H”的旧两位语义；已改为 HSJU 四位掩码。

### D3.6 A/D

- A/D 由硬件维护；不是软件每次扫描。
- 基本语义：
  - A：页被访问（读/写/取指）时置 1；
  - D：页被写时置 1；
- 具体 TLB 回写见 §4。
- L1 next-level 不更新 A/D。

---

## 4. TLB

### D4.1 合并

- `cfx_tlb` 合并进 `cfx_ptw`。
- cfx5 释放。
- TLB 异常是 ptw 异常子集，不再单独一套。

### D4.2 ASID / 索引

- ASID 必须有，独立寄存器 `ptw_tlb_asid`。
- ASID 与地址范围/inv all 正交：
  - `INV_ALL + ASID`：只清该 ASID；
  - `INV_ALL + ASID_ANY`：全清；
  - `INV_RANGE + ASID`：该 ASID 范围；
  - `INV_VA + ASID`：单 VA。
- 不再按 64 个 PTBR 集合索引；按 VA/ASID/页大小匹配。
- 单 VA 是 range 的特殊情况：`size = 页大小`；**不需要单独 page_size 操作数**，硬件按 TLB 条目自身页大小匹配。

### D4.3 A/D dirty 与回写

- TLB 条目记录：
  - `A_local/D_local`：TLB 内当前值；
  - `A_dirty/D_dirty`：fill 时 PTE 对应位为 0，且后来置位过；
- fill 时：
  - PTE A=0 → A_dirty=1；
  - PTE D=0 → D_dirty=1；
  - 已为 1 的位不需要回写，dirty=0。
- evict/flush 时：
  - 只对 dirty 位做 **原子 OR** 到 PTE；
  - 不是整 PTE 覆盖；
  - 回写后清 dirty。
- 多 hart 暂不考虑；单 hart 本地完成。
- OS 清 A/D 后必须 TLB invalidate，否则 TLB 旧值/旧 dirty 不一致。
- 页表页必须可写；回写失败 → 异常，不能静默丢 A/D。

### D4.4 操作术语（不要再用口语）

- **CLEAN**：回写 A/D，保留 TLB 条目；
- **FLUSH**：回写 A/D + 删除条目；
- **INVALID**：只删除，不回写；A/D 丢失。
- 作用域：all / ASID / VA / range。
- 正常 CLEAN/FLUSH/INVALID 不产生异常；非法编码/操作数才 CFXREG/ILLI。
- 不使用 `DISCARD` 作为正式名；`INVALID` 就是“不回写的失效”。

### D4.5 开启/关闭

- 不设 `tlb_enable`/`tlb_exist`。
- PTBR/`ptw_enable` 开启即启用 TLB。
- **不做硬件自动 flush**；PTBR/ASID 切换后由软件 invalidate。
- PTW 关闭时 TLB bypass；重新开启由软件决定是否清空。

---

## 5. 异常路由

### D5.1 当前模式异常

以下同步异常进入**当前运行模式的 cfx**：

- ILLI、UNDI（译码）
- RASOF、RASUF
- IALIGN（取指前）
- MALIGN（有效地址算出后、访存前）

目标：

- U → `cfx_umon`
- J → `cfx_jmon`
- S → `cfx_smon`
- H → `cfx_hmon`

`cfx0` 保留 `umon`，不改名。

### D5.2 MALIGN

- 判断：`EA % access_width != 0`，宽度 2/4/8；1 字节永不 MALIGN。
- 时机：地址计算后、真正访存前；精确异常。
- `ldm/stm`：基址按元素宽度对齐；否则第一次传输前 MALIGN，避免部分完成。
- 优先级：IALIGN → ILLI/UNDI → MALIGN → 页表异常/访存。
- `cfxld/cfxst` 的 DMA 对齐错误**不占 MALIGN**，归 `CFXDMA`。

### D5.3 页表异常

- PTW 页表异常进入 `cfx_ptw`，运行模式 supv（按用户此前口径）。
- TLB 异常是 ptw 子集。
- NSPERM/NHPERM 保留。

### D5.4 DMA 异常

- DMA 同步/异步错误统一 `CFXDMA`。
- `CFXREG` 只给非法 cfx 寄存器访问；`ILLI/UNDI` 只给编码。
- `CFXDMA` cause info：
  - 方向（ld/st）
  - 内部地址
  - PA
  - size
  - source：`CFX` / `PMEM`
  - 错误类型：越界/对齐/总线/超时/ECC
- 同步错误：发射时精确异常。
- 异步错误：DMA 完成后异步异常；owner 记录发起 mode/cfx。
- outstanding 数量是实现细节，不在架构层规定。

---

## 6. cfxld / cfxst

### D6.1 指令格式

```
cfxld/cfxst cfxha, rb_internal, rd_pa, rd_size
```

- `cfxha`：目标 cfx。
- `rb_internal`：内部地址（cfxha + 42 位 offset）。
- `rd_pa`：PA56（物理地址，DMA 配置）。
- `rd_size`：字节数（64 位）。
- 方向由 opcode：
  - `cfxld`：internal=dest，PA=src（pmem→cfx）；
  - `cfxst`：internal=src，PA=dest（cfx→pmem）。
- 编码：8 opcode + 6 cfxha + 6 rb + 6 rd + 6 rd = 32 位。
- 没有 imm，不需要小立即数。
- 不需要 DMA 配置寄存器。

### D6.2 语义

- 内部地址：高 6 位由 cfxha 选，寄存器只放 42 位 offset。
- PA 是物理地址，**不经过 PTW/TLB**；PTBR 前后一致。
- 异步 DMA；操作数在发射时捕获。
- 错误 → `CFXDMA`，不在指令后写状态判断。
- 完成后 `fence cfx` 等待完成/可见性。
- 单/多 outstanding 是实现细节。

### D6.3 直接 ld/st

- cfx 内部存储可直接 `ld/st`（high6=cfx + offset），同步、小数据。
- `cfxld/cfxst` 只做块 DMA，不混用单字语义。
- 不设 block_sel；内部存储按地址映射；非法/越界/未对齐 → `CFXMEM`（DMA 则 CFXDMA）。

### D6.4 CFX 内部 SRAM

- 每 cfx 1–63 可有内部 SRAM；cfx0 无。
- 大小按 **4 字节倍数**可配，无固定上限（受 42 位空间限制）。
- 大小寄存器/描述中给软件；代码/栈/异常帧按需。
- 不是所有 cfx 固定 64 KiB；按实际初始代码配置。

---

## 7. 启动骨架

### D7.1 复位与 hypv

- 复位后 hypv。
- `power` 内有 boot ROM + SRAM；`0xffff_ffff_0000` 只是跳板，不再跳 hmon 完成启动。
- `hmon` 有一小块 SRAM，负责启动期同步异常；**不碰 pmem**。

### D7.2 第一张页表

1. PTW 默认关；`high6=0` 的 CPU 访存直接异常，不直通 pmem。
2. 初始化 pmem（start/size/attr），保留页表区。
3. 用 `cfxld/cfxst` + PA 把第一张页表写进 pmem（页表只在 pmem）。
4. `fence cfx_pmem`。
5. 写 PTBR（PPN[55:16]）。
6. 置 `ptw_enable=1`。
7. 通过 VA 继续建完整页表，配置 smon/HSJU，交 supv。

### D7.3 交接

- hmon 初始化完资源后交 smon/supv；不要求完整 HEE。
- 页表、SRAM、pmem 不混用；hmon 启动异常处理不依赖 pmem。
- 不设“高 6 位 0 直通 pmem”的启动洞。

---

## 8. 已否决/不要再提

- 64 个 PTBR 全占高 6 位。
- 预留 PTBR 0 作为“所有 cfx 直通窗口”。
- `high6=0` 直通 pmem。
- DMA 使用 VA/PTW/TLB。
- `cfxld/cfxst` 使用 immu12/immu18 做长地址。
- `cfxld/cfxst` 使用一个 `rb_data` 传数据。
- 页表放 SRAM。
- 每个 cfx 固定 64 KiB SRAM。
- 把 DMA 错误记成 CFXREG。
- TLB 硬件自动 flush（本设计由软件负责）。
- 用 `discard` 作为正式 TLB 操作名。

---

## 9. Open（阻塞 Accepted/spec）

1. **cfx1–63 访问权限**：控制寄存器位置、粒度（cfx/偏移）、默认值；控制寄存器仅 S/H。
2. **启动闭环**：power/hmon SRAM 布局/大小、cfx_pmem 的 SRAM/DMA、页表保留区、PTBR/ptw_enable 时序、hmon 启动异常。
3. **HEE 最小职责/所有权**：hmon 与 power 边界、哪些资源归 HEE、哪些交 SEE。
4. **DMA 组织**：每 cfx 本地 DMA vs 共享后端 vs 独立 `cfx_dma`（当前建议本地，不做独立 cfx）。
5. **U/S 页策略**：用户页是否必须 `U+S`、kernel `S`、jail `J+S`；hmon 能否访问 `S` 页；NUPERM/NJPERM 是否保留编码。
6. **小超页/SPF**：最终尺寸/对齐；GPF 与 superpage/L2 边界。
7. **cfx4/cfx5 命名与 TLB 接口细节**：ASID 宽度、命令编码、cfx4 是否 reserved。
8. **42 位 VA 的 user/kernel 划分**：`TASK_SIZE/PAGE_OFFSET`。
9. **spec/QEMU/tests 落地**：semihosting 目标重定向、arch 覆盖、最终全量/夜跑。

## 10. Consequences

- 现有 48 位/64 PTBR/pahi/pthi/perm 用例全部失效。
- 页级 HSJU 取代 PTBR perm；user/kernel 隔离依赖 Open 5。
- 页表只在 pmem；启动靠 cfxld/cfxst + PA 写第一张页表；PTW 默认关。
- TLB 合并后 ptw 变重，但 cfx5 释放、接口/别名减少。
- 本 ADR 未 Accepted 前不改 `spec/`；Open 1–5 定完后按本 ADR 落 SEE。
