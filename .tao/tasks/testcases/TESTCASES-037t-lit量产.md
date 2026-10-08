# TESTCASES-037t: lit 量产（骨架生成 + 期望机械派生，禁反填）

**模块**：testcases
**项目里程碑**：M6
**依赖**：`LLVM-062t`（整数调用约定）、`QEMU-052t`（load_elf）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `contracts/opcodes.yaml` / `contracts/legality_rules.yaml`（**单一真源**）。
  - `spec/Process-05-里程碑TDD规范.md`（三层向量 + 反例门控）、`spec/Process-01-组件补丁组织与构建编排.md`。
  - 既有 lit 体例：`tests/llvm/lit/**`（MC/CodeGen/E2E）、`tests/e2e/lit/**`。
  - `INTEG-023k §A（#19 lit 量产）`（骨架 agent 生成 + 期望值从 `spec`/`contracts` **机械派生**、**禁从 `llc`/QEMU 反填**；目标**数百**；分层：**快档入 `make check`、全量档 opt-in**）。
- **输出**：
  1. **骨架生成器**（落 `tools/testcases/`，随产物入库）：由模板/真源批量生成 lit 用例**骨架**。
  2. **期望值机械派生**：CHECK 串/期望值**由脚本从 `spec`/`contracts` 派生**（**禁**从 `llc`/QEMU 结果反填）。
  3. **分层**：**快档**入 `make check`；**全量档** opt-in（新 target，如 `check-lit-full`，**不进 `make check`**）。
- **约束**：
  - **禁反填**（硬约束）：期望值来源可追溯到 `spec`/`contracts`。
  - **计数不写死**：用例条数/通过数由脚本/门控**现场统计**；门控断言写「**不下降 / 逐项相等**」，**不得**硬编码数字。
  - 生成器**非易失位置**（`tools/testcases/`，入库）；临时产物放 `/tmp/opencode/TESTCASES-037t/`。

## 硬约束

- **临时目录** `/tmp/opencode/TESTCASES-037t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **一键证据脚本** `.work/evidence/TESTCASES-037t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁 `tee`**。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/testcases/TESTCASES-037t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **骨架生成器可用**：给定真源生成 lit 骨架；生成器落 `tools/testcases/`（入库）；可重跑、幂等（给真实输出）。
2. **期望机械派生**：CHECK/期望值由脚本从 `spec`/`contracts` 派生；给「来源可追溯」证据，**无**从 `llc`/QEMU 反填。
3. **规模达标**：用例总数达目标量级（**由脚本现场统计**，任务书/验收**不写死数字**）。
4. **分层生效**：快档入 `make check` 且 EXIT=0；全量档 opt-in target 可跑（给真实输出）。
5. **反例门控**：检查器能对**注入反例**失败（给注入→FAIL→还原→回绿真实输出）。
6. **不回归**：`make check`/`check-lit` EXIT=0（通过数**不下降 / 逐项相等**）。
7. **一键证据脚本**：`.work/evidence/TESTCASES-037t/run.sh` 逐项通过、`RUN_EXIT=0`；给真实输出与退出码。
8. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

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
