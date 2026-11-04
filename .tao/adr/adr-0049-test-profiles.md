# ADR-0049: 测试运行环境分层（Tiny / Node / SE）

**状态**：Accepted
**日期**：2026-11-04
**接受日期**：2026-11-04
**关联**：ADR-0004（测试机几何）、ADR-0043（Node 启动/页表）、ADR-0048（QEMU/gem5 一致性）、`spec/Machine-v5-测试机运行环境.md`、`spec/DADAO-12`；任务线索 `QEMU-079t`/`QEMU-080t`、`GEM5-014t`/`GEM5-016t`、`TESTCASES-091t`/`TESTCASES-092t`

## Context（背景）

现有规范已给出 `Machine-v5-Tiny` / `Machine-v5-Node` 两套 FS 几何，也已存在 QEMU user / gem5 SE 路径；但“哪种测试跑在哪个运行环境”长期混用：

- Tiny 被误当作可跑 cfx / 需要 system call 的平台；
- Node 被误当作普通 `inst`/`embench`/`picolibc` 测试平台；
- SE 的地址模型与 semihosting 边界没有与 FS 两 profile 分开；
- ADR-0043 的 Node 启动/页表路径被误套到 Tiny 或 SE。

M11 需要把三类运行环境固定为**互斥的测试归属**，避免同一用例在不同引擎上使用不同假设。精确地址、PTE 位域、页表步进和 semihosting 编号仍以 `spec/`、`contract-*` 与 ADR-0043/0040 为准；本 ADR 只固定**归属与运行模式**，不承载规范正文。

## Decision（决策）

- **D1 — Tiny：无 system call 的普通测试环境**
  - 只承担不需要 system call 的测试：`inst` + `embench` + `picolibc`。
  - 不实现任何 cfx，包括 `cfx_power`；不建页表，PTW 关闭。
  - 不跑 `arch`（cfx / 异常 / 页表类）测试。
  - 唯一允许的 cfx 类行为是 `trap` 触发的 semihosting；不进入 user 模式。
  - 地址几何与装载细节以 `spec/Machine-v5` 的 Tiny profile 为准。

- **D2 — Node：cfx 测试环境**
  - 专门承担 cfx 测试；启动一律从 `cfx_power` 开始，初始运行模式为 **hypv**。
  - 支持两种测试深度，由测试本身决定：
    - 浅层：`cfx_power → hmon → 测试本体`，停在 hypv；
    - 深层：`cfx_power → hmon → smon → …`，进入 supv / user。
  - 三种模式都必须覆盖：`hypv`、`supv`、`user`。
  - Node 的 Linux/smon 启动链（`power → hmon → smon → cfx_pmem → PTW`）以 ADR-0043 为准；本 ADR 不重复其页表/PTW 细节。
  - Node 不作为普通无 syscall `inst`/`embench`/`picolibc` 测试平台。

- **D3 — SE：需要 system call 的测试环境**
  - 承担需要 system call 的测试，默认运行在 **user mode**。
  - 地址模型：`VA = PA`，从 0 开始，容量 2 GiB。
  - 只允许 `trap` semihosting；不允许其它 cfx。
  - 使用 QEMU user / gem5 SE 路径；不复用 Tiny/Node 的 FS 启动链。

- **D4 — 测试归属矩阵**
  - 无 system call、无 cfx ⇒ Tiny。
  - 测 cfx（含异常、页表、hypv/supv/user）⇒ Node。
  - 需要 system call ⇒ SE。
  - 同一测试不得因引擎不同而改写其所属运行环境；跨引擎一致性比较只在同一运行环境内进行。

- **D5 — 与既有 ADR 的边界**
  - ADR-0004 继续承载测试机基础几何/加载/退出协议；本 ADR 只补充测试运行环境归属。
  - ADR-0043 的 D10/D11/D12 只属于 **Node 的 Linux/smon 启动链**，不是 Tiny 测试页表，也不是 SE 地址模型。
  - ADR-0048 的 QEMU/gem5 一致性判据按本 ADR 的同一运行环境配对；Tiny 对 Tiny、Node 对 Node、SE 对 SE，不跨环境配对。

## Rationale（理由）

- **按能力选环境，而不是按引擎选环境**：Tiny 无 cfx、无 PTW，适合纯 ISA / 编译器 / picolibc；Node 才具备 cfx、PTW 和 hmon/smon 路径；SE 才具备 system call 语义。
- **避免“Node 跑普通测试”造成假覆盖**：Node 的启动链、页表与 cfx 权限会引入 Tiny/SE 没有的变量；把无 syscall 测试放到 Node，既增加成本，也掩盖 Tiny 的真实约束。
- **避免“Tiny 跑 cfx”造成规范冲突**：Tiny 明确无 cfx_power 且不能进 user，cfx 测试必须去 Node。
- **SE 独立地址模型**：SE 的 `VA=PA [0, 2 GiB)` 与 Node 的 PTW 映射不是同一语义；把二者混用会让 ELF/栈/指针测试产生错误期望。
- **保留 Node 的双深度**：cfx 测试有浅有深；浅层只验证 hypv 可见行为，深层才需要 smon/supv/user，不能强制所有 cfx 测试都走完整启动链。

## Consequences（影响）

- **Tiny**：测试资产不得引入 cfx 寄存器、PTW 或 user 模式；`trap` 仅用于 semihosting；`inst` / `embench` / `picolibc` 的期望值以 Tiny 几何为准。
- **Node**：测试需显式声明目标模式（hypv/supv/user）与启动深度；浅层与深层分别建资产，不得用一个“Node 通用”镜像覆盖全部模式。
- **SE**：测试默认 user mode、`VA=PA [0, 2 GiB)`；只允许 trap semihosting；不得引用 Node 的页表/PTW 或 Tiny 的 BootROM 启动路径。
- **QEMU/gem5**：同一环境内做一致性比较；Tiny、Node、SE 的引擎差异分别归因，不把跨环境差异写成 parity 失败。
- **规范侧**：Tiny/Node 的几何与 Node 页表细节仍归 `spec/Machine-v5` 与 ADR-0043；本 ADR 不替代这些正文。
- **任务侧**：现有把 Node 当普通测试平台、或把 SE 当 FS 路径的任务，需按本 ADR 重新划范围；不得直接把旧结果写成新环境 PASS。

## 状态说明

**Accepted**（2026-11-04）：用户审阅后确认本 ADR，D1–D5 全部生效。

- **用户原话**：「adr-0049已审阅，accepted」。
- 生效后，Tiny / Node / SE 的测试归属按 D1–D5 执行；具体地址几何、PTE 位域与 semihosting 编号仍以 `spec/`、`contract-*`、ADR-0004/0043/0048 为准。
- 决策变更按 `Process-03` 处理：新增 ADR 或标 `Superseded`，不直接改写已 `Accepted` 的 decision。
