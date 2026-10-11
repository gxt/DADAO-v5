# LLVM-073t: 128 位乘高半 `umul_lohi` / `mulhu`【G2】

**模块**：llvm
**项目里程碑**：M6
**依赖**：`INFRA-050t`（一次构建 `DADAO;X86`）、`INFRA-051t`（Embench 源树）、`LLVM-062t`/`LLVM-063t`/`LLVM-069t`（均已 `已验证`）、`QEMU-052t`（ELF 加载，`已验证`）；**与 Wave 2 其它 llvm 任务同改 `components/llvm-project/patches` ⇒ 串行**
**状态**：已验证

> **覆盖缺口**：**G2（`ISS-176`）**。

## 执行环境
**执行环境**：本地

## 背景 / 问题根源（自包含）

- **现象**：`Cannot select: ... mulhu t5, Constant:i64<-6148914691236517205>`（`llc` rc=134）。
- **最小复现**：`unsigned long f(unsigned long a, unsigned long b){ return a*b/3; }`（`-O0`/`-O2`）——**非 2 的幂除数**触发 128 位乘高半；`unsigned long long` 直接路径亦触发（aha-mont64 `mulul64`）。
- **定性**：DADAO 后端**无 `ISD::MULHU`（及 `umul_lohi`/多字乘）的 lowering/模式**。
- **命中基准**：aha-mont64（`-O0`/`-O2`）、wikisort（`-O0` 的 `mulhu`）。
- **性质 = 缺能力（编译期显式失败，非静默）**。

**证据指针**：`.work/log/testcases/TESTCASES-039t-stage1-gaps.md §G2`；矩阵 `.work/log/testcases/TESTCASES-039t-stage1-matrix{,-O0}.log`；issue `ISS-176`。

## 接口规范

- **输入**：
  - `components/llvm-project/patches/llvm/lib/Target/DADAO/**`（源树 `.work/source/llvm-project`）。
  - `.tao/knowledge/contract-isa.md`（乘/移位/进位相关指令，如 `mul`/`mulh`/`mulhu` 类；若 ISA 无高位乘，则须给出等价展开路径）；`contract-abi.md`（若涉 libcall 或 `__umulh` 运行时——**注意 M6「不引 libc/compiler-rt」约束**）。
  - `spec/Process-01-组件补丁组织与构建编排.md`（补丁纪律）。
- **输出**（`components/llvm-project/patches/llvm/lib/Target/DADAO/**` + 必要的 `tests/llvm/**`/`tests/e2e/**`）：
  1. **128 位乘高半 lowering**：为 `ISD::MULHU`（及必要的 `umul_lohi`/多字乘分解）实现 lowering/模式，使 `a*b/c`（非 2 的幂）与 `unsigned long long` 乘法可编译、语义正确。
  2. 如需新增 `DADAOISD` 节点/模式或改 `DADAOISelDAGToDAG`/`DADAOCodeGen.td`/`DADAOISelLowering.{h,cpp}`，一并落地；受影响 `tests/llvm/**` 期望值按册/契约**重新派生**（**不从实现反填**）。
  3. `series`/`changelog.md` 随任务追加（`Process-01`）。
- **约束**：
  - 语义口径来自 `spec/`/`contracts/`（**不从实现反推**，Spec-first），须给乘高半的**独立 oracle** 手算（如 host Python 大整数乘法）验证。
  - **不改 `spec/`/`contracts/`**（`git -c core.quotepath=false diff --name-only | grep -E '^(spec|contracts)/'` → 无输出）；纯后端能力补全 ⇒ 无新决策、无需 ADR。
  - **不引 libc/compiler-rt**（M6 约束；若实现依赖运行时辅助例程，须停下报告）。
  - 计数口径**派生自单一真源、不硬编码**。

## 硬约束

- **临时目录** `/tmp/opencode/LLVM-073t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **`Process-01` 补丁纪律**：树形补丁集 + 一文件一补丁 + `git apply`；`make check-patch-tree` 断言⑥绿。
- **一键证据脚本** `.work/evidence/LLVM-073t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁** `tee`。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **注入有效性**：注入后须验 `git -c core.quotepath=false diff --name-only` **非空**；还原须**含重建**（源码还原 ≠ 二进制还原）。
- **重建成本申报 + 脱离工作区生命周期**：改 `components/llvm-project/patches/**` ⇒ 开工前写明「重建 LLVM（增量），预计 N 分钟」；**长构建须 `setsid nohup … >log 2>&1 &` 脱离 opencode 工作区**（`lessons §8.21`），落盘完成标记（`EXIT=$rc`），**禁**会话内后台等待器；一次构建、勿零散重跑。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/llvm/LLVM-073t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **`mulhu` 可编译**：最小复现 `unsigned long f(unsigned long a, unsigned long b){ return a*b/3; }`（`-O0`/`-O2`）经 `clang`/`llc` **rc=0**（给真实命令 + rc + 反汇编证据）。
2. **乘高半语义正确**：给**独立 oracle**（host Python 大整数）手算的边界用例（大值、跨 `2^32`、`2^64-1` 乘积）与 DADAO 产出**逐条**一致（不得采样）。
3. **E2E**：`a*b/c`（非 2 的幂）与 `unsigned long long` 乘法经「编译 → 链接 → QEMU 执行 → **正确退出码**」端到端通过（给真实命令 + 退出码）。
4. **真实基准**：aha-mont64 **rc=0**（至少 `-O0`；`-O2` 若仍受它类缺口阻塞须说明，不阻断本任务）。
5. **不回归**：`make build-mc`/`make check`/`make check-patch-tree`/`make check-lit` EXIT=0（通过数与改前**逐项相等 / 不下降**）。
6. **`spec/` 交集为空**：`git -c core.quotepath=false diff --name-only | grep -E '^(spec|contracts)/'` → 无输出。
7. **一键证据脚本**：`.work/evidence/LLVM-073t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检（改高半计算/进位 ⇒ 断言 FAIL ⇒ `cp`+md5 还原 ⇒ 重建 ⇒ 回绿），给真实输出与退出码。
8. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区

**测试结果**：一键证据 `.work/evidence/LLVM-073t/run.sh` 默认 `RUN_EXIT=0`（checks=48 failed=0）；`--inject` `RUN_EXIT=0`（注入⇒`lit_umul_lohi`+`oracle_m1_c0` FAIL⇒`cp`+md5 还原〔md5 `b260038c…` 相等〕⇒重建⇒回绿）。门控：`make build-mc`/`check-patch-tree`(109 patches)/`check-lit`(**82/82**＝基线 81＋本任务 1)/`check` 均 EXIT=0。

**修改文件**：补丁 2 份 `components/llvm-project/patches/llvm/lib/Target/DADAO/{DADAOCodeGen.td,DADAOInstrInfo.cpp}.patch`、`components/llvm-project/changelog.md`、`tests/llvm/lit/CodeGen/DADAO/umul-lohi.ll`(A)、`tests/e2e/mulhi_e2e.c`(A)、本任务书；证据（gitignored）`.work/evidence/LLVM-073t/run.sh`。`series` 仍 71；组件源树 HEAD `90a6d2d7`=base+1 clean。

**验收结果**（真实命令 + rc；缺口原话 `ISS-176`：`128 位乘高半 umul_lohi / mulhu 不可 select（Cannot select: ... mulhu rc=134）`；最小复现 `unsigned long f(unsigned long a,unsigned long b){return a*b/3;}`）：
- ① 最小复现：`llc -march=dadao -O0/-O2` **rc=0**（改前 rc=134 同一 `Cannot select … mulhu`）；反汇编证据 `mul.uo {rd4, rd0}, rd4, rd5`（`rdha`=高半、`rdhb`=`rd0` 丢弃低半；依据 `contract-isa.md §6.1.4` `mul.uo rdha:rdhb=rdhc×rdhd`）；`clang -O0/-O2 -c` **rc=0**。
- ② 独立 oracle（host Python 大整数；10 边界用例×4 模式＝40 用例、**320 次逐字节全等**，0 mismatch；含大值/跨 2^32/`2^64-1`/`(2^64-1)^2`）：`RUN_EXIT=0`。**实现=ISA 专用 `mul.uo`（非等价序列）。**
- ③ E2E `tests/e2e/mulhi_e2e.c`：clang→ld.lld→QEMU，`-DMODE=0..3`（低半/高半/`a*b/3`/`lo^hi`）逐字节退出码＝Python（如 case0 hi=`0xfffffffffffffffe`⇒退出码 254）。
- ④ aha-mont64（`umul_lohi`）：**`-O0` rc=0**；`-O2` 被**它类缺口**阻塞（`Cannot select … load<…, zext from i1>`，与 G2 无关，不阻断）。
- ⑤ `build-mc`/`check`/`check-patch-tree`/`check-lit` EXIT=0（check-lit 82/82 不下降）。⑥ `git -c core.quotepath=false diff --name-only | grep -E '^(spec|contracts)/'` → 无输出。⑧ 仅本任务改动，无 `_tmp/_orig/_rej`。

**新发现/坑**：① i64 `MULHU`/`MUL_LOHI` 默认 `Legal`（`TargetLowering` 初值）⇒ `BuildUDIV`/`expandMUL_LOHI` 直接生成 `mulhu`/`umul_lohi`，必须给 pattern，否则 `Cannot select`。② `ISD::UMUL_LOHI` 结果序 **(low, high)**（`ISDOpcodes.h`；`TargetLowering::expandDIVREMByConstant` bind `getValue(0)=Lo`），而 `mul.uo` 定义序 (high, low) ⇒ 伪指令须**换序**。③ 同族缺口（**未修、范围外**）：`MULHS`/`SMUL_LOHI` 亦缺 pattern（`long g(long,long){return a*b/3;}` 仍 rc=134）。④ aha-mont64 `-O2` 新暴露 `i1` zext-load 缺口（`trunc(load i64)→load i1`），此前被 G2 掩盖。

**遗留问题**：① `MULHS`/`SMUL_LOHI`（`mul.so` 同族）未在本任务范围（任务书仅列 `mulhu`/`umul_lohi`）⇒ 建议另立任务；② aha-mont64 `-O2` 的 `i1` load 缺口（归它类/另立）。二者均非本任务能力缺口，`ISS-176` 实现面已收口。

## 审阅记录

#### 第 1 轮 engineer 自审

**自主逐行审查**（2 文件改动）：
- `DADAOCodeGen.td`：`MULHU_PSEUDO`＝`(set GPRD:$dst,(mulhu GPRD:$a,GPRD:$b))`（`mulhu`＝`SDTIntBinOp`：1 结果/2 参，常量操作数由 matcher 物化入 GPRD）；`UMUL_LOHI_PSEUDO`＝`(set $lo,$hi,(umullohi …))`，结果序 (low,high) 与 `ISDOpcodes.h`/`expandDIVREMByConstant`（`getValue(0)=Lo`）一致。
- `DADAOInstrInfo.cpp`：`MULHU_PSEUDO → mul.uo Dst,rd0,a,b`（高半入 Dst、低半丢 `rd0`；满足「双目的不得同时 rd0」）；`UMUL_LOHI_PSEUDO → mul.uo {Hi,Lo},a,b`（定义序 high,low＝换序）。
- 边界：常量操作数（两 pattern 实测 OK）；i128 路径（`umul_lohi` 实测 `{rd5,rd4}` 双非 rd0）；`-O0`/`-O2`；`-verify-machineinstrs` 干净。
- 防造假：证据脚本用真实 `llc`/`clang`/`ld.lld`/QEMU；计数现场统计（`ORACLE: cases=40 byte-comparisons=320`）；`--inject` 注入→FAIL→`cp`+md5（`b260038c…`）→重建→回绿 `RUN_EXIT=0`；无 `tee` 吞码。

**finding 处置**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 lit RUN 未开 `-verify-machineinstrs`（2 结果伪指令无 MIR 校验） | ✅已修 | `umul-lohi.ll` RUN + 证据 `check_lit` 加该 flag | `llc -O0/-O2 -verify-machineinstrs` rc=0；`check-lit` 82/82 |
| F2 证据脚本 `local o=$1 bdir=…$o` 在 `set -u` 下 `o: unbound variable` | ✅已修 | 拆成独立 `local` 赋值 | 功能档 `RUN_EXIT=0` checks=48 |
| F3 `oracle_expect` 把注释内 `0xAAA` 当数据（IN_B 解析出 11 项） | ✅已修 | 解析前剥离 C 注释 + 改注释 | `cases: 40`（A=B=10 现场统计）；oracle 全等 |
| F4 `MULHS`/`SMUL_LOHI` 同族缺口 | ⏸延后 | 未改（任务书仅列 `mulhu`/`umul_lohi`） | `long g(long,long){return a*b/3;}` 仍 rc=134（记入遗留） |

**判决**：finding 全部 ✅已修或 ⏸延后（F4 范围外），状态置 `待验收`。

#### 第 1 轮 reviewer 验收

**重跑记录**（全部 reviewer 自跑，真实 rc；日志 `.work/log/llvm/LLVM-073t-review-*.log`）：
- ① 最小复现（自写 `r.ll`/`r.c`）：`llc -march=dadao -O0/-O2` rc=0/rc=0；`clang -O0/-O2 -c` rc=0/rc=0；反汇编 `mul.uo {rd0, rd4}, rd16, rd17`（低半）+ `mul.uo {rd4, rd0}, rd4, rd5`（高半，`rdhb=rd0` 丢低半）——确用 `mul.uo`。
- ② 独立语义 oracle（reviewer 自写 `oracle_check.py`，自选 10 边界〔0/1/2^31/2^32±1/2^63/2^64-1/`(2^32+1)^2`/`(2^64-1)^2`〕×4 模式 ×8 字节）：**320/320 逐字节全等，mismatch=0**（`HILO/REVIEW-ORACLE-EXIT=0`）。**半字序判定**：mode1 高半 `(2^32+1)^2→0x1`、`(2^64-1)^2→0xff…fe` 正确；另补**非交换** `hi-lo` 用例强制双目的 `mul.uo {rd5, rd4}`（反汇编确认），8×8=64 字节全等（`(2^32+1)^2` ⇒ `0xfffffffe00000000`）⇒ **`UMUL_LOHI` 换序正确、半字未互换**。
- ③ E2E `a*b/c`（`0x123456789abcdef0*0xfedcba9876543210/3`）：clang/ld.lld/QEMU rc=0/0/170；host Python 全值 `0x0bcf2daa1cb2efaa`，低字节 170 ✓。
- ④ aha-mont64：`-O0` 4 对象全 rc=0；`-O2` `mont64.c rc=1`，`Cannot select: t78: i64,ch = load<…>, zext from i1>`（reviewer 独立复现）。
- ⑤ 不回归（一次一个 make）：`make build-mc` rc=0（ninja no work）；`make check-patch-tree` rc=0（3 组件 109 patches OK）；`make check-lit` rc=0（Total 82 / Passed 82 / Failed 0 / Unsupported 0；前任务 LLVM-072t 提交记 81/81 ⇒ 81+1 不下降）；`make check` rc=0（`repository checks: PASS`）。⑥ `diff --name-only | grep -E '^(spec|contracts)/'` 计 0；`git status` 交集亦空。
- ⑦ 证据脚本（逐条审：llc/lit/oracle/aha/spec 均有可达 FAIL 路径、oracle 逐字节现场比对、计数现场统计、无 `tee` 吞码）：功能档重跑 `checks=48 failed=0 RUN_EXIT=0`。**reviewer 独立注入**（与半字互换不同：`MULHU_PSEUDO` 展开 `mul_uo_rd→mul_so_rd`，有符号高半不同值）：diff 非空、md5 `b260038c…→ad2e2b94…`，重建 rc=0 ⇒ 同脚本 **`RUN_EXIT=1`（9 FAIL：llc_repro O0/O2、lit、oracle_m1 六用例逐字节不符）** ⇒ `cp` 还原 md5 回 `b260038c…`（与 engineer 记录一致）⇒ 重建 rc=0 ⇒ 复跑 `RUN_EXIT=0`。
- ⑧ 补丁纪律：`series` 71 条（现场 `grep -vc`）；`check-patch-tree` 断言绿；两补丁派生内容与源树文件**逐字节相等**（647/533 行）；源树 HEAD `90a6d2d78`=锁 base `6dfe1677a`+1 clean；`git status --porcelain -uall` 仅本任务 6 文件，无 `_tmp/_orig/_rej`；验收前后快照（status+md5）逐行对账一致。

**约束核验**：临时目录 `/tmp/opencode/LLVM-073t-review/` ✓；未改被测物/未提交 git ✓；构建 `setsid` 脱离 + JOBS=8 ✓；还原用 `cp`+md5（未用 checkout/restore/stash）✓；证据脚本未代写 ✓。

**新缺口复核（属实，供登记）**：① `long g(long,long){return a*b/3;}` ⇒ `llc rc=134`，`LLVM ERROR: Cannot select: t14: i64 = mulhs t5, Constant:i64<6148914691236517206>`（`MULHS`/`SMUL_LOHI` 未实现，建议另立）；② aha-mont64 `-O2` 阻塞于 `load<…, zext from i1>`（它类缺口，与 G2 无关）。

**非阻断建议**：已提交用例中 mode3 `lo^hi` 为 XOR 交换不变、lit `umul128_xor` 亦然，**区分不了双目的换序**；建议后续在 `umul-lohi.ll`/`mulhi_e2e.c` 补 `hi-lo` 之类非交换断言（本审查已实测通过，不阻断）。

**判决**：**Accepted**——验收 1–8 全部经 reviewer 独立重跑通过，约束无违反；两处新缺口属实且均非本任务范围。
