# INTEG-061t: M11 里程碑核验与归档（无 m 后缀）

**模块**：integ
**项目里程碑**：M11
**依赖**：`TESTCASES-103t`、`TESTCASES-104t`、`INTEG-059t` 全部 `已验证`
**可并行分片**：否（核验与归档，单写者）
**状态**：已验证

## 背景

用户 2026-11-08 裁定：M11 的模块 `m` 册门控**取消**（选 B）；M11 收口判据 = **已知功能都实现 + 已知 bug 都解决 + 该做的验证都做完**，不要求回归跑（原「夜跑」）完成；M11 收口改为**立一个 integ 核验任务**（无 `m` 后缀）——「该检查任务状态检查任务状态，该归档归档即可」。本任务即该核验任务，**不新建 `m` 册**。

## 目标

### 1. 任务状态核验（机械）

- `make check-tasks`（含 `--strict`）：所有 M11 任务书 `**状态**` 与 `milestones.md` 表位置一致；漏收尾 = 0
- `make check-milestones-fresh`：分类一致 / 覆盖 / 已验证倒序 / 格式
- 逐个抽查「已验证」行对应的任务书：状态字段、完成区存在、审阅记录有判决
- 对 `待开始`/`进行中` 残留逐一给结论：并入 M11 归档、转入 M12，或明确登记为后续（写明理由与去向）

### 2. 里程碑判据复核（真实重跑）

- `make check-full`（L3）rc=0；`check-l3-report` rc=0
- 回归跑（原「夜跑」）**不是收口条件**（用户 2026-11-08）：若已有结果则复核落盘证据；未完成不阻塞，只在报告中记录状态
- QEMU ↔ gem5 双向一致性矩阵存在且与 059t 结论一致；`docs/TestReports/M11-三平台一致矩阵.md` 已重生成
- 已知 BLOCKED 项（picolibc `math_test` B7 浮点）在报告中保留且不计入通过数

### 3. M11 归档（按 `docs/Process-04`）

- 建 `.tao/archive/M11/`：`README.md` 五节齐全（结构与册字段以 `check_archive.py` 判定为准）
- M11 任务书 `git mv` 入 `.tao/archive/M11/<模块>/`；归档任务自身最后入档
- `issues.yaml`：提取 M11 阶段（≤ 达成日）`closed` 项 → `issues-closed.md`，活台账移除
- `milestones.md`：删除 ≤ 达成日的「已验证」行；`待开始`/`进行中` 行不删，随里程碑迁移或另立
- 里程碑断言：`milestones.md` 的 `项目里程碑 = M11` 保留至 M12 正式接管（切换动作不在本任务，如需切按 `m12-infra-001` 双台账口径）

## 验收标准

1. `make check-tasks` rc=0 且 `--strict` 漏收尾 = 0；`make check-milestones-fresh` rc=0
2. `make check-full`（L3）rc=0、`check-l3-report` rc=0；回归跑状态如实在报告中记录（不作为通过条件）
3. `make check-archive` rc=0（含新 M11 归档，`--self-test` 亦 rc=0）
4. `git mv` 后无任务书遗留于 `.tao/tasks/`（M11 已完成项）；`.tao/archive/M11/README.md` 五节齐备
5. 核验报告写明：M11 任务总数、已验证数、残留项去向、已知 BLOCKED 项
6. `make check`（L1）rc=0
7. 完成区 ≤30 行、无运行期路径

## 非范围

- 不新建 `m` 册；不改 `check_milestone_tasks.py`（m 册门控取消归 `m12-infra-002`）
- 不修 M11 期间遗留的语义缺口（如需修复另立任务，本任务只登记去向）
- 不动 M12 台账与 M12 任务书

## 完成区

**测试结果**：M11 任务 108（已验证 106：gem5 32 / infra 25 / integ 8 / llvm 1 / qemu 8 / spec 16 / testcases 16）；106 册逐册核验状态字段/完成区/审阅记录齐备（GEM5-002t/003t/032t 无显式 `Accepted` 文本，分别为自审、architect 档位、只读定位记录，均有判决与证据）。门控：`check-milestones-fresh` rc=0；`check-archive` rc=0（`--self-test` 14/14）；L3 `check-full` 8/8 rc=0（`make` 首跑戳 `20261109T081545Z`；持久日志目录重跑同清单 8/8、戳 `20261109T082411Z`）；`check-l3-report` rc=0；L2 `check-modules` rc=0；L1 `make check` rc=2，唯一红 = `check-patch-tree`（chipyard 在途任务引起，主工作树同红，非本任务改动；排除该项后 L1 rc=0）；`check-tasks --strict` 收尾前漏收尾 0，置 `待验收` 后唯一命中本任务（待验收固有，architect 置 `已验证` 后归零）。
**修改文件**：`.tao/tasks/**` 106 册 `git mv` → `.tao/archive/M11/<模块>/`（`R100`）；新增 `.tao/archive/M11/README.md`、`m11-retrospective.md`、`issues-closed.md`；`.tao/knowledge/issues.yaml`（14 条 closed 移入快照，留 6 open）；`tools/infra/check_archive.py` 与 `docs/Process-04-里程碑归档规范.md`（模块白名单与任务号正则加 `gem5`，越界披露）；本任务书。
**验收结果**：
- 归档：106 册按 7 个模块子目录 `git mv`；README 五节齐备、§1 计数与目录一致、§2 流水 106 行；issues 快照 14 条；`.tao/tasks/` 无其它 M11 已完成册。
- 残留去向：`GEM5-033t`（B7 注销，`待开始`，留活待用户裁定）；本任务 `INTEG-061t`（验收后由 architect 最后 `git mv` 入 `integ/`）；6 条 M10 之后的任务留活台账、不入本归档（其中 5 条标「M10 后（维护）」、`INFRA-113t` 为「M10 后（清理，不纳入 M10 收尾）」）。
- 已知 BLOCKED：picolibc `math_test` B7 浮点仍记 BLOCKED（`GEM5-015t`），根因已由 `GEM5-032t` 定位为「可注销」，注销待 `GEM5-033t`；不计入通过数。open issue 6 条（`ISS-345`/`ISS-355`–`ISS-359`）留活台账。
- 矩阵与回归：`docs/TestReports/M11-三平台一致矩阵.md` 存在（FS tiny/inst、SE static+dynamic），与 `INTEG-059t` 结论一致；回归运行末次完整报告 2026-11-05-13（4/4 rc=0），2026-11-06-09 无产物，`TESTCASES-105t` 后未跑完整集（用户 2026-11-08 裁定非收口条件）。
- 证据：一键证据脚本（运行期证据目录）27/27 PASS，含「删 README 节 ⇒ `check-archive` FAIL ⇒ `cp`+md5 还原 ⇒ 回绿」注入自检。
**新发现/坑**：① `check_archive` 的模块白名单与任务号正则不含 `gem5`，M11 首次归档 gem5 模块必须机械扩展（已改，不改归档语义）；② 工作树内跑 L3 时 manifest 记逻辑临时路径，工作树清理后 `check-l3-report` 不可复核（上一戳即因此红）⇒ 以持久日志目录重跑并落新戳；③ `check-run-artifacts` 要求运行期日志目录新增文件命名合规（任务号前缀 + `.log/.json/.txt`），数据文件须先改名。
**遗留问题**：① `milestones*.md` 未改（派单硬约束）：architect 需删除 **106 条 M11 `已验证` 行**（保留 6 条 `M10 后` 行与 `GEM5-033t`/`INTEG-061t` 行）；② 自归档时 README §1 `integ 8→9` 并在 §2 追加 `INTEG-061t` 行；③ `GEM5-033t` 待用户裁定后派工；④ 6 条 open issue 转 M12/M13 处理；⑤ `.tao/README.md` 的「M1–M10」归档列表与 `MEMORY.md` 归档指针需 architect 顺带更新。

## 审阅记录

### 第 1 轮 engineer 自审

**范围**：106 册归档字段与 `git mv` 结果、M11 README/回顾/issues 快照、`issues.yaml` 删除边界、`check_archive.py`/Process-04 扩展、门控重跑。
**方法**：逐册脚本核验（状态/完成区/审阅记录）；`check-archive` 正反例注入；L3/L2/L1 真实重跑并按 rc 逐条对齐；归档 ID 集合与流水集合现场比对。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `check_archive` 白名单/正则不含 gem5 ⇒ 归档必红 | ✅已修 | `MODULES` 与文件名正则扩 `gem5`/数字前缀；Process-04 §5 同步 | `check-archive` rc=0、`--self-test` 14/14 |
| F2 L3 manifest 记临时逻辑路径，工作树清理后不可复核 | ✅已修 | 以持久日志目录重跑 L3，新戳 `20261109T082411Z` | manifest 8 行日志路径均在持久证据目录；`check-l3-report` rc=0 |
| F3 运行期数据文件命名不合 `check-run-artifacts` | ✅已修 | 数据文件加任务号前缀并改 `.txt/.json` | `check-run-artifacts` rc=0 |
| F4 `check-patch-tree` 红（chipyard） | ⏸外部 | 不改共享组件源 | 主工作树同红；L1 排除该项后 rc=0 |
| F5 `check-tasks --strict` 命中本任务 | ⏸预期 | 不改完成区/状态约束 | 收尾前 0；置待验收后仅本任务，architect 置已验证后归零 |
| F6 归档任务自归档未完成 | ⏸待收尾 | — | 完成区「遗留问题」列出 architect 动作 |

**判决**：F1–F3 已修并复验；F4 为已核实外部红、F5/F6 属收尾态动作；归档与门控证据齐全，状态置 `待验收`。

### 第 1 轮 reviewer 验收

**重跑记录（reviewer 独立执行，全部在本 worktree 内）**
- `python3 tools/infra/check_archive.py` ⇒ `结果: PASS` / `M11: 册 106；清单 gem5=32/infra=25/integ=8/llvm=1/qemu=8/spec=16/testcases=16；流水 106 行`，rc=0；`--self-test` ⇒ `自检结果: 14/14`，rc=0。
- 独立统计 `ls .tao/archive/M11/*/*.md | wc -l`=106（分册 32/25/8/1/8/16/16）；README §1–§5 标题齐备；流水 ID 集合 `diff` == 磁盘册 ID 集合（各 106、无重复），106 行「时间/一句」与 `milestones.md` **0 差异**（可机械复核）。
- `git diff --cached --raw` ⇒ `renames=106 blob_diff=0`（新旧 blob SHA 全等，内容零改动；5 个抽查同结论）；`--diff-filter=D`=0；`.tao/tasks` 余 M11 册 2（`GEM5-033t` 待开始 / `INTEG-061t` 待验收），字段核 106+2=108。
- 改动面：`check_archive.py` +3/-3（`MODULES` 增 `gem5`；ID 正则两处 `[A-Z]+`→`[A-Z][A-Z0-9]*`）、`Process-04` +2/-2（仅 §5），**未放宽任何断言**；`--self-test` 14 例基线仅 `INFRA-001t`，**未覆盖 gem5/数字前缀扩展**。
- issues：HEAD 20 条 → 移除 14 条（HEAD 中状态全 `closed`）与 `issues-closed.md` 14 个 `ISS-*` **集合全等**；余 6 条全 `open`；`check_issues` rc=0（`6 open, 0 closed`）。
- 门控：`check-milestones-fresh` rc=0（M11/M12/M13 三册 PASS）；`check-tasks` rc=0、`check_tasks.py --strict` **rc=1 / 漏收尾=1（唯一命中本任务）**；`make check-modules` rc=0；`make -k check` **唯一红 = `check-patch-tree`（assertion ⑨）**，主工作树 `master` 同命令 **rc=1 同错** ⇒ 外部红；`check-run-artifacts` rc=0。
- L3：reviewer 自跑 `make check-full` ⇒ `check-full: PASS (8/8 member(s) green)`、`[exit marker] rc=0`，rc=0；`make check-l3-report` rc=0（manifest 8 行 rc 全 0）。reviewer 自有戳已迁出 shared `l3/` 根（保留于运行期临时目录），最新戳复位为 engineer 的持久戳 `20261109T082411Z`，复跑 `check-l3-report` rc=0。
- 证据脚本：逐条审 `.work/evidence/INTEG-061t/run.sh`（27 断言均有可达 FAIL 路径、无两支同结果、计数现场统计）⇒ 重跑 rc=0、27/27，与 engineer 日志 **逐行 IDENTICAL**。
- **独立反例注入**（改 `.tao/archive/M11/integ/INTEG-059t-*.md` 状态 `已验证`→`待验收`，非脚本自带用例）⇒ 同脚本 **rc=1 / 3 条 FAIL**（check-archive、check-milestones-fresh、还原后回绿）⇒ `cp`+md5 还原（`f001076f…` 相等）⇒ 重跑 rc=0；证据文件 md5 集合复原未变。
- 快照对账：审查前后 `git status --porcelain -uall` 均 **113 行**（106 R100 + 3 A + 4 M），0 未暂存、0 未跟踪，与完成区「修改文件」逐项一致，无 `git add -A` 痕迹（0 删除、0 越界路径）。

**约束核验**：完成区 10 行 ≤30、全文无运行期路径 ✅；未触碰 `spec/contracts/Makefile/tests/components` ✅；`milestones.md`/`.tao/README.md`/`MEMORY.md` **确未改** ⇒ 第 6 项台账动作**尚未执行**（应由 architect 收尾做）✅。
**偏差（engineer 已披露、reviewer 已复现）**：① 验收标准 1 的 `--strict 漏收尾=0` 现为 1（本任务待验收固有，architect 置 `已验证` 后须复跑至 rc=0）；② 验收标准 6 的 L1 现 rc=2（唯一红 chipyard `check-patch-tree`，主工作树同红、非本任务改动，排除后 L1 全绿）。
**文档级 finding（不阻断）**：a) `check_archive.py` docstring 仍写「只允许 6 个模块名」且未列 `gem5`；b) `--self-test` 未补 gem5/数字前缀用例；c) README §2 `GEM5-032t` 一句改动=`3–5 h`（`milestones.md` 原值照搬，非本任务引入）；d) 完成区称 6 条 `M10 后（维护）`，其中 `INFRA-113t` 实为 `M10 后（清理，不纳入 M10 收尾）`。
**收尾顺序建议（architect）**：① 显式 staging 本审阅记录并在任务分支 commit → ② `/complete` 置 `已验证` 后**复跑 `check_tasks.py --strict`（期望 rc=0）** → ③ 删 `milestones.md` 106 条 M11 `已验证` 行（留 6 条维护行 + `GEM5-033t`/`INTEG-061t`）并跑 `check-milestones-fresh` → ④ 自归档 `INTEG-061t` 入 `integ/`、README §1 `integ 8→9` + §2 追加该行，跑 `check-archive` → ⑤ 更新 `.tao/README.md` 归档列表与 `MEMORY.md` 指针（M1–M10 → M1–M11）→ ⑥ L1/L2/L3 全绿后 `merge --squash`。
**判决**：**Accepted**

#### 收尾（architect，2026-11-09 17:38）

- 判决 **Accepted**（reviewer 16:57 完成；完成通知未送达，主会话按盘上事实收口）。
- 结构核验：106 项 `R100`、blob 零差异；README 五节 + 流水 106 行与磁盘/台账 0 差异；issues 14 条快照与移除集合全等；`check_archive --self-test` 14/14。
- 4 条 finding：a) `check_archive.py` docstring 已补 `gem5`；c) README §2 `GEM5-032t` 一句改动已改正；d) 完成区「6 条维护行」已改为准确表述；b) `--self-test` 未覆盖 gem5/数字前缀 —— **记录不改**（扩展会改动基线 14 例，留后续）。
- 自归档本任务入 `M11/integ/`，README §1 `integ 8→9`、§2 追加本行。
