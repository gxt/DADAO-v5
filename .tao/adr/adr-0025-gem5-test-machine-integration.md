# ADR-0025: gem5 测试机接入边界

**状态**：Accepted
**日期**：2026-10-12
**关联**：`GEM5-001k`、`GEM5-003t`–`GEM5-007t`、`ADR-0004`、`ADR-0020`、`spec/Machine-01`

## Context（背景）

v5 已通过 QEMU、boot ROM、LLVM ELF 和 semihosting 形成裸机运行链路。gem5 首版要成为同一规范下的第二执行实现；如果另造地址图、启动路径或服务协议，现有程序和独立向量无法直接复用。现阶段没有内核、MMU 或周期精度验收要求。

## Decision（决策）

- **D1**：首版使用 gem5 全系统配置中的 `AtomicSimpleCPU`、单核、裸机运行；不采用 syscall emulation 模式。
- **D2**：以现行 `spec/Machine-01` 为测试机接口真源，沿用 ROM 复位、ELF `PT_LOAD`、RAM、运行模式、异常与退出协议；gem5 不产生另一套机器规范。
- **D3**：以 DADAO 适配层对接 gem5 semihosting 机制，实现 `Machine-01 §5` 的完整 25 服务及 guest 退出码传播；适配层不改变 guest ABI 或服务号。
- **D4**：正确性门槛以从 `spec/` 和合约独立派生的向量为准；QEMU 差分只用于定位分歧，不能生成期望值。

## Rationale（理由）

全系统裸机路径能复用 boot ROM 和现有应用，`AtomicSimpleCPU` 足以建立功能正确性闭环。共享 `Machine-01` 能防止两台测试机协议漂移。gem5 已有 semihosting 基础机制，可由 DADAO 层适配其调用约定。对比方案：直载 ELF 而跳过 ROM/运行模式会减小早期工作量，但不能满足本阶段的完整测试机目标；SE 模式会引入另一套 syscall 语义。

## Consequences（影响）

需要新增 DADAO ISA、系统对象、启动与测试配置；首版性能统计仅作调试数据，不作为性能结论。`Machine-01` 的版本变化须检查 QEMU/gem5 两实现及共享测试。gem5 平台能力矩阵只凭实测填列。

## 状态说明

用户于 2026-10-12 逐条回复「接受 D1」「接受 D2」「接受 D3」「接受 D4」，故本 ADR 置为 Accepted。gem5 实现按用户后续裁定与 M7 并行实施。
