# ADR-0033: ansibench 上游选择、commit 锁定与语料改动边界

**状态**：Accepted
**日期**：2026-10-20
**决策者**：用户（`D1`–`D5` 2026-10-20 逐条确认；原话逐字见 `## 状态说明`）
**关联**：`ADR-0005`（组件锁多源；`manifests/components.lock.toml`）、`ADR-0002`（构建编排：`.cache/<name>.git` bare mirror + `.work/source/<name>`）、`ADR-0022`（embench-iot 上游选择先例）/`ADR-0023`（picolibc）/`ADR-0025 D6`（libc-test 语料先例）、`TESTCASES-055t`（落点册）、`.tao/contracts/contract-abi.md §4.1`（三 bank 参数分配：`rd`/`rb`/`rf` 独立计数）

> **边界（本笔）**：**未改** `spec/` ✗、**未改** `contracts/**` 或 `.tao/contracts/**` ✗、**未改** `components/**` ✗、**未改**任何任务书 `**状态**` ✗。本 ADR 只记**决策 / 理由 / 被否 / 落点**（`docs/Process-03`「ADR 不承载规范正文」）。**与 `ADR-0022` 的差别**：该条把锁字段填写留给后续任务，本条因用户要求「先走通第一步」⇒ 锁条目 `[[component]] name = "ansibench"` 由 architect 随本 ADR 同一提交落地（`D5`），执行者只需 `make fetch`。

## Context（背景）

### 现场事实（2026-10-20 实测，勿重查）

- 仓库 **`https://github.com/nfinit/ansibench.git`**；pin = **`ef90abd09d7b7bb1f2809f896d6f67fb9724bebe`** = `refs/heads/master` tip（= `HEAD`，最新提交日期 **2026-01-12**「Fixed makefile argument patterns…」）；**该仓库无任何 tag**。
- 体量 **1.8 MB**、**23 个 `.c`**。顶层目录 = `coremark` `dhrystone` `hint` `linpack` `nbench` `stream` `tripforce` `whetstone`（**8 个基准**）+ `utilities` `mk`（支撑）。
- **构建机制**：每个基准目录用**小写 `makefile`**，以 `cc=` 变量选择 `mk/$(cc)/{stdflags.mk,opt/$(opt).mk,<bench>/stdflags.mk}` 片段，形如 `-include ../mk/$(cc)/…`；仓库内**只有 `mk/gcc`、`mk/hp-c`、`mk/vac` 三套**。缺少 `mk/dadao` 时 `-include` **静默跳过**（不报错）⇒ **不改语料也能用 `make CC=<安装根 clang>` 驱动**。
- **仓库内无任何 golden / expected 输出**（0 个期望值文件）；**唯一自校验** = CoreMark 自带 CRC（⇒ 唯一真 oracle）。`dhrystone`/`whetstone`/`linpack`/`stream`/`nbench`/`hint`/`tripforce` **只打印计时数字** ⇒ 只能判「跑完 / 崩 / 超时」。
- **渠道现状（2026-10-20 实测）**：直连 `github.com` 的 `git ls-remote` **超时**（`timeout 40` ⇒ rc=124）；走 `gh-proxy.com` 前缀 **rc=0** 且回报 `HEAD` = `refs/heads/master` = `ef90abd0…`（与 pin 一致）⇒ 见 `D5` 附注的 `[[component.source]]` 两个条目。

### 用户原话（**逐字引录**）

> 「创建任务，下载并测试：https://github.com/nfinit/ansibench；就用这个仓库最新的commit锁定即可」

> 「testcases，先走通第一步，是否能做基线对比，分析后再说」

> 「ADR-0033：根据需要可以做改动，尤其是注意rd/rb参数的问题」

> 「A」

### 与既有语料的分工（**不重叠**）

- `llvm-test-suite`（`ADR-0022` 同批语料，pin `2919e551…`）= **编译器正确性与回归**；
- `libc-test`（`ADR-0025 D6`，pin `b7ec4679…`）= **C 库一致性**；
- **ansibench = 计时 / 冒烟**（`D3` 的判据边界即由此推出）。

## Decision（决策）

**D1 — 上游选择**
采用 **`https://github.com/nfinit/ansibench.git`**。理由：纯 ANSI C（C90）**计时型**基准集合，8 个（`coremark`/`dhrystone`/`hint`/`linpack`/`nbench`/`stream`/`tripforce`/`whetstone`），1.8 MB / 23 个 `.c`；与既有语料**分工不重叠**（`llvm-test-suite` = 编译器正确性与回归；`libc-test` = C 库一致性；ansibench = **计时/冒烟**）。

**D2 — 锁定值**
精确 commit **`ef90abd09d7b7bb1f2809f896d6f67fb9724bebe`**（= 当时 `refs/heads/master` 的 tip；该仓库**无 tag**）；`shallow = false`（1.8 MB，全量克隆成本可忽略，避免「锁分支 tip 却浅克隆」的漂移歧义）；`patchless = true`；`role = "ANSI C benchmark corpus"`。

**D3 — 用途与判据边界**
**仅作计时/冒烟语料，不作正确性 oracle** —— 唯一例外是 CoreMark **自带 CRC 自校验**；qemu 用户态计时**不代表真机性能**，只允许**相对比较**；任何性能数字必须标注运行环境与方法。

**D4 — 语料改动与归因（用户裁定的修订版）**
语料原则上保持上游原样，构建用 `make CC=<安装根 clang>`；**但允许最小必要补丁**（一文件一补丁 + `series`），补丁**仅限**因 **bank 分离 ABI / C90 UB** 导致的 `int`↔指针失配，且每个补丁必须写明「原代码为何违 C 标准或与 ABI 不兼容」；**任何失败必须逐条归因三类** —— ①编译器/后端缺陷 ②语料 UB（含隐式声明、无原型）③**`rd`/`rb` bank 失配** —— **不得混类**，**不得**把 ②③ 记成 ①。

**D5 — 启用与门控范围**
本 ADR 立后 `manifests/components.lock.toml` 条目 `enabled = true`；但**不纳入 L1/L2/L3 门控**，直到基线分析结论确定；纳入门控须另立决策。

> **D5 附注（渠道，实测支撑）**：按 `libc-test` 形态登记两个 `[[component.source]]` —— `gh-proxy`（`https://gh-proxy.com/https://github.com/nfinit/ansibench.git`，`source[0]`，`make fetch` 默认）与 `github`（`https://github.com/nfinit/ansibench.git`，命名备份，`COMPONENT_SOURCE_ANSIBENCH=github` 选用）；依据 = 上文「渠道现状」的 rc=124 / rc=0 实测。**不写** `patch_dir`/`patch_series`（`patchless` 声明它们会被 `manifest-check` 判错），**不写** `shallow_ref`（pin = 分支 tip，无 tag）。

## Rationale（理由）

- **D1**：ansibench 是**纯 ANSI C（C90）、纯计时**的老牌基准集，体量小、依赖少（无第三方库），正好填补「计时/冒烟」这格；与 `llvm-test-suite`（正确性/回归）与 `libc-test`（C 库一致性）**不重叠**（用户已定「testcases」模块归属）。
- **D2**：用**精确 commit** 而非 tag/branch（`ADR-0005`）；因该仓库**无 tag** 且 pin = 分支 tip，浅镜像（`--depth 1 --branch master`）会随上游推进**丢掉 pin**（同一理由见 `libc-test` 条目注释）⇒ `shallow = false` 换可复现性，1.8 MB 成本可忽略。`patchless` 与 `llvm-test-suite`/`libc-test` 同类：**参考/语料输入**，不是 v5 交付组件。
- **D3**：语料无 golden（实测 0 个期望值文件），除 CoreMark 外**没有语义 oracle**；把计时数字当正确性证据会把「跑得快」误读成「算得对」，故**禁用**其作正确性 oracle；qemu 用户态计时与真机差距大，只可**相对**比较。
- **D4**：`rd`/`rb` **分 bank**（`contract-abi.md §4.1` 三 bank 独立计数）使「`int` 与指针混用/截断」类 C90 老代码更容易暴露 —— 若一律禁止改语料，这类失败会**无法定位**；若一律允许改语料，又会把编译器缺陷掩盖成语料问题。故**放开最小必要补丁 + 强制三类归因**：补丁须自证「原代码违标准或违 ABI」，失败须**逐条分类且不得混类**（**禁**把 ②③ 记成 ①），保「语料问题 vs 后端缺陷」可分辨。被否方案见下。
- **D5**：门控里放一套**尚未分析过基线**的计时语料，会把「计时波动」变成红灯来源（不稳定门控）；故先**只启用条目**、不入门控，基线结论出来后再议。

## 被否方案（已拒绝）

- **免 ADR、以用户原话直接授权**：用户已指定要 ADR-0033（`D1`–`D5` 逐条确认），且「选上游 + 锁 commit」命中 `docs/Process-03` 判据 1/4。
- **`shallow = true` + `shallow_ref = master`**：无 tag、pin = 分支 tip ⇒ 浅镜像只跟随被跟踪 ref，上游一推进即**丢锁 commit**（可复现性归零）。
- **`patch_dir` 空目录**（照「有补丁集但暂时为空」形态）：会让 `check-patch-tree` 期待 `series`，且与「语料参考输入」的语义不符；`patchless = true` 才是既有先例（`libc-test`/`llvm-test-suite`/linux/chipyard）。
- **语料绝对零改动（原派单口径）**：见 `D4`；用户裁定改为「允许最小必要补丁 + 三类归因」。
- **把 ansibench 直接纳入 L1/L2/L3**：见 `D5`（基线未分析 ⇒ 不稳定门控）。

## Consequences（影响）

- **锁条目**：`manifests/components.lock.toml` 新增 `[[component]] name = "ansibench"`（`enabled = true`、`shallow = false`、`patchless = true`）+ 两个 `[[component.source]]`（见 `D5` 附注）；`make manifest-check` 仍须 rc=0。
- **`TESTCASES-055t`**：执行者 `make fetch` ⇒ 裸仓库 `.cache/ansibench.git` + 干净检出 `.work/source/ansibench`（detached 在 pin）；随后 8 基准构建 + `qemu-dadao` 实跑；**第一步 = 走通 + 基线对比只分析**。
- **门控**：`check-patch-tree` 跳过 `patchless` 组件 ⇒ 组件数/补丁数**不变**（ansibench 不进补丁树）；ansibench **不进** L1/L2/L3。
- **可复现性**：组件不入库、按需 `make fetch`；**升级 commit / 改判据边界 / 纳入门控 ⇒ 新增 ADR 或标 `Superseded`**（`docs/Process-03`）。
- **失败处置约束**：任何基准失败须按 `D4` 三类**逐条归因**，禁混类；需要改语料时补丁须写明「原代码为何违 C 标准或与 ABI 不兼容」。
- **不变**：不改 `spec/`、`contracts/**`、`components/**`；不引入 ansibench 之外的基准套件。

## 状态说明

**Accepted（2026-10-20）**：`D1`–`D5` 已由用户**逐条确认**，无否决未处置（`D4` 为**修订版**口径 —— 由「不改语料」放为「最小必要补丁 + 三类归因」）。

- **判定来源（用户原话，逐字）**：
  - 「创建任务，下载并测试：https://github.com/nfinit/ansibench；就用这个仓库最新的commit锁定即可」⇒ `D1`/`D2`（上游 + 最新 commit 锁定）。
  - 「testcases，先走通第一步，是否能做基线对比，分析后再说」⇒ `D3`（只作计时/冒烟；基线对比只分析）。
  - 「ADR-0033：根据需要可以做改动，尤其是注意rd/rb参数的问题」⇒ `D4`（**修订版**：允许改语料，重点 bank 失配）。
  - 「A」⇒ 对逐条确认的**整体确认**（`D1`–`D5` 全部）。
- **变更流程**：决策变更（升级 commit / 放开或收紧语料改动 / 纳入门控）时**新增 ADR 或标注 `Superseded`**；经授权的就地修订须用户逐条确认（`docs/Process-03-ADR编写规范.md`）。
