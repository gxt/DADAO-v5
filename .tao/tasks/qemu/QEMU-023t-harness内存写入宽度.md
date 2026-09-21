# QEMU-023t: harness `input_state.memory` 按宽度写入

**模块**：qemu
**项目里程碑**：M1
**依赖**：`QEMU-016t`（harness memory **读**比对路径）、`QEMU-015t`
**状态**：待开始
**上游发现**：`QEMU-015t` 完成区「新发现 4」；`QEMU-016t` 验收 #6（跨模块阻塞）
**决策依据**：用户裁定（2026-09-21）——采方案 **C**；契约补注 `ADR-0009`（见其「补注续二」）

## 执行环境

**执行环境**：本地

## 背景（已实测确认）

**契约（本次用户裁定并写入 `ADR-0009` 补注）**：

> `tests/vectors/isa/*.yaml` 的 `input_state.memory[].value` 表示「**`address` 处存放的 N 字节值**」，N = 被测向量的**访存宽度**（由 mnemonic 推导：`b`→1、`w`→2、`t`→4、`o`→8；`stm.*`/`ldm.*` 按元素宽度）。harness 须以**宽度 N** 的 store 写入该值。

**现状缺陷**：`tests/scripts/build_test_binary.py` 的 `build_loader()` 对 `input_state.memory` **无条件**用 `st.o`（8 字节）写。在大端下 `value=0x42` 写到 A 时字节序列为 `00 00 00 00 00 00 00 42`——**`0x42` 落在 `A+7`，A 处是 `0x00`**；而窄 load 从 A 读 → 读得 `0x00`。

**实测影响**（`--batch tests/vectors/isa/` 基线 `597/566/26/5/0`）：
- **24 条窄 load FAIL**（`mem-rd` 的 `ld.ub/uw/ut/sb/sw/st` + `ldm.*`，各 semantic+boundary；0-based 索引 `[3,4,9,10,15,16,20,21,26,27,32,33,66,67,72,73,78,79,83,84,89,90,95,96]`）
- 使用 `input_state.memory` 的向量共 **48 条**（`mem-rd` 36 + `mem-ra` 6 + `mem-rb` 6）；其余 24 条为 8 字节（`ld.o`/`ldm.o`/`stm.o`，行为不变）或 `stm.b/w/t`（宽度 1/2/4，行为改变但仍应 PASS）

**与真实大端机器惯例一致**：MIPS/SPARC/PowerPC 下类型化数据按**自然宽度**存放（`char` 占 1 字节），`lbu A` 读得 A 处的字节。DADAO `spec/DADAO-21-ABI §数据表示` 亦为「多字节数据最高有效字节在最低地址」；其「右对齐」仅适用于 **8 字节参数/varargs slot**，非通用内存。

## 目标

`build_loader()` 写 `input_state.memory` 时，按被测向量的访存宽度 N 使用 `st.b`/`st.w`/`st.t`/`st.o`，把 `value` 的**低 N 字节**写到 `address`，使 `ld.<N>` 从 `address` 读得 `value`。

## 接口规范

- 输入：`tests/scripts/build_test_binary.py`（`build_loader()`、`build_test_binary()`）
- 输出：
  - `tests/scripts/build_test_binary.py`：`build_loader()` 的 memory 写路径按宽度选 store
  - `tests/vectors/schema.md`：补一句 `input_state.memory[].value` 的契约说明（**文档同步**，跨 testcases 模块的 doc，非数据修改）
- 约束：
  - **不改任何 vector YAML**（48 条向量零改动）
  - **不改** QEMU 补丁（`components/qemu/patches/`）
  - **不改** `--dump`/退出码/`expected_state` 比对路径（`016t` 的读侧不动）
  - 宽度推导**复用** `QEMU-016t` 已引入的 `derive_width_from_mnemonic()`（`st.b`→1B … `stm.*` 按元素宽度）；若需扩展（如 `ld.*` 也走同一函数）须保持单一实现
  - 编码取自 `contracts/opcodes.yaml`：`st.b`/`st.w`/`st.t`/`st.o` 的 op 从表取，**不硬编码**
  - 8 字节场景行为**必须与改动前逐字节一致**（`st.o` 路径）

## 关键概念 / 数据

**宽度推导**（与 `016t` 的读侧对称）：
- `ld.ub`/`ld.sb`/`ldm.ub`/`ldm.sb`/`st.b`/`stm.b` → 1
- `ld.uw`/`ld.sw`/`ldm.uw`/`ldm.sw`/`st.w`/`stm.w` → 2
- `ld.ut`/`ld.st`/`ldm.ut`/`ldm.st`/`st.t`/`stm.t` → 4
- `ld.o`/`ldm.o`/`st.o`/`stm.o` → 8

**关键不变量**：`input_state.memory` 的地址可能**非 8 字节对齐**（如 `stm.b` 的元素地址）；用宽度 N 的 store 后，对齐要求变为 **N 字节对齐**（`st.b` 无对齐要求、`st.w` 需 2、`st.t` 需 4、`st.o` 需 8）。须核对 48 条的地址是否满足其宽度的对齐要求（不满足则须报告，**不得**静默跳过或回退）。

## 交付物

- `tests/scripts/build_test_binary.py`：`build_loader()` 按宽度写 `input_state.memory`
- `tests/vectors/schema.md`：`input_state.memory[].value` 契约说明（文档）
- 完成区附：24 条窄 load「改前 FAIL → 改后 PASS」逐条对比；48 条 memory 向量全 PASS；全量回归数字；反例门控真实输出

## 验收标准

| # | 验收项 | 现在可跑 / BLOCKED | 说明 |
|---|--------|-------------------|------|
| 1 | `build_loader()` 按 mnemonic 宽度用 `st.b/w/t/o` 写 `input_state.memory` | 现在可跑 | 代码审查 + 反解析二进制核对 op 字段 |
| 2 | **24 条窄 load 全部由 FAIL → PASS**（逐条） | 现在可跑 | 须给改前/改后逐条对比 |
| 3 | 使用 `input_state.memory` 的 **48 条全 PASS**（含 `ld.o`/`ldm.o`/`stm.o` 的 8B 场景与 `stm.b/w/t`） | 现在可跑 | `mem-rd`/`mem-ra`/`mem-rb` 子集 `--batch` |
| 4 | 全量 `tests/vectors/isa/ --batch` = **597/590/2/5/0**（26 failed → 2，仅余 `misc` 的 `fence` ILLI 桩），**零新增** | 现在可跑 | 逐条核对失败清单 |
| 5 | **8 字节场景逐字节不变**：`ld.o`/`ldm.o`/`stm.o` 的 loader 产物与改动前一致 | 现在可跑 | 二进制比对 |
| 6 | **对齐核对**：逐条确认 48 条的地址满足其宽度的对齐要求；不满足者须报告（不得静默跳过/回退） | 现在可跑 | 脚本化逐条核对 |
| 7 | **反例门控**：把宽度写错（如 `st.b`→`st.o`，或反之）→ 至少 1 条窄 load 必须 FAIL；还原（含重建）→ PASS | 现在可跑 | 证明宽度选择承重、非恒真 |
| 8 | 不改 vector YAML / 不改 QEMU 补丁 / 不改 `expected_state` 比对路径 | 现在可跑 | `git diff` |
| 9 | `tests/vectors/schema.md` 契约说明已补 | 现在可跑 | diff |

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
