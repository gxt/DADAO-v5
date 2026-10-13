# ADR-0014: fence 移出 M1（对齐浮点的 excluded 处理）

**状态**：Accepted
**日期**：2026-09-29
**关联**：SPEC-039t、contract-isa.md §14.1、opcodes.yaml、ISS-056

## Context（背景）

`fence` 的处理与「浮点缺失」**不一致**：

| 层 | 浮点（正确） | fence（变更前） |
|----|-------------|--------------|
| `contract-isa.md` | `Excluded from M1` | §14.1 已标 `Excluded` ✓ |
| `opcodes.yaml` | `excluded_m1: true` | **无 `excluded_m1`**（计入 M1 178）❌ |
| QEMU | excluded → ILLI（合规） | ILLI 桩（对 M1 指令是缺陷，ISS-056） |

`contract-isa.md §14` 已把 fence 列为 `Excluded from M1`，但 `opcodes.yaml` 未标 `excluded_m1`，导致 fence 被当作 M1 指令（178 之一），QEMU ILLI 桩成为「M1 指令未实现」的缺陷。

**用户裁定（2026-09-29）**：按浮点方式补齐。

## Decision（决策）

- **D1**：`fence`（MISC-AMO ha=0x01）标 `excluded_m1: true`（与浮点 RF / 特权 cfx / LR-SC 同），M1 身份集 178 → 177。
  - 依据：`contract-isa.md §14.1` 既已 Excluded；本决策消除与 `opcodes.yaml` 的不一致。
- **D2**：QEMU `trans_fence` 的 ILLI 桩变为 excluded → ILLI **合规**，ISS-056 关闭。
- **D3**：LLVM lit 的 fence 保留（编码正确性，与 M1 运行语义不冲突）——同浮点指令 LLVM 侧亦可汇编。

## Rationale（理由）

1. **一致性**：消除 `contract-isa.md`（已 Excluded）与 `opcodes.yaml`（未标 excluded_m1）之间的不一致。
2. **与浮点对齐**：浮点指令已在 opcodes.yaml 中标 `excluded_m1: true`，fence 应采用相同处理方式。
3. **ISS-056 自然关闭**：fence 为 excluded 后，QEMU ILLI 桩成为正确行为（excluded 指令应 ILLI），不再是缺陷。

## Consequences（影响）

- **正面**：M1 身份集与 `contract-isa.md §14` 完全一致；ISS-056 可关闭；QEMU fence ILLI 桩不再被视为缺陷。
- **负面**：M1 计数从178 降为177，需连锁更新各 checker/文档中的计数断言。
- **后续约束**：fence 的完整运行语义实现（nop 或 ILLI 根据 immu18 bits[17:4]）推迟到 M2 或后续任务。

## 状态说明

- **Accepted（2026-09-29）**：用户逐条确认 D1/D2/D3 **全部保留**。
- **确认记录**：2026-09-29 主会话向用户呈现 D1–D3，用户判定全部保留后置 `Accepted`。
