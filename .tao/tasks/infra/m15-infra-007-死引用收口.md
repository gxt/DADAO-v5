# m15-infra-007: 两处既有死引用收口

**模块**：infra
**项目里程碑**：M15
**依赖**：`m15-infra-004`（`check_dead_refs.py` 已入仓）
**可并行分片**：否
**预估**：0.5–1 h
**档位**：小改
**状态**：待验收

## 背景（`m15-infra-004` 首次运行 `check_dead_refs.py` 抓到的现存死引用）

`tools/infra/check_dead_refs.py` 首次运行即报出两处**真实的仓内死引用**（当时记为「建议各自收口」，未修）：

1. `tools/infra/check_milestones_fresh.py:85` 的 `--file` 默认值仍指向已分册化的 `milestones.md`（现为 `milestones-m14/15/16.md`；根 `milestones.md` 是否仍存在以现场为准）。
2. `tools/qemu/check_005t_coverage.py` 仍读**已退役的 YAML 载体**（无调用者；`check_005t_coverage` 是否还在 Makefile 里以现场为准）。

## 目标

1. 两处逐一核实（现场 `grep` + 跑一次脚本），确认是「默认值过时」还是「脚本整体已退役」。
2. 按性质处置：
   - **仍在使用** ⇒ 修默认值/载体路径，使其指向现存文件；修后脚本自身 rc=0。
   - **已无调用者且载体退役** ⇒ 删除脚本（或移入 `.tao/archive/tools/`，按 `AGENTS.md`「脚本入仓判据」判断，选一种并在完成区写明理由）；同步删 Makefile 目标（若有）。
3. 不新增功能、不改判据语义。

## 验收（逐条贴真实 rc）

1. `python3 tools/infra/check_dead_refs.py` **rc=0** 且 `missing` 计数为 0（当前基线 0，修完仍 0；若你新增了路径，必须同样为 0）。
2. 两处逐一给出：现场证据（`grep` 输出 / Makefile 命中）、处置、修后验证。
3. 若删除脚本：`grep -rn "<脚本名>" Makefile tools docs` = 0（历史任务书/归档除外，逐条列明）；`make check` 相关目标不因删除而失败。
4. `check-dirs`、`check-no-residue`、`make check-tasks` rc=0。
5. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树；**禁提交 git**；不改版本号。
2. 只动上述两处脚本 + 必要的 Makefile 行 + 本任务书。
3. **不碰 `components/`、`tests/`、`spec/`、`contracts/`**。
4. `cp`+md5 还原（禁 checkout/restore/stash/show）。

## 待裁定

（无）

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 去掉 `audit`/`_run` 默认参数后，`r1_self_test` 内仍 `_run(repo)` ⇒ `TypeError` | ✅已修 | 补 `_run(repo, KNOWLEDGE_REL / LEGACY_LEDGER_NAME)` | `--self-test` rc=0（self-test: PASS） |
| 路径常量改文件名后，旧格式兜底路由语义是否漂移 | ✅不修（语义不变） | 保留 `LEGACY_LEDGER_NAME` 走 `home_ledger`/A2 悬空号分支 | A6 八类 + R1 六类 + R2 两例全 PASS |
| 新增「无活台账 ⇒ fail-closed」分支须可达 FAIL | ✅已修 | evidence 3b：空树 `--root` | rc=1（期望 1） |
| 注入还原须 `cp`+md5、且注入非空 | ✅已修 | evidence 第 7 段 | md5 一致 + 注入后 `git status` 非空 |
| 删脚本前须确认无活引用 | ✅已修 | `grep -rn check_005t_coverage Makefile tools docs`=0；`compileall -q tools` rc=0 | 现场 0 命中；compileall rc=0 |

判决：上述 finding 全部处置完毕，无未修项 ⇒ 状态置「待验收」。

### 第 1 轮 reviewer 验收（2026-11-18，小改档）

**自证**：`git rev-parse --show-toplevel` = 本任务 worktree（独立树）、`branch=m15-infra-007`、注入前后 `git status --porcelain -uall` 均空；base = merge-base `8400e307`；`git diff --name-status 8400e307..HEAD` 恰 4 文件（任务书 M / `check_dead_refs.py` M / `check_milestones_fresh.py` M / `check_005t_coverage.py` D）。

**重跑记录（reviewer 亲跑；退出码取被检命令自身，非管道）**：
1. 第 1 处死路径：`git show 8400e307:tools/infra/check_milestones_fresh.py` 第 85 行 = `MILESTONES_REL = Path(".tao/knowledge/milestones.md")`，而 `git ls-tree 8400e307 .tao/knowledge/` **无**根 `milestones.md` ⇒ 缺省确为死路径；base 版脚本对本树无参跑 **rc=1** `ERROR: 台账不存在: .tao/knowledge/milestones.md`。修后无参 **rc=0**，输出 3 个 `check-milestones-fresh —` 段头，与 `ls .tao/knowledge/milestones*.md` 现场 3 本（m14/m15/m16）一致，三本均 `结果: PASS`。
2. `python3 tools/infra/check_milestones_fresh.py --self-test` **rc=0**、`self-test: PASS`、PASS 用例 31 条；与 base 版自检用例名 `diff` **为空** ⇒ 未删用例、未弱化断言。
3. 第 2 处：`grep -rn check_005t_coverage Makefile tools docs tests` **rc=1（0 命中）**；`grep -n 005t Makefile` 0 命中（无对应目标）；base 树内除 `check_dead_refs.py` 白名单条目与脚本自身外无调用者；`tests/inst/base/` 目录已不存在 ⇒「无调用者 + 载体退役」成立，删除成立且删除后无门控依赖。
4. `NON_LIVE` 11→3 **只删不加**（diff 中条目行全为 `-`、无新增键）；剩 3 条理由与行号准确（`check_inst_macro_scope.py:560/575/590` 的 `FIXTURE` 表，真树 3 个路径均 `MISSING`）。**独立佐证**：拿 base 版（11 条）脚本跑修后树 ⇒ 恰好 8 条 `STALE table entry`（6 条 yaml + 根台账 + m12 台账）⇒ 被删 8 条正是仅因两处死引用才存在。
5. `python3 tools/infra/check_dead_refs.py` **rc=0**，`scanned 267 file(s), 186 repo-path constant(s), 0 missing, 3 non-live`，`STALE` **0** 条。
6. 证据脚本审阅（19 断言均有可达 FAIL 路径；第 7 段注入非空 + md5 对账，无恒真/两支同果）后重跑 **rc=0、19/19 PASS**，与完成区一致。
7. **独立反例注入**（选任务书未列文件 `tools/testcases/lib/run_qemu_test.py`，`cp` 备份 md5=`0fb0f4fc…`）：追加死常量 ⇒ `check_dead_refs` **rc=1**、stderr 指名 `tools/testcases/lib/run_qemu_test.py:978: docs/__review_007_no_such__.md`、`187 … 1 missing`；`cp` 还原 ⇒ md5 相同、**rc=0**、`git status` 空（全程未用 checkout/restore/stash/show）。
8. 门控：`make check-dirs` / `check-no-residue` / `check-tasks` / `make check-milestones-fresh` **均 rc=0**；`python3 -m compileall -q tools` **rc=0**。

**越界**：`git diff --name-only 8400e307..HEAD -- components tests spec contracts` = 0 文件；4 文件内无版本号变更。

**阻断项（本判决唯一理由）**：`make check-knowledge-refs` **rc=2**（`make: *** [Makefile:1372: check-knowledge-refs] Error 1`），`结果: FAIL (1 具体 .work/** 引用不可复现)`，唯一命中 = **本任务书完成区「测试结果」行写了具体运行期证据脚本路径**（`.work/evidence/<任务ID>/run.sh` 形）；base 版任务书该引用 0 条、其余 147 个扫描文件本任务未动 ⇒ **本任务引入的 L1 回归**（同类先例 `ba39265a`「check-knowledge-refs 回绿：005 审阅记录里的 .work 路径改措辞」）。**修法**：完成区该行改为占位/不落路径措辞（保留 19/19 结论），改后 `make check-knowledge-refs` 须 rc=0。属「门控/退出码」阻断面，非文档笔误。

**环境项（非本任务、不阻断）**：`make check`（L1 全量）rc=2，停在 `check-isa-coverage`：`ERROR: 找不到 llvm-mc` —— 本 worktree 无 `.work/build/llvm`（主工作树有），属未构建工具链的环境缺失，与本任务 4 文件无关。

**遗留裁定（验收第 8 项）**：Makefile:1438-1447 仍硬编码 `MILESTONES_M14/15/16` 且 `if [ -f ]` 缺册即跳过 ⇒ 判 **「可接受、记遗留」，本任务不改**：改成自动发现会变更门控校验对象集合 = 判据语义变更，超出硬约束 2「只动两处脚本 + 必要 Makefile 行」与目标 3「不改判据语义」；该缺陷是渐进性 fail-open（M17 新册不被校验、旧册缺文件不报红），非本任务引入。建议后续立单独小任务把该目标改为「不传 `--file` 走自动发现」（一行），并在 M17 建册前完成。

**判决：Needs Revision** —— 仅上述 `check-knowledge-refs` 一条门控红（rc=2）；其余 8 项重跑全绿，硬约束 1–4 全守住。修完该行复验即可 Accepted。

### 第 2 轮 engineer 返工（2026-11-18）

| reviewer finding | 处置 | 改了什么 | 复验证据（真实 rc） |
|---|---|---|---|
| 完成区「测试结果」行写具体 `.work/evidence/<任务ID>/run.sh` ⇒ `check-knowledge-refs` rc=2 | ✅已修 | 该行改为「运行期证据目录内的 run.sh」，19/19 结论与数字一字未动 | `make check-knowledge-refs` **rc=2 → rc=0**（`结果: PASS (0 具体 .work/** 引用; …)`） |
| Makefile 硬编码 `MILESTONES_M14/15/16`（判「可接受、记遗留」；建议 M17 建册前立单独小任务） | ✅记遗留（不改 Makefile） | 完成区「遗留问题」① 补写该建议 | 未改 Makefile：`git status -uall` 仅任务书 1 处 |

复验：`make check-dirs` / `check-no-residue` / `check-tasks` / `check-milestones-fresh` 均 **rc=0**；`git status --porcelain -uall` 仅 `.tao/tasks/infra/m15-infra-007-死引用收口.md`（M）。判决：阻断项已消除 ⇒ 状态置「待验收」。

### 第 2 轮 reviewer 验收（2026-11-18，小改档）

**自证**：worktree = 本任务独立树、`branch=m15-infra-007`、HEAD `1d2a08e5`、`git status --porcelain -uall` 空；`git diff --name-status 8400e307..HEAD` 仍恰 4 文件；返工提交 `ed5143e9..HEAD` **只动任务书** 1 个文件。

**1. 阻断已消除**：`make check-knowledge-refs` **rc=0**，`具体路径 (不可复现): 0`、`结果: PASS (0 具体 .work/** 引用; 0 悬空小节级互指；小节级: ADR 552 + contract 115 已校验)`；完成区段（`## 完成区` 起）按模式「`.work/` + `evidence`」grep = **0** ✓。
**计数差异如实记**：全文按该模式 grep 本任务书 = **2**（非派单预期 0）——两处均为**占位形** `.work/evidence/<任务ID>/run.sh`（一处是本轮之前我自己的第 1 轮记录引用 finding 原文、一处是 engineer 返工表引用），按门控口径 `<>` 形判占位跳过 ⇒ 门控 rc=0；**完成区内 0**。非具体路径，不构成阻断。

**2. 结论未动**：`git diff ed5143e9..HEAD` 仅两处改写 + 一处新增 —— ① 完成区「测试结果」行的**具体** `.work/evidence/<任务ID>/run.sh` 措辞 →「运行期证据目录内的 run.sh」；② 遗留段① 补写 reviewer 判定与 M17 建议；新增「第 2 轮 engineer 返工」表。`**判决：Needs Revision**` 行两版 `diff` **SAME**；完成区「通过 19/19」两版字面一致（全文 `19/19` 计数 3→4 系返工表复述一次，非改写）；第 1 轮 reviewer 段正文逐行未改。

**3. 遗留段 + Makefile**：完成区遗留① 含 `MILESTONES_M14/15/16` 硬编码 + 「reviewer 判可接受、记遗留，建议 **M17 建册前立单独小任务**改成不传 `--file` 走自动发现（本任务不改 Makefile）」 ✓；`git diff 8400e307..HEAD -- Makefile` = **0 行**，`git diff HEAD~1..HEAD -- Makefile` = **0 行** ✓。

**复跑门控**：`make check-dirs` / `make check-no-residue` / `make check-tasks` / `make check-milestones-fresh` **均 rc=0**。

**判决：Accepted** —— 第 1 轮唯一阻断（`check-knowledge-refs` rc=2）已消除并复验 rc=0，完成区结论与数字未被改写，Makefile 零改动、遗留已落盘；第 1 轮其余 8 项本轮采信不重复。遗留：Makefile 硬编码待 M17 前单独立项；L1 全量 `make check` 在本 worktree 因无 llvm-mc 未能跑完（环境项，非本任务）。

## 完成区

**测试结果**：通过 19/19（运行期证据目录内的 run.sh，含注入反例）；失败原因：无。

**修改文件**：`tools/infra/check_milestones_fresh.py`（`--file` 缺省改为现场发现 `milestones*.md` 逐本校验；两个指向已删台账的路径常量改为「文件名 + `KNOWLEDGE_REL`」，`audit`/`_run` 去默认参数）；`tools/qemu/check_005t_coverage.py`（**删除**）；`tools/infra/check_dead_refs.py`（`NON_LIVE` 11 项 → 3 项，只删不加）；本任务书。

**验收结果**：
1. `python3 tools/infra/check_dead_refs.py` rc=0，`scanned 267 file(s), 186 repo-path constant(s), 0 missing, 3 non-live`，`STALE` 0 条。
2. ① `check_milestones_fresh.py`：修前无参运行 rc=1（`ERROR: 台账不存在: .tao/knowledge/milestones.md`；实存台账仅 `milestones-m14/15/16.md`）；**仍在使用**（Makefile 逐本传 `--file`）⇒ 修默认值：无参 rc=0，逐本校验本数现场统计 3 == 现存 3，三本全 PASS。
   ② `check_005t_coverage.py`：修前 rc=1（读已退役的 `tests/inst/base/*.yaml` 与 `.work/source` 下 translate.c）；`grep -rn check_005t_coverage Makefile tools docs` = 0 活引用，Makefile 无目标 ⇒ **已退役**，删除（判据「会不会再跑」=不会：无调用者、载体随 `m13-testcases-043` 退役；不另存归档，内容可由 `git show` 取回）。
3. 删脚本后 `grep -rn "check_005t_coverage" Makefile tools docs` = 0；余下命中仅 `.tao/tasks/`（本任务书 + `m15-infra-004`）、`.tao/archive/**`、`components/qemu/changelog.md`（历史记载，按任务书豁免逐条列明）。
4. `make check-dirs` / `make check-no-residue` / `make check-tasks` / `make check-milestones-fresh` 均 rc=0；`compileall -q tools` rc=0。
5. `git status -uall`：仅上述 3 个实现文件 + 任务书改动（`.work/` 已 gitignore）。

**新发现/坑**：① 门控的「默认值」是盲区——Makefile 一直显式传 `--file`，缺省值自 M14 分册后就失效却无人踩到；缺省值应尽量写成现场发现。② `check_dead_refs` 的 `STALE` 机制有效：两处修完后 8 条 `NON_LIVE` 自动转 STALE，正好指出该收窄的项（白名单未腐烂）。③ 删 `check_005t_coverage.py` 后 `tests/inst/base/*.yaml` 失去唯一引用面 ⇒ 6 条 `NON_LIVE` 一并收窄，收口无新增死引用。

**遗留问题**：① Makefile 仍硬编码 `MILESTONES_M14/15/16`（M17 起须再加一行）；reviewer 判「可接受、记遗留」，建议 **M17 建册前立单独小任务**把该目标改成不传 `--file` 走自动发现（本任务不改 Makefile）。② 未跑 L2/L3（无编译输入变化、删除脚本无门控目标），已跑 L1 相关 4 目标。
