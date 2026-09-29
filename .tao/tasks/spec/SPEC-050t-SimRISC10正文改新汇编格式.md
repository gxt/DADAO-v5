# SPEC-050t: SimRISC-10（8位数据运算）正文改为新汇编格式

**模块**：spec
**项目里程碑**：M1→M2
**依赖**：`ADR-0013`、`assembly-language.md` v1.1、`tools/llvm/gen_asm_list.py`、内嵌速查表；前置 `SPEC-041t`…`049t`
**状态**：待开始

## 修改范围（仅 `spec/SimRISC-10-8位数据运算.md`）

### A. 块 57–84（26 条，**全部平铺**）

旧：`add.ub  rdhb, rdhc, rdhd` 之类；新：`add.ub  rdHB, rdHC, rdHD`。

- `orrr`（18 条）：`add/sub/cmp/mul/div/rem.{ub,sb}`、`and/or/xor/xnor.b`
- `orri`（8 条，移位/扩展；`immu6`=移位量/起始位，**不加组记法**）：`shl/shr.{ub,sb} rdHB, rdHC, immu6`、`ext.{ub,sb} rdHB, rdHC, immu6`
- 说明：`shl.ub/shr.ub/shr.sb/ext.ub/ext.sb` 各有 `orrr`（`rdHB, rdHC, rdHD`）与 `orri`（`rdHB, rdHC, immu6`）两行，**逐条查生成表**核对

### B. 块 95–97

`neg.b   rd1, rd2        ; rd1 = -rd2（低 8 位取负，符号扩展）` —— 伪指令/具体示例，**保持**。

### C. 正文散文引用

`rdhb`/`rdhc`/`rdhd` → `rdHB`/`rdHC`/`rdHD`；具体寄存器保持。

## 约束

- **只改 `spec/SimRISC-10-8位数据运算.md`**；不改生成器 / `contracts/` / `docs/`
- **不改生成区**（本文件行 6–40）
- **语义零变化**；逐条核对；命令缺失 → 停下报告

## 验收标准

1. A 段 26 条全部平铺；`orri` 移位/扩展**不加**组记法
2. B 段 `neg.b rd1, rd2` 未被误改
3. C 段引用大写；具体寄存器未误改
4. **语义零变化**（逐 hunk）
5. **不改生成区**（命中行号 > 40）
6. 26 条与生成表「汇编形式」列**逐条相符**（独立复算）
7. 反例验证：注入一处回退 → 检查可检出；复原后无残留
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
