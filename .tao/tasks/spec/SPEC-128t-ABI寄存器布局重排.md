# SPEC-128t: ABI 寄存器布局重排（spec/契约侧）

**模块**：spec
**项目里程碑**：M6
**依赖**：`SPEC-127t`（聚合传参收口，`已验证`）；与所有改 `spec/`/锁任务**串行**（同改 `spec/DADAO-21` + `manifests/spec-readonly.lock.toml`）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 用户裁定（原话留痕，2026-10-09；`lessons §7.3`）

> 1. 「**我想把fp改为rb63**，在明确需要的时候，rb63是fp，否则，rb63可以由llvm分配；且**rb63自身就是callee saved**」。
> 2. 「想把 **rb4-rb7 作为 caller saved regs**，交给 llvm 使用，**现有的 rbgp/rbtp 改为 rb2/rb3**；这样的**规整性**是极好的」。
> 3. 「**ldm/stm 会用到 32 个寄存器的情况**，应该比较罕见，而且这种情况下，**如果 rb63 正好被用作 fp，也完全可以先保存再恢复**」。
> 4. 「**同样的，rd4-rd7/rf1-rf7 也改为 caller-saved，由 llvm 分配使用**」→ 追问后定：「**可以建一个新任务，只放开 rd4-rd7，rd2 和 rd3 可以加说明：调试/测试保留**」。
> 5. 追问里程碑后定：「**放 M6，排 clang target 之前**」；追问 ADR：「**不立 ADR（只改册+契约）**」。

- **裁定要点**：新角色表（下方）；**RF 表不改**（`DADAO-21` 已把 `rf1–rf7` 定为 caller-saved temp、`rf0`=FCSR；RF 的 M3 边界实现侧放开归 `LLVM-066t`）；`rd2–rd3` **加「调试/测试保留」说明**。
- **「不立 ADR」** = **不新建** ADR；**就地修订既有 `ADR-0018 C7 D6`**（该条现文「`rb2` 始终 reserved（可能是 FP）」在新布局下**事实失真**，不改则与册/契约矛盾）。

## 目标角色表（本任务落册 + 契约）

| 编号 | 新角色 | 旧角色 |
|---|---|---|
| `rb0`/`rb1` | PC / SP（不变） | 同 |
| **`rb2`** | **GP（global pointer）** | 原 `rb3`（`rbgp`） |
| **`rb3`** | **TP（thread pointer）** | 原 `rb4`（`rbtp`） |
| **`rb4–rb7`** | **temporary regs（caller-saved，可分配）** | 原 `rb4`=TP、`rb5–rb7` reserved |
| `rb8–rb31` | 不变（temporary） | 同 |
| `rb32–rb62` | callee saved（不变） | 同 |
| **`rb63`** | **FP（条件占用）：`hasFP` 为真时保留；否则可作通用 callee-saved 分配**（callee-saved = Yes） | 原属 `rb32–rb63` 通用 callee-saved 块 |
| **`rd2–rd3`** | **reserved（调试/测试保留）** | 原 `rd2–rd7` reserved |
| **`rd4–rd7`** | **temporary regs（caller-saved，可分配）** | 原 `rd2–rd7` reserved |
| `rd8–rd63` | 不变 | 同 |
| **RF** | **不改册**（实现侧放开归 `LLVM-066t`） | 同 |

- **净收益**：`rb4–rb7`（+4）+ `rd4–rd7`（+4）= **+8 可分配**（FP 由 `rb2` 移 `rb63` 本身不增减，因 `rb2` 变 GP 仍 reserved）。

## 接口规范

- **输入**：
  - `spec/DADAO-21-ABI-应用程序二进制接口.md §寄存器规范`（现 `rb2`=rbfp、`rb3`=rbgp、`rb4`=rbtp、`rb5–rb7` reserved、`rb32–rb63` callee saved；`rd2–rd7` reserved）。
  - **用户授权原话**（上方；`DADAO-21` 为**上游只读册**，改册须用户事先授权 + **同一变更**内同步 `sha256` 锁，`Process-06`）。
  - `.tao/knowledge/contract-abi.md`（现 §1.2/§1.3/§1.6 + §2.1/§3/§4.5/§4.7 引用 `rb2`=FP/`rb3`=GP/`rb4`=TP 等旧角色）。
  - `contracts/abi.yaml`（`registers`/`allocatable`/`non_allocatable`/`callee_saved`/`reserved_registers`/`scalar_calling_convention`）。
  - `.tao/adr/adr-0018-m3-codegen-choices.md §C7`（`D2`/`D3`/`D6`）。
  - `manifests/spec-readonly.lock.toml`（`DADAO-21` 段 `sha256`）。
- **输出**：
  1. `spec/DADAO-21 §寄存器规范`：**RD 表**（`rd2–rd3` reserved〔说明「调试/测试保留」〕、`rd4–rd7` temporary regs〔caller-saved〕）+ **RB 表**（`rb2`=rbgp、`rb3`=rbtp、`rb4–rb7` temporary regs、`rb32–rb62` callee saved、`rb63`=rbfp〔条件占用；`hasFP` 为真时保留〕）。**RF 表一字不改**。
  2. `.tao/knowledge/contract-abi.md`：§1.2 / §1.3 / §1.6 按新角色表重写；并**最小同步**正文其它处对旧寄存器号的引用（§2.1 `FP = rb2`→`rb63`；§3 派生索引描述；§4.5 callee-saved/caller-saved/CSR/reserved；§4.7 `getFrameRegister = hasFP ? rb63 : rb1` 与 `rb63` 条件保留）。
  3. `contracts/abi.yaml`：`registers.{rd,rb}`、`allocatable.{rd,rb}`、`non_allocatable`、`reserved_registers`、`scalar_calling_convention.callee_saved`（`caller_saved_rd/rb`、`reserved_rd/rb`）与 `stack_frame`（`frame_pointer: rb63`、`get_frame_register: "hasFP ? rb63 : rb1"`、条件保留）同步。
  4. `manifests/spec-readonly.lock.toml`：`DADAO-21` 段 `sha256` **同步**（改毕 `sha256sum` 实测 + 追加一行说明注释）。
  5. `ADR-0018 C7 D6` **就地修订**（`rb2` 始终保留 → **`rb63` 条件保留**）+ `## 修订` 追加 rev. 2026-10-09 条目（用户原话摘要）；**只在该 decision / 该修订条目**，**不重写其它 decision 正文**。
- **约束**：
  - **只动授权范围**：`spec/` 仅允许 `DADAO-21`；其余只读册**一字不改**（`git diff --name-only | grep '^spec/'` 仅 `DADAO-21`）。
  - **RF 表不改**：`spec/DADAO-21 §RF寄存器` 与 `contract-abi §1.4` 逐条不变；RF 实现侧放开**不属本任务**（归 `LLVM-066t`）。
  - **不立新 ADR**（用户裁定）；仅就地修订 `ADR-0018 C7 D6`（事实已变，不改则失真）。
  - **ADR 一致性**：`C7 D2`/`D3` 以 `rb2` 指代 FP 寄存器；D6 修订后须保证 ADR 内不自相矛盾——最小做法 = 在 `## 修订` 条目显式声明「FP 寄存器由 `rb2` 改为 `rb63`；`C7` 中作为 FP 的 `rb2` 一并理解为 `rb63`（策略语义不变）」。**若** engineer 判定须就地改 `D2`/`D3` 的寄存器号方可自洽，属同一授权（用户原话已覆盖），须在完成区披露。
  - **`rb63` 条件语义**：`hasFP` 为真 ⇒ `rb63` 保留为 FP（prologue/epilogue 保存/恢复旧 `rb63`）；否则 `rb63` 为**通用 callee-saved 可分配**（∈ CSR）。**`rb63` 恒为 callee-saved**（用户原话）。
  - **`ldm/stm` 不变式**（用户裁定 3）：`rb63` 是 RB 组最高编号 ⇒ 批量保存 callee-saved 时 `immu6` 连续区间**不能从 `rb63` 往上展开** ⇒ 须**排除 FP** 或「先保存再恢复」；契约正文须登记该不变式。
  - **不含实现**：`components/**`/`tools/**`/`tests/**` 归 `LLVM-068t`；本任务 `git diff` 与实现侧交集为空。
  - 只读册改动**必须同一变更**内同步 `sha256` 锁（`Process-06`）。
  - 与 `SPEC-123t`/`SPEC-124t`/`SPEC-126t`/`SPEC-127t` **串行**（同改 `spec/`）。
  - 计数口径**派生自单一真源、不硬编码**。
  - 与 `SPEC-124t`（返回 `rd8/rb8/rf8`、K=8）已定口径**不冲突**（本任务只改**分配/角色**，不动返回值约定）。

## 硬约束

- **临时目录** `/tmp/opencode/SPEC-128t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **一键证据脚本** `.work/evidence/SPEC-128t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁** `tee`。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/spec/SPEC-128t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **RD 表**：`DADAO-21` 中 `rd2–rd3` = reserved（含「调试/测试保留」表述）、`rd4–rd7` = temporary regs（caller-saved）；`rd0/rd1/rd8–rd15/rd16–rd31/rd32–rd63` 逐条未变（给 `git diff` 对账）。
2. **RB 表**：`rb2`=rbgp、`rb3`=rbtp、`rb4–rb7`=temporary regs、`rb32–rb62`=callee saved、`rb63`=rbfp（FP 条件占用；含「`hasFP` 为真时保留」表述）；`rb0/rb1/rb8–rb31` 逐条未变。
3. **RF 表未改**：`git diff` 的 `DADAO-21` RF 段（`rf0`–`rf63`）**0 变更**（给出对账）。
4. **contract-abi 同步**：§1.2/§1.3 与新册一致；§1.6 可分配含 `rd4–rd7`/`rb4–rb7`、不可分配含 `rd2–rd3`/`rb2`(GP)/`rb3`(TP)、`rb63` 为**条件保留**（非无条件不可分配）；§4.5/§4.7 的 CSR/`getFrameRegister`（`hasFP ? rb63 : rb1`）与 `rb63` 条件保留表述一致。
5. **派生投影同步**：`contracts/abi.yaml` 与 `contract-abi.md` 一致（`registers`/`allocatable`/`non_allocatable`/`callee_saved`/`reserved_registers`/`scalar_calling_convention.callee_saved`/`stack_frame`）；YAML 可解析。
6. **`rb63` 条件 + `ldm/stm` 不变式**：册/契约中登记「`rb63` 恒 callee-saved；`hasFP` 真 ⇒ 保留为 FP；批量保存须排除 FP（`immu6` 连续区间不可从最高编号向上展开）或先保存再恢复」。
7. **ADR 修订**：`ADR-0018 C7 D6` 就地修订（`rb2` 始终保留 → `rb63` 条件保留）+ `## 修订` rev. 2026-10-09（含用户原话摘要）；ADR 内不自相矛盾（D2/D3 的 FP 寄存器号一致性已声明）。
8. **锁同步**：`DADAO-21` 段 `sha256` == 实测；`make check-spec-readonly` EXIT=0；**未改册** `sha256` **逐条未变**（`git diff` 中既有 `sha256` 行 `-`/`+` 仅 1/1）。
9. **授权范围**：`git diff --name-only | grep '^spec/'` 仅 `spec/DADAO-21-ABI-应用程序二进制接口.md`。
10. **门控**：`make check` EXIT=0（含 `check-spec-refs`/`check-spec-readonly`/`check-contracts`）。
11. **一键证据脚本**：`.work/evidence/SPEC-128t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检（如把 `rb63` 改回 `rb2` ⇒ 断言 FAIL ⇒ `cp`+md5 还原 ⇒ 回绿），给真实输出与退出码。
12. **无残留**：`git status --porcelain -uall` 仅本任务应有改动（`spec/DADAO-21-*` + `manifests/spec-readonly.lock.toml` + `.tao/knowledge/contract-abi.md` + `contracts/abi.yaml` + `.tao/adr/adr-0018-*.md` + 本任务书）；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区

**测试结果**：

**修改文件**：

**验收结果**：

**新发现/坑**：

**遗留问题**：
- **可选遗留（不本任务做，改该册需授权）**：`spec/DADAO-22-SBI` 示例用 `rb3` 作 scratch（`set.rb rb3, rd3` + `jump [rb3, rd0, 0]`）；`rb3` 改 TP 后，改用 `rb8+` 更合适——记为遗留，改该册须用户授权。

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
