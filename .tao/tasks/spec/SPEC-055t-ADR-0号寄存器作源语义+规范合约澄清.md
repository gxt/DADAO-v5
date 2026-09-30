# SPEC-055t: ADR（0 号寄存器作源语义）+ 规范/合约澄清

**模块**：spec
**项目里程碑**：M1→M2
**依赖**：用户裁定（2026-09-30）
**状态**：待开始

## 背景

`rb0`（只读，读出应为**当前指令的地址**）与 `rd0`（只读，读出为 **0**）在**作源**时的语义，v5 知识库**四处不一致**，导致 `st.*` 的源为 0 号寄存器时被**误判 ILLI**：

- `spec/SimRISC-01 §存取RD:84`：`st` **允许** `rd0`（读出 0）——但 `contracts/legality_rules.yaml` `store_src_rd0` 判 **ILLI**
- `spec/SimRISC-01 §存取RB:132`：`st.o/stm.o` **允许** `rb0`，但**理由写错**（"读出 0"）；`legality_rules.yaml` `rb_base_rb0_store` 反而判 **ILLI**
- 设计意图见 `docs/02-大道至简.md`：**"将当前指令地址编码为 0 号…；ld/st 指令可以直接用 rb0 组成 symbol 的地址"**

**用户裁定（2026-09-30）**：
- **A**：`rb0` 读出 = **当前指令的地址**（非下一条）；作**显式目的** → ILLI
- **B**：`rd0` 作**源**读出 **0**，**不产生 ILLI**
- **合立一条 ADR**

## 一、新建 ADR

落点 `.tao/knowledge/adr-0015-zero-register-as-source.md`（编号递增；关联本任务与 `SPEC-056t`/`QEMU-028t`/`TESTCASES-019t`），**逐字采用**下述 decisions：

```markdown
# ADR-0015: 0 号寄存器作源（source）的语义

**状态**：Accepted（用户逐条确认 2026-09-30）
**日期**：2026-09-30
**关联**：`SPEC-055t`、`QEMU-028t`、`TESTCASES-019t`、`SimRISC-00 §基址寄存器/§数据寄存器`、`SimRISC-01 §存取RD寄存器/§存取RB寄存器`、`docs/02-大道至简.md`

## Context（背景）

SimRISC 每组寄存器的 0 号寄存器只读：`rd0` 恒 0、`rb0` 读出为**当前指令的地址**（设计意图见 `docs/02-大道至简.md`：「将当前指令地址编码为 0 号…；`ld/st` 指令可以直接用 `rb0` 组成 symbol 的地址」）。

M1 期间，「0 号寄存器作**源**」的语义在 spec、`contracts/`、QEMU 实现与测试向量之间**不一致**：`st.*` 的源为 `rd0`/`rb0` 被误判 ILLI；且 `rb0` 的语义被笼统写作「PC」，未区分「当前指令地址」与「下一条指令地址」。该不一致直接影响 CodeGen 的 PC 相对数据寻址（`[rb0, imm]`）与间接调用，须在 M2 前固化。

## Decision（决策）

### D1：`rb0` 读出为当前指令的地址

- `rb0` 读出**MUST**为**当前指令的地址**（即正在执行/翻译的该条指令的地址），**MUST NOT**为下一条指令的地址。
- 该语义适用于**一切读取 `rb0` 的场合**：寄存器复制（`rb2rd`/`rb2rb` 的源）、访存（`st.o-rb`/`stm.o-rb` 的**源**；`ld.*`/`st.*`/`ldm.*`/`stm.*` 的**基址**）、64 位地址运算（`add.si-rb`/`add.so-rb`/`sub.so-rb`/`cmp.uo-rb` 的操作数）、控制流（`br.*`/`jump`/`call` 的基址）。
- `rb0` **MUST NOT** 作显式目的；违反 **MUST** 触发 ILLI。

**备选（否决）**：
- R1：把 `rb0` 语义写作「PC」（下一条指令地址）→ 与设计意图冲突，且会让 `[rb0, imm]` 的符号寻址整体偏移一条指令；否决。
- R2：`rb0` 作源读出 0（与 `rd0` 同）→ 使 PC 相对寻址不可能，且与 `docs/02` 的设计意图冲突；否决。

### D2：`rd0` 读出为 0

- `rd0` 读出**MUST**为 **0**；作显式目的时按既有规则（`rrrr` 双目的允许其一为 `rd0`、`ret rd0, 0` 允许、其余目的为 `rd0` 触发 ILLI）。

**备选（否决）**：R1：`rd0` 作源触发 ILLI → 无依据（0 是确定的可用值）；否决。

### D3：`st.*`/`stm.*` 的源可为 0 号寄存器

- `st.*`/`stm.*` 的**源**为 `rd0` **MAY**（读出 0）、为 `rb0` **MAY**（读出当前指令地址）；**MUST NOT** 因此触发 ILLI。
- 依据：源侧的 0 号寄存器读出的是**确定值**（0 或当前指令地址），不像目的侧会「丢弃结果」，故无 ILLI 理由。

**备选（否决）**：R1：沿用旧规则（`rd0`/`rb0` 作 `st` 源 → ILLI）→ 与 `SimRISC-01 §存取RD/§存取RB` 的明文冲突，且使「存 PC 到内存」这一合法用途不可用；否决。

### D4：`rb0` 可作访存基址

- `ld.*`/`st.*`/`ldm.*`/`stm.*` 的**基址** **MAY** 为 `rb0`，此时有效地址 = **当前指令地址** + 偏移（`[rb0, imms12]` 或 `[rb0, rdHC]`）。
- 这是 `docs/02-大道至简.md`「`ld/st` 指令可以直接用 `rb0` 组成 symbol 的地址」的规范落地，供 CodeGen 的 PC 相对数据寻址使用。

**备选（否决）**：R1：禁止以 `rb0` 为基址 → 与设计意图冲突，且迫使 CodeGen 用多条指令拼接地址；否决。

## Rationale（理由）

1. **确定值优先**：0 号寄存器作源时读出的是确定值，无「丢弃结果」问题，不应与目的侧同规矩。
2. **与设计意图一致**：`docs/02-大道至简.md` 明示 `rb0` = 当前指令地址、可作符号寻址基址。
3. **消歧**：明确「当前指令地址」而非「PC/下一条」，消除 `[rb0, imm]` 的 off-by-one 风险。

## Consequences（影响）

- `contracts/legality_rules.yaml` 的 `store_src_rd0`、`rb_base_rb0_store` 须删除/改写；`rb_dest_rb0`/`rd_dest_rd0` 须**限定为「目的」**。
- `contracts/opcodes.yaml` 中 `st.*` 系列**不得**新增 `!= rd0`/`!= rb0` 合法性约束（现状已正确）。
- QEMU `trans_st_*_rrii_rd`/`trans_stm_*_rrri_rd`/`trans_st_o_rrii_rb`/`trans_stm_o_rrri_rb` 的 `ha == 0 → ILLI` 须删除。
- 测试向量中「`st` 源为 0 号寄存器 → ILLI」的用例须改判为合法，并补正向用例（`st.o rb0` 存当前指令地址；`[rb0, imm]` 作基址）。
- CodeGen 的 PC 相对寻址获得规范依据（`ACTUAL`）。

## 状态说明

- 用户于 2026-09-30 逐条确认 D1–D4 后置 `Accepted`；落地由 `SPEC-055t`（本文档与合约）、`QEMU-028t`、`TESTCASES-019t` 执行。
```

## 二、规范/合约澄清（与 ADR 同步）

| # | 位置 | 改为 |
|---|---|---|
| A1 | `spec/SimRISC-00:62` | `rb0` 读出 = **当前指令的地址**（非下一条）；作显式目的 → ILLI；`rb0[63:48]=0`；复位值不变 |
| A2 | `spec/SimRISC-01:132`（§存取RB） | `st.o/stm.o` 允许 `rbHA` 为 `rb0`（**读出为当前指令的地址**） |
| A2b | `spec/SimRISC-01:84`（§存取RD） | 保留「`st` 允许 `rd0`（读出 0）」（已正确） |
| A3 | `spec/SimRISC-05:60` | 同 A1 措辞 |
| A3b | `spec/SimRISC-06`（33/46/61/84/95/107/118） | 把 "PC" 明确为「当前指令的地址」 |
| A3c | `spec/SimRISC-12:100` | 同 |
| A4 | `contracts/legality_rules.yaml` `rb_base_rb0_store` | **删除**（`st.o-rb`/`stm.o-rb` 的源为 rb0 合法） |
| A5 | `contracts/legality_rules.yaml` `store_src_rd0` | **删除**（`st.*-rd` 的源为 rd0 合法） |
| A6 | `contracts/legality_rules.yaml` `rb_dest_rb0` / `rd_dest_rd0` | 明确**仅约束「目的」**（`ld.o-rb` 的 `rbha`、`orrr/orri` 的 `rbhb` 等） |
| A7 | `.tao/knowledge/contract-isa.md`（44、322 等） | 同步（§1.3.2 rb0 措辞；§3.2 例外表限 **load**；§3.1/§3.3 同理核查） |
| A8 | `.tao/knowledge/contract-abi.md:53`、`contracts/abi.yaml:90` | `rb0` 角色措辞（读出 = 当前指令地址） |
| A9 | `docs/impact-matrix.md:40` | 如索引受影响则同步 |

## 约束

- **不得改动 `docs/02-大道至简.md`**（设计意图原文）
- 不改 `contracts/opcodes.yaml` 中 `st.*` 的合法性列表（现状已正确，**不要**加 `!= rd0`/`!= rb0`）
- 语义零变化（除本 ADR 明确变更者）
- 命令缺失 → 停下报告

## 验收标准

1. ADR-0015 新建，含 D1–D4 + 备选 + 影响，且与上述正文一致
2. A1–A9 逐条完成；`grep -rn "读出 0" spec/ contracts/ .tao/knowledge/` 中与 `rb0` 相关者**为零**
3. `make check` EXIT=0（`legality_rules.yaml` 改动后相关 checker 仍绿）
4. 反例验证：注入一处回退（如把 `st.o` 源为 `rb0` 的描述写回 ILLI）→ 可检出；复原后无残留

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
