# SPEC-142t: `rev.{o,t,w,b}`（逐块反转）指令落地

**模块**：spec
**项目里程碑**：M8
**依赖**：`ADR-0012 D10`（**前置：`D10.1`–`D10.8` 已逐条确认完成 ✓** —— 用户 2026-10-14 原话「**D10.1-D10.8 认可**」，见 `adr-0012 §D10.0` / `§状态说明`；`D10.6a` 已定案 (b)，**`D10.6b` 亦已定案 = `scope: m8`**）；`SPEC-141t`（ISA 指令扩展预研，**只读**来源）；`INFRA-078t`（compiler-rt 预研：`bswap` 缺口来源，**只读**）；`docs/Process-06`（`spec/` 目录保护）；`ADR-0012 D4`（`spec/` 只读策略）
**状态**：待验收
**阶段进度**：A 契约/编码层 ✅ 已验证（2026-10-15，reviewer `Accepted`）；B MC ⏳ 待做；C QEMU ⏳ 待做

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
