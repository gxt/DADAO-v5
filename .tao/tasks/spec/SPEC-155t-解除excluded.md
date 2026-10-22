# SPEC-155t: `clmul.o` 解除 `excluded`（`scope` → `m9`，契约/生成物/只读锁同步）

**模块**：spec
**项目里程碑**：M9
**依赖**：`LLVM-122t`（**前置 1**：`check-instrinfo` 的 coverage 要求 `m9` 记录必须有 `.td`）与 `QEMU-068t`（**前置 2**：`check_qemu_trans` 是 L2 成员，缺 trans 时翻转会让 L2 红 ⇒ 先落 trans 再翻）、`ADR-0035`（`D5` 编码 / `D6` rd0 / `D7` 实现后落）
**状态**：已验证

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
- `spec/SimRISC-04 §1.5` 里的 ILLI 是 **`rd0` 合法性规则**（仍成立），**不动**。
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

- 只在 `SimRISC-00` 变更记录**末尾追加** 1 行（格式照既有条目：日期 + M9 + 「`clmul.o` 解除 `excluded`（`scope → m9`），执行语义见 `SimRISC-04 §1.5`」）；**不得**改写 `:418` 那行历史。
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
- 不改 `SimRISC-04 §1.5` 的 `rd0` ILLI 规则（仍成立）。
- 不顺手清理其它 27 条 `excluded` 记录的陈旧文案（另议/另册）。

## 完成区

**测试结果**：`./.work/evidence/SPEC-155t/run.sh` rc=0（c1–c22 全 OK，22/22；含 L1/L2）；`run.sh --inject` rc=0（12/12：3 例注入变红 → `cp`+md5 还原 → 回绿）；`--quick` rc=0（20/20）。
**修改文件**：`tools/spec/generate_opcodes.py`（`scope="m9"` + 删 `EXCLUDED_KEEP_RULE_REFS` 及其 docstring + 注释/头文案计数同步）；`tools/spec/check_scope.py`（`excluded 27`/`m9 9` + 判据来源追加 ADR-0035 D7 一行 + 文件头计数）；`contracts/opcodes.yaml`（重生成）；`spec/SimRISC-00-指令系统设计.md`（0.5.5-rc **追加** 1 条，历史行不改）；`spec/SimRISC-04-64位数据运算.md`（`gen_legality_list --apply`：移除 clmul 的 excluded 区块 3 行）；`.tao/contracts/contract-asm-list.md`、`tools/llvm/llvm-isa-backend-matrix.{md,tsv}`（重生成）；`manifests/spec-readonly.lock.toml`（00/04 sha256 重算 + 注释）；`.tao/knowledge/milestones.md`（1 行）；本任务书；新增 `.work/evidence/SPEC-155t/{run.sh,checks.py}`。
**验收结果**（真实输出，日志 `.work/log/spec/SPEC-155t/`）：
- 计数现场：`excluded 计数: 期望=27 实际=27`、`m9 计数: 期望=9 实际=9`、`total 计数: 期望=260 实际=260`（`check-scope: PASS`）。
- `clmul.o_rrrr_rd`：`scope: m9`、**无** `decode`、`rule_refs: [dst_dual_same]`；`op 0x56`/`format rrrr`/`mask 0xFF000000`/`value 0x56000000`/`fields`/`legality`/`spec_cite` 与基线逐字节相同；其余 **259 条整条 dict 逐条相同**（c1/c2 PASS）。
- `validate-encoding` 260 OK；`check-rule-refs` PASS（335 引用）；`check-instrinfo` 0 errors（allow-list `clmul_o_rd → m9`）；`check-isa-coverage --check` PASS（**accept 258 / reject 2**，现场派生；翻转前同为 258/2 —— `.td` 已由 `LLVM-122t` 落地；变化体现在缺口分桶 `excluded 19→18`、`仅 post-ISel 22→23`）；`check_qemu_trans --strict` **260/260**；`check-fp-contract`/`check-spec-{readonly,changelog,numbering,drift}`/`check-asm-list{,-drift}`/`check_lit_gen` 全 rc=0。
- 可达 FAIL（cp 备份 + md5 对账，禁 git checkout）：I1 `check_scope` 计数回退 28/8 ⇒ rc=1（`check-scope: FAIL — excluded 计数: 期望 28，实际 27`）→ 还原 md5 MATCH → rc=0；I2 锁内 SimRISC-00 sha 回退 ⇒ `check-spec-readonly` rc=1 → 还原 → rc=0；I3 生成物塞回 `decode: ILLI` ⇒ `checks.py record` rc=1 → 还原 → rc=0。
- `make check`（L1）rc=0（`repository checks (L1): PASS`）；`make check-modules`（L2）rc=0（`module checks (L2): PASS`，picolibc fast 18/20 pass、fail 0）。
- `git status --porcelain -uall`：10 个已跟踪文件（上列）+ 本任务书，无越界文件；`.work/**` 为 gitignore 证据目录。
**新发现/坑**：① L2 首跑红在 `check-musl-freshness`（`toolchain stamp == current clang/ld.lld: different`——仅 clang/lld **mtime** 变、size/version/git commit 全同，系 `LLVM-122t` 的 `install-host` 重装；按门控提示 `make build-musl-shared JOBS=8` 重建后转绿）⇒ **非本册引入**，属既有「工具链重装 ⇒ musl 过期」面；② `check-run-artifacts` 对 `.work/log/**` 有机械命名约束（`<TASK-ID>-<purpose>.log`，purpose **仅 ASCII**）⇒ 证据脚本日志名须合规，否则 L1 红；③ `check-milestones-fresh` 要求 milestones 行与任务书 `**状态**` 一致、按时间**倒序**、且未完成态时间须带 `（登记）`（待验收也算未完成）；④ 生成器模块 docstring/头文案里的分区计数（28→27、8→9）也是"写死计数"，须同笔同步（本次已改）。
**遗留问题**：① `.tao/contracts/contract-isa.md` 的 `scope: m9`（`8 条`）与 excluded 口径文案仍按翻转前表述——**非生成物、非本册授权面**，未改（建议另册同步）；② `Makefile` 的 `check-scope` 注释仍写「counts 152/60/15/227」（**既有**陈旧，本册未扩面）；③ `ISS-317` 现场为 `closed`（`resolved_by: QEMU-068t`），本册未触碰；④ 未改 `SimRISC-04 §1.5` 的 `rd0` ILLI 规则（仍成立）；⑤ `ADR-0035 D6` 文本仍写「以 `EXCLUDED_KEEP_RULE_REFS` 显式例外保留」（机制句随翻转失效，decision 本体 `rd0` 规则不变）——改 `Accepted` ADR 需用户逐条确认，未动。

## 审阅记录

（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）

### 第 1 轮 engineer 自审

逐行审查 `generate_opcodes.py`（`scope="m9"`、删 `EXCLUDED_KEEP_RULE_REFS` 及其 docstring、`_compute_rule_refs` 化简、头文案计数）、`check_scope.py`（两处常量 + 判据来源）、`spec/SimRISC-00`（仅追加 1 条）、锁（00/04 sha256 + 注释）、以及证据脚本 `run.sh`/`checks.py`。finding 与处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `checks.py record` 的「键集合」断言误把 `scope` 也从不变量里剔除 ⇒ c1 恒 FAIL（首跑 1/20） | ✅已修 | 期望键集合改 `set(base) - {"decode"}`；删未用常量 `ALLOWED_DIFF_KEYS` | `run.sh --quick` c1 rc=0（20/20） |
| F2 证据日志名不合 `check-run-artifacts`（要求 `<TASK-ID>-<purpose>`、purpose 仅 ASCII）⇒ L1 首跑 rc=2 | ✅已修 | `step` 改 `$TASK-cNN.log`；注入日志改 `$TASK-inject-<I1/I2/I3>[-restored].log`；清理旧非法名日志 | `make check` L1 rc=0；full 22/22 |
| F3 summary 读 `"$LOGDIR"/*.log`，而调用方把 stdout 重定向进同目录 ⇒ 自我增长（现场 291 GB） | ✅已修 | 只读 `$TASK-c[0-9][0-9].log`；去掉会命中超长 routing 行的 `accept` grep | 复跑 quick 20/20、full 22/22；`du` 892K |
| F4 milestones 行未带 `（登记）` 且落在 23:50 区块 ⇒ `check-milestones-fresh` 3 项 VIOLATION（L1/L2 双红） | ✅已修 | 该行置顶 + `2026-10-22 05:51（登记）` + 与任务书 `待验收` 一致 | `make check-milestones-fresh` PASS（48 行）；full 22/22 |
| F5 `checks.py gen` 把 `generate_lit_vectors` 连跑两次（冗余、无新覆盖） | ✅已修 | 删重复步骤 | c20 rc=0；生成物逐字节不变 |
| F6 L2 首跑红于 `check-musl-freshness`（clang/lld 仅 mtime 变，size/version/commit 全同） | ⏸延后/环境处置 | 按门控提示 `make build-musl-shared JOBS=8` 重建（非本册代码改动） | `check-musl-freshness` PASS；L2 rc=0；已记「新发现/坑」① |
| F7 `ADR-0035 D6` 仍写「以 `EXCLUDED_KEEP_RULE_REFS` 显式例外保留」——机制句随翻转失效（`D6` 本体 `rd0` 规则不变） | ⏸延后 | 未改：`Accepted` ADR 的 decision 改动须用户逐条确认 | 已记「遗留问题」⑤；`check-scope`/`check-rule-refs` 均 rc=0 |
| F8 生成器模块 docstring 与生成头文案的写死计数（`excluded 28`/`m9 8`）会与产物矛盾 | ✅已修 | docstring 28→27、8→9；生成头 m9/excluded 文案同步；`rec()` docstring 的 scope 集合补 `m9` | 重跑生成器逐字节不变（c20）；`check-scope` PASS |

判决：全部 finding 已处置（F6 为环境面已按门控处方闭环并披露、F7 属跨册授权面已披露）⇒ 状态 `待验收`。

### 第 1 轮 reviewer 验收（2026-10-22，独立重跑，不信完成区）

**重跑记录（rc 均为本人退出码）**
- `check_scope.py` rc=0：`excluded 期望=27 实际=27`、`m9 期望=9 实际=9`、`total 期望=260 实际=260`；本人独立 yaml 统计 260 = m1 156 / fp 60 / excluded 27 / m3 1 / m8 7 / m9 9。
- `clmul.o_rrrr_rd`：`scope: m9`、无 `decode`、`rule_refs: [dst_dual_same]`；自写比对（`git show c7b14fa1:contracts/opcodes.yaml`，未复用证据脚本）：**仅该条差异且仅 scope/decode 两键**，其余 **259 条整条 dict 相同**；`op/mask/value/fields/legality/spec_cite` 逐字节同基线。
- `grep -c EXCLUDED_KEEP_RULE_REFS tools/spec/generate_opcodes.py` = **0**（含 docstring）；仓库内仅 `ADR-0035`/任务书残留提及。
- 门控逐条 rc=0：validate-encoding（260 OK）/ check-rule-refs（335 处）/ validate_instrinfo（0 errors）/ check-fp-contract / gen_isa_coverage --check（**accept 258 / reject 2** 现场派生）/ check_qemu_trans --strict（**260/260**）/ check-spec-{readonly,changelog,numbering,drift} / check-asm-list{,-drift} / check_lit_gen（64 passed）。
- L1 `make check` **rc=0**（`repository checks (L1): PASS`）；L2 `make check-modules` **rc=0**（picolibc 18/20 pass、fail 0）。
- 只读锁：本人 `sha256sum` SimRISC-00=`68f414a5…`、SimRISC-04=`134d7349…`，与锁内值一致；`check-spec-readonly` 21 册 OK。
- 生成物幂等（本人 md5 快照→重跑 generate_opcodes / gen_asm_list --embed-spec / gen_legality_list --apply / generate_lit_vectors / gen_isa_coverage→复查）：39 文件全部无漂移。（注：`gen_asm_list --drift` 非该脚本旗标 rc=2；漂移由 `check-asm-list-drift` PASS 覆盖，等价达成）
- 独立注入（`cp`+md5，未用 git checkout/restore）：① `EXPECTED_EXCLUDED 27→28` ⇒ check-scope **rc=1**（`FAIL — excluded 计数: 期望 28，实际 27`）→ 还原 md5 MATCH → rc=0；② 锁内 SimRISC-00 sha 回退 ⇒ check-spec-readonly **rc=1** → 还原 MATCH → rc=0。
- 证据脚本审毕（断言均有可达 FAIL、`$?` 直捕不吞码、日志名合规）；本人重跑 `run.sh` rc=0（**22/22**）、`run.sh --inject` rc=0（**12/12**，3 例注入红→还原绿）。

**约束核验**：改动 = commit `02e52679` 共 11 文件，与完成区声明逐一相符、无越界、无契约/测试弱化；check_scope 只改计数常量 + changelog（判定语义未动）；`SimRISC-00` **仅追加 1 行**（0 删除，历史 `:418` 行原文仍在）；`SimRISC-04` 仅删 excluded 区块 3 行、`dst_dual_same` 仍列 clmul.o；验收前/后 `git status --porcelain -uall` 均 0 行 + 5 目标文件 md5 复查全 OK（注入完全还原）；完成区 11 行 ≤30、与真实输出对齐；milestones 行含`（登记）`且状态一致；ISS-317 现场 `closed`（QEMU-068t 关闭）本册未触碰。

**遗留（只记录，不改）**：① `.tao/contracts/contract-isa.md` §11/§A.10 仍写 `m9`（8 条）——非生成物、任务书输入/输出清单未列、无机械门控覆盖，且该文件另有**既有**陈旧口径（§A.7 仍写 excluded 11 条，早于 ADR-0034 即过时）⇒ **不属本册验收面**，建议另册统一同步 m9/excluded 口径；② `ADR-0035` `D6` 的 `EXCLUDED_KEEP_RULE_REFS` 机制句与 `D7`「scope = excluded」随翻转失效——decision 本体（`rd0` 规则/编码）不变；改 `Accepted` ADR 须用户逐条确认，建议由 architect 提请用户裁定（加状态注记或就地修订机制句）。

**判决：Accepted**（验收标准 8 条在本人重跑下全过、硬约束无违反；两处遗留均属文案/授权面，不阻断本册）。

