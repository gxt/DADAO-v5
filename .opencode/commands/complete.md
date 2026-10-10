---
description: Complete a finished task - review code and update memory/knowledge - 任务收尾
agent: build
---

# /complete $ARGUMENTS — 任务收尾

任务执行完成后，进行代码 review 并更新 memory 和知识库，完成整个任务生命周期。

## 前置条件

- 任务已完成执行（工程师已填完成区，状态为 `待验收` 或 `待返工`）
- 若任务尚未执行完成，先 `/dispatch` 下发执行
- **逐任务收尾，禁止积压**：多个任务同时待收尾时，**逐个** `/complete`，不得合并为一次补做

## 执行步骤

### 0. 定位交互目录

按 `.tao/README.md`「交互目录 `$TAO_ROOT` 定位」确定 `$TAO_ROOT`。

### 1. 找到并读取任务文件

在 `$TAO_ROOT/tasks/` 中递归搜索 `$ARGUMENTS*.md`（搜索模式 `$TAO_ROOT/tasks/**/$ARGUMENTS*.md`）。

**若匹配到 `m` 里程碑标记文件**：不执行验收，提示用户这是里程碑标记、无需 `/complete`。

**找到文件后，先检查 `**执行环境**` 字段是否含 `远端`**：
- 若是远端任务，**必须先从远端拉取最新版本**，再读取，否则读到的是发出时的旧版本（完成区为空）。
- 拉取命令从 `$TAO_ROOT/knowledge/registry.md`（若存在）的 dispatch 路由规则中反推：push 命令 `scp [-P port] <file> user@host:remote_path` → pull 命令 `scp [-P port] user@host:remote_path/<file> <local_file>`；若该文件不存在，请用户提供 pull 命令。
- 拉取失败时报错，不继续。
- 拉取成功后，后续步骤（验收、知识沉淀）在**本地**完成。

读取任务文件的 **完成区**（`## 完成区` / `## 执行结果` / `## 结论` 等）。
若任务文件没有完成区内容（仍是模板占位），说明结果还没写回，提示用户。

### 2. 调起审查者验证

若任务有代码改动，**先调起 `reviewer` 子代理独立验证**，再更新 memory：

- **若任务文件的最新一轮 reviewer 验收子区已有 Accepted 判决，则跳过本步骤**（已审查过）
- 用 `task` 工具调起 `reviewer` 子代理（**subagent_type**：`reviewer`，模型 = mimo/mimo-v2.5-pro），让它读取任务文件并重跑验收命令
- 审查者判决 **Needs Revision** → 告知用户，将状态改为 `待返工`，不继续写 memory（等返工）
- 审查者判决 **Accepted** → 进入「交叉复核」步骤

### 2.5 交叉复核（双模型相互验证）

> 即使 §2 因「已有 Accepted」跳过，本步骤**仍必须执行**（否则失去双模型互验）。

调起 `architect` 子代理（模型 = deepseek/deepseek-flash）**复核 reviewer 的验收判决**：

- 对照规划任务文件与实际实现/产出，检查 reviewer 验收是否遗漏关键验收项、约束是否有违反、判决是否过严或过松
- architect 返回复核意见（确认 Accepted / 提出补充发现）

主会话**汇总 reviewer 验收与 architect 复核**，生成统一验收报告：

- 两份独立意见的共识与分歧
- 最终判决：Accepted（进入 memory 更新）/ Needs Revision（改 `待返工`）
- 统一报告要点写入任务文件审阅记录与 `.tao/knowledge/`（reviewer 已自行落盘其「reviewer 验收」记录，主会话**只写统一报告与最终判决**，不重复写 reviewer 记录）

> 若 architect 复核发现补充问题且 reviewer 已 Accepted：以复核意见为准，判 Needs Revision 或要求 reviewer 补充验收。

### 3. 判断需要更新哪些文件

对照完成区内容（尤其工程师在"新发现/坑"字段记录的沉淀建议），逐一检查。**知识库更新由本命令统一执行，工程师不直接写知识库。** 任务部分完成时也必须更新 memory 反映当前状态，不要因为"任务未完成"而跳过更新。

**A. `$TAO_ROOT/knowledge/MEMORY.md` 摘要行**
- 若任务结论改变了某个项目的状态/进展，更新对应摘要行

**B. project_*.md 文件**
- 若任务涉及某个活跃项目，找到对应的 `knowledge/project_*.md` 并更新进展/状态

**C. lessons.md 文件（教训 §7 / 规范 §8）**
- 若任务暴露了新的教训或操作规范（"应该这样做"/"不该那样做"），追加到 `$TAO_ROOT/knowledge/lessons.md`（**不另建 `feedback_*.md`**；新增条目 ≤3 行 + 指针，细节进 `.work/log/`）

**D. 知识库文件**（`$TAO_ROOT/knowledge/`）
- 若任务包含新的技术结论，检查知识库是否需要新增章节
- 知识库更新较重，若结论确定才写；若还有后续验证，先写 memory 即可

**E. changelog**
- 若任务对仓库代码有实质改动，且 `$TAO_ROOT/knowledge/changelog.md` 存在，则添加一行记录（格式：`| 日期 | 描述 | 执行方 |`）；不存在则跳过

| 有新发现 | 推翻旧结论 | 操作 |
|---------|----------|------|
| 是 | 否 | 追加到现有 memory 文件 |
| 是 | 是 | 更新现有记录，标注旧结论已过时 |
| 否（复现已知结论） | — | 无需写 memory，告知用户 |
| 纯调研、无决策 | — | 视内容决定：若有可复用的技术细节则写知识库 |

### 4. 执行更新（必须在讨论之前完成）

**无论用户是否附加"讨论"参数，memory/MD 更新必须先执行，不能跳过。**
"讨论"是在更新完成后额外进行的，不是替代更新。

直接更新文件，**不要等用户确认**。更新后列出修改了哪些文件、改了什么，再进行讨论。

若改动较多（超过 3 个文件），先列出清单让用户确认再写。

### 5. 收尾提交（分支 → 落地 master → push；2026-10-06 起）

见 `AGENTS.md`「任务收尾·分支—提交—push」（**单一真源**）；本步骤只列项目侧要点：

- 确认任务书 `**状态**` 已是 `已验证`；由主会话将本任务**开工分支** `git merge --squash <branch> && git commit`（信息含任务编号 + 「已验证」）**一次性落地 `master`**，随后删分支。
- 再 `git push`（FF，本任务提交已落地）；**只推送本任务的提交**；**已 push 的提交不得改写历史**（只能追加）。
- push 前核对 `git show --stat` 的文件集与任务书「修改文件」声明一致（可复用 architect 的审核结论）。

## 注意

- `$TAO_ROOT/knowledge/MEMORY.md` 超过 200 行时把细节移入子文件，只留摘要行
- 知识库章节号从现有最大章节号 +1 递增
- 不写代码细节进 memory（代码在仓库里，memory 只写结论和规律）
- 不写临时路径、临时文件名进 memory
- 任务文件**只允许**更新 `**状态**` 字段（`待验收`→`已验证`；判 Needs Revision 时→`待返工`）；**不得改写**完成区与审阅记录的既有内容（须追加者只追加）。
