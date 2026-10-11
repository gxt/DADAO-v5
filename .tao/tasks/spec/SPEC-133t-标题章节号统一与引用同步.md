# SPEC-133t: 21 册标题章节号统一（`N / N.M / N.M.K`）+ 全仓引用同步

**模块**：spec
**项目里程碑**：M7
**依赖**：无（**改 21 册 `spec/*.md` + 全仓 § 引用 ⇒ 与 `SPEC-131t`/`SPEC-134t` 一律串行**）
**状态**：已验证

> 本任务书由**主会话**依用户 2026-10-11 裁定撰写（非常规 architect 起草，已披露）。编号说明：`SPEC-132m` 为 M7 spec 里程碑保留（`INTEG-033k`），故本件取 `133t`。

## 用户裁定（2026-10-11，**原话**）

> 「顺带把每个文件的标题的章节号补上，最多到 4 级标题即可，也就是最多 `a.b.c`」
> 「（章节号口径）**全面统一重编号**」

## 目的

`spec/` 21 册标题编号：`##` → `N`，`###` → `N.M`，`####` → `N.M.K`（**最深 `####`**）；使 21 册风格一致、标题可被机械引用。**本任务不写附录**（`## 附录：版本与变更记录` 归 `SPEC-134t`）。

## 接口规范

### 输入（主会话实测，**执行时现场复核、计数不写死**）

- **21 册**（`manifests/spec-readonly.lock.toml` 锁内全套）= `SimRISC-00..12`（13）+ `DADAO-11/12/13/21/22/23`（6）+ `Toolchain-01` + `Machine-01`。
- 标题 **314**；**无编号 227**；**`≥5` 级 0**（无超深需降级）。
- **关键事实**：`SimRISC-00..12` **全部无编号**（引用它们的方式是**标题文本**：如 `[SimRISC-00 §SimRISC QFC]`）⇒ **补号不打断既有引用**；`Toolchain-01` 已有 `N`/`N.M` 风格（49 标题 / 13 无号）⇒ **补缺号、保持一致**；`DADAO-*`、`Machine-01` 部分有号。
- **引用面（须现场 `grep` 全量列，计数不写死）**：`contracts/*.yaml`（尤其 `opcodes.yaml` 的 **`spec_cite`**）、`.tao/knowledge/contract-*.md`、`.tao/adr/*`、`docs/**`、21 册**互引**、`tests/**`、`tools/**`、`.tao/tasks/**`（历史叙述保留）。
- **工具链**：`tools/infra/check_spec_refs.py`（`[册 §…]` 引用有效性；**已支持数值节号**）、`check_spec_drift.py`、`tools/spec/check_asm-prose.py`（**扫描 `spec/**` 与 `docs/**`**）、`check_spec_codeblocks.py`（只扫 `spec/`）、`check-spec-readonly`（21 册 `sha256`）。

### 输出

1. **盘点表**（先做，落 `.work/log/spec/`；**供决策与留档**）：逐册 `标题数 / 有号 / 无号 / 深度分布`；`spec_cite` 与其它引用的**形态普查**（按号 / 按标题 / 混合）；**哪些引用会因补号而需要改写**。
   - ⚠️ **停下报告条件（硬约束）**：若盘点发现 ① 同册内**已有编号与新编号风格冲突**（如已有 `一、`/`1)` 等异体，需**改变既有编号语义**才统一）；或 ② **需要大范围改写引用**（非机械可同步，如 `spec_cite` 语义依赖旧无号文本）⇒ **停下报告，等用户裁定**，不得擅自动手。
2. **统一编号**（21 册）：按树下**位置顺序**分配号；`##`→`N`、`###`→`N.M`、`####`→`N.M.K`；**同册内唯一、连续**；`Toolchain-01` 已有号**保持不变**（只补缺号），若发现其编号有断号/重号 ⇒ **报告**（不擅自重排）。
3. **引用同步**：按盘点表，**机械同步**受影响的引用（`contracts/*.yaml`/`contract-*.md`/`adr/*`/`docs/**`/册互引/`tests/**`/`tools/**`）；`.tao/tasks/**` 与 `.tao/archive/**` **不改**（历史叙述）。**每条改动须可追溯到"哪册哪标题号变了"**（清单留档）。
4. **锁同步**：21 册 `sha256` 更新（**只**这 21 册变动）。
5. **门控**：`make check`（L1）EXIT=0；**逐项实测**至少 `check-spec-refs`、`check-spec-readonly`、`check-asm-prose`、`check-spec-codeblocks`、`check-spec-drift`、`check-legality-*`、`validate-vectors`、`check-rule-refs` ⇒ 各 EXIT=0（**捕获命令自身退出码，禁 `cmd | tee` 吞码**）。

### 约束

- **只动标题行与其引用**：不改规范**正文语义**（`Process-06 §2` 授权 = 用户 2026-10-11 原话，**落纸**）；不改 `.tao/archive/**`、`.tao/tasks/**`、`contracts/` 的**数据语义**（只改 § 引用字符串）。
- **序号插入不得改变既有标题文本**（只**加**号/改号，不重命名标题）。
- **计数不写死**；临时目录 `/tmp/opencode/SPEC-133t/`；**不提交 git**；禁 `git add -A`/`.`。
- 反例注入还原**禁** `git checkout/restore/stash`；一律 `cp` + md5 对账。
- 任务书/记录中**不得写字面 `.work/<具体路径>`**（用 `<>` 占位），否则 `check-knowledge-refs` 判悬空、`make check` 自伤。

## 验收标准

1. **编号一致**：21 册每个 `##/###/####` 均符合 `N`/`N.M`/`N.M.K`；**无 `#####`**；同册内**唯一且连续**（机械校验脚本 + 真实输出）。
2. **正文未变**：除标题行与 § 引用外，**正文零改动**（`git diff` 逐册核，抽样给出证据）。
3. **引用同步**：盘点表所列受影响引用**全部同步**（逐条清单 + `grep` 证据）；**无残留旧引用**（现场 `grep` 计数）。
4. **门控**：第 5 条所列门控**各 EXIT=0**（真实输出/退出码）。
5. **锁**：21 册 `sha256` 更新且 `check-spec-readonly` EXIT=0（**只**这 21 册变动）。
6. **反例可失败**：注入「某册标题号与正文引用不一致」（或把某标题号改重）⇒ 编号校验脚本 / 门控 **FAIL** ⇒ `cp`+md5 还原 ⇒ 回绿。
7. **一键证据脚本**落 `.work/evidence/SPEC-133t/`（能失败、可达 FAIL、结构断言、计数不写死、捕获退出码）。
8. **完成区**（≤30 行）与真实输出逐条对齐。

## 完成区
**测试结果**：`make check`(L1) rc=0；逐项门控 16 项各 rc=0（见「验收结果」）；`check_numbering`/`matcher_selftest` PASS；独立工具 `check_qfc_coverage`/`check_d7_consistency`/`gen_legality_list --verify`/`gen_cfx_aliases --verify` 各 rc=0；一键证据脚本 rc=0。
**修改文件**：21 册 `spec/*.md`（锁内全套；19 册共 227 标题行改动，`DADAO-13`/`DADAO-23` 已合规 0 改动）；`tools/infra/check_spec_refs.py`（剥离标题前导号）、`tools/llvm/gen_asm_list.py`、`tools/spec/check_asm_list_consistency.py`、`tools/spec/gen_legality_list.py`、`tools/spec/check_qfc_coverage.py`；`manifests/spec-readonly.lock.toml`（19 册 sha256）；`.tao/knowledge/milestones.md`（流水行）。（另有 `.work/evidence/<任务ID>/`、`.work/log/<模块>/` 证据/盘点、本任务书。）
**验收结果**：盘点表落 `.work/log/<模块>/`；引用形态普查：SimRISC 全按标题文本、已编号册号保持原值 ⇒ **需改写引用 = 0 条**（改造前/后全仓括号形引用解析失败集相同，各 12 条**既有**悬挂，与本任务无关）。
- `check_numbering`：`files=21 h2=108 h3=178 h4=28 h5+=0 total=314` + `PASS (编号唯一且连续，深度 ≤ 4)`。
- `make check` rc=0：`repository checks (L1): PASS`。
- 反例注入（cp+md5）：重号 ⇒ `check_numbering` rc=1（`编号重复 3.1`）⇒ 还原回 rc=0（md5 `3d7c28…==3d7c28…`）；标题引用不一致 ⇒ `make check-spec-refs` rc=2（24 violations）⇒ 还原回 rc=0。
**新发现/坑**：① 生成块标题须同步生成器——`## 1. 汇编指令速查`/`### 1.1 {cls}（…）`（`gen_asm_list`）与 `## 2. 合法性检查`（`gen_legality_list`）在生成区内，重生成会回退，故写死位置号并同步一致性/漂移校验器。② `check_qfc_coverage._split_sections` 原 `startswith("## SimRISC QFC")` 因加号失配 ⇒ 改前导号容忍。③ 层级异常 3 处（`SimRISC-03` 的 `set.rd`/`set.rb`、`SimRISC-11` 的 `nop`）原为 `##` 直挂 `####`（无 `###` 父）⇒ **提升为 `###`**（标题文本不变）以获合法 `N.M.K`。④ `##` 编号沿用既有 `N.` 形（`DADAO-*`/`Machine-01`/`Toolchain-01` 与 `docs/Process-0x` 既定体例），`###`/`####` 为 `N.M`/`N.M.K`。⑤ **并发兄弟任务书致 L1 红（越界披露，未改）**：`SPEC-134t-*.md:76` 写死其证据目录的**字面路径**（未用 `<>` 占位、目录尚未创建）⇒ `check-knowledge-refs` 悬空、`make check` rc≠0（与本任务改动无关，现场隔离后 rc=0；见证据脚本）。建议该任务书改用 `<>` 占位（`禁止事项`：本任务不改范围外文件）。
**遗留问题**：SPEC-134t 任务书 `:76` 悬挂引用未修（越界，归主会话/SPEC-134t 处置）；本任务范围无遗留。既有 12 条悬挂 spec 引用（盘点表 §3）属其它范围，非本任务引入（改造前后失败集相同）。

## 审阅记录

#### 第 1 轮 engineer 自审
- 逐行审查 `check_spec_refs._header_matches`/`_strip_lead_number`：标题与引用**两侧**均剥离前导号；`_num_section_matches` 仍先跑（`§7.2`→`7.2 …`），不放松为子串。构造边缘证据：全部 21 册标题「去号正文」**无一以数字+空格开头**（现场 0 命中）⇒ 不会二次剥离；`16位数据运算`/`0.5.0（…）` 因号后非空格不被剥离。
- 匹配器自证（8 断言全绿）：编号引用命中（`§3.1`/`§5.1`）、标题引用命中（`§存取RD寄存器`/`§1. 运行模式…`）、前缀误命中不发生（`§5` 不中 `5.1 …`、`§2.2` 不中 `2.20 …`）、子串误命中不发生（`§存取RD` 不中 `3.1 存取RD寄存器`）。
- 生成/消费链排查：`gen_asm_list`↔`check_asm_list_consistency`（`SECTION_HEADER`+`_section_content` 同步）、`gen_legality_list`↔`check_legality_drift`（复用同渲染）、`check_qfc_coverage`（前导号容忍）、`gen_cfx_aliases`（按表头行解析，行号不变故 `source` 列不变）逐一核；`check_d7_consistency`（内容 needle，非标题）与 `check_spec_codeblocks`/`check_asm_prose`（仅代码块）不受影响。
- 防造假：全部结论取真实退出码（`make <target>; rc=$?`，无 `| tee` 吞码）；反例注入 cp+md5 对账还原。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 生成区标题若不改生成器，重生成回退 | ✅已修 | `gen_asm_list`（`## 1.`/`### 1.1`）、`gen_legality_list`（`## 2.`） | `check-asm-list`/`check-asm-list-drift`/`check-legality-drift` rc=0 |
| F2 `check_qfc_coverage` 因加号失配 | ✅已修 | `_QFC_HEAD_RE` 前导号容忍 | 直跑 rc=0（QFC 双向一致） |
| F3 `SimRISC-03/11` 跳级无 `###` 父⇒编号无法合法 | ✅已修（披露） | 3 处 `####`→`###` | `check_numbering` PASS（连续） |
| F4 `§N. 标题` 叶点引用（`contract-see` 等） | ❌不修（无需） | 标题号保持 `N.` 形 | 改造前/后解析失败集相同（12 既有） |

#### 第 1 轮 reviewer 验收

**重跑记录**：`make check`(L1) rc=0；逐项门控 16 项（check-spec-refs/readonly/asm-prose/spec-codeblocks/spec-drift/legality-drift/legality-invariants/validate-vectors/rule-refs/scope/asm-list/asm-list-drift/knowledge-refs）各 rc=0；证据脚本 `<>` run.sh rc=0（含其自身重号+引用注入 FAIL→md5还原回绿）。
**编号**：独立脚本 MY-CHECK `files=21 h2=108 h3=178 h4=28 h5+=0 total=314` + PASS；与 engineer `check_numbering` 输出一致；code-fence 内伪标题=0。异体编号盘点=0（改造前标题无一、/1) 等异体）。已有编号（Toolchain-01/DADAO-*）逐条核不变；加号不改标题文本。
**正文零改动**：`body_diff` 227 标题行替换、3 处 `####`→`###` 提升（SimRISC-03 set.rd/set.rb、SimRISC-11 nop，文本不变）；DADAO-13/23 改动=0；抽样 4 册非标题行 diff=0。
**引用未打断**：① 括号形全仓 154 条失败集改造前/后**完全相同**（0 打断、0 修复）；② `spec_cite` 227 条：203 命中 header、**24 条失败但改造前同样失败**（SimRISC-08/09/10 的「Bit manipulating：位操作指令」「比较操作」——实际标题带「 — 值语义」后缀）；③ 5 条抽验（§SimRISC QFC/§寄存器组之间块赋值/§寄存器规范§RB寄存器/§存取RD寄存器/§3.1）全命中；④ engineer 口径 12 条悬挂可复现（全仓排历史区 9 + 3 共 12）。「需改写引用 0 条」成立。
**边界用例**：`_strip_lead_number` 对 `3.16位`/`16位`/`0.5.0（…）`（号后非空格）**不剥离** ✓；`2.0.5.4 说明`（数字.数字+空格）**会剥离**（`§说明` 可误命中），但 21 册「二次剥离」标题=0 实际命中。
**脚本落点**：check_numbering.py / matcher_selftest.py 只在 `.work/evidence/<任务ID>/`（gitignored，违反「生成器/脚本随产物保留」）→ F1。
**锁**：独立重算 21 册 sha256 全与锁一致；与 HEAD 锁对比仅 19 册变动（DADAO-13/23 不变）；check-spec-readonly rc=0。
**独立注入**（与 engineer 不重复）：① SimRISC-05 `### 3.2 自增自减` 删号 → eng rc=1 + my rc=1 + check-spec-readonly rc=2 → cp+md5 还原（md5 `45758e2…`==`45758e2…`）→ rc=0；② SimRISC-04 `#### 4.1.2`→`#### 4.9.1` 孤儿父节 → my FAIL（缺父节）、**eng PASS**（F2：check_numbering 缺父节断言）→ 还原回绿。
**越界核**：禁改区（`.tao/archive/`/`.tao/tasks/`除本任务书/`contracts/`/`tests/`/`docs/`）0 改动；26 文件全在允许范围（19 册 spec + lock +5 tools + milestones）。SPEC-134t 未纳入。
**判定：Accepted**（验收 1–8 全部达成）。

| finding | 级别 | 说明 | 整改 |
|---------|------|------|------|
| F1 脚本落点 | **收尾阻断** | check_numbering/matcher_selftest 仅在 `.work/evidence/<任务ID>/`，/complete 收尾检查③「证据留非易失位置」会拦 | 收尾前迁入 `tools/spec/` 或登记 issues 获豁免 |
| F2 编号校验缺父节断言 | 非阻断 | 孤儿编号（无父节）可通过 engineer check_numbering（实测注入 eng PASS） | 整改：补父节存在断言（可参考 `<>` reviewer 独立脚本逻辑） |
| F3 24 条既有 spec_cite 悬挂 | 非阻断 | SimRISC-08/09/10 标题带「 — 值语义」后缀，spec_cite 省略后缀；改造前后失败集完全相同（24==24），非本任务引入 | 建议登记 issues（标题后缀匹配或 spec_cite 补后缀） |

## 返工 1（F1+F2）（2026-10-11）

> 触发：第 1 轮 reviewer 判 `Accepted`，但含 **1 项收尾阻断（F1）+ 1 项非阻断（F2）**。本返工**只修 F1+F2**；F3 归 architect 登记 issue（不在范围）。

**F1（收尾阻断）——脚本落点迁入非易失位置**
- finding（reviewer 要点）：`check_numbering.py` / `matcher_selftest.py` 仅在 `.work/evidence/<任务ID>/`（gitignored）⇒ 违反 `AGENTS.md`「生成器/脚本随产物保留（优先 `tools/<module>/`）」。
- 改动：`check_numbering.py` → **`tools/spec/check_numbering.py`**（`REPO` 由 `parents[3]` 改 `parents[2]`）；`matcher_selftest.py` → **`tools/spec/check_spec_refs_selftest.py`**（同改；重命名以消歧，属 `tools/infra/check_spec_refs` 匹配器自证）。旧副本自 `.work/evidence/<任务ID>/` 删除；证据脚本 `run.sh` 调用路径同步为新落点。

**F2（非阻断）——补「父节存在」断言**
- finding：reviewer 注入 `SimRISC-04` 孤儿父节（`##` 直挂 `####`）时，`my-check` FAIL 而 `check_numbering` PASS。
- 改动：`tools/spec/check_numbering.py` 新增断言 5「父节存在（层级逐级）」：每个 ≥3 级标题的父号须作为其上一级（`L-1`）标题出现。

**验收结果（真实输出/退出码逐条）**
- 迁移后 `tools/spec/check_numbering.py`：`files=21 h2=108 h3=178 h4=28 h5+=0 total=314` + `check-numbering: PASS (…父节逐级…)`，rc=0。
- `tools/spec/check_spec_refs_selftest.py`：`matcher-selftest: PASS (8/8 断言)`，rc=0。
- 反例注入（`cp`+md5，临时目录 `/tmp/opencode/SPEC-133t-rework/`）：`#### 4.1.2`→`#### 4.9.1` 孤儿父节 ⇒ `check-numbering: FAIL (1 violation(s))` + `SimRISC-04-64位数据运算.md:L182: 父节缺失 4.9.1（无 3 级标题 4.9；禁跳级）`，rc=1；`cp` 还原 ⇒ md5 `7c453c74…==7c453c74…` ⇒ 复跑 rc=0（回绿）。
- 一键证据脚本 `.work/evidence/<任务ID>/run.sh` rc=0（含重号 / 孤儿父节 / 引用不一致三注入 FAIL→md5 还原→回绿；计数现场统计）。
- 门控：`make check`(L1) rc=0（`repository checks (L1): PASS`）；`make check-spec-readonly` rc=0；`make check-no-residue` rc=0。
- 未动 21 册 `spec/*.md` 正文（仅注入→md5 还原）、`contracts/`、`tests/`、`docs/`；未提交 git。

#### 第 2 轮 engineer 自审（返工 1）
- F2 断言逐行核：`by_level` 以实测标题号集构造，对 L≥3 节点查 `parent ∈ by_level[L-1]`；父号缺失即报「父节缺失」——**双向可达**（注入孤儿 ⇒ FAIL，还原 ⇒ PASS，均实测）。
- F1 迁移核：新落点 `REPO` 层级按 `parents[2]` 核（`tools/spec/x.py` → 仓库根），两脚本实测 rc=0；`run.sh` 4 处路径全部同步（grep 无旧路径残留）。
- 防造假：全部取真实退出码（`… ; rc=$?`，无 `| tee` 吞码）；还原用 `cp`+md5 对账，未用 `git checkout/restore/stash`。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 脚本落点（收尾阻断） | ✅已修 | 迁 `tools/spec/check_numbering.py`、`tools/spec/check_spec_refs_selftest.py`；`run.sh` 同步 | 两脚本 rc=0；`run.sh` rc=0 |
| F2 编号校验缺父节断言 | ✅已修 | `check_numbering` 新增断言 5（父节存在） | 注入孤儿 ⇒ rc=1（`父节缺失 4.9.1`）；md5 还原 ⇒ rc=0 |

#### 复验轮（第 1 轮 reviewer，2026-10-11）

- **F1 落点**：`tools/spec/check_numbering.py` / `tools/spec/check_spec_refs_selftest.py` 存在 ✓；旧副本 `.work/evidence/<任务ID>/check_numbering.py` / `matcher_selftest.py` 已删 ✓；`run.sh` grep 无旧路径残留 ✓；`git check-ignore -v` exit=1（非忽略，会入库）✓。
- **F2 鉴别力**（独立注入，与 engineer 不重复）：`SimRISC-08` `#### 3.1.1`→`#### 3.5.1`（无父节 3.5）⇒ `check_numbering` rc=1 + `父节缺失 3.5.1（无 3 级标题 3.5；禁跳级）` ⇒ `cp`+md5 还原（`e1ed480…`==`e1ed480…`）⇒ rc=0。
- **未波及核**：21 册 `spec/*.md` md5 与上轮快照一致（0 变化）✓；`git diff --stat -- spec/` 仍为 227 ins / 227 del（仅本轮注入→还原，净零变化）✓；禁改区 0 改动。
- **门控**：`make check`(L1) rc=0；`run.sh` rc=0（重号/孤儿/引用三注入 FAIL→md5 还原→回绿）。
- **判定：Accepted**（F1 收尾阻断已解除，F2 鉴别力补全）。F3（24 条既有 spec_cite 悬挂）维持非阻断，归 architect 登记 issue。

#### 交叉复核 + 提交（architect，2026-10-11）

- **交叉复核（独立，现场 rc）**：`make check` **rc=0**（`repository checks (L1): PASS`）；`make check-no-residue` **rc=0**；`make check-spec-readonly` **rc=0**（21 册 OK）；`python3 tools/infra/check_issues.py` **rc=0**（20 open / 7 closed）；`python3 tools/spec/check_numbering.py` **rc=0**（`files=21 h2=108 h3=178 h4=28 h5+=0 total=314` + `PASS`）。任务书 `**状态**`=已验证。日志 `/tmp/opencode/<本次任务>/*.log`。
- **F3 登记**：新增 `ISS-192`（`scope: [spec]`，open）——`contracts/opcodes.yaml` **24** 条 `spec_cite` 引用 `SimRISC-08/09/10` 的「比较操作」/「Bit manipulating：位操作指令」，实际标题带「 — 值语义」后缀 ⇒ 解析失败；改造前/后失败集完全相同（24==24）、非本任务引入、L1 门控不红（`check_fp_contract` 的 `spec_cite` 仅校验 `SimRISC-0[0-7]`）。先 `grep`（`值语义`/`spec_cite`/`悬挂`）= 0 命中，确认**无重复条目**。`check_issues.py` **rc=0**。
- **milestones**：`SPEC-133t` 行 → `已验证` + `完成时间` 回填 `2026-10-11 22:09`（= 落地提交时间，提交时强制 `GIT_{AUTHOR,COMMITTER}_DATE`）。
- **提交（architect；档位=正常，reviewer 复验 `Accepted`）**：显式 staging（逐路径，禁 `git add -A`/`.`）；`git diff --cached --name-status`：**A=3**（`SPEC-133t` 任务书 + `tools/spec/check_numbering.py` + `tools/spec/check_spec_refs_selftest.py`）、**M=27**（19 册 `spec/*.md` + `manifests/spec-readonly.lock.toml` + 5 `tools/**` + `milestones.md` + `issues.yaml`）；与完成区「修改文件」对账：**无漏提 / 多提 / 越界**（超出完成区清单者为 F1 迁入的 2 脚本 + 本步 F3 的 `issues.yaml`，均已在本记录披露）；**排除** gitignored 证据/日志目录、`.dadao/`、`.cache/` 及 2 份并行任务书（`SPEC-134t`/`INFRA-064t`）。分支 `SPEC-133t` = `bd0ea74`；落地 `master`（`merge --squash` 单提交，提交号见 `git log master`）；**未 `push`**、分支已删。
