# LLVM-004t: Register TableGen

**模块**：llvm
**项目里程碑**：M1
**依赖**：`LLVM-003t`、`SPEC-006t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：`LLVM-003t` 的 target 骨架、`.tao/knowledge/contract-isa.md` §1（寄存器模型）、`.tao/knowledge/contract-abi.md`（SPEC-006t，可分配集合/保留寄存器/SP/FP 角色）
- 输出：`components/llvm/patches/0003-dadao-register-info.patch`、更新后的 `components/llvm/patches/series`
- 约束：4 bank × 64 = 256 个 RegisterDef；只定义寄存器，不写指令；RF/RA 全部 non-allocatable（M1 范围外）；可分配集合精确取自 `contract-abi.md`，不自行扩展/缩减；合约引用用章节号

## 背景（完整）

### 目标

在骨架上用 LLVM TableGen 定义 DADAO 全部寄存器 bank（RD/RB/RF/RA），设置可分配集合与保留寄存器约束，使 `make build-mc` 仍 PASS，并为 `LLVM-005t`（指令格式 TableGen）提供完整寄存器类型。

### 设计理由

- 寄存器模型是 MC/CodeGen 的共同基础；M1 只定义、不接入寄存器分配（CodeGen 属 M2）。
- 以 Lanai 最简 register `.td` 风格为参考；多 bank 参考 RISCV。

### 关键概念 / 数据

**寄存器组**（`contract-isa.md` §1.1）：RD `rd0–rd63`、RB `rb0–rb63`、RF `rf0–rf63`、RA `ra0–ra63`，每组 64 个、每寄存器 64 位。

**RD bank（64）**：`rd0` 硬连接零、immutable；其余保留/可分配集合按 `contract-abi.md`。注册 `GPRD`（全部 64，MC 用途）与 `GPRD_Allocatable`（可分配子集，CodeGen 用；M1 只定义不连接 isel）。

**RB bank（64）**：`rb0` 为 PC（只读，`[63:48]=0`）；`rb1` SP、`rb2` FP、`rb3` GP、`rb4` TP 等角色按 `contract-abi.md`；注册 `GPRB` 与 `GPRB_Allocatable`。

**RF bank（64）**：`rf0` 为 FCSR（`contract-isa.md` §1.3.3）；M1 范围不含浮点，全部 non-allocatable，注册 `GPRF`。

**RA bank（64）**：`ra0` 为 MemRAS 引用计数/指针，`ra1–ra63` 为 RegRAS（`contract-isa.md` §1.3.4）；全部 non-allocatable，注册 `GPRA`。

**别名**：`RBSP = rb1`、`RBFP = rb2`（按 `contract-abi.md` 的 SP/FP 约定）。

**实现文件**：`DADAORegisterInfo.td`、`DADAORegisterInfo.{h,cpp}`（继承 TableGen 生成的 `DADAOGenRegisterInfo`，实现 `getCalleeSavedRegs`/`getReservedRegs`/`eliminateFrameIndex` 存根、`getFrameRegister`）、顶层 `DADAO.td`、`CMakeLists.txt`（`tablegen(... -gen-register-info)` + 源文件）、`DADAOMCTargetDesc.cpp`/`DADAOTargetMachine.cpp` 注册 `createDADAORegisterInfo`。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-008a-llvm-reginfo.md`（完整转述：目标、RD/RB/RF/RA bank 表、文件清单、约束、验收、Architecture Review）。
- DADAO-0628：`components/llvm/patches/0003-dadao-register-info.patch`（**仅参考命名与顺序**，不复制正文）。
- DADAO-0628：`contracts/isa/spec.md §1`、`contracts/abi/spec.md §1`（0.4.1，仅作结构参考）。

## 交付物

- `components/llvm/patches/0003-dadao-register-info.patch`：包含 `DADAORegisterInfo.td`、`DADAORegisterInfo.{h,cpp}`、`DADAO.td`、`CMakeLists.txt`、注册代码。
- `components/llvm/patches/series`：追加 `0003-dadao-register-info.patch`。
- 生成的 `DADAOGenRegisterInfo*.inc`（构建产物，不入 git）。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

- **可分配集合来源**：v5 以 `.tao/knowledge/contract-abi.md`（SPEC-006t）为准，不照抄 0628 的 rd8–rd63 / rb8–rb63 表；若 v5 ABI 集合不同，以合约为准。
- **保留寄存器**：`rd0` 只读零、`rb0` 为 PC、`rf0` 为 FCSR、`ra0` 为 RAS 计数，均来自 0.5.3 `contract-isa.md §1.3`，与 0.4.1 表述可能有别。
- **RF/RA 处理**：M1 不含浮点，RF 全部 non-allocatable；RA 由 call/ret 隐式管理，全部 non-allocatable。是否定义 RF/RA 全部 64 个 def 按 256 def 约束执行。
- **补丁命名**：沿用 `0003-dadao-register-info.patch`（series 顺序 0001→0002→0003），但内容按 0.5.3 重新生成。
- **不复制 0.4.1 补丁正文/编码数据**。

## 已知坑 / 结论

- `make build-mc` 必须仍然 PASS：patch apply → cmake → ninja 无错。
- 4 bank × 64 = 256 个 RegisterDef，不多不少。
- 只定义寄存器，不引入 `DADAOInstrInfo.td`（属 `LLVM-005t`）。
- RF/RA 全部 `isAllocatable = 0`，注释说明 M1 范围 defer 原因。
- patch 03 紧接 patch 02 apply，确保 `.work/source/llvm` 上 01+02 已应用。
- 引用合约用章节号（§1 等），不引用行号。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-008a-llvm-reginfo.md`
- DADAO-0628：`.work/DADAO-0628/components/llvm/patches/series`
- DADAO-0628：`.work/DADAO-0628/code-agent/designs/0002-detailed-roadmap.md`
- 知识库：`.tao/knowledge/MEMORY.md`
- 本项目：`.tao/knowledge/contract-isa.md`（§1）、`.tao/knowledge/contract-abi.md`（SPEC-006t 产出后）

## 验收标准

1. `components/llvm/patches/0003-dadao-register-info.patch` 存在并追加到 `series`
2. `make build-mc` PASS（无新增错误/警告）
3. 构建产物含 `DADAOGenRegisterInfo*.inc`（含 enums/header/MCDesc）
4. 256 个 RegisterDef；`GPRD`/`GPRD_Allocatable`/`GPRB`/`GPRB_Allocatable`/`GPRF`/`GPRA` 类均生成
5. `rd0` immutable、`rb0` 保留、RF/RA non-allocatable；可分配集合与 `contract-abi.md` 一致
6. 未引入任何指令 `.td`

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
