# 资源管理 -- cfx 存储模型

**本册要点**

- `cfxld`/`cfxst`：cfx 内部 SRAM 与内存之间的块传输。
- 64 B 对齐；长度 = `immu12 × 64`。
- `block_sel`（cg7 rc0）选块；`sram_addr`（cg7 rc1）选块内偏移。
- 当前 deferred；未实现时 decode ILLI。
- 不是 DMA：无 descriptor/中断。
- 边界：vs MMIO 逐字、vs `memcpy` 内存到内存。

## 1. 为什么 cfx 需要自己的内部 SRAM，而不是直接 MMIO 访问设备？

**答：** 因为有些设备的内部存储不是“按寄存器逐字访问”的，而是“一块缓冲”；给 cfx 配内部 SRAM，可以用一条块传输指令搬整块数据，避免逐字 MMIO 的开销。

- **内部 SRAM**：cfx 自己的块存储；不是通用内存，也不在 48 位地址空间里。
- **块传输**：`cfxld`/`cfxst` 在 SRAM 与内存之间搬 64 字节的整数倍。
- **对比 MMIO**：MMIO 适合控制/状态寄存器；大块数据逐字读写会产生大量总线事务。
- **对比 DMA**：DMA 有 descriptor/完成中断；`cfxld`/`cfxst` 是 CPU 驱动的简单块传输。
- **现状**：`cfxld`/`cfxst` 仍 deferred，语义未定稿。

## 2. 为什么要求 64 字节对齐、64 字节的倍数？

**答：** 因为 64 字节是块传输的粒度：对齐后一次传输不会跨块边界，硬件可以按块搬运，不需要处理首尾碎片。

- **对齐**：`rbHB` 与 `cfx_<name>_sram_addr` 都要 64 字节对齐。
- **长度**：`immu12 × 64` 字节；不足一块的余量无法表达。
- **为什么是 64**：和 cache line 的常见粒度一致；块内偏移用 64 字节对齐的 `sram_addr`。
- **代价**：小于 64 字节的传输要软件补齐或改用寄存器访问。

## 3. 为什么用 `block_sel` + `sram_addr` 两级定位？

**答：** 因为一个 cfx 可能有多个 SRAM 块，块内还要指定起始偏移；`block_sel` 选块，`sram_addr` 选块内偏移。

- **`block_sel`**（cg7 rc0）：选择目标 SRAM 块。
- **`sram_addr`**（cg7 rc1）：块内字节偏移，须 64 字节对齐。
- **为什么两级**：块数由 `block_sel` 的位宽决定，块内偏移由 `sram_addr` 决定；不需要把“块号 × 块大小 + 偏移”压成一个扁平地址。
- **对比**：DMA 用 descriptor 指定地址/长度；cfx 用两个寄存器 + 一条指令，更简单但没有链式传输。

## 4. 为什么 `cfxld`/`cfxst` 是 deferred？

**答：** 因为块传输的语义还没有定稿，当前也没有必须使用它的消费方；先保留编码，等真实场景明确后再启用。

- **状态**：`cfxld`/`cfxst` 暂不启用；未实现该语义的机器执行时 decode ILLI。
- **触发条件**：需要“设备内部 SRAM ↔ 内存”的整块搬运，且 MMIO/逐字访问代价太高。
- **风险**：块大小、错误处理、与 cache 的一致性还没冻结；过早启用会返工。
- **对比**：DMA 已经能覆盖大块搬运；cfx 块传输只在“设备内部 SRAM 不是内存映射”时才有优势。

## 5. 与 DMA、MMIO、`memcpy` 相比，cfx 块传输的边界在哪里？

**答：** `cfxld`/`cfxst` 是“CPU 直接驱动的、设备内部 SRAM ↔ 内存”的块传输；它没有 descriptor/中断，也不是内存到内存的 `memcpy`。

- **vs DMA**：没有 descriptor 链、没有完成中断；CPU 在指令流里发起。
- **vs MMIO**：不是逐寄存器读写，而是一整块搬运。
- **vs `memcpy`**：目标是 cfx 内部 SRAM，不是普通内存；受 64 字节对齐/倍数约束。
- **适用**：设备缓冲、固件/表项加载；不适用于通用大内存拷贝。

## 背景知识

### 术语与概念

- **SRAM**：cfx 内部的块存储，不是通用内存。
- **块传输**：以 64 字节为单位，在 cfx SRAM 与内存之间搬数据。
- **DMA**：由独立引擎按 descriptor 搬运，通常带完成中断；`cfxld`/`cfxst` 不是 DMA。
- **MMIO**：把设备寄存器映射到内存地址；cfx 走寄存器窗口，不走 MMIO。
- **对齐**：`cfxld`/`cfxst` 要求 64 字节对齐与 64 字节倍数。

### 对照

**x86-64**：`MOVDIR64B` 做 64 字节直接存储；设备多用 MMIO/DMA。

**ARM64**：`LD`/`ST` + DMA；设备多用 MMIO。

**RISC-V**：MMIO + DMA；没有 cfx 内部 SRAM 这一层。

**MIPS**：MMIO + DMA。

**SPARC**：MMIO + DMA。

**PowerPC**：MMIO + DMA。
