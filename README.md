# DADAO for SimRISC 0.5.4

基于 `spec/` 目录下的 19 份上游规范文档（SimRISC-00~12 + DADAO-11~23）与 v5 自定规范（`Toolchain-01`、`Process-0x`，索引见 `spec/README.md`），实现 LLVM 编译器、QEMU 模拟器、Chipyard 仿真器和 Linux 内核的全栈支持。

## 当前版本号

| 组件 | 版本 |
|------|------|
| SimRISC | 0.5.4 |
| AEE / ABI | 0.9.2 |
| SEE / SBI | 0.7.1 |
| HEE / HBI | 0.1.2 |
| Toolchain | 1.1 |

版本号取自 `spec/` 各文档头部的 `> **版本：X.Y.Z**`。同步要求：AEE ↔ ABI、SEE ↔ SBI、HEE ↔ HBI 必须一致，全部基于同一 SimRISC 版本号。

## 项目里程碑

**M1 — MC + QEMU 标量核心 + MC↔QEMU 集成**（已达成，2026-09-22）

`llvm-mc` 能汇编/反汇编全部 M1 指令；`qemu-system-dadao` 能在 MMU-off 裸机模式执行标量程序；独立测试向量经「MC 汇编 → QEMU 执行 → 结果比对」一致，形成 MC↔QEMU 集成闭环。

**M2 — 规范与接口冻结（Normative Freeze）**（已达成，2026-10-04）

`spec/`（0.5.4）→ 投影（`contracts/*`、`contract-*.md`）→ checker 三层机械一致；浮点实现侧收口并冻结接口；偏离台账成型，为后续 CodeGen 提供稳定契约。

**M3 — Basic CodeGen（纯整数）**（进行中）

`llc` 将标量整数/指针函数（LLVM IR）编译为 DADAO 汇编，经 MC → 单 TU obj/raw binary → `qemu-system-dadao` 执行结果正确（freestanding、单 TU 自包含、无链接器）。
