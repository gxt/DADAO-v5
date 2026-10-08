# TESTCASES-036t: M6 新能力向量（L1 编码 + L3 执行）

**模块**：testcases
**项目里程碑**：M6
**依赖**：`LLVM-062t`~`066t`、`QEMU-052t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `contracts/opcodes.yaml` / `contracts/legality_rules.yaml`（编码/合法性事实，**单一真源**）。
  - `.tao/knowledge/contract-abi.md`（调用约定）、`contract-elf.md §2–§4`（reloc）、`contract-isa.md`（FP/RF）。
  - `spec/Process-05-里程碑TDD规范.md`（L1 编码 / L2 结构 / L3 执行三层）。
  - 已实现的 `LLVM-062t`~`066t`、`QEMU-052t` 能力（作为被测对象，**不作期望值来源**）。
- **输出**：
  1. `tests/vectors/**`：M6 新能力的 **L1 编码向量**（调用约定相关指令/reloc 编码）与 **L3 执行向量**（变参/聚合/多返回/间接调用、大帧四形态、FP/RF、reloc 端到端）。
  2. `tests/llvm/lit/MC/DADAO/**`（L1，可复用 `LLVM-*` 向量）与执行侧用例（按 `Process-05` 分层）。
  3. **独立 oracle**：期望值**独立派生自 `spec`/`contracts`**（**禁**从 `llc`/QEMU 结果反填）。
- **约束**：
  - **Independent oracle**：期望值不得从 LLVM/QEMU 生成（硬约束）。
  - 一能力一向量、规模 ∝ 能力，**不超前建大套件**。
  - **计数不写死**：覆盖率/条数由脚本/门控现场统计。
  - `LLVM-062t`~`066t` 未就绪的向量可**分阶段**（`UNSUPPORTED:` 暂缓，就绪后去除），但**不得**以暂缓掩盖缺口。

## 硬约束

- **临时目录** `/tmp/opencode/TESTCASES-036t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **一键证据脚本** `.work/evidence/TESTCASES-036t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁 `tee`**。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/testcases/TESTCASES-036t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **L1 覆盖**：新能力涉及指令/reloc 的 L1 编码向量存在且经独立 oracle 校验（给真实输出）。
2. **L3 覆盖**：调用约定/大帧/FP-RF/reloc 端到端执行向量存在且通过（给真实输出；**条数由脚本现场统计**）。
3. **oracle 独立性**：给出「期望值独立派生」的证据（派生脚本/来源引用）；**无**从 `llc`/QEMU 反填。
4. **反例门控**：验证脚本/检查器能对**注入反例**失败（给注入→FAIL→还原→回绿的**真实输出**）。
5. **不回归**：`make check`/`check-lit` EXIT=0（通过数与改前**逐项相等 / 不下降**）。
6. **一键证据脚本**：`.work/evidence/TESTCASES-036t/run.sh` 逐项通过、`RUN_EXIT=0`；给真实输出与退出码。
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
