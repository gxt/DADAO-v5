# VERIF-001k: verif 模块启动

**模块**：verif
**项目里程碑**：M1
**依赖**：无
**状态**：待开始

## 问题根源

实现（LLVM/QEMU/gem5/Sail）之间需要**独立**的交叉验证，否则单一实现的 bug 会穿透。DADAO-0628 的验证链（ADR-0009）用「独立黄金模型 + 生成式合法性矩阵 + 多路差分」把翻译链变成可机械检验的差分。当前 DADAO-v5 只有编码表与合法性规则，尚无差分运行器、检查工具、集成 harness。

## 目的

建立验证基础设施：把 MC↔QEMU（及后续 gem5/Sail）的语义一致性变成可机械检验的差分；提供生成式合法性矩阵、spec 引用审计、issue/trans 检查等工具。

## 对照关系

- **借鉴**：DADAO-0628 的 ADR-0009 验证链（M1 引用审计、M2a 黄金模型、M3 生成式合法性矩阵）与 MC↔QEMU 集成。
- **差异**：v5 基于 SimRISC 0.5.3，向量/编码/合法性规则需按 0.5.3 重建；差分运行器需适配 v5 向量格式。

## 任务分解

| 编号 | 任务 | 交付物 | 依赖 |
|------|------|--------|------|
| `VERIF-002t` | 合法性规则与验证器 | `verif/legality_rules.yaml` | `SPEC-003t` |
| `VERIF-003t` | QEMU 语义测试 harness | `tests/scripts/build_test_binary.py`、`run_qemu_test.py`、`gen_trampoline.py`、`trampoline.bin`、`README.md` | `QEMU-014m`、`TESTSUITE-003t`、`SPEC-006t` |
| `VERIF-004t` | harness 语义验证修复 | `build_test_binary.py`（`emit_state_compare`）、`run_qemu_test.py`（fault 路由 + fail-closed） | `VERIF-003t` |
| `VERIF-005t` | QFC 覆盖校验 + lit 字节 oracle | `verif/check_qfc_coverage.py`、`verif/check_lit_bytes.py` | `SPEC-003t`、`LLVM-009t` |
| `VERIF-006t` | harness `expected_state.memory` 验证 | `build_test_binary.py`（memory 比对路径） | `VERIF-004t`、`TESTSUITE-006t` |
| `VERIF-007t` | issue registry + QEMU trans lint | `docs/issues.yaml`、`verif/check_issues.py`、`verif/check_qemu_trans.py` | `SPEC-003t`、`QEMU-014m` |
| `VERIF-008t` | 分支语义 harness 扩展 | `build_test_binary.py`（`build_branch_test_binary`）、`control-flow.yaml` semantic 激活 | `VERIF-004t`、`TESTSUITE-008t` |
| `VERIF-009t` | call/ret 语义 + RA stack | `build_test_binary.py`（`emit_call_ret_pattern`）、call/ret 语义测试 | `VERIF-008t`、`QEMU-012t` |
| `VERIF-010t` | MC↔QEMU 端到端冒烟 | `tests/e2e/*.s`、`tests/lit/E2E/*` | `LLVM-012m`、`QEMU-014m`、`SPEC-006t` |
| `VERIF-011t` | spec 引用审计器 | `verif/check_spec_refs.py` + 首轮审计报告 | `SPEC-002t`、`SPEC-008t` |
| `VERIF-012m` | M1 集成里程碑 | 模块里程碑标记（核验各任务） | `VERIF-002t`~`VERIF-011t` |

- **依赖关系**：`VERIF-002t` 依赖 `spec/SPEC-003t`（编码表）；harness 链为 `VERIF-003t` → `VERIF-004t` → {`VERIF-006t`、`VERIF-008t` → `VERIF-009t`}；`VERIF-005t`/`VERIF-007t`/`VERIF-011t` 为独立检查工具；`VERIF-010t` 依赖 LLVM/QEMU 里程碑；`VERIF-012m` 收敛全部。
- **分解理由**：合法性规则属验证链（DADAO-0628 DL-043a M3），从 spec 模块迁入本模块；其余对应 DADAO-0628 `DL-019a`、`DL-021a`、`DL-022a`、`DL-022b`、`DL-023a`、`DL-028a`、`DL-029a`、`DL-030a`、`DL-033a`、`DL-039a`，按「harness 基础 → 语义比较 → 内存/分支/call-ret 扩展 → 端到端冒烟」与「独立检查工具（QFC/lit/issue/trans/spec-refs）」两条线拆分，每个任务可独立验收。
- **规划完成**：M1 集成/差分/检查任务已全部补入，见上表；`VERIF-012m` 为 M1 集成里程碑。

## 说明

- 验证的独立性是命根子：合法性规则/黄金模型只从 `spec/` 与 `verif/opcodes.yaml` 派生，不抄 QEMU 源码。
- `verif/` 目录同时存放 spec 派生的机器可读数据（`opcodes.yaml`/`legality_rules.yaml`/`abi.yaml`）与验证工具。
