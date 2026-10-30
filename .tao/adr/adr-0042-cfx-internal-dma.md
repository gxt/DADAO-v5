# ADR-0042: CFX 核内空间与 cfx_pmem DMA

**状态**：Accepted
**日期**：2026-10-30
**关联**：ADR-0039（地址空间）、ADR-0044（fence）；`spec/DADAO-12` §1/§2.1/§2.2；任务 `INTEG-042t`（Step 4）

## Context（背景）

cfx1–63 各有一段 42 位核内空间，CPU 可以直接 `ld/st`。此前考虑用 `cfxin/cfxout` 指令或每个 cfx 自带 DMA 完成块搬运，但这会把 DMA 变成通用指令语义，并要求每个 cfx 实现 DMA，职责过重。现简化为：只在 `cfx_pmem` 内提供 SRAM 和 DMA，CPU 通过 `ld/st` 访问该 SRAM，DMA 只在 SRAM 与 physical memory 之间搬运。

## Decision（决策）

- **D1 核内空间**：cfx1–63 内部空间 42 位；cfx0 无内部空间；核内地址 = 高 6 位 cfx + 低 42 位 offset。
- **D2 CPU 直接访问**：CPU 对任意 cfx 内部 SRAM/MMIO 用普通 `ld/st`，同步、小数据；非法/越界/未对齐 → CFXMEM。**不设 `cfxin/cfxout` 指令**。
- **D3 cfx_pmem SRAM**：`cfx_pmem`（cfx17）内配置一段 **64 KiB** SRAM（初版，64 KiB 对齐，核内起始 `0x47ff_0000_0000`，内部偏移 0）；大小/基址可由 cfx_pmem 描述/寄存器报告；CPU 可直接 `ld/st` 访问。
- **D4 cfx_pmem DMA**：cfx_pmem 内 DMA 只在 **cfx_pmem SRAM ↔ physical memory（PA56）** 之间搬运；PA 不经 PTW/TLB；不直接访问其它 cfx 的 SRAM。
- **D5 设备通路**：device ↔ pmem 由 CPU 中转：CPU 把 device SRAM 数据搬到 cfx_pmem SRAM，再由 DMA 写 pmem；反向同理。高带宽设备若需直连，后续另加本地 DMA，不改变本模型。
- **D6 无 per-cfx DMA**：不在每个 cfx 后挂 DMA，不设 `cfx_dma`，不新增 DMA ISA 指令；DMA 只属于 cfx_pmem。
- **D7 控制/状态**：DMA 由 cfx_pmem 的 rc 寄存器控制（源/目的/大小/方向/启动/状态）；CPU 写完 SRAM 后触发，DMA 完成后 CPU 才能复用。完成/错误事件用 cfx_pmem 的 status/pending；具体 cause 名与位在 Step 4 落地时定。
- **D7.4 cfx_pmem DMA 异常**：新增 `PMEM_DMA = 1 << 8`，异步、可屏蔽；`dma_ctrl.IRQ_EN=1` 时 `DONE` 或 `ERROR` 触发；`cause_info` 携带 `dma_status`（含 `ERR_CODE`）；被屏蔽时置 cfx_pmem pending；目标 cfx 为 `cfx_pmem`。cfx 异常原因编码按 cfx 独立编址，`1<<8` 在 cfx_pmem 内不与其它 cfx 冲突。当前按**单 hart 简化**：`PMEM_DMA` 直接投递到该 hart 的 cfx_pmem 异常入口；多 hart 的接收者/target 规则后置。
- **D7.3 寄存器落点**：`cfx_pmem` SRAM 固定内部偏移 0、64 KiB；DMA 寄存器放 `cfx_pmem` cg15：rc0 `dma_src`、rc1 `dma_dst`、rc2 `dma_size`、rc3 `dma_ctrl`、rc4 `dma_status`；cg15 其余 rc 保留；不新增 SRAM base 寄存器，后续多 SRAM 块再扩展。
- **D7.2 控制/状态位**：`dma_ctrl`：bit0 START（启动后自清）、bit1 DIR（0=CFX→PA，1=PA→CFX）、bit2 IRQ_EN；其余 SBZ。`dma_status`：bit0 BUSY（RO）、bit1 DONE（W1C）、bit2 ERROR（W1C）、bit3..15 ERR_CODE（13 位 one-hot，RO；用户裁定：字段有几位占几位，不在 spec 写 16 位）、其余保留。`ERROR` W1C 时一并清 `ERR_CODE`；`BUSY=1` 时忽略 `DONE/ERROR` 的 W1C。
- **D7.1 地址与长度**：`dma_src`/`dma_dst` 为 64 位；方向位 1 位（0=CFX→PA，1=PA→CFX）。CFX 侧只取低 42 位，PA 侧只取低 56 位；高位**忽略**，不因高位非 0 报错。`dma_size` 为 30 位，合法范围 `1..2^29`（512 MiB）；`size=0` 或 `>512 MiB` 报 setup 错误。实际传输还受当前 SRAM 范围/PA 范围/地址+size 溢出约束。
- **D8 启动**：hmon 可把第一张页表写入 cfx_pmem SRAM，再由 DMA 写到 PA；PTW 可保持关闭，不需要直通 pmem 的启动洞。
- **D9 权限**：CPU 访问 cfx_pmem SRAM 的模式权限归 Step 6；本 ADR 不定义。

## Rationale（理由）

DMA 是内存侧资源，放在 `cfx_pmem` 最自然；CPU 直接 `ld/st` 访问各 cfx 已覆盖控制/小数据，DMA 只解决 pmem 批量搬运。这样不需要每个 cfx 实现 DMA，也不需要把块搬运塞进 ISA；设备高带宽需求可后续单独扩展。

## Consequences（影响）

- `cfxin/cfxout`、`crii`、`immu12`、64 字节/块选择接口全部不采用。
- cfx_pmem 需要 SRAM + DMA 控制/状态寄存器；CPU 与 DMA 并发访问 SRAM，软件必须做所有权/双缓冲/同步。
- device↔pmem 需 CPU 中转，带宽受 CPU 限制；这是本简化模型的明确代价。
- 启动仍可在 PTW 关闭时用 SRAM+DMA 建第一张页表。
- cfx5=cache、cfx6–14/19–61 reserved 的编号安排保留；权限见 Step 6。

## 状态说明

用户已确认“设备↔pmem 由 CPU 中转”和“当前单 hart 简化”。`cfx_pmem` 的 SRAM 大小、DMA 寄存器布局、完成/错误 cause 名留 Step 4 落地前确定。
