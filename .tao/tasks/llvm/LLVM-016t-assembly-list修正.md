# LLVM-016t: assembly-list 生成器修正（feature 错误 + header 条数）

**模块**：llvm
**项目里程碑**：M1→M2
**依赖**：无
**状态**：待开始

## 问题描述

`docs/assembly-list.md`（由 `tools/llvm/gen_asm_list.py` 生成）存在两类缺陷：

### G1. 6 条 id 错误（feature 重算错误）

同一 id 对应多个汇编形式（重复）：

| 错误 id | 汇编形式 | 正确 id |
|---------|---------|---------|
| `cmp.uo_orrr_rd` | `cmp.uo rdHB, rbHC, rbHD` | `cmp.uo_orrr_rb` |
| `cs.eq_rrrr_rd` | `cs.eq {rdHA,rdHB}?, rfHC, rfHD` | `cs.eq_rrrr_rf` |
| `cs.n_rrrr_rd` | `cs.n {rdHA}?, rfHB, rfHC, rfHD` | `cs.n_rrrr_rf` |
| `cs.ne_rrrr_rd` | `cs.ne {rdHA,rdHB}?, rfHC, rfHD` | `cs.ne_rrrr_rf` |
| `cs.p_rrrr_rd` | `cs.p {rdHA}?, rfHB, rfHC, rfHD` | `cs.p_rrrr_rf` |
| `cs.z_rrrr_rd` | `cs.z {rdHA}?, rfHB, rfHC, rfHD` | `cs.z_rrrr_rf` |

**根因**：`gen_asm_list.py:119` 按旧 `insn` 格式（`cs.ne-rd`）解析 feature；SPEC-024t 改为 `id` 后失效 → 按 dst 寄存器组重算得 `rd`。

**修法**：`id` 直接取自 `opcodes.yaml` 的 `id` 字段（权威），不再重算 feature。

### G6. header 条数陈旧

`docs/assembly-list.md` + `gen_asm_list.py`：写「256 条 = M1 178 + `excluded_m1` 78」→ 应「254 条 = M1 178 + `excluded_m1` 76」。

## 修改内容

### 1. tools/llvm/gen_asm_list.py

- `primary_feature()` / id 构造：改为直接用 `entry["id"]`（opcodes.yaml 权威值），不再重算
- 删除或修正 `FEATURE_OVERRIDE` 等不再需要的重算逻辑（若仍用于其它用途，保留但确保 id 用权威值）
- L9-10 docstring、L391、L433：条数「256/178/78」→「254/178/76」；移除 docstring 中的 `role` 提法（若已过时）

### 2. 重生成

```
python3 tools/llvm/gen_asm_list.py -o docs/assembly-list.md
```

## 约束

- **改生成器，不改产物**（产物随生成器重生成）
- 逐条核对，禁止正则批量替换
- 只改 feature 来源与条数表述，不改分类/顺序

## 验收标准

1. `docs/assembly-list.md` 中无重复 id（6 个错误全部消除）
2. `assembly-list.md` 的每个 id 与 `opcodes.yaml` 的 id 集合一致
3. header 写「254 条 = M1 178 + `excluded_m1` 76」
4. 生成器重跑输出与仓库文件逐字节一致
5. 无 256/78 残留

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