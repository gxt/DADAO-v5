# ADR-0048: QEMU/gem5 同模式一致性与 M11 测试覆盖

**状态**：Accepted
**日期**：2026-11-02（恢复稿；内容按用户 2026-11-02 讨论重建）
**关联**：`GEM5-001k`、`GEM5-002t`、`GEM5-012t`、`G2`/`G3`；`docs/Process-09-测试组织规范.md`

## Context（背景）

M11 同时交付 gem5 FS 与 SE，但 QEMU 和 gem5 是两套独立实现。
如果跨模式比较（例如 gem5 FS 对 QEMU user），会把系统态与用户态的差异误判为
实现错误；如果只比较日志或通过数，也无法证明架构结果一致。
因此需要冻结“同模式配对”和测试覆盖的验收口径。

## Decision（决策）

- **D1 同模式配对**：gem5 FS 只对 QEMU system；gem5 SE 只对 QEMU user；
  不允许拿 gem5 FS 对 QEMU user，也不允许反过来。
- **D2 比较内容**：同一 case ID 比较通过/失败、退出码和架构可见结果
  （寄存器/内存/异常）；不比较时序、性能或主机日志格式。
- **D3 测试复用**：FS 复用 `tests/inst`/`tests/arch`；SE 复用 `tests/tset`
  （`libc-test`、`llvm-ts`、Embench）；工具链复用 `tests/unit`；
  不新建 `tests/gem5` 平行体系。
- **D4 M11 覆盖**：SE 最终覆盖完整 `tset`（静态先行，动态链接、TLS、线程/futex
  后补但不得降级）；FS 覆盖 `inst`/`arch` 与裸机 E2E；测试向量和期望值
  独立派生自当前 spec/contracts，不从 QEMU/gem5 实现反推。
- **D5 差异处置**：同模式结果不一致必须定位到 spec/实现/测试资产之一，
  保留真实现场；不得用跨模式结果或时序差异掩盖。

## Rationale（理由）

同模式比较才能把 QEMU 和 gem5 的差异归因到实现，而不是模式语义；
复用现有 test scope 避免平行测试树和重复 oracle；最终覆盖完整 tset
才能支撑 M11 的“FS + SE”声明。

## Consequences（影响）

- `TESTCASES` 的 gem5 段必须按 FS/SE 分开出结果矩阵；
- QEMU/gem5 不一致时先查 spec/contracts，再查各自实现；
- 动态链接、TLS、线程/futex 属于 M11 SE 最终补齐项，不能以静态通过代替；
- 测试资产和 oracle 仍由 testcases 任务维护，不在 gem5 实现任务内夹带。

## 状态说明

本文件是 ADR-0048 的恢复稿；当前仓库历史中未找到原始文件。
D1–D5 按用户 2026-11-02 的讨论与同意重建；用户 2026-11-02 已复核并确认
无误，状态置 `Accepted`。
