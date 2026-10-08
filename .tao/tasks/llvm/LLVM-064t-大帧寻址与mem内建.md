# LLVM-064t: 大帧寻址四形态 + `mem*` 内建

**模块**：llvm
**项目里程碑**：M6
**依赖**：`LLVM-062t`（整数完整调用约定）、`SPEC-122t`（`adr-0018 §C7 D4` 修订须 `Accepted`）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - 修订后的 `.tao/adr/adr-0018-m3-codegen-choices.md §C7 D4`（**四形态 + 代价驱动**；`SPEC-122t` 产出，须 `Accepted`）。
  - `.tao/knowledge/contract-abi.md §4.7`（帧布局/FP 策略）。
  - `.tao/knowledge/issues.yaml`：`ISS-138`（>128K 帧未实现，现显式失败）。
  - `INTEG-023k §A（#3 不引 libc）`（`mem*`/`str*` 自写最小实现 + `MaxStoresPerMem*=16`）。
- **输出**：
  1. `components/llvm-project/patches/llvm/lib/Target/DADAO/**`（`DADAOFrameLowering`/`DADAOISelLowering`/`DADAOInstrInfo`）：大帧寻址 **四形态**——①`[sp,disp12]` ②`rb2rb`+`add.si` ③`add.o tmprb,sp,tmp`+`[tmprb,disp]` ④`ldm/stm [sp,tmp]`（`immu6`=1 单次、>1 批量）；**由编译器按代价（指令数 × 访存条数/复用次数）选择**（`ISS-138`）。
  2. **`mem*` 内建**（`memcpy`/`memset`/`memmove`/`memcmp`… 自写最小实现）+ 后端 **`MaxStoresPerMem*=16`**（不引 libc）。
  3. `series`/`changelog.md` 随任务追加（`Process-01`）。
- **约束**：
  - **ADR 未 `Accepted` 前不进实现**（本任务依赖修订后的 `adr-0018 §C7 D4`）。
  - **不引 libc**（`mem*`/`str*` 自写最小实现）。
  - **`spec/` 交集为空**。
  - 与 Wave 2 **同改 `components/llvm-project/patches` ⇒ 串行**。

## 硬约束

- **临时目录** `/tmp/opencode/LLVM-064t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **`Process-01` 补丁纪律**：树形补丁集 + 一文件一补丁 + `git apply`；`make check-patch-tree` 断言⑥绿。
- **一键证据脚本** `.work/evidence/LLVM-064t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁 `tee`**。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **重建成本申报**：改 `components/llvm-project/patches/**` ⇒ 开工前写明「重建 LLVM（增量），预计 N 分钟」；一次构建、勿零散重跑。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/llvm/LLVM-064t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **四形态可触发**：构造覆盖**四种寻址形态**的大帧用例（含 >128K），各形态按**代价选择**逻辑选对（给真实编译产物/反汇编）；`ISS-138` 的「scheme 1 not implemented」**不再出现**（给证据）。
2. **`mem*` 内建**：`memcpy`/`memset`/`memmove`/`memcmp` 由自写最小实现提供（**不引 libc**）；后端 `MaxStoresPerMem*=16` 生效（给真实输出）。
3. **ADR 一致**：实现口径与修订后的 `adr-0018 §C7 D4` 逐条一致（给对照）。
4. **不回归**：`make build-mc`/`make check`/`make check-patch-tree`/`make check-lit` EXIT=0（通过数与改前**逐项相等**）。
5. **`spec/` 交集为空**：`git diff --name-only | grep -E '^spec/'` → 无输出。
6. **一键证据脚本**：`.work/evidence/LLVM-064t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检，给真实输出与退出码。
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
