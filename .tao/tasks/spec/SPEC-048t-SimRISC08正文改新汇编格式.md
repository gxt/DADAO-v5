# SPEC-048t: SimRISC-08（32位数据运算）正文改为新汇编格式

**模块**：spec
**项目里程碑**：M1→M2
**依赖**：`ADR-0013`、`assembly-language.md` v1.1、`tools/llvm/gen_asm_list.py`、内嵌速查表；前置 `SPEC-041t`…`047t`
**状态**：待开始

## 修改范围（仅 `spec/SimRISC-08-32位数据运算.md`）

### A. 块 57–84（26 条，**全部平铺**）

旧：`add.ut  rdhb, rdhc, rdhd` 之类；新：`add.ut  rdHB, rdHC, rdHD`。

- `orrr`（18 条）：`add/sub/cmp/mul/div/rem.{ut,st}`、`and/or/xor/xnor.t`
- `orri`（8 条，移位/扩展；`immu6`=移位量/起始位，**不加组记法**）：`shl/shr.{ut,st} rdHB, rdHC, immu6`、`ext.{ut,st} rdHB, rdHC, immu6`
- 说明：`shl.ut/shr.ut/shr.st/ext.ut/ext.st` 各有 `orrr`（`rdHB, rdHC, rdHD`）与 `orri`（`rdHB, rdHC, immu6`）两行，**逐条查生成表**核对

### B. 块 95–97

`neg.t   rd1, rd2        ; rd1 = -rd2（低 32 位取负，符号扩展）` —— `neg.t` 为**伪指令**、具体寄存器示例，**保持**（与 `SPEC-044t` 行 173 同款）。

### C. 正文散文引用

`rdhb`/`rdhc`/`rdhd` → `rdHB`/`rdHC`/`rdHD`；具体寄存器（`rd1`/`rd2`/`rd0`）保持。

## 约束

- **只改 `spec/SimRISC-08-32位数据运算.md`**；不改生成器 / `contracts/` / `docs/`
- **不改生成区**（`<!-- ASSEMBLY_LIST_START/END -->`，本文件行 6–40）
- **语义零变化**：数值/位宽/限制条文一字不动
- 逐条核对；命令缺失 → 停下报告，禁止自行安装

## 验收标准

1. A 段 26 条全部平铺；`orri` 移位/扩展**不加**组记法
2. B 段 `neg.t rd1, rd2` 未被误改
3. C 段引用大写；具体寄存器未误改
4. **语义零变化**（逐 hunk）
5. **不改生成区**（命中行号 > 40）
6. 26 条与生成表「汇编形式」列**逐条相符**（独立复算）
7. 反例验证：注入一处回退（如 `ext.ut ... immu6` 误加组记法、字段位序对调）→ 检查可检出；复原后无残留
8. `make check` EXIT=0

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
