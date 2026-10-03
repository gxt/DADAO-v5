# LLVM-027t: ret rd0 静态检查 — 汇编期报错

**模块**：llvm
**项目里程碑**：M1→M2
**依赖**：`LLVM-026t`、`SPEC-083t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `components/llvm-project/patches/.../DADAOAsmParser.cpp.patch`（**由 LLVM-026t 完成后提供基线，本任务在其之上叠加**）
  - `contracts/opcodes.yaml`（`ret_riii_ra` 条目，SPEC-083t 完成后含 legality）
  - `contracts/legality_rules.yaml`（SPEC-083t 完成后含新增规则）
  - 已有 lit 测试模式（参考 `tests/lit/` 下现有 `.s` 文件格式）

- **输出**：
  1. `components/llvm-project/patches/.../DADAOAsmParser.cpp.patch`：在 `parseInstruction` 或 matchAndEmitInstruction 阶段对 `ret` 指令做静态检查：当 `rdha == rd0`（寄存器编号 0）且 `imms18 != 0` 时，报**硬错误**（`Error` 级：汇编失败、非零退出码；**不得**降为 warning）
  2. 新增 lit 测试文件（建议 `tests/lit/MC/Dadao/ret-rd0-legality.s`）：
     - **正例**：`ret rd0, 0` 必须成功汇编（`# CHECK-NOT: error`）
     - **反例**：`ret rd0, 1` 必须报错（`# CHECK: error:`）
     - **边界**：`ret rd0, -1` 必须报错
     - **非 rd0 正例**：`ret rd1, 0` 和 `ret rd1, 42` 均成功（无此约束）
  3. 补丁按"工作树改 → `git diff` 导出"，遵循树形补丁集规范（`spec/Process-01-组件补丁组织与构建编排.md`）

- **约束**：
  - **LLVM-026t 硬约束**：`DADAOAsmParser.cpp.patch` 正被后台的 LLVM-026t 修改。**本任务不得读取或依赖该补丁的当前内容**。任务书写作"在 LLVM-026t 完成后、于其成果之上叠加该检查"，执行时须核对 LLVM-026t 的合并点（查看其完成区确定改了哪些行/函数）
  - 需**增量重建 llvm-mc**（`JOBS=8`，预计 10–20 分钟），一次只跑一个长构建
  - 不提交 git
  - 全程中文

## 验收标准

1. **正例通过**：`ret rd0, 0` 在 llvm-mc 下成功汇编，无 error/warning。
2. **反例失败**：`ret rd0, 1` 在 llvm-mc 下报错，退出码非零，错误信息包含相关提示。
3. **反例失败**：`ret rd0, -1` 在 llvm-mc 下报错。
4. **非 rd0 不受影响**：`ret rd1, 0` 和 `ret rd1, 42` 均成功汇编。
5. **lit 测试**：`llvm-lit tests/lit/MC/Dadao/ret-rd0-legality.s` 全部 PASS。
6. **回归**：已有 lit 测试不受影响（`llvm-lit tests/lit/MC/` 全绿）。
7. **反例门控**：将检查逻辑临时注释掉后，反例用例应 PASS（证明检查逻辑确实生效）。
8. **补丁规范**：补丁文件符合树形补丁集规范，`make check-patch-tree` 通过。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（待填写）

#### 第 1 轮 reviewer 验收
（待填写）