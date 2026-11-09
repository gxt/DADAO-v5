# INFRA-113t: 里程碑绑定清理（退役 `M1-gate` 判据 + 清 ADR-0030/M9 过时基准）

**模块**：infra
**项目里程碑**：M11
**依赖**：无
**状态**：已验证

## 定位与边界（先读）

- 本任务是**M10 之后的清理**：**不纳入 `M10` 收尾判据**、**不阻塞 `check-night`**、**不列进 `INTEG-052m`**（该册尚未建立；建立时**不得**列本任务）。
- 执行期若发现本任务与 M10 收尾存在**强制关联**（例如某条验收只能靠 M10 收尾门控才可判）⇒ **停下报告**，不得自行改 `INTEG-052m` / M10 状态 / M10 模块 `m`。
- 只改代码与登记口径，不改任何规范正文、不改组件、不立 ADR（理由：不动跨组件合约；判据真源仍是单文件 `tools/infra/check_issues.py`）。

## 执行环境
**执行环境**：本地（纯 Python + 文档改动；另需定向跑 libc-test 5 例。**不重建组件**：工具链 / qemu / musl `libc.a` 现场已具备）

## 问题根源

### 范围 A：`M1-gate` 已退役，判据残留

`M1-gate` 是 M1 阶段的 issue 阻断判据；M1 已于 2026-09-22 达成（历史口径见 `.tao/archive/M2/infra/INFRA-033t-*.md`：门控随 M1 达成退役、`check_issues.py` 只保留字段检查）。但**代码里没退**：

- `tools/infra/check_issues.py`：docstring L2/L4 与 `if "M1-gate" in blocks:`（L53）、输出文案 L82/L90 —— 该字符串是**唯一**阻断判据。
- `Makefile:997`：`_locked-check` 目标体内**直调** `python3 tools/infra/check_issues.py` ⇒ 每次 L1 都跑它（不是独立 target，不在依赖表里）。
- `.tao/knowledge/issues.yaml`（现场 2026-11-01 09:0x）：**17 条、全部 `closed`**、`blocks` **全为 `[]`**、`resolved_by` **全非空**；全文**无 `M1-gate` 字样**；文件**无头注释**（L1 即 `- id: ISS-098`）。
- `docs/Process-04-里程碑归档规范.md:42`（§3 步骤 5）：「更新文件头的里程碑状态、字段约束、`gate` 判据（如 `M1-gate` 历史化）」——把 `gate` 判据写成**在役**项。
- 其它命中**只在 `.tao/archive/**`**（历史册，**不改**）。

### 范围 B：runner 的 ADR-0030 / M9 基准自证失效

- **目标已是 binary128**：`components/musl/patches/arch/dadao/bits/float.h.patch:32` ⇒ `#define LDBL_MANT_DIG 113`；工作树 `musl 组件源树中的 arch/dadao/bits/float.h:26` 同值。
- **M9 已交付**：`components/musl/changelog.md:40` 记 5 例 `math/{acoshl,asinhl,erfcl,lgammal,tgammal}` 静态/动态两档 `known-fail → pass`（各 5/5）。
- **但 `tools/testcases/tset/libc-test/run_libc_test_user_suite.py` 仍以「目标 = binary64（53）/ ADR 把工作排在 M9」为 known-fail 基准**，其证据函数**末项硬断言 `LDBL_MANT_DIG == "53"`**（L779–783）⇒ 现场 113，基准**恒 False**（自证失效）。
  - `ADR0030_ID` / `ADR0030_FILE` / `ADR0030_CASE_LIST`（L304–307）、`KNOWN_FAIL_BASES` 的 `ADR0030_ID` 行（L312–313，文案含 `LDBL_MANT_DIG=53`）；
  - `adr0030_evidence()`（L737–789，docstring 述「defers it to M9」「gap M9 removes」，证据串写 `-> M9`）；
  - `attribute_known_fail_bases()` 的 `fail` 分支（L851）、审计 `bad_known` 的 `ADR0030_ID` 分支（L1574–1575）与 `missed_adr`（L1587–1588）；
  - `CASE_NOTES` 的 5 条 `math/*l` note（L392–415，均写 `LDBL_MANT_DIG=53` + `binary128 in M9`）；
  - 模块 docstring：L114–116（`binary128 in M9, so the five math/*l ulperr failures disappear then`）、L121–123（`in the dynamic round dlopen is out of the declared M8 scope -- ADR-0025 D2 / INFRA-085t item 7`）。
- **另一处过期＋误引**：`STRUCTURAL_EXCLUSIONS` 的 4 条静态档排除理由（L453–468）写 `ADR-0025 D2 defers dlopen to M9+`。现场核：`ADR-0025` 的 `D2` = 「**无内核目标**」，**不含** dlopen 决策（误引）；且 `DYNAMIC_EXCLUSION_REASONS` 自 `LLVM-117t` 起为空、动态档已正常建/跑这 5 例 DSO 用例（`HELPER_DSOS`，`discover()` L926–928 在 `dynamic` 时 `pop`）⇒ 「M9+ 才做」也过期。
- **口径更正（执行时按现场）**：下发清单里写「`SPECIAL_CASES` 中 math `*l` 的 known-fail 口径」——**该变量在本文件不存在**，对应物是 `CASE_NOTES`（`SPECIAL_CASES` 仅存在于 `tools/testcases/oracle_fma.py`，与本任务无关，**不改**）。另：排除理由的 `ADR-0025 D2` 误引出现在 **4 行**（L456 / L460–461 / L464 / L467），不止 3 处。

## 目的

- **A**：`M1-gate` 概念在**在役面**彻底消失；`check_issues.py` 只保留 `status` / `resolved_by` 字段约束，**fail-closed 不变**。
- **B**：runner 不再持有过期基准——`math/*l` 按**当前** binary128 事实判定；`M9` / `M9+` / 误引 `ADR-0025 D2` 的表述改为当前事实；**真实的动态加载缺口说明保留**（静态档 `-static` 无动态装载器，属结构事实）。

## 接口规范

### 输入（现场事实，2026-11-01 09:0x 核）

- `tools/infra/check_issues.py` 现场可跑；`issues.yaml` 17 条全 `closed`、`blocks` 全空（`python3 -c` + `yaml` 逐条统计）。
- 定向跑前置齐备：`安装根 bin 下的 clang`、`运行期 QEMU 构建树中的 qemu-dadao`、`musl 组件源树中的 lib/libc.a`（mtime `2026-11-01 03:48` **晚于** `float.h` 的 `2026-10-24 15:47` ⇒ 该 `libc.a` 已含 binary128）、语料 `libc-test`（`运行期临时目录` 下 `libc-test` 语料树）。
- 5 例 id：`math/acoshl`、`math/asinhl`、`math/erfcl`、`math/lgammal`、`math/tgammal`。
- `make check` **受 `gate.lock` 串行**（`Makefile` `GATE_LOCKED_TARGETS` 含 `check` / `check-modules` / `check-full`；等待上界 `GATE_LOCK_WAIT`，超时 rc=75）⇒ 夜跑占用时不能假设即时可跑。
- 行号会随编辑漂移：**一律按符号名定位**（`ADR0030_*`、`adr0030_evidence`、`CASE_NOTES`、`STRUCTURAL_EXCLUSIONS`），行号只作现场参照。

### 输出（改动清单，逐条）

1. **`tools/infra/check_issues.py`**（A）
   - **删除** `M1-gate` 阻断检查：`if "M1-gate" in blocks:` 分支、`n_blocking` 计数与两处输出文案。
   - **保留**：fail-closed（`issues.yaml` 缺失 ⇒ rc=1）、`status` 取值合法性、`closed ⇒ resolved_by` 必填、`open ⇒ resolved_by` 为 null/空（现状判据不动）。
   - docstring 改为「`resolved_by` 字段约束检查（`M1-gate` 阻断判据已退役：M1 达成 2026-09-22 后无在役 gate；`blocks` 字段保留为**描述位**、不参与判定）」。
   - **决策**：不另立通用 `gate` 键。理由：现场 17 条 `blocks` 全空、无任何非 `M1-gate` 取值的使用者 ⇒ 换名等于保留一条**无人填写**的死判据；将来若确需 gate，另立任务从判据出发（不在本任务预埋）。
2. **`.tao/knowledge/issues.yaml`**：**内容零改动**（17 条已全 `closed` / `blocks` 全空 / 无 `M1-gate`）。现场**无头注释** ⇒ 不新增头注释（避免无谓改动）；若实施中确需 1 行说明 `blocks` 为保留描述位，**只允许 1 行 YAML 注释**，不动条目。
3. **`docs/Process-04-里程碑归档规范.md`**（§3 步骤 5，现场 L42）：`gate` 判据项改为**已退役**口径（例：「更新字段约束（`status` / `resolved_by`）；`gate` 判据已退役——`M1-gate` 随 M1 达成退役，`INFRA-113t`」）；不新增章节、不复制判据正文。同时把该步「更新文件头的里程碑状态」与现状（`issues.yaml` 无文件头）的错位**酌情一句更正**（若改，仍不超过原条目长度）。
4. **`tools/testcases/tset/libc-test/run_libc_test_user_suite.py`**（B）
   - **先判定，再改**：按「判定门槛」跑 5 例两档，取真实分类。
   - `pass=5 / fail=0`（预期）⇒ **删除** ADR-0030 全链路：`ADR0030_ID` / `ADR0030_FILE` / `ADR0030_CASE_LIST`、`KNOWN_FAIL_BASES` 该行、`adr0030_evidence()`、`attribute_known_fail_bases()` 的该分支、审计两处（`bad_known` 的 `ADR0030_ID` 分支 + `missed_adr`）、`CASE_NOTES` 的 5 条 `math/*l`。
   - 若仍有 `fail` ⇒ **不删**，按 **binary128** 重算 basis（`LDBL_MANT_DIG=113`、`__SIZEOF_LONG_DOUBLE__=16`）并在完成区写明；**禁**继续以 53 为据、**禁**把 `fail` 改判为 `pass`。
   - docstring：L114–116 的 M9 表述与 L121–123 的「M8 scope / ADR-0025 D2」按当前事实改写；`STRUCTURAL_EXCLUSIONS` 4 条理由去掉 `M9+` 与 `ADR-0025 D2` 误引，**保留**「静态档 `-static` 无动态装载器」这一真实缺口，并注明动态档自 `LLVM-117t` 起正常建/跑（`HELPER_DSOS`）。**不新增** ADR 引用（避免再次误引；如需引用须逐字核对该 ADR 决策标签）。
   - **不改**分类器其余判据：`GAP_SIGNATURES`、ISS-226 的「不得随意改判」、ISS-246 / ISS-251 / ISS-255 三个基准、`--reserved-va` / `-R 4G` 口径。
5. **`.tao/knowledge/milestones.md`**：任务流水**表首**插 1 行（本任务书，`待开始` + `（登记）`）。
6. **本任务书**：状态 / 完成区 / 审阅记录。

### 判定门槛（B，机械）

两档直接调驱动（**不经 make** ⇒ 不占 `gate.lock`）：

```
python3 tools/testcases/tset/libc-test/run_libc_test_user_suite.py \
  --link-mode static \
  --filter '^math/(acoshl|asinhl|erfcl|lgammal|tgammal)$' \
  --json-out <运行期临时目录>
```

dynamic 档同法换 `--link-mode dynamic` 与文件名。判据：`pass=5 且 fail=0 且 known-fail=0 且 blocked=0` ⇒ 走**删除**分支；否则走**重算**分支（完成区注明每条真实分类）。

## 约束

- 只改：`tools/infra/check_issues.py`、`docs/Process-04-里程碑归档规范.md`、`tools/testcases/tset/libc-test/run_libc_test_user_suite.py`、`.tao/knowledge/milestones.md`、本任务书；证据落 `运行期证据（已清理，未归档）`（`<>` 占位，不写具体文件名）。
- 禁改：`.tao/archive/**`（历史 `M1-gate` 命中**保留**）、`.tao/knowledge/issues.yaml` 条目内容、`contracts/**`（尤其 `opcodes.yaml` 的 `scope: m1` 基础 ISA 身份集）、`.tao/contracts/**`、`.tao/adr/**`（`adr-0030` 正文不改）、`components/**`、`spec/`、`tests/`、`Makefile`。
- 不改 M3 / M4 / M5 / M6 仍有效的回归门控名称，也不动 `scope: m1`（基础 ISA）与 `scope: fp` / `m9` 口径。
- 不跑 `make check-full` / `check-night` / `check-modules` / tset smoke/full（L2/L3 与夜跑不在本任务面）；`make check` **只在验收时**跑一次（并允许因锁分两次）。
- 反例注入**禁** `git checkout` / `restore` / `stash` 还原：`issues.yaml` 用 `cp` 备份 + md5 对账；runner 用 `运行期临时目录` 副本树。
- 临时目录 `运行期临时目录`；仓库内不得留探针/临时文件。

## 验收标准

1. **A·在役面零残留**：`git grep -n 'M1-gate' -- tools docs .tao/knowledge .tao/contracts Makefile` ⇒ **0 行**（rc=1）。
   - 说明：`.tao/archive/**`（历史册）与 `.tao/tasks/**`（任务记录，含本任务书）**不计**——本任务书自身必然出现该词。附证：`git grep -c 'M1-gate' -- .tao/archive | wc -l` > 0（历史保留，贴计数）。
2. **A·字段约束仍生效**：`python3 tools/infra/check_issues.py` ⇒ **rc=0**；输出**不含** `M1-gate`；仍打印 `resolved_by 约束 OK (… 17 closed → 非空 / 0 open → null)` 与计数行。
3. **A·反例可达 FAIL**（`cp` 备份 + md5 对账，禁 git 还原）：
   - 注入 `status: closed` 且 `resolved_by: null` ⇒ **rc=1** 且点名该 id；
   - 注入 `status: open` + `blocks: [M1-gate]` ⇒ **rc=0**（证明阻断已退役、`blocks` 不参与判定）——这一条是「退役」的正向证据，须与上一条同时贴；
   - `cp` 还原后 `md5sum` 与注入前一致，`git status --porcelain -uall` 只剩本任务允许的改动。
4. **B·判定留证**：两档 JSON 落 `运行期临时目录`；贴 `pass / fail / known-fail / blocked` 计数 + 5 例逐条状态。
5. **B·零残留**：对 `run_libc_test_user_suite.py`：`grep -n 'ADR-0030\|adr0030\|LDBL_MANT_DIG=53'` ⇒ **0 行**；`grep -n 'M9'` ⇒ **0 行**。（走「重算」分支时改为：无 `53`、无 `M9`，且 basis 明写 113。）
6. **B·反例可达 FAIL（审计不放宽）**：在 `运行期临时目录` **副本树**里把 `ISS251_ID` 的 `KNOWN_FAIL_BASES` 指向恒 False 的 evidence，跑 `--filter '^functional/strptime$'` ⇒ 审计段 rc≠0 并报未归因失败（`unexplained_fail` / `bad_known`）；仓库内原文件 md5 前后一致（零改动）。
7. **L1**：`make check` ⇒ **rc=0**（含 `repository checks (L1): PASS`）。
   - 若 `gate.lock` 被夜跑占用：先取 2/4/5/6 的直调证据，锁空后**补跑**并贴真实 rc；**rc=75（锁等待超时）不作通过证据**，也不得记为 PASS。
8. **体例**：`make check-tasks`（报告型）rc=0 且本任务不在「漏收尾」主表；`make check-milestones-fresh` ⇒ **rc=0**（表首行状态/格式/倒序一致）。本任务书完成区 ≤30 行。
9. **证据脚本**：`运行期证据（已清理，未归档）` 下一键脚本跑通（`checks=N failures=0`，脚本自身 rc 落证据），每条断言有**可达 FAIL** 路径（禁恒真）。

## 文件范围（摘要）

- 允许：`tools/infra/check_issues.py`、`docs/Process-04-里程碑归档规范.md`、`tools/testcases/tset/libc-test/run_libc_test_user_suite.py`、`.tao/knowledge/milestones.md`、`.tao/tasks/infra/INFRA-113t-*.md`、`运行期证据（已清理，未归档）`。
- 禁止：其余一切（`.tao/archive/`、`.tao/adr/`、`contracts/`、`.tao/contracts/`、`components/`、`spec/`、`tests/`、`Makefile`、`issues.yaml` 条目内容）。

## 用户授权原话

> 「可以，如果不影响M10收尾的话，现在立任务」

（2026-11-01，主会话；据此立项：**M10 后清理，不纳入 M10 收尾**。）

## 下发前预检（5 项，结论均为现场核）

1. **任务书内部一致**：改动清单 ⊆ 文件范围；验收 1–9 均机械可执行；状态 `待开始`；背景事实（`check_issues.py` L2/4/53/82/90、`Process-04:42`、`issues.yaml` 17 条全 `closed`、`blocks` 全空、`float.h` 113、`libc.a` mtime、runner 行号）**逐条来自现场命令**。
2. **验证前置可用**：`python3` + `yaml` 可跑 `check_issues.py`（现场 rc=0）；`git grep` 可用；toolchain / `qemu-dadao` / musl `libc.a` / 语料齐备（均 `ls` 过）⇒ 5 例可定向跑；`make check` **受锁** ⇒ **验收 7 现在 = BLOCKED（夜跑占锁时）**，替代证据 = 验收 2/4/5/6 的直调 + 锁空后补跑真实 rc。
3. **验收逐条可跑性**：1/2/3/4/5/6/8/9 **现在可跑**；7 见上（锁）；`make check-milestone` **不可**作绿判据（前置含夜跑/L3 报告与 `m` 册 ⇒ 现状必红），本任务**不引用**它。
4. **与 `contracts/`、`tests/inst/` 一致**：二者零改动；`scope: m1` 身份集与 `check-scope` / `check-isa-coverage` 不受影响（改的只是「读它的人」的注释口径）。
5. **拟改文件 × `spec/` 清单**：4 个文件均不在 `spec/` ⇒ **无命中、无 BLOCKED**；`check-spec-readonly` 必绿（`spec/` 未动）。

## 完成区

**测试结果**：evidence `运行期证据脚本（已清理，未归档）` **checks=36 failures=0**（脚本自身 rc=0，落 `run.rc`）；5 例两档 **pass=5 / fail=0 / known-fail=0 / blocked=0**（static、dynamic 各 5/5，closure_ok=classification_ok=true）；`make check` rc=0。
**修改文件**：
- `tools/infra/check_issues.py`：删 M1 阶段阻断分支/计数/文案；只留 `status`/`resolved_by`；fail-closed 不变。
- `docs/Process-04-里程碑归档规范.md`：§3 步骤 5 的 `gate` 判据改「已退役」+ 文件头口径更正（不新增章节）。
- `tools/testcases/tset/libc-test/run_libc_test_user_suite.py`：删 ADR-0030 全链路（常量/表行/evidence 函数/fail 分支/审计两处/CASE_NOTES 5 条）；清 `M9`/`M9+`/`ADR-0025 D2` 误引（含 4 条 `STRUCTURAL_EXCLUSIONS` 与 2 处链接注释）；保留「`-static` 无动态装载器」真缺口并注明动态档经 `HELPER_DSOS` 正常建/跑。判据其余（`GAP_SIGNATURES`、ISS-226/246/251/255、`--reserved-va`）零改动。
- `.tao/knowledge/milestones.md`（113 行状态 → 待验收）、本任务书、`运行期证据脚本（已清理，未归档）`（新证据脚本）。`issues.yaml` 零改动。
**验收结果**（真实 rc/计数）：
1. `git grep -n 'M1-gate' -- tools docs .tao/knowledge .tao/contracts Makefile` ⇒ **0 行 rc=1**；`.tao/archive` **71** 文件保留。
2. `check_issues.py` rc=0，输出 `check_issues: 0 open, 0 closed` + `resolved_by 约束 OK (0 closed → 非空 / 0 open → null)`，不含该词；17-closed 形态用 `运行期临时目录` 同名副本证明（实打实打印 `17 closed → 非空 / 0 open → null`）；缺文件 fail-closed rc=1。
3. 注入 `closed`+`resolved_by:null` ⇒ **rc=1** 点名 `ISS-TEST-A`；注入 `open`+`blocks:[M1-gate]` ⇒ **rc=0**；`cp` 还原后 md5 `9c4e93fb…` 前后一致。
4. 两档 JSON `运行期临时目录`：5/5 pass（逐例 pass，exit=0）。
5. runner `grep -nE 'ADR-0030|adr0030|LDBL_MANT_DIG=53'` ⇒ **0**；`grep -n 'M9'` ⇒ **0**。
6. `运行期临时目录` 副本树 ISS-251 evidence 恒 False ⇒ **rc=1** + `unclassified failure(s) remain: ['functional/strptime']`；adopt-无证据变体 ⇒ **rc=1** + `known-fail without live basis evidence`；仓库 runner md5 `dc54cce3…` 前后一致。
7. `make check` **rc=0** + `repository checks (L1): PASS`（锁空，一次跑通）。
8. `make check-tasks` rc=0、`make check-milestones-fresh` rc=0（6 行 PASS）。

**新发现/坑**：
- 任务书「17 条全 closed」已过期：M10 归档（2026-11-01）把 17 条冻结到 `.tao/archive/M10/issues-closed.md`，活台账现为 `[]`（0/0）。`issues.yaml` 零改动 ⇒ 验收 2 的 "17 closed" 只能用 `运行期临时目录` 副本证明格式。
- `check-tasks` ① 在 `待验收` 窗口必然命中本任务（完成区已填 + 待验收），`INFRA-114t` 已有同口径先例；已用临时树翻 `已验证` 证明 ① 归零。
- `git status` 对中文路径转义，判定须 `-c core.quotepath=false`（lessons §2.19 再次命中，证据脚本首轮曾因此误红）。

**遗留问题**：无阻塞项。两处「任务书字面 vs 现场」已按现场处置并留证（活台账 0/0、① 命中本任务），`/complete` 时知会即可。

## 审阅记录

#### 第 1 轮 engineer 自审

**范围**：`check_issues.py` 全文、`Process-04` §3 步骤 5、runner 全量 diff（docstring / 常量 / `CASE_NOTES` / `STRUCTURAL_EXCLUSIONS` / evidence / attribute / audit）逐行核对。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `check_issues.py` docstring 若照任务书原话写 `M1-gate`，会撞验收 1（`git grep` 须 0 行） | ✅已修 | 改为「M1 stage's issue-blocking gate」表述，不出现字面串 | `git grep 'M1-gate' -- tools …` rc=1 |
| F2 删除分支 vs 重算分支：最初按 binary128 改写 5 条 `CASE_NOTES` | ✅已修 | 按删除分支整条删（`pass` 不带 note，保留只增维护负担） | 文件内 `math/*l` note 0 处 |
| F3 `regression/tls_get_new-dtv.c` 旧理由写「port has no threads」（INFRA-095t 后已假） | ✅已修 | 只述 `-static` 无动态装载器 + 动态档建 DSO | diff 该条；`grep M9`=0 |
| F4 删 `missed_adr` 后 `classification_ok`/emit/注释是否残留 | ✅已修 | 同步删变量、emit、注释 | 两档 classification_ok=true；B6 注入仍 rc=1 |
| F5 边界：删掉 fail 分支的第二个 basis 后 ISS-251 归因链是否仍有效 | ✅已验 | —（无需改） | `运行期临时目录` 副本恒 False ⇒ rc=1 反证归因在用 |
| F6 证据脚本对中文路径用 `git status` 转义导致误红（实跑 A3-tree-scope FAIL） | ✅已修 | 加 `-c core.quotepath=false` | 重跑转绿 |
| F7 反例是否恒真：每类断言是否有可达 FAIL | ✅已验 | 补 4 条负控制（grep/JSON/runner/任务表） | 负控制全部按预期非零/命中 |

判决：findings 全部已修/已验 ⇒ 状态置 `待验收`。

#### 第 1 轮 reviewer 验收

**重跑记录（全部本人执行，日志 `运行期临时日志`）**：
- `运行期证据脚本（已清理，未归档）` 重跑：**checks=36 failures=0 / SCRIPT_RC=0 / run.rc=0**，与完成区一致（`reviewer-run.log`）；逐条审脚本：A1/A2/A3/A2b/A2c、B4（含 doctored-JSON 负控制）、B5（含注入副本负控制）、B6（两处 `运行期临时目录` 副本树真跑 qemu 变异 ⇒ rc=1）、L1 均有可达 FAIL 路径，无恒真。
- 验收 1：`git grep -n 'M1-gate' -- tools docs .tao/knowledge .tao/contracts Makefile` ⇒ **0 行 rc=1**；`git grep -l 'M1-gate' -- .tao/archive | wc -l` = **71**（历史保留）。
- 验收 2：`python3 tools/infra/check_issues.py` ⇒ **rc=0**，输出 `check_issues: 0 open, 0 closed` + `resolved_by 约束 OK (0 closed → 非空 / 0 open → null)`，无该词；`运行期临时目录` 合成 17-closed 副本实打 `17 closed → 非空`；缺文件 rc=1。
- 验收 3（**独立注入**，`cp`+md5，未用 git 还原）：注入 `closed`+`resolved_by:null` ⇒ **rc=1** 且点名 `ISS-REVIEW-A`；注入 `open`+`blocks:[M1-gate]` ⇒ **rc=0**；两次还原 md5 均 `9c4e93fb…` 一致，`git status` 只剩 5 个允许文件。
- 验收 4：两档 JSON 本人重跑生成并逐例核对 —— static/dynamic 均 `counts={'pass':5,'fail':0,'known-fail':0,'blocked':0}`、`closure_ok=classification_ok=True`，5 例逐条 `pass|exit=0`；`known_fail_bases` 仅 ISS-246/251/255；static 档 4 条 dlopen 排除理由已为 `-static` 真缺口 + `HELPER_DSOS` 说明，dynamic 档不再排除。
- 验收 5：`grep -nE 'ADR-0030|adr0030|LDBL_MANT_DIG=53|ADR-0025'` ⇒ rc=1；`grep -n 'M9'` ⇒ rc=1；`GAP_SIGNATURES`/ISS-226/246/251/255/`--reserved-va`/`-R 4G`/`DYNAMIC_EXCLUSION_REASONS`（保留空表）均在。另 `git grep adr0030_evidence|ADR0030` 全仓 0 命中。
- 验收 6：`make check` 本人直跑 ⇒ **rc=0** + `repository checks (L1): PASS`（`reviewer/make-check.log`）。
- 验收 8：`make check-tasks` rc=0；`make check-milestones-fresh` rc=0（6 行 PASS）。
- **反向注入补充**（reviewer 独立，`运行期临时目录` 副本树）：`iss251_evidence` 体改恒 True ⇒ rc=0 —— 可解释：`strptime` 本征 fail，admission 与 audit 复用同一证据函数（本任务前同构，非回归），且验收 6 的两条判据（证据输入恒 False、无证据 adopt ⇒ rc=1）我重跑均见 FAIL，审计未放宽。

**约束核验**：改动 = 5 个允许文件（`git status` 前后快照一致）；`issues.yaml` `git diff` 空（md5 `9c4e93fb…` 前后一致）；`Makefile`/`contracts/`/`.tao/adr/`/`.tao/archive/`/`spec/`/`tests/`/`components/` 零改动；未跑 L2/L3/夜跑；无临时残留（`*_tmp*`/`*.orig`/`*.rej` 扫描空）。

**非阻断说明**：① 任务书「17 条全 closed」为**事实过期**——`b9de21c3`（M10 归档，分支基点 `e6998c44` 祖先）已把 17 条冻结到 `.tao/archive/M10/issues-closed.md`（实数 17 行），活台账现 `[]`，非漏做；② `check-tasks` ① 命中本任务属**工具设计**（完成区已填 + 待验收 ⇒ 报告型提示），脚本内临时树翻 `已验证` 后 ① 归零已证；③ F1 处置（docstring 不写字面 `M1-gate`）合理，否则与验收 1 冲突。

**判决：Accepted**（9 条验收在本人重跑下全过，约束无违反；两处「任务书字面 vs 现场」已留证，`/complete` 知会即可）。
