# LLVM-034t: 值类型 + 寄存器类（GPRD/GPRB）+ 跨 bank 搬运

**模块**：llvm
**项目里程碑**：M3
**依赖**：`LLVM-033t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：`LLVM-033t` 的骨架（GPRD 已注册，MIR 可出）；`DADAORegisterInfo.td` 既有 `GPRD`/`GPRD_Allocatable`/`GPRB`/`GPRB_Allocatable`/`GPRF`/`GPRA` 类。
- **输出**：GPRB 接入 SelectionDAG（指针/地址走 GPRB），跨 bank 搬运可在 MIR 选择到指令；导出的补丁。
- **约束**：
  - **GPRD** = i64 数据（`rd8–rd63` 可分配）；**GPRB** = 指针/地址（`rb8–rb63` 可分配）。**C1 硬双类**（`ADR-0018（C1）`）：指针经 CC/ISel 强制落 GPRB，不依赖寄存器分配器软偏好。**C2 指针 value type = i64 通吃**（`ADR-0018（C2）`）：不引入独立 MVT，指针参数（IR `ptr`/`iPTR`）须落入 **GPRB 虚拟寄存器**（`LowerFormalArguments` 按 `ArgFlags.isPointer()`/`CCIfPtr` 等 bank 判定指派 GPRB vreg；参照 0628 `DL-050a`）。
  - **跨 bank 搬运**（`DADAOInstrInfo.cpp::copyPhysReg`）：v5 已有专用 orri 指令 `rd2rd`/`rb2rb`/`rd2rb`/`rb2rd`（见 `DADAOInstrInfo.td`）。**C3 已判**：同 bank 用专用 `rd2rd`/`rb2rb`，跨 bank 用 `rd2rb`/`rb2rd`（不采用 0628 的 `addi r,r,0`）。须 `using TargetInstrInfo::copyPhysReg;` 防重载隐藏。
  - **无 subreg（C13，`ADR-0018（C13）`）**：单一 64 位寄存器，指针/窄值均落 64 位寄存器类，不引入子寄存器。
  - **DataLayout/栈对齐**：本任务不改（C9 已判并由 `LLVM-033t` 落地 `ADR-0018（C9）` 的串）。
  - **不实现**：算术语义、load/store、branch、帧、调用（后续任务）。本任务只到「指针参数/返回指针落 GPRB、跨 bank COPY 有指令」。
  - 补丁纪律同 `LLVM-033t`（`spec/Process-01`；`make check-source-state`；`make check-patch-tree`）。
  - 构建 `ninja -j$(JOBS) -C .work/build/llvm llc`；临时目录 `/tmp/opencode/LLVM-034t/`；输出留存 `.work/log/llvm/`；**不提交 git**；**防造假**（真实 MIR + 重 build）。

## 验收标准

1. `ninja` 退出 0；`llc -stop-after=finalize-isel` 对：
   - `define ptr @pass_ptr(ptr %p){ ret ptr %p }` → MIR 含 `class: gprb` 的虚拟寄存器（参数落 GPRB）；
   - `define i64 @add_i64(i64 %a,i64 %b){ %s=add i64 %a,%b  ret i64 %s }` → MIR 仍含 `class: gprd`（GPRD 不回归）。
2. 跨 bank COPY 在 MIR 下降为真实搬运指令（非仅 virtual COPY）——给出 `llc -stop-after=finalize-isel` 或 `-stop-after=finalize-isel` 后 `-verify-machineinstrs` 的实证。
3. 不带 `llvm_unreachable`/崩溃；`llc` 退出码 0。
4. 补丁导出且 `make check-patch-tree` 通过；不回归 `make check-lit`。
5. 一键证据脚本 `.work/evidence/LLVM-034t/run.sh`（规格同 `LLVM-033t`，含反例注入）。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
