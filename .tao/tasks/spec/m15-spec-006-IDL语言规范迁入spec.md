# m15-spec-006: IDL 语言规范与语义库迁入 `spec/`（新册 `IDL-SimRISC-ISA语义描述语言与语义库`）

**模块**：spec
**项目里程碑**：M15
**依赖**：无（`m15-spec-005` 已收尾；`.idl` 内容不动）
**可并行分片**：否
**预估**：2–3 h
**档位**：中改
**状态**：已验证

## 背景（用户 2026-11-20 裁定）

`idl/README.md` 现有 **428 行**，实际是**规范正文**：§1 语法基线（UDB IDL 子集）、§2 命名约定、§3 寄存器模型、§4 语义库（4.1–4.7，约 260 行）、§5 语法扩展提案、§6 `idlc` 复用评估、§7 变更记录。而 `spec/README.md:36` 把它当真源指（「语法基线、寄存器模型与语义库见 `../idl/README.md`」）。

⇒ 规范正文寄生在**工具目录的 README** 里，与三分界（`spec/` = 技术规范正文唯一真源）相反。

**UDB 的对应做法**：语言说明书是独立文档 **`doc/idl.adoc`**（ISA Description Language），语义库是 `spec/std/isa/isa/*.idl`。

**用户裁定**：
1. **就一册**（语言 + 语义库同册）；
2. 文件名**要写清是什么语言**——即 **SimRISC ISA 语义描述语言**（`IDL-SimRISC-ISA语义描述语言与语义库.md`）。

## 要做

1. **新建** `spec/IDL-SimRISC-ISA语义描述语言与语义库.md`：
   - 正文 = 现 `idl/README.md` 的 §1–§6（保持内容，可重排编号适配 spec 体例）；
   - §7 变更记录迁入本册的**变更记录附录**（`check-spec-numbering` 对非 `SimRISC-` 册要求「变更记录附录为最后一个 `##`」）；
   - 册内 `## N.` 编号连续、不跳级（`check-spec-numbering`）。
2. **`idl/README.md` 精简**为**目录导航 + 用法**（≤60 行）：12 册 `SimRISC-NN.idl`、`lib/fp.idl`、`render.py` 的三条用法、`.manifests.toml`；语言与语义库的正文**指向** `spec/IDL-SimRISC-ISA语义描述语言与语义库.md`。
3. **`idl/render.py` 的扫描面改指新册**：现 `render.py:210-213` 解析 `idl/README.md §4` 的代码块，作为「每条 operation 调用的函数都在语义库声明」这条断言（E 组）的扫描面；改为解析 `spec/IDL-SimRISC-ISA语义描述语言与语义库.md` 的语义库章节。**保持「+ `idl/lib/*.idl`」那一半不变**。
4. **`spec/README.md`**：「ISA 语义（IDL）」节的指针改指新册；「分册清单」加一行（可按现有分组，或新开「ISA 语义（IDL）」组内列入本册）。
5. **`spec/.manifests.toml`**：加本册条目 + `sha256`；`spec/README.md` 的 `sha256` 同笔重算。

## 硬约束

- **不动任何 `.idl` 内容**（12 册 + `lib/fp.idl` 一字不改）；
- **不改门控判据**（`check-idl-sync`/`check-spec-*` 的逻辑不变，只换被扫描的路径）；
- 术语一律「寄存器组」；
- 不升级版本号。

## 验收（逐条贴真实 rc）

1. `python3 idl/render.py --check` rc=0（263 条 / 12 册逐字节一致）；
2. `make check-idl-sync`、`check-manifests-guard`、`check-spec-numbering`、`check-spec-purity`、`check-spec-codeblocks`、`check-spec-drift`、`check-spec-refs`、`check-spec-changelog`、`check-knowledge-refs` 全 rc=0；
3. **断言 E 仍可达 FAIL**：临时在某条 operation 里调用一个未声明函数 ⇒ `render.py --check` 必须红（`cp`+md5 还原）；
4. **内容零丢失**：新册正文与 `idl/README.md` 旧 §1–§7 逐段对账（可用 diff，排除重排编号），列出差异仅为「编号/标题层级」；
5. **`idl/README.md` ≤60 行**且无规范正文（只有导航 + 用法 + 指针）。

## 审阅记录

### 第 1 轮 engineer 自审

审查对象：新册全文、`idl/README.md`、`idl/render.py`（`SEMANTICS_REL`/`load_declared`）、`spec/README.md`、`spec/.manifests.toml`、`tools/spec/check_spec_changelog.py`、证据脚本（`run.sh`/`content_diff.py`/`layout_check.py`）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `check_spec_changelog` 把 `IDL-SimRISC-ISA…` 误判为 SimRISC 系列册（实测 2 条违规：禁附录 + 误入互锁组） | ✅已修（**越界披露**） | 2 处 `"SimRISC-" in …` → `Path(…).name.startswith("SimRISC-")`（与 `check_numbering`/`check_spec_purity` 同口径）；只收窄误判面 | `run.sh` 3.10 fake `SimRISC-01` 带附录仍 FAIL（「只允许出现在 SimRISC-00」）、3.12 fake `IDL-…SimRISC-…` 独立册 PASS；真仓 22 册 PASS |
| F2 §6.1 末句「结论记在本任务的完成区」属任务书写法 | ✅已修 | 删该分句；列入 `content_diff.py` 的 `DOCUMENTED_EDITS` | `content_diff` A 段差异 0 |
| F3 §4.2 代码块注释「见 README §3」在新册内自指失效 | ✅已修 | 改「见 §3」；列入 `DOCUMENTED_EDITS` | 同上；`render.py --check` rc=0 |
| F4 三处把 ISA 写成「DADAO」（`DADAO 的 ft 结果`/`DADAO 需要`/`DADAO 只需`） | ✅已修 | 按用户 2026-11-20 更正改 `SimRISC`；`DADAO-12` 引用保留 | `layout_check` E：新册裸 `DADAO` 0 处 |
| F5 §7 含任务号 `m15-idl-016/017`；`idl/.manifests.toml`/`sha256` 待办属工具目录 | ✅已修 | 变更记录按 spec 体例去任务号（技术内容全保留）；待办行迁 `idl/README.md` | `content_diff` B：4 个未覆盖记号均逐条注明 |
| F6 `.idl` 注释的 `idl/README §N` 记号未改（硬约束） | ⏸延后 | `idl/README.md` 注明「旧 §N → 新册 §N」 | 登记遗留 ② |
| F7 卷首定位段 = 旧 3 行 blockquote 合并（非 §1–§6 正文） | ✅已修 | 保留基线/方向/可解析范围三点；文件表留在 `idl/README.md` | `content_diff` 只比 §1–§6；新册 425 行 |

**判决：待验收**（F1 为硬约束越界的必要修正，需用户/主会话确认；其余全部已修，无未修 finding）。自审另核：`render.py --self-test` 11/11 PASS；`Path` 已在 `check_spec_changelog.py` 导入；证据脚本注入均作用于临时副本，真实 `.idl` md5 `0c5df887…` 前后不变。

### 第 1 轮 reviewer 验收

**重跑（我自己的命令 + 真实 rc，全部在任务 worktree 执行；判决只依据我的输出）**

- `python3 idl/render.py --check` → **rc=0**（`源 operation=263 条 / 落点 12 册 / 标记块 263 个`）；`--self-test` → **rc=0**（11/11 PASS，`undeclared-call` 期望非 0 实得 1）。
- 9 个门控逐条实跑：`check-idl-sync`=**0**（263 逐字节）、`check-manifests-guard`=**0**（文件 47 / sha256 23 全符）、`check-spec-numbering`=**0**（files=22）、`check-spec-purity`=**0**（files=23 hits=0）、`check-spec-codeblocks`=**0**（519 行）、`check-spec-drift`=**0**（11 合约错误 0）、`check-spec-refs`=**0**、`check-spec-changelog`=**0**（files=22 segments=58）、`check-knowledge-refs`=**0**（悬空 0）。
- 工程师权威证据脚本（**运行期证据目录内的 `run.sh`**）我原样重跑 → `EVIDENCE: PASS`、**rc=0**、25 项全 PASS；未采信其转述。

**硬判据 1：门控 2 行 = 判据对齐，非放松** — 谓词逐字等于 `check_numbering.py:141` / `check_spec_purity.py:70` 的 `<path>.name.startswith("SimRISC-")`；真实清单 23 册上新旧判据集合差 = **仅新册一册**（14→13），13 册 `SimRISC-00..12` 归类不变。独立 fixture（同一棵树跑基线脚本 vs 新脚本）：① `SimRISC-07` 带附录 → **rc=1**「变更记录附录只允许出现在 SimRISC-00」；② `SimRISC-00` 缺附录 → **rc=1**「未找到唯一的…（命中 0）」；③ `IDL-SimRISC-ISA-*` 带附录 → **rc=0 PASS**（基线脚本对同 fixture 报 3 违规；对真仓复现 engineer 自报的 2 条误判：`IDL-…须删除` + `互锁组 ['0.1.1-rc','0.5.7-rc']`）。反向注入：真册 `SimRISC-07` 册头+顶部段改 `0.5.6` → **rc=1**「互锁组组内册头版本不一致」⇒ 13 册互锁仍有效，未放松。

**硬判据 2：内容零丢失（我自己 diff）** — 基线固定 commit `a59a6555`（任务书新增提交之父；其 `idl/README.md` md5 与 `1ae96e42` 同为 `f1ca9f2b…`，`git diff a59a6555 1ae96e42 -- idl/` 空）。新册 §1–§6 与基线 §1–§6 **原始 diff：403 vs 403 行，仅 5 行差异**，逐行 = `README §3`→`§3`、`DADAO 的 ft 结果`/`DADAO 需要`/`DADAO 只需`→`SimRISC…`、删「…结论记在本任务的完成区」，与 `DOCUMENTED_EDITS` **一一对应**；去标题+空行 320 vs 320。§4 函数声明我独立计数 **23 = 23、集合差空**；§7 → 附录版本段化（4 个未覆盖记号均逐条注明）。

**硬判据 3：断言 E 可达 FAIL（我自己注入，非采信）** — 临时树基线 rc=0；① 在 `idl/SimRISC-05.idl` 尾追加 `zz_probe_undeclared(6'd0);` → **rc=1**「`cmp.uo_orrr_dbb`: 调用未声明的函数 `zz_probe_undeclared(`」；`cp` 还原 + md5 `30777fd9…` 相同 → **rc=0**。② **删新册 §4 的 `builtin function ip {`** → **rc=1**（200+ 条「调用未声明的函数 `ip(`」）⇒ 扫描面确为新册（旧 README 已无 `## 4.`）；还原 md5 `fb8af2b9…` 相同 → **rc=0**。

**其余核验**：`idl/README.md` **22 行**（≤60）且无正文（`## N.` 0 / ` ```idl ` 0 / 函数声明 0，只有文件表+用法+指针+待办）；13 个 `.idl` 与基线**逐字节 0 漂移**；manifest 23 条 sha256 现算全符（新册 `9a130dca…`、`spec/README.md` `5eeca0d0…` 同笔重算）；`git show --name-only HEAD` = **7 文件**、无其它 spec 册、无版本号改动、术语合规。

**约束核验**：不动 `.idl` ✅；术语「寄存器组」✅；不升版本号 ✅；**我未改任何代码**（写入本记录前 `git status --porcelain -uall` 空，六个目标文件 md5 已记档）。

**判决：Accepted**（三条硬判据在我自己的重跑下全部通过）。finding（不阻断，交 architect 定夺）：**①须追认** — `check_spec_changelog.py` 2 行确实触碰任务书硬约束「不改门控判据」，但属与另两门控**对齐的必要修正**（不改则新册被误判 2 条违规；改名又与用户 2026-11-20「文件名要写清是什么语言」的裁定冲突），engineer 已越界披露并挂「待用户裁定」，**须 architect/用户追认后方可 `/complete`**。② `content_diff.py` 的 `normalise` 以 `line.startswith('#')` 剥行，连 ` ```idl ` 内 `# ` 注释行一并跳过 ⇒ 断言 A 对这类行有盲区（`README §3` 那条声明改动实际未被断言覆盖）；本次交付我已用原始 diff 独立核过，不阻断，建议改为只剥 `#{1,6} ` 标题行。③ 新册 §4.7 保留 3 处 `m15-idl-016/017`，`check-spec-purity` 任务号模式只认大写前缀故不命中（既有盲区、非本任务引入），已由 engineer 登记遗留③。

### 第 2 轮 engineer 自审（返工 1）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| R1 旧册名含 `SimRISC-` 子串 ⇒ 基线 `check_spec_changelog` 误判（第 1 轮 F1 的越界根因） | ✅已修 | `git mv` → `spec/IDL-ISA语义描述语言与语义库.md`；`tools/spec/check_spec_changelog.py` 恢复基线 blob（`cp`，md5 `1effc019…`，未用 `git checkout/restore`） | `git diff <基线> -- tools/` 空；9 门控全 rc=0；`run.sh` 3.10–3.13 |
| R2 reviewer finding ②：`content_diff.normalise` 用 `startswith('#')` 把 `.idl` 注释行一并剥掉（对账盲区） | ✅已修 | 改为只剥 `^#{2,6}\s` 标题；`# 四组寄存器…见 §3` 注释行纳入对账 | A 段 322 vs 322 行、差异 0（此前 320 vs 320） |
| R3 改名后引用可能遗漏（`render.py` 的 `SEMANTICS_REL`/docstring、证据脚本） | ✅已修 | 同步 `idl/render.py`、`idl/README.md`、`spec/README.md`、`spec/.manifests.toml`、证据脚本 | 全仓 grep 旧名 0（任务书历史与里程碑台账除外）；`render.py --check` rc=0 |
| R4 `cp` 还原时误带 `chmod +x`（mode 100755） | ✅已修 | `chmod 644` 恢复 | `git diff <基线> -- tools/` 空（含 mode） |

**判决：待验收**（R1–R4 全部已修；第 1 轮越界项随门控撤回归零，无未修 finding）。

### 第 2 轮 reviewer 验收

**重跑（我自己的命令 + 真实 rc）**：9 门控逐条 —— `check-idl-sync`=**0**（263 逐字节）、`check-manifests-guard`=**0**（文件 47 / sha256 23）、`check-spec-numbering`=**0**（files=22）、`check-spec-purity`=**0**（files=23 hits=0）、`check-spec-codeblocks`=**0**（519 行）、`check-spec-drift`=**0**（11 合约错误 0）、`check-spec-refs`=**0**、`check-spec-changelog`=**0**（`files=22 segments=58 rc_segments=10 bullets=285 simrisc_header_versions=['0.5.7-rc']`，与自报一致）、`check-knowledge-refs`=**0**（悬空 0）；`check-tasks`=**0**（报告型：①漏收尾 1 / ②待开工 13，不阻断）。`idl/render.py --check`=**0**（263 条 / 12 册 / 263 块）、`--self-test`=**0**（11/11，含 `undeclared-call` rc=1）。证据脚本（**运行期证据目录内的 `run.sh`**）原样重跑 → `EVIDENCE: PASS`、**rc=0**、**26 PASS / 0 FAIL**。

**核 1 册名与引用同步** — `spec/IDL-ISA语义描述语言与语义库.md`（425 行）在位，sha256 = **`9a130dca…`**（与第 1 轮旧名册 blob 同值 ⇒ 正文零改动）；`spec/README.md` sha256 = **`54420b03…`**，manifest 中新册与 README 两条 sha256 与我现算逐字相同；`idl/render.py` 的 `SEMANTICS_REL`（+ docstring）、`idl/README.md` 指针、`spec/README.md` 分册行+指针、`spec/.manifests.toml`、证据脚本全部指新名。全仓 grep `IDL-SimRISC-ISA` 仅剩任务书（含第 1 轮记录历史）与 `milestones-m15.md` 台账行；`spec/` 下旧名册文件 **0 残留**。

**核 2 门控撤回（以分支基点判，不以工作树对 HEAD 判）** — `git diff $(git merge-base master HEAD) HEAD -- tools/` → **空，rc=0，净改动 0**；`git status --porcelain -uall` → **空**（HEAD 已含撤回，无 `M`）；`md5sum tools/spec/check_spec_changelog.py` = **`1effc019a49100a3057a4a621b281856`**，与基线 blob、`git show HEAD` 两处**同值** ⇒ 与基线**逐字节相同**（含 mode），squash 合入后 `tools/` 净零。

**核 3 基线判据下 3 个 fixture（被测脚本 md5 `1effc019…` 即基线）** — ① `SimRISC-07` 带附录 → **rc=1**「变更记录附录只允许出现在 SimRISC-00」；② `SimRISC-00` 缺附录 → **rc=1**「未找到唯一的 `## 附录：版本与变更记录`（命中 0）」；③ `IDL-ISA-*` 带附录 → **rc=0 PASS**；附带 ④ 旧名 `IDL-SimRISC-ISA-*` 带附录 → **rc=1**（证明改名是根治、不是门控放松）。

**核 4 finding ② 真修** — `content_diff.normalise` 现为 `re.match(r"^#{2,6}\s", line)`（原 `line.startswith('#')`），单 `#` 的 `.idl` 注释行不再被剥；`content_diff` 报 **A：旧 322 / 新 322、差异 0**（原 320）；我独立归一化同样得 **322 vs 322**，多出的 2 行正是 `# 四组寄存器各 64×64；0 号语义见 §3（模型不变量）` 与 `# rf 的两个数据视图…`。

**核 5 内容零丢失（我自己 diff，基线固定 commit `a59a6555`）** — §1–§6 **403 vs 403 行**，变更行**只有原 5 处**（`README §3`→`§3`、3 处 `DADAO…`→`SimRISC…`、删「…结论记在本任务的完成区」）；§4 函数声明 **23 = 23、集合差空**；§7 记号 45/42、未覆盖 4 个逐条注明。

**核 6/7/8** — `idl/README.md` **22 行**且无正文；13 个 `.idl` 与基线**逐字节 0 漂移**；`git show --name-only HEAD` = **7 文件**（任务书、`idl/README.md`、`idl/render.py`、`spec/.manifests.toml`、改名新册、`spec/README.md`、`tools/spec/…` 撤回），基线净 diff 6 文件且 `tools/` 为 0；工作树干净 —— **我未改任何代码**（写入本记录前 6 个目标文件 md5 已记档）。

**判决：Accepted** — 四件全过；第 1 轮 finding ①（门控越界）已由**改名 + 撤回**根治（`tools/` 净零、判据回到基线），finding ② 已真修；finding ③（新册 §4.7 残留 `m15-idl-016/017`、`check-spec-purity` 任务号模式只认大写前缀故不命中）仍未处理，维持**不阻断**、留 architect 定夺。

## 完成区

### 返工 1（用户 2026-11-20 追加裁定：文件名删 `SimRISC` 子串）

**裁定**：册名去掉 `SimRISC` ⇒ `spec/IDL-ISA语义描述语言与语义库.md`（`git mv`），这样**不必动门控判据**。
**处置**：① 改名（正文零改动，sha256 仍 `9a130dca…`）；② `tools/spec/check_spec_changelog.py` **恢复基线版本**（`cp` 自基线 blob `1effc019…`，**禁** `git checkout/restore`）；③ 同步 `spec/README.md`（分册行 + 指针）、`spec/.manifests.toml`（条目名 + `spec/README.md` sha256 `54420b03…`）、`idl/README.md`、`idl/render.py`（`SEMANTICS_REL` + docstring）、证据脚本；④ 顺带修 reviewer finding ②（`normalise` 只剥 `##`+ 标题，`#` 注释行参与对账）。
**复验（真实 rc）**：`git diff <基线> -- tools/` **空**（`tools/spec/` 不在改动集；`..HEAD` 仍含返工前的 WIP 提交，待 architect 重提交后归零）；9 门控全 **rc=0**（**基线判据**对新册名不再误判：`check-spec-changelog` files=22 segments=58）；`render.py --check`=0（263 条 / 12 册 / 263 块）；零丢失仍为原 5 处（322 vs 322 行、差异 0）；`idl/README.md` 22 行；证据脚本 `EVIDENCE: PASS`（26 项）。
**效果**：`m15-spec-006` 的硬约束**越界项归零**——门控文件与基线逐字节一致，任务书不再有「待裁定」项。

#### 第 1 轮完成区（返工 1 之前的记录，供追溯；册名/门控/25 项计数均已由返工 1 更新）

**测试结果**：运行期证据目录内 `run.sh` → `EVIDENCE: PASS`（**25 项 PASS / 0 FAIL**）。覆盖：`render.py --check` = **263 条 / 12 册 / 263 块**；`render.py --self-test` = PASS（11/11）；验收点名的 9 个门控全 rc=0；断言 E 注入（临时树追加 `rd_read_typo(6'd0);`）→ rc=1 且红灯为「调用未声明的函数」→ `cp`+md5 还原 → rc=0；零丢失删行注入 → FAIL；README 灌到 61 行 → FAIL；门控收窄双向（fake `SimRISC-01` 带附录 → FAIL；fake `IDL-…SimRISC-…` 独立册 → PASS）。
**修改文件**：新增 `spec/IDL-SimRISC-ISA语义描述语言与语义库.md`；`idl/README.md`（428→22 行）、`idl/render.py`（断言 E 扫描面）、`spec/README.md`（指针 + 分册行）、`spec/.manifests.toml`（新册 + README sha256）、`tools/spec/check_spec_changelog.py`（**越界 2 行**，见自审 F1；**返工 1 已撤回、与基线逐字节一致**）、本任务书。
**验收结果**：逐条 rc：`render.py --check`=0、`check-idl-sync`=0、`check-manifests-guard`=0、`check-spec-numbering`=0、`check-spec-purity`=0、`check-spec-codeblocks`=0、`check-spec-drift`=0、`check-spec-refs`=0、`check-spec-changelog`=0、`check-knowledge-refs`=0。`check-numbering` files=22、`check-manifests-guard` 文件 47/sha256 23 全符、`check-spec-changelog` files=22 segments=58。零丢失：旧 README §1–§6 正文 320 行 vs 新册 320 行、差异 0（5 处逐条注明的改动除外）；§7 反引号记号 45 个、未覆盖 4 个全部注明；§4 函数声明 23/23 等价；`.idl` 13 个逐字节未动。
**新发现/坑**：① `check_spec_changelog` 以路径子串 `"SimRISC-"` 判 SimRISC 系列册，新册名 `IDL-SimRISC-ISA…` 会被误判（禁附录 + 误入互锁组）；一度改为文件名前缀判定（收窄）；**返工 1 按用户裁定改名并撤回该改动**，基线判据不再误判。② `check_spec_changelog` 的 `-rc` 段校验假定三段版本号（`x.y.z`），两段会索引越界；新册版本段用 `0.0.1`/`0.1.0`/`0.1.1-rc`。③ 新册首版版本号取 `0.1.1-rc`（承旧 README 的 v0.1 + 未定版浮点库），未改任何既有册版本号。④ `check-spec-archive` 在本 worktree 因 `.cache/refs/DADAO.wiki` 缺失跳过 A3/A4（rc=0，环境所致）。
**遗留问题**：① ~~待用户裁定：门控 2 行判据收窄~~ → **返工 1 已消解**（用户裁定改名 + 撤回门控，越界归零）。② `.idl` 注释里的 `idl/README §N` 记号（`SimRISC-03/06` 共 9 处）因「不动 `.idl`」未改；已在 `idl/README.md` 注明「旧 §N 记号对应新册 §N」，建议另立小任务改注释并重渲染。③ 新册 §4.7 正文保留 `m15-idl-016/017` 任务号记号（零丢失优先；`check-spec-purity` 不命中），建议后续清理。
