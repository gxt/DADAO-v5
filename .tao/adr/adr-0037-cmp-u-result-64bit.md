# ADR-0037: `cmp.{ut,uw,ub}` 的 -1 结果按 64 位扩展（修正原文零扩展错误）

**状态**：Accepted（2026-10-25，用户原话裁定）
**日期**：2026-10-25
**关联**：`spec/SimRISC-08/09/10 §1.2`、`.tao/contracts/contract-isa.md`、ADR-0019（重定位无关）、任务 `SPEC-173t` / `QEMU-074t` / `TESTCASES-065t` / `LLVM-133t`

## Context（背景）

- 原文（`SimRISC-08/09/10 §1.2`）规定：比较结果 −1/0/+1「按后缀扩展」——`.st/.sw/.sb ⇒ 符号扩展`、`.ut/.uw/.ub ⇒ 零扩展」。
- QEMU 照此实现：`trans_cmp_{ut,uw,ub}` 在 `gen_cmp_three_way` 之后再做 `ext32u/ext16u/ext8u(result)` ⇒ `cmp.ut(-1)` = `0x00000000FFFFFFFF`。
- LLVM 后端（`DADAOCodeGen.td` 的 `DADAOCmpU` pattern）注释明确假设结果是 **i64 {-1,0,1}**（即 -1 = 全 1），供 `br.*` / `cs.*` 消费。
- `br.n`（及 `br.nn`、`cs.*` 的符号类条件）只看**第 63 位**：零扩展后的 -1 是正数 ⇒ **判负失效**。
- 向量 `tests/vectors/isa/reg-compare.yaml` 也按零扩展写了期望值（`0x00000000FFFFFFFF`）。

## Decision（决策）

**D1 — `cmp.{ut,uw,ub}` 的 −1 结果 = 64 位全 1**
- 结果集：`-1 / 0 / +1`；其中 **`-1 = 0xFFFF_FFFF_FFFF_FFFF`**（按 64 位符号扩展），`0 = 0`，`+1 = 1`。
- 源操作数仍按 width 截断后比较（32/16/8 位）；只改**结果扩展**。
- `cmp.{st,sw,sb}` **不变**（符号扩展，-1 本来就是全 1）。
- 理由：`br.n`/`br.nn`/`cs.*` 依赖第 63 位；LLVM pattern 已假设 i64 {-1,0,1}；与 signed 变体语义一致。

**D2 — 版本口径 = `0.5.6-rc`，不归档**
- 本次为**原文错误修正**（不是新特性）；13 册版本头与 `SimRISC-00` changelog 记为 `0.5.6-rc`。
- `-rc` 为预发布，**不建归档目录**（沿用 2026-10-25 用户裁定；`check_spec_archive` / `gen_spec_archive --verify` 均跳过 `-rc`）。

## Rationale（理由）

- 若保持零扩展，`cmp.ut` 后接 `br.n`/`br.nn` 的代码（含编译器按 C 有符号比较生成的序列）会走错分支；这是**语义错误**，不是实现细节。
- 修 spec 而不修 QEMU/向量，会造成「文档、模拟器、测试」三方继续互相矛盾。
- 选 64 位全 1（而非「按后缀符号扩展」的另一种解释）才能与 `br.n` 的判据（bit63）和 LLVM 既有假设同时对齐。

**被否方案（记录）**：
- 保留零扩展、让 `br.n` 改看低位 ⇒ 每条分支指令都要知道比较宽度，ISA/编译器复杂度上升，且 `cs.*` 同样受害。
- 只改 QEMU 不改 spec ⇒ 文档与实现继续分叉。

## Consequences（影响）

- `spec/SimRISC-08/09/10 §1.2`、`SimRISC-00` changelog、`.tao/contracts/contract-isa.md` 同步；
- QEMU 去掉三条零扩展；向量期望值改为全 1，并新增 `cmp.ut → br.n` 用例；
- LLVM 代码预计**无需改**（pattern 已假设全 1），仅补断言；
- 不产生归档目录（`-rc`）。

## 状态说明

- **用户原话**（2026-10-25）：
  > 「补充simrisc的一个重要内容：cmp.ut/cmp.uw/cmp.ub的-1结果，不是按后缀扩展，而是64位扩展；否则，br.n无法做出正确判断；」
  > 「原始文档就写错了！！！0.5.6-rc，rc版本不要归档」
- 据此置 `Accepted`；`D1`/`D2` 均来自上述原话，无额外提案。
