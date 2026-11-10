# m13-testcases-004: 测试报告目录规范与工具对齐

**模块**：testcases
**项目里程碑**：M13
**依赖**：无（报告目录已先行落地：`docs/TestReports/`）
**可并行分片**：否（跨 tools/docs 单写者）
**状态**：已验证

## 背景

用户 2026-11-10 裁定：

- **人读结论放 `docs/`，加子目录**；原始数据不入库；矩阵快照随结论同处（不污染 `tests/`）。
- 目录命名定为 **`docs/TestReports/`**，其下不再分 `parity` 等二级主题子目录，靠**文件名**区分；文件名须清晰整齐。
- 现存 `tests/parity/matrix-M11.md` **已迁入并改名** `docs/TestReports/M11-三平台一致矩阵.md`（凡例同步迁为 `…-凡例.md`），`tests/parity/` 已删除。
- 目录约束（命名 / 收什么不收什么 / 必备四项 / 禁止项）已写入 `docs/TestReports/README.md`；`docs/README.md` 已加索引。
- 现有 qemu/gem5 差分结论已落 `docs/TestReports/M13-三平台差分-qemu-gem5.md`。

**本任务只做「规范落地 + 工具/门控对齐」，不改上述结论内容。**

## 目标

1. **规范入册**：在 `docs/Process-09`（测试组织规范）新增「测试报告归属」一节，写清四类产物的落点（运行产物 / 原始数据 / 里程碑快照 / 人读结论）、命名规则、必备四项、禁止项；与 `docs/TestReports/README.md` 互为一致（不重复造第二套口径，Process-09 引 README 为准）。
2. **工具对齐**：`tools/testcases/parity/run_parity.py`、`se_tset_matrix.py`、`tools/testcases/night_run.py` 及 `tools/testcases/parity/README.md` 中默认输出路径 / 注释 / 示例改为 `docs/TestReports/<M>-…` 形态（**不改变算法与口径**）。
3. **门控**：新增 L1 检查 `check-test-reports`（`tools/infra/check_test_reports.py` + `Makefile` + `Process-07` 层归属登记），断言：
   - `docs/TestReports/` 下无运行期绝对路径（`/tmp/**`、`/home/**`、`.work/**` 具体路径）
   - 快照类文件首行含 `<!-- 现场生成，勿手改 -->`
   - 文件名符合 `<M>-<主题>[-<后缀>].md`（`<M>` = `M\d+`）
   - 每册头部含「生成时间 / 数据来源 / 机器指纹 / 复现命令」四项关键词
   - 检查器**必须可达 FAIL**（注入 4 类各一次，`cp`+md5 还原）
4. **引用一致性**：`git grep 'tests/parity'` 只剩白名单（归档册的历史叙述、`docs/README.md` 的来源说明），其余 0；`tests/parity/` 目录不存在。
5. **回归**：`check-tasks` / `check-knowledge-refs` / `check-run-artifacts` / L1 / L2 rc=0。

## 非范围

- 不改 `docs/TestReports/` 下两份报告的**结论与数据**（只允许修格式/链接错误，且须在完成区逐条列出）
- 不改生成器的选例/比对算法
- 不重跑长尾计时（`m13-testcases-003`）
- 不动 `.tao/archive/` 的正文（历史册路径已在迁移时机械更新，不再改写）

## 验收标准

1. `docs/Process-09` 有「测试报告归属」节，与 `docs/TestReports/README.md` 无矛盾（逐条对照表）
2. 三个工具脚本 + 其 README 的默认输出/示例指向新目录（`python3 tools/testcases/parity/run_parity.py --help` 可见）
3. `make check-test-reports` rc=0；4 类注入各可达 FAIL 并还原回绿
4. `git grep tests/parity` 仅白名单；`tests/parity` 不存在
5. L1 / L2 / `check-tasks` / `check-knowledge-refs` / `check-run-artifacts` rc=0（外部红逐条核实归属）
6. 一键证据脚本（运行期证据目录下的 `run.sh`）
7. 完成区 ≤30 行、无运行期路径

## 说明

- 门控复杂度按最小原则：先做 4 条静态断言，不引入格式化/渲染。
- `docs/TestReports/README.md` 与两份报告由 architect 先行落地；本任务以其为**输入**，不重写。
- 构建/门控在主控机；不占用 207/208。

## 硬约束（子代理必读）

1. 临时目录 `/tmp/opencode/<任务ID>/`，禁仓库内临时文件。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；只在需用户语义裁定时留问。
6. 复杂命令输出留存运行期日志目录。
7. 一键证据脚本；反例注入须「注入→FAIL→还原（`cp`+md5）→回绿」。
8. 用户裁定须原样写入任务书。
9. 命令作用域 = workdir（仓库根），用相对路径。

## 审阅记录

### 第 1 轮 engineer 自审

逐行审查：新增 `tools/infra/check_test_reports.py`、`run_parity.py` 的
`_display_path`/`write_markdown`、`se_tset_matrix.py` 用法串、`night_run.py`
epilog、`Makefile` 接线、`Process-07/09` 两节、`docs/TestReports` 两册格式、
根 `README.md` 一行。

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|---|
| 1 | R2 用「现场生成」词判定会把凡例误判为快照 | ✅已修 | 改为正文含 marker 注释判定；首行提到该词但非 marker 亦 FAIL | 门控 3 册/1 快照 PASS；self-test R2 注入红 |
| 2 | 生成器 markdown 仍写绝对运行期路径，重生成会把违规带回 | ✅已修 | `_display_path`（仓库内相对 / 否则 basename）+ 首行 marker + 册头四项 | 合成调用 `write_markdown` 产物过门控（1/1 PASS） |
| 3 | Process-09 与 README §2「基线原文不入库」措辞可能冲突 | ✅已修 | 区分「原始数据不入库 / 被引 summary 升格 refs」 | README §1–§4 逐条对照一致 |
| 4 | `--self-test` 默认目录若落在任务 worktree 会污染工作树 | ✅已修 | 默认改任务号同级 `…-selftest` 目录 | `--self-test` 5 项全 PASS，`git status` 无新增 |
| 5 | 4 类注入需真实树可达（非仅自检） | ✅已验 | 证据脚本对真实册注入 4 次 | 4 次均 rc=1；`cp`+md5 还原后回绿 |

判决：未修 finding = 0。

### 第 1 轮 reviewer 验收

**重跑记录（本人执行，真实输出/退出码）**
- 门控基线 `python3 tools/infra/check_test_reports.py` → `PASS (3 report(s), 1 snapshot(s))` rc=0；`--self-test` 5 项（基线+4 类注入）全 PASS rc=0。
- 证据脚本 `./run.sh`（运行期证据目录）→ `m13-testcases-004 evidence: PASS` rc=0，含 4 类**真实树**注入各 rc=1、`cp`+md5 还原 md5 相等、还原后回绿。
- reviewer 独立注入 8 例（cp+md5 还原，终态 `git status` 干净）：全删快照标记→`R2 zero snapshot(s) (vacuous)` rc=1；首行含「现场生成」非 marker→rc=1；二级子目录 `parity/`→rc=1；正文写具体 `.work` 路径→rc=1；册头删「复现」→rc=1；零报告→rc=1；目录缺失→rc=1；glob 形态 `/tmp/**` 文本→PASS（R1 按设计不命中）。
- 回归：`make -k check` rc=2，**唯一红** = `check-patch-tree`（3 条 gem5 断言 ⑨⑨⑥），log 中 `check-test-reports: PASS` 且无其它 `Error`/`[FAIL]`；`make check-modules`(L2) rc=0；`check-tasks` / `check-knowledge-refs` / `check-run-artifacts` 各 rc=0。
- 红归属核实（不背锅也不误放行）：主工作树 master 复跑 `check-patch-tree` 同 3 条 rc=1；共享 `.work/source/gem5`（`m13-gem5-003` 的 `.work` 软链到主树）HEAD `304f55f`（今日 06:45 `dadao: gem5 patch series`，reflog 有 commit/reset 循环），该任务书在其 worktree 副本状态 `待验收`、证据进程在跑，其 `semihosting.cc`/`process.cc` 改动未进 master 补丁集 ⇒ **外部红**，与本任务 12 文件零交集。
- 算法未动：三脚本 `git diff HEAD^ HEAD` 共 8 个 hunk，全在 docstring/`_display_path`/`write_markdown` 渲染/help/epilog；把 `HEAD^` 旧版就地副本对跑，`run_parity`/`se_tset_matrix --self-test` 输出**逐字节相同**，`--help` 仅程序名与帮助文差异。
- 数据完整：矩阵册 `## Counts…` 段 md5 `a257abd8fdbb369964e3db4fdd542e20` 迁移前后相同；全量变更行仅 marker + 册头 4 项 + 5 行 identity/2 行 evidence 路径→basename（各 md5/size 数值原样）；凡例仅册头 4 项、来源句、示例路径。
- 引用：`git grep tests/parity` 10 行全在白名单（归档 1 / discussing 1 / 任务书 6 / `docs/README.md` 2），白名单外 0；`tests/parity/` 不存在。
- 对账：提交 12 文件 = 完成区 11 条 + 任务书自身（惯例不自列，抽查无任务自列）；完成区 26 行、无 `/tmp`/`/home`/`.work` 运行期路径；`git status --porcelain -uall` 干净，无本人注入残留。

**约束核验**：临时目录、不提交、只动任务书范围、证据脚本、注入还原纪律（cp+md5，未用 checkout/restore）均守住；L2 与三个单检 rc=0；L1 红已核实归属外部。

**阻断 finding（1）**：R3 声称「无日期」但**未实现**——注入 `docs/TestReports/M11-2026-11-10-凡例.md` → `PASS (4 report(s), 1 snapshot(s))` rc=0；而 `check_test_reports.py` docstring L14、FAIL 文案 L103（`(M<digits>, no date, no whitespace)`）、`Makefile` L1203 注释、`docs/Process-07 §1.1` 登记行均写「无日期」⇒ 规范/门控自述与实际断言不一致（README §1「不带日期（必须）」无机械强制）。修法二选一：① `NAME_RE` 增日期拒绝 + `--self-test` 补一例可达 FAIL；② 四处删「无日期/no date」。修后重跑门控、`--self-test`、证据脚本。
（非阻断随改：完成区「任务书 3」现为 6 行——写入时任务书自身尚无后 2 处，属计数笔误。）

**判决：Needs Revision**（仅上述 R3 描述↔实现不一致；其余验收项在本人重跑下全绿）。

### 第 2 轮 engineer 返工（R3 no-date）

| # | reviewer finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|---|
| 1 | R3 自述「无日期」但实现未拒绝 `M11-2026-11-10-凡例.md`（阻断） | ✅已修 | `check_test_reports.py` 增 `NAME_DATE_RE = 20YY-MM-DD|20YYMMDD`，R3 命中 ⇒ FAIL；docstring 与 FAIL 文案同步为「no date / 写入册头」；`--self-test` 补 `R3 date in file name` 一例 | 注入 `M11-2026-11-10-凡例.md` → `[FAIL] R3 … file name must not carry a date` rc=1；删文件后回绿 |
| 2 | 完成区「任务书 3」行数笔误（非阻断） | ✅已修 | 按现场 `git grep` 统计改为 7（本册 6 + 历史 `m12-integ-001` 1） | 见完成区「验收结果」 |

返工复跑（真实输出）：
- `python3 tools/infra/check_test_reports.py --self-test` → 6 项全 PASS（基线 + R1 + R2 + R3 名称 + R3 日期 + R4）rc=0。
- `make check-test-reports` → `PASS (3 report(s), 1 snapshot(s))` rc=0。
- 证据脚本（真实树注入，含新增日期例）→ `m13-testcases-004 evidence: PASS` rc=0；R3 日期注入 rc=1，`cp`+md5 还原后回绿。
- 现有三册均不含日期，R3 新断言对其零影响（门控 PASS 同上）。
- 另修一处门控红：reviewer 记录里的具体 `.work` 路径表述触发 `check-knowledge-refs`，改为文字描述（结论不变，未改判决）⇒ rc=0。

判决：本轮 finding 全部已修；任务保持 `待验收`。

### 第 2 轮 reviewer 验收

**重跑记录（本人执行，真实输出/退出码）**
- 日期拒绝 3 形态注入（`M11-2026-11-10-凡例.md` / `M11-20261110.md` / `M12-2026-01-02-三平台矩阵.md`）各 → `[FAIL] R3 … file name must not carry a date (put it in the header)` rc=1；`cp`+md5 还原后回绿 `PASS (3 report(s), 1 snapshot(s))` rc=0，四册 md5 与注入前逐一相等、`git status` 干净。
- 不误伤：`M13-长尾计时-2026.md`、`M14-差分结论-v2.md` 与现有 4 文件 → PASS（`5 report(s)`）rc=0；正则单测：`2026Q1`/`20261`/`202611`/`case2026x` 不命中，仅 8 位连写或 `20YY-MM-DD` 形态命中（唯一边缘：`M13-2026-2027.md` 类「20YY-YY-YY」被命中，属日期同形，可接受）。
- 独立反例：把 `NAME_DATE_RE` 改为永不命中 → `--self-test` 的 `R3 date in file name` 由 rc=1 变 **FAIL（actual 0）**、真实树日期注入变 PASS ⇒ 断言确由新正则驱动（非恒真）；`cp`+md5 还原（`fce4ba52…` 相等）后 self-test 回 6/6 PASS、门控回绿。
- `--self-test` 6 项现场逐项：baseline rc=0，R1/R2/R3 名称/R3 日期/R4 各 rc=1；5 个注入分别打 R1 正则、R2 首行、R3 `NAME_RE`、R3 `NAME_DATE_RE` 的 elif 分支、R4 关键词，各自独立合成树，互不重复。
- 证据脚本 `./run.sh` → `m13-testcases-004 evidence: PASS` rc=0（含真实树日期注入 rc=1 + `cp`+md5 还原回绿）。
- 回归：`make check-test-reports` rc=0（首次 rc=1 系**我方**与证据脚本并发竞态撞上其 R4 注入，串行复跑即绿；重试 1 次，记录在案）；`check-tasks` / `check-knowledge-refs` / `check-run-artifacts` / L2 各 rc=0。
- L1 `make -k check` rc=2，2 条红**均外部**：① `check-patch-tree` 3 条 gem5 断言 —— 主工作树 master 复跑同 rc=2，共享 gem5 源树 HEAD `304f55f`（今日 06:45）系 `m13-gem5-003`（状态 `待验收`）改动、未进 master 补丁集；② `check-milestones-fresh` R1 报 `m13-testcases-003` 台账在「待开始」—— 本分支落后 master 9 笔（含 `台账：m13-testcases-003 启动（进行中）`），主工作树复跑 rc=0；另 `check-temp-dirs` 首轮曾红（他任务证据目录 2.2 h，现场已清理），复跑已绿。本任务门控在 log 中 `check-test-reports: PASS`。

**约束核验**：本轮改动 2 文件（`check_test_reports.py` + 任务书）与完成区「修改文件」对账一致（任务书按惯例不自列）；完成区 26 行、无运行期路径；`git status` 干净、无我方提交（HEAD `08834fbf` 为 architect 提交）；我方注入全部 `cp`+md5 还原。engineer 将我第 1 轮记录中一处具体运行期路径改为文字描述（判决与证据未变，该形态原会触发 `check-knowledge-refs`），已核 rc=0。非阻断 nit：`Process-07`/`Makefile` 仍写「四类注入」（现为 4 类 5 例，语义仍成立）、脚本 docstring 只列 2 种日期形态而实现更严（超集）。

**判决：Accepted**（第 1 轮唯一阻断已实证消除；L1 两条红逐条核实为外部，非本任务引入）。

## 完成区

**测试结果**：`make check-test-reports` PASS（3 report(s)、1 snapshot(s)，现场统计）；`--self-test` 6/6 PASS（基线 + R1/R2/R3 名称/R3 日期/R4）；证据脚本 rc=0；L2 `make check-modules` rc=0；`make -k check` 唯一红 = `check-patch-tree`（外部：共享 gem5 源树被在途任务推进；主工作树 master 复跑同 3 条 rc=1）；`check-tasks` / `check-knowledge-refs` / `check-run-artifacts` rc=0。

**修改文件**：
- `tools/infra/check_test_reports.py`（新增 L1 门控）
- `Makefile`（`.PHONY` + `_locked-check` + help + 目标）
- `docs/Process-07-门控分层规范.md`（§1 L1 组成 + §1.1 登记行）
- `docs/Process-09-测试组织规范.md`（新增 §15「测试报告归属」）
- `tools/testcases/parity/run_parity.py`（markdown 首行/册头/路径渲染 + help/docstring）
- `tools/testcases/parity/se_tset_matrix.py`（用法串/`--compose-out` help 指向新目录名）
- `tools/testcases/night_run.py`（epilog 指向 `docs/TestReports`）
- `tools/testcases/parity/README.md`（SE 段示例 + 入库快照说明）
- `docs/TestReports/M11-三平台一致矩阵.md`（格式：首行 marker、册头四项、7 行运行期路径→文件名；md5/计数未改）
- `docs/TestReports/M11-三平台一致矩阵-凡例.md`（格式：册头四项、来源句、示例名→新目录名）
- `README.md`（一致性矩阵路径改为 `docs/TestReports/…`）

**验收结果**：
- 门控基线 `check-test-reports: PASS (3 report(s), 1 snapshot(s))`；R1/R2/R3 名称/R3 日期/R4 真实树注入各 rc=1，`cp`+md5 还原后回绿（日期例：`R3 … file name must not carry a date`）。
- 三工具 `--help` 均含 `docs/TestReports`；`run_parity --self-test` / `se_tset_matrix --self-test` PASS（算法未改）。
- `git grep tests/parity`：白名单外 0（归档 1、任务书 7（含历史 `m12-integ-001` 1）、`discussing.md` 1、`docs/README.md` 2）；`tests/parity/` 不存在。
- README §1–§4 ↔ Process-09 §15 逐条对照：命名 / 收不收 / 必备四项 / 禁止项 / 门控一致（§15 只登记落点并指 README 为真源）。

**新发现/坑**：快照首行 marker 与册头四项应由生成器直接输出（已在 `run_parity.write_markdown` 落地），否则「只 cp 不手改」会把运行期路径与缺失册头带回入库册；门控识别快照用 marker 注释而非「现场生成」词，避免凡例等说明册误判。

**遗留问题**：L1 的 `check-patch-tree` 外部红（共享 gem5 源树在途推进；master 复现同 3 条），需该任务收口后复跑 L1；`discussing.md` 的 `tests/parity` 残留归主会话修改（子代理不改该文件）；历史任务书与归档册的历史叙述按白名单保留。

#### 收尾（architect，2026-11-10 08:27）

- 第 1 轮 Needs Revision（R3 未实现「文件名不带日期」）；第 2 轮 **Accepted**：日期三形态注入全 FAIL、正常名不误伤（`M13-长尾计时-2026.md` 等 PASS）、self-test 6/6 各打不同分支。
- 交付：`docs/Process-09 §15` 归属节、`docs/Process-07 §1.1` 登记、`check-test-reports`（R1–R4，真实树 + 合成树双路注入）、`run_parity.py`/`se_tset_matrix.py`/`night_run.py` 输出对齐（算法未动，旧版对跑 `--self-test` 逐字节相同）。
- 数据完整性：M11 矩阵「Counts」段 md5 迁移前后一致；变更仅 marker/册头/7 行路径。
- 非阻断 nit：`Process-07`/`Makefile` 仍写「四类注入」而现为 4 类 5 例；脚本 docstring 列 2 种日期形态而实现是超集。
- L1 两条外部红（`check-patch-tree` 3 条 gem5 断言 = `m13-gem5-003` 在途；`check-milestones-fresh` = 分支落后 master 9 笔），主工作树复跑均不复现。
