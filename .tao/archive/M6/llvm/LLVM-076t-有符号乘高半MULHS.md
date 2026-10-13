# LLVM-076t: 有符号乘高半 `MULHS` / `SMUL_LOHI`【G2 同族】

**模块**：llvm
**项目里程碑**：M6
**依赖**：`INFRA-050t`（一次构建 `DADAO;X86`）、`INFRA-051t`（Embench 源树）、`LLVM-062t`/`LLVM-063t`/`LLVM-069t`/`LLVM-073t`（均已 `已验证`）、`QEMU-052t`（ELF 加载，`已验证`）；**与 Wave 2 其它 llvm 任务同改 `components/llvm-project/patches` ⇒ 串行**
**状态**：已验证

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

**测试结果**：证据 `.work/evidence/LLVM-076t/run.sh` 功能档 `RUN_EXIT=0`（checks=50 failed=0）；`--inject` `RUN_EXIT=0`（注入⇒5 检查 FAIL〔lit + oracle m1_c0/c1 + m3_c0/c1〕⇒`cp`+md5 还原〔md5 `3511bf2958f2e6d363a9c7d0fa362ed7` 相等〕⇒重建⇒回绿）。门控 `build-mc`/`check`/`check-patch-tree`(109 patches)/`check-lit`(**88/88**＝基线 87＋本任务 1) 均 EXIT=0。

**修改文件**：补丁 2 份（改）`components/llvm-project/patches/llvm/lib/Target/DADAO/{DADAOCodeGen.td,DADAOInstrInfo.cpp}.patch`、`components/llvm-project/changelog.md`（追加）；新增 `tests/llvm/lit/CodeGen/DADAO/smul-lohi.ll`、`tests/e2e/smulhi_e2e.c`；本任务书。证据（gitignored）`.work/evidence/LLVM-076t/run.sh`、日志 `.work/log/llvm/LLVM-076t-*.log`。`series` 仍 71；组件源树 HEAD `6868a04fd`=base(`6dfe1677a`)+1 clean。

**验收结果**（真实命令 + rc；缺口原话 `ISS-185`：`有符号乘高半 MULHS/SMUL_LOHI 缺失 ⇒ long g(long a,long b){return a*b/3;} ⇒ llc rc=134 Cannot select … mulhs`）：
- ① 最小复现 `long g(long a,long b){return a*b/3;}`：`llc -march=dadao -O0/-O2` **rc=0**（改前 rc=134 同一 `Cannot select … mulhs`）；反汇编 `mul.so {rd4, rd0}, rd4, rd5`（`rdha`=高半、`rdhb`=`rd0` 丢弃低半；依据 `contract-isa.md §6.1.4` `mul.so rdha:rdhb=rdhc×rdhd`）；`clang -O0/-O2 -c` **rc=0**。
- ② 独立 oracle（host Python **有符号**大整数；10 边界用例×4 模式＝40 用例、**320 次逐字节全等**，0 mismatch；含 `-1`/负数/跨 `2^32`/`2^63-1`/`-2^63`/`(2^63-1)^2`/`(-2^63)^2`）：`RUN_EXIT=0`。**实现=ISA 专用 `mul.so`（非等价序列）。**
- ③ **半字序可判别**（引 `lessons §8.46`）：lit/E2E 用**非交换** `hi - lo`（非 `xor`）；`halfswap_sensitivity` 现场统计 **6/10** 用例低字节随半字互换而变；**注入两半互换 ⇒ lit 与 oracle m3 均 FAIL**（见 `--inject`）。
- ④ E2E `tests/e2e/smulhi_e2e.c`：clang→ld.lld→QEMU，`-DMODE=0..3`（低半/高半`mulhs`/`a*b/3` 有符号/非交换 `hi-lo`）逐字节退出码＝Python（如 mode1 case0 hi=0⇒退出码 0；case1=`0x3fffffffffffffff`）。
- ⑤ `aha-mont64` **`-O0` 全部对象 rc=0**；`-O2` 被**它类缺口** `ISS-186`（`Cannot select … load<…, zext from i1>`）阻塞、**不阻断**；**现场统计** `bench_sweep_O0: 19/19` 基准 `-O0` 全 rc=0。
- ⑥ 门控 EXIT=0（见上，`check-lit` 88/88 不下降）。⑦ `git -c core.quotepath=false diff --name-only | grep -E '^(spec|contracts)/'` → 无输出。⑨ `git status --porcelain -uall` 仅本任务 5 文件，无 `_tmp/_orig/_rej`。

**新发现/坑**：① 与 `MULHU`/`UMUL_LOHI`（LLVM-073t）**同族**：`MULHS`/`SMUL_LOHI` 亦默认 `Legal`（`TargetLowering` 初值）却无 pattern ⇒ `Cannot select: … mulhs`。② `mul.so` 定义序 (rdha=high, rdhb=low)，而 `ISD::SMUL_LOHI` 结果序 (low, high) ⇒ 伪指令列 (lo,hi) 后由 `expandPostRAPseudo` **换序**（同 `mul.uo`）。③ 有符号 `a*b` 的**高半**走 `mul.so`、**低半**走 `mul.uo`（低 64 位有/无符号相同）。④ XOR 交换不变 ⇒ 对半字序不敏感（§8.46），故改用 `hi-lo`；另有 4/10 用例 hi==lo 时低字节天然不可判别（已记入统计口径）。

**遗留问题**：无（`ISS-185` 实现面已收口）；`aha-mont64 -O2` 的 `zext from i1` load 缺口归 `ISS-186`/另立（非本任务能力缺口）。

## 审阅记录

#### 第 1 轮 engineer 自审

**自主逐行审查**（2 文件改动）：
- `DADAOCodeGen.td`：`MULHS_PSEUDO`＝`(set GPRD:$dst,(mulhs GPRD:$a,GPRD:$b))`；`SMUL_LOHI_PSEUDO`＝`(set $lo,$hi,(smullohi …))`，结果序 (low,high) 与 `ISDOpcodes.h`／`TargetLowering::expandDIVREMByConstant`（`getValue(0)=Lo`）一致——与既有 `MULHU/UMUL_LOHI` 同构。
- `DADAOInstrInfo.cpp`：`MULHS_PSEUDO → mul.so Dst,rd0,a,b`（高半入 Dst、低半丢 `rd0`）；`SMUL_LOHI_PSEUDO → mul.so {Hi,Lo},a,b`（换序）；满足「双目的不得同时 rd0」。
- 边界：常量操作数（`BuildSDIV` 经 `CONST_WYDE` 物化入 GPRD，lit `sdiv3` 实测 `set.zw`+`mul.so`）、i128 有符号乘（`smul128_delta`/mode3 实测 `mul.so {rd5,rd4}`）、`-O0`/`-O2`、`-verify-machineinstrs` 干净。
- 防造假：真实 `llc`/`clang`/`ld.lld`/QEMU；计数现场统计（`ORACLE: cases=40 byte-comparisons=320`、`bench_sweep 19/19`）；`--inject` 注入→FAIL→`cp`+md5→重建→回绿；无 `tee` 吞码。

**finding 处置**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 证据脚本 `oracle_num_cases` 未剥注释 ⇒ 把 `IN_A` 注释内 `0x123456789abcdef0` 当数据（11≠10），oracle 在 case10 越界 FAIL | ✅已修 | 解析前剥 `/* */` 与 `//` | 功能档 `ORACLE: cases=40 …`、`RUN_EXIT=0` |
| F2 lit `sdiv3` 断言 `set.ow`，实际有符号 magic 常量 `0x5556…5555` 为正 ⇒ 用 `set.zw` | ✅已修 | 改 `set.zw` | llc+FileCheck rc=0 |
| F3 lit `muldiv3` 期望低半 `mul.so`，实际为 `mul.uo`（低半有/无符号相同） | ✅已修 | 首行改 `mul.uo {rd0, rdN}` | llc+FileCheck rc=0 |
| F4 已提交 `umul128_xor` 式 XOR 交换不变、对半字序不敏感（§8.46） | ✅已改 | 用例改**非交换** `hi - lo` + oracle mode3 + `halfswap_sensitivity` 现场统计 | 注入 m3 FAIL、`6/10` 用例可判别 |
| F5 只验 `aha-mont64` 不足以覆盖「相关基准」 | ✅已补 | 证据脚本加 `bench_sweep_O0`（全 `src/*/` 现场统计） | `bench_sweep_O0: 19/19` |

**判决**：finding 全部 ✅已修，状态置 `待验收`。

#### 第 1 轮 reviewer 验收（**Accepted**）

**环境处置**：22:06:55 起另一并发 reviewer 会话在同一源树/构建树做注入自检，致 `clang-23` 重写中无 +x（my oracle rc=126 现场留存）。22:13 用户确认无并发后继续。对方 `REBUILD_RESTORE_EXIT=0`/`RUNSH_RESTORE_EXIT=0`；ninja no-op 确认二进制↔干净源码对应后继续。

**快照对账**：开工快照（6 文件 status + 5 文件 md5）已留 snap-pre.*；**终态快照 diff rc=0、md5 全一致、组件源树 clean**——注入已完全还原。

**已重跑（真实输出/退出码）**：
- **门控**：`check-patch-tree` EXIT=0「109 patches OK」；`check-lit` EXIT=0「88/88 Passed」含 `smul-lohi.ll`；`make check` EXIT=0；`build-mc` EXIT=0（no work to do）。
- **证据脚本功能档**：rc=0，RUN_EXIT=0，checks=50 failed=0；halfswap=6/10，ORACLE 320/320，bench_sweep 19/19，aha-mont64 O0 全绿、O2 被 `zext from i1`（ISS-186）挡。
- **最小复现**：`llc -O0/-O2 rc=0`，`mul.so {rd4, rd0}, rd4, rd5`（高半入 rd4、低半丢 rd0）——独立确认。
- **独立 oracle**：Python 独立重算 40 期望值（读工程师 C 矢量 IN_A/IN_B、自写 signed big-int 逻辑），0 mismatch（ORACLE_VERIFY: cases=40 mismatches=0）。
- **半字序判别**：独立 Python 验证 6/10 用例 `(hi-lo)&0xff ≠ (lo-hi)&0xff`——与 engineer 的 halfswap_sensitivity=6 完全一致。
- **`--inject` 重跑**：RUN_EXIT=0；注入后 5 FAIL（lit + m1_c0/c1 + m3_c0/c1）→ md5 `3511bf…` 还原 → 重建 → 回绿。
- **我的独立注入（仅 SMUL_LOHI 双目互换、不动 MULHS）**：注入后 10 FAIL（m3_c0..c9 全报；m0/m1/m2 全 PASS、lit PASS）→ `cp`+md5 还原 → 重建 → 50/0 回绿。**两半互换注入被非交换语义断言检出** ✓。
- **spec|contracts 交集**：grep rc=1（空）。
- **脚本审计**：各断言可达 FAIL 路径；注入锚 assert 唯一；计数现场统计。

**观察（不阻断）**：`smulhi_e2e.c` 未接入 `tests/e2e/lit`（半字序回归保护仅在 gitignored 证据脚本中），与 `LLVM-073t` 的 `mulhi_e2e.c` 先例一致；结构 lit 覆盖指令选择、e2e 覆盖语义——可后续统一改进。

**判决**：**Accepted**——全部 9 条验收标准满足、硬约束无违反、注入自检通过、独立 oracle 独立验证通过。
