# SPEC-155t: `clmul.o` 解除 `excluded`（`scope` → `m9`，契约/生成物/只读锁同步）

**模块**：spec
**项目里程碑**：M9
**依赖**：`LLVM-122t`（**前置 1**：`check-instrinfo` 的 coverage 要求 `m9` 记录必须有 `.td`）与 `QEMU-068t`（**前置 2**：`check_qemu_trans` 是 L2 成员，缺 trans 时翻转会让 L2 红 ⇒ 先落 trans 再翻）、`ADR-0035`（`D5` 编码 / `D6` rd0 / `D7` 实现后落）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 为什么单列一册

- `scope` 是**规范/契约面属性**（`ADR-0035 D7`：编码先定、实现后落），不属 LLVM/QEMU 任何一侧的模块职责。
- 但翻转**不能**先于 `.td`：`tools/llvm/validate_instrinfo.py` 的 coverage 检查（第 25/27 行）要求 `scope:m1/m3/m8/`**`m9`** 记录**恰有**匹配的 `.td` def；`m9` 先例 = `rol.*`（第 78 行）。
- 而 `.td` 允许先于翻转：同一校验器第 34 行明写「MC 层仍需的个别 `scope:excluded`，如 `fence`」⇒ **`excluded` 记录可以已有 `.td`**（`fence` 即先例）。
⇒ 顺序 = `LLVM-122t`（加 `.td`，scope 不动）→ **本册**（翻 scope）→ `QEMU-068t`（decode/trans）→ `TESTCASES-057t`。每步都能全绿。

### 现场事实（2026-10-21 核，执行前须复核）

- `contracts/opcodes.yaml`（**产物**）里 `clmul.o_rrrr_rd`：`scope: excluded`、`decode: ILLI`、`rule_refs: [dst_dual_same]`。
- `scope` 的真源在**生成器**：`tools/spec/generate_opcodes.py` 的 `rec("clmul.o-rd", "clmul.o", "rrrr", 0x56, …, scope="excluded")`。
- `tools/spec/generate_opcodes.py` 的 `EXCLUDED_KEEP_RULE_REFS = frozenset({"clmul.o_rrrr_rd"})` 是 `ADR-0035 D6` 的**显式例外**（excluded 默认清空 `rule_refs`）⇒ 翻转后须**撤销**，否则留下「accepted 也走例外」的隐性规则。
- `tools/spec/check_scope.py` 把分区计数**写死**断言（文件头：`m1 156 / fp 60 / excluded 28 / m3 1 / m8 7 / m9 8 → 260`）+ changelog 段落 ⇒ 须同步为 `excluded 27 / m9 9`（总数仍 260）并追加一行 changelog。
- `spec/SimRISC-00` 变更记录里有一行（`:418` 附近）写「新增 `clmul.o` … `scope` 为 `excluded`（执行 ILLI）」—— 属**历史记录**，**不改写**，改为**追加**一条 M9 记录。
- `spec/SimRISC-04 §3.5` 里的 ILLI 是 **`rd0` 合法性规则**（仍成立），**不动**。
- 只读锁 `manifests/spec-readonly.lock.toml` 记录 `spec/**` 的 `sha256`；改 `SimRISC-00` 即须重算（`check-spec-readonly` 门控）。

## ✅ 已裁定（2026-10-21）

- 用户选定 **4 册拆分**：规范面单列本册（`SPEC-155t`），不把 spec 改动塞进 `LLVM-122t`/`QEMU-068t`。
- `clmul.o` 的 `scope` 最终值 = **`m9`**（M9 新增 ISA 指令，与 `rol.*` 同档），删除 `decode: ILLI`。
- **spec 授权（2026-10-21，用户原话）**：问「授权 `SPEC-155t` 追加 1 行 spec 变更记录 + 重算只读锁吗？」答 **「授权（推荐）」** ⇒ `spec/SimRISC-00` **追加 1 行**（**不改写** `:418` 历史行）+ `manifests/spec-readonly.lock.toml` sha256 重算，由本册执行。

## 目标

1. `clmul.o` 由 `excluded` 转 `m9`，`decode: ILLI` 移除，`dst_dual_same` 仍生效；
2. 所有派生生成物与门控计数**现场派生**后一致（不写死猜测值）；
3. `spec/` 只有 1 行变更记录被**追加**（历史行不改写），只读锁重算。

## 接口规范

- **输入**：`tools/spec/generate_opcodes.py`、`tools/spec/check_scope.py`、`tools/spec/gen_asm_list.py`、`tools/spec/gen_legality_list.py`、`tools/llvm/gen_isa_coverage.py`、`tools/testcases/generate_lit_vectors.py`、`spec/SimRISC-00`（**须授权**）、`manifests/spec-readonly.lock.toml`。
- **输出**：
  1. 生成器 `scope="m9"` + 例外撤销；
  2. `contracts/opcodes.yaml` 重生成（260 条、`excluded` 27、`m9` 9）；
  3. 全部生成物重跑并入库：`SimRISC-04 §1.1/§2`（`gen_asm_list --embed-spec`、`gen_legality_list --apply`）、`tests/llvm/lit/MC/DADAO-gen/gen-excluded.s`、`contracts-*`/`contract-asm-list.md`、ISA 覆盖矩阵；
  4. `spec/SimRISC-00` 追加 1 行 + 只读锁 sha256；
  5. 证据 `.work/evidence/<任务ID>/run.sh`。
- **约束**：**只**改 `clmul.o` 的记录与为此必需的计数/例外/文案；其它 259 条记录**逐字节不变**（`git diff` 自查）；不改门控**判定语义**（只改计数常量与 changelog）；不 commit/push。

## 设计要点（**不预设唯一实现**，但下列各点必须覆盖）

### A. 翻转的最小面

- 生成器：`scope="m9"`；`EXCLUDED_KEEP_RULE_REFS` 整条删除（并同步其 docstring 说明，避免留死代码）。
- `check_scope.py`：写死计数 `excluded 28→27`、`m9 8→9`（总数 260 不变）+ 文件头 changelog 追加一行（写清「ADR-0035 D7 实现后落」）。
- 判据不变式自检：`scope == excluded ⇔ decode == ILLI` 对翻转后的 `clmul.o` 必须**不成立**（无 `decode` 字段）；对其它 27 条仍成立。

### B. 生成物一致性（**逐项现场跑，不凭记忆**）

- `generate_opcodes` → `check_scope` → `validate-encoding` → `check-isa-coverage`（`accept`/`reject` 计数现场派生）→ `gen_asm_list --embed-spec` / `--drift` → `gen_legality_list --apply` → `generate_lit_vectors` → `gen_isa_coverage` → `.tao/contracts/contract-asm-list.md`。
- `gen-excluded.s`：`clmul.o` 的「UNREC（助记符不可汇编）」反例必须**消失**；若 `LLVM-122t` 已处理生成器前提，本册只需确认生成结果一致（**不重复改**）。

### C. spec 文本与只读锁

- 只在 `SimRISC-00` 变更记录**末尾追加** 1 行（格式照既有条目：日期 + M9 + 「`clmul.o` 解除 `excluded`（`scope → m9`），执行语义见 `SimRISC-04 §3.5`」）；**不得**改写 `:418` 那行历史。
- 重算 `manifests/spec-readonly.lock.toml` 的 `sha256`（脚本/流程照既有做法），`check-spec-readonly` rc=0。

## 验收标准

1. `contracts/opcodes.yaml`：260 条；`excluded` **27**；`m9` **9**；`clmul.o` 无 `decode`、`rule_refs` 仍含 `dst_dual_same`（现场 `grep`/计数输出粘入完成区）。
2. `check_scope` / `validate-encoding` / `check-rule-refs` / `check-instrinfo`（`.td` 已由前置册提供）全绿。
3. `check-isa-coverage` PASS，`accept`/`reject` 计数变化与翻转一致（现场输出）。
4. `check-spec-changelog` / `check-spec-numbering` / `check-spec-readonly` / `check-spec-drift` 全绿。
5. `check_qemu_trans --strict` **260/260 全绿**（`QEMU-068t` 已落 trans）⇒ 翻转后 L1/L2 无 new red、也无 known-red。
6. `make check`（L1）rc=0。
7. **可达 FAIL ≥ 2**（真实注入 → 红 → `cp`+md5 还原 → 绿）：(a) 忘改 `check_scope` 计数 ⇒ `check-scope` 红；(b) 不改只读锁 sha ⇒ `check-spec-readonly` 红。
8. 完成区 ≤30 行、与真实输出逐条对齐；`milestones.md` 一行；`ISS-317` 保持 open（关闭归 `QEMU-068t`）。

## 做（阶段）

1. 现场复核（生成器 `scope` 位置、`check_scope` 计数、只读锁条目、`gen-excluded.s` 现状）；取得 spec 授权原话。
2. 改生成器 + 计数 + 例外撤销 → 重生成 → 逐项门控。
3. `SimRISC-00` 追加 1 行 + 只读锁重算。
4. 反例注入（2 条）+ 还原回绿。
5. L1 + 完成区。

## 可达 FAIL（**≥2，须真实注入并回绿**）

- 临时把 `check_scope.py` 的 `excluded` 计数改回 28（或漏改）⇒ `check-scope` 红；还原 ⇒ 绿。
- 临时不更新 `spec-readonly.lock.toml`（`cp` 备份 + md5）⇒ `check-spec-readonly` 红；还原/重算 ⇒ 绿。

## 已知边界（**披露，不自行扩面**）

- 不实现执行语义（`QEMU-068t`）、不做 LLVM 选择（`LLVM-122t`）。
- 不改 `SimRISC-04 §3.5` 的 `rd0` ILLI 规则（仍成立）。
- 不顺手清理其它 27 条 `excluded` 记录的陈旧文案（另议/另册）。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
