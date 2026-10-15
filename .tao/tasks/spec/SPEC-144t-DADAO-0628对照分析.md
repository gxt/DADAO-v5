# SPEC-144t: `DADAO-0628` 对照分析（只读、内容溯源、非执行必需）

**模块**：spec
**项目里程碑**：M8
**依赖**：`ADR-0025`（`§Rationale`「与 `DADAO-0628` 的对照」= 现有**最小**对照，本任务 = 系统化扩写，**不改** ADR 正文）；`ADR-0019 D10` / `ADR-0026`（动态链接）/ `ADR-0027`（compiler-rt）（**只读**交叉引用）；`manifests/references.lock.toml`（`DADAO-0628` 锁条目 = 只读来源真源）；`.cache/refs/DADAO-0628/**`（**只读**工作树，`make fetch-refs` 幂等重建）
**状态**：待开始

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
- **主产出 = 本任务书 `## 对照分析` 节**（6 项 × 5 列 + `file:line` 溯源）。
  **理由**：① `AGENTS.md`「新增文档三问」（能门控机械判？**否**；与既有重复？与 `ADR-0025 §对照` **部分重叠** ⇒ 优先就地承载；只服务当前任务？**否** ⇒ 不属「一律落 `.work/`」）⇒ **倾向不新建顶层知识文档**；② `.tao/knowledge/` **顶层是显式白名单门控**（`tools/infra/check_knowledge_dir.py` `_ALLOWED_FILES` 6 项）⇒ 新增 `ref-*.md` 顶层文件即 **FAIL**，**扩白名单 = 放宽门控 ⇒ 须用户授权**；③ 任务书正文不受「完成区 ≤30 行 / 审阅记录每轮 ≤40 行」限长约束，可承载长对照。
- **结论层落点（必做）**：`milestones.md`「M8 规划区」加 **≤3 行**结论 + 指针（本册 + `ADR-0025 §对照`）。
- **备选（标出、不阻塞）**：若该对照后续需**长期反复引用** ⇒ 迁入 `.tao/knowledge/` **子目录**（子目录不受顶层白名单约束，如 `refs/`）+ 同步引用门控；**是否迁，待用户裁定**（见「待确认项 2」）。

## 待确认项（**标出**，**不阻塞开工** ✗）
1. **分析深度**：主会话倾向「**系统级逐模块**」（= 按上表 6 项逐项对照）；**用户尚未明确** ⇒ **默认按系统级逐模块执行**；若用户要求「逐文件级 / 全仓级」深度 ⇒ 追加深度后另行下发。
2. **产出落点**：任务书内（**默认**）vs `.tao/knowledge/` 子目录（须同步门控/白名单相关处置）。

## 接口规范
- **输入**：`.cache/refs/DADAO-0628/**`（**只读**）；`manifests/references.lock.toml`（`[[reference]] id="DADAO-0628"` / `path` / `repository` / `head` / `reuse`）；v5 侧既有载体（`.tao/adr/*`、`.tao/contracts/*`、`.tao/knowledge/{milestones,lessons,issues}`、`docs/Process-0x`、相关任务书）。
- **输出**：本任务书 `## 对照分析` 节（6 项 × 5 列 + `file:line` + 「内容溯源，非执行必需」标注）+ `milestones.md` M8 规划区 ≤3 行结论 + 指针。
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

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

按轮次追加，每次返工新增一轮。

#### 第 1 轮 engineer 自审

#### 第 1 轮 reviewer 验收
