# INFRA-080t: 门控覆盖补齐（`check-knowledge-refs` 小节级互指 + `check_issues.py` `closed ⇒ resolved_by`）

**模块**：infra
**项目里程碑**：M8
**依赖**：`ISS-203`（立项来源 = `SPEC-137t` reviewer 第 1 轮「非阻断发现」+ 用户裁定）；分层真源 = `docs/Process-07-门控分层规范.md`（**L1 = `make check`**）；被扩展门控 = `tools/infra/check_knowledge_refs.py`（源 `INFRA-058t`/`INTEG-037t`）、`tools/infra/check_issues.py`
**状态**：已验证

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
**测试结果**：一键证据 `.work/evidence/INFRA-080t/run.sh` **rc=0（PASS 52 / FAIL 0）**；`make check`（L1）rc=0；`make check-modules`（L2，`-o install-host` 避写 `.work/build/**`）rc=0（`module checks (L2): PASS`：check-interface ✓ / check-lit 107-107 / check-qemu-smoke ✓ / test-codegen 15-15 / test-elf 5-5 / test-semihost ✓ / picolibc-tests fast fail=0）；`check-knowledge-refs` rc=0；`check_issues.py` rc=0；`check-patch-tree`/`check-no-residue`/`check-tasks` 各 rc=0。
**修改文件**：`tools/infra/check_knowledge_refs.py`（+288/−7：新增 (B) 小节级互指；既有 (A) `.work/**` 判定逐行不动）；`tools/infra/check_issues.py`（+33/−2：`resolved_by` 字段约束）；`.work/evidence/INFRA-080t/run.sh`（一键证据，52 项，非交互/失败非零/`cp`+md5 还原）；**`Makefile` 未改**（两断言本已在 `make check` 既有路径内，无需装配）。
**验收结果**（真实输出，日志 `.work/log/infra/`）：
- ① 真树 `check-knowledge-refs` rc=0：`扫描面 .tao/knowledge/**/*.md（5 文件）；ADR 引用 61（无小节 23 / 占位 0 / 无法判定 0 / 校验 38）；contract 引用 57（无 § 23 / 校验 34）；悬空 0`。
- ① 可达 FAIL：注入 `[ADR-0019 D99]`+`[contract-elf.md §9.9]` ⇒ rc=1，逐条指名 `ADR-0019 D99` / `contract-elf.md §9.9`（`悬空小节级互指`）⇒ `cp`+md5 还原 ⇒ rc=0。
- ① 占位/示意：注入 `[ADR-0003 §DN]` ⇒ rc=0 且计入「占位/示意 (跳过)」明细（不静默放过、不假阳性）；`[ADR-0025 §Consequences]` 命名小节可解析。
- ② 真树 `check_issues.py` rc=0：既有行 `34 open, 7 closed (0 blocking M1-gate: 0)` 保留；新增行 `resolved_by 约束 OK (7 closed → 非空 / 34 open → null)`。
- ② 可达 FAIL：`ISS-200`(closed) `resolved_by`→`null` ⇒ rc=1 `MISSING resolved_by: ISS-200`；`ISS-203`(open)→文本 ⇒ rc=1 `UNEXPECTED resolved_by: ISS-203`；均 `cp`+md5 还原 ⇒ rc=0。
- **L1 生效**：`make check` rc=0（30 s）且输出含 `[INFRA-080t] 小节级互指存在性` 与 `resolved_by 约束 OK`（两断言确在其中执行）；注入小节级悬空时 `make check` **rc=2**。
- **未放宽既有判定**：`.work/**` 悬空 ⇒ rc=1 且指名路径；两处空转守卫 ⇒ rc=1（既有文案 `vacuous: no checkable .work/** refs` 逐字保留）；非法 `status` ⇒ rc=1（`INVALID STATUS`）；`M1-gate` 阻断 ⇒ rc=1（`BLOCKER`）。
**新发现/坑**：① 扫描面按任务书 §接口规范 输出①「**限** `.tao/knowledge/**/*.md`」落地（与「要做」括号里「与 `.tao/contracts/**`」有张力；因合同侧含既存悬空，若纳入则 L1 必红）；**诊断性**（**未**纳入门控，现场 13 条 / 4 类；可复现命令与输出见 `.work/log/infra/INFRA-080t-contracts-diagnostic.log`）：`contract-abi.md:144/345`→`contract-isa.md §5.6`、`contract-elf.md:84`→`contract-isa.md §4.7`、`contract-elf.md:113/154`→`contract-isa.md §4.1.1`（`contract-isa.md` 均无该小节）、`contract-dynlink.md` ×8→`ADR-0018 C6`（`adr-0018` 无 `C6` 标签，C6 归 ABI）；**未改任何正文、不静默加白名单**。② 子设计符 `Dn.m` 口径：`adr-0012` 的 `D3.1` 无独立标题、仅在其 `## 状态说明`/`## 修订` 提及 ⇒ 判据 = 父决策存在 **且 目标 ADR 文件**提及该子设计符（取目标文本，非源文本；自审 finding 1 修正）。
**遗留问题**：① 上述 `.tao/contracts/**` 既存悬空**只报告、未登记 issue**（改知识正文/台账越界）⇒ 建议 architect 收尾时登记；② `make check-modules` 以 `make -o install-host check-modules` 真跑 rc=0（`install-host` 会写 `.work/build/**`，与本任务并发约束冲突故跳过其重建；log `.work/log/infra/INFRA-080t-check-modules.log`）；③ `Makefile` help 文案（「Dangling .work/** reference gate」）未同步新覆盖面（最小改动、非必要，仅披露）。

## 审阅记录

#### 第 1 轮 engineer 自审
**范围**：`tools/infra/check_knowledge_refs.py`（逐行）、`tools/infra/check_issues.py`（逐行）、`.work/evidence/INFRA-080t/run.sh`。**判决：通过（5 finding：4 ✅已修、1 ❌不修；0 未修）**。

| # | finding | 处置 / 复验证据 |
|---|---|---|
| 1 | **高**：`_decision_desig_missing()` 的「目标文件提及」回退误传**源文件**文本（`raw`）⇒ 退化为自指恒真，`Dn.m` 判据实际只剩「父存在」 | ✅已修：改传**目标 ADR 文本**（`adr_cache` 存 `ptext`）。复验：`[ADR-0004 D2.9]`（父 `D2` 在、目标未提及）⇒ rc=1 指名；`[ADR-0012 D3.1]`（目标提及）⇒ 通过；真树 rc=0 |
| 2 | **高**：命名小节正则 `[A-Za-z][A-Za-z]+` 把占位符 `§DN` 误判为命名小节 ⇒ 假阳性 | ✅已修：先判占位（`[A-Z]{1,3}`），命名小节收紧为 `[A-Z][a-z][A-Za-z]*`。复验：`[ADR-0003 §DN]` ⇒ rc=0 + 计入「占位/示意 (跳过)」明细 |
| 3 | **低**：新增「小节级空转守卫」排在 `dangling` 之前 ⇒ 会掩盖 `.work/**` 悬空报告（仅合成树可见） | ✅已修：判定顺序改「先悬空、后空转」。复验：合成树 `.work` 悬空 ⇒ `FAIL (1 悬空 .work/** 引用)`；无引用 ⇒ 仍**原文案** `vacuous: no checkable .work/** refs` |
| 4 | **低**：同一文件被读两遍（`_iter_lines_with_fences` + `raw`），存在竞态/浪费 | ✅已修（并入 finding 1：`_iter_lines_with_fences(text)` 单次读取） |
| 5 | **低**：`check_issues.py` 把空串在 `open` 时视为 null 等价（文件头字面为 "null"） | ❌不修（有意从宽：空串与 null 同为「未填写」；docstring 已注明；`closed` 侧非空判定不受影响） |

**边界/未测输入复核**：`.tao/knowledge/` 缺目录 ⇒ `files=[]` ⇒ 新增守卫生效（rc=1，不静默绿）；`contract-` 通配形（`contract-*.md`、`contract-<名>.md`）不匹配 ⇒ 不假阳性；代码块（``` 围栏）内 token 跳过；`ADR-` 大小写敏感 ⇒ 不误吃小写文件名 `adr-00xx-*.md`。
**防造假**：本区全部反例、还原（`cp`+md5，**未用** `git checkout/restore/stash`）与回绿均为真跑，逐条日志在 `.work/log/infra/`；证据脚本可 `--inject` 单独复跑。

#### 第 1 轮 reviewer 验收
**独立重跑**（workdir=仓库根；快照对账：验收前后 `git status --porcelain -uall` 均空 ✓）：
1. **① 我自己的注入**（`cp`+md5 还原，未用 git 还原；日志 `/tmp/opencode/INFRA-080t/review/`）：
   - 真实引用改错：`milestones.md:40` `ADR-0025 D6`→`D60` ⇒ rc=1 `milestones.md:40 ADR-0025 D60 (目标小节不存在)`；`MEMORY.md:36` `contract-elf.md §1.3`→`§1.39` ⇒ rc=1 指名；还原 md5 一致 ⇒ rc=0 ✓
   - 不存在引用：注入 `[ADR-0026 D9]`+`[contract-isa.md §5.6]` ⇒ rc=1 逐条指名（2 悬空）；还原回绿 ✓
   - 占位/围栏：`[ADR-0003 §DN]`/`[ADR-0019 §N]` ⇒ **rc=0** 且计入「占位/示意 (跳过)」明细（2 条逐条列名）；围栏内 `[ADR-0019 D99]`/`[contract-elf.md §9.9]` ⇒ 不计不报 ✓
   - **非恒真证明**：上述 4 例（engineer 用例之外）改坏即红、指名 token、还原回绿 ⇒ 两断言均有可达 FAIL 路径。
2. **② 我自己的注入**：`ISS-205`(closed) `resolved_by`→null ⇒ rc=1 `MISSING resolved_by: ISS-205`；`ISS-219`(open)→文本 ⇒ rc=1 `UNEXPECTED resolved_by: ISS-219`；md5 还原 ⇒ rc=0 ✓（双向均非恒真）
3. **make check 路径内**：`make check` rc=0，输出 L171 `[INFRA-080t] 小节级互指存在性（…文件 5）` + L215 `check_issues: resolved_by 约束 OK (7 closed → 非空 / 35 open → null)`；`Makefile:446` `check:` 依赖含 `check-knowledge-refs`、`:447` recipe 跑 `check_issues.py`；`Makefile` 0 改动（`git diff HEAD~2 HEAD -- Makefile` 空）✓
4. **现网统计**（现场、非写死）：`.tao/knowledge/**` 5 文件；ADR 61（无小节 23/占位 0/无法判定 0/校验 38）；contract 57（无 § 23/校验 34）；**悬空 0**；issues 35 open/7 closed、**违规 0**（注：完成区引文「34 open」系 ISS-219 登记前的当时实况，良性漂移）
5. **诊断面复核 ≥2 条**（均亲核目标确不存在）：`contract-abi.md:144/345→contract-isa.md §5.6`（isa 仅 §5.1/5.2/5.4，`grep -c §5.6`=0 ✓）；`contract-elf.md:84→§4.7`、`:113/154→§4.1.1`（isa 无 ✓）；`contract-dynlink.md`×8→`ADR-0018 C6`（adr-0018 无 C6 标签 ✓）。诊断命令复跑 = **13 条** ✓。判定：**只报告未改 + 已登记 ISS-219**（bd11564）⇒ **可接受**（符合「不静默改正文/不加白名单」；契约侧扩面属 ISS-219 范围）
6. **门控逐项**：`make check`(L1)=0、`make check-modules`(L2，完整真跑非 `-o` 短路)=0（`module checks (L2): PASS`）、`check-knowledge-refs`=0、`check_issues.py`(python3)=0、`check-patch-tree`=0、`check-no-residue`=0、`check-tasks`=0 ✓
7. **证据脚本**：`./.work/evidence/INFRA-080t/run.sh` rc=0（PASS=52/FAIL=0，与完成区一致）；`--inject` rc=0（PASS=39/FAIL=0）✓。脚本审读：`expect_rc`/`expect_grep` 均可达 FAIL、注入 `assert n==1` 非空、`cp`+md5 还原、计数现场统计、无 `git checkout/restore/stash` ✓
8. **完成区对齐**：`+288/−7`、`+33/−2` 与 `git diff --stat`（295/35 行）对账 ✓；删除行仅文案/格式（`git diff` 核 −7/−2），既有判定（`.work/**` 悬空、空转守卫原文案、`M1-gate`、`INVALID STATUS`）逐条保留 ✓。**遗留判定**：①已由 ISS-219 消解；②`-o install-host` 可接受（我完整 L2 rc=0）；③`Makefile` help 文案未同步 ⇒ **可接受**（非功能性、最小改动，建议后续顺手带上）
9. **ISS-203 闭合建议**（只建议）：两条断言已落地、可达 FAIL 证据齐备（本审独立注入复证）⇒ **建议 `closed` + `resolved_by: INFRA-080t`**。非阻断观察 2 条：`check_issues.py` 无 shebang 须 `python3` 调（既有形态）；`（Cn）` 全角括号设计符形不被小节识别（当前 knowledge 面 0 命中，非现实缺口）。

**判决：Accepted** —— 验收命令块在本人独立重跑下全部通过（rc 逐条如上），硬约束逐条守住（限改两 `.py`、未放宽既有判定、未改知识正文/`spec/`/`contracts/`、计数不写死、L1 装配不动 `Makefile`）。
