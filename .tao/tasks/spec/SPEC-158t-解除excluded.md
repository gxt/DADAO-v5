# SPEC-158t: `ftfma`/`fofma` 解除 `excluded`（`scope → fp`，族表/计数/锁同步）

**模块**：spec
**项目里程碑**：M9（FP 完备性）
**依赖**：`SPEC-157t`（记录已立）、`QEMU-070t`（trans 已落 ⇒ 翻转后 L2 仍绿）、`LLVM-123t`（`.td` 已落 ⇒ `check-instrinfo` 绿）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 为什么必须等三册落地才能翻

- `scope: fp` 的记录必须有 `.td`（`validate_instrinfo.py` 文件头：`m1/m3/m8/m9` 与 `fp` 均参与 coverage）⇒ 等 `LLVM-123t`；
- `check_qemu_trans --strict` 是 **L2** 成员，缺 trans 时翻转会让 L2 红 ⇒ 等 `QEMU-070t`；
- 两条都到位后，本册翻转**不会再制造任何新红**（与 `SPEC-155t` 同一纪律，顺序已在 clmul 链上修正）。

### 现场事实（2026-10-21 核，执行前须复核）

- `scope` 真源在生成器：`tools/spec/generate_opcodes.py` 的 `rec("ftfma-...", ..., scope="excluded")` / `fofma`。
- `check_fp_contract.py`：FP 分 **12 族**、`fp` 计数写死 **60**；翻转后必须 **13 族 / 62 条**（新族 `fma` = 2）。
- `contracts/fp_semantics.yaml` 由生成器产出、只收 `scope == "fp"` 的记录；每条需 `family`、`spec_cite`（`^SimRISC-0[0-7]`）、`semantics_ref = contract-fp.md#<anchor>`、`legality_refs`。
- `.tao/contracts/contract-fp.md` 的 `fma` 段与 `<a id="fma">` 锚点由 `SPEC-157t` 提供（本册只引用，不新建）。
- `check_scope.py` 的分区计数为**写死断言**（`excluded`、`fp`、`total` 均需同步）+ changelog 段。

## 目标

1. `ftfma`/`fofma` 由 `excluded` 转 **`fp`**（移除 `decode: ILLI`），`dst_rf0` 仍生效；
2. FP 族表新增 `fma`（2 条），`fp` 计数 60→62；
3. 全部派生生成物与门控计数现场派生后一致；只读锁重算。

## 接口规范

- **输入**：`tools/spec/generate_opcodes.py`、`tools/spec/check_scope.py`、`tools/spec/check_fp_contract.py`、`tools/spec/gen_asm_list.py`、`tools/spec/gen_legality_list.py`、`tools/llvm/gen_isa_coverage.py`、`spec/SimRISC-07`（追加 1 行变更记录）、`manifests/spec-readonly.lock.toml`。
- **输出**：`opcodes.yaml`（`fp 62`、`excluded` 相应减 1、total 262）、`fp_semantics.yaml`（+2 条 `family: fma`）、`check_fp_contract` 族枚举 12→13 与计数、`check_scope` 计数与 changelog、速查表/合法性清单/ISA 矩阵/`contract-asm-list` 重生成、只读锁 sha。
- **约束**：**只**改 `ftfma`/`fofma` 相关记录与本册必需的计数/族表；其它记录**逐字节不变**；不改判定语义（只改计数常量与族枚举）；不 commit/push。

## 设计要点（**不预设唯一实现**，但下列各点必须覆盖）

### A. 族与契约

- `fp_semantics.yaml` 新增两条：`family: fma`、`spec_cite: "SimRISC-07 §无符号乘法加法"`（以实际章节名为准）、`semantics_ref: "contract-fp.md#fma"`、`legality_refs: [dst_rf0]`；
- `check_fp_contract.py` 的 `families` 段新增 `fma` 的 `required_keys`（与既有族同构），族计数 12→13、`fp` 60→62；
- 锚点可达性：`contract-fp.md` 必须含 `<a id="fma">`（`SPEC-157t` 已建，本册校验）。

### B. 计数与生成物（**逐项现场跑**）

- `generate_opcodes` → `check_scope` → `validate-encoding` → `check-rule-refs` → `check_fp_contract` → `gen_asm_list --embed-spec/--drift` → `gen_legality_list --apply` → `gen_isa_coverage` → `contract-asm-list`；
- `SimRISC-07` 变更记录**追加** 1 行（不改写历史）；只读锁重算。

### C. 不改面

- `opcodes.yaml` 中 `ftfma`/`fofma` 的 `op`/`ha`/`format`/`legality` 逐字节不变（只改 `scope`、删 `decode`）；
- 其它 260 条记录零改动（`git diff` 自查并粘输出）。

## 验收标准

1. `fp` = **62**、`excluded` = 现场派生（本册应减 1）、`total` = **262**；`fp_semantics.yaml` 含 2 条 `family: fma`。
2. `check_scope` / `check_fp_contract`（**13 族 / 62**）/ `validate-encoding` / `check-rule-refs` / `check-instrinfo` / `check-isa-coverage` 全绿。
3. `check_qemu_trans --strict` = **262/262**（`QEMU-070t` 已落）。
4. `check-spec-changelog` / `check-spec-readonly` / `check-spec-drift` / `check-asm-list*` 全绿；`git diff --stat` 显示非 `fma` 记录零改动。
5. `make check`（L1）rc=0；`make check-modules`（L2）rc=0。
6. **可达 FAIL ≥ 2**：① 漏改 `check_fp_contract` 的族计数 ⇒ 红；② 不重算只读锁 ⇒ `check-spec-readonly` 红。
7. 完成区 ≤30 行、与真实输出逐条对齐；`milestones.md` 一行。

## 做（阶段）

1. 现场复核（生成器 `scope` 位置、族枚举、计数、锚点）。
2. 生成器改 `scope="fp"` + 族映射 → 重生成 → 逐项门控。
3. `check_fp_contract` 族/计数；`check_scope` 计数；变更记录 1 行；只读锁。
4. 反例注入 + L1/L2 + 完成区。

## 可达 FAIL（**≥2，须真实注入并回绿**）

- 临时不改 `check_fp_contract.py` 的族计数（仍 12/60）⇒ `check-fp-contract` 红；还原 ⇒ 绿。
- 临时不更新 `spec-readonly.lock.toml` ⇒ `check-spec-readonly` 红；重算 ⇒ 绿。

## 已知边界（**披露，不自行扩面**）

- 不实现语义/选择（已由 `QEMU-070t`/`LLVM-123t` 完成）；不做测试（`TESTCASES-058t`）。
- 不顺手清理其它 `excluded` 记录或既有族划分。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
