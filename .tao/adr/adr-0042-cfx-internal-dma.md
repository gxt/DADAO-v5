# ADR-0042: CFX 核内空间、cfxld/cfxst 与 DMA

**状态**：Proposed
**日期**：2026-10-29
**关联**：ADR-0039（地址空间）、ADR-0044（fence ciii）；`spec/DADAO-12` §1/§2.1/§2.2；任务（Step 4，待立）

## Context（背景）

cfx1–63 各有一段 42 位核内空间，CPU 可以直接 `ld/st`。大块数据需要在 cfx 内部存储与 pmem 之间搬运，但 DMA 不能走 VA/PTW，也不能把核内地址当物理地址。需要固定传输指令和 DMA 错误语义。

## Decision（决策）

- **D1 核内空间**：cfx1–63 内部空间 42 位（4 TiB 逻辑空间，实际 SRAM/MMIO 可稀疏）；cfx0 没有内部空间；核内地址 = 高 6 位 cfx + 低 42 位 offset。
- **D2 直接 ld/st**：核内存储直接 `ld/st`，同步、小数据；不设 `block_sel`；内部存储按地址映射；非法/越界/未对齐 → CFXMEM。
- **D3 传输指令**：`cfxld/cfxst cfxha, rb_internal, rd_pa, rd_size`；`cfxha` 选 cfx，`rb_internal` 只放 42 位 offset，`rd_pa` 是 PA56，`rd_size` 是字节数；方向由 opcode 决定。
- **D4 语义**：PA 不经过 PTW/TLB；操作数在发射时捕获；异步 DMA；`cfxld/cfxst` 只有一个 `cfxha`，没有“发起 cfx”第二角色；`fence` 只保证顺序/可见性，不等待完成（ADR-0044）；outstanding 数量是实现细节。
- **D5 本地 DMA**：每个 cfx 本地 DMA，不单独做 `cfx_dma`，不设 DMA 配置寄存器；CFX 内部 SRAM 大小按 4 字节倍数可配，不固定 64 KiB。
- **D6 同步错误 `CFXLDST`**：仅用于发射时就能判定的错误（`rd_size=0`、目标 cfx 不接受的对齐/范围/MMIO、无 DMA 能力）；精确异常、不可屏蔽、DMA 未启动、无副作用；`cause_info` 记录方向/内部地址/PA/size/错误类型；目标 = `cfxha`。
- **D7 异步错误 `CFXDMA`**：用于发射后发生的总线/超时/ECC/中途错误；异步中断、可屏蔽/pending；可能部分完成、不可回滚；目标 = `cfxha`；`cause_info` 记录同一组字段；`fence` 不清 pending。
- **D8 编码**：`CFXLDST = 1<<3`、`CFXDMA = 1<<4`；`PTWERR=1<<7` 不变；reserved cfx 仍 `ILLI`，不归入这两个 cause。
- **D9 传输边界**：ISA 不强制 `rd_pa`/内部地址对齐；`rd_size` 为字节数；`rd_size=0` 统一 `CFXLDST`；各 cfx 可对对齐/范围/MMIO/SRAM 加限制，不满足时 `CFXLDST`；`cfx0` 无内部空间，`cfxld/cfxst` → `CFXLDST`。
- **D10 cfx 编号**：`cfx5` 为 cache（由原 cfx6 移入）；`cfx6–14`、`cfx19–61` reserved；reserved cfx 的 cfx 指令一律 `ILLI`。
- **D11 与启动的关系**：第一张页表通过 `cfxld/cfxst` + PA 写入 pmem，启动细节见 ADR-0043。

## Rationale（理由）

DMA 直接使用 PA，避免页表/VA 语义混入设备搬运；`cfxld/cfxst` 四寄存器格式不需要 imm 或配置寄存器，减少 rc/cg 数量。本地 DMA 避免一个共享后端成为所有 cfx 的瓶颈，也不引入新的 `cfx_dma` 编号。直接 ld/st 与块 DMA 分工明确，避免单字语义和异步语义混用。

## Consequences（影响）

- 删除 `sram_block_sel/sram_addr` 一类按块选择的接口；内部存储按地址映射。
- `cfxld/cfxst` 的 PA 不经过 PTW/TLB；启动期 PTW 关闭时也能用。
- 页表只能放 pmem，不能放 SRAM；DMA 不能使用 VA。
- cfx 访问权限仍由后续 CFX 权限 ADR 决定，本 ADR 不定义谁能访问哪个 cfx。

## 状态说明

Step 4 待落地；cfx 访问权限、DMA 多通道/共享后端优化后置。fence 语义见 ADR-0044；`CFXLDST`/`CFXDMA` 的编码与 spec/QEMU/测试同步在 Step 4 落地。
