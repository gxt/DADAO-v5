# INFRA-061t: `changelog.md` 合并进 `milestones.md`（台账单一真源）

**模块**：infra
**项目里程碑**：M7
**依赖**：无（同改 `.tao/knowledge/**`、`.opencode/commands/complete.md`、`docs/Process-04`、`tools/spec/check_scope.py` ⇒ 与 `INFRA-056t` / `INFRA-057t` **串行**）
**状态**：已验证

> 本任务书由**主会话**依用户 2026-10-11 裁定撰写（非常规 architect 起草，已披露）。

## 用户裁定（2026-10-11，**原话**）

> 「`changelog.md` 还有必要存在吗？是不是直接合并进 `milestones.md`；」
> 「合并，且先做这步（推荐）」

## 目的

消除**同轴孪生台账**：`changelog.md`（逐任务实质改动）与 `milestones.md`「任务流水」（逐任务清单）记录的**是同一批任务**，且在里程碑归档时并排落到同一份归档（`archive/M*/README.md` §1 流水 / §2 changelog）⇒ 两处需同步、易漂移。**合并为单一真源 `milestones.md`**。

## 接口规范

### 输入（现场事实）

- `milestones.md`（54 行）现结构：`# 项目里程碑` / `## 项目里程碑`（指针→根 `README.md`）/ `## 任务流水（仅当前里程碑）` / `## 当前进度`。
- `changelog.md`（23 行 + 数据行）：头部 M1–M6 **归档指针**（各里程碑条目已移入 `.tao/archive/M*/README.md §2`）+ 表格（列 = 日期 | 描述 | 执行方）。**实测**：数据行单元格**最长 1071 字**、中位数 510、**5/6 行 >40 字** ⇒ 表格**不合体**（依用户表格判据）。
- 指向 `changelog.md` 的**活引用**（现场 `git grep` 为准，不写死）：`.opencode/commands/complete.md`（收尾追加步骤）、`docs/Process-04-里程碑归档规范.md`（归档清单）、`tools/spec/check_scope.py`（`HISTORY_PREFIXES`，历史载体豁免项）、`.tao/README.md`、`docs/repository-layout.md`、`.tao/knowledge/{MEMORY,issues.yaml,lessons.md}`（**部分为历史叙述，须逐条判**）。
- **表格判据（用户 2026-10-11）**：表格**每格内容须单行显示**（经验阈值 ≈ ≤40 半角字符/格）；**任一行需换行 ⇒ 不用表格**，改「小标题 + 列表」。

### 输出

1. **`milestones.md` 重排为单一真源**（5 节，顺序）：
   1. `# 项目里程碑`（标题行保持）
   2. `## 项目里程碑`——保留指向根 `README.md` 的**一行指针**（不变）
   3. `## 任务流水`——**本里程碑**逐任务一行：`| 编号 | 状态 | 日期 | 一句改动 |`（**每格 ≤1 行、不换行**；细节**指针到任务书**）；**M7 已终态任务按各任务书 `**状态**` 现场回填**（`INTEG-033k` / `INFRA-058t` / `INFRA-060t` 等；**计数现场统计、不写死**）。
   4. `## 当前进度`——保留现内容（M6 达成 + M6 遗留 + 规划中 + M7 裁定等，**按现场增补**）。
   5. `## 历史台账指针`——原 `changelog.md` 的 M1–M6 归档指针**原文搬入**（说明「各里程碑逐任务改动记录见 `.tao/archive/M*/README.md`」）。
2. **删除 `changelog.md`**：`git rm .tao/knowledge/changelog.md`（**M1–M6 的旧条目仍在 `.tao/archive/M*/README.md §2`，一律不动**——不追溯重写）。
3. **连带同步（4 处 + 指针）**：
   - `.opencode/commands/complete.md`：收尾「追加实质改动」的目标由 `changelog.md` → `milestones.md`（改述落点与形态）；
   - `docs/Process-04-里程碑归档规范.md`：归档清单去掉 changelog（流水与改动**同节搬运**）；
   - `tools/spec/check_scope.py`：`HISTORY_PREFIXES` 去掉 `.tao/knowledge/changelog.md`（避免指向不存在路径的死项）；
   - 指针类活引用同步（`.tao/README.md`、`docs/repository-layout.md`、`.tao/knowledge/{MEMORY,issues.yaml,lessons.md}`）——**仅改"活指针"，历史叙述保留**，逐条判并在完成区列明。
4. **形态纪律**：`milestones.md` 任务流水表**每格单行**；**长描述不入表**（指任务书）。

### 约束

- **不动** `.tao/archive/**`、不动已归档任务书、不改 `spec/`、`contracts/`、`tests/vectors/`。
- 只动上述范围；越界须披露。
- **计数 / 条数 / 引用数不写死**（现场 `grep`/`ls` 产出）。
- 临时目录 `/tmp/opencode/INFRA-061t/`；**不提交 git**；禁 `git add -A`/`.`。
- **反例注入不得用** `git checkout`/`restore`/`stash`；一律 `cp` 备份 + md5 对账（或临时树注入）。
- 任务书 / 记录 / 文档中**不得出现字面 `.work/<具体路径>`**（一律 `<>` 占位），否则 `check-knowledge-refs` 判悬空、`make check` 自伤（本项目已两次踩到；`lessons §8.56`）。

## 验收标准

1. **合并生效**：`.tao/knowledge/changelog.md` **不存在**（`ls` 真实输出）；`milestones.md` 含上列 5 节，任务流水表**每格单行**（`awk` 量测单元格长度，**最长 ≤ 阈值**并给出实测值，计数不写死）。
2. **活引用收敛**：`git grep -n 'changelog\.md'`（**排除** `.tao/archive/**` 与历史叙述）⇒ **仅剩**经判定可留的历史叙述，**逐条列明**；`tools/spec/check_scope.py` 无该路径。
3. **门控**：`make check`（L1）**EXIT=0**（捕获**命令自身**退出码，禁 `cmd | tee` 吞码）；`make check-no-residue` EXIT=0。
4. **注入反例可失败**：把某活文件里指向 `milestones.md` 的指针临时改回 `changelog.md`（不存在）⇒ 证据脚本 / 断言 **FAIL** ⇒ `cp`+md5 还原 ⇒ 回绿（留真实输出）。
5. **一键证据脚本**落 `.work/evidence/INFRA-061t/`（能失败、可达 FAIL、结构断言、计数不写死、捕获退出码）。
6. **完成区**（≤30 行）与真实输出逐条对齐；「连带同步」逐处列明（改了/未改 + 理由）。

## 完成区
**测试结果**：`make check`(L1) rc=0；`make check-no-residue` rc=0；一键证据 `.work/evidence/INFRA-061t/run.sh` rc=0（8 断言全 PASS + `--inject` 自检 rc=0）。任务流水数据行 **14**（现场统计）、最长单元格半角宽 **31**（阈值 40）。
**修改文件**：`.tao/knowledge/milestones.md`(重排 5 节 + M7 任务流水)、`.tao/knowledge/changelog.md`(`git rm` 删除)、`.opencode/commands/complete.md`(E 段 → milestones.md 任务流水)、`docs/Process-04-里程碑归档规范.md`(判据/模板/§7 去 changelog)、`tools/spec/check_scope.py`(HISTORY_PREFIXES 去 changelog.md)、`.tao/README.md`(knowledge 行列去 changelog.md)、本任务书。
**验收结果**：
1. 合并生效：`ls .tao/knowledge/changelog.md` → `No such file or directory`；milestones.md 5 节按序（行 1/7/13/35/74：`# 项目里程碑`→`## 项目里程碑`→`## 任务流水`→`## 当前进度`→`## 历史台账指针`）；任务流水表列 `| 编号 | 状态 | 日期 | 一句改动 |`，每格单行、最长半角宽 31（≤40）。
2. 活引用收敛：`git grep 'knowledge/changelog\.md'` 排除 archive ⇒ 仅 `.tao/tasks/infra/INFRA-055t-*.md`（2 行=完成区历史记录）；`check_scope.py` 已无该路径。
3. 门控：`make check` rc=0（日志 `.work/log/infra/INFRA-061t-check.log`）；`make check-no-residue` rc=0。
4. 注入反例：`run.sh --inject` 将 complete.md 的 `knowledge/milestones.md` 改回 `knowledge/changelog.md` ⇒ 断言 `[FAIL]` ⇒ `cp`+md5 还原（before=after=`608efd619439e36fcd054bdba6bf3dba`）⇒ 回绿 rc=0。
5. 证据脚本：`.work/evidence/INFRA-061t/run.sh`（+ `cell_width.py`）。
**连带同步（逐处：改/不改 + 理由）**：
- **改** `.opencode/commands/complete.md`（收尾 E 段）：活输出落点 → `milestones.md` 任务流水，含每格单行口径。
- **改** `docs/Process-04`：§4.2 判据、§6 模板（判据行/§2 标题+表头/§4 指针）、§7 行、§8 一处 = `changelog.md`→`milestones.md`「任务流水」。
- **改** `tools/spec/check_scope.py`：`HISTORY_PREFIXES` 去 `.tao/knowledge/changelog.md`（避免死路径项）。
- **改** `.tao/README.md:43`：`knowledge/` 目录说明去 `changelog.md`（活目录清单）。
- **不改** `.tao/README.md:94`、`.tao/knowledge/lessons.md:134`：迁移/历史快照叙述（历史保留）。
- **不改** `.tao/knowledge/issues.yaml:169`、`docs/Process-01`(3)、`docs/repository-layout.md:14`、`INFRA-055t/057t/060t`：均指**组件** `components/*/changelog.md`（别体，非本次知识库 changelog）。
- **不改** `.tao/knowledge/MEMORY.md`：无 `changelog.md` 引用。
- **不改** `docs/Process-04 §9`：`教训（M1 归档实录）`历史记录（非活「归档清单」）。
- **不改** `.tao/archive/**`：任务约束禁改（含 M1–M6 README 的「变更流水（之后）：changelog.md」历史指针）。
**新发现/坑**：无新增（既有坑见 `lessons`）。`check-knowledge-refs` 会校验任务书内具体 `.work/` 引用须存在（本任务书 `.work/evidence/INFRA-061t/` 由证据脚本建立 ⇒ 绿）。
**遗留问题**：无。

## 审阅记录

#### 第 1 轮 engineer 自审
**范围**：逐行审查 6 个改动文件（见「修改文件」）逻辑/边界/防造假。
**findings 与处置**：F1 §9 Process-04 仍述「changelog 为 append-only」→ 属「教训（M1 归档实录）」历史记录，非活「归档清单」⇒ **保留**（历史不追溯改写）。F2 `.tao/README.md:94` 历史叙述含 `changelog.md` ⇒ **保留**。F3 `INFRA-055t` 完成区含 `.tao/knowledge/changelog.md` ⇒ 历史完成区，只追加 ⇒ **保留**。F4 本表 `INFRA-061t` 行状态写时 `待验收`，`/complete` 后追加为 `已验证` 属正常快照漂移 ⇒ **接受**。F5 `components/*/changelog.md`（issues.yaml/Process-01/repository-layout/INFRA-055t/057t/060t）为**组件** changelog，与知识库 changelog 别体 ⇒ **不改**。
**判决**：无待修 finding；空注入被 md5 检测拦截、断言可达 FAIL、还原 `cp`+md5 对账 ⇒ 逻辑与防造假通过。
#### 第 1 轮 reviewer 验收

**重跑（reviewer 本人终端；rc = 命令自身退出码，无 `tee` 吞码）**：
- `make check`（L1）**rc=0**（含 `check-knowledge-refs` 具体路径 86/悬空 0、`check-components` 3/3）。
- **`make check-modules`（L2，本任务首次启用该触发点）rc=0、耗时 96s**；组成 = `check-interface`+`check-lit`+`check-qemu-smoke`+`test-codegen`+`test-elf`+`test-semihost` 全 PASS（无异常/无超时，`124` 判据不触发）。
- `make check-no-residue` **rc=0**；证据脚本 `<WORK>/evidence/INFRA-061t/run.sh` 全量 **rc=0**（8 断言 + 2 门控全 PASS，27s）。
- **独立量测（自写 measure.py，东亚洲宽 W/F=2，非采信 engineer）**：任务流水数据行 **14**、表头列 `| 编号 | 状态 | 日期 | 一句改动 |`、**最长格半角宽 31**（「门控分层 + check-spec-refs 修复」）≤ 阈值 40 ⇒ PASS（与 engineer 31 独立复算一致）；`grep -n '^#'` 5 节按序（行 1/7/13/35/74）。

**信息不丢**：`git show HEAD:.tao/knowledge/changelog.md`（只读）比对——M1–M6 归档指针 6 条与「历史台账指针」节 **diff 逐字一致（rc=0）**；原表 5 条数据行按「一句改动 + 指针到任务书」口径落位，抽验细节可溯源（`shallow_ref→tag` 见 INFRA-055t 任务书 :54/:91；INTEG-022t 事实见 `.tao/archive/M5/integ/INTEG-022t-*.md` :98/:130/:464）⇒ 无实质信息丢失。M7 状态抽查 `INTEG-033k` 待开始 / `INFRA-058t` 已验证 / `INFRA-060t` 已验证（实测 14 行全查）与各任务书 `**状态**` 逐条一致（INFRA-061t 行 `待验收` = 任务书现值，`/complete` 翻转属正常快照）。

**删除与连带（grep 真实输出）**：`ls .tao/knowledge/changelog.md` → `No such file or directory`（rc=2）；`check_scope.py` grep `changelog` 无命中（rc=1）；`complete.md:80-81` E 段落点 = `milestones.md`「任务流水」+ 每格单行口径；`Process-04` §4.2 判据/§7 表/模板/指针行已并（`原名 changelog.md 条目` 注记 + §9 教训属历史保留）；`.tao/README.md:43` knowledge 行已去 changelog ⇒ 4 处连带全落实。

**活指针独立清单**（`git grep -n 'changelog\.md'` 排除 `.tao/archive/**`，逐条判定）：组件别体不改（`components/*/changelog.md`：issues.yaml:169、Process-01 ×3、repository-layout:14、INFRA-055t/057t/060t）；历史叙述可留（.tao/README.md:94、lessons:134、milestones:76 说明行、Process-04「原名」注记 ×3、INFRA-055t 完成区历史行 ×2）⇒ **指向已删文件的活指针 = 0**。

**证据脚本五项审**：一键可跑（`--inject`/`--no-gate` 模式）✓；能失败（FAIL→exit 1）✓；可达 FAIL（7 断言各有 fail 路径，`cell_width.py` 结构错 rc=2/超阈 rc=1）✓；结构断言（5 节序 + 表头 4 列 + 分隔行 + 列数=4）✓；计数不写死（行数/命中现场统计）✓；捕获退出码（make rc 直捕）✓。**独立注入（与 engineer 不同断言）**：milestones.md INFRA-061t 行「一句改动」注入 123 半角宽超长格 ⇒ `run.sh` **rc=1**、`[FAIL] 任务流水表每格单行`（其余断言仍绿，鉴别力好）⇒ `cp`+md5 还原 **before=after=`8efeb38e…`** ⇒ `run.sh --no-gate` **rc=0 回绿**。engineer `--inject` 自检重放 rc=0（complete.md md5 before=after=`608efd61…`）。

**约束核验**：临时产物全在 `/tmp/opencode/INFRA-061t-review/`、仓库零残留（收尾快照对账：`git status --porcelain -uall` 与验收前逐行 diff **rc=0 无差异**、5 个被测文件 `md5sum -c` 全 OK）；未提交 git、未改被测实现（只写本审阅记录）；未动 `.tao/archive/**`/`spec/`/`contracts/`/`tests/`（status 证）；注入还原全程 `cp`+md5（禁 checkout/restore/stash）；完成区 ≤30 行且与真实输出逐条对齐。

**非阻断小注**（不判 finding，供 architect 终审参考）：① `check_readme_pointer` 只锁单一旧串、`check_no_live_dead_pointer` 对 `.tao/tasks/**` 整目录豁免，覆盖面略窄（本任务范围内可接受）；② milestones「历史台账指针」首行称数据行「已随归档移入 archive」，实为 4 条 M7 行由任务流水+任务书承载、INTEG-022t 行由其归档任务书承载（语义近似、可追溯，建议 `/complete` 时不改、下轮归档顺带校准措辞）。

**判决：Accepted**——验收 1–6 全部通过（本人重跑），无阻断项。

#### architect 提交与文件集审核（2026-10-11）
- **档位**：**正常提交**（reviewer 判 `Accepted`）。
- **交叉复核（独立重跑，rc = 命令自身退出码）**：`make check`(L1) **rc=0**、`make check-no-residue` **rc=0**、`tools/infra/check_issues.py` **rc=0**（17 open / 7 closed / 0 blocking）；任务书 `**状态**：已验证`（`sed` 实测）；`milestones.md` 5 节按序（行 1/7/13/35/74）+ `INFRA-061t` 行 = `已验证`；`.tao/knowledge/changelog.md` **不存在**（`ls` rc=2）；`tools/spec/check_scope.py` 无 `changelog` 命中（`grep` rc=1）。
- **文件集对账**（`git status --porcelain -uall` vs 完成区「修改文件」+ 任务书自身 + 主会话两项收尾改动）：**A=1**（本任务书）、**M=5**（`complete.md` / `.tao/README.md` / `milestones.md` / `Process-04` / `check_scope.py`）、**D=1**（`changelog.md`）；`git diff --cached --name-status` 与清单一致；**无漏提 / 多提 / 越界**；`.work/**`（gitignored）未纳入。
- **提交**：分支 `INFRA-061t` = `be7bb1d`；落地 `master`（`merge --squash` 单提交）；分支已删；**未 push**。
