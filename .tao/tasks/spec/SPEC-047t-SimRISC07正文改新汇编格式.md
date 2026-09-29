# SPEC-047t: SimRISC-07（浮点运算）正文改为新汇编格式

**模块**：spec
**项目里程碑**：M1→M2
**依赖**：`ADR-0013`、`assembly-language.md` v1.1、`tools/llvm/gen_asm_list.py`、内嵌速查表；前置 `SPEC-041t`…`046t`、`SPEC-040t`（cls 正文）、`LLVM-023t`（cls 生成表）
**状态**：待开始

## 背景

`cls`（§浮点分类）已由 `SPEC-040t`+`LLVM-023t` 改为多寄存器组记法。本任务转换第 7 章**其余**代码块与正文引用。

## 修改范围（仅 `spec/SimRISC-07-浮点运算.md`）

### A. 块 69–93（格式转换，`orri` 多寄存器，双组）

**目的/源寄存器组以生成表为准**（见 `docs/assembly-list.md` 172–217 行）：

| 旧 | 新 |
|---|---|
| `ft2fo   rfhb, rfhc, immu6` | `ft2fo   {rfHB:rfHB+immu6-1}, {rfHC:rfHC+immu6-1}` |
| `fo2ft   rfhb, rfhc, immu6` | `fo2ft   {rfHB:rfHB+immu6-1}, {rfHC:rfHC+immu6-1}` |
| `ft2ft   rfhb, rfhc, immu6` | `ft2ft   {rfHB:rfHB+immu6-1}, {rfHC:rfHC+immu6-1}` |
| `fo2fo   rfhb, rfhc, immu6` | `fo2fo   {rfHB:rfHB+immu6-1}, {rfHC:rfHC+immu6-1}` |
| `ft2it   rdhb, rfhc, immu6` | `ft2it   {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` |
| `ft2io   rdhb, rfhc, immu6` | `ft2io   {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` |
| `ft2ut   rdhb, rfhc, immu6` | `ft2ut   {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` |
| `ft2uo   rdhb, rfhc, immu6` | `ft2uo   {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` |
| `it2ft   rfhb, rdhc, immu6` | `it2ft   {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}` |
| `io2ft   rfhb, rdhc, immu6` | `io2ft   {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}` |
| `ut2ft   rfhb, rdhc, immu6` | `ut2ft   {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}` |
| `uo2ft   rfhb, rdhc, immu6` | `uo2ft   {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}` |
| `fo2it   rdhb, rfhc, immu6` | `fo2it   {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` |
| `fo2io   rdhb, rfhc, immu6` | `fo2io   {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` |
| `fo2ut   rdhb, rfhc, immu6` | `fo2ut   {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` |
| `fo2uo   rdhb, rfhc, immu6` | `fo2uo   {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` |
| `it2fo   rfhb, rdhc, immu6` | `it2fo   {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}` |
| `io2fo   rfhb, rdhc, immu6` | `io2fo   {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}` |
| `ut2fo   rfhb, rdhc, immu6` | `ut2fo   {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}` |
| `uo2fo   rfhb, rdhc, immu6` | `uo2fo   {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}` |

（注释 `; 浮点寄存器间搬移` 保留）

### B. 其余代码块

| 块 | 旧 | 新 |
|---|---|---|
| 114–126（`orrr`） | `ftadd   rfhb, rfhc, rfhd` 等 12 条 | `ftadd   rfHB, rfHC, rfHD`（平铺，无花括号） |
| 140–144（`orri`，**非**多寄存器） | `ftroot  rfhb, rfhc, immu6` 等 4 条 | `ftroot  rfHB, rfHC, immu6`（`immu6`=根次/底，**不加组记法**） |
| 160–163（`orrr`） | `ftsgnj  rfhb, rfhc, rfhd` 等 4 条 | `ftsgnj  rfHB, rfHC, rfHD` |
| 184–188（`orrr`） | `ftqcmp  rdhb, rfhc, rfhd` 等 4 条 | `ftqcmp  rdHB, rfHC, rfHD`（dest=rd） |

### C. 正文内联示例（**旧 3 操作数形式** → 新组记法）

| 位置 | 旧 | 新 |
|---|---|---|
| 96 | `ft2fo rf4, rf8, 3` | `ft2fo {rf4:rf6}, {rf8:rf10}` |
| 209 | `focls rd4, rf8, 3` | `focls {rd4:rd6}, {rf8:rf10}` |

（对应文字「将 rf8→rf4、rf9→rf5、rf10→rf6」「对 rf8、rf9、rf10 分类，结果分别写入 rd4、rd5、rd6」保持不变）

### D. 正文散文引用

`rfhb`/`rfhc`/`rfhd`/`rdhb` → `rfHB`/`rfHC`/`rfHD`/`rdHB`（含行 96、129、131、133、147、149、151、153、166–168、174–177、181、191、198、209、211 等）。具体寄存器（`rf0`/`rd4`/`rf8` 等）保持。

## 约束

- **只改 `spec/SimRISC-07-浮点运算.md`**；不改生成器 / `contracts/` / `docs/`
- **不改生成区**（`<!-- ASSEMBLY_LIST_START/END -->`，本文件行 6–60）
- **语义零变化**：IEEE754 语义、数值、限制条文一字不动
- 逐条核对；命令缺失 → 停下报告，禁止自行安装

## 验收标准

1. A 段 20 条格式转换 = 双组组记法，**目的/源组与生成表逐条相符**（写脚本反推组校验，非字符串等值）
2. B 段 24 条平铺（`orrr`/`orri`）；`ftroot`/`ftlog`/`foroot`/`folog` 的 `immu6` **不加**组记法
3. C 段 2 处内联示例改为组记法
4. D 段引用大写；具体寄存器未误改
5. **语义零变化**（逐 hunk）
6. **不改生成区**（命中行号 > 60）
7. 与生成表「汇编形式」列逐条相符（独立复算）
8. 反例验证：注入一处回退（如 `ftroot` 误加组记法、`it2ft` 目的/源组对调、C 段写回旧 3 操作数）→ 检查可检出；复原后无残留
9. `make check` EXIT=0

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
