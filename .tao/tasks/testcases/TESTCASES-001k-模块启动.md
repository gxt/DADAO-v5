# TESTCASES-001k: testcases 模块启动

**模块**：testcases
**项目里程碑**：M1
**依赖**：无
**状态**：已验证

## 问题根源

DADAO-v5 的 TDD 合约要求：在任何 LLVM/QEMU 实现字节被写入之前，M1 scope 内每条指令必须已有独立测试向量，且向量期望值必须**手工派生自 `spec/` 与 `.tao/knowledge/contract-isa.md`**，不得从 LLVM 汇编输出或 QEMU 运行结果反推——否则测试只是实现的自证，无法捕获实现自身的错误。

当前仓库已有 `contracts/opcodes.yaml`（SPEC-003t，256 条记录）作为机器可读编码 oracle，但**没有任何测试向量数据、schema、覆盖矩阵或向量校验器**，后续 llvm/qemu/gem5 模块没有独立 oracle 可比对。DADAO-0628 的 DL-001d 正是为此建立 `tests/vectors/` 与 `validate_vectors.py`，并在随后 DL-017a/017b/020a/022c/027a/028a/034a 中反复修复覆盖率与数据缺陷；这些缺陷与结论是本模块的直接经验来源。

## 目的

建立 testcases 的独立向量层：

- 产出 `tests/vectors/schema.md`、`inventory.md`、`README.md`、`isa/*.yaml`（5 类向量：encoding / legality / semantic / boundary / overlap）与 `tools/testcases/validate_vectors.py`；
- 把向量校验接入 `make check` 作为门控；
- 使 M1 scope 内每条指令身份（`(insn, format)`，等价于编码表的 `(op, ha)`）都有 ≥1 条 active 向量，期望值全部可回溯到合约/spec；
- 使向量层可作为 LLVM/QEMU/gem5 的独立 oracle，并作为后续差分验证的输入。

## 对照关系

- **借鉴**：DADAO-0628 的向量工作流——DL-001d 建 schema/inventory/data/validator；DL-017a/017b 修覆盖率身份与唯一性；DL-020a 补 encoding class；DL-022c 内存地址 ROM→RAM；DL-027a/028a/034a 修数据与 control-flow/load 的 deferred 重设计；以及 `0002-detailed-roadmap.md` 的 TDD Contract / Vector Taxonomy / Ordering Rule。
- **差异**：v5 基于 SimRISC 0.5.3——指令命名带 `.b`/`.w`/`.t`/`.o` 与 `s`/`u` 后缀（`add.uo`/`ld.ub`/`st.o`/`set.zw`/`br.nz`/`illi`）；`contracts/opcodes.yaml` 的 `insn` 字段（如 `ld.o-rd`/`ld.o-rb`）区分 RD/RB/RA 变体，但**并非全局唯一**——`ext.*`/`shr.*`/`shl.*` 的 `orrr`（寄存器移位量/扩展位）与 `orri`（立即数）两条记录共享同一 `insn`（实测 20 组重复；178 条 M1 记录仅 158 个唯一 `insn`）。唯一编码身份是 `(op, ha)`（256/256 唯一，`op`=`value>>24`、`ha`=`(value>>18)&0x3f`），向量侧等价键为 `(insn, format)`（256/256 唯一）。**覆盖率主键须用 `(insn, format)`**，否则这 20 组会重演 0628 的假全覆盖；MISC-byte/wyde/tetra/octa 子表改变向量文件组织；RB 算术为**全 64 位**（0.4.1 的 48-bit 截断/高 16 位保持结论**不适用**）；**M1 scope 以 `contracts/opcodes.yaml` 的 `excluded_m1: true` 为唯一判据**（78 条：浮点 RF 全部、特权 cfx、LR-SC 原子），其余 178 条为 M1——**RA 存取/块赋值（`ld.o-ra`/`st.o-ra`/`ldm.o-ra`/`stm.o-ra`/`ra2rd`/`rd2ra`）与系统指令（`swym`/`illi`/`fence`）属 M1，不得从门控排除**（与 `contract-isa.md` §4.9、§7 及 `legality_rules.yaml` 的 active 规则一致）。
- **拒绝的 legacy 行为**：把 QEMU/LLVM 运行结果当作期望值；用 `(mnemonic, format)` 作覆盖率主键导致 RD/RB 变体假全覆盖；用非唯一的 `insn` 作覆盖率主键导致 `orrr`/`orri` 变体假全覆盖；让 deferred case 静默缺席；把向量校验脚本与编码表混为一套真相；复制 0.4.1 的向量数据/编码正文。

## 任务分解

| 编号 | 任务 | 交付物 | 依赖 |
|------|------|--------|------|
| `TESTCASES-002t` | 向量 schema + inventory + validator | `tests/vectors/schema.md`、`inventory.md`、`README.md`、`isa/*.yaml`、`tools/testcases/validate_vectors.py`、`Makefile` check 集成 | `SPEC-003t`、`SPEC-008t` |
| `TESTCASES-003t` | encoding class 向量补全 | 各 `tests/vectors/isa/*.yaml` 追加 encoding 向量 | `TESTCASES-002t` |
| `TESTCASES-004t` | 向量覆盖率修复（opcode identity + encoding.word） | `tools/testcases/validate_vectors.py`、缺漏向量补全 | `TESTCASES-003t` |
| `TESTCASES-005t` | validator 身份唯一性修复 | `tools/testcases/validate_vectors.py` | `TESTCASES-004t` |
| `TESTCASES-006t` | 语义向量内存地址 ROM→RAM | `tests/vectors/isa/rd-load-store.yaml`、`rb-ops.yaml` | `TESTCASES-002t`、`SPEC-006t` |
| `TESTCASES-007t` | ISA 向量文件修复（5 文件） | 5 个 `tests/vectors/isa/*.yaml` | `TESTCASES-004t`、`TESTCASES-009t` |
| `TESTCASES-008t` | control-flow 向量修复 + TDD 补全 | `tests/vectors/isa/control-flow.yaml` | `TESTCASES-004t` |
| `TESTCASES-009t` | load encoding deferred 重设计 | `tests/vectors/isa/rd-load-store.yaml` | `TESTCASES-006t` |
| `TESTCASES-010m` | testcases 里程碑 | 里程碑标记 | `TESTCASES-002t`~`TESTCASES-009t` |

- **依赖关系**：`002t → 003t → 004t → 005t`；`004t → 008t`；`002t + SPEC-006t → 006t → 009t`；`009t → 007t`；`010m` 汇总全部。
- **文件级串行约束**：`rd-load-store.yaml` 被 `006t`（语义地址迁移）、`009t`（load encoding 重设计）、`007t`（数据修复）依次修改，故 `007t` 依赖 `009t`，三者不得并行；`rb-ops.yaml` 由 `006t` 修改，不与 `007t` 冲突。`control-flow.yaml` 仅 `008t` 修改。
- **分解理由**：先建「schema + 数据 + 校验器」基座（002t），再补 encoding 层（003t），再修覆盖率身份与 encoding.word（004t/005t），随后按文件修数据（006t/009t/007t/008t）。每步可独立用 `tools/testcases/validate_vectors.py` + `make check` 验收。

## 说明

- 本模块只规划向量层，不实现 LLVM/QEMU/gem5。
- 期望值必须独立派生自 `spec/` 与 `.tao/knowledge/contract-isa.md`（independent oracle 原则）；禁止从 LLVM/QEMU 生成。
- `contracts/opcodes.yaml`（SPEC-003t）是唯一编码真相；向量不得另造编码表。覆盖率主键为 `(insn, format)`（`insn` 非唯一，见「对照关系」）。
- M1 scope 判据为 `contracts/opcodes.yaml` 的 `excluded_m1` 字段（78 条排除，178 条 M1），不另立指令清单。
- `tools/testcases/validate_vectors.py` 置于 `tools/testcases/`（v5 各模块工具目录；`validate_encoding.py` 在 `tools/spec/`）；0628 置于 `scripts/`，差异在各任务注明。
- 测试机相关的地址/exit/fault 语义以 `.tao/knowledge/adr-0004-test-machine.md`（SPEC-006t）为准；向量 schema 的 `expected_fault` 除 6 个 spec fault 外须能表达 ADR-0004 D5.8 的 `0x87`（unmapped，测试机约定）。
- control-flow / load 的 QEMU 运行验收依赖 qemu/integ 模块的 harness（qemu 模块 `QEMU-014t`~`019t`，`verif` 已解散），相关任务以数据不变量 + validator 为主验收，运行验收作为下游集成检查。
- 详细背景与 DADAO-0628 对照见各 `t` 任务文件。
