# INFRA-129t: 清理任务书中的运行期证据引用（fresh clone L1 可绿）

**模块**：infra
**项目里程碑**：M11
**依赖**：无（与 `GEM5-030t` 文件域不重叠）
**状态**：已验证

## 背景与事实

新节点是 **fresh clone**，跑 `make check`（L1）时 `check-knowledge-refs` 失败：

```
结果: FAIL (20 悬空 `.work/**` 引用)
```

原因是若干任务书/知识文件里写了**具体运行期证据文件**（`<运行期目录>/evidence/<任务>/run.sh`、`<运行期目录>/log/...`）。这些文件只在跑过该任务的机器上存在，fresh clone 上没有 ⇒ 判悬空。主控机之所以通过，只是因为本机恰好有这些文件。

这违反「任务书不得写运行期路径」，也让新机器无法直接拿 L1 绿。

## 目标

把下列位置中**指向运行期证据/日志的具体文件或目录引用**，改成「运行期证据（未归档）」「运行期日志（未归档）」或等价措辞；保留原句的结论与上下文，不改判据、不改结论。

- `.tao/knowledge/MEMORY.md:78`
- `.tao/knowledge/refs/DADAO-0628-对照分析.md:12,76`
- `.tao/knowledge/refs/GEM5-021t-baseline-findings.md:60`
- `.tao/tasks/gem5/GEM5-019t-SYS_ELAPSED与TICKFREQ时钟一致.md:212`
- `.tao/tasks/infra/INFRA-121t-运行期日志命名清理.md:62`
- `.tao/tasks/integ/INTEG-053t-cfxha重编号与作用域.md:199,214,224`
- `.tao/tasks/spec/SPEC-184t-Node-D10与ISS-340收口.md:155,158,183`
- `.tao/tasks/spec/SPEC-185t-spec非spec引用清理.md:87,113,125`

注意：`check-knowledge-refs` 对**构建树/源码树**前缀有豁免；只处理「证据/日志」这类具体运行期路径，不要顺手改豁免项，也不要改 `spec/` 与 `contracts/`。

## 范围 / 非范围

**在范围内**：上述文件与行、本任务书、`milestones.md`。

**不在范围**：门控逻辑（`check_knowledge_refs.py` 不改）、spec/contracts、任何代码、其它任务书。

## 验收标准

1. **模拟 fresh clone**：在仓库外临时目录用 `git archive HEAD`（或 `git clone` 到临时目录）导出一份**不含运行期目录**的树，对这份树跑 `python3 tools/infra/check_knowledge_refs.py --root <临时树>` ⇒ **rc=0、悬空 0**。
2. 主工作树 `make check`（L1）rc=0。
3. 逐行核对：只改措辞，报告/结论/数字不变（给出 `git diff` 统计与抽样对照）。
4. 完成区 ≤30 行；状态 `待验收`。

## 说明

- 这是「让新机器可直接 L1 绿」的前置清理；不新增文档、不改门控。
- 若某处引用其实是**长期证据**（例如确实要入库的快照），改为指向仓库内可跟踪路径，而不是删掉结论。

## 用户裁定（2026-11-07）

- **问题**：清理后 fresh clone 上 `具体路径(校验)=0`，触发 `check_knowledge_refs.py` 的 `checked == 0` 空转判据（rc=1）。`.work/**` 整体被 gitignore ⇒ 正确清理后必然没有可校验的具体路径，验收 #1 的「rc=0」与「门控不改」互斥。
- **真实问答（architect 向用户提问后得到）**：选项 **A = 「按扫描到的引用数判空转」**；用户选择 **A**。
- **落点**：(A) 面空转条件改为 `found == 0`（没有扫描到任何 `.work/**` 引用才判空转）；悬空判据与 (B) 面不变；门控 docstring 同步。
- **更正说明**：上一版任务书曾写「用户原话：最小修正空转判据（推荐）」，该内容**无 session 问答证据**；architect 已撤回上一版门控改动并更正，本版按上述真实问答复核后重新应用。
- **范围增补（同类悬空，一并清理）**：`AGENTS.md` 5 处、`GEM5-029t` 3 处。fresh clone 实测 23 处 = 背景所述 20 处 + 上述 3 处（任务书列举的 15 行即 20 处中的 15 条，另 5 条在 `AGENTS.md`）。

## 完成区

**测试结果**：fresh clone 模拟（`git archive HEAD` + 本任务未提交改动 patch，确认无运行期目录）⇒ 门控 rc=0、悬空 0、扫描引用 41 条（占位 25 / 前缀 1 / 豁免 14 / 删除语境 1 / 具体校验 0）；反例注入（悬空路径、移除全部运行期引用）均 rc=1 且还原回绿。本机 L1 见「遗留问题」。
**修改文件**：`AGENTS.md`、`.tao/knowledge/MEMORY.md`、`.tao/knowledge/refs/{DADAO-0628-对照分析,GEM5-021t-baseline-findings}.md`、`.tao/tasks/{gem5/GEM5-019t-SYS_ELAPSED与TICKFREQ时钟一致,gem5/GEM5-029t-SE-syscall语义对齐,infra/INFRA-121t-运行期日志命名清理,integ/INTEG-053t-cfxha重编号与作用域,spec/SPEC-184t-Node-D10与ISS-340收口,spec/SPEC-185t-spec非spec引用清理}.md`、`tools/infra/check_knowledge_refs.py`、本任务书、`.tao/knowledge/milestones.md`。
**验收结果**：清理范围（11 个既有文件）`git diff --shortstat HEAD -- <上述 11 文件>` = `11 files changed, 29 insertions(+), 27 deletions(-)`；本任务书与 `milestones.md` 另计（13 文件合计 60+/29−）。逐文件仅 1–3 行措辞替换、无结论/数字删除（抽样：MEMORY 仅将日志目录写法改为「运行期日志目录（可删、未归档）」；INTEG-053t「30/30」、SPEC-184t「62/62」、SPEC-185t「19/19 / 223→0」全部保留；AGENTS 仅目录措辞）。门控改动仅空转判据 `checked==0`→`found==0`，悬空与 (B) 面逐行未动。
**新发现/坑**：① fresh clone 的运行期引用悬空清理到 0 后必然触发 `checked==0` 空转，二者互斥（真实问答选 A，见上）；② 上一版任务书引用的「用户原话」无 session 问答证据，已由 architect 更正并撤回门控改动，本轮按真实问答复核后重应用；③ 并发 `GEM5-030t` 把其未提交的 gem5 补丁 apply 进共享源树，`check-patch-tree` 与本任务分支的补丁集失配，`make check` 因此红（与本任务改动无关）。
**遗留问题**：**L1 `make check` 未能在本环境取绿**：rc=2，唯一失败项 `check-patch-tree`（10 处 gem5 源树/补丁失配，现场已保留）；同 target 在未含本任务改动的 `master` 工作树同样 rc=2 同 10 处，且 `GEM5-030t` 正在使用共享 gem5 源树（其工作树 `components/gem5/patches/**` 未提交改动 + 活跃 `gem5.opt` 进程），故判定为外部并发占用，非本任务引入。其余 49 个 L1 target 逐项 rc=0（含 `check-knowledge-refs`、`check-milestones-fresh`）；本任务 diff 不含 `components/`，待 `GEM5-030t` 补丁集收口并与其共享源树一致后，在含该补丁集的 master 上重跑 L1 即应转绿。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-07）

自主逐行审查 13 个改动文件 + 门控改动 + 证据脚本。结论：措辞替换未动结论/数字（逐行核对），门控只改空转判据、悬空与 (B) 面未动；证据脚本两条注入均实测可达 FAIL 且 `cp`+md5 还原回绿，未用 git 还原。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| fresh clone 清理到 0 后触发 `checked==0` 空转，与验收 #1 互斥 | ✅已修（真实问答选 A） | (A) 面空转判据 `checked==0`→`found==0`；悬空判据不动 | fresh tree rc=0；移除全部运行期引用注入仍 rc=1 `vacuous` |
| 清单外同类悬空 8 处（AGENTS 5 + GEM5-029t 3） | ✅已修 | 同类措辞清理，不做其它改动 | fresh tree 悬空 23→0、具体校验 0 |
| 本机 L1 被并发 `GEM5-030t` 占用共享源树阻塞 | ⏸延后（外部） | 不改组件/共享源树；保留现场 | master 同 target 同 10 处；其余 49 target rc=0 |
| 完成区 diff 数字与实际不符 | ✅已修 | 按 `git diff --shortstat` 分区统计 | 11 files / 29+ / 27−（另本任务书/台账） |

#### 第 1 轮 reviewer 验收（2026-11-07）

**方式**：任务 worktree（分支 `INFRA-129t`，HEAD `f4c9ea39` + engineer 未提交改动）独立重跑；不 commit/push；分析 13 个改动文件全文 + 门控 diff + 证据脚本逐行 + `check_milestones_fresh.py` 口径。注入一律 `cp` 备份 + md5 对账（未用 git 还原）；开工/收尾 `git status -uall` 与 13 文件 md5 **逐个相同**、无 `??` 残留。

**重跑记录（本人真实输出/退出码）**
- fresh clone：`git archive HEAD` + `git diff HEAD` patch 应用到仓库外临时树，确认无运行期目录 ⇒ `check_knowledge_refs.py --root <临时树>` **rc=0、悬空 0、具体路径校验 0**（引用总数 41：占位25/前缀1/豁免14/删除语境1/校验0）。
- 主树 `check-knowledge-refs` **rc=0**（非 vacuous）；`check-milestones-fresh` **rc=0**（91 行、状态一致）。
- 反例 A（注入悬空具体路径）：**rc=1、`悬空: 1`**；`cp` 还原后 md5 `d548c5b2…` 前后相等 ⇒ **rc=0**。
- 反例 B（临时树移除全部 `.work/` 引用）：**rc=1**、`FAIL (vacuous: no .work/** refs scanned)`。
- (B) 面回归（注入 `ADR-9999 D1`）：**rc=1、`目标文件不存在`** ⇒ (B) 判据未被波及。
- 证据脚本重跑：`run.sh` **rc=0**，11 项 CHECK 全 PASS、L1 记 BLOCKED（外部）。
- **独立注入（改被测产物，非脚本自检）**：向任务书追加悬空具体路径 ⇒ 重跑同一 `run.sh` ⇒ **rc=1**（fresh rc=1 悬空1、主树 rc=1，共 6 项 FAIL）⇒ `cp`+md5 还原（与开工快照逐个相等）⇒ 重跑 **rc=0** 回绿。
- L1：任务 worktree `make check` **rc=2**，唯一失败 `check-patch-tree` 10 处（gem5 源树/补丁失配，断言⑥/⑨，5 文件）；同 target 在**未含本任务改动**的 master（HEAD `0712ec69`、状态干净）同样 **rc=2、同 10 处** ⇒ 外部并发（`GEM5-030t` 活跃进程占用共享 gem5 源树），不判本任务失败；其余 49 个 L1 target `make -k` 逐项 **rc=0**（0 条 Error）。

**约束核验**
- 只改措辞：逐行比对 11 个清理文件，改动行数字序列除「路径内任务号随路径删除」与状态/时间行外全等；`30/30`、`62/62`、`19/19`、`223→0`、`2815/7/2810` 等结论数字均保留。`spec/`、`contracts/`、其它门控脚本 **0 改动**。
- 门控：diff 仅 2 个 hunk（docstring + (A) 空转条件 `checked==0`→`found==0` + 注释/文案），悬空判据与 (B) 面代码逐字未动。
- 完成区 5 行 ≤30、无运行期具体路径；`milestones.md` 行 `待验收` 与任务书一致。
- 23 处构成实测：任务书所列 15 处 + `AGENTS.md` 5 处 + `GEM5-029t` 3 处 = 23（新节点所报 20 = 15 + `AGENTS.md` 5）。
- **用户裁定节**：已改为「真实问答（architect 向用户提问后得到）：选项 A = 按扫描到的引用数判空转；用户选择 A」+ 更正说明；全文仅在更正语境引用旧文案并标注「无 session 问答证据」，**不再声称未经证实的原话**。

**Findings（非阻断，交 architect 收尾）**
1. 完成区「扫描引用 41 条（占位 25…）」已过期：现场 **41 条（占位 25）**——后续新增「用户裁定」两处占位引用所致；rc/悬空判据不受影响，属完成区数字陈旧。
2. `.tao/tasks/spec/SPEC-185t-spec非spec引用清理.md:92` 仍含具体运行期日志路径，仅因该行含「删除」被记为删除语境而未校验（fresh rc=0 依赖该豁免）；不在本任务所列行内，建议另立任务清理。

**判决：Accepted** —— 验收 1/2/3/4/6 在我自己的重跑下全部通过；验收 5（L1）经归属核实为外部并发、其余 49 target 全绿，按任务口径不判本任务失败。

#### 收尾（architect，2026-11-07 20:28）

- F1：完成区引用总数已按 reviewer 实测改为 41（占位 25）；rc/悬空判据不受影响。
- F2：`SPEC-185t` 任务书另有一处具体运行期日志路径，因所在行含「删除」被跳过；登记为遗留，后续清理。
- 用户裁定 A（按扫描到的引用数判空转）已按真实问答落盘；原无 session 证据的「用户原话」已撤回并更正。
- 判决 Accepted，状态置 `已验证`。
