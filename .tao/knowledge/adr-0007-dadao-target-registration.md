# ADR-0007: DADAO target 的 CMake 注册通道

**状态**：Candidate
**日期**：2026-09-17
**关联**：`LLVM-003t`、`LLVM-002t`、`ADR-0001`、`ADR-0002`

## Context（背景）

DADAO 是 v5 自建 target（`ADR-0001` greenfield），由 `LLVM-003t`（Triple 注册 + 最小 target 骨架）首次加入 LLVM 源码树。`LLVM-002t` 已建立 `build-mc` 配方，使用 `-DLLVM_TARGETS_TO_BUILD=DADAO`。

LLVM 23.1.1 的 `llvm/CMakeLists.txt` 对 `LLVM_TARGETS_TO_BUILD` 条目有硬校验：每个条目必须存在于 `LLVM_ALL_TARGETS`（core-tier 列表）或 `LLVM_ALL_EXPERIMENTAL_TARGETS`（experimental 列表），否则 cmake 报 `FATAL_ERROR` 并退出。当前 `LLVM_ALL_TARGETS` 仅含上游 core-tier targets（AArch64/AMDGPU/ARM/AVR/BPF/Hexagon/Lanai/LoongArch/Mips/MSP430/NVPTX/PowerPC/RISCV/Sparc/SPIRV/SystemZ/VE/WebAssembly/X86/XCore），DADAO 不在其中。

`LLVM-002t` 实测确认：`cmake -DLLVM_TARGETS_TO_BUILD=DADAO` → `CMake Error at CMakeLists.txt:1175`（exit 1），属于预期失败（target 未注册）。`-DLLVM_TARGETS_TO_BUILD=X86` → configure 成功（exit 0），证明 checkout 与宿主工具链可用。

需要确定 DADAO 注册到 LLVM 构建系统的通道，并将决策固化。

## Decision（决策）

**D1**：DADAO target 通过**把 `DADAO` 加入上游 `llvm/CMakeLists.txt` 的 `LLVM_ALL_TARGETS` 列表**来注册，使 `build-mc` 现有的 `-DLLVM_TARGETS_TO_BUILD=DADAO` 生效。

**否决**改用 `LLVM_EXPERIMENTAL_TARGETS_TO_BUILD` 通道。

## Rationale（理由）

### 选择 `LLVM_ALL_TARGETS` 的理由

1. **语义正确**：DADAO 是 v5 自建 target（`ADR-0001`），不属于上游 experimental 范畴。`LLVM_ALL_EXPERIMENTAL_TARGETS` 的语义是「上游认可的实验性 target」（如 ARC/CSKY/DirectX/M68k/Xtensa），将 DADAO 放入该列表语义不匹配。
2. **与 `build-mc` 配方一致**：`LLVM-002t` 建立的 `build-mc` 使用 `-DLLVM_TARGETS_TO_BUILD=DADAO`（core-tier 通道），无需修改 Makefile 配方。
3. **实现简单**：只需在 `LLVM_ALL_TARGETS` 列表中增加一个条目 `DADAO`，改动最小。

### 被否决方案：`LLVM_EXPERIMENTAL_TARGETS_TO_BUILD` 通道

否决理由：

1. **语义不匹配**：`LLVM_ALL_EXPERIMENTAL_TARGETS` 是上游认可的 experimental targets，DADAO 不属于此列。
2. **默认行为导致构建量爆炸**：使用 experimental 通道时，若未显式设置 `-DLLVM_TARGETS_TO_BUILD=""`（空字符串），cmake 默认构建全部 core-tier targets（约 20 个），构建量从单 target 激增到全量，耗时和磁盘空间不可接受。
3. **需改 `build-mc` 配方**：必须将 `-DLLVM_TARGETS_TO_BUILD=DADAO` 改为 `-DLLVM_EXPERIMENTAL_TARGETS_TO_BUILD=DADAO -DLLVM_TARGETS_TO_BUILD=""`，增加复杂度且与既有配方不一致。

## Consequences（影响）

1. **`LLVM-003t` 的补丁必须包含 `llvm/CMakeLists.txt` 的 `LLVM_ALL_TARGETS` 增项**（加入 `DADAO`），否则 `build-mc` 的 cmake configure 必然失败（`FATAL_ERROR`）。这是 `LLVM-003t` 交付物的必要组成部分。
2. **在 `LLVM-003t` 完成前，`LLVM-002t`/`LLVM-003t` 的 DADAO configure 属预期失败**——target 尚未注册，cmake 校验必然拦截。`LLVM-002t` 已用 X86 验证 checkout 与工具链可用。
3. **未来 bump LLVM 版本时 `LLVM_ALL_TARGETS` 列表可能变动**：上游可能新增或重排 core-tier targets，bump 时需检查 DADAO 条目是否仍在列表中（通常不会被移除，但需人工确认）。

## 状态说明

本决策由用户于 2026-09-17 裁定（D1 逐条确认），置为 Candidate。待 `LLVM-003t` 落地后可验证决策有效性，届时由主会话升为 Accepted。
