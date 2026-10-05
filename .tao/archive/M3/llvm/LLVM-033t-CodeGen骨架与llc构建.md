# LLVM-033t: CodeGen 骨架（`llc` build + DataLayout + 注册 ISel/FrameLowering/AsmPrinter）+ RA/RF 保留配置

**模块**：llvm
**项目里程碑**：M3
**依赖**：`INFRA-035t`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：`INFRA-035t` 产出的 `llc` 构建目标；v5 DADAO target 现状（`.work/source/llvm-project/llvm/lib/Target/DADAO/`）。
- **输出**：最小可跑的 SelectionDAG CodeGen 骨架，使 `llc -march=dadao -stop-after=finalize-isel` 对最小 IR 产出 MIR；导出的 LLVM 补丁集。
- **约束**：
  - **现状事实（实测，勿臆造）**：`DADAO.td` 未 include `CallingConv.td`；`DADAOInstrInfo.td` 全部 `Pattern = []`；无 `DADAOSubtarget`/`DADAOISelLowering`/`DADAOISelDAGToDAG`/`DADAOAsmPrinter`；`DADAOTargetMachine` 无 `createPassConfig`/`Subtarget`；`DADAO.h` 已声明 `createDADAOISelDagLegacyPass` 但无实现；`CMakeLists.txt` 的 `DADAOCodeGen` 仅含 4 个 cpp。
  - **必须**（最小接线）：新增 `DADAOSubtarget.{h,cpp}`（持 `DADAOInstrInfo`/`DADAORegisterInfo`/`DADAOTargetLowering`/`DADAOFrameLowering`，实现 `getSubtargetImpl`）；`DADAOISelLowering.{h,cpp}`（`addRegisterClass(MVT::i64,&GPRDRegClass)`、`computeRegisterProperties`、最小 `LowerReturn`）；`DADAOISelDAGToDAG.cpp`（LLVM 23.1.1 的 `SelectionDAGISelLegacy` + 工厂 + `INITIALIZE_PASS`；以本仓 `llvm/` 头文件为准）；`DADAOPassConfig`（`addInstSelector` → `createDADAOISelDag`）；`DADAOAsmPrinter` 存根（能注册、能跑 `-stop-after=finalize-isel` 即可，完整 `.s` 发射留 `LLVM-040t`）；`CMakeLists.txt` 接入新文件与 `-gen-subtarget`/`-gen-dag-isel`（如需要）；`DADAO.td` include 必要时新增的 `.td`。
  - **DataLayout（C9，已判 → `ADR-0018（C9）`）**：把 `llvm/lib/TargetParser/TargetDataLayout.cpp` 的 `case Triple::dadao` **确定为 `E-m:e-p:64:64-i64:64-i128:128-n8:16:32:64-S128`**（在现值基础上把 `n32:64` 改为 `n8:16:32:64`；`S128`/`i128:128` 保留、省略 `a:`、端序 `E` 有意）。完成区记录实际串与 `grep` 对照。
  - **指令选择框架（C11，已判 → `ADR-0018（C11）`）**：以 **SelectionDAG 为主**，**预留后续加 GISel 的空间**（M3 不做 GISel）；用 `SelectionDAGISelLegacy` + `createDADAOISelDag`。
  - **RA/RF 保留配置**（本任务显式范围，C7/C15 → `ADR-0018（C7/C15）` D6）：确认 `DADAORegisterInfo::getReservedRegs` 保留 `rd0`/`rb0`/`rb1`/`rb2`、全部 `rf*`、全部 `ra*`，且 `rd1-7`/`rb3-7` 保留；`GPRF`/`GPRA` 类 `isAllocatable = 0`；保留方式统一为 **`isAllocatable=0` + 显式 `Reserved.set` 双保险**；codegen 不分配 RA/RF；`call`/`ret` 依赖 RegRAS（**不**做软件 RA 保存）。若发现分配器可触及 RA/RF，修到「仅保留不分配」。
  - **补丁纪律**（`spec/Process-01`）：源码改动只在 `.work/source/llvm-project` 的 working tree 内做（`git commit` 收敛为 base+1 后由 `tools/infra/make_patch.py` 导出树形补丁到 `components/llvm-project/patches/llvm/...`）；**不得手工编辑补丁**；改动前/后各跑 `make check-source-state`。新增文件产出新补丁文件。
  - **不实现**：GPRB、算术语义、load/store、branch、帧消解、调用、完整 AsmPrinter、重定位（→ `LLVM-034t`+）。本任务只到「`ret` 最小函数出 MIR」。
  - 构建：`ninja -j$(JOBS) -C .work/build/llvm llc`；**禁止**全核并行。临时目录 `/tmp/opencode/LLVM-033t/`。
  - **不提交 git**；复杂命令输出留存 `.work/log/llvm/LLVM-033t-*.log`。
  - **防造假**：完成区贴**真实** `ninja` 尾巴与 `llc` 真实 MIR；架构师会重 build + 重跑。

## 验收标准

1. `ninja -C .work/build/llvm llc` 退出 0；`llc --version | grep -i dadao` 命中。
2. `llc -march=dadao -stop-after=finalize-isel` 对 `define void @f() { ret void }` 与 `define i64 @g(i64 %a){ ret i64 %a }` 产出 MIR（含 `%N:gprd`），退出 0。
3. `DADAORegisterInfo::getReservedRegs` 保留 RA/RF 全集；给出「RA/RF 不可分配」的证据（如对含 RA/RF 使用的 IR 编译不崩溃 / `-debug-only=regalloc` 或静态检查）。
4. 新增 CodeGen 文件已导出为**含有效 hunk**的树形补丁；`make check-patch-tree` 通过（断言①～⑨，含断言⑥ blob 一致性）。
5. 不回归：`make build-mc` 后 `make check-lit`（MC+E2E，31/31）仍绿。
6. 交付**一键证据脚本** `.work/evidence/LLVM-033t/run.sh`：非交互；任一检查失败非零退出；逐项打印检查名/期望/实际/退出码；含 `--inject` 反例注入（如把 `addRegisterClass` 去掉 → 预期编译/选择失败）与还原。

## 完成区
**测试结果**：通过 **11/11**（一键证据脚本 `.work/evidence/LLVM-033t/run.sh` 全 PASS，`EXIT=0`）；`run.sh --inject` 自检 PASS（去 `addRegisterClass` → 重建 → MIR 检查 FAIL → 还原 → 重建 → 回绿，`EXIT=0`）。`make check` `EXIT=0`；`make check-lit` 31/31；`make check-patch-tree` 77 patches OK；`make check-source-state` E1 OK。

**修改文件**：

组件源码（`.work/source/llvm-project`，收敛为 base+1，共 18 文件 = 8 新增 + 10 修改）：
- 新增：`llvm/lib/Target/DADAO/DADAOSubtarget.{h,cpp}`、`DADAOISelLowering.{h,cpp}`、`DADAOISelDAGToDAG.cpp`、`DADAOAsmPrinter.{h,cpp}`、`DADAOCodeGen.td`。
- 修改：`DADAO/CMakeLists.txt`（`-gen-dag-isel` + 新源文件 + `LINK_COMPONENTS` AsmPrinter/SelectionDAG/Target）、`DADAO.td`（include `DADAOCodeGen.td`）、`DADAO.h`（`createDADAOISelDag` + `initializeDADAODAGToDAGISelLegacyPass`/`initializeDADAOAsmPrinterPass`）、`DADAORegisterInfo.td`（`GPRD`/`GPRB` 改为可分配）、`DADAORegisterInfo.cpp`（`getReservedRegs` 补 `rd1-7`/`rb3-7`）、`DADAOTargetMachine.{h,cpp}`（`Subtarget`/`createPassConfig`/`getSubtargetImpl`/`TargetLoweringObjectFileELF`）、`DADAOFrameLowering.h`（补 3 个纯虚实现）、`DADAOInstrInfo.cpp`（`GET_INSTRINFO_MC_DESC`→`GET_INSTRINFO_CTOR_DTOR`）、`llvm/lib/TargetParser/TargetDataLayout.cpp`（DataLayout C9）。

DADAO-v5 仓库：`components/llvm-project/{changelog.md,series}` + 11 份修改补丁 + 8 份新增补丁；任务书（本文件）。

未入库（gitignored）：`.work/evidence/LLVM-033t/run.sh`；日志 `.work/log/llvm/LLVM-033t-*.log`；临时 `/tmp/opencode/LLVM-033t/`。

**验收结果**（真实命令 + 真实输出 + 退出码）：

1) 构建 `llc` + 注册 dadao：
```
$ ninja -j8 -C .work/build/llvm llc > .work/log/llvm/LLVM-033t-build-cleanup.log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=0
$ tail -3 .work/log/llvm/LLVM-033t-build-cleanup.log
[1/3] Building CXX object lib/Target/DADAO/CMakeFiles/LLVMDADAOCodeGen.dir/DADAOISelLowering.cpp.o
[2/3] Linking CXX static library lib/libLLVMDADAOCodeGen.a
[3/3] Linking CXX executable bin/llc
$ .work/build/llvm/bin/llc --version; echo "EXIT=$?"
  LLVM version 23.1.1
  Registered Targets:
    dadao - DADAO SimRISC
EXIT=0
```
（首次完整接入 CMake 的构建日志见 `LLVM-033t-build.log`；`EXIT=0`。）

2) `-stop-after=finalize-isel` 产出 MIR：
```
$ .work/build/llvm/bin/llc -march=dadao -stop-after=finalize-isel -o - /tmp/opencode/LLVM-033t/f.ll; echo "EXIT=$?"
  target datalayout = "E-m:e-p:64:64-i64:64-i128:128-n8:16:32:64-S128"
  ...
body:             |
  bb.0 (%ir-block.0):
    RET_PSEUDO
EXIT=0

$ .work/build/llvm/bin/llc -march=dadao -stop-after=finalize-isel -o - /tmp/opencode/LLVM-033t/g.ll; echo "EXIT=$?"
registers:
  - { id: 0, class: gprd, preferred-register: '', flags: [  ] }
body:             |
  bb.0 (%ir-block.0):
    %0:gprd = COPY $rd16
    $rd31 = COPY %0
    RET_PSEUDO implicit $rd31
EXIT=0
```
（`%N:gprd` 命中；DataLayout 串与 C9 一致。）

3) RA/RF 保留不可分配：`run.sh` 的 `reserved-source` + `regclass-alloc` 检查（静态 + 生成表，task 允许「静态检查」）：
```
[PASS] reserved-source | getReservedRegs reserves RA/RF full set + rd1-7/rb3-7; GPRF/GPRA non-alloc | ok | rc=0
[PASS] regclass-alloc | GPRD/GPRB allocatable; GPRF/GPRA not | ok | rc=0
```
- `DADAORegisterInfo::getReservedRegs`：`Reserved.set` rd0/rb0/rb1/rb2，循环 rd1–rd7、rb3–rb7、rf0–rf63、ra0–ra63。
- 生成表 `DADAOGenRegisterInfoMCDesc.inc`：GPRD/GPRB `Allocatable=true`，GPRF/GPRA `Allocatable=false`。
- 说明：本任务只到 finalize-isel，无 RA 阶段，`-debug-only=regalloc` 无从触发；`llvm.read_register`（拟用 RA/RF 的 IR 途径）返回 `LLVM ERROR: Named registers not implemented for this target`（显式失败，不崩溃）——故按任务「静态检查」口径取证。

4) 树形补丁 + `check-patch-tree`：
```
$ python3 tools/infra/make_patch.py llvm-project; echo "EXIT=$?"
make-patch: 1 written, 44 unchanged (skipped)
make-patch: llvm-project wrote 45 patches to .../components/llvm-project/patches
make-patch: series .../components/llvm-project/series
EXIT=0
$ make check-patch-tree; echo "EXIT=$?"
check-patch-tree: 2 component(s), 77 patches OK
EXIT=0
```
8 份新增 CodeGen 补丁均含 `new file mode` + 有效 hunk（`run.sh` 的 `patch-hunks` PASS）。

5) 不回归：`make build-mc` `EXIT=0`；`make check-lit` `Passed: 31 (100.00%)`，`EXIT=0`；`make check` `EXIT=0`。

6) 一键证据脚本：
```
$ .work/evidence/LLVM-033t/run.sh; echo "EXIT=$?"
[PASS] llc-exists ... rc=0
[PASS] llc-version ... rc=0
[PASS] mir-f ... rc=0
[PASS] mir-g ... rc=0
[PASS] datalayout ... rc=0
[PASS] reserved-source ... rc=0
[PASS] regclass-alloc ... rc=0
[PASS] patch-hunks ... rc=0
[PASS] check-patch-tree ... rc=0
[PASS] check-source-state ... rc=0
[PASS] check-lit ... rc=0
RESULT: PASS (11 checks, 0 failures)
EXIT=0

$ .work/evidence/LLVM-033t/run.sh --inject; echo "EXIT=$?"
inject: removing addRegisterClass(MVT::i64, ...) from DADAOISelLowering.cpp
inject: dirty: llvm/lib/Target/DADAO/DADAOISelLowering.cpp
inject: rebuild EXIT=0
[FAIL] mir-f | actual: rc=134, RET_PSEUDO=no | rc=1
[FAIL] mir-g | actual: rc=134, gprd=no | rc=1
inject: llc: TargetLoweringBase.cpp:1739: ... Assertion `LargestIntReg != MVT::i1 && "No integer registers defined!"' failed.
inject: restoring source and rebuilding ...
inject: rebuild EXIT=0
inject: restore sha256 unchanged (06e7149c...)
inject: PASS (injection FAILed MIR checks; restore sha256 unchanged; checks green again)
EXIT=0
```
（脚本结尾 `echo "EXIT=$rc"; exit "$rc"`，无 `tee` 吞退出码。）

**新发现/坑**：
- **`GPRD`/`GPRB` 必须可分配**：M1/M2 版把二者设为 `isAllocatable=0`（注释「MC use only」），但 `MachineRegisterInfo::createVirtualRegister` 对非可分配类 `assert`，且验收要 `%N:gprd`（`GPRD_Allocatable` 会打印成 `gprd_allocatable`）。故本任务将 `GPRD`/`GPRB` 改为可分配（0628 同此），`rd0-7`/`rb0-7` 由 `getReservedRegs` 排除。
- **`DADAOInstrInfo.cpp` 与 `DADAOMCTargetDesc.cpp` 的重复符号**：`DADAOInstrInfo.cpp` 原用 `GET_INSTRINFO_MC_DESC`，与 `DADAOMCTargetDesc.cpp` 各定义一份 `DADAODescs`/`DADAOInstrNameIndices`/`DADAOInstrNameData`；在无对象引用 `DADAOInstrInfo` 时静态库惰性链接掩盖了它，接入 Subtarget 后被拉入即链接失败。改为 `GET_INSTRINFO_CTOR_DTOR`（表由 Descs 定义、构造函数在 CodeGen）后消除。
- **`DADAOFrameLowering` 抽象**：仅设基类构造，缺 `emitPrologue`/`emitEpilogue`/`hasFPImpl` 纯虚；`DADAOSubtarget` 实例化它才暴露。补：prologue/epilogue `llvm_unreachable`（LLVM-038t），`hasFPImpl` 返回 false（C7 D2 默认 SP-only）。
- **`DADAOSubtarget` 须自声明 `ParseSubtargetFeatures`**：`-gen-subtarget` 的 `GET_SUBTARGETINFO_TARGET_DESC` 会定义 `DADAOSubtarget::ParseSubtargetFeatures`，但生成的头不声明它。
- **`DADAO.h` 既有声明名错**：`initializeDADAOISelDAGLegacyPass` 与 `INITIALIZE_PASS(DADAODAGToDAGISelLegacy,…)` 实际生成的 `initializeDADAODAGToDAGISelLegacyPass` 不符；`createDADAOISelDagLegacyPass` 无实现。按任务改为 `createDADAOISelDag` + 正确 init 名。
- **`SelectionDAGISel` 要求 target 实现 `Select(SDNode*)->SelectCode`**；generated `DADAOGenDAGISel.inc` 只提供 `SelectCode`。
- **`DADAO::RET_PSEUDO` 需 `GET_INSTRINFO_ENUM`**：`DADAOInstrInfo.h` 仅含 `GET_INSTRINFO_HEADER`（类声明），opcode 枚举需在 ISelDAGToDAG.cpp 单独引入。
- **重复 `GET_REGINFO_ENUM`**：`DADAOInstrInfo.h`（经 Subtarget.h）与 `MCTargetDesc/DADAOMCTargetDesc.h` 同 TU 各引一次 → 枚举重定义；去掉后者。
- **`llc -stop-after=<pass>` 不创建 AsmPrinter**（`willCompleteCodeGenPipeline()==false` → 加 `createPrintMIRPass`），故 `DADAOAsmPrinter` 存根本任务不被执行，仅需可注册/可编译。
- **`MCStreamer` 前置声明导致 `unique_ptr` 不完整**：AsmPrinter.h 的 inline 构造需 `#include "llvm/MC/MCStreamer.h"`。
- **`llvm.read_register` 不支持**（无法在 IR 中引用 RA/RF），RA/RF 行为证据只能走静态 + 生成表。
- **`components/llvm-project/README.md` 补丁数仍写「36 份」**（本次后实为 45）；前序任务（027t/029t/030t/031t）亦未同步。非本任务范围，未改，仅披露。

**遗留问题**：
- **指针参数/返回的 bank 落位未完成**：`LowerFormalArguments` 把指针参数按 `isPointer()` 指派到 `rb16+`，但虚拟寄存器类仍是 `GPRD`（`addRegisterClass` 仅 i64），故 MIR 出现跨 bank `COPY $rb16 -> %N:gprd`；跨 bank `copyPhysReg` 与 GPRB vreg 由 **LLVM-034t** 落地（ADR-0018 C1/C2 Consequences 已列）。本任务验收（i64/void）不受影响。
- **RA/RF「不可分配」为静态 + 生成表证据**：无 RA 阶段可跑 `-debug-only=regalloc`；`llvm.read_register` 不支持。已在 `run.sh` 以静态 + 生成表机械核验。
- 帧消解/prologue/epilogue → **LLVM-038t**；`call`/`ret` 真指令发射（`ret_riii`）与 `.s`/重定位 → **LLVM-039t/040t/041t**。
- `README.md` 补丁数陈旧（见上「新发现」），建议主会话在收尾时决定是否另立文档小任务同步。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审范围**：组件源码 18 文件（8 新增：`DADAOSubtarget.{h,cpp}`/`DADAOISelLowering.{h,cpp}`/`DADAOISelDAGToDAG.cpp`/`DADAOAsmPrinter.{h,cpp}`/`DADAOCodeGen.td`；10 修改：`CMakeLists.txt`/`DADAO.td`/`DADAO.h`/`DADAORegisterInfo.{td,cpp}`/`DADAOTargetMachine.{h,cpp}`/`DADAOFrameLowering.h`/`DADAOInstrInfo.cpp`/`TargetDataLayout.cpp`）；`.work/evidence/LLVM-033t/run.sh`；`components/llvm-project/changelog.md`。

**审查要点（逐行）**：
- 逻辑正确性：`LowerReturn` 仅处理 0/1 个 i64 返回值（>`1` 或非 i64 显式 `report_fatal_error`，不静默）；`LowerFormalArguments` 仅处理 i64 寄存器实参，>16 个/byval/sret/nest 显式失败；`getReservedRegs` 的循环边界（rd1..rd7 / rb3..rb7 / rf0..rf63 / ra0..ra63）与生成枚举连续性一致（rb16=83、rd16=147，同 bank 连续）。
- 设计/惯用法：`DADAOISD::RET_GLUE`（`SDTNone`+`SDNPHasChain/SDNPOptInGlue/SDNPVariadic`）+ `RET_PSEUDO` pattern 沿用 0628/RISCV 惯例；`DADAOSubtarget` 成员顺序与初始化列表一致；`SelectionDAGTargetInfo` 直接用基类（自定义节点名经 `DADAOTargetLowering::getTargetNodeName`）。
- 防造假：完成区所有输出均为 `cmd > log 2>&1; rc=$?` 捕获后逐条粘贴；`llc` MIR 为真实运行结果；`--inject` 真实重建、真实断言失败、真实还原。
- 边界：`@f`（void，无 vreg）与 `@g`（i64，`%0:gprd`）均 EXIT=0；DataLayout 串逐字符核对；`check-patch-tree` 断言⑥（blob 一致）间接覆盖补丁 hunk 正确性。

**findings 与处置**：

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | `DADAOFrameLowering` 为抽象类（缺 `emitPrologue`/`emitEpilogue`/`hasFPImpl`），`DADAOSubtarget` 实例化时报错 | ✅已修 | `DADAOFrameLowering.h` 补 3 个 override：prologue/epilogue `llvm_unreachable`（LLVM-038t），`hasFPImpl` 返回 false | `ninja llc` 由 `error: cannot declare field ... abstract` 转为 EXIT=0 |
| 2 | `DADAOInstrInfo.cpp` 用 `GET_INSTRINFO_MC_DESC`，与 `DADAOMCTargetDesc.cpp` 重复定义 `DADAODescs`/`DADAOInstrNameIndices`/`DADAOInstrNameData`，链接 multiple definition | ✅已修 | 改为 `GET_INSTRINFO_CTOR_DTOR`（表归 Descs，构造函数归 CodeGen） | attempt6 链接报 multiple definition → attempt7 `[3/3] Linking CXX executable bin/llc` EXIT=0 |
| 3 | `DADAO.h` 声明 `initializeDADAOISelDAGLegacyPass`，与 `INITIALIZE_PASS(DADAODAGToDAGISelLegacy,…)` 生成的 `initializeDADAODAGToDAGISelLegacyPass` 不符；`createDADAOISelDagLegacyPass` 无实现 | ✅已修 | `DADAO.h` 改声明为 `createDADAOISelDag` + `initializeDADAODAGToDAGISelLegacyPass`，`DADAOTargetMachine.cpp` 调正确名 | 编译期 `should have been declared inside 'llvm'` 消除；`llc --version` 命中 dadao |
| 4 | `DADAO::RET_PSEUDO` opcode 枚举未引入（`DADAOInstrInfo.h` 仅 `GET_INSTRINFO_HEADER`） | ✅已修 | `DADAOISelDAGToDAG.cpp` 加 `#define GET_INSTRINFO_ENUM` + include | 编译 `'RET_PSEUDO' is not a member of 'llvm::DADAO'` 消除，链接/运行通过 |
| 5 | 同 TU 重复 `GET_REGINFO_ENUM`（`DADAOInstrInfo.h` 与 `MCTargetDesc/DADAOMCTargetDesc.h`）致枚举重定义 | ✅已修 | 从 `DADAOISelLowering.cpp` 去掉 `MCTargetDesc/DADAOMCTargetDesc.h` include | 编译 redefinition 错误消除 |
| 6 | `ISD::InputArg::VT` 是 `MVT`，误调 `.getSimpleVT()` | ✅已修 | 改为 `Arg.VT != MVT::i64` | 编译通过；`mir-g` PASS |
| 7 | `DADAOSubtarget` 未声明 `ParseSubtargetFeatures`，而生成的 `GET_SUBTARGETINFO_TARGET_DESC` 定义它 | ✅已修 | `DADAOSubtarget.h` 增声明 | 编译 `no declaration matches` 消除 |
| 8 | 生成 `DADAOGenSubtargetInfo.inc`（TARGET_DESC）用到 `LLVM_DEBUG` 但 `DEBUG_TYPE` 未定义 | ✅已修 | `DADAOSubtarget.cpp` include 前 `#define DEBUG_TYPE "dadao-subtarget"` | 编译 `'DEBUG_TYPE' was not declared` 消除 |
| 9 | `DADAOAsmPrinter.h` inline 构造需完整 `MCStreamer`（`unique_ptr` sizeof） | ✅已修 | 增 `#include "llvm/MC/MCStreamer.h"` | 编译 `invalid application of 'sizeof' to incomplete type` 消除 |
| 10 | 验收要 `%N:gprd` 且 `addRegisterClass(i64,&GPRDRegClass)`，但 `GPRD` 原 `isAllocatable=0` → `createVirtualRegister` 必断言 | ✅已修 | `DADAORegisterInfo.td` 去掉 `GPRD`/`GPRB` 的 `isAllocatable=0` | `mir-g` MIR 出现 `%0:gprd`；`regclass-alloc` 检查 GPRD/GPRB=true、GPRF/GPRA=false |
| 11 | `.work/evidence/.../run.sh` 的 `--inject` 首版把「检查通过」计为失败（`&&` 逻辑反了），且提前退出未重建被注入的二进制 | ✅已修 | 改 `check_* || fail_count++`；还原后显式 `rebuild_llc` | 复跑 `--inject`：注入态 2 项 `[FAIL]`（rc=134 + `No integer registers defined!`），还原+重建后回绿，`EXIT=0`，源码 `git status` 干净 |
| 12 | `DADAOISelLowering.cpp` 含 3 个未用 include（`CallingConvLower`/`MachineFunction`/`MachineRegisterInfo`） | ✅已修 | 删除 | 重建 `[1/3]…[3/3]` EXIT=0；`run.sh` 11/11 PASS |
| 13 | `INITIALIZE_PASS` 生成的 `void llvm::initialize...` 需前置声明（`DADAOAsmPrinter.cpp`/`DADAOISelDAGToDAG.cpp` 未 include `DADAO.h`） | ✅已修 | 两文件加 `#include "DADAO.h"` | `should have been declared inside 'llvm'` 消除 |
| 14 | 指针参数被指派到 `rb16+`，但 vreg 类仍是 `GPRD`（跨 bank COPY）；指针返回同理 | ⏸延后（有依据） | 不改，补注释 | task 明示「不实现调用」「指针落 GPRB 属 LLVM-034t（ADR-0018 C1/C2）」；本任务验收仅 i64/void，不受影响。已记入「遗留问题」 |
| 15 | RA/RF「不可分配」仅有静态 + 生成表证据（无 RA 阶段、`read_register` 不支持） | ❌不修（口径允许） | 不改 | task 验收③原文：「…或**静态检查**」；`run.sh` 的 `reserved-source`/`regclass-alloc` 机械核验 |
| 16 | `components/llvm-project/README.md` 补丁数（36）陈旧（实为 45），前序任务亦未同步 | ❌不修（越界） | 不改 | 非本任务范围（README 为概览、按 Process-01 §10「不写逐补丁开发史」）；已披露，建议另立文档小任务 |
| 17 | `--inject` 注入后先落盘「注入态二进制」，若中途异常退出，工作树干净但二进制为注入态（AGENTS 教训） | ⏸延后（已由脚本兜底） | 不改 | `--inject` 在注入态验证后**必然**执行还原 + `rebuild_llc`；`trap EXIT` 至少还原源码；本次两次完整运行均 `EXIT=0` 且还原后 sha256 一致 |

**自审判决**：所有 finding 均已按上表处置，无未修项（#14/#15/#16/#17 为有依据的延后/不改，已记录）。证据脚本 11/11 PASS 且 `--inject` 具备可达 FAIL 路径与可复原性；完成区结论与真实输出逐条对齐。任务状态置 **待验收**，交 reviewer 独立验收。

#### 第 1 轮 reviewer 验收

**审查范围**：证据脚本 `.work/evidence/LLVM-033t/run.sh`；验收 1–6 逐项独立重跑；独立注入反例一次；披露越界改动复核；遗留复核。

---

##### A. 证据脚本审查

逐条核对 `run.sh`（301 行）：

| # | 断言 | FAIL 路径 | 恒真？ | 判定 |
|---|------|-----------|--------|------|
| 1 | `check_llc_exists` | 文件缺失/不可执行 → rc=1 | 否 | ✓ |
| 2 | `check_llc_version` | rc≠0 或 grep 无 match → rc=1 | 否 | ✓ |
| 3 | `check_mir_f` | rc≠0 或无 `RET_PSEUDO` → rc=1 | 否 | ✓ |
| 4 | `check_mir_g` | rc≠0 或无 `%N:gprd` → rc=1 | 否 | ✓ |
| 5 | `check_datalayout` | rc≠0 或串不匹配 → rc=1 | 否 | ✓ |
| 6 | `check_reserved_source` | Python regex 缺任一 pattern → sys.exit(1) | 否 | ✓ |
| 7 | `check_regclass_alloc` | 生成表值不匹配 → sys.exit(1) | 否 | ✓ |
| 8 | `check_patch_hunks` | 文件缺失或无 new file mode/@@ → sys.exit(1) | 否 | ✓ |
| 9–11 | `check_make` ×3 | make 退出非零 → rc≠0 | 否 | ✓ |

- **`--inject` 非空且可还原**：sed 移除 `addRegisterClass` 行 → sha256 前后比对确认改动 → `git diff --name-only` 非空 → 重建 → MIR 检查预期 FAIL → `restore_source` + `rebuild_llc` → sha256 一致 → MIR 回绿。✓
- **结尾不吞退出码**：`echo "EXIT=$rc"; exit "$rc"`，无 `tee`。✓
- **`record()` 函数**：`return "$rc"` 传递真实退出码，`check_* || fail_count++` 正确累加失败。✓

**脚本判定**：合格，可作为验收证据。

---

##### B. 重跑证据脚本（正常模式）

```
$ cd /mnt/tao/DADAO-v5 && .work/evidence/LLVM-033t/run.sh > /tmp/opencode/LLVM-033t-review/evidence-normal.log 2>&1; echo "EXIT=$?"
EXIT=0
```

逐项输出：

| 检查名 | 期望 | 实际 | 退出码 |
|--------|------|------|--------|
| llc-exists | executable exists | exists+exec | 0 |
| llc-version | rc=0 and 'dadao' registered | rc=0, match=yes | 0 |
| mir-f | rc=0, RET_PSEUDO | rc=0, RET_PSEUDO=yes | 0 |
| mir-g | rc=0, %N:gprd | rc=0, gprd=yes | 0 |
| datalayout | E-m:e-p:64:64-i64:64-i128:128-n8:16:32:64-S128 | found (rc=0) | 0 |
| reserved-source | RA/RF full set reserved; GPRF/GPRA non-alloc | ok | 0 |
| regclass-alloc | GPRD/GPRB alloc; GPRF/GPRA not | ok | 0 |
| patch-hunks | 8 new CodeGen patches valid | ok | 0 |
| check-patch-tree | make rc=0 | rc=0 | 0 |
| check-source-state | make rc=0 | rc=0 | 0 |
| check-lit | make rc=0 | rc=0 | 0 |

**结果：PASS（11 项，0 失败），EXIT=0** ✓

---

##### C. 独立验收 1–5 重跑

**验收 1**：构建 `llc` + 注册 dadao

```
$ .work/build/llvm/bin/llc --version
LLVM version 23.1.1
Registered Targets:
  dadao - DADAO SimRISC
EXIT=0
```
✓

**验收 2**：`-stop-after=finalize-isel` 产出 MIR

`f.ll`（void ret）：
```
body: |
  bb.0 (%ir-block.0):
    RET_PSEUDO
EXIT=0
```
✓

`g.ll`（i64 ret）：
```
registers:
  - { id: 0, class: gprd, preferred-register: '', flags: [  ] }
body: |
  bb.0 (%ir-block.0):
    %0:gprd = COPY $rd16
    $rd31 = COPY %0
    RET_PSEUDO implicit $rd31
EXIT=0
```
`%0:gprd` 命中 ✓

**验收 3**：RA/RF 保留不可分配

- 静态源码：`getReservedRegs` 保留 rd0/rb0/rb1/rb2 + 循环 rd1–rd7/rb3–rb7/rf0–rf63/ra0–ra63 ✓
- 生成表 `DADAOGenRegisterInfoMCDesc.inc`：GPRD=true, GPRB=true, GPRF=false, GPRA=false ✓
- `DADAORegisterInfo.td`：GPRF/GPRA 有 `isAllocatable = 0`；GPRD/GPRB 无此限制 ✓

**验收 4**：树形补丁 + `check-patch-tree`

```
$ make check-patch-tree
check-patch-tree: 2 component(s), 77 patches OK
EXIT=0
```
8 份新增 CodeGen 补丁均有 `new file mode` + 有效 hunk（每份至少 1 个 `@@`）✓

**验收 5**：不回归

```
$ make check-lit
Passed: 31 (100.00%)
EXIT=0

$ make check
EXIT=0
```
✓

---

##### D. 独立注入反例

**注入点**：`DADAOISelLowering.cpp` 的 `addRegisterClass(MVT::i64, &DADAO::GPRDRegClass)` 行。

**注入前**：
```
$ sha256sum DADAOISelLowering.cpp
06e7149c7ec4e928a8704486bdf61350e2a5c1e5ebd68dadf4a14824ebed7863
$ git -C .work/source/llvm-project diff --name-only
（空，工作区干净）
```

**注入**：
```
$ sed -i 's/^  addRegisterClass(MVT::i64, .*$/  \/\/ REVIEWER INJECT: addRegisterClass removed/' .work/source/llvm-project/llvm/lib/Target/DADAO/DADAOISelLowering.cpp
$ git -C .work/source/llvm-project diff --name-only
llvm/lib/Target/DADAO/DADAOISelLowering.cpp
```
注入有效性：`git diff --name-only` 非空 ✓

**重建**：
```
$ ninja -j8 -C .work/build/llvm llc
BUILD_EXIT=0
```

**注入态 MIR 检查（预期 FAIL）**：
```
$ llc -march=dadao -stop-after=finalize-isel f.ll
f_EXIT=134
llc: ... Assertion `LargestIntReg != MVT::i1 && "No integer registers defined!"' failed.

$ llc -march=dadao -stop-after=finalize-isel g.ll
g_EXIT=134
（同上断言失败）
```
注入态 MIR 检查 FAIL ✓（退出码 134 = SIGABRT，`No integer registers defined!`）

**还原**：
```
$ cp /tmp/opencode/LLVM-033t-review/DADAOISelLowering.cpp.reviewer-bak .work/source/llvm-project/llvm/lib/Target/DADAO/DADAOISelLowering.cpp
$ sha256sum DADAOISelLowering.cpp
06e7149c7ec4e928a8704486bdf61350e2a5c1e5ebd68dadf4a14824ebed7863
$ git -C .work/source/llvm-project diff --name-only
（空）
```
源码还原 + sha256 一致 + git 干净 ✓

**重建**：
```
$ ninja -j8 -C .work/build/llvm llc
RESTORE_BUILD_EXIT=0
```
二进制还原 ✓

**还原态 MIR 检查（预期回绿）**：
```
$ llc -march=dadao -stop-after=finalize-isel f.ll | grep RET_PSEUDO
    RET_PSEUDO
f_EXIT=0

$ llc -march=dadao -stop-after=finalize-isel g.ll | grep gprd
    %0:gprd = COPY $rd16
g_EXIT=0
```
还原后回绿 ✓

---

##### E. 越界改动复核

| 改动 | 必要性 | 判定 |
|------|--------|------|
| `DADAORegisterInfo.td`：GPRD/GPRB 去掉 `isAllocatable=0` | 必须——否则 `createVirtualRegister` 断言失败，MIR 无法产出 `%N:gprd` | **必要** ✓ |
| `DADAOFrameLowering.h`：补 3 个纯虚 override | 必须——`DADAOSubtarget` 实例化 `DADAOFrameLowering`，抽象类不可实例化 | **必要** ✓ |
| `DADAOInstrInfo.cpp`：`GET_INSTRINFO_MC_DESC`→`GET_INSTRINFO_CTOR_DTOR` | 必须——消除与 `DADAOMCTargetDesc.cpp` 的重复符号链接错误 | **必要** ✓ |
| `components/llvm-project/changelog.md` | 正常文档更新 | **可接受** ✓ |

---

##### F. 遗留复核

- **`README.md` 补丁数 36→45 陈旧**：`components/llvm-project/README.md` 第 9 行仍写「36 份」，实际 45 份。非本任务范围（engineer 已披露），非阻塞文档问题。建议主会话收尾时决定是否另立文档小任务。

---

##### 判决

**Accepted**。

- 验收 1–5 全部在我独立重跑下通过，退出码与 engineer 完成区一致。
- 证据脚本 11/11 PASS，`--inject` 具备可达 FAIL 路径与可复原性。
- 独立注入一次反例（移除 `addRegisterClass`）：注入态 2 项 FAIL（rc=134, `No integer registers defined!`）→ 还原+重建 → 回绿，`git diff --name-only`/sha256 核实。
- 4 项越界改动均为必要且不破坏既有行为。
- `README.md` 补丁数陈旧为非阻塞文档问题，已披露。
