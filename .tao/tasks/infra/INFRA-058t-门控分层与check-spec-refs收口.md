# INFRA-058t: 门控分层（L1/L2/L3）与 `check-spec-refs` 处置收口

**模块**：infra
**项目里程碑**：M7
**依赖**：无（M7 **「第 0 步」**，**排最前**；同改 `Makefile` ⇒ 与 `INFRA-056t`/`INFRA-057t` **串行**）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - **用户裁定（2026-10-08 / 10-09，明确「推到 M7」）**：门控**三层** = **L1 完整性/可用性**（秒~几十秒）/ **L2 各模块功能代表集**（几十~几百秒）/ **L3 较完整**（几百~几千秒）+ **模块完整按需单独调用**。落点：`milestones.md §规划中`「门控分层（推迟到 M7）」（**本任务即其落地**；由 `INTEG-036t §收口核对` 从「规划中」收口为立项）。
  - **设计要点（自包含）**——原设计草稿 `.work/log/integ/gate-tiering-design.md`（**gitignored**，仅作溯源、「**内容溯源，非执行必需**」）：
    - **L1 `make check`（默认）** = 现有**全部静态检查** + **组件可用性冒烟**（`llc` / `clang --print-targets` / `qemu-system-dadao` **可执行且含 `dadao`**；**不跑被测语义**）。
    - **L2 `make check-modules`（新）** = `check-lit`（受控子集）+ `check-interface` + **`check-qemu-smoke`（新）** + `test-codegen` / `test-elf` / `test-semihost`。
    - **L3 `make check-full`（新）** = `check-qemu-semantics` **全量** + `check-lit-full`（现 opt-in 档）+ Embench（`test-m6`）+ 全量向量回放。
    - **按需（模块完整）** = 各 `test-*` / `check-*` 单独调（模块全量 / profiling）。
  - **现状事实（`Makefile`，现场复测）**：`check:`（现 `Makefile:383`）= 23 项（静态 ~19 + `check-qemu-semantics`（149 用例，跑 QEMU）+ `check-lit`）；**不在** `check` 的：`test-codegen` / `test-elf` / `test-semihost` / `check-lit-full`。`TESTCASES-038t` 实测 `make check` ≈ 32 s ⇒ 现规模已在 L1 目标带边缘（"庞大"是**增长趋势**问题）。
  - **`check-spec-refs` 现状（本轮实测，计数以现场统计为准、不写死）**：工具 `tools/infra/check_spec_refs.py`；`Makefile:423` **standalone**（`Makefile:422` 注释明示「**不在 `make check`**」）。当前 **Check1 = 0 失败 / Check2 = 1 违规**（`.tao/knowledge/contract-asm.md:206`，引 `[Toolchain-01 §7.2]`）。
  - **根因（本轮实测）**：
    1. `SPEC_PREFIX_MAP`（第 44–64 行）**不含 `Toolchain-01`**，且 `_PREFIX_ANCHOR`（第 69 行）只匹配 `SimRISC-` / `DADAO-` ⇒ **`[Toolchain-01 §…]` 引用对 Check1 完全不可见**（既不被校验、也不计作「已引用」）⇒ 第 206 行**唯一**的引用被判「无引用断言」= **误报**（**非 spec drift**；引用有效、内容与 `Toolchain-01` 一致）。
    2. `Toolchain-01` 的节标题是「`### 7.2 对齐指示符`」形态、而引用写「`§7.2`」**数值节号**；`_text_matches`（第 160 行）的 lead-in 集 `_TEXT_LEAD_IN`（第 157 行）**含 `：:（(，,`、不含空格** ⇒ 数值节号 `7.2` 命中不了标题 `7.2 对齐指示符` ⇒ **仅补前缀会把 1 条误报放大为全部 `[Toolchain-01 §…]` 失败**（本会话现场统计：contracts 中 `[Toolchain-01 §…]` **91** 条；用户口径「112 条」以**现场复测为准**）。
    3. **同类隐患（一并核）**：`[Machine-01 §…]`（现场统计 **13** 条）同样**不在前缀表**（未校验）；`[SimRISC-XX §]` / `[DADAO-NN §]` = **模板占位**，**不应**被当引用校验。
  - 规则：`lessons §8.34`（验证正则须自证「确有命中」）、`§8.35`（须断言「结构」：成对 / 条数）；`AGENTS.md`「验证脚本反例门控」。
- **输出**：
  1. **逐门控计时（第 0 步，现场实测）**：对 `make` 各门控目标**逐个** `time`（`make -n` 不适用），产出**实际耗时表**（落 `.work/log/infra/`），据实测确定 L1/L2/L3 边界与「是否值得拆」（**耗时/计数现场统计，不写死**）。
  2. **三层切分（`Makefile`）**：`check` **收缩为 L1**（`check-qemu-semantics` **移出** L1）；新增 **`check-qemu-smoke`**（149 条按**语义类别机械派生**各抽代表，**禁手工挑**）、**`check-modules`**（L2）、**`check-full`**（L3）；**层间不重复**（同一检查只在一层跑）。组件可用性冒烟进 L1。
  3. **每层「能失败 + 结构断言」**：逐层给**注入反例 ⇒ 该层 FAIL** 的真实输出（改错期望值 / 编码、回退 ILLI 桩等），断言须含**成对 / 条数结构**（`§8.34` / `§8.35`）。
  4. **触发点写 `AGENTS.md`**（≤2 行 + 门控名）：**任务收尾跑 L2**、**里程碑 / `/complete` 跑 L3**（否则「按需层」**必腐烂**——分层后「L1 绿、L2/L3 红」会成常态，此条是**前提**、非可选）。
  5. **`check-spec-refs` 处置（并入本任务）**：① **改匹配器认「§编号」**——`_PREFIX_ANCHOR` / `SPEC_PREFIX_MAP` 增补 `Toolchain-01`（及同类 `Machine-01`）；`_header_matches` / `_text_matches` 支持「标题以 `N.M ` 起始 ⇒ 命中 `N.M`」（**不得**放宽为任意子串匹配）；② **统一引用口径**——在合约编写规范（`spec/Process-02`）与 `contract-*` 侧明确 `[<册> §<节号|标题>]` 的规范写法（消除「§编号 vs 标题文本」双轨）；③ **决定是否纳入 `make check`**——纳入则**归层**（L1 或 L2，**择一并说明**）且须能失败；不纳入须写明理由 + 落独立 target 文档。
  6. **关联遗留（`TESTCASES-037t` reviewer 标注）**：`check-lit-full`（227 条全量，MC / `DADAO-gen`）**仅 opt-in** ⇒ `contracts/` 漂移在 `make check` 中**不报警**——**决定其进 L2 还是 L3 并落地**。
- **约束**：
  - **先计时、后切分**（无实测不切）。
  - **层间不重复**；代表集**由类别清单机械派生**（`contracts/` 格式类 / 指令 `scope`、QEMU 语义类别）。
  - **计数 / 耗时 / 条数不写死**；一律现场统计。
  - **不在本任务改 `spec/` 正文**；引用口径若须改规范，按 `lessons §8.5`（改 `spec/` 须用户**事先**授权）与 `SPEC-131t` 同款流程。
  - 只动任务范围（`Makefile` / `tools/infra/**` / 测试脚本 / `AGENTS.md` 触发点），越界须披露。
  - 长命令 / 构建按 `AGENTS.md`「长任务」（`setsid nohup` + 落盘标记 + **申报耗时**、`JOBS=8`、禁全核）。
  - **搬迁项（见下「追加范围」③）**：搬迁内容须为**结论/设计/口径**（可长），**一次性过程**保留 `.work/log/`；被引用证据材料落**非易失位置**（`AGENTS.md`「临时目录」+ `lessons §8.6`）。

## 追加范围（用户 2026-10-11 裁定：「认 + 并入 `INFRA-058t`」，`INTEG-037t`）

> **用户原话（2026-10-11）**：「**认 + 并入 `INFRA-058t`**」——即：**`.work/log/` 归类判据**按四分类办，并把「**判据落纸 + 门控 + 搬迁**」**并入 `INFRA-058t`**。

**四分类判据（原文写进任务书）**：

- `spec/` = **规范正文**；
- **`.tao/knowledge/` = 结论/设计/口径**（**含长文**——它是"知识"不是"日志"）；
- **`.work/log/` = 一次性过程**（分析/报告/日志，**可删**）；
- **凡被引用的材料，一律不得只放 `.work/`**；**能被门控机械判定的，不写文档**。

1. **判据写入 `AGENTS.md`**（≤2 行 + 指针）：落实「文档分层与单一真源」扩展——须修正现 `AGENTS.md:65` 的「`.tao/knowledge/` = 结论与指针（**长叙述不允许**）」为「**结论/设计/口径（含长文）**」，并写入上列四分类 + 「**被引用材料不得只放 `.work/`**」。
2. **新增门控 `check-knowledge-refs`**：扫 `AGENTS.md` / `spec/` / `.tao/knowledge/` / **任务书**（`.tao/tasks/**`）中对 `.work/**` 的引用 ⇒ **引用路径不存在即红**；**须有可达 FAIL 路径**（引 `lessons §8.34`「验证正则须自证确有命中」、`§8.35`「须断言结构：成对/条数」）；并**决定是否纳入 `make check`**——纳入则**归层**（L1/L2，**择一并说明**）且须能失败；不纳入须写明理由 + 落独立 target 文档。
3. **搬迁**：把**被引用**的 `.work/log/` 材料**升格**到 `.tao/knowledge/`（或将**结论/口径摘要**进 knowledge + 保留指针）；**至少** `gate-tiering-design.md`（现被 `milestones.md §规划中`、本任务书引用）、`embench-analysis.md`（现被 `.tao/archive/M6/integ/INTEG-025t` 引用）；**迁移清单以现场 `grep` 引用为准、不写死**（`.work/` 被 `.gitignore` 整体忽略 ⇒ 仅放 `.work/` 的引用会**悬空**）。

## 验收标准

1. **分层生效**：`make check` = L1（静态 + 可用性冒烟）、`make check-modules` = L2、`make check-full` = L3；**层间无重复项**（逐项列出各层组成，机械可核对）。
2. **各层 EXIT=0**：三层**各自**真实跑通，**捕获命令自身退出码**（禁 `cmd | tee` 吞码）EXIT=0。
3. **注入反例可失败**：**每层**至少 1 次「注入反例 ⇒ 该层 FAIL ⇒ 还原 ⇒ 回绿」的真实输出（`cp` 备份 + md5 对账，**禁** `git checkout` / `restore` / `stash`）。
4. **计时表**：`.work/log/infra/` 存逐门控实测耗时（现场统计）。
5. **`check-spec-refs`**：改后 **EXIT=0**（0 误报）；注入反例（改错一条 `§号`）⇒ **FAIL**；「是否纳入 `make check`」有明确决定 + 落点。
6. **触发点**：`AGENTS.md` 含 L2 / L3 触发行（`grep` 真实输出）。
7. **判据落纸**（追加范围①）：`AGENTS.md` 含四分类判据（≤2 行 + 指针，`grep` 真实输出）；`.tao/knowledge/` 定义修正为「**结论/设计/口径（含长文）**」（非「长叙述不允许」）。
8. **门控 `check-knowledge-refs`**（追加范围②）：改后 **EXIT=0**（无悬空引用）；注入反例（引用指向不存在路径）⇒ **FAIL** ⇒ 还原 ⇒ 回绿（`cp` + md5 对账，**禁** `git checkout`/`restore`/`stash`）；「是否纳入 `make check`」有明确决定 + 落点。
9. **搬迁生效**（追加范围③）：所有**被引用**的 `.work/log/` 材料升格到 `.tao/knowledge/`（或摘要 + 指针）；`check-knowledge-refs` 绿灯；清单由现场 `grep` 得出（**不写死**）。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立重跑记录、约束核验、判决）

#### 第 1 轮 architect 追加（`INTEG-037t`，2026-10-11）
- 依用户 2026-10-11 裁定「**认 + 并入 `INFRA-058t`**」追加范围三项（见「追加范围」，含四分类判据**原文**）：① 判据写入 `AGENTS.md`（修正 `knowledge` = 含长文）；② 新增门控 `check-knowledge-refs`（扫 `.work/**` 引用、悬空即红、引 `lessons §8.34/§8.35`）；③ 被引用 `.work/log/` 材料搬迁升格（清单现场 `grep` 得出）。
- 同步 `INTEG-033k §任务分解` 行 + `milestones.md §规划中`；`lessons §8.55` 追加（被引用材料不得只放 `.work/`）。
