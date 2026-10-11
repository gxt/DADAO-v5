# LLVM-082t: M7 后端欠账收口（`llvm-mc` 数据指导符唯一集 + 尾调用 relocation/栈实参）

**模块**：llvm
**项目里程碑**：M7
**依赖**：无（同改 `components/llvm-project/patches` ⇒ 与 `LLVM-079t`/`080t`/`081t` **串行**）
**状态**：待开始

> 立项来源：`INTEG-036t §收口核对`（从 `milestones.md §M6 遗留（→M7）` **未覆盖项** 收口为本任务；「小事归批」——`ISS-189` 与 `LLVM-074t` 遗留同属「M7 **非 FP** 后端欠账」，合并为一个任务）。

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `ISS-189`（M6→M7；`milestones.md §M6 遗留`）：其它 LLVM 内建**数据指导符**（`.2byte` / `.4byte` / `.8byte` / `.value` / `.int` / `.dc.b` / `.single` / `.double` 等）**仍被 `llvm-mc` 受理**——裁定口径外的剩余面；**M7 按 `spec/Toolchain-01 §7`（指导符「唯一集合」）口径收口**。
  - `LLVM-074t` 遗留（M6→M7）：`tailjmp` **不参与 `BranchRelaxation`** ⇒ 远距离尾调用由 `lld` 报 **relocation overflow**（**非静默**）；**栈实参 / 变参尾调用未优化**（可选增强）。
  - 真源与口径：`spec/Toolchain-01 §7`（`§7.1` 数据指示符唯一集合 / `§7.2` 对齐指示符）；`.tao/knowledge/contract-asm.md §7.1/§7.2`（现口径：`llc` / `llvm-mc` MUST **只**受理 `.dd.*` 集、GAS 指示符 MUST NOT 被受理）；`ADR-0019`（reloc 口径，`D8` 禁 `ABS32`）。
  - 出处指针：`.tao/archive/M6/llvm/LLVM-078t-*.md`「遗留问题」、`.tao/archive/M6/llvm/LLVM-074t-*.md`。
- **输出**：
  1. **数据指导符唯一集收口**：`llvm-mc`（MC 层，含 AsmParser）**拒绝** `Toolchain-01 §7.1` 唯一集之外的数据指导符；**以 `spec/Toolchain-01 §7.1` 唯一集为真源**、逐条列出「应受理 / 应拒绝」（**禁手工挑拣**）。范围 `components/llvm-project/patches/llvm/lib/Target/DADAO/**`。
  2. **尾调用 relocation / 栈实参**：`tailjmp` 纳入 `BranchRelaxation`（消除远距离尾调用的 `lld` relocation overflow，**当前非静默**）；栈实参 / 变参尾调用（**可选增强**，不做须**显式登记理由**）。
  3. lit / `llvm-mc` 用例（期望值**独立派生自 `spec`**，禁从 `llc` 反填）；重建工具链（`setsid` 脱离 + `JOBS=8` + **申报耗时**；`lessons §8.21`）。
- **约束**：
  - **真源 = `spec/Toolchain-01 §7`**（不从实现反推，Spec-first）；**不改上游只读册**。
  - 计数不写死；只动任务范围，越界须披露。
  - **可选增强（栈实参尾调用）**若不做，**显式登记**（不得静默跳过）。

## 验收标准

1. **唯一集收口**：`llvm-mc` 对 `Toolchain-01 §7.1` 唯一集**全部受理**、对口径外数据指导符**全部拒绝**（真实输出；**非抽样**，逐条比对）。
2. **尾调用**：远距离尾调用不再由 `lld` 报 relocation overflow（真实 E2E 输出 + 退出码）；栈实参尾调用若不做，**显式登记**。
3. **注入反例可失败**：收口断言可被注入反例致 FAIL（保留「注入 ⇒ FAIL ⇒ 还原 ⇒ 回绿」真实输出）。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立重跑记录、约束核验、判决）
