# INFRA-016t: doctor.py 补组件构建依赖检查

**模块**：infra
**项目里程碑**：M1→M2
**依赖**：无
**状态**：待开始

## 问题描述

`tools/infra/doctor.py`（`INFRA-005t`）在 native 路径只查 `git/make/cmake/python3/ninja/clang/docker`，**不检查组件的构建依赖**（glib-2.0 / pixman-1 / libfdt / zlib 等）。

**实证（2026-09-29）**：`make build-qemu` 因缺 `pkg-config`/`glib-2.0` 失败（`meson.build:1059: Dependency lookup for glib-2.0 ... Pkg-config ... not found`），而 `make doctor` 仍 PASS。

`deferred.md` 已登记此缺口（`QEMU-002t` 交叉复核，2026-09-18）。

## 修改内容

`tools/infra/doctor.py`：增加**组件构建依赖检查**（按需/按启用组件）：

- **LLVM**：`cmake`（版本下限）、`ninja`、C++ 工具链
- **QEMU**：`pkg-config`、`glib-2.0`、`pixman-1`、`zlib`、（`libfdt` 视 target 需要）
- 机制：用 `pkg-config --exists <pkg>` 探测（**注意**：Ubuntu 的 `libfdt-dev` 不提供 `libfdt.pc`，需特殊处理或注明）
- 未装 → `doctor` 报 **FAIL**（给出缺失清单与安装建议，**不自行安装**）

## 约束

- 只加检查，不改现有检查
- **`doctor` 只报告、不安装**（命令缺失 → 提示用户）
- 完成后 `make check` EXIT=0（doctor 本身不阻断 `make check`，除非既有约定）

## 验收标准

1. `doctor.py` 检查 QEMU（`pkg-config`/`glib-2.0`/`pixman-1`/`zlib`）与 LLVM（`cmake`/`ninja`/C++）依赖
2. 缺依赖时 `make doctor` 报 FAIL 并列出缺失项
3. 现有检查不受影响
4. 反例验证（模拟缺依赖 → FAIL）

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
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）