# INFRA-043t: LLD 入构建目标

**模块**：infra
**项目里程碑**：M4
**依赖**：无
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：`Makefile` 现有 LLVM 构建设施；`.work/source/llvm-project`（已 `make prepare`，含 `lld/` 源码树，`lld/ELF/Arch/` 已有 RISCV/PPC64/SystemZ 等 target）。
- **输出**：`Makefile` 新增构建入口，产出 **`ld.lld`**（`.work/build/llvm/bin/ld.lld`）+ 构建证据。
- **约束**：
  - **现状事实（实测）**：`Makefile` 的 `build-mc`/`build-mc-reconfig` 用 `cmake -DLLVM_ENABLE_PROJECTS=""`（**不含 `lld`**）配置 `.work/build/llvm`；`build-mc` 在 `build.ninja` 已存在时**跳过 cmake**（增量快路径）。因此启用 `lld` **必须**改 `LLVM_ENABLE_PROJECTS`（含 `lld`）并重跑 cmake。
  - **改动最小**：优先新增独立目标 `build-lld`（与 `build-mc` 同风格：`manifest-check` + `component-enabled,llvm-project` 前置；`-DLLVM_TARGETS_TO_BUILD=DADAO -DLLVM_ENABLE_PROJECTS=lld`；`ninja ld.lld`）；**不得**擅自改变 `build-mc` 的既有语义/产物，以免 M3 `test-codegen` 回归。若实现选择扩展 `build-mc`，须说明并保证不回归。
  - 由于 `build.ninja` 的 `LLVM_ENABLE_PROJECTS` 不同，**须评估**是否需要独立构建目录或强制 reconfig；若复用同一 `.work/build/llvm`，须在任务书/完成区说明对 `build-mc` 增量路径的影响并验证不回归。
  - 并行度受 `JOBS`（默认 8）限制，**禁止** `-j$(nproc)`；LLD 构建预计 **5–20 分钟**（`lld` + 其 `LLVM` 依赖；具体以实测为准）——**开始前在回复写明预计耗时**。
  - **不伪造成功**：目标须真实构建 `ld.lld`；失败即停、不自动重试。
  - 不改组件源码、不改 `components/**` 补丁集（LLD target 代码由 `LLVM-056t` 负责）。
  - 临时目录 `/tmp/opencode/INFRA-043t/`；**不提交 git**。

## 验收标准

1. 新目标（如 `make build-lld`）EXIT=0；`.work/build/llvm/bin/ld.lld` 存在、可执行，且 `ld.lld --version` EXIT=0（输出含 `LLD`）。
2. `make build-mc` 原行为**不回归**（`llvm-mc`/`llvm-objdump`/`llvm-objcopy`/`llvm-readobj`/`FileCheck`/`not`/`llc` 仍产出或报告 `no work to do`）。
3. `make check-no-residue` EXIT=0；`git status --untracked-files=all` 仅 `Makefile` + 本任务书。
4. 一键证据脚本 `.work/evidence/INFRA-043t/run.sh`：非交互；任一失败非零退出；逐项打印「检查名/期望/实际/rc」；内置注入自检（临时隐藏/改名 `ld.lld` → 检查 FAIL → 还原 → 回绿；结尾**不得**用 `tee` 吞退出码）；完成区贴真实输出。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决）
