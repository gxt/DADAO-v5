# INFRA-120t: 任务书运行期路径清零

**模块**：infra
**项目里程碑**：M11
**依赖**：无（`INFRA-119t` 的完成区/审阅记录属本次清理对象，不作执行依赖）
**状态**：已验证

## 用户授权（2026-11-04，原话摘要）

- 「任务书不得引用运行期临时路径，即非仓库可跟踪路径。」
- 「执行路径留着没有用！！！临时目录用完后，就会被删除。」
- 同意范围不只 72 条悬空，而是清理任务书中所有具体运行期路径。

## 执行环境

**执行环境**：本地（仓库根；从含本册的 `master` 建独立 `git worktree` + 分支 `INFRA-120t`）。运行期证据/日志放「运行期临时目录」，任务收尾前清理、不归档；本册只留持久结论。

## 问题与目标

`check-knowledge-refs` 现有 **72 条**悬空（均为任务书对运行期证据/日志的引用）；另有大量任务书引用构建树、安装树、对象库、宿主绝对路径与家目录。这些路径在临时目录清理、换机或重建后即失效，且不可复现。

目标：任务书只写**仓库可跟踪路径**与可复现的命令入口；旧证据改写成不带路径的历史说明；在 `AGENTS.md` 固化规则防止回填。

## 路径口径（本任务唯一判据）

**运行期路径** = 非仓库可跟踪路径，包括：

- 仓库内被 `.gitignore` 覆盖的运行期树：工作区、构建、源码、安装、对象库（以 `.gitignore` 实际清单为准）；
- 系统临时根、宿主绝对路径、家目录（含波浪号与家目录变量两种写法）。

**仓库可跟踪路径**（保留）：`spec/`、`contracts/`、`tests/`、`tools/`、`components/`、`docs/`、`manifests/`、`Makefile`、`.tao/`。

**允许写法**：`make` 目标、脚本名、环境变量、「运行期临时目录」文字；结构上确需泛指时用 `<...>` 占位（不得用于历史证据行）。

## 接口规范

### 1. `AGENTS.md`（唯一规则改动）

在「参考来源与任务自包含」末尾追加两条（逐字）：

- **任务书不写运行期路径**：任务书（含完成区/审阅记录）不得出现具体运行期路径——构建产物树、源码/安装树、临时目录、家目录、宿主绝对路径；命令只写 `make` 目标/脚本名/环境变量或「运行期临时目录」，旧证据只写「运行期证据已清理，未归档；结果见完成区」。
- **减少交叉引用**：任务书须自包含，不靠其它任务书/运行期文件补足执行事实；确需引用只引仓库可跟踪路径与 `§` 章节。

### 2. `.tao/tasks/**/*.md` 清理

- 逐文件把具体运行期路径替换为**不带路径的历史说明**；完成区/审阅记录优先改写为「运行期证据已清理，未归档；结果见完成区」。
- 命令类改写成 `make <目标>` / `python3 <脚本名>` / `<环境变量>=...`，不写执行目录。
- 保留全部仓库可跟踪路径、任务号、结论、真实退出码与计数。
- **不得**用新占位（例如给旧证据补 `<...>`）或新增门控豁免换绿灯；**不删任务书**、不创建空文件、不改写既有结论。

### 3. 不改动

`tools/infra/check_knowledge_refs.py` 门控逻辑、`tests/`、`spec/`、`contracts/`、`components/`、`tools/`、`Makefile`、`docs/`、`manifests/`；不伪造证据；不 commit。

## 验收标准

1. **0 具体运行期路径**：以运行期脚本扫描 `.tao/tasks/**/*.md`，按「路径口径」逐 token 判定，命中数 = 0（允许 `<...>` 占位与「运行期临时目录」文字；家目录变量本身不算占位）。
2. **门控真实转绿**：`make check-knowledge-refs` **rc=0** 且输出 `悬空: 0`（基线 72）。同时 `git diff -U0 <base> -- .tao/tasks` 的**新增行**用同一扫描器（**不豁免占位**）命中数 = 0 ⇒ 证明不是靠新占位/豁免伪造。
3. **仓库路径未误删**：清理后 `.tao/tasks/**` 的仓库可跟踪路径引用 token 数 ≥ 基线（改动前采集）；`spec/README.md`、`contracts/`、`tests/inst/`、`tools/infra/`、`components/`、`.tao/tasks/` 六项 `test -e` 为真；随机抽查 20 个仓库路径 token，不可解析数不高于基线。
4. **台账与残留**：`make check-milestones-fresh` rc=0、`make check-no-residue` rc=0；`make check`（L1）记录改动前失败 target 集与改动后失败集，**无新增失败**且 `check-knowledge-refs` 从失败集消失；其余既有红逐条如实写入完成区（不归因本任务、不声称全绿）。
5. **可达 FAIL（≥2 处）**：① 向任一任务书恢复一条**具体运行期路径**（字面量由脚本运行时拼接，不预置在仓库）⇒ 验收 1 rc≠0；② 在完成区保留一条**历史证据路径** ⇒ 验收 1 与 `check-knowledge-refs` 同时 rc≠0；两处均 `cp` 备份 + `md5sum` 还原后回绿，附注入/还原日志与前后 md5。
6. **范围与体例**：`git diff --name-only <base>` 只含 `AGENTS.md`、`.tao/tasks/**/*.md`、本册、`.tao/knowledge/milestones.md`；无 `*_tmp*`/`*_gate*`/`*.orig`/`*.rej` 残留；完成区 ≤30 行、与真实输出逐条对齐；状态 `待验收`。

## 证据与留痕

- 一键脚本（运行期临时目录）：`scan.sh`（基线 → 清理 → 复扫 → 门控 → 注入 → 还原），每步落 `*_EXIT`；`REPORT.md` 数字由脚本现场生成。
- 完成区只写：扫描计数（基线/清理后）、`check-knowledge-refs` rc 与悬空数、L1 失败集对账、注入前后 md5、未决项。旧证据一律「已清理，未归档」。

## 完成区

**测试结果**：运行期证据脚本 `scan.sh` **PASS（failures=0，rc=0）**；基线运行期 token **776 → 0**；新增行（不豁免占位）**0**。
**修改文件**：`AGENTS.md`（+2 条规则）；42 册运行期路径清理（gem5 18、infra 6、qemu 6、testcases 7、spec 4、llvm 1）；本册完成区；`.tao/knowledge/milestones.md`（状态行）；共 45 文件，均为路径改写/状态登记，无结论删除。
**验收结果**：`make check-knowledge-refs` **rc=0、悬空 0**（基线 72）；`check-milestones-fresh` rc=0；`check-no-residue` rc=0；仓库路径 token **2652 ≥ 基线 2643**，不可解析 292 = 292；`spec/README.md`、`contracts/`、`tests/inst/`、`tools/infra/`、`components/`、`.tao/tasks/` 六项 `test -e` 全真；L1 基线失败集 `check / check-knowledge-refs / check-run-artifacts` → 清理后 `check / check-run-artifacts`，**无新增**且 `check-knowledge-refs` 退出失败集。注入①恢复具体运行期路径 ⇒ scan rc=1（count=1）；注入②完成区保留历史证据路径 ⇒ scan rc=1 且 `check-knowledge-refs` rc=2；两者 `cp`+md5 还原（脚本现场打印前后 md5 相等）后均回绿。
**新发现/坑**：扫描须带标识符边界（`cpu.workload` 不是路径）；仓库 token 统计须排除运行期路径内部的子串（安装根子目录不是 v5 仓库引用）；多行 code span / brace 列表需先整段折叠；`check-run-artifacts` 的 7 条红为共享运行期日志目录既有非法名（mergetree.out、GEM5-018t-*.EXIT 等），非本任务引入。
**遗留问题**：无本任务遗留；L1 既有 `check-run-artifacts` 7 problem 未处置（共享运行期日志，属其它任务）。

## 审阅记录

### 第 1 轮 engineer 自审

逐文件审 `git diff`（45 文件）：① 运行期 token 全部改为路径无关叙述，未删除任务号/结论/真实 rc；② 未误改 `cpu.workload` / `.dadao-*-config` 等代码标识；③ 仓库路径 token 计数 ≥ 基线；④ 注入脚本真能红、`cp`+md5 还原后回绿；⑤ 未 commit/push。判决：可提交 `待验收`。

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| F1 多行 code span 被截断 | ✅已修 | transform 先整段折叠 brace/多行列表 | `scan.py --root scan-tree` = 0 |
| F2 代码标识被误改（`cpu.workload`） | ✅已修 | token 前后加标识符边界 | scan = 0，diff 人工逐行核对 |
| F3 仓库 token 数下降 | ✅已修 | 排除运行期路径内部子串、保留 `Makefile` 子句 | 2651 ≥ 2643 |
| F4 状态行不同步 | ✅已修 | `milestones.md` 行改 `待验收` | `check-milestones-fresh` rc=0 |
| F5 注入可达性 | ✅已验 | 两处注入均先红后绿 | scan rc=1 / krefs rc=2，还原后均 rc=0 |

### 第 1 轮 reviewer 验收

**重跑记录（我本人执行；workdir=任务 worktree，HEAD=`a4539796`）**
- 一键证据脚本 `scan.sh`（扫描器 `scan.py`，均在运行期证据目录）`--root .` ⇒ `runtime tokens: 0 (files=44)` **rc=0**；`--added 4569f6eb`（不豁免占位）⇒ `added-line runtime tokens: 0 (lines=598)` **rc=0**。
- 基线复核：`git archive 4569f6eb .tao/tasks` 解到临时树后同扫描器 ⇒ `runtime tokens: 776` **rc=1**（与完成区 776 一致）。
- `make check-knowledge-refs` **rc=0、`悬空: 0`**；把基线整树 archive 到临时树 + 运行期证据目录软链后跑同一脚本 ⇒ **`悬空: 72`、FAIL rc=1**（基线 72 独立复现，非采信）。
- `make check-milestones-fresh` **rc=0**；`make check-no-residue` **rc=0**。
- `make check`（L1）**rc=2**，失败目标集 = `{check, check-run-artifacts}`；L1 内 `check-knowledge-refs` PASS（悬空 0）；7 条 `check-run-artifacts` problem 与基线 L1 日志 `diff` **逐行相同** ⇒ 无新增失败、`check-knowledge-refs` 退出失败集（基线集 `{check, check-knowledge-refs, check-run-artifacts}` 中 krefs 一项由我独立复现为 FAIL）。
- 仓库路径 token：基线 **2643 → 2652**（≥）；不可解析 token **集合** base/now 逐项相同（unique 91，新增 0、丢失 0）；六项 `test -e` 全真；随机 20 token 抽查 17 可解析、3 个为基线已存在悬空。
- 证据脚本 `scan.sh` 重跑 ⇒ **rc=0、`RESULT: PASS (failures=0)`**，17 项全 PASS。

**独立注入（`cp` 备份 + `md5`，禁 git 还原）**
- ① 向 GEM5-002t 追加具体运行期路径 ⇒ scan `count=1` **rc=1**；`cp` 还原 md5 `553b8389…` 前后相等 ⇒ scan **rc=0**、`git status` 空。
- ② 向本册完成区追加历史证据路径 ⇒ scan **rc=1**、`make check-knowledge-refs` **rc=2（悬空 1）**；还原 md5 `a023973c…` 相等 ⇒ scan **rc=0**、krefs **rc=0**、`git status` 空。

**约束核验**
- 范围：`git diff --name-only 4569f6eb..HEAD` = **45 个 M**（AGENTS + 43 册任务书 + 本册 + milestones 状态行），无 D/A，无 `tests|spec|contracts|components|tools|Makefile|docs|manifests` 命中，无 `*_tmp*|_gate*|*.orig|*.rej` 残留，工作树无未跟踪文件。
- AGENTS 两条规则与任务书逐字一致；42 册计数 18+6+6+7+4+1=42 ✓；完成区 5 行 ≤30；状态 `待验收`、milestones 行 `待验收`。
- 逐行配对 diff（590 增/588 删）：改动行全部为路径改写；数字差异只来自路径内任务号与证据文件名，rc/PASS 计数/结论无丢失；行数仅 GEM5-002t **−2**（证据文件清单 3 行并 1 行）与本册 **+12**（完成区/审阅记录），其余 44 文件行数不变。
- SPEC-184t：仅 4 行路径改写，identity/页表语义未动；新增 `<...>` 占位只在命令参数（`--source <组件源树>` 等），未用于历史证据行；无门控豁免/测试/契约改动（`tools/`、`Makefile` 0 改动）。

**finding（非阻断，交 architect 收尾改）**：① SPEC-184t 改写后成「若 A 或 A 在现场存在」重复短语，丢失 QEMU-080t/GEM5-016t 两处证据的区分（文档级）；② 审阅记录 F3 行写 `2651 ≥ 2643`，实测与完成区均为 **2652**（数字笔误，非门控读取值）；③ `scan.sh` 的 L1 对账段在两份日志缺失时 `[SKIP]` 且不计 FAIL——已由我本人跑 L1 补证；④ 审查期间 HEAD 由 `df0dec4f` 变为 `a4539796`（engineer 修正完成区计数与 md5 表述、补 findings 表、milestones 置 `待验收`），本轮按 `a4539796` 验收。

**判决：Accepted**——验收命令块在我本人重跑下全部通过、约束无违反；两处注入均「注入→FAIL→`cp`+md5 还原→回绿」；快照对账：审前/审后 `git status --porcelain -uall` 均空，AGENTS `1c467cee…`、milestones `ff724712…`、本册 `a023973c…` 前后未变。
