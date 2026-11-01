# INFRA-113t: 里程碑绑定清理（退役 `M1-gate` 判据 + 清 ADR-0030/M9 过时基准）

**模块**：infra
**项目里程碑**：M10 后（清理，不纳入 M10 收尾）
**依赖**：无
**状态**：待开始

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

- **目标已是 binary128**：`components/musl/patches/arch/dadao/bits/float.h.patch:32` ⇒ `#define LDBL_MANT_DIG 113`；工作树 `.work/source/musl/arch/dadao/bits/float.h:26` 同值。
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
- 定向跑前置齐备：`.dadao/cross-toolchain/bin/clang`、`.work/build/qemu/qemu-dadao`、`.work/source/musl/lib/libc.a`（mtime `2026-11-01 03:48` **晚于** `float.h` 的 `2026-10-24 15:47` ⇒ 该 `libc.a` 已含 binary128）、语料 `libc-test`（`.work/` 下 `libc-test` 语料树）。
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
  --json-out /tmp/opencode/INFRA-113t/math-static.json
```

dynamic 档同法换 `--link-mode dynamic` 与文件名。判据：`pass=5 且 fail=0 且 known-fail=0 且 blocked=0` ⇒ 走**删除**分支；否则走**重算**分支（完成区注明每条真实分类）。

## 约束

- 只改：`tools/infra/check_issues.py`、`docs/Process-04-里程碑归档规范.md`、`tools/testcases/tset/libc-test/run_libc_test_user_suite.py`、`.tao/knowledge/milestones.md`、本任务书；证据落 `.work/evidence/<任务ID>/`（`<>` 占位，不写具体文件名）。
- 禁改：`.tao/archive/**`（历史 `M1-gate` 命中**保留**）、`.tao/knowledge/issues.yaml` 条目内容、`contracts/**`（尤其 `opcodes.yaml` 的 `scope: m1` 基础 ISA 身份集）、`.tao/contracts/**`、`.tao/adr/**`（`adr-0030` 正文不改）、`components/**`、`spec/`、`tests/`、`Makefile`。
- 不改 M3 / M4 / M5 / M6 仍有效的回归门控名称，也不动 `scope: m1`（基础 ISA）与 `scope: fp` / `m9` 口径。
- 不跑 `make check-full` / `check-night` / `check-modules` / tset smoke/full（L2/L3 与夜跑不在本任务面）；`make check` **只在验收时**跑一次（并允许因锁分两次）。
- 反例注入**禁** `git checkout` / `restore` / `stash` 还原：`issues.yaml` 用 `cp` 备份 + md5 对账；runner 用 `/tmp` 副本树。
- 临时目录 `/tmp/opencode/INFRA-113t/`；仓库内不得留探针/临时文件。

## 验收标准

1. **A·在役面零残留**：`git grep -n 'M1-gate' -- tools docs .tao/knowledge .tao/contracts Makefile` ⇒ **0 行**（rc=1）。
   - 说明：`.tao/archive/**`（历史册）与 `.tao/tasks/**`（任务记录，含本任务书）**不计**——本任务书自身必然出现该词。附证：`git grep -c 'M1-gate' -- .tao/archive | wc -l` > 0（历史保留，贴计数）。
2. **A·字段约束仍生效**：`python3 tools/infra/check_issues.py` ⇒ **rc=0**；输出**不含** `M1-gate`；仍打印 `resolved_by 约束 OK (… 17 closed → 非空 / 0 open → null)` 与计数行。
3. **A·反例可达 FAIL**（`cp` 备份 + md5 对账，禁 git 还原）：
   - 注入 `status: closed` 且 `resolved_by: null` ⇒ **rc=1** 且点名该 id；
   - 注入 `status: open` + `blocks: [M1-gate]` ⇒ **rc=0**（证明阻断已退役、`blocks` 不参与判定）——这一条是「退役」的正向证据，须与上一条同时贴；
   - `cp` 还原后 `md5sum` 与注入前一致，`git status --porcelain -uall` 只剩本任务允许的改动。
4. **B·判定留证**：两档 JSON 落 `/tmp/opencode/INFRA-113t/`；贴 `pass / fail / known-fail / blocked` 计数 + 5 例逐条状态。
5. **B·零残留**：对 `run_libc_test_user_suite.py`：`grep -n 'ADR-0030\|adr0030\|LDBL_MANT_DIG=53'` ⇒ **0 行**；`grep -n 'M9'` ⇒ **0 行**。（走「重算」分支时改为：无 `53`、无 `M9`，且 basis 明写 113。）
6. **B·反例可达 FAIL（审计不放宽）**：在 `/tmp` **副本树**里把 `ISS251_ID` 的 `KNOWN_FAIL_BASES` 指向恒 False 的 evidence，跑 `--filter '^functional/strptime$'` ⇒ 审计段 rc≠0 并报未归因失败（`unexplained_fail` / `bad_known`）；仓库内原文件 md5 前后一致（零改动）。
7. **L1**：`make check` ⇒ **rc=0**（含 `repository checks (L1): PASS`）。
   - 若 `gate.lock` 被夜跑占用：先取 2/4/5/6 的直调证据，锁空后**补跑**并贴真实 rc；**rc=75（锁等待超时）不作通过证据**，也不得记为 PASS。
8. **体例**：`make check-tasks`（报告型）rc=0 且本任务不在「漏收尾」主表；`make check-milestones-fresh` ⇒ **rc=0**（表首行状态/格式/倒序一致）。本任务书完成区 ≤30 行。
9. **证据脚本**：`.work/evidence/<任务ID>/` 下一键脚本跑通（`checks=N failures=0`，脚本自身 rc 落证据），每条断言有**可达 FAIL** 路径（禁恒真）。

## 文件范围（摘要）

- 允许：`tools/infra/check_issues.py`、`docs/Process-04-里程碑归档规范.md`、`tools/testcases/tset/libc-test/run_libc_test_user_suite.py`、`.tao/knowledge/milestones.md`、`.tao/tasks/infra/INFRA-113t-*.md`、`.work/evidence/<任务ID>/`。
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

**测试结果**：（待填写）
**修改文件**：（待填写）
**验收结果**：（待填写）
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审

（待填）

#### 第 1 轮 reviewer 验收

（待填）
