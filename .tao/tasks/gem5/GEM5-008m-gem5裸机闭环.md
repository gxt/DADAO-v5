# GEM5-008m: gem5 裸机闭环

**模块**：gem5
**项目里程碑**：M8
**状态**：里程碑
**目标**：`AtomicSimpleCPU` 在完整 `Machine-01` 测试机中运行现有 DADAO ELF，并由独立向量和端到端程序证明结果正确。
**关联任务**：`GEM5-001k`、`GEM5-002t`、`GEM5-003t`、`GEM5-004t`、`GEM5-005t`、`GEM5-006t`、`GEM5-007t`

## 核验

- `ADR-0035`、`ADR-0036` 的 decision 已逐条确认且状态为 Accepted；关联 `GEM5-001k` 为 `已验证`，所有关联 `t` 任务均为 `已验证`。
- 组件锁、构建目标、补丁集、向量、脚本、能力矩阵与证据文件存在且引用可解析。
- `make check`、`make check-modules`、`make check-full`、`make check-gem5-full` 全绿；检查反例注入证据与真实退出码。
- 跨模块影响已处置；gem5 与 M7 并行实施，里程碑只按 gem5 自身交付及实际跨模块依赖验收，不以 M7 完成为形式前置。

## 2026-10-21 核验记录

- 前置 `GEM5-001k`–`007t` 状态、`ADR-0035`/`0036`、组件锁、40 份补丁、base+1 源码树及证据引用均已核对；迁移后的契约路径已修正。
- `make test-gem5` 与 `make check-gem5-full` 均退出 0；现场计数为 opcode 259/259、current 510、Machine-01 47、remaining 620、FP 329、程序集代表 9/9、完整 58/58。
- 六类 gem5 反例均观察到被检命令退出 1：ISA 序列、excluded 误接受、Machine 启动状态、FP 结果、程序集退出结果、程序集退出码丢失；补丁损坏反例观察到 `git apply` 退出 128。
- 用户授权必要的非 gem5 解阻后，仅补录 8 个纯 FileCheck LLVM 用例到既有 `no-value-entry` 类，并使 `.work` 引用门控对终态任务历史采用与归档任务一致的口径；活跃任务和知识页仍严格检查，正反自测通过。
- 最终 `make check`、`make check-modules`、`make check-full`、`make check-gem5-full` 均退出 0；L2 gem5 代表 9/9，L3 QEMU 351/351、M6 全绿、gem5 完整 58/58。稳定摘要见 `components/gem5/evidence/GEM5-008m.md`。
