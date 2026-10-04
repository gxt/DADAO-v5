# LLVM-039t: 调用约定（FormalArgs/Return/callee-save）+ call/ret

**模块**：llvm
**项目里程碑**：M3
**依赖**：`SPEC-097t`、`LLVM-038t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：`SPEC-097t` 的标量调用约定合约（`contract-abi.md` §4 正文 + `contracts/abi.yaml`）；`LLVM-038t` 的栈帧；v5 指令定义。
- **输出**：`DADAOCallingConv.td`（新建）+ `LowerFormalArguments`/`LowerCall`/`LowerCallResult`/`LowerReturn`/`LowerReturn` 的调用约定实现 + `getCalleeSavedRegs`/`getCallPreservedMask` + call/ret 指令属性；导出的补丁。
- **约束**：
  - **期望值来源 = `SPEC-097t` 合约**（`contract-abi.md §4`），**不得**从 `.cache/refs/DADAO-0628/contracts/abi/spec.md` 反推（该文件是 0.4.1/参考口径，仅只读对照）。
  - **参数（C4/C2）**：整型/标量 → `rd16–rd31`（独立计数）；指针/地址 → `rb16–rb31`（独立计数；用 `ArgFlags.isPointer()`/`CCIfPtr` 判定 bank，C2/`ADR-0018（C2）`）；`<8B` 标量按符号性由 **caller 扩展**到 8B（C4 `ADR-0018（C4）` D2）；寄存器耗尽按**统一栈溢出区**规则（**全局声明序单栈区**，C4 `ADR-0018（C4）` D1；调用者布置、被调用者读）。返回：标量 → `rd31`、指针 → `rb31`。
  - **callee-saved（C6）**：`CSR = rd32–63 ∪ rb32–63`；**SP(rb1) ∉ CSR**（对称回收；`call`/`ret` 靠 RegRAS，不入通用 CSR）；`getCalleeSavedRegs` 返回对应列表；`determineCalleeSaves` + prologue/epilogue 存/取（`ld.o`/`st.o`）。
  - **caller-saved / `getCallPreservedMask`（C16，`ADR-0018（C16）`）**：`rd8–rd31`、`rb8–rb31` 为 caller-saved；**必须**实现 `DADAORegisterInfo::getCallPreservedMask`（现无）——**含 rb32–63**（否则 GPRB callee-saved 被误 clobber）——并在 `LowerCall` 把它**附到 call 指令的 RegMask 操作数**（`ML-004c` 教训：否则「调用前算好 GPRB 地址 → 调用 → 调用后继续用」会静默用陈旧值）；`storeRegToStackSlot`/`loadRegFromStackSlot` **按 bank 路由**（GPRB → RB-bank）。
  - **call/ret（C16，`ADR-0018（C16）`）**：`call imms24`（iiii）/`ret`（riii，`ret rdha, imm18`）；返回地址由 `call` 压 RegRAS、`ret` 弹（**无 link register、无内存返回地址槽**）。`call_iiii`/`call_rrii` 须加 `isCall = 1`、`Defs = [rd31, rb31]`（`DL-070a` 教训：缺 `rb31` 会在 `-O1+` MachineVerifier 报 undefined physical register）；`ret` 视为 terminator/barrier，**不加 `Defs`**（返回值定义在更早的 `CopyToReg`+glue 链）。**间接调用**（`call rba, rdb, imm12`）→ M4，本任务不实现。
  - **返回值扩展（C5，`ADR-0018（C5）`）**：指针返回**直接 `rb31`**；窄返回由 **callee 扩展（canonical）、caller 不截断**，在 `ret` 前按 `SPEC-097t` 的 M3 口径扩展（v5 合约 §6 `[OPEN] #2` 已由本决策固化）。
  - **范围**：直接调用、返回、callee-save、栈参数。**不含**：变参、聚合、sret、多返回值、间接调用（→M4）。
  - 不回归 `LLVM-033t`~`LLVM-038t`。
  - 补丁纪律、构建/日志/临时目录/防造假纪律同 `LLVM-033t`。
  - 参照 0628 `DL-055a`（LowerCall）/`DL-069a`（RB 指针 CC）/`DL-070a`（call Defs）/`ML-004c`（RegMask）；M68k `M68kCallingConv.{td,h}`（`CC_M68k_Any_AssignToReg` 指针优先）——只读溯源。

## 验收标准

1. `ninja` 退出 0。
2. `llc -march=dadao -stop-after=finalize-isel` 真实 MIR：
   - 参数就位：`define i64 @f(i64 %a, ptr %p){ ... }` → `%a` 落 `rd16`、`%p` 落 `rb16`（独立计数，**不**串号）；
   - 指针返回：`define ptr @g(ptr %p){ ret ptr %p }` → 返回值走 `rb31`；
   - `call`：`define i64 @caller(i64 %x){ %r=call i64 @callee(i64 %x, i64 5)  ret i64 %r }` → 含 `call` MI，参数 `rd16`/`rd17`，返回值取自 `rd31`，且含 call RegMask（clobber caller-saved GPRD/GPRB）。
3. callee-save：被调用函数若使用 `rd32+`/`rb32+`，prologue 保存、epilogue 恢复（给出 `-stop-after=prologepilog` MIR）。
4. `llc -verify-machineinstrs`（`-O1`/`-O2` 打开 liveness）对「返回指针并通过 call 使用」的 IR 退出 0（复现 `DL-070a` 场景，确认无 undefined physical register）。
5. 不回归 `LLVM-033t`~`LLVM-038t`；补丁导出且 `make check-patch-tree` 通过；`make check-lit` 不回归。
6. 一键证据脚本 `.work/evidence/LLVM-039t/run.sh`（规格同 `LLVM-033t`；反例注入：从 `Defs` 去掉 `rb31` 或去掉 RegMask → 预期 verifier/语义 FAIL，再还原）。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
