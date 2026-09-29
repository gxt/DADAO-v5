# SPEC-041t: SimRISC-01（取数存数）正文改为新汇编格式

**模块**：spec
**项目里程碑**：M1→M2
**依赖**：`ADR-0013`（语法冻结）、`docs/spec/assembly-language.md` v1.1、`tools/llvm/gen_asm_list.py`、内嵌速查表（生成区）
**状态**：待开始

## 背景与目标

`spec/SimRISC-XX-*.md` 正文里的指令书写仍是**旧字段级小写记法**（如 `ld.sb rdha, rbhb, imms12`），与文件内**生成区速查表**（`ld.sb rdHA, [rbHB, imms12]`）不一致。

**用户裁定（2026-09-29）**：已有的指令书写内容**全部改为新汇编格式**（`ADR-0013` D1–D7 / `assembly-language.md` v1.1），**按指令类别逐章**推进。本任务是**第 1 章：取数存数**。

## 权威来源（转换目标）

每条指令的「新汇编形式」= `tools/llvm/gen_asm_list.py::new_form(entry, ops, field=True)` 的输出，即**同文件内嵌速查表「汇编形式」列**（生成区）。**逐条以生成表为准**，不得自行发明。

## 修改范围（仅 `spec/SimRISC-01-取数存数.md`）

### 规则

1. **寄存器字段名小写 → 大写占位**：`rdha→rdHA`、`rbhb→rbHB`、`rdhc→rdHC`、`rbha→rbHA`、`raha→raHA`、`rfha→rfHA`
2. **访存地址 → `[...]`**：`ld.sb rdha, rbhb, imms12` → `ld.sb rdHA, [rbHB, imms12]`
3. **多寄存器（`ldm`/`stm`，`rrri`）→ 组记法**：`ldm.sb rdha, rbhb, rdhc, immu6` → `ldm.sb {rdHA:rdHA+immu6-1}, [rbHB, rdHC]`；`stm.b ...` 同款（组为**源**寄存器范围）
4. **立即数原样**：`imms12`（访存偏移，单位字节，**无 `i` 后缀**）、`immu6` 原样
5. **正文中的内联指令示例**同步转换：`stm.b rd16, rb2, rd0, 8` → `stm.b {rd16:rd23}, [rb2, rd0]`
6. **正文中的字段名引用**同步大写：`rdha`→`rdHA`、`rbhb+rdhc`→`[rbHB, rdHC]` 等（保持前后一致）

### 5 个代码块（` ```simrisc `）逐块转换

| 块（行） | 段 | 转换 |
|---|---|---|
| 67–80 | 存取RD-单 | `ld.*/st.* rdha, rbhb, imms12` → `... rdHA, [rbHB, imms12]` |
| 88–101 | 存取RD-多 | `ldm.*/stm.* rdha, rbhb, rdhc, immu6` → `{rdHA:rdHA+immu6-1}, [rbHB, rdHC]` |
| 121–127 | 存取RB | `rbha` → `rbHA`；余同上 |
| 142–148 | 存取RA | `raha` → `raHA`；余同上 |
| 161–171 | 存取RF | `rfha` → `rfHA`；余同上 |

### 正文引用（行 82–181）

`rdha`/`rbha`/`raha`/`rfha`/`rbhb`/`rdhc` 等在「限制」列表与说明中的引用 → 大写；行 106 的 `stm.b rd16, rb2, rd0, 8` → `stm.b {rd16:rd23}, [rb2, rd0]`。

## 约束

- **只改 `spec/SimRISC-01-取数存数.md`**；不改生成器 / `contracts/` / `docs/` 其它文件
- **不改语义**：仅记法/标点（`[...]`/`{...}`/大小写）；数值、寄存器范围、限制条文一字不动
- **不改生成区**（`<!-- ASSEMBLY_LIST_START/END -->` 之间）；只改正文
- 逐条核对，禁止正则批量替换后不复查

## 验收标准

1. 5 个代码块全部为新汇编格式（`[...]` 地址、`{start:start+immu6-1}` 组）
2. 正文内联指令示例/字段名引用一致大写
3. **语义零变化**（数值/限制/寄存器范围逐条比对，与 HEAD 版一致）
4. **不改生成区**：`git diff` 命中行全部在 `ASSEMBLY_LIST` 区之外（给出证据）
5. 每个新形式与**内嵌速查表「汇编形式」列**（或 `docs/assembly-list.md`）**逐条相符**（给出对照证据）
6. 反例验证：注入一处回退（如把某行改回 `rdha`）→ 检查可检出；复原后无残留
7. `make check` EXIT=0

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
