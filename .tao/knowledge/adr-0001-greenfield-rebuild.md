# ADR-0001: Greenfield 重建

**状态**：Candidate
**日期**：2026-09-12
**关联**：ADR-0002（构建编排）；`README.md`（规范版本表，SimRISC 0.5.3）；`AGENTS.md`（核心原则）；任务 `INFRA-008t`

## Context（背景）

DADAO 的历史实现（`DADAO` 参考仓库的各阶段代码）建立在更早的 ISA、ABI、异常与 MMU 设计之上；其工作树也不是干净、可复现的基线。DADAO-v5 以 SimRISC 0.5.3 规范为唯一权威来源，需要一套来源可追溯、可复现的实现路径，避免把历史假设带入新规范。

## Decision（决策）

- **D1**：DADAO-v5 从干净的上游组件 commit 出发实现，**不回植（cherry-pick）历史实现代码**。
- **D2**：只复用历史 meta-repository 的**编排概念**与已文档化的**工程教训**；参考仓库经 `manifests/references.lock.toml` 以 `reference-only` 策略按精确 commit 锁定，仅作只读溯源。
- **D3**：行为期望一律来自 `spec/` 与 `.tao/knowledge/contract-*.md`（0.5.3），不从任何实现反推。

## Rationale（理由）

- 历史实现携带旧 ISA/ABI 假设，直接复用会把过时语义与不可追溯的来源带进 v5。
- 干净基线 + 精确上游 commit + 有序补丁序列，使每个行为都能回溯到规范合约，满足 Spec-first 与 Component lock 原则。
- 参考仓库已停止更新且规范版本不同（0.4.1），只能提供工程经验，不能作为实现来源。

## Consequences（影响）

- 不回植历史实现；历史测试须按独立期望重写，不能直接搬用。
- 初期进度可能较慢，但每个行为都有可追溯的合约依据。
- 与开发期历史对象的兼容性**不是目标**。
- 参考仓库（`DADAO`、`DADAO-0628`）仅作只读溯源，不得作为任务的执行依赖。

## 状态说明

Candidate：待评审。评审通过后由主会话置 `Accepted`；决策变更时新增 ADR 或标注 `Superseded`，不直接改写已 `Accepted` 的决策。
