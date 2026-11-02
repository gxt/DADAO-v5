# ADR-0047: gem5 版本与组件基线

**状态**：Accepted
**日期**：2026-11-02（恢复稿；决策事实 2026-11-01 已由用户确认）
**关联**：`GEM5-003t`、`GEM5-001k`、ADR-0005；`manifests/components.lock.toml`

## Context（背景）

M11 需要一个独立的 gem5 第二参考实现，覆盖 FS + SE，并与 QEMU 对应模式比较。
上游 gem5 的 tag/branch 不能单独作为可复现基线，组件锁必须固定到完整 commit；
同时要明确 M11 使用的 CPU 模型和性能边界。

## Decision（决策）

- **D1 上游仓库**：gem5 固定为 `https://github.com/gem5/gem5.git`。
- **D2 版本基线**：使用 `v25.1.0.1` 作为版本标识。
- **D3 commit 锁定**：组件锁固定到完整 commit `c8222cc67a399bfc01e8658dd14b30d5bfd634f9`；tag 只作下载/对照标识，不作为可复现基线；tarball 只作校验物。
- **D4 M11 角色**：gem5 作为 M11 第二参考，覆盖 FS + SE，使用 `AtomicSimpleCPU`；时序/性能不在 M11 范围内。

## Rationale（理由）

- 完整 commit 可复现，避免 tag 漂移或浅引用失效；
- FS + SE 同一 ISA 核心、两种系统模式，符合 M11 目标；
- `AtomicSimpleCPU` 足以做功能对照，性能/时序不是 M11 验收项；
- 与现有 `manifests/components.lock.toml` 和 `GEM5-003t` 记录一致。

## Consequences（影响）

- 组件下载/校验以锁文件中的完整 commit 为准；
- 升级 gem5 必须更新 ADR/组件锁，并重跑对应门控；
- FS/SE 的模式差异在任务书中分开验收，不互相冒充；
- 性能/时序工作延后，不在 M11 内推进。

## 状态说明

本文件是 ADR-0047 的恢复稿；当前仓库历史中未找到原始文件。
四条 decision 已按 `GEM5-003t` 与 `manifests/components.lock.toml` 重建；
用户 2026-11-02 已逐条确认 D1–D4，状态置 `Accepted`。
