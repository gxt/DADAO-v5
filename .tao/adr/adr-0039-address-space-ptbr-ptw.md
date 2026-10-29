# ADR-0039: 地址空间、PTBR/PTW 与访存异常入口

**状态**：Proposed
**日期**：2026-10-29
**关联**：ADR-0040（PTE/页表）、ADR-0041（TLB）、ADR-0042（CFX/DMA）、ADR-0043（启动）；`spec/DADAO-12` §2；任务 `INTEG-038t`

## Context（背景）

旧口径把 VA 当 48 位、用 VA 高 6 位选择 64 个 PTBR，并用 `pahi/pthi` 拼物理地址。该结构与 cfx 高 6 位地址分区重叠，且无法表达单页表、56 位 PA。Step 1 需要先固定地址空间和 PTW 开关，后续 PTE/TLB/启动都依赖它。

## Decision（决策）

- **D1 CPU 地址 48 位**：`addr[47:42]` 是分区键；`0` 为内存窗口，`1..63` 为 cfx 1–63 核内空间；`cfx0`（umon）没有内部空间。
- **D2 地址宽度**：内存窗口 VA = 42 位（`VA[41:0]`）；每个 cfx 核内空间 = 42 位（高 6 位由地址/`cfxha` 给出）；PA = 56 位。CPU 地址与 PA 是两个地址空间，不能互相当作对方。
- **D3 单 PTBR**：只有一份 `cfx_ptw_ptbr`，只存 `PPN[55:16]`，物理基址 64 KiB 对齐；无 valid 位、无 64 项数组、无 `pahi/pthi`、无 `ptbr_enable` 位图。PTBR=0 是合法基址 PA 0，是否使用由 `ptw_enable` 决定。
- **D4 `ptw_enable`**：0 时 `high6=0` 的 CPU 访存（含取指）不翻译，触发 **CFXMEM**，目标是当前运行模式的 cfx；不得直通 pmem。1 时按 PTBR 走页表。复位 PTBR=0、`ptw_enable=0`、TLB 空。
- **D5 无隐含 TLB 操作**：写 PTBR 或写 `ptw_enable=1` 都允许，但不隐含 TLB invalidate；软件显式 invalidate。
- **D6 非法核内访问**：保留 cfx（7–14、19–61）的普通 `ld/st` 和取指触发 **CFXMEM**；`trap/escape` 到保留 cfx 沿用 ILLI。
- **D7 基本异常入口**：ILLI、UNDI、RASOF、RASUF、IALIGN、MALIGN 进入当前运行模式的 cfx（U/J/S/H → umon/jmon/smon/hmon）；MALIGN 在地址计算后、访存前，按访问宽度检查。页表异常、DMA 异常分别见 ADR-0040/ADR-0042。
- **D8 权限后置**：cfx1–63 的核内访问权限不在本 ADR 定义，留到后续 CFX 权限 ADR。

## Rationale（理由）

单 PTBR + 56 位 PA 消除高 6 位与 cfx 分区的重叠；PTE 自存完整 PPN，不再需要 `pahi/pthi` 高 16 位拼接。PTW 关闭时报 CFXMEM 而不是页表异常，因为此时页表/PTW 可能尚未初始化，启动期只能靠 hmon 处理。显式 TLB 失效避免硬件隐含行为，便于软件控制和测试。

## Consequences（影响）

- `spec/DADAO-12` §2 改为 48 位 CPU 地址、42 位 VA、56 位 PA、单 PTBR、`ptw_enable`。
- 旧 64 PTBR、`pahi/pthi`、PTBR 模式权限、`ptbr_enable` 全部失效。
- Step 1 只验证地址分区、PTBR、PTW 关闭/打开和 fail-closed；真正页表步进在 ADR-0040。

## 状态说明

Step 1 已由 `INTEG-038t` 落地并验收；本 ADR 仍为 Proposed，待 Step 2–5 全部收口后再评估 Accepted。
