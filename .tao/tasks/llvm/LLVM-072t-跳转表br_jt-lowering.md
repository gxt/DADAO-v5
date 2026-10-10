# LLVM-072t: 跳转表 `br_jt` lowering【G3】

**模块**：llvm
**项目里程碑**：M6
**依赖**：`INFRA-050t`（一次构建 `DADAO;X86`）、`INFRA-051t`（Embench 源树）、`LLVM-062t`/`LLVM-063t`/`LLVM-069t`（均已 `已验证`）、`QEMU-052t`（ELF 加载，`已验证`）；**与 Wave 2 其它 llvm 任务同改 `components/llvm-project/patches` ⇒ 串行**
**状态**：待开始

> **覆盖缺口**：**G3（`ISS-177`）**。

## 执行环境
**执行环境**：本地

## 背景 / 问题根源（自包含）

- **现象**：`Cannot select: t4: ch = br_jt t2:1, JumpTable:i64<0>, t2>`（`llc` rc=134）——**`-O0` 即触发**（非优化级专属）。
- **最小复现**：`switch(x)` 含 16 个 case（含 fallthrough 全分支）→ `clang`/`llc` rc=134。
- **定性**：DADAO 后端**无 `ISD::BR_JT` / `JumpTable` 的 lowering**（跳转表未实现）⇒ 密集 `switch` 分发不可编译。
- **命中基准**：picojpeg / qrduino。
- **性质 = 缺能力（编译期显式失败，非静默）**。

**证据指针**：`.work/log/testcases/TESTCASES-039t-stage1-gaps.md §G3`；issue `ISS-177`。

## 接口规范

- **输入**：
  - `components/llvm-project/patches/llvm/lib/Target/DADAO/**`（源树 `.work/source/llvm-project`）。
  - `.tao/knowledge/contract-isa.md`（间接跳转 / 相对寻址相关指令，如 `br`/`jump` 族；如有 `jump` 表基址+偏移形态）；`.tao/knowledge/contract-elf.md`（数据段/重定位，跳转表落在数据段的方式）——**以 `spec/`/`contracts/` 为准，不从实现反推**。
  - `spec/Process-01-组件补丁组织与构建编排.md`（补丁纪律）。
- **输出**（`components/llvm-project/patches/llvm/lib/Target/DADAO/**` + 必要的 `tests/llvm/**`/`tests/e2e/**`）：
  1. **`br_jt` lowering**：为 `ISD::BR_JT` 实现 lowering（跳转表落数据段 + 间接跳转；参考既有目标的做法，按 DADAO ISA 能力选择实现），使密集 `switch` 可编译。
  2. 如需新增 `DADAOISD` 节点/模式或改 `DADAOISelDAGToDAG`/`DADAOCodeGen.td`/`DADAOISelLowering.{h,cpp}`，一并落地；受影响 `tests/llvm/**` 期望值按册/契约**重新派生**（**不从实现反填**）。
  3. `series`/`changelog.md` 随任务追加（`Process-01`）。
- **约束**：
  - 语义口径来自 `spec/`/`contracts/`（**不从实现反推**，Spec-first）。
  - **不改 `spec/`/`contracts/`**（`git -c core.quotepath=false diff --name-only | grep -E '^(spec|contracts)/'` → 无输出）；纯后端能力补全 ⇒ 无新决策、无需 ADR（若实现引入**新的 reloc/段语义**，须停下报告、提请 ADR）。
  - 计数口径**派生自单一真源、不硬编码**。

## 硬约束

- **临时目录** `/tmp/opencode/LLVM-072t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **`Process-01` 补丁纪律**：树形补丁集 + 一文件一补丁 + `git apply`；`make check-patch-tree` 断言⑥绿。
- **一键证据脚本** `.work/evidence/LLVM-072t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁** `tee`。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **注入有效性**：注入后须验 `git -c core.quotepath=false diff --name-only` **非空**；还原须**含重建**（源码还原 ≠ 二进制还原）。
- **重建成本申报 + 脱离工作区生命周期**：改 `components/llvm-project/patches/**` ⇒ 开工前写明「重建 LLVM（增量），预计 N 分钟」；**长构建须 `setsid nohup … >log 2>&1 &` 脱离 opencode 工作区**（`lessons §8.21`），落盘完成标记（`EXIT=$rc`），**禁**会话内后台等待器；一次构建、勿零散重跑。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/llvm/LLVM-072t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **`br_jt` 可编译**：最小复现（`switch` 含 16 个 case，`-O0`）经 `clang`/`llc` **rc=0**（给真实命令 + rc）。
2. **`switch` 语义正确（E2E）**：至少覆盖「命中各 case / `default` / fallthrough」的 `switch` 程序经「编译 → 链接 → QEMU 执行 → **正确退出码**」端到端通过（给真实命令 + 退出码）。
3. **真实基准**：picojpeg / qrduino **至少一个**经 `-O0` 编译 **rc=0**（给真实命令 + rc）。
4. **不回归**：`make build-mc`/`make check`/`make check-patch-tree`/`make check-lit` EXIT=0（通过数与改前**逐项相等 / 不下降**）。
5. **`spec/` 交集为空**：`git -c core.quotepath=false diff --name-only | grep -E '^(spec|contracts)/'` → 无输出。
6. **一键证据脚本**：`.work/evidence/LLVM-072t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检（改跳转表基址/偏移 ⇒ 断言 FAIL ⇒ `cp`+md5 还原 ⇒ 重建 ⇒ 回绿），给真实输出与退出码。
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
（审查者独立验证的重跑记录、约束核验、判决）
