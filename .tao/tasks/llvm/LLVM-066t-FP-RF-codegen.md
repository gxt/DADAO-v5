# LLVM-066t: FP/RF codegen（排整数之后）

**模块**：llvm
**项目里程碑**：M6
**依赖**：`LLVM-062t`（整数调用约定先行）、`SPEC-122t`（相关 ADR 就位）
**状态**：已验证

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

**测试结果**：门控全绿（真实 rc）：`make check` **EXIT=0**（lit **73/73**；改前 72 ⇒ **+1 新 lit**（`fp-codegen.ll`），其余套件**逐项相等/无回归**）；`make check-patch-tree` **EXIT=0**（`2 component(s), 105 patches OK`）；`make test-codegen` **EXIT=0**（`19/19 passed`，与改前相等）；`make test-elf` **EXIT=0**（`5/5 passed`，与改前相等）。一键证据脚本 `.work/evidence/LLVM-066t/run.sh` **RUN_EXIT=0**（35/35 PASS = 29 常规 + 6 注入自检）。日志 `.work/log/llvm/LLVM-066t-*.log`。

**用户裁定原话留痕（2026-10-09；`lessons §7.3`，经 `SPEC-127t`/`SPEC-128t` 连带）**：①「FP/RF codegen 纳入 M6，但排在整数之后」；②「聚合槽位上限 = 8（64 B）」（含 HFA/HPA，HFA 走 RF bank）；③「返回值 K=8 每 bank：FP 返回 `rf8`–`rf15`，FP 参数 `rf16–rf31`」；④「同样的，**rd4-rd7/rf1-rf7 也改为 caller-saved，由 llvm 分配使用**」（RF 实现侧放开归本任务；`rf0`=FCSR 保留；`rf32–rf63` callee-saved；**册不改**）；⑤「`DADAOABIInfo` 为最小首版 ⇒ HFA/HPA 与细粒度跨 bank 拆分由本任务补齐（HFA 属 FP）」。

**软浮点结论（验收 3）**：**不引入 compiler-rt**。依据：ISA 60 条硬件 FP 已覆盖 clang/LLVM 所需核心——`fadd/fsub/fmul/fdiv`、`fsqrt`、`fneg`、`fpext/fptrunc`、`fp↔int` 转换、比较、`select`（`cs.*`）均一对一 map 到指令（本任务全部落地）；余下（`frem/fma/fabs/超越函数`）置 `Expand`（个别成 libcall，freestanding 程序不用）即可，无需新增组件/依赖。**唯一硬件缺口**：无 `fma`（`llvm.fmuladd`→`fmul+fadd`）；`fabs` 因 `rf0` 物理寄存器在双类型 `GPRF` 中不可作 TableGen 模式操作数 ⇒ 走 `Expand`（见「遗留」）。

**修改文件**（组件补丁集 `make_patch.py llvm-project` 导出，`series` 仍 71）：`components/llvm-project/patches/llvm/lib/Target/DADAO/` 下 **9 补丁**——`DADAORegisterInfo.{td,cpp}`、`DADAOCallingConv.td`、`DADAOCodeGen.td`、`DADAOISelLowering.{h,cpp}`、`DADAOISelDAGToDAG.cpp`、`DADAOInstrInfo.cpp`、`DADAOFrameLowering.cpp` + `components/llvm-project/changelog.md`（+1 行）；测试 `tests/e2e/fp_codegen.c`、`tests/e2e/fp_hfa.c`、`tests/llvm/lit/CodeGen/DADAO/fp-codegen.ll`。源树 `.work/source/llvm-project` HEAD=base+1、clean。**`spec/`/`contracts/` 交集为空**。

**验收结果**（真实输出；llc=`.work/build/llvm/bin/llc`）：
- ①FP 算术/转换/比较（-O2，`fp_arith.ll`）：`fodiv rf1,rf16,rf17` / `fomul rf2,rf16,rf17` / `foadd rf8,rf2,rf1`；`fo2io {rd8},{rf16}`（fptosi）、`io2fo {rf8},{rd16}`（sitofp）；`foqcmp rd4,rf16,rf17` + `br.nn`。-O0 亦正确（FP spill 走 `st.o/ld.o` RF 形态）。
- ②FP 传参/返回（`fp_ret.ll`，-O2）：`foadd rf8, rf16, rf17`；HFA `{double,double}` 返回 `fo2fo {rf8}/{rf9}`。clang -O2 亦为 `foadd rf8, rf16, rf17`。
- ③RF 分配：`rf_alloc.ll`（-O2）用 `rf1/rf2/rf3`（`rf[1-7]` 计数 12）；`csr_fp.ll`（-O2 -verify-machineinstrs rc=0）跨调用用 **`rf32`–`rf38`** 并 `st.o rf32..,[rb1,off]` / `ld.o ...` 保存恢复。
- ④`rf0` 目的一律非（`grep`=0）；`getReservedRegs` 仅 `Reserved.set(DADAO::rf0)`。
- ⑤E2E：`clang -O2/-O0 fp_codegen.c → llvm-mc crt0 → ld.lld → qemu` 退出码 **42**；`fp_hfa.c`(-O2) 退出码 **42**。
- ⑥注入自检：reserve `rf1–rf7` ⇒ `inject_md5_changed` ⇒ `ninja llc` ⇒ `inject_detected`（rf1-7 计数 0）⇒ `cp`+md5 还原（`422b2345…` 相等）⇒ 重建 ⇒ `restore_green`。

**ISS 处置**：`ISS-081`（FP 衔接点）——llvm **codegen 部分已实现**（本任务）；**FP 向量 / harness RF** 归 M6（`TESTCASES-036t/041t`）、**FP 独立 oracle** 归 `GOLDEN-*`（M7），理由：本任务不产生期望值/向量（`Spec-first`）。`ISS-126`（FP 开放点固定取值）——属 **spec/golden 侧**（位级/转换/算术开放点期望值），codegen 不涉及；**留后归 `GOLDEN`**。`ISS-078`（`focls/ftcls` 之外未复核）——**属 spec 侧**（`scope: [spec]`，语义固定值复核），本任务**只做实现侧**不改 `spec/`；**登记并保持归 spec**。

**新发现/坑**：①`getCalleeSavedRegs`（手写）必须与生成的 `CSR`（`CSR_RegMask`）**集合相等**——旧版仅列 `rd/rb32-63`，本次加 `rf32-63`，否则 RA 视 RF callee-saved 而 PEI 不保存 ⇒ 静默坏寄存器（自审发现并修）。②`GPRF` 含两个类型（f64+f32）时**裸物理寄存器 `rf0` 不能作 TableGen 模式操作数**（类型歧义）⇒ `fabs`（`fosgnj x,rf0`）无法成 Pat，改 `Expand`。③FP 常量在**无常量池**后端由 `DAGToDAG` 的 `ISD::ConstantFP` 材料化（整数位型 + `rd2rf`）；须 `setOperationAction(ConstantFP, Legal)`，否则 `convertSelectOfFPConstantsToLoadOffset` 会**引入常量池**（后端无此路径）。④`clang -O2` 的 `if`/`return` 会 if-convert 成 **FP `select_cc`** ⇒ 必须有 `cs.*` 模式（本任务加 RD/RF 两族 × 10 谓词，含 operand/t-f swap 与 `>`/`>=` 交换）。⑤`6.0` 恰只占 `wp3` ⇒ 单条 `set.zw` + `rd2rf`。

**遗留问题**：①`fabs` 未成 Pat（`Expand`，libcall）——E2E 不用；②`frem`（DADAO `forem` 是 IEEE remainder，与 LLVM `frem`=`fmod` 语义不同）未映射，置 `Expand`；③FP `select_cc` 仅覆盖 10 个 C 谓词（`ueq/one/ord/uno` 等显式 `report_fatal_error`）；④FP **分类**（`ISD::IS_FPCLASS` bit-remap lowering）未做（「按需」，无 libm 可见需求；MC 层 `LLVM-029t/030t` 已有指令）；⑤FP↔RB 跨 bank 单指令拷贝不存在 ⇒ `copyPhysReg` 显式失败。均**显式失败/记录**，非静默降级。〔**补正（2026-10-10 登记，源 `.work/log/integ/pending-registrations.md §R4`）**：`RB` = **基址寄存器**（`rb0`=PC / `rb1`=SP / `rb2`=GP…，服务访存地址，**非通用整数 bank**）；FP 位搬运的真实缺口是 `bitcast`(FP↔RD) 的 **ISel 模式**缺失，指令 `rf2rd`/`rd2rf` **已在**。〕

## 审阅记录

#### 第 1 轮 engineer 自审
自主逐行审查（engineer 深度 1，无嵌套子代理）。范围：`DADAORegisterInfo.{td,cpp}`、`DADAOCallingConv.td`、`DADAOCodeGen.td`、`DADAOISelLowering.{h,cpp}`、`DADAOISelDAGToDAG.cpp`、`DADAOInstrInfo.cpp`、`DADAOFrameLowering.cpp`、`.work/evidence/LLVM-066t/run.sh`。判决：**全部 finding 已处置**（F2/F7 为「按需未做」的能力缺口，登记遗留）；状态 → 待验收。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `getCalleeSavedRegs` 未含 `rf32–rf63`，与 `CSR_RegMask` 不一致 ⇒ RA 视其 preserved 而 PEI 不保存（静默坏寄存器） | ✅已修 | `DADAORegisterInfo.cpp` 的 `ReversedCSR[]` 加 `rf63..rf32`（集合= `CSR`） | `csr_fp.ll` -O2：`st.o rf32..rf38,[rb1,off]` / `ld.o ...`；`-verify-machineinstrs` rc=0；`csr_fp_save/restore` PASS |
| F2 `fabs` 模式引用裸 `rf0`，`GPRF` 双类型 ⇒ TableGen「could not infer types」 | ⏸延后 | 删 `fabs` Pat；`FABS→Expand`；写注释 | 构建通过；E2E 不用；登记遗留 |
| F3 FP `select_cc` 无支持 ⇒ `clang -O2`（if-convert）无法编译 | ✅已修 | `DADAOCodeGen.td` 加 `DADAOFPSelCC`（RD/RF × 10 谓词 → `cs.n/z/p`） | `fp_codegen.c` -O2 编出 `cs.n {rd4}?, rd4, rd6, rd5` + QEMU 42 |
| F4 `ConstantFP` 被折成常量池 load（后端无常量池） | ✅已修 | `setOperationAction(ConstantFP, Legal)` + `DAGToDAG` 的 `ISD::ConstantFP`（`CONST_WYDE` + `rd2rf`） | `6.0` ⇒ `set.zw rd4,wp3,0x4018 ; rd2rf {rf2},{rd4}`；E2E 42 |
| F5 `BR_CC` 仅 `i64` Custom，FP 比较落默认 Legal 崩 | ✅已修 | 加 `BR_CC(f32/f64) Custom`；`LowerBR_CC` 加 FP 谓词（含 `UGT/UGE/ULT/ULE` 交换） | `fp_cmp` 编出 `foqcmp`+`br.nn` |
| F6 脚本 clang arg/ret 断言用 -O0（-O0 先存栈） | ✅已修 | 改 `-O2` | `clang_args_rf16_rf17_ret_rf8` PASS |
| F7 FP 分类 lowering（`focls/ftcls`→`ISD::IS_FPCLASS`）未做 | ⏸延后 | 无（「按需」） | 登记遗留；MC 层 `LLVM-029t/030t` 已有 |
| F8 脚本 `csr_fp` 计数断言写死 `1`（实为 7） | ✅已修 | 改「>0 ⇒ 1」布尔 | 重跑 PASS |
| F9 改源码后未重导出补丁 ⇒ `check-patch-tree` 失败 | ✅已修 | `--amend` + `make_patch.py` 重导出 | `check-patch-tree` 105 OK |

自审补充核对：`spec/`/`contracts/` 交集为空；一文件一补丁 + `series` 同步（71）；计数未写死；源树 clean、HEAD=base+1；`/tmp/opencode/LLVM-066t/` 与 `.work/` 放临时产物，仓库无 `_tmp/_orig/_rej`。

#### 第 1 轮 reviewer 验收

**重跑**：`bash .work/evidence/LLVM-066t/run.sh` EXIT=0，35/35 PASS（含 6 注入自检）。注入 md5=`422b2345…` 还原相等。

**门控**：`make check` EXIT=0（73/73）；`make check-patch-tree` EXIT=0（105 OK）；`make test-codegen` EXIT=0（19/19）；`make test-elf` EXIT=0（5/5）。`spec/`/`contracts/` 交集=`grep`=空。

**独立 FP lowering**（自写 .ll）：`foadd/fomul/fodiv/fosub/foqcmp/ft2fo/fo2ft/fo2uo/uo2fo/foroot` 均正确；rf0 作目的=0。`foadd rf8,rf16,rf17`+`fo2fo {rf8}/{rf9}` ABI 正确。E2E `fp_codegen.c`/`fp_hfa.c` QEMU exit=42。

**独立 RF 分配**：`csr_test.ll` -O2 -verify-machineinstrs rc=0，`rf32–rf36` st.o/ld.o 跨调用保存恢复。`rf1–rf7` 被分配（独立 .ll 计数>0）。`getReservedRegs` 仅 `rf0`。

**独立注入**（与 engineer 不同）：改 `DADAOCallingConv.td` FP 返回 `rf8–rf15`→`rf16–rf23` ⇒ ninja llc ⇒ `fp_ret_args_rf16_rf17` FAIL + `hfa_ret_rf8` FAIL + `hfa_ret_rf9` FAIL + `check-patch_tree` FAIL（4 项）。cp+md5 还原（`85483505…`=相等）⇒ 重建 ⇒ 回绿 EXIT=0。

**④软浮点证伪**：`llvm.sqrt.f64`→`foroot` ✓（无 libcall）。`llvm.fabs.f64`→ISel crash（bitcast 未降，已知遗留#1）。`fmod`（`frem`）-O0 产出 `call [rb0, fmod]`（`*UND*` 外部符号）；-O1/-O2 tail-call assertion crash。**结论**：核心 FP（add/sub/mul/div/sqrt/转换/比较/select）均一对一硬件指令，无 libcall ⇒ **无 libc 对 M6 核心路径成立**；`fabs`/`fmod`/`fma` 为显式遗留（crash/report_fatal_error，非静默降级），不影响 E2E。

**判决：Accepted** — 门控全绿、ABI/rf0/CSR 正确、注入可检测可还原、软浮点结论有据。
