# TESTCASES-020t: RA 向量重写（ADR-0012 D7）

**模块**：testcases
**项目里程碑**：M2（**本任务推翻 M1 已验收的 RA 向量期望值**）
**依赖**：`ADR-0012 D7`（已固化）；`SPEC-062t`（规范基线，**须先定稿**）；E2E 执行需 `QEMU-030t`（**本任务只产出向量 + 结构性校验**）
**状态**：待开始（**未下发**）

## 背景

`ADR-0012 D7` 改变了 RA 语义（`RACNT`/`MRPTR`、有效性判据、递归折叠、MemRAS 无引用计数）。现有向量的期望值**按旧语义编写**，且用旧机制构造场景，必须重写：

| 现状 | 问题 |
|---|---|
| `tests/vectors/isa/ctrl-call.yaml`（223 行，**22 处**期望值含高 16 计数） | 有效性机制改为 `RACNT`；压栈流程改 C1–C3b |
| `tests/vectors/isa/ctrl-ret.yaml`（42 行，2 处） | 弹栈流程改 D1–D4b |
| 两文件的"满栈"构造：`pre-set ra1–ra63（高16=0x0001）使其有效` | **D7 下无效**——有效性由 `ra0[53:48]`(`RACNT`) 判定，pre-set 条目高 16 **不**使其有效 |
| `grep -rn MemRAS tests/vectors/` → **0 命中** | **MemRAS 路径向量层零覆盖**（D7 前由探针 `013t` 承担） |

**生成器**：`tools/testcases/generate_ctrl_jump_call_ret.py`（产物即上述两个 yaml）。

## 修改内容

1. **改生成器** `tools/testcases/generate_ctrl_jump_call_ret.py`：按 D7 的 C1–C3b / D1–D4b 重新派生期望值；
2. **重新生成** `tests/vectors/isa/ctrl-call.yaml`、`ctrl-ret.yaml`；
3. **新增 MemRAS 用例**（`ra0[53:48] = RACNT ≠ 0`、`ra0[47:0] = MRPTR`）：至少覆盖 **C3b**（满栈溢出到 MemRAS）与 **D4b**（从 MemRAS restore：条目递归计数 = 1 / > 1 / = 0→RASUF 三种）；
4. **满栈构造一律改用** `ra0[53:48] = 63`（+ 相应条目内容），不得再用"pre-set 条目高16=0x0001"；
5. 每个用例的 `notes` 标注 **spec 来源章节**（`SimRISC-00 §返回地址栈` / `SimRISC-06 §call|§ret`）。

## 约束

- **Independent oracle**：期望值**独立派生自 `spec/`**，**严禁**从 QEMU 实现（`trans_ctrl.c.inc`）反推；改生成器期间**不得**打开 QEMU 实现。
- **只改**：`tests/vectors/isa/ctrl-call.yaml`、`ctrl-ret.yaml`、`tools/testcases/generate_ctrl_jump_call_ret.py`（如需，可补 `tests/vectors/README.md` 的说明）。
- **不改**：`spec/`、`contracts/`、`components/qemu/`、其它向量。
- 命令缺失/失败 → **停下报告**；反例注入须可复原。
- 完成区须说明：**E2E 执行依赖 `QEMU-030t`**，本任务只保证结构校验与独立重算。

## 验收标准

1. **生成器 ↔ 产物一致**：重跑生成器 → `git diff` 为空（给出命令与输出）。
2. **独立全量重算（关键）**：对全部 `semantic`/`boundary` 用例**逐条**独立重算 `RACNT`、`MRPTR`、`ra63`/条目内容、fault 判定，并与产物比对——**不得抽样**；给出逐条对照表。
3. **MemRAS 覆盖**：`grep -n "MemRAS\|ra0" tests/vectors/isa/ctrl-*.yaml` 显示 C3b 与 D4b 用例存在；`MRPTR`/`RACNT` 期望值可核。
4. **无旧机制残留**：`grep -n "0x0001" tests/vectors/isa/ctrl-call.yaml` 中用于"使条目有效"的用法清零（给出说明）。
5. `python3 tools/testcases/validate_vectors.py` **EXIT=0**；`make check` **EXIT=0**（真实退出码，`cmd > log 2>&1; rc=$?`）。
6. **反例门控**：/tmp 副本注入 (a) 把某用例的 `RACNT` 期望值改错 (b) 把 C3b 的溢出条目改错 (c) 删一个 D4b 用例 —— `validate_vectors.py` 或独立重算脚本 **FAIL**；复原后 PASS。
7. **未触其它文件**：`git diff --name-only` 与清单逐项对齐。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
