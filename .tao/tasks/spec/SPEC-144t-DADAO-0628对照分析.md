# SPEC-144t: `DADAO-0628` 对照分析（只读、内容溯源、非执行必需）

**模块**：spec
**项目里程碑**：M8
**依赖**：`ADR-0025`（`§Rationale`「与 `DADAO-0628` 的对照」= 现有**最小**对照，本任务 = 系统化扩写，**不改** ADR 正文）；`ADR-0019 D10` / `ADR-0026`（动态链接）/ `ADR-0027`（compiler-rt）（**只读**交叉引用）；`manifests/references.lock.toml`（`DADAO-0628` 锁条目 = 只读来源真源）；`.cache/refs/DADAO-0628/**`（**只读**工作树，`make fetch-refs` 幂等重建）
**状态**：待验收

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

## 对照分析

> **性质**：全节 **内容溯源，非执行必需**（`AGENTS.md`「参考来源与任务自包含」）。0628 侧**只读**（`.cache/refs/DADAO-0628`，锁 `head = 2d270604b778d609e1a09b4047271b5309005ffc`）；**不复制实现**（单条引文 ≤3 行）；**本产出不作任何实现任务的执行依赖**。
> **路径约定**：`0628:` 前缀 = `.cache/refs/DADAO-0628/`；`linux:` 前缀 = `.work/source/linux/`（v5 锁定的内核 `7.2.10`，`commit 7b20d05f…`，可由 `make fetch` 重建）。**全节所有行号均本次现场读取**（`sed -n '<行>p'`），由 `.work/evidence/SPEC-144t/run.sh` 逐条复核（全文 `path:line` 引用 **72** 条全部实读命中，含可达 FAIL 注入）。凡写作 `:N` 而**本条 bullet 内**未带全路径者，均指**同一 bullet 内此前已给出全路径的同一文件**。
> **v5 侧**：只**引用**既有载体（ADR / 契约 / 任务书 / `docs/`），不新建规范正文。

### 汇总（6 项 × 5 列）

| # | 议题 | 它（0628）怎么做 | 我们（v5）怎么做 | 差异 | 是否借鉴 | 风险 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | syscall 层 | `trap cfx_smon`；**自定** ABI `rd16` 号 / `rd17–rd22` 参数 / `rd31` 返回；号表 = Linux **asm-generic** | `trap cfxha, immu18`；`umon(cfx0)`/`jmon(cfx1)` 分发；号 **`rd15`**；参数**按类型分 bank**（`rd16+`/`rb16+`/`rf16+`）；返回 **`rd8`**；errno = `rd8` 负值 | 寄存器约定**全不同**；号表**同源**（见下「号表同源复核」）；入口层次 1 vs 2 | **不借鉴**寄存器约定（v5 真源 = `spec/DADAO-21 §4`）；仅借鉴「`default: -ENOSYS` 显式失败」口径（已在内） | 分 bank + `__dadao_argmask()` 为自造机制 ⇒ 加服务须同步加表项，漏加即指针参数被当整数传的**静默错** |
| 2 | `pk` 路线 | **完全无 `pk`**（全仓 0 命中）；裸加载（`-kernel`/ELF）+ **真内核** Linux 5.4（K0–K4） | **无内核目标**；`pk` 仅作 **Chipyard 参考平台冒烟**且**未闭环**（`PK_EXIT=2`）、已后置 | 同名不同物：0628 无 `pk` 实践，v5 的 `pk` 与内核无关 | **不借鉴**（无可借实践）；其「先 bare-metal 内核态回归再碰真 Linux」方法**仅备将来**，M8 无落点 | v5 `pk` 未闭环 ⇒ 不得判 `ADR-0024` 闭环；**0628 侧 `ADR-0015` 文字与锁文件不一致**（现场见 1 处） |
| 3 | 动态链接 / TLS 承担 | 置于 **kernel 之后**（「真正需要 kernel 级机制的部分」延后） | **无内核** ⇒ `ld.so` = musl 自带 ldso；「内核/加载器侧」整段 = **QEMU user-mode（`P3`）** | 承担者不同（内核 vs musl ldso + `qemu-user`）；但「musl 本体不需 TLS 重定位」结论**两侧同向** | **部分借鉴**（只借「依赖分层」结论面，不借实现）；无落点变更 | `P3` 成**单点**（auxv/`PT_INTERP`/路径解析全在其身）；动态档一到即须动 `crt_arch.h`/`reloc.h` |
| 4 | libc 移植 | musl **1.2.5** + **15** 补丁；`arch/dadao/` = **compile-time skeleton**（自述「linkable/runnable 尚未」）；TP = **`rb4`**；命名寄存器变量绑物理寄存器 | musl **1.2.6** + **16** 补丁（树形）；静态最小集；TP = **`rb3`**；inline asm 只写字面名 + 局部寄存器变量 | 版本/补丁数不同；**TP 寄存器号不同**（`rb4` vs `rb3`）；后端能力不同（0628 时 RB bank 变量被拒，v5 可用） | **借鉴教训面**（已落地 `INFRA-082t`/`INFRA-076t`）；**不引入**其 1.2.5 基线与补丁 | **spec 版本差异 ⇒ 寄存器编号整体错位**：照抄 0628 的 `rb4`-TP 即错；0628 仓内**三套编号并存** |
| 5 | 测试体系 | 4 层 T0–T3（按工具/后端）+ 5 向量 class；T2 = **四方差分**（interp/QEMU/gem5/Sail）；大型集走薄 lit 递归入口、不另封 target | 3 层 L1/L2/L3（按抽象层）+ 门控 3 层（按规模）；三套 × 两档；自建 runner（无内核 ⇒ 上游 harness 不可用） | v5 **无四方差分对应物**（单后端 + 宿主机过渡 oracle）⇒ T2 等价层更薄；大型集封法不同 | **借鉴**（已高位对齐：独立 oracle / 薄封装 / 失败分类有据）；`interp`·`gem5`·`Sail` **不借鉴**（新外部组件须用户裁定） | 单后端盲区；两侧 `make check` **都不跑被测语义** ⇒ 引用其"绿"当能力证据会失真 |
| 6 | 工程流程 / 教训 | `definition-of-done`（7 条 + 明写 compile-only 不算证据）/ `greenfield-charter`（Non-Reuse Rule + 6 条）/ `repository-layout` / `issues.yaml`（open/归档分册）/ `docs/reviews/**` | `AGENTS.md`（规则 ≤2 行 + 门控名）+ `docs/Process-01…07` + `.tao/knowledge/lessons.md`（判据）+ 任务书四态 + 审查者独立验证 + `check_issues.py` 断言 | **同构度最高**；差异在**表述形态**（0628 少量长文档 vs v5 规则/规范/判据/门控分层）；外部规范 pin 门控 vs `spec/` 漂移门控 | **借鉴**（多数已落地）；其 `code-agent/` 目录名**不借鉴**（v5 已有等价物） | 两侧"绿灯含义窄"；0628 的 ADR 文字漂移已见 ⇒ **引用 0628 以锁文件/现场读为准，不以叙述为准** |

### 项 1：syscall 层

**① 它怎么做（0628）**

- 机制 = `trap cfx_smon` → CFXTRAP → **模拟器侧** responder（`0628:docs/adr/0014-libc-syscall-charter.md:19`：「syscall 机制 = SEE `trap cfx_smon`（spec-first，非半主机/MMIO-hack）」；D4 明写 MVP 在 QEMU/gem5 侧、未来换真 monitor firmware：同文件 `:42` / `:44`）。
- 软件 ABI = **其本仓自定**（`0628:docs/adr/0014-libc-syscall-charter.md:14` 自述 wiki 未定义）：号 `rd16`（同文件 `:28`）、参数 `rd17`–`rd22`（`:29`）、返回 `rd31`（`:30`）。
- 号表 = **Linux asm-generic**（`0628:docs/adr/0014-libc-syscall-charter.md:32`：「`write=64` `exit=93` `exit_group=94` `brk=214` `read=63` …」）。
- QEMU 实现取证：`uint64_t sysno = env->rd[16];`（`0628:components/qemu/patches/0014-dadao-trap-syscall.patch:71`）；`case 64: /* SYS_write … */`（`:78`）；`case 93: /* SYS_exit */`（`:97`）；`case 214: /* SYS_brk … */`（`:102`）；`default: ret = (uint64_t)(-(int64_t)38); /* -ENOSYS */`（`:112`–`:113`）；`env->rd[31] = ret;`（`:116`）。
- 其 musl stub 侧同一约定：`rd16 = syscall number (input only)` / `rd17..rd22 = arg0..arg5` / `rd31 = return value (output only)`（`0628:components/musl/patches/0001-dadao-add-arch-dadao-compile-time-skeleton-ML-009a.patch:752`–`:754`）。

**② 我们怎么做（v5）**

- 入口 = `trap cfxha, immu18` 发起 / `escape` 返回；`umon`(`cfx0`)/`jmon`(`cfx1`) 以 `immu18 = 0`（`SBI_*_SYSCALL`）分发，入参 `rd15 = nr`、出参 `rd8 = result`（`.tao/contracts/contract-syscall.md:53`–`:54`）。
- 号在 **`rd15`**、**沿用 RISC-V Linux 编号**（`.tao/contracts/contract-syscall.md:23`；决策 `.tao/adr/adr-0025-m8-scope-linux-compat.md:24`）。
- 参数**按类型分 bank**：数据 `rd16–rd31`、地址 `rb16–rb31`、浮点 `rf16–rf31`，各自独立计数、**不共享槽位**（`.tao/contracts/contract-syscall.md:61`；`read` 例 `fd→rd16`/`buf→rb16`/`count→rd17` 在 `:64`）。
- 返回 = **`rd8`**（`:65`）；errno = **`rd8` 负值**（`:70`，2026-10-14 用户裁定）。
- musl stub 落地（`components/musl/README.md:14`）：`rd15` + `trap cfx_umon, 0` + `rd8` + `__dadao_argmask()`。
- 服务方：`dadao-m1` 上的 `umon` 服务**已由用户裁定撤回**，运行验证移交 **`P3`（`qemu-user`）**（`.tao/knowledge/milestones.md:157`）。

**③ 差异**：寄存器约定**逐项不同**（号 `rd16`→`rd15`；参数单 bank `rd17–22`→按类型三 bank；返回 `rd31`→`rd8`；errno 无载体→`rd8` 负值）；入口层次 0628 单入口 vs v5 `umon`/`jmon` 双入口（`.tao/contracts/contract-syscall.md:55`–`:56`）。**号表本身不构成差异**（见「号表同源复核」）。

**④ 是否借鉴**：**不借鉴其寄存器约定** —— 0628 的 ABI 是其**自选**（`0628:docs/adr/0014-libc-syscall-charter.md:14` 自述 wiki 未定义），且其自家旧项目 ABI 又与现仓不同（其 `ADR-0015 D4` 存档说明：旧项目 `nr=rd15`/`args=rd16..21` vs 现仓 `nr=rd16`/`args=rd17..22`，`0628:docs/adr/0015-kernel-bringup-charter.md:46`）⇒ 无"标准"可照搬；v5 真源 = `spec/DADAO-21 §4`（指针，见 `.tao/contracts/contract-syscall.md:9`）。**借鉴（仅 1 条、且已在内）**：「未实现号一律**显式** `-ENOSYS`，不静默成功」（`0628:components/qemu/patches/0014-dadao-trap-syscall.patch:112`–`:113`）与 v5 `AGENTS.md`「不支持须显式失败」同向，落点 = `.tao/contracts/contract-syscall.md §6`（口径内，**无须新任务**；若将来扩服务，落点 = **`P3`（`qemu-user`）**）。**待立任务**：无。

**⑤ 风险**：v5 的「参数分 bank + `__dadao_argmask()` 按号恢复指针性」是**自造机制**（musl stub 只交 `long`）⇒ **加服务即须同批加表项**，漏加即「指针参数被当整数传」的静默错误（判据 `components/musl/README.md:14`）；0628 单 bank 无此风险（亦无此能力）——**不得**以 0628 的简洁反推 v5 机制冗余。**内容溯源，非执行必需**。

### 号表「同源」结论复核（**双源取证**）

**待复核结论**：0628 用 Linux `asm-generic` 编号；RISC-V(64) 的号表本身即引用 `asm-generic` ⇒ **两侧号表同源**（`write`=64 / `exit`=93）。

**源 A（0628 自述 + 其生成物）**：

- `0628:components/musl/patches/0001-dadao-add-arch-dadao-compile-time-skeleton-ML-009a.patch:327`：「`DADAO syscall numbers = Linux asm-generic numbering (ADR-0014 D2:`」；
- 同文件 `:329`：「`arch/riscv64/bits/syscall.h.in (riscv64 uses the same modern`」 —— 即其号表**逐字复制自 riscv64 的 `bits/syscall.h.in`**（`:330`：「`asm-generic/unistd.h snapshot with no legacy 32-bit-era syscalls), MINUS`」）；
- 同文件 `:331`–`:333`：「`riscv64's own arch-specific tail (its "sysriscv"/"riscv flush icache" vendor syscall range) -- DADAO has no analogous vendor range and none is defined here.`」⇒ 0628 **不设** arch-specific 段。
- 交叉核（其 ADR 原话）：`0628:docs/adr/0014-libc-syscall-charter.md:32` = 「**Linux asm-generic**」。

**源 B（v5 锁定内核 `7.2.10` 现场，证明 RISC-V(64) 号表同源于 `asm-generic`）**：

| 环节 | 现场取证 |
|---|---|
| RISC-V uapi **不自定号**，只按字长转发 | `linux:arch/riscv/include/uapi/asm/unistd.h:20` = `#include <asm/unistd_64.h>` |
| 该头**由生成器产出**（非手写） | `linux:arch/riscv/include/uapi/asm/Kbuild:3` = `syscall-y += unistd_64.h` |
| 生成输入 = **`common,64`** 通用 ABI 表 | `linux:scripts/Makefile.asm-headers:19` = `syscall_abis_64  += common,64` |
| 通用表内容 | `linux:scripts/syscall.tbl:83` = `64	common	write				sys_write` |
| 通用头同值（同一号） | `linux:include/uapi/asm-generic/unistd.h:174` = `#define __NR_write 64` |

**结论**：**成立** —— 0628 的号表**明文派生自 riscv64**，而 riscv64 的 `asm/unistd_64.h` 由内核生成器从 `common,64`（=`asm-generic`）派生 ⇒ **两侧共同上游 = `asm-generic`**，`write=64`/`exit=93`/`exit_group=94`/`brk=214` 等**共同名集上号值必然一致**；**真正差异不在号表，而在寄存器约定（项 1）与「是否另设 arch-specific 段」**：v5 **沿用** RISC-V 的 `riscv_hwprobe`/`riscv_flush_icache`（`.tao/contracts/contract-syscall.md:46`–`:47`），0628 明文**不设**。**内容溯源，非执行必需**。

### 项 2：`pk`（proxy kernel）路线

**① 它怎么做**：**完全没有 `pk`**。本次现场全仓检索（`.md`/`.yaml`/`.toml`/全文件，剔除 `.git`）对 `\bpk\b`、`Chipyard`、`FireMarshal`、`proxy kernel` **均 0 命中**（复核入口：`.work/evidence/SPEC-144t/run.sh --only=pk`，四个模式各 `0 files`）。其路线 = **裸加载 + 真内核**：QEMU/gem5 直接 `-kernel`/ELF 裸加载、**无引导固件层、无 FDT/DTB**（`0628:docs/adr/0015-kernel-bringup-charter.md:28`）；分阶段 **K0–K4**（`:36`–`:40`），其中 `K3` = `arch/dadao` 从零写 + **Linux 5.4** 树（`:39`）、`K4` = `Run /init` 真正跑 **musl 链接的用户程序**（`:40`）；锁条目 `linux` 现场为 `enabled = true`、`commit = "219d54332a09e8d8741c1e1982f5eae56099de85"`、`role = "Linux 5.4 baseline for the fresh DADAO K3 architecture port"`（`0628:manifests/components.lock.toml:56`–`:61`）。

**② 我们怎么做**：**无内核目标**（`.tao/adr/adr-0025-m8-scope-linux-compat.md:28`，用户原话「无内核目标（推荐）」）。`pk` 仅出现在 **Chipyard 参考平台冒烟**语境：M8 判据「参考平台能跑通 `pk`（+ 可选 Linux）并与我们 QEMU 的结果对照」（`.tao/adr/adr-0024-chipyard-baseline.md:38`），且**未闭环**（`PK_EXIT=2`，`.tao/knowledge/milestones.md:130` 待办①；`.tao/adr/adr-0025-m8-scope-linux-compat.md:74`「`pk` 未闭环」）；用户 2026-10-14 裁定 chipyard 后续任务后置于 M8 之后、暂不推进（`.tao/knowledge/milestones.md:134`）。

**③ 差异**：**同名不同物** —— 0628 没有 `pk` 实践（其"加载"角色由真内核承担）；v5 的 `pk` 是**第三方 RISC-V 参考平台**的一致性冒烟，与内核路线无因果关系。

**④ 是否借鉴**：**不借鉴**（0628 无 `pk` 可借；v5 的 `pk` 用途已由 `ADR-0024 D5` 定案且已后置）。**可备将来参照（仅方法、无当前落点）**：其「**先 bare-metal 内核态回归（K2）再碰真 Linux**」的方法论（`0628:docs/adr/0015-kernel-bringup-charter.md:38`，源自其旧项目三次未跑通的教训）—— M8 无内核 ⇒ **无落点**；若将来立内核路线任务，可作方法参照。**待立任务**：无（本任务**不提**变更）。

**⑤ 风险**：① v5 `pk` 未闭环 ⇒ **不得**据此判 `ADR-0024` 闭环（`.tao/knowledge/milestones.md:130`）；② **0628 侧文字与落盘不一致（现场核，1 处）**：其 `ADR-0015 §参考指针` 称「`linux` 组件目前 `enabled=false`」（`0628:docs/adr/0015-kernel-bringup-charter.md:59`），而锁文件实为 `enabled = true`（`0628:manifests/components.lock.toml:57`）⇒ **引用 0628 须以锁文件/现场读为准**。**内容溯源，非执行必需**。

### 项 3：动态链接 / TLS 的承担方式

**① 它怎么做（置于内核之后）**：

- 其 ADR 明文把动态链接与 TLS 归入「**真正需要 kernel 级机制**」一档、**按原计划延后**：`0628:docs/adr/0014-libc-syscall-charter.md:73`（「多线程/信号/`__thread`/动态链接（真正需要 kernel 级机制的部分）仍按原计划延后」）。
- musl 集成阶段划分：「Phase C (threading, signals, `__thread`, dynamic linking) explicitly deferred.」（`0628:docs/development-roadmap.md:329`）。
- 其延后清单原文：`Dynamic linking, signals, atomics, SMP, and user `__thread` TLS relocations`（`0628:docs/development-roadmap.md:629`），理由「only genuinely thread/kernel-dependent features are deferred here」（同文件 `:631`–`:632`）。
- 顺序旁证：该延后清单段落之后**紧接**「`## Kernel bring-up (ADR-0015, 2026-07-18)`」章（`0628:docs/development-roadmap.md:634`，`sed -n '634p'` 现场）；其自身 5 条路线 A–E 的末位是 `kernel`、**动态链接不在路线内**（`:733`–`:734`：`stdio runtime → vfprintf/libcall → optional be99→d3bd causal isolation → mallocng e2e → kernel`）。
- **但**其"TLS 依赖"分两层：musl **本体**静态单线程子集**不等内核**（`TLS is not a blocker`，`:309`；依据 = `contracts/abi/spec.md §1.2` 已定 `rb4 = rbtp` + musl 源码零处 `__thread`，`:310`–`:316`）⇒ 「用户 `__thread` / 动态链接」才需内核。

**② 我们怎么做（无内核 ⇒ 用户态承担）**：`ld.so` = **musl 自带 ldso**（`.tao/adr/adr-0025-m8-scope-linux-compat.md:32`；`.tao/adr/adr-0026-dynamic-linking-behavior.md:21`）；**0628 交给内核的那段责任，v5 交给 QEMU user-mode**——角色表原文：「「内核 / 加载器侧」（auxv 注入、`PT_INTERP` 解释器装载、加载偏置分配、路径解析）| **QEMU user-mode**（`linux-user`，P3）」（`.tao/contracts/contract-dynlink.md:27`）；重定位类型集与编号已定（`contract-dynlink.md §4.3`；`ADR-0019 D10`）。TLS/TP：**TP = `rb3`**、`TLS_ABOVE_TP` 无偏置（`components/musl/README.md:15`）；musl 对 TP + TCB **硬依赖**已查证（`SPEC-140t`，结论见 `.tao/knowledge/milestones.md:31`）。

**③ 差异**：承担者不同（**内核** vs **musl ldso + `qemu-user`**）；但**结论面同向**：0628「musl 本体不需 TLS 重定位」与 v5 `SPEC-140t`「TP/TCB 硬依赖、重定位类型可缓」互为**独立来源的交叉印证**。

**④ 是否借鉴**：**部分借鉴（只借"依赖分层"的结论面）**。① 0628 的「TLS/动态链接按**是否真需 kernel**分层延后」判据，与 v5 `ADR-0025 D5`「先查证再定」+ `SPEC-140t` 已得结论**同向** ⇒ **v5 口径无须改动**；② 0628 **未产出** 可复用的 `ldso`/动态链接实现（其路线里根本没做）⇒ **无实现面可借**；③ 「0628 归内核、v5 归 `qemu-user`」的分工差异**已由 `ADR-0025 D2`/`D6` 定案且可回溯用户原话** ⇒ 本任务**不提变更**。**待立任务**：无（动态档落点 = `P2`/`P3`，已排于 `.tao/knowledge/milestones.md:151`–`:153`）。

**⑤ 风险**：① v5 把「内核/加载器侧」整段移给 `qemu-user`（`P3`）⇒ **`P3` 成为单点**；这与 0628「有真内核兜底」是**不同工程取舍**（非优劣判断），但意味着 v5 动态档的**可达性完全押在 `P3`**；② 动态档一到即须动 `crt_arch.h`/`reloc.h`（`contract-dynlink.md §7` 的偏置由 arch 定值 + 静态档 `tls_cnt = 0`），并连带 `ISS-206`（`.tao/knowledge/milestones.md:171`）。**内容溯源，非执行必需**。

### 项 4：libc 移植

**① 它怎么做（0628）**

- 基线 musl **1.2.5**（tag `v1.2.5`，commit `0784374d561435f7c787a555aeab8ede699ed298`）：`0628:components/musl/README.md:3`（`Enabled at musl 1.2.5 (upstream tag `v1.2.5`,`）+ `0628:manifests/components.lock.toml:48`–`:53`（`name = "musl"` … `commit = "0784374d…"` … `role = "musl 1.2.5 … arch/dadao compile-time skeleton (ML-009a)"`）。
- 补丁数 = **15**（现场 `ls .cache/refs/DADAO-0628/components/musl/patches/*.patch | wc -l`；对照 v5 = **16**）。
- 形态 = **compile-time skeleton**（`syscall_arch.h`/`reloc.h`/`bits/*.h`/`kstat.h`），README 自述「does not yet produce a linkable/runnable libc」（`0628:components/musl/README.md:7`–`:13`）。
- stub 写法：**命名寄存器变量** `register long rd16 __asm__("rd16")` / `: "=r"(rd31) : "r"(rd16)`（`0628:components/musl/patches/0001-dadao-add-arch-dadao-compile-time-skeleton-ML-009a.patch:780`–`:783`），并明说「`rd31` 是专用返回寄存器、与 riscv64/arm64 的 `a0` 复用不同」（`:761`–`:764`）。
- **TP = `rb4`**：`0628:contracts/abi/spec.md:42`（`| rb4      | rbtp     | Thread pointer | — |`）；实现用 `rb2rd rd31, rb4, 1`（`0628:components/musl/patches/0004-dadao-add-arch-dadao-pthread_arch.h-get_tp.s-__set_t.patch:15`，说明见 `:7`）。**且其明确 `__asm__("rb4")` 被 clang 拒绝**（"unknown register name"），故走独立 `.s`（`0628:components/musl/patches/0004-dadao-add-arch-dadao-pthread_arch.h-get_tp.s-__set_t.patch:9`–`:11`）。
- 号表 = 自 riscv64 逐字复制（项 1「号表同源复核」源 A）。

**② 我们怎么做（v5）**

- 基线 musl **1.2.6**（`v1.2.6` ⇒ `9fa28ece75d8a2191de7c5bb53bed224c5947417`）：`manifests/components.lock.toml:212`；组件面 `components/musl/{README.md,changelog.md,patches/,series}`。
- 补丁 = **16**（现场计数；一文件一补丁树形集 + `series` 16 行），范围 = **静态最小集**（`components/musl/README.md:7`–`:9`：`arch/dadao/**` 12 文件 + `src/setjmp/dadao/**` + `src/thread/dadao/__set_thread_area.s` + `configure`）。
- **TP = `rb3`**（`components/musl/README.md:15`；`.tao/contracts/contract-abi.md:53`「`| rb3 | rbtp | thread pointer（TP） |`」）；`__get_tp()` 用 `rb2rd` 读、`__set_thread_area` 是纯寄存器写（README:15）。
- inline asm 口径：**只写字面寄存器名 + 局部寄存器变量绑同一物理寄存器**，理由 = clang DADAO **不能**把 `%N` 代进模板（README「inline asm 口径（重要）」）。
- 号表 stub：沿用 RISC-V 编号，与锁定号表**逐名同值**（`components/musl/README.md:13`：「`bits/syscall.h.in` 与锁定的 RISC-V 号表逐名同值（314 个共同名 0 冲突，现场复算）」）。
- 后端受阻面 = 13 源**显式排除 + 每次构建 `$(info …)` 打印**（README:20），保证**链接期显式失败**而非静默。

**③ 差异**：版本（1.2.5 vs 1.2.6）、补丁数（15 vs 16）、成熟度（compile-time skeleton vs **静态可运行**）；**TP 寄存器号不同**（`rb4` vs `rb3`）；**后端能力不同**：0628 当时 `__asm__("rb4")` 被拒（RB bank 变量不可用）⇒ 走独立 `.s`，而 v5 可用 `__asm__("rd8")`/`__asm__("rb3")` 命名寄存器变量。两侧**独立得出同一工程结论**：「命名寄存器变量绑物理寄存器可行 / 后端缺 `%N` 或 RB 变量能力 ⇒ 用 `.s` 或字面名」，互为印证。

**④ 是否借鉴**：**借鉴教训面（已落地），不引入其实现**。① 已借鉴且已交付：TP 概念与 `__set_thread_area` 寄存器写、musl 源码零 `__thread` 的依赖判定、`-ENOSYS` 显式失败、后端受阻源过滤 —— 落点 = `INFRA-082t`（P1 静态最小集，`已验证`）+ `INFRA-076t`（1.2.6 取源与锁定）。② **不引入** 0628 的 1.2.5 基线与 15 补丁（版本不同、其所据 spec 版本亦不同）。③ 「软 libc 先行去后端风险」的经验，v5 已由 `ADR-0023`（picolibc 上游基线）/`INFRA-068t` 走同一路线 ⇒ **无须新增任务**。**待立任务**：无。

**⑤ 风险（本项最高，含一级警示）**：**spec 版本差异导致寄存器编号整体错位** —— 0628 `rb3 = rbgp` / `rb4 = rbtp`（`0628:contracts/abi/spec.md:41`–`:42`），v5 `rb2 = rbgp` / `rb3 = rbtp`（`.tao/contracts/contract-abi.md:53` + `:211`）⇒ **照抄 0628 的 `rb4` 作 TP 即直接写错寄存器**。更甚者 **0628 仓内三套编号并存**：① 现仓 `rd16` 号 / `rb4`-TP；② 其旧项目 `nr=rd15`/`args=rd16..21`（`0628:docs/adr/0015-kernel-bringup-charter.md:46` 存档说明）；③ 其 `contracts/abi/spec.md` 自身 `rb3`-rbgp/`rb4`-rbtp。⇒ **后续任何引用 0628 的任务必须带 spec 版本号**。**内容溯源，非执行必需**。

### 项 5：测试体系（向量 / benchmark / 大型测试集 / 分层）

**① 它怎么做（0628）**

- **向量设计**：独立预期值原则 —— 「所有测试的期望值必须来自 `contracts/` 或 `tests/vectors/isa/*.yaml`，**不得**从被测实现（LLVM/QEMU）的输出中获取」（`0628:docs/adr/0007-testing-methodology.md:25`–`:26`）；5 个向量 class = `encoding`/`legality`/`semantic`/`boundary`/`overlap`（`:33` 起）；**D4 = 测试先于实现**、向量/失败测试与实现**同批提交**、不单独建"补覆盖度"任务（`:61`）。
- **运行分层**：**T0–T3**（`0628:docs/adr/0012-test-tiering-strategy.md:23`=`T0`「in-tree `CodeGen/DADAO/*.ll` FileCheck + `MC/DADAO` 编码，无模拟器、秒级、每次改动」；`:25`=`T2`「全 E2E + 四方差分（**QEMU + gem5** 双后端），验收门槛 / CI，分钟级」）；核心认知 = 「**分歧是金信号**」（同文件 `:15`）。
- **大型集编排**：**薄 lit 封装**、`tests/lit/E2E/llvm-test-suite/` 即 `tests/lit/E2E/` 普通子目录、随唯一 E2E 入口一起跑（当时 `54/54` 含其 `23/23`），**明确不新增** `make check-suite` 之类重复封装；`make check` **不含 E2E**（`0628:docs/adr/0012-test-tiering-strategy.md:60`）。
- **语料/门控**：`0628:Makefile:41` = `check: manifest-check validate-encoding validate-vectors check-wiki-drift check-wiki-refs check-wiki-refs-abi check-issues`（**结构性**，不跑被测语义）；锁条目 role 原文 = `SingleSource pure-compute regression source (ADR-0012 D4, thin lit wrapper, not upstream CMake/lit harness)`（`0628:manifests/components.lock.toml:37`）、`Embench-IoT 19-benchmark functional correctness corpus (ML-032a)`（同文件 `:45`）。
- **目录与规模（现场计数）**：`tests/{vectors,lit,interface,e2e,runtime,scripts,embench}`；`tests/lit` **171** 文件、`scripts` **54**、`vectors` **13**、`e2e` **3**、`interface` **1**、`runtime` **1**、`embench` **1**。
- 终极目标 = **gcc-c-torture 全量通过 + 失败必有明确理由**，沿用旧工具链 `1617/1708` 的**失败分类方法论**（不抄代码）：`0628:docs/adr/0012-test-tiering-strategy.md:62`–`:72`。

**② 我们怎么做（v5）**

- **三层向量** L1 编码/汇编器（MC）/ L2 CodeGen 结构 / L3 执行语义（独立 oracle；L2「仅锁回归、不证语义」）：`docs/Process-05-里程碑TDD规范.md:13` 起（表头 `:15`、各行 `:17`–`:19`）；规模原则「一能力一向量」（`:38`）；**反例门控 MUST**（`:48`）。
- **门控分层** L1/L2/L3（按规模/耗时）+ 触发点（任务收尾 L2、里程碑/`/complete` L3）：`docs/Process-07-门控分层规范.md:16`（L1 行，「不跑被测语义」）。
- **测试面 = 三套 × 两档**（`embench-iot`：`tools/integ/run_embench_e2e.py`；`libc-test`；`llvm-test-suite`；先静态后动态）：`.tao/knowledge/milestones.md:153`；runner + 首份分类统计 + `unsupported` 逐条有据 = `TESTCASES-045t`（`.tao/tasks/testcases/TESTCASES-045t-两大测试集全量跑.md`）。
- **目录与规模（现场计数）**：`tests/{e2e,llvm,qemu,scripts,vectors}`；`tests/llvm` **174**、`e2e` **34**、`scripts` **25**、`vectors` **20**、`qemu` **1**。

**③ 差异**：① **切法不同**：0628 = 4 层（按**工具/后端**）× 5 向量 class（按**验证目标**）二维；v5 = 3 层（按**抽象层**）× 门控 3 层（按**规模/耗时**）二维。② **v5 无"多独立实现差分"对应物**：0628 的 T2 = interp/QEMU/gem5/Sail **四方差分**，v5 = QEMU system **单后端** + 宿主机过渡 oracle（`docs/Process-05-里程碑TDD规范.md:23` 的 `§2.1` 标注「过渡态、非判据真源」）⇒ **v5 的 T2 等价层更薄**。③ **大型集封装**：0628 挂 lit 递归入口、**不另封 target**；v5 因无内核（上游 harness 依赖 `fork`/`waitpid`/信号）⇒ **自建 runner**，并另立统计/边界声明任务。

**④ 是否借鉴**：**借鉴（多为高位对齐，已无需改动 v5）**：① 「独立预期值 / 不从实现反推」= v5 `AGENTS.md`「Independent oracle」+ `docs/Process-05 §4`，**同源同向**；② 「薄封装、不重复封装同一条命令」= v5「复用优先」；③ 「失败分类有据、不为通过放宽判据」= `TESTCASES-045t` 的 `excluded` 逐条有据 + 覆盖边界声明。**可借鉴但未落地（本任务不擅自扩）**：0628 的 **T0「in-tree FileCheck/MC 秒级层」作为"选错指令/填错立即数"的快回归网** —— v5 有 `tests/llvm/lit/{MC,CodeGen}` 用例面，但**无"每次改动秒级"的独立触发点**（`Process-07` L1 明确排除被测语义）；**是否补，属用户裁定**，可作 `TESTCASES-*` 后续议题。**不借鉴**：`interp`/`gem5`/`Sail` 四方差分——v5 组件锁里**无** interp/Sail，引入 = **新外部组件**（`AGENTS.md`「新组件须问模块归属」+ 大文件下载须用户定源）⇒ **本任务不提**。**待立任务**：无。

**⑤ 风险**：① v5 缺"第 4/5 独立实现" ⇒ **单后端盲区**（0628 的历史 bug 全靠双后端分歧逮出，其 `0628:docs/adr/0012-test-tiering-strategy.md:15` 原文「**分歧是金信号**」）；v5 以「宿主机过渡 oracle + `check-qemu-semantics` 全量」部分替代（`docs/Process-05-里程碑TDD规范.md:23`；`docs/Process-07-门控分层规范.md:18`），**不得**据此认为等价。② **两侧 `make check` 都不跑被测语义**（0628 `0628:Makefile:41`；v5 `docs/Process-07-门控分层规范.md:16`）⇒ **引用对方"`make check` 绿"当作能力证据即失真**（本次分析发现的最易误用点）。**内容溯源，非执行必需**。

### 项 6：工程流程 / 可借鉴的教训

**① 它怎么做（0628）**

- `docs/definition-of-done.md`：7 条 DoD，首条 = 「Its specification clause is named and in the locked scope.」（`:5`），末条 = 「The repository can reproduce the result from clean source commits.」（`:11`），并**明写**「Compilation success, an assembler round trip, or a QEMU-only test is **not** sufficient evidence by itself.」（`:13`）。
- `docs/greenfield-charter.md`：**Non-Reuse Rule** = 「Legacy DADAO implementation code is not copied, cherry-picked, or used as the starting branch. It may be inspected to identify failure modes, missing tests, and useful repository-management patterns.」（`:10`–`:12`）+ 「DADAO semantics come only from the locked specification and accepted contracts.」（`:14`）；6 条工程规则（垂直切片 / 不支持必须显式 / 基线锁全 commit / 生成物不入历史 / 两组件共用契约须 interface test / **禁** compile-only 判完成）。
- `docs/repository-layout.md`：8 类落点（`manifests/`/`components/`/`contracts/`/`tests/`/`scripts/`/**`code-agent/`**= designs/task contracts/reviews/distilled knowledge，`:8`/`.work/**` 五类，`:3`–`:13`），并明写「The repository never tracks upstream source trees or build outputs.」（`:15`）。
- issue 台账：`docs/issues.yaml` **只放 open**、closed 归档 `issues-archive.yaml`（`:11`–`:12`）；现场计数 **open 25 / archive 43**。
- 独立审查文化：`docs/reviews/**` 每任务成对 `*-worker-report-*` + `*-independent-review-*`（现场 ls 数十份，如 `DL-071a-independent-review-20260723.md`）；`code-agent/knowledge/**` = **7** 份 distill（`01-qemu-translate-patterns.md` … `07-abi-call-convention.md`，另有 `README.md`）。
- 门控：`0628:Makefile:41` = `check: manifest-check validate-encoding validate-vectors check-wiki-drift check-wiki-refs check-wiki-refs-abi check-issues`。

**② 我们怎么做（v5）**：`AGENTS.md` = **可执行规则（每条 ≤2 行）+ 门控名/文件指针**，判据层 → `.tao/knowledge/lessons.md`；工程流程规范 = `docs/Process-01`…`07`（补丁组织 / 合约编写 / ADR 编写 / 里程碑归档 / 里程碑 TDD / `spec/` 保护 / 门控分层）；任务书 = `.tao/tasks/<module>/` + 四态状态机（`待开始`/`待返工`/`待验收`/`已验证`）+ 「完成区」+「审阅记录」（engineer 自审 / reviewer 独立验收）；issue 台账 = `.tao/knowledge/issues.yaml`（现场 **51** 条，其中 `closed` **13** 条 —— `check_issues.py` 现场输出 `38 open, 13 closed`）+ `tools/infra/check_issues.py`（断言 `closed ⇒ resolved_by`）；审查 = `.opencode/agents/reviewer.md` + 「可达 FAIL 反例门控」（`AGENTS.md`「验证脚本反例门控」）；组件侧 = `components/*/changelog.md` + `check-component-changelog`。

**③ 差异**：**本项同构度最高** —— 两侧都是「ADRs + 契约 + 上游源码不入库 + 每任务独立 review + issue 台账 + `make check` 门控」。差异在**表述形态**：0628 = **少量长文档**（`definition-of-done`(14 行)/`greenfield-charter`(29 行)/`repository-layout`(17 行)，规则集中）；v5 = **分层**（`AGENTS.md` 规则 + `docs/Process-0x` 规范 + `lessons.md` 判据 + **机械门控**）。**第二处**：0628 把**外部 wiki** 的 pin 当漂移门控（`check-wiki-drift`/`check-wiki-refs`/`check-wiki-refs-abi`）；v5 对应 = `manifests/` 锁 `spec/` 快照 + `check-spec-drift`/`check-spec-readonly`/`check-spec-refs`。

**④ 是否借鉴**：**借鉴（多数已落地，无须改动 v5）**：① 「DoD 里明写 compile-only / 仅文本比对不算证据」→ v5 `docs/Process-05 §2`（「L2 仅锁回归、不证语义」）+ `AGENTS.md`「留证须捕**被检命令自身**退出码」；② 「Non-Reuse Rule（看失败模式、不抄代码）」→ v5 `AGENTS.md`「参考目录只读参考、不复制代码」+ 本任务；③ 「open/closed 分册 + 归档」→ v5 `issues.yaml` + `check_issues.py`（**更严**：`closed ⇒ resolved_by` 机械断言）；④ 「两组件共用契约须 interface test」→ v5 `tests/interface` 面 + 模块门控。**已识别、建议登记为警示（不新增任务）**：0628 在其 `codex` 长跑期出过 **patch 导出/披露纪律漂移**（`0628:docs/development-roadmap.md:738`–`:746`：7 个真实提交**未导出**到 `components/*/patches/`，其中 QEMU 那个以**全零假 commit hash** 的补丁文件背书**脏工作树**（一次 `git checkout`/`clean` 即静默丢数据）；且一个 Blocked 任务的**全局 `-O0` 覆盖被静默基线化**、后续所有对象矩阵数字都建立在它之上）。v5 对应防线已存在（`docs/Process-01` 强制导出 + `check-patch-tree` 断言 + `AGENTS.md`「**禁** `git checkout` 覆盖工作树未提交改动」+ `lessons.md §2`）⇒ **本任务只登记录入「新发现/坑」，交主会话判是否入 `lessons.md`**（工程师**不直接写知识库**）。**不借鉴**：其 `code-agent/` 目录名与四类落点划分（v5 已有 `.tao/{tasks,adr,contracts,knowledge}` 等价物，改名即无收益迁移）。**待立任务**：无。

**⑤ 风险**：① **"绿灯含义窄"两侧同病**（`make check` 均不跑被测语义）⇒ 引用对方绿结果时**不得**当作能力证据（同项 5 风险②）；② **0628 的叙述与落盘会漂移**（本任务现场已见 1 处：`ADR-0015 §参考指针` 说 `linux` `enabled=false`，锁文件实为 `enabled = true`，见项 2 风险②）⇒ **引用 0628 一律以锁文件/现场读为准**；③ 0628 的 6 条工程规则是**单体长文档式**表达，v5 若照其形态集中规则，会**削弱**现有「规则 + 机械门控」的可判性 ⇒ **不建议**照搬形态。**内容溯源，非执行必需**。

### 6 项之外：**必须**覆盖面建议（**列出 + 说明，不擅自扩**）

> 以下为本次现场分析中撞到、但**不属**任务书 6 项范围的面。**仅列出与理由**，**是否覆盖待用户裁定**（不擅自开工、不擅自扩范围）。

1. **HBI §3「硬件复位后运行模式永为 hypv」与最小 hypv→supv 移交桩**（`0628:docs/adr/0015-kernel-bringup-charter.md:30`）：这是 0628 把「裸加载直接进 S-mode」这一**错误假设**纠正出来的**spec 层硬件事实**（其原文：「`裸加载直接进 S-mode` 在当前 spec 下没有对应硬件行为」；须约 15–20 条指令的 `cfx2rc` delegation + 一次 `escape`，已列为其 K1 首项）。**对 M8（无内核）无直接影响**；但**凡将来立内核 / 特权级路线任务（M9+），它是必答前置**。**建议**：若要覆盖，**单立只读查证任务**（对照 v5 `spec/` 对应条款，判 v5 是否有同款口径），**不在本任务内扩**。
2. **外部规范 pin 与漂移门控的逐检查项对照**：0628 = `check-wiki-drift`/`check-wiki-refs`/`check-wiki-refs-abi`（`0628:Makefile:41`）vs v5 = `check-spec-drift`/`check-spec-readonly`/`check-spec-refs` + `manifests/` 锁快照。本任务项 6 只一句带过；若作为**门控设计对照**，需逐检查项 × 双清单对照（0628 `Makefile` 全表 × `docs/Process-07 §1` 全表）。**建议**：列为独立只读任务候选，**不在本任务内扩**。
3. **0628「仓内多套寄存器编号并存」的引用规范**：本任务已在项 1/项 4 风险列点名（现仓 `rd16`/`rb4`-TP；旧项目 `rd15`/`rd16..21`；其 `contracts/abi/spec.md` = `rb3`-rbgp/`rb4`-rbtp）⇒ 任何引用 0628 的后续任务**必须带 spec 版本**。**建议**：若用户要，可单立「引用 0628 注意事项」短条目（落点须用户定，因 `.tao/knowledge/` 顶层为白名单门控），**不在本任务内扩**。

### 待确认项（**标出，不阻塞**）

1. **分析深度**：默认按任务书 6 项**系统级逐模块**执行（本任务书「待确认项 1」），未收到更深（逐文件级 / 全仓级）要求；**用户尚未明确**。
2. **产出落点**：本节落**任务书内**（默认口径，理由见任务书「产出」节）；迁 `.tao/knowledge/` **子目录**（须同步门控）**待用户裁定**。
3. **上节「6 项之外」3 条**是否覆盖，**待用户裁定**。

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
