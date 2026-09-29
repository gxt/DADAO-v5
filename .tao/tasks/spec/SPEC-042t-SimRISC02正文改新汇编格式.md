# SPEC-042t: SimRISC-02（寄存器复制）正文改为新汇编格式

**模块**：spec
**项目里程碑**：M1→M2
**依赖**：`ADR-0013`、`docs/spec/assembly-language.md` v1.1、`tools/llvm/gen_asm_list.py`、内嵌速查表（生成区）；前置 `SPEC-041t`（第 1 章已完成）
**状态**：待开始

## 背景与目标

`SPEC-041t` 已把第 1 章「取数存数」正文改为新汇编格式。本任务处理**第 2 章：寄存器复制**。规则与验证方式同 `SPEC-041t`，**权威来源 = `new_form(field=True)`（内嵌速查表「汇编形式」列）**。

## 修改范围（仅 `spec/SimRISC-02-寄存器复制.md`）

### 块 43–55（寄存器复制，`orri`，多寄存器组记法，双组）

| 旧 | 新（以生成表为准） |
|---|---|
| `rd2rd   rdhb, rdhc, immu6` | `rd2rd   {rdHB:rdHB+immu6-1}, {rdHC:rdHC+immu6-1}` |
| `rb2rd   rdhb, rbhc, immu6` | `rb2rd   {rdHB:rdHB+immu6-1}, {rbHC:rbHC+immu6-1}` |
| `rd2rb   rbhb, rdhc, immu6` | `rd2rb   {rbHB:rbHB+immu6-1}, {rdHC:rdHC+immu6-1}` |
| `rb2rb   rbhb, rbhc, immu6` | `rb2rb   {rbHB:rbHB+immu6-1}, {rbHC:rbHC+immu6-1}` |
| `ra2rd   rdhb, rahc, immu6` | `ra2rd   {rdHB:rdHB+immu6-1}, {raHC:raHC+immu6-1}` |
| `rd2ra   rahb, rdhc, immu6` | `rd2ra   {raHB:raHB+immu6-1}, {rdHC:rdHC+immu6-1}` |
| `rf2rd   rdhb, rfhc, immu6` | `rf2rd   {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` |
| `rd2rf   rfhb, rdhc, immu6` | `rd2rf   {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}` |

### 块 73–77 / 82–85（条件赋值 `cs.*`，条件组 `{...}?` 前置）

| 旧 | 新 |
|---|---|
| `cs.n rdha, rdhb, rdhc, rdhd` | `cs.n {rdHA}?, rdHB, rdHC, rdHD` |
| `cs.z rdha, rdhb, rdhc, rdhd` | `cs.z {rdHA}?, rdHB, rdHC, rdHD` |
| `cs.p rdha, rdhb, rdhc, rdhd` | `cs.p {rdHA}?, rdHB, rdHC, rdHD` |
| `cs.eq rdha, rdhb, rdhc, rdhd` | `cs.eq {rdHA, rdHB}?, rdHC, rdHD` |
| `cs.ne rdha, rdhb, rdhc, rdhd` | `cs.ne {rdHA, rdHB}?, rdHC, rdHD` |

### 块 94–98 / 103–106（浮点条件赋值）

| 旧 | 新 |
|---|---|
| `cs.n rdha, rfhb, rfhc, rfhd` | `cs.n {rdHA}?, rfHB, rfHC, rfHD` |
| `cs.z rdha, rfhb, rfhc, rfhd` | `cs.z {rdHA}?, rfHB, rfHC, rfHD` |
| `cs.p rdha, rfhb, rfhc, rfhd` | `cs.p {rdHA}?, rfHB, rfHC, rfHD` |
| `cs.eq rdha, rdhb, rfhc, rfhd` | `cs.eq {rdHA, rdHB}?, rfHC, rfHD` |
| `cs.ne rdha, rdhb, rfhc, rfhd` | `cs.ne {rdHA, rdHB}?, rfHC, rfHD` |

**关键**：`cs.eq`/`cs.ne` 条件组含**两个**寄存器 `{rdHA, rdHB}?`；`cs.n`/`cs.z`/`cs.p` 只含**一个** `{rdHA}?`。其余操作数保持原序。

### 正文引用（行 56–110 等）

字段名引用大写（`rdhb`→`rdHB`、`rbhc`→`rbHC`、`rdhc`→`rdHC`、`rdha`→`rdHA` 等）；仿 SPEC-041t 一并核对全文。

## 约束

- **只改 `spec/SimRISC-02-寄存器复制.md`**；不改生成器 / `contracts/` / `docs/`
- **不改生成区**（`<!-- ASSEMBLY_LIST_START/END -->`）
- **语义零变化**：仅记法/标点；数值/限制条文一字不动
- 逐条核对，禁止正则批量替换后不复查
- 命令缺失 → 停下报告，禁止自行安装

## 验收标准

1. 5 个代码块全部为新格式（双组组记法、`{...}?` 条件组）
2. `cs.eq/ne` 为双寄存器条件组、`cs.n/z/p` 为单寄存器条件组（**逐条**核对极性/个数）
3. 正文引用一致大写
4. **语义零变化**（逐 hunk 核对）
5. **不改生成区**（给出命中行号 > `ASSEMBLY_LIST_END` 的证据）
6. 每条新形式与内嵌速查表/`docs/assembly-list.md`「汇编形式」列**逐条相符**（独立复算）
7. 反例验证：注入一处回退（如 `cs.eq` 条件组写错个数）→ 检查可检出；复原后无残留
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
