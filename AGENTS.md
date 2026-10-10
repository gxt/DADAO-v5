# AGENTS.md — DADAO-v5 项目规则

> 全局规则（沟通约定、开发约定、八荣八耻）由 `~/.config/opencode/AGENTS.md` 自动加载；交互目录 `$TAO_ROOT` 定位见 `.tao/README.md`。本文件只写 DADAO-v5 特有内容。

## 基本规则（必须遵守）

- **工作范围**：仅在 DADAO-v5/ 目录内修改或创建文件，可读取其他目录。
- **git 操作**：DADAO-v5 为**独立仓库**（`.git` 为目录、无 superproject；`origin = git@github.com:gxt/DADAO-v5.git`），所有 git 操作限于本仓库内。
- **参考目录**：`DADAO-0628` 和 `DADAO` 作为工程经验参考，不复制其代码。两者 commit 已锁定在 `manifests/`，只读工作树检出在 **`.cache/refs/<id>/`**（`make fetch-refs` 幂等重建）。
- **组件补丁**：组件补丁集的组织/生成/应用/校验以 **`spec/Process-01-组件补丁组织与构建编排.md`** 为准（树形补丁集 + 一文件一补丁 + `git apply`），由 `make check` 的 `check-patch-tree` 机械校验。
- **提交确认**：所有提交必须先经用户确认；architect 的 WIP / 正常提交为流程授权（见「任务收尾·分支—提交—push」），`push` 仍须用户/主会话。
- **推送范围**：`push` 只推送 `gxt` 账号名下仓库（本项目 `origin = gxt/DADAO-v5`）；其它账号/域名的仓库禁止推送或先询问。
- **push 检查**：**push 前**向用户列待推分支 + commit 清单（`git log origin/master..HEAD --oneline`）、核查 `git remote -v` 归属、`git pull --rebase` 同步远端确认无冲突；**push 后**验证（`git status` up-to-date 或 `git log origin/master..HEAD` 为空）。本仓库**无 submodule**，子模块「先子后主」提交/推送序 **不适用**。
- **操作前提问**：进行实际操作前先向用户提问，一次只问一个问题，根据回答追问直到完全理解需求。

## 进入项目

首次进入先读 `.tao/README.md`（角色/命令/流程/项目结构）与 `.tao/knowledge/MEMORY.md`（当前状态），再读 `.tao/tasks/` 下当前模块任务。

## 核心原则

- **Spec-first**：所有编码/语义期望值来自 `.tao/knowledge/contract-*.md`，不从实现反推
- **Independent oracle**：测试向量不能从 LLVM 或 QEMU 生成，必须独立派生自 `spec/`
- **Component lock**：LLVM/QEMU/gem5 以 `manifests/` 中的精确 commit hash 锁定，不用 tag/branch
- **里程碑 TDD**：自 M4 起，每个里程碑**先立测试向量/门控、再实现**（三层 L1 编码/L2 结构/L3 执行，见 `spec/Process-05-里程碑TDD规范.md`）；「一能力一向量」、规模 ∝ 能力，不超前建大套件

## 参考来源与任务自包含

- 任务书必须**自包含**：执行所需的事实/格式/模板写入任务书或 v5 自身知识（`.tao/knowledge/`），不依赖外部仓库内容。
- **模板/格式**以 v5 自身知识为准（如 `spec/Process-03-ADR编写规范.md`、`spec/Process-02-合约编写规范.md`），不引用外部仓库的模板文件。
- DADAO-0628 / DADAO 等参考仓库**仅作只读溯源/对照**，其文件**不得作为任务的执行依赖**；引用时标注「内容溯源，非执行必需」。
- 参考仓库按 commit 锁定（`manifests/`）；如需核对内容，按锁定 commit 从外部获取，不 vendor 进仓库。

## ADR 提醒

- 讨论 / 任务涉及 ADR 判据（高代价、跨模块、多方案、外部契约、结论固化、定位）时，**必须主动提醒用户是否生成 ADR**，不擅自决定、不静默略过。判据与格式见 `spec/Process-03-ADR编写规范.md`。ADR **不承载规范正文**——规范正文归 `spec/` 与 `contract-*`，ADR 只记决策/理由/被否方案与指向的规范章节。

## ADR decision 逐条确认

- **写入 ADR 的每个 decision（D1、D2…）都必须逐条与用户确认**；**不得**因任务书 / 参考文档 / 子代理产出里已写有该决策，就默认其通过。
- 任务书里的 decision 只是**提案**。固化进 ADR 之前，须由用户逐条判定（保留 / 修改 / 否决），确认后方可写入。
- 主会话与子代理（architect / engineer / reviewer）均不得擅自把**未经用户逐条确认**的 decision 写为 `Accepted`。
- 已 `Accepted` 的 ADR 若要改动其 decision，仍须逐条经用户确认（按 `spec/Process-03-ADR编写规范.md`：新增 ADR / 标注 `Superseded` / 经授权的就地修订）。

## 目录结构

```
DADAO-v5/
├── AGENTS.md              # 本文件
├── README.md              # 项目总览
├── .tao/                  # 交互目录（任务/知识/ADR/日志）
│   ├── tasks/<module>/    # 任务文件 <PREFIX>-nnn<suffix>-描述.md
│   ├── knowledge/         # 合约（contract-*.md）与台账（MEMORY/changelog/deferred/milestones）
│   └── adr/               # 架构决策记录 adr-<nnnn>-*.md（决策层）
├── manifests/             # 锁文件（规范/参考组件）
├── spec/                  # 规范：上游 SimRISC/DADAO + v5 自定 Toolchain/Process；索引 spec/README.md（spec 模块任务可改，见 ADR-0012 D4）
├── contracts/             # 机器可读合约数据（编码表/ABI/合法性规则）
└── tools/<module>/        # 各模块工具脚本（infra/spec/llvm/qemu/testcases）
```

## 文档分层与单一真源（2026-10-08，措施 2）

- **文档分工（单一真源）**：
  - `AGENTS.md` = **只放可执行规则**（每条 ≤2 行 + 门控名/文件指针），**不放叙述/复盘/历史**；**能被门控机械判定的，不写文档**（写了会产生漂移）。
  - `spec/` = 规范正文（**被引用不复述**）；`.tao/knowledge/` = **结论与指针**（**长叙述不允许**）。
  - **长叙述 / 一次性分析** → `.work/log/<模块>/`；**历史** → `.tao/archive/M*/`。
- **新增文档三问**（**三者皆否**才允许新增到活 `knowledge/`）：① 能否被**门控机械判定**（能 ⇒ 只加门控 + 一行指针，**不写文档**）？② 是否与**既有文件重复**（是 ⇒ **改既有**）？③ 是否**只服务当前任务**（是 ⇒ 落 `.work/log/`）？
- **新增台账条目口径**：`lessons.md` 等**新增教训/规范条目 ≤3 行 + 指针**，**细节进 `.work/log/`**；**不追溯重写**既有条目（历史条目保持原样）。

## 临时目录

- 所有临时/合成测试/一次性产物一律放 `/tmp/opencode/<任务ID>/`，**不另起** `/tmp/<其它名>`（对齐全局约定）；不得放仓库内或 `~/`。
- 子代理（engineer/reviewer/architect）的合成测试树必须建在此处，完成后可清理，**不得污染真实仓库**。
- **生成器/脚本随产物保留**：凡产出**被提交**（入 git）的生成器或脚本，必须随产物一并保留在**非易失位置**——优先提交到 `tools/<module>/`（可复用/可审计价值高），否则放 `.work/<任务ID>/`；**不得只放 `/tmp`**。判据是**产物是否入库**，而不是"脚本是否只服务一个任务"；**"一次性"只描述用途，不等于可丢弃**（否则产物不可复现、返工脆弱）。

## 命令与任务执行纪律（配置重构时并入，仅留通用必需项）

- **执行前声明预期**：说明命令目的 + 期望 exit code / 输出标志；含 `/` 的相对路径脚本一律写 `./` 前缀（opencode 权限按是否含 `/` 判定，无 `./` 会绕过 ask）。
- **交互式调试**：禁 `| tail`/`| head` 截断调试脚本输出，用 `python3 -u` 无缓冲、逐步打印进度；输出过大时先完整落盘再分块查看（不适用交互式调试）。
- **远端任务**：快速任务（预计 ≤5min）本地等待取结果；**慢速任务（>10min）** `nohup` 后台启动 + 落 PID 文件、**不等待**、告知用户预计耗时（记录实测耗时供后续估计）；等待完成用远端阻塞命令（`while kill -0 $(cat pid); do sleep 15; done`），查询状态非阻塞返回「进行中/已完成」。
- **远端环境**：执行脚本**纳入仓库**（防漂移，从仓库副本调用）、日志落 `<taskdir>/build.log`；涉及 license / 依赖 / 路径时**先确认网络与环境差异**再执行。

## 大文件下载与镜像

- 需从**国外站**（GitHub 等）下载**较大**软件（LLVM、QEMU、linux-kernel 等）时：**先查教育网联合镜像站列表** <https://mirrors.cernet.edu.cn/list/> 判断是否有镜像地址；对候选地址**逐个测试连通性与下载速度**；**给出建议**（含直连 GitHub 作对照）；由**用户确定**从哪个站下载。**不得**自行选定并开始下载。
- 目标有**明确的 release 版本或 tag** 时**默认浅下载**，但**仍须先询问用户**再确定（是否浅下载、范围、落点）；若流程需完整历史（如 `tools/infra/fetch.py` 的 `git clone --mirror`），须说明并确认。
- 执行细则与记录要求见 `.tao/knowledge/mirrors.md`。

## 中间验证规范

每个子任务完成后立即验证：① 输出文件存在；② 跑验证脚本（如 `tools/spec/validate_encoding.py`）；③ 引用一致性（如 SimRISC-00/01/02/03/04，而非 DADAO-11）；④ 填完成区。
数据/期望值类还须**独立全量重算**（size/sign 敏感用例逐条比对、非抽样）、**validator 绿灯 ≠ 语义正确**、**错值当场修**、只有能力缺口才登记遗留（依据见 `.tao/knowledge/lessons.md` §1）。

## 下发前预检（强制）

`/dispatch` 任何任务前，主会话必须完成四项预检并在下发说明中给出结论：① 任务书内部一致性（目标/范围/约束/验收不矛盾）；② **本任务验证手段**所需全部前置（含跨任务指令/工具）实际可用；③ 验收逐条标「现在可跑 / BLOCKED（原因 + 替代证据）」；④ 指令范围/编码/期望值来源与 `contracts/`、`tests/vectors/` 一致。
预检细节与教训（`QEMU-014t`/`QEMU-005t`）见 `.opencode/commands/dispatch.md`。

## 验证脚本反例门控

验收脚本、检查器必须**能失败**：可对注入反例报 FAIL（改错期望值/编码、回退 ILLI 桩等），并给出**注入→FAIL→还原→回绿**的真实输出；**只会报 PASS 的脚本不是证据**。完成区结论须与**真实输出/退出码逐条对齐**，留证须捕获**被检命令自身**退出码（禁 `cmd | tee` 吞码）；每条断言/用例须有**可达 FAIL 路径**（禁恒真、「两支写同一结果」）；覆盖 ≠ 语义（语义须独立 oracle）；注入还原用 `cp`+md5 且含重建，缺陷须「修一类」。
工程侧细则（一键证据脚本五项要求、可达 FAIL、计数不写死、`§8.34/§8.35`）见 `.opencode/agents/engineer.md`、`.opencode/agents/reviewer.md`、`.tao/knowledge/lessons.md` §2。

## 任务分解与执行确认

- 当前 `.tao/tasks/` 下的任务分解是**参考 DADAO-0628 生成**的，**未对每个任务书逐一审核**。
- 因此，**执行任何具体任务之前，必须先与用户确认该任务书内容；确认后方可 `/dispatch` 分派执行**。不得未经确认直接下发。

## 模块里程碑与跨模块交互

- 模块里程碑（`m` 文件）核验时，须考虑**其它模块可能对本模块产生的影响**（如上游模块的修复/变更、跨模块依赖的接口调整）。
- 若因其它模块影响而需要**修复类型**的任务，应二选一：
  - 将本模块里程碑**后移**（保持 `待开始`，待修复完成后再核验）；或
  - **增加专门任务**，用于与其它模块进行交互（接口对齐、回归修复等）。
- 存在未处置的跨模块影响时，**不得**将模块里程碑置为 `里程碑`。

## 子代理返回异常处理

`task` 返回 `Task cancelled`/空结果时先核对落盘（完成区 + `git status`）；未落盘则**重试 1 次同一任务**（附失败现场）；仍异常 ⇒ **停止重试、主动提醒用户并商定拆分任务**（重试中不得换任务/扩范围）；每次异常登记 `.tao/knowledge/issues.yaml`（或完成区）。主会话代行修改须在停止重试且经用户同意后，代行结果仍须 reviewer 验收。
详见 `.tao/knowledge/lessons.md` §3（及 §8.9）。

## 角色与流程

角色规则、任务编号（`<PREFIX>-nnn<suffix>`，模块内递增）、四态状态机与命令（`/plan` `/dispatch` `/complete` `/status`）见 `.tao/README.md`、`.opencode/agents/*.md`、`.opencode/commands/*.md`（agent 定义与 command 随项目入库）。

## 任务收尾（`/complete`）（强制）

**生命周期**：`/dispatch`（实现 + 填完成区；状态 → `待验收`）→ reviewer 独立重跑验收（见「验证脚本反例门控」）→ `/complete` 收尾（交叉复核 + 知识沉淀；主会话置状态 → `已验证`）→ 提交（须已含收尾）。**逐任务收尾，禁止积压/批量**。

**分支—提交—push（单一真源；`lessons §8.26`）**：
- **开工建分支**，名 = 任务号前缀（如 `INTEG-027t`）；该任务 **WIP / 返工 / reviewer 修改**一律提交在**该分支**。
- **architect**（唯一有提交权的子代理）在**每次 engineer / reviewer 返回后**于**该分支内** `commit`（提交前显式 staging、禁 `git add -A`、与完成区「修改文件」对账）：reviewer 判 Accepted ⇒ 正常提交；否则前缀 `WIP:`；**architect 禁 `push`**。
- 完全确定后由主会话**一次性落地 `master`**（`git merge --squash <branch> && git commit` 或 FF）并删分支；**`push`(FF) 只由主会话在 `/complete` 后**执行 ⇒ `master` 永不改写已推送历史（`已 push` 只追加）。**未收尾不得推送**（推送前任务书 `**状态**` 须为 `已验证`）。
- **状态字段边界**：收尾只更新 `**状态**`，**不得**改写既有「完成区/审阅记录」（须补充者只追加）。

**知识沉淀落点**（用户 2026-10-08 裁定）：统一落 `.tao/knowledge/lessons.md`（教训入 §7、规范入 §8），**不另建 `feedback_*.md`**。
**任务书限长**（措施 3）：完成区 ≤30 行、审阅记录每轮 ≤40 行（长输出留 `.work/log/`）。

**收尾检查**（在知识沉淀**之前**执行，任一不过即停下报告）：① 门控按改动类型全绿（门控范围类改 `make check`，纯文档/台账豁免、跑 `check-no-residue` 即可）；② 仓库无临时残留（`git status --untracked-files=all` 干净，禁 `*_tmp*`/`_gate*`/`*.orig`/`*.rej`）；③ 证据留非易失位置 `.work/log/<模块>/`；④ 无未提交的任务结果。步骤细节（reviewer 验收、architect 复核、`MEMORY`/`changelog`/知识库更新）见 `.opencode/commands/complete.md`。

## 并行任务上限（用户裁定 2026-10-01）

- **同时在跑的子代理任务 ≤ 8**；达到上限时，等已有任务完成再下发。
- **同改共享文件**（`contracts/`、`Makefile`、`tests/vectors/`、`spec/SimRISC-0x` 等）的任务**一律串行**，不得并行；避免同一工作树并发跑 `make check`/构建类长任务（污染证据、曾致 shell 被取消级事件）。构建并行度与长构建约束见「长任务」。

## 长任务（长构建 / 长命令）（用户裁定 2026-10-10）

- **脱离生命周期**：长构建/夜跑须 `setsid nohup <cmd> >log 2>&1 &` 脱离 opencode 工作区，**落盘完成标记**（`XXX_EXIT=$rc`），**勿用会话内等待器**；**一次只跑一个**长构建，`JOBS=8` 限制、**禁全核** `-j$(nproc)`（`lessons` §8.21）。
- **申报与判据**：启动前**申报预计耗时**，**不为确认而空等**；完成判据须含**运行期带超时的退出码**——编译 rc=0 ≠ 可运行，须逐优化级跑（`timeout` 的 `124` 判 FAIL，`lessons` §8.42）。
- **诊断超时**：约 60 min 无根因 ⇒ **停下报告**，不试错、不盲目重试。
- **超时保护**：bazel/Vivado 类长命令须设充足 `timeout`，避免中途被杀掩盖真实问题（判定判据见 `lessons` §8.42）。

## 构建与注入测试的成本控制（用户裁定 2026-10-01）

**只有当"编译输入"变化时才需重建**：改 `components/{qemu,llvm-project}/patches/**` 或须验证改动后二进制行为 ⇒ 重建（用增量、避免 `make prepare` 全量）；改 oracle / 期望值 / CHECK 串 / 探针 / 文档 / 契约数据 ⇒ **不重建**。
注入优先选"不改编译输入"方式、多例合并到一轮、先证方法再批量、每次重建前申报「重建 X，预计 N 分钟」。

## 子代理硬约束（下发提示必带）

每次 `/dispatch` 提示**必须内联**以下最小清单（引用既有规则，不重复定义）：

1. **临时目录** `/tmp/opencode/<任务ID>/`，禁仓库内临时文件（→「临时目录」）
2. **不提交 git**（→「提交确认」）
3. **完成区与真实输出逐条对齐**（→「验证脚本反例门控」）
4. **只动任务书范围，越界须披露**（→「外科手术式修改」）
5. **失败即停，禁自动重试**（→ 全局「最小安全设计 / 可恢复」）
6. **补丁导出纪律**：写 `/tmp`、行数下限、非空 blob、`check-patch-tree` 断言⑥（→「组件补丁」）
7. **复杂命令输出留存** `.work/log/<模块>/`（→ `.tao/README.md`「日志留存」）
8. **一键证据脚本**：engineer 产 `.work/evidence/<任务ID>/` 脚本并跑通；reviewer 审脚本 + 重跑 + **独立注入一次反例**（→「验证脚本反例门控」）
9. **用户裁定落盘**：子代理取得用户裁定后，**须把用户原话（或问答摘要）原样写入任务书**（完成区 / 审阅记录）——**子会话问答对父会话不可见**；主会话不得仅因「父会话无记录」就否定裁定、反复回问（→ `.tao/knowledge/lessons.md §7.3`）
10. **提交权归 architect（2026-10-06 起）**：engineer / reviewer **不提交 git**；其每次返回后由 **architect** 在**本任务分支内**判断并 `commit`——reviewer 判 Accepted ⇒ **正常提交**；否则 ⇒ **`WIP:`** 前缀；**architect 禁 `push`**。提交前必须**显式 staging（禁 `git add -A`）+ `git diff --cached --name-only` 与完成区「修改文件」对账（漏提 / 多提 / 越界）**。`push` 只由主会话在 `/complete` 后、将分支 **`merge --squash` 一次性落地 `master`** 再 FF 推送（→「任务收尾·分支—提交—push」）。
11. **反例注入的还原纪律（2026-10-06 起）**：**禁**用 `git checkout`/`git restore`/`git stash`/`git show <commit>:<path>` 还原注入（会清掉未提交改动）；一律 **`cp` 备份 + md5 对账**，或**优先临时树注入**；**`git status`/`git diff` 干净不作"已还原"证据**（→ `.opencode/agents/reviewer.md`「还原纪律」、`.tao/knowledge/lessons.md §2`）。
