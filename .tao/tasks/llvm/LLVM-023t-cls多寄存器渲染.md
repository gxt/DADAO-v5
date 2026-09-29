# LLVM-023t: cls 多寄存器渲染（生成器 + 重生成）

**模块**：llvm
**项目里程碑**：M1→M2
**依赖**：无
**状态**：待开始

## 问题描述

`SPEC-040t` 已把 `spec/SimRISC-07-浮点运算.md` **§浮点分类指令**（正文）改为多寄存器（组记法），但**生成区**仍是旧格式：

- `spec/SimRISC-07` 内嵌速查表（`<!-- ASSEMBLY_LIST_START/END -->`）：`focls rdHB, rfHC, immu6` / `ftcls rdHB, rfHC, immu6`
- `docs/assembly-list.md:179,198`：同上

根因：`tools/llvm/gen_asm_list.py` 的**多寄存器渲染列表**（`_MULTI_REG_MNEMONICS`）**不含 `focls`/`ftcls`** → 未按 `{start:end}` 组记法渲染。

**用户裁定（2026-09-29）**：cls 端到端改完（含生成器 + 重生成）。

## 修改内容

1. `tools/llvm/gen_asm_list.py`：把 **`focls`/`ftcls`** 加入 `_MULTI_REG_MNEMONICS`（与 `ft2fo` 等 20 条转换同款）→ 渲染为：
   ```
   focls {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}
   ftcls {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}
   ```
2. **重生成**：`docs/assembly-list.md` + 12 个 spec 内嵌速查表（`--embed-spec`）
3. 确认 `spec/SimRISC-07` 正文（`SPEC-040t` 已改）与生成表**一致**

## 约束

- 只加 `focls`/`ftcls` 到多寄存器渲染；不改其他渲染
- **`contracts/opcodes.yaml` 无需改**（fields 已是 rdhb/rfhc/immu6；assembly form 由生成器派生）——若确需改请说明
- 逐条核对；命令缺失/构建失败 → 停下报告，禁止自行安装/下载
- 完成后 `make check` EXIT=0（含 `check-asm-list-consistency`）

## 验收标准

1. `docs/assembly-list.md` 的 `focls`/`ftcls` 行为组记法 `{rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}`
2. `spec/SimRISC-07` 内嵌速查表的 `focls`/`ftcls` 同步
3. 正文（SPEC-040t）与生成表一致
4. 生成器**幂等**（重跑无 diff）；其他 252 条渲染不变
5. `make check` EXIT=0
6. 反例验证（移除 focls 渲染 → 回退旧格式可检出）

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