# LLVM-038t: FrameIndex 消解 + spill/reload + prologue/epilogue

**模块**：llvm
**项目里程碑**：M3
**依赖**：`LLVM-036t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：`LLVM-036t`（load/store + GPRB 地址）；v5 栈约定（`.tao/knowledge/contract-abi.md` §2 / `SPEC-097t`）。
- **输出**：标准栈帧 lowering（`eliminateFrameIndex` + `emitPrologue`/`emitEpilogue` + `determineFrameLayout`），使含局部变量/寄存器压力的函数跑过 PEI；导出的补丁。
- **约束**：
  - **约定事实**：栈**向下**增长（`ADR-0004`）；`SP = rb1`；`FP = rb2`（可选）；`call` 前 SP 8B 对齐（`contract-abi.md §2.2`）。帧布局见 `SPEC-097t` 提取的 `DADAO-21 §The Stack Frame`。
  - **`DADAORegisterInfo::eliminateFrameIndex`**（现为 `llvm_unreachable`）：把 `FrameIndex` 解成 `[rbsp, offset]`（offset = `MFI.getObjectOffset(FI)` + 帧大小调整）或 `[rbfp, offset]`（若建 FP）；必须**不**残留 FrameIndex（PEI 后）。
  - **`DADAOFrameLowering`**（现为空存根，未覆写 `hasFPImpl`/`emitPrologue`/`emitEpilogue`）：实现 `emitPrologue`（入口下调 SP 分配帧；建/不建 FP）/`emitEpilogue`（对称回收；恢复 FP）；栈调整用 `add.si`（riii，`add_si_rb` 变体，原地加立即数）；spill/reload 用 `ld.o`/`st.o`。
  - **帧策略（C7/C8，已判 → `ADR-0018（C7/C8）`）**：`hasFPImpl = DisableFramePointerElim ∨ hasVarSizedObjects ∨ isFrameAddressTaken ∨ hasStackRealignment`；**默认 SP-only（rb1）**，上述条件成立或有选项时 → **FP = rb2**；**`getFrameRegister = hasFP ? rb2 : rb1`**（**替代现行恒返回 `rb2` 的实现**，C8）。**大帧：方案2 为主**（`rb2rb` + `add.si`，≤±128K，单/多寄存器都支持），方案1（rd 存偏移 + `ldm/stm`）仅 **>128K**。**M3 现在实现**（帧布局、prologue/epilogue、大帧方案2）。
  - **`rb2` 始终 reserved（C15）**：`rb2` 保留（可能是 FP）；RA/RF 保留不分配；`rd1-7`/`rb3-7` 保留；保留方式统一为 `isAllocatable=0` + 显式 `Reserved.set`（`ADR-0018（C7/C15）` D6）。
  - **寄存器 spill/reload**：`loadRegFromStackSlot`/`storeRegToStackSlot`（或等价的 `copyPhysReg` + GPRB 地址）使寄存器压力下可溢出；`RegScavenger` 可用。
  - **范围**：FrameIndex 消解、prologue/epilogue、寄存器 spill/reload。**callee-save 集合**（`getCalleeSavedRegs`/`determineCalleeSaves`/CSR 保存恢复）属 `LLVM-039t`（调用约定），本任务只需为其预留帧结构，不做 CSR。
  - 不回归 `LLVM-034t`~`LLVM-036t`；`RBSP/RBFP` 帧寄存器用 GPRB 可识别名。
  - 补丁纪律、构建/日志/临时目录/防造假纪律同 `LLVM-033t`。
  - 参照 0628 `DL-053a`（`eliminateFrameIndex` + prologue/epilogue + `getFrameIndexReference`）；M68k `M68kFrameLowering.cpp`（`hasFPImpl`/`getFrameIndexReference`）——只读溯源。

## 验收标准

1. `ninja` 退出 0。
2. `llc -march=dadao -stop-after=prologepilog` 对含多个局部变量的函数（如两 `alloca` + load/store + add）产出 MIR：
   - prologue/epilogue 有 SP 调整（`add.si`）；
   - 栈访问解成 `[rbsp, 正确偏移]`（无残留 FrameIndex / `%stack.`，`grep -c "FrameIndex\|%stack\."` 期望 0）；
   - 多个栈槽偏移**互不冲突**（逐槽核对）；
   - **默认 SP-only** 时 `getFrameRegister` 返回 `rb1`；给出一个触发 `hasFPImpl` 条件的用例（如 `alloca` 变长对象 / 取帧地址 / 栈重对齐），此时 `getFrameRegister` 返回 `rb2`、栈访问基址为 `[rbfp, offset]`（C7/C8/`ADR-0018（C7/C8）`）。
3. 寄存器压力用例（如 20+ 活跃 i64 值）能溢出/重载，`llc -verify-machineinstrs -stop-after=prologepilog` 退出 0。
4. 不回归 `LLVM-034t`~`LLVM-036t`；补丁导出且 `make check-patch-tree` 通过；`make check-lit` 不回归。
5. 一键证据脚本 `.work/evidence/LLVM-038t/run.sh`（规格同 `LLVM-033t`；反例注入：改帧偏移常量 → 预期 FAIL）。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
