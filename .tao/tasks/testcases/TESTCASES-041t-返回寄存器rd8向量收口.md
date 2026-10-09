# TESTCASES-041t: 返回寄存器 `rd8` 收口——受影响向量/期望值重派生重验

**模块**：testcases
**项目里程碑**：M6
**依赖**：`SPEC-124t`（函数返回域契约）、`SPEC-126t`（系统调用/半托管返回域契约）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 用户裁定（原话）

> **「统一为 rd8」**（系统调用与函数 ABI 统一；此前 `rd31`）。**不立 ADR**（用户既定）。

## 变更边界（两个独立变更，**分别验收**）

本任务含**两个域**的向量/期望值收口，须**分段、分别验收**：

- **域 A「函数返回」**（依据 `SPEC-124t`）：函数返回寄存器 `rd31/rb31 → rd8/rb8`。
- **域 B「半托管返回」**（依据 `SPEC-126t`）：半托管服务返回寄存器 `rd31 → rd8`。

**不得**以某一域已改充另一域，**不得**以旧期望值充数。

## 接口规范

- **输入**：
  - `contract-abi.md §4.4/§4.6`（返回区 `rd8–rd15`，`SPEC-124t`）；`contract-semihosting.md §2/§4`（`SPEC-126t`）。
  - `tests/scripts/codegen_crt0.s` + `tools/integ/run_codegen_e2e.py`（注释/桩：函数返回 `rd31`）。
  - `tests/llvm/codegen/**`（`expected.yaml`/`README.md`/`*.ll` 注释中的函数返回 `rd31`/`rb31`）。
  - `tests/llvm/lit/CodeGen/DADAO/branch-fold-two-way.mir`（`RET_PSEUDO implicit $rd31`、`call_iiii` 返回 `$rd31`）。
  - `tests/llvm/codegen/m5/**`（`m5_semi_write.s`/`expected.yaml`：半托管 `SYS_WRITE` 返回 `rd31`）。
- **输出**：
  1. **域 A**：`codegen_crt0.s`（桩读取的返回寄存器 `rd31 → rd8`；`st.o` 存回位置随之）、`run_codegen_e2e.py` 注释、`tests/llvm/codegen/**`（期望/说明）与 `.mir` 中**函数返回**处 → `rd8`/`rb8`。
  2. **域 B**：`tests/llvm/codegen/m5/**` 中**半托管服务返回** `rd31 → rd8`（含「返回落 `rd8`」语义）。
  3. 受影响向量**重派生期望值并重验**（给真实输出与退出码）。
  4. **逐条分类表**（改 / 不改 + 理由）入完成区；计数脚本现场统计（**不写死**）。
- **约束**：
  - **只改返回用途**：**不改**参数区 `rd16–rd31`（如 `call_multiarg_stack.ll` 的参数注释）、`rd31` 作通用暂存处、寄存器角色表。
  - **期望值独立派生**：**禁**从 `llc`/QEMU 结果反填（`Process-05` / 独立 oracle）。
  - **两层分明**：域 A/域 B 的验收证据须**分开列出**（分别给真实输出）。
  - **不改 `spec/`**（`git diff --name-only | grep -E '^spec/'` 无输出）；**不改** `components/**`。
  - `.mir`/codegen 用例若因 `LLVM-062t` 未就绪而**暂不可跑**，须按 `Process-05` 用 `UNSUPPORTED:` 暂缓并**登记遗留**（不得以暂缓掩盖缺口），完成区披露。
  - **门控保持全绿**，不回归。

## 硬约束

- **临时目录** `/tmp/opencode/TESTCASES-041t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **一键证据脚本** `.work/evidence/TESTCASES-041t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁 `tee`**。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/testcases/TESTCASES-041t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **域 A（函数返回）**：`codegen_crt0.s`/`run_codegen_e2e.py`/`tests/llvm/codegen/**`/`.mir` 中函数返回处 == `rd8`（给 grep/摘录真实输出）；参数区 `rd16–rd31` **逐条未变**。
2. **域 B（半托管返回）**：`tests/llvm/codegen/m5/**` 中服务返回处 == `rd8`（给真实输出）。
3. **重派生重验**：受影响向量**重跑通过**（或按 `Process-05` `UNSUPPORTED:` 暂缓并登记遗留），给真实输出与退出码；**无旧期望值残留**充数。
4. **逐条分类表**：完成区给「改 / 不改」逐条分类（`文件:行 + 用途 + 理由`），计数脚本现场统计。
5. **不回归**：`make check`/`check-lit` EXIT=0（通过数与改前**逐项相等 / 不下降**）。
6. **一键证据脚本**：`.work/evidence/TESTCASES-041t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检，给真实输出与退出码。
7. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

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
