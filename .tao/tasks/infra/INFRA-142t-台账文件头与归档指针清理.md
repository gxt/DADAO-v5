# INFRA-142t: 里程碑台账文件头说明与删除历史归档指针

**模块**：infra
**项目里程碑**：M11
**依赖**：`INFRA-141t`（三分表；本任务只改文件头与归档口径，不改表体）
**状态**：已验证

## 用户授权（原话）

> 「milestones.md：在文件开头把三个类别和每一列写什么描述清楚，不要留什么 M9/M10归档指针」

## 目标

### 1. `milestones.md` 文件头

- **保留**唯一断言行：`> **项目里程碑 = M11**（…本行是唯一断言；只在里程碑切换时改）`（`check-milestone` 依赖它）。
- **删除** `M9 归档指针` / `M10 归档指针` 两个 blockquote。
- **新增**一段「本页结构与列含义」说明，写清：

```markdown
> **本页只维护任务台账**：历史任务见 `.tao/archive/`，当前讨论/规划见 `.tao/knowledge/discussing.md`。

本页分三张表，**分类 = 任务书 `**状态**`**（不另设状态列）：

| 表 | 收录状态 | 列 |
| --- | --- | --- |
| 待开始（未开工） | `待开始` | `编号` / `预估时间` / `一句改动` |
| 进行中（已提交待验收 / 待返工） | `待验收`、`待返工` | `编号` / `预估时间` / `一句改动` |
| 已验证 | `已验证` | `编号` / `完成时间` / `一句改动` |

- **预估时间**：人工估值，只作参考；格式 `N h` / `N–M h` / `N 天` / `N–M 天` / `N min`。
- **完成时间**：`YYYY-MM-DD HH:MM`；「已验证」表按完成时间**倒序**（同时间按编号升序）。
- **一句改动**：≤120 字符，只作索引，细节在任务书。
```

（说明段放在两表/三表**之前**、`## 待开始…` 之后不要重复。）

### 2. `docs/Process-04-里程碑归档规范.md`

- 删除「活台账**加归档指针**」的要求（§「活台账只留」、§7 的 `.tao/knowledge/milestones.md` 行、§113 的「归档指针行」表述）。
- 改为：归档后活台账**只留当前/维护任务行**，**不写归档指针**（历史由 `.tao/archive/<M>/` 自身承载）。

## 范围 / 非范围

**在范围内**：`.tao/knowledge/milestones.md`（仅文件头 blockquote 区域）、`docs/Process-04-里程碑归档规范.md`、本任务书、`milestones.md` 自身行。

**不在范围**：三张表的内容/行序、门控脚本、`AGENTS.md`、`Process-07`。

## 验收标准

1. `make check-milestones-fresh` rc=0；`make check-milestone`（或等价的目标）rc=0（证明 `项目里程碑 = M11` 断言仍在）。
2. `grep -n 'M9 归档指针\|M10 归档指针' .tao/knowledge/milestones.md` 命中 0。
3. 文件头包含三表说明与列含义（人工核对清单：类别↔状态映射、预估格式、完成时间格式、一句改动 ≤120）。
4. 三张表的**行内容与行序未变**（`git diff` 仅文件头区域）。
5. `docs/Process-04` 中「归档指针」要求已删除，其余归档流程未改。
6. 完成区 ≤30 行、无运行期路径。

## 说明

- 只改说明文字与归档口径，**不动门控判据**；若 `check-milestones-fresh` 因说明段（非表格行）报错，说明门控把说明误判成表格，需先停下报告，不要改门控。

## 完成区

**测试结果**：通过 14/14（一键证据：9 项检查 + 2 注入反例 + 2 次还原 md5 对账 + 1 次回绿）；门控 `make check-milestones-fresh` rc=0、`--self-test` rc=0（11 类注入各自可达 FAIL）。
**修改文件**：`.tao/knowledge/milestones.md`（文件头说明段、删 M9/M10 指针、本任务行移入「进行中」）、`docs/Process-04-里程碑归档规范.md`（3 处归档指针要求）、本任务书（状态 + 完成区 + 审阅记录）。
**验收结果**：
- 先 `git merge master`（含已合入的 INFRA-141t 三分表）再写说明段，故说明段与三表口径一致。
- `make check-milestones-fresh` → PASS（待开始 7 / 进行中 1 / 已验证 96；A1 分类 / A2 覆盖 / A3 长度 / A4 倒序 / A5 格式无状态列），rc=0。
- `make check-milestone` → rc=2，**首个失败项 = M11 无 `m` 册**（`check_milestone_tasks` 现场统计「M11（断言 1 处）」；`master` 的 `.tao/tasks/**` 亦 0 份 `m` 册 ⇒ M11 未收口的预置信号，与本任务无关）；其前置 `check-spec-archive` / `check-spec-archive-verify` / `check-sync-nonmaskable` / `check-l3-report` 全 PASS。
- `grep 'M9 归档指针\|M10 归档指针'` → 0 命中；`项目里程碑 = M11` 仍恰好 1 处。
- `git diff` 仅 3 文件：milestones 文件头 + 本任务行、Process-04 三处、本任务书；其他任务表行零改动（证据脚本 7a 断言）。
- `check_tasks.py --strict` rc=1（**报告型**）：① 漏收尾 1 条 = 本任务（完成区已填、状态 `待验收`，即 `/complete` 前正常态）；② 已立未开工 7 条，不阻断。
- 附：`check-knowledge-refs` / `check-archive` / `check-knowledge-dir` 均 rc=0。
**新发现/坑**：
- 任务 worktree 的 `.work` 是主工作树共享软链 ⇒ 证据脚本不能由 `$0` 推仓库根（实测误检主树、注入打到主树），须按 cwd 取根。
- `make check` 唯一红 = `check-patch-tree` 4 条（qemu `mmap.c` / gem5 `se_workload.cc`）：在主工作树（干净 master、零本任务改动）复现**同样 4 条** ⇒ 归并发 QEMU-085t / GEM5-028t；本任务 3 个改动文件命中 `components/` **0**。
- `MEMORY.md` 仍写「归档指针见页首」，指针已删 ⇒ 建议后续任务一并校正（本任务范围外）。
**遗留问题**：无（`m` 册红属 M11 未收口预置信号，非本任务遗留）。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-08）

逐行审查 `milestones.md` 文件头 + `Process-04` 三处改动 + 本任务行迁移：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 说明段若落在小节内，其表格会被 A5「不得出现状态值」误杀、被 A2 正文扫描污染 | ✅已修 | 说明段置于三表之前、首个 `##` 标题之上 | 证据脚本检查 1 rc=0；检查 6 四要素齐全 |
| F2 状态改 `待验收` 后本任务行留在「待开始」表会 A1 分类不一致 | ✅已修 | 仅本任务行移入「进行中」，预估时间/一句改动逐字保留 | 证据脚本 7a 其他任务行零改动；检查 1 rc=0 |
| F3 说明段若把小节标题写成引用块，会重复标题/扰乱三表次序判定 | ✅已修 | 说明段不用小节标题（仅列类别名） | 检查 1 三表次序 PASS |
| F4 证据脚本按 `$0` 定位仓库根，遇 `.work` 共享软链会误检主树（实测命中） | ✅已修 | 改为 cwd 取根 + 打印被检树 | 重跑 14/14 PASS；主树 `git status` 干净 |
| F5 `Process-04 §9` 教训仍提「归档指针（blockquote）」 | ❌不修 | 任务书仅要求删三处「要求」（§2/§6/§7）；§9 属历史教训，表格完整性纪律仍适用 | `grep` 检查 8：`加归档指针`=0、`归档指针行`=0、`不写归档指针`=2 |

判决：无未修缺陷（F5 为非缺陷项）⇒ 置 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-08）

**判决：Accepted**（以下全部为 reviewer 独立重跑，未采信完成区转述；未 commit / 未 push）

**重跑记录**（workdir 内相对路径；退出码取命令自身，非管道）
- `make check-milestones-fresh` ⇒ **rc=0**：待开始 7 / 进行中 1 / 已验证 96、三表 104 行 = 7+1+96（说明段的表**未被计入**任何一表）、A1/A2/A3/A4/A5 全过。
- `python3 tools/infra/check_milestones_fresh.py --self-test` ⇒ **rc=0**，`注入 PASS=11`（十一类注入逐条 `rc=1 marker=True`）。
- 重跑 engineer 一键证据脚本 ⇒ **rc=0，`SUMMARY: PASS=14 FAIL=0`**（含注入 A/B → 指针命中/他行改动 FAIL、`cp` 还原 md5 相同、回绿）。
- `make check-milestone` ⇒ **rc=2**，唯一失败 = `VIOLATION: 当前里程碑 M11 在 .tao/tasks/** 下无 m 册`（预置、预期）；现场 `当前里程碑（现场统计）: M11（断言 1 处）`；前置 `check-spec-archive` / `check-spec-archive-verify` / `check-sync-nonmaskable` / `check-l3-report` 均 PASS ⇒ **断言未丢，红因仅为无 m 册**。
- `grep -c '项目里程碑 = M11'` ⇒ **1**；`grep -n 'M9 归档指针\|M10 归档指针'` ⇒ **0 命中**（rc=1）。
- `make -k check` ⇒ **rc=2，唯一红 = `check-patch-tree 4 problem(s)`**：qemu `linux-user/mmap.c` ⑨/⑥ + gem5 `se_workload.cc` ⑨/⑥；在**主工作树**（master、`git status` 干净）跑 `make check-patch-tree` 复现**同样 4 条** ⇒ 归并发 QEMU-085t / GEM5-028t；本任务 3 改动文件命中 `components/` **0**；其余 L1 子门控无第二红。
- `check_knowledge_refs` / `check_archive` / `check_knowledge_dir` ⇒ **rc=0 / 0 / 0**；`check_tasks.py --strict` ⇒ **rc=1**（漏收尾 1 = 本任务 `待验收`、已立未开工 7，与完成区一致）。

**独立注入**（reviewer 自做，`cp` 备份 + md5 → 改 → 跑 → `cp` 还原 → md5 相等 → 回绿；未用 git 还原）
- 注入① 把文件头说明段整段挪进 `## 待开始` 小节内 ⇒ **rc=2，18 项 VIOLATION**（说明表被判为待开始表：表头不符 / 含状态列 / 编号不合格式 / A1 无任务书）⇒ 门控可达 FAIL，且证明说明段**必须**留在首个 `##` 之前。
- 注入② 删 `## 进行中（已提交待验收 / 待返工）` 标题 ⇒ **rc=2** `ERROR: 缺小节 … ⇒ fail-closed`。
- 还原：两次 `md5 = 806e9cc3818b0f52fc697ee4ebe78655`（与注入前逐位相等），回绿 `make check-milestones-fresh` **rc=0**。披露：注入①首次备份因目录未建失败，改用逆操作重建，**以同一 md5 校验通过**。

**约束核验**
- 改动文件恰 3（milestones / Process-04 / 本任务书）；`git diff master -- milestones` 表行增删**仅 `INFRA-142t` 一行**（待开始 → 进行中），其余任务行逐字未变；`Process-04` 仅 3 行改动（§2 活台账只留、§5 指针节、§7 原台账表）。
- 文件头四要素齐：类别↔状态映射（待开始/进行中(待验收·待返工)/已验证）、各表列、预估 `N h`…、完成 `YYYY-MM-DD HH:MM`+倒序、一句改动 ≤120；位于首个 `##`（L19）之前；完成区 16 行 ≤30、无运行期路径。
- `MEMORY.md`「归档指针见页首」在本 worktree 仍在，因 **HEAD 落后 master 一个提交 `76f3bd3a`**（`git merge-tree` 预演 **0 冲突**、本任务未改 MEMORY.md）⇒ 合入后无残留。
- **finding（文档级，不阻断）**：`Process-04 §7` 仍留「`MEMORY.md` 在『当前进度』表内加一行归档指针」，与「活台账不写归档指针」并存；任务书只点名三处、该行属 MEMORY 流程 ⇒ 记 finding 交 architect 收尾统一。完成区「MEMORY.md 仍写归档指针见页首，建议后续任务校正」已被 `76f3bd3a` 修掉，表述过时（文档级）。

**三问**：① 规则写清楚了——三表↔状态、每表列、预估/完成时间格式、≤120 全部逐条列出，且与三张表实际表头逐字一致；② 删指针未破坏归档流程——§2/§5/§7/§8/§9 完整，仅 milestones 口径改为「不写归档指针」，残留 §7 MEMORY 行与 §9 教训已记 finding；③ 说明段不会被门控误判——现位 rc=0（说明表未计入三表），挪进小节即 18 项 FAIL，既不误杀也不放过。

#### 收尾（architect，2026-11-08 13:02）

- 判决 Accepted：reviewer 独立注入证明「说明段挪进小节 ⇒ 18 项 FAIL」「删标题 ⇒ fail-closed」，说明段位置既不被误杀也不放过错位；`项目里程碑 = M11` 仍恰好 1 处；M9/M10 指针命中 0；表行仅本任务一行由待开始→进行中。
- F1：`Process-04 §7` 的 `MEMORY.md` 行按范围澄清——该条只约束 `MEMORY.md` 的**归档导航行**（「入口指针」表内合法表行），`milestones.md` 明确**不写归档指针**；两处口径不再冲突。
- F2：完成区「`MEMORY.md` 仍写归档指针见页首」已过时——architect 已在 master 修（`76f3bd3a`）。
- 文件头结构：断言行 → 本页说明 → 三表映射表 → 列规则，置于首个 `##` 之前。
