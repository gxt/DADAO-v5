# LLVM-070t: `-O2` 误编译致死循环（诊断根因 + 修复）【G6 · 优先】

**模块**：llvm
**项目里程碑**：M6
**依赖**：`INFRA-050t`（一次构建 `DADAO;X86`）、`INFRA-051t`（Embench 源树）、`LLVM-062t`/`LLVM-063t`/`LLVM-069t`（均已 `已验证`）、`QEMU-052t`（ELF 加载，`已验证`）；**与 Wave 2 其它 llvm 任务同改 `components/llvm-project/patches` ⇒ 串行**
**状态**：已验证

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

**根因**：DADAO 后端**未处理尾调用**——`tail call` 被当普通 `call` 发射，且调用者因 `IsTailCall` 为真**不再发射 `ret`**；`call` 在 RegRAS（`ra63`）压入的返回地址 = 调用者函数结束处（当 `call` 是最后一条指令时即**被调者自身入口**）⇒ 被调者 `ret` 弹回自身入口，**静默无限重入**。触发点 = `warm_caches` 的 `tail call @benchmark_body`（`-O2` 内联+展开放大循环体，稳定复现；`-O1` 因重入后参数被 clobber 侥幸退出）。定位证据（IR `-emit-llvm`、`llc` 各优化级对照、`UPPERLIMIT`/禁展开二分、反汇编逐字节对比、`qemu -d exec,nochain` PC 序列、`-d cpu` 寄存器 dump）见 `.work/log/llvm/LLVM-070t-rootcause{,-raw}.md|.log`；最小复现 `mm.c`（`LOCAL_SCALE_FACTOR=3`）`-O2`=124 / `-O0/-O1`=0。
**修复**：`DADAOTargetLowering::LowerCall` 拒绝尾调用形态（`CLI.IsTailCall=false`，依 `TargetLowering::CallLoweringInfo::IsTailCall` 文档约定）⇒ 发普通 `call`+正常 `ret`（正确代码）；`musttail` 不可合法降级 ⇒ `report_fatal_error`（显式失败，不静默错码）。
**ISS-180 原话**：「`huffbench`/`matmult-int`/`nettle-sha256`/`statemate` 在 `-O2` 编译成功（clang/llc rc=0），但 QEMU 运行超时被杀（`GUEST_EXIT=124`）；同基准 `-O0`/`-O1` exit=0…属 `-O2` 优化级误编译（非算法死循环）…任何 `-O2` 产物都可能静默错码」。
**测试结果**：`.work/evidence/LLVM-070t/run.sh` → `fail=0 detected=1 RUN_EXIT=0`（含注入自检）。
**修改文件**：`components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOISelLowering.cpp.patch`（源改 1 文件，`series` 仍 71）；新增 `tests/llvm/lit/CodeGen/DADAO/tail-call-lowering.ll`；`components/llvm-project/changelog.md`（追加 LLVM-070t 行）。
**验收结果**（真实输出+退出码，日志 `.work/log/llvm/LLVM-070t-*.log`）：
1. **4 基准 `-O2` E2E**（clang→ld.lld→QEMU 带 `timeout`）逐例 **exit=0**：huffbench=0、matmult-int=0、nettle-sha256=0、statemate=0。
2. **`-O0` 不下降**：depthconv/huffbench/matmult-int/nettle-aes/nettle-sha256/nsichneu/statemate/tarfind/ud/xgboost **10/10 exit=0**。
3. **门控**：`make check` EXIT=0；`make check-patch-tree` 3 组件 109 patches OK；`make check-lit` 78 discovered/77 passed/1 unsupported（+1 新测试）；`make build-mc` PASS。
4. `spec|contracts` 交集空；`git status --porcelain -uall` 仅 patch+新 lit 两项，无 `_tmp/_orig/_rej`。
5. **注入自检**：`if (CLI.IsTailCall)`→`if (false)` ⇒ 重建 llc ⇒ 尾调用复现、断言 FAIL（`inject-detected`）⇒ `cp`+md5（`cde06736…`）还原 ⇒ 重建 ⇒ 回绿。
**新发现/坑**（建议沉淀）：①DADAO 无尾调用指令 ⇒ `LowerCall` 必须显式拒绝 `tail`（清零 `IsTailCall`，`musttail` 显式失败），否则静默错码。②`-O1` 的同类缺陷因重入后寄存器被 clobber「偶然退出」，**不得**以「-O1 正常」判其无缺陷。③**同一 bug 两种表现**：void 尾调用 ⇒ 静默死循环（G6）；非 void 尾调用 ⇒ `LowerCall emitted a return value for a tail call!` 断言（G4/`LLVM-074t`）——G4 与 G6 **同根**。
**遗留问题**：①本任务仅**拒绝**尾调用（正确、放弃该优化）；**实现**真尾调用（tail-jump 复用调用者返回地址 + 拆帧）留 `LLVM-074t`（与 G4 同根，本修复已消除其实质缺陷）。②`-O2` 其余缺口 G1–G5 由 `LLVM-071t`~`073t` 处置，不在本任务范围。

## 审阅记录

#### 第 1 轮 engineer 自审

**判决**：可交付（`待验收`）。改动范围 = `components/llvm-project/patches/**`（1 补丁）+ `tests/llvm/**`（1 新测试）+ `changelog.md`；未动 `spec/`/`contracts/`，未改已有函数签名，未引入外部依赖。

**自主逐行审查**：
- `LowerCall` 新守卫置于 `SelectionDAG` 取参之后、`CallConv` 校验之前；`CLI.IsTailCall=false` 使 `TargetLowering::LowerCallTo` 走非尾路径（返回 value chain），`SelectionDAGBuilder::visitCall` 因而正常发射 `ret`（已由反汇编确认 `call`+`ret`）。仅改 `IsTailCall` 一个字段，不影响参数/返回值 lowering。
- `musttail`：`CLI.CB && CLI.CB->isMustTailCall()` ⇒ `report_fatal_error`（`CLI.CB` 可能为空，已判空）。非 `musttail` 的 `tail`（提示性）可安全降级。
- 边界：间接调用（函数指针）、varargs、sret 路径均不引用 `IsTailCall`（`grep` 确认 `LowerCall` 内无该字段使用），零副作用。
- 回归防护：4 基准 `-O2`=0、`-O0` 10/10=0、`make check`/`check-lit`/`check-patch-tree`/`build-mc` 全绿。
- 防造假：证据脚本 `rc=$?` 直取退出码（无 `tee`）；注入真实重建 llc 并检出；还原以 `cp`+md5 对账（`cde06736…` 相等）+ `check-source-state` 干净。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 是否属「禁优化级规避」 | ❌不修（非规避） | —（`IsTailCall` 清零是 LLVM 文档指定的能力边界处理；发正确代码，非降 `-O`） | `.work/log/llvm/LLVM-070t-rootcause.md` §4 |
| F2 `musttail` 直接清零会否误编译 | ✅已修 | 加 `isMustTailCall()` ⇒ `report_fatal_error` | 源码守卫 + `grep` 无其他 `IsTailCall` 使用 |
| F3 与 G4（`LLVM-074t`）是否重复 | ✅已记录 | 同根，void/非-void 两表现 | 完成区「新发现」③ |

#### 第 1 轮 reviewer 验收

**判决：Accepted**（1–8 逐条独立重跑；长输出 `.work/log/llvm/LLVM-070t-review-*.log` + `/tmp/opencode/LLVM-070t-review/`）

1. **根因**：补丁 hunk 位于 `DADAOTargetLowering::LowerCall` 开头（`CLI.IsTailCall` 守卫）✓。独立取 `matmult-int` `-O2` 中间产物（`clang -O2 -S -emit-llvm`，rc=0）：`warm_caches` = `tail call fastcc void @benchmark_body(...)`（IR 第 25 行）✓；修复后机器码 = `call [rb0, benchmark_body]` + 帧恢复 + `ret rd0, 0`；**修复前**（我注入态反汇编）= `call [rb0, benchmark_body]` 后**无 `ret` 直接 `.Lfunc_end1`** ⇒ 与「被调者返回自身入口/下一函数」根因吻合。
2. **4 基准 `-O2` E2E**（我自拼管线 `/tmp/opencode/LLVM-070t-review/my-e2e.sh`，clang→ld.lld→qemu `-timeout 60`）：huffbench/matmult-int/nettle-sha256/statemate 逐例 `GUEST_EXIT=0 rc=0`；**`-O0` 10 例逐例 `GUEST_EXIT=0`**（depthconv/huffbench/matmult-int/nettle-aes/nettle-sha256/nsichneu/statemate/tarfind/ud/xgboost）不下降。
3. **非绕过**：`git status --porcelain -uall` 仅 4 文件（patch+changelog+新 lit+任务书），**无** `components/embench-iot/**`、`tests/scripts/**` 改动；diff 仅 `LowerCall` 一处守卫、无优化级/Embemb 源改动；`musttail` 确为 `report_fatal_error`（真跑：`LLVM ERROR: DADAO: 'musttail' calls are not supported…`，rc=134，显式失败）✓。
4. **G4 判定（可关）**：构造非 void 尾调用 `.ll`（`%r = tail call i64 @callee`）。修复后 `llc` **rc=0**、发射 `call`+`ret rd0, 0`（无断言）；我注入态（恢复原行为）同一输入 **断言崩溃 rc=134**：`SelectionDAGBuilder.cpp:11745: Assertion '(!CLI.IsTailCall || InVals.empty()) && "LowerCall emitted a return value for a tail call!"' failed`。⇒ G4 断言与 G6 同根（尾调用形态未处理），本修复使该断言路径不可达，**G4 可关**（`LLVM-074t` 仅余「实现真尾调用」能力项）。
5. **我的独立注入**（删 `CLI.IsTailCall = false;` 清零行，与 engineer 的 `if(false)` 不同）：注入前 md5 `cde06736b29695b633f6ae5cb5c9091f` → 注入后 `438b42b10262d2c93ca2c965a65c5c01`，`git diff --name-only` 非空 1 文件 → `make build-mc` EXIT=0（重建，`setsid`+JOBS=8，`/tmp/opencode/LLVM-070t-review/inj.build.log`）⇒ **FAIL 复现**：matmult-int `-O2` **GUEST_EXIT=124**（qemu 仅 `[board:init]`、timeout 杀）、lit 形态破（`call` 后无 `ret`）、G4 断言 rc=134 ⇒ `cp`+md5 还原（=`cde06736…` 相等，源树 `git status` 0 行）⇒ **重建** `make build-mc` EXIT=0 ⇒ **回绿**：4 基准 `-O2` 逐例 rc=0、`warm:`=`call`+`ret rd0, 0`、G4 输入 rc=0。
6. **门控**（一次一个，我自跑）：`make build-mc` EXIT=0（`build-mc: PASS`）；`make check` EXIT=0（`repository checks: PASS`）；`make check-patch-tree` EXIT=0（`3 component(s), 109 patches OK`）；`make check-lit` EXIT=0（78 discovered/77 passed/1 unsupported，`PASS: DADAO-CodeGen :: tail-call-lowering.ll`）；**重建后复跑 `check-lit` EXIT=0、78/77/1 不下降**。
7. **补丁纪律**：`series` llvm=71/qemu=34/embench=4（llvm 补丁文件恰 71、无空 blob、`DADAOISelLowering.cpp.patch` 单文件对应）；`git diff --name-only | grep -E '^(spec|contracts)/'` **无输出**（rc=1）；无 `_tmp/_orig/_rej`（`.work/source` 下 `_tmpl.cpp` 为 LLVM 自带测试夹具、子串误匹配，非残留）。
8. **证据脚本**（`.work/evidence/LLVM-070t/run.sh`）：逐条审 25 项断言均有可达 FAIL 路径（`check`/`detect` 双向比较、注入 `md5_changed`+`diff_nonempty` 防空注入、`cp`+md5 还原、无 `tee`、rc 直取、结尾 `exit` 正确）；**重跑**：`fail=0 detected=1`，`RUN_EXIT=0`（`.work/log/llvm/LLVM-070t-review-evidence.log`）。完成区/日志与我重跑数字逐项一致（4/4 `-O2`、10/10 `-O0`、78/77/1、109 patches）。

**问题/披露（均不构成打回）**：
- 我的 E2E 脚本首轮 `GUEST_EXIT=127`：系**我脚本缺陷**（build 树无 `qemu-system-dadao`，`timeout` 找不到命令），非产品失败；现场留存，显式给 QEMU 路径后重跑得 124（注入态）/0（还原态）。
- 审查期间工作区新增 `.opencode/**` 12 个未跟踪文件（非我创建、非本任务产物，与全局规则更新同段出现，疑平台同步）；4 任务文件 md5 前后 `MD5_IDENTICAL`、快照仅此差异 ⇒ 请 architect 提交前处置（gitignore 或披露）。
- engineer 注入自检为结构性断言（asm 无 `ret`），未复现运行期死循环；我已用 E2E `GUEST_EXIT=124` 独立补足，不构成打回。
- 还原纪律核验：全程 `cp`+md5（未用 `git checkout/restore/stash`、未用 `git show >`）；工作区/源树快照前后对账如上。

#### architect 提交（文件集审核与收尾）

**档位**：reviewer 判决 **Accepted** ⇒ **正常提交**（无 `WIP:` 前缀）。**只 `commit`、未 `push`**（push 归主会话 `/complete` 后）。
**文件集对账**（显式 staging、逐个路径，**禁** `git add -A`）：产物 = 补丁 `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOISelLowering.cpp.patch` + `components/llvm-project/changelog.md` + `tests/llvm/lit/CodeGen/DADAO/tail-call-lowering.ll` + 本任务书 + 收尾台账（`milestones.md`〔`LLVM-070t` 已验证 + 结束时间 + `LLVM-074t`/`TESTCASES-039t` 行说明〕/`issues.yaml`〔`ISS-178`/`ISS-180` 置 `closed` + `resolved_by: LLVM-070t`〕/`lessons.md §8.43`/`LLVM-074t` 任务书改范围）——与完成区「修改文件」**逐条相等**（**无漏提 / 无多提 / 无越界**）。
**`.opencode/**`（12 未跟踪文件）处置**：经查为**用户刻意迁入的项目级 opencode 配置**（`agent/command/instructions`，与全局源 `~/t.a.o/opencode/{agent,command,instructions}` HEAD **逐字节相同**）——**属项目内容、非运行时会话缓存** ⇒ **不删除、不加 `.gitignore`、不纳入本次提交**（尊重用户迁移，见回报）。

