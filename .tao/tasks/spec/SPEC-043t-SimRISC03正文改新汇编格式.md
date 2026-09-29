# SPEC-043t: SimRISC-03（16位立即数操作）正文改为新汇编格式

**模块**：spec
**项目里程碑**：M1→M2
**依赖**：`ADR-0013`、`docs/spec/assembly-language.md` v1.1、`tools/llvm/gen_asm_list.py`、内嵌速查表（生成区）；前置 `SPEC-041t`/`SPEC-042t`
**状态**：待开始

## 背景与目标

第 1、2 章已完成。本任务处理**第 3 章：16位立即数操作**（`set.zw`/`set.ow`/`set.w`/`or.w`/`andn.w`，8 条 `rwii`）+ 4 组伪指令展开示例。

## 修改范围（仅 `spec/SimRISC-03-16位立即数操作.md`）

### A. `rwii` 真指令（块 31–36 / 47–51 / 55–57）

| 旧 | 新 |
|---|---|
| `set.ow   rdha, wpN, immu16` | `set.ow   rdHA, wpN, immu16` |
| `set.zw   rdha, wpN, immu16` | `set.zw   rdHA, wpN, immu16` |
| `or.w     rdha, wpN, immu16` | `or.w     rdHA, wpN, immu16` |
| `andn.w   rdha, wpN, immu16` | `andn.w   rdHA, wpN, immu16` |
| `set.zw  rbha, wpN, immu16` | `set.zw  rbHA, wpN, immu16` |
| `or.w    rbha, wpN, immu16` | `or.w    rbHA, wpN, immu16` |
| `andn.w  rbha, wpN, immu16` | `andn.w  rbHA, wpN, immu16` |
| `set.w    rfha, wpN, immu16` | `set.w    rfHA, wpN, immu16` |

（`wpN`/`immu16` 原样，见生成表「汇编形式」列）

### B. 伪指令展开示例中的**块赋值/格式转换**（真指令，多寄存器组记法）

`set.rd`/`set.rb`/`set.ft`/`set.fo` 的展开注释里出现的真指令是 **旧 3 操作数形式**（`X, Y, 1`），须改为**新组记法**。`immu6=1` → **单寄存器组，不带冒号**（`assembly-language.md` §4 第 97 行、§5 速查表 `{reg}` count=1）。

| 位置 | 旧 | 新 |
|---|---|---|
| 111 | `展开为 rb2rd rd5, rb3, 1` | `展开为 rb2rd {rd5}, {rb3}` |
| 112 | `展开为 rf2rd rd2, rf7, 1` | `展开为 rf2rd {rd2}, {rf7}` |
| 113 | `展开为 rd2rd rd8, rd3, 1` | `展开为 rd2rd {rd8}, {rd3}` |
| 114 | `展开为 ra2rd rd4, ra10, 1` | `展开为 ra2rd {rd4}, {ra10}` |
| 137 | `展开为 rd2rb rb5, rd3, 1` | `展开为 rd2rb {rb5}, {rd3}` |
| 138 | `展开为 rb2rb rb2, rb7, 1` | `展开为 rb2rb {rb2}, {rb7}` |
| 161 | `展开为 rd2rf rf1, rd0, 1` | `展开为 rd2rf {rf1}, {rd0}` |
| 162 | `展开为 rd2rf rf1, rd0, 1` | `展开为 rd2rf {rf1}, {rd0}` |
| 168 | `展开为 rd2rf rf1, rd5, 1` | `展开为 rd2rf {rf1}, {rd5}` |
| 169 | `展开为 ft2ft rf1, rf2, 1` | `展开为 ft2ft {rf1}, {rf2}` |
| 170 | `展开为 fo2fo rf2, rf7, 1` | `展开为 fo2fo {rf2}, {rf7}` |

> **注意**：`X2Y` 的组顺序为**目的在前、源在后**，以生成表「汇编形式」列（`rd2rf {rfHB:…}, {rdHC:…}` 等）为准，**逐条核对**，不得仅按本表盲改。

### C. 其余展开注释（`set.zw`/`set.ow`/`or.w`/`set.w`，已具体寄存器）

如 `; 展开为 set.zw rd1, wp0, 0` —— 已是新格式（具体寄存器），**保持**；仅需确认无小写字段名残留。

### D. 正文引用

字段名引用大写：`rdha`→`rdHA`、`rfha`→`rfHA` 等；行 42 注中的 `or.w rdhb, rdhc, rdhd` → `or.w rdHB, rdHC, rdHD`。

## 约束

- **只改 `spec/SimRISC-03-16位立即数操作.md`**；不改生成器 / `contracts/` / `docs/`
- **不改生成区**（`<!-- ASSEMBLY_LIST_START/END -->`，本文件行 6–22）
- **语义零变化**：仅记法/标点；数值（`0x1234`/`-42`/`0xDEAD…` 等）、限制条文一字不动
- **伪指令的调用写法不改**（`set.rd rd5, rb3` 等，非硬件指令，不在速查表内）
- 逐条核对，禁止正则批量替换后不复查

## 验收标准

1. A 段 8 条真指令为新格式（`rdHA`/`rbHA`/`rfHA`，`wpN`/`immu16` 原样）
2. B 段 11 处展开注释为 `{reg}, {reg}` 单元素组（**无冒号**；目的/源顺序与生成表相符）
3. C 段具体寄存器注释未被误改
4. 正文引用大写、无小写字段名残留
5. **语义零变化**（逐 hunk；数值/条文未动）
6. **不改生成区**（证据：命中行号 > `ASSEMBLY_LIST_END`）
7. 与生成表「汇编形式」列**逐条相符**（独立复算；A 段 8 条 + B 段 11 条对照）
8. 反例验证：注入一处回退（如 B 段写成 `{rd5:rd5}` 或改回 `rd5, rb3, 1`）→ 检查可检出；复原后无残留
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
