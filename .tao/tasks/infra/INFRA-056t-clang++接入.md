# INFRA-056t: 接入 `clang++` + 核实 2 个 `.cpp` 测试需求

**模块**：infra
**项目里程碑**：M7
**依赖**：`INFRA-050t`（LLVM 一次构建 + 双落点，`已验证`；同改 `Makefile` ⇒ 串行）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - 用户裁定（2026-10-11；`INTEG-033k §裁定汇总 #3`）：**加 `clang++`** + 核 **2 个 `.cpp`** 测试需求。
  - 现状：`.dadao/cross-toolchain/bin/` 已有 `clang`（无 `clang++`）；`INFRA-050t` 的一次构建（`LLVM_ENABLE_PROJECTS=clang;lld`）**已含 clang 驱动**（`clang++` 通常是 `clang` 的 C++ 驱动模式，`clang -x c++` 等价），安装落点当前只装 `clang`。
  - picolibc 自带 test 中的 2 个 C++ 文件（实测）：`test/test-cdefs-cxx03.cpp`、`test/test-cplusplus.cpp`（位于 `.work/source/picolibc/test/`，随 `INFRA-055t` 浅克隆）。
  - `ADR-0016`（install 布局：`D3/D4/D5/D11`）；`Makefile` 的 `install-host` target。
- **输出**：
  1. `.dadao/cross-toolchain/bin/clang++` 落点（可执行；`clang++ --version` 与 `clang` 同源）——按 `ADR-0016` 布局；`Makefile`/`tools/infra/**` 同步。
  2. **2 个 `.cpp` 需求核实报告**：逐条说明其编译需求（是否需要 C++ 头/库、freestanding 形态、`-nostdlib` / `-ffreestanding` 下能否编），实测证据（编译/失败真实输出）。
- **约束**：
  - **不引入** C++ 标准库（freestanding 优先）；若某 `.cpp` 需 libstdc++/libc++，**显式登记**（不静默跳过）。
  - **依赖 `INFRA-050t` 的构建产物**，不重复构建 LLVM；仅补安装/落点。
  - **计数不写死**；只动任务范围，越界须披露。

## 验收标准

1. **`clang++` 可用**：`.dadao/cross-toolchain/bin/clang++ --version` EXIT=0（真实输出）；与 `clang` 同 commit。
2. **幂等**：连续两次 `make install-host` 均 EXIT=0（同 `INFRA-053t` 口径）。
3. **2 个 `.cpp` 核实**：逐条给出编译命令 + 真实结果（OK / 缺什么）；需求结论明确（是否需要 C++ 库）。
4. **门控**：`make check`、`check-no-residue` EXIT=0；`check-patch-tree` EXIT=0。
5. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
