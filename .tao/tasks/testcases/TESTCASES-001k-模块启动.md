# TESTCASES-001k: testcases 模块启动

**模块**：testcases
**项目里程碑**：M1
**依赖**：无
**状态**：待开始

## 问题根源

DADAO-v5 的 TDD 合约要求：在任何 LLVM/QEMU 实现字节被写入之前，M1 scope 内每条指令必须已有独立测试向量，且向量期望值必须**手工派生自 `spec/` 与 `.tao/knowledge/contract-isa.md`**，不得从 LLVM 汇编输出或 QEMU 运行结果反推——否则测试只是实现的自证，无法捕获实现自身的错误。

当前仓库已有 `contracts/opcodes.yaml`（SPEC-003t，256 条记录）作为机器可读编码 oracle，但**没有任何测试向量数据、schema、覆盖矩阵或向量校验器**，后续 llvm/qemu/gem5 模块没有独立 oracle 可比对。DADAO-0628 的 DL-001d 正是为此建立 `tests/vectors/` 与 `validate_vectors.py`，并在随后 DL-017a/017b/020a/022c/027a/028a/034a 中反复修复覆盖率与数据缺陷；这些缺陷与结论是本模块的直接经验来源。

## 目的

建立 testcases 的独立向量层：

- 产出 `tests/vectors/schema.md`、`inventory.md`、`README.md`、`isa/*.yaml`（5 类向量：encoding / legality / semantic / boundary / overlap）与 `tools/testcases/validate_vectors.py`；
- 把向量校验接入 `make check` 作为门控；
- 使 M1 scope 内每条指令身份（`insn`）都有 ≥1 条 active 向量，期望值全部可回溯到合约/spec；
- 使向量层可作为 LLVM/QEMU/gem5 的独立 oracle，并作为后续差分验证的输入。

## 对照关系

- **借鉴**：DADAO-0628 的向量工作流——DL-001d 建 schema/inventory/data/validator；DL-017a/017b 修覆盖率身份与唯一性；DL-020a 补 encoding class；DL-022c 内存地址 ROM→RAM；DL-027a/028a/034a 修数据与 control-flow/load 的 deferred 重设计；以及 `0002-detailed-roadmap.md` 的 TDD Contract / Vector Taxonomy / Ordering Rule。
- **差异**：v5 基于 SimRISC 0.5.3——指令命名带 `.b/.w/.t/.o` 与 `s/u` 后缀（`add.uo`/`ld.ub`/`st.o`/`set.zw`/`br.nz`/`illi`）；`contracts/opcodes.yaml` 以唯一 `insn` 字段（如 `ld.o-rd`/`ld.o-rb`）区分变体，覆盖率主键应为 `insn`（0628 为 `(op, ha)`）；MISC-byte/wyde/tetra/octa 子表改变向量文件组织；RB 算术为**全 64 位**（0.4.1 的 48-bit 截断/高 16 位保持结论**不适用**）；M1 scope 排除浮点/原子/系统/特权/RA 多存取等，覆盖率门控须显式限定 M1 scope。
- **拒绝的 legacy 行为**：把 QEMU/LLVM 运行结果当作期望值；用 `(mnemonic, format)` 作覆盖率主键导致 RD/RB 变体假全覆盖；让 deferred case 静默缺席；把向量校验脚本与编码表混为一套真相；复制 0.4.1 的向量数据/编码正文。

## 任务分解

| 编号 | 任务 | 交付物 | 依赖 |
|------|------|--------|------|
| `TESTCASES-002t` | 向量 schema + inventory + validator | `tests/vectors/schema.md`、`inventory.md`、`README.md`、`isa/*.yaml`、`tools/testcases/validate_vectors.py`、`Makefile` check 集成 | `SPEC-003t` |
| `TESTCASES-003t` | encoding class 向量补全 | 各 `tests/vectors/isa/*.yaml` 追加 encoding 向量 | `TESTCASES-002t` |
| `TESTCASES-004t` | 向量覆盖率修复（opcode identity + encoding.word） | `tools/testcases/validate_vectors.py`、缺漏向量补全 | `TESTCASES-003t` |
| `TESTCASES-005t` | validator 身份唯一性修复 | `tools/testcases/validate_vectors.py` | `TESTCASES-004t` |
| `TESTCASES-006t` | 语义向量内存地址 ROM→RAM | `tests/vectors/isa/rd-load-store.yaml`、`rb-ops.yaml` | `TESTCASES-002t`、`SPEC-006t` |
| `TESTCASES-007t` | ISA 向量文件修复（5 文件） | 5 个 `tests/vectors/isa/*.yaml` | `TESTCASES-004t` |
| `TESTCASES-008t` | control-flow 向量修复 + TDD 补全 | `tests/vectors/isa/control-flow.yaml` | `TESTCASES-004t` |
| `TESTCASES-009t` | load encoding deferred 重设计 | `tests/vectors/isa/rd-load-store.yaml` | `TESTCASES-006t` |
| `TESTCASES-010m` | testcases 里程碑 | 里程碑标记 | `TESTCASES-002t`~`TESTCASES-009t` |

- **依赖关系**：`002t → 003t → 004t → 005t`；`004t → {007t, 008t}`；`002t + SPEC-006t → 006t → 009t`；`010m` 汇总全部。
- **分解理由**：先建「schema + 数据 + 校验器」基座（002t），再补 encoding 层（003t），再修覆盖率身份与 encoding.word（004t/005t），随后按文件修数据（006t/007t/008t/009t）。每步可独立用 `tools/testcases/validate_vectors.py` + `make check` 验收。

## 说明

- 本模块只规划向量层，不实现 LLVM/QEMU/gem5。
- 期望值必须独立派生自 `spec/` 与 `.tao/knowledge/contract-isa.md`（independent oracle 原则）；禁止从 LLVM/QEMU 生成。
- `contracts/opcodes.yaml`（SPEC-003t）是唯一编码真相；向量不得另造编码表。
- `tools/testcases/validate_vectors.py` 置于 `tools/testcases/`（v5 各模块工具目录；`validate_encoding.py` 在 `tools/spec/`）；0628 置于 `scripts/`，差异在各任务注明。
- control-flow / load 的 QEMU 运行验收依赖 qemu/verif 模块的 harness（待规划），相关任务以数据不变量 + validator 为主验收，运行验收作为下游集成检查。
- 详细背景与 DADAO-0628 对照见各 `t` 任务文件。
