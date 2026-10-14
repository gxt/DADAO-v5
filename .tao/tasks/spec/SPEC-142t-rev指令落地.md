# SPEC-142t: `rev.{o,t,w,b}`（逐块反转）指令落地

**模块**：spec
**项目里程碑**：M8
**依赖**：`ADR-0012 D10`（**前置：`D10.1`–`D10.8` 已逐条确认完成 ✓** —— 用户 2026-10-14 原话「**D10.1-D10.8 认可**」，见 `adr-0012 §D10.0` / `§状态说明`；`D10.6a` 已定案 (b)，**唯 `D10.6b` 仍待确认**）；`SPEC-141t`（ISA 指令扩展预研，**只读**来源）；`INFRA-078t`（compiler-rt 预研：`bswap` 缺口来源，**只读**）；`docs/Process-06`（`spec/` 目录保护）；`ADR-0012 D4`（`spec/` 只读策略）
**状态**：待开始

## 执行环境
**执行环境**：本地

> ✅ **开工前置（已满足）**：本任务书对应 `ADR-0012 D10`；用户 **2026-10-14 已逐条确认** `D10.1`–`D10.8`（原话「**D10.1-D10.8 认可**」）⇒ `D10` 已 `Accepted`（**唯 `D10.6b` 仍待确认**，见「`D10.6a` 定案 / 待用户确认项」）。用户原话/日期已补入本任务书「立项来源 / 用户裁定落纸」段与 `adr-0012 §状态说明`，可 `/dispatch`。

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
  - 「`D10.1-D10.8` 认可」⇒ **逐条确认完成 ✓**（**唯 `D10.6b` 仍待确认**）。
- **本任务 = 执行落点**：把上列 **已确认** 的 `D10` 决策**逐条落到全链**（`spec/` + `contracts/` + 生成器 + 向量 + MC + QEMU + 门控）。**`D10.6b` 未确认 ⇒ 不得自行选定**（见「`D10.6a` 定案 / 待用户确认项」）。

## 目的

为 `SimRISC` 新增 **4 条** `rev` 指令（`rev.o`/`rev.t`/`rev.w`/`rev.b`），提供**逐块（块内按位单元）反转**能力，从而以**单条指令**覆盖 `__bswapdi2`/`__bswapsi2`（`bswap` 类）与位反转（`bitreverse`）需求（对比 ARM/RISC-V 需 2 条组合）——为 `INFRA-079t`（compiler-rt builtins 接入）的 hw 特化提供 ISA 支撑（`ADR-0027 D3`）。

## 指令契约（**自包含**；与 `adr-0012 §D10` 一致）

### 1. 格式与编码

四条统一 `orri` 格式：`opx`（= `ha`，`bits[23:18]`）+ 两个寄存器 + 6 位立即数在 `hd[5:0]`。

| 指令 | `id` | 子表 | `op` | `ha` | `mask` | `value` |
|---|---|---|---|---|---|---|
| `rev.o` | `rev.o_orri_rd` | `MISC-octa` | `0x40` | `0x0C` | `0xFFFC0000` | `0x400C0000` |
| `rev.t` | `rev.t_orri_rd` | `MISC-tetra` | `0x41` | `0x0C` | `0xFFFC0000` | `0x410C0000` |
| `rev.w` | `rev.w_orri_rd` | `MISC-wyde` | `0x42` | `0x0C` | `0xFFFC0000` | `0x420C0000` |
| `rev.b` | `rev.b_orri_rd` | `MISC-byte` | `0x43` | `0x0C` | `0xFFFC0000` | `0x430C0000` |

- `opx = 001100`（行 `001-xxx` × 列 `xxx-100`）；`value = op<<24 | ha<<18`。
- 字段：`rdhb`（**目的**，`bits[17:12]`，bank `rd`）/ `rdhc`（**源**，`bits[11:6]`，bank `rd`）/ `immu6`（`bits[5:0]`，**无符号**）。
- 汇编语法（`spec/Toolchain-01 §…` `orri` 行）：`rev.o rdHB, rdHC, immu6`（例：`rev.o rd8, rd9, 8`）。
- **不冲突**（现场已核）：`001-100` 在四个子表均为空；`SPEC-069t` 的 reserved/已删集 = 每子表 8 条（`001-000…011` 4 逻辑 + `010/011-000/001` 2 ext×2 格式），**不含 `001-100`**；`contracts/opcodes.yaml` 无 `ha: '0x0C'` / `0x??0C0000` 条目。

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

## `D10.6a` 定案 / 待用户确认项

1. **`D10.6a` 正文分册归位 = 定案 (b) 分册**（用户 2026-10-14 裁定原话「**1、分册写**」）：`.o`→`spec/SimRISC-04`、`.t`→`08`、`.w`→`09`、`.b`→`10`；逐块语义**总述置于 `04 §4.2`**、其余三册（`08/09/10`）**引用**。**据此可动 `spec/` 正文（分册 = `04/08/09/10`）。**
2. **`D10.6b` `scope` 取值（待用户确认 ✗，不得自行选定）**：建议 `scope: m8`（仿 `scope: m3` 先例；须同步 `tools/spec/check_scope.py` 的 `ALLOWED_SCOPES` + 分区计数 + 注释）。**确认前不得写 `opcodes.yaml` / `check_scope.py`。**

## 分阶段实现（**定案**）

> 落地方案由主会话定（**用户 2026-10-14 裁定原话「2、你来定」授权**）。原「分阶段分解建议（建议，待用户确认）」**已随该裁定转为定案**。方案 = **一个任务书、三阶段验收**。

- **阶段 A（契约 / 编码层，单任务可验收）**：`spec/SimRISC-00` QFC 四子表 + `SimRISC-04/08/09/10` 分册正文（依 `D10.6a` 定案 (b)）+ 各册 `LEGALITY` 生成区（`tools/spec/gen_legality_list.py --apply`）+ `contracts/opcodes.yaml`（生成器 `tools/spec/generate_opcodes.py`）+ `contracts/legality_rules.yaml`（`encode_onehot`）+ `.tao/knowledge/contract-isa.md` / `contract-asm-list.md`（`tools/llvm/gen_asm_list.py`）+ `tests/vectors/**` + `inventory.md` + `tools/testcases/generate_isa_vectors.py`。
- **阶段 B（MC）**：`DADAOInstrInfo.td`（def/mnemonic/编码）、`DADAOAsmParser`（`orri` 受理）、`DADAOInstPrinter`、`MCCodeEmitter`/decode；`check-instrinfo` / `check-isa-coverage` 回绿。
- **阶段 C（QEMU）**：`insn.decode`（四条 token）+ `trans_rev.c.inc`（`trans_rev_o`/`_t`/`_w`/`_b`）+ `translate.c` 分派（`helper.c` 如需）；语义向量经 QEMU 跑通。
- **定案理由**（主会话，2026-10-14，授权 = 用户原话「2、你来定」）：① 与 `D9`（新增 `sub.o`）「全链单任务」惯例一致；② 三部分共享**同一编码真源**，拆开易漂移；③ 阶段化验收让**契约层先独立可验**（Spec-first），问题早暴露。
- **依赖关系**：**阶段 A → 阶段 B / 阶段 C**（编码 / 契约先行）；阶段 B 与阶段 C 可并行（**不同补丁树**），但若同改 `contracts/` 或 `tests/vectors/` 则**串行**（`AGENTS.md` 并行任务上限）。

## 接口规范

- **输入**：`adr-0012 §D10`（**决策（已由用户逐条确认 ✓）**，含用户原话）；`spec/SimRISC-00 §3.1/§4.2–§4.5`（QFC 子表，**只读**）；`contracts/opcodes.yaml` / `contracts/legality_rules.yaml`（**真源**）；`spec/Toolchain-01`（`orri` 汇编语法）；`tools/spec/generate_opcodes.py`、`tools/spec/gen_legality_list.py`、`tools/llvm/gen_asm_list.py`、`tools/testcases/generate_isa_vectors.py`；`components/llvm-project/patches/llvm/lib/Target/DADAO/**`、`components/qemu/patches/target/dadao/**`。
- **输出**：`spec/SimRISC-00`（+ `04/08/09/10` 分册正文，依 `D10.6a` 定案 (b)）、`contracts/opcodes.yaml`（**生成**）、`contracts/legality_rules.yaml`、`.tao/knowledge/contract-isa.md`、`contract-asm-list.md`（**生成**）、`tests/vectors/**` + `inventory.md`、MC 补丁、QEMU 补丁、门控；完成区（**≤30 行**）+ 一键证据脚本。
- **越界声明（硬性）**：改 `spec/**` **仅限**本任务书授权的四子表 / 分册正文（`04/08/09/10`，依 `D10.6a` 定案 (b)）/ 生成区（授权原话见上）；**同一变更内**须更新 `manifests/spec-readonly.lock.toml` 对应册 `sha256`（`Process-06 §5`）；**未经确认不得**动 `spec/` 正文。

## 验收标准

1. `**状态**` = `待开始`（开工前）→ `待验收`（实现后）；本任务书**自包含**（执行不需依赖外部仓库内容）；`**项目里程碑**` = `M8`。
2. **前置状态**：`adr-0012 §D10` 的 `D10.1`–`D10.8` **已逐条确认**（用户 2026-10-14 原话「**D10.1-D10.8 认可**」已落纸于本任务书 + `ADR §状态说明`）；`D10.6a` **已定案 (b) 分册**；**`D10.6b`（`scope` 取值）仍待用户确认 ⇒ 涉及 `scope` 的写入**（`contracts/opcodes.yaml` / `check_scope.py`）**须待确认后方执行**（其余阶段可先落地）。
3. **编码逐条**：四条 `value`/`mask`/`op`/`ha` 与「指令契约 §1」**逐字一致**；`tools/spec/generate_opcodes.py` 生成结果与 `contracts/opcodes.yaml` **幂等**（`--check`/重生成 diff = 0）；`validate-encoding` rc=0。
4. **语义逐条（独立 oracle，禁从 LLVM/QEMU 反推）**：以 Python 大整数**独立实现**逐块反转，对**每条指令 × 每个合法 `k`**（见下）以及边界（`rdHC=0`、`rdHC` 全 1、`rdHB==rdHC`、`rdHC=rd0`）产出期望值；向量经 QEMU 实跑**全部一致**。**端序 = 大端（本项目为大端）**，端序敏感用例须显式覆盖。
   - 合法集覆盖：`.o` `k∈{1,2,4,8,16,32}` / `.t` `k∈{1,2,4,8,16}` / `.w` `k∈{1,2,4,8}` / `.b` `k∈{1,2,4}` —— **计数现场统计、不写死**。
5. **合法性逐条**：`k` 非 one-hot 或 `k ≥ S` ⇒ **ILLI**（含 `k=0`、`k=S` 恒等档）；`rdhb == rd0` ⇒ ILLI；`rdhc == rd0` / `rdhb == rdhc` ⇒ **不**报 ILLI。每条断言均有**可达 FAIL 路径**（独立注入一次反例：注入 ⇒ FAIL ⇒ `cp`+md5 还原 ⇒ 回绿）。
6. **同步面齐备**（`D10.6` 逐项，缺项须显式标「本环不涉及 + 理由」）：四子表 + 计数、分册正文（`04/08/09/10`，依 `D10.6a` 定案 (b)）、各册 `LEGALITY` 生成区、`opcodes.yaml`、`legality_rules.yaml`、`contract-isa.md`、`contract-asm-list.md`、`tests/vectors/**` + `inventory.md`、MC、QEMU、门控。
7. **门控**：`make check`(L1)、`make check-modules`(L2) 各 **rc=0**；语义向量（`check-qemu-semantics` 或等价，含新增 `rev` 向量）rc=0；`check-isa-coverage` / `check-instrinfo` / `check-asm-list-drift` / `check-legality-drift` / `check-legality-invariants` / `check-rule-refs` / `check-spec-readonly` 各 rc=0；`check-no-residue` / `check-knowledge-refs` / `tools/infra/check_issues.py` 各 rc=0。
8. **`spec/` 授权与锁**：`git diff --name-only` 与 `spec/` 清单交集**均为本任务书授权范围**；变动的只读册 `sha256` 已在**同一变更**内更新（`make check-spec-readonly` rc=0）。
9. **一键证据脚本**（`.work/evidence/<本任务ID>/`）：非交互、任一失败非零退出、逐项打印「检查名 + 期望/实际 + rc」、含**可达 FAIL** 自检（**计数不写死**，现场统计）。
10. 完成区（**≤30 行**）与真实输出**逐条对齐**；长输出留 `.work/log/spec/**`（指针给出）；**禁** `cmd | tee` 吞码。

## 硬约束（下发提示必带）

1. **临时目录** `/tmp/opencode/<本任务ID>/`；命令一律在 **workdir（= 仓库根）** 内、用**相对路径**；**禁**出界 `cd`（绝对 / `~` / `..`）；禁仓库内临时文件。
2. **不提交 git**（提交权归 architect）；显式 staging（**禁** `git add -A`/`.`）。
3. **前置边界**：`D10` 已逐条确认、`D10.6a` 已定案 (b)；**`D10.6b` 未确认 ⇒ 涉及 `scope` 的写入（`opcodes.yaml` / `check_scope.py`）停下报告**，不自行选定。
4. **Spec-first**：期望值来自 `contracts/`/`contract-isa.md` 与本任务书契约，**不从 LLVM/QEMU 反推**；**独立 oracle** 用 Python 大整数算法定义独立派生。
5. **`spec/` 保护**：改 `spec/**` 仅限授权范围；同一变更内更新 `manifests/spec-readonly.lock.toml` 的 `sha256`（`Process-06 §5`）。
6. **完成区与真实输出逐条对齐**；**计数不写死**；事实与推测分开；复杂命令输出留 `.work/log/spec/**`。
7. **失败保留现场并继续推进**（自行处置：查证 / 绕行 / 有据重试并记录次数 / 登记后跳过）；**只在需用户语义裁定（新决策 / 需授权）时留问**，禁自拟自答；**不得以重试掩盖根因**。
8. **补丁导出纪律**：MC/QEMU 改动按 `docs/Process-01` 树形补丁集（一文件一补丁 + `git apply`），`check-patch-tree` 须绿。
9. **反例注入还原纪律**：**禁** `git checkout`/`restore`/`stash`/`git show <commit>:<path>`；一律 `cp` 备份 + md5 对账，或临时树注入。
10. 文本**不写**字面 `.work/<具体路径>`（用 `<>` 占位）；任务书**自包含**。

## 参考检索（`DADAO-0628`，**内容溯源，非执行必需**）

> 规划期只读检索 `.cache/refs/DADAO-0628/**`（**不复制代码、不作执行依赖**）。
>
> - **0628 做法**：无 `rev`/`bswap` 相关 ISA 指令（`grep` 0 命中，含 `sail/dadao_insts.sail`）；其 ISA 真源为 `sail/dadao_insts.sail` + 机器可读编码表，扩展流程以「权威 spec 先行」固化（`ADR-0011`）。
> - **本项目差异**：真源 = `spec/SimRISC-00` QFC 子表 + `contracts/opcodes.yaml`（生成器）+ `manifests/spec-readonly.lock.toml` 哈希锁 + L1 编码门控。
> - **建议落点**：沿用本项目既有全链同步面（本任务书「指令契约」+ `D10.6` 十项），**不引入** 0628 的 sail 路径。

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
