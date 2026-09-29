# TESTCASES-018t: 向量 notes 文本笔误订正

**模块**：testcases
**项目里程碑**：M1→M2
**依赖**：无
**状态**：待开始

## 问题描述（来自 `deferred.md`）

- **notes 文本笔误**（`006t` 遗留 N-1）：`ctrl-call.yaml` case[7] 与 `generate_ctrl_jump_call_ret.py` 的 notes 写「low 48=**0xAAAA000000000000**」（**多 4 个 0**），实际 `low48 = 0xAAAA00000000`（12 位十六进制 = 48 位）。**数值全部正确**、重算 0 mismatch；纯文本笔误。

## 修改内容

1. `tools/testcases/generate_ctrl_jump_call_ret.py`：notes 的 `0xAAAA000000000000` → `0xAAAA00000000`
2. 重新生成 `tests/vectors/isa/ctrl-call.yaml`（确认仅该文本变化）

## 约束

- 只改该文本；**不动任何编码/期望值/其他 notes**
- 生成器重跑须幂等（重跑无 diff）
- 完成后 `make check` EXIT=0；`validate_vectors` 178/178

## 验收标准

1. notes 中的 `low 48` 数值为 `0xAAAA00000000`（48 位）
2. 向量语义未变（`ctrl-call.yaml` 逐 case 比对仅该文本差异）
3. 生成器幂等；`validate_vectors` EXIT=0；`make check` EXIT=0

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