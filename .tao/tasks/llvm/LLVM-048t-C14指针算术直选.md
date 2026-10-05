# LLVM-048t: C14 指针算术直选（base+offset → GPRB 单条 `add.o`）

**模块**：llvm
**项目里程碑**：M3
**依赖**：`LLVM-036t`（访存/地址）、`LLVM-038t`（栈帧）、`LLVM-035t`（ISelDAGToDAG 结构）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：`ISS-137`（`LLVM-036t` 披露：C14 D1 指针算术未直接落 GPRB）；`tests/codegen/ptr_add_offset.ll`（`TESTCASES-026t`，实测走 `rb2rd`/`rd2rb`）；`ADR-0018（C14）` D1；v5 指令定义。
- **输出**：指针（GPRB）算术 `base + offset` 直接选 **`add.o`（orrr，`rb` 目的 = `add.o_orrr_bbd`，RB+RB→RB）**，而非「搬到 GPRD 做算术再搬回 GPRB」；导出的补丁。
- **约束**：
  - **语义事实**：`add.o_orrr_bbd`（op 0x30；`adr-0012 D9` 改名/改槽）为 RB 目的、RB+RB→RB 的 64 位加。指针 bank = GPRB（C1/C2）。
  - **目标**：`getelementptr` / 地址计算中的 **指针 + 偏移**（偏移亦为 GPRB 值）在 `SelectionDAG` 选择阶段落到 `add.o_orrr_bbd`；**不得**再用 `rb2rd`×N + GPRD `add` + `rd2rb` 兜底。
  - **bank 归属判定**：沿用 `LLVM-035t`/`037t` 的 `isPointerBankValue`（GPRB vreg / `CopyFromReg`）思路，判「两操作数是否均指针 bank」；是 → 选 `add.o_orrr_bbd`；否 → 维持 GPRD 算术。
  - **范围**：**仅** `ptr(基址) + 偏移`（GPRB+GPRB→GPRB）。**不含**：`ptr−ptr`（已由 `sub.o_orrr_dbb` 覆盖，`SPEC-100t`）、小偏移已由访存 `[rb, imm12]`（`LLVM-036t`）直接承担的路径、指针×常数（→M4 若需要）。不改 `contracts/**`。
  - 不回归 `LLVM-033t`~`LLVM-041t` 的 MIR；不回归 `make check-lit`；不改 `tests/codegen/**` 的期望值语义（若 `ptr_add_offset.ll` 的 MIR 覆盖点更新，须保持 independent oracle 与覆盖声明一致，作为本任务的**验证受益方**记录）。
  - 补丁纪律、构建/日志/临时目录/防造假纪律同 `LLVM-033t`。
  - 参照 0628 指针算术 bank 处理（只读溯源，非执行依赖）。

## 验收标准

1. `ninja -C .work/build/llvm llc` 退出 0。
2. `llc -march=dadao -stop-after=finalize-isel` 对 `tests/codegen/ptr_add_offset.ll`（或等价最小 IR）：
   - 含 `add.o`（orrr，**`rb` 目的**、两操作数 **GPRB**）；
   - **无** `rb2rd`/`rd2rb` 兜底搬运（`grep -c` 核对）；
   - 反例：把偏移改成非指针（GPRD）值 → **不选** `add.o`（退回 GPRD 算术），证明 bank 判定可达 FAIL。
3. `llc -verify-machineinstrs`（`-O0`~`-O2`）EXIT=0。
4. **语义正确**：给至少一组「base + 非零偏移」样本，独立核对最终结果（host/Python 手算，不取自 `llc`/QEMU）；本任务只保证选择正确，端到端结果由 `INTEG-012t` 承接。
5. 不回归 `LLVM-033t`~`LLVM-041t`；补丁导出 + `make check-patch-tree` 通过；`make check-lit` 不回归。
6. 一键证据 `.work/evidence/LLVM-048t/run.sh`（规格同 `LLVM-033t`；反例注入：去掉 `add.o` 的 bank 选择条件/改 bank 判定 → MIR 检查 FAIL，再还原）。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
