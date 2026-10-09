# LLVM-066t: FP/RF codegen（排整数之后）

**模块**：llvm
**项目里程碑**：M6
**依赖**：`LLVM-062t`（整数调用约定先行）、`SPEC-122t`（相关 ADR 就位）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `.tao/knowledge/contract-isa.md`（FP 指令/寄存器 `rf`/`instr` 语义；`SimRISC-07`）。
  - `.tao/knowledge/contract-abi.md`（RF 寄存器角色/`rf0` 状态寄存器）。
  - `.tao/adr/adr-0018-m3-codegen-choices.md`（CodeGen 决策）。
  - `.tao/knowledge/issues.yaml`：`ISS-081`（FP 衔接点：独立 oracle/harness RF/FP 向量/E2E/实现缺口）、`ISS-126`（FP 开放点固定取值）、`ISS-078`（`focls/ftcls` 之外未复核）。
  - `INTEG-023k §A（#2 FP/RF codegen；含 compiler-rt 软浮点取舍随 #2）`。
  - 用户 2026-10-09 裁定（经 `SPEC-128t` 连带）：「**同样的，rd4-rd7/rf1-rf7 也改为 caller-saved，由 llvm 分配使用**」——RF 实现侧放开归本任务。
- **输出**：
  1. `components/llvm-project/patches/llvm/lib/Target/DADAO/**`：FP/RF **codegen**——FP 寄存器类（`rf`）、FP 指令 lowering/选择、FP 传参/返回（按 `contract-abi` FP 部分）；`ISS-081`/`ISS-126`/`ISS-078` 范围内收口。
  2. **compiler-rt 软浮点取舍**（随 #2 裁定）；如引入须落 `components/`/`runtime` 相应位置并申报。
  3. **RF 实现侧放开（`SPEC-128t` 裁决连带，2026-10-09）**：解除 M3 边界对 RF 的保留——`getReservedRegs`/`GPRF` 中 **`rf1–rf7` 放开为可分配 caller-saved**（`rf0`=FCSR **保留**）；`GPRF`（`rf0–rf63`）由全保留改为「`rf0` 保留 + 其余按 ABI（`rf1–rf7`/`rf8–rf31` temporary、`rf32–rf63` callee-saved）可分配」；**册不改**（`DADAO-21` 已定 RF 角色，本项仅实现侧放开）。
  4. `series`/`changelog.md` 随任务追加（`Process-01`）。
- **约束**：
  - **排在整数之后**（依赖 `LLVM-062t`）。
  - **不引 libc**；软浮点取舍给**明确结论**（引入/不引入 + 理由）。
  - **`spec/`/`contracts/` 交集为空**（RF 角色已由 `DADAO-21` 定，本任务只做实现侧放开）。
  - 与 Wave 2 **同改 `components/llvm-project/patches` ⇒ 串行**（本任务为 Wave 2 收尾）。

## 硬约束

- **临时目录** `/tmp/opencode/LLVM-066t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **`Process-01` 补丁纪律**：树形补丁集 + 一文件一补丁 + `git apply`；`make check-patch-tree` 断言⑥绿。
- **一键证据脚本** `.work/evidence/LLVM-066t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁 `tee`**。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **重建成本申报**：改 `components/llvm-project/patches/**` ⇒ 开工前写明「重建 LLVM（增量），预计 N 分钟」；一次构建、勿零散重跑。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/llvm/LLVM-066t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **FP/RF codegen 可用**：FP 算术/转换/比较等由后端正确 lower（给真实编译产物/反汇编）；FP 传参/返回与 `contract-abi` FP 部分一致。
2. **`ISS-081/126/078` 处置**：逐条给「已实现/已消解/留后 + 理由」（`ISS-078` 若仍属 spec 侧，登记并说明归属）。
3. **软浮点取舍**：给出 compiler-rt **引入/不引入**的明确结论 + 理由。
4. **RF 实现侧放开**：`rf1–rf7` 可被分配为 caller-saved、`rf0`(FCSR) 保留（给 `getReservedRegs` 真实输出 + 分配证据）；RF 角色与 `DADAO-21 §RF寄存器`（`rf1–rf7`/`rf8–rf31` temporary、`rf32–rf63` callee-saved）逐条一致。
5. **不回归**：`make build-mc`/`make check`/`make check-patch-tree`/`make check-lit` EXIT=0（通过数与改前**逐项相等**）。
6. **`spec/`/`contracts/` 交集为空**：`git diff --name-only | grep -E '^(spec|contracts)/'` → 无输出。
7. **一键证据脚本**：`.work/evidence/LLVM-066t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检，给真实输出与退出码。
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
