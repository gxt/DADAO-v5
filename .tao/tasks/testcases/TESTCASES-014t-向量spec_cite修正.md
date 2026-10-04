# TESTCASES-014t: 向量 spec_cite 按新文档编号修正

**模块**：testcases
**项目里程碑**：M2
**依赖**：无
**状态**：待开始

> **处置（2026-10-04，`SPEC-090k` 核验）：改范围（继续执行，范围收窄）。**
> 原「位宽主引用」部分**已完成**（向量 `spec_cite` 已用 `SimRISC-08/09/10`；`swym` 已指 `SimRISC-11 §占位指令`）；**残留**为生成器 `tools/testcases/generate_isa_vectors.py` 的 `_ILLI_RULES`（**L974/976/978**）三条**规则引用**陈旧，与 `contracts/legality_rules.yaml` 权威值不一致：
> | `_ILLI_RULES` 键 | 现值（陈旧） | `legality_rules.yaml` 权威值 |
> |---|---|---|
> | `dst_rd0` | `SimRISC-01 §rd0 为目的寄存器约定` | `SimRISC-00 §数据寄存器` |
> | `dst_dual_same` | `SimRISC-01 §加减操作` | `SimRISC-04 §加减操作` |
> | `dst_rb0` | `SimRISC-02 §rb0 为目的寄存器约定` | `SimRISC-00 §基址寄存器` |
> **本任务收窄为**：修 `_ILLI_RULES` 三条规则引用（对齐 `legality_rules.yaml`）+ 重生成受影响向量；位宽主引用部分作废，不重复。

## 问题描述（G3）

`tests/vectors/isa/*.yaml` 的 `spec_cite` 仍用**旧文档编号**（重组前 SimRISC-01~04 的语义），共约 **589 条** 指向的文档不含该指令。例如：

- `SimRISC-01 §加减操作`（SimRISC-01 现为「取数存数」）→ 应按位宽指向 SimRISC-04/08/09/10
- `SimRISC-01 §rd0 为目的寄存器约定` → 已迁至 SimRISC-00
- `misc.yaml` 的 swym `SimRISC-04 §占位指令` → SimRISC-11

## 修改内容（收窄后）

### 1. 规则引用对齐（`tools/testcases/generate_isa_vectors.py`）

把 `_ILLI_RULES`（L974/976/978）三条规则引用的 `spec_cite` 改为与 `contracts/legality_rules.yaml` **权威值一致**：

| 键 | 现值（陈旧，删） | 新值（对齐 `legality_rules.yaml`） |
|---|---|---|
| `dst_rd0` | `SimRISC-01 §rd0 为目的寄存器约定` | `SimRISC-00 §数据寄存器` |
| `dst_dual_same` | `SimRISC-01 §加减操作` | `SimRISC-04 §加减操作` |
| `dst_rb0` | `SimRISC-02 §rb0 为目的寄存器约定` | `SimRISC-00 §基址寄存器` |

> 建议：改为**从 `contracts/legality_rules.yaml` 读取**（或与之一致），避免硬编码再次漂移；如保留常量，须加注释指向权威文件。

### 2. 重生成受影响向量

按生成器既有 `scoped` 用法重生成受影响文件（`reg-arith.yaml` / `reg-compare.yaml` / `reg-cond-assign.yaml` / `reg-imm-block.yaml` / `reg-logic.yaml` / `reg-shift-extend.yaml` 中含规则引用的用例），产物与仓库一致；**不得**全量重跑破坏既有预存漂移（见 `issues.yaml ISS-125`）。

（原「位宽主引用」「`swym` 指向 `SimRISC-11`」部分已完成，见头部「处置」，不重复。）

## 约束

- **改生成器，不改产物**
- 逐条核对，禁止正则批量替换
- 不改动向量的 word/input_state/expected 等语义字段

## 验收标准

1. 向量中不再出现陈旧规则引用：`SimRISC-01 §rd0 为目的寄存器约定` / `SimRISC-01 §加减操作` / `SimRISC-02 §rb0 为目的寄存器约定` 条数 = **0**（实测当前分别为 **87 / 6 / 6** 条：`§rd0` 分布 reg-arith 35 + reg-compare 11 + reg-cond-assign 5 + reg-imm-block 4 + reg-logic 4 + reg-shift-extend 28；`§加减操作` 在 reg-arith 6；`§rb0` 分布 reg-arith 3 + reg-imm-block 3）。
2. 受影响向量中的规则引用与 `contracts/legality_rules.yaml` 的 `dst_rd0`/`dst_dual_same`/`dst_rb0` 逐条一致（独立复算，非抽样）。
3. `python3 tools/testcases/validate_vectors.py` EXIT=0（**152/152**，gaps 0）。
4. `make check` **EXIT=0**；`check-legality-drift` 不回归。
5. 向量的语义字段（`word`/`input_state`/`expected_state`）**逐字节未改**（`git diff` 只含 `spec_cite` 行）。
6. `git diff --name-only` 只含 `tools/testcases/generate_isa_vectors.py` 与受影响向量文件（**不误伤** 4 个预存漂移文件，见 `ISS-125`）。
7. 一键证据脚本：非交互、任一失败即非零退出、逐项打印「检查名 + 期望/实际 + 退出码」+ 注入反例自检（如把 `dst_rd0` 改回陈旧值 → 自检 FAIL）。落点 `.work/evidence/TESTCASES-014t/`。

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