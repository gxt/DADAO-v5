# QEMU-026t: QEMU 11.1.1 / GCC 15 构建修复

**模块**：qemu
**项目里程碑**：M1→M2
**依赖**：无
**状态**：待开始

## 问题描述

`make build-qemu` 在当前环境**构建失败**：

```
target/dadao/cpu.c:204:5: error: implicit declaration of function
'cpu_loop_exit_restore'; did you mean 'cpu_loop_exit_requested'?
[-Wimplicit-function-declaration]
```

**根因**（主会话已查明）：

1. **潜在缺陷**：DADAO 补丁的 `target/dadao/cpu.c` **一直缺少** `#include "accel/tcg/cpu-loop.h"`（该声明在 QEMU 11.x 位于此头文件；`target/riscv/tcg/op_helper.c:30` 即显式包含）。**重整前/后补丁均无此 include**——非近期改动引入。
2. **编译器严格化**：**GCC 14+ 将隐式函数声明从「警告」改为「默认错误」**。本环境 **GCC 15.2.0**（`dpkg.log`：2026-09-26 安装）。
   - M1 构建（2026-09-22）用的是更宽松的编译器 → 带警告通过
   - 现 GCC 15 → 直接报错

3. **可能不止一处**：构建会逐个暴露同类的隐式声明 / API 不兼容（QEMU 11.1.1 的接口变动）。

## 目标

修复 `target/dadao/*` 与 `hw/dadao/*` 在 **QEMU 11.1.1 + GCC 15** 下的构建问题，使 `make build-qemu` 成功产出 `qemu-system-dadao`。

## 修改内容（迭代式）

1. **补 include**：`target/dadao/cpu.c` 加 `#include "accel/tcg/cpu-loop.h"`（对照 `target/riscv/tcg/op_helper.c`）
2. **重放补丁 + 重构建**，逐个修复后续暴露的错误（隐式声明、API 签名变动、已移除符号等）
3. **每个文件改动落入 `components/qemu/patches/`**（按 `docs/spec/component-patching.md`：**裸 `git diff`**，一文件一补丁）
4. 构建成功后：`qemu-system-dadao -M ?` 显示 `dadao-m1`；`tools/qemu/smoke-dadao-m1.sh`（若在）通过

## 约束

- **命令缺失/构建失败于依赖（非本补丁）→ 停下报告，禁止自行安装/下载**
- **不得改变指令语义**——只修编译/API 适配
- 逐条核对，禁止正则批量替换
- 完成后 `make check` EXIT=0

## 验收标准

1. `make build-qemu` **EXIT=0**，产出 `.work/build/qemu/qemu-system-dadao`
2. `qemu-system-dadao -M ?` 含 `dadao-m1`
3. 补丁格式合规（每份恰 1 个 `diff --git`）；补丁与源树 `git diff` 一致
4. `make check` EXIT=0
5. 记录**本轮修复的全部 API 适配点**（供参考）

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