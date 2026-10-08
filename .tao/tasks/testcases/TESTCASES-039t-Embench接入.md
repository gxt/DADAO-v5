# TESTCASES-039t: Embench 接入（钉子③）

**模块**：testcases
**项目里程碑**：M6
**依赖**：`INFRA-051t`（Embench 组件接入）、`LLVM-062t`/`063t`（编译能力）、`QEMU-052t`（ELF 加载）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `INFRA-051t` 产出：`.work/source/embench-iot`（工作树）+ `components/embench-iot/{patches/**,series,changelog.md}`。
  - `LLVM-062t`/`063t` 的 DADAO 工具链（编译能力）；`QEMU-052t` 的 ELF 加载。
  - `spec/Process-01-组件补丁组织与构建编排.md`（board shim/运行时补充的承载）。
  - `INTEG-023k §A（#3 不引 libc）`、`§C（TESTCASES-039t）`：board shim 3 函数 + 最小运行时 + `md5sum` 大端适配；**首验收 = 最小基准 QEMU 正确退出码**。
- **输出**：
  1. **board shim 3 函数**：`initialise_board`/`start_trigger`/`stop_trigger`（落 `components/embench-iot/patches/**`）。
  2. **最小运行时**：`mem*`/`str*`/`ctype`/`sqrt`（**不引 libc**）。
  3. **`md5sum` 大端适配**（Embench 的 `md5sum` 依赖端序）。
  4. **最小基准**端到端跑通：DADAO 工具链编译/链接 → QEMU 执行 → **正确退出码**（首验收）。
- **约束**：
  - **不引 libc**（最小运行时自写）。
  - 组件补丁遵循 `Process-01`（树形补丁集 + 一文件一补丁）；工作树 `.work/source/embench-iot` 由 `make fetch` 生成（gitignored）。
  - **首验收 = 最小基准正确退出码**；全量基准可后续增量，**不**在首验收硬性要求。
  - **计数不写死**：基准条数/通过数由脚本/门控**现场统计**。

## 硬约束

- **临时目录** `/tmp/opencode/TESTCASES-039t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **`Process-01` 补丁纪律**（涉 `components/**` 者）：树形补丁集 + 一文件一补丁 + `git apply`；`make check-patch-tree` 断言⑥绿。
- **一键证据脚本** `.work/evidence/TESTCASES-039t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁 `tee`**。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **重建成本申报**：涉 `components/**/patches/**` 或 QEMU 重建 ⇒ 开工前写明「重建 X，预计 N 分钟」；一次构建、勿零散重跑。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/testcases/TESTCASES-039t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **board shim 3 函数**：`initialise_board`/`start_trigger`/`stop_trigger` 存在并被 Embench 调用（给真实输出）。
2. **最小运行时**：`mem*`/`str*`/`ctype`/`sqrt` 自写实现，**不引 libc**（给证据）。
3. **`md5sum` 大端**：Embench `md5sum` 在大端 DADAO 上结果正确（给真实输出）。
4. **首验收 = 最小基准正确退出码**：至少**一个**最小基准经「编译 → QEMU 执行 → 正确退出码」端到端通过（给真实命令 + 退出码）。
5. **门控**：`make check`/`check-interface`/`check-patch-tree` EXIT=0（通过数**不下降 / 逐项相等**）。
6. **一键证据脚本**：`.work/evidence/TESTCASES-039t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检，给真实输出与退出码。
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
