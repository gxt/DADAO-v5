# TESTCASES-010t: `mem-rd` 窄 load 向量与 ISA 内存模型对齐

**模块**：testcases
**项目里程碑**：M1
**依赖**：`TESTCASES-004t`（RAM 地址迁移）、`QEMU-016t`（harness memory 比对路径）
**状态**：待开始
**上游发现**：`QEMU-015t` 完成区「新发现 4」/ `QEMU-016t` 验收 #6（跨模块阻塞）

## 执行环境

**执行环境**：本地

## 问题（已实测确认）

`tests/vectors/isa/mem-rd.yaml` 有 **24 条窄 load** 向量（12 `semantic` + 12 `boundary`，0-based 索引 `[3,4,9,10,15,16,20,21,26,27,32,33,66,67,72,73,78,79,83,84,89,90,95,96]`），在 harness 下**全部 FAIL**（`exit=0x01`）。涉及助记符：`ld.ub/uw/ut/sb/sw/st` 与 `ldm.ub/uw/ut/sb/sw/st`。

**根因**：**向量 golden 与 ISA 的大端+右对齐内存模型冲突**。

- ISA 是**大端**（`contracts/abi.yaml`: `endianness: big`；`spec/SimRISC-00 §指令系统设计`：「数据端序同样为大端序」）
- ABI 明确**右对齐**（`spec/DADAO-21-ABI §数据表示`）：「8 字节 slot 内，N 字节类型的有效值**右对齐**（byte `8-N` 至 `7`），低地址字节（byte `0` 至 `8-N-1`）为符号/零扩展位」
- 即：一个窄值放在 slot 中时，其**低字节在高地址**；从 **EA** 做窄 load 读到的是**扩展位**，不是有效值
- 而向量 golden 假定窄值在**低地址**。例（索引 3，`ld.ub` semantic）：
  - `input_state.memory: [{address: 0xFFFF00000100, value: 0x42}]`（harness 按 BE-8B `st.o` 写入 → `0x42` 落在 `EA+7`，`EA` 字节为 `0x00`）
  - `expected_state.rd.rd1 = 0x42`
  - 实际 `ld.ub` 从 `EA` 读出 `0x00` → FAIL
  - 按 ABI 右对齐，正确写法应是 `address = EA + 7`（`ld.ub` 自 `EA+7` 读得 `0x42`），或 golden 改为 `0x00`

**与 `QEMU-016t` 的边界**：`016t` 已实现 `expected_state.memory` 比对（**store** 向量侧，24 条全 PASS）；本任务是**load** 向量侧的 golden 修正，**不改** harness。

## 待裁决（须用户逐条确认）

**方案 A（向量侧改地址，右对齐）**：把 24 条的 `input_state.memory[].address` 由 `EA` 改为 `EA + (8 - N)`（N = 该向量的访存宽度）。golden 不变（仍断言窄 load 读得有效值）。
- 优点：忠实 ISA 右对齐模型；`expected_state.rd` 语义清晰；harness 不改
- 缺点：需逐条按宽度算偏移；`boundary` 用例的边界语义需重新表述

**方案 B（向量侧改 golden）**：地址不变，把 `expected_state.rd` 改为「从 EA 读到的扩展位」（如 `ld.ub` → `0x00`；`ld.sb` → `0x00`/符号扩展）。
- 优点：改动小
- 缺点：**弱化测试意图**——原意图是「窄 load 读得该值」，改成读扩展位后不再检验有效值读取；`boundary` 用例失去意义

**方案 C（harness 侧按宽度写输入内存）**：harness 写 `input_state.memory` 时按向量 mnemonic 宽度用 `st.b/st.w/st.t/st.o`。
- 优点：向量不改
- 缺点：改变 harness 既有语义（`input_state.memory` 现定义为 BE-8B slot）；影响所有向量，回归面大；属 QEMU 模块改动

> ⚠️ 触及 **ADR 判据**（跨模块契约、多方案、结论固化）——须用户判定是否生成 ADR。

## 交付物

- 修正后的 `tests/vectors/isa/mem-rd.yaml`（24 条；**仅**这 24 条，不得改动其它向量）
- 完成区附「24 条在 harness 下**逐条** PASS」的真实输出
- 反例门控：任取一条篡改 → FAIL；还原 → PASS（**还原须含重建**）

## 约束

- **不改** harness（`tests/scripts/`）、**不改** QEMU 补丁
- 每条向量的**语义意图**（测窄 load 从内存读得有效值）必须保留
- 修改后须重跑 `tools/testcases/validate_vectors.py`（结构/一致性）
- **不得**以 validator 绿灯为唯一判据；期望值须**独立重算**（按 ABI 右对齐逐条核对地址与值）

## 验收标准

| # | 验收项 | 现在可跑 / BLOCKED | 说明 |
|---|--------|-------------------|------|
| 1 | 24 条窄 load 向量在 harness 下**逐条** PASS | 现在可跑 | `python3 tests/scripts/run_qemu_test.py tests/vectors/isa/mem-rd.yaml --batch`（临时目录） |
| 2 | 语义意图保留：仍检验「窄 load 读得有效值」 | 现在可跑 | 代码级逐条核对（不得退化为断言扩展位） |
| 3 | 反例门控：篡改一条 → FAIL；还原 → PASS | 现在可跑 | 须附真实输出与还原证据 |
| 4 | 仅改这 24 条，其它向量零改动 | 现在可跑 | `git diff --stat` |
| 5 | `validate_vectors.py` 通过（结构/一致性） | 现在可跑 | 结构门控，**非**语义证据 |
| 6 | 全量 batch 失败数由 29 → 5（24 条消除；余 3 `ctrl-call` + 2 `misc` 归 `017t`/`018t`/deferred） | 现在可跑 | 须附前后对比 |

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
