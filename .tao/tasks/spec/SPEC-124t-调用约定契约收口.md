# SPEC-124t: 调用约定契约收口（`contract-abi §6` 三 `[OPEN]`）

**模块**：spec
**项目里程碑**：M6
**依赖**：`SPEC-122t`（涉决策者须先经 ADR/用户确认）
**状态**：待开始

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
  - **不改 `spec/`**（除非另有授权；本任务默认仅改 `.tao/knowledge/contract-abi.md` 等投影层）。
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
7. **无残留**：`git status --porcelain -uall` 仅本任务应有改动（`.tao/knowledge/contract-abi.md`〔+ `contracts/abi.yaml` 若涉〕 + 本任务书）。

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
