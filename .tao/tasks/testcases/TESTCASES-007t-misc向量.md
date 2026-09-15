# TESTCASES-007t: misc 向量（swym / illi / fence）

**模块**：testcases
**项目里程碑**：M1
**依赖**：`TESTCASES-006t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `tests/vectors/schema.md`（`TESTCASES-002t` 返工后：含 encoding 恒 fault 豁免）
  - `contracts/opcodes.yaml`（`swym-iiii`/`illi`/`fence` 编码字段；`op=value>>24`、`ha=(value>>18)&0x3f`）
  - `.tao/knowledge/contract-isa.md` §7（系统指令：`swym`/`fence`）、§8.2（保留编码 UNDI）、§8.3（全零字 → ILLI）、§9.1（ILLI）
- **输入说明（陈旧引用修正）**：仓库内**无任何 `tests/vectors/isa/*.yaml`**——上一版 `002t` 的向量数据已随返工**一并丢弃**。本任务按 `schema.md` **从零生成** `misc.yaml`，**不是**重组/修复既有文件。
- 输出（**本任务拥有的文件**，`tests/vectors/isa/`）：
  - `misc.yaml`
- 约束：
  - 期望值**手工派生自 `contract-isa.md`/`spec/`/ADR-0004**，不得从 LLVM/QEMU 反推
  - 覆盖率主键 `(insn, format)`；M1 scope 以 `excluded_m1 != true` 为准（`swym`/`illi`/`fence` 均属 M1）
  - **只生成/修改 `misc.yaml`**；**不改** `contracts/`；**不改** `ctrl-*`/`reg-*`/`mem-*`
  - 参考仓库（`.work/DADAO-0628/`）的向量数据**仅内容溯源，不得作为执行依赖**（禁止复制数据正文）
  - 完成后不自行 commit

## 任务范围

### 1. 目标文件（从零生成）

> **数据来源说明**：仓库内**无既有向量数据**（上一版已丢弃），本任务按 `schema.md` 从零生成 `misc.yaml`；不再有「旧文件 → 新文件」的重组动作。

| 目标文件 | 覆盖身份 |
|---|---|
| `misc.yaml` | `swym-iiii`/`illi`/`fence`（3 个） |

- `br.*`/`jump`/`call`/`ret`（`005t`/`006t`）不在本任务。

### 2. F6：`illi` 的 encoding 豁免（复核）

- **事实**：`illi` 恒 ILLI（`contract-isa.md` §8.2/§9.1），`encoding` 类定义为「可解码执行无 fault」→ `illi` 的 encoding case **不可构造**，豁免。
- **要求**：`misc.yaml` 中 `illi` 的 encoding 列保持 `—`，覆盖率由 `legality` active（`expected_fault: ILLI`）满足；notes 说明豁免理由（恒 fault）。`schema.md` 的豁免条款由 `002t` 写入，本任务复核数据与之一致。

### 3. F10：`misc.yaml` 的 encoding 向量修复

- **要求**：逐条修正 `swym`/`fence` 的 encoding 向量（`illi` 豁免，见 §2），使 `word` 满足 `(word & mask) == value` 且可解码执行无 fault：
  - `swym`：占位指令（`contract-isa.md` §7），不改架构状态；`expected_state: null`、`expected_fault: null`、`status: active`；
  - `fence`：nop-like，不改寄存器；同上；
  - `expected_pc: null`（`swym`/`fence` 不改变 PC 目标——PC 顺延到下一条，属 harness 常规推进，不构成「改变 PC」；若 `002t` schema 对顺延有明确规定，按 schema 执行）。
- **全零字**：`0x00000000` 是 `illi` → **ILLI**，不是 UNDI（`§8.3`）；UNDI 的保留编码表达归 `TESTCASES-008t`，不在本任务。

### 4. 语义/合法性

- 复核 `illi` 的 legality（`expected_fault: ILLI`）、`swym`/`fence` 的 semantic（不改状态）。

## 验收标准

1. `misc.yaml` 覆盖 `swym-iiii`/`illi`/`fence` 三个 M1 身份
2. `misc.yaml` 从零生成，覆盖 `swym-iiii`/`illi`/`fence` 3 个 M1 身份（无遗漏）
3. `illi` 无 encoding case，inventory 显式标注豁免理由（恒 fault）；覆盖率由 `legality` active 满足
4. `swym`/`fence` 的 encoding 经推演确认可解码执行无 fault（不 ILLI）；字段值 + 依据章节齐备
5. 未改 `contracts/`；未动 `ctrl-*`/`reg-*`/`mem-*`
6. `python3 tools/testcases/validate_vectors.py` 零错误；`make check` PASS
7. 未自行 commit

## 背景（完整）

### 目标

把系统/杂项指令集中到 `misc.yaml`，复核 `illi` 的 encoding 豁免，并修复 `swym`/`fence` 的 encoding 向量（F10）。

### 设计理由

- `swym`/`illi`/`fence` 均属 M1 系统指令，但语义上互不相关且不共享格式族；集中在一个 `misc.yaml` 便于管理。
- `illi` 是唯一的恒 fault 指令，必须显式豁免并记录，避免覆盖率门控假阴性。

### 关键概念 / 数据

- **`swym`**：占位指令（`contract-isa.md` §7），不改变架构状态。
- **`fence`**：内存栅栏，M1 下 nop-like。
- **`illi`**：恒 ILLI（§9.1）；全零字 `0x00000000` = `illi 0`（§8.3）。
- **保留编码（QFC 空白格）→ UNDI**（§2.9/§8.2）：本任务不处理，归 `008t`。

### 上游引用

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-001d-vector-data.md`、`DL-020a-encoding-vectors.md`（内容溯源，非执行依赖）

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **助记符**：`unimp`→`illi`；`swym`/`fence` 保留。
2. **`illi` 恒 ILLI**：与 0628 一致；v5 明确 encoding 豁免。
3. **UNDI 区分**：v5 明确「保留编码 → UNDI」与「全零字 → ILLI」不同（§8.2/§8.3）。
4. **覆盖率身份**：v5 用 `(insn, format)`。

## 已知坑 / 结论

1. **全零字不是 UNDI**：`0x00000000` → ILLI（§8.3）。
2. **`illi` encoding 不可达**：恒 fault，豁免；覆盖率由 legality 满足。
3. **`misc.yaml` 从零生成**：不依赖任何既有文件；`swym`/`illi`/`fence` 三个身份一次生成齐备。
4. **不自行 commit**：完成后等待审查。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-001d-vector-data.md`、`DL-020a-encoding-vectors.md`（内容溯源）
- 本项目：`.tao/knowledge/contract-isa.md` §7/§8/§9、`contracts/opcodes.yaml`、`tests/vectors/schema.md`
- 知识库：`.tao/knowledge/MEMORY.md`、`.tao/knowledge/deferred.md`

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

### 第 1 轮 engineer 自审
（待填写）

### 第 1 轮 reviewer 验收
（待填写）
