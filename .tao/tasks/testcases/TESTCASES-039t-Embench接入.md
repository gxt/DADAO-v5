# TESTCASES-039t: Embench 接入（钉子③）

**模块**：testcases
**项目里程碑**：M6
**依赖**：`INFRA-051t`（Embench 组件接入）、`LLVM-062t`/`063t`（编译能力）、`QEMU-052t`（ELF 加载）
**状态**：待开始（⚠️ **阻塞**：交付工具链缺整数 `setcc`/`select_cc` lowering ⇒ 首验收不可达；见「完成区」）

> **追加（2026-10-10）**：本任务**新增依赖** `LLVM-069t`（整数 `setcc`/`select_cc` lowering，`ISS-173`）+ `INFRA-054t`（clang 内置头/resource-dir，`ISS-174`）；**二者就绪后重新下发**。当前 `状态` 保持 `待开始`，阻塞说明（完成区）保留。证据指针：`.work/log/testcases/TESTCASES-039t-{blocker.log,progress.md}`。

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

> ⚠️ **未完成 / 阻塞**：首验收（≥1 最小基准退出码 0）**不可达**——交付工具链无法编译任何真实 C（详见下）。判据**未降级**（恒定 = 退出码 0）。未产出交付物（board shim/runtime/md5 补丁），因其**无法编译/验证**，产出即属降级判据。

**测试结果**：0/1 首验收通过（阻塞）。19/19 基准均无法编译（非运行失败，是编译即崩）。

**修改文件**：无交付物改动。仅新增证据（`.work/` 不入 git）：`.work/log/testcases/TESTCASES-039t-{blocker_probe.sh,blocker_probe_result.txt,matrix.sh,matrix_result.txt,blocker.log,progress.md}`。

**验收结果**：
- **阻塞（致命）**：DADAO 后端**无法 lower 整数 `setcc`（比较取值）/ 整数 `select_cc`**。最小复现：`int f(int a,int b){return a==b;}` → `clang` rc=1、`llc` rc=134（均 *error in backend: Cannot select: i64 = setcc ... :ch*）。矩阵：`== != < <= && ! 三元 ?: 无符号比较 及 main.c:37 return(!correct)` **全部 FAIL**；仅纯分支 `if(a<b) return 1; return 0;`（`br(icmp)`，-O0）可过（-O2 if-convert 又转 `select_cc` 崩）。后端源码仅设 `ISD::BR_CC/BRCOND=Custom`，**无 SETCC/SELECT_CC action/pattern**；`llc` 手工 `.ll` 复现 ⇒ 与 clang 无关。⇒ 14/19 基准 `verify_benchmark` 直接 `return (比较)`，其余经 `main.c` 过 `setcc` ⇒ **无一基准可编译**。
- **阻塞（次要、可绕过）**：clang 内置头缺失——`-print-resource-dir`→`.dadao/cross-toolchain/lib/clang/23`（**不存在**）；`#include <stddef.h>` 即失败。
- **反例证据（证明工具链其余部分正常）**：`if(a<b)`（分支形）`clang rc=0 → ld.lld rc=0 → qemu rc=0`；`m6_varargs.ll`（`br(icmp)`）`llc rc=0`。

**新发现/坑**：① M6「LLVM-062t/063t 已验证」**≠「可编译真实 C」**：各任务范围**均未覆盖**整数 `setcc`-as-value/`SELECT_CC`；M4/M6 向量一律用 `br(icmp)` 回避此形态，`LLVM-066t` 注释已自认「no FP setcc-as-value」。② 判据证据：`.work/log/testcases/TESTCASES-039t-progress.md`（含命令/退出码/建议）。

**遗留问题**：**未修**（越界：修它须改 `components/llvm-project/**`）。建议：①**新增 LLVM 任务**补整数 `setcc`/`select_cc` lowering；（可选）② `install-host` 随装 clang 内置头（或约定 `-resource-dir`）；③ 二者就绪后**重新下发 TESTCASES-039t**。

## 审阅记录

#### 第 1 轮 engineer 自审（2026-10-10，**无代码改动**，自审=阻塞核实）

- 本任务无源码改动（未产出交付物），自审=**独立复核阻塞结论**：先用手工 `.ll`（不含 clang）在 `llc` 上复现 `setcc` 崩溃 → 排除 clang/TargetInfo 因素，确认为后端 ISel 能力缺口；再矩阵化 C 构造（O0/O2）→ 确认 Embench 必经形态无一可编。**判定**：首验收不可达，判据不降级，`待开始`（阻塞）返回。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 整数 `setcc`/`select_cc` 无 lowering ⇒ Embench 不可编译 | ⏸延后（越界，须改 `components/llvm-project/**`） | 无（越界；仅记录） | `.work/log/testcases/TESTCASES-039t-{blocker.log,matrix_result.txt}`；`llc sc.ll` rc=134 |
| clang 内置头缺失（resource-dir 不存在） | ⏸延后（可绕过，非本任务致命项） | 无 | `.work/log/testcases/TESTCASES-039t-blocker_probe_result.txt`（D1 rc=1 / D3 NO） |

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
