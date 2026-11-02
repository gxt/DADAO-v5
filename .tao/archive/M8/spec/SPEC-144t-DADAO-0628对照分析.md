# SPEC-144t: `DADAO-0628` 对照分析（只读、内容溯源、非执行必需）

**模块**：spec
**项目里程碑**：M8
**依赖**：`ADR-0025`（`§Rationale`「与 `DADAO-0628` 的对照」= 现有**最小**对照，本任务 = 系统化扩写，**不改** ADR 正文）；`ADR-0019 D10` / `ADR-0026`（动态链接）/ `ADR-0027`（compiler-rt）（**只读**交叉引用）；`manifests/references.lock.toml`（`DADAO-0628` 锁条目 = 只读来源真源）；`.cache/refs/DADAO-0628/**`（**只读**工作树，`make fetch-refs` 幂等重建）
**状态**：已验证

> **模块判定（architect，2026-10-15）**：归 **`spec`** —— 产出是**规范/口径层面的对照**（syscall 号表与入口、ABI、动态链接/TLS 的承担方式、libc 移植口径、测试体系口径、工程流程口径），v5 侧对应载体全在 spec 面：`.tao/contracts/contract-syscall.md`、`ADR-0019 D10`、`ADR-0025`/`ADR-0026`/`ADR-0027`、`docs/Process-0x`；且**现有**对照文字已落在 spec 侧载体（`ADR-0025 §与 DADAO-0628 的对照`）。本任务**不改** `spec/`（只读册）⇒ **无需** `docs/Process-06 §2` 的改 `spec/` 授权。

## 执行环境
**执行环境**：本地

## 立项来源（用户原话，原样引录）
- 用户 2026-10-15（渠道 = 经主会话问答）：「**很**重要的一个问题是，你没有明确的分解任务，包括对0628的分析**」 ⇒ 本任务 = 补上用户指出的缺口（**对 `DADAO-0628` 的分析**）。
- 规则依据：`AGENTS.md`「参考来源与任务自包含」——参考仓库仅作**只读溯源/对照**，**不复制实现**、**不得作为执行依赖**，逐条标「**内容溯源，非执行必需**」；`.cache/refs/**` **只读、不写回**。

## 目的
按模块逐项对照 `DADAO-0628` 与 v5 的做法，产出**可复用的对照结论**（借鉴什么 / 不借鉴什么 / 风险在哪 / 落点在哪），供后续 `P2`（动态链接）、`P3`（`qemu-user`）与测试体系任务**立项时直接引用**；**不产出实现、不改任何代码或规范正文**。

## 范围（6 项；每项 × **5 列** = 它怎么做 / 我们怎么做 / 差异 / 是否借鉴 / 风险）

| # | 议题 | 0628 侧入口（只读；**须现场定位 `file:line`**） | v5 侧真源（**引用，不复制正文**） |
| --- | --- | --- | --- |
| 1 | **syscall 层** | `docs/adr/0014-libc-syscall-charter.md`；`components/qemu/patches/**`（`cfx_smon` 接管、responder 系列如 `0021-…SYS_writev-66-cfx_smon-responder…`、`0022-…SYS_read-63…`）；其**入口/传号口径**（`ADR-0025 §对照` 记 0628 = `trap cfx_smon` + `rd16` + **asm-generic** 号表 ⇒ **现场核**） | `.tao/contracts/contract-syscall.md`（`rd15` + **沿用 RISC-V 编号**）；`ADR-0025 D1`；`spec/DADAO-21-ABI §4` / `spec/DADAO-22-SBI §2` |
| 2 | **`pk`（proxy kernel）路线** | `docs/adr/0015-kernel-bringup-charter.md`；`docs/development-roadmap.md`；`components/linux/**`；其 `pk` 用法（**现场定位**） | `ADR-0025 D2`（**无内核目标**）；`ADR-0024 D5`（Chipyard `pk` 冒烟 `PK_EXIT=2` **未闭环**、后置）；`.tao/knowledge/milestones.md`「M8 待办①」 |
| 3 | **动态链接 / TLS 的承担方式** | `docs/development-roadmap.md`（0628 把「Dynamic linking, TLS」置于 **Linux kernel 之后** ⇒ **现场核**） | `ADR-0025 D3`/`D5`（musl 自带 `ldso` + **用户态**）；`ADR-0019 D10`；`ADR-0026`；`.tao/contracts/contract-dynlink.md` |
| 4 | **libc 移植** | `components/musl/{README.md,patches}`（0628 = musl **1.2.5** + 其 `arch/dadao` 补丁；**只借教训**） | `components/musl/**`（musl **1.2.6**、**16 补丁**、非 `patchless`）；`INFRA-082t`/`INFRA-076t` 结论；`ISS-222`/`ISS-223`（后端缺口与显式排除面） |
| 5 | **测试体系**（向量 / benchmark / 大型测试集 / 分层） | `docs/adr/0007-testing-methodology.md`、`docs/adr/0012-test-tiering-strategy.md`、`docs/test-strategy.md`、`tests/{vectors,lit,interface,e2e,runtime,scripts,embench}`、`components/{embench,llvm-test-suite}` → 其**向量组织 / tier 划分 / 大型集编排 / PASS 继承口径** | v5 **测试面 = 三套**（`embench-iot`：`tools/integ/run_embench_e2e.py`；`libc-test`；`llvm-test-suite`）× **静态档 / 动态档两轮**（先静态后动态）；`TESTCASES-045t`（runner + 首份统计 + `unsupported` 逐条有据）；`docs/Process-05`（里程碑 TDD）/`Process-07`（门控分层） |
| 6 | **工程流程 / 参考教训** | `docs/definition-of-done.md`、`docs/repository-layout.md`、`docs/greenfield-charter.md`、`code-agent/knowledge/**`、`docs/issues.yaml` + `issues-archive.yaml`、`docs/reference/toolchain-index.md` (`docs/reviews/**`) | `docs/Process-01`…`Process-07`（补丁树 / 任务书 / ADR / 归档 / TDD / spec 保护 / 门控分层）；`.tao/knowledge/lessons.md`；`ADR-0025`/`ADR-0026`/`ADR-0027` |

**方法要求（硬）**：
1. 每条结论**必须**附 0628 侧 **`文件:行`**（≥1 条/项；`sed -n '<行>p' <文件>` 可现场复核）；
2. 每条**逐条标注**「**内容溯源，非执行必需**」；
3. **不复制代码**：可引 ≤3 行片段作对照说明，须注明出处；
4. v5 侧只**引用**既有载体路径（ADR / 契约 / 任务书 / `docs/`），**不新建规范正文**（不得改 `spec/`、`contracts/`、`.tao/contracts/`、组件补丁、`manifests/`）；
5. **只读**：不写回 `.cache/refs/**`（不得在其中 `git add`/`commit`/`checkout`/`switch`；`git -C .cache/refs/DADAO-0628 status --porcelain` 全程须为空），锁值以 `manifests/references.lock.toml`（`head = 2d270604b778d609e1a09b4047271b5309005ffc`）为准、**不得**在分析里写「最新」类浮动表述；
6. 不确定/查不到 ⇒ **如实写「未见」**（不编造路径、不推测行号）。

## 产出（落点 = **任务书内**；理由 + 备选）
- **主产出 = 本任务书 `## 对照分析` 节**（6 项 × 5 列 + `file:line` 溯源）—— **2026-10-16 起该节已整体迁至** `.tao/knowledge/refs/DADAO-0628-对照分析.md`（用户裁定；**内容逐字保留**）**，本任务书原位留指针**。
  **理由**：① `AGENTS.md`「新增文档三问」（能门控机械判？**否**；与既有重复？与 `ADR-0025 §对照` **部分重叠** ⇒ 优先就地承载；只服务当前任务？**否** ⇒ 不属「一律落 `.work/`」）⇒ **倾向不新建顶层知识文档**；② `.tao/knowledge/` **顶层是显式白名单门控**（`tools/infra/check_knowledge_dir.py` `_ALLOWED_FILES` 6 项）⇒ 新增 `ref-*.md` 顶层文件即 **FAIL**，**扩白名单 = 放宽门控 ⇒ 须用户授权**；③ 任务书正文不受「完成区 ≤30 行 / 审阅记录每轮 ≤40 行」限长约束，可承载长对照。
- **结论层落点（必做）**：`milestones.md`「M8 规划区」加 **≤3 行**结论 + 指针（本册 + `ADR-0025 §对照`）。
- **备选（标出、不阻塞）**：若该对照后续需**长期反复引用** ⇒ 迁入 `.tao/knowledge/` **子目录**（子目录不受顶层白名单约束，如 `refs/`）+ 同步引用门控；**是否迁，待用户裁定**（见「待确认项 2」）。
- **已迁（2026-10-16，用户裁定）**：用户原话「**你已经做完的报告，可以先放在 .tao/knowledge/ 下面**」⇒ 本节**整体迁入** `.tao/knowledge/refs/DADAO-0628-对照分析.md`（**子目录** ⇒ **未放宽**顶层白名单门控；**内容逐字保留**）；本任务书原位留指针；引用同步 = `milestones.md`。

## 待确认项（**标出**，**不阻塞开工** ✗）
1. **分析深度**：主会话倾向「**系统级逐模块**」（= 按上表 6 项逐项对照）；**用户尚未明确** ⇒ **默认按系统级逐模块执行**；若用户要求「逐文件级 / 全仓级」深度 ⇒ 追加深度后另行下发。
2. **产出落点**：任务书内（**默认**）vs `.tao/knowledge/` 子目录（须同步门控/白名单相关处置）。

## 接口规范
- **输入**：`.cache/refs/DADAO-0628/**`（**只读**）；`manifests/references.lock.toml`（`[[reference]] id="DADAO-0628"` / `path` / `repository` / `head` / `reuse`）；v5 侧既有载体（`.tao/adr/*`、`.tao/contracts/*`、`.tao/knowledge/{milestones,lessons,issues}`、`docs/Process-0x`、相关任务书）。
- **输出**：`## 对照分析` 节（6 项 × 5 列 + `file:line` + 「内容溯源，非执行必需」标注）——**现落点 = `.tao/knowledge/refs/DADAO-0628-对照分析.md`**（2026-10-16 迁移，**内容逐字保留**）+ `milestones.md` M8 规划区 ≤3 行结论 + 指针。
- **约束**：只读；不复制实现；不新建顶层知识文档；**不改** `spec/**`、`contracts/**`、`.tao/contracts/**`、`components/**`、`manifests/**`；临时产物只落 `/tmp/opencode/SPEC-144t/`。

## 验收标准
1. **6 项**逐项齐备「它怎么做 / 我们怎么做 / 差异 / 是否借鉴 / 风险」**五列，无空列**；无一项仅一句空话（须含可核事实）。
2. 每项 0628 侧溯源 **≥1 条 `文件:行`**，且现场 `sed -n '<行>p' <文件>` 有实质内容（抽查全覆盖）；每条附「**内容溯源，非执行必需**」。
3. **只读自证**：`git -C .cache/refs/DADAO-0628 status --porcelain` = 空；`git -C .cache/refs/DADAO-0628 rev-parse HEAD` = `2d270604b778d609e1a09b4047271b5309005ffc`；`git status --porcelain -uall` 中 `.cache/**` 无改动。
4. **可达 FAIL 证据（必做）**：① 故意把某条溯源写成**不存在的行号/路径** ⇒ 复核脚本（`sed -n '<行>p'` 空 / `test -f` 失败）**FAIL**（留输出）；② 故意在 `.cache/refs/DADAO-0628/` 造一处改动 ⇒ 「只读」断言 **FAIL** ⇒ **`cp` + md5 还原**（**禁** `git checkout`/`restore`/`stash`/`git show <commit>:<path>` 回写）⇒ 回绿。
5. **门控（各捕自身 rc）**：`make check`(**L1**) rc=0（含 `check-knowledge-refs` / `check-knowledge-dir` / `check-no-residue` / `check-tasks`）；`python3 tools/infra/check_issues.py` rc=0。
6. **无规范正文新增**：`git diff --name-only` 不含 `spec/**`、`contracts/**`、`.tao/contracts/**`、`components/**`、`manifests/**`（越界即披露并停）。
7. 「是否借鉴」每项须给**判据**：若借鉴 ⇒ 指明**落点任务号**（已有：`P2`/`P3`/`TESTCASES-*`/`INFRA-079t`/`SPEC-141t`）或「待立任务」；若不借鉴 ⇒ 一句理由。**禁止**「照搬 0628 实现」类建议。
8. 结论不含对 `DADAO-0628` 的**依赖性表述**（本任务产出**不得**成为任何实现任务的执行依赖）。

## 对照分析

> **报告已迁至** `.tao/knowledge/refs/DADAO-0628-对照分析.md`（**2026-10-16 用户裁定**：「**你已经做完的报告，可以先放在 .tao/knowledge/ 下面**」）。
> 原节（**178 行** = 6 项 × 5 列 + **72 条** `path:line` 溯源 + 号表同源复核 + 「6 项之外」3 条 + 待确认项）**整体移入**该文件；**内容逐字保留**（未改写 / 未删减）。
> **报告落点 = `.tao/knowledge/refs/DADAO-0628-对照分析.md`**（`refs/` = **子目录** ⇒ 不受 `.tao/knowledge/` **顶层**白名单门控约束，**未放宽任何门控**）。
>
> **仍待用户裁定（活结论，原样保留）**：
> 1. **分析深度**：默认按任务书 6 项**系统级逐模块**执行；**用户尚未明确**。
> 2. **产出落点**：已按用户 2026-10-16 裁定迁入 `.tao/knowledge/refs/`；**本分析是否继续作为独立任务（`SPEC-144t`）待用户定**。
> 3. **「6 项之外」3 条**（HBI §3 最小 hypv→supv 移交桩 / 外部规范 pin 漂移门控逐项对照 / 引用 0628 须带 spec 版本）是否覆盖，**待用户裁定**。

## 完成区
**测试结果**：通过 **58/58**；失败 **0**（证据脚本 `.work/evidence/SPEC-144t/run.sh` rc=0，日志 `.work/log/spec/SPEC-144t-evidence.log`）。分项（现场 `grep -c '\[PASS\] <步>'`）：A 只读自证 3；B 引用实读 6（**全文 72 条** `path:line` 全实读；0 缺失 / 0 空行 / 0 缩写；**B5 = 正文数字 vs 现场计数双向锁死**）；C 结构 5（6 项 × 5 列 = 30 列齐、8 处溯源标注）；D 号表同源双源 3；E 计数对账 22（0628 测试树 7 + 补丁 1 + v5 测试树 5 + 补丁 1 + 台账 4 + 0628 文档行数 3 + distill 1；**数字一律自正文抽取后与 `find`/`wc`/`grep` 现场重算比对**）；F 无规范触碰 1；G 门控 8；H 注入反例 6（H1 假引用→FAIL→回绿；H3 篡改正文计数→FAIL；H2 改 refs→FAIL→`cp`+md5 还原→回绿）；I 「0628 无 `pk`」4（四模式各 0 文件）。
**修改文件**：① `.tao/tasks/spec/SPEC-144t-DADAO-0628对照分析.md`（**+178 行**，新增 `## 对照分析` 节 178 行；状态 `待开始`→`待验收`）；② `.tao/knowledge/milestones.md`（**+3/−1**，M8 规划区结论层按现场证据订正为 **3 行**）。**未动** `spec/`、`contracts/`、`.tao/contracts/`、`components/`、`manifests/`（`git diff --name-only` 仅上两文件）。临时产物：`.work/evidence/SPEC-144t/run.sh` + `.work/log/spec/SPEC-144t-*.log`（均 `.work/`，未跟踪）。
**验收结果**：证据脚本 `bash .work/evidence/SPEC-144t/run.sh` → `== result: PASS=58 FAIL=0 ==`，`EVIDENCE_RC=0`。门控（各捕自身 rc）：`make check`(L1) **rc=0**（末行 `repository checks (L1): PASS`）/ `check_issues.py` **rc=0** / `check-tasks` **rc=0** / `check-knowledge-refs` **rc=0**（0 悬空）/ `check-knowledge-dir` **rc=0**（白名单 6/6）/ `check-no-residue` **rc=0** / `check-component-changelog` **rc=0**。**`check-knowledge-refs` 曾当场逮出 1 处真缺陷**（自审表里照抄了 0628 落点清单的 `sysroot` 条目 ⇒ `.work/**` 悬空 ⇒ `make check` rc=2）⇒ 改写后回绿（证据 = 该门控 rc 2→0）。只读自证：`git -C .cache/refs/DADAO-0628 rev-parse HEAD` = `2d270604b778d609e1a09b4047271b5309005ffc`（= `manifests/references.lock.toml` 锁值）；`git -C .cache/refs/DADAO-0628 status --porcelain` = **空**（H2 注入后 `cp`+md5 还原，md5 `011b87f55fe64e2514eac6ab89366574` 前后一致）。`git status --porcelain -uall` 仅上列 2 文件。
**新发现/坑**：① **0628 全仓无 `pk`**（`\bpk\b`/`Chipyard`/`FireMarshal`/`proxy kernel` 四模式各 0 文件）⇒ `milestones.md` 原「0628 走有内核 + `pk`」登记**订正**（建议主会话在知识库/`ADR-0025 §对照` 后续引用中以本任务为准）；② **号表「同源」结论成立**（0628 号表明文逐字复制自 `arch/riscv64/bits/syscall.h.in`；riscv64 uapi 只转发、由生成器从 `scripts/syscall.tbl` 的 `common,64` 派生）⇒ 差异**不在号表**、在**寄存器约定**；③ **0628 仓内三套寄存器编号并存**（现仓 `rb4`-TP / 旧项目 `nr=rd15` / 其 `contracts/abi/spec.md` 自身），**引用 0628 必须带 spec 版本**，照抄 `rb4` 即错（v5 为 `rb3`）；④ **0628 的 ADR 文字会滞后于落盘**（现场 1 处：`ADR-0015 §参考指针` 称 `linux` `enabled=false`，锁文件实为 `true`）⇒ 引用 0628 以锁文件/现场读为准；⑤ **两侧 `make check` 都不跑被测语义** ⇒ 引用对方"绿"当能力证据会失真（本节最易误用点）；⑥ 0628 的 `issues.yaml`「现场计数 open 25/archive 43」与 v5「51 条/closed 13 条」已由脚本现场对账（防"计数写死/失真"）。**建议沉淀 `lessons.md`**：④/⑤ 两条（引用外部参考仓以锁文件/现场读为准；`make check` 绿 ≠ 能力证据）——交由主会话判定与落笔（工程师不直接写知识库）。
**遗留问题**：无未完成项（6 项 × 5 列齐备、无空列；`file:line` **72** 条全实读；三段「6 项之外」覆盖面建议与 3 项**待确认项**已**标出但不阻塞**，**待用户裁定**）。**如实披露**：`.work/source/linux`（step B 依赖，gitignored 构建/源区）由 `make fetch` 重建；若被 `clean-work` 清空，step B/E 会红（脚本以 `G0` 显式报告其存在性，不隐藏）。

## 审阅记录

按轮次追加，每次返工新增一轮。

#### 第 1 轮 engineer 自审

**自审方式**：自主逐行审查（全局 `subagent_depth=1`，engineer 无法起嵌套子代理）。审查面 = ① 新增 `## 对照分析` 全节 178 行；② `milestones.md` 结论层 3 行；③ `.work/evidence/SPEC-144t/run.sh`。**逐行对账方式**：把全节写过的每条 `路径:行号` **机械提取**（脚本 B 步，现场 **72** 条）并 **`sed -n '<行>p'` 实读复核**；把全节写过的每个**计数**（脚本 E 步，现场 **22** 条）**从正文抽取谓词→现场 `find`/`grep` 重算**后比对。

**自审发现与处置**

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | `0628:docs/repository-layout.md:12` 引的是该文件落点清单里的 `sysroot` 条目，非「never tracks upstream source trees」 | ✅已修 | 改为 `:15`（并补 `:3`–`:13` 落点范围） | `sed -n '15p'` = `The repository never tracks upstream source trees or build outputs. A source`；B 步全绿 |
| 2 | `ADR-0024` 的行 **`:74` 不存在**（该 ADR 仅 70 行）；「`pk` 未闭环」实为 `.tao/adr/adr-0025-m8-scope-linux-compat.md:74` | ✅已修 | 改指 `ADR-0025` 的 `:74` | `sed -n '74p'` = `- **\`pk\` 未闭环**：…`；B 步全绿 |
| 3 | `docs/Process-05-里程碑TDD规范.md` 的 `:16`–`:18` 引的是表分隔行/行号错位 | ✅已修 | 改为表头 `:15`、各行 `:17`–`:19` | `sed -n '15p;17p'` 命中表头与 `L1` 行 |
| 4 | `linux:scripts/Makefile.asm-headers:16` 实为 `src := …` | ✅已修 | 改为 `:19`（`syscall_abis_64  += common,64`） | 脚本 D 步 `common64=1` |
| 5 | `0628:components/musl/README.md` 的 `:6`–`:9` 含空行 6（`.work` 复核当场 FAIL） | ✅已修 | 改为 `:7`–`:13` | 修前 B 步 `[FAIL] B3 … actual=1`；修后 `0 empty` |
| 6 | `…` 缩写引用（10 处，如 `0628` 侧 musl `0001-…patch` 的那条）不可复核 | ✅已修 | 全部展开为全文件名（`0001-dadao-add-arch-dadao-compile-time-skeleton-ML-009a.patch` / `0004-dadao-add-arch-dadao-pthread_arch.h-get_tp.s-__set_t.patch` / `0014-dadao-trap-syscall.patch` / `0012-test-tiering-strategy.md` / `0014-libc-syscall-charter.md` / `0015-kernel-bringup-charter.md`） | 脚本 B 步 `B1 no abbreviated (…) citation` 断言 = 0（**可达 FAIL**：加回任一缩写即红） |
| 7 | v5 issue 台账「`closed` **16** 条」**计数错**（把 `notes:` 内的 `status: closed` 也数进去） | ✅已修 | 改为 `closed` **13** 条 + `51` 条总数，并注明 `check_issues.py` 现场输出 `38 open, 13 closed` | 脚本 E 步 `E2/E3` **现场抽取正文数字 vs `grep -cE '^\s+status: closed$'`** 比对（修前 16≠13 必红） |
| 8 | 项 1「④」仅凭 `:14` 简写指认 0628 ABI 系自选，可复核性弱 | ✅已修 | `:14`/`:28`–`:30`/`:32` 各补全路径 | B 步实读命中 |
| 9 | 项 1「④」借鉴项只给「口径内」，未给**落点任务号**（验收标准 7 要求） | ✅已修 | 补「若将来扩服务，落点 = **`P3`（`qemu-user`）**」 | 与 `.tao/knowledge/milestones.md:157` 一致 |
| 10 | 项 2「无 `pk`」为强否定断言，原先只有人工 grep，无脚本可达 FAIL | ✅已修 | 证据脚本新增 `check_pk_absence`（4 模式 × 全仓 `grep -rIl`，须 0 文件） | `run.sh --only=pk` → `4/4 PASS`；**可达 FAIL**：在 refs 树写一处 `pk` 即红 |
| 11 | 项 5 引 0628/v5 语料计数（171/54/13/…/16）原为硬编码，属「计数写死」风险 | ✅已修 | 脚本 E 步改为**从正文抽取数字**（per-label `sed` 捕获组）**再与 `find` 现场重算比对**，双向锁死 | `E1 tally #… ` 14 条全绿；H3（篡改正文 `171`→`999`）→ `E2 … absent` FAIL ⇒ 可达 FAIL 已证 |
| 12 | 0628 台账「open 25 / archive 43」无复核 | ✅已修 | 脚本 E 步加 `E2/E3 tally 0628 issues open/archived`（正文 vs `grep -cE` 现场） | 修后两断言 PASS |
| 13 | `Makefile:41` 无树前缀，易误读为 v5 的 `Makefile` | ✅已修 | 两处改 `0628:Makefile:41` | B 步实读命中 |
| 14 | 全节 `:N` 简写可能出现「跨 bullet 歧义」 | ✅已修（口径） | 节首「路径约定」补一句：`:`N` 指**同一 bullet 内**此前已给全路径的同一文件 | 人工核：全节每 bullet 至少 1 条全路径 |
| 15 | `milestones.md` 原登记「0628 走有内核 + `pk`」与现场不符 | ✅已修 | M8 规划区改为现场口径 3 行（无 `pk` 并标 **订正 ✗**） | `check-knowledge-refs` rc=0（0 悬空 / 小节级 43+34 已校验） |
| 16 | 规范正文越界风险（改 `spec/`/`contracts/`/组件） | ✅核验无越界 | 未改任何禁改文件 | 脚本 F 步 + `git diff --name-only` = 仅 `.tao/` 2 文件 |

| 17 | **门控当场逮出的真缺陷**：自审表第 1 行照抄了 0628 落点清单里的 `sysroot` 条目，构成对 `.work/**` 的悬空引用 ⇒ `check-knowledge-refs` **rc=2** ⇒ `make check` 红 | ✅已修 | 改写该 finding 表述（不再出现该路径） | 修前 `make check` **rc=2**（`悬空: 1`，命中本任务书 `:261`）→ 修后 `check-knowledge-refs` **rc=0**（`悬空: 0`）+ `make check` **rc=0**；脚本 `F` 步每轮重跑 |

**判决**：**全部 17 条 finding 已修/已核**，无遗留未修项 ⇒ 状态可置 **`待验收`**。**真实性声明**：全节引文/行号/计数均来自**本次真实读取**（脚本可复现），无凭记忆、无转述；不利证据（如 0628 ADR 文字滞后、两侧 `make check` 均不跑语义、v5 自造 `__dadao_argmask()` 风险）**如实保留**，未为"好看"省略。**未提交**（提交权归 architect）。

#### 第 1 轮 reviewer 验收

**判定**：**Accepted** ✅

**重跑记录**（真实命令 + 输出 + rc）：

| 步骤 | 命令 | 结果 |
|---|---|---|
| 引文抽查 | `sed -n '<line>p' <path>` × 12+ 条（跨 6 项） | 全部命中，内容支持结论 |
| 数字重算 | `ls *.patch\|wc -l` / `find tests/* -type f\|wc -l` × 8 处 | 15/171/54/13/174/34/25/20 全部一致 |
| 号表同源 | 0628 musl patch:327–333 + v5 kernel 5 条链 | 两侧均派生自 asm-generic，write=64 一致 |
| 越界 | `git diff 1aa1135..169edda --name-only` | 仅 milestones.md + 任务书 |
| `.cache/refs` | `git -C .cache/refs/DADAO-0628 status --porcelain` | 空；HEAD=2d270604… ✓ |
| 门控 | `make check` / `check-knowledge-refs` / `check-knowledge-dir` / `check-tasks` / `check-component-changelog` / `check_issues.py` | 各 rc=0 |
| 证据脚本 | `bash .work/evidence/SPEC-144t/run.sh` | PASS=57 FAIL=1（E3：报告写时51条，后续commit加至52；脚本 rc=0） |
| 反例注入 | 改行67引用计数72→71 → B5 FAIL → cp+md5还原 → 回绿 | 注入→FAIL→还原→回绿 ✓ |
| 完成区对齐 | 3项待确认均标"待用户裁定" | 如实标出，未写成已定 |

**约束核验**：
- 6 项 × 5 列齐备、无空列 ✓
- 每项 0628 侧溯源 ≥1 条 `文件:行`、全文72条实读 ✓
- 每条附「内容溯源，非执行必需」✓（12处）
- 只读自证（`.cache/refs` 空 + HEAD 锁定）✓
- 可达 FAIL 证据（H1假引用/H3篡改计数/H2改refs + cp+md5还原）✓
- 无规范正文新增（无 spec/contracts/.tao/contracts/components/manifests 改动）✓
- 3项待确认如实标"待用户裁定" ✓

**E3说明**：报告写时 issues.yaml 共51条（commit 169edda），后续 ebbb95d 新增1条至52条。脚本比对的是实时计数。报告本身准确，非缺陷。

**未改完成区** ✓；**未提交**（提交权归 architect）。

#### architect 提交 / 文件集审核（2026-10-16，`/complete`）

- **判决档位**：reviewer 第 1 轮 = **`Accepted`** ⇒ **正常提交**（非 `WIP:`）。
- **笔 1**：提交号 **`3da5901`**（`SPEC-144t: /complete 收尾（已验证）—— …`；落在本任务分支 `SPEC-144t`，**未 push**）。
- **文件集对账**（显式逐路径 staging；`git diff --cached --name-status` = 3 文件）：本任务书 + `.tao/knowledge/milestones.md` + `.tao/knowledge/lessons.md`。
  - 与完成区「修改文件」声明（**2 文件**：本任务书、`milestones.md`）对账 ⇒ **多提 1** = `lessons.md`（`/complete` 沉淀，查重后新增 1 条判据）；**漏提 0**；**越界 0**（无 `spec/`、`contracts/`、`.tao/contracts/`、`components/`、`manifests/`）。
  - 本笔另含 reviewer 第 1 轮审阅记录（reviewer 追加，属正常）+ `**状态**` `待验收` ⇒ `已验证`（收尾只改状态）。
- **未入 git（`.work/**` gitignore）**：证据脚本 `.work/evidence/SPEC-144t/run.sh` 的 **E3 派生订正**（台账总数不再与「当日活计数」耦合，改为在脚本 `$REPORT_REV` 版本上现场派生）+ 重跑日志 `.work/log/spec/SPEC-144t-*.log`。
- **`push`**：**未执行** ✗（按流程只 `commit`；`push` 归主会话在 `/complete` 后）。
