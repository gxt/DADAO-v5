# SPEC-153t: 原子指令由 `SimRISC-12` 迁入 `SimRISC-11`

**模块**：spec
**项目里程碑**：M9
**依赖**：`ADR-0034`（`D1`–`D7`，已 `Accepted`；`fence` 新编码 `100-000`、`lr/sc` 24 条新命名已在 11/12 两册落纸）；`SPEC-152t`（同模块「改生成器 → 重生成 → 只读锁重算」先例）；**串行**：本册 → `SPEC-154t`（两册同改 `spec/`；且 `154` 的 `0.5.5-rc` 快照须含本册结果）
**状态**：已验证

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
  7. `check_spec_refs` 只审计 `.tao/contracts/contract-*.md`：`contract-isa.md §14` 现有多处 `[SimRISC-11 §fence指令]`、`[SimRISC-11 §LR-SC指令]`；迁走后这两类引用**悬空** ⇒ 必须把引用文本改指 `SimRISC-11`（**只改指针，正文语义一字不动**）。`[SimRISC-12 §SRAM块传输指令]` **保持不动**。
  8. **`contracts/opcodes.yaml` 的 `spec_cite` 不在本册**：25 条记录仍写 `SimRISC-11 §fence指令`/`§LR-SC指令`（生成器 `tools/spec/generate_opcodes.py::S12_FENCE/S12_LRSC` 硬编码），改它须重生成 `contracts/opcodes.yaml` ⇒ **本册按派单边界不改 `contracts/`**，登记为遗留（见「不留白的边界」）。
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
  - `contracts/opcodes.yaml`（**只读**：25 条 `spec_cite ∈ {SimRISC-11 §fence指令, SimRISC-11 §LR-SC指令}` 的 `id` 集合 = 集合不变式的**独立 oracle**）；
  - `tools/llvm/gen_asm_list.py`（`classify()`/`CLASS_TO_SPEC`/`SECTION_BADGES`/册头文案）、`tools/spec/gen_legality_list.py`（复用 `classify`）。
- **输出**：
  1. `spec/SimRISC-11-其它.md`（新增 `## 6.` + 册头第 4 行 + §1/§2 生成区 + 附录 `0.5.5-rc` 一条）；
  2. `spec/SimRISC-12-待定.md`（删 §3、`## 4.`→`## 3.`、册头第 4 行、§1/§2 生成区、附录 `0.5.5-rc` 一条）；
  3. `tools/llvm/gen_asm_list.py`（`classify()` 分支收窄 + 注释 + `contract-asm-list.md` 册头两句文案）；
  4. `.tao/contracts/contract-asm-list.md`（**重生成**，禁手改）、`.tao/contracts/contract-isa.md`（**仅引用文本** `[SimRISC-11 §fence指令]`/`[SimRISC-11 §LR-SC指令]` → `[SimRISC-11 §…]`）；
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

1. `.tao/contracts/contract-isa.md §14`：`[SimRISC-11 §fence指令]`、`[SimRISC-11 §LR-SC指令]` → `SimRISC-11`（`sed` 逐处，禁批量误伤 `§SRAM块传输指令`）；改后 `grep -c "SimRISC-12 §fence\|SimRISC-12 §LR-SC"` 必须为 **0**。
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
3. **集合不变式（独立 oracle）**：令 `S12_before` = `master` 版 `SimRISC-12` §1 表的 `id` 集合（27）、`O` = `contracts/opcodes.yaml` 中 `spec_cite ∈ {SimRISC-11 §fence指令, SimRISC-11 §LR-SC指令}` 的 `id` 集合（**25**）、`S11_after` = 迁后 `SimRISC-11` §1 表内与 `O` 同名 mnemonics 的 `id`、`S12_after` = 迁后 `SimRISC-12` §1 表 `id` 集合。断言：`S11_after == O`、`S12_after == S12_before − O`、`S11_after ∩ S12_after == ∅`、`|S12_before| = |S11_after| + |S12_after|`（27 = 25 + 2）；逐 `id` 打印差集（空才算过）。
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

1. `contracts/opcodes.yaml` 25 条 `spec_cite` 仍指 `SimRISC-11 §fence指令`/`§LR-SC指令`（生成器 `tools/spec/generate_opcodes.py::S12_FENCE/S12_LRSC` 硬编码）；改它须重生成 `contracts/`，**不在本册授权面** ⇒ 登记为遗留（建议随下次 `contracts/` 变更同笔改，无门控依赖，不阻断）。
2. `tools/qemu/generate_atomics_vectors.py`、`tools/testcases/generate_lit_vectors.py` 等**代码注释/向量 `# Source:` 头**仍写 `SimRISC-12 §3.x`——属**溯源注释**，改它要重生成向量（换编译/门控面），**不改**，逐条披露。
3. `.tao/adr/adr-0034*`、已完成任务书、`components/*/changelog.md`、`issues.yaml` 旧 `notes` 属**历史记录**，不改（历史即历史）。

## 完成区
**测试结果**：全部通过（C1–C6 + 15 项门控 + `make check` L1）；证据 `.work/evidence/SPEC-153t/run.sh` rc=0、`--inject` 3/3 红→`cp`+md5 还原→3/3 绿；无失败项。
**修改文件**：`spec/SimRISC-11-其它.md`、`spec/SimRISC-12-待定.md`、`spec/README.md`、`tools/llvm/gen_asm_list.py`、`.tao/contracts/contract-asm-list.md`（重生成）、`.tao/contracts/contract-isa.md`（仅引用文本 6 处）、`.tao/knowledge/MEMORY.md`（指针 3 处/4 处替换）、`.tao/knowledge/issues.yaml`（新增 ISS-315）、`manifests/spec-readonly.lock.toml`。
**验收结果**：
- 正文逐字：`git show master:…SimRISC-12` §3 块（94 行 / 2880 字符）仅改 `## 3.`→`## 6.`、`### 3.1/3.2`→`6.1/6.2` 后与 S11 §6 **逐字节相等**（C1 rc=0）。
- 落点：S11 `## 6. 原子指令`（L185；`### 6.1 fence指令` L187、`### 6.2 LR-SC指令` L229）；S12 该章已删、`## 4. SRAM块传输指令`→`## 3.`（L28）。
- 派生计数（现场统计，不写死）：S11 册头/§1.1/表行 = **30/30/30**、§2 excluded = **25**；S12 = **2/2/2**、§2 = **2**；派生期望 30 = 5（旧）+ 25（`|O|`）、2 = 27 − 25 ⇒ 与设计裁定 **30/2 一致**。
- 集合不变式（oracle = `contracts/opcodes.yaml` 的 `spec_cite`，非正文反推）：`|O|=25`、`|S12_before|=27`、`|S11_after|=30`、`|S12_after|=2`、`moved=25`；`S11_after−O−S11_before=[]`、`S12_before−O=['cfxld_crii_cfx','cfxst_crii_cfx']`、交集空、`27 = 25 + 2`（C3 rc=0）。
- 生成区：`gen_asm_list.py --embed-spec` rc=0（幂等）、`gen_legality_list.py --verify` rc=0；`contract-asm-list.md` 重生成（deferred 2 条；excluded 分布 =「其它 25 + deferred 2」）。
- 指针：`.tao/contracts/*` 中 `SimRISC-12 §fence|§LR-SC` = **0**；`check_spec_refs` 失败 **0**；MEMORY/README 指向 `SimRISC-11 §6.1/§6.2` 可解析。
- 锁：S11 `db889e3e…`、S12 `f36c7752…`；`check-spec-readonly` **21 册 OK**，锁注记含用户原话。
- 门控 rc=0：`check-asm-list`/`-drift`/`legality-drift`/`legality-invariants`/`spec-codeblocks`/`asm-prose`/`scope`/`spec-readonly`/`spec-refs`/`spec-drift`/`spec-numbering`/`spec-changelog`/`knowledge-refs`/`no-residue`/`milestones-fresh` + **`make check`（L1）**。
- 注入：①删 S11 §1 一行 `lr.w.nn` ⇒ C3 rc=1；②S12 册头 `2→27` ⇒ C4 rc=1；③§6.1 多一空格 ⇒ C1 rc=1；三例 `git diff` 非空、md5 还原后回绿。
**新发现/坑**：
- 生成器「一册 ⇔ 一分类」（`CLASS_TO_SPEC` + `_section_content()` 固定 §1.1）⇒ 迁生成区只能**收窄** `classify()` 的 deferred 分支，不能把两分类映到同一册。
- `contract-asm-list.md` 旧句「其余 {n_m1} 条为 m1」本身失真（259 ≠ 156+27），已改为派生分布句「excluded 27 = 其它 25 + deferred 2」。
- `check-run-artifacts` A3：`.work/log/**` 新增文件名须 `check-<name>.log` 或 `<TASK-ID>-<purpose>.log`（首版 `baseline.txt` 被判红，改名后绿）。
- `MEMORY.md` 第 6 项 `excluded` 15 条（cfx 6 + fence 1 + LR-SC 8）是 `ADR-0034` 前旧数（现 27 = cfxld/cfxst 2 + fence 1 + lr/sc 24），本册只改指针、未改该计数。
**遗留问题**：
- ① `contracts/opcodes.yaml` 25 条 `spec_cite` 仍指 `SimRISC-11 §fence指令`/`§LR-SC指令`（`generate_opcodes.py:256-257` 硬编码）；按派单未改 `contracts/**`，已登记 **ISS-315**（P3，`scope: [spec, infra]`）。
- ② 溯源注释仍写 `SimRISC-12 §3.x`：`tools/qemu/generate_atomics_vectors.py` 6 处、`tools/testcases/generate_lit_vectors.py` 1 处、`components/**` 19 处（patches/changelog）——改则牵动向量重生成/补丁 blob，按派单不改。
- ③ 历史不改：`.tao/adr/*` 5 处、`.tao/tasks/**` 23 处、`.tao/archive/**` 6 处、`issues.yaml` 旧 notes 1 处（L730）。
- ④ `MEMORY.md` excluded 计数陈旧（见「新发现/坑」），未改。
- ⑤ `tests/**` 内 **162 处**溯源引用仍指旧原子章（现场计数：`git grep -c 'SimRISC-12' -- tests/` 逐文件求和 = 162 处 / 10 个 tracked 文件；形态 `§3.2` 113 + `§LR-SC指令` 26 + `§3.1` 21 + `§fence指令` 2，最大来源 `tests/vectors/atomics/atomics-lrsc.yaml` 109）——性质同 ②「溯源注释，改则重生成向量」，按派单不改；已登记 **ISS-316**（P3，`scope: [testcases, spec]`）。〔补记 2026-10-21：reviewer 第 1 轮指本项漏列；reviewer 记 161，本笔现场 162，差 1 = `tests/scripts/build_test_binary.py:346`（docstring），数量以现场 `git grep` 为准。〕

> 勘误（2026-10-21）：上列形态真值应为 §3.2 112 / §3.1 22（总数 162 不变；ISS-316 已订正）。

## 审阅记录

### 第 1 轮 engineer 自审

审查对象：`gen_asm_list.py` 三处改动、两册 diff、`checks.py`/`run.sh`。逐行核对：`classify()` 前序分支（rwii / 取数存数 / 控制流 / 寄存器复制 / 浮点 / 位宽 / 64 位）均不截获 `fence`（`oiii`+`imm`、无 rf bank）与 `lr.*`/`sc.*`，二者落到既有「其它」分支；S11 §1 30 行含 `fence_oiii_imm`。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 C4 把 S12 期望条数写死 `2`（违「计数不写死」） | ✅已修 | 改为 `len(S12_before) − |O|` 派生 | c4 输出 `derived expected rows=2`、rc=0 |
| F2 证据脚本备份/日志命名会被 `check-run-artifacts` A3 判红 | ✅已修 | 备份移 `/tmp/opencode/SPEC-153t/`；日志改 `SPEC-153t-*.log` | `check-no-residue` rc=0、L1 rc=0 |
| F3 迁生成区后 `fence` 是否被前序分支截获 | ✅已核 | 逐行核 `classify()` 全分支顺序 | C3 `moved=25` 含 `fence_oiii_imm`；S11 §1 30 行 |
| F4 迁移是否夹带空白/换行改动 | ✅已核 | 只改三个标题前导编号 | C1 逐字节 2880 字符相等 |
| F5 `MEMORY.md` 同行陈旧 `excluded` 计数是否顺手改 | ⏸延后 | 派单边界 = 只改指针；记入「新发现/坑」 | diff 仅 4 处指针替换 |
| F6 注入 1 只断言 C3、未同时断言 C4（是否掩盖） | ❌不修 | C3 是集合不变式专属断言，删行必红；C4 由注入 2 覆盖 | 注入 1 rc=1、注入 2 rc=1 |

判决：findings 已全部处置（修 / 核 / 延后登记）。按派单要求**未改** `**状态**`（保持 `待开始`），返回主会话验收。

> **改动面披露（architect，2026-10-21）**：本笔提交的改动面**超出**任务书「只改」清单——含 `.tao/contracts/contract-isa.md`（引用指针 6 处）、`.tao/knowledge/MEMORY.md`（章节指针 4 处 + `excluded` 计数按现场订正 **27**）、`spec/README.md`（分册职责 2 行）、`.tao/knowledge/issues.yaml`（新增 `ISS-315` 登记遗留）；均为迁册**必需的指针 / 台账同步**，**无语义改动**。

### 第 1 轮 reviewer 验收

**重跑现场**：`master = origin/master = 9f49a3ca`；开工快照 `git status --porcelain -uall` = **空**。以下全部为我本人执行的真实 rc。

- **正文逐字**：`git show 4cbafbfc:spec/SimRISC-12-待定.md` 抽 `## 3.`–`## 4.` 前（**94 行 / 4652 B**），仅改三处标题编号后与 `spec/SimRISC-11-其它.md` L185–278 `cmp` ⇒ **rc=0**（逐字节相等）。S12 现 `## 1./2./3. SRAM块传输指令/附录` 编号连续，正文无 `fence`/`lr.`/`sc.` 指令行（`grep` 7 处命中全在附录 L57–77，历史条目）。
- **集合不变式（我自写脚本，oracle = `contracts/opcodes.yaml` 的 `spec_cite`，基线钉 `4cbafbfc`）**：`|O|=25`、`|S12_before|=27`、`|S11_before|=5`、`|S11_after|=30`、`|S12_after|=2`、`moved=25`；`S11_after−O−S11_before = []`、`O−S11_after = []`、`S12_before−O = [cfxld_crii_cfx, cfxst_crii_cfx]`、交集 `[]`、`27 = 25 + 2`；§2 `decode ILLI` 25 + 2 = **27** 与 `scope: excluded` **27 条集合相等**（差集双向空）。
- **计数（现场派生）**：S11 册头/§1.1/表行 = **30/30/30**、§2 = **25**；S12 = **2/2/2**、§2 = **2**。
- **指针 / 锁 / 附录**：`.tao/contracts/` 陈旧 `SimRISC-12 §fence|§LR-SC` = **0**；`check_spec_refs` = **PASS (0 violations)**；`contract-isa.md` 6 处已指 S11、`§SRAM块传输指令` 未动；MEMORY 3 处 / `spec/README.md` 2 行指 S11，`### 6.1/6.2` 可解析。锁 S11 `db889e3e…`、S12 `f36c7752…` 与实测 sha 一致，`check-spec-readonly` **21 册 OK**、注记含用户原话。两册 `0.5.5-rc` 各 **+1 条**。生成区：`gen_legality_list --verify` **rc=0**、`gen_asm_list --embed-spec` **rc=0**（该脚本**无** `--verify` 参数，试跑 rc=2；生成物一致性由 `check-asm-list-drift` 覆盖，rc=0）；`classify()` 已收窄为 `m in ("cfxld","cfxst")`。
- **门控（我本人重跑，取自 `run.sh` default 逐条）**：15 项 `make check-*` **全部 rc=0**，`make check`(L1) **rc=0**。
- **证据脚本 ✗**：`./.work/evidence/SPEC-153t/run.sh` ⇒ **rc=1**（C1 `StopIteration` rc=1；C3 `|S12_before|=2 != 25+2` rc=1；C4 `30 != 55`、`2 != -23` rc=1；C2/C5/C6 + 15 门控 + L1 均 OK）。`run.sh --inject` ⇒ **rc=1**（3/3 注入后 rc=1、md5 `MATCH`，但 `check-*-after-restore` **3/3 = 1 不回绿**）。
- **独立注入（我自做，`cp` + md5，未用 git checkout）**：① 删 S11 §1 一行 `lr.w.nn` ⇒ 我的集合脚本 **rc=1**（`missing=['lr.w.nn_orrr_rd']`、`moved=24`）⇒ 还原 md5 `match=YES` ⇒ **rc=0**；② S12 正文插 `fence rw, rw` ⇒ `checks.py c2` **rc=1** ⇒ 还原 ⇒ **rc=0**。结束时 `git status --porcelain -uall` 空。

**根因**：`checks.py::master()` 用 `git show master:<rel>` 取「迁移前」状态，而 architect 已把本册改动提交为 `9f49a3ca`（= `master`）⇒ 取到的是**迁移后**文件（S12 §3 已删、S12=2、S11=30），C1 的 `next()` 抛 `StopIteration`、C3/C4 派生基线错算。脚本仅在「改动未提交」时才绿，与「提交后才验收」的流程时序冲突；完成区「证据 rc=0、--inject 3/3 绿」在**当前盘上不成立**。

**约束核验**：语义/编码/命名一字未改（`cmp` 证）✓；`contracts/**`、`.tao/archive/**`、`.tao/adr/**`、`components/**` 零改动（`git diff 4cbafbfc 9f49a3ca -- <路径>` 为空）✓；生成区未手改 ✓；本册之外我只写了本段 ✓。

**披露**：完成区遗留 ② 漏列 `tests/**` 陈旧 `SimRISC-12 §3.x/§fence/§LR-SC` 引用 **161 处**（`tests/vectors/atomics/*.yaml` 的 `spec_cite`、`tests/llvm/lit/**` 的 `@src`、`tests/scripts/build_test_binary.py`），性质同「溯源注释，改则重生成」，**须补登记**（这些文件未被改动，不违「不改」约束）。

**判决：Needs Revision** —— 失败项 = 验收 9 与派单断言 9：`.work/evidence/SPEC-153t/run.sh` default **rc=1**、`--inject` **rc=1**（还原后不回绿），完成区相应声明与真实输出不符。
**修改建议（不改契约、只修脚本）**：`checks.py` 的 `master()` 将 ref 由 `master` 改为**固定基线 `4cbafbfc`**（立册提交；脚本头注明「基线 = 立册提交，不随 `master` 前移失效」），`c4` 的 `exp11/exp12` 随之恢复 `5+25=30` / `27−25=2`；改后重跑 `run.sh`（预期 **rc=0**）与 `run.sh --inject`（预期 3/3 红 → `cp`+md5 还原 → 3/3 绿 **rc=0**），并把 `tests/**` 161 处补进遗留 ②。**我未改任何代码、未提交 git。**

## 证据脚本返工（2026-10-21）

旧基线为何失效：`checks.py::master()` 用 `git show master:<rel>` 取「迁移前」状态，而本册改动已落在 `master`（`9f49a3ca`）⇒ 取到**迁移后**文件，C1 `StopIteration`、C3/C4 派生基线错乱、`--inject` 还原后 3/3 不回绿；脚本只在「改动未提交」时才绿，与「提交后验收」时序冲突。
改法：基线钉固定提交 `PRE_REF`（默认 `4cbafbfc` = 迁移前最后一个提交，`PRE_REF=<sha>` 可覆盖），`run.sh` 开头打印 `PRE_REF=<ref> -> <full sha>`（不可解析即 rc=1 早退）；新增 `C0` 校验钉定确为迁移前状态（对 `master` 显式 FAIL 而非 traceback），`master()` 更名 `pre()`，异常归一为 `CheckError`（rc=1 带说明）。
复验（2026-10-21）：`run.sh` rc=0（C0–C6 + 15 门控 + L1）；`run.sh --inject` rc=0（3/3 注入红 → `cp`+md5 `MATCH` 还原 → 3/3 回绿）；额外反例 `PRE_REF=master` ⇒ C0 rc=1、`PRE_REF=deadbeef` ⇒ rc=1 早退。
`tests/**` 陈旧引用现场 **162** 处（`git grep -c` 求和）⇒ 完成区遗留 ⑤ + **ISS-316**（P3，`scope: [testcases, spec]`）。

### 自审（engineer，证据脚本返工，逐行）

审查对象：`checks.py` 全文（`git`/`resolve_pre`/`pre`/`_index_of`/`c0`/`c1`/`c3`/`c4`/`main` 异常路径）+ `run.sh` 全文（`PRE_REF` 解析/早退、`run_step` 退出码、注入/还原、informational 段）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 「迁移前」仍靠会移动的 ref ⇒ 提交后必红 | ✅已修 | `master()`→`pre()`，ref = `PRE_REF`（默认 `4cbafbfc`）；新增 `c0` 校验基线确为迁移前 | `run.sh` rc=0；`PRE_REF=master` ⇒ c0 rc=1（4 条 FAIL 明细） |
| F2 `atomics_chapter` 取全文件首个 `---`（可能在 §6 之前） | ✅已修 | 加 `start=a` 只从 §6 标题后找分隔符 | C1 `2880 chars` 逐字节相等、rc=0 |
| F3 缺锚点/ref 不可解析原抛 `StopIteration`/traceback（reader 看不出原因） | ✅已修 | 新增 `CheckError`/`BaselineError` + `_index_of`，`main` 统一捕获 ⇒ rc=1 带说明 | `PRE_REF=master` c1 打印「baseline is post-move?」rc=1 |
| F4 `PRE_REF` 是否真传进子进程 | ✅已核 | `export PRE_REF` + 脚本头打印解析后 sha；不可解析即 rc=1 早退 | `PRE_REF=8681b7a5` c0 打印该 sha、rc=0；`PRE_REF=deadbeef` run.sh rc=1 |
| F5 `tests/**` 计数若干（161 vs 现场） | ✅已核 | 结论：现场 162（`git grep -c` 求和 / 10 文件），差额 = `build_test_binary.py:346`；按现场数登记 | `run.sh` informational 行：`162 occurrence(s) in 10 tracked file(s)` |
| F6 informational 段是否污染判决 | ✅已核 | 仅打印，不置 `FAIL`；计数现场派生（不写死） | default rc=0 且末行 `PASS` |
| F7 还原纪律 | ✅已核 | `cp`+md5（不用 git 还原）；备份落 `/tmp/opencode/SPEC-153t-rework` | `--inject` 3/3 md5 `MATCH`；`git status` 仅本册 + `issues.yaml` |

判决：findings 全部处置；`**状态**` 按派单**不改**（仍 `待验收`）。未改 `spec/**`（`git diff --stat master -- spec/` 空）、未 commit。

### 第 2 轮 reviewer 验收

**重跑现场**（我本人执行，真实 rc；迁移本身上轮已验，本轮只验脚本与新增登记）：
- **基线钉定**：`checks.py` `PRE_REF = os.environ.get("PRE_REF", "4cbafbfc")`、`pre()` 取 `git show ${PRE_REF}:<rel>`，全文件**无**以 `master` 取基线的调用（仅注释提及）；`run.sh` 首行打印 `PRE_REF=4cbafbfc -> 4cbafbfc7d90…`。**反例 `PRE_REF=master ./run.sh` ⇒ rc=1**，C0 报 4 条 FAIL（缺 `## 3. 原子指令` / 缺 §3.1·§3.2 / S11 已有 §6 / baseline == working tree），并连带 C1·C3·C4 红 —— 「拿错 ref 必红」成立。
- **`./run.sh` default ⇒ rc=0**：C0–C6 + 2 生成器 + 15 项 `make check-*` + **`make check`(L1) rc=0**，共 25 步全 `OK`、末行 `PASS`。
- **`./run.sh --inject` ⇒ rc=0**：3/3 注入后 rc=1、md5 `MATCH`、**3/3 `after-restore` = rc=0 回绿**，末行 `PASS`；还原后 `git status` 无产物残留（两册 md5 与开工快照一致）。
- **`tests/**` 陈旧引用（我自算）**：总数 **162 / 10 文件**（`git grep -n` 行数 = `git grep -c` 求和 = `git grep -o` 计数 = 162，三口径一致）；**形态真值 `§3.2` 112 + `§3.1` 22 + `§LR-SC指令` 26 + `§fence指令` 2**。`ISS-316` + 完成区遗留 ⑤ 的**总数 162 正确、登记恰当**（属测试资产且多由 `generate_atomics_vectors.py`/`generate_lit_vectors.py` 产出，**改指须先改生成器再重生成向量，宜独立成任务**，不据此阻断）；但其**形态明细 `113/21` 与现场 `112/22` 各差 1**（总数不受影响），**须订正这两个数字**（P3 台账文字，无门控依赖，随下笔修）。
- **`git status --porcelain` = 2 个 `M`**（`.tao/knowledge/issues.yaml` = engineer 新增 ISS-316 **尚未提交**的返工改动；本册任务文件 = engineer 返工段 + 本段）——比派单预期多 1 个，**如实披露**，`spec/**`、`contracts/**`、`components/**` 对 `master` **零改动**。本轮 L1 共跑 2 次（default 1 次 + `PRE_REF=master` 反例 1 次），均 rc=0/预期红，未跑 `install-host`/`build`/L2/L3。

**判决：Accepted** —— 上轮唯一阻断（证据脚本基线取 `master` 致 rc=1）已由 `PRE_REF` 钉定 + `C0` 自证修复，`default`/`--inject` 在我自己的重跑下均 rc=0 且 3/3 回绿；`ISS-316` 登记正确（总数符现场）。**遗留订正项**（不阻断）：ISS-316 / 遗留 ⑤ 形态明细 `113/21` → `112/22`。**我未改任何代码/产物、未提交 git。**
