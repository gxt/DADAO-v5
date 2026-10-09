# LLVM-069t: 整数 `setcc` / `select_cc` lowering（补后端能力缺口）

**模块**：llvm
**项目里程碑**：M6
**依赖**：`INFRA-050t`（一次构建 `DADAO;X86`）、`LLVM-062t`（整数完整调用约定，已验证）、`LLVM-066t`（FP `select_cc`/`FCMP` 结构可作对照，已验证）、`LLVM-063t`（clang target / E2E 通道，已验证）；**与 Wave 2 其它任务同改 `components/llvm-project/patches` ⇒ 串行**
**状态**：待开始

## 执行环境
**执行环境**：本地

## 背景（自包含；主会话 2026-10-10 已独立复核）

`TESTCASES-039t`（Embench 接入）engineer **诚实停工**（判据**未降级** = 恒定退出码 0）：交付的 DADAO 工具链**无法编译任何真实 C 代码**——凡把比较结果**当值**使用（`a==b`、`!x`、`a<b`、三目 `?:`、逻辑 `&&`/`||`）的函数，`clang`/`llc` 在**指令选择**阶段崩溃（SIGABRT）：

```
fatal error: error in backend: Cannot select: t16: i64 = setcc t20, t21, seteq:ch   (clang rc=1)
LLVM ERROR: Cannot select: t13: i64 = setcc t2, t4, seteq:ch                        (llc rc=134)
```

**纯分支**形态 `if(a<b) return 1; return 0;`（`br(icmp)`，-O0）正常（rc=0）；-O2 因 if-conversion 又转 `select_cc` 崩溃。`llc` 手工 `.ll`（`icmp eq`+`zext i1→i64`）亦复现 ⇒ **与 clang 无关，是后端 ISel 能力缺口**。

**根因**：DADAO 后端 `DADAOTargetLowering` 仅把 `ISD::BR_CC`/`ISD::BRCOND` 设 `Custom`（`DADAOISelLowering.cpp`），**无 `ISD::SETCC` / 整数 `ISD::SELECT_CC` 的 action 或 ISel 模式**（`grep -rniE setcc` 仅命中注释）。M4/M6 向量一律用 `br(icmp)` 回避此形态，故历次任务未暴露。

**影响**：19 个 Embench 基准中 **14 个** `verify_benchmark` 直接 `return (比较)`，其余经 `support/main.c:37 return (!correct)` 也必经 `setcc` ⇒ **无一基准可编译**，`TESTCASES-039t` 首验收不可达。

**证据指针**：`.work/log/testcases/TESTCASES-039t-{blocker.log,blocker_probe_result.txt,matrix_result.txt,progress.md}`。

## 接口规范

- **输入**：
  - `components/llvm-project/patches/llvm/lib/Target/DADAO/**`（源树 `.work/source/llvm-project`）；现 `DADAOISelLowering.cpp` 已定义 `DADAOISD::CMP`/`CMPU`/`FCMP` 与 `LowerBR_CC`/`LowerBRCOND`，`DADAOCodeGen.td` 已有 `DADAOCmp`/`DADAOCmpU`（`SDTIntBinOp`）与 FP `selectcc` 模式。
  - `.tao/knowledge/contract-isa.md §6.2`（`cmp.si`/`cmp.ui` 立即数比较、`cmp.uo` 寄存器比较；**结果按 -1/0/1 写满 64 位**，见 §6.2.1/§6.2.2）、`§6.5`（`cs.n`/`cs.z`/`cs.p`/`cs.eq`/`cs.ne` 条件赋值，rrrr）、`§8`（条件跳转 `br.*`）。
  - `.tao/knowledge/contract-fp.md §8` + `DADAOCodeGen.td` 的 FP `selectcc`→`cs.*` 模式（结构对照）。
  - `spec/Process-01-组件补丁组织与构建编排.md`（补丁纪律）。
- **输出**（`components/llvm-project/patches/llvm/lib/Target/DADAO/**` + 必要的 `tests/llvm/**`）：
  1. **整数 `setcc`-as-value lowering**（IR `icmp` 经 `zext i1→i64`）：产出 **0/1 的 i64 值**。做法（engineer 择一，须给理由）：(a) `setOperationAction(ISD::SETCC, MVT::i64, Custom)` + `LowerSETCC`——用 `DADAOISD::CMP`/`CMPU`（结果 -1/0/1）+ `cs.*` 归一化为 0/1；(b) TableGen `Pat` 直接匹配 `setcc`。**谓词须全覆盖**：`eq/ne/slt/sle/ult/ule/sgt/sge/ugt/uge`（有符号 `CMP` / 无符号 `CMPU` 两条路径）。
  2. **整数 `select_cc` / `select` lowering**：整数 `SELECT_CC`（及经合法化后的 `select`）lowering 为 `cs.*` 条件赋值（结构参照 FP `selectcc`，注意操作数/真值臂交换）。
  3. 如需新增 `DADAOISD` 节点/模式或改 `DADAOISelDAGToDAG`/`DADAOCodeGen.td`/`DADAOISelLowering.{h,cpp}`，一并落地；受影响 `tests/llvm/**` 期望值按册/契约**重新派生**（**不从实现反填**）。
  4. `series`/`changelog.md` 随任务追加（`Process-01`）。
- **约束**：
  - 语义口径来自 `contract-isa §6.2/§6.5`（`cmp` = -1/0/1；`cs.*` 条件赋值），**不从实现反推**（Spec-first）。
  - **不改 `spec/`/`contracts/`**（`git -c core.quotepath=false diff --name-only | grep -E '^(spec|contracts)/'` → 无输出）；**不改 ISA/ABI/ELF 契约**（纯后端能力补全，无新决策 ⇒ 无需 ADR）。
  - 与 Wave 2 同改 `components/llvm-project/patches` ⇒ **串行**（不得与其它 Wave 2 任务并行）。
  - 计数口径**派生自单一真源、不硬编码**。

## 硬约束

- **临时目录** `/tmp/opencode/LLVM-069t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **`Process-01` 补丁纪律**：树形补丁集 + 一文件一补丁 + `git apply`；`make check-patch-tree` 断言⑥绿。
- **一键证据脚本** `.work/evidence/LLVM-069t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁** `tee`。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **注入有效性**：注入后须验 `git -c core.quotepath=false diff --name-only` **非空**；还原须**含重建**（源码还原 ≠ 二进制还原）。
- **重建成本申报 + 脱离工作区生命周期**：改 `components/llvm-project/patches/**` ⇒ 开工前写明「重建 LLVM（增量），预计 N 分钟」；**长构建须 `setsid nohup … >log 2>&1 &` 脱离 opencode 工作区**（`lessons §8.21`），落盘完成标记（`EXIT=$rc`），**禁**会话内后台等待器；一次构建、勿零散重跑。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/llvm/LLVM-069t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **`setcc` 全谓词可编译**：对 `eq/ne/slt/sle/ult/ule/sgt/sge/ugt/uge`（有/无符号）各构造返回比较值的函数，`clang`（或 `llc`）**rc=0** 生成目标文件（给真实命令 + 输出）。原崩溃最小复现 `int f(int a,int b){return a==b;}` 必须 rc=0。
2. **`setcc` 语义正确（E2E）**：至少覆盖「相等 / 有符号小于 / 无符号小于 / 不等 / `!x` / 逻辑与」各一例，经「编译 → 链接 → QEMU 执行 → **正确退出码**」端到端通过（给真实命令 + 退出码）；含 `return (a<b)`、`return !x`、`return (a<b)&&(c<d)` 形态。
3. **整数 `select_cc`/`select` 语义正确（E2E）**：三目 `?:`（有/无符号条件）经端到端执行**退出码正确**（给真实命令 + 退出码）；-O2 形态（if-conversion 产生的 `select_cc`）不再崩溃。
4. **真实 C 可编译**：Embench `support/main.c:37` 的 `return (!correct)` 惯用法与 `verify_benchmark` 的 `return (比较)` 惯用法**可编译**（给真实命令 + rc）；不要求在 `TESTCASES-039t` 范围内跑通全量基准。
5. **不回归**：`make build-mc`/`make check`/`make check-patch-tree`/`make check-lit` EXIT=0（通过数与改前**逐项相等 / 不下降**，计数由门控现场统计）。
6. **`spec/` 交集为空**：`git -c core.quotepath=false diff --name-only | grep -E '^(spec|contracts)/'` → 无输出。
7. **一键证据脚本**：`.work/evidence/LLVM-069t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检（如把某谓词的 `CMP`/`CMPU` 选错或归一化常数改错 ⇒ 断言/期望 FAIL ⇒ `cp`+md5 还原 ⇒ 重建 ⇒ 回绿），给真实输出与退出码。
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
