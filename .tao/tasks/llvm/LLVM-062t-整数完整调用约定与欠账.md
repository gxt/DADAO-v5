# LLVM-062t: 整数完整调用约定 + 小欠账收口

**模块**：llvm
**项目里程碑**：M6
**依赖**：`INFRA-050t`（一次构建）、`SPEC-124t`（调用约定契约收口）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `.tao/knowledge/contract-abi.md §6`（`SPEC-124t` 消解后的调用约定口径：多返回值/`i128`/red zone）。
  - `.tao/knowledge/contract-abi.md §4`（标量调用约定基线）。
  - `.tao/adr/adr-0018-m3-codegen-choices.md`（C1/C2/C4/C5/C16 等 CodeGen 决策）。
  - `.tao/knowledge/issues.yaml`：`ISS-005`/`ISS-006`（完整调用约定/ABI `[OPEN]`）、`ISS-043`/`ISS-045`/`ISS-047`/`ISS-148`/`ISS-159`/`ISS-162`（小欠账）。
  - `spec/Process-01-组件补丁组织与构建编排.md`（补丁纪律）。
- **输出**：
  1. `components/llvm-project/patches/llvm/lib/Target/DADAO/**`：整数**完整调用约定**——**变参**/聚合传参/聚合返回（`sret`）/多返回值/**间接调用**（`ISS-005`/`ISS-006`）。
  2. **小欠账收口**：
     - `ISS-043`（越界立即数静默截断 ⇒ 加诊断）；
     - `ISS-045`（`getFixupKindForInstr` default 未白名单化）；
     - `ISS-047`（`llvm-objdump` 的 `e_machine` → dadao 映射）；
     - `ISS-148`（消除硬编码计数：`tools/llvm/gen_m1_asm.py`/`test_m1_asm.py` docstring 陈旧「177 条」，**做法 = 消除硬编码计数**，非改数字 ⇒ 由脚本现场统计或引用单一真源）；
     - `ISS-159`（lower IR `not`/`neg` 路径）；
     - `ISS-162`（`DADAOAsmParser` 诊断枚举加 `FIRST_TARGET_MATCH_RESULT_TY` 偏移 + 显式 `case Match_Invalid…:`）。
  3. `series`/`changelog.md` 随任务追加（`Process-01`）。
- **约束**：
  - **`ISS-110` 全留后**（不实现 `cfxld`/`cfxst`/`crii` 别名等）。
  - **`spec/` 交集为空**（本任务改 `components/**` + `tools/llvm/**` + lit，不改 `spec/`）。
  - 期望值来自 `contracts/`/`.tao/knowledge/contract-abi.md`，**不从实现反推**（`Spec-first`）。
  - 与其它 Wave 2 任务**同改 `components/llvm-project/patches` ⇒ 串行**。

## 硬约束

- **临时目录** `/tmp/opencode/LLVM-062t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **`Process-01` 补丁纪律**：树形补丁集 + 一文件一补丁 + `git apply`；`make check-patch-tree` 断言⑥绿。
- **一键证据脚本** `.work/evidence/LLVM-062t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁 `tee`**。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **重建成本申报**：改 `components/llvm-project/patches/**` ⇒ 开工前写明「重建 LLVM（增量），预计 N 分钟」；一次构建、勿零散重跑。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/llvm/LLVM-062t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **完整调用约定**：变参/聚合/`sret`/多返回/间接调用各 ≥1 运行时用例通过（给真实输出；**计数由脚本现场统计**）；ABI 与 `.tao/knowledge/contract-abi.md §6` 口径一致。
2. **小欠账逐条**：`ISS-043/045/047/148/159/162` 各给出「已修」的真实证据（`ISS-148` 以**消除硬编码**方式，**非**改数字）；无遗留。
3. **`ISS-110` 留后**：`grep` 证明未实现 `cfxld`/`cfxst`/`crii`（保持 `excluded`/decode ILLI）。
4. **不回归**：`make build-mc`/`make check`/`make check-patch-tree`/`make check-lit` EXIT=0；通过数与改前**逐项相等**（不下降）。
5. **`spec/` 交集为空**：`git diff --name-only | grep -E '^spec/'` → 无输出。
6. **一键证据脚本**：`.work/evidence/LLVM-062t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检，给真实输出与退出码。
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
