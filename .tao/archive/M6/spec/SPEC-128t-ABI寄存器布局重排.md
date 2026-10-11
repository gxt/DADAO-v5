# SPEC-128t: ABI 寄存器布局重排（spec/契约侧）

**模块**：spec
**项目里程碑**：M6
**依赖**：`SPEC-127t`（聚合传参收口，`已验证`）；与所有改 `spec/`/锁任务**串行**（同改 `spec/DADAO-21` + `manifests/spec-readonly.lock.toml`）
**状态**：已验证

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

**用户裁定（原话留痕，2026-10-09）**：「我想把fp改为rb63…rb63自身就是callee saved」；「想把 rb4-rb7 作为 caller saved regs…现有的 rbgp/rbtp 改为 rb2/rb3」；「只放开 rd4-rd7，rd2 和 rd3 可以加说明：调试/测试保留」；「不立 ADR（只改册+契约）」；「放 M6，排 clang target 之前」。（RF 表不改。）

**测试结果**：全绿。`make check` EXIT=0（末行 `repository checks: PASS`）；`check-spec-readonly` EXIT=0（21 册 OK）；`check-spec-refs` EXIT=0（0 violations）；`check-spec-drift` EXIT=0；`check-patch-tree` EXIT=0（93 patches OK）；证据脚本 `RUN_EXIT=0`。日志 `.work/log/spec/SPEC-128t-*.log`。

**修改文件**：
- `spec/DADAO-21-ABI-应用程序二进制接口.md`（§寄存器规范 RD/RB 两表重排 + `rb63` 条件语义 + `ldm`/`stm` 不变式；RF 表未改）
- `manifests/spec-readonly.lock.toml`（`DADAO-21` `sha256` 同步，`-`/`+` 各 1 行）
- `.tao/knowledge/contract-abi.md`（§1.2/§1.3/§1.6 重写 + §2.1/§3/§4.5/§4.7/§6 最小同步）
- `contracts/abi.yaml`（`registers`/`allocatable`/`non_allocatable`/`callee_saved`/`reserved_registers`/`scalar_calling_convention.callee_saved`/`stack_frame`/`stack`）
- `.tao/adr/adr-0018-m3-codegen-choices.md`（`§C7 D6` 就地修订 + `## 修订` rev. 2026-10-09 + 状态行/状态说明）
- 本任务书；`.work/evidence/SPEC-128t/run.sh`（`.work/` 不在 git）

**验收结果**（真实输出）：
- `DADAO-21` 实测 `sha256=675bbbdc7ab3227b131d3a6ce8ba94a0b7de529b851141074e5877f44d1f39a8` == 锁；`check-spec-readonly: 21 read-only spec volume(s) OK`。
- `check-spec-refs`：`结果: PASS (0 violations)`；`make check` 末行 `repository checks: PASS`。
- 证据脚本 `RUN_EXIT=0`；Phase B 注入（`rb63` 行删 / `rb32–63` 复现 / `rd4–7`→`rd2–7` 保留）⇒ 12 项 FAIL + `check-spec-readonly` 非零；`cp`+md5 还原（md5 相等）⇒ 回绿。
- RF 表 0 变更（脚本：本任务 `git diff` 内 rf 表行变更数=0）；`spec/` 变更仅 `DADAO-21`（须 `git -c core.quotepath=false`；git 默认 quote 非 ASCII 路径，`git diff --name-only | grep '^spec/'` 命中 0）。

**新发现/坑**：`ADR-0018 C7 D6` 现文（`rb2` 始终 reserved）在新布局下事实失真——按用户「不立 ADR」经授权就地修订；`C7 D2`/`D3` 的 FP 寄存器号于 `## 修订`③ 统一声明为 `rb63`（不改其 decision 正文）。任务书验收 #10 所列 `check-contracts` target **不存在**（Makefile 无此 target）；等价合约门控 `check-spec-drift`/`check-spec-refs`/`check-rule-refs` 均绿。

**遗留问题**：
- `spec/DADAO-22-SBI` 示例 5 处用 `rb3` 作 scratch（`set.rb rb3, rd3` + `jump [rb3, rd0, 0]`）；`rb3` 改 TP 后宜改 `rb8+`——改该册须用户授权，不在本任务。
- 后端同步（调用约定 / FP 策略 / CSR / `getCalleeSavedRegs`）归 `LLVM-068t`；本任务 `components/**`/`tools/**`/`tests/**` 未碰。

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：`spec/DADAO-21 §寄存器规范` RD/RB/RF 三表 + `rb63`/`ldm` 段；`contract-abi.md §1.2/§1.3/§1.6/§2.1/§3/§4.5/§4.7/§6`；`contracts/abi.yaml`（YAML 解析 + 逐字段）；`manifests/spec-readonly.lock.toml`；`ADR-0018 §C7 D6`/`## 修订`；对照用户 5 条裁定。**判决：全部处置完毕，转「待验收」。**

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 验收 #2 要求逐字「hasFP 为真时保留」表述 | ✅已修 | spec 段改为「hasFP 为真时保留为 `rbfp`」 | 脚本 `A RB hasFP 为真时保留为(逐字)` PASS |
| `callee_saved.rb=[32,62]` 与 CSR `rb32–rb63` 上界不一致之疑 | ✅已澄清（语义区分） | `contract-abi §1.6/§3` + `abi.yaml` 注释明示「通用块止于 62；`rb63` 条件式 FP、恒 callee-saved，故 ∈ CSR[32,63]」 | 脚本 `CABI rb63 条件占用 FP`/`YAML 全部字段断言`（`csr_rb=[32,63]`）PASS |
| `fp_in_csr` 由 `false`→`true` | ✅已修（语义自洽） | `rb63` ∈ `csr_rb[32,63]` 且恒 callee-saved，故 FP 属 CSR；注释说明作 FP 时由 prologue 保存旧值 | 脚本 YAML 断言 PASS |
| `ADR D2`/`D3` 的 FP 寄存器号未就地改 | ❌不修（按任务） | 任务明令「只在该 decision〔D6〕/该修订条目，不重写其它 decision 正文」；`## 修订`③ 声明 `rb2`→`rb63` | `git diff` ADR 仅 D6 + 修订/状态行；D2/D3 未动 |
| 验收 #9 `git diff --name-only \| grep '^spec/'` 命中 0（git quote 非 ASCII） | ✅已修（脚本口径） | 脚本改用 `git -c core.quotepath=false` 断言仅 `DADAO-21`；完成区披露该坑 | 脚本 `A/B/C spec/ 变更仅 DADAO-21` PASS |
| RF 表「0 变更」缺机械证据 | ✅已加 | 脚本断言本任务 `git diff` 内 rf 表行变更数=0 + 5 条 RF 行为期望值 | 脚本 `A RF rf0/rf1-7/rf32-63`、`RF diff 内 rf 表行变更数` PASS |
| 验收 #10 列 `check-contracts` target | ⏸披露（非阻塞） | Makefile 无该 target；等价合约门控为 `check-spec-drift`/`check-spec-refs`/`check-rule-refs` | 三者 + `make check` EXIT=0 |

#### 第 1 轮 reviewer 验收

**重跑**：`bash .work/evidence/SPEC-128t/run.sh` EXIT=0（Phase A 39/39 PASS，Phase B 13 项预期 FAIL + 6 注入检查 PASS，Phase C 39/39 PASS + md5 还原相等 `e137d1c8`）。

**独立注入反例**：cp 备份 `e137d1c8`→ 删 rb63 行 + rb32-62→rb32-63（旧布局）→ 脚本报 5 项 FAIL（rb32-62 callee / rb63 / hasFP / rb32-63 旧 / 锁 sha256）+ check-spec-readonly 非零→ cp 还原→ md5=`e137d1c8` 相等→ 回绿 EXIT=0。

**独立复核**：① DADAO-21 RD/RB 表与裁定逐条一致（rb2=GP rb3=TP rb4-7 temp rb32-62 callee rb63=rbfp 条件 rd2-3 reserved 调试 rd4-7 temp）；RF 表 git diff 0 变更。② 锁 sha256=实测 `675bbbdc…`，diff 仅 1 行变。③ contract-abi §1.2/§1.3/§1.6/§2.1/§4.5/§4.7 与册一致；abi.yaml 解析 OK 全字段断言通过；grep 旧口径仅命中历史说明段（L292）。④ ADR-0018 §C7 D6 原文保留+追加修订子条+`## 修订` rev. 2026-10-09 含用户原话；D2/D3 一致性于 ③ 声明。⑤ git status 6 个 tracked 文件，无 components/tools/tests，无 _tmp/_orig/_rej。`make check` EXIT=0（68/68 + repository checks: PASS）；`make check-patch-tree` EXIT=0（93 patches OK）。

**注**：HEAD 含 `LLVM-062t` 本地 WIP 提交（后端调用约定，旧布局，预期），非本任务改动。

**判决：Accepted**

#### 第 1 轮 architect 提交（2026-10-09）

- **档位**：reviewer `Accepted` ⇒ **正常提交** `6e78ff6`（`SPEC-128t: ABI 寄存器布局重排…`）。
- **文件集对账**：显式 staging（禁 `git add -A`）后 `git -c core.quotepath=false diff --cached --name-only` = **6 文件**，与完成区「修改文件」声明**逐条一致**（`spec/DADAO-21` + `manifests/spec-readonly.lock.toml` + `.tao/knowledge/contract-abi.md` + `contracts/abi.yaml` + `.tao/adr/adr-0018-*.md` + 本任务书）；**无漏提/多提/越界**，`spec/` 变更仅 `DADAO-21`。
