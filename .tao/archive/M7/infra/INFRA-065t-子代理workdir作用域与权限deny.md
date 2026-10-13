# INFRA-065t: 子代理工作目录作用域（workdir）规则 + 权限 fail-fast

**模块**：infra
**项目里程碑**：M7
**依赖**：无（**改 `AGENTS.md` + `.opencode/agents/*.md` ⇒ 与在办任务串行**）
**状态**：已验证

> 本任务书由**主会话**依用户 2026-10-11 裁定撰写（非常规 architect 起草，已披露）。**缘起**：子代理常在命令首位写 `cd /mnt/tao`（仓库**父目录**）⇒ 触发权限询问 ⇒ **夜跑无人应答 = 挂死**。

## 用户裁定（2026-10-11，**原话**）

> 「子代理在组合命令的时候，经常会使用 `cd /mnt/tao` 来作为命令的起始第一条，于是，就卡住在访问权限这里；这个事情如何避免；尤其是在夜跑的时候」
> 「**`cd` 命令本身是不能禁止的，应该是限制子代理都在 `workdir` 中**」
> 「**可以**；不过现在就要夜跑了，**等明早吧**」

## 目的

把"子代理作用域"钉在 **workdir = 仓库根**：仓内相对路径 `cd` 允许；**越出仓库**（绝对路径 / `~` / 上跳）**当场失败**（fail-fast），而不是"无人应答地挂 ask"。

## 诊断（已取证，写入本任务书供复核）

| 检查 | 结果 | 推断 |
|---|---|---|
| OS 层 `cd /mnt/tao` | rc=0 正常 | 非文件系统问题 |
| `.opencode/agents/{architect,engineer,reviewer}.md` frontmatter | `permissions: [shell * → allow, sudo * → deny]` + 两条 `external_directory` deny | **订正（实测+文档）**：越界 ask **来自 `external_directory` 动作**（默认 `external_directory * → ask`），**非 `shell`**；且 `external_directory` **先于** `shell` 检查 ⇒ `shell` 规则（含 `shell` deny）**挡不住**。落点 = **agent frontmatter**（agent 规则**追加**于全局、**不替换**）——**当前服务下未生效 ✗**（canary3 实为 `ask` + 用户人工 reject；`message` 字面无法与真 `deny` 区分 ⇒ 不采信；`POST /api/location/reload` 未见效）⇒ 待 `opencode service restart` 后复验 |
| 仓内 `cd /mnt` 示例 | `git grep` **0 命中** | 非文档所示范，属模型习惯 |

## 输出

1. **canary 验证**（**先做**）：后台起一子代理，只跑 `cd /mnt/tao && pwd; echo rc=$?`，据结果判定 `permissions` 是否生效与**该写哪种形态**（agent frontmatter vs 项目 `.opencode/opencode.jsonc`）：
   - 返回 `deny/error` ⇒ 权限层生效 ✓；
   - 返回 `rc=0` 且无 ask ⇒ 仅"越界默认 ask"作怪 ⇒ deny 规则同样有效 ✓；
   - **长时间不返回** ⇒ 权限层不可靠 ⇒ 只靠规则层 + 夜跑冒烟（**须登记**）。

   - **根因（查证官方文档 `opencode.ai/v2/docs/permissions`）**：越界 ask 来自 **`external_directory` 动作**（默认 `external_directory * → ask`），**非 `shell`**；且 `external_directory` **先于** `shell` 检查 ⇒ `shell` deny（含本任务原拟三条 `shell` deny）**无效** ✗。
   - ⚠️ **教训（2026-10-12 用户实测证伪后修订）**：`permission.rejected` 的 `message` 字面**不能**区分「真 `deny`」与「`ask` + 人工 reject」——人工 reject 同样返回 `message="Permission denied: external_directory"` ⇒ **判「deny 是否生效」唯一可靠依据 = 用户观察是否弹询问**（子代理无该视角、**不得**就此下结论）。

   **结论（据用户更正，2026-10-12）**：**agent frontmatter 的 `external_directory` deny 在当前服务下未生效 ✗**；`POST /api/location/reload` **未见效** ⇒ **只能靠服务重启**（用户明早自行执行 `opencode service restart`）后复验。

   **完整纠正链**：
   1. **canary1**（2026-10-11；现象经用户确认）：起子代理跑越界 `cd`（`/mnt/tao`、`~`、`..`）**四种均弹 `ask`（需人工点）**；用户点 reject ⇒ 子代理仅见 `permission.rejected`、命令**未执行** ⇒ **无人值守会挂死**。
   2. **canary2**（2026-10-12，新会话；现象经用户确认）：加 agent frontmatter `external_directory` deny 后，越界 `cd /mnt/tao` **仍弹 ask**（用户确认弹了询问）⇒ 子代理所获工具返回 `{"type":"permission.rejected","message":"ask"}`，**`message` 字面为 `ask`** ⇒ 仍走 ask ⇒ 当时判 **未生效** ✗。
   3. **`POST /api/location/reload`**：改 agent 配置后执行该接口（服务端重建已加载 location）——**本次未见效**（仍弹 ask、行为无变化）。
   4. **canary3**（2026-10-12；现象**经用户更正**）：起 `engineer` 型子代理跑越界 `cd /mnt/tao`，工具返回 **`{"type":"permission.rejected","message":"Permission denied: external_directory"}`**；**用户更正**：该次**实为 `ask` + 用户人工 reject**（**并非**"直接拒绝"）⇒ 故 `message` 与「真 `deny`」**不可区分** ⇒ **不作生效证据** ✗。
   5. **reviewer 自查**（第 1 轮验收）：reviewer 自跑同样拿到该 `message` ⇒ **同一现象可由人工 reject 产生** ⇒ 其"行为核=自动 deny"**不成立、不采信** ✗（**不改写 reviewer 既有审阅记录**，仅在此说明）。
   - ⚠️ **误判订正（历史，一并保留）**：canary1/早期子代理曾自报「已经生效」，唯一证据即 `message` 字面（子代理自证不可靠）；**`message` 不能作判据**这一结论已由用户实测证伪原判据后固化。

   **全局层加固（用户 2026-10-12 裁定；已由主会话写入、非本任务改动）**：在全局配置文件 `~/.config/opencode/opencode.jsonc` 加 `/mnt/*`、`/home/ubuntu/tao/*` 两条 `external_directory deny`（**仓库外**，备份在容器临时目录）；**全局配置文件改动不在 location 重载范围 ⇒ 需服务重启生效**（**同样需重启**）。
2. **规则层（作用域 = workdir，不禁 `cd`）**：
   - `AGENTS.md`「**子代理硬约束（下发提示必带）**」**新增一条**：命令一律在 **workdir（= 仓库根）** 内、用**相对路径**；**禁出界** `cd /*`、`cd ~*`、`cd ..*`；换目录用工具的 **`workdir` 参数**。
   - `.opencode/agents/{architect,engineer,reviewer}.md` 各自的硬约束节各一句（同一口径）。
3. **权限层（fail-fast，替掉"无人应答的 ask"）**：按 canary 结论在**生效的位置**加 deny：
   > **订正 1（实测+文档，见 §输出 1）**：动作应为 **`external_directory`**（**非** `shell`，`shell` deny 无效）。下列 `shell` 三条为**原拟形态**，已被取代：
   > **订正 2（据用户更正，2026-10-12，见 §输出 1）**：**落点 = agent frontmatter 的 `external_directory` deny**（三 agent 各两条，`/mnt/tao/*` 与 `/home/ubuntu/tao/*`），**当前服务下未生效 ✗**（canary3 实为 `ask` + 用户人工 reject；`location.reload` 未见效）⇒ **待 `opencode service restart` 后复验**。
   > **订正 3（已撤销）**：曾试**项目 `.opencode/opencode.jsonc` 的 `experimental.policies`**（hard-deny）——其 `action` 枚举在 v2.0.22 **仅 `provider.use`**（`ConfigV2.Experimental.Policy.action`）⇒ 非法 ✗；**已删除**，`opencode.jsonc` 恢复为仅 `$schema` + `watcher`（逐字与原状一致）。
   > frontmatter 两行 **deny 保留**（作待验证规则），注释改注「**未生效（canary3 实为 `ask` + 用户人工 reject；`message` 字面与"真 deny"不可区分）；原因 = 当前服务未吃进配置 ⇒ 待 `opencode service restart` 后复验**」。
   ```
   - action: shell
     resource: "cd /*"     # 绝对路径 ⇒ 出界
     effect: deny
   - action: shell
     resource: "cd ~*"     # home ⇒ 出界
     effect: deny
   - action: shell
     resource: "cd ..*"    # 上跳 ⇒ 出界（仓内 `cd .work/...` 不受影响）
     effect: deny
   ```
4. **夜跑纪律**：夜跑前做**权限冒烟**（1 条代表性命令，不含绝对 `cd`）+ 下发提示内联该条；夜跑任务避免绝对路径。
5. **知识沉淀**：`lessons` 追加一条（≤3 行 + 指针）：**"待办/计划"必须落任务书或 `milestones.md`，不得落 `.work/`（可丢弃、无人提醒）**；并在 `milestones.md`「规划中」登记本任务。

## 约束

- **不加门控**（用户口径：能靠规则 + 权限解决的，不新增门控）。
- 只动 `AGENTS.md`、`.opencode/agents/*.md`、`.opencode/opencode.jsonc`、`lessons.md`、`milestones.md`、本任务书；越界须披露。
- 临时目录 `/tmp/opencode/INFRA-065t-rework/`（返工轮）、`/tmp/opencode/INFRA-065t-final/`（收尾返工轮）；**不提交 git**；禁 `git add -A`/`.`。
- 反例注入还原**禁** `git checkout`/`restore`/`stash`；一律 `cp` + md5 对账。
- 任务书/记录中**不得写字面 `.work/<具体路径>`**（用 `<>` 占位），否则 `check-knowledge-refs` 判悬空、`make check` 自伤。

## 验收标准

1. **canary 结论**：给出**实测**结果 + 依据（真实输出 + **用户确认现象**），并据此确定 deny 落点 = **agent frontmatter**（`POST /api/location/reload` **未见效** ⇒ 待服务重启复验）；`experimental.policies` 已撤销（schema 不接受 `action:"permission"`）。
2. **规则落地**：`AGENTS.md`「子代理硬约束」含该条（`grep` 真实输出）；三个 agent 定义各含一句（`grep` 真实输出）。
3. **权限 deny 生效（⏳ BLOCKED：需 `opencode service restart`，非本任务可验证）**：实跑一条**出界命令**（`cd /mnt/tao`，**用子代理**）⇒ 期望**当场失败**（`permission.rejected`）、**用户未见询问**；仓内相对路径仍**正常**（对照）。**当前状态 = 未生效 ✗**（canary3 实为 `ask` + 用户人工 reject；`location.reload` 未见效）。
   > **替代证据（本任务现已可得）**：① **规则层 `grep`**：三 agent frontmatter 各含 2 条 `external_directory` deny（`/mnt/tao/*`、`/home/ubuntu/tao/*`，`effect: deny`）+ `AGENTS.md`/三 agent 含 workdir 硬约束条（真实 `grep` 输出见证据脚本）；② **静态断言**：证据脚本 `chk_c2`/`chk_c5`（可达 FAIL）；③ **门控** `make check` / `check-knowledge-refs` / `check-no-residue` 各 `rc=0`。**行为核（真 `deny`）须待服务重启后由用户观察复验**。
4. **夜跑冒烟（现状：期望不成立，须待服务重启）**：给出「夜跑前冒烟」可执行步骤（1 条命令 + 期望结果）；**当前服务下越界 `cd` 仍弹 `ask`（人工 reject 亦产 `permission.rejected`）⇒ 夜跑前冒烟不可依赖 deny，须以「用户在场 / 无可越界命令」为纪律**；服务重启后复验期望 = 立即 `permission.rejected` 且用户未见询问。
5. **知识沉淀**：`lessons` 新条目（≤3 行 + 指针）+ `milestones.md`「规划中」登记。
6. **门控**：`make check`、`check-knowledge-refs`、`check-no-residue` 各 EXIT=0（捕获**命令自身**退出码）。
7. **完成区**（≤30 行）与真实输出逐条对齐。

## 完成区

**结论**：**规则层 ✅ / 权限层 ⏳（未生效，待服务重启复验，BLOCKED）**。
**测试结果**：证据脚本 `.work/evidence/<任务ID>/run.sh` 6 条静态断言全 PASS（`rc=0`）；`--selftest` 逐条可达 FAIL（注入后 rc 均≠0）+ 回绿 `rc=0`；`--inject`（临时树注入反例）注入后 `rc≠0`、cp 还原后 `rc=0`，md5 前后对账（非空注入）。
**修改文件**：`.opencode/agents/{architect,engineer,reviewer}.md`（注释订正为「未生效…待服务重启复验」；两条 deny 保留）、`.tao/knowledge/lessons.md`（§3.18 删错误判据、改 `message` 不可区分）、`.tao/knowledge/milestones.md`（`INFRA-065t` 行改未生效 + 待办加复验行）、`.tao/knowledge/issues.yaml`（新增 `ISS-199` open）、本任务书（正文订正为未生效 + 纠正链 + 验收 3 标 BLOCKED + 替代证据）；`.work/evidence/<任务ID>/run.sh`（gitignored，未入库）。`.opencode/opencode.jsonc`、`AGENTS.md` 本轮未改。
**验收结果**（命令自身退出码）：
- `make check` → `rc=0`；`make check-knowledge-refs` → `rc=0`；`make check-no-residue` → `rc=0`
- `python3 tools/infra/check_issues.py` → `rc=0`（`25 open, 9 closed`；基线 `24 open, 9 closed` ⇒ **+1 open**）
- **规则层 `grep`**（替代证据）：三 agent 各 2 条 `external_directory` deny；`AGENTS.md`/三 agent 含 workdir 硬约束条
**权限层现状（⏳ 未生效，待服务重启复验）**：**agent frontmatter `external_directory` deny 在当前服务下未生效**（canary3 实为 `ask` + 用户人工 reject；`message` 字面不可区分；`POST /api/location/reload` 未见效）⇒ 只能靠 `opencode service restart` 后复验；**替代证据 = 规则层 grep + 静态断言 + 门控**（验收 3 标 BLOCKED）。
**全局层加固（用户 2026-10-12 裁定；主会话写入、仓库外、非本任务改动）**：`~/.config/opencode/opencode.jsonc` 加 `/mnt/*`、`/home/ubuntu/tao/*` 两条 `external_directory deny`；**同样需服务重启生效**。
**新发现/坑**：
- **判据订正（用户实测证伪）**：`permission.rejected` 的 `message` 字面（含 `Permission denied: external_directory`）**不能**区分真 `deny` 与 `ask`+人工 reject ⇒ **判生效只能靠用户观察是否弹询问**；**子代理不得就此下结论**（无该视角）。
- **本次纠正链**：canary1 ask（用户确认）→ canary2 ask（用户确认）→ `POST /api/location/reload`（未见效）→ canary3 **ask + 用户 reject**（用户更正）→ reviewer 自查同样拿到该 `message`（不可区分 ⇒ 不采信）。
- **配置生效途径**：改项目/agent 级配置后 `POST /api/location/reload` 通常令其生效（**本任务实测未见效，待复验**）；**全局配置文件改动需重启服务**。
**遗留问题**：权限层未生效 ⇒ `ISS-199`（open）+ `milestones.md` 待办行登记；**须用户执行 `opencode service restart` 后做 canary 复验**（本任务不可验证，标 BLOCKED）。

## 审阅记录

#### 第 1 轮 engineer 自审

**自主逐行审查**（改 7 文件，无子代理）：
- frontmatter YAML：注释行与 `- action` 同缩进（2 空格），块序列内注释合法；三文件同口径；原 `shell *`/`sudo *`（及 architect `git push *`）未动。
- 规则句：`AGENTS.md` 第 12 条与三 agent 句措辞同口径（`grep` 证据内嵌 run.sh，逐条可达 FAIL）。
- 防造假：三处门控 `rc` 现场取得（非转述）；`--inject` 走临时树、md5 前后不同（非空注入）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 分支 `INFRA-065t` 不存在（下发称已 checkout） | ✅已修 | `git switch -c INFRA-065t master` 自建 | `git branch --show-current`=INFRA-065t（rc=0） |
| §输出 3 原拟 `shell` deny 与实测结论矛盾 | ✅已修 | 加订正注：动作改 `external_directory`、原拟 `shell` 被取代 | `git diff` 任务书该段 |
| `external_directory` deny 或过匹配仓库自身（父目录） | ⏸延后 | 由主会话 canary 对照核（`cd .work/...` 应正常） | 完成区「新发现/坑」已登记 |

**判决**：finding 均已处置（1 项延后并登记）；状态标 `待验收`。

#### 第 2 轮 engineer 自审（返工：权限层方案替换 + 误判订正）

**自主逐行审查**（改 `.opencode/opencode.jsonc` + 三 agent 注释 + 任务书 + `lessons`；无子代理）：
- `opencode.jsonc`：JSONC 合法（`python json.load` + `api --standalone` `rc=0` 双证）；`$schema`/`watcher` 逐字未动（c2 断言）；两条 policy 形态与用户指定一致。
- YAML frontmatter：注释行缩进 2 空格、块序列内合法；三 agent `external_directory` 计数各 ==2（c3 断言）。
- 防造假：门控 `rc` 现场取得；`--selftest` 6 条均可达 FAIL（非恒真）；`--inject` md5 前后对账；**未用** `git checkout/restore/stash`。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 上轮 frontmatter `external_directory` deny 未生效（canary2） | ✅已修 | 权限层改项目 `experimental.policies`；frontmatter 注释标「实测未生效」 | `api --standalone` 显示 policies；`--inject` rc=1/回绿 rc=0 |
| 任务书正文隐含「落点=frontmatter 即有效」 | ✅已修 | 加 canary2 记录 + 误判订正 + 改道段 | 任务书 §输出 1；run.sh c4 断言 |
| `debug config` project `info` 无 policies | ✅澄清 | 系**服务端缓存**（同文件在临时树可见 policies） | 对照 proj-real 输出；`--standalone` 为准 |
| policy `action` 枚举（schema 仅 `provider.use`） | ⏸延后 | 按用户指定 `permission` 形态照落 | canary3 定；回报 ⑧ 已披露 |
| `~`=`/home/ubuntu` 不被两条 policy 覆盖 | ⏸延后 | 按指定形态照落、未擅自扩 | 完成区「新发现/坑」已登记 |

**判决**：canary2 finding 已修；2 项延后并登记（均待 canary3/用户裁定）；状态标 `待验收`。

#### 第 3 轮 engineer 自审（收尾返工：删 `policies` + 定案"已生效"）

**自主逐行审查**（改 `.opencode/opencode.jsonc`、三 agent 注释、任务书、`lessons`、`milestones`；无子代理）：
- `opencode.jsonc`：删 `experimental.policies` 后 `md5==7b9266f1…`、`git diff master` **空** ⇒ 逐字等于原状（仅 `$schema`+`watcher`）；`json.load` `rc=0`；`api --standalone` 的 project doc `keys=['$schema','watcher']`、`experimental` 缺席。
- 三 agent：`external_directory` 计数各 ==2（deny 保留）；注释改为「已实测生效（canary3… `message="Permission denied: external_directory"`；用户确认无询问；生效方式 = `POST /api/location/reload`）」。
- 任务书正文：canary1→canary2→reload→canary3 证据链 + 全局层（`~/.config/opencode/opencode.jsonc`，需重启，仓库外、非本任务改动）齐；正文无 stale「待 canary3」。
- `lessons §3.18`：精简为判据层（reload 生效 / 全局需重启 / `experimental.policies` 非法 / `message` 可判据）。
- 防造假：三处门控 `rc` 现场取得；`--selftest` 6 条均可达 FAIL；`--inject` md5 前后对账（`b9c13c36…→7571f2d9…→b9c13c36…`）；**未用** `git checkout/restore/stash`。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 上轮 `experimental.policies`（行动枚举疑似非法）与"不需要这么麻烦"冲突 | ✅已修 | 删 `policies`，恢复 `$schema`+`watcher` 逐字原状 | md5 `7b9266f1…`、`git diff master` 空、c1 断言 |
| 三 agent 注释标「实测未生效…待 canary3 定」与定案矛盾 | ✅已修 | 改为「已实测生效（canary3…reload）」 | c2 断言（计数 2 + 关键字） |
| 任务书/`lessons`/`milestones` 残留「待 canary3」 | ✅已修 | 正文/`lessons`/`milestones` 改定案 + 证据链 | c3/c4/c6 断言 |
| c6 若对全文查 stale 会误伤历史「审阅记录」段 | ✅已修 | c6 只查正文（`## 审阅记录` 之前） | `--selftest` 正文注入 stale ⇒ FAIL；回绿 rc=0 |

**判决**：finding 均已修；状态标 `待验收`。

#### 第 1 轮 reviewer 验收

**门控**：`make check` rc=0、`check-knowledge-refs` rc=0、`check-no-residue` rc=0 ✓
**规则形态**：三 agent 各 2 条 `external_directory` deny（`/mnt/tao/*`、`/home/ubuntu/tao/*`，`effect: deny`）+ 注释标「已实测生效」+ 原 `shell` 规则保留 ✓；`AGENTS.md` L134 workdir 硬约束语义正确 ✓；`opencode.jsonc` 无 `policies`，`git diff master` 空 ✓
**行为核（reviewer 自跑）**：
- 越界 `cd /mnt/tao` → `{"error":{"type":"permission.rejected","message":"Permission denied: external_directory"}}` ✓（自动 deny，无 ask）
- 对照 `cd .work && pwd` → `/home/ubuntu/tao/DADAO-v5/.work` rc=0 ✓
- 对照 `/tmp/opencode/` 建/删文件 → rc=0 ✓
- `cd ~` → `message:"为什么又出现权限询问，这次是我reject的"`（ask，非 deny）→ 与任务书登记的 `~` 覆盖缺口一致 ✓
- `cd ..` → `Permission denied: external_directory` ✓
**lessons §3.18**：判据层 3 条齐（reload 生效 / policies 非法 / message 判据），结论与证据链一致 ✓
**证据链自洽**：canary1 ask→reject → canary2 `message:"ask"`+用户确认弹询问 → reload → canary3 `message:"Permission denied: external_directory"`+用户确认无询问，因果有依据 ✓
**独立反例**：改 engineer.md「已实测生效」→「待验证」→ `chk_c2` FAIL（rc=1）→ cp+md5 还原（`b9c13c36…`）→ 回绿 rc=0 ✓
**越界核**：修改文件 = 三 agent + AGENTS.md + lessons + milestones + 任务书（7 文件）；`.opencode/opencode.jsonc` 无 diff；`.work/evidence/` gitignored ✓
**非阻断发现**：`chk_c3_task_final` selftest 注入 `sed "s/canary3/canaryX/"` 仅替换首处、任务书多处 `canary3` 仍命中 → 恒真（BAD），但 c3 目的（定案关键词覆盖）已由 reviewer 独立 grep 验证；建议 engineer 后续改用 `replaceAll` 或 `grep -c` 计数断言
**判决**：**Accepted**

#### 第 4 轮 engineer 自审（订正返工：把「已生效」错误结论改为事实「未生效」）

**自主逐行审查**（改三 agent 注释 + `lessons §3.18` + `milestones` + `issues.yaml` + 本任务书 + 证据脚本；无子代理）：
- 三 agent 注释：逐字同口径（未生效 + canary3 人工 reject + `message` 不可区分 + `opencode service restart`）；`grep -c "已实测生效"` == 0；两条 `external_directory` deny 保留（各 ==2）。
- 任务书正文（`## 审阅记录` 之前）：canary1→canary2→reload→canary3 纠正链、人工 reject、BLOCKED、替代证据齐；`grep "已生效"` 于正文 == 0（历史误判句改用「已经生效」以不误触断言）；**未改写 reviewer 既有审阅记录**。
- `lessons §3.18`：错误判据（`message` 含 `Permission denied` ⇒ 生效）已删；并存 1 处 §3.18（无重复）。
- 防造假：门控 `rc` 与 `check_issues` 计数现场取得；`--selftest` 6 条均可达 FAIL（`/g` replaceAll，修 reviewer 非阻断项恒真）；`--inject` md5 前后对账（`849be363…→cf017921…→849be363…`）；**未用** `git checkout/restore/stash`。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 三 agent 注释标「已实测生效」与用户更正矛盾 | ✅已修 | 改「未生效…待 `opencode service restart` 复验」 | `chk_c2` PASS；`grep -c 已实测生效`=0 |
| 任务书 canary 段/定案段标「已生效」✗ | ✅已修 | 改未生效 + 纠正链 + 验收 3 标 BLOCKED + 替代证据 | `chk_c3` PASS（正文无 stale 已生效） |
| `lessons §3.18` 含错误判据（message 含 `Permission denied` ⇒ 生效） | ✅已修 | 删错误判据、改「不可区分 ⇒ 靠用户观察」 | `chk_c4` PASS（错误判据串已删） |
| reviewer 非阻断：`chk_c3` 注入恒真（sed 仅首处） | ✅已修 | 注入改 `/g`（replaceAll）+ 断言覆盖 | `--selftest` c3 注入后 rc=1（非恒真） |
| 遗留登记缺失 | ✅已修 | 新增 `ISS-199`（open）+ `milestones` 待办行 | `check_issues` 24→25 open；`chk_c6` PASS |

**判决**：finding 均已修；权限层未生效属**用户操作待复验**（BLOCKED，非本次可修）；状态标 `待验收`。

#### 复验轮 reviewer 验收

**更正**：第 1 轮 ③ 将 `message:"Permission denied: external_directory"` 判为"自动 deny"——**已被用户证伪**（实为 ask + 人工 reject，message 不可区分）；该结论**不作为生效证据**。
**文本核**：三 agent 注释均为「未生效…待重启复验」，无"已实测生效/已生效"残留 ✓；两条 deny 保留 ✓。
**任务书核**：纠正链完整（canary1→2→reload未见效→3 ask+用户reject→reviewer不可采信）；验收 3 标 BLOCKED + 替代证据 ✓；无"已验证生效"结论 ✓。
**lessons §3.18**：错误判据（message 含 `Permission denied` ⇒ 生效）已删 ✓；新判据 = 用户观察 + 子代理不得下结论 ✓。
**登记核**：`ISS-199` 存在（open）✓；`check_issues.py` rc=0（25 open）✓；`milestones.md` 待办行（用户操作：重启→复验）✓。
**证据脚本**：`/g` 修复后 `--selftest` 6 条均可达 FAIL（含上轮恒真的 c3 现 rc=1）✓。
**门控**：`make check`/`check-knowledge-refs`/`check-no-residue` 各 rc=0 ✓。
**判定**：**Accepted**（规则层 ✅ / 权限层 ⏳ BLOCKED〔待 `opencode service restart` 复验，`ISS-199`〕）。

---

## 更正（2026-10-13）

> **只追加、不改写上文原结论**（原结论：「权限层 ⏳ 未生效，待服务重启复验」）。

- **服务重启后全局 deny 生效 ✓**：用户执行 `opencode service restart`（2026-10-13）并复验——出界 `cd /mnt/tao` / `cd ..` ⇒ `{"type":"permission.rejected","message":"Permission denied: external_directory"}`、**无人工介入**（用户确认仅弹过一条）；`/mnt/*`、`/home/ubuntu/tao/*` 均无人工介入即拒绝；对照仓内 `cd .work` 与 `/tmp/opencode/**` 正常放行 ✓。
- **已知局限**：`cd ~`（`/home/ubuntu/*`）**仍 ask** ⇒ 属已知设计（若罩 `/home/ubuntu/*` 会误伤既有放行 `~/.cache`/`~/.config/opencode`/`~/.local/share/opencode`/`~/t.a.o`）⇒ 靠**规则层兜底**（`AGENTS.md` 子代理硬约束禁 `cd ~*`）+ **夜跑冒烟含该项**。
- **规则层同日均已落地**（三 agent workdir 硬约束 + `AGENTS.md` 第 12 条）。
- **依据** = 用户确认观察 + canary4 逐字返回（系统固定文案不可反推，见 `lessons §3.18`）；`ISS-199` 已 `closed`（`resolved_by` = 用户重启 + 复验）。
