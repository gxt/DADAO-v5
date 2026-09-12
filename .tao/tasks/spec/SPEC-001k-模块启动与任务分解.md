# SPEC-001k: spec 模块启动

**模块**：spec
**项目里程碑**：M1
**依赖**：无
**状态**：待开始

## 问题根源

Agent 不能直接读 `spec/` 的 11 份原始规范（面向人类、存在歧义）。需要把规范归一化投影成精确的合约与机器可读数据，作为所有下游实现（LLVM/QEMU/golden/gem5/Sail）的单一事实来源。

## 目的

从 `spec/`（SimRISC 0.5.3）提取归一化产物：ISA 合约与编码表（M1 实现 oracle）、ABI 合约、Object ABI / Test Machine ADR、ELF 合约，并完成规格冻结，为 M1 及后续 CodeGen 提供冻结的规格基线。

## 对照关系

- **借鉴**：DADAO-0628 的规范归一（`DL-001a` ISA 合约、`DL-001c` 编码验证器、`DL-002a` ABI、`DL-003a/b` ADR、`DL-004a/b` ELF 合约与冻结）。
- **差异**：v5 基于 SimRISC 0.5.3（0628 为 0.4.1），指令命名（`.b/.w/.t/.o` 后缀）、QFC 编码表、格式体系均变化，须按 0.5.3 重写，不照抄 0.4.1 数据。

## 任务分解

| 编号 | 任务 | 交付物 | 依赖 |
|------|------|--------|------|
| `SPEC-002t` | ISA 规范合约提取 | `.tao/knowledge/contract-isa.md` | 无 |
| `SPEC-003t` | 机器可读编码表 | `verif/opcodes.yaml`、`verif/validate_encoding.py` | `SPEC-002t` |
| `SPEC-004t` | ABI 合约（非变参标量） | `.tao/knowledge/contract-abi.md`、`verif/abi.yaml` | `SPEC-002t` |
| `SPEC-005t` | Object ABI ADR | `.tao/knowledge/adr-0003-object-abi.md` | `SPEC-002t`、`SPEC-004t` |
| `SPEC-006t` | Test Machine ADR | `.tao/knowledge/adr-0004-test-machine.md` | `SPEC-002t`、`SPEC-004t`、`VERIF-002t` |
| `SPEC-007t` | ELF 合约 | `.tao/knowledge/contract-elf.md` | `SPEC-005t`、`SPEC-002t` |
| `SPEC-008t` | Spec 冻结 | `docs/impact-matrix.md`、`scripts/check_spec_drift.py` | `SPEC-004t`~`SPEC-007t` |
| `SPEC-009m` | M1 spec 里程碑 | 里程碑标记 | `SPEC-002t`~`SPEC-008t` |

- **依赖关系**：`002t → 003t`；`002t → 004t → {005t → 007t, 006t} → 008t`；`009m` 汇总全部。
- **分解理由**：先归一化语义合约（`002t`）与编码表（`003t`）；再在其上定义 ABI（`004t`）→ Object ABI ADR（`005t`）/ Test Machine ADR（`006t`）→ ELF 合约（`007t`）→ 冻结（`008t`）。每个任务可独立验收。
- **k↔m**：本模块一个规划 `k`（`001k`）对应一个里程碑 `m`（`009m`）。

## 说明

- Spec-first：期望值来自 `spec/`，不从实现反推。
- `SPEC-002t`/`003t` 的产出（`contract-isa.md`/`opcodes.yaml`）在本次重排后需**重新生成**；旧文件暂作参考（见 `.tao/knowledge/deferred.md`）。
- 暂缓 / 多出的内容（如 ABI 的 M2/CodeGen 部分与 `[OPEN]` 项、`EM_DADAO` 注册状态、LLD scope 等）记入 `.tao/knowledge/deferred.md`，避免遗忘。
- 参考 `.work/DADAO-0628/code-agent/tasks/DL-001a-isa-contract.md`、`DL-001c-encoding-validator.md`。
