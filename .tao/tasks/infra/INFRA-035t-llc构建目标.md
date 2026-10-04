# INFRA-035t: 将 `llc` 纳入 LLVM 构建目标

**模块**：infra
**项目里程碑**：M3
**依赖**：无
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：`Makefile` 现有 LLVM 构建设施；`.work/source/llvm-project`（已 `make prepare`，DADAO target 已注册）。
- **输出**：`make build-mc`（或新增 `build-llc`）产出 `llc` 可执行文件。
- **约束**：
  - 现状事实（实测）：`Makefile:LLVM_MC_FULL_TARGETS = llvm-mc llvm-objdump llvm-objcopy llvm-readobj FileCheck not LLVMDADAOCodeGen`；`build-mc` 已编译 `LLVMDADAOCodeGen` 但**不产出 `llc`**（`.work/build/llvm/bin/llc` 不存在）。
  - 改动最小：在 `LLVM_MC_FULL_TARGETS` 追加 `llc`（`llc` 依赖 `LLVMDADAOCodeGen`，已在内）。若不希望改 `build-mc` 语义，则新增独立 `build-llc` 目标，但需 `manifest-check` + `component-enabled` 前置，与 `build-mc` 同风格（**禁止伪造成功**）。
  - 并行度受 `JOBS`（默认 8）限制，**禁止** `-j$(nproc)`。
  - **框架依据（C11，已判 → `ADR-0018（C11）`）**：M3 CodeGen 以 **SelectionDAG 为主**（预留后续加 GISel 的空间，M3 不做 GISel）；本任务只需产 `llc` + `LLVMDADAOCodeGen`，无需额外框架目标。
  - 不改组件源码；不改 `components/**` 补丁集。

## 验收标准

1. `make build-mc`（或 `make build-llc`）成功，且 `.work/build/llvm/bin/llc` 存在、`llc --version` 含 `dadao`。
2. `make build-mc` 原行为不回归（`llvm-mc`/`llvm-objdump`/`llvm-objcopy`/`llvm-readobj`/`FileCheck`/`not` 仍产出）。
3. `make check-no-residue` 干净；`git status --untracked-files=all` 仅含本任务应有改动。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
