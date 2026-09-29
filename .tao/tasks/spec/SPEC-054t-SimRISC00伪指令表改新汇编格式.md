# SPEC-054t: SimRISC-00 伪指令表改为新汇编格式

**模块**：spec
**项目里程碑**：M1→M2
**依赖**：`ADR-0013`（含 D8）、`assembly-language.md` v1.1、生成表；前置 `SPEC-041t`…`053t`
**状态**：待开始

## 背景

全库终检发现 `spec/SimRISC-00-指令系统设计.md` §伪指令 表格（约 L378–395）仍为**旧小写字段级**写法（该文件无 ` ```simrisc ` 块、无生成区，故前序章节转换未覆盖）。本任务收尾。

## 修改范围（仅 `spec/SimRISC-00-指令系统设计.md`）

### §伪指令表（L384–395 等）

| 旧 | 新（以生成表为准） |
|---|---|
| `not.b rdhb, rdhc` / `not.w` / `not.t` / `not.o` | `not.b rdHB, rdHC` 等 |
| `xnor.b rdhb, rdhc, rd0` / `xnor.w` / `xnor.t` / `xnor.o` | `xnor.b rdHB, rdHC, rd0` 等（平铺；`rd0` 为具体寄存器）|
| `neg.b rdhb, rdhc` / `neg.w` / `neg.t` / `neg.o` | `neg.b rdHB, rdHC` 等 |
| `sub.sb rdhb, rd0, rdhc` / `sub.sw` / `sub.st` | `sub.sb rdHB, rd0, rdHC` 等（**`orrr` 平铺**）|
| `sub.so rd0, rdhb, rd0, rdhc`（`neg.o` 展开） | `sub.so {rd0, rdHB}, rd0, rdHC`（**双目的**，与 `SPEC-044t` 第 4 章同款）|

**保持**：`nop` / `swym 0`、`return` / `ret rd0, 0`（具体示例）；`set.rd rdxx, imm64` 等伪指令签名（`rdxx`/`rbxx`/`rfxx` 为伪指令形参）。

### 其它

全文扫描确认无其它旧式**寄存器字段引用**（`rdhb`/`rbhb`/`cg`/`rc` 小写等）；如发现一并转换并说明。

## 约束

- **只改 `spec/SimRISC-00-指令系统设计.md`**；不改生成器 / `contracts/` / `docs/`
- **语义零变化**：位宽/数值/条文一字不动
- 具体寄存器/编号（`rd0`）保持
- 命令缺失 → 停下报告，禁止自行安装

## 验收标准

1. 伪指令表内所有**真指令**写法为新格式；`neg.o` 展开为**双目的** `sub.so {rd0, rdHB}, rd0, rdHC`
2. `swym 0`/`ret rd0, 0`/`set.rd rdxx, imm64` 等**未被误改**
3. 全文重扫**零残留**小写字段引用（`\b(r[bdr]h[a-z]|cg[a-z]{2}|rc[a-z]{2})\b` 为空）
4. **语义零变化**（逐 hunk）
5. 与生成表「汇编形式」列（`not`/`neg` 相关）逐条相符
6. 反例验证：注入一处回退（如 `neg.o` 展开写回 4 操作数、或 `not.b` 小写）→ 检查可检出；复原后无残留
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
