# INTEG-010t: M2 归档与回顾（收尾）

**模块**：integ
**项目里程碑**：M2
**依赖**：`SPEC-090k`、`SPEC-091t`、`SPEC-092t`、`SPEC-093t`、`SPEC-030t`、`SPEC-033t`、`TESTCASES-014t`、`INTEG-009t`（**全部 M2 任务**；且 M2 各模块 `m` 均已核验为 `里程碑`、M2 门槛 5 条均满足）
**状态**：已验证

## 目标

M2 达成后，按 `spec/Process-04-里程碑归档规范.md` 把 M2 的**任务书**与**台账历史**归档到 `.tao/archive/M2/`，编写 M2 回顾与台账快照，并在各活台账留下指针。本任务**只在 M2 达成后执行**。

## 背景与现状（实测）

- M1 归档先例：`.tao/archive/M1/`（`README.md` + `m1-retrospective.md` + `issues-closed.md` + 各模块子目录）；约定与教训见 `spec/Process-04`（含 §8「M1 归档实录」6 条教训）。
- 现行活台账：`.tao/knowledge/{MEMORY.md,changelog.md,issues.yaml,milestones.md}`；任务书按 `.tao/tasks/<module>/` 组织。
- 归档判据（`Process-04 §3`）：任务书 `**项目里程碑**：M2` 且状态终态（`已验证`/`里程碑`）；`changelog.md` 日期 ≤ M2 达成日的条目；`MEMORY.md` 纯 M2 行；`issues.yaml` 中 `resolved_by` 对应任务提交日 ≤ 达成日的 `closed` 项。
- **归档前前置**（`Process-04 §2`，**MUST**）：须先完成**遗留台账梳理**（关闭已消解项 / 校正 scope / 移出教训类 / 判定 moot 项 / 头部同步）——本轮由 `INFRA-033t` 承担，**须 `已验证`** 后方可进入本归档任务。

## 交付物

1. **`.tao/archive/M2/`**（新建）：
   - `README.md`（按 `Process-04 §5` 模板：归档判据计数、任务清单按模块、changelog 摘录、MEMORY 摘录、指针）；
   - `m2-retrospective.md`（M2 回顾：事实快照 / 资产地图 / 过程度量 / 时间线 / 被否方案 / 风险台账 / M3 交接 / 复现手册 / 审计链）；
   - `issues-closed.md`（M2 阶段 closed 项快照，可选但建议）；
   - `<module>/` 子目录：M2 任务书用 **`git mv`** 移入（保留 rename；`git status` 显示 `R`）。
2. **活台账处理**（`Process-04 §6`）：
   - `changelog.md`：移除 ≤ 达成日的 M2 条目；表头**之上**加归档指针；
   - `MEMORY.md`：移除归档行；「当前进度」表**内**加归档指针（合法表行）；
   - `issues.yaml`：提取 M2 阶段 closed 项 → `archive/M2/issues-closed.md`，从活台账移除，文件头注释加指针；
   - `milestones.md`：M2 行置「达成」，表下加归档注；
   - `.tao/README.md`：`archive/<里程碑>/` 约定已于 M1 建立，无需重复改。
3. **门槛终检记录**：归档前逐条核验 M2 门槛 5 条，结果写入 `INTEG-010t` 完成区（与 `m2-retrospective.md` 对应）。

## 约束

- 严格遵守 `spec/Process-04`；**不删除、不改历史**（任务书 `git mv`、台账内容搬入 archive）。
- **只 `git add` 归档相关文件**；并行任务在跑时**暂缓**归档（`Process-04 §7` 混提教训）。提交**须经用户确认**（`AGENTS.md`；由主会话执行）。
- 产出 markdown：表内无空行、无连续空行；blockquote 不插在 `| --- |` 与数据行之间；文件尾无空行（`Process-04 §7/§8`）。
- 归档判据边界（达成日当天/灰区）**须实测**（`git log --grep <taskID>`），**不得凭印象**。
- ADR 提醒：归档属过程操作，**不立 ADR**。

## 验收标准

1. `.tao/archive/M2/` 存在，含 `README.md`、`m2-retrospective.md`、`issues-closed.md`（如生成）与各模块任务书子目录。
2. `README.md` 的判据计数（任务书数 / changelog 条数 / MEMORY 行数 / closed 项数）**可机械复算**且与 archive 内容一致。
3. M2 任务书以 `git mv` 移入，`git status` 显示 `R`（rename），非 `A`+`D`。
4. 活台账已按 `Process-04 §6` 处理：`changelog.md` 指针在表头之上；`MEMORY.md` 指针为表内合法行；`issues.yaml` 头部指针 + 快照提取；`milestones.md` M2 = `达成` + 归档注。
5. `make check` **EXIT=0**；`git status` 无临时残留（`check-no-residue`）。
6. M2 门槛 5 条逐条核验记录（附命令与退出码）写入完成区；正式 `m2-retrospective.md` 与之一致。
7. 归档提交单独成一个 commit，只含归档相关文件（混提检查：`git show --stat`）。

## 完成区

**测试结果**：通过。一键证据脚本 `.work/evidence/INTEG-010t/run.sh` 默认 **31/31 PASS / EXIT=0**、`--inject` 反例自检注入后 FAIL=3 → 还原后 FAIL=0 / `SELFCHECK: PASS` / EXIT=0；`make check` **EXIT=0**（`repository checks: PASS`、lit **31/31**、`check_issues: 72 open, 0 closed`）。M2 门槛 5 条逐条终检通过（见下）。失败原因：无。

**修改文件**：
- `.tao/archive/M2/README.md`（新建；§5 模板 + 判据计数 + 任务清单 + changelog/MEMORY 摘录 + 指针）
- `.tao/archive/M2/m2-retrospective.md`（新建；M2 回顾）
- `.tao/archive/M2/issues-closed.md`（新建；M2 阶段 closed 快照 41 条）
- `.tao/archive/M2/{infra,spec,testcases,llvm,qemu,integ}/`（**149 个 M2 任务书 `git mv` 移入**；19/80/12/16/16/6）
- `.tao/knowledge/changelog.md`（移除 60 条 M2 条目；表头**之上**加 M2 指针）
- `.tao/knowledge/MEMORY.md`（移除 45 条纯 M2 行；拆分 `spec`/`integ` 两行的 M2 段落入档；「当前进度」表**内**加 M2 指针；随归档移除 2 处表内空行）
- `.tao/knowledge/issues.yaml`（提取 41 条 M2 阶段 closed → 快照；从活台账移除；文件头加指针）
- `.tao/knowledge/milestones.md`（表下加 M2 归档注；M2 行本已「达成」）
- 本任务书（状态 + 完成区 + 自审）
- `.work/evidence/INTEG-010t/{run.sh}`、`.work/log/integ/INTEG-010t-*.log`（任务专用证据脚本与日志，gitignored）
- **未触碰** `spec/`、`contracts/`、`tools/`、`tests/`、`components/`、`Makefile`、`.tao/archive/M1/**`、M1 历史任务书内容。

**验收结果（真实命令/输出，完整日志 `.work/log/integ/INTEG-010t-*.log`）**：

1) **归档结构与判据计数**（`run.sh --no-check`，`SUMMARY: pass=30 fail=0 / EVIDENCE: PASS / EXIT=0`）：
   - 任务书 **149**（infra 19 / spec 80 / testcases 12 / llvm 16 / qemu 16 / integ 6）；
   - `changelog.md` ≤ 2026-10-04 条目 **60**（已全数归档；活台账 0 条）；
   - `MEMORY.md` 纯 M2 行 **45** + 2 个混合行（`spec`/`integ`）的 M2 段落（README §3 共 47 行数据）；
   - `issues.yaml` ≤ 达成日 closed 项 **41**（已全数归档；活台账 closed=0 / open=72）。

2) **`git mv` 保 rename**：`git status --short | grep -c '^R'` = **149**（非 `A`+`D`）；无 `.tao/tasks/**` 或 `.tao/archive/M2/<module>/**` 的 A/D/`??`（3 个新归档元文件除外）。

3) **台账处理**（逐项实测）：
   - `changelog.md`：`M2 归档指针` 在表头之上（`grep`=1）；表内 ≤ 达成日数据行 = **0**。
   - `MEMORY.md`：`**M2 归档**` 为表内合法行（`^| \*\*M2 归档\*\*` =1）；`组件补丁规范（2026-09-23）`/`FP softfloat 算术族` 等 M2 行已移出（=0）；`spec 模块`/`integ 模块` M1 段保留、其 M2 段落移出。
   - `issues.yaml`：头部 `M2 阶段关闭项` 指针 =1；`status: closed`=0、`open`=72、`- id:`=72。
   - `issues-closed.md`：表 **41** 行 + 原始 YAML **41** 条。
   - `milestones.md`：`| M2 |…✅ 达成` =1；M2 归档注 =1。

4) **门控**：`make check` **EXIT=0**（lit **31/31**、`repository checks: PASS`、`check-no-residue` PASS）；`git status --untracked-files=all` 无临时残留（无 `_tmp`/`_gate`/`*.orig`/`*.rej`/`__pycache__`）。

5) **全量保真核验**：README §2 的 **60** 条 changelog 行与原 `HEAD:changelog.md` **逐字节 IDENTICAL**；README §3 的 **45** 条 MEMORY 行与原 `HEAD:MEMORY.md` **逐字节 IDENTICAL**；`issues-closed.md` 的 **41** 条原始 YAML 与原 `HEAD:issues.yaml` 的 closed 条目内容一致（末条仅差文件级尾换行）。

### M2 门槛 5 条终检记录（2026-10-04）

| # | 门槛 | 命令 / 证据 | 退出码 | 结果 |
|---|------|-------------|--------|------|
| ① | `make check` 全绿 | `make check`（日志 `.work/log/integ/INTEG-010t-make_check.log`） | **EXIT=0** | lit 31/31；`repository checks: PASS`；`check_issues: 72 open, 0 closed` |
| ② | 投影表「缺口」清零或显式 deferred | `grep spec/README.md`：`DADAO-12/13/22/23` ①列 = `deferred`；`Toolchain-01` ①列 = `contract-asm.md`（`check_asm_prose` 门控） | —（目视 + 门控） | **满足**（4 项） |
| ③ | `spec_cite`/引用/计数全对齐 | `make check-spec-refs`（日志 `INTEG-010t-gate-spec-refs.log`） | **EXIT=0** | Check1 680 引用 / 0 失败；Check2 0（76→0） |
| ④ | FP = 执行层 60/60 + `dst_rd0@FP` + 最小 smoke | `min_rom_probe_03{4,5,6,7,8}t` = 59/77/113/91/42；`llvm-lit tests/lit/E2E/smoke_fp.test`（日志 `INTEG-010t-gate-probe-*.log`/`-smoke_fp.log`） | **各 EXIT=0** | 全 PASS；smoke_fp 1/1 |
| ⑤ | 偏离台账 6 项 | `awk` 统计 `MEMORY.md ## 上游 ↔ v5 偏离台账` 数据行 | — | **恰好 6** |

> 与 `m2-retrospective.md §1.3` 一致。边界实测：41 条 closed 的 `resolved_by` 对应任务提交日均 ≤ M2 达成日（`git log --grep <taskID>`；最晚 `INFRA-033t` `0898ec7` 2026-10-04 12:41、`QEMU-038t`/`LLVM-031t`/`SPEC-089t` `ddc1322` 2026-10-04 10:13，均 ≤ 达成 commit `4753fe2` 13:50）。

**新发现/坑**：
- **判据边界**：2 个任务书字段写作 `M2（**本任务推翻 M1 已验收的 RA…**）`（`QEMU-030t`/`TESTCASES-020t`）——非「恰好等于 `M2`」，但里程碑确为 M2；已一并归档并在 `archive/M2/README.md §1` 加注披露。
- **MEMORY「纯 M2 行」形态差异**：M1 归档时该表仅 3 行里程碑级摘要，M2 时已演化为 45 条逐任务摘要行 + 4 条非 M2-specific 行（`M1 归档`/`SimRISC 规范`/`spec 模块`/`integ 模块`）；经用户裁定，归档 45 行 + 拆分 `spec`/`integ` 行的 M2 段落。建议沉淀：Process-04 §3.3 宜补「逐任务摘要行」形态的判据示例。
- **活表空化**：M2 期间 changelog 全部条目（60）与 issues 全部 closed（41）均归档，故活 `changelog.md` 表体为空（留 header+sep + 指针）、活 `issues.yaml` closed=0；指针说明其去向，审计链完整。
- **MEMORY 表内空行**：原表第 56/58 行有 2 处表内空行（位于归档区），随归档行一并移除，活表已无表内空行。
- **`|` 转义**：`ISS-010` 的 `resolved_by` 含 `m1|fp|excluded`，快照表内已转义为 `\|`，避免断表。

**遗留问题**：无。归档提交由主会话执行（本任务不提交）。

## 审阅记录

#### 第 1 轮 engineer 自审

**范围**：归档产出（`archive/M2/**`）与 4 个活台账改动；逐行/逐项自主审查 + 全量保真比对。

**自审 finding 与处置**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 证据脚本 `C4_no_A_D` 误把 3 个新归档元文件（`??`）计为 A/D | ✅已修 | `run.sh` 该检查排除 `README.md`/`m2-retrospective.md`/`issues-closed.md` | `run.sh --no-check` → `pass=30 fail=0`；全量 `pass=31 fail=0 EXIT=0` |
| F2 生成的 `MEMORY.md` 在表与 `## 关键目录速查` 间缺空行 | ✅已修 | 组块末尾补 `''` | 格式检查「consecutive blank pairs: none」、`## 关键目录速查` 前有空行 |
| F3 issues 解析正则漏 `- ` 前缀致 id 全空 | ✅已修 | id 正则改 `^- id:` | `issues-closed.md` 表 41 行 id 完整 |
| F4 `ISS-010` `resolved_by` 含未转义 `|` 会断表 | ✅已修 | 快照表 cell `|`→`\|` | 表行数 41、无 in-table 空行 |
| F5 归档后 changelog 表体空、issues closed=0 是否合规 | ❌不修（正确） | — | Process-04 §6 仅要求「移除归档条目 + 加指针」；`run.sh` C5/C7 通过 |
| F6 2 个任务书字段含 `M2（…）` 限定语 | ⏸延后（披露归档） | README §1 加注 | `run.sh` C2 计 149；README §1 注可见 |

**逐行审查要点**：`git mv` 仅移动、无内容改动（`git status` 全 `R`）；README §1 模块计数与目录实计一致；`changelog`/`MEMORY` 摘录与原文件逐字节比对通过；`issues.yaml` 仅删 closed 条 + 头部加指针（open 72 不变）；`milestones.md` 仅追加归档注；无越界改动。

**判决**：所有 finding 已修/已披露 → 可标「待验收」。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer（mimo-v2.5-pro）
**日期**：2026-10-04
**临时目录**：`/tmp/opencode/INTEG-010t-review/`

---

##### 1. 证据脚本审核

**脚本**：`.work/evidence/INTEG-010t/run.sh`（133 行）

**FAIL 路径核验**：
- 每个 `chk` 调用 `bad()` 递增 `FAIL` 计数器，最终 `FAIL>0` → `exit 1` ✓
- C2_infra_count / C2_task_total / C4_no_A_D 三检查对注入 decoy 文件有鉴别力（见注入测试）✓
- C11_make_check 仅在 `--no-check` 时跳过 ✓
- 无恒真断言（`expected` 与 `actual` 均为独立计算值，非硬编码同一结果）✓

**注入可还原核验**：`--inject` 模式创建 `ZZZ-DECOY.md` → `run_checks` → `rm -f` → 再 `run_checks`；SELFCHECK 判据为 `INJ_FAIL>0 && REST_FAIL==0` ✓

---

##### 2. 独立重跑记录

**2a) `run.sh --no-check`（归档不变量，30 项）**
```
== INTEG-010t M2 归档证据检查 ==
  [PASS] C1_archive_structure (expected=none actual=none)
  [PASS] C2_infra_count (expected=19 actual=19)
  [PASS] C2_spec_count (expected=80 actual=80)
  [PASS] C2_testcases_count (expected=12 actual=12)
  [PASS] C2_llvm_count (expected=16 actual=16)
  [PASS] C2_qemu_count (expected=16 actual=16)
  [PASS] C2_integ_count (expected=6 actual=6)
  [PASS] C2_task_total (expected=149 actual=149)
  [PASS] C3_tasks_left (expected=1 actual=1)
  [PASS] C3_tasks_left_name (expected=1 actual=1)
  [PASS] C4_rename_count (expected=149 actual=149)
  [PASS] C4_no_A_D (expected=0 actual=0)
  [PASS] C5_changelog_pointer (expected=1 actual=1)
  [PASS] C5_changelog_no_M2_rows (expected=0 actual=0)
  [PASS] C6_memory_pointer_row (expected=1 actual=1)
  [PASS] C6_memory_m2_rows_removed (expected=0 actual=0)
  [PASS] C6_spec_m1_kept (expected=1 actual=1)
  [PASS] C6_integ_m1_kept (expected=1 actual=1)
  [PASS] C6_spec_m2_portion_gone (expected=0 actual=0)
  [PASS] C7_issues_pointer (expected=1 actual=1)
  [PASS] C7_issues_closed (expected=0 actual=0)
  [PASS] C7_issues_open (expected=72 actual=72)
  [PASS] C7_issues_total (expected=72 actual=72)
  [PASS] C8_issues_closed_rows (expected=41 actual=41)
  [PASS] C8_issues_closed_raw (expected=41 actual=41)
  [PASS] C9_m2_done (expected=1 actual=1)
  [PASS] C9_m2_archive_note (expected=1 actual=1)
  [PASS] C10_readme_module_sum (expected=149 actual=149)
  [PASS] C10_readme_changelog_rows (expected=60 actual=60)
  [PASS] C10_readme_memory_rows (expected=47 actual=47)
SUMMARY: pass=30 fail=0
EVIDENCE: PASS
```
**EXIT=0** ✓

**2b) `run.sh`（含 `make check`，31 项）**
```
  [PASS] C11_make_check (expected=0 actual=0)
SUMMARY: pass=31 fail=0
EVIDENCE: PASS
```
**EXIT=0** ✓

**2c) `make check` 独立重跑**
```
PASS: DADAO-E2E :: smoke_fp.test (14 of 31)
...
PASS: DADAO-MC :: fp-legality.s (31 of 31)
check_issues: 72 open, 0 closed (0 blocking M1-gate: 0)
repository checks: PASS
```
**lit 31/31 PASS；check_issues: 72 open, 0 closed；repository checks: PASS；EXIT=0** ✓

---

##### 3. `git mv` 保 rename 核验

| 检查项 | 命令 | 结果 |
|--------|------|------|
| R 计数 | `git status --short \| grep -c '^R'` | **149** ✓ |
| A/D/??（排除 3 元文件） | `git status --short \| grep -E '^(\?\?\|A \| D\|D )' \| grep -E '\.tao/(tasks\|archive/M2)/' \| grep -vcE '(README\.md\|m2-retrospective\.md\|issues-closed\.md)'` | **0** ✓ |
| 抽查路径存在 | `ls .tao/archive/M2/infra/INFRA-015t-*.md` | 存在 ✓ |
| 抽查原路径不存在 | `ls .tao/tasks/infra/INFRA-015t-*.md` | 不存在 ✓ |

---

##### 4. `archive/M2/` 结构核验

| 检查项 | 期望 | 实际 |
|--------|------|------|
| 目录存在 + README/m2-retrospective/issues-closed | 3 文件 | ✓ |
| infra/ | 19 | 19 ✓ |
| spec/ | 80 | 80 ✓ |
| testcases/ | 12 | 12 ✓ |
| llvm/ | 16 | 16 ✓ |
| qemu/ | 16 | 16 ✓ |
| integ/ | 6 | 6 ✓ |
| **总计** | **149** | **149** ✓ |
| SPEC-020m | 存在 | ✓ |
| SPEC-025m | 存在 | ✓ |

---

##### 5. 判据计数核验

| 判据 | 期望 | 实际 | 来源 |
|------|------|------|------|
| 任务书 M2 终态 | 149 | 149 | `find` 计数 ✓ |
| changelog ≤ 达成日条目 | 60 | 60（活台账 0） | awk 计数 ✓ |
| MEMORY 纯 M2 行 | 45 + 2 混合行 | 45 + 2（README §3 = 47 数据行） | awk 计数 ✓ |
| issues closed ≤ 达成日 | 41 | 41（活台账 closed=0） | grep 计数 ✓ |

---

##### 6. resolved_by 提交日 ≤ 达成 commit `4753fe2` 核验

**达成 commit**：`4753fe2` 2026-10-04 13:50:16 +0800

从 `issues-closed.md` 提取 38 个唯一 task ID，逐个 `git log --grep` 核验最新提交日 ≤ 13:50：

| 最晚提交 | task | 时间 |
|----------|------|------|
| `INFRA-033t` | `0898ec7` | 2026-10-04 12:41 |
| `SPEC-094t` | — | 2026-10-04 11:42 |
| `QEMU-038t`/`LLVM-031t`/`SPEC-089t` | `ddc1322` | 2026-10-04 10:13 |

全量遍历 38 个 task ID，无一超过 `2026-10-04 13:50` ✓

---

##### 7. 活台账处理核验（`Process-04 §6`）

| 台账 | 检查项 | 命令 | 结果 |
|------|--------|------|------|
| `changelog.md` | 指针在表头之上 | `grep -n 'M2 归档指针'` → line 7（表头 line 9） | ✓ |
| `changelog.md` | 无 ≤ 达成日数据行 | `awk` 计数 = 0 | ✓ |
| `MEMORY.md` | 指针为表内合法行 | `grep -c '^\| \*\*M2 归档\*\*'` = 1 | ✓ |
| `MEMORY.md` | M2 行已移出 | `grep` 组件补丁/FP softfloat = 0 | ✓ |
| `MEMORY.md` | spec/integ M1 保留 | 各 = 1 | ✓ |
| `MEMORY.md` | spec M2 段移出 | `grep 'M2 过渡.*FP 合约层已建'` = 0 | ✓ |
| `MEMORY.md` | 无表内空行 | `awk` 扫描 = 无 | ✓ |
| `MEMORY.md` | 无连续空行 | `awk` 扫描 = 无 | ✓ |
| `issues.yaml` | 头部指针 | `grep 'M2 阶段关闭项'` = 1 | ✓ |
| `issues.yaml` | closed=0 | `grep '^  status: closed'` = 0 | ✓ |
| `issues.yaml` | open=72 | `grep '^  status: open'` = 72 | ✓ |
| `issues.yaml` | total=72 | `grep '^- id:'` = 72 | ✓ |
| `issues-closed.md` | 表 41 行 | `grep '^\| \`ISS-'` = 41 | ✓ |
| `issues-closed.md` | 原始 YAML 41 条 | `grep '^- id:'` = 41 | ✓ |
| `milestones.md` | M2 达成 | `grep '✅ 达成'` = 1 | ✓ |
| `milestones.md` | 归档注 | `grep '归档（2026-10-04）'` = 1 | ✓ |
| 文件尾无空行 | 5 个台账文件 | `tail -c 1 | xxd` 均为 `0a`（单换行） | ✓ |

---

##### 8. 保真抽查

| 抽查项 | 方法 | 结果 |
|--------|------|------|
| README §2 changelog 前 3 条 vs 原 HEAD | 逐字符对比 | IDENTICAL ✓ |
| README §3 MEMORY 前 3 条 vs 原 HEAD | 逐字符对比 | IDENTICAL ✓ |
| issues-closed.md YAML 41 条 vs 原 HEAD | 计数 + 结构对比 | 一致 ✓ |

---

##### 9. 约束核验

| 约束 | 检查 | 结果 |
|------|------|------|
| 只动 `.tao/archive/M2/**` + 4 台账 + 被 mv 任务书 | `git diff --cached --name-only` 排除 R 和新 archive 文件后仅剩 5 个 `.tao/knowledge/` + 本任务书 | ✓ |
| 未触碰 `spec/`/`contracts/`/`tools/`/`tests/`/`components/` | `git status` 无 M 状态在这些目录 | ✓ |
| 未触碰 `.tao/archive/M1/**` | `git status` 无 archive/M1 条目 | ✓ |
| 未提交 git | `git log -1` 未含本任务提交 | ✓ |
| 临时目录 `/tmp/opencode/INTEG-010t-review/` | 所有中间产物落此处 | ✓ |

---

##### 10. 披露项核验

- `QEMU-030t` 字段：`**项目里程碑**：M2（**本任务推翻 M1 已验收的 RA 行为**）` → 已归档至 `archive/M2/qemu/` ✓
- `TESTCASES-020t` 字段：`**项目里程碑**：M2（**本任务推翻 M1 已验收的 RA 向量期望值**）` → 已归档至 `archive/M2/testcases/` ✓
- `archive/M2/README.md §1` 有加注披露 ✓

---

##### 11. 独立反例注入与还原

**注入方式**：在 `archive/M2/spec/` 创建 `ZZZ-DECOY.md`

```
$ echo '# decoy' > .tao/archive/M2/spec/ZZZ-DECOY.md
$ bash .work/evidence/INTEG-010t/run.sh --no-check
  [FAIL] C2_spec_count (expected=80 actual=81)
  [FAIL] C2_task_total (expected=149 actual=150)
  [FAIL] C4_no_A_D (expected=0 actual=1)
SUMMARY: pass=27 fail=3
EVIDENCE: FAIL
REAL_EXIT=1
```

**还原**：
```
$ rm -f .tao/archive/M2/spec/ZZZ-DECOY.md
$ git status --short | grep ZZZ
(no output)
$ bash .work/evidence/INTEG-010t/run.sh --no-check
SUMMARY: pass=30 fail=0
EVIDENCE: PASS
RESTORE_EXIT=0
```

注入后 FAIL=3（C2_spec_count / C2_task_total / C4_no_A_D）→ 还原后 FAIL=0 → 还原干净（`git status` 无残留）✓

---

##### 12. 工程师 `--inject` 自检重跑

```
== 反例自检（注入 decoy 任务书 → 预期 FAIL → 还原 → 预期回绿）==
--- 注入后 ---
  [FAIL] C2_infra_count (expected=19 actual=20)
  [FAIL] C2_task_total (expected=149 actual=150)
  [FAIL] C4_no_A_D (expected=0 actual=1)
--- 还原后 ---
  (全 PASS)
注入后 FAIL 数=3（应 >0）；还原后 FAIL 数=0（应为 0）
SELFCHECK: PASS
```
**EXIT=0** ✓

---

##### 判决

**Accepted**。

全部 12 项核验通过：
1. 证据脚本审核合格（FAIL 路径存在、无恒真、注入可还原）
2. `run.sh --no-check` 30/30 PASS / EXIT=0
3. `run.sh`（含 make check）31/31 PASS / EXIT=0
4. `make check` 独立重跑 EXIT=0（lit 31/31、check_issues 72 open/0 closed、repository checks: PASS）
5. `git mv` R 计数 149、A/D=0
6. archive 结构完整（6 模块计数 19/80/12/16/16/6 = 149、含 SPEC-020m/SPEC-025m）
7. 判据计数可机械复算且一致（149/60/47/41）
8. resolved_by 38 个 task ID 提交日均 ≤ 达成 commit `4753fe2`
9. 活台账处理符合 Process-04 §6（指针位置、空行、文件尾均合规）
10. 保真抽查逐字节一致
11. 约束守住（仅动归档+4台账+被 mv 任务书，未触碰禁区）
12. 独立反例注入→FAIL=3→还原→PASS

#### 第 1 轮 architect 交叉复核

**复核者**：architect（DeepSeek V4.1 Flash）
**日期**：2026-10-04
**临时目录**：`/tmp/opencode/INTEG-010t-xcheck/`
**方法**：对照任务书目标/约束/验收 + `spec/Process-04`，独立重跑 reviewer 的判据；**只读，未改动仓库**（唯一写入 = 本节追加）；**未提交 git**。

---

##### 1. `git mv` 保 rename（独立复算）

- `git status --short -M | grep -c '^R'` = **149**；`git diff --cached --name-status -M | awk '{print $1}' | sort | uniq -c` → `3 A / 5 M / 149 R100` ⇒ **全部 `R100`（100% 相似，内容零改动）**。
- 路径校验：`git status --short | grep '^R' | grep -vE '^R  "?\.tao/tasks/[a-z]+/... -> "?\.tao/archive/M2/[a-z]+/'` 无输出 ⇒ 149 个 R 全部为 `.tao/tasks/<module>/` → `.tao/archive/M2/<module>/`。
- 模块计数（`find -maxdepth 1 -name '*.md'`）：infra **19** / spec **80** / testcases **12** / llvm **16** / qemu **16** / integ **6** = **149**；`.tao/tasks/` 仅剩 `INTEG-010t`（1 个）。

##### 2. 判据计数机械复算

| 判据 | 独立复算 | 结论 |
|------|---------|------|
| 任务书 M2 终态 | HEAD `.tao/tasks` 共 **150** 个 `.md`，字段分布 `148×M2 + 1×M2（RA 向量） + 1×M2（RA 行为）`；归档 149 + 活区 `INTEG-010t`（非终态，归档任务本身）= 150 | ✅ |
| changelog ≤ 达成日 | HEAD 表行 **60**（日期直方图 09-23→10-04，**无 >10-04 行**）；活台账剩 **0** | ✅ |
| MEMORY 纯 M2 行 | README §3 数据行 **47**；逐行 `grep -Fx` 对照 HEAD：**45 行逐字节命中**，仅 2 行非命中 = `spec 模块`/`integ 模块` 的「（M2 段落）」拆分行（见下） | ✅ |
| issues ≤ 达成日 closed | HEAD `- id:` **113** = closed **41** + open **72**；活台账 closed **0** / open **72** / total **72** | ✅ |

**MEMORY 拆分保真**（集合差）：`comm -23 <(HEAD表行) <(活表行)` = **47 行**（= 45 纯 M2 + `spec`/`integ` 2 条混合整行），`comm -13` 新增 3 行 = `spec 模块`(M1 段) / `integ 模块`(M1 段) / `**M2 归档**` 指针 ⇒ 与「45 + 2 段落」口径一致，无数据丢失。

##### 3. 保真（逐字节，非抽查）

- changelog：HEAD 60 条表行 vs README §2 60 条 → `diff` **IDENTICAL**。
- MEMORY：45 条纯行 `grep -Fx` 全部逐字节命中；2 拆分行的 M2 段落与 HEAD `spec`/`integ` 行 `**M2 过渡**`/`**2026-09-25 INTEG-005t**` 之后内容一致。
- issues-closed.md：41 条原始 YAML 与 HEAD 41 条 closed 记录逐字节比对，**唯一差异 = 源文件的分节注释行（`# ── llvm/qemu…`）未搬入**（非 issue 内容）；id 集合完全一致，无遗漏/多余。
- 整包内容未改：`R100` 已证 149 任务书内容零变化。

##### 4. 活台账处理（`Process-04 §6`）

| 台账 | 独立核验 | 结论 |
|------|---------|------|
| `changelog.md` | 指针 `M2 归档指针` 在表头（§ 表头 L9）**之上** L7；表内 ≤ 达成日数据行 = **0** | ✅ |
| `MEMORY.md` | `^\| \*\*M2 归档\*\*` 表内合法行 = **1**；`spec/integ` M1 段保留；`组件补丁规范`/`FP softfloat` 等 M2 行 = 0 | ✅ |
| `issues.yaml` | 头部注释指针 `M2 阶段关闭项` = 1；`status: closed` = 0 | ✅ |
| `milestones.md` | `\| M2 \|…✅ 达成` = 1；表下归档注 = 1 | ✅ |
| 格式 | 7 文件：表内空行 **none**、连续空行 **0**、尾字节均 `0a`（单换行，无尾空行） | ✅ |

##### 5. 门控与证据脚本

- `make check` 独立重跑 **EXIT=0**（lit **31/31**、`check_issues: 72 open, 0 closed`、`repository checks: PASS`）；`make check-no-residue` **EXIT=0**（PASS）。
- 证据脚本重跑：`run.sh --no-check` **30/30 EXIT=0**；`run.sh`（含 make check）**31/31 EXIT=0**。
- **独立注入（异于 reviewer 的 decoy 模块计数法）**：向 `changelog.md` 表尾追加一行 `| 2026-10-04 | DECOY-INJECT-CHECK | x |` → `C5_changelog_no_M2_rows (expected=0 actual=1)` **FAIL**，`SUMMARY: pass=29 fail=1 / EVIDENCE: FAIL / REAL_EXIT=1`；还原（sha256 前后均 `41589e84…`，与注入前一致）→ 复跑 **30/30 / EXIT=0**。**反向证伪了 C5 断言的 FAIL 路径真实可达**（reviewer 仅注入 C2/C4 路径）。

##### 6. 约束与边界

- `git status --short -- spec contracts tools tests components .tao/archive/M1` **无输出**；`git status --untracked-files=all | grep '^??'` 无输出。
- 改动集合 = `.tao/archive/M2/**` + 4 个 `.tao/knowledge/{MEMORY,changelog,issues,milestones}` + 本任务书，**无越界**。

##### 7. 前置与 caveat

- `Process-04 §2` 前置 `INFRA-033t`：归档件状态 **已验证**，提交 `0898ec7`（2026-10-04 12:41）为 `4753fe2` 祖先 ⇒ 前置满足。
- caveat 归档正确：`SPEC-020m`/`SPEC-025m` 在 `archive/M2/spec/`（状态 `里程碑`）；`QEMU-030t`（`M2（推翻 M1 RA 行为）`）/ `TESTCASES-020t`（`M2（推翻 M1 RA 向量期望值）`）在 `archive/M2/{qemu,testcases}/`，README §1 有加注披露。
- 全部 149 归档件状态均终态（139 `已验证` + 2 带注 `已验证` + 8 `里程碑`）。

##### 发现（非阻断）

1. `ISS-101` 的 `resolved_by` 引用 `SPEC-031t`，但**无独立提交**（`git log --grep` 无命中）；其改动经 bundled commit `8fe4976`（2026-09-28，`SPEC-016t/018t`）落地，仍 **≤ 达成日**。reviewer「38 个 task ID 均 ≤ 达成日」结论**成立**，但该条依赖「bundled 提交」而非直查，评审记录未标注——属可补充的细节，不影响判决。
2. 归档任务 `INTEG-010t` 自身 `**项目里程碑**：M2` 且非终态，按 `Process-04 §3.1`（须终态）**不入归档**——与 `milestones.md`「唯一非终态 M2 任务」披露一致，属固有 carve-out。
3. 验收标准 7（归档单独成一个 commit）在本任务内**不可达**（提交由主会话执行），与「本任务不提交」一致——非缺陷。

##### 判决

**确认 Accepted**（复核未发现 reviewer 的遗漏关键项、约束违反或判决过松/过严；上述 3 条为披露性说明，不影响结论）。
