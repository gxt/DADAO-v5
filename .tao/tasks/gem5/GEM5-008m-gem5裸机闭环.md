# GEM5-008m: gem5 裸机闭环

**模块**：gem5
**项目里程碑**：M8
**状态**：待开始
**目标**：`AtomicSimpleCPU` 在完整 `Machine-01` 测试机中运行现有 DADAO ELF，并由独立向量和端到端程序证明结果正确。
**关联任务**：`GEM5-001k`、`GEM5-002t`、`GEM5-003t`、`GEM5-004t`、`GEM5-005t`、`GEM5-006t`、`GEM5-007t`

## 核验

- `ADR-0024`、`ADR-0025` 的 decision 已逐条确认且状态为 Accepted；关联 `GEM5-001k` 为 `已验证`，所有关联 `t` 任务均为 `已验证`。
- 组件锁、构建目标、补丁集、向量、脚本、能力矩阵与证据文件存在且引用可解析。
- `make check`、`make check-modules`、`make check-full`、`make check-gem5-full` 全绿；检查反例注入证据与真实退出码。
- 跨模块影响已处置；gem5 与 M7 并行实施，里程碑只按 gem5 自身交付及实际跨模块依赖验收，不以 M7 完成为形式前置。
