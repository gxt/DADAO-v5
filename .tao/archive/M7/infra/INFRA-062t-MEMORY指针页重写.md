# INFRA-062t: `MEMORY.md` 重写为纯指针页（去副本化）

**模块**：infra
**项目里程碑**：M7
**依赖**：`INFRA-061t`（**同改 `tools/spec/check_scope.py` 与 `.tao/knowledge/**`，必须串行**）
**状态**：已验证

> 本任务书由**主会话**依用户 2026-10-11 裁定方向撰写（非常规 architect 起草，已披露）。

## 用户裁定（2026-10-11，**原话**）

> 「`.tao/knowledge/` 目录下的三个文件：`MEMORY.md`,`changelog.md`,`milestones.md`，有重复的内容，有不必要的内容，应该如何界定，你有何建议」
> 「为何要删 `MEMORY.md`?」
> **裁决**：「（B）保留 + 重写为纯指针页」

## 目的

`MEMORY.md` 现为「多份真源的一旧副本」（**已实证漂移**：引用今日已删除的 `docs/integ-interface-alignment.md`；仍称 `spec/` 含 `Process-0x`）。按用户裁定：**保留文件、改为纯指针页**——只写「哪类信息看哪里」，**不复制任何事实**；并写入维护规则「**勿在此复制事实**」。

## 接口规范

### 输入：逐节处置（**现场已核；执行时复核**）

| 现 `MEMORY.md` 节 | 处置 |
|---|---|
| 这是什么 / 关键目录速查 / 职责边界 / 如何参考 0628 | **删**（改指针：见下「指针页内容」；真源 = 根 `README.md` / `.tao/README.md` / `AGENTS.md`） |
| 当前进度（**已陈旧**） | **删**（指针 → `.tao/knowledge/milestones.md`） |
| 重要决策（11 条） | **删**（指针 → `.tao/adr/` + `AGENTS.md`） |
| 规范版本对应 | **删**（指针 → 根 `README.md`「当前版本号」） |
| 文件映射 spec → contracts | **删**（指针 → `spec/README.md` 投影表） |
| 0.5.4 vs 0.4.1 差异 / 不变的差异 | **删**（历史；git 可回溯） |
| **上游 ↔ v5 偏离台账** | **删副本**；但须**先逐条比对**根 `README.md` 同名节，**缺项补入根 `README.md`**（改既有，**不新建文件**）——避免丢信息 |

### 输出

1. **`MEMORY.md` 重写为纯指针页**：**≤20 行**；只有「主题 → 真源」指针；**无任何事实副本**（无进度表 / 无决策列表 / 无版本表 / 无目录详解）；含维护规则一行，如：
   > **维护规则**：本页只做导航；任何事实以真源为准，**勿在此复制**（复制必漂移）。
   指针至少覆盖：项目总览/里程碑/版本号（根 `README.md`）、当前进度/任务流水/规划中/裁定（`.tao/knowledge/milestones.md`）、决策（`.tao/adr/`）、交互目录/角色/命令/编号（`.tao/README.md`）、技术规范（`spec/` + `spec/README.md`）、工程流程规范（`docs/Process-0x` + `docs/README.md`）、合约（`.tao/knowledge/contract-*.md`）与机器数据（`contracts/`）、参考仓库（`.cache/refs/` + `manifests/`）、issue/教训（`issues.yaml`/`lessons.md`）、历史（`.tao/archive/M*/`）、临时区（`/tmp/opencode/<任务ID>/`）。
2. **偏离台账缺项补入根 `README.md`**（逐条比对表 + 结论入完成区）。
3. **连带判定（逐条「改 / 不改 + 理由」，**不写死计数**）**：`git grep -n 'MEMORY\.md'`（活文件；计数现场统计）——至少含 `.opencode/commands/{complete,status}.md`、`.tao/README.md`、`AGENTS.md`（**首读清单保留 `MEMORY.md`**，因其仍是入口页）、`.tao/adr/*`、`docs/{DDLN/README,Process-04,repository-layout}.md`、`.tao/knowledge/{milestones,issues,lessons}.*`、`.tao/tasks/**`（**历史叙述保留**）。**「进入项目」首读清单不变**（`MEMORY.md` 保留）。
4. **`tools/spec/check_scope.py`**：`HISTORY_PREFIXES` 是否仍含 `.tao/knowledge/MEMORY.md` ——**按重写后现场判定**（若页内已无历史字样 ⇒ 去掉该豁免；否则保留），**结论与理由写入完成区**。
5. `.tao/archive/**`、已归档任务书、`spec/`、`contracts/`、`tests/vectors/` 一律**不动**。

### 约束

- 只动上述范围；越界须披露。**计数 / 条数 / 引用数不写死**。
- 临时目录 `/tmp/opencode/INFRA-062t/`；**不提交 git**；禁 `git add -A`/`.`。
- 反例注入还原**禁** `git checkout`/`restore`/`stash`；一律 `cp` 备份 + md5 对账。
- 任务书 / 记录 / 文档中**不得出现字面 `.work/<具体路径>`**（用 `<>` 占位），否则 `check-knowledge-refs` 判悬空、`make check` 自伤（`lessons §8.56`）。

## 验收标准

1. **纯指针页**：`MEMORY.md` **行数 ≤20**（`wc -l` 真实输出）；`grep` 证明**无**进度表 / 决策列表 / 版本表（如：无 `| M1 |`、无 `## 重要决策`、无 `0.4.1` 之类事实副本）；含维护规则行。
2. **信息未丢**：原「上游↔v5 偏离台账」**逐条比对表** + 缺项已补入根 `README.md` 的证据（`git diff` / `grep` 真实输出）。
3. **无副本残留**：`MEMORY.md` 中不出现「进度 / 版本 / 决策」类事实条目（人判 + `grep` 佐证）。
4. `make check`（L1）**EXIT=0**（捕获**命令自身**退出码，禁 `cmd | tee` 吞码）；`make check-no-residue` EXIT=0。
5. **注入反例可失败**：临时把 `MEMORY.md` 塞回一段事实副本（如旧版本表行）⇒ 证据脚本 / 断言 **FAIL**（如行数 >20 或匹配到事实模式）⇒ `cp`+md5 还原 ⇒ 回绿（留真实输出）。
6. **一键证据脚本**落 `.work/evidence/<任务ID>/`（能失败、可达 FAIL、结构断言、计数不写死、捕获退出码）。
7. **完成区**（≤30 行）与真实输出逐条对齐；逐节处置 + 连带判定逐条列明。

## 完成区

**测试结果**：`make check`（L1）EXIT=0；`make check-no-residue` EXIT=0；`check-knowledge-refs` EXIT=0。证据脚本 `.work/evidence/<任务ID>/run.sh` 10/10 PASS（日志 `.work/log/infra/INFRA-062t-*.log`）；注入自检 PASS。
**修改文件**：`.tao/knowledge/MEMORY.md`（重写 144→18 行纯指针页）、`README.md`（+「上游 ↔ v5 偏离台账」节：7 行 + 2 订正说明）、`tools/spec/check_scope.py`（`HISTORY_PREFIXES` 移除 `.tao/knowledge/MEMORY.md`）、`.tao/knowledge/milestones.md`（+`INFRA-062t` 流水行）、`.tao/README.md`（`knowledge/` 描述改「纯指针页/入口导航」）、`.opencode/commands/status.md`（§3 改读 `milestones.md`「当前进度」）、`.opencode/commands/complete.md`（§A/§注意 改纯指针页口径）、`docs/DDLN/README.md`（失效指针改写）、本任务书（状态/完成区/自审；§验收 6 的字面证据脚本路径已改占位 `<>`）。**未动**：`.tao/archive/**`、`spec/`、`contracts/`、`tests/vectors/`、`AGENTS.md`。
**验收结果**：
- ① 纯指针页：`wc -l .tao/knowledge/MEMORY.md`=18（≤20）；事实副本 `grep`=0（无 `## 重要决策`/`| M1 |`/`0.4.1`/`## 当前进度`）；含维护规则行「勿在此复制」。
- ② 信息未丢：README 台账 7 行 + 2 订正说明与原 `MEMORY.md` **逐字一致**（`diff` 仅表头差、数据行 byte-identical）。
- ⑤ 注入反例：追加事实副本 ⇒ C1=24>20、C3 命中 2 ⇒ **FAIL**；`cp`+md5 还原（md5 `3a3f38ea…` 注入前=还原后）⇒ 回绿。
**新发现/坑**：原台账**非**根 README 同名节的副本（`SPEC-093t` 直接写入 `MEMORY.md`，根 README 仅一句「成型（6 项）」摘要）——任务书前提不成立 ⇒ 按「缺项补入」重建 README 该节。`git grep 'MEMORY\.md'` 活文件 = 11 文件（现场统计）。
**遗留问题**：`docs/Process-04`（§4.3/§6§3/§7/§8 述「归档 MEMORY 进度行」，重写后恒空=no-op）与 `.tao/adr/adr-0013`（指针「登记 `MEMORY.md` 偏离台账」漂移）**未改**——前者属工程规范修订、后者改 Accepted ADR 须用户确认；建议后续单独清理。

## 审阅记录

#### 第 1 轮 engineer 自审

**逐节处置**（原 `MEMORY.md` → 处置）：这是什么/关键目录速查/职责边界/如何参考 0628 → 删（真源 = 根 README/`.tao/README.md`/`AGENTS.md`）；当前进度（陈旧）→ 删（→`milestones.md`）；重要决策（11 条）→ 删（→`.tao/adr/`+`AGENTS.md`）；规范版本对应 → 删（→根 README「当前版本号」）；文件映射 spec→contracts → 删（→`spec/README.md` 投影表）；0.5.4 vs 0.4.1 差异/不变的差异 → 删（历史，git 可回溯）；上游 ↔ v5 偏离台账 → 删副本、**逐字迁入**根 README 同名节。

**偏离台账逐条比对**（`条目｜根 README 改前已有？｜处置`）：① exit port｜无｜补第 1 行；② `fence` SBZ｜无｜补第 2 行；③ 测试机地址映射/复位值｜无｜补第 3 行；④ `ra0`（MemRAS 简化）｜无｜补第 4 行；⑤ `e_flags` 版本字段｜无｜补第 5 行；⑥ M1/M2 排除口径｜无｜补第 6 行；⑦ 汇编伪指令集收缩｜无｜补第 7 行。（皆「无」：改前根 README 仅 M2 一句「偏离台账成型（6 项）」摘要，无逐项内容。）

**连带判定（`git grep -n 'MEMORY\.md'` 活文件，计数现场统计 = 11 文件）**：
- **改**：`status.md`（§3 读 MEMORY「当前进展」段已不存在 ⇒ `/status` 会失效；改读 `milestones.md`「当前进度」）；`complete.md`（§A「MEMORY 摘要行」+§注意「超 200 行」⇒ 改纯指针页口径）；`.tao/README.md`（`knowledge/` 描述「状态摘要」不实 ⇒ 改「纯指针页/入口导航」）；`milestones.md`（加 `INFRA-062t` 流水行）；`docs/DDLN/README.md`（指针「0.5.4 与 0.4.1 的差异」指向已删内容 ⇒ 改「项目知识入口导航」）。
- **不改**：`AGENTS.md`（任务明示「进入项目」首读清单保留 `MEMORY.md`）；`.tao/adr/adr-0013`/`adr-0016`（已 `Accepted` 决策记录，改正文须用户逐条确认；adr-0013 指针漂移已披露）；`docs/Process-04`（归档规范「MEMORY 进度行」条款对 M7+ 恒空 = no-op 非错误；改工程规范超最小范围—遗留）；`docs/repository-layout.md`（无引用）；`.tao/knowledge/{issues,lessons}.*`（无引用）；`.tao/tasks/**`（历史叙述保留）。

**finding**：自审未发现缺陷（`MEMORY.md` 18 行 ≤20、无事实副本；`check_scope.py` 移除豁免后 `check-scope` 仍 PASS——MEMORY 无旧字段 `excluded_m1`）。
**判决**：无待修 finding ⇒ 状态置「待验收」。

#### 第 1 轮 reviewer 验收

**重跑（真实输出/退出码；日志 `/tmp/opencode/INFRA-062t-review/`）**：
- `make check` rc=0（L1 PASS，check-knowledge-refs 0 悬空）；`make check-modules` rc=0（L2：83/83 + QEMU 86/86 + 15/15 + 5/5 + m5-e2e 10/10 + semihost PASS）；`make check-no-residue` rc=0；`make check-scope` rc=0（旧字段非历史文件=0）。禁 tee，逐条 `cmd; echo rc=$?`。
- 纯指针页：`wc -l`=18（≤20）；事实模式逐项 grep=0：`## 当前进度`/`## 重要决策`/`## 规范版本对应`/`## 文件映射`/`0.4.1`/`0.5.4`/`| M[0-9]`/`excluded_m1`/旧悬空引用；维护规则行「勿在此复制」L3；任务书要求的 15 类指针逐项 grep=1 全覆盖。
- 信息不丢：`git show HEAD:` 原 MEMORY 台账节 vs 现根 README 节——**数据行 7 条 diff=0**（md5 `f5923156…` 双侧相同）、**订正说明 2 段 diff=0**（md5 `c26e7c8e…`）；仅引言段改写（「7 项」+`SPEC-106t` 增至 7 项——`SPEC-106t` 真实存在且归档述「台账 6→7」）+ 尾空行差。**无丢失、无凭空新增**；engineer「数据行/订正段 byte-identical」属实。
- 连带逐条：`status.md` §3 改读 `milestones.md`「当前进度」且该节实存（里程碑/规划中/裁定齐，语义自洽）；`complete.md` §A/§注意已改纯指针页口径；`.tao/README.md` knowledge 描述已改；`docs/DDLN/README.md` 失效指针（0.5.4/0.4.1 差异）已改「项目知识入口导航」；`git grep -n 'MEMORY\.md'` 活文件逐条判——complete.md×3/.tao/README.md/docs/DDLN：**活指针（已更新）**；`AGENTS.md:18` 首读清单保留且 MEMORY.md 存在（未误删）；adr-0013:180「登记 MEMORY 偏离台账」**指针漂移**（台账现于根 README）+ adr-0016 上下文列举——Accepted ADR 不擅改，遗留已披露（非阻断）；Process-04×5 处「MEMORY 归档行」条款重写后恒空=no-op（遗留，非阻断）；repository-layout/issues/lessons/milestones 引用=0；`.tao/tasks/**` 2 处历史叙述保留（合规）。
- `milestones.md`：`INFRA-062t` 流水行已加，每格单行，格宽 10/3/10/12（≤40）。
- 证据脚本（`.work/evidence/<ID>/run.sh`）五项：一键可跑 ✓；能失败 ✓；结构断言（C1 行数/C3 模式/C4 指针集/C5 台账行+要点）✓；计数现场统计（`${#toks[@]}`/awk，不写死）✓；退出码逐条 `cmd; rc=$?` 捕获 ✓。重跑正常模式 10/10 PASS rc=0；engineer 自注入复核属实（C1=24 FAIL、C3 命中 2 FAIL、md5 `3a3f38ea…` 注入前=还原后）。
- **reviewer 独立注入（与 engineer 不重复）**：末尾加一行**版本事实**「规范版本：SimRISC 0.5.4 / AEE·ABI 0.9.2（已冻结）」（19 行≤20）⇒ **脚本 rc=0 全绿、未报 FAIL**；追加「`| M2 |` 型进度行」（20 行）⇒ **仍 rc=0 全绿**。`cp`+md5 还原（`3a3f38ea…` 前=后，快照对账 SNAPSHOTS_MATCH）⇒ 回绿（final rc=0，10/10）。

**finding**：
- **阻断**：证据脚本 C3「无事实副本」模式类覆盖不全——版本事实类仅字面 `0.4.1`、进度行仅字面 `| M1 |`；对「版本事实（`0.5.4` 等）」「`| M2 |` 型进度行」两类**明令禁止的事实副本注入不报 FAIL**（实测 rc=0）⇒ **验收 5 对该类反例不成立**、验收 1/3 的「版本类事实副本」无断言覆盖。**整改（范围极小）**：C3 模式泛化（建议 `[0-9]+\.[0-9]+\.[0-9]+` + `\| M[0-9]+ \|` + 决策列表泛化），重跑正常/自注入模式，并接受 reviewer 复验（须对我上述两条注入回证 FAIL）。
- 非阻断：README L41「成型（6 项）」与台账「7 项」并存（M2 时点叙述，SPEC-106t 6→7 有据）；adr-0013 / Process-04 漂移遗留（已披露，处置须用户裁定/工程规范修订）。交付物内容本身无缺陷（18 行纯指针、信息零丢失、连带一致）。

**判决**：**Needs Revision**（唯一阻断项 = 证据脚本 C3 模式泛化 + 复验；其余验收项均经我独立重跑通过）。

#### 返工 1（C3 模式泛化）— engineer

**reviewer finding 原文要点**（第 1 轮验收，阻断）：证据脚本 C3「无事实副本」模式类覆盖不全——版本事实类仅字面 `0.4.1`、进度行仅字面 `| M1 |`；对「版本事实（`0.5.4` 等）」「`| M2 |` 型进度行」两类注入**不报 FAIL**（实测 rc=0）⇒ 验收 5 不成立。整改 = C3 模式泛化 + 复验回证 FAIL。

**改了什么**（仅证据脚本 `.work/evidence/<任务ID>/run.sh`；交付物未动）：C3 由字面单点改为**模式类**，新增 `FACT_RE`（`^#+` 层级自适应）：
- 事实类小节标题：`当前进度`/`重要决策`/`规范版本对应`/`文件映射`/`关键目录速查`/`职责边界`/`关键差异`/`不变的差异`/`这是什么`/`如何参考`/`上游`（「决策 / 文件映射」类一并泛化）；
- 版本事实：`[0-9]+\.[0-9]+\.[0-9]+`（三节号，覆盖 `0.5.4`/`0.9.2`/`0.4.1`/`0.5.3`）；
- 进度行：`\|[[:space:]]*\**M[0-9]+`（表格首格 `| M<数字>`，含 `**` 粗体，覆盖 `| M1 |`/`| M2 |`/`| **M1 归档** |`）。
`--inject` 自检改**逐类**用例（version / progress / legacy-heading），共用 `cp` 备份 + md5 对账；C3 抽为 `check_c3()` 单独可调用（隔离 C1 行数）。计数仍现场统计、不写死；被检命令退出码逐条 `cmd; rc=$?`，无 `tee`。

**重跑真实输出（逐条捕获退出码）**：
- `run.sh`（正常模式）**rc=0**：`C1`=18≤20、`C3`=0 命中、`C4`=14/14、`C5a`=7、`C5b`=7/7、`C6`=0、`C7` rc=0、`C8 make check` rc=0、`C9` rc=0 ⇒ `content=0 gate=0`。
- `run.sh --inject` **rc=0**：① 版本行 `… 0.5.4 / …0.9.2…` ⇒ C3 命中 **1 FAIL**；② `| M2 | 已验证 | …` ⇒ C3 命中 **1 FAIL**；③ 回归 `## 当前进度` + `| **M1 归档** | ✅ 0.4.1 |` ⇒ C3 命中 **2 FAIL**；三类 `cp` 还原均回绿，md5 前=后=`3a3f38ea…`。
- 手动注入（`cp`+md5，无 git）：版本行 / `| M2 |` 行 grep 各命中；两次还原后 `grep -c`=0，md5 `3a3f38ea…` 注入前=还原①=还原②（MD5_MATCH）。
- **防过度泛化**：合成合法指针页（含 `M7`/`SimRISC-*`/`Process-0x`/`/tmp/opencode/<任务ID>/`）⇒ `FACT_RE` 命中 **0**（无假阳性）；当前 `MEMORY.md` 亦 0 命中。
- 门控：`make check` rc=0、`make check-no-residue` rc=0。日志：`.work/log/<模块>/INFRA-062t-rework-*.log`。

**engineer 自审（返工 1）**：逐行复核脚本——`check_c3` 于 `content_checks` 调用前已定义、返回码经 `|| ok=0` 聚合；`FACT_RE` 三分支（标题/三节号/表格首格 `M<数字>`）逐条手工构造正反例验证；`--inject` 三类用例 `cp`+md5 对账；无 `tee`、无 `set -e` 掩盖、备份均落 `/tmp/opencode/<任务ID>/`。自审无待修 finding。

**判决**：原阻断 finding 已修（✅已修，2 类新反例均回证 FAIL）；状态回 `待验收`。

#### 复验轮（第 2 轮 reviewer 验收）

- **独立注入反例①**（版本事实 `0.5.4` 行）：C3=1 **FAIL**（命中 `[0-9]+\.[0-9]+\.[0-9]+`）rc=1；`cp`+md5 还原 ⇒ md5 `3a3f38ea…` 前=后，回绿 rc=0。
- **独立注入反例②**（进度行 `| M2 |`）：C3=1 **FAIL**（命中 `\|[[:space:]]*\**M[0-9]+`）rc=1；`cp`+md5 还原 ⇒ 前=后，回绿 rc=0。
- **正常模式**：`run.sh` 10/10 PASS rc=0（C1=18、C3=0、C4=14/14、C5a=7、C5b=7/7、C6=0、C7/C8/C9=0）。**engineer `--inject`** 3 类（version/progress/legacy-heading）均 FAIL ⇒ cp+md5 还原回绿（md5 `3a3f38ea…`）。
- **交付物未变**：8 项 md5 全 MATCH（对照上轮快照）；git status 同上轮（8 modified + 任务书 untracked）；`.work/` 内容 gitignored、不影响交付物。
- **假阳性对照页**（含 `M7`/`SimRISC`/`Process-0x`/`<任务ID>` 的指针页）：C3=1 FAIL（`| M7 规划… |` 命中 `\|[[:space:]]*\**M[0-9]+`）——当前 `MEMORY.md` 不含此类行、**不受影响**（正常 rc=0）。**非阻断建议**：进度行模式收紧为 `\| M[0-9]+ \|`（要求行尾闭合 pipe），避免指针表里程碑提及行误报。
- `make check` rc=0（0 悬空）。

**判定**：**Accepted**（阻断项已修复、两条独立注入均回证 FAIL、交付物未变、门控全绿；附非阻断建议 1 条）。
