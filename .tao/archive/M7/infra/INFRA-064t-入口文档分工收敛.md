# INFRA-064t: 入口文档分工收敛（`.tao/README.md` 瘦身 → `AGENTS.md` / `MEMORY.md`）

**模块**：infra
**项目里程碑**：M7
**依赖**：`SPEC-133t`（同改文档层，避免并发；**串行**）
**状态**：已验证

> 本任务书由**主会话**依用户 2026-10-11 裁定撰写（非常规 architect 起草，已披露）。

## 用户裁定（2026-10-11，**原话要点**）

1. 「`.tao/README.md` 文档中，无需**项目结构**一节，**model** 一节也没必要，**日志目录迁移说明**也没必要」。
2. 「有些内容是不是应该放到 `.opencode/AGENTS.md`（= 项目 `AGENTS.md`）中，以及 `.tao/knowledge/MEMORY.md` 中，另外，**重复的内容可以删除**，比如那个 `tee`」。
3. 主会话提出映射表 → 用户批复「`.tao/README.md` **可以**」⇒ **映射表照批**（含**模块表留 `.tao/README.md`**）。

## 目的

消除三份入口文档的**重复**，确立单一真源：**规则**归 `AGENTS.md`、**导航**归 `.tao/knowledge/MEMORY.md`、`.tao/README.md` 只留**交互目录自身**的说明。

## 映射（执行依据）

| `.tao/README.md` 现存 | 处置 |
|---|---|
| `## 核心原则` | **删**（`AGENTS.md`「核心原则」是真源） |
| `## 角色分工` + 流程行 | **上移 `AGENTS.md`「角色与流程」**（保留"主会话=协调者"+ `/plan`→`/dispatch`→`/complete` 流程）→ 本页留**一行指针** |
| `### 命令总览`（3 行表 + 注） | **上移 `AGENTS.md`**（`/plan` `/dispatch` `/complete` `/status` 一行）→ 本页留指针；**修**"注里提 `status` 而表里没有"的自相矛盾 |
| `## $TAO_ROOT 定位` | **留本页**（压 1 行） |
| `## 目录` | **留** `.tao/` 命名与状态机要点；**删**与 `MEMORY.md` 指针表重复的职责描述（改一行"各目录职责与真源索引见 `MEMORY.md`"）；**删** `.work/` 与"日志留存"重复段（→ `AGENTS.md` 硬约束 7）；**删那处 `tee`**（与 `lessons §2.1` 冲突：**禁** `cmd \| tee` 吞码，须 `cmd; echo rc=$?`） |
| `## 模块与任务编号` | 规则正文真源 = **`.opencode/agents/architect.md`**（状态机/编号）；本页只留 `PREFIX-nnn<suffix>` 格式一行 + 指针；**删**"已取消过渡期任务"历史 |
| `## 任务书限长` | **删**（`AGENTS.md`「任务收尾·限长」是真源；本页留指针或直接去掉） |
| **模块表**（`infra`…`sail`） | **留本页**（`AGENTS.md` 不载列表类）；`golden`/`gem5`/`sail` 标"**未开工**" |
| `issues.yaml` 描述 | 措辞修正（现"异常登记" ⇒ **issue 台账**） |
| （新增） | **一行**：文档三分界指针（`spec/` / `docs/` / `.tao/knowledge/` → `AGENTS.md`） |
| `## 项目结构` / `## model` / `## 日志目录迁移说明` | **删**（用户明确；历史属 `.tao/archive/`，git 可回溯） |

## 输出

1. **`.tao/README.md` 按表瘦身**：只留「交互目录说明书」= `.tao/` 结构命名 + 状态机/编号指针 + **模块表** + `$TAO_ROOT` + 三分界指针；**行数现场统计下降**（不设目标值）。
2. **`AGENTS.md`** 收走**规则**：`/plan` `/dispatch` `/complete` `/status` 一行 + "主会话=协调者"一句（并入「角色与流程」节，**不新增节、不膨胀**；如与既有内容重复则只保留一处）。
3. **`MEMORY.md`** 收走**导航**：确保 `.tao/` 各子目录职责与真源索引在**该处唯一承载**（.tao/README.md 改为指针）；保持"**入口指针页**"定位（不复制事实）。
4. **一致性**：三份文件**互不复述**（同一事实只在一处，其余给指针）。

## 约束

- **只动** `.tao/README.md`、`AGENTS.md`、`.tao/knowledge/MEMORY.md`（+ 本任务书 + `milestones.md` 流水行）；越界须披露。
- **不新增门控**、**不新增篇幅**（净减）；**不追溯重写**历史（历史归 `.tao/archive/`，git 可回溯）。
- **计数/行数不写死**（现场 `wc -l`）。
- 临时目录 `/tmp/opencode/INFRA-064t/`；**不提交 git**；禁 `git add -A`/`.`。
- 反例注入还原**禁** `git checkout`/`restore`/`stash`；一律 `cp` + md5 对账。
- 任务书/记录中**不得写字面 `.work/<具体路径>`**（用 `<>` 占位），否则 `check-knowledge-refs` 判悬空、`make check` 自伤。

## 验收标准

1. **三节已删**：`.tao/README.md` 无 `## 项目结构` / `## model` / `## 日志目录迁移说明`（`grep` 真实输出，rc≠0）。
2. **重复已消**：`.tao/README.md` 无「核心原则」节、无「命令总览」表、无「任务书限长」节（`grep` 证据）；**无 `tee` 吞码措辞**（`grep` 证据）。
3. **规则上移**：`AGENTS.md`「角色与流程」含 4 命令 + 协调者一句（`grep` 真实输出）；**未新增节**（节数不增，现场统计）。
4. **导航归位**：`.tao/` 目录职责在 `MEMORY.md` **唯一**（`.tao/README.md` 为指针）；`MEMORY.md` 仍为指针页（无事实副本）。
5. **净减**：三份文件总行数**下降**（现场 `wc -l` 前后对比，不写死目标）。
6. **门控**：`make check`、`check-knowledge-refs`、`check-no-residue` 各 EXIT=0（捕获**命令自身**退出码，禁 `cmd \| tee`）。
7. **反例可失败**：注入（在 `.tao/README.md` 塞回一段"核心原则"重复文本 / 塞一行 `cmd \| tee`）⇒ 校验脚本或 `grep` 断言 **FAIL** ⇒ `cp`+md5 还原 ⇒ 回绿。
8. **一键证据脚本**落 `.work/evidence/<任务ID>/`（能失败、可达 FAIL、结构断言、计数不写死、捕获退出码）。
9. **完成区**（≤30 行）与真实输出逐条对齐。

## 完成区

**测试结果**：通过 23/23（`.work/evidence/<任务ID>/run.sh` rc=0：15 项验收断言 + 8 项注入自检）；失败原因：无。
**修改文件**：
- `.tao/README.md`（94→**32** 行）按映射表瘦身
- `AGENTS.md`（132→**133** 行）「角色与流程」补协调者一句 + 4 命令一行（节数 24→24，**未增节**）
- `.tao/knowledge/MEMORY.md`（40→**41** 行）入口指针表拆「交互目录」/「角色·流程·命令」两行
- `.tao/knowledge/milestones.md`（+1 流水行：`INFRA-064t` `待验收`）
**验收结果**（真实命令；退出码现场捕获）：
- 1 三节已删：`grep -nE '^## (项目结构|model|日志目录迁移说明)' .tao/README.md` → rc=1（无命中）
- 2 重复已消：`grep -nE '核心原则|命令总览|任务书限长' .tao/README.md` rc=1；`grep -n 'tee' .tao/README.md` rc=1
- 3 规则上移：`grep '主会话 = \*\*协调者\*\*' AGENTS.md` rc=0；「角色与流程」节内 4 命令 4/4；AGENTS 节数 24 = `git show HEAD:AGENTS.md` 基线，未增
- 4 导航归位：README 指向 `MEMORY.md「入口指针」`；README 无 archive「只读」/知识库文件枚举/「数据/工具分离」重复（rc=1）；职责索引唯一在 MEMORY
- 5 净减：现场 `wc -l` 合计 **266→206**（README 94→32、AGENTS 132→133、MEMORY 40→41）
- 6 门控：`make check` rc=0；`check-knowledge-refs` rc=0（具体路径校验 74、悬空 0）；`check-no-residue` rc=0
- 7 反例可失败：注入「`## 核心原则`」重复段 ⇒ 断言 FAIL ⇒ `cp`+md5 还原 ⇒ 回绿；注入一行 `cmd | tee` ⇒ 断言 FAIL ⇒ 还原回绿（md5 对账一致）
**新发现/坑**：
- 映射表「`issues.yaml` 描述→issue 台账」与验收#4「职责唯一在 MEMORY」有张力：保留为 README 指针行内的**最小术语修正**（`issues.yaml` = issue 台账），其余职责枚举删除。
- 原 README「数据/工具分离」注与 `AGENTS.md`「目录结构」同事实 ⇒ 按一致性要求#4 删除（**越界披露**：映射表未单列，属 README 内去重）。
**遗留问题**：无。

## 审阅记录

#### 第 1 轮 engineer 自审
逐行审查三份改动文件（`.tao/README.md` / `AGENTS.md` / `.tao/knowledge/MEMORY.md`）+ 证据脚本 `run.sh`。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1：「数据/工具分离」注与 `AGENTS.md`「目录结构」同事实，违反验收#4「互不复述」 | ✅已修 | 删 README 该注（34→32 行） | `grep -nE '数据/工具分离' .tao/README.md` rc=1；run.sh 断言块内 PASS |
| F2：README「目录」节 `issues.yaml` 描述须保留映射表要求的最小修正，而非整体删除 | ✅已修 | 指针行内嵌 `（issues.yaml = issue 台账）`，不再枚举各目录职责 | run.sh「README 指向 MEMORY『入口指针』」PASS |
| F3：注入自检须有**可达 FAIL** 且还原**可核对**（非恒真、非 `git checkout`） | ✅已修 | `run.sh` 内置两组单例注入（`## 核心原则` 段 / `cmd \| tee` 行）+ `cp`+md5 对账 | run.sh「注入A/B 后断言 FAIL」「还原 md5 对账」「还原后回绿」全 PASS |

判决：无未修 finding；状态置 `待验收`。

#### 第 1 轮 reviewer 验收

**重跑记录**（全部独立执行，不采信 engineer 输出）：
- `make check` EXIT=0（含 `check-knowledge-refs` PASS 0 悬空、`check-no-residue` PASS）
- 删除项逐条 `grep`：`## 项目结构`/`## model`/`## 日志目录迁移说明`/`核心原则`/`命令总览`/`任务书限长`/`tee` 均 rc=1（无命中）✅
- 判据承载：`Spec-first`/`Independent oracle`/`Component lock` → `AGENTS.md` L21-23；角色/协调者/四命令 → `AGENTS.md` L101；限长 → `AGENTS.md` L108；`tee` 口径 → `AGENTS.md` L87 + `lessons.md` L197/325-326 ✅
- 引用悬空普查：`.opencode/commands/{status,dispatch,complete,plan}.md` 均引用 `.tao/README.md`「交互目录 `$TAO_ROOT` 定位」→ 该节存在（L6）✅；`AGENTS.md` L3 引 README → 存在；其余活文件无指名已删小节的引用 ✅
- 一致性：三文件互不复述（角色/流程仅在 AGENTS；目录职责仅在 MEMORY 指针表；README 只给指针）✅；AGENTS 节数 24→24 未增 ✅；`tee` 口径与 `lessons §2.1/3.11` 一致 ✅
- 净减：README 94→32、AGENTS 132→133、MEMORY 40→41，合计 266→206（净减 60）✅；diff 抽样确认无内容悄悄消失 ✅
- 独立注入：注入 `## 核心原则` 段到 README ⇒ grep 检出 rc=0（FAIL）⇒ `cp`+md5 还原（`ba39937…`==`ba39937…`）⇒ grep rc=1（回绿）✅
- 越界核：`git status` 只有 4 个预期修改文件（README/AGENTS/MEMORY/milestones）+ 1 个任务书 + 1 个未动的 SPEC-134t（untracked，未触碰）✅

| # | 检查项 | 结果 |
|---|--------|------|
| 1 | 门控 `make check` rc=0 | ✅ |
| 2 | 删除项 7/7 grep rc=1 | ✅ |
| 3 | 判据无丢失（6 项→承载处逐条） | ✅ |
| 4 | 引用悬空（活文件 4 处→节存在） | ✅ 0 悬空 |
| 5 | 一致性 3 处 + 节数 + tee | ✅ |
| 6 | 净减 266→206 | ✅ |
| 7 | 独立注入 FAIL→还原→回绿 | ✅ |
| 8 | 越界核 | ✅ 无越界 |

**判决：Accepted** — 验收命令块全部通过、约束无违反、判据无丢失、引用无悬空、反例可失败。
