# LLVM-076t: 有符号乘高半 `MULHS` / `SMUL_LOHI`【G2 同族】

**模块**：llvm
**项目里程碑**：M6
**依赖**：`INFRA-050t`（一次构建 `DADAO;X86`）、`INFRA-051t`（Embench 源树）、`LLVM-062t`/`LLVM-063t`/`LLVM-069t`/`LLVM-073t`（均已 `已验证`）、`QEMU-052t`（ELF 加载，`已验证`）；**与 Wave 2 其它 llvm 任务同改 `components/llvm-project/patches` ⇒ 串行**
**状态**：待开始

> **覆盖缺口**：**`ISS-185`（有符号乘高半 `MULHS`/`SMUL_LOHI`）**；与 `LLVM-073t`（无符号 `mulhu`/`umul_lohi`）**同族**。

## 用户裁定（2026-10-10，原话/结论）

> 用户 **2026-10-10 裁定：4 条缺口（`ISS-182` / `ISS-185` / `ISS-186` / `ISS-181`）全部纳入 M6**（「10 点前完不成 ⇒ 全加、跑一晚上」）。本任务 = **`ISS-185`**，**照 `LLVM-073t` 套路**。

## 执行环境
**执行环境**：本地

## 背景 / 问题根源（自包含）

- **现象**：`Cannot select: ... mulhs ...`（`llc` rc=134）。
- **最小复现**：`long g(long a, long b){ return a*b/3; }`（`-O0`/`-O2`）——非 2 的幂除数的**有符号**路径触发 128 位乘高半；`long long` 直接路径亦触发。
- **定性**：DADAO 后端**无 `ISD::MULHS`（及 `smul_lohi`）的 lowering/模式**（`LLVM-073t` 仅实现无符号 `MULHU`/`UMUL_LOHI`）。
- **ISA 依据**：`contract-isa.md §6.1.4` **`mul.so rdha, rdhb, rdhc, rdhd`**（有符号乘法，`rdha:rdhb = rdhc × rdhd`，128 位结果；`rdha`=高 64 位、`rdhb`=低 64 位）——**与无符号 `mul.uo` 同族**。
- **性质 = 缺能力（编译期显式失败，非静默）**。
- **测试强度要求（引 `lessons §8.46`）**：`LLVM-073t` 已提交用例 `lo^hi`/`umul128_xor` 为 **XOR 交换不变** ⇒ 对「双结果半字序互换」**不可检**；本任务**测试断言须能区分半字序**（构造**非交换**判别用例，如 `hi - lo`）。

**证据指针**：`.work/log/llvm/LLVM-073t-review-*.log`；`.tao/tasks/llvm/LLVM-073t-128位乘高半umul_lohi.md`「新发现/坑③」「遗留问题①」；issue `ISS-185`。

## 接口规范

- **输入**：
  - `components/llvm-project/patches/llvm/lib/Target/DADAO/**`（源树 `.work/source/llvm-project`）；参照 `LLVM-073t` 对 `MULHU`/`UMUL_LOHI` 的既有实现（`DADAOCodeGen.td`/`DADAOInstrInfo.cpp`）。
  - `.tao/knowledge/contract-isa.md §6.1.4`（`mul.so` 有符号 128 位积）；`contract-abi.md`（**M6「不引 libc/compiler-rt」**约束）。
  - `spec/Process-01-组件补丁组织与构建编排.md`（补丁纪律）。
- **输出**（`components/llvm-project/patches/llvm/lib/Target/DADAO/**` + 必要的 `tests/llvm/**`/`tests/e2e/**`）：
  1. **有符号乘高半 lowering**：为 `ISD::MULHS`（及必要的 `smul_lohi`/多字有符号乘分解）实现 lowering/模式（**对照 `LLVM-073t` 无符号套路**，用 ISA 专用 `mul.so`），使 `a*b/c`（非 2 的幂、有符号）与有符号 `long long` 乘法可编译、语义正确。
  2. 如需新增 `DADAOISD` 节点/伪指令或改 `DADAOISelDAGToDAG`/`DADAOCodeGen.td`/`DADAOInstrInfo.cpp`/`DADAOISelLowering.{h,cpp}`，一并落地；受影响 `tests/llvm/**` 期望值按册/契约**重新派生**（**不从实现反填**）。
  3. `series`/`changelog.md` 随任务追加（`Process-01`）。
- **约束**：
  - 语义口径来自 `spec/`/`contracts/`（**不从实现反推**，Spec-first），须给乘高半的**独立 oracle** 手算（host Python **大整数有符号**乘法，含负数/边界）验证。
  - **不改 `spec/`/`contracts/`**（`git -c core.quotepath=false diff --name-only | grep -E '^(spec|contracts)/'` → 无输出）；纯后端能力补全 ⇒ 无新决策、无需 ADR。
  - **不引 libc/compiler-rt**（M6 约束；若实现依赖运行时辅助例程，须停下报告）。
  - 计数口径**派生自单一真源、不硬编码**。

## 硬约束

- **临时目录** `/tmp/opencode/LLVM-076t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **`Process-01` 补丁纪律**：树形补丁集 + 一文件一补丁 + `git apply`；`make check-patch-tree` 断言⑥绿。
- **一键证据脚本** `.work/evidence/LLVM-076t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁** `tee`。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **注入有效性**：注入后须验 `git -c core.quotepath=false diff --name-only` **非空**；还原须**含重建**（源码还原 ≠ 二进制还原）。
- **重建成本申报 + 脱离工作区生命周期**：改 `components/llvm-project/patches/**` ⇒ 开工前写明「重建 LLVM（增量），预计 N 分钟」；**长构建须 `setsid nohup … >log 2>&1 &` 脱离 opencode 工作区**（`lessons §8.21`），落盘完成标记（`EXIT=$rc`），**禁**会话内后台等待器；一次构建、勿零散重跑。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/llvm/LLVM-076t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **`mulhs` 可编译**：最小复现 `long g(long a, long b){ return a*b/3; }`（`-O0`/`-O2`）经 `clang`/`llc` **rc=0**（给真实命令 + rc + 反汇编证据，确用 `mul.so`）。
2. **有符号乘高半语义正确（独立 oracle 逐条）**：给**独立 oracle**（host Python **有符号大整数**）手算的边界用例（负数、跨 `2^32`、`2^63-1`、`-2^63`、`(2^63-1)^2`、`(-2^63)^2` 等）与 DADAO 产出**逐条**一致（**不得采样**；含**逐字节**比对）。
3. **测试断言能区分半字序**：`smul_lohi` 双结果用例须为**非交换**判别（引 `lessons §8.46`；如 `hi - lo` 或单取 `hi`，并对「两半互换」注入可检出）；给该注入的 FAIL/回绿证据。
4. **E2E**：`a*b/c`（非 2 的幂、有符号）与有符号 `long long` 乘法经「编译 → 链接 → QEMU 执行 → **正确退出码**」端到端通过（给真实命令 + 退出码）。
5. **真实基准**：`aha-mont64` 及相关基准 `-O0` **rc=0**（`-O2` 若仍受 `ISS-186` 它类缺口阻塞须说明，**不阻断本任务**）；改善以**现场统计**（不改写死计数）表述。
6. **不回归**：`make build-mc`/`make check`/`make check-patch-tree`/`make check-lit` EXIT=0（通过数与改前**逐项相等 / 不下降**）。
7. **`spec/` 交集为空**：`git -c core.quotepath=false diff --name-only | grep -E '^(spec|contracts)/'` → 无输出。
8. **一键证据脚本**：`.work/evidence/LLVM-076t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检（**改有符号高半计算/半字序 ⇒ 断言 FAIL ⇒ `cp`+md5 还原 ⇒ 重建 ⇒ 回绿**），给真实输出与退出码。
9. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

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
