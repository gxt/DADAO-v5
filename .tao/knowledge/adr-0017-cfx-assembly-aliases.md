# ADR-0017: cfx 汇编别名（寄存器符号化）

**状态**：Accepted
**日期**：2026-10-02
**关联**：`ADR-0013`（汇编语法；`D8` cfx 记法、`D9` 注释符）、`.tao/knowledge/contract-isa.md`、`spec/DADAO-12-*`（`cfxname`↔`cfxcode` 表）、`spec/DADAO-13-*` 等（寄存器表：`cg`/`rc`/`regname` 列）；任务编号待定

## Context（背景）

- `ADR-0013 D8` 已定：`cfxHA` 为核芯功能扩展编号占位；`cfx_<cfxname>` 是其**宏别名**（D8.3）；`cfx2rd`/`cfx2rc`（`crrr`）的三操作数为 **`cfxHA, cgHB, rcHC, rdHD`**（D8.2）。
- 但 spec 文档（`DADAO-22`/`23` 等）以如下形式书写：`cfx2rc cfx_smon_supv_excp_vector, rd2`、`cfx2rd cfx_smon_excp_cause_id, rd2` —— 一个**寄存器符号**同时编码 `(cfxha, cg, rc)`。
- 需要决定：该写法的**归属**（汇编规范 vs 预处理头文件）与**语法形态**（是否加花括号）。
- 依据：`spec` 的 cfx 寄存器表已含 `cg`/`rc`/`regname` 三列（如 `DADAO-13`：`| 3 | 0 | hypv global version | cfx_⟨cfxname⟩_hypv_global_version | …`），`cfxname`↔`cfxcode` 表见 `DADAO-12` ⇒ 别名表**可从 spec 机械生成**。
- 约束：`ADR-0013 D7`（就近原则）与 `ADR-0013 D9`（`#` 已释放给 cpp）——本决策**不引入** cpp 头文件依赖。

## Decision（决策）

> D1–D10 已于 2026-10-02 经用户**逐条确认**（全部保留；D9 裁定为独立生成附录；D10 裁定为数组寄存器单下标）。

- **D1（归属）**：cfx 别名属**汇编规范**——由汇编器内置**符号表**解析；**不采用** cpp 头文件/宏。
  理由：单一真源、可机械生成、`.s→.o→.s` 往返；cpp 宏无法往返，且会使示例依赖预处理环境。
- **D2（形态）**：**不引入花括号**。`{}` 已有 4 种用途（`ADR-0013 D1/D6`）；别名靠**符号前缀**区分，不新增第 5 种。
- **D3（标量别名）**：`cfx_<cfxname>` ⇔ **`cfxHA`**（沿用 `D8.3`；如 `cfx_power` ⇔ `cfx63`）。
- **D4（寄存器别名）**：**`cfx_<cfxname>_<regname>`** ⇔ 三元组 **`(cfxha, cg, rc)`**。
  - **无固定 `<mode>` 段**：`supv`/`hypv`/`umon` 等只是**某些 `regname` 的一部分**（如 `..._supv_excp_vector`），**不是**独立字段。
  - 映射**查 spec 寄存器表的 `cg`/`rc` 列**得到，**禁止**从名字字符串解析推断 ✗。
- **D5（两种拼写）**：`cfx2rd`/`cfx2rc` 允许
  - **规范长形**：`cfx2rc cfxHA, cgHB, rcHC, rdHD`（如 `cfx2rc cfx_smon, cg2, rc0, rd2`）；
  - **别名形**：`cfx2rc <cfxreg>, rdHD`（如 `cfx2rc cfx_smon_supv_excp_vector, rd2`）；
  二者解析到**同一操作元组** `(cfxha, cg, rc, rdhd)`；操作数个数（4↔2）与逗号数（3↔1）的差异在**指令级 parse** 中处理。
- **D6（往返）**：**反汇编器输出规范长形**（保往返一致性）；别名仅作**输入糖**。
- **D7（文档）**：**文档示例优先别名形**（人读友好，且与既有 `DADAO-11/22/23` 一致）。
- **D8（生成）**：别名表**由 spec 寄存器表机械生成**（与 `docs/assembly-list.md` 同族的生成器），**禁止手工维护** ✗。
- **D9（落点，2026-10-02 用户裁定）**：别名表作为**独立生成附录** **`docs/spec/cfx-aliases.md`**（由 spec 寄存器表机械生成；纳入漂移门控）。
- **D10（数组寄存器单下标，2026-10-02 用户裁定）**：数组 cfx 寄存器支持**单下标** **`cfx_<cfxname>_<regname>[N]`** ⇔ `(cfxha, cg, rc = rc_base + N)`，其中 `N` **落在** spec 寄存器表该行 `rc` 列的范围（如 `0-63`、`8-15`）内；别名表以 **`cfx_<…>[lo..hi]`** 记整数组，**单下标是其具体化**。汇编器/检测器**接受**该形（不视为违规）。

### 示例（别名映射，源自 spec 表）

| `regname`（spec） | 别名 | → `(cfxha, cg, rc)` |
|---|---|---|
| `cfx_⟨cfxname⟩_hypv_global_version`（`cfxname=smon`）| `cfx_smon_hypv_global_version` | `(2, 3, 0)` |
| `cfx_⟨cfxname⟩_supv_excp_vector`（`cfxname=smon`）| `cfx_smon_supv_excp_vector` | `(2, 2, ?)` |

> ⚠️ 上表 `cg`/`rc` 值须以 spec 寄存器表实际列值为准（`D9` 生成时机械取列）；此处不臆造 ✗。

## Rationale（理由）

- **放规范 vs 头文件**：`ADR-0013 D9` 已把 `#` 让给 cpp，但**别名不必走 cpp**；规范层符号表（类比 RISC-V 把 CSR 名做成汇编器符号）单一真源、可生成、可往返，优于头文件宏。
- **无花括号**：`{}` 已在条件组/双目的/范围/单寄存器四场景，`D6` 靠内容消歧；再加第 5 种徒增成本。
- **两种拼写**：规范长形保证反汇编确定性与可读的字段结构；别名形保证文档与手写可读性。两者映射到同一编码，无语义二义。

**备选（否决）**：
- R1：cpp 头文件/宏 → 依赖预处理、不可往返、破坏单一真源；否决。
- R2：给 `cfx_<reg>` 加花括号 → 与 `{}` 四用途冲突；否决。
- R3：只保留规范长形、不引入别名 → 文档可读性差、与既有 `DADAO-11/22/23` 不符；否决。

## Consequences（影响）

- **正面**：cfx 寄存器书写如实、与 spec 寄存器表一一对应；别名表机械生成不漂移；往返确定（反汇编出长形）。
- **负面/成本**：
  - LLVM MC 需实现**符号表 + 指令级双拼写 parse + 反汇编长形**（cfx 属 **M1 之外**，随 M2 落地）。
  - 需一个**生成器**（spec 表 → 别名表）并纳入门控。
  - 文档需统一为别名形（`DADAO-11/22/23` 迁移）。
- **后续约束**：别名只增不改语义；新增 cfx 寄存器须经生成器入表。

## 状态说明

- 本 ADR 于 2026-10-02 经用户**逐条确认 D1–D10（全部保留；D9 裁定为独立生成附录 `docs/spec/cfx-aliases.md`；D10 裁定为数组寄存器单下标）** ⇒ 置 **Accepted**。
- 落地方向：注释符落地 → cfx 别名实现 → 检测器 → 文档迁移 → 门控收口。
- 决策变更：新增 ADR 或标 `Superseded`，不直接改写已 `Accepted` 的决策。
