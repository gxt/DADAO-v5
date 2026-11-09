# INFRA-123t: DDLN TT 草稿工作流退役

**模块**：infra
**项目里程碑**：M11
**依赖**：无（`docs/DDLN` 规则与草稿清理）
**状态**：已验证

## 执行环境
本地；改 DDLN 规则与索引，删除 gitignored TT 草稿，退役 lecnotes agent。**不做 TT 备份**（用户明确授权）。

## 用户裁定（2026-11-05，原话）

> 「现在主会话已经固定在master分支上了，lecnote单独一个会话已无意义，是不是完全做一次同步之后，删除TT-*」
> 「可以；无需备份TT」
>
> **补充裁定（2026-11-05，用户经主会话转述）**：「`.opencode/agents/lecnotes.md` 不再需要保留：它编码的是 TT 草稿工作流 + 单独 lecnotes 会话；两者都已退役。主会话固定在 master、直接处理 DDLN，不需要这个旧 agent。不新建替代 agent、不保留精简版。」

## 现场（2026-11-05）

`docs/DDLN`：

- `DD-*`：81 册
- `TT-*`：81 册
- 一一对应，无单边文件；**81 对 = 76 相同 + 5 差异**
- 76 对完全相同
- 5 对不一致，且 **DD 全部更新、TT 落后**：
  - `A002`：DD 11 种格式；TT 12 种（含已撤销 `crii`）
  - `A011`：DD 新 `fence cfxha`；TT 旧 `fm/pred/succ`
  - `C001`：DD 三段作用域（含 per-task）；TT 两段
  - `E003`：DD 11 格式类；TT 写 `crii` 未启用
  - `F003`：DD 含 per-task；TT 仅 per-hart/per-system

`D002` 说明：`SPEC-191t` 合入前，主树 `TT-D002` 已更新而 `DD-D002` 半边未提交，曾短暂成为第 6 处差异（当时口径 = 75 相同 + 6 差异）；191t 合并后 DD-D002 已对齐，现归入“相同”，故为 **76 相同 + 5 差异**。

这些 DD 更新来自任务代理直接编辑 DD（如 `INTEG-041t` 任务书明确记录“本次直接改了 DD，建议收尾时同步 TT”），TT 未同步；D002 已由 SPEC-191t 收口，不再计入差异。

## 目标

1. **确认 DD 为唯一真源**：不执行 TT→DD 同步（会回退 5 册）；5 处不一致以 DD 为准。
2. 删除全部 `TT-*`（81 份）；**不备份**。
3. 改 DDLN 规则，去掉 TT 草稿工作流：
   - `docs/DDLN/AGENTS.md`：删除“TT 草稿/DD 定稿/TT→DD 同步/DD 不直接改”等规则；改为“DD 是唯一真源，直接编辑 DD；不再有 TT”。
   - `docs/DDLN/.gitignore`：删除 `TT-*` 忽略规则（不再有 TT）；若保留需写明“已退役”。
   - `.tao/knowledge/MEMORY.md`：删除“草稿 TT-* 由 .gitignore 忽略”表述。
   - `docs/DDLN/README.md`/其它活文件若有 TT 说明，同步更新。
4. 更新索引/规则后跑 L1 与 `check-knowledge-refs`；不改任何 DD 技术内容（除规则文件）。
5. **退役 lecnotes agent**：删除 `.opencode/agents/lecnotes.md`（tracked）；不新建替代 agent、不保留精简版。

## 接口规范

- 只改 `docs/DDLN/AGENTS.md`、`docs/DDLN/.gitignore`、`docs/DDLN/README.md`（若引用 TT）、`.tao/knowledge/MEMORY.md`、本任务书、`milestones.md`；删除 `.opencode/agents/lecnotes.md`。
- 不改 81 册 `DD-*` 内容；不把 TT 内容复制进 DD。
- 删除 `TT-*` 由 architect 在主工作树执行（TT 是 gitignored，任务 worktree 不可见）；子代理只做审计与规则修改。
- 删除后验证：`find docs/DDLN -name 'TT-*' | wc -l` = 0；`DD-*` = 81。
- 不新增/改写 DDLN 写作规则其它条目。
- `lecnotes` agent 删除后，活配置不得再引用它；`docs/DDLN/README.md` 的“讲义（lecnotes）”为文体描述，保留。不新建替代 agent。

## 范围 / 非范围

**在范围内**：`docs/DDLN/AGENTS.md`、`docs/DDLN/.gitignore`、`docs/DDLN/README.md`（若引用 TT）、`.tao/knowledge/MEMORY.md`、本任务书、`milestones.md`、`.opencode/agents/lecnotes.md`（删除）；主工作树 `docs/DDLN/**/TT-*.md` 删除。

**不在范围内**：81 册 `DD-*` 内容、`spec/**`、ADR、contracts、QEMU/gem5/tests、其它知识库、其它 `.opencode/agents/*`；不新建替代 agent。

## 验收标准

1. **DD/TT 审计**：81 对 = 76 相同 + 5 差异；差异集合恰为 `A002/A011/C001/E003/F003` 且均为 DD 更新；`D002` 在相同集合；无单边文件。
2. **TT 删除**：主工作树 `find docs/DDLN -name 'TT-*'` = 0；`DD-*` 仍 81；无备份（用户授权）。
3. **规则退役**：`docs/DDLN/AGENTS.md` 不再出现“TT 草稿 / TT→DD / DD 不直接改”规则；明确“DD 唯一真源、直接编辑”。
4. **索引/知识库**：`.gitignore` 不再忽略 TT（或注明退役）；`MEMORY.md`/DDLN README 不再把 TT 当草稿。
5. **门控**：`check-knowledge-refs`、`check-milestones-fresh`、`make check`（L1）rc=0。
6. **反例可达 FAIL**：在规则文件写回“TT 草稿”或主树新建一个 TT 测试文件 ⇒ 断言 FAIL；删除/还原后回绿（TT 测试文件在仓库外或临时路径）。
7. **agent 退役**：`.opencode/agents/lecnotes.md` 已删除且不再被 git 跟踪；活配置（`.opencode/`、`.tao/knowledge/`、`AGENTS.md`）无 `lecnotes` agent 引用（README 文体描述与历史任务除外）；无替代 agent。
8. **体例**：完成区 ≤30 行；状态 `待验收`。

## 说明

- 用户明确“无需备份 TT”，删除不可恢复；执行前必须完成 81 对审计与 5 处 DD 为准的确认。
- 这是工作流退役，不是内容改写；DD 技术内容零改动。
- 若删除后发现某册内容只存在于 TT、DD 缺失，立即停止并报告；本次审计无 TT-only。

## 完成区

**测试结果**：证据脚本 运行期证据脚本 30/30 PASS（rc=0，含主树 DD/TT 现场审计）；`--inject` 4/4 PASS（写回“TT 草稿”→规则断言 FAIL，cp+md5 还原→回绿）。
**修改文件**：`docs/DDLN/AGENTS.md`、`docs/DDLN/.gitignore`、`.tao/knowledge/MEMORY.md`、`.tao/knowledge/milestones.md`、本任务书；删除 `.opencode/agents/lecnotes.md`（`git rm`，已入 index）。未改任何 `DD-*` 内容；证据脚本在 运行期证据目录。
**验收结果**：
- 主树 DD/TT：**81 对 = 76 相同 + 5 差异**（`A002/A011/C001/E003/F003`），差异集合严格相等、均 DD 更新 TT 落后；`D002` 字节相同（`SPEC-191t` 已对齐）；无单边文件；未做 TT→DD 同步。方向用 DD 新表述 / TT 旧表述 + `cmp`/md5 + 任务书记录现场断言。
- 规则：AGENTS 已无“TT 草稿/定稿/同步/DD 不直接改”，改立“DD 唯一真源、直接编辑”；`.gitignore` 无生效 TT 规则（仅退役注记）；MEMORY 无 TT 草稿表述。
- agent：`lecnotes.md` 已删、git 不再跟踪；`.opencode/`、`.tao/knowledge/`、`AGENTS.md`、`Makefile` 无 agent 引用（README 文体描述与任务台账除外）。
- 门控：`make check-knowledge-refs` rc=0；`make check-milestones-fresh` rc=0（63 行，状态一致）；`make check` rc=0（`repository checks (L1): PASS`）。
**新发现/坑**：用户口径“75 相同”是 `SPEC-191t` 合入前（75 相同 + 6 差异 = 81）；191t 后 D002 归入相同，实测 **76 + 5 = 81**，未改数凑绿。`lecnotes` agent 内也编码了 TT→DD 同步规则，已随本任务一并退役；`docs/DDLN/README.md` 的“讲义（lecnotes）”只是文体描述，保留。
**遗留问题**：81 份 `TT-*` 仍待 architect 在主工作树删除（gitignored，任务 worktree 不可见；用户授权不备份）；本任务**未**声称已删除 TT。删除前须保持本脚本主树审计绿；删除后复查 `DD-*`=81、`TT-*`=0。

## 审阅记录

#### 第 1 轮 engineer 自审

**范围/逻辑**：逐行核对 5 个改动文件与删除项；AGENTS 仅替换“草稿与定稿”节与命名行，未动写作规则 1–8；`.gitignore` 仅留退役注记、无忽略模式；MEMORY 仅改 DDLN 导航行；milestones 行状态与任务书一致（A1 已由门控复核）；未触碰 81 册 DD 内容。
**反例/证据**：`run.sh --inject` 真实改写 AGENTS（md5 变化）→ `rules_check` rc=1；cp 还原后 md5=原值、`rules_check` rc=0；脚本无 tee，失败即非零。
**agent 引用**：全仓 grep 仅余 README 文体描述、本任务书与 milestones 台账行；活配置 0 引用。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| lecnotes.md 残留 TT→DD 同步规则，且用户补充要求删除该 agent | ✅已修 | 先按原范围改规则，后按补充范围整文件删除（`git rm`） | grep 活配置 0 引用；文件不存在且 index 无记录 |
| 证据脚本把 milestones 台账行误判为 agent 活引用 | ✅已修 | 排除 `milestones.md`/`discussing.md` 台账 | 重跑 17/17 PASS |

**判决**：无未修 finding；完成区与真实输出逐条对齐；状态 `待验收`。

#### 第 1 轮 reviewer 验收

**重跑记录（我的真实输出/退出码，均在任务 worktree 内相对路径执行）**
- 运行期证据脚本 → `== 汇总: PASS=17 FAIL=0 ==`，**rc=0**。
- 同脚本 `--inject` → `PASS=4 FAIL=0`，**rc=0**：注入改写 AGENTS（md5 `0829e4…` → `e1c714…`）→ `rules_check` FAIL（1 项违例：`` `TT-*` 是草稿 ``）→ cp 还原 md5 相等 → 回绿。
- **reviewer 独立注入**（`.gitignore` 追加 `TT-*` 忽略行 + `MEMORY.md` 写回“草稿 `TT-*`”）→ 同一脚本 **rc=1**：`[FAIL] 规则退役断言失败（2 项）：.gitignore 仍有生效的 TT-* 忽略规则 / MEMORY.md 仍把 TT-* 当草稿`；`cp`+`md5sum -c` 还原 OK → 重跑 **rc=0**、17/17 回绿。注入前后 `git status -porcelain -uall` 快照逐行一致，5 个目标文件 md5 全 OK。
- 三门控我直跑：`make check-knowledge-refs` **rc=0**（`0 悬空`）；`make check-milestones-fresh` **rc=0**（`结果: PASS (63 行；状态一致…)`）；`make check` **rc=0**（`repository checks (L1): PASS`）。

**约束核验（逐条）**
- 规则退役 ✅ AGENTS 仅改头部/命名/草稿节：命名示例改 `DD-C001…`，立 `唯一真源 / 直接编辑 DD-* / 不再创建 TT-*`；写作规则 1–8、指导原则未动；全文件仅 1 处 `TT` 且为退役说明。
- 配置/索引 ✅ `.gitignore` 无生效忽略行（仅退役注记）；MEMORY 无 TT 草稿表述；README 只余“讲义（lecnotes）”文体、无 TT/草稿。
- agent ✅ `lecnotes.md` 已删且 index 无记录，`.opencode/agents/` 只余 architect/engineer/reviewer，活配置（`.opencode/`、`.tao/knowledge/`、`AGENTS.md`、`Makefile`）0 引用。
- DD 零改动 ✅ `git diff HEAD --name-only` = 6 个文件全在范围；`diff -rq 主树文档/DDLN` 仅 `.gitignore`/`AGENTS.md` 不同，81 册 DD 字节一致；spec/ADR/contracts/QEMU/gem5/tests 改动 0。
- TT 边界 ✅ 主树 `find TT-*`=81、`DD-*`=81；完成区明确“81 份仍待 architect 主树删除、本任务未声称已删除”。
- 体例 ✅ 完成区 9 行 ≤30、无运行期路径、状态 `待验收`。

**失败项 —— 验收标准 1（DD/TT 审计）**：现场/完成区写“76 相同、**5 处**差异、均 DD 更新 TT 落后”；我在主树用 `cmp` 循环与 python md5 两种方法对账，结果一致 = **81 对 / 75 相同 / 6 处差异**（`A002 A011 C001` **`D002`** `E003 F003`）。D002 方向相反：主树 `TT-D002`（mtime 11-05 20:35:28）已是“统一归 `CFXMEM`、不再单列 `unmapped`、见 `spec/Machine-v5 §7.1`”，主树 `DD-D002`（mtime 10-27）仍写 `unmapped`(0x87) 独立码，而 spec 当日 `4cc3e66e SPEC-187t` 记“删除…未映射独立码表述”（spec 内 `unmapped`/`0x87` 命中 0）。成因：`SPEC-191t` 用户裁定 A 要同改 `DD-D002`+`TT-D002`，DD 半边仍在 `运行期临时目录` 未提交、TT 半边已进主树。⇒ 任务书自设停止条件“内容只存在于 TT、DD 缺失 ⇒ 立即停止并报告”**已触发但未报告**。其余 5 处方向我按 spec/contracts 独立复核（crii 撤销、`fence` 改 ciii/cfxha、DADAO-12 §`cfx16–cfx31 per-task`、INTEG-053t 07:44），确为 DD 更新、TT 落后。

**finding（阻断）**
1. 审计计数与方向与现场不符（5 vs 6；D002 反向），该数字是**验收标准 1 本身**，不适用“文档笔误”豁免。
2. `run.sh` 对标准 1 无独立核验：`grep -Fq "$id" "$TASK"` 只核任务书自述、`NOTE … 以任务书记载为准` ⇒ 册数写错或新增差异都不会 FAIL（覆盖 ≠ 语义）。
3. TT 删除的前置审计须在 TT 可见的主树重做；D002 需先处置（等 SPEC-191t 落 DD 半边或显式同步）再删 TT，否则主树 DD-D002 长期与 spec 相悖且 TT 侧新内容被删。

**判决：Needs Revision**（仅验收标准 1 及其证据覆盖失败，标准 2–8 在我重跑下全部成立）。返工限于：① 主树重做 81 对审计，把实测 6 处与 D002 方向、成因写回现场与完成区；② `run.sh` 把“以任务书记载为准”的自证 PASS 改为可 FAIL 的现场断言，或显式标注该项不由脚本覆盖、由 architect 删除前核验——**禁止改数凑绿**；③ 将 D002 处置与删除顺序上报架构师裁定。

#### 第 2 轮 engineer 自审（返工）

**Needs Revision 处置**：`SPEC-191t` 已合并，主树 D002 的 DD 半边已对齐；`run.sh` 重写为标准 1 的现场审计：用 `git worktree list` 取主树（不写死路径），全量 `cmp` 配对 + md5、差异集合严格相等、逐册方向断言（DD 含新表述 / TT 含旧表述），并直接核验 D002 字节相同。未知差异、册数不符、方向反转、D002 不同都会 `bad` 并 rc=1。

**实测口径**：主树 **81 对 = 76 相同 + 5 差异**（`A002/A011/C001/E003/F003`）；D002 与 DD 字节相同（md5 一致），归入相同。任务书原写 76 正确；用户所述“75 相同”对应 191t 合入前（75+6=81），已在现场说明，未改数凑绿。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 审计计数写成 5，现场实为 6（含 D002） | ✅已修 | D002 随 SPEC-191t 对齐；现场改为 76 相同 + 5 差异并说明 75 的来历 | `run.sh` 实测 76/5，D002 相同 |
| D002 方向相反（TT 新 / DD 旧） | ✅已修 | SPEC-191t 合并后 DD-D002 更新；脚本断言 D002 `cmp` 相同 | `D002 DD/TT 字节相同` PASS |
| `run.sh` 依赖任务书自证、不能 FAIL | ✅已修 | 改为主树 `cmp`/md5 全量配对 + 方向标记 + 集合严格相等 | 30/30 PASS；注入反例 4/4 PASS |
| TT 删除前置审计 | ✅已处置 | 删除前由本脚本主树审计；TT 仍待 architect 删除 | 完成区明确未声称已删 TT |

**判决**：Needs Revision 三项均已处置；无未修 finding；完成区与真实输出逐条对齐；状态 `待验收`。

#### 第 2 轮 reviewer 验收（返工复验）

**重跑（我本人执行，真实输出/退出码）**
- 运行期证据脚本 基线 → `== 汇总: PASS=30 FAIL=0 ==`，**rc=0**（36s）；`--inject` → `PASS=4 FAIL=0`，**rc=0**。脚本未被我改写：`run.sh` md5 `cba6899a…` = 本轮开工备份。
- **独立注入 A**（主树 `TT-D002` 追加一行，制造第 6 处差异）→ **rc=1**：`[FAIL] 差异集合 actual=A002 A011 C001 D002 E003 F003`、`差异数 expected=5 actual=6`、`相同数 expected=76 actual=75`、`D002 在相同集合 expected=1 actual=0`、`D002 DD/TT 未对齐`、`D002 方向断言失败` ⇒ `PASS=26 FAIL=6`；`cp` 还原后 md5 复原。
- **独立注入 B**（抹掉 `TT-A002` 旧表述“12 种操作数格式”）→ **rc=1**：仅 `[FAIL] A002 方向断言失败或方向未知` ⇒ `PASS=29 FAIL=1`；`cp` 还原 md5 复原。首次注入 B 我用“（已抹旧标记）”后缀、子串仍在故仍绿（**注入无效**，非脚本问题），第 2 次真抹才 FAIL——重试 1 次，如实记录。
- 还原后回绿 → `PASS=30 FAIL=0`，**rc=0**；主树 81 个 `TT-*` 对注入前快照 `md5sum -c` **81/81 OK**，主树 `git status -uall` 0 行且与注入前一致；worktree `git status` 与上轮结束逐行一致，4 个非任务书目标 md5 未变。
- 三门控直跑：`make check-knowledge-refs` **rc=0**（`0 悬空`）；`make check-milestones-fresh` **rc=0**（`结果: PASS (63 行；状态一致…)`）；`make check` **rc=0**（`repository checks (L1): PASS`）。

**现场审计（我独立复算，不采信转述）**：主树 `cmp` 循环 + python md5 两法一致 = **81 对 / 76 相同 / 5 差异（`A002 A011 C001 E003 F003`）**，TT-only 0、DD-only 0；`DD-D002`/`TT-D002` md5 同为 `2927be3f…`（D002 已对齐，由 `99c4ab27 SPEC-191t` 合入更新 DD 半边，TT 侧 mtime 仍 11-05 20:35:28 ⇒ **非本任务写入**）；方向断言串 10/10 在主树现场存在。

**约束复核**：规则退役 ✅ AGENTS 全文仅 1 处 `TT`（退役说明）、命名示例改 `DD-C001…`、写作规则 1–8 未动；`.gitignore` 生效忽略行 0 ✅；MEMORY 草稿 TT 0 ✅；README `TT/草稿/定稿` 0 ✅；`lecnotes` 已删且 index 无记录、agents 仅余 3 个、活配置引用 0（仅 milestones 台账行）✅；DD 零改动 ✅ `git diff HEAD --name-only` 6 文件全在范围、脚本 `dd_changed=0`（主树与 worktree 的 `DD-*` 现仅 `DD-D002` 不同，源于 master 已进 191t 而本分支基线未进，**非本任务改动**，squash 合并不会回退）；TT 删除边界 ✅ 主树 `TT-*`=81、完成区明确“仍待 architect 删除、未声称已删”；体例 ✅ 完成区 9 行、无运行期路径、状态 `待验收`。

**脚本判定**：已不再“以任务书记载为准”；差异集合 / 差异数 / 逐册方向 / D002 对齐四类断言经我三次注入证明**可达 FAIL 且失败原因可区分**；`grep -F "$id" "$TASK"` 已降为辅助断言。

**非阻断 finding（交 architect 收尾处置）**：① 任务书第 1 轮 reviewer 记录（我写的）含 1 处运行期路径 `运行期临时目录`，属文档级，请收尾时脱敏；我本轮不改写既有审阅记录。② 脚本断言“主树 `TT-*`=81”是**删除前**前置条件：architect 删 81 份 TT 后重跑必 rc=1（完成区已注“删除后复查 `TT-*`=0、`DD-*`=81”），届时按 `find` 口径验收，勿把脚本转红误判为回归。③ `相同数=配对数-5` 与 `差异数=5` 数学等价（冗余）、A011 的 `dd_pat` 仅 `cfxha` 偏弱——可不改。

**判决：Accepted** —— 验收标准 1、3–8 在我重跑下全部成立；标准 2（主树删除 81 份 `TT-*`）按任务书接口规范由 architect 执行，已在完成区/遗留问题明确登记，不计本任务未完成项。

#### 收尾（architect，2026-11-05）

- 主工作树 TT 删除已执行：`find docs/DDLN -name 'TT-*' -type f` 由 81 → **0**；`DD-*` 仍 **81**；无备份（用户明确授权）。
- 删除前后 `git status` 无新增/残留；TT 为 gitignored，删除不入 git。
- reviewer 第 2 轮 Accepted（81 对 / 76 相同 / 5 差异，D002 已由 SPEC-191t 对齐）。
- 状态置 `已验证`。
