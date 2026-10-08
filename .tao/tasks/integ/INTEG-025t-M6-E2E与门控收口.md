# INTEG-025t: M6 E2E + 门控收口（`test-m6`）

**模块**：integ
**项目里程碑**：M6
**依赖**：`TESTCASES-036t`~`039t`、`LLVM-065t`、`QEMU-053t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `tools/integ/**`（既有 E2E 驱动，如 `run_codegen_e2e.py`/`run_elf_e2e.py`；**优先复用、不重复造**）。
  - `Makefile`（既有目标 `check`/`check-lit`/`test-codegen`/`test-elf`/`test-semihost`）。
  - `TESTCASES-036t`~`039t` 的向量/驱动/对拍/Embench 产物；`LLVM-065t` 的 reloc；`QEMU-053t` 的 RAM@0 收口。
  - `spec/Process-04 §1`（里程碑开闭）、`spec/Process-05 §6`（落点规则）。
- **输出**：
  1. **M6 E2E 驱动**（落 `tools/integ/`；**优先复用**既有驱动，必要时扩展）：驱动 `lli` 值级对拍 / Embench / lit **全量档**。
  2. `Makefile`：新 target **`test-m6`**——**opt-in，不进 `make check`**。
  3. **`make check` 收口**（不回归）：既有门槛全绿。
- **约束**：
  - **`test-m6` 不进 `make check`**（opt-in；快档已在 `make check` 内）。
  - **不回归**既有门槛（`test-codegen`/`test-elf`/`test-semihost`/`check`/`check-lit`）。
  - **`spec/` 交集为空**。
  - 生成物落点遵循 `.dadao/tests/`（`INFRA-048t`/`Process-05 §6`）。

## 硬约束

- **临时目录** `/tmp/opencode/INTEG-025t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **一键证据脚本** `.work/evidence/INTEG-025t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁 `tee`**。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **重建成本申报**：如需重建 ⇒ 开工前写明「重建 X，预计 N 分钟」；一次构建、勿零散重跑。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/integ/INTEG-025t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **`test-m6` 定义正确**：`Makefile` 有 `test-m6` 目标；`grep` 证明其**不在** `make check` 依赖链内（opt-in）。
2. **E2E 跑通**：`make test-m6` EXIT=0（驱动 `lli` 对拍 / Embench / lit 全量档；给真实输出）。
3. **不回归**：`make test-codegen`/`test-elf`/`test-semihost`/`check`/`check-lit` EXIT=0，通过数与改前**逐项相等 / 不下降**（给真实输出）。
4. **落点合规**：生成物落 `.dadao/tests/`（`Process-05 §6`），`.work/log`/`.work/evidence` 不动。
5. **`spec/` 交集为空**：`git diff --name-only | grep -E '^spec/'` → 无输出。
6. **一键证据脚本**：`.work/evidence/INTEG-025t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检（如把 `test-m6` 误挂入 `check` ⇒ 断言 FAIL ⇒ `cp`+md5 还原 ⇒ 回绿），给真实输出与退出码。
7. **无残留**：`git status --porcelain -uall` 仅本任务应有改动（`tools/integ/**`、`Makefile`、必要时 `tests/e2e/lit/**` + 本任务书）；无 `*_tmp*`/`*.orig`/`*.rej`。

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
