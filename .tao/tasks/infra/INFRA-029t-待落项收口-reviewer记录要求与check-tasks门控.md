# INFRA-029t: 待落项收口 — reviewer 记录要求 + make check-tasks 门控

**模块**：infra
**项目里程碑**：M1→M2
**依赖**：无
**状态**：已验证

> **来源**：`/tmp/tao.md`（用户整理的 DADAO-v5 待落项）中 **②③ 已落地**（`AGENTS.md` L135–147「任务收尾」规程、L151–156「收尾检查」），本任务落 **①** 与 **④**。
> **归属**：①是项目 `AGENTS.md` 一句话补充，④是 `tools/infra/` 脚本 + `Makefile` 目标 ⇒ 均归 **infra**（普通 `t`）。
> **串行提醒**：本任务改 `AGENTS.md` ⇒ 与任何同改该文件的任务**串行**（当前无并行任务）。编号已核对：`.tao/tasks/infra/` 最大 `028` → `029`。

## 一、要落地的两项（用户已确认）

### ① 项目 `AGENTS.md` 补一句（「验证脚本反例门控」段）
在现有 reviewer 条目「**reviewer 必须主动证伪**」（L99）之后补明：
> 其**审阅记录须含**：**判决** + **逐项真实命令输出/退出码** + **反例注入与还原证据**。

现状：L99 有「必须主动证伪」、L101 有「反例注入须可复原……**在完成区**给还原证据」，但**未写明审阅记录本身须含该证据**（本任务是补这条约束）。

### ② 新增 `make check-tasks`（机械门控，**报告型**）
- 扫 `.tao/tasks/**/*.md`，**列出「完成区已填（非占位）但 `**状态**` 仍为 `待验收`」**的任务书（即「漏 `/complete`」）。
- **默认警告**（报告型，**退出码 0**）；提供 **`--strict`** 使其失败（计数 >0 ⇒ 非零）。
- **不并入 `make check` 的阻断路径**（用户明示「非强制/不阻断」，与本仓 `size-report` 同策略）；可并入 `/status` 或提交前自查说明。
- 实现落 `tools/infra/check_tasks.py`（脚本）+ `Makefile` 目标。
- 须有**能失败**的反例（fixture 造「完成区已填 + 待验收」被列出；`--strict` 时非零）。

## 二、现状基线（2026-10-03 实测，供对照；engineer 须复算）

- `.tao/tasks/**/*.md` 共 **195** 个；含 `## 完成区` 的 **179** 个。
- 状态分布：`已验证` **163**、`待验收`（含 `待验收（…）` 变体）**13**、`待开始` 9、`里程碑` 8、其余为 ADR/`Candidate` 类（非本门控对象）。
- **符合「完成区已填 + 待验收」= 13 个**（初步扫描；engineer 以脚本复算为准）：
  `INFRA-018t`、`INFRA-019t`、`SPEC-058t`、`SPEC-062t`、`SPEC-063t`、`SPEC-066t`、`SPEC-067t`、`SPEC-068t`、`SPEC-069t`、`SPEC-071t`、`SPEC-073t`、`SPEC-074t`、`TESTCASES-020t`。
- 判据：`**状态**` 以 `待验收` 开头；`## 完成区` 段去掉字段标签与 `（待填写）` 后仍有非空内容 ⇒ 已填。

## 三、接口规范

### 输入
- `AGENTS.md`（「验证脚本反例门控」段 L92–105，尤其 L99/L101）
- `.tao/tasks/**/*.md`（任务书；`t` 类含 `## 完成区`）
- `Makefile`（`.PHONY`、`check:` 依赖行、help）
- 参照：`tools/infra/size_report.py`（**报告型**工具范式：发现异常但退出码恒 0、不进门控）、`tools/infra/check_spec_drift.py`（`--repo-root` 重定位）

### 输出
1. `AGENTS.md`：「reviewer 必须主动证伪」条目后补「审阅记录须含 判决 + 逐项真实命令输出/退出码 + 反例注入与还原证据」一句（**不改**其它段落）。
2. `tools/infra/check_tasks.py`：报告型脚本（见 §四.2）。
3. `Makefile`：`.PHONY` 增 `check-tasks` + 目标（**不入 `check:`**）+ help 一行。
4. （可选）`.tao/README.md` 或 `AGENTS.md` 收尾检查段：补一句「提交前可跑 `make check-tasks`（报告型）自查漏收尾」。

### 约束
- 全程中文；**不提交 git**；只动任务书范围，越界须披露。
- **不改决策语义**：仅**新增**一句 reviewer 记录要求 + 报告型工具；不动四态状态机、不动 `make check` 组成。
- **不得**把 `check-tasks` 并入 `make check` 的**阻断**路径：`check:` 依赖行不得含 `check-tasks`；默认**退出码 0**。
- 不改历史台账/已验收任务书；`spec/SimRISC-0.5.3/` 不改。
- 临时产物 `/tmp/opencode/INFRA-029t/`；证据留 `.work/log/infra/INFRA-029t-*.log`（`cmd > log 2>&1; rc=$?; echo "EXIT=$rc"`）。
- 遵循 `AGENTS.md`「子代理硬约束」。

## 四、实施步骤

### 1. `AGENTS.md` 补 reviewer 记录要求
- 在「**reviewer 必须主动证伪**」条目（L99）之后新增一条（或就地补明）：
  > **reviewer 审阅记录须含**：**判决**（Accepted/Needs Revision）+ **逐项真实命令输出与退出码** + **反例注入与还原证据**（注入→FAIL→还原→回绿的真实输出）；不得只给结论。
- 保持「验证脚本反例门控」段其它条目与既有教训不变。

### 2. `tools/infra/check_tasks.py`（报告型）
- 签名（建议）：`check_tasks.py [--repo-root DIR] [--strict]`；默认 `--repo-root`＝仓库根。
- 逻辑：
  1. 遍历 `<root>/.tao/tasks/**/*.md`；
  2. `**状态**`＝`^\*\*状态\*\*[：:]\s*(.+)$`（取首行）；命中条件：以 `待验收` 开头（兼容 `待验收（…）` 变体）；
  3. 提取 `## 完成区` 段（至下一个 `^## ` 标题或文件末）；**已填**判据＝去掉 5 个字段标签（`**测试结果**：` 等）与 `（待填写）`/空行/空白后仍有非空内容（建议要求 `测试结果` 或 `验收结果` 至少一项非空，避免仅「新发现」有字）；
  4. 无 `## 完成区` 的文件（`k`/`m` 类）**跳过**；
  5. 输出被列为 `路径 | 状态`，并打印计数与提示行（示例：`提示：以下任务完成区已填但状态仍为「待验收」——疑似漏 /complete（报告型，不阻断）。`）。
- **退出码**：默认恒 `0`（即使列出多个）；`--strict` 且计数 >0 ⇒ 非零（如 1）；硬错误（路径不存在）另定（2）。
- 只读，不修改任何文件。

### 3. `Makefile`
- `.PHONY` 增 `check-tasks`；新增目标：
  ```
  # 待收尾任务自查 (INFRA-029t): 报告型，列出「完成区已填 + 待验收」的漏 /complete 任务。
  check-tasks:
  	@$(PYTHON) tools/infra/check_tasks.py
  ```
- help 增一行 `make check-tasks  Report tasks with filled 完成区 but status still 待验收 (advisory; --strict to fail)`。
- **`check:` 依赖行不得含 `check-tasks`**。

### 4.（可选）可发现性
- 在 `.tao/README.md`（命令/目录说明）或 `AGENTS.md` 收尾检查段补一句「提交前可跑 `make check-tasks`（报告型）自查漏收尾」。若省略，完成区说明理由。

## 五、验收标准（每项均可失败）

> 证据留 `.work/log/infra/INFRA-029t-*.log`；反例优先用 `/tmp` fixture（不污染真实任务书）。

1. **① 记录要求落位**：`grep -nE "审阅记录须含|反例注入与还原证据" AGENTS.md` 命中该条；其所在段其余条目与既有「完成区」表述**未被删改**（`git diff -- AGENTS.md` 仅新增该条/该句）。
2. **② 门控存在且报告型**：`python3 tools/infra/check_tasks.py` → **EXIT=0**；`make check-tasks` → **EXIT=0**；输出列出「完成区已填 + 待验收」任务（当前实测 **应为 13 个**，见 §二；engineer 以脚本复算，如实报数并列出）。
3. **② 不进门控**：`grep -n "check-tasks" Makefile` 命中 `.PHONY`/help/目标，**不命中** `check:` 依赖行；`make -n check \| grep -c check-tasks` = **0**。
4. **② 可失败（`--strict`，fixture 反例）**：在 `/tmp/opencode/INFRA-029t/fixture/.tao/tasks/x/` 造 `TST-001t-demo.md`（`**状态**：待验收` + `## 完成区` 的 `测试结果` 非空）→
   - `python3 tools/infra/check_tasks.py --repo-root <fixture>` → **EXIT=0** 且**列出** `TST-001t-demo.md`；
   - `python3 tools/infra/check_tasks.py --repo-root <fixture> --strict` → **非零退出**；
   - 对照：同 fixture 另造 `TST-002t-done.md`（`已验证` + 完成区已填）与 `TST-003t-new.md`（`待开始` + 完成区占位）→ **不**被列出（判据区分正确）。
   - 给创建命令与真实输出。
5. **② 检出真实样本**：真实仓库跑 `make check-tasks` 输出的清单**非空**且与 §二 实测集合一致（≥1；如实报数）。**可失败对照**：若脚本漏判（如把 `待验收（…）` 变体漏掉或把已填判成占位），清单会少于实测 ⇒ 断言失败。
6. **`make check` 不受影响**：`make check` → **EXIT=0**（lit 25/25、`repository checks: PASS`）；加入 `check-tasks` 前后均绿 ⇒ 非阻断。
7. **无越界**：`git diff --name-only` 仅 `AGENTS.md`、`Makefile`（+可选 `.tao/README.md`）；新增 `tools/infra/check_tasks.py`；`git diff --name-only -- components/ spec/SimRISC-0.5.3/ .tao/adr/` 为空；**未改任何已验收任务书**。
8. **脚本只读**：跑报告后 `git status --porcelain` 无新增改动。

## 六、下发前四项预检（主会话下发时须逐条给结论）

1. **任务书内部一致性**：✅ 两项（①AGENTS.md、②check-tasks）↔ 产出/验收一一对应；「非强制/报告型」↔「默认退出码 0 + 不入 `check:`」一致；反例（fixture `--strict`）与正例（真实 13 个）互补。无自相矛盾。
2. **依赖链实际可用性**：✅ 无前置任务；`AGENTS.md` L99 与 `## 完成区` 段存在；`.tao/tasks` 含 179 个完成任务书；实测「完成区已填 + 待验收」= **13**（复算见 §二）。
3. **验收可执行性**：「现在可跑」全部项（Python + `Makefile` + 文档，**无需构建**）；`make check` 全量需构建产物——当前在位；缺失时 **BLOCKED**，替代证据为 `make check-tasks` + `grep Makefile` + fixture 反例 + `check-no-residue`。
4. **与 spec/vectors 一致**：本任务不涉及编码/期望值/向量。

## 完成区
**测试结果**：全部验收项通过（8/8）。核心输出：
- `python3 tools/infra/check_tasks.py` **EXIT=0**；`make check-tasks` **EXIT=0**。**实现完成时**列出 **13** 个「完成区已填 + 状态前缀 `待验收`」任务，与 §二 实测集合一致；**本任务自身置 `待验收` 后**清单为 **14** 个（第三项即本任务 INFRA-029t——「待验收」本义即待 `/complete`，被列出属正确行为；`/complete` 置 `已验证` 后即消失）。
- fixture 反例（`/tmp/opencode/INFRA-029t/fixture/.tao/tasks/x/`）：`TST-001t-demo`（待验收+测试结果非空）**被列出**，默认 **EXIT=0**、`--strict` **EXIT=1**；否定对照 `TST-002t-done`（已验证）、`TST-003t-new`（待开始+占位）**未被列出**；另验 `TST-004t-suffix`（`**验收结果**（round 2 …）：非空`）被列出、`TST-005t-boundary`（仅 `**修改文件**` 有字）未被列出。不存在 `--repo-root` → **EXIT=2**。
- `grep -nE "审阅记录须含|反例注入与还原证据" AGENTS.md` 命中 L100；`git diff -- AGENTS.md` 仅新增 1 行。
- `make -n check | grep -c check-tasks` = **0**（不阻断）；`grep -n check-tasks Makefile` 命中 `.PHONY`(L45)/help(L89)/目标(L250)，**不在** `check:` 依赖行。
- `make check` **EXIT=0**（lit 25/25、`repository checks: PASS`）；`python3 -m compileall -q tools` **EXIT=0**；`check-no-residue` **PASS**。
- 真实仓库 `--strict` **EXIT=1**（计数 13>0）。
- 证据日志：`.work/log/infra/INFRA-029t-*.log`（`accept-core`/`accept-fixture`/`accept-fixture2`/`accept-real2`/`accept-misc`/`accept-final`/`accept-make-check`）。

**修改文件**：
- `AGENTS.md`：「验证脚本反例门控」段「reviewer 必须主动证伪」条目后**新增 1 条**「reviewer 审阅记录须含 判决 + 逐项真实命令输出/退出码 + 反例注入与还原证据」。
- `Makefile`：`.PHONY` 增 `check-tasks`；help 增 1 行；新增 `check-tasks` 目标（`@$(PYTHON) tools/infra/check_tasks.py`）；**未**并入 `check:` 依赖。
- `.tao/README.md`：目录段补 1 行「任务收尾自查 — 提交前可跑 `make check-tasks`（报告型…）」。
- `tools/infra/check_tasks.py`：**新增**报告型脚本（只读，stdlib）。

**验收结果**：
1. `grep -nE "审阅记录须含|反例注入与还原证据" AGENTS.md` → L100 命中，EXIT=0；`git diff -- AGENTS.md` 仅 `+` 1 行（其余条目与既有「完成区」表述未删改）。
2. `python3 tools/infra/check_tasks.py` EXIT=0；`make check-tasks` EXIT=0；实现完成时列出 13 个（含 `待验收（…）` 4 个变体）；本任务置 `待验收` 后为 14 个（含本任务）。
3. `grep -n check-tasks Makefile` → L45/L89/L250；`make -n check | grep -c check-tasks` → 0（EXIT=1 系 grep 无匹配）。
4. fixture：默认列出且 EXIT=0；`--strict` EXIT=1；否定对照未被列出；`--repo-root` 不存在 EXIT=2。真实输出见 `.work/log/infra/INFRA-029t-accept-fixture*.log`。
5. 真实仓库 `--strict` EXIT=1；实现完成时清单 = §二 13 个集合（自置 `待验收` 后 14 个 = 13 + 本任务）。
6. `make check` EXIT=0；lit `25 passed (100.00%)`；`repository checks: PASS`。
7. `git diff --name-only` = `.tao/README.md`、`AGENTS.md`、`Makefile`；新增 `tools/infra/check_tasks.py`；`git diff --name-only -- components/ spec/SimRISC-0.5.3/ .tao/adr/` 为空；未改任何已验收任务书。
8. 报告后 `git status --porcelain` 无新增改动（脚本只读）；`check-no-residue: PASS`。

**新发现/坑**：
- 实测 `.tao/tasks/**/*.md` 共 **196** 个（任务书 §二 基线记 195，差 1；疑为基线扫描时本任务书 INFRA-029t 尚未落盘或漏计）。「完成区已填 + 待验收」集合 **13 个**与 §二一致。
- 任务书完成区字段存在**带括号限定语**的写法（如 SPEC-068t 的 `**验收结果**（round 4 全量重跑）：`），若正则只认 `**字段**` 紧接冒号会漏判；已兼容（`RE_LABEL_QUALIFIER`），并加 fixture `TST-004t` 固化。
- 「已填」判据必须**在字段边界切分**后再判非空：否则 `**测试结果**：`（空）会把后续 `**修改文件**：…` 内容吸收进来造成假阳性；已用 `RE_FIELD_LABEL` 做边界，并加 fixture `TST-005t` 固化。
- 建议沉淀：`make check-tasks` 为报告型漏收尾自查门控（不阻断），判据「状态前缀 `待验收` + 完成区 `测试结果`/`验收结果` 至少一项非空（剥离 `（待填写）`）」；13 个历史漏收尾任务另议。
- **自指行为**：任务书一旦置 `待验收` 且完成区已填，`check-tasks` 会**列出该任务自身**（因为「待验收」正是「待 `/complete`」）；`/complete` 置 `已验证` 后消失。实测：实现完成时 13 → 本任务置 `待验收` 后 14。reviewer 重跑应见 14（含 INFRA-029t），属预期，非漏判。

**遗留问题**：
- 历史 13 个漏收尾任务**本任务只建门控，不逐个 `/complete`**（主会话裁定 #5，另议）。
- `check-tasks` 未集成 `/status`（裁定 #4：仅 Makefile help + `.tao/README.md`）。

## 审阅记录

#### 第 1 轮 engineer 自审
**改动逐行审查**：
- `AGENTS.md`：仅新增 1 条 reviewer 记录要求，位置在「reviewer 必须主动证伪」后、其他教训条目前；语义为**补充约束**，未改决策语义/状态机。✅
- `Makefile`：`.PHONY` 续行正确（`\` + 缩进）；目标无 tab 错误（recipe 行以 tab 开头）；**未**加入 `check:` 依赖（`make -n check` 反证 =0）。✅
- `tools/infra/check_tasks.py`：只读；`RE_STATUS` 取首个状态行、按前缀 `待验收` 判定；`extract_completion` 至下一 `^## ` 止；`field_value` 兼容括号限定语并要求**字段边界**切分，避免假阳性；`--strict`/硬错误退出码符合 1/2；stdlib-only，无新依赖。✅

**自主证伪（反例门控）**：
- 反例 1（该被列出却漏判）：`TST-001t`（完成区已填+待验收）被列出；`TST-004t`（括号限定语）被列出。✅
- 反例 2（不该列出却误列）：`TST-002t`（已验证）、`TST-003t`（待开始+占位）、`TST-005t`（仅 `修改文件` 非空）均未被列出。✅
- 反例 3（`--strict` 须失败）：真实仓库与 fixture `--strict` 均 EXIT=1。✅
- 反例 4（不阻断）：`make -n check | grep -c check-tasks`=0。✅

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 括号限定语字段标签（如 `**验收结果**（…）：`）会被漏判为非空 | ✅已修 | `field_value` 加 `RE_LABEL_QUALIFIER`；`RE_FIELD_LABEL` 兼容括号 | fixture `TST-004t` 被列出；SPEC-068t 仍被列出（13 计数不变） |
| 字段值未按边界切分会导致假阳性（空 `测试结果` 吸收 `修改文件`） | ✅已修 | `field_value` 用 `RE_FIELD_LABEL` 停止收集 | fixture `TST-005t` 未被列出 |
| 输出行「扫描任务书: N 个（含 `## 完成区` 的待验收任务）」表述有误 | ✅已修 | 改为「（.tao/tasks/ 下全部 .md）」 | 复跑输出一致、计数 196 |
| 任务书 §二 基线 195 vs 实测 196 | ⏸延后 | 不改门控；在完成区「新发现」如实记录差异 | `find .tao/tasks -name '*.md' \| wc -l` = 196 |

**判决**：所有 finding 已处置（3 修 / 1 记为差异说明），验收 8/8 通过 ⇒ 状态置 `待验收`。

#### 第 1 轮 reviewer 验收

**判决**：**Accepted**

**重跑记录**（全部命令由 reviewer 独立执行，非采信 engineer 输出）：

| # | 验收项 | 命令 | 真实输出 | EXIT | 判定 |
|---|--------|------|---------|------|------|
| 1 | ① AGENTS diff 仅 +1 行 | `git diff -- AGENTS.md` | `1 file changed, 1 insertion(+)`；`git diff -- AGENTS.md \| grep '^+' \| grep -v '^+++' \| wc -l` = **1** | 0 | ✅ |
| 1 | ① grep 命中 L100 | `grep -nE "审阅记录须含\|反例注入与还原证据" AGENTS.md` | L100 命中 | 0 | ✅ |
| 2 | ② 正例 python3 | `python3 tools/infra/check_tasks.py` | 列出 **14** 个条目（13 基线 + INFRA-029t 自指），扫描 196 个 | **0** | ✅ |
| 2 | ② 正例 make | `make check-tasks` | 输出同上，14 个条目 | **0** | ✅ |
| 3 | ② 反例 fixture 默认 | `python3 tools/infra/check_tasks.py --repo-root <fixture>` | 列出 TST-001t（待验收+测试结果非空）；TST-002t/TST-003t 未列出 | **0** | ✅ |
| 3 | ② 反例 fixture --strict | `... --strict` | 同上清单，计数 1>0 | **1** | ✅ |
| 3 | ② 反例 --repo-root 不存在 | `... --repo-root /nonexistent` | `check-tasks: ERROR — tasks 目录不存在` | **2** | ✅ |
| 4 | 不阻断 grep -c | `make -n check 2>&1 \| grep -c check-tasks` | **0**（grep 无匹配，grep 自身 EXIT=1） | 0（计数） | ✅ |
| 4 | 不阻断 make check | `make check` | lit 25/25 (100%)，80 项接口 PASS，repository checks: PASS | **0** | ✅ |
| 5 | 只读 git status | `git status --porcelain` | 仅 `.tao/README.md` `AGENTS.md` `Makefile` 修改 + 任务书/check_tasks.py 新增 | — | ✅ |
| 6 | 无越界 | `git diff --name-only -- components/ spec/SimRISC-0.5.3/ .tao/adr/` | 空（无改动） | 0 | ✅ |
| 6 | 未动已验收任务书 | `git diff --name-only -- .tao/tasks/` | 空（无改动） | 0 | ✅ |
| 7 | 真实仓库 --strict | `python3 tools/infra/check_tasks.py --strict` | 14 个条目，计数 14>0 | **1** | ✅ |

**约束核验**（逐条）：
1. ✅ **AGENTS 仅 +1 行**：`git diff -- AGENTS.md` = `1 file changed, 1 insertion(+)`，新增条在 L100「reviewer 必须主动证伪」之后、其余条目未动。
2. ✅ **正例 EXIT=0 且列出 14 个**：`python3` 与 `make check-tasks` 均 EXIT=0，列出 14 条（含 INFRA-029t 自指、4 个待验收变体），扫描 196 个。
3. ✅ **反例可失败**：fixture TST-001t 被列出（默认 EXIT=0 / `--strict` EXIT=1）；TST-002t（已验证）/TST-003t（待开始+占位）未被列出；`--repo-root` 不存在 EXIT=2。
4. ✅ **不阻断**：`make -n check | grep -c check-tasks` = 0；`check:` 依赖行不含 `check-tasks`；`make check` EXIT=0。
5. ✅ **只读**：跑前后 `git status --porcelain` 一致，脚本无副作用。
6. ✅ **范围无越界**：`components/`、`spec/SimRISC-0.5.3/`、`.tao/adr/`、已验收任务书均未改动。
7. ✅ **完成区一致性**：「自指 14」= 13 基线 + INFRA-029t 自身 ✅；「基线 195→196」扫描 196 个 ✅；`--strict` EXIT=1 ✅；fixture 反例行为均如实。

**反例注入与还原证据**：
- 注入：在 `/tmp/opencode/INFRA-029t-review/fixture/.tao/tasks/x/` 创建 TST-001t（待验收+测试结果非空）、TST-002t（已验证+已填）、TST-003t（待开始+占位）。
- FAIL 证据：`--strict` EXIT=1（计数 1>0）；TST-002t/TST-003t 未被列出（假阳性 = 0）。
- 还原：`rm -rf /tmp/opencode/INFRA-029t-review` 已清理；`git status --porcelain` 与注入前一致（无新增改动）。
- 注入有效：fixture 创建在 `/tmp`，未污染真实仓库。

## 收尾与提交（用户裁定，2026-10-03）
- **执行期不提交**：engineer/reviewer 子代理**不得** `git commit`/`git add`。
- **收尾后提交一次**：本任务经 `/complete` 通过、`**状态**` 置为 `已验证` 后，**主会话**为该任务做一次独立提交；**未收尾不得提交**。
- 提交前满足项目 `AGENTS.md`「任务收尾」的收尾检查。

## 开放问题（只列不决）
1. **「完成区已填」判据**：是否要求 `测试结果`/`验收结果` 至少一项非空（本任务书建议「是」），还是任一字段非空即可——默认前者。
2. **状态变体**：`待验收（**已下发**）`/`待验收（**待用户确认任务书后下发**）` 等变体是否一律计入（本任务书建议「是」，按前缀 `待验收`）——若认为「未真正下发」者应排除，请裁定。
3. **是否也应报 `待返工`**：本门控仅列 `待验收`；`待返工` 是否纳入（默认否）。
4. **可发现性落点**：`/status` 集成 vs `.tao/README.md` 说明 vs 仅 `Makefile` help（默认 README/help 说明，不集成 `/status`）。
5. **本任务实测 13 个漏收尾任务**：本任务**只创建门控**、**不**逐个 `/complete`（它们是历史任务，另议）——请确认范围。
