# INFRA-070t: `.tao/knowledge/` 顶层收拢（立 `Process-07` + 9 文件处置 + 白名单门控）

**模块**：infra
**项目里程碑**：M7
**依赖**：与在办文档/门控类任务**串行**（同改 `docs/**`、`Makefile`、`.tao/knowledge/**`）
**状态**：已验证

> 立项来源：用户 2026-10-12——① 「`gate-tiering-design.md` **应该有一个工程规范文档来专门说明此事，放到 `docs` 下面**」；② 「`.tao/knowledge` 顶层文件太多 ⇒ **难以发现混入新文档**」；③ 要求**逐个看 9 个升格文件的内容并定去留**（**已逐条确认**）。

## 用户裁定 / 指令（2026-10-12，**原话/摘要**）

- 「**`gate-tiering-design.md` …应该有一个工程规范文档来专门说明此事，放到 `docs` 下面**」；
- 「**归档并不意味着创建个子目录，放到子目录里，这是自欺欺人**」（⇒ **归档 = 真进 `.tao/archive/`；"不留" = `git rm`**，**不得**用子目录假装归档 ✗）；
- 「我们逐个看一下每个文件的简要内容，确定是否要留」⇒ 逐条结果经用户 **「可以」** 确认（下表）。

## 现状与**逐条处置**（用户 2026-10-12 确认）

`.tao/knowledge/` 顶层 24 个 = 9 个 `contract-*.md` + 6 个台账/索引 + **9 个升格文档**（本任务处置对象）：

| # | 文件 | 行数 | 处置（**已确认**） |
|---|---|---|---|
| 1 | `embench-analysis.md` | 355 | **提炼 3–5 条要点**进 `docs/Machine-00` §5（套件接入要点）⇒ 原文**归档** `.tao/archive/M7/notes/` |
| 2 | `INTEG-027t-report.md` | 217 | **归档** `.tao/archive/M7/notes/`（唯一记录，保溯源） |
| 3 | `LLVM-070t-rootcause.md` | 86 | **归档** `.tao/archive/M7/notes/` |
| 4 | `SPEC-129t-count-table.md` | 40 | **归档** `.tao/archive/M7/notes/` |
| 5 | `gate-tiering-design.md` | 48 | **并入 `docs/Process-07`**；`milestones.md` 引用**改指规范**；原文**归档** |
| 6 | `TESTCASES-039t-stage1-gaps.md` | 66 | **核实**其内容已被 `ISS-175`–`180`/`187` 覆盖 ⇒ 改引用为 `issues.yaml` ⇒ **`git rm`** |
| 7 | `pending-registrations.md` | 43 | **核实**内容已落 `ISS-187`/`188`/`189` ⇒ 改引用（`issues.yaml`+`milestones.md`）⇒ **`git rm`** |
| 8 | `llvm-isa-backend-matrix.{md,tsv}` | 443/228 | **移 `tools/llvm/`**（随生成器）⇒ 同步生成器默认路径、`--check`、全部引用 |

- `docs/Process-0x` 现有 **6 份** ⇒ 新规范编号 = **`Process-07`**（实测顺延）。

## 接口规范

- **输出**：
  1. **立 `docs/Process-07-门控分层规范.md`**：**分层定义与各层组成**（L1 静态 + 可用性冒烟 / L2 模块功能代表集 / L3 较完整）｜**触发点**｜**"新检查进哪一层"的归属规则**｜**层间不重复**｜**每层须可达 FAIL**｜**与 `AGENTS.md` 的分工**（`AGENTS.md` 留**规则 + 指针**；本规范载**明细与演进规则**，**不重复**）；吸收 `gate-tiering-design.md` 的实质内容。
  2. **9 文件按上表处置**（§1 要点提炼、§5 并入、§6/§7 核实后 `git rm`、其余归档、§8 移 `tools/llvm/`）；**所有引用同步**（`01`/`issues.yaml`/`milestones.md`/生成器/`--check`），**无悬空引用**。
  3. **加白名单门控 `check-knowledge-dir`（治根）**：`.tao/knowledge/` **顶层只允许**既定模式（`contract-*.md`、台账集合、**子目录**）⇒ **白名单外文件即 FAIL**；**须可达 FAIL**（注入一个白名单外文件 ⇒ FAIL ⇒ 还原 ⇒ 回绿）；**纳入 L1**（与 `INFRA-069t` 口径一致），**计数不写死**。
  4. `.tao/knowledge/milestones.md` 流水更新 `INFRA-070t` 行（状态 `待验收`，`完成时间` `—`）。
- **约束**：
  - **归档 = 真进 `.tao/archive/M7/notes/`**（**禁**用 `knowledge/` 子目录假装归档 ✗）；**`git rm` 须先核实内容已被覆盖**（§6/§7）；
  - **不改** `spec/`、`contracts/`、`tests/vectors/`、组件补丁；`contract-*.md` **本任务不迁**；**计数不写死**。

## 验收标准

1. **`Process-07` 存在且不重复**：含上列 6 项要素；与 `AGENTS.md` 分工清楚（`grep` 证明无逐条重复）。
2. **9 文件处置落地**：逐条给出**处置 + 引用替换**；`knowledge/` 顶层**不再含**这 9 个名（`ls` 真实输出）；归档者在 `.tao/archive/M7/notes/`（`ls` 证据）；被 `git rm` 者给出**内容已被覆盖**的逐条核对表。
3. **无悬空引用**：`check-knowledge-refs` rc=0；全仓 `grep` 旧路径**仅剩历史**（archive/任务书）。
4. **顶层收拢**：`knowledge/` 顶层文件数 **before/after 现场统计**（不写死目标值）。
5. **白名单门控**：`check-knowledge-dir` 常态 rc=0；**注入白名单外文件 ⇒ FAIL** ⇒ 还原 ⇒ 回绿（真实输出）；**已入 `make check`**。
6. **门控**：`make check`、`check-no-residue`、`check-knowledge-refs`、`check-issues` 各 EXIT=0。
7. **完成区**（≤30 行）与真实输出逐条对齐。

## 追加范围（用户 2026-10-12 裁定：`contract-*.md` 迁入 `contracts/`）

**裁定原话/结论**：
- 「`contract-*.md`，我还是觉得**放到 `contracts` 目录下好**，唯一的问题是导致 `contracts` 目录下文件过多，是不是建个子目录呢？」⇒ 主会话给数据（`contracts/` 现 5 个 → 迁后 **14 个**，不算多）与代价（建子目录 ⇒ 249 处引用多一层 + 生成器/门控同步）⇒ **不建子目录**；
- 「投影文件是不是加个统一的前缀？」⇒ 主会话给数据（4 个 yaml 改名 = **~520 处**引用；`contract-isa.md` ↔ **两个** yaml ⇒ 映射**非 1:1**；目录内前缀**冗余**；投影关系**已有** `spec/README.md`「投影表」）⇒ **不统一前缀**；
- 「yaml 是不是改成 toml 更合适？」⇒ 主会话给数据（`opcodes.yaml` **6137 行**、大数组+每条嵌套 `fields` ⇒ **TOML 弱项**；格式改 ⇒ **54 处 `yaml.safe_load`** + ~520 处引用）⇒ **保持 YAML**；
- **用户最终选择 = 「保持 YAML + 分工规则（推荐）」**。

**输出追加**：
1. **9 个 `contract-*.md` 迁入 `contracts/` 顶层**（**禁**建子目录 ✗；引用**全量同步**，现场 `grep` 计数）。
2. **命名**：**不统一前缀** ⇒ 4 个 `*.yaml` **不改名**；`.md` **保留 `contract-` 前缀**。
3. **格式**：**保持 YAML**（不转 TOML）。
4. **`contracts/README.md`** 内容 = **两张清单**（叙述型 `.md` / 机器数据 `.yaml`，逐行一句话）+ **一行指针** → `spec/README.md`「投影表」+ **一行分工规则**：*"扁平锁/清单 → TOML（如 `manifests/*.toml`）；嵌套合约数据 → YAML（本目录）"*。
5. **`check-contracts-dir` 白名单门控**：`contracts/` 顶层**只允许** `*.yaml` / `contract-*.md` / `README.md` / 子目录 ⇒ 白名单外即 **FAIL**；**纳入 L1**。

**验收追加**：
8. **迁入生效**：`contracts/` 顶层含 **9 个** `.md`（`ls` 证据）；**旧路径 `.tao/knowledge/contract-*.md` 不再存在**；引用全量同步（`grep` before/after 计数）；`check-knowledge-refs` rc=0。
9. **命名/格式未动**：`git diff --name-status` 显示 4 个 `*.yaml` **无 `R`（未改名）**、内容未变；`contracts/README.md` 含两清单 + 指针 + 分工规则（`grep` 真实输出）。
10. **`check-contracts-dir`**：常态 rc=0；注入白名单外文件 ⇒ **FAIL** ⇒ 还原 ⇒ 回绿；**已入 `make check`**。

## 硬约束（下发提示必带）

1. 临时目录 `/tmp/opencode/INFRA-070t/`；**命令一律在 workdir（= 仓库根）内、相对路径；禁 `cd` 出界**；禁仓库内临时文件。
2. **不提交 git**；显式 staging（禁 `git add -A`）。
3. 完成区与真实输出逐条对齐；**禁 `cmd | tee` 吞码**。
4. 只动任务范围（`docs/**`、`.tao/knowledge/**`、`.tao/archive/M7/notes/**`、`tools/llvm/**`、`Makefile`、`tools/infra/**`、任务书）；越界须披露。
5. **处置表已确认**；**若实施中发现某条与"内容已被覆盖"不符** ⇒ **停下报告**（禁自拟自答，`lessons §3.17`）。
6. 任务书/记录中**不得写字面 `.work/<具体路径>`**（用 `<>` 占位）。
7. 一键证据脚本落 `.work/evidence/<任务ID>/`（能失败、可达 FAIL、结构断言、计数不写死、捕获退出码）。
8. 反例注入还原**禁** `git checkout`/`restore`/`stash`；一律 `cp` + md5 对账。
9. **计数不写死**。

## 完成区

**测试结果**：`.work/evidence/INFRA-070t/run.sh` → `RESULT: ALL PASS`，`EVIDENCE_EXIT=0`（A1–A7 全绿）；`make check` / `check-no-residue` / `check-knowledge-refs` / `check-issues` / `check-isa-coverage` 各 EXIT=0。
**修改文件**：新增 `docs/Process-07-门控分层规范.md`、`tools/infra/check_knowledge_dir.py`、证据脚本；改 `AGENTS.md`、`docs/README.md`、`docs/Machine-00-执行环境分层-Draft.md`、`Makefile`、`tools/llvm/gen_isa_coverage.py`、`.tao/knowledge/{issues.yaml,milestones.md}`；`git mv` 5 篇→`.tao/archive/M7/notes/`、矩阵 2 件→`tools/llvm/`；`git rm` 2 篇（**移动/删除已入索引**；`docs/Process-07`+`check_knowledge_dir.py` 现为未跟踪，architect 提交时须显式 staging）。
**验收结果（真实输出）**：
- `check-knowledge-dir` 常态 rc=0；**注入白名单外文件 rc=1**；还原（目录清单 md5 相等）后 rc=0；已入 `check:`（L1）。
- `knowledge/` 顶层 **before 24 → after 15**（`ls | wc -l` 现场统计）；9 文件名已不在顶层。
- 归档 `.tao/archive/M7/notes/`(ls 实测)：embench-analysis / INTEG-027t-report / LLVM-070t-rootcause / SPEC-129t-count-table / gate-tiering-design。
- 矩阵新路径 `tools/llvm/llvm-isa-backend-matrix.{md,tsv}`；生成器默认路径/自引已同步；`--check` PASS。
- `check-knowledge-refs`：悬空 0；旧矩阵/旧文件路径非历史引用 = 0（仅 changelog 历史行，见遗留）。

**§6/§7 覆盖逐条核对（`git rm` 依据，实测）**：039t §G1→`ISS-175`(:21,LLVM-071t)｜§G2→`ISS-176`(:22,LLVM-073t)｜§G3→`ISS-177`(:23,LLVM-072t)｜§G4→`ISS-178`(:24,LLVM-070t)｜§G5→`ISS-179`(:25,LLVM-071t)｜§G6→`ISS-180`(:26,LLVM-070t)｜039t 逐基准矩阵/结论→归档 `.tao/archive/M6/testcases/TESTCASES-039t-Embench接入.md`（行号指 `.tao/archive/M6/issues-closed.md`）；pending §R1→`ISS-181`(:27)+`ISS-189`｜§R2→`ISS-182`(:28)｜§R3→`ISS-187`。（任务书表中「039t 由 `ISS-175–180/187` 覆盖」的 `187` 实属 `pending §R3`；039t 六条 = `ISS-175–180` **全覆盖**，无未覆盖项。）
**新发现/坑**：① 门控分层明细原在 `AGENTS.md`、`gate-tiering-design.md`、`Makefile` 头注释三处；收敛后 `AGENTS.md` 只留规则+指针、明细归 `Process-07`（`lessons §2.11` 生成投影类同源）。② `gen_isa_coverage.py --check` 会在 `TSV_DEFAULT` 命中时断言「TSV 数据行 == 真源记录数」，搬路径后须同步该默认值（否则 `--check` 在旧路径找不到产物）。
**遗留问题**：**Phase B（9 个 `contract-*.md`→`contracts/`）未执行——硬约束冲突，需用户裁定**（未空等，保留现场）：`contract-*.md` 引用散布于「只动范围」**之外**且与「不改 `spec/`、`contracts/`、组件补丁」**冲突**——(a) `spec/Toolchain-01`（**只读哈希锁册**，5 处）+ `spec/README.md`（2 处）⇒ 改须用户事先授权（`Process-06 §2`），且主会话预检 #5「无 `spec/` 命中」与 Phase B 清单含 `spec/README.md` **自相矛盾**；(b) `contracts/*.yaml` 8 处（含字段 `contract:`/`detail_contract:`）⇒ 任务书要求「内容不动」；(c) `tools/testcases/**`(7)/`tools/qemu/**`(8)/`tools/integ/**`(1) 硬编码旧路径（如 `check_fp_contract.py:108`）⇒ 不在「只动范围」；(d) `components/**` 补丁注释(~10)、`tests/**`(~10)。**执行 Phase B 会在只读锁卷留悬空引用** ⇒ 停手报告（`lessons §3.17`）。另：`components/llvm-project/changelog.md:57`（LLVM-081t 历史行）、`tools/integ/run_embench_e2e.py:13`（`.work/…` 历史指针）出界未改。

## 审阅记录

#### 第 1 轮 engineer 自审（自主逐行）
实施后逐行复核 Phase A 改动源码/文档，逐条 finding 处置（无代码逻辑，重点在门控可达 FAIL 与引用一致性）：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `check_knowledge_dir.py` docstring 引 `_CONTRACT_GLOB`（无该名，实为 `_ALLOWED_GLOBS`） | ✅已修 | 改 docstring 名 | `python3 tools/infra/check_knowledge_dir.py` rc=0；证据 A5 |
| F2 门控须可达 FAIL 且非 vacuous（防「只会 PASS」） | ✅已修 | 注入白名单外文件→rc=1；空/无白名单文件→fail-closed | 证据 A5b 注入 rc=1；A5c md5 相等；A5d 回绿 rc=0 |
| F3 搬矩阵后生成器默认路径/自引未同步会致 `--check` 假绿/假红 | ✅已修 | `TSV_DEFAULT`/`MD_DEFAULT`/docstring/`render_md` 四处 | `gen_isa_coverage.py --check` PASS（现场重生成后） |
| F4 `AGENTS.md` 是否残留门控明细（与 Process-07 重复） | ✅已修 | 明细句改为指针 | 证据 A2b：`grep -F '新检查进哪一层' AGENTS.md` 不命中 |
| F5 引用同步后旧路径是否仍被非历史引用 | ✅已修 | 改 `issues.yaml`(×3)/`milestones.md`(×3)+归档 5 篇 | 证据 A6b 旧矩阵路径非历史=0；`git grep` 旧文件路径全 0 |

判决：全部 finding 已处置（无未修项）→ 状态置 **待验收**。

#### 第 1 轮 reviewer 验收

**判决：Accepted（Phase A）｜Phase B ⏳ BLOCKED（硬约束冲突，需用户授权，不在本轮验收范围）**。验收 1–7 全过、约束无违反；全程自跑，未采信完成区转述。

**重跑记录（真实退出码，均 reviewer 自跑）**：`make check` EXIT=0（L1 PASS）｜`check-no-residue`/`check-knowledge-refs`/`check_issues.py`/`check-isa-coverage`/`gen_isa_coverage.py --check`（PASS，真源 227）/`check-knowledge-dir` 各 EXIT=0。`check-knowledge-dir` 确在 `check:` 依赖链（`Makefile:445` + `make -n check` 命中 `check_knowledge_dir.py`）；重跑 `<证据目录>`/run.sh ⇒ `RESULT: ALL PASS`、`RUN_EXIT=0`（A1–A7 全绿，含其 A5b 注入 rc=1）。

**① Process-07**：6 要素 `grep` 全命中（§1 分层组成/§2 触发点/§3 新检查归属/§4 层间不重复/§5 可达 FAIL/§6 分工）；`AGENTS.md` 门控节已指针化（字节级核实为「新检查进哪层」，`grep -F '新检查进哪一层'` rc=1 ⇒ 无明细重复）；对照归档 `gate-tiering-design.md`：四条必须规则（L1 收缩/能失败+结构断言/机械派生+不重复/触发点）与三层映射表**实质全吸收**，无要点丢失（非阻断：原稿 §五「逐门控计时」待办未搬入，建议补一句或在 `INFRA-058t` 收口）。

**② `git rm` 逐条覆盖独立核对（自读 `git show HEAD:` 原文 vs 现行台账/归档，非采信核对表）**：G1→`ISS-175`、G2→`ISS-176`、G3→`ISS-177`、G4→`ISS-178`、G5→`ISS-179`、G6→`ISS-180`（`.tao/archive/M6/issues-closed.md:21-26`）；R1→`ISS-181`（SPEC-130t 归档含用户 6 条裁定，含「不立 ADR」④ ⇒ R1「ADR 建议」已有着落）+`ISS-189`（剩余面/受理侧机制）；R2→`ISS-182`；R3→`ISS-187`（notes 实质逐项吻合）⇒ **无未覆盖条目**。最小复现另存 `.tao/archive/M6/llvm/LLVM-070t…075t`（G2 含 wikisort `-O0 mulhu` 命中）；逐基准结果可由 039t 归档任务书 line75 按缺口清单 + 验收4 通过清单完全重构（19/19 对账）。非阻断：首错列原文仅存 `<日志目录>` 易失日志；`ISS-188` notes 引「§R4」但被删文件仅 R1–R3（既有失准引用，非本任务引入）。

**③ 归档核**：5 篇真在 `.tao/archive/M7/notes/`（`ls` 5/5）；`knowledge/` 顶层 **15 文件/0 子目录**（无子目录假装归档）；before 24（`git ls-tree HEAD`）→ after 15（现场 `ls|wc -l`）。

**④ 矩阵迁移**：`tools/llvm/` 两件在；`tools/` 内旧路径 grep=0；生成器 `TSV_DEFAULT`/`MD_DEFAULT`/自引全同步；`--check` PASS（EXIT=0）；机械性核：tsv 与旧文**逐字节相同**、md 仅 1 行自引路径差异（无手改数据列）。非阻断：重生成 md 改动**未入索引**（`RM`），architect 须把工作树版一并 staging（完成区已披露 staging 责任）。

**⑤ embench 提炼**：`Machine-00 §5.1` 5 条；抽查 4 条与归档原文实质一致（3 函数接入面/退出码判据不靠打印 correct/md5sum 唯一端序坑/内存 64 KiB·268 KiB·≥250×）。

**⑥ 引用同步**：全仓旧路径 grep 仅剩历史（archive 自引、任务书历史行、`components/llvm-project/changelog.md:57`）⇒ **非历史悬空 = 0**。

**⑦ 独立反例（与 engineer 不同名不同法）**：`cp docs/Process-07-*.md → .tao/knowledge/zz-reviewer-inject-Process-07.md` ⇒ 门控 **EXIT=1**（FAIL，报 1 个白名单外文件）+ run.sh **EXIT=1**（`[FAIL] A5a 常态`、`RESULT: FAIL`）；`rm` 还原 ⇒ 目录清单 md5 `b3f3a293…`==`b3f3a293…` ⇒ 门控 EXIT=0 + run.sh 重跑 `RESULT: ALL PASS`、EXIT=0（注入→FAIL→还原→回绿闭环，未用 `git checkout/restore/stash`）。

**⑧ Phase B BLOCKED 核（真实）**：`spec/Toolchain-01` 确在 `manifests/spec-readonly.lock.toml`（`path`+`sha256` 锁册）；`contract-*.md` 引用散布 `spec/README.md`、`contracts/*.yaml`（`contract:`/`detail_contract:`）、`tools/{testcases,qemu,integ,spec}`（36 行）、`components/`（13 行）、`tests/`（12 行）⇒ **均在「只动范围」外**，停手理由成立（计数与完成区略有出入，方向一致，不阻断）。完成区/`milestones.md` 均如实标「Phase B 未执行·待裁定」，未写「全部完成」。

**约束核验**：临时目录 `<审查临时目录>`；未提交 git、未改被测实现；快照对账 `git status` + 7 目标文件 md5 审查前后 **diff EXIT=0**（本记录写入属预期）；无越界、未用 `question`；还原用 `rm`（新文件）+ md5 对账。**非阻断建议**：(a) 补「逐门控计时」落点；(b) archit 提交时补 staging 重生成 md；(c) 039t 归档任务书指向已删稿的 `<日志目录>` 旧指针可在 `issues.yaml:290` 注释中再指明归档任务书行号。
