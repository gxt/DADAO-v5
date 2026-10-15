# INFRA-084t: 组件 `changelog.md` 表格 → 列表 + 按里程碑分节

**模块**：infra
**项目里程碑**：M8
**依赖**：无（独立；4 个 `components/*/changelog.md` 均已在库、`docs/Process-01 §10` 在位、无生成器/门控依赖其形态——见「现场事实」）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 背景与立项来源
- **用户裁定（原话，2026-10-15；渠道 = 经主会话问答）**：
  - 「**changelog不要用表格，而是用列表**」（**很重要**）；
  - 「**摘要另起缩进行**」；
  - 「**component下的changelog，是否按里程碑进行划分？**」⇒ 主会话据实答复**建议分节**（可机械归属：任务书 `**项目里程碑**` 字段 / 归档目录名双路径），用户未反对 ⇒ **本任务按分节办**。
- **补充裁定（2026-10-15，经主会话；本任务书已定稿）**：① **保留反引号**、**2 空格缩进**、第 3 列标题用 **「摘要」**（旧列名 `变更` 不再沿用）；② **新增「本体例 L1 形态门控」为新工作项**（范围**只到形态断言**）；③ **不立 ADR**。逐条见「裁定（2026-10-15）」「目标形态」「硬要求 5」。
- **现状**：4 个组件 changelog 均为 Markdown **表格**（表头 `| 日期 | 任务 | 变更 |`；**部分行另有第 4 列「执行者」**，表头**未声明**该列）；`docs/Process-01 §10` 只写「按任务一条、追加式」，未定义体例。
- **性质**：**体例（形态）变更**，**不改内容**（不改判据、不补记录、不删条目）。
- **与 `ISS-090` 不同轴**：`ISS-090`（`open`）= *缺记录*（`QEMU-025t`~`033t` 9 条历史行缺失）；本任务不补记录 ⇒ **不关该 issue**（仅在其 `notes` **只追加**一句体例变更指针，见验收 6）。
- **`.tao/knowledge/changelog.md`**：architect 现场 `ls` 实测**不存在**（该名词属历史，已并入 `milestones.md`/各组件 changelog）⇒ **无需动作**。

## 目标形态（**体例真源**；执行时逐字照此）
> **体例定稿（2026-10-15 主会话裁定）**：① 任务号**保留源行反引号**（如 `` - **2026-10-03 `QEMU-034t`** ``）；② 缩进行 **2 空格**；③ 第 3 列标题用 **「摘要」**；④ **旧列名 `变更` 不再沿用**（`变更` 不得再作列名/标签出现）。
```markdown
# <组件名> 组件变更记录

> 粒度：**按任务一条**，追加式。**体例 = 列表式（不用表格）+ 按里程碑分节**：每条 = `- **<日期> <任务号或 —>**`，**摘要另起缩进行** `  - 摘要：<摘要正文，逐字保留>`；原表其余列各占一条缩进行（如 `  - 执行者：engineer`）。节 = `## M<k>`（节序 M1→M2→…），**节内按日期升序**；**新里程碑到来时在文末开新节**（不留空节）。补丁集的生成/应用/校验规范见 `docs/Process-01-组件补丁组织与构建编排.md §10`。

## M1

- **2026-09-23 —**
  - 摘要：**M1 补丁集重整**：由「16 份编号补丁 + `git am`」改为「树形补丁集 + `git apply`」（…**逐字保留**…）

- **2026-10-03 `QEMU-034t`**
  - 摘要：**FP 执行层基础设施 + RF 数据搬运族（16 条）从 ILLI 桩换为真实 TCG**。新建 `target/dadao/insn_trans/trans_fp.c.inc`（…**逐字保留**…）
  - 执行者：engineer        ← **仅当源行有该列**（无损保留）

## M2
…
```
**体例细节（逐条须一致）**：
1. **条目头** = `` - **<日期> <任务号或 —>** ``：日期 `YYYY-MM-DD`；任务号**保留源行反引号**（如 `` `QEMU-034t` ``；**2026-10-15 主会话裁定：保留**，不剥）；无任务号写 `—`（**不带括号**）。`- **` 顶格（无缩进）。
2. **摘要行** = `  - 摘要：<正文>`（缩进 **2 空格**，**标签字面 = `摘要`**），正文 = 源表**第 3 列正文**（**逐字**，含 `**加粗**`/`` `code` ``/标点/空格），**首尾空白 trim**、不加句号、不换行。**旧列名 `变更` 不再沿用**（源表头 `日期 | 任务 | 变更` 的 `变更` 一律改称 `摘要`）。
3. **其余列** = 各占一条 `  - <列名>：<值>`；本仓现存仅 **`执行者`**（实测 qemu **17** 条；值如 `engineer` / `engineer + reviewer`）。
4. **分节** = `## M<k>`（二级标题，**只写有条目的里程碑**、不留空节；节序 M1→M2→…→M8）。
5. **节内排序** = 键 `(日期升序, 源表行号升序)`（稳定；源表存在 1 处日期倒序——llvm `2026-10-06` 行早于 `2026-10-05` 行 ⇒ 允许重排）。
6. **条目间空一行**（可读性；机械判不依赖）。
7. **文件头**：第 1 行 `# <组件名> 组件变更记录` 不变；第 3 行 blockquote **替换**为上例体例说明（各文件同文，仅组件名无关）；llvm 另有「**维护规则**」段（`components/llvm-project/changelog.md` L5）**保留判据内容**，仅把措辞 **`入表判据`→`入本文件判据`**、**`不入本表`→`不入本文件`**、**`追加一行`→`追加一条`**，其余逐字不变。
8. **旧列名不再沿用**：源表头 `日期 | 任务 | 变更` 的 `变更` 一律改称 **`摘要`**；4 个组件 changelog 内**不得**再出现 `变更` 作列名/标签（正文中作为「变更记录」等普通词语不受限）。

## 现场事实（architect 预核，2026-10-15；**执行时须重派生**）
| 项 | 观测值 |
| --- | --- |
| 范围文件（**= 全部现存** `components/*/changelog.md`） | `llvm-project` / `qemu` / `picolibc` / `embench-iot`（`components/` 下**仅此 4 个**组件，均**有** `changelog.md`） |
| 表数据行数（现场派生） | llvm **96** / qemu **18** / picolibc **6** / embench **2** = **122** |
| 行内字段数（`split('|')` 视角） | 表头声明 **3** 列；llvm **3** 行、qemu **1** 行**正文内含字面 `\|`**（未转义）⇒ 拆出多余空/续片；qemu **17** 行有**未声明**的第 4 列「执行者」 |
| 无任务号行 | **2**（llvm L20 + qemu L7，均 `2026-09-23`「**M1 补丁集重整**」） |
| 任务书里的任务不存在 | **1**（`LLVM-016t`，llvm L21，`2026-09-28`）——该任务 **M2 期关闭删除**（M2 用户裁定；见 `.tao/archive/M2/m2-retrospective.md` L197 / `.tao/archive/M2/README.md` L37） |
| 任务书 `**项目里程碑**` 字段覆盖 | 本地/归档任务书 **434/434** 均有该字段（无缺字段者）；`INFRA-055t` 值带附注（`M7（规划中；…）`）⇒ 取**首个 `M\d+` token** |
| 归属预核结果（**脚本须现场重算，禁写死**） | llvm：M1 12 / M2 22 / M3 20 / M4 10 / M5 1 / M6 16 / M7 11 / M8 4；qemu：M1 1 / M2 5 / M3 1 / M4 1 / M5 3 / M6 3 / M7 2 / M8 2；picolibc：M7 6；embench：M6 2 |
| **改形态前的既有依赖**（2026-10-15 定稿前实测） | `grep -rln 'changelog.md' tools/ Makefile tests/` = **空**（无**既有**脚本读组件 changelog）；`tools/infra/check_components.py`（L1）只作工具可用性冒烟、**不解析 changelog**。**注意**：本任务**新增** `tools/infra/check_component_changelog.py` 后，该 grep 将**且仅应**命中它（见验收 5） |
| **`tools/spec/check_spec_changelog.py` 是否受影响** | **不受影响**（预核）：该器 `lock_entries()` 只遍历 `manifests/spec-readonly.lock.toml` 所列 **`spec/*.md`（21 册）**；其「段内不得含表格行」断言只约束 spec 册附录 ⇒ 与 `components/*/changelog.md` 无关。**执行时须现场复跑复核并留证** |
| 锁/权限 | `spec-readonly.lock.toml` 只锁 `spec/**`；`docs/Process-01-*.md`、`components/*/changelog.md` **均不在锁内** ⇒ 本任务**无需用户授权**（`spec/` 零触碰） |
| 开工 base | `master` = **`60a75bddabe98f65c1b97d6a91cfceeb0a0555d3`**（工作树干净；分支 `infra-084t`） |

## 归属规则（**机械可判，按序**）
1. 行内任务号 ⇒ 本地任务书（`.tao/tasks/**` 或 `.tao/archive/**`，文件名前缀 `<ID><后缀>-`）存在：
   取该任务书 `**项目里程碑**` 字段的**首个 `M\d+`**。
2. 同上但任务书**不存在**（实测仅 `LLVM-016t`）⇒ 兜底：`.tao/archive/M<k>/**` 目录名（不适用）→ **行日期 ∈ 里程碑期**（`README.md`「项目里程碑」达成日：M1 09-22 / M2 10-04 / M3 10-05 / M4 10-07 / M5 10-08 / M6 10-11 / M7 10-13）⇒ `2026-09-28` ⇒ **M2**（与 M2 归档口径一致）。
3. 无任务号（`—`，实测 2 行）⇒ 依**行内事件括注** `M1 补丁集重整` + 日期 ⇒ **M1**。
4. **无法判定 ⇒ 不得静默选择**：单独成节 `## 未归属` 并在完成区「新发现/坑」如实登记（实测 **0** 例）。

## 范围
**做**（仅此）：
- 4 个 `components/*/changelog.md`：表 → 列表 + 按里程碑分节（含文件头第 3 行体例说明；llvm 维护规则段最小措辞适配）。
- `docs/Process-01-组件补丁组织与构建编排.md`：§10（L162）补明**列表体例 + 里程碑分节 + 新里程碑开新节**（判据内容不变、仅把「追加一行」改「追加一条」）；§2 目录树注（L23）改为「（按任务一条，追加式；**列表式 + 按里程碑分节**）」；§13 追加一条 `rev.` 行（体例 + 新门控）。
- **新增** 体例形态门控 `tools/infra/check_component_changelog.py`（**硬要求 5**）；`Makefile` 新增 `check-component-changelog` target（`.PHONY` + help + 并入 `make check`）；`docs/Process-07-门控分层规范.md` §1 登记该 L1 成员。
- 一次性对账脚本 + 证据（落 `.work/`,见下）。
**不做**（✗）：
- **不改 changelog 内容**：不删/不增不改任何条目的**日期、任务号、摘要正文、执行者**（只换形态；摘要**逐字**保留）；
- 不动 `spec/**`、`.tao/contracts/**`、`contracts/**`、代码、补丁集、`components/**` 其它文件；
- **不补** `ISS-090` 缺的 9 条历史记录、**不关**任何 issue；
- 门控**只做形态断言**（硬要求 5 的 ①–⑤），**不做**内容/语义校验；**不新增**上述以外的任何门控/脚本。

## 硬要求
1. **信息无损**：旧表**每一行**的每个字段（日期 / 任务 / 变更正文 / 执行者…）都能在新列表一一对应；**摘要逐字一致**（比对口径：**去首尾空白后逐字相等**）。
2. **机械对账**（可重跑，**锚定任务基线**）：脚本 = `.work/evidence/<任务ID>/`（任务 ID = `INFRA-084t`）下的 `table2list_check.py`，旧侧取 `git show $BASE:<path>`（`BASE` 默认 = **`60a75bddabe98f65c1b97d6a91cfceeb0a0555d3`**、可用环境变量覆盖；**禁以 `HEAD` 为基线**——`lessons §2.14` / `ISS-218`）。断言语义：
   ① 行数相同（旧表数据行 == 新 `^- \*\*` 条目）；
   ② **摘要 multiset 逐字相等**；③ 任务号 multiset 相等（**两侧归一：剥反引号后比对**；`—` 归一）；④ 日期 multiset 相等；⑤「执行者」multiset 相等（不写死计数）；
   ⑥ 新文件**无** `^\|` 行（无表格）；⑦ **归属独立重算**（按上「归属规则」）与条目所在 `## M<k>` 节一致 + 节序升序 + 每节非空 + 节内日期非降序；
   ⑧ 文件头 3 要素在位（`# <组件名> 组件变更记录` + 体例说明含「列表式 / 按里程碑分节 / 摘要」）。
   任一 FAIL ⇒ rc=1；全 PASS ⇒ rc=0；计数**现场派生**。
   > **旧行解析口径（勿用朴素 `split('|')`）**：`raw.strip()` 两端须为 `|` ⇒ 去外层后按**前两个 `|` 切片**得 日期/任务，余段再以 `^(.*)\|\s*(engineer(\s*\+\s*reviewer)?|reviewer(\s*\+\s*engineer)?)\s*$` 判**执行者**，其余**原样**为摘要正文（保留正文内字面 `|`）。
3. **可达 FAIL 证据**：脚本 `--self-test` 在 `/tmp/opencode/INFRA-084t/` 的**临时树**上注入（**不改真实仓库**；**禁** `checkout`/`restore`/`stash`）：① 删 1 条目 ⇒ ① ② FAIL；② 改摘要 1 字符 ⇒ ② FAIL；③ 条目挪错节 ⇒ ⑦ FAIL；④ 插 1 行表格 ⇒ ⑥ FAIL。各注入 rc=1、还原后 rc=0，留真实输出。
4. **归属规则写清**：上「归属规则」四条 + 实测特例（`LLVM-016t` / 2 条 `—`）在完成区如实交代。
5. **本体例 L1 形态门控（新工作项，2026-10-15 裁定）**：新增 checker **`tools/infra/check_component_changelog.py`**，并入 **L1**（`make check`）并在 `docs/Process-07-门控分层规范.md` 登记。**落点判断**：**独立文件**——与既有 `tools/infra/check_components.py`（组件**可用性冒烟**、跑可执行）职责不同轴（本器 = **静态文档形态**门控，「Do One Thing」），**不并入** `check_components.py`。**断言（仅形态级，粒度宁松勿紧、避免误伤）**：
   ① 各 `components/*/changelog.md` **不得**出现**表格分隔行**（形如 `| --- |` / `|---|---|`）；
   ② 每条条目形如 `^- \*\*<日期>`（顶格 `- **` + `YYYY-MM-DD`）；
   ③ 每条条目**紧接着**一条**缩进行**（摘要，形如 `^  - 摘要：`）；
   ④ 存在 `^## M\d+` 节、且**节序递增**（M 号严格递增、至少 1 节）；
   ⑤ **覆盖全部** `components/*/changelog.md`（**现场 glob 派生**；命中文件集为空 ⇒ **vacuous FAIL**）。
   **要求**：每条断言**可达 FAIL**（给「注入 → FAIL → 还原 → 回绿」真实输出）；计数**现场派生**、**不写死**；**不得校验正文内容**（禁 `split('|')` 等脆弱解析）；`make check` 的 L1 组成与 `Makefile`/`Process-07` 同步登记（`Makefile` 加 target + `.PHONY` + help 一行）。

## 验收标准
1. `python3 .work/evidence/<任务ID>/table2list_check.py`（任务 ID = `INFRA-084t`；默认模式）**rc=0**，且 4 文件逐条 PASS + 现场计数；`--self-test` rc=0（各注入 rc=1 留证）。
2. 门控各 **rc=0**：`make check`（L1，**含新 `check-component-changelog`**）/ `make check-patch-tree` / `make check-no-residue` / `make check-knowledge-refs` / `make check-tasks` / `python3 tools/infra/check_issues.py`。
   - **新增形态门控专项**：`python3 tools/infra/check_component_changelog.py` **rc=0**（**4 文件**逐条 PASS + 现场计数）；`--self-test` rc=0，且 ①–⑤ **每条断言各有可达 FAIL 注入**（① 插表格分隔行 / ② 改条目头形态 / ③ 删摘要行 / ④ 乱节序或缺节 / ⑤ 扫描面为空）各 **rc=1**、还原后 rc=0（留真实输出）；`make check` 输出含该 target PASS。
3. **人工可读性抽查**（留 `sed`/`head` 输出）：4 文件均为「`# 标题` → 体例说明 → `## M<k>` 节 → `- **<日期> <任务号>**` → `  - 摘要：…`」形态，无表格、无缩进错位。
4. `docs/Process-01`：§10（L162）与 §2（L23）已补明体例、§13 有 `rev.` 行，**与实态一致**（引文与 4 文件实际形态一致）；**门控登记一致**：`Makefile` 有 `check-component-changelog` 且并入 `check`（L1）、`docs/Process-07 §1` 的 L1 组成含该目标 ⇒「实现 ↔ 登记 ↔ 触发」三者对齐。
5. **未受影响复核**：现场重跑 `grep -rln 'changelog.md' tools/ Makefile tests/`，**期望且仅应**命中本任务新增的 `tools/infra/check_component_changelog.py`（其余为空）+ 读 `tools/spec/check_spec_changelog.py` 的 `lock_entries()` 证其只扫 `spec/*.md`；`make check` 全绿即含 `check-spec-changelog` PASS ⇒ 一并留证。
6. `.tao/knowledge/issues.yaml`：`ISS-090` `notes` **只追加**一句「组件 changelog 体例变更（表格→列表+里程碑分节，`INFRA-084t`，2026-10-15）⇒ 补记时按新体例」，`status` 保持 `open`、`resolved_by` 保持 `null`；`check_issues.py` rc=0。
7. 完成区 ≤30 行、审阅记录每轮 ≤40 行；长输出留 `.work/log/infra/`；临时产物一律 `/tmp/opencode/INFRA-084t/`；**不提交 git**（提交权归 architect）。

## 裁定（2026-10-15；原「待确认项」三条提请已由主会话定稿）
1. **是否把「组件 changelog 体例」纳入 L1 机械门控** ⇒ **纳入**（轻量一条）。**理由**：该体例用户明确「**很重要**」，而一次性对账脚本留 `.work/` 会随 `clean-work` 消失 ⇒ **不防回归**（`lessons §2.11` 同旨）。**范围只到「形态断言」**（硬要求 5 的 ①–⑤），**不做**内容校验；**落点** = 新 `tools/infra/check_component_changelog.py`（**独立文件**：`check_components.py` 是组件可用性冒烟、跑可执行，二者不同轴；「Do One Thing」）⇒ 并入 `make check`（L1）+ `docs/Process-07 §1` 登记；**本任务实现**。
2. **体例细节是否照准** ⇒ **照准并定稿**：**保留反引号**（如 `` - **2026-10-03 `QEMU-034t`** ``）、**缩进 2 空格**、第 3 列标题用 **「摘要」**；**旧列名 `变更` 不再沿用**（见「目标形态·体例细节」1/2/8）。
3. **是否就本「体例变更」立 ADR** ⇒ **不立**（属**文档体例**、与 `docs/Process-01` 同级；可逆、无外部契约 ⇒ 不命中 ADR 判据）。

## 说明
- **门控**：见「硬要求 5」+「裁定 1」——新 `tools/infra/check_component_changelog.py` 为**本任务实现**的**形态级**门控，并入 L1 并在 `docs/Process-07` 登记；**一次性对账脚本**仍按先例（`INFRA-083t`/`LLVM-092t`）留 `.work/evidence/`、**不入库**（两者职责不同）。
- **未来追加者**：`Process-01 §10` 更新后，后续任务追加 changelog 须按新体例并归入**对应里程碑节**（无该节则在文末开新节）。
- 本任务**不触碰** `spec/`（`check-spec-readonly` 无影响），故无 `AGENTS.md`「下发前预检⑤」BLOCKED 项。

## 完成区
**测试结果**：**通过 28/28**（`.work/evidence/INFRA-084t/run.sh` rc=0；计数现场统计）；失败原因：无。
- 对账 `table2list_check.py`：4 文件 × 8 断言 = **32 项 PASS**（rc=0）；`--self-test` rc=0（删条目/改摘要/挪节/插表格行 4 注入各 rc=1，`cp`+md5 还原后 rc=0）。
- 新 L1 门控 `check_component_changelog.py`：4 文件 × 4 断言 + ⑤覆盖 = **17 项 PASS**（rc=0）；`--self-test` rc=0（①表格分隔行 ②条目头 ③摘要行 ④乱节序 ④b缺节 ⑤空树 6 注入各 rc=1，还原后 rc=0）。
- 门控：`make check`(L1) / `check-patch-tree` / `check-no-residue` / `check-knowledge-refs` / `check-tasks` / `check_issues.py` / `check_spec_changelog.py` 各 **rc=0**（`make check` 日志含 `check-component-changelog: PASS`）。
- 证据脚本 `run.sh --inject` rc=0（5 谓词抽样「破坏 ⇒ 判 FAIL」+ 真实文件 md5 前后对账一致）。
**修改文件**（7 改 + 1 新；证据另落 `.work/`，**本任务不提交 git**）：
- `components/{llvm-project,qemu,picolibc,embench-iot}/changelog.md`（96/18/6/2 = **122** 行 → 列表式 + `## M<k>` 分节）
- `tools/infra/check_component_changelog.py`（**新增**）｜`Makefile`（target + `.PHONY` + help 一行 + 并入 `check`）｜`docs/Process-07-门控分层规范.md`（§1 登记）
- `docs/Process-01-组件补丁组织与构建编排.md`（§10 体例 / §2 目录树注 / §13 rev 行）｜`.work/evidence/INFRA-084t/{run.sh,table2list_check.py,table2list_migrate.py}`
**验收结果**（真实输出，全文 `.work/log/infra/INFRA-084t-run.out`）：
- **形态实例**：llvm `` - **2026-09-17 LLVM-002t** `` + `  - 摘要：**LLVM 组件基线**：…`；qemu `` - **2026-10-03 `QEMU-034t`** `` + 摘要 + `  - 执行者：engineer`；picolibc `` - **2026-10-11 `INFRA-055t`** ``；embench `` - **2026-10-09 `INFRA-051t`** ``（后二者无第 4 列）。
- **对账**（锚定 `60a75bd`，现场计数）：行数 96/18/6/2 == 新条目 96/18/6/2；**摘要 multiset 逐字相等 122/122**；任务号/日期/执行者 multiset 相等（执行者 17 条：`engineer` / `engineer + reviewer`）；`^\|` 行 **0**；`变更` 作标签 **0**。
- **里程碑归属**：llvm M1 12 / M2 22 / M3 20 / M4 10 / M5 1 / M6 16 / M7 11 / M8 4；qemu 1/5/1/1/3/3/2/2；picolibc M7 6；embench M6 2（与任务书预核**逐项一致**）；**不可判 0**（无 `## 未归属` 节）。
- **验收 5**：`grep -rln --exclude-dir=__pycache__ 'changelog.md' tools/ Makefile tests/` **只**命中 `tools/infra/check_component_changelog.py`。
**新发现/坑**：
- 含**字面 `|`** 的行实测 **llvm 4 行**（预核写 3；L74/79/103/104）+ qemu 1 行（`cfxha<<42\|0x3ff…`）⇒ 计数按现场修正；「禁朴素 `split('|')`」结论不变。
- 归属特例：`LLVM-016t` 任务书不存在 ⇒ 达成日区间兜底（首个「达成日 > 日期」= **M2**）；2 条 `—` 行 ⇒ 行内括注 **M1**；`` `INFRA-068t`（返工 1） `` token 含附注 ⇒ 抽 ID 按任务书归 **M7**。
- `Process-01 §10` 只按任务书把「追加一行」→「追加一条」，**未**动 `入表判据` 标签；llvm changelog 内同判据按任务书改称「入本文件判据」⇒ 两处用词轻微不一致（见遗留，未越界擅改）。
- §2 目录树注在代码围栏内 ⇒ 未加 `**`（避免字面 `**`），取「（按任务一条，追加式；列表式 + 按里程碑分节）」。
- 验收 6 前置（`ISS-090.notes` 体例变更指针）**已由 architect 立任务时写入**（`ce72fda`）⇒ 现场核对后**未重复追加**；`status=open` / `resolved_by=null` 不变。
- 门控 ④ 只认 `## M\d+`（按任务书字面）；将来若出现 `## 未归属` 且**无任何** M 节则 ④ FAIL（现实总存在 M 节，登记为观察点）。
**遗留问题**：
- 无未完成项：4 changelog + `Process-01`/`Process-07` + `Makefile` + 新 checker + 证据脚本全部落地且门控 rc=0。
- 非阻塞待裁定（**未越界改**）：`Process-01 §10` 的 `入表判据` 标签是否统一为「入本文件判据」——任务书未列入本任务范围，留待 architect/用户裁定。

## 审阅记录

#### 第 0 轮 architect 任务书补定（2026-10-15；分支 `infra-084t-spec`）
- **性质**：规划层定稿（非实现），**只改本任务书**（`.tao/tasks/infra/INFRA-084t-changelog列表化与里程碑分节.md`），未动任何代码/文档/门控实现。
- **定稿内容**：① 体例定稿——任务号**保留反引号**、缩进 **2 空格**、第 3 列标签 **「摘要」**、**旧列名 `变更` 不再沿用**（新增体例细节 8；修 1/2 条与示例）；② 新增 **硬要求 5**「本体例 L1 形态门控」（新工作项，范围**只到形态断言**：①–⑤ + 可达 FAIL + 计数现场派生 + 禁内容校验；落点独立文件 `tools/infra/check_component_changelog.py`、并入 L1、`Process-07` 登记）；③ 范围/验收同步（做/不做、验收 2 专项、验收 4 三处对齐）；④ 原「待确认项」三条 → 「裁定（2026-10-15）」。
- **门控（architect 侧）**：`make check`(L1) / `check-knowledge-refs` / `check-no-residue` / `check-tasks` / `check_issues.py` 各 rc=0（详见回报）。
- **文件集对账**：`git diff --cached --name-status` **仅**本任务书（1 文件）。
- **未立 ADR**（裁定 3）；**未 push**。

#### 第 1 轮 engineer 自审
（自主逐行审查范围：`tools/infra/check_component_changelog.py`、`.work/evidence/INFRA-084t/{run.sh,table2list_check.py,table2list_migrate.py}`、4 个 changelog 抽样、`Makefile`/`Process-01`/`Process-07` 改动；证据 = 每次修复后重跑 `run.sh` + 两个 `--self-test`。）

| # | finding（自审意见） | 处置 | 改了什么 | 复验证据 |
|---|---------------------|------|---------|---------|
| 1 | `table2list_check.py` 重构残留死代码 `_nth_section` | ✅已修 | 删除该函数 | `py_compile` OK；默认模式 rc=0 |
| 2 | `milestone_achieved_dates()` 用 walrus-in-generator，可读性差/易错 | ✅已修 | 改显式 for 循环 | rc=0；`--self-test` rc=0 |
| 3 | L1 门控 `check_tree()` 对同一文件重复读 3 次 | ✅已修 | 读一次后复用 | rc=0；17 项 PASS |
| 4 | 任务号 token 含附注（`` `INFRA-068t`（返工 1） ``）⇒ 误走区间兜底（规则 1 未生效） | ✅已修 | 新增 `task_id_of()` 抽 ID（③ 仍按整 token 归一比对） | migrate 输出「特例归属 · … ⇒ M7（token 含附注，按 ID 归属）」；4 文件 md5 **幂等不变**；⑦ PASS |
| 5 | Makefile 注释含字面 `changelog.md` ⇒ 使验收 5 扫描多命中 Makefile | ✅已修 | 注释改「`components/*/` 下的组件变更记录」 | `grep -rln … tools/ Makefile tests/` 仅命中新 checker |
| 6 | `run.sh` 断言「L1 含新门控 PASS」把 standalone 与 `make check` 计成 2 | ✅已修 | per-check 日志 + 专用 grep `make check` 日志 | 实际=1 → PASS |
| 7 | `run.sh` 断言「§10 体例」因 §13 同短语计成 2 | ✅已修 | 改 `awk '/^## 10\./,/^## 11\./'` 限定区间 | 实际=1 → PASS |
| 8 | `run.sh` 标签内反引号触发命令替换报错（`变更: command not found`） | ✅已修 | 标签去反引号 | 断言 25 实际=0 → PASS |
| 9 | `run.sh` ISS-090 断言误用 `d['issue']`（yaml 顶层为 list） | ✅已修 | `[i for i in issues if …]` | 实际=`open/None`、notes 指针=1 → PASS |
| 10 | 对账 `--self-test` 的「挪节」注入坐标错位 ⇒ 连带 ② FAIL（隔离度不足） | ✅已修 | 用删除后的坐标重算 `last_sec` | ③ 注入**只**命中 ⑦；还原后 rc=0 |
| 11 | 防造假核查：rc/输出是否全为真实执行 | ✅通过 | — | 28 项检查日志留 `.work/log/infra/`；**未用** `git checkout/restore/stash`（还原一律 `cp`+md5） |
| 12 | 越界核查：是否只动任务书列出的文件 | ✅通过 | — | `git status --porcelain -uall` = 7 改 + 1 新（均在本任务范围） |

**判决**：12 条 finding **全部已修/已核**，无 ⏸/❌ ⇒ 任务状态置 **`待验收`**，返回主会话交 reviewer 独立验收。

#### 第 1 轮 architect 提交与文件集审核（2026-10-15；分支 `INFRA-084t`）
- **档位**：**正常提交（不带 `WIP:`）**，**提交号 `970217e`**，落在本任务分支内（**未 merge、未 push**）。**档位差异披露**：本任务书 `**状态**` 仍为 `待验收`、reviewer 第 1 轮尚未落记录，按 architect 默认规则应为 `WIP:` 前缀；本次按**主会话 2026-10-15 明确指示**（不带 `WIP:`）执行 —— 差异如实留痕。
- **开工前 `git status --porcelain -uall`** = **9 项**（4 `components/*/changelog.md` + `Makefile` + `docs/Process-01…md` + `docs/Process-07…md` + 新 `tools/infra/check_component_changelog.py` + 本任务书）；**范围外 0**（`spec/` / `contracts/` / `components/*/patches/**` 均无）。
- **显式 staging**（**禁** `git add -A`，逐路径 `git add -- <path>`）⇒ `git diff --cached --name-status` = **8 `M` + 1 `A`**，与完成区「修改文件」逐条对账：**多提 0 / 漏提 0 / 越界 0**。
- **术语统一（architect 顺手，属本次体例变更收尾；越任务书范围的 1 处小改，如实披露）**：`docs/Process-01 §10` 的 `入表判据`→`入本文件判据`、`不入本表`→`不入本文件`（**只改措辞、判据语义零改**）；同文件 §13 rev 行补记该措辞统一。llvm changelog 本已同名 ⇒ 两处用词一致；**遗留问题第 2 项（待裁定）由此闭合**。范围外同类扫描：`docs/` 内仅 `Process-04 §5` 的「表内/表头之上」指 **`milestones.md`/`MEMORY.md` 表格**（非本 changelog）⇒ **不动**，登记为观察项。
- **只读核对（真实 rc；日志 `.work/log/infra/INFRA-084t-architect2-*.log`）**：`make check`=**0**、`make check-component-changelog`=**0**（16 项 ①–④ + ⑤ 覆盖，计数现场派生）、`check-patch-tree`=**0**、`check-knowledge-refs`=**0**、`check-no-residue`=**0**、`check-tasks`=**0**、`check_issues.py`=**0**；`make check` 日志含 `check-component-changelog: PASS` + `repository checks (L1): PASS`。
- **对账脚本基线核验**：`.work/evidence/INFRA-084t/table2list_check.py` 的 `DEFAULT_BASE = 60a75bddabe98f65c1b97d6a91cfceeb0a0555d3`（**非 `HEAD`**；脚本内 `HEAD` 仅出现于「禁以 `HEAD` 为基线」注释与 `ROW_HEADER` 字面）⇒ 现场复跑 rc=**0**、首行打印基线 `60a75bd…` ✓。

#### 第 1 轮 reviewer 验收
（长输出留 `.work/log/infra/INFRA-084t-review1-*.out`；工作区验收前后 md5 快照逐字节一致、`git status` 干净；未提交 git。）
**重跑记录**（全部 reviewer 亲跑，真实 rc）：
- 对账 `python3 .work/evidence/INFRA-084t/table2list_check.py` **rc=0**；首行基线 `60a75bddabe98f65c1b97d6a91cfceeb0a0555d3`（**非 HEAD** ✓）；4 文件 × 8 断言 = 32 项 PASS；摘要 multiset 逐字相等 **2+96+6+18=122/122**；任务号/日期/执行者 multiset 相等（qemu 执行者 17）。
- **独立抽验 9 条**（自写 `indep_cmp.py`，锚定前后缀剥离、非工程师解析器；`git show 60a75bd:` 原文行 ⇒ 现列表条目）**9/9 逐字 MATCH**：llvm `LLVM-016t`/`LLVM-062t`/`LLVM-069t`（后两条 = 含字面 `|` 行 L74/L79）、qemu `—` 行/`QEMU-034t`/`QEMU-044t`（执行者+字面 `|`）、picolibc `INFRA-068t` 及 `INFRA-068t`（返工 1）、embench `TESTCASES-039t`。
- **形态（4 文件，自跑 grep/awk）**：条目头 122 条全 `- **YYYY-MM-DD …**` 顶格、以 `**` 收尾、越形 0；摘要行数==条目数且**全 2 空格** + 标签 `摘要：`；qemu `执行者：` 17 行；`变更` 作列名/标签 **0**（仅正文普通词）；`^\|` 行 **0**；节序 M1…M8 递增、节内日期非降序、无节外条目；反引号保留源行（qemu/picolibc 带、llvm 源行本无）✓。
- **里程碑归属抽查 7 条跨 4 组件**（独立查任务书 `**项目里程碑**`/归档目录）**7/7 与所在节一致**：LLVM-002t M1、LLVM-062t M6、QEMU-034t M2、QEMU-044t M5、INFRA-068t（返工 1）M7、TESTCASES-039t M6、LLVM-016t（任务书缺失 ⇒ README 达成日 09-22/10-04 区间兜底 ⇒ M2）；分节计数独立统计与预核逐项一致（llvm 12/22/20/10/1/16/11/4、qemu 1/5/1/1/3/3/2/2、picolibc M7 6、embench M6 2）。
- **新 checker 5 断言·我的注入**（临时树 + cp/md5，未用 engineer 用例）：① 插 `|---|---|` ⇒ rc=1 命中①；② 条目头去 `**` ⇒ rc=1 命中②；③ 删摘要行 ⇒ rc=1 命中③；④ 乱节序 M8→M0 ⇒ rc=1 命中④（另有误删 `## M6` ⇒ ④ 缺节 FAIL 旁证）；⑤ `--root` 空目录 ⇒ rc=1 vacuous FAIL；逐例 `cp` 还原 md5 相等 ⇒ rc=0 回绿。
- **L1 路径**：`make check` **rc=0**，日志含 `check-component-changelog: PASS` + `repository checks (L1): PASS`；`Makefile` target+`.PHONY`+help+`check` 依赖、`Process-07 §1` 登记三者对齐。
- **门控逐项**：`make check`=**0**、`make check-component-changelog`=**0**（16+⑤=17 项）、`check-patch-tree`=**0**、`check-knowledge-refs`=**0**、`check-no-residue`=**0**、`check-tasks`=**0**、`check_issues.py`=**0**。
- **证据脚本**：`run.sh` **rc=0**（28 项 0 失败，复跑）；`--inject` **rc=0**（5 谓词「破坏⇒判≠期望」+ 真实文件 md5 前后一致）；**独立反例注入**（改被测产物、重跑同一脚本）：真仓 picolibc 追加表格分隔行 ⇒ `run.sh` **rc=1**（FAIL 8 项）⇒ `cp` 还原 md5=`ed6bb85…` 相等 ⇒ 复跑 **rc=0** 回绿。
- **未受影响复核**：`grep -rln 'changelog.md' tools/ Makefile tests/` 仅命中新 checker ✓；`check_spec_changelog.lock_entries()` 只遍历 `spec-readonly.lock.toml`（21 条全 `spec/`）✓。ISS-090 `status=open`/`resolved_by=None`、notes 含体例变更指针 1 处 ✓。
**约束核验**：信息无损 ✓（122/122 + 9 条独立抽验）｜只换形态不改内容 ✓｜`spec/**`/`contracts/**` 零触碰 ✓｜门控仅形态断言、计数现场派生 ✓｜临时产物在 `/tmp/opencode/INFRA-084t/` ✓｜不提交 git ✓｜完成区 ≤30 行/审阅记录限长 ✓。
**遗留判定**：① `Process-01 §10` 术语已统一（`入表判据/不入本表` 残留 0、`入本文件判据/不入本文件` 在位）——architect 越范围 1 处已披露、遗留第 2 项闭合 ✓；② `Process-04` 的「表内」实指 `milestones.md`/`MEMORY.md` 表（L125 明文）、§9 为 M1 归档**历史教训** ⇒ **「不必改」判定成立** ✓；③ 字面 `|` 行 llvm **4**（L74/79/103/104）vs 预核 3 已在「新发现/坑」如实记录，reviewer 独立计数一致 ✓。
**观察项（非阻断）**：① 分支纪律——「漏开工建分支、完成后补建」**未在任务书落盘**（盘上 grep 无痕，此处置痕）；对交付物**零影响**：验收前后 md5 逐字节一致、`master` 仍旧表形态/无新 checker/无该 target，`master..INFRA-084t`=仅 `970217e`+`11f5c32`、反向为空（实现改动只在任务分支）；② checker ③ 用 `^ +`（≥1 空格）较体例 2 空格略松（合「宁松勿紧」，供知悉）；③ 完成区遗留第 2 项已被 architect 后续提交闭合，收尾时按「只改状态」不再回改。
**判决：Accepted** —— 验收命令块全部在 reviewer 亲自重跑下通过（含独立抽验与独立反例注入→FAIL→还原→回绿），硬约束无违反；观察项 3 条不阻断。
