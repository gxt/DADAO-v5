# m12-infra-002: 取消 m 册门控（M12 起）

**模块**：infra
**项目里程碑**：M12
**状态**：已验证

## 用户裁定（原话）

「m11 收口→仍然是立一个 integ 的任务，M11里程碑核验，只是没有 m 后缀，该检查任务状态检查任务状态，该归档归档即可」（用户 2026-11-08；此前对「m 册门控去留」选 B = 取消）

## 背景

- `tools/infra/check_milestone_tasks.py`（`make check-milestone` 的一环）当前**强制要求**当前里程碑存在 `m` 册，无册即非零退出。
- M11 已裁定不建 `m` 册、改由 `INTEG-061t` 核验；M12 起编号为 `m12-<module>-<NNN[N]>`（无 k/t/m 后缀），也不会有 `m` 册。
- 结果：`make check-milestone` 在当前里程碑上必然红——是**假的失败信号**，会掩盖其余真实检查。
- `make check-milestone` **不在 L1**（`.PHONY` 列表中有，但 `_locked-check` 不含）。

## 目标

1. `check_milestone_tasks.py`：把「必须有 m 册」改为**可选**——
   - 有 `m` 册：按原规则校验（册自报里程碑一致、册内任务号真实存在、至少列一个任务号）
   - 无 `m` 册：**不再判失败**，打印「本里程碑按用户裁定不建 m 册，跳过」（非静默：明确输出分支名）
   - `--self-test` 覆盖两分支（有册缺→FAIL；无册→PASS 且打印跳过；册内号不存在→FAIL）
2. `Makefile` 的 `check-milestone` 目标：移除对 m 册的硬依赖，保留 SIMRISC archive / sha / sync-nonmaskable / L3 report / `check-tasks --strict` 各项。
3. `docs/Process-07` 的 `check-milestone` 行同步（取消 m 册要求，说明 M12 起口径）。
4. 确认 `Makefile` help 文本与 `AGENTS.md` 若有「m 册」表述同步（只改规则表述，不改历史任务书）。

## 验收标准

1. `python3 tools/infra/check_milestone_tasks.py` rc=0 且输出含「不建 m 册，跳过」分支
2. `--self-test` rc=0；新增两分支的自检项各有可达 FAIL
3. `make check-milestone` 在有/无 m 册两种状态下都不因 m 册而红（其余项失败仍红）
4. `make check`（L1）rc=0
5. 不改 `INTEG-061t`、不改历史任务书、不改已归档册
6. 完成区 ≤30 行、无运行期路径

## 说明

- 这是**门控语义变更**（不是放宽判据）：m 册从「必需」变为「可选」，其余校验项保持。
- 若将来恢复 m 册（例如某里程碑需要专门核验册），本改动仍兼容（有册即校验）。

## 完成区

**测试结果**：一键证据 38/38 PASS（连续两次 rc=0，运行期证据目录，未归档；结果见完成区）；`--self-test` 20/20 PASS；隔离 clone 的 L1 rc=0。（architect 措辞修正，2026-11-09：改运行期措辞，结论不变）
**修改文件**：`tools/infra/check_milestone_tasks.py`、`Makefile`、`docs/Process-07-门控分层规范.md`、本任务书。
**验收结果**：
1. 基线 `python3 tools/infra/check_milestone_tasks.py` ⇒ rc=0，打印「分支: 本里程碑按用户裁定不建 m 册，跳过」。
2. `--self-test` ⇒ rc=0；新增两分支各有可达 FAIL：退化「无册分支」后 self-test rc=1（证据 5b），退化「旧册顶替检查」后 rc=1（证据 5e）。
3. `make check-milestone` 完整目标仍因 `check-spec-archive-verify`（缺 `.cache/refs`，环境）与 `check-l3-report`（未跑 L3）而红；`make -o` 隔离这两个不可用前置后，m 册环节 PASS 且无「m 册缺失」，整体 rc=2 仅因 `check_tasks --strict` 漏收尾=1（本任务待验收，`/complete` 后归零）。注入册内号 `INFRA-999t` ⇒ rc=1 + `MISSING`；删除后 rc=0。
4. L1：任务 worktree 内红项仅台账行（A1 状态与 R1 在跑，同一根因；reviewer 亦记 A1+R1，预期），其余全绿（工具链只读借用安装根）；同文件集隔离 clone（detached、只读借用工具链）`make check` rc=0。
5. 证据脚本（运行期产物，未归档）rc=0（全项 PASS，含注入/还原/退化注入）。（architect 措辞修正，2026-11-09：改运行期措辞，结论不变）
6. `check-milestone` 仍不在 `_locked-check` 依赖（token 级断言 7a）。
**新发现/坑**：worktree 根即 `/tmp/opencode/<TID>`，临时目录须用其子目录并在退出时清理（否则污染仓库）；`make -k` 不会运行前置失败目标的 recipe，隔离不可用前置用 `make -o`；fresh worktree 的 L1 `check-isa-coverage` 需 `llvm-mc`（未 install-host 时只能只读借用安装根）；M12 新编号须同时扩 `TASK_ID_RE`/`TASK_FILE_RE`，否则恢复 m 册时册内号会被判 vacuous。另（非阻断，本次不改）：新式 `mNN-<module>-*` 核验册名不被 `MBOOK_NAME_RE` 命中会按无册跳过；m 册标题自引自身号可绕 vacuous。
**遗留问题**：L1 工作树内红项是台账行（A1+R1，同一根因；非本改动；主会话把本任务移入「进行中」后复跑应绿）。

**第 2 轮返工**（Needs Revision → 待验收）
- F1：完成区与 reviewer 记录共 4 处具体 `.work/**` 路径改运行期措辞（均标 architect 措辞修正），`check_knowledge_refs.py` rc=0。
- F2：证据脚本 clone 改为 `--branch master --no-checkout` + checkout 被测树 HEAD SHA，并断言 clone HEAD == 被测 HEAD、本地仅 master；连续两次 rc=0、38/38。
- 复跑：基线 rc=0；self-test 20/20；`make check` 除台账行外全绿；`git status -uall` = 完成区 4 文件。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 证据脚本 TMPDIR 指向 worktree 根，残留 `c*.out`/`mut*.py` 于仓库 | ✅已修 | 改用 `$ROOT/.evidence-tmp` + `trap` 退出清理 | 重跑后 `git status -uall` 仅 3 个源码改动 |
| 工具链选择取第一个 worktree，主/任务 worktree 顺序不同会借不到 | ✅已修 | 遍历 `git worktree list` 找存在的 `cross-toolchain` | 证据 6a0 PASS |
| `TASK_ID_RE`/`TASK_FILE_RE` 不认 M12 编号，恢复 m 册时册内新号 vacuous FAIL | ✅已修 | 两正则同时支持 `mNN-<module>-<3–4 位>`；self-test 增 2 项 + 有册 PASS 用新号 | self-test 20/20；证据 2b 覆盖 |
| `audit` 台账缺失仍 fail-closed（先于无册跳过） | ❌不修 | 无（保留：无台账无法定义当前里程碑） | 基线/self-test 覆盖 |
| `make -k` 无法让前置失败的目标跑 recipe（影响验收取证方式） | ❌不修 | 无（改用 `make -o` 隔离不可用前置，已在证据与完成区说明） | 证据 3c/3e |
| 任务置「待验收」后 `check_tasks --strict` 漏收尾=1，证据原断言「隔离 rc=0」失效 | ✅已修 | 证据改为只断言 m 册环节 PASS/无「m 册缺失」，整体 rc 记 INFO；「其余项仍红」由 3a/3b 覆盖 | 证据 33/33 PASS |

### 第 1 轮 reviewer 验收

**判决：Needs Revision**（门控本体达标；完成区写具体 `.work/**` 路径致 L1 红 + 证据脚本 6b 不可复现，两条须改）
长输出留运行期日志目录（未归档）。（architect 措辞修正，2026-11-09：改运行期措辞，结论不变）

**重跑记录（均我方现场执行，退出码取 `cmd; echo $?`）**
1. `python3 tools/infra/check_milestone_tasks.py` ⇒ rc=0，打印「分支: 本里程碑按用户裁定不建 m 册，跳过（当前 M11…）」。
2. `--self-test` ⇒ rc=0，**20/20 PASS**（20 行 PASS 逐条数过）。
3. 退化注入（无册分支 `return 0`→`return 1`；`cp` 备份 md5 `a4a15408…`）⇒ self-test **rc=1**（`FAIL 无 m 册 ⇒ PASS: expect=0 actual=1`）；`cp` 还原、md5 相等 ⇒ self-test rc=0。
4. 我方独立注入 A：空 m 册（无任务号）⇒ rc=1「② 无法核验（vacuous）」；注入 B：仅旧册自报 M10 ⇒ rc=1、2 项 VIOLATION（含「有册但无当前册」）；`rm` 还原 ⇒ rc=0。
5. `make -k check-milestone` ⇒ rc=2，**仅 2 红**：`check-spec-archive-verify`（缺 `.cache/refs/DADAO.wiki`）、`check-l3-report`（无 `.dadao/tests/l3`）；`check-milestone:` 依赖行与 `git show HEAD:Makefile` diff = 空；master 上同两目标 rc=0 / rc=0 ⇒ 与本任务无关。
6. `make -o check-spec-archive-verify -o check-l3-report check-milestone` ⇒ m 册环节 PASS、无「m 册缺失」，整体 rc=2 仅 `check_tasks --strict` 漏收尾=1（本任务待验收）。
7. token 级：`_locked-check` 词表无 `check-milestone`（含 `check-milestones-fresh`）⇒ 仍不在 L1。
8. `bash <运行期证据目录>/run.sh` ⇒ **rc=1**（32 PASS / 1 FAIL，FAIL=6b）。（architect 措辞修正，2026-11-09：改运行期措辞，结论不变）
9. `make -k check`（本 worktree）⇒ rc=2，红 = `check-knowledge-refs`（**本任务完成区 2 处**）、`check-milestones-fresh` A1+R1（台账，预期）、`check-isa-coverage`/`check-width-sizes`/`check-components`（本 worktree `.dadao` 无工具链，环境）。

**阻断 finding**
- **F1 完成区 L44/L51 含具体 `.work/**` 路径** ⇒ `make check-knowledge-refs`（L1 成员）FAIL；master 树 + 本任务书模拟 ⇒ **3 处红**（合入后 master L1 变红）；我在临时树把两处改成运行期措辞后该门控 **rc=0**。修复：改「运行期证据已清理，未归档；结果见完成区」或 `<任务ID>` 占位形。
- **F2 `run.sh` 6b `git clone --branch master` 依赖移动 master**：`bf62961c`（00:16:58，晚于 engineer 证据 51 s）新增 chipyard-002 的 `.work/**` 引用 ⇒ 我复跑 6b rc=2。修复：clone 后 pin 分支 HEAD（或记 SHA）再拷交付文件，复跑须 rc=0。

**约束核验**：改动 4 文件 = 完成区「修改文件」✓；完成区 11 行 ≤30 ✓（但含 F1 路径 ✗）；未碰 `INTEG-061t`/历史任务书/归档册/契约/`tests` ✓；`docs/Process-07` 四处（表行/fail-closed/层归属/触发点）+ Makefile help 自洽 ✓；`AGENTS.md` 无「m 册必然」表述 ✓；注入前后 `git status -uall` 与 4 文件 md5 逐行/逐值一致 ✓。

**三问**：① 有册 fail-closed **完整保留**（里程碑自报不符、有册无当前册、册内零号 vacuous、册内号 MISSING，四类我均实测 rc=1）。② `check-milestone` 两红**与本任务无关**（环境前置；依赖行与基线逐字相同、master 同状态 rc=0）。③ 无册分支**不掩盖真实错误**（台账缺失/无断言/任务目录缺失均在跳过分支**之前** fail-closed，跳过仅在「`.tao/tasks/**` 存在且 m 册数=0」触发且显式打印）；残留两点非阻断、记录不判：新式 `mNN-<module>-*` 核验册名不被 `MBOOK_NAME_RE` 命中会按无册跳过、m 册标题自引自身号可绕 vacuous（基线已有，非本次引入）。

### 第 2 轮 reviewer 验收

**判决：Accepted**（两条 finding 均真修；门控语义与三类判据未被放宽）
长输出留运行期日志目录（reviewer 第 2 轮 `run1/run2/drift/l1_tc`）。

**F1 真修**
- `python3 tools/infra/check_knowledge_refs.py` ⇒ **rc=0**（`结果: PASS (0 具体 .work/** 引用…)`）。
- 逐行核 4 处：完成区 L44/L51 + 我方记录 L77/L87；把**第 1 轮我的原文**与现文 `difflib` 逐行比对 ⇒ 仅这 2 行（我的记录内）变化 + 1 空行，**判决「Needs Revision」、重跑记录 1–7/9、阻断 finding、约束核验、三问原文一字未动**；完成区 33/33→38/38 随新证据更新、结论不变。任务书残留 `.work/` 仅 `.work/**` 通配形（豁免）。

**F2 真修（抗 master 前进）**
- `run.sh`：`PIN_SHA=$(git -C "$ROOT" rev-parse HEAD)` → `clone --shared --no-checkout --branch master` → `checkout --detach $PIN_SHA` → 断言 `clone HEAD == 被测 HEAD`（51203f8a）、`本地仅 master`、`cat-file -e $PIN_SHA`；另加第 8 节 `check-knowledge-refs` rc=0 断言。
- 本树连跑 2 次：**均 rc=0、38 PASS / 0 FAIL，两次输出 `diff` = IDENTICAL**。
- 漂移模拟（临时树，未碰真实仓库）：shared clone → detach `51203f8a` + 拷交付文件 → 把该树本地 `master` 推进到 `e94a9f22`（含具体 `.work/**` 毒丸）⇒ 复跑 run.sh **仍 rc=0、38/38、pin=51203f8a**；反证按**旧**方式 `checkout master` 同门控 **rc=1**（`zz-reviewer-poison.md:3 .work/evidence/poison/run.sh`）、pin 树 rc=0 ⇒ pin 确实抗 master 前进。

**回归**
- `--self-test` rc=0 **20/20**；基线 rc=0 且打印跳过分支；`make -o … check-milestone` ⇒ m 册环节 PASS、无「m 册缺失」，rc=2 仅 `check_tasks --strict` 漏收尾=1；`make -k check-milestone` 仍仅 2 个环境前置红。
- 判据未放宽（3 次注入复测）：仅旧册 ⇒ rc=1（2 项，含「有册但无当前册」）；空册 ⇒ rc=1 vacuous；`INFRA-999t` ⇒ rc=1 `MISSING`；`rm` 还原 ⇒ rc=0。三文件 md5 与第 1 轮逐值相同（`a4a15408…` / `60de7417…` / `f1a7ea09…`）。
- `make -k check`（只读借用工具链）⇒ **唯一红 = `check-milestones-fresh` A1+R1 台账行**，`check-knowledge-refs` 已不在失败列表；不借工具链时另有 isa-coverage/width-sizes/components 三红 = 本 worktree 无 `.dadao/cross-toolchain`（环境）。

**约束**：完成区 15 行 ≤30、含「第 2 轮返工」、无具体 `.work/**` 路径 ✓；`git status -uall` = 4 文件，与「修改文件」逐项一致 ✓；未碰 `INTEG-061t`/历史任务书/归档册/契约/`tests` ✓；本轮注入均已还原，审前/审后 md5 与 status 逐项对账（任务书仅因本轮审阅新增一节）。

**三问**：① F1 **真消除 L1 红**（该门控 rc=0，且 L1 失败列表已无它）。② F2 的 **pin 抗 master 前进**（毒丸 master 下旧方式红、pin 方式绿）。③ 四文件改动**仍与完成区一致**（4 = 4）。

#### 收尾（architect，2026-11-09 01:25）

- 第 1 轮 **Needs Revision**（完成区 4 处具体 `.work/**` 路径致 L1 红 + 证据脚本 6b 依赖移动 master）→ 返工 → 第 2 轮 **Accepted**。
- F2 已被 reviewer 用「临时树推进 master 并放毒丸」反证：pin 被测树 HEAD 后 run.sh 仍 38/38 rc=0，旧方式 rc=1。
- 判据未放宽：reviewer 注入「仅旧册/空册/`INFRA-999t`」三例均 FAIL，三个代码文件 md5 与第 1 轮逐值相同。
- 观察项（基线既有）已立 `ISS-356`。
