# TESTCASES-017t: 向量 schema `insn` → `id`（主键简化为 id）

**模块**：testcases
**项目里程碑**：M1→M2
**依赖**：无
**状态**：待开始

## 问题描述

向量 schema 的字段名与语义已不一致：

- 向量 YAML 的字段名是 `insn`，但**值已是 `id`**（`mnemonic_format_feature`，如 `add.uo_rrrr_rd`）
- `tests/vectors/inventory.md` 用 `(id, format)` 主键
- `tests/vectors/schema.md` 仍描述 `insn` 为「对应 `opcodes.yaml` 的 `insn`；**单独不唯一**」（旧语义）

且 `opcodes.yaml` 的 `id` 已**单独唯一**（254/254）→ 复合主键 `(id, format)` 中的 `format` 冗余。

## 用户裁定（2026-09-29）

1. 字段名 **`insn` → `id`**
2. 覆盖率主键 **`(id, format)` → `id`**（简化；`format` 保留为普通字段，不再入键）

## 修改内容

### 1. 向量数据（`tests/vectors/isa/*.yaml`，14 文件）

- 字段 `insn:` → `id:`
- 保留 `format` 字段（数据，不入键）

### 2. `tests/vectors/schema.md`

- 更新字段表：`id`（对应 `contracts/opcodes.yaml` 的 `id`，**唯一**）
- 覆盖率主键：`(insn, format)` → **`id`**
- 更新示例（含 `ld.ub-rd` → `ld.ub_rrii_rd` 等旧示例）

### 3. `tests/vectors/inventory.md`

- 主键口径统一为 `id`

### 4. `tools/testcases/`

- `validate_vectors.py`：读 `id`；覆盖率/唯一性检查按 `id`（不再 `(insn,format)`）
- `generate_isa_vectors.py` / `generate_mem_vectors.py` / `generate_ctrl_br.py` / `generate_ctrl_jump_call_ret.py` / `generate_misc.py`：写出 `id`；`FILE_MAP`/`BY_KEY` 等按 `id`
- `009t-audit.py`：按 `id`

### 5. 消费方同步（跨模块）

- `tools/llvm/check_lit_bytes.py`（若读向量 `insn`）
- `tools/qemu/check_qemu_trans.py`、`check_005t_coverage.py`（若读向量 `insn`）
- `tests/scripts/run_qemu_test.py`（`case.get("insn")` → `case.get("id")`）
- `tools/integ/check_interface_alignment.py`（若校验向量字段）

## 约束

- **改名 + 主键简化**；**不改向量语义**（word/input_state/expected 不变）
- 生成器同步后须**可复现**（重跑无 diff）
- 逐条核对，禁止正则批量替换
- 完成后 `make check` EXIT=0

## 验收标准

1. 向量中无 `insn:` 字段（改为 `id:`）
2. `schema.md`/`inventory.md` 主键口径为 `id`
3. `python3 tools/testcases/validate_vectors.py` EXIT=0（178/178）
4. 生成器重跑与已提交向量**逐字节一致**（幂等）
5. 消费方（llvm/qemu/harness）均按 `id` 读取，无 `insn` 残留
6. `make check` EXIT=0
7. 反例验证（注入错 `id` → validator/覆盖率检查失败）

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