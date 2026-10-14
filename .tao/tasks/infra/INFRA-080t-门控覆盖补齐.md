# INFRA-080t: 门控覆盖补齐（`check-knowledge-refs` 小节级互指 + `check_issues.py` `closed ⇒ resolved_by`）

**模块**：infra
**项目里程碑**：M8
**依赖**：`ISS-203`（立项来源 = `SPEC-137t` reviewer 第 1 轮「非阻断发现」+ 用户裁定）；分层真源 = `docs/Process-07-门控分层规范.md`（**L1 = `make check`**）；被扩展门控 = `tools/infra/check_knowledge_refs.py`（源 `INFRA-058t`/`INTEG-037t`）、`tools/infra/check_issues.py`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源 / 用户裁定

- **来源**（`ISS-203`，open）：**①** `check-spec-refs` 不覆盖 `.tao/knowledge/**` 内互指——`SPEC-137t` 的 `ADR-0019 D9` ↔ `contract-elf.md §3.3` **双向互指**完整性本次由 reviewer **人工 `grep -c`** 核对，门控未机械校验；**②** `check_issues.py` **不校验** `closed` 条目必填 `resolved_by`（文件头字段约束「`resolved_by`: `closed` 时必填、`open` 时 `null`」无对应断言）——`ISS-201` 的 `resolved_by` 本次亦由 reviewer 人工确认。
- **用户裁定（2026-10-14，原话 = 「A」；渠道 = 经主会话问答）**：**(A) 两条都补、并入 L1** ⇒ **本任务两条都实现**（另一选项 = 只登记不补）。
- **本任务不做**：不改任何**被校验的知识正文**（`.tao/knowledge/**/*.md`、`.tao/adr/*.md`）——只扩**校验器**；发现真实悬空/违规 ⇒ **报告，不静默改正文、不静默加白名单**。

## 已查证事实（供执行，勿重复查证）

1. **并入 L1 无需新 target**：`make check`（`Makefile` 的 `check` 目标）依赖列表已含 `check-knowledge-refs`（→ `tools/infra/check_knowledge_refs.py`），并在 recipe 内直接跑 `tools/infra/check_issues.py`。若执行者另建 target，**须并入 `make check`**。
2. `check_knowledge_refs.py` 现状：扫 `AGENTS.md` / `spec/**` / `.tao/knowledge/**` / `.tao/tasks/**` 中的 `.work/**` 引用；分类 = 占位/通配（`< > * $`）、前缀截断（尾 `-`）、构建/源码豁免（`.work/build`、`.work/source`）、删除语境（`已删`/`删除`/`deleted`/`removed`）、其余**要求存在**；含**空转即 FAIL**（`checked == 0` ⇒ rc=1）。**这些既有判定一律保留**。
3. **ADR 小节体例有两种**（解析规则须同时覆盖）：粗体标签 `**Dn — <标题>**`（如 `adr-0019`/`adr-0025`/`adr-0026`）与标题 `### Dn <标题>` / `#### Dn.m <标题>`（如 `adr-0004`）；`adr-0018` 另有 `### Cn <标题>` + 其下 `### Cn` 小节。命名小节形如 `## Context（背景）` / `## Consequences（影响）` ⇒ 名称匹配须容忍**中文括注**。
4. **契约小节体例**：标题 `## §<n> <标题>` / `### §<n>.<m> <标题>` / `#### §<n>.<m>.<k>`（如 `contract-elf.md`）。
5. `.tao/knowledge/**/*.md` 现互指形态（**现场统计，计数不写死**）示例：`[ADR-0019 D10]`、`[ADR-0019 §D9]`、`[ADR-0004 §D2.2]`、`[ADR-0003 §D5]`、`[ADR-0003 §Consequences]`、`[ADR-0003 §Context]`、`[ADR-0026 D1–D8]`（**区间**）、`[ADR-0018 §C7 D4]`（§ 后带尾随项）、`[ADR-0018（C6）]`、`[ADR-0025]`（**无小节**）、`[contract-elf.md §3.3]`、`[contract-isa.md §1.3.2]`。
6. **占位形必须跳过**：`contract-elf.md` 头部「来源标注」约定行含示例 token `[ADR-0003 §DN]` / `[ADR-0019 §DN]` / `[ADR-0004 §DN]`——`DN`（及 `§N` 类）是**占位符**，**不是**真实引用 ⇒ 须按占位跳过（否则必假阳性）。
7. `issues.yaml` 现 **30** 条、`closed` **3** 条且**均已**有非空 `resolved_by` ⇒ ② 的新断言对当前树**应为绿**（执行时现场复核，不采信本行计数）。

## 接口规范

- **输入**：`tools/infra/check_knowledge_refs.py`、`tools/infra/check_issues.py`（两个扩展点）；被校验真源 `.tao/knowledge/**/*.md` + `.tao/adr/adr-*.md`；`Makefile`（L1 装配）。
- **输出 ①（`.tao/knowledge/**` 小节级互指存在性断言，落在 `check_knowledge_refs.py`）**：
  - 扫描面**限** `.tao/knowledge/**/*.md`（既有 `.work/**` 扫描面**不动**）；
  - 识别两类互指 token 并**要求目标真实存在**：
    - `[ADR-<4 位数字> …]` ⇒ 目标文件 `.tao/adr/adr-<NNNN>-*.md`；**带小节设计符**者（`§Dn` / `Dn` / `§Cn` / `Cn` / `§n(.m(.k))` / `§<命名小节>`）须在目标文件中**找到该小节**；
    - `[contract-<名>.md §…]` ⇒ 目标文件 `.tao/contracts/contract-<名>.md` 的 `§n(.m)` 小节存在；
  - 细则：**无小节者**（如 `[ADR-0025]`）只校验**文件存在**；`§` **可选**（`D10` 与 `§D9` 同族）；**区间**（`D1–D8`）按**端点集合**判定（两端均须存在）；`§D9` 后**尾随内容**（如 `§C7 D4`）取**第一个**小节设计符为准；**命名小节**按标题名匹配（兼容中文括注）；
  - **占位形**（`DN`、`§N` 等非真实编号/名称）⇒ **跳过并分类计数**；
  - 输出格式对齐既有风格：分类**计数**（总/校验/跳过/悬空）+ 悬空逐条 `文件:行  token`；悬空 ⇒ rc=1；**计数不得写死**（现场统计）。
- **输出 ②（`check_issues.py` 新断言）**：每条 `status: closed` ⇒ `resolved_by` **非空**（非 `null`、非空串、非纯空白）⇒ 否则 FAIL 并逐条列出 `id`；`open` 条目的 `resolved_by` 期望为 `null` 的既有语义**不改**。
- **输出 ③（L1 装配）**：两断言由**既有 `make check` 路径**执行；`Makefile` 仅在**必要**时改（最小改动）。
- **约束**：**不得放宽**任何既有判定——`.work/**` 悬空检查、空转 FAIL、`M1-gate` blocking 检查、`status` 合法性校验**逐条保留**；改动面**限**上述两个 `.py`（+ 必要时 `Makefile`）；**不得**改知识正文 / `spec/` / `contracts/`；计数不写死。

## 验收标准

1. **① 可达 FAIL**：注入 **1 个不存在的**小节引用（`cp` 备份 + **md5 对账**，或临时树）⇒ `make check-knowledge-refs` **rc≠0** 且输出**指名该引用**；**还原**（`cp` 回写 + md5 一致）⇒ 回绿 rc=0。留**真实输出 + 退出码**（禁 `cmd | tee` 吞码）。
2. **② 可达 FAIL**：把某 `closed` 条目 `resolved_by` 临时置空 ⇒ `check_issues.py` **rc≠0** 且列出该 `id`；还原 ⇒ rc=0（同法留证）。
3. **零假阳性**：当前树 `check-knowledge-refs` rc=0、`check_issues.py` rc=0；**报告**扫描面/被校验 token 数/跳过分类数（**现场统计、不写死**）；若发现**真实**悬空引用 ⇒ 不动正文，**报告**并登记（不得靠白名单掩盖）。
4. **L1 确实生效**：`make check` 真实运行 rc=0；并证明两断言**确在其中执行**（如注入时 `make check` 亦红，或 `make check` 输出含新断言的分类计数行）。
5. **未放宽既有判定**：逐条注入真跑并留证——① 一个悬空 `.work/**` 引用仍 FAIL；② 一个非法 `status` 仍 FAIL（③ 既有计数行/空转守卫生效）。
6. **门控**：`make check`（**L1**）/ `make check-modules`（**L2**）/ `check-knowledge-refs` / `check-no-residue` / `check_issues.py` 各 **rc=0**（各留真实 rc）。
7. **证据**：一键证据脚本 `.work/evidence/<任务ID>/run.sh`（含上述注入 → FAIL → 还原 → 回绿 全链，`cp`+md5 还原纪律，**禁** `git checkout/restore/stash`）。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
