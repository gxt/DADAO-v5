# LLVM-070t: `-O2` 误编译致死循环（诊断根因 + 修复）【G6 · 优先】

**模块**：llvm
**项目里程碑**：M6
**依赖**：`INFRA-050t`（一次构建 `DADAO;X86`）、`INFRA-051t`（Embench 源树）、`LLVM-062t`/`LLVM-063t`/`LLVM-069t`（均已 `已验证`）、`QEMU-052t`（ELF 加载，`已验证`）；**与 Wave 2 其它 llvm 任务同改 `components/llvm-project/patches` ⇒ 串行**
**状态**：待开始

> **优先级**：**最高**——G6 是**缺陷（编译成功但运行期静默错码）**，会**污染所有 `-O2` 交付**（编译 rc=0 掩盖运行期错误），须先于其它 LLVM 缺口任务处置。

## 执行环境
**执行环境**：本地

## 背景 / 问题根源（自包含）

`TESTCASES-039t`（Embench 接入）首验收达标（`-O0` 10/19 基准退出码 0）后暴露的 **6 类后端缺口**中，**G6 = 唯一缺陷**：

- **现象**：`huffbench` / `matmult-int` / `nettle-sha256` / `statemate` 在 `-O2` **编译成功**（`clang`/`llc` rc=0），但 QEMU 运行**超时被杀**（`GUEST_EXIT=124`）；同基准 `-O0`/`-O1` **exit=0**。
- **最小复现**：`.work/source/embench-iot/src/matmult-int/matmult-int.c` 仅把 `LOCAL_SCALE_FACTOR 39` 改 `3`（副本 `/tmp/opencode/TESTCASES-039t/red/mm.c`）：`-O2` 死循环、`-O0`/`-O1` exit=0。
- **执行轨迹**（`qemu -d exec`）：停在 `memcpy` 的两条指令（PC `0x4e0` / `0x4f4`）反复自转；`rd4`（i）持续自增而 `rd5`（n）=0，即循环不推进。QEMU 输出仅 `[board:init]`、无 `[board:start]`（hang 于 `warm_caches`）。
- **定性**：属 **`-O2` 优化级误编译**（非算法死循环）；疑似某优化 pass 与 DADAO 后端交互产生错误代码。
- **影响**：任何 `-O2` 产物都可能**静默错码**，故为 M6「完整编译正确性」的**阻断性缺陷**。

**证据指针**：`.work/log/testcases/TESTCASES-039t-stage1-gaps.md §G6`；reviewer 独立复现 `.work/log/testcases/TESTCASES-039t-review-{matrix,gates,e2e}.log`（`TO=25` 下 `-O2` huffbench/matmult-int ⇒ rc=124，`-O0` ⇒ 0）；issue `ISS-180`。

## 接口规范

- **输入**：
  - `components/llvm-project/patches/llvm/lib/Target/DADAO/**`（源树 `.work/source/llvm-project`）——先**诊断根因**（`-O2` 与 `-O0`/`-O1` 的 IR / 机器码差异，疑某优化 pass 与后端 lowering 的交互）。
  - Embench 源树 `.work/source/embench-iot`（`make fetch` 生成）+ `TESTCASES-039t` 交付的 board shim / 最小运行时（`components/embench-iot/patches/**` + `tests/scripts/{embench_runtime.c,embench_include/*.h,dadao_mem_runtime.ll}`）。
  - `spec/Process-01-组件补丁组织与构建编排.md`（补丁纪律）。
- **输出**：
  1. **根因诊断报告**（写入完成区 + `.work/log/llvm/LLVM-070t-*.log`）：定位产生错误代码的 pass/环节，给出 `-O2` 与 `-O0` 的差异证据（IR `-emit-llvm` / `llc -debug` / 反汇编）。
  2. **修复**（`components/llvm-project/patches/llvm/lib/Target/DADAO/**` + 必要的 `tests/llvm/**`/`tests/e2e/**`），使 4 个基准 `-O2` **运行期正确退出（码 0）**。
  3. `series`/`changelog.md` 随任务追加（`Process-01`）。
- **约束**：
  - **先诊断、后修复**：禁止未定位根因即"绕开"（如禁 `-O2`）；若根因为**后端已知能力边界**，须显式失败（`report_fatal_error`），**不得**以静默错码换通过。
  - 语义口径来自 `spec/`/`contracts/`（**不从实现反推**，Spec-first）。
  - **不改 `spec/`/`contracts/`**（`git -c core.quotepath=false diff --name-only | grep -E '^(spec|contracts)/'` → 无输出）；无新决策 ⇒ 无需 ADR。
  - 计数口径**派生自单一真源、不硬编码**（判据恒为「退出码 0」，非计数）。

## 硬约束

- **临时目录** `/tmp/opencode/LLVM-070t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **`Process-01` 补丁纪律**：树形补丁集 + 一文件一补丁 + `git apply`；`make check-patch-tree` 断言⑥绿。
- **一键证据脚本** `.work/evidence/LLVM-070t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁** `tee`。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **注入有效性**：注入后须验 `git -c core.quotepath=false diff --name-only` **非空**；还原须**含重建**（源码还原 ≠ 二进制还原）。
- **重建成本申报 + 脱离工作区生命周期**：改 `components/llvm-project/patches/**` ⇒ 开工前写明「重建 LLVM（增量），预计 N 分钟」；**长构建须 `setsid nohup … >log 2>&1 &` 脱离 opencode 工作区**（`lessons §8.21`），落盘完成标记（`EXIT=$rc`），**禁**会话内后台等待器；一次构建、勿零散重跑。
- **超时判据**：E2E 运行必须带显式超时（如 `timeout N`），`124` 即判 **FAIL**（不得当作"跑完"）。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/llvm/LLVM-070t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **根因诊断**：给出 `-O2` 误编译的**根因**（产生错误代码的 pass/环节）+ 差异证据；最小复现（`mm.c` / matmult-int）在 `-O2` 下**死循环**（`GUEST_EXIT=124`）、`-O0`/`-O1` **exit=0** 可复现。
2. **修复后 E2E**：4 个基准 `huffbench`/`matmult-int`/`nettle-sha256`/`statemate` 经「`-O2` 编译 → 链接 → QEMU 执行（带超时）→ **退出码 0**」端到端通过（给真实命令 + 退出码）。
3. **不静默**：修复后若仍有 `-O2` 形态不可编译/不可执行，须**显式失败**（`report_fatal_error`/编译报错），**不得**静默错码（编译 rc=0 而运行错）。
4. **不回归**：`make build-mc`/`make check`/`make check-patch-tree`/`make check-lit` EXIT=0（通过数与改前**逐项相等 / 不下降**）；`-O0` 10/19 首验收集**不下降**。
5. **`spec/` 交集为空**：`git -c core.quotepath=false diff --name-only | grep -E '^(spec|contracts)/'` → 无输出。
6. **一键证据脚本**：`.work/evidence/LLVM-070t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检（改回退/改错误代码路径 ⇒ 断言 FAIL ⇒ `cp`+md5 还原 ⇒ 重建 ⇒ 回绿），给真实输出与退出码。
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
