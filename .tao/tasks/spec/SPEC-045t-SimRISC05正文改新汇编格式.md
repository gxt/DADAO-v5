# SPEC-045t: SimRISC-05（64位地址运算）正文改为新汇编格式

**模块**：spec
**项目里程碑**：M1→M2
**依赖**：`ADR-0013`、`docs/spec/assembly-language.md` v1.1、`tools/llvm/gen_asm_list.py`、内嵌速查表（生成区）；前置 `SPEC-041t`…`044t`
**状态**：待开始

## 修改范围（仅 `spec/SimRISC-05-64位地址运算.md`）

### A. 代码块

| 位置 | 旧 | 新（以生成表为准） |
|---|---|---|
| 30 | `add.so  rbhb, rbhc, rdhd` | `add.so  rbHB, rbHC, rdHD` |
| 31 | `sub.so  rbhb, rbhc, rdhd` | `sub.so  rbHB, rbHC, rdHD` |
| 41 | `add.si  rbha, imms18` | `add.si  rbHA, imms18` |
| 57 | `cmp.uo  rdhb, rbhc, rbhd` | `cmp.uo  rdHB, rbHC, rbHD` |

> 均为 `orrr`/`riii`，**平铺三操作数**（非双目的，**不加**花括号）。注意 `cmp.uo-rb` 是 `rdHB, rbHC, rbHD`（dest=rd，srcs=rb/rb），以生成表为准。

### B. 正文散文中的字段名引用

行 25（`rbhc`/`rdhd`/`rbhb`）、26（`rbhb`）、44（`rbha`）→ `rbHC`/`rdHD`/`rbHB`/`rbHA`。具体寄存器（`rb0`、`rbHB` 的高 16 位表述）保持。

## 约束

- **只改 `spec/SimRISC-05-64位地址运算.md`**；不改生成器 / `contracts/` / `docs/`
- **不改生成区**（`<!-- ASSEMBLY_LIST_START/END -->`，本文件行 6–18）
- **语义零变化**：数值/位宽/限制条文一字不动
- 逐条核对；命令缺失 → 停下报告，禁止自行安装

## 验收标准

1. A 段 4 条代码块行全部为新格式（**平铺，无花括号**）
2. B 段引用一致大写
3. **语义零变化**（逐 hunk）
4. **不改生成区**（命中行号 > 18）
5. 4 条与生成表「汇编形式」列**逐条相符**（独立复算）
6. 反例验证：注入一处回退（如 `cmp.uo` 写成花括号双目的、或字段位序对调）→ 检查可检出；复原后无残留
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
