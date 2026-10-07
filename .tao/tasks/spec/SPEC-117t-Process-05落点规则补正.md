# SPEC-117t: `Process-05 §6` 落点规则补正（`.dadao/tests/` 口径）

**模块**：spec
**项目里程碑**：M5
**依赖**：`INFRA-048t`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **背景**：`spec/Process-05-里程碑TDD规范.md §6` 现行「测试产物落点与留存」只写了「按测试本身定；模块固定路径 ⇒ 落模块目录下；否则 `.dadao/tests/`（`ADR-0016 D6`）；不强制留存」。**M5 起落点口径收紧**（用户 2026-10-06 裁定）：**默认 `.dadao/tests/`；只有"难以放进 `.dadao/`"才退到模块目录；判据 = "能否用配置选项解决"——能配置解决的一律必须放 `.dadao/`**。`INFRA-048t` 已把 `test-codegen`/`test-elf`/lit 落点迁到 `.dadao/tests/`，本任务把该口径写入规范正文，使规范与实现一致。
- **输入（自包含）**：
  - `spec/Process-05-里程碑TDD规范.md §6`（现行文本）。
  - 用户 2026-10-06 裁定原话（见 `.tao/knowledge/milestones.md`「生成物落点口径」与「落点规则生效时点」）：**默认 `.dadao/tests/`**；**判据 = 能配置解决 ⇒ 必进 `.dadao/`**；**`.work/log`/`.work/evidence` 不算"生成物"、不动**；**M4 已完成落点不动、自 M5 起按新规则**。
  - `ADR-0016 D6`（测试向量运行产物根 = `.dadao/tests/`）、`ADR-0016 D8`（真实路径）。
  - `INFRA-048t` 迁移后的实际落点（`.dadao/tests/{codegen-e2e,elf-e2e,lit-output/<name>}`）。
- **输出**：
  - `spec/Process-05-里程碑TDD规范.md §6` 修订：把「测试产物落点与留存」改写为**明确默认 + 判据**——① **默认落 `.dadao/tests/`**（`ADR-0016 D6`）；② 仅当**用配置选项**仍"难以放进 `.dadao/`"时才退到该模块目录；③ **落点路径须经 `manifests/install-dirs.lock.toml`/`tools/infra/paths.py` 解析（禁硬编码，`ADR-0016 D7/D8`）**；④ **`.work/log`/`.work/evidence` 不算"生成物"、不受本规则约束**；⑤ **M4 及以前的落点不动，自 M5 起生效**；⑥ 保留「不强制留存」。
- **约束（硬）**：
  - **只改 `Process-05 §6` 落点规则正文**，不改规范其它节语义、不改 `ADR`（ADR 只记决策）。
  - **不产向量、不改 `Makefile`/`tools/`**（落点实现归 `INFRA-048t`）。
  - `spec/` 为共享文件，与其它改 `spec/` 的任务（`SPEC-113t`~`116t`）**串行**。
  - `make check` EXIT=0；**另**单独跑 `make check-spec-refs` EXIT=0（standalone，不在 `make check` 依赖链）；`spec/README.md` 投影表如含 `Process-05` 相关行需同步（无则跳过）。
  - 失败即停、**禁自动重试**；临时目录 `/tmp/opencode/SPEC-117t/`；**不提交 git**；复杂命令输出留存 `.work/log/spec/`（**禁 `tee`**）。
  - **重建成本申报**：不触发组件重建。

## 验收标准

1. **规则落地**：`Process-05 §6` 含「默认 `.dadao/tests/` + 判据（能配置解决 ⇒ 必进 `.dadao/`）+ 经定位机制解析（`ADR-0016 D7/D8`）+ `.work/log`/`.work/evidence` 不动 + 自 M5 起」五要点（`grep`/`sed` 真实输出）。
2. **与实现一致**：§6 示例/口径与 `INFRA-048t` 迁移后的实际落点（`.dadao/tests/{codegen-e2e,elf-e2e,lit-output}`）不矛盾。
3. **门控**：`make check` EXIT=0（`repository checks: PASS`）；给真实输出。
4. **一键证据脚本**：`.work/evidence/SPEC-117t/run.sh`——非交互、失败非零、逐项打印；**内置注入自检**（删去「默认 `.dadao/tests/`」句/把判据改回旧措辞 ⇒ 断言 **FAIL** ⇒ 还原 ⇒ 回绿），结尾**禁 `tee`**；给真实输出。
5. **无残留**：`git status --untracked-files=all` 仅 `spec/Process-05-里程碑TDD规范.md`（及必要的 `spec/README.md` 投影行）+ 本任务书。

## 完成区

**测试结果**：一键证据脚本 `.work/evidence/SPEC-117t/run.sh` **18/18 PASS**（`SCRIPT_EXIT=0`）；`make check` **EXIT=0**（`repository checks: PASS`）、`make check-spec-refs` **EXIT=0**（`结果: PASS (0 violations)`）。失败原因：无。

**修改文件**：
- `spec/Process-05-里程碑TDD规范.md` —— 仅 §6「测试运行产物落点与留存」段改写（`git diff --stat` = `1 file changed, 9 insertions(+), 2 deletions(-)`）。
- `.tao/tasks/spec/SPEC-117t-Process-05落点规则补正.md` —— 完成区/审阅记录/状态。
- **未改** `spec/README.md`（投影行 L88 仍「不适用（人工遵守）」，本任务不引入新投影 ⇒ 无需同步；md5 未变）、`Makefile`、`tools/`、`.tao/adr/`（ADR 只记决策）。
- **越界披露**：无越界；`git status --porcelain -uall` 见下。

**验收结果**（真实输出摘录，完整日志 `.work/log/spec/SPEC-117t-evidence.log`、`SPEC-117t-check_post.log`）：

1. 规则落地 —— `run.sh` 逐项 PASS（`grep -F` 真实命中）：
```
[PASS] ①默认落 .dadao/tests/ | expected=present actual=present
[PASS] ②判据关键词 | expected=present actual=present
[PASS] ②能配置解决⇒必进 .dadao/ | expected=present actual=present
[PASS] ③定位机制(manifest+paths.py+D7/D8) | expected=present actual=present
[PASS] ④.work 日志/证据不受约束 | expected=present actual=present
[PASS] ⑤自 M5 起生效 | expected=present actual=present
[PASS] ⑥保留不强制留存 | expected=present actual=present
[PASS] 旧口径已移除 | expected=absent actual=absent
```
2. 与实现一致：
```
[PASS] §6 示例覆盖三处落点 | expected=codegen-e2e/elf-e2e/lit-output actual=present
[PASS] 实现落点经 paths.py 解析 | expected=5/5 命中 actual=5/5 命中
[PASS] 实际落点目录存在 | expected=3/3 actual=3/3
```
3. 门控：
```
[PASS] make check | expected=EXIT=0 actual=EXIT=0
[PASS] make check-spec-refs | expected=EXIT=0 actual=EXIT=0
```
   独立真实运行：`make check > log 2>&1; echo $?` ⇒ `CHECK_EXIT=0`；日志末行 `repository checks: PASS`。
4. 注入自检（改回旧措辞 ⇒ FAIL ⇒ 还原 ⇒ 回绿）：
```
注入前 md5 = a2f02181e6b444e9b379b59d07b9a81d
注入后 md5 = a52763b0420c6194b1f17d61539507f7
[PASS] 注入有效性(md5 变化) | expected=differs actual=differs
[PASS] 注入后判据断言 | expected=FAIL(absent) actual=FAIL(absent)
还原后 md5 = a2f02181e6b444e9b379b59d07b9a81d
[PASS] 还原 md5 对账 | expected=a2f0218... actual=a2f0218...
[PASS] 还原后判据断言回绿 | expected=present actual=present
```
   还原纪律：**`cp` 备份 + `md5sum` 对账**（备份 `/tmp/opencode/SPEC-117t/spec.Process-05.bak`），未用 `git checkout/restore/stash`；还原后 md5 与注入前逐字相等。
5. 无残留（`git -c core.quotepath=false status --porcelain -uall`）：
```
 M .tao/tasks/spec/SPEC-117t-Process-05落点规则补正.md
 M spec/Process-05-里程碑TDD规范.md
```
   （仅规范文件 + 本任务书，均在允许集内；README md5 `8c5a572b...` 与 HEAD 一致，`git diff --quiet -- spec/README.md` ⇒ UNCHANGED。）

**新发现/坑**：
- **`check-spec-refs` 是 standalone target，不在 `make check` 依赖链内**：`Makefile:297` 的 `check:` 未列它，`Makefile:335-338` 注释明示 "Standalone target, not part of `make check`"。下发预检称其「确在 `make check` 依赖链内（`Makefile:41`）」不准确（`Makefile:41` 是 `.PHONY` 清单，非依赖）。本任务**两者都单独跑**，均 EXIT=0，结论不受影响。建议后续任务书表述改为「`make check` + `make check-spec-refs`（standalone）」。
- **`git diff --name-only` 默认转义中文路径**（`core.quotepath=true`，输出八进制 `\351\207...`），脚本做路径集合比较会误判；须用 `git -c core.quotepath=false diff --name-only`。已在证据脚本中修正。
- 规范等级表述：§6 标题标 `（SHOULD）`，而本次新增的运行产物落点为 MUST 级；已在段内以 `> **规范等级**` 说明（不改标题，避免越界改 §6 之外内容）。建议沉淀为修订惯例。

**遗留问题**：无。三条自审 finding（F1–F5，见审阅记录）均已处置；`spec/README.md` 投影行经判定无需改动（并说明理由）。

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

**自审范围**：`spec/Process-05-里程碑TDD规范.md §6` 改写段（+9/−2）；`.work/evidence/SPEC-117t/run.sh`。逐行审查逻辑正确性、边界（还原路径/注入有效性）、惯用法（markdown 约定）、防造假（真实执行过）。

**判决**：实现通过（全部 finding 已处置，无未修项）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 证据脚本用 `git diff --name-only` 比较改动范围，中文路径被八进制转义致误报「越界」 | ✅已修 | `run.sh` 改 `git -c core.quotepath=false -C ... diff --name-only` | 首跑 `[FAIL] 改动范围` → 修后 `[PASS] 改动范围 ... 符合`，`SCRIPT_EXIT=0` |
| F2 「规范等级」注用任务书编号 ①②③⑥（规范正文无此编号，读者无法对应） | ✅已修 | 改为名称表述「默认落点、退让判据、定位机制为 MUST；不强制留存为 MAY」 | 改后 `sed -n '44,54p'` 复核；`make check` EXIT=0、`run.sh` 18/18 PASS |
| F3 §6 标题 `（SHOULD）` 与新增段 MUST 语气潜在不一致 | ✅缓解（不越界） | 段内加 `> **规范等级**` 说明本节 SHOULD 仅指 L1/L2/L3 示例；**未改标题**（避免改动 §6 落点段之外内容） | 段内注释可见；`make check` EXIT=0 |
| F4 下发预检「`check-spec-refs` 在 `make check` 依赖链内」与实测不符 | ❌不修（事实修正，非代码问题） | —（两者均单独运行） | `grep -n 'check-spec-refs' Makefile` = L41(.PHONY)/L83/L337；`Makefile:337` 注释 "not part of make check"；两者 EXIT=0 |
| F5 `spec/README.md` 投影表 L88（`Process-05` 行值为「不适用（人工遵守）」）是否需同步 | ❌不修（判定无需改） | 本任务不引入新投影（无 machine data/门控/oracle），该行仍成立 | `git diff --quiet -- spec/README.md` ⇒ UNCHANGED，md5 `8c5a572b...` 未变 |

**防造假自查**：证据脚本每条断言均有可达 FAIL 路径（`grep -F` 存在/不存在两支分别记 pass/fail）；注入自检含「md5 变化」有效性断言（防空注入）、「注入后 FAIL」与「还原后回绿」三项；还原用 `cp`+`md5` 对账（非 `git checkout`），md5 逐字相等。所有命令 `rc=$?` 直接判退出码，**无 `tee`**。约束自查：只改 `spec/Process-05 §6` + 本任务书；未改 `Makefile`/`tools/`/`components/`/`ADR`/`contracts/`；无新依赖；临时目录 `/tmp/opencode/SPEC-117t/`；未提交 git。

#### 第 1 轮 reviewer 验收
（审查者独立验证：`run.sh` 审核 + 重跑 + **独立注入一次反例** + 逐条核五要点 + 判决）

**A. 证据脚本审核**（`.work/evidence/SPEC-117t/run.sh`）：

逐条核可达 FAIL 路径：
- 验收 1 共 8 条断言：每条 `has()` → `pass/fail` 两支，**非恒真**。✓
- 验收 2 共 3 条断言：`IMPL_OK`/`DIR_OK` 标志变量，路径缺失即报 fail。✓
- 验收 3/3b：`rc=$?` 直接判退出码，**无 `tee`**。✓
- 改动范围：`RANGE_OK` 标志，越界文件即报 fail。✓
- 注入自检：① md5 变化断言（防空注入）② 注入后断言 FAIL ③ 还原 md5 对账 ④ 还原后回绿 —— **四项齐全**。✓
- 结尾：`exit 0`（PASS）/`exit 1`（FAIL），**无 `tee`**。✓
- 还原用 `cp` + `md5sum` 对账，**未用 `git checkout/restore/stash`**。✓
- 结论：**脚本合格，可达 FAIL 路径无恒真。**

**B. 重跑证据脚本**：

```
SPEC-117t 证据：Process-05 §6 落点规则（默认 .dadao/tests/ + 判据）
==================================================================
[PASS] ①默认落 .dadao/tests/ | expected=present actual=present
[PASS] ②判据关键词 | expected=present actual=present
[PASS] ②能配置解决⇒必进 .dadao/ | expected=present actual=present
[PASS] ③定位机制(manifest+paths.py+D7/D8) | expected=present actual=present
[PASS] ④.work 日志/证据不受约束 | expected=present actual=present
[PASS] ⑤自 M5 起生效 | expected=present actual=present
[PASS] ⑥保留不强制留存 | expected=present actual=present
[PASS] 旧口径已移除 | expected=absent actual=absent
[PASS] §6 示例覆盖三处落点 | expected=codegen-e2e/elf-e2e/lit-output actual=present
[PASS] 实现落点经 paths.py 解析 | expected=5/5 命中 actual=5/5 命中
[PASS] 实际落点目录存在 | expected=3/3 actual=3/3
[PASS] make check | expected=EXIT=0 actual=EXIT=0
[PASS] make check-spec-refs | expected=EXIT=0 actual=EXIT=0
[PASS] 改动范围 | expected=仅 spec/Process-05(+任务书) actual=符合
注入前 md5 = a2f02181e6b444e9b379b59d07b9a81d
注入后 md5 = a52763b0420c6194b1f17d61539507f7
[PASS] 注入有效性(md5 变化) | expected=differs actual=differs
[PASS] 注入后判据断言 | expected=FAIL(absent) actual=FAIL(absent)
还原后 md5 = a2f02181e6b444e9b379b59d07b9a81d
[PASS] 还原 md5 对账 | expected=a2f0218... actual=a2f0218...
[PASS] 还原后判据断言回绿 | expected=present actual=present
结果：PASS（全部检查通过，注入自检有效并已还原）
SCRIPT_EXIT=0
```

**18/18 PASS，SCRIPT_EXIT=0。**

**C. 独立注入反例**（审查者自行执行，非沿用 engineer 自检）：

注入策略：删除「默认落 `.dadao/tests/`」句（替换为「运行产物随便落（审查者注入反例）」），验证断言 ① FAIL。

```
# 注入前快照
$ git -c core.quotepath=false status --porcelain -uall
（空 — 工作区干净）
$ md5sum spec/Process-05-里程碑TDD规范.md
a2f02181e6b444e9b379b59d07b9a81d

# cp 备份
$ cp spec/Process-05-里程碑TDD规范.md /tmp/opencode/SPEC-117t-review/spec.Process-05.preinject
$ md5sum /tmp/opencode/SPEC-117t-review/spec.Process-05.preinject
a2f02181e6b444e9b379b59d07b9a81d  ← 与原文件一致

# 注入（python3 替换）
$ md5sum spec/Process-05-里程碑TDD规范.md
5003600de8a907526cb2db99fba80e39  ← 已变化

# 重跑证据脚本（注入态）
SCRIPT_EXIT=1
[FAIL] ①默认落 .dadao/tests/ | expected=present actual=missing
（其余 17 项 PASS — 注入只影响断言 ①）

# 还原
$ cp /tmp/opencode/SPEC-117t-review/spec.Process-05.preinject spec/Process-05-里程碑TDD规范.md
$ md5sum spec/Process-05-里程碑TDD规范.md
a2f02181e6b444e9b379b59d07b9a81d  ← 与注入前一致

# 重跑证据脚本（还原态）
SCRIPT_EXIT=0
18/18 PASS

# 还原后快照
$ git -c core.quotepath=false status --porcelain -uall
（空 — 工作区干净，与注入前一致）
```

注入有效性：md5 从 `a2f02181` → `5003600d`（变化）→ `a2f02181`（还原）；**未用 `git checkout/restore/stash`**，纯 `cp` 备份 + md5 对账。

**D. 逐条核验收 1–5**：

| 验收项 | 结论 | 证据 |
|--------|------|------|
| ①默认 `.dadao/tests/` | ✅ | §6 L49:「测试**运行产物默认**统一落 **`.dadao/tests/`**」 |
| ②判据「能配置解决 ⇒ 必进 `.dadao/`」 | ✅ | §6 L50:「**能配置解决的一律必须放 `.dadao/`**」 |
| ③经 `manifests/install-dirs.lock.toml`/`tools/infra/paths.py` 解析、禁硬编码 | ✅ | §6 L51:「落点路径**必须**经 `manifests/install-dirs.lock.toml`（`test_artifacts_dir`）与 `tools/infra/paths.py` 解析（`ADR-0016 D7/D8`）；Makefile 与 Python 脚本**禁止硬编码**」 |
| ④`.work/log`/`.work/evidence` 不算生成物 | ✅ | §6 L52:「二者是**日志/证据留存区，不算「生成物」**，落点**不动**」 |
| ⑤自 M5 起生效，保留「不强制留存」 | ✅ | §6 L53:「**M4 及以前**已完成/在做的测试落点**一律不动**；**自 M5 起**按本规则执行」；§6 L54:「**不强制留存**」 |

与 `INFRA-048t` 实现一致：§6 L49 举 `.dadao/tests/codegen-e2e`、`.dadao/tests/elf-e2e`、`.dadao/tests/lit-output/<name>` 为示例，与迁移后实际落点吻合。✓

门控：`make check` EXIT=0 ✓；`make check-spec-refs` EXIT=0（standalone，不在 `make check` 依赖链——经独立核实 `Makefile:337` 注释 "not part of make check"）✓。

`git status --porcelain -uall`：仅 `spec/Process-05-里程碑TDD规范.md` + 本任务书（均在允许集内）。✓

**E. 越界核验**：

`git diff e5dd38d~1..e5dd38d -- spec/Process-05-里程碑TDD规范.md` 仅一个 hunk `@@ -41,9 +41,16 @@`，完全在 §6 范围内。其它节（§1–§5、§7）语义未动。未改 `spec/README.md`、`Makefile`、`tools/`、ADR、`contracts/`。✓

**F. 规范一致性（B）**：

核 ADR-0016 D6/D7/D8 原文：
- **D6**：「测试向量运行产物根 = `.dadao/tests/`」→ §6「默认落 `.dadao/tests/`（`ADR-0016 D6`）」一致 ✓
- **D7**：「统一'定位机制'：单一真源 + 解析模块；脚本/Makefile 禁止硬编码」→ §6「落点路径必须经 `manifests/install-dirs.lock.toml` 与 `tools/infra/paths.py` 解析（`ADR-0016 D7/D8`）；禁止硬编码」一致 ✓
- **D8**：「路径规范化 = 真实路径」→ §6 引用 `D7/D8` 覆盖 ✓

§6 新措辞未引入 ADR 未定的新决策（适用范围说明、规范等级标注均为对已有 D6/D7/D8 决策的正文落地，非新决策）。✓

**判决：Accepted**

- 证据脚本 18/18 PASS，SCRIPT_EXIT=0
- 独立注入反例：删「默认落 `.dadao/tests/`」→ 断言 ① FAIL（SCRIPT_EXIT=1）→ 还原 → 回绿（18/18 PASS）
- 还原纪律：`cp` 备份 + `md5sum` 对账，未用 `git checkout/restore/stash`，注入前后快照一致
- 验收 1–5 五要点全部落纸且与实现一致
- `make check` EXIT=0 + `make check-spec-refs` EXIT=0（standalone 独立核实）
- `git diff` 仅 §6 段落，无越界
- ADR-0016 D6/D7/D8 一致性：§6 新措辞为已有决策的正文落地，无新决策

#### 下发前预检更正（主会话，2026-10-07）

主会话在下发前预检中曾**误称**「`check-spec-refs` 在 `make check` 依赖链内」，并引 `Makefile:41` 为据。实测更正如下（证据真实输出）：

- `sed -n '41p' Makefile` ⇒ `.PHONY` 清单行（`... check-spec-refs check-spec-drift ...`），为**伪目标声明**，非依赖。
- `sed -n '297p' Makefile` ⇒ `check:` 目标的依赖行**不含** `check-spec-refs`。
- `Makefile:336` 注释明示 `# Standalone target, not part of \`make check\`.`，其下 `check-spec-refs:` 为独立目标。
- 工程师实测：`make check` 与 `make check-spec-refs` **单独跑均 EXIT=0**，**结论不受影响**。

⇒ 已把「约束（硬）」中「`make check`（`check-spec-refs` 等）EXIT=0」更正为：「`make check` EXIT=0；**另**单独跑 `make check-spec-refs` EXIT=0（standalone，不在 `make check` 依赖链）」。此为**任务书事实措辞更正**，不改变任务范围与验收标准，不涉代码/产物。

#### 第 1 轮 architect 提交（WIP）

- **档位**：**WIP**（engineer 已完成并填完成区，状态 `待验收`，**reviewer 尚未验收** ⇒ 按「验收完成 ⇒ 正常提交；否则 ⇒ `WIP:`」规则取 WIP 档）。
- **提交信息**：`WIP: SPEC-117t Process-05 §6 落点规则补正（待 reviewer 验收）`。
- **staging**：显式逐路径（`git add .tao/tasks/spec/SPEC-117t-Process-05落点规则补正.md`、`git add spec/Process-05-里程碑TDD规范.md`），**未用 `git add -A`**。
- **文件集对账**（`git diff --cached --name-only` vs 完成区「修改文件」声明 + 任务范围）：
  - 声明/范围：`spec/Process-05-里程碑TDD规范.md`（仅 §6）+ 本任务书；**未改** `spec/README.md`/`Makefile`/`tools/`/`ADR`/`contracts/`。
  - 对账：**漏提 0 / 多提 0 / 越界 0**（两个待提文件均在允许集内）。
- **推送**：**只 commit、未 push**（`push` 归主会话收尾）。
- （具体提交号见回报，不写死在本记录。）

#### 第 1 轮 architect 提交（正常）

- **档位**：**正常**（reviewer 判 **Accepted** ⇒ 正常提交，不加 `WIP:`）。同时把任务书 `**状态**` 由 `待验收` 置 `已验证`（正常提交含知识沉淀）。
- **提交信息**：`SPEC-117t Process-05 §6 落点规则补正（reviewer Accepted）`。
- **staging**：显式逐路径（任务书 + `.tao/knowledge/{changelog,milestones,MEMORY}.md` + 新增 `feedback_003-*.md`），**未用 `git add -A`**。
- **文件集对账**（`git diff --cached --name-only` vs 任务书声明 + 任务范围）：
  - 规范产物 `spec/Process-05-里程碑TDD规范.md` 已在 WIP 提交 `e5dd38d` 内，本次**不重复提交**（工作树 md5 `a2f02181…` 与该提交逐字一致、无注入残留）。
  - 本次台账：本任务书（reviewer 记录 + 状态 + 本记录）、`.tao/knowledge/changelog.md`、`.tao/knowledge/milestones.md`、`.tao/knowledge/MEMORY.md`、`.tao/knowledge/feedback_003-make依赖链与PHONY清单勿混读.md`。
  - 对账：**漏提 0 / 多提 0 / 越界 0**（均在允许集内；无 `Makefile`/`tools/`/`ADR`/`contracts/` 改动）。
- **交叉复核**：reviewer 判决 **Accepted** 成立，无遗漏/过严/过松；`git diff` 仅 §6 单 hunk；`check-spec-refs` standalone 更正已如实落纸；§6 与 `ADR-0016 D6/D7/D8` 一致、无新决策。补充发现：F4/E 记 `Makefile:337` 为注释行（实为 **336**，337 为目标），仅行号偏一，不影响结论。
- （具体提交号见回报，不写死在本记录。）

#### 主会话统一验收报告（`/complete`，2026-10-07）

- **reviewer**：`Accepted`。证据脚本重跑 **18/18 PASS, SCRIPT_EXIT=0**；**独立注入**（自行删去 §6「默认统一落 `.dadao/tests/`」句）⇒ 断言① **FAIL（SCRIPT_EXIT=1）** ⇒ `cp`+`md5` 还原（`a2f02181 → 5003600d → a2f02181`）⇒ **回绿**；门控 `make check` **EXIT=0**、单独 `make check-spec-refs` **EXIT=0**。
- **architect 交叉复核**：**确认 `Accepted`**（无过严/过松/遗漏）。逐行核 `git diff` **仅 1 个 hunk**（`@@ -41,9 +41,16 @@` = §6；§1–§5、§7 语义零改动）；**独立**核实 `check-spec-refs` 为 **standalone**（`Makefile:41` = `.PHONY` 清单、`check:`(L297) 不含、L336 注释明示）；核 §6 五要点与 **`ADR-0016 D6/D7/D8`** 一致、**未引入 ADR 未定决策**。
- **预检更正（主会话错误，已如实落纸）**：我下发前预检 #3 误称「`check-spec-refs` 在 `make check` 依赖链内（引 `Makefile:41`）」——**错误**（L41 是 `.PHONY` 续行）。engineer 当场指出并实测两门控单独跑均 EXIT=0；architect 已把更正写入任务书「审阅记录」并沉淀 `feedback_003`。
- **共识**：§6「测试产物落点与留存」已改为**默认 `.dadao/tests/` + 判据「能配置解决 ⇒ 必进 `.dadao/`」+ 经 `paths.py`/lock 解析（禁硬编码）+ `.work/log`/`.work/evidence` 不受约束 + 自 M5 起生效 + 保留「不强制留存」**，与 `INFRA-048t` 实现落点一致。
- **补充发现（微，不影响判决）**：architect/reviewer 记录中 `Makefile:337` 应为 **L336**（注释行；行号偏一）。
- **收尾检查**：`spec/` 改动在 `make check` 覆盖内 ⇒ 门控全绿（reviewer 重跑，`EXIT=0`）；台账/任务书为纯文档（豁免）；`git status --porcelain -uall` 干净；证据留 `.work/evidence/SPEC-117t/`、`.work/log/spec/`（非 `/tmp`）。
- **最终判决**：**`Accepted`** ⇒ 任务书 `**状态**` = `已验证`。
