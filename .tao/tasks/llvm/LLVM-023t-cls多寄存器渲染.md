# LLVM-023t: cls 多寄存器渲染（生成器 + 重生成）

**模块**：llvm
**项目里程碑**：M1→M2
**依赖**：无
**状态**：已验证

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
**测试结果**：通过 6/6；全部验收标准满足
**修改文件**：
- `tools/llvm/gen_asm_list.py` — `_MULTI_REG_MNEMONICS` 加入 `focls`/`ftcls`（+2行）
- `docs/assembly-list.md` — 重生成，仅 cls 2行变更
- `spec/SimRISC-07-浮点运算.md` — 重生成嵌入表，仅 cls 2行变更

**验收结果**：
1. `docs/assembly-list.md` 行 179,198：`focls {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` / `ftcls {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` ✅
2. `spec/SimRISC-07` 嵌入表行 20,39：同步 ✅
3. 正文（SPEC-040t 行 205-206）与生成表一致 ✅
4. 幂等：重跑2次无新 diff ✅；其他252 条 `git diff` 仅见 cls 行 ✅
5. `make check` EXIT=0（含 `check-asm-list-consistency: 12 spec files OK`）✅
6. 反例验证：移除 `focls` 后回退为旧格式 `focls rdHB, rfHC, immu6`；还原后 `git diff` 确认仅新增2行 ✅

**新发现/坑**：无
**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：`tools/llvm/gen_asm_list.py` +2行，`docs/assembly-list.md` cls 2行变更，`spec/SimRISC-07-浮点运算.md` cls 2行变更

**逐项核验**：
1. `focls`/`ftcls` 在 `opcodes.yaml` 中为 `orri` 格式，字段 `rdhb`(dst/rd) + `rfhc`(src/rf) + `immu6` — 与现有 `_MULTI_REG_MNEMONICS` 中的转换指令完全同构 ✅
2. `_MULTI_REG_MNEMONICS` 新增2条，总数30 — 注释 `# 浮点分类（2 条）` 正确 ✅
3. `new_form()` 多寄存器分支：`reg_ops[0]`=dst(`rdhb`→`rdHB`), `reg_ops[1]`=src(`rfhc`→`rfHC`) → `{rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` ✅
4. `example_line()` 同路径 → 示例渲染 `{rd8:rd10}, {rf2:rf4}` ✅
5. 幂等：重跑2次，`git diff --stat` 不变 ✅
6. 其他252 条：diff 仅含 cls 行，`foadd`/`fodiv`/`ftadd`/`ftdiv` 等相邻条目不变 ✅
7. 反例注入+还原：移除→回退旧格式→还原→确认无残留 ✅

**Finding**：无

**判决**：通过，标「待验收」

#### 第 1 轮 reviewer 验收

**审查范围**：`tools/llvm/gen_asm_list.py`（+2 行）、`docs/assembly-list.md`（2 行）、`spec/SimRISC-07-浮点运算.md`（2 行）；`contracts/opcodes.yaml`。

**重跑记录（本人终端真实输出/退出码）**

1. 生成器重跑：
   ```
   $ python3 tools/llvm/gen_asm_list.py ; echo EXIT=$?
   gen-asm-list: 254 entries -> /home/ubuntu/DADAO-v5/docs/assembly-list.md
   EXIT=0
   $ python3 tools/llvm/gen_asm_list.py --embed-spec ; echo EXIT=$?
   gen-asm-list: embedded 取数存数（38 条）... 待定（12 条）  # 12 个 spec 全部写出
   EXIT=0
   ```
2. 幂等：重跑 2 次（主表 + embed-spec），文件 sha256 **完全不变**：
   - `gen_asm_list.py` `a0e08426…9210`
   - `docs/assembly-list.md` `a2af399e…cebf`
   - `spec/SimRISC-07-浮点运算.md` `46b19b8f…7cb1`
   第 2 次重跑后 `git diff --stat` 与首次一致。
3. `docs/assembly-list.md` vs HEAD 逐行 diff（`git diff -U0`）：**仅 2 条变更**：
   ```
   -| `focls` | … | `focls rdHB, rfHC, immu6` |
   +| `focls` | … | `focls {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` |
   -| `ftcls` | … | `ftcls rdHB, rfHC, immu6` |
   +| `ftcls` | … | `ftcls {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` |
   ```
   `git diff --numstat` = `2 2`（即其余 252 条渲染未变）；实际行号 **179（focls）/198（ftcls）**，与任务书一致。
4. `spec/SimRISC-07` 内嵌速查表（`<!-- ASSEMBLY_LIST_START/END -->`）行 **20（focls）/39（ftcls）** 同步为组记法（`grep -n` 实测）。
5. `make check`：`EXIT=0`，含 `check-asm-list-consistency: 12 spec files OK`、`repository checks: PASS`。
6. `contracts/opcodes.yaml`：`git diff --name-only -- contracts/opcodes.yaml` 输出为空 → **未改**。核对字段：`ftcls`/`focls` 为 `orri`，`rdhb`(role=dst,bank=rd) + `rfhc`(role=src,bank=rf) + `immu6` → 生成组记法起点 `rdHB`/`rfHC` 正确。
7. 正文（SPEC-040t）行 205-206 形式 `{rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` 与生成表**一致**（正文示例行 209 `focls rd4, rf8, 3` 用显式个数的写法，与同章 `ft2fo rf4, rf8, 3` 同款约定，非缺陷）。

**反例验证（可检出 + 可复原）**

- 注入：`sed -i` 从 `_MULTI_REG_MNEMONICS` 删除 `"focls", "ftcls",`；`git diff --name-only` 非空（确认注入生效）。
- 检出：`python3 tools/spec/check_asm_list_consistency.py` → **EXIT=1**：
  ```
  FAIL: 浮点运算: content mismatch in SimRISC-07-浮点运算.md
  1 inconsistency(ies) found, 11 OK
  ```
  `make check-asm-list` → EXIT=2（Error 1）。
- 回退可检出：注入后重生成 `docs/assembly-list.md` → 两条**回退旧格式** `focls rdHB, rfHC, immu6` / `ftcls rdHB, rfHC, immu6`。
- 复原：从备份恢复生成器 → `sha256sum -c` OK → 重跑主表 + `--embed-spec` → 4 个被审文件哈希与注入前 `diff` **IDENTICAL**，`git diff --stat`/`git status` 无残留（仅 4 个预期文件）。

**约束核验**

- 只加 `focls`/`ftcls` 到多寄存器渲染；不改其他渲染 —— ✅（生成器 diff 仅 +2 行；docs diff 仅 2 条）
- `contracts/opcodes.yaml` 未改 —— ✅
- 完成后 `make check` EXIT=0（含 `check-asm-list-consistency`）—— ✅
- 命令缺失/构建失败即停下 —— ✅（无缺失；全程未安装/下载）

**判决：Accepted**

- 验收标准 1-6 均在本人独立重跑下通过；约束无违反；反例证明该项改动确实被 `check-asm-list-consistency` 门控覆盖，且注入已完全复原。
- 无阻断性问题。