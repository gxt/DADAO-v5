# LLVM-077t: `-O2` `Cannot select: ... load<..., zext from i1>`【它类缺口】

**模块**：llvm
**项目里程碑**：M6
**依赖**：`INFRA-050t`（一次构建 `DADAO;X86`）、`INFRA-051t`（Embench 源树）、`LLVM-062t`/`LLVM-063t`/`LLVM-069t`/`LLVM-073t`（均已 `已验证`）、`QEMU-052t`（ELF 加载，`已验证`）；**与 Wave 2 其它 llvm 任务同改 `components/llvm-project/patches` ⇒ 串行**
**状态**：已验证

> **覆盖缺口**：**`ISS-186`**（`aha-mont64 -O2` 的 `i1` zext-load 后端缺口；**它类**，与 G2 无关）。

## 用户裁定（2026-10-10，原话/结论）

> 用户 **2026-10-10 裁定：4 条缺口（`ISS-182` / `ISS-185` / `ISS-186` / `ISS-181`）全部纳入 M6**（「10 点前完不成 ⇒ 全加、跑一晚上」）。本任务 = **`ISS-186`**，**先诊断根因**再修。

## 执行环境
**执行环境**：本地

## 背景 / 问题根源（自包含）

- **现象**：`aha-mont64` 在 `-O2` 编译 `mont64.c` **rc=1**，`LLVM ERROR: Cannot select: ... load<..., zext from i1>`；`-O0` rc=0 正常。此前被 `ISS-176`（G2）掩盖（`-O2` 先撞 G2）。
- **形态**：`trunc(load i64)` ⇒ `load i1` + `zext` **无 lowering**（后端缺 `i1` 的 load/zext 组合选择）。
- **定性**：DADAO 后端**缺该形态的 lowering/pattern**（**须先诊断根因**：是缺 `i1` 的 `load` 合法化、还是缺 `zext i1` 选择、抑或 `setcc`/布尔表示相关；给最小 `.ll` 复现与 `-debug-only=isel` 轨迹）。
- **性质 = 缺能力（编译期显式失败，非静默）**。
- **命中基准**：`aha-mont64`（`-O2`）。

**证据指针**：`.work/log/llvm/LLVM-073t-review-*.log`；`.tao/tasks/llvm/LLVM-073t-128位乘高半umul_lohi.md`「新发现/坑④」「遗留问题②」；issue `ISS-186`。

## 接口规范

- **输入**：
  - `components/llvm-project/patches/llvm/lib/Target/DADAO/**`（源树 `.work/source/llvm-project`）。
  - `.work/source/embench-iot/src/aha-mont64/mont64.c`（复现源）；`.tao/knowledge/contract-isa.md`（访存/位宽相关指令）；`contract-abi.md`（**M6 不引 libc/compiler-rt**）。
  - `spec/Process-01-组件补丁组织与构建编排.md`（补丁纪律）。
- **输出**（`components/llvm-project/patches/llvm/lib/Target/DADAO/**` + 必要的 `tests/llvm/**`/`tests/e2e/**`）：
  1. **诊断报告（先）**：给最小复现（`.ll`/`.c`）+ 触发指令（`load i1` zext 形态）+ 根因结论（缺哪条 action/pattern）。
  2. **修复**：为该形态实现 lowering/pattern（**或**若诊断表明应经合法化在更早阶段拆分，则说明并落地相应改动），使该形态 `-O2` 可编译、语义正确。
  3. 受影响 `tests/llvm/**` 期望值按册/契约**重新派生**（**不从实现反填**）；新增向量覆盖 `i1` zext-load 形态。
  4. `series`/`changelog.md` 随任务追加（`Process-01`）。
- **约束**：
  - 语义口径来自 `spec/`/`contracts/`（**不从实现反推**，Spec-first）。
  - **不改 `spec/`/`contracts/`**（`git -c core.quotepath=false diff --name-only | grep -E '^(spec|contracts)/'` → 无输出）；纯后端能力补全 ⇒ 无新决策、无需 ADR。
  - **不引 libc/compiler-rt**（M6 约束；若实现依赖运行时辅助例程，须停下报告）。
  - 计数口径**派生自单一真源、不硬编码**。

## 硬约束

- **临时目录** `/tmp/opencode/LLVM-077t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **`Process-01` 补丁纪律**：树形补丁集 + 一文件一补丁 + `git apply`；`make check-patch-tree` 断言⑥绿。
- **一键证据脚本** `.work/evidence/LLVM-077t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁** `tee`。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **注入有效性**：注入后须验 `git -c core.quotepath=false diff --name-only` **非空**；还原须**含重建**（源码还原 ≠ 二进制还原）。
- **重建成本申报 + 脱离工作区生命周期**：改 `components/llvm-project/patches/**` ⇒ 开工前写明「重建 LLVM（增量），预计 N 分钟」；**长构建须 `setsid nohup … >log 2>&1 &` 脱离 opencode 工作区**（`lessons §8.21`），落盘完成标记（`EXIT=$rc`），**禁**会话内后台等待器；一次构建、勿零散重跑。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/llvm/LLVM-077t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **最小复现 `-O2` 可编译**：`aha-mont64`（或诊断得出的最小 `.ll`/`.c`）`llc`/`clang` `-O2` **rc=0**（给真实命令 + rc；附改前 rc=1/134 对照）。
2. **根因已诊断**：给最小复现 + 触发指令 + 根因结论（缺哪条 action/pattern），并在完成区**引用证据**（`-debug-only=isel` 或等价轨迹）。
3. **E2E 正确**：该形态（或 `aha-mont64`）经「编译 → 链接 → QEMU 执行 → **正确退出码**」端到端通过（给真实命令 + 退出码）。
4. **不回归**：`make build-mc`/`make check`/`make check-patch-tree`/`make check-lit` EXIT=0（通过数与改前**逐项相等 / 不下降**）。
5. **`spec/` 交集为空**：`git -c core.quotepath=false diff --name-only | grep -E '^(spec|contracts)/'` → 无输出。
6. **一键证据脚本**：`.work/evidence/LLVM-077t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检（**改/禁该 lowering ⇒ 断言 FAIL/rc≠0 ⇒ `cp`+md5 还原 ⇒ 重建 ⇒ 回绿**），给真实输出与退出码。
7. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区

**测试结果**：一键证据 `.work/evidence/LLVM-077t/run.sh` 功能档 `checks=28 failed=0 RUN_EXIT=0`；`--inject` `RUN_EXIT=0`（注入〔`Promote`→`Legal`〕⇒`llc_repro_O0/O2`+`lit_i1_load`+`e2e_O2_byte0` 共 4 检查 FAIL、`llc` rc=134 `Cannot select … zext from i1`⇒`cp`+md5 还原〔`ce45c89c563845873809bccbb2bcbada` 相等〕⇒重建⇒回绿）。门控：`build-mc`(no work)/`check`/`check-patch-tree`(109 patches, `series` 71)/`check-lit`(**89/89**＝基线 88＋本任务 1) 均 EXIT=0。

**修改文件**：补丁 2 份 `components/llvm-project/patches/llvm/lib/Target/DADAO/{DADAOISelLowering.cpp,DADAOCodeGen.td}.patch`、`components/llvm-project/changelog.md`、`tests/llvm/lit/CodeGen/DADAO/i1-load.ll`(A)、`tests/e2e/i1_load_e2e.c`(A)、本任务书；证据（gitignored）`.work/evidence/LLVM-077t/run.sh`。`series` 仍 71；组件源树 HEAD `5ae35d385`=base+1 clean。

**验收结果**（真实命令 + rc；缺口原话 `ISS-186`：`aha-mont64 -O2` 编译 `Cannot select: … load<…, zext from i1>`；`-O0` 正常）：
- ① 最小复现（`@g=internal global i1` + `load i1`+`select`，＝`GlobalOpt` shrink-to-bool）：`llc -march=dadao -O2` **rc=0**（改前 rc=134 同 `Cannot select … zext from i1`）；发射 `ld.ub rd8, [rb4, 0]`；`clang -O0/-O2 -c` rc=0。
- ② 根因：i1 存储型 load-ext 默认 `Legal`（`TargetLoweringBase::initActions`）而后端仅 i8/i16/i32/i64 load pattern。轨迹 `.work/log/llvm/LLVM-077t-evidence.log.insel`：`ISEL: Starting selection on root node: t11: … zext from i1` → 全表 `Match failed` → `LLVM ERROR: Cannot select: t11 … zext from i1`（注入档实测）。
- ③ E2E：`tests/e2e/i1_load_e2e.c`（`set_g` noinline 常量存储 ⇒ `-O2` `load i1`、`-O0` 普通 i64 load）BYTE0..7×O0/O2＝**16 逐字节全等**（host Python oracle 读源常量，0 mismatch）；`aha-mont64` 编译→链接→QEMU **`-O0`/`-O2` guest exit=0**。
- ④ 不回归：四门控 EXIT=0（check-lit 89/89 不下降）。⑤ `git -c core.quotepath=false diff --name-only | grep -E '^(spec|contracts)/'` → 无输出。⑥ 证据脚本见「测试结果」。⑦ `git status --porcelain -uall` 仅本任务 5 文件，无 `_tmp/_orig/_rej`。
- ⑥(**Embench 复测，现场统计**) 编译 rc=0：`-O0` **19/19**、`-O2` **19/19**；全 E2E（编译→链接→QEMU exit=0）：`-O0` **19/19**、`-O2` **19/19**。**`aha-mont64 -O2` 唯一失败已消除。**

**新发现/坑**：① i1 存储型 load-ext 默认 `Legal` 而非 `Expand`（`initActions` 只把 i2/i4 置 Expand）⇒ `zextloadi1` 直达 ISel 无 pattern；标准修法 `Promote` 到 i8（SystemZ/Mips/MSP430 同法，`LegalizeDAG.cpp` 有专门注释解释 i1→i8 技巧）。② `SEXTLOAD i1` 提升后**附带**产生 `sign_extend_inreg i64,i1`（`LegalizeDAG` L776）⇒ 须一并给 `ext.so …,0` pattern，否则只是换一种 `Cannot select`。③ 本形态源自 `GlobalOpt::TryToShrinkGlobalToBoolean`（初值＋单一常量存储的静态全局 ⇒ `i1`），与 BE 无关（i1 全局只存 0/1，`ld.ub` 语义精确）。④ `llc` 崩溃 rc=134（SIGABRT）。

**遗留问题**：无（`ISS-186` 收口）。

## 审阅记录

#### 第 1 轮 engineer 自审

**自主逐行审查**（2 文件改动）：
- `DADAOISelLowering.cpp`：`for (MVT VT : MVT::integer_valuetypes()) setLoadExtAction({EXTLOAD,SEXTLOAD,ZEXTLOAD}, VT, MVT::i1, Promote);`——对齐 SystemZ/Mips 先例；本后端仅 i64 合法 ⇒ 实际只 i64 行生效，其余无害。语义：i1 内存占一字节（DAG MMO 报 8 位）且良定义值为 0/1 ⇒ 提升到 i8 的 `ld.ub`（`§3.1.1` `zero_extend(mem8[…])`）精确。
- `DADAOCodeGen.td`：`(i64 (sext_inreg GPRD:$src, i1)) → (ext_so_orri GPRD:$src, 0)`——`§6.4.2` hd=0 复制 bit0 并从 bit0 符号扩展 = 0/−1；immu6 含 0。
- 边界：`-O0`/`-O2`、`zext`/`sext`、全局/指针两类地址、`-verify-machineinstrs` 干净（lit `i1-load.ll`）。
- 防造假：证据脚本用真实 `llc`/`clang`/`ld.lld`/QEMU；oracle 为 host Python 读源常量（单真源，无硬编码）；计数现场统计（`checks=28`、`16 byte`、`E2E_*`、`19/19`）；`--inject` 注入→4 FAIL→`cp`+md5（`ce45c89c…`）→重建→回绿 `RUN_EXIT=0`；全脚本无 `tee` 吞码。

**finding 处置**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 证据脚本 `check_aha_mont64` 的 `local o=$1 d=$WORK/aha-$o` 在 `set -u` 下 `o: unbound variable`（与 `LLVM-076t` F2 同型） | ✅已修 | 拆成独立 `local` 赋值 | 功能档重跑 `checks=28 failed=0 RUN_EXIT=0` |
| F2 仅补 `ZEXTLOAD` 会漏 `EXTLOAD`/`SEXTLOAD`（后者的提升伴生 `sext_inreg i1`） | ✅已修 | 置三条 + 补 `ext.so …,0` pattern | `sext_bool` lit 断言 + `i1-load.ll` FileCheck rc=0 |
| F3 `tests/e2e/i1_load_e2e.c` 的 `-O0` 需确认不产生 `load i1`（否则形态不可判别） | ✅已修 | 证据脚本加 `shape_O0_no_load_i1` 断言 | `shape_O0_no_load_i1: PASS` |

**判决**：finding 全部 ✅已修，状态置 `待验收`。

#### 第 1 轮 reviewer 验收

**重跑记录**（真实输出/退出码，独立构造用例）：

1. **独立最小复现**（自写 `.ll`：`@g1 = global i1 false` + `load i1` + `zext`/`sext`）：
   - `llc -march=dadao -O2` rc=0；`llc -O0` rc=0
   - asm：`zext_global` → `ld.ub rd8, [rb4, 0]`；`sext_global` → `ld.ub rd4, [rb4, 0]` + `ext.so rd8, rd4, 0`
2. **根因证据**：`.work/log/llvm/LLVM-077t-evidence.log.insel`（独立注入 `Expand` 实测，见下）：
   - `ISEL: Starting selection on root node: t11: i64,ch = load<... zext from i1> ...`
   - `Match failed` × 多条 → `LLVM ERROR: Cannot select: t11 ... zext from i1`
3. **独立语义**（proper i1 store/load，非 i8 类型双关；X86 参照后端 -O2 行为一致）：
   - `zext(i1 true)` → exit=1 == handcalc=1 ✓
   - `zext(i1 false)` → exit=0 == handcalc=0 ✓
   - `sext(i1 true)` → exit=255 == handcalc=255 ✓
   - `sext(i1 false)` → exit=0 == handcalc=0 ✓
   - 注：用 i8 全局值 0xFE/0xFF 加载为 i1 的 zext 在 X86 -O2 上同样返回整字节值（254/255），属 LLVM `AssertZext` 语义（i1 内存值 0/1 假设），非 DADAO 缺陷
4. **E2E**（独立重跑）：`i1_load_e2e.c` BYTE0-7 × O0/O2 = 16 次编译→链接→QEMU，guest exit 逐例匹配 Python oracle，0 mismatch；`aha-mont64 -O0` exit=0，`-O2` exit=0
5. **Embench 独立统计**：`-O0` 19/19、`-O2` 19/19 compile rc=0（live count，非硬编码）
6. **回归**：`make build-mc` RC=0；`make check-patch-tree` 109 patches RC=0；`make check-lit` 89/89 PASS RC=0
7. **证据脚本**：`run.sh` 功能档 checks=28 failed=0 RUN_EXIT=0
8. **独立注入**（与 engineer 不同：`Promote` → `Expand`，非 `Legal`）：
   - 注入：`md5sum` before=ce45c89c563845873809bccbb2bcbada；rebuild llc（ninja -j8）；`llc -O2` rc=134（SIGABRT，Cannot select）→ 预期 FAIL ✓
   - 还原：`cp` backup → after_md5=ce45c89c…（相等）；rebuild llc；`llc -O2` rc=0，ld.ub emitted → 回绿 ✓
9. **补丁纪律**：`series` 71；一文件一补丁（2 文件各 1 `.patch`）；非空 blob；源树 `5ae35d385`=base+1 clean；`git diff --name-only | grep -E '^(spec|contracts)/'` → 无输出
10. **无残留**：`git status --porcelain -uall` 仅本任务 5 文件 + 任务书；无 `_tmp/_orig/_rej`

**判决**：**Accepted** — 全部 10 条独立核验通过，无 finding。状态可置 `已验证`。

#### architect 提交留痕

- 档位：**正常提交**（reviewer 判 `Accepted`）。
- 提交：`d448997`（`LLVM-077t: 修 i1 存储型 load-ext …`）；文件集对账（`git diff --cached --name-only` vs 完成区「修改文件」）= 6/6 一致，**无漏提/多提/越界**。
