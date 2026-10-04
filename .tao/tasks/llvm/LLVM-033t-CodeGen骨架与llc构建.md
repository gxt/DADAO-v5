# LLVM-033t: CodeGen 骨架（`llc` build + DataLayout + 注册 ISel/FrameLowering/AsmPrinter）+ RA/RF 保留配置

**模块**：llvm
**项目里程碑**：M3
**依赖**：`INFRA-035t`
**状态**：待开始

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
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
