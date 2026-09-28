# QEMU-026t: QEMU 11.1.1 / GCC 15 构建修复

**模块**：qemu
**项目里程碑**：M1→M2
**依赖**：无
**状态**：已验证

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

**测试结果**：通过 5/5（`make build-qemu` EXIT=0、`-M ?` 含 `dadao-m1`、补丁格式合规、`make check` EXIT=0、补丁与源树一致）

**修改文件**：
- `components/qemu/patches/target/dadao/cpu.c.patch`（更新，反映以下两处修复）

**本轮修复的 API 适配点**：
1. **`#include "accel/tcg/cpu-loop.h"`**：`cpu_loop_exit_restore()` 的声明在 QEMU 11.x 位于 `include/accel/tcg/cpu-loop.h:65`（`G_NORETURN void cpu_loop_exit_restore(CPUState *cpu, uintptr_t host_pc)`）。GCC 14+ 将隐式函数声明默认报错，此前 M1 构建靠更宽松编译器带警告通过。
2. **`G_NORETURN` 修饰 `dadao_cpu_do_unaligned_access`**：`TCGCPUOps.do_unaligned_access` 函数指针类型为 `G_NORETURN void (*do_unaligned_access)(...)`（`include/accel/tcg/cpu-ops.h:248`）。函数定义缺少 `G_NORETURN` 会触发 `-Wdiscarded-qualifiers`（GCC 15 下 `noreturn` 限定符不匹配）。对照 `target/riscv/cpu.h:655` 的 `G_NORETURN void riscv_cpu_do_unaligned_access(...)`。

**验收结果**：
```
$ make build-qemu
[16/16] Linking target qemu-system-dadao
build-qemu: PASS

$ .work/build/qemu/qemu-system-dadao -M ?
Supported machines are:
dadao-m1             DADAO M1 bare-metal test machine
none                 empty machine

$ make check
repository checks: PASS
check-patch-tree: 2 component(s), 67 patches OK
```

**新发现/坑**：
- GCC 15 对隐式函数声明和 `noreturn` 限定符不匹配的严格检查是本任务的触发条件。QEMU 11.x 的 `cpu_loop_exit_restore` 移至 `accel/tcg/cpu-loop.h` 是上游变更，DADAO 补丁一直缺少此 include。
- `do_unaligned_access` 的 `G_NORETURN` 要求在 QEMU 11.x 的 `include/accel/tcg/cpu-ops.h` 中明确标注，其他 target（如 riscv）也遵循此约定。

**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：`components/qemu/patches/target/dadao/cpu.c.patch` 的两处改动

**finding 1**：`#include "accel/tcg/cpu-loop.h"` 位置正确（在 `#include "accel/tcg/cpu-ops.h"` 之后），与 riscv 的 `target/riscv/tcg/op_helper.c:30` 模式一致。
- 判决：✅无问题

**finding 2**：`G_NORETURN static void` 的修饰符位置——GCC 接受 `G_NORETURN` 在 `static` 前（`G_NORETURN` 展开为 `__attribute__((noreturn))`），与 riscv 的 `target/riscv/cpu.h:655` 写法一致。
- 判决：✅无问题

**finding 3**：构建验证——clean apply + rebuild 成功，`make check` 全绿。
- 判决：✅无问题

**总判决**：无遗留 finding，可标 `待验收`。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer（DeepSeek V4.1 Flash）｜**方式**：独立重跑，不采信完成区
**环境**：GCC 15.2.0、git 2.53.0、ninja 1.13.2、22 核；组件 qemu 锁定 `c3d48b7d1e89`（v11.1.1）

**分析了哪些文件**
- `components/qemu/patches/target/dadao/cpu.c.patch`（本任务唯一改动产物，`git diff` 与 HEAD 对比：仅 2 处 —— 新增 `#include "accel/tcg/cpu-loop.h"`、`dadao_cpu_do_unaligned_access` 加 `G_NORETURN` + 续行缩进）
- `Makefile`（`build-qemu` / `check` / `prepare` 目标）、`docs/spec/component-patching.md`、`tools/infra/{make_patch,apply_series,check_patch_tree,fetch}.py`
- `tools/qemu/smoke-dadao-m1.sh`、`tests/lit/E2E/*.test`

**重跑记录（全部为审查者自己的输出）**

1) `make build-qemu` —— EXIT=0
```
$ make build-qemu > log 2>&1; echo $?
0
build-qemu: PASS
```
2) 产出与机型
```
$ ls -la .work/build/qemu/qemu-system-dadao
-rwxr-xr-x 1 ubuntu ubuntu 35498792 Sep 29 07:18 .../qemu-system-dadao
$ .work/build/qemu/qemu-system-dadao -M ?; echo $?
Supported machines are:
dadao-m1             DADAO M1 bare-metal test machine
none                 empty machine
0
```
3) **clean apply + 全量重建**（最强路径，独立执行）
```
$ git -C .work/source/qemu checkout -- . && git -C .work/source/qemu clean -fd
Removing configs/devices/dadao-softmmu/ ... target/dadao/ ...
$ git -C .work/source/qemu status --porcelain   # 空 → 已回 base
$ make prepare; echo $?
0
apply-series: qemu applied 31 patches        # 从干净 base 重放
$ rm -rf .work/build/qemu && time make build-qemu; echo $?
EXIT=0        real 2m6.6s  (2356/2356 编译链接完成)
build-qemu: PASS
```
   重放后 `git hash-object target/dadao/cpu.c` = `a454c5effa3816...`，与补丁 `index 0000000..a454c5e` 一致。

4) 补丁格式合规
```
$ 对 series(31 份) 逐份 grep -c '^diff --git' → 全部 1
$ make check → check-patch-tree: 2 component(s), 67 patches OK
```
5) 补丁 ↔ 源树 `git diff` 一致（reviewer 自写脚本，逐份比对，忽略 `index` 行 hash 缩写长度）
```
MATCH=31 MISMATCH=0
```
6) `make check` —— EXIT=0
```
$ make check > log 2>&1; echo $?
0
check-patch-tree: 2 component(s), 67 patches OK
repository checks: PASS
```
7) **反例验证（回退 include → 构建必须失败）** —— 通过
```
$ sed -i '/cpu-loop.h/d' .work/source/qemu/target/dadao/cpu.c
$ make -C .work/build/qemu -j22; echo $?
2
../../source/qemu/target/dadao/cpu.c:204:5: error: implicit declaration of function
‘cpu_loop_exit_restore’; did you mean ‘cpu_loop_exit_requested’?
[-Wimplicit-function-declaration]
```
   证实「补上 include 前确实无法构建」，且构建真能捕获该缺陷。**已还原**：`cp` 回备份，`diff` 与备份完全一致（`RESTORED_IDENTICAL`），后续全量 clean 重建即从补丁态构建，无残留。

8) 附带核验（QEMU 构建后解锁）
```
$ bash tools/qemu/smoke-dadao-m1.sh; echo $?   → 0  （ILLI exit=136 确认）
$ .work/build/llvm/bin/llvm-lit -v tests/lit/E2E/; echo $?  → 0
PASS: DADAO-E2E :: smoke_arith.test / smoke_jump.test / smoke_add.test
Total Discovered Tests: 3   Passed: 3 (100.00%)
```
   `smoke_add.test` 的 RUN 行实调 `%llvm_mc / %llvm_objcopy / %qemu`，非桩；此前 0/3 已解锁为 3/3。

**约束核验（逐条）**
- 不得安装/下载：审查全程未安装/未联网下载，`make prepare` 走后本地 mirror（日志 `skipping fetch`）✅
- 不得改指令语义：本任务唯一改动为 `cpu.c`（CPU 类初始化/复位/dump，不含指令译码或语义），补丁 `git diff` 仅 include + `G_NORETURN` + 缩进；其余 30 份 qemu 补丁与 llvm 补丁零改动（`git status` 仅 2 文件）✅
- 逐条核对、禁止批量替换：无法从产物直接观测过程，仅核验最终补丁为精确差分（内容 hash 匹配）✅
- `make check` EXIT=0 ✅

**与完成区一致性核对**
- 「通过 5/5」「check-patch-tree 67 patches OK」「`-M ?` 含 dadao-m1」均与 reviewer 重跑一致 ✅
- 完成区 1/5 项的生效性说明全部属实。**一处需澄清**：完成区 API 适配点 2 说 `G_NORETURN` 缺失会触发 `-Wdiscarded-qualifiers`——reviewer 实测属实（警告），但该警告在当前 `--disable-werror` 配置下**不会**导致构建失败（实测移除 `G_NORETURN` 后 `make -C build/qemu` EXIT=0，仅告警）。即：**硬性阻断只有 include 一项**，`G_NORETURN` 属警告级 API 适配。完成区表述未宣称它是构建失败原因，故不构成不实陈述，仅在此注明供架构师知悉。

**观察（非阻断）**：补丁 `index 0000000..a454c5e` 为 7 位缩写；`git 2.53.0` 下 `make_patch.py` 会输出 10 位（本次复算得 `index 0000000000..a454c5effa`）。二者仅缩写长度不同、blob hash 与内容完全一致，且与既有 30 份 qemu 补丁的 7 位写法一致；补丁经 `git apply` 全量重放校验通过，不影响合规与可复现性。

**判决：Accepted**

理由：验收标准 1–5 全部在 reviewer 独立重跑下通过；clean apply（`make prepare` 重放）→ 全量重建可复现；反例（回退 include）实测构建失败、已还原；约束无违反；附带核验 8/9 由 0/3 解锁为 3/3 且 smoke 通过。建议主会话将任务状态置为 `已验证`（最终接受仍由架构师终审）。