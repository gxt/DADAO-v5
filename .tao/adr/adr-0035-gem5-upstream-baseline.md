# ADR-0035: gem5 上游基线

**状态**：Accepted
**日期**：2026-10-12
**关联**：`GEM5-001k`、`GEM5-002t`、`ADR-0002`、`manifests/components.lock.toml`

## Context（背景）

gem5 已在组件锁中预留，但 `enabled = false`、`commit = ""`，`make build-gem5` 仍是拒绝成功的占位目标。新增 ISA 需与 gem5 上游源码和 SCons 构建接口绑定；仓库要求组件使用完整 commit 锁定，并由树形补丁集保存定制源码。

## Decision（决策）

- **D1**：上游仓库使用 `https://github.com/gem5/gem5.git`。
- **D2**：首版基线使用官方 release tag `v25.1.0.1` 所指向的完整 commit `c8222cc67a399bfc01e8658dd14b30d5bfd634f9`；manifest 只以完整 commit 作复现依据。
- **D3**：`shallow_ref = "v25.1.0.1"`；启用组件前核实 tag、commit、浅取行为与补丁可应用性，未通过则保持 disabled。

## Rationale（理由）

官方发布记录将 `v25.1.0.1` 标为发布版；官方仓库的该提交包含版本号更新。用固定发布版和完整 SHA 可避免 `stable` 分支继续移动。既有 LLVM/QEMU/picolibc 组件也使用精确 commit 与补丁集。对比方案：追踪 `stable` 分支会造成输入漂移；取旧 DADAO fork 会引入与当前 gem5 API 不同的历史实现，不作为执行基线。

## Consequences（影响）

`GEM5-002t` 更新组件锁、组件说明、基础补丁集并验证上游构建环境；`GEM5-003t` 随 ISA 骨架落地 DADAO 构建目标。后续上游升级需要重新验证所有补丁与运行门控。国外大仓库下载仍按项目镜像选择规则执行。

## 状态说明

用户于 2026-10-12 逐条回复「接受 D1」「接受 D2」「接受 D3」，故本 ADR 置为 Accepted。启用组件仍须在 `GEM5-002t` 按 D3 核实 tag、完整提交与补丁可应用性，；用户另行授权 gem5 与 M7 并行实施。

## 核实来源

- 官方发布记录：<https://github.com/gem5/gem5/releases/tag/v25.1.0.1>
- 官方提交：<https://github.com/gem5/gem5/commit/c8222cc67a399bfc01e8658dd14b30d5bfd634f9>
