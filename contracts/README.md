# contracts/ — 机器可读合约数据

从 `.tao/knowledge/contract-*.md` 与 ADR 派生的**机器可读合约数据**，供各模块工具与实现消费。

## 文件说明

| 文件 | 内容 | 来源 |
|------|------|------|
| `opcodes.yaml` | 每条指令的编码字段、mask、value、变体 | `contract-isa.md`（`SPEC-003t`） |
| `abi.yaml` | 参数寄存器编号、callee-saved 列表、DataLayout | `contract-abi.md`（`SPEC-004t`） |
| `legality_rules.yaml` | 非法编码组合、非对齐访问规则 | `contract-isa.md` 异常条款（`SPEC-008t`） |
| `fp_semantics.yaml` | FP（`scope: fp`，60 条）语义投影：FCSR 环境、12 族、`id→family→spec_cite→semantics_ref→legality_refs`（不含编码、不含期望值） | `contract-fp.md`（`SPEC-087t`） |

## 原则

- **独立于实现**（Independent oracle）：只从 `spec/` 与合约派生，不从 LLVM/QEMU 反推。
- `opcodes.yaml` 须自检：每条指令的 mask & value 唯一、同 mnemonic 的变体共享基名、无编码空间重叠（由 `tools/spec/validate_encoding.py`）。
- **工具脚本不放这里**：生成/校验脚本在 `tools/spec/`，各模块检查脚本在 `tools/<module>/`。
- 黄金模型（Python 独立 oracle）属 `golden` 模块（M2），不在此目录。
