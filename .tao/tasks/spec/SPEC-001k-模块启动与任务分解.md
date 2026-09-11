# SPEC-001k: spec 模块启动

**模块**：spec
**依赖**：无
**状态**：已验证

## 问题根源

Agent 不能直接读 `spec/` 的 11 份原始规范（面向人类、存在歧义）。需要把规范归一化投影成精确的合约与机器可读数据，作为所有下游实现（LLVM/QEMU/golden/gem5/Sail）的单一事实来源。

## 阶段目的

从 `spec/`（SimRISC 0.5.3）提取：ISA 规范化合约（`.tao/knowledge/contract-isa.md`）、机器可读编码表（`verif/opcodes.yaml`），为后续 ABI/ELF 合约与 M1 实现提供 oracle。

## 对照关系

- **借鉴**：DADAO-0628 的规范归一（DL-001a ISA 合约、DL-001c 编码验证器）。
- **差异**：v5 基于 SimRISC 0.5.3（0628 为 0.4.1），指令命名（`.b/.w/.t/.o` 后缀）、QFC 编码表、格式体系均变化，须按 0.5.3 重写，不照抄 0.4.1 数据。

## 任务分解

| 编号 | 任务 | 交付物 | 依赖 |
|------|------|--------|------|
| `SPEC-002t` | ISA 规范合约提取 | `.tao/knowledge/contract-isa.md` | 无 |
| `SPEC-003t` | 机器可读编码表 | `verif/opcodes.yaml`、`verif/validate_encoding.py` | `SPEC-002t` |

- **依赖关系**：`002t → 003t`。
- **分解理由**：先归一化语义合约（002t），再从中派生机器可读编码表（003t）。
- **迁出说明**：合法性规则（原 `SPEC-004t`）已迁至 `verif` 模块（`VERIF-002t`）——它是验证链工作（DADAO-0628 DL-043a M3），非规范归一。

## 说明

- Spec-first：期望值来自 `spec/`，不从实现反推。
- 本模块 M1 阶段另有 ABI/ELF/ADR/冻结任务：`SPEC-006t`~`SPEC-010t`（`**阶段**：4`）。
- 参考 `.work/DADAO-0628/code-agent/tasks/DL-001a-isa-contract.md`、`DL-001c-encoding-validator.md`。
