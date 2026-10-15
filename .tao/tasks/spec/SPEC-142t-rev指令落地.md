# SPEC-142t: `rev.{o,t,w,b}`（逐块反转）指令落地

**模块**：spec
**项目里程碑**：M8
**依赖**：`ADR-0012 D10`（**前置：`D10.1`–`D10.8` 已逐条确认完成 ✓** —— 用户 2026-10-14 原话「**D10.1-D10.8 认可**」，见 `adr-0012 §D10.0` / `§状态说明`；`D10.6a` 已定案 (b)，**`D10.6b` 亦已定案 = `scope: m8`**）；`SPEC-141t`（ISA 指令扩展预研，**只读**来源）；`INFRA-078t`（compiler-rt 预研：`bswap` 缺口来源，**只读**）；`docs/Process-06`（`spec/` 目录保护）；`ADR-0012 D4`（`spec/` 只读策略）
**状态**：待验收
**阶段进度**：A ✅ 已验证（2026-10-15）；B MC ✅ 已验证（2026-10-15，reviewer Accepted）；C QEMU ✅ 已完成（2026-10-15，待验收）

> **`**状态**` 口径说明**：本任务 = **一个任务书、三阶段验收** ⇒ `**状态**` 表**任务级**进度（**整体未完成**，故**不**置 `已验证`）；**阶段级**进度见上行 `**阶段进度**`（阶段 A 已由 reviewer `Accepted`，见「第 1 轮 reviewer 验收」）。

## 执行环境
**执行环境**：本地

> ✅ **开工前置（已满足）**：本任务书对应 `ADR-0012 D10`；用户 **2026-10-14 已逐条确认** `D10.1`–`D10.8`（原话「**D10.1-D10.8 认可**」）⇒ `D10` 已 `Accepted`（**`D10.6b` 亦已于 2026-10-14 定案 = `scope: m8`**，见「`D10.6a` 定案 / `scope` 定案」）。用户原话/日期已补入本任务书「立项来源 / 用户裁定落纸」段与 `adr-0012 §状态说明`，可 `/dispatch`。

## 立项来源 / 用户裁定落纸

- **来源**：`ADR-0012 D10`（2026-10-14 新增，**已由用户逐条确认 ✓**，见下）——`SPEC-141t` 预研候选 `C1`（`bswap` 类，主流 ISA 均有专门支持）的**落地路径 = 新增 ISA 指令**（用户 2026-10-14 经主会话问答裁定「可以增加部分指令」，见 `D10.0`）。
- **授权**（满足 `docs/Process-06 §2`）：用户原话「**a/b授权**」——授权修改 `ADR-0012` ✓，**且**授权修改 `spec/SimRISC-00` + `contracts/opcodes.yaml` + `contracts/legality_rules.yaml` ✓（**授权原话留存于 `adr-0012 §D10.0`**）。
- **用户裁定原话（Q1–Q4，原样，渠道 = 经主会话问答，2026-10-14；完整引录见 `adr-0012 §D10.0`）**：
  - Q1：「前者，你的理解很正确」（`immu6` = **单元序反转、单元内位序不变**）
  - Q2：「按 `t/w/b` 做划分……以 `w` 为例，每个 64 位寄存器，划分为四个 `w`，如果 `immu6` 为 4，每个 `w` 内部的 4 个 4 位进行翻转；所以，如果 `rdHC` 高 48 位为 0，则 `rdHB` 的高 48 位也为 0，否则，也进行类似运算」（**逐块语义**）
  - Q3：「ILLI；需要增加 `encode_onehot` 合法性规则，配合 `encode_sbz` 合法性规则；此外，还有 `dst_rd0`」
  - Q4：「`rdHC` 可以为 `rd0`，`rdHB` 可以和 `rdHC` 是同一个寄存器」
- **用户 2026-10-14 逐条确认裁定（原话原样引录，渠道 = 经主会话问答）**：「**1、分册写；2、你来定；D10.1-D10.8 认可**」
  - 「1、分册写」⇒ **`D10.6a` 定案 = 备选 (b) 分册**：`.o`→`spec/SimRISC-04`、`.t`→`08`、`.w`→`09`、`.b`→`10`；逐块语义**总述置于 `04 §4.2`**、其余三册**引用**。
  - 「2、你来定」⇒ **实现分阶段由主会话定**（定案见「分阶段实现（定案）」）。
  - 「`D10.1-D10.8` 认可」⇒ **逐条确认完成 ✓**（**`D10.6b` 后于 2026-10-14 定案 = `scope: m8`**）。
- **本任务 = 执行落点**：把上列 **已确认** 的 `D10` 决策**逐条落到全链**（`spec/` + `contracts/` + 生成器 + 向量 + MC + QEMU + 门控）。**`D10.6b` 已定案 = `scope: m8`**（见「`D10.6a` 定案 / `scope` 定案」）。
- **新增硬要求（用户 2026-10-14；原话原样引录，渠道 = 经主会话问答）**：「**关于scope的事情，增加指令与里程碑并没有绑定关系，不必纠结类似问题，甚至于不必额外记录，只需在SimRISC版本记录中写明即可**」⇒ ① 新增指令与里程碑**无绑定关系**；② **不必额外记录**（**不**新增 `scope` 说明段；`scope` 只按 `m8` 落 `contracts/`）；③ **新增的 4 条 `rev` 指令须在 `SimRISC` 的「版本与变更记录」区写明**（`SimRISC-00` 及各相关分册 `04/08/09/10`）。

## 目的

为 `SimRISC` 新增 **4 条** `rev` 指令（`rev.o`/`rev.t`/`rev.w`/`rev.b`），提供**逐块（块内按位单元）反转**能力，从而以**单条指令**覆盖 `__bswapdi2`/`__bswapsi2`（`bswap` 类）与位反转（`bitreverse`）需求（对比 ARM/RISC-V 需 2 条组合）——为 `INFRA-079t`（compiler-rt builtins 接入）的 hw 特化提供 ISA 支撑（`ADR-0027 D3`）。

## 指令契约（**自包含**；与 `adr-0012 §D10` 一致）

### 1. 格式与编码

四条统一 `orri` 格式：`opx`（= `ha`，`bits[23:18]`）+ 两个寄存器 + 6 位立即数在 `hd[5:0]`。

| 指令 | `id` | 子表 | `op` | `opx`（= `ha`） | `mask` |
|---|---|---|---|---|---|
| `rev.o` | `rev.o_orri_rd` | `MISC-octa` | `0x40` | `001100`（`0x0C`；行`001`×列`100`） | `0xFFFC0000` |
| `rev.t` | `rev.t_orri_rd` | `MISC-tetra` | `0x41` | 同上（四子表各一格 `001-100`） | `0xFFFC0000` |
| `rev.w` | `rev.w_orri_rd` | `MISC-wyde` | `0x42` | 同上 | `0xFFFC0000` |
| `rev.b` | `rev.b_orri_rd` | `MISC-byte` | `0x43` | 同上 | `0xFFFC0000` |

- **`value` 以 `contracts/opcodes.yaml`（生成器 `tools/spec/generate_opcodes.py` 产出）为唯一真源，本任务书不复写**（用户 2026-10-15 口径：按位域写清楚，派生值由生成器算）。
- `opx = 001100`（行 `001-xxx` × 列 `xxx-100`）；`value = op<<24 | opx<<18` **由生成器计算**（本任务书**不写具体值**）。
- **勘误（2026-10-15）**：本表原复写的 `0x400C0000`/`0x410C0000`/`0x420C0000`/`0x430C0000` 系列系**主会话算术笔误** ✗ —— 6 位 `opx` 落 `bits[23:18]` 放进字节需 `<<2`（`0x0C → 0x30`）；**现改为「位域 + 引真源」以杜绝此类复写笔误**。用户 2026-10-15 确认原话「**可以**」×2 + 位域口径原话「**无需计算 mask 后的值，就按位域写清楚就行，是谁的责任，谁来认真计算**」（渠道 = 经主会话问答）。
- 字段：`rdhb`（**目的**，`bits[17:12]`，bank `rd`）/ `rdhc`（**源**，`bits[11:6]`，bank `rd`）/ `immu6`（`bits[5:0]`，**无符号**）。
- 汇编语法（`spec/Toolchain-01 §…` `orri` 行）：`rev.o rdHB, rdHC, immu6`（例：`rev.o rd8, rd9, 8`）。
- **不冲突**（现场已核）：`001-100` 在四个子表均为空；`SPEC-069t` 的 reserved/已删集 = 每子表 8 条（`001-000…011` 4 逻辑 + `010/011-000/001` 2 ext×2 格式），**不含 `001-100`**；`contracts/opcodes.yaml` 无 `ha: '0x0C'` 条目（现场 `grep` 0 命中）。

### 2. 语义（逐块）

- 后缀 ⇒ **块大小 `S`**：`.o`=64 / `.t`=32 / `.w`=16 / `.b`=8；一个 64 位寄存器 ⇒ **`64/S` 个块**（1/2/4/8）。
- `immu6 = k` ⇒ **每块内部**按 `k` 位切分为 `S/k` 个**单元**，**反转单元顺序**；**单元内部位序不变**。
- **所有块一律同样处理**（不存在"范围外更高位保持/清零"）；`rdHB` 全 64 位 = `rdHC` 的逐块反转结果。
- 伪代码：`for i in 0..(64/S)−1: out_block[i] = 将 in_block[i] 的 S/k 个 k 位单元按下标倒序拼接`。
- 例：`.w` + `k=4` ⇒ 每个 16 位块切成 4 个 4 位单元并翻转；`rdHC[63:16]==0 ⇒ rdHB[63:16]==0`。

### 3. 合法性（`immu6` = one-hot）

| 后缀 | `S` | 合法 `k` | `k=8` 时对应 |
|---|---|---|---|
| `.o` | 64 | `{1,2,4,8,16,32}` | `bswap64` |
| `.t` | 32 | `{1,2,4,8,16}` | `bswap32` |
| `.w` | 16 | `{1,2,4,8}` | `bswap16` |
| `.b` | 8 | `{1,2,4}` | —（`k=8` 即恒等，**非法**） |

- 判据：`k` 须为 **one-hot（2 的幂）且 `k < S`**（即 `k ∈ {S/2, S/4, …, 1}`）；**排除 `k=S` 恒等档**；**非 one-hot（`0`/`3`/`5`/`6`/…/`63`）或 `k ≥ S` ⇒ `ILLI`**。
- 新增规则 **`encode_onehot`**（落 `contracts/legality_rules.yaml`，**与 `encode_sbz` 并列**）；四条 `rule_refs = ['dst_rd0', 'encode_onehot']`，`legality` = `rdhb != rd0` + 该后缀 one-hot 约束。
- **`rdHC` 可为 `rd0`**（源，合法）；**`rdHB == rdHC` 允许**（原地反转）。

### 4. 用途映射（后端用）

- `bswap16/32/64` = `rev.w`/`rev.t`/`rev.o` + `k=8`。**前提：源的高 `(64−S)` 位为 0**（否则其余块也被逐字节反转）⇒ **后端待核实项**。
- `bitreverse` = `rev.o` + `k=1`；**注意 `rev.t`+`k=1` ≠ 64 位全位反序**（仅每 32 位块内），`rev.w`+`k=1` 同理——**须在正文写明防误用**。

## `D10.6a` 定案 / `scope` 定案

1. **`D10.6a` 正文分册归位 = 定案 (b) 分册**（用户 2026-10-14 裁定原话「**1、分册写**」）：`.o`→`spec/SimRISC-04`、`.t`→`08`、`.w`→`09`、`.b`→`10`；逐块语义**总述置于 `04 §4.2`**、其余三册（`08/09/10`）**引用**。**据此可动 `spec/` 正文（分册 = `04/08/09/10`）。**
2. **`D10.6b` `scope` 取值 —— 已定案 = `scope: m8`**（用户 2026-10-14；见 `adr-0012 §D10.6b`）。**须同步** `tools/spec/check_scope.py` 的 `ALLOWED_SCOPES` + 分区计数 + 注释，及 `generate_opcodes.py` 的 scope 说明。**可写 `opcodes.yaml` / `check_scope.py`（按 `m8`）。**

## 分阶段实现（**定案**）

> 落地方案由主会话定（**用户 2026-10-14 裁定原话「2、你来定」授权**）。原「分阶段分解建议（建议，待用户确认）」**已随该裁定转为定案**。方案 = **一个任务书、三阶段验收**。

- **阶段 A（契约 / 编码层，单任务可验收）**：`spec/SimRISC-00` QFC 四子表 + `SimRISC-04/08/09/10` 分册正文（依 `D10.6a` 定案 (b)）+ **各册「附录：版本与变更记录」区写明本批 4 条指令**（硬要求）+ 各册 `LEGALITY` 生成区（`tools/spec/gen_legality_list.py --apply`）+ `contracts/opcodes.yaml`（生成器 `tools/spec/generate_opcodes.py`）+ `contracts/legality_rules.yaml`（`encode_onehot`）+ `.tao/contracts/contract-isa.md` / `contract-asm-list.md`（`tools/llvm/gen_asm_list.py`）+ `tests/vectors/**` + `inventory.md` + `tools/testcases/generate_isa_vectors.py`。
- **阶段 B（MC）**：`DADAOInstrInfo.td`（def/mnemonic/编码）、`DADAOAsmParser`（`orri` 受理）、`DADAOInstPrinter`、`MCCodeEmitter`/decode；`check-instrinfo` / `check-isa-coverage` 回绿。
- **阶段 C（QEMU）**：`insn.decode`（四条 token）+ `trans_rev.c.inc`（`trans_rev_o`/`_t`/`_w`/`_b`）+ `translate.c` 分派（`helper.c` 如需）；语义向量经 QEMU 跑通。
- **定案理由**（主会话，2026-10-14，授权 = 用户原话「2、你来定」）：① 与 `D9`（新增 `sub.o`）「全链单任务」惯例一致；② 三部分共享**同一编码真源**，拆开易漂移；③ 阶段化验收让**契约层先独立可验**（Spec-first），问题早暴露。
- **依赖关系**：**阶段 A → 阶段 B / 阶段 C**（编码 / 契约先行）；阶段 B 与阶段 C 可并行（**不同补丁树**），但若同改 `contracts/` 或 `tests/vectors/` 则**串行**（`AGENTS.md` 并行任务上限）。

## 接口规范

- **输入**：`adr-0012 §D10`（**决策（已由用户逐条确认 ✓）**，含用户原话）；`spec/SimRISC-00 §3.1/§4.2–§4.5`（QFC 子表，**只读**）；`contracts/opcodes.yaml` / `contracts/legality_rules.yaml`（**真源**）；`spec/Toolchain-01`（`orri` 汇编语法）；`tools/spec/generate_opcodes.py`、`tools/spec/gen_legality_list.py`、`tools/llvm/gen_asm_list.py`、`tools/testcases/generate_isa_vectors.py`；`components/llvm-project/patches/llvm/lib/Target/DADAO/**`、`components/qemu/patches/target/dadao/**`。
- **输出**：`spec/SimRISC-00`（+ `04/08/09/10` 分册正文，依 `D10.6a` 定案 (b)）、`contracts/opcodes.yaml`（**生成**）、`contracts/legality_rules.yaml`、`.tao/contracts/contract-isa.md`、`contract-asm-list.md`（**生成**）、`tests/vectors/**` + `inventory.md`、MC 补丁、QEMU 补丁、门控；完成区（**≤30 行**）+ 一键证据脚本。
- **越界声明（硬性）**：改 `spec/**` **仅限**本任务书授权的四子表 / 分册正文（`04/08/09/10`，依 `D10.6a` 定案 (b)）/ 生成区（授权原话见上）；**同一变更内**须更新 `manifests/spec-readonly.lock.toml` 对应册 `sha256`（`Process-06 §5`）；**未经确认不得**动 `spec/` 正文。

## 验收标准

1. `**状态**` = `待开始`（开工前）→ `待验收`（实现后）；本任务书**自包含**（执行不需依赖外部仓库内容）；`**项目里程碑**` = `M8`。
2. **前置状态**：`adr-0012 §D10` 的 `D10.1`–`D10.8` **已逐条确认**（用户 2026-10-14 原话「**D10.1-D10.8 认可**」已落纸于本任务书 + `ADR §状态说明`）；`D10.6a` **已定案 (b) 分册**；**`D10.6b`（`scope` 取值）已定案 = `m8` ⇒ 涉及 `scope` 的写入**（`contracts/opcodes.yaml` / `check_scope.py`）**可执行**。
3. **编码逐条**：四条 `op`/`opx`（= `ha`）/`mask` 与「指令契约 §1」**逐字一致**；四条 `value` 以 `contracts/opcodes.yaml`（生成器产出）为**唯一真源**（本任务书**不复写**，见 §1 勘误）；`tools/spec/generate_opcodes.py` 生成结果与 `contracts/opcodes.yaml` **幂等**（`--check`/重生成 diff = 0）；`validate-encoding` rc=0。
4. **语义逐条（独立 oracle，禁从 LLVM/QEMU 反推）**：以 Python 大整数**独立实现**逐块反转，对**每条指令 × 每个合法 `k`**（见下）以及边界（`rdHC=0`、`rdHC` 全 1、`rdHB==rdHC`、`rdHC=rd0`）产出期望值；向量经 QEMU 实跑**全部一致**。**端序 = 大端（本项目为大端）**，端序敏感用例须显式覆盖。
   - 合法集覆盖：`.o` `k∈{1,2,4,8,16,32}` / `.t` `k∈{1,2,4,8,16}` / `.w` `k∈{1,2,4,8}` / `.b` `k∈{1,2,4}` —— **计数现场统计、不写死**。
5. **合法性逐条**：`k` 非 one-hot 或 `k ≥ S` ⇒ **ILLI**（含 `k=0`、`k=S` 恒等档）；`rdhb == rd0` ⇒ ILLI；`rdhc == rd0` / `rdhb == rdhc` ⇒ **不**报 ILLI。每条断言均有**可达 FAIL 路径**（独立注入一次反例：注入 ⇒ FAIL ⇒ `cp`+md5 还原 ⇒ 回绿）。
6. **同步面齐备**（`D10.6` 逐项，缺项须显式标「本环不涉及 + 理由」）：四子表 + 计数、分册正文（`04/08/09/10`，依 `D10.6a` 定案 (b)）、各册 `LEGALITY` 生成区、`opcodes.yaml`、`legality_rules.yaml`、`contract-isa.md`、`contract-asm-list.md`、`tests/vectors/**` + `inventory.md`、MC、QEMU、门控。
7. **门控**：`make check`(L1)、`make check-modules`(L2) 各 **rc=0**；语义向量（`check-qemu-semantics` 或等价，含新增 `rev` 向量）rc=0；`check-isa-coverage` / `check-instrinfo` / `check-asm-list-drift` / `check-legality-drift` / `check-legality-invariants` / `check-rule-refs` / `check-spec-readonly` 各 rc=0；`check-no-residue` / `check-knowledge-refs` / `tools/infra/check_issues.py` 各 rc=0。
8. **`spec/` 授权与锁**：`git diff --name-only` 与 `spec/` 清单交集**均为本任务书授权范围**；变动的只读册 `sha256` 已在**同一变更**内更新（`make check-spec-readonly` rc=0）。
9. **一键证据脚本**（`.work/evidence/<本任务ID>/`）：非交互、任一失败非零退出、逐项打印「检查名 + 期望/实际 + rc」、含**可达 FAIL** 自检（**计数不写死**，现场统计）。
10. 完成区（**≤30 行**）与真实输出**逐条对齐**；长输出留 `.work/log/spec/**`（指针给出）；**禁** `cmd | tee` 吞码。
11. **版本记录（硬要求，用户 2026-10-14 原话「只需在SimRISC版本记录中写明即可」）**：新增的 4 条 `rev` 指令须在 `spec/SimRISC-00` 与各相关分册（`04/08/09/10`）的「**附录：版本与变更记录**」区**写明**（指令名 / 条数 / 日期），可 `grep` 核（门控 `tools/spec/check_spec_changelog.py` 保持 rc=0）。

## 阶段 A 验收口径（**架构裁定，2026-10-15**；本任务 = 一个任务书、三阶段验收，本节只定义**阶段 A** 的通过门槛）

1. **已知红（结构性必然，非缺陷）**：`make check-modules`(L2) 的子目标 **`check-interface` 有 2 项失败** = 「QEMU `trans_*` ↔ `contracts/opcodes.yaml`」核对不一致 —— 本环新增的 4 条 `rev.*`（`rev.o/t/w/b`）尚无 `trans_rev_{o,t,w,b}` 实现（阶段 C 落地）。该门控要求「**每条** `opcodes.yaml` 记录都有对应 `trans_*`，且**定义数 == 条目数**」⇒ **契约层先行（阶段 A）必然红到阶段 C**，与实现质量无关。
2. **阶段 A 验收口径** = **L1 全绿**（`make check` rc=0）**+ L2 除 `check-interface` 的上述 2 项 `rev` 相关失败外全绿**（`make check-modules` 其余子目标逐项 rc=0；L2 失败项**恰为 2 项**且**均**为 QEMU `trans_*` 缺失）。**L3 不属阶段 A 触发点**：`check_lit_gen`（`make check-full`）待**阶段 B** 重跑 `generate_lit_vectors.py` 后回绿；`make check-full`(L3) **非**阶段 A 触发点。
3. **登记（待复查）**：**阶段 C 完成后须复查** `check-interface` **转绿**（4 条 `rev.*` 均出现对应 `trans_*`，定义数 == 条目数）；届时 L2 应整体 rc=0。
4. 本口径**只**解释阶段 A 的通过门槛，**不弱化**任何门控（本环未改任何门控 / 校验脚本）；阶段 B / C 的门控口径另行给出。

## 硬约束（下发提示必带）

1. **临时目录** `/tmp/opencode/<本任务ID>/`；命令一律在 **workdir（= 仓库根）** 内、用**相对路径**；**禁**出界 `cd`（绝对 / `~` / `..`）；禁仓库内临时文件。
2. **不提交 git**（提交权归 architect）；显式 staging（**禁** `git add -A`/`.`）。
3. **前置边界**：`D10` 已逐条确认、`D10.6a` 已定案 (b)、**`D10.6b` 已定案 = `scope: m8`**；`scope` 的写入（`opcodes.yaml` / `check_scope.py`）**可执行**（按 `m8`）。
4. **Spec-first**：期望值来自 `contracts/`/`contract-isa.md` 与本任务书契约，**不从 LLVM/QEMU 反推**；**独立 oracle** 用 Python 大整数算法定义独立派生。
5. **`spec/` 保护**：改 `spec/**` 仅限授权范围；同一变更内更新 `manifests/spec-readonly.lock.toml` 的 `sha256`（`Process-06 §5`）。
6. **完成区与真实输出逐条对齐**；**计数不写死**；事实与推测分开；复杂命令输出留 `.work/log/spec/**`。
7. **失败保留现场并继续推进**（自行处置：查证 / 绕行 / 有据重试并记录次数 / 登记后跳过）；**只在需用户语义裁定（新决策 / 需授权）时留问**，禁自拟自答；**不得以重试掩盖根因**。
8. **补丁导出纪律**：MC/QEMU 改动按 `docs/Process-01` 树形补丁集（一文件一补丁 + `git apply`），`check-patch-tree` 须绿。
9. **反例注入还原纪律**：**禁** `git checkout`/`restore`/`stash`/`git show <commit>:<path>`；一律 `cp` 备份 + md5 对账，或临时树注入。
10. 文本**不写**字面 `.work/<具体路径>`（用 `<>` 占位）；任务书**自包含**。
11. **版本记录（硬要求）**：新增指令须在 `spec/SimRISC-00` 及各相关分册的「**附录：版本与变更记录**」区**写明**（用户 2026-10-14 原话）；与「**不必额外记录**」并列——**不**新增 `scope` 说明段。

## 参考检索（`DADAO-0628`，**内容溯源，非执行必需**）

> 规划期只读检索 `.cache/refs/DADAO-0628/**`（**不复制代码、不作执行依赖**）。
>
> - **0628 做法**：无 `rev`/`bswap` 相关 ISA 指令（`grep` 0 命中，含 `sail/dadao_insts.sail`）；其 ISA 真源为 `sail/dadao_insts.sail` + 机器可读编码表，扩展流程以「权威 spec 先行」固化（`ADR-0011`）。
> - **本项目差异**：真源 = `spec/SimRISC-00` QFC 子表 + `contracts/opcodes.yaml`（生成器）+ `manifests/spec-readonly.lock.toml` 哈希锁 + L1 编码门控。
> - **建议落点**：沿用本项目既有全链同步面（本任务书「指令契约」+ `D10.6` 十项），**不引入** 0628 的 sail 路径。

## 完成区

**测试结果**：`./.work/evidence/SPEC-142t/run.sh` 全量 **PASS=40 FAIL=0**（脚本 rc=0）；`run.sh --inject` 6/6 PASS。其中 L2 项以**期望 rc=2** 显式断言（失败项须**恰为** 2 项 QEMU `trans_*`，见「遗留问题」①）；L1 `make check` rc=0。
**修改文件**（`git diff --name-status -M`：19 改 + 2 新）：`spec/SimRISC-00`（四子表 `001-100` 单元格 + 附录）、`spec/SimRISC-04/08/09/10`（`§4.2.1` 正文 + 册头分类计数 + 附录 + `ASSEMBLY_LIST`/`LEGALITY` 生成区）；`contracts/opcodes.yaml`（生成，231 条）+ `contracts/legality_rules.yaml`（`encode_onehot`）；`.tao/contracts/contract-isa.md`（§2.8/§6.4.3/附录 A.2~A.5/A.8）+ `contract-asm-list.md`（生成）；`tests/vectors/rev/rev.yaml`（新）+ `inventory.md`（非 M1 节）；`tools/spec/{generate_opcodes,check_scope,gen_legality_list}.py`；`tools/llvm/{gen_asm_list,gen_isa_coverage}.py` + `llvm-isa-backend-matrix.{tsv,md}`（生成）；`tools/testcases/generate_rev_vectors.py`（新）+ `generate_isa_vectors.py`（docstring 指针）；`manifests/spec-readonly.lock.toml`（5 册 sha256）。
**验收结果**：
- 编码逐条（`run.sh` §1 机器核实）：`ha=0x0C`（opx `001100` = 行 `001-xxx` × 列 `xxx-100`）、`mask=0xFFFC0000`、`value=0x40300000/0x41300000/0x42300000/0x43300000`（=`op<<24 | ha<<18`）；QFC 四子表单元格 ↔ yaml **双向 0 差异**（`check_qfc_coverage`：231/231）。**⚠ 任务书 §1 表写 `0x400C0000`，与其同段公式/`opx=001100` 矛盾（算术笔误），本环按真源落地为 `0x40300000`（见自审 F2）。**
- 语义：独立 oracle（Python 大整数；`k=8` 另经「大端字节序块内倒序」第二条路径）**全量重算** 39 例一致；合法 (id,k) 覆盖 18/18（现场统计）；`--check` 逐字节一致（生成器可复现）。
- 门控真实 rc：L1 `make check`=0；`check-spec-{refs,drift,readonly,changelog,numbering}`=0；`validate-encoding`/`check-scope`/`check-rule-refs`=0；`check-asm-list(-drift)`/`check-asm-prose`/`check-spec-codeblocks`=0；`check-legality-{drift,invariants}`=0；`check-isa-coverage`/`check-instrinfo`=0；`check-no-residue`/`check_issues`/`check-tasks`=0。**L2**：`make check-modules` rc=2（失败项**恰为** 2 项，均在 `check-interface` 内、同为 QEMU `trans_*` 缺失）；L2 其余子目标（`check-lit`/`check-qemu-smoke`/`test-codegen`/`test-elf`/`test-semihost`/`check-picolibc-tests`）逐项 rc=0。
- 证据脚本 `.work/evidence/SPEC-142t/run.sh`（+ `log/` 原始产物）：`--inject` 6/6 PASS（注入①向量错值 ⇒ `--check` FAIL；注入②spec 子表单元格改名 ⇒ 核对 FAIL；`cp`+md5 还原 ⇒ 回绿）。
**新发现/坑**：①任务书 §1 `value` 算术笔误（上）；②L2 `check-interface` 要求**每条** `opcodes.yaml` 记录都有 `trans_*` 且「定义数 == 条目数」⇒ 契约层单独先行（阶段 A）**必然**让 L2 红，直到阶段 C 落地（跨阶段结构性耦合，须架构裁定）；③`spec/SimRISC-0{4,8,9,10}` 册头「分类…（N 条）」为**手工**行、08/09/10 早已漂移（26 vs 生成区 18），本环按生成区现场值校正（30/19/19/19）；④改 `opcodes.yaml` 须同步重生成 `llvm-isa-backend-matrix.{tsv,md}`（L1 硬校验）；⑤`check_qfc_coverage` 的 `classify_m1` 不认识 `scope: m8`，会提示「M1 外集合不一致 +4」（informational、exit 0）；⑥legality 用显式枚举式（`immu6 == 1 || …`）避开 `validate_encoding.ALLOWED_NON_FIELD` 白名单改动。
**遗留问题**：①**阶段 B（MC）/阶段 C（QEMU）未做** ⇒ L2 `check-interface` 唯一 2 FAIL（`trans_rev_*` 缺失）+ 任务书验收 4「向量经 QEMU 实跑一致」待阶段 C；②L3 `check-lit-full` 的 `check_lit_gen.py` 待阶段 B 重跑 `generate_lit_vectors.py`（`gen-*.s` 现不含 `rev.*`）；③`tools/testcases/generate_isa_vectors.py` 保持 M1-only（`rev ∉ M1`，仅加 docstring 指针），`rev` 向量改由独立生成器 `generate_rev_vectors.py` 产出（与任务书同步面列名有差异，理由见自审 F6）。

### 阶段 B（MC）—— 静态完成 + 重建已启动（2026-10-15；第二阶段待验）

**测试结果**：`./.work/evidence/SPEC-142t/run-b.sh` **PASS=12 FAIL=0**（rc=0）；`run-b.sh --inject` **PASS=11 FAIL=0**（3 组注入各在**临时副本/临时树**内使目标断言 FAIL，仓库 4 文件 md5 前后逐一相同）。`make check`(L1) rc=0；`make check-modules`(L2) rc=2（失败项**恰 2**，同阶段 A，均 `check-interface` 的 QEMU `trans_rev_*` 缺失）。
**修改文件**（`git status --porcelain -uall` = 4）：`components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOInstrInfo.td.patch`（`+4` def，1509→1549 行，`tools/infra/make_patch.py` 导出）；`tools/llvm/validate_instrinfo.py`（新增 Check 2b + non-m1 策略纳入 `scope: m8`）；`tools/llvm/llvm-isa-backend-matrix.tsv`（重生成：`rev.*` 的 `td_def` 列 0→`rev_*_orri_rd`；`.md` 未变）；`components/llvm-project/changelog.md`（`Process-01 §10` 追加一行）。`series` 不变（71）。
**验收结果**（真实 rc；日志 `.work/log/llvm/SPEC-142t-b-phB.log`、`.work/evidence/SPEC-142t/log/`）：`check-patch-tree`=0（4 组件 127 补丁）；`check-index-blobs`=0（91 新增补丁，`index 000000000..972e9f815`）；`check-instrinfo`=0（`M8 records: 4` / `4/4 条 M8 记录各有唯一 .td def` / non-m1 6 个均在 allow-list）；`check-isa-coverage`=0（重生成后）；`check-asm-list`/`check-asm-list-drift`/`check-scope`/`check-rule-refs`/`check-fp-contract`/`check-no-residue`/`check-spec-readonly` 各 =0。
**重建（启动证据）**：`setsid nohup bash -c 'JOBS=8 make build-mc > .work/log/llvm/SPEC-142t-b-phB.log 2>&1; rc=$?; echo "SPEC-142t_B_EXIT=$rc" > .work/log/llvm/SPEC-142t-b-phB.<EXIT 标记>'`；外层 PID **910488** / `make` **910490** / `ninja -j8` **910507**（16 核机器、**未**用全核）；**启动后即返回、未等待**；启动现场 41/45 步 ⇒ **预计 ≪72 min**（72 min = 上次**全量** `build-mc` 实测；本次为增量：TableGen `.inc` 再生 + DADAO 目标 + 重链接）。
**新发现/坑**：①`check-isa-coverage` 的 `td_def` 列取自 `.td` 补丁树 ⇒ **改 `.td` 必重生成矩阵**；而第①层须 `llvm-mc` ⇒ `accept` 值**随重建再变**（重建后须再生成，见遗留①c）。②`.td` 分节计数注释**本就漂移**（`orri format (26)` 实际 20、`orrr format (81)` 实际 64）——本环**未改**（最小改动），`rev` 块另起注释段。③`validate_instrinfo.py` 的 non-m1 策略原仅放行 `m3`（+`excluded` 白名单）⇒ 新 `scope`（`m8`）一进 `.td` 即红，须同步门控（本环加 Check 2b + 策略，属 **MC 门控面**、**非弱化**）。
**遗留问题**：①**第二阶段（`.EXIT` 就绪后）**：①a `llvm-mc` 汇编 `rev.{o,t,w,b}` 四条 + 编码比对（期望 `0x40300000`/`0x41300000`/`0x42300000`/`0x43300000`）+ `llvm-objdump` 反汇编往返；①b **非法 `immu6`**（非 one-hot / `k ≥ S`）**汇编期是否报错未定**——**任务书阶段 B 未要求汇编期实现**，本环**未加**汇编期 `encode_onehot`（见自审 F7，须架构裁定）；①c `python3 tools/llvm/gen_isa_coverage.py` 重生成 + `--check` 回绿（第①层 `rev.*` reject→accept）；①d `generate_lit_vectors.py` 重跑（L3 `check_lit_gen`）。②L2 `check-interface` 的 2 FAIL 仍待阶段 C。③**未提交**（提交权归 architect）；**未越界**（未触 QEMU / `spec/` / `contracts/` / compiler-rt）。
### 阶段 B-a（MC 行为验证，2026-10-15；①a–①d 完成）
**测试结果**：`.work/evidence/SPEC-142t/run-b2.sh` **PASS=14 FAIL=0**（rc=0，156 s）；`run-b2.sh --inject` **PASS=9 FAIL=0**（2 组注入各在**临时副本**内使目标断言 FAIL⇒回绿；4 个仓库文件 md5 前后逐字节相同）。子检查器 `check_mc_dynamic.py` **PASS=72 FAIL=0**（日志 `.work/log/llvm/SPEC-142t-Ba-*.log`、`MC-behavior-check.log`）。
**修改文件**（`git status --porcelain -uall` = 4 = 本任务书 + 3 个产物，**产物均为任务书第 5 项生成物**）：`tools/llvm/llvm-isa-backend-matrix.tsv`（`rev.*` 4 行 `reject`→`accept ok`；第①层 217→221 / 14→10）、`llvm-isa-backend-matrix.md`（同计数 + 4 行）、`tests/llvm/lit/MC/DADAO-gen/gen-orri.s`（+4 条 `rev.*` 向量）。**未改** MC 源码 / QEMU / `spec/` / `contracts/`。
**验收结果**（真实命令 + rc）：
- ① 编码逐条（`llvm-mc --show-encoding`，四条**逐条不抽样**）：`rev.o rd8,rd9,8`→`0x40308248`／`rev.t`→`0x41308248`／`rev.w`→`0x42308248`／`rev.b rd8,rd9,4`→`0x43308244`；`& mask=0xFFFC0000` ⇒ **`0x40300000`／`0x41300000`／`0x42300000`／`0x43300000`**，与 §1 给定期望**逐条一致**，且与 `op<<24|ha<<18` 派生值、`opcodes.yaml` `value` **三方相等**。
- ② 反汇编往返：`llvm-mc -filetype=obj` ⇒ `llvm-objdump -d` ⇒ 4/4 **文本 + 字节一致**；反汇编结果再汇编 ⇒ 文本/字节幂等。
- ③ `immu6` 边界/非法**现状**：`rev.o k=0/3/5/63`、`rev.b k=8`、`rev.t k=32` **全部 rc=0 静默接受**；`k=64`／`-1` **rc=1 拒绝**（既有 `immu6` 范围 `[0,63]`）；`rd0` 作目的 **rc=0**（MC 层无 `dst_rd0`）；`rd0` 作源 / `rd8,rd8` **rc=0**（契约合法）。
- ④ `immu6` 语义映射（MC 可观测投影）：同一 `k=8` 四条**仅第 0 字节（`op`）不同**；`.o` 32/16、`.t` 16/8、`.w` 8/4、`.b` 4/2 各取值下 `op` 与 `immu6` **原样透传**；**逐块语义本身 MC 层不可观测** ⇒ 归阶段 C。
- ⑤ 工具链联动与门控：`gen_isa_coverage.py` 重生成 + `--check` **rc=0**（`rev.*=accept ok`）；`generate_lit_vectors.py` 重跑（正例 221 / 反例 10，现场统计）；`check_lit_gen.py` **rc=0**（64 passed）；`make check-lit-full` **rc=0**（12/12，含 `gen-orri.s`）；L1 `make check` **rc=0**；`make check-modules`(L2) **rc=2** —— **恰 2 FAIL，均 `check-interface` 的 `trans_rev_*` 缺失**（去重 4 条）；L2 其余子目标（`check-lit`/`check-qemu-smoke`/`test-codegen`/`test-elf`/`test-semihost`/`check-picolibc-tests`）**逐项 rc=0**（`check-interface` 是 L2 首个前置 ⇒ make 早停，故逐项单跑）。
**新发现/坑**：①**"工具已重建"只完成一半**：`.work/build/llvm/bin/**` 为新（07:51），但**门控/lit 实际用的安装根** `.dadao/cross-toolchain/bin/llvm-mc` 仍是**重建前**的（md5 `655d7ab…` ≠ `750a449…`，且**不识别 `rev.o`**）⇒ 按 `Makefile` 既有口径（`check-isa-coverage` 注释："Needs llvm-mc (run 'make install-host' first)"）执行 `make install-host`（rc=0，**127 s**）后二者 md5 相同。**未做此步**时 `gen_isa_coverage` 重生成得回 `reject`（与阶段 B 目标不符），而 L1 仍全绿（旧工具 + 旧生成物自洽）⇒ **无门控可发现安装根滞后**。②`llvm-mc --disassemble` 对本目标**端序不符**（`40 30 82 48` 解成 `ldm.ub …`）⇒ 往返以 `llvm-objdump` 为准（防误用）。③`check_mc_dynamic.py` 的 `ILLEGAL_SNAPSHOT` 为**现状快照**：B-b 落地汇编期 `encode_onehot` 后**必须同步更新**（否则脚本报 FAIL 提示）。
**遗留问题**：①**B-b 未做**（汇编期 `encode_onehot`：非 one-hot / `k≥S` ⇒ 报错；现状静默接受）——须架构裁定是否纳入；②阶段 C（QEMU `trans_rev_*`）未做 ⇒ L2 2 FAIL 仍在；③新增待办：**安装根滞后应可判**（建议加一致性门控或收尾纪律"重建后必 `make install-host`"）；④`.dadao/`（gitignore 内）已刷新，非仓库改动，但复现步骤须含 `make install-host`。
### 阶段 C（QEMU `rev.*` 执行支持，2026-10-15；重建 + 行为验证）

**测试结果**：`.work/evidence/SPEC-142t/run-c.sh` **PASS=21 FAIL=0**（rc=0）；`run-c.sh --inject` **PASS=13 FAIL=0**（3 组注入各使目标断言 FAIL ⇒ 回绿；注入 C 为组件源树 `cp` 备份 + md5 还原，还原后 `git -C .work/source/qemu status` 干净）。**`make check-modules`(L2) rc=0**（= 本阶段核心指标：`check-interface` 83/83 PASS，`QEMU trans ↔ opcodes.yaml` = **231/231**，`QEMU trans_* 定义数 231`）。`make check`(L1)=0；`check-qemu-semantics`(L3 语义)=0（**149/149，无回归**）；`check-lit-full`=0（12/12）。
**修改文件**（`git status --porcelain -uall` 除**本任务书**外 = 6，**全在 `components/qemu/**`**）：`patches/target/dadao/insn.decode.patch`（+4 pattern，246→250 行；头计数 227→231）、`patches/target/dadao/insn_trans/trans_rev.c.inc.patch`（**新**，105 行）、`patches/target/dadao/translate.c.patch`（+1 `#include`，485→486 行）、`series`（+1）、`changelog.md`、`README.md`（规模 34→35）。**未触** `spec/`、`contracts/`、`components/llvm-project/**`；`helper.c` 无需改。
**验收结果**（真实 rc；原始日志 `.work/log/qemu/SPEC-142t-c-*.log`、`SPEC-142t-C-*.log`）：
- **编码 / 接口**：4 条 pattern（`rev_{o,t,w,b}_orri_rd` = `01000000/01/10/11` + `001100` = op `0x40..0x43` + ha `0x0C`）与 `opcodes.yaml` `value`/`mask` 逐条一致（`validate_decodetree` 231/231 PASS）；`check_qemu_trans --strict` **231/231 (M1 155/155)**；`check-interface` **83/83 PASS**；`check-patch-tree`（4 组件 128 补丁）/`check-index-blobs`（92 新增）rc=0。
- **语义 e2e（独立 oracle）**：`.work/evidence/SPEC-142t/check_rev_qemu.py` 以**第三种**独立实现（MSB-first bit 串逐块单元倒序）派生期望值（`--self-check`：与阶段 A 两条路径 90 例**三方全等**）⇒ 生成 80 例（semantic 36 / boundary 16 / legality 28，**现场统计**；非平凡例 36）经 QEMU 实跑 **80/80 PASS**；阶段 A 向量 `tests/vectors/rev` **62/62 PASS**；覆盖 4 条 × **全部合法 `k`**（含 `k=1`、`k=S/2`、`k=8`）。
- **`ILLI`（真实 QEMU 退出码）**：非 one-hot（`k=0/3/5/6/63`）、`k ≥ S`（`.t k=32` / `.w k=16` / `.b k=8`）、`rdhb=rd0` ⇒ **`Exit code: 0x88`（ILLI）**，**非** UNDI(`0x89`)、**非**静默；`rdhc=rd0`、`rdhb=rdhc` ⇒ **不**报错（PASS）。
- **重建（启动证据）**：`setsid nohup bash -c 'JOBS=8 make build-qemu …'`（外层 PID **1024816** / `make` **1024818**）⇒ `.work/log/qemu/SPEC-142t-c-phC.EXIT` = **`SPEC-142t_C_EXIT=0`**（22/22 步、**<1 min**，增量）；随后 `make install-host` rc=0，安装根与构建树 QEMU md5 相同（`682aac9d18b03ea89b804c4ff53d9f02`）。
**新发现/坑**：① `trans_*` 函数名由 `opcodes.yaml` 的 `id` 派生（`rev.o_orri_rd` ⇒ **`trans_rev_o_orri_rd`**），**非**任务书简写 `trans_rev_o`（`check_qemu_trans`/`check-interface` 按派生名精确匹配）；② `insn.decode` 由 `tools/qemu/generate_decodetree.py` 生成，其头计数**硬编码 256**（提交版按现场数维护 ⇒ `231`），插入位置须与生成器输出一致（本环逐条插在生成器对应位置并 diff 核对）；③ `make check-modules`/`check-qemu-semantics` 用**安装根** QEMU ⇒ 改 QEMU 后**必须** `make install-host`，否则门控测旧二进制（承阶段 B-a G6）；④ `ILLI` 判据因 `immu6` 是**立即数**而属**翻译期静态**判定，照既有 `trans_*_orri_rd` 惯例用 `gen_exception_illegal`（与 F4 裁定一致：MC 层不查、执行层查）。
**遗留问题**：① `make check-full`(L3) 未跑——其两组件已单跑（`check-qemu-semantics` 149/149 rc=0、`check-lit-full` 12/12 rc=0）；`test-m6` 非本任务触发点（归 `/complete` 的 L3）；② **`ISS-211` 可闭合**（执行层 `ILLI` 已落地并复核；闭合动作归主会话/architect）；③ 任务书 §1 表 `value` 笔误见阶段 A 自审 F2（本阶段按真源 `0x40300000` 系列落地）；④ **未提交**（提交权归 architect）；**未越界**（未触 `spec/`/`contracts/`/LLVM/compiler-rt）。

## 审阅记录

#### 第 1 轮 engineer 自审

（自主逐行审查；对象 = 本环新增/改动的 `tools/**` 源码、`spec/` 正文与生成区、向量与门控改动。全局 `subagent_depth=1`，engineer 无法再起嵌套子代理，故为自主逐行审查。）

**逐行审查意见与判决**

1. `onehot_expr(S)`（`generate_opcodes.py`）：`vals = [v for v in (1,2,4,8,16,32) if v < S]` ⇒ `.o`=6 档 /
   `.t`=5 / `.w`=4 / `.b`=3 档，与 `spec §4.2.1` 表逐条一致；`.o` 的 `k=64`（=`S` 恒等档）因 `immu6` 仅 6 位
   不可编码，故枚举 6 档即完整。**正确**。
2. `rev_block()` / `bswap_via_bytes()`（`generate_rev_vectors.py`）：以**第三种**独立实现（64 字符 MSB-first
   二进制串按 `k` 切片倒序）对全部 (S,k) 组合交叉验证 ⇒ 三路径全等（`src ∈ {0,1,0x0123456789ABCDEF,全 1}`）；`src >= 0x2^64` 由 `& MASK64` 归一。**正确**（F1 已修）。
3. legality 表达式用显式枚举（`immu6 == 1 || …`）而非函数式 `onehot(immu6)` ⇒ 无需改
   `validate_encoding.ALLOWED_NON_FIELD` 白名单，token 仅 `immu6`（字段名）；4 条表达式 → 同一 `encode_onehot`
   规则（同 `encode_sbz` 的「多表达式 → 一规则」惯例）。**正确且最小**。
4. **可达 FAIL**：`--inject` 两处注入均使对应检查变红（向量错值 ⇒ `--check` FAIL；spec 单元格改名 ⇒ QFC
   单元格核对 FAIL；`check_qfc_coverage` 差异 +1）；`cp`+md5 还原后逐项回绿且 md5 与注入前一致。
5. 生成物一致性/幂等：`generate_opcodes.py` 重跑 md5 不变；`gen_asm_list --embed-spec`、`gen_legality_list
   --apply` 对本环 4 册 md5 不变；`check-asm-list-drift`/`check-legality-drift` 逐字节 PASS。
6. 防造假：oracle 仅标准库 + PyYAML、**无 subprocess**（不调用 LLVM/QEMU）；期望值由算法派生；计数现场
   统计（不写死 `62/39/19/18`）。**符合 Spec-first / 独立 oracle**。
7. 越界自查：未触 MC（`components/llvm-project`）、QEMU（`components/qemu`）、compiler-rt；`spec/**` 改动
   仅 `00/04/08/09/10`（授权范围）；`.tao/knowledge/` 未改（知识沉淀归 `/complete`）。
8. `contract-isa.md` 新增文本逐行/逐块带 `[SimRISC-0X §…]` 引用 ⇒ `check-spec-refs` Check1+Check2 0 违例；
   版本记录硬要求满足（`SimRISC-00/04/08/09/10` 附录 `-rc` 段写明，无任务号/ADR 号）⇒ `check-spec-changelog` PASS。
9. 还原纪律：注入还原一律 `cp` 备份 + md5 对账，**未**用 `git checkout/restore/stash`。

**Finding 处置**

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `rev_block(src,S,0)` 会 `ZeroDivisionError`（崩溃而非显式失败） | ✅已修 | `k<1 或 S%k ⇒ ValueError`；`bswap_via_bytes` 加 `S%8` guard | `--check`/`--self-check` rc=0；负例实测抛 `ValueError` |
| F2 任务书 §1 表 `value=0x400C0000` 与同段公式 `value=op<<24\|ha<<18`、`opx=001100`（`ha=0x0C`）矛盾 | ⏸披露不改任务书（真源优先） | 按真源落地 `0x40300000`（QFC 单元格 + 既有 231 条惯例） | `run.sh` §1 编码核对 4/4；`check_qfc_coverage` 双向 0 差异 |
| F3 L2 `check-interface` 因阶段 C 未落地而红（2 项） | ⏸延后（跨阶段，须架构/用户裁定） | **未**改任何门控（弱化门控须授权） | `run.sh` 断言「L2 失败项恰 2 项且均 QEMU trans_*」+ 原始日志 |
| F4 `spec/SimRISC-0{8,9,10}` 册头分类计数早已漂移（26 vs 生成区 18） | ✅已修（在授权册内） | 四册册头计数按生成区现场值校正（30/19/19/19） | `check-asm-list`（与生成区逐字比对）PASS |
| F5 `check_qfc_coverage` 的 `classify_m1` 不认识 `scope: m8` ⇒ M1 外集合提示 +4 | ⏸延后（informational，恒 exit 0） | 未改（该脚本按 QFC 单元格名分类，无 scope 信息） | 见「新发现/坑」⑤ |
| F6 同步面列名为 `generate_isa_vectors.py`，而 `rev ∉ M1` | ⏸按差异披露 | 不改逻辑（保持 M1-only），仅加 docstring 指针；`rev` 向量由新生成器产出 | `generate_rev_vectors.py --check` PASS |

**判决**：全部 finding 已处置（F1/F4 已修；F2/F3/F5/F6 为显式披露/延后，其中 F3 属跨阶段结构性耦合、需架构裁定）。无未处置的代码缺陷 ⇒ 状态置 `待验收`。

#### 第 1 轮 reviewer 验收

**重跑记录**（全部在 workdir，相对路径）

| 检查项 | 命令 | rc | 结论 |
|--------|------|-----|------|
| L1 `make check` | `make check` | 0 | ✅ 全绿 |
| L2 `make check-modules` | `make check-modules` | 2 | ✅ 恰 2 FAIL，均 `check-interface` 内 `QEMU trans_rev_{o,t,w,b}` 缺失 |
| L2 逐子目标 | check-lit/check-qemu-smoke/test-codegen/test-elf/test-semihost/check-picolibc-tests | 各 0 | ✅ 全绿 |
| 证据脚本全量 | `run.sh` | 0 | ✅ PASS=40 FAIL=0 |
| 证据脚本注入 | `run.sh --inject` | 0 | ✅ 6/6 PASS |
| 新反例注入 | 改 SimRISC-10 legality ⇒ `check-legality-drift` | 2→0 | ✅ 注入 FAIL→cp 还原→回绿 |

**独立重算①–⑥**

| # | 内容 | 结论 |
|---|------|------|
| ① | opx=001100→ha=0x0C→value=op<<24\|ha<<18=0x40300000 系列 | ✅ 非 0x400C0000；yaml 实际值一致 |
| ② | QFC 四子表 ↔ opcodes.yaml rev.* 双向核对（自写 parse，4 条） | ✅ 差异=0 |
| ③ | encode_onehot 可达 FAIL：k=3/5/0/8 ⇒ ILLI；四指令 legal_k 全量 eval | ✅ 一致 |
| ④ | 独立 oracle（第四种：逐块位操作法）39 例 semantic/boundary + 19 legality + 4 encoding | ✅ 差异=0 |
| ⑤ | 分册 04 §4.2.1 总述 + 08/09/10 §4.2.1 引用；5 册版本记录含 rev.* | ✅ |
| ⑥ | 锁册 sha256：受改 5 册逐册重算与 lock.toml 一致 | ✅ |

**约束核验**

- L1 全绿 ✅；L2 恰 2 FAIL 且均 rev.* trans_* 缺失 ✅；L3 非阶段 A 触发点 ✅
- 编码 value 与真源公式一致 ✅；任务书 §1 表 0x400C0000 为笔误（完成区 F2 披露）✅
- 版本记录硬要求：5 册附录均写明 ✅
- spec/ 改动限授权范围（00/04/08/09/10）✅；锁册 sha256 同步 ✅
- 反例注入可达 FAIL ✅（engineer 2 组 + reviewer 新 1 组）

**Finding**

| # | 描述 | 严重度 | 处置 |
|---|------|--------|------|
| R1 | 任务书 §1 value 笔误 0x400C0000 未标勘误待办 | 低 | 建议 /complete 时补勘误条目 |
| R2 | 修改文件数完成区写 19+2=21，git diff 实际 22（含任务书） | 信息 | 不阻塞 |

**判决**：**Accepted** — L1 全绿、L2 恰 2 FAIL（均为阶段 C 依赖的 rev.* trans_* 缺失）、证据脚本 40/0 + 6/6、独立重算①–⑥全部通过、无阻断缺陷。

#### architect 提交与文件集审核留痕（2026-10-15；**只追加**）

- **档位**：**正常提交**（依据 = 上「第 1 轮 reviewer 验收」判决 `Accepted`；**阶段级**，见 `**阶段进度**`）。
- **提交**：分支 `SPEC-142t-A` 头提交（提交信息 = `SPEC-142t A: 阶段A收尾（已验证）+ value 改引真源（勘误主会话笔误）+ 阶段进度行`；**只 `commit`，未 `merge`、未 `push`**）。**注**：本留痕与提交同体 ⇒ **不内嵌 SHA**（SHA 随留痕内容变化而变、会自指失真）；SHA 以分支头 / 父会话回报为准。
- **文件集对账**（`git diff --cached --name-only` ↔ 本笔范围）：**2** 项 = 本任务书 + `.tao/knowledge/milestones.md` ⇒ **无漏提、无越界**（阶段 A 实改文件已于 `19d7c57` 落地；本笔仅收尾文书）。
- **本笔内容**：① `**阶段进度**` 行 + `**状态**` 口径说明（任务级 `待验收`，**不**置 `已验证`）；② §1 表/正文 `value` 复写 → **位域 + 引真源**（删具体值）+ §1 勘误条（主会话 `0x400C0000` 系列算术笔误：6 位 `opx` 落 `bits[23:18]` 需 `<<2`，`0x0C→0x30`）；③ §1「不冲突」③ 的 `0x??0C0000`（笔误模式）→ `ha: '0x0C'`；④ 验收 3 同步「`value` 以 `contracts/opcodes.yaml` 为唯一真源」；⑤ `milestones.md` `SPEC-142t` 流水行补阶段 A 已完成并验收（2026-10-15）+ 状态/完成时间同步（`value` 改引真源）。
- **finding 处置回应**：**R1**（§1 `value` 笔误未标勘误待办）⇒ **已处置**（§1 勘误条 + 引真源）；**R2**（完成区 19+2 vs 实际 22）⇒ **不阻塞、不改完成区**（原样留证）。
- **门控（本笔后）**：`make check`(L1)=0、`check-knowledge-refs`=0、`check-knowledge-dir`=0、`check-dirs`=0、`check-no-residue`=0、`make check-tasks`=**0**（**报告列出本任务** = 预期：完成区已填 + 任务级 `待验收`；报告型、不阻断）。

#### 第 2 轮 engineer 自审（阶段 B / MC）

（自主逐行审查；对象 = 本环新增/改动的 `.td` 补丁、`tools/llvm/validate_instrinfo.py`、矩阵 `tsv`、组件 `changelog.md`、证据脚本。全局 `subagent_depth=1`，无法起嵌套子代理，故为自主逐行审查。）

**逐行审查意见与判决**

1. `DADAOInstrInfo.td` 四个 def：格式类 `DADAOOrri`（`FormatKind=7` ⇒ `ha=opx, hb=rb, hc=rc, hd=imm6`），`op=0x40..0x43`、`ha=0x0C` 逐条取自 `contracts/opcodes.yaml` 的 `rev.{o,t,w,b}_orri_rd`（`op/ha/mask` 一致，见 `check_mc_static` 现场核对）。编码 = `op<<24 | ha<<18 | rdhb<<12 | rdhc<<6 | immu6` ⇒ `0x40300000` 系列，与 `value` 一致。**正确**。
2. 操作数形态 `(outs GPRD:$rb)` + `(ins GPRD:$rc, immu6:$imm6)` 与真源 `fields`（`rdhb` dst/rd、`rdhc` src/rd、`immu6` imm/无符号）逐字段对应；`Pattern = []`（MC 层，不进 CodeGen）与 `sub_o_dbb`/cfx 先例一致。**正确**。
3. **未改** `DADAOAsmParser`/`DADAOMCInstPrinter`/`MCCodeEmitter`/`Disassembler`：逐行核对了两处 mnemonic 白名单（`isMultiToSingleOrriMnemonic`、instprinter `FK_orri` 分组渲染表）——`rev.*` **不在**其中，故走通用 `orri` 路径（解析 `dst, src, imm`、flat 打印、TableGen 生成的匹配器/解码表）。**正确且最小**。
4. 补丁导出用 `tools/infra/make_patch.py`（E1 校验 + §6.2 幂等写），hunk 头 `+1,1549` 与 `index ..972e9f815` 由 `git diff` 生成，**非手改**（`check-patch-tree` 断言⑥/⑨ + `check-index-blobs` 独立复算）。**正确**。
5. `validate_instrinfo.py`：Check 2b 与策略放行 `m8`，行为与 `m3` 对称；反例（临时 `.td` 改 `rev.t` 的 `op`）实测 FAIL ⇒ 该断言有**可达 FAIL 路径**。**正确**。
6. 矩阵 `tsv`：仅 `rev.*` 4 行的 `td_def` 列变化（其余 227 行逐字节不变，`git diff` 仅 4 行）；`.md` 未变。**正确**。
7. **反例注入纪律**：3 组注入全部落在 `/tmp/opencode/SPEC-142t/` 临时副本/临时树，**未**用 `git checkout/restore/stash`，**未**改仓库内文件；`--inject` 末尾以 md5 逐文件对账（4 个仓库文件）不变。**符合**。
8. 越界自查：`git diff --name-only` = 4 项，与 `spec/` 交集 **空**；未触 `components/qemu/**`、`contracts/**`、`compiler-rt`；`.tao/knowledge/` 未改（知识沉淀归 `/complete`）。**符合**。
9. `changelog.md` 追加行属 `Process-01 §10`「组件补丁变更须同一变更内追加」的**强制项**（虽不在任务书文件清单内，属规则要求 ⇒ 披露）。**正确**。

**Finding 处置**

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 改 `.td` 使 `check-isa-coverage` 的 `td_def` 列漂移（必然） | ✅已修 | 重生成 `llvm-isa-backend-matrix.tsv`（4 行） | `make check-isa-coverage` rc=0；`gen_isa_coverage --check` PASS |
| F2 新 `scope: m8` 不在 `validate_instrinfo` 的 non-m1 策略内 ⇒ `check-instrinfo` 红 | ✅已修（MC 门控面，非弱化） | 加 Check 2b + 策略放行 `m8`（+docstring） | `make check-instrinfo` rc=0（`4/4 M8 记录各有唯一 .td def`） |
| F3 矩阵第①层 `rev.*` 仍为 `reject`（重建前 `llvm-mc` 尚不识别） | ⏸延后（须重建） | 未伪造 `accept`；重生成后按现状落盘 | 见「遗留问题①c」（第二阶段重生成 + `--check` 回绿） |
| F4 任务书阶段 B **未要求**汇编期 `encode_onehot`（`immu6` 非 one-hot / `k≥S`） | ⏸延后（须架构裁定） | **未加**汇编期静态合法性（若加则须改 `AsmParser` 且属行为新增） | 自审披露 + 「遗留问题①b」；`immu6` 仅按 `uint6` 范围校验（既有 `checkImmediateRanges`） |
| F5 `.td` 分节注释计数本就漂移（orri 26/实际 20、orrr 81/实际 64） | ⏸披露不改（最小改动） | 未改这两行；`rev` 块另起独立注释段 | 「新发现/坑」② |
| F6 组件 `changelog.md` 不在任务书文件清单内 | ✅已做（规则强制项，须披露） | 追加 SPEC-142t 一行 | `make check`（含 `check-components`）rc=0 |

**判决**：全部 finding 已处置（F1/F2/F6 已做，F3/F4/F5 为显式披露/延后，其中 F4 属**行为新增**、须架构裁定）。阶段 B **静态部分**无未处置代码缺陷；`llvm-mc` 行为验证与矩阵再生成属**本任务第二阶段**（重建完成、`.EXIT` 就绪后另行派发）。阶段级状态：**待第二阶段**（任务级 `**状态**` 维持 `待验收`，口径同阶段 A）。

#### 第 3 轮 engineer 自审（阶段 B-a / MC 行为验证，2026-10-15）

（自主逐行审查；对象 = 本环**新增证据脚本** `check_mc_dynamic.py` / `run-b2.sh` + **重生成产物**（矩阵 `tsv`/`md`、`gen-orri.s`）+ 为满足门控一致性执行的 `make install-host`。全局 `subagent_depth=1`，故为自主逐行审查。）

**逐行审查意见与判决**

1. `check_mc_dynamic.py` 的 `word_be()`（大端拼字）**非假定**：§2 以三方交叉（`op<<24|ha<<18` 派生 / yaml `value` / `llvm-mc` 实测字）互证 ⇒ 端序若有误，四条会**同时** FAIL（有可达 FAIL 路径）。**正确**。
2. `parse_encoding()` 只取**首处** `encoding: [` ⇒ 所有调用均传**单条**汇编输入（逐条调用）⇒ 无隐含截断。**正确**。
3. §3 反汇编：`OBJ_RE` 要求「4 字节 hex + `rev.` 助记符」锚定整行 ⇒ 不会把 `...rev4.o: file format` 头行误当指令（首版曾误匹配，首跑 FAIL=3 暴露，见 G2）。往返以**两条独立路径**互证（`objdump` 字节 vs `--show-encoding` 字节）+ 再汇编幂等。**正确**。
4. §4 现状断言**两类分开**：`ILLEGAL_SNAPSHOT`（6 例，现状快照、B-b 落地后必改）与「超 6 位范围被拒」（2 例，既有类型范围检查、真断言）；注入②实测可达 FAIL。**正确且诚实**（未把「静默接受」粉饰为合规）。
5. §5 语义映射**只断言 MC 可观测投影**（`op` 选块大小 + `immu6` 原样透传），并**显式声明**逐块语义在 MC 层不可观测、归阶段 C ⇒ **不越权冒充语义验证**。**正确**。
6. `--root` 参数：首版以 `parents[3]` 推导仓库根 ⇒ 临时副本（`/tmp`）下 ROOT 解析错误、`--inject` 先验基线假 FAIL（实测暴露，见 G3）；改显式 `--root` 后干净。**已修**。
7. 反例注入纪律：2 组注入全在 `/tmp/opencode/SPEC-142t/` **临时副本**；`--inject` 末尾对 4 个仓库文件 md5 前后对账（**未**用 `git checkout/restore/stash`；不以 `git status` 干净作还原证据）。**符合**。
8. `run-b2.sh` 退出码：`run_gate` 直取 `$?`（**无** `tee`）；两模式均以 `if [ "$FAIL" != 0 ]; then exit 1; fi; exit 0` 收尾；L2 单跑 `check-interface` 并以「表内 FAIL 行数 == 2」+「缺失 `trans_rev_*` 去重 == 4」双断言（计数现场统计）。**正确**。
9. `make install-host` **正当性**：非仓库改动（`.dadao/` 在 `.gitignore`），且 `Makefile` 对 `check-isa-coverage` 明确要求先做；不做则矩阵只能落 `reject`（与阶段 B 目标冲突）。处置留痕：rc=0 / **127 s**；`git status --porcelain -uall` 仍为 3 个生成物（无额外污染）。**符合**。
10. 越界自查：本环 `git status` = 3 项（`matrix.tsv`/`matrix.md`/`gen-orri.s`）**均为任务书第 5 项生成物**；未触 `components/llvm-project/**`、`components/qemu/**`、`spec/**`、`contracts/**`。**符合**。

**Finding 处置**

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| G1 安装根 `.dadao/cross-toolchain/bin/llvm-mc` 滞后于重建（不识别 `rev.o`）⇒ 矩阵只能 `reject`，且 L1 无法发现 | ✅已处置（按 `Makefile` 既有前置） | `make install-host`（rc=0，127 s）；随后重生成矩阵 | 安装根/构建树 md5 相同（`750a449f…`）；`gen_isa_coverage --check` rc=0；`rev.*=accept ok` |
| G2 首版 `OBJ_RE` 误匹配 objdump 头行（`rev4.o: file format`）⇒ §3 假 FAIL=3 | ✅已修 | 正则改为「4 字节 hex + `rev.`」整行锚定 | 重跑 §3 全 PASS；`check_mc_dynamic.py` PASS=72 FAIL=0 |
| G3 临时副本下 `parents[3]` 推导 ROOT 失败 ⇒ `--inject` 先验基线假红 | ✅已修 | 加 `--root`（默认仍按脚本位置推导）；注入时传 `--root "$ROOT"` | `--inject` 首版 8/1 → 修后 **9/0 PASS** |
| G4 `ILLEGAL_SNAPSHOT` 为现状快照（B-b 落地后必改） | ⏸披露不改（设计如此） | 常量注释 + 脚本打印 + 「新发现/坑」③ | 注入②证明该断言可达 FAIL |
| G5 `llvm-mc --disassemble` 端序不符（喂大端字节解错） | ⏸披露不改（非本环范围） | 未改任何工具；往返改用 `llvm-objdump` | 「新发现/坑」② |
| G6 安装根滞后**无门控可判**（旧工具 + 旧生成物互相自洽） | ⏸延后（建议新门控/纪律，跨任务） | **未**加门控（新增/弱化门控须授权） | 「遗留问题」③ |

**判决**：全部 finding 已处置（G1/G2/G3 已修，G4/G5/G6 为显式披露/延后，其中 G6 属**新增门控**、须架构裁定）。本环**未发现** `rev.{o,t,w,b}` 的 MC 编码/反汇编**缺陷**（四条编码与真源、任务书期望三方一致；往返文本/字节一致）。阶段级状态：**B-a 完成 → 待验收**（任务级 `**状态**` 维持 `待验收`，口径同阶段 A）。

#### architect 提交与文件集审核留痕 + 主会话裁定留痕（阶段 B-a，2026-10-15；**只追加**）

- **档位**：**正常提交**（依据 = 上「第 3 轮 engineer 自审」判决「B-a 完成 → 待验收」；阶段级，任务级 `**状态**` 维持 `待验收`；**不带 `WIP:`**，供 reviewer 独立验收）。
- **提交**（分支 `SPEC-142t-B`，三笔；**只 `commit`，未 `merge`、未 `push`**）：① `SPEC-142t B: MC 支持完成（rev.* 4 条编码/反汇编验证通过；isa-coverage / lit 生成物同步）`；② `SPEC-142t B: 登记 B-a 2 条 issue（ISS-210 / ISS-211）`；③ 本笔（仅本留痕）。**注**：本留痕与提交③同体 ⇒ **不内嵌 SHA**（SHA 随留痕内容变化而变、会自指失真）；SHA 以分支头 / 父会话回报为准。本任务书在提交①（阶段 B-a 记录）与本笔各出现一次（增量追加，非改写）。
- **文件集对账**：① 提交① `git diff --cached --name-status -M` = **4** 项 ↔ 完成区「阶段 B-a 修改文件」声明 **4** 项 ⇒ **无漏提、无多提、无越界**（本任务书 + `tools/llvm/llvm-isa-backend-matrix.{tsv,md}` + `tests/llvm/lit/MC/DADAO-gen/gen-orri.s`；三产物均为任务书第 5 项生成物；**未触** `components/**` / `spec/**` / `contracts/**` / QEMU）。② 提交② = `issues.yaml` **单笔**（现场取号：`ISS-209` 之后 ⇒ `ISS-210` / `ISS-211`）。
- **门控（本笔前实跑）**：`python3 tools/infra/check_issues.py` **rc=0**（`check_issues: 30 open, 4 closed (0 blocking M1-gate: 0)`）。
- **裁定留痕的效力说明**：本节**只追加** ⇒ 上方「**阶段进度**」行与「阶段 B-a 遗留问题①」原文**保留不动**，其含义以本节为准（原文「B-b 未做」＝ **B-b 取消**）。
- **主会话裁定 F4（2026-10-15）：不加汇编期 `encode_onehot` 检查** —— `rev.{o,t,w,b}` 的**非 one-hot `immu6` / `k ≥ S` 不要求汇编期报错**，MC 层维持现状（静默接受，仅既有 `immu6` 类型范围越界报错）。
  - **理由①（与既有层一致）**：合法性规则（`encode_onehot` / `dst_rd0`）**落在契约 / 生成器与执行层**（`contracts/legality_rules.yaml` + 阶段 A 落地物）；既有 **120 条**指令同样**不在 MC 层**做此类检查 ⇒ 单为 `rev.*` 加检查 = **破坏既有分层口径**。
  - **理由②（`ILLI` 属执行期）**：非法编码异常 `ILLI` 是**执行期**语义，由**阶段 C（QEMU）**承担；MC 层职责限于「格式可编码 + 既有类型范围」。
  - **口径全条落纸** = `ISS-211`（`open`、留档；阶段 C 落地 `ILLI` 并复核后可闭合）。
- **连带裁定：B-b 取消** ⇒ 阶段 B **无需第二次重建**（`.dadao/` 安装根已 `install-host` 刷新、与构建树 md5 一致）；阶段 B 完成门槛 = B-a ①a–①d 全绿 + 本裁定口径落纸。**副作用（如实说明）**：`check_mc_dynamic.py` 的 `ILLEGAL_SNAPSHOT`（6 例「静默接受」快照）**因 B-b 取消而即当前口径的固定断言**（非「待同步的临时快照」）；engineer「B-a 遗留问题①」不再待派。若后续有人给 MC 层加合法性检查，该断言会 FAIL ⇒ 提示「口径变更须先走裁定」。
- **未做（按纪律）**：**未** merge `SPEC-142t-B`、**未** push（`push` 只在 `/complete` 后由主会话执行）；分支 `INFRA-076t` **未动**（仍未合并，原样保留）。

#### 第 2 轮 reviewer 验收（阶段 B-a / MC 行为验证，2026-10-15）

**重跑记录**（独立执行，workdir 仓库根，相对路径；分支 `SPEC-142t-B`=`6950a58`）

| # | 检查项 | 命令/方式 | 实测 rc | 结论 |
|---|--------|-----------|---------|------|
| 1 | 两处二进制测 rev.o（假绿陷阱） | `.dadao/cross-toolchain/bin/llvm-mc` + `.work/build/llvm/bin/llvm-mc` | 0/0 | 两者 md5=`750a449f…` 相同，均输出 `encoding: [0x40,0x30,0x82,0x48]` ✓ |
| 2 | 四条编码逐条 + 三方比对（机器） | Python 独立脚本实测 vs yaml `value` vs `op<<24\|ha<<18` | 0 | 4/4 三方一致；ha=0x0C=0b001100 ✓；期望值 `0x40300000/0x41300000/0x42300000/0x43300000` |
| 3 | 反汇编往返 | `llvm-mc -filetype=obj` → `llvm-objdump -d` → 再汇编 `cmp` | 0 | 4/4 助记符+操作数正确；再汇编 `cmp rc=0`（字节一致） |
| 3b | 独立位域解码 | Python 按位取 rdhb/rdhc/immu6 | 0 | 4/4 与 objdump 显示一致（含 k=3/5/1 非 one-hot） |
| 4a | rev.* immu6 现状 | k=0/3/5/63 rc=0（静默）；k=64/-1 rc=1（类型范围） | — | 与完成区③/F4 裁定一致 ✓ |
| 4b | 既有 orri 对照（dst_rd0/encode_sbz） | `ext.uo/shr.uo/shl.uo rd0,rd9,8` + `shr.ub rd8,rd9,63` + `shl.ut rd8,rd9,40` | 0（全部静默） | **既有 orri 同样不做** MC 层合法性检查（仅 immu6 类型范围 [0,63]），独立支撑「与既有分层一致」✓ |
| 5a | gen_isa_coverage 重生成+幂等+--check | `gen_isa_coverage.py` 重跑 md5 不变 → `--check rc=0` | 0 | accept=221/reject=10 ✓ |
| 5b | generate_lit_vectors 重跑+幂等 | `generate_lit_vectors.py` + md5 对比 | 0 | gen-orri.s md5 不变；rev.* 行=16 ✓ |
| 5c | check_lit_gen + make check-lit-full | 各自独立 | 0/0 | 64 passed / 12 of 12 ✓ |
| 6 | L1 `make check` | `make check` | 0 | 全绿 ✓ |
| 6b | L2 `make check-modules` | `make check-modules` | 2 | 恰 2 FAIL：check-interface QEMU trans_rev_{o,t,w,b} 缺失（去重 4 条）✓ |
| 6c | L2 逐子目标 | 7 项各自独立 | 2/0/0/0/0/0/0 | check-interface=2（预期），其余 6 项均 0 ✓ |
| 7 | **我的新反例**（不在 engineer 清单） | 注入矩阵 tsv rev.o `td_def`→`WRONG_DEF` → `--check` | 1→0 | 注入 FAIL；cp+md5 恢复回绿；仓库文件 md5 前后一致 ✓ |
| 8a | 证据脚本 run-b2.sh 重跑 | 全量 + --inject | 0/0 | PASS=14/0 + PASS=9/0 ✓ |
| 8b | issues.yaml ISS-2xx 编号唯一性 | Python 统计 | 0 | 12 条无重复 ✓ |
| 8c | 完成区对账 | git diff vs 完成区声明 | — | B-a 产物 4 项 + 提交链 4 笔一致 ✓ |

**约束核验**（逐条）

- F4 裁定与实测一致：`rev.*` 非 one-hot `immu6` 均 rc=0 静默接受（k=0/3/5/63/8/32）；既有 `orri`（`ext.uo/shr.uo/shl.uo`/`shr.ub`/`shl.ut`）同样不做 `dst_rd0`/合法性检查 ✓
- 两处二进制 md5 相同（`750a449f…`）且均识别 `rev.*`（安装根无假绿）✓
- L1 全绿；L2 恰 2 FAIL（均 `check-interface` 的 `trans_rev_*` 缺失，阶段 C 依赖）✓
- 工具链联动全绿（gen_isa_coverage/check_lit_gen/check-lit-full）✓
- 证据脚本可达 FAIL（engineer 2 组 + reviewer 1 组独立注入）✓
- 完成区 ≤30 行，与真实输出逐条对齐 ✓

**Finding**：无。无阻断缺陷。

**判决**：**Accepted** —— L1 全绿、L2 恰 2 FAIL（阶段 C 依赖的 `trans_rev_*` 缺失）、四条编码三方一致、往返字节一致、`immu6` 现状与 F4 裁定一致、既有 `orri` 独立支撑「不分层一致」、工具链联动全绿、证据脚本 14/0 + 9/0、我的新反例注入 FAIL→回绿、编号唯一性无重复。

#### 第 4 轮 engineer 自审（阶段 C / QEMU，2026-10-15）

（自主逐行审查；对象 = 本环新增/改动的 `insn.decode` 4 条 pattern、`insn_trans/trans_rev.c.inc`（105 行）、`translate.c` 的 1 行 `#include`、`series`/`changelog.md`/`README.md`、证据脚本 `check_rev_qemu.py` + `run-c.sh`。全局 `subagent_depth=1`，无法起嵌套子代理，故为自主逐行审查。）

**逐行审查意见与判决**

1. `gen_rev_units`（`trans_rev.c.inc`）：编译期展开的**位位置置换**——`for b in 0..64/S-1`（块）× `for u in 0..S/k-1`（块内单元），`src` 取 `src>>(b*S+u*k) & unit_mask` 后左移到镜像位 `b*S+(n_units-1-u)*k`；`src_shift` 最大 `64-k < 64`、`dst_shift < 64` ⇒ 无 UB/无 64 位移位；`unit_mask=(1ULL<<k)-1` 且 `k<=32`（合法集内 `k<S<=64` 且 one-hot ⇒ `k<=32`）⇒ 无 64 位溢出。`k=0` 会除零，但 `rev_legal` 在**全部 4 个**调用点先行否决（`k<1`）⇒ 不可达；保持最小改动（不另加断言）。**正确**。
2. 语义 ↔ 契约（`ADR-0012 D10.3`）：块按 LSB 起 `b*S..b*S+S-1` 切分、块内 `S/k` 个 `k` 位单元倒序、单元内位序不变、**所有块同样处理**——与 `spec/SimRISC-04 §4.2.1` 逐条一致；`rdHB` 全 64 位为结果，无「范围外高位」特例。**正确**。
3. `rev_legal`：`rdhb==rd0` ⇒ `ILLI`（`dst_rd0`）；`k<1 || (k&(k-1))!=0 || k>=S` ⇒ `ILLI`（`encode_onehot`）；`k=0` 由 `k<1` 短路（避免 `(k&(k-1))` 的 one-hot 误判）；`immu6` 为**立即数** ⇒ 翻译期静态判定，用 `gen_exception_illegal`（照 `trans_shr_uw_orri_rd` 等既有 `orri` 先例），**未**新增运行期分支。**正确**。
4. `insn.decode`：4 条 pattern 逐条与 `generate_decodetree.py` **现场产出一致**（本环 diff 生成物 vs 提交版：除头计数外**零差异**）⇒ 无插入位置漂移；`validate_decodetree` 231/231 PASS（mask/value/格式双向）。**正确**。
5. `translate.c`：`#include "insn_trans/trans_rev.c.inc"` 紧随 `trans_fp.c.inc`（与该文件既有 include 群一致）；hunk 头 `@@ -0,0 +1,486 @@` 与 `index` 行由 `tools/infra/make_patch.py` 自动生成（**非**手改），`check-patch-tree` 断言⑥/⑨ 与 `check-index-blobs` 独立复算通过。**正确**。
6. 独立 oracle（`check_rev_qemu.py`）：与阶段 A 生成器**代码独立**（MSB-first 字符位串 vs 整数移位/大端字节序），`--self-check` 90 例三方全等；**无** subprocess、不调用 LLVM/QEMU。**符合 Spec-first / independent oracle**。
7. **可达 FAIL（逐断言）**：注入 A（篡改 semantic 期望值）⇒ 1 FAIL；注入 B（把**合法 `k`** 标为「期望 `ILLI`」）⇒ FAIL（证明 `ILLI` 断言非恒真）；注入 C（组件源树去掉单元倒序 `(n_units-1-u)→(u)` 并重建）⇒ **40 FAIL**（证明 QEMU **实现本身**被比对，非空跑）。还原后回绿。**符合**。
8. 证据脚本纪律：全量 21 项、注入 13 项；`cmd >log 2>&1` 后取 `$?`（**无** `tee`）；覆盖/计数**现场统计**（cases/cases.json/`trans 231/231` 从日志抓取）；收尾 `rc=0; [ FAIL = 0 ] || rc=1; exit $rc`。**符合**。
9. 还原纪律：注入 C 用 `cp` 备份 + md5 对账（`5edb643e…`），**未**用 `git checkout/restore/stash`；还原后源树 md5 复原 + `git -C .work/source/qemu status --porcelain` 为空（**不以** `git status` 干净单独作证据，另有 md5）。**符合**。
10. 防造假：`ILLI` 结论取**真实 QEMU 退出码**（`Exit code: 0x88`，逐条 5 例）；安装根与构建树 QEMU md5 一致（`682aac9d…`）⇒ 门控测的是新二进制而非旧件。**符合**。
11. 越界自查：`git status --porcelain -uall` = 6 项，与 `spec/`、`contracts/`、`components/llvm-project/**` 交集**空**；未改 `helper.c`（纯 TCG，无需 helper）。**符合**。

**Finding 处置**

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `trans_*` 名与任务书简写（`trans_rev_o`）不一致；门控按 `opcodes.yaml.id` 派生名精确匹配 | ✅已按真源落地并披露 | 用 `trans_rev_{o,t,w,b}_orri_rd` | `check_qemu_trans --strict` 231/231；`check-interface` 83/83 |
| F2 改 QEMU 后若未 `make install-host`，门控测**旧**二进制（旧件+旧生成物自洽、门控不可察） | ✅已处置（按 `Makefile` 既有前置） | 重建后执行 `make install-host`（rc=0） | 安装根/构建树 QEMU md5 相同（`682aac9d…`）；L2 231/231 |
| F3 仅「向量级」注入不足以证明 QEMU **实现**被比对 | ✅已补（新增注入 C） | 源树去单元倒序 + 重建 ⇒ 40 FAIL；`cp`+md5 还原 ⇒ 回绿 | `run-c.sh --inject` PASS=13 FAIL=0；还原后 `git status` 干净 |
| F4 `insn.decode` 头计数由脚本硬编码（`256`）与现场数（`231`）不一致 | ⏸披露不改（既有惯例：提交版按现场数维护） | 未改生成器（改生成器属越界/另立任务） | 「新发现/坑」② |

**判决**：全部 finding 已处置（F1/F2/F3 已处置，F4 为显式披露/延后）。本环**未发现** `rev.{o,t,w,b}` 的 QEMU 执行**缺陷**（语义 80/80 + 62/62 双向量经独立 oracle 全等；`ILLI` 真实退出码 0x88）。阶段级状态：**C 完成 → 待验收**（任务级 `**状态**` = `待验收`）。
