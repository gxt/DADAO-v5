# SPEC-124t: 调用约定契约收口（`contract-abi §6` 三 `[OPEN]`）

**模块**：spec
**项目里程碑**：M6
**依赖**：`SPEC-122t`（涉决策者须先经 ADR/用户确认）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `.tao/knowledge/contract-abi.md §6`（仍 `[OPEN]` 的 **3 项**：① 多返回值声明顺序；② red zone（128B）；③ `i128` 传参/返回约定）。
  - `spec/DADAO-21-ABI-应用程序二进制接口.md §返回值 §多返回值` / `§标量类型返回值`（spec 依据；内部冲突项）。
  - `spec/Process-02-合约编写规范.md`（合约正文口径）。
  - `.tao/knowledge/issues.yaml`（`ISS-005`/`ISS-006` 的 `[OPEN]` 台账）。
  - `INTEG-023k §A（#1 整数完整调用约定）`、`§B`（M6 用户裁定原话）。
- **输出**：
  1. `.tao/knowledge/contract-abi.md §6`：**三 `[OPEN]` 消解**（① 多返回值声明顺序；② red zone 采用与否；③ `i128` 传参/返回约定），**逐条给结论 + 来源**（spec 依据或 ADR/用户决策）。
  2. 派生投影同步：`contract-abi.md` 的 `open_items`/相关索引；如涉 `contracts/abi.yaml` 则同步（以实测为准）。
  3. 供 `LLVM-062t` 的**执行依据**（消解后的调用约定口径）。
- **约束**：
  - `[OPEN]` 消解**必须给依据**（spec，或经用户逐条确认的 ADR 决策）；**不得**凭空定值。
  - **不改 `spec/`**（除非另有授权；本任务默认仅改 `.tao/knowledge/contract-abi.md` 等投影层）。——**已更正（2026-10-09）**：用户授权扩大范围至改 `spec/`（见下条「用户授权说明」），本约束作废。
  - **用户授权说明（2026-10-09）**：用户授权本任务修改 `spec/DADAO-21-ABI-应用程序二进制接口.md` 并同步锁 `manifests/spec-readonly.lock.toml`（改册 + 锁同步纳入本任务范围）。
  - 与 `SPEC-122t`/`SPEC-123t` **同改 `.tao/knowledge/`/`spec/` ⇒ 串行**。
  - 与 `LLVM-062t` 的**依据关系**：本任务收口后 `LLVM-062t` 方可实现（`Spec-first`）。

## 硬约束

- **临时目录** `/tmp/opencode/SPEC-124t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **一键证据脚本** `.work/evidence/SPEC-124t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁 `tee`**。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/spec/SPEC-124t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **三 `[OPEN]` 全消解**：`contract-abi.md §6` 不再含这 3 项 `[OPEN]`；逐条给**结论 + 来源**（给 `grep`/摘录）。
2. **依据充分**：每条消解指明 spec 章节或经用户确认的 ADR/决策；无凭空定值。
3. **投影一致**：`contract-abi.md` 的 `open_items` 等派生索引与 `§6` 一致（给真实输出）。
4. **可作实现依据**：`LLVM-062t` 所需的调用约定口径（多返回值/`i128`/red zone）已在契约中明确可引用。
5. **门控**：`make check` EXIT=0（含 `check-contracts`/`check-spec-refs` 等）。
6. **一键证据脚本**：`.work/evidence/SPEC-124t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检（如把某 `[OPEN]` 还原 ⇒ 断言 FAIL ⇒ `cp`+md5 还原 ⇒ 回绿），给真实输出与退出码。
7. **无残留**：`git status --porcelain -uall` 仅本任务应有改动（**范围已含 `spec/` + 锁**）：`spec/DADAO-21-….md`、`manifests/spec-readonly.lock.toml`、`.tao/knowledge/contract-abi.md`、`contracts/abi.yaml`、`.tao/knowledge/project_M3-codegen-choices.md` + 本任务书。

## 完成区

**测试结果**：`make check` **EXIT=0**（`.work/log/spec/SPEC-124t-make-check.log`：lit 62/62、`check-spec-readonly` 21 册 OK、`repository checks: PASS`）；`make check-spec-refs` **EXIT=0**（790 引用 / Check2=0）；`make check-spec-drift` **EXIT=0**；`make check-patch-tree` **EXIT=0**（2 组件/92 补丁）；一键证据 `run.sh` **RUN_EXIT=0**（`.work/log/spec/SPEC-124t-run.log`：C1–C10 + S1–S7 + INJ0–INJ6 全 PASS）。

**用户裁定原话（2026-10-09，逐条，`lessons §7.3`）**：①「跟主流保持一致，不必只有一个返回值寄存器；……可以最多拿 8 个寄存器来存返回值」②「把返回值寄存器改为 rd8/rb8/rf8」③「K = 8」④「参数和返回值没有规定不能重叠」⇒ 撤销上轮 `n_args+n_ret≤16` 约束（实测该约束当前**不存在**，无需删；新设计返回区 `rd8–rd15` 与参数区 `rd16–rd31` 本就不重叠）⑤「多个返回值正序还是逆序也要规定」⇒ 定为**声明顺序（正序）、自 8 递增** ⑥ red zone **不采用**、`i128` **不支持** ⑦「**不立 ADR**」。

**新语义落点**：`spec/DADAO-21 §返回值`（返回寄存器 `rd8`/`rb8`/`rf8`；多值/聚合**声明顺序自 8 递增**（可观测）；**每 bank K=8**；超 8 ⇒ `sret` 经 `rb16`、后继参数自 `rb17`；返回区/参数区不重叠）＋ 锁 sha256→`96ecc66e…c819`；`.tao/knowledge/contract-abi.md` §4.4 / §4.6（`call Defs`=区间 `rd8–rd15`,`rb8–rb15`）/ §6 表 / §6.1（改引 `DADAO-21`、**删「偏离」段**）/ 附录；`contracts/abi.yaml` `return_values`+`call_defs`；`project_M3-codegen-choices.md` **仅追加修订注记**。

**修改文件**：`spec/DADAO-21-….md`、`manifests/spec-readonly.lock.toml`、`.tao/knowledge/contract-abi.md`、`contracts/abi.yaml`、`.tao/knowledge/project_M3-codegen-choices.md`、`.work/evidence/SPEC-124t/run.sh`（`.work` 不入 git）、本任务书。

**新发现/坑（`rd31/rb31/rf31` 分类）**——**改**（函数返回值约定）：`DADAO-21 §返回值`、`contract-abi §4.4/§4.6/§6/附录`、`abi.yaml return_values/call_defs`、`project_M3`（加注记）。**不改**：寄存器角色表/参数区（`DADAO-21:22/38/50/149-151/231/233/246`、`contract-abi:40/56/68/93/94/167-169/172/177/206/220`）；系统调用约定（`DADAO-21:377`、`DADAO-22`/`DADAO-23`、`contract-see §5`）；semihosting/测试机（`Machine-01:120/122/124/165`、`contract-semihosting`）；汇编示例（`Toolchain-01:205`）。口径冲突：原「聚合总大小 ≤2 字/>64 位⇒sret」与「每 bank 计数」冲突，**按任务以「每 bank K=8」为准**（§6.1 登记，spec 聚合段同步）。

**遗留问题**：① `contract-see §5` / `DADAO-21 §系统调用规范` 返回寄存器仍 `rd31`（系统调用约定，非函数调用 ABI，未改）；② `contract-abi §5` 未涉行仍书「→ M4」（历史措辞）；③ `.tao/knowledge/milestones.md` `ISS-006` 台账未同步（归 `/complete`）。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审范围**：`contract-abi.md` §3/§5/§6 + 头「来源标注」、`contracts/abi.yaml`、证据脚本；逐行审查 + 反例证伪。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 §6 若仅改状态、保留字面 `[OPEN]`，机械验收（grep）易误判 | ✅已修 | §6 全块去字面 `[OPEN]`（改「未决项」）；标题由「`[OPEN]` 汇总」→「契约收口」 | C1 PASS（§6 无 `[OPEN]`，grep rc=1） |
| F2 结论须「可直接照做」（返回寄存器编号/`sret` 位置/>2 字口径） | ✅已修 | 新增 §6.1–§6.3 + 表：`rd31/rb31/rf31`→`rd30/…`、`sret`→`rb16`、>16B 判据 | C2a–C2f PASS |
| F3 用户裁定无 ADR ⇒ `check-spec-refs` Check 2「无引用断言」会亮红 | ✅已修 | 非 spec 依据行标 `[spec-decision]`；可援引 spec 行标 spec ref | `check_spec_refs.py` EXIT=0（Check 2 命中 0） |
| F4 `≤2 字` 与 spec `>64 位⇒sret` 边界冲突若隐去，属掩盖问题 | ✅已修 | §6.1 增「与 spec 的边界关系」显式登记（以用户裁定为准） | §6.1 第 4 行存在；完成区「新发现」披露 |
| F5 派生投影须与 §6 一致 | ✅已修 | `abi.yaml open_items: []`；§3 描述、§5 三行同步 | C3/C4/C5 PASS；`yaml.safe_load` OK |
| F6 证据脚本须能失败（反例门控） | ✅已修 | INJ0–INJ5：注入「走返回寄存器→一律 sret」⇒ FAIL ⇒ `cp`+md5 还原 ⇒ 回绿 | INJ2 FAIL、INJ5 PASS；RUN_EXIT=0 |
| F7 复跑发现 C7 假 FAIL：`git status --porcelain` 对非 ASCII 路径加引号/转义 ⇒ 与白名单不等 | ✅已修 | 三处 `git status` 加 `-c core.quotepath=false` | C7 由 FAIL（extra=转义路径）→ PASS（extra=`<none>`） |

**判决**：7 条 finding 全部 ✅已修，无未修项。范围外既有措辞（§5「→ M4」等）记于完成区「遗留 1」，非本任务缺陷。任务状态置 `待验收`。

#### 第 1 轮 reviewer 验收

**重跑证据脚本**：`bash .work/evidence/SPEC-124t/run.sh` EXIT=0，C1–C8 + INJ0–INJ5 全 PASS（日志 `/tmp/opencode/SPEC-124t-review/run.log`）。

**独立注入反例**：`sed -i 's/不采用/采用/g' contract-abi.md` ⇒ C2e `[FAIL]`（EXIT=1）；`cp`+md5 还原（md5=a44d4bf…，注入前/后相等）⇒ 回绿 EXIT=0（日志 `inject2.log`、`restore.log`）。

**独立复核**：
- ① §6 无 `[OPEN]`；`abi.yaml open_items == []` ✓
- ② §6.1 返回寄存器 `rd31→rd30→…`、`rb31→rb30→…`、`sret` 经 `rb16`、>2 字（>16B）判定口径明确；§6.2 red zone 不采用；§6.3 i128 不支持 ✓
- ③ `spec/` 交集为空 ✓
- ④ `git status` 仅 `contract-abi.md`、`abi.yaml`、本任务书，无残留 ✓
- ⑤ **边界冲突已登记**：spec `>64 位⇒sret` vs 用户裁定 `≤2 字（128 位）⇒返回寄存器`，§6.1「与 spec 的边界关系」显式标注以用户裁定为准 ✓

**门控**：`make check` EXIT=0；`make check-patch-tree` EXIT=0。

**判决：Accepted**

#### 第 2 轮 engineer 自审（rev. 2026-10-09：改册 + 返回寄存器 `rd8/rb8/rf8`）

**自审范围**：`spec/DADAO-21 §返回值`、`contract-abi.md` §4.4/§4.6/§6/附录、`contracts/abi.yaml`、`manifests/spec-readonly.lock.toml`、`project_M3-codegen-choices.md` 注记、`run.sh`；逐行审查 + 反例证伪。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 spec 返回值 intro 仍书「最后一个参数寄存器/逆序」，与改册后语义矛盾 | ✅已修 | `DADAO-21 §返回值` 重写为「固定返回寄存器组 rd8/rb8/rf8 + 自 8 递增 + K=8」 | S1–S7 PASS |
| F2 证据脚本 C2j/S6 用 `\brd31\b` 误伤参数区 `rd16–rd31`（假 FAIL） | ✅已修 | 断言改「无旧返回寄存器 `rd31`/逆序」精确模式 | 复跑 C2j/S6 PASS、RUN_EXIT=0 |
| F3 §6.1「与 spec 的边界关系（偏离）」段就改册后失效 | ✅已修 | 删除该段；来源改引 `DADAO-21 §返回值` | C2k（无「偏离/边界关系」）PASS |
| F4 `call Defs` 仍 `[rd31,rb31]`，与新返回区不符 | ✅已修 | `contract-abi §4.6`＝区间 `rd8–rd15`/`rb8–rb15`；`abi.yaml call_defs=[rd8-rd15,rb8-rb15]` | C3 投影 PASS |
| F5 聚合「总大小≤2 字/>64 位⇒sret」与「每 bank K=8」冲突 | ✅已修 | 统一为「每 bank K=8」，§6.1 登记取代关系；spec 聚合段同步 | C2e/C5/S5 PASS |
| F6 只读册改后未同步 sha256 会致 `check-spec-readonly` FAIL | ✅已修 | 同变更内更新锁 sha256 | C9 PASS；`make check-spec-readonly` EXIT=0 |
| F7 改动须覆盖全仓 `rd31/rb31/rf31` 命中（修一类） | ✅已修 | 逐条分类；非函数返回用途（syscall/semihosting/参数区/角色表）不改 | 分类表见完成区「新发现」 |

**判决**：7 条 finding 全部 ✅已修，无未修项。`make check`/`check-spec-refs`/`check-spec-drift`/`check-patch-tree` 全 EXIT=0。任务状态置 `待验收`。

#### 第 2 轮 reviewer 验收

**重跑证据脚本**：`bash .work/evidence/SPEC-124t/run.sh` EXIT=0，C1–C10 + S1–S7 + INJ0–INJ6 全 PASS（日志 `/tmp/opencode/SPEC-124t-review2/run.log`）。

**独立注入反例**：`sed -i 's/K=8/K=2/g; s/K = 8/K = 2/g' contract-abi.md` ⇒ C2e `[FAIL]`（EXIT=1）；`cp`+md5 还原（md5=`b491e18…`，注入前/后相等）⇒ 回绿 EXIT=0（日志 `inject-run.log`、`restore-run.log`）。

**独立复核**：
- ① `spec/DADAO-21 §返回值`：rd8/rb8/rf8、声明顺序自 8 递增、K=8/每 bank、sret 经 rb16（后继 rb17）、返回区/参数区不重叠 ✓
- ② manifest sha256=`96ecc66e…c819` == 实测 sha256 ✓
- ③ `contract-abi §4.4`（rd8/rb8/rf8）、`§4.6`（Defs=`rd8–rd15,rb8–rb15`）、`§6`（三 OPEN 消解 + K=8 + 无偏离段）；`abi.yaml` return_values/call_defs/open_items 一致 ✓
- ④ 漫游 `rd31/rb31/rf31`（91 命中）：函数返回值用途已改 rd8/rb8/rf8；未改项均为参数区（`rd16–rd31`）、系统调用（`DADAO-22`/`DADAO-23`/`contract-see §5`）、semihosting（`Machine-01`/`contract-semihosting`）、寄存器角色表、汇编示例 ✓
- ⑤ `project_M3-codegen-choices.md` 末尾追加修订注记（`---` 后），正文不追溯重写 ✓
- ⑥ `git status` 仅 6 个预期文件（spec/DADAO-21、manifest、contract-abi、abi.yaml、project_M3、任务书），无越界 ✓
- ⑦ 无 `_tmp/_orig/_rej/_preinject` 残留 ✓

**门控**：`make check` EXIT=0；`make check-patch-tree` EXIT=0。

**判决：Accepted**
