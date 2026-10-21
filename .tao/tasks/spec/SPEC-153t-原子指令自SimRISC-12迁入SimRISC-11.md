# SPEC-153t: 原子指令由 `SimRISC-12` 迁入 `SimRISC-11`

**模块**：spec
**项目里程碑**：M9
**依赖**：`ADR-0034`（`D1`–`D7`，已 `Accepted`；`fence` 新编码 `100-000`、`lr/sc` 24 条新命名已在 11/12 两册落纸）；`SPEC-152t`（同模块「改生成器 → 重生成 → 只读锁重算」先例）；**串行**：本册 → `SPEC-154t`（两册同改 `spec/`；且 `154` 的 `0.5.5-rc` 快照须含本册结果）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源 / 现场事实（**先读，勿重复查证；仍须现场复核**）

- **用户原话（逐字）**：「**把 原子指令 从SimRISC-12移动到SimRISC-11**」（渠道 = 经主会话转达；architect 2026-10-21 立册）。
- **现场事实（architect 2026-10-21 实测，`master` = `8681b7a5`；执行时逐条复核并留命令输出）**：
  1. `spec/SimRISC-12-待定.md`（220 行）`## 3. 原子指令` = `### 3.1 fence指令`（`fm`/`pred`/`succ` 三段位域表 + `PRED_*`/`SUCC_*` 八个常量 + `|` 组合示例 `0x00C3` + `fm` 取值表 + 保留⇒ILLI 两条）＋ `### 3.2 LR-SC指令`（`<lr|sc>.<b|w|t|o>.<nn|an|nr|ar>` 24 条汇编示例、宽度缩写、`nn/nr/an/ar` 语义、按宽度自然对齐⇒MALIGN、保留机制段）；其后的 `## 4. SRAM块传输指令`（`cfxld`/`cfxst`）**不迁**。
  2. `spec/SimRISC-12` 册头第 4 行：`> **分类：待定 [deferred]**（27 条）— cfxld/cfxst/fence/lr.*/sc.*`；**27 = 2（`cfxld`/`cfxst`）+ 1（`fence`）+ 12（`lr.*`）+ 12（`sc.*`）**。本册迁 **25** 条（`fence` + 24 条 `lr/sc`）⇒ 余 **2** 条仍 deferred。
  3. `spec/SimRISC-11-其它.md`（176 行）现有章节：§1 汇编速查（生成区）、§2 合法性检查（生成区，现为「（本章无适用规则）」）、§3 占位指令（`swym`）、§4 非法指令、§5 特权指令、附录。册头第 4 行：`> **分类：其它**（5 条）— cfx2rc/cfx2rd/escape/swym/trap`。
  4. **生成器结构硬约束（关键，决定了本册的做法）**：`tools/llvm/gen_asm_list.py` 与 `tools/spec/gen_legality_list.py` 共用 `classify()` + `CLASS_TO_SPEC`，**一册 ⇔ 一分类**（`_section_content()` 固定输出 `### 1.1`；`check_asm_list_consistency.py` 按分类整块比对）。⇒ **不能**把两个分类映射到同一册（后写者覆盖前块）。故迁移生成区的唯一自洽改法 = **`classify()` 的「待定」分支收窄为 `cfxld`/`cfxst`**，`fence` 与 `lr.*`/`sc.*` 落入既有 `其它` 分支（`gen_asm_list.py` 里已有 `lr_/sc_` → `其它` 的兜底行，`fence` 落到末行兜底 ⇒ 同为 `其它`）。
  5. **静态文案陷阱（门控不会报，必须手改）**：`tools/llvm/gen_asm_list.py` 生成 `contract-asm-list.md` 的册头两条静态句——「**分章**：… / **deferred**（原「待定」；暂不归类：`cfxld`/`cfxst`/`fence`/`lr.*`/`sc.*`）」与「**范围与状态**：… 其余 `{n_m1}` 条为 `scope: m1`」。迁走后 `deferred` 只剩 2 条而 `scope: excluded` 仍 27 条，「其余 = m1」变成**假命题**；须同笔订正（`check-asm-list-drift` 只比生成器 ↔ 生成物，两边同错仍绿 ⇒ 靠本册验收兜住）。
  6. `check_numbering` 要求 `##` 编号**连续**：`SimRISC-12` 删 §3 后，原 `## 4. SRAM块传输指令` **必须重编为 `## 3.`**。
  7. `check_spec_refs` 只审计 `.tao/contracts/contract-*.md`：`contract-isa.md §14` 现有多处 `[SimRISC-12 §fence指令]`、`[SimRISC-12 §LR-SC指令]`；迁走后这两类引用**悬空** ⇒ 必须把引用文本改指 `SimRISC-11`（**只改指针，正文语义一字不动**）。`[SimRISC-12 §SRAM块传输指令]` **保持不动**。
  8. **`contracts/opcodes.yaml` 的 `spec_cite` 不在本册**：25 条记录仍写 `SimRISC-12 §fence指令`/`§LR-SC指令`（生成器 `tools/spec/generate_opcodes.py::S12_FENCE/S12_LRSC` 硬编码），改它须重生成 `contracts/opcodes.yaml` ⇒ **本册按派单边界不改 `contracts/`**，登记为遗留（见「不留白的边界」）。
  9. 只读锁：`manifests/spec-readonly.lock.toml` 覆盖 `SimRISC-11`（`80a10eda…`）与 `SimRISC-12`（`53418495…`），改册同笔须重算（`docs/Process-06 §5`）。

## 用户授权（`spec/` 改动，逐字）

> 「**把 原子指令 从SimRISC-12移动到SimRISC-11**」（2026-10-21，经主会话转达）
>
> **授权范围** = 上述「原子指令」章（`fence` + `lr/sc`）**原样迁入** `SimRISC-11` 及其**必需的机械同步**（`SimRISC-11`/`SimRISC-12` 两册正文与生成区、册头计数、附录变更记录、只读锁 `sha256`、`spec/README.md` 分册职责一句、生成器分类映射与其静态文案、`.tao/contracts/contract-isa.md` 的引用文本、`.tao/knowledge/MEMORY.md` 的章节指针）。**不含**任何语义/编码/命名改动，**不含** `contracts/**`（机器可读数据）与 `.tao/archive/**`。

## 目标

在不改**任何**语义与编码的前提下，把「原子指令」章从 12 号册搬到 11 号册并让规范面门控全绿：

1. **正文**：`SimRISC-12 §3` 整章（§3.1 `fence指令`、§3.2 `LR-SC指令`）**逐字**迁至 `SimRISC-11` 新 `## 6. 原子指令`（`### 6.1 fence指令`、`### 6.2 LR-SC指令`；**标题文本不变**，只改前导编号），`SimRISC-12` 删除该章、原 §4 重编为 §3。
2. **生成区**：`classify()` 收窄 ⇒ `fence` + 24 条 `lr/sc` 的汇编速查/合法性检查随分类落到 `SimRISC-11`（§1.1 其余 5 条 ⇒ **30 条**；§2 出现 `scope: excluded（decode ILLI）` 25 条），`SimRISC-12` 只剩 `cfxld`/`cfxst`（§1.1 **2 条**｜deferred）。
3. **计数与列表**：两册册头「分类」行、`SimRISC-12` 的 deferred 表述、`contract-asm-list.md` 册头两句文案同步为真。
4. **指针**：活指针全部改指新位置（`contract-isa.md` 引用文本、`MEMORY.md` 三处、`spec/README.md` 分册职责）。
5. **只读锁**：两册 `sha256` 同笔重算 + 授权注记。

## 接口规范

- **输入（真源）**：
  - `spec/SimRISC-12-待定.md`（迁移源，`master` 版本 = `git show master:spec/SimRISC-12-待定.md`）；
  - `spec/SimRISC-11-其它.md`（迁入目标）；
  - `contracts/opcodes.yaml`（**只读**：25 条 `spec_cite ∈ {SimRISC-12 §fence指令, SimRISC-12 §LR-SC指令}` 的 `id` 集合 = 集合不变式的**独立 oracle**）；
  - `tools/llvm/gen_asm_list.py`（`classify()`/`CLASS_TO_SPEC`/`SECTION_BADGES`/册头文案）、`tools/spec/gen_legality_list.py`（复用 `classify`）。
- **输出**：
  1. `spec/SimRISC-11-其它.md`（新增 `## 6.` + 册头第 4 行 + §1/§2 生成区 + 附录 `0.5.5-rc` 一条）；
  2. `spec/SimRISC-12-待定.md`（删 §3、`## 4.`→`## 3.`、册头第 4 行、§1/§2 生成区、附录 `0.5.5-rc` 一条）；
  3. `tools/llvm/gen_asm_list.py`（`classify()` 分支收窄 + 注释 + `contract-asm-list.md` 册头两句文案）；
  4. `.tao/contracts/contract-asm-list.md`（**重生成**，禁手改）、`.tao/contracts/contract-isa.md`（**仅引用文本** `[SimRISC-12 §fence指令]`/`[SimRISC-12 §LR-SC指令]` → `[SimRISC-11 §…]`）；
  5. `.tao/knowledge/MEMORY.md`（3 处章节指针）、`spec/README.md`（`SimRISC-11`/`SimRISC-12` 分册职责各一句）；
  6. `manifests/spec-readonly.lock.toml`（两册 `sha256` + 授权注记）；
  7. `.work/evidence/SPEC-153t/**`（default + `--inject`）、日志 `.work/log/spec/SPEC-153t/**`。
- **约束**：
  - **语义/编码/命名一字不改**：正文迁移只允许改标题前导编号；`diff` 归一化后必须**逐字节相等**。
  - **不改** `contracts/**`（`opcodes.yaml`/`legality_rules.yaml`）、`.tao/archive/**`、`.tao/adr/**`、`.tao/tasks/**`（含已完成册）、`components/**/changelog.md`、`.tao/knowledge/issues.yaml` 既有 `notes`（历史不改；新事实只进本册完成区）。
  - **生成区禁手改**：§1/§2 只由生成器产出；改完必须 `--verify` / `check-*` 绿。
  - `fence`/`lr`/`sc` 的 `scope: excluded`（decode ILLI）**身份不变**——本册只改「住哪一册」，不改范围语义。

## 做（顺序）

### 阶段 0：开工前置（不满足 ⇒ 停）

1. `git branch --show-current` = 本任务分支、`git status --porcelain -uall` 干净；`git rev-parse HEAD` 记入完成区。
2. 现场复核「现场事实」1–9：`grep -n` 取 `SimRISC-12` §3/§4 行范围、册头两行原文、`classify()` 现状、`contract-isa.md §14` 的引用命中数（`grep -c`）、两册锁 `sha256`；输出留 `.work/log/spec/SPEC-153t/**`。
3. **独立 oracle 快照**：用 `contracts/opcodes.yaml` 派生 25 个 `id`（按 `spec_cite` 过滤）存 `.work/log/spec/SPEC-153t/**`；与 `git show master:spec/SimRISC-12-待定.md` §1 表内 27 行做集合比对，**先证「25 + 2 = 27」再动笔**。

### 阶段 A：生成器分类（先改代码，后动正文）

1. `tools/llvm/gen_asm_list.py::classify()`：把「待定」分支收窄为 `if m in ("cfxld", "cfxst"): return "待定"`（注释改为「待定 = SRAM 块传输（`cfxld`/`cfxst`），用户裁定 2026-10-21 原子指令归 `其它`」），其余不变；`fence` 与 `lr.*`/`sc.*` 由既有兜底落 `其它`。
2. 同文件册头文案（生成 `contract-asm-list.md` 的两条静态句）：`deferred` 列举改为「暂不归类：`cfxld`/`cfxst`」；「范围与状态」句补明 `scope: excluded` 仍 27 条（其中 25 条在「其它」章 ⇒ 不得再写「其余 = m1」这种失真表述）。
3. 先跑 `python3 tools/llvm/gen_asm_list.py --embed-spec`（此时生成区会**先**按新分类落位）——确认无异常后再进 B。

### 阶段 B：正文迁移（逐字）

1. 从 `git show master:spec/SimRISC-12-待定.md` 取 §3 整块（`## 3. 原子指令` 起、`## 4. SRAM块传输指令` 前止），**只**把 `## 3.`→`## 6.`、`### 3.1`→`### 6.1`、`### 3.2`→`### 6.2`。
2. 追加到 `spec/SimRISC-11-其它.md` 的 §5 之后、`---`/附录之前（保持既有的「空行 + `---`」结构）。
3. `spec/SimRISC-12-待定.md` 删除该块；`## 4. SRAM块传输指令` → `## 3. SRAM块传输指令`（其内部若有 `§4`/`§3.x` 互指，逐条同步）。
4. 两册册头第 4 行：`SimRISC-11` → `（30 条）— cfx2rc/cfx2rd/escape/swym/trap/fence/lr.*/sc.*`；`SimRISC-12` → `（2 条）— cfxld/cfxst`（条数**现场派生**，不写死）。
5. 两册附录 `0.5.5-rc` 各加**一条**（**不带任务号/ADR 号**）：
   - 11：「新增「原子指令」章（`fence` / `lr`·`sc`），由 `SimRISC-12` 原样迁入；汇编速查与合法性检查生成区随之纳入（分类由「待定」改为「其它」）。」
   - 12：「「原子指令」章（`fence` / `lr`·`sc`）迁至 `SimRISC-11`；本册仅余 SRAM 块传输（`cfxld`/`cfxst`），deferred 记 27 → 2；原 §4 重编为 §3。」

### 阶段 C：生成区重生成与自查

1. `python3 tools/llvm/gen_asm_list.py --embed-spec`（§1 + `contract-asm-list.md`）、`python3 tools/spec/gen_legality_list.py --apply`（§2）。
2. 自查：`--verify`、`check-asm-list-consistency`、`check-asm-list-drift`、`check-legality-drift`、`check-legality-invariants` 逐个 rc=0。
3. 人工核 §1/§2 块内**行数现场统计**（11 册 30 行、12 册 2 行；§2 分别 25 / 2 条）——写进完成区。

### 阶段 D：活指针同步

1. `.tao/contracts/contract-isa.md §14`：`[SimRISC-12 §fence指令]`、`[SimRISC-12 §LR-SC指令]` → `SimRISC-11`（`sed` 逐处，禁批量误伤 `§SRAM块传输指令`）；改后 `grep -c "SimRISC-12 §fence\|SimRISC-12 §LR-SC"` 必须为 **0**。
2. `.tao/knowledge/MEMORY.md` 3 处（`fence SBZ`、`M1/M2 排除口径`、章节订正段）改指 `SimRISC-11`。
3. `spec/README.md` 分册职责两行：`SimRISC-11` → 「其它类指令（占位/非法/特权/原子）」、`SimRISC-12` → 「待定类指令（SRAM 块传输 `cfxld`/`cfxst`）」。
4. `grep -rn "SimRISC-12 §3\|SimRISC-12 §fence\|SimRISC-12 §LR-SC"` 在全仓（除 `.tao/archive/**`、`.cache/**`、`.work/**`）应 **0 命中**——历史记录（ADR/任务书/changelog/issues 旧 notes）**豁免**，命中须逐条说明「历史，不改」。

### 阶段 E：只读锁

1. 两册 `sha256sum` 重算；`manifests/spec-readonly.lock.toml` 对应条目更新 + 上一条注释行写明「2026-10-21（用户原话「把 原子指令 从SimRISC-12移动到SimRISC-11」授权）：§3 原子指令整章原样迁入 `SimRISC-11 §6`；sha256 同笔重算」。
2. `make check-spec-readonly` rc=0（21 册）。

### 阶段 F：证据

1. `.work/evidence/SPEC-153t/**`：① 全量门控（见验收 5）；② **集合不变式**；③ **正文逐字比对**；④ 计数/册头；⑤ 指针 0 悬空。脚本必须带 `--inject`（注入可达 FAIL，`cp` 备份 + `md5` 还原，**禁** `git checkout/restore/stash`）。
2. 日志落 `.work/log/spec/SPEC-153t/**`；完成区贴真实命令 + rc。

## 验收标准（逐条可机械判）

1. **改动面**：`git diff --stat master -- spec/` 只含 `SimRISC-11-其它.md`、`SimRISC-12-待定.md`；`git diff --stat master` 不含 `contracts/**`、`.tao/archive/**`、`.tao/adr/**`、`.tao/tasks/**`、`components/**`。
2. **正文逐字迁移**：`git show master:spec/SimRISC-12-待定.md | sed -n '/^## 3\. 原子指令/,/^## 4\. /p'`（去掉末行）经 `sed 's/^## 3\./## 6./;s/^### 3\.1/### 6.1/;s/^### 3\.2/### 6.2/'` 后，与 `spec/SimRISC-11-其它.md` 的 `## 6.` 段**逐字节 `diff` 为空**（rc=0）。
3. **集合不变式（独立 oracle）**：令 `S12_before` = `master` 版 `SimRISC-12` §1 表的 `id` 集合（27）、`O` = `contracts/opcodes.yaml` 中 `spec_cite ∈ {SimRISC-12 §fence指令, SimRISC-12 §LR-SC指令}` 的 `id` 集合（**25**）、`S11_after` = 迁后 `SimRISC-11` §1 表内与 `O` 同名 mnemonics 的 `id`、`S12_after` = 迁后 `SimRISC-12` §1 表 `id` 集合。断言：`S11_after == O`、`S12_after == S12_before − O`、`S11_after ∩ S12_after == ∅`、`|S12_before| = |S11_after| + |S12_after|`（27 = 25 + 2）；逐 `id` 打印差集（空才算过）。
4. **计数/列表为真**：`SimRISC-11` §1.1 = **30 条**、§2 `decode ILLI` = **25 条**；`SimRISC-12` §1.1 = **2 条**、§2 = **2 条**；两册册头第 4 行条数与表内行数**现场比对一致**；`SimRISC-12` 全文不再出现 `fence`/`lr.`/`sc.` 的指令行（历史附录段除外，须 `grep -n` 逐条说明）。
5. **门控全绿（rc 现场记录）**：`check-asm-list`、`check-asm-list-drift`、`check-legality-drift`、`check-legality-invariants`、`check-spec-codeblocks`、`check-asm-prose`、`check-scope`、`check-spec-readonly`、`check-spec-refs`、`check-spec-drift`、`check-numbering`、`check-spec-changelog`、`check-knowledge-refs`、`check-no-residue`、`check-milestones-fresh` + **`make check`（L1，一次）rc=0**。
6. **指针无悬空**：`check_spec_refs.py` 输出「失败: 0」；`grep -c "SimRISC-12 §fence\|SimRISC-12 §LR-SC"` 在 `.tao/contracts/*.md` = 0；`MEMORY.md`/`README.md` 的指向在 `SimRISC-11` 中可解析（`grep -n "^### 6.1 fence指令"`/`"^### 6.2 LR-SC指令"` 命中）。
7. **只读锁**：两册 `sha256` 与锁一致（`check-spec-readonly` 21 册 OK）；锁文件注释含授权原话。
8. **可达 FAIL ≥2（脚本 `--inject` 现场输出）**：① 临时删掉 `SimRISC-11` §1 表一行 `lr.w.nn` ⇒ 验收 3 的差集非空、rc=1；② 把 `SimRISC-12` 册头 `（2 条）` 改 `（27 条）` ⇒ 验收 4 比对 rc=1；③ 正文某段多一个空格 ⇒ 验收 2 的 `diff` 非空 rc=1。三例均须 `md5` 还原后回绿。
9. **证据脚本**：`.work/evidence/SPEC-153t/**` 下的 `run.sh` 全绿；`--inject` 三例均 FAIL 且还原。

## 独立 oracle（不从两册正文反推）

- **条目集合** ← `contracts/opcodes.yaml` 的 `spec_cite` 字段（机器数据，25 条；本册不改它）。
- **迁移前集合/正文** ← `git show master:spec/SimRISC-12-待定.md`（版本控制真源，非当前工作树）。
- **计数** ← 现场 `grep`/脚本统计（不写死 27/25/2/30 中的任何值）。

## 不留白的边界（写进完成区「遗留问题」）

1. `contracts/opcodes.yaml` 25 条 `spec_cite` 仍指 `SimRISC-12 §fence指令`/`§LR-SC指令`（生成器 `tools/spec/generate_opcodes.py::S12_FENCE/S12_LRSC` 硬编码）；改它须重生成 `contracts/`，**不在本册授权面** ⇒ 登记为遗留（建议随下次 `contracts/` 变更同笔改，无门控依赖，不阻断）。
2. `tools/qemu/generate_atomics_vectors.py`、`tools/testcases/generate_lit_vectors.py` 等**代码注释/向量 `# Source:` 头**仍写 `SimRISC-12 §3.x`——属**溯源注释**，改它要重生成向量（换编译/门控面），**不改**，逐条披露。
3. `.tao/adr/adr-0034*`、已完成任务书、`components/*/changelog.md`、`issues.yaml` 旧 `notes` 属**历史记录**，不改（历史即历史）。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
