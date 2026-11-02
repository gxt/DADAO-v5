# LLVM-131t: 代码模型 default / large（驱动 + 后端）

**模块**：llvm
**项目里程碑**：M10
**依赖**：ADR-0036（已 Accepted）、INFRA-106t（跨度门控，验收用）
**状态**：已验证

## 执行环境
**执行环境**：本地（LLVM 重建 `make install-host` 由主会话执行，属长任务）

## 接口规范

### 背景事实（实测，2026-10-25）
- 直接 `call` / `jump` = REL26（`imms24` 字偏移）⇒ **±32 MiB**；实测 64 MiB 布局 LLD 报
  `R_DADAO_REL26 out of range: 16515066 is not in [-8388608, 8388607]`，16 MiB 布局正常。
- `DADAOTargetMachine.cpp` 默认 `CodeModel::Small`，但后端**零处** `getCodeModel()`；驱动拒绝 `-mcmodel=large|medium`（`unsupported argument`）。
- 动态链接：PLT 12 B、紧贴 `.text`（实测 `.text@0x20240`、`.plt@0x20260`），跨 DSO 调用天然在 ±32 MiB。
- ADR-0036 决策：**两种模型**——`default`（代码 ≤32 MiB、数据任意 48 位）与 `large`（代码任意）；不提供 `medium`/`kernel`/`tiny`。

### 输入
- `components/llvm-project/patches/clang/lib/Driver/ToolChains/DADAO.cpp.patch`（`-mcmodel` 取值与拒绝）
- `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOTargetMachine.cpp.patch`（`CodeModel::Large` 生效）
- `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOISelLowering.cpp.patch` / `DADAOInstrInfo.cpp.patch`（large 的调用/跳转形态）

### 输出
1. **驱动口径**：接受 `-mcmodel=default`、`-mcmodel=large`；`small` = `default` 别名；`medium|kernel|tiny` ⇒ **明确报错**（rc≠0，文案含目标名与允许值）。
2. **`large` 形态**：超出 ±32 MiB 的 `call` / `jump` ⇒ `ABS48` 物化 48 位目标地址 + 间接 `call rb, rd, imm12` / `jump [rb, rd, imm]`；动态导入（走 PLT）保持直接调用；条件分支仍由 `BranchRelaxation` 处理，不引入链接器 thunk。
3. **测试**（lit / 脚本，落 `components/llvm-project/patches/llvm/test/CodeGen/DADAO/` 或既有测试目录）：
   - 远距布局（>32 MiB）在 `large` 下链接成功；
   - 同一布局在 `default` 下 LLD 报 REL26 越界（既有行为，作对照）；
   - 小镜像在 `large` 下功能正确（qemu 运行或等价回归）。

### 约束
- 不改 ISA、不改 `spec/`、不改 REL26 字段定义；
- `-mcmodel=large` 必须在后端**真实生效**后才允许被驱动接受（不得"接受但无行为"）；
- 共享文件（`Clang.cpp` / `CommonArgs.cpp`）如需改动，完成区单列理由。

## 验收标准
1. `-mcmodel=default|large|small` 接受；`medium|kernel|tiny` 报错且信息可读。
2. 远距布局：`large` 链接 rc=0；`default` 报 REL26 越界（对照）。
3. `large` 产物反汇编可见 ABS48 物化 + 间接 `call`；小镜像运行结果与 `default` 一致。
4. `make install-host` 后 L1 绿、L2 代表集绿。
5. 完成区贴真实输出与退出码。

## 完成区
**测试结果**：**返工第 2 轮（default 下 libcall 误走间接 → 已修门控）**；增量重建后：`run.sh` **24 PASS / 0 FAIL / 0 BLOCKED（rc=0）**、`run.sh --inject` **29 PASS / 0 FAIL（rc=0）**、L1 `PASS`（rc=0）、L2 `module checks (L2): PASS`（rc=0）；上一轮 8 个 lit 红全部转绿（reviewer 逐条核到 PASS）。日志：`.work/log/llvm/LLVM-131t-{evidence,evidence-inject,L1,L2}.log`。
**修改文件**：
- 组件（`.work/source/llvm-project`，已 commit 为 base+1 并导出）：`clang/lib/Driver/ToolChains/CommonArgs.cpp`、`clang/include/clang/Basic/DiagnosticDriverKinds.td`、`llvm/lib/Target/DADAO/{DADAOTargetMachine.cpp,DADAOISelLowering.cpp,DADAOISelDAGToDAG.cpp,DADAOInstrInfo.cpp,DADAORegisterInfo.td,DADAOCodeGen.td}`；
- 测试：`tests/llvm/lit/CodeGen/DADAO/code-model-large.ll`、`tests/e2e/lit/mcmodel.test`、`tests/e2e/{mcmodel_e2e.c,mcmodel_far.c,mcmodel_far.lds}`（返工仅改自建用例 `mcmodel.test` 的一个 objdump 期望；**既有 lit 期望值一个未动**）；
- 证据脚本：`.work/evidence/LLVM-131t/run.sh`（`.work/` 不入库）；
- 流程一致性（L1 `check-milestones-fresh` 强制）：`.tao/knowledge/milestones.md` L48 `LLVM-131t` 状态 `待开始`→`待验收`（仅该单元格）+ 本任务书 `**状态**`；
- 生成物重派生：`components/llvm-project/{series,patches/**}`（95 份补丁）+ `tools/llvm/llvm-isa-backend-matrix.{tsv,md}`（补丁行号漂移，`gen_isa_coverage.py`）。
- **共享文件理由（单列）**：`CommonArgs.cpp::addMCModel` 是全目标 `-mcmodel` 的唯一落点（`Clang.cpp:6379` 无条件调用），DADAO 分支只能加在这里；`DiagnosticDriverKinds.td` 新增 1 条 diag —— 现有 diag 都不带「允许值」，而任务要求文案含目标与允许值。
**验收结果**（当次真实输出与退出码）：
- `-fsyntax-only`（编译命令取自 `compile_commands.json`）rc=0 ×5；返工后重跑 `DADAOISelLowering.cpp`/`DADAOISelDAGToDAG.cpp` rc=0/0；注入语法错的同命令 rc=1（可达 FAIL）。
- `ninja lib/Target/DADAO/DADAOCommonTableGen`（仅 tablegen，非构建）rc=0 —— `.td` 改动（GPRBTC + tailjmp_rrii 操作数类）通过。
- `make check-patch-tree` ⇒ `5 component(s), 200 patches OK` rc=0；`make apply-series` ⇒ `llvm-project already applied (base+1, matches patches); skipped` rc=0；`make check-source-state` ⇒ `llvm-project: OK count=1 clean=True`。
- `make check`（L1 全量）⇒ `repository checks (L1): PASS` rc=0（含 `check-instrinfo`、`check-isa-coverage`）；`check-code-range --self-test` 属 **L2**（`check-modules`）已 PASS（见 L2 日志）。
- **ADR-0036 D5 偏离（已说明）**：D5 字面 = 静态 ABS48 物化；**PIC（`-fPIC/-fPIE`）下不用 ABS48**（绝对地址不能写进共享对象 `.text`），改走既有 **GOT PCREL 取址 + 间接 call**（`ADR-0029 D4`）；代码注释见 `DADAOISelLowering.cpp` 的 `useIndirectCallee` 上方。
- 运行时（安装根=**修复前**二进制）：`mcmodel.test` PASS、`tail-call-lowering.ll` PASS、`llc -code-model=medium` 的 `REJECT` 行 PASS、远距布局 large/default 对照 PASS；仅 `code-model-large.ll` 的 `SMALL` 行 FAIL（= 待修的那一处，见第 2 轮自审 F11）。
**新发现/坑**：
1. **门控缺失（返工主因）**：`ExternalSymbolSDNode`（libcall）分支只判了 `Reloc != Static`，漏了 `CodeModel::Large` ⇒ **default 下 libcall 也被物化 + 间接调用**，冲掉 8 条既有 lit（`m6-memintrin`/`f128-codegen`/`p1-fp-libcall-*`/`m8-*-libcall` 等）的 `call [rb0, memcpy]` 形态。教训：**新增「按模型变形」的路径，门控要在唯一入口（lambda 顶部）判一次**，别在每个分支各判一半；`useIndirectCallee` 现为唯一判据（GV 为空 = libcall），`ISD::ExternalSymbol` 选择侧也同门（default 下落到 `SelectCode` 硬报错，不静默变形）。
2. 尾调用的地址寄存器**必须**是 call-clobbered：PEI 把 callee-saved 恢复插在终止指令之前，callee-saved 基址会在「物化地址→jump」之间被覆盖（x86 `GR64_TC` / AArch64 `tcGPR64` 同因）。已加 `GPRBTC`（rb4–rb31）并让 `tailjmp_rrii` 用它；**同一隐患在原函数指针尾调用里已存在**（本次一并修）。
3. FileCheck 的 `--implicit-check-not` 在 **DAG 组内不可靠**（现场构造：DAG 区域内的直接 `call [rb0,` 未被捕获）⇒ 否定断言改用 `%not grep -q`（仓库 `fma_e2e.test` 已有此范式）。
4. **objdump 对 .o 打印的是原始立即数 + 独立重定位行**（`call [rb0, 0]` 后跟 `R_DADAO_REL26 far_fn`），不是汇编文本里的符号形态；自建用例曾按 `.s` 形态写期望 ⇒ 重建后假红。对象级断言须以真实 `llvm-objdump -dr` 输出为准。
5. 改组件补丁会**漂移** `tools/llvm/llvm-isa-backend-matrix.{tsv,md}`（证据列写补丁物理行号），必须重派生；L1 会红否则。
**遗留问题**：
- ~~待增量重建~~ **已完成**：`make install-host`（r2）后 `run.sh` 24/0、`run.sh --inject` 29/0、L1、L2 全绿。
- PIC+`large` 只在汇编层验证（GOT 取址 + 间接 call）；未做 `-shared` 链接测试。
- 单函数内 >32 MiB 的条件分支：`BranchRelaxation` 仍插 `jump_iiii`（ADR-0036 D5 明确「条件分支仍由 BranchRelaxation 处理、不引入 thunk」），越界仍由链接器硬报错 —— 不改，登记为已知边界。
- `-mcmodel=large` + 静态 reloc + `-shared`（即 `-shared` 未加 `-fPIC`）会把 ABS48 落进 `.text`，LLD 报 textrel 类错误（非本次引入，属非 PIC 共享对象的既有错误面）。
- 函数级 `code_model` 属性/逐函数模型未纳入（本任务按 TU 级 `-mcmodel`）。

## 审阅记录

#### 第 1 轮 engineer 自审

逐行审 `LowerCall`（两处 callee 构造 + lambda）、`selectCodeModel`、`ISD::ExternalSymbol` 选择、`GLOBAL_ADDR` 展开、`addMCModel` 分支。finding 与处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 尾调用基址可能落到 callee-saved（epilogue 覆盖） | ✅已修 | 新增 `GPRBTC`（rb4–rb31）+ `tailjmp_rrii` 用它 + tail 路径 vreg 用它 | tablegen rc=0；`-fsyntax-only` rc=0；默认/尾调用 lit 口径见 R1 |
| F2 表生成名冲突：`DADAO::GPRBTC` 是 pressure-set 枚举，类对象叫 `GPRBTCRegClass` | ✅已修 | 改用 `DADAO::GPRBTCRegClass` | `-fsyntax-only` rc=1→0 |
| F3 `addExternalSymbol` 无 offset 参数 | ✅已修 | 去掉 offset（libcall 目标无附加偏移） | `-fsyntax-only` rc=0 |
| F4 `std::optional` 未显式包含 | ✅已修 | 加 `#include <optional>` | 同上 |
| F5 `.td` 行号漂移导致 `check-isa-coverage` 红 | ✅已修 | `gen_isa_coverage.py` 重派生矩阵 | `make check-code-range`/`check-isa-coverage` PASS；L1 PASS |
| F6 E2E 程序在 -O2 下被常量折叠（无调用） | ✅已修 | 输入改 `volatile`，`-S` 复核出现 3 处调用 | 现场 `-S` 输出（`call [rb0, helper]` 等） |
| F7 `--implicit-check-not` 在 DAG 组内失效（假绿） | ✅已修 | LARGE 否定断言改 `%not grep -q`；DEFAULT 保留（非 DAG，已用反例验证） | 现场 canary：注入 `call [rb0,` ⇒ rc=1 |
| F8 weak-undefined 函数在 large 下会变成「跳到地址 0」，破坏 lld 自环约定 | ✅已修 | `useIndirectCallee` 对 external-weak 声明返回 false | `-fsyntax-only` rc=0；行为与 `weak_undef_e2e.c` 一致（该用例不传 -mcmodel） |
| F9 ABS48 物化寄存器 bank 是否正确（`call_rrii` 要 RB） | ❌不修（已核对） | `GLOBAL_ADDR` 走 `set_zw_rb/or_w_rb`，结果本就是 GPRB | 既有 `&gi` 汇编形态（`set.zw rb8…`） |
| F10 测试断言是否可达 FAIL | ✅已修/已证 | 每条新断言均做过 canary | `mimic*.s` + 注入：LARGE/SMALL/PIC/FAR-OBJ/REL26/DEFAULT 全部 rc=0→注入后 rc=1 |

判决：全部 finding 已处理（F9 经核对无需改），状态置 `待验收`。

#### 第 2 轮 engineer 自审（返工：L2 8 红）

输入：`.work/log/llvm/LLVM-131t-L2.log`（8 条 lit 红）+ 主会话定位。逐条核现场后处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F11 **`ExternalSymbolSDNode` 分支缺 `CodeModel::Large` 门控** ⇒ default 下 libcall 被物化+间接调用（8 红根因） | ✅已修 | `largeModelCallee` 顶部统一门控（非 Large 直接 `nullopt`）；libcall 分支改用 `useIndirectCallee(TM, nullptr)` 单一判据 | `-fsyntax-only` rc=0；default 路径未触碰 DAG（结构上恢复旧形态）；`.s` 期望 `call [rb0, memcpy]` 由既有 lit 钉住 |
| F12 选择侧 `ISD::ExternalSymbol` 无条件物化 | ✅已修 | `if (TM.getCodeModel() != CodeModel::Large) break;` ⇒ default 落到 `SelectCode`（硬报错，不静默变形） | 同上 |
| F13 自建用例 `FAR-OBJ-DEFAULT: call [rb0, far_fn]` 期望形态错（objdump 对 .o 打原始立即数 + 独立重定位行） | ✅已修 | 改 `call [rb0, 0]` + `FAR-OBJ-DEFAULT-NEXT: R_DADAO_REL26 far_fn` | 现场真对象 `llvm-objdump -dr far_def_now.o` 通过 rc=0；把 `REL26`→`REL20` 的 canary rc=1 |
| F14 返工是否动了既有 lit 期望值 | ❌不修（无需） | 未动：`git diff --name-only HEAD -- tests/llvm/lit tests/e2e/lit` 仅 `mcmodel.test`（本任务新建） | 见命令输出 |

判决：F11/F12/F13 已修，F14 确认合规；静态自检与 L1 全绿，运行时仅剩「安装根二进制未更新」这一项（`code-model-large.ll` 的 `SMALL` 行），状态保持 `待验收`，待增量重建后转绿。

#### 第 1 轮 reviewer 验收（2026-10-25，独立重跑）

**重跑记录（reviewer 亲自执行，输出留 `.work/log/llvm/LLVM-131t-reviewer-*.log`）**：
- `bash .work/evidence/LLVM-131t/run.sh` ⇒ `24 PASS / 0 FAIL / 0 BLOCKED`，**rc=0**。
- `bash .work/evidence/LLVM-131t/run.sh --inject` ⇒ `29 PASS / 0 FAIL`（I-1 删 series 项 rc=2→还原 md5 相等→回绿），**rc=0**。
- `make check`（L1）⇒ `repository checks (L1): PASS`，**rc=0**（日志含 instrinfo 266 记录校验 + `gen_isa_coverage --check: PASS`）。
- `make check-modules`（L2）⇒ `module checks (L2): PASS`，**rc=0**；上一轮 8 红逐条核：`code-model-large.ll`(20 of 150)、`f128-codegen.ll`、`p1-fp-libcall-logf.ll`、`m8-f128-math-libcall.ll`、`p1-fp-libcall-log.ll`、`m8-i128-f128-libcall.ll`、`m6-memintrin.ll`、`mcmodel.test`(150 of 150) 全部 `PASS:`；日志内 6 处 `FAIL` 均为 `FAIL=0` 计数/标签，无真红。
- 工程师 `.work/log/llvm/LLVM-131t-verify-summary.log`（5 行 EXIT=0）与本轮逐项一致。

**手工行为核验（reviewer 自写用例，不经测试脚本）**：
- memcpy 程序：`default`/`small` ⇒ `call [rb0, memcpy]`（直接，逐字节同形）；`large` ⇒ `set.zw rb4, wp0, memcpy` + 2×`or.w`（ABS48 三段物化）+ `call [rb4, rd0, 0]`，`grep 'call \[rb0,'`=0。
- `medium|kernel|tiny` ⇒ rc=1，文案含目标与允许值：`unsupported code model '…' … on target 'dadao-unknown-…-elf'; DADAO supports 'default' ('small' is an alias) and 'large'`。
- 远距布局（自写 far2.c + 自写 lds，两 .o 相距 **128 MiB**，`--emit-relocs`）：`large` 链接 **rc=0**（ELF 内 ABS48 重定位解析为 `0xfc0008000000` + 间接 call）；`default` **rc=1** 且 `R_DADAO_REL26 out of range: 33554415 is not in [-8388608, 8388607]`。ELF 内唯一直接 `call [rb0,` 来自 crt0 `_start→main`（默认模型启动对象，非 large 编译单元；large 单元内计数 0）。

**独立反例注入（改被测产物，cp 备份 + md5 还原）**：`tests/e2e/mcmodel_far.lds` 的 `.far` 从 `0xFC0004000000`（64 MiB）改为 `0xFC0000100000`（1 MiB）⇒ 重跑同一 `run.sh` ⇒ **rc=1，3 FAIL**（`R1 lit mcmodel.test`、`R3 default 链接 rc≠0`、`R3 REL26 grep`）；`cp` 还原后 md5 `e5c1893835817d8b01e8dbcf4bba81b3` 相等，重跑回绿 **24 PASS / 0 FAIL rc=0**。证明远距/否定断言非恒真。

**约束核验**：未改 ISA/spec/REL26 字段（diff 18 文件内无 `spec/`、`contracts/`）；`large` 真实生效（后端物化+间接 call 实测）；共享文件 `CommonArgs.cpp`/`DiagnosticDriverKinds.td` 完成区已单列理由；diff 文件集与完成区「修改文件」逐条一致，测试文件全为新建（既有 lit 期望值一个未动，F14 证实）；验收前后快照对账：`git status` 空、series/milestones md5 相等。ADR-0036 D5 的 PIC 偏离：代码注释完备（`DADAOISelLowering.cpp.patch` 明确 D5 字面 = 静态 ABS48，PIC 走 `aip.si`+`ld.o` GOT PCREL，引 ADR-0029 D4 理由）；完成区第 68 行提及 GOT 取址但未显式标注「偏离 D5」。

**非阻塞 finding（文档级，随收尾提交由 architect 改）**：① 完成区把 `check-code-range --self-test` 列入 L1，实际属 L2（已跑过、PASS）；② 完成区「测试结果」仍为重建前 23/1 快照（有「待重建转绿」标注，重建后 24/0 见 verify-summary.log，属实）；③ PIC GOT 偏离建议在完成区补一句显式声明。

**判决：Accepted**（验收命令块本人重跑全绿、手工核验独立复现、反例注入证非恒真、约束无违反）。
