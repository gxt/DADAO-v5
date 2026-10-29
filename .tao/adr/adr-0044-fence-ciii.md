# ADR-0044: fence ciii（按 cfx 资源域的屏障）

**状态**：Proposed
**日期**：2026-10-29
**关联**：ADR-0039（地址空间）、ADR-0042（CFX/DMA）；`spec/SimRISC-11`、`spec/SimRISC-12`、`contracts/opcodes.yaml`；任务 `INTEG-041t`（待立）

## Context（背景）

旧 `fence immu18` 位于 SimRISC-12「其它指令」，采用 `fm/pred/succ` 三字段，没有 cfx 选择。DADAO 的普通内存、cfx 内部 SRAM/MMIO、IO 设备都按 cfx 资源域划分；旧 fence 无法指定作用域，也无法区分 cfx memory、cfx IO 和系统内存。单 hart 场景下，需要的是本 hart 的资源域顺序，不是跨 hart 或 DMA 完成等待。

## Decision（决策）

- **D1 编码**：`fence` 使用 32 位 `ciii` 形式：
  - `opc = 0x79`（`0111_1001`）；
  - `ha = cfxha`（6 位）；
  - `hb = 0`（固定，SBZ）；
  - `hc = pred`（6 位掩码）；
  - `hd = succ`（6 位掩码）。
- **D2 cfx 选择**：`ha = 0` 表示 **all cfx**；汇编别名 `cfx0` 与 `cfx_umon` 都映射到 `ha=0`，不表示只作用于 umon 本地资源；`cfx1..cfx63` 表示指定 cfx。
- **D3 立即数**：汇编只写一个 18 位 `immu18`，不拆成三个操作数；其位域为：
  - `[17:12] = hb = 0`（SBZ，非 0 → ILLI）；
  - `[11:6] = pred`；
  - `[5:0] = succ`。
- **D4 pred/succ 位**：
  - bit0 `cr`（cfx memory read）
  - bit1 `cw`（cfx memory write）
  - bit2 `ci`（cfx IO input）
  - bit3 `co`（cfx IO output）
  - bit4 `mr`（system memory read）
  - bit5 `mw`（system memory write）
  - `pred=0` 且 `succ=0` 是合法 no-op。
- **D5 语义**：只保证本 hart 对所选 cfx 的对应访问顺序/可见性；不跨 hart，不等待 DMA 完成，不负责 TLB/icache 维护。
- **D6 移册**：`fence` 从 SimRISC-12「其它指令」移到 SimRISC-11「核芯功能扩展指令」；删除 `fm`/TSO；旧 `fence immu18` 与 `fence 0` 不再接受。
- **D7 汇编语法**：`fence cfx0, immu18` 或 `fence cfx_umon, immu18`；不接受 `fence 0`；`immu18` 可用符号常量按位或构造。
- **D8 异常**：`hb != 0`、reserved cfx 等按 ILLI；正常 fence 不产生异常；不改变 `CFXDMA`/`CFXLDST` 语义。

## Rationale（理由）

`cfxha` 直接表达资源域，`cr/cw/ci/co/mr/mw` 把 cfx memory、cfx IO 和系统内存分开；`cfx0`/`cfx_umon` 作为 all 的别名沿用汇编习惯。单 hart 不引入跨 hart 语义；不等待 DMA，避免不可控阻塞。`fm` 当前未使用，删除后 SBZ 保留未来扩展空间。

## Consequences（影响）

- SimRISC-11/12、DADAO-12、Toolchain-01、`contracts/opcodes.yaml`、LLVM MC/汇编器、QEMU decode（如已实现 fence）、测试和索引都要同步。
- 旧 `fence 0`/`fm` 用例失效；`fence` 归类从其它指令变为 cfx 指令。
- 不提供 `fence.vma`/`fence.i` 语义；TLB/icache 维护仍走 `cfx_ptw`/`cfx_cache` 操作。

## 状态说明

关键语义已确认：`cfx0`/`cfx_umon`=all、`pred=succ=0` no-op、`hb` SBZ、`fm` 删除。落地由 `INTEG-041t` 负责。
