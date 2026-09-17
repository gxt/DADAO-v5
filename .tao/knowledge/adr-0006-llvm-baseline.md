# ADR-0006: LLVM 组件基线选版

**状态**：Candidate
**日期**：2026-09-17
**关联**：`LLVM-002t`（LLVM 组件基线任务）

## Context（背景）

v5 的 LLVM MC 开发需要选定一个可复现的上游 LLVM commit 作为基线。该基线须满足：

- **MC 框架**：提供 `MCTargetDesc`、`MCCodeEmitter`、`MCObjectWriter`、`MCAsmBackend`、`ELFObjectWriter` 等核心基础设施，用于汇编和输出 DADAO 目标的 ELF 可重定位对象。
- **TableGen**：基于 `.td` 的指令定义、寄存器信息和 MC 级代码生成表文件。
- **lit**：LLVM 集成测试运行器，用于 MC 和汇编测试。

DADAO 是全新目标（`ADR-0001`），不复用旧版工具链代码。所有 M1 补丁均应用于此干净上游 commit。

### 选版约束

1. **可复现性**：commit 必须为完整 40 字符 SHA，不接受 tag/branch/短 SHA。
2. **稳定性**：优先选择 release 分支的稳定版本，避免 main 分支的 API 颠簸。
3. **MC 框架可用性**：确认所选 commit 已包含稳定的 MC 层 API。
4. **构建验证**：在 `make doctor` 环境内能 `cmake -DLLVM_TARGETS_TO_BUILD=...` 无错完成 configure。
5. **与 0628 的关系**：v5 须独立决定版本，不得直接照搬 0628 的 `llvmorg-22.1.8`；若沿用须重新验证并写明理由。

## Decision（决策）

**待用户逐条确认**。以下为候选方案，尚未选定：

### 候选 A：LLVM 23.1.1（最新稳定版）

| 字段 | 值 |
|------|-----|
| LLVM 版本 | 23.1.1 |
| Commit SHA | `6dfe1677ab8dffbc6ec13d53a1e0215d75147689` |
| Tag | `llvmorg-23.1.1` |
| 发布日期 | 2026-09-08 |

### 候选 B：LLVM 22.1.8（DADAO-0628 使用版本）

| 字段 | 值 |
|------|-----|
| LLVM 版本 | 22.1.8 |
| Commit SHA | `ca7933e47d3a3451d81e72ac174dcb5aa28b59d1` |
| Tag | `llvmorg-22.1.8` |
| 发布日期 | 2026-06-16 |

## Rationale（理由）

### 候选 A：LLVM 23.1.1

1. **稳定性**：23.x 是当前主线大版本，23.1.1 是该系列首个补丁版本（2026-09-08），包含自 23.1.0（2026-08-25）以来的所有 bugfix。作为最新的正式发布版，经过完整的发布测试流程。

2. **MC 框架可用性**：LLVM 23.x 继承了 22.x 的稳定 MC 层 API。自 LLVM 15–17 以来，MC 框架（`MCTargetDesc`、`MCCodeEmitter`、`MCELFObjectTargetWriter`、`ELFObjectWriter`）接口保持稳定，23.x 无破坏性变更。

3. **构建验证**：该 commit 是 `llvm-project` 仓库中的官方发布 commit，可通过 `git ls-remote` 验证可达性。

4. **前瞻性**：选择最新稳定版可获得更长的支持窗口和更多上游 bugfix，减少后续 cherry-pick 需求。

5. **取舍**：较新版本可能有未发现的回归问题；但作为正式发布版，风险可控。

### 候选 B：LLVM 22.1.8

1. **稳定性**：22.1.x 是成熟的 LTS 系列，22.1.8（2026-06-16）是该系列最新补丁版本，包含累积的 bugfix。DADAO-0628 已基于此版本完成 MC 框架开发，验证了其稳定性。

2. **MC 框架可用性**：与候选 A 相同，LLVM 22.x 的 MC 层 API 稳定。0628 的实践证明该版本的 MC 框架可正常工作。

3. **构建验证**：该 commit 已在 0628 中通过验证（`git ls-remote` 确认可达）。v5 可复用此验证经验。

4. **兼容性**：与 0628 使用相同版本，便于对比和参考 0628 的补丁实现。

5. **取舍**：版本较旧（3 个月前），可能缺少 23.x 的改进；但 MC 框架差异极小，不影响 M1 目标。

## Consequences（影响）

1. M1 所有补丁（MC 框架、ELF 输出器、TableGen 定义、lit 测试）均针对此 commit 开发。
2. M1 期间 commit 不 bump。若发现严重 MC 框架 bug，通过 cherry-pick 处理并记录新 ADR，不整体 bump。
3. `llvm` 组件在 `manifests/components.lock.toml` 中标记 `enabled = true`，并填入完整 40 字符 commit SHA。
4. `Makefile` 的 `build-mc` 目标使用此 commit 进行真实 `cmake` + `ninja` 构建。

## 状态说明

- **Candidate**：本文档为候选方案，待用户逐条确认 decision 后升为 Accepted。
- **确认流程**：用户对每个候选方案逐条判定（保留/修改/否决），确认后写入最终 Decision 并标注 `Accepted`。

---

**内容溯源**：DADAO-0628 `docs/adr/0005-llvm-baseline.md`（使用 LLVM 22.1.8，commit `ca7933e47d3a3451d81e72ac174dcb5aa28b59d1`）。v5 须独立验证 commit 可达性，不得直接照搬。
