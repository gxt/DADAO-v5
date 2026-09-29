# SPEC-039t: fence 移出 M1（对齐浮点的 excluded 处理）

**模块**：spec
**项目里程碑**：M1→M2
**依赖**：无
**状态**：待开始

## 问题描述

`fence` 的处理与「浮点缺失」**不一致**：

| 层 | 浮点（正确） | fence（当前） |
|----|-------------|--------------|
| `contract-isa.md` | `Excluded from M1` | **§14.1 也标 Excluded** ✓ |
| `opcodes.yaml` | `excluded_m1: true` | **无 `excluded_m1`**（计入 M1 178）❌ |
| deferred / issues | ✓ / `blocks: []` | ✓ / `ISS-056 blocks: []` ✓ |
| `assembly-list.md` | 浮点章 deferred | 待定章 deferred ✓ |
| QEMU | excluded → ILLI（**正确**） | ILLI 桩（对 M1 指令是**缺陷**，故成 ISS-056） |

即 **`contract-isa.md §14` 已把 fence 列为 `Excluded from M1`，但 `opcodes.yaml` 未标 `excluded_m1`** → fence 被当作 M1 指令（178 之一）→ QEMU ILLI 桩成为「M1 指令未实现」的缺陷。补齐后与浮点完全一致。

**用户裁定（2026-09-29）**：按浮点方式补齐。

## 修改内容

### 1. `contracts/opcodes.yaml`（经生成器）

`tools/spec/generate_opcodes.py`：`fence` 记录加 **`excluded_m1: true`**（与浮点同），重生成。

### 2. 连锁处置（M1 计数 178 → 177）

- `tools/spec/check_qfc_coverage.py`、`tools/qemu/check_qemu_trans.py`、`tools/integ/check_interface_alignment.py`、`tools/testcases/validate_vectors.py` 等对 M1 计数的**断言/常量**（如 `EXPECTED_M1 = 178`）
- `tests/vectors/inventory.md`：fence 行的 M1 口径 → excluded
- `.tao/knowledge/contract-isa.md`：M1 汇总/附录 A 的 fence 条目口径对齐（§14 已 Excluded，检查附录）
- `docs/assembly-list.md`：待定章 fence 标注「Excluded from M1」
- `docs/issues.yaml`：`ISS-056` 的判据更新（fence 现为 excluded → ILLI 合规，可关闭或改述）

### 3. 不改动

- **LLVM lit**：`fence` 的 lit 可保留（LLVM 能**正确汇编/编码** fence，属编码正确性，与「M1 是否实现运行语义」不冲突）——同浮点指令 LLVM 侧亦可汇编
- QEMU `trans_fence` 的 ILLI 桩：变为 excluded → ILLI **合规**

### 4. ADR

按 `AGENTS.md`，涉及 M1 范围的调整 → 立 **`ADR-0014`**（fence 移出 M1）：
- D1：fence 归 `Excluded from M1`（与浮点/特权 cfx/LR-SC 同），M1 身份集 178 → 177
- 依据：`contract-isa.md §14` 既已 Excluded；本 ADR 消除与 `opcodes.yaml` 的不一致
- **决策须逐条与用户确认后方可 `Accepted`**

## 约束

- 只改 `excluded_m1` 及连锁**计数/口径**；不改指令语义/编码
- 逐条核对，禁止正则批量替换
- 完成后 `make check` EXIT=0；各 checker 全绿

## 验收标准

1. `contracts/opcodes.yaml`：`fence` 含 `excluded_m1: true`；M1 计数 = **177**
2. `check_qfc_coverage` / `check_qemu_trans` / `check_interface_alignment` / `validate_vectors` 全绿（M1 177/177）
3. `inventory.md`/`contract-isa.md`/`assembly-list.md`/`issues.yaml` 口径一致
4. `ADR-0014` 创建（`Candidate` → 用户逐条确认 → `Accepted`）
5. `make check` EXIT=0
6. 反例验证

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）