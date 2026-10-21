# SPEC-160t: `ftmin`/`fomin`/`ftmax`/`fomax` 解除 `excluded`（`scope → fp`，族 `minmax`）

**模块**：spec
**项目里程碑**：M9（FP 完备性）
**依赖**：`SPEC-159t`（记录已立）、`QEMU-071t`（trans 已落）、`LLVM-124t`（`.td` 已落）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 为什么必须等三册

- `scope: fp` 记录必须有 `.td`（`validate_instrinfo.py` 的 coverage 覆盖 `fp`）⇒ 等 `LLVM-124t`；
- `check_qemu_trans --strict` 属 **L2**，缺 trans 时翻转会让 L2 红 ⇒ 等 `QEMU-071t`；
- 两者到位后本册**不制造任何新红**（与 `SPEC-155t`/`SPEC-158t` 同一纪律）。

### 现场事实（2026-10-21 核，执行前须复核）

- `check_fp_contract.py`：`FAMILY_COUNTS` 为 12 族（FMA 链后 13 族/62 条）；本册新增 **`minmax`: 4** ⇒ **14 族 / 66 条**；
- `EXPECTED_TOTAL` 常量与 `check_scope.py` 的 `fp` 计数均需同步；
- `contracts/fp_semantics.yaml` 只收 `scope == "fp"`；每条需 `family`、`spec_cite`（`^SimRISC-0[0-7]`）、`semantics_ref = contract-fp.md#<anchor>`、`legality_refs`；
- `contract-fp.md` 的 `minmax` 段与 `<a id="minmax">` 由 `SPEC-159t` 提供。

## 目标

1. 4 条由 `excluded` 转 **`fp`**（删 `decode: ILLI`），`dst_rf0` 仍生效；
2. 新增族 `minmax`（4 条），`fp` 计数 +4；
3. 生成物/计数/只读锁同步。

## 接口规范

- **输入**：`tools/spec/generate_opcodes.py`、`tools/spec/check_scope.py`、`tools/spec/check_fp_contract.py`、`tools/spec/gen_asm_list.py`、`tools/spec/gen_legality_list.py`、`tools/llvm/gen_isa_coverage.py`、`spec/SimRISC-07`（追加 1 行）、`manifests/spec-readonly.lock.toml`。
- **输出**：`opcodes.yaml`（`fp` +4）、`fp_semantics.yaml`（+4 条 `family: minmax`）、`check_fp_contract` 族表/计数、`check_scope` 计数与 changelog、速查/合法性/矩阵/`contract-asm-list` 重生成、只读锁。
- **约束**：只改 4 条记录与本册必需的计数/族表；其它记录逐字节不变；不改判定语义；不 commit/push。

## 设计要点（**不预设唯一实现**）

### A. 族与契约

- `fp_semantics.yaml` 每条：`family: minmax`、`spec_cite: "SimRISC-07 §最小最大值"`（以实际章节名为准）、`semantics_ref: "contract-fp.md#minmax"`、`legality_refs: [dst_rf0]`；
- `check_fp_contract.py`：`FAMILY_COUNTS["minmax"] = 4`、`EXPECTED_TOTAL` = 现场派生（66）、族集合断言同步；
- 锚点可达性由 `check_fp_contract` 校验（`contract-fp.md` 须含 `<a id="minmax">`）。

### B. 计数与生成物（逐项现场跑）

`generate_opcodes` → `check_scope` → `validate-encoding` → `check-rule-refs` → `check_fp_contract` → `gen_asm_list --embed-spec/--drift` → `gen_legality_list --apply` → `gen_isa_coverage` → `contract-asm-list` → `SimRISC-07` 变更记录 1 行 → 只读锁。

## 验收标准

1. `fp` 计数 = 现场派生（+4）；`excluded` 相应 −4；`total` 不变；`fp_semantics.yaml` 含 4 条 `family: minmax`。
2. `check_scope` / `check_fp_contract`（**14 族**）/ `validate-encoding` / `check-rule-refs` / `check-instrinfo` / `check-isa-coverage` 全绿。
3. `check_qemu_trans --strict` 全绿（`QEMU-071t` 已落）。
4. `check-spec-*` / `check-asm-list*` 全绿；`git diff --stat` 显示非本 4 条记录零改动。
5. `make check`（L1）rc=0；`make check-modules`（L2）rc=0。
6. **可达 FAIL ≥ 2**：① 漏加 `minmax` 族 ⇒ `check-fp-contract` 红；② 不重算只读锁 ⇒ 红。
7. 完成区 ≤30 行、与真实输出逐条对齐；`milestones.md` 一行。

## 做（阶段）

1. 现场复核（族表、计数、锚点）。
2. 生成器 `scope="fp"` + 族映射 → 重生成 → 门控。
3. 计数/族表/变更记录/只读锁。
4. 反例注入 + L1/L2 + 完成区。

## 可达 FAIL（**≥2**）

- 不改 `check_fp_contract` 的族表 ⇒ 红；还原 ⇒ 绿。
- 不更新只读锁 ⇒ `check-spec-readonly` 红；重算 ⇒ 绿。

## 已知边界（**披露**）

- 不实现（已由 `QEMU-071t`/`LLVM-124t` 完成）；不做测试（`TESTCASES-059t`）。
- 不清理其它 `excluded` 记录。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
