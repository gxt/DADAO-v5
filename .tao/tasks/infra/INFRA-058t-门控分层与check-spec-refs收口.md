# INFRA-058t: 门控分层（L1/L2/L3）与 `check-spec-refs` 处置收口

**模块**：infra
**项目里程碑**：M7
**依赖**：无（M7 **「第 0 步」**，**排最前**；同改 `Makefile` ⇒ 与 `INFRA-056t`/`INFRA-057t` **串行**）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - **用户裁定（2026-10-08 / 10-09，明确「推到 M7」）**：门控**三层** = **L1 完整性/可用性**（秒~几十秒）/ **L2 各模块功能代表集**（几十~几百秒）/ **L3 较完整**（几百~几千秒）+ **模块完整按需单独调用**。落点：`milestones.md §规划中`「门控分层（推迟到 M7）」（**本任务即其落地**；由 `INTEG-036t §收口核对` 从「规划中」收口为立项）。
  - **设计要点（自包含）**——原设计草稿 `.tao/knowledge/gate-tiering-design.md`（INFRA-058t 升格自 `.work/log/integ/`；仅作溯源、「**内容溯源，非执行必需**」）：
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
  5. **`check-spec-refs` 处置（并入本任务）**：① **改匹配器认「§编号」**——`_PREFIX_ANCHOR` / `SPEC_PREFIX_MAP` 增补 `Toolchain-01`（及同类 `Machine-01`）；`_header_matches` / `_text_matches` 支持「标题以 `N.M ` 起始 ⇒ 命中 `N.M`」（**不得**放宽为任意子串匹配）；② **统一引用口径**——在合约编写规范（`docs/Process-02`）与 `contract-*` 侧明确 `[<册> §<节号|标题>]` 的规范写法（消除「§编号 vs 标题文本」双轨）；③ **决定是否纳入 `make check`**——纳入则**归层**（L1 或 L2，**择一并说明**）且须能失败；不纳入须写明理由 + 落独立 target 文档。
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

**测试结果**：全绿。L1 `make check` rc=0(27.1s)、L2 `make check-modules` rc=0(90.9s)、L3 `make check-full` rc=0(86.7s)；`check-spec-refs`/`check-knowledge-refs`/`check-components`/`check-qemu-smoke` 各 rc=0。一键证据 `.work/evidence/INFRA-058t/run.sh` rc=0（5 组「注入⇒预期 FAIL⇒`cp`+md5 还原⇒回绿」，逐项打印退出码、无 `tee` 吞码）。

**修改文件**：`Makefile`；`tools/infra/check_spec_refs.py`(改)+`tools/infra/check_knowledge_refs.py`(新)+`tools/infra/check_components.py`(新)；`tests/scripts/run_qemu_smoke.py`(新)；`AGENTS.md`；`.tao/knowledge/{lessons.md,milestones.md,issues.yaml}`(搬迁后引用同步)；升格新增 `.tao/knowledge/{gate-tiering-design,embench-analysis,pending-registrations,INTEG-027t-report,LLVM-070t-rootcause,SPEC-129t-count-table,TESTCASES-039t-stage1-gaps}.md`；本任务书；`.work/log/infra/INFRA-058t-gate-timing.md`；`.work/evidence/INFRA-058t/run.sh`。

**验收结果**（逐条，真实输出见 `.work/evidence/INFRA-058t/` 与 `/tmp/opencode/INFRA-058t/*.log`）：
1. **分层**（直接依赖**交集=∅**）：**L1**=`check`=22 静态+`check-spec-refs`+`check-knowledge-refs`+`check-components`；**L2**=`check-modules`=`check-interface`+`check-lit`+`check-qemu-smoke`+`test-codegen`+`test-elf`+`test-semihost`；**L3**=`check-full`=`check-qemu-semantics`+`test-m6`。
2. 各层 rc=0（上）。3. 注入：L1 改 `contract-asm-list.md`⇒`check` rc=2；L2 改 `reg-compare.yaml` 期望值⇒`check-modules` rc=2；L3 改 `reg-shift-extend.yaml`⇒`check-full` rc=2；`check-spec-refs` §7.2→§7.99⇒rc=1；`check-knowledge-refs` 注入悬空 `.work/…`⇒rc=1；均 `cp`+md5 还原回绿。
4. 计时表落 `.work/log/infra/INFRA-058t-gate-timing.md`。5. `check-spec-refs` 改后 rc=0 ⇒ **纳入 L1**。6. `AGENTS.md` 含 L2/L3 触发行（grep 见审阅记录）。7. 四分类 +「knowledge=结论/设计/口径（含长文）」入 `AGENTS.md`。8. `check-knowledge-refs` rc=0 ⇒ **纳入 L1**。9. 升格 7 文件、引用同步、门控绿灯。

**新发现/坑**：
1. **`check-qemu-semantics` 实测仅 1.52s**（149 用例/`--jobs 8`）⇒ 移出 L1 是**语义归类**（L1=静态+可用性）而非提速；L1 耗时来自静态项（`check-patch-tree` 7.9s、`validate-vectors` 6.5s）。L2/L3 成本主要是 `install-host`(≈56s)（+L2 经 `test-semihost` 前置顺带的 L1 `check`≈27s）。
2. **引用形态口径（A/B/C）**：`<>`/`*`/`$`/尾 `-` 形态跳过（占位/通配/前缀）；`.work/build`/`.work/source` 豁免（clean 即失）；删除语境行不校验；其余**具体路径**须存在——四分类/「该放哪」写成 `AGENTS.md` 规则，门控只判「悬空」。
3. **`check-spec-refs` 修复**：+`Toolchain-01`/`Machine-01`（总引用 905，此前 104 条不可见）+「`§N.M` 命中标题 `N.M `」（严格：不匹配 `N.Mx`；去反引号归一）+「`§x`/`§N` 占位跳过」⇒ Check1=0/Check2=0。
4. **搬迁（现场 grep）**：升格 7 篇 `.md`→`.tao/knowledge/` 并同步全部引用。**未搬（披露）**：`ISS-reconcile.md`（其引用在**历史**任务书 `INTEG-028t`[已验证]⇒改其引用属越界/§5.3）+ `.work/log/**` 过程 `.log/.txt/.sh`（`LLVM-071t-g5-relax.log`/`SPEC-126t-rescan-ci.txt`/`INFRA-055t-fetch.log`/`picolibc-probe-*`；结论已在引用文档、属「一次性过程」）；`embench-analysis.md` 唯一引用在 `.tao/archive`（不在扫描面）⇒搬迁后该 archive 引用陈旧、按 §5.3 保留。
5. 全 15 ISA 向量回放实测 rc=1（`mem-rd.yaml` 等 `UNMAPPED/MALIGN` 失败，**pre-existing、非本任务引入**）⇒ `check-qemu-semantics` 维持 2 文件 149 用例（「全量」= 该门控全集）。

**遗留问题**：无（未做/口径项均已在「新发现/坑」披露）。两处「择一」决定：`check-interface` 归 **L2**（遵设计 §L2 枚举；与任务书 §L1「现有全部静态检查」措辞有张力，按「层间不重复」硬约束取 L2）；`check-lit-full` 归 **L3**（由 `test-m6` 步骤 [1/3] 承载，不重复列出）。

## 审阅记录

#### 第 1 轮 engineer 自审
**改动摘要**：`Makefile`（分层 target/`.PHONY`/help）、`check_spec_refs.py`（前缀+数值节号+占位跳过）、新 `check_knowledge_refs.py`/`check_components.py`/`run_qemu_smoke.py`、`AGENTS.md`（四分类/L2·L3 触发点）、7 篇 `.md` 升格 + 引用同步。逐行自审如下。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| S1 `check-qemu-smoke` 代表集取 `(class,mnemonic)` ⇒ 86/149，缩减有限 | ✅保留+记明 | 脚本头注 + 完成区口径；规则=每组取首条（机械、覆盖全 class×全 mnemonic） | 证据脚本 L2 段 rc=0；注入 rc=2 |
| S2 `make check-modules` 经 `test-semihost` 前置**顺带跑 L1** | ✅已披露 | Makefile 注释 + 完成区；「层间不重复」按**直接**依赖口径（交集=∅） | `grep '^check' Makefile` 逐行核对；L2 rc=0 |
| S3 `check-interface` 归层（任务书 §L1「全部静态检查」 vs 设计 §L2）张力 | ✅取 L2+披露 | Makefile 从 `check` 移出；完成区/遗留问题记明 | 分层定义 grep；三层 rc=0 |
| S4 `check_knowledge_refs` 的「删除语境」按行跳过，可能误跳同行的真引用 | ✅实测核 | 仅 §7.11 一行（codegen-e2e-elf）命中；报告 `删除语境 (历史): 1` | 门控输出该计数=1，悬空=0 |
| S5 升格把任务域报告移入 `knowledge/`；`embench-analysis.md` 的 archive 引用变陈旧 | ✅披露 | 加「升格指针」行；完成区记 §5.3 不回溯 | 门控 rc=0；用户裁定「被引用材料不得只放 .work/」 |
| S6 `_PLACEHOLDER_SECTION_RE=[A-Za-z]+$` 可能误跳合法 ASCII 节名 | ❌不修 | 实测全库节名仅「数值 / CJK / `x`/`N` 占位」三类，无误伤 | 单元测 8/8 OK + `check-spec-refs` rc=0 |
| S7 数值节号规则是否过宽（`5` 命中 `5.1`？`7.2` 命中 `7.25`？） | ✅已收紧 | `. ` / ` ` 双 lead-in，禁任意子串 | 单元测：`5`↛`5.1`、`7.2`↛`7.25` |
| S8 证据/还原纪律 | ✅遵守 | 全程 `cp` 备份 + `md5` 对账；未用 `git checkout/restore/stash` | 证据脚本 5 组 md5「注入前=还原后」 |

**判决**：全部 finding 已处置（S6 判 ❌不修并附证据）；无未修项 ⇒ 状态置 `待验收`。
**真实 grep（触发点/四分类）**：`AGENTS.md:71` 含「任务收尾跑 L2 / 里程碑·`/complete` 跑 L3」；`AGENTS.md:63` 含四分类、`:64` 含「被引用材料不得只放 `.work/`」。

#### 第 1 轮 reviewer 验收（2026-10-11）

**独立重跑（逐层捕获命令自身退出码，无 `tee` 吞码）**：
- `make check` → EXIT=0（L1，23 prereqs + 2 inline）
- `make check-modules` → EXIT=0（L2，6 prereqs）
- `make check-full` → EXIT=0（L3，2 prereqs）
- `check-spec-refs` → EXIT=0（905 refs, Check1=0, Check2=0）
- `check-knowledge-refs` → EXIT=0（143 refs, 77 具体路径校验, 悬空=0）
- `check-components` → EXIT=0（llc/clang/qemu 均含 dadao）

**层间重复判定**：直接依赖**交集=∅**（L1:23, L2:6, L3:2 —— 无交集）。`test-semihost`→`check` 为**间接依赖**（INTEG-020t 设计），L2 顺带跑 L1 已在 Makefile 注释披露；按直接组成口径可接受。`check-lit`(L2) 为 `check-lit-full`(L3) 的受控子集，层间目标不同，无重复。

**独立注入（check-spec-refs）**：改 `contract-fp.md` 的 `[SimRISC-01 §存取RF寄存器]`→`§存取RF寄存器NOEXIST` ⇒ EXIT=1（8 violations Check1）；`cp`+md5 还原 ⇒ EXIT=0（md5=99d07863… 匹配）。N.Mx 误命中验证：`_num_section_matches` 单元测 8/8 OK（§5↛5.1, §7.2↛7.25, §5.1→5.1✓）。

**独立注入（check-knowledge-refs）**：往 `milestones.md` 追加 `.work/log/infra/<INFRA-058t-DOES-NOT-EXIST>.md` ⇒ EXIT=1（1 悬空）；`cp`+md5 还原 ⇒ EXIT=0（md5=f33393f6… 匹配）。

**证据脚本五项**：① 一键可跑（`set -u`, deterministic）✓ ② 能失败（FAILED=1 + exit 1）✓ ③ 可达 FAIL 路径（5 组真实注入）✓ ④ 成对结构（inject→FAIL / restore→PASS）✓ ⑤ 退出码直接捕获（`$?`, 无 `tee`）✓。计数来自 harness 动态统计，不写死 ✓。

**AGENTS.md 四处 grep**：`:63` 四分类（knowledge=结论/设计/口径**含长文**）✓；`:64` 被引用材料不得只放 `.work/` + `check-knowledge-refs` 机械保证 ✓；`:70` L1/L2/L3 分层定义 ✓；`:71` 触发点（任务收尾=L2, 里程碑/`/complete`=L3）✓。

**搬迁现场 grep**：7 篇已升格 `.tao/knowledge/` 全部存在（gate-tiering-design/embench-analysis/pending-registrations/INTEG-027t-report/LLVM-070t-rootcause/SPEC-129t-count-table/TESTCASES-039t-stage1-gaps）。残余 `.work/` 引用均为**证据/日志指针**（`.work/evidence/`/`.work/log/` + `.work/build`/`.work/source` 豁免），门控悬空=0。`ISS-reconcile.md` 引用在历史任务书 INTEG-028t[已验证]，文件本地存在，口径成立。

**check-qemu-smoke 派生**：`run_qemu_smoke.py` 按 `(class, mnemonic)` 分组各取首条——机械派生，无硬编码清单；149→86（4 class × 24 mnemonic，boundary=14），结构断言覆盖≥源集合。

**约束核验**：临时目录 `/tmp/opencode/INFRA-058t-review/` ✓；未提交 git ✓；注入还原用 `cp`+md5（禁 `git checkout/restore/stash`）✓；工作区快照对账一致 ✓。

**判决：Accepted**。无阻断项。非阻断注记：L2 间接跑 L1 增加 ~27s（test-semihost 依赖 `check`），若未来 L1 规模增长可考虑拆解该前置。

**修正披露（reviewer 2026-10-11）**：行 123 原字面假路径（无 `<>` 尖括号形态）触发本轮新增门控 `check-knowledge-refs`（`make check` rc=2），已改为占位形态 `.work/log/infra/<INFRA-058t-DOES-NOT-EXIST>.md`；修正后 `make check` **EXIT=0**（全绿，含 `check-knowledge-refs` 悬空=0）、`check-knowledge-refs` 单跑 **EXIT=0**。

- **第 2 次修正披露（architect 交叉复核，2026-10-11）**：上面这条披露行**自身**又写了**无尖括号的字面假路径**，被同一门控判悬空 ⇒ architect 独立重跑 `make check` **rc=2**（与主会话回报 EXIT=0 不符）。本轮已把该字面路径改为「无 `<>` 尖括号形态」的文字描述（不再出现具体 `.work/` 路径）；重跑 `make check` **rc=0**、`check-knowledge-refs` **rc=0**（悬空=0）。

#### 第 1 轮 architect 追加（`INTEG-037t`，2026-10-11）
- 依用户 2026-10-11 裁定「**认 + 并入 `INFRA-058t`**」追加范围三项（见「追加范围」，含四分类判据**原文**）：① 判据写入 `AGENTS.md`（修正 `knowledge` = 含长文）；② 新增门控 `check-knowledge-refs`（扫 `.work/**` 引用、悬空即红、引 `lessons §8.34/§8.35`）；③ 被引用 `.work/log/` 材料搬迁升格（清单现场 `grep` 得出）。
- 同步 `INTEG-033k §任务分解` 行 + `milestones.md §规划中`；`lessons §8.55` 追加（被引用材料不得只放 `.work/`）。
