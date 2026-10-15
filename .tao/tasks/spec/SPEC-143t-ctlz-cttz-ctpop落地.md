# SPEC-143t: `ctlz`/`cttz`/`ctpop`（位扫描与计数）指令落地

**模块**：spec
**项目里程碑**：M8
**依赖**：`ADR-0012 D11`（**前置已全部满足 ✓**：`D11.1`–`D11.10` 用户 2026-10-14 **逐条确认** ✓〔原话「**D11全部认可**」〕+ **改 `spec/` 授权** ✓〔原话「**同样授权**」，与 `SPEC-142t` 的「a/b授权」同样〕——见「开工前置」与 `adr-0012 §状态说明`；`D11` 已 `Accepted`）；`SPEC-141t`（ISA 指令扩展预研，候选 `C2` = `clz`/`ctz`/`popcount`，**只读**来源）；`INFRA-078t`（compiler-rt 预研：缺口来源，**只读**）；`LLVM-079t`（现状：`CTLZ`/`CTTZ`/`CTPOP` 走 `Expand`，**只读**溯源）；`docs/Process-06`（`spec/` 目录保护）；`ADR-0012 D4`（`spec/` 只读策略）。**串行**：与 `SPEC-142t`（`rev.{o,t,w,b}` 落地）**须串行**（同改 `contracts/opcodes.yaml` / `tests/vectors/**`），先后由主会话排定。
**状态**：待验收
**阶段进度**：A 契约/编码层 ✅ 已验证（2026-10-15，reviewer `Accepted`；**含 3 项结构性 known-red**〔`ISS-215`〕，见「完成区」⚠）；B MC ⏳ 待做；C QEMU ⏳ 待做

> **`**状态**` 口径**：本任务 = **一个任务书、三阶段验收**（照 `SPEC-142t`）⇒ `**状态**` 表**任务级**进度（**整体未完成**，故**不**置 `已验证`）；**阶段级**进度见上行 `**阶段进度**`（阶段 A 已由 reviewer `Accepted`，见「第 1 轮 reviewer 审阅」）。

## 执行环境
**执行环境**：本地

> ✅ **开工前置（已全部满足 ✓ ⇒ 可下发；但须与 `SPEC-142t` 串行）**：① `ADR-0012 D11` 的 `D11.1`–`D11.10` 已经用户 **2026-10-14 逐条确认** ✓（原话「**D11全部认可**」）；② **已取得用户对改 `spec/` 的明确授权** ✓（`docs/Process-06 §2`：`spec/` 下任何新增/修改/删除均须用户**事先**明确允许）——用户原话「**同样授权**」⇒ `SPEC-143t` 与 `SPEC-142t`（原话「**a/b授权**」）**同样已获改 `spec/` 的授权**（授权原话留存本任务书）；③ 与 `SPEC-142t` 的**先后顺序由主会话排定**（两者同改共享文件，不得并行）⇒ **本任务可下发，但须与 `SPEC-142t` 串行**。

## 立项来源 / 用户裁定落纸

- **来源**：`ADR-0012 D11`（**2026-10-14 新增；已由用户逐条确认 ✓**，见下）＝ `SPEC-141t §候选` 预研候选 **`C2`（`clz`/`ctz`/`popcount`）** 的**落地路径 = 新增 ISA 指令**（用户 2026-10-14 经主会话问答裁定「**可以增加部分指令**」并指定实现范围，见 `adr-0012 §D11.0`）。
- **用户裁定原话（原样引录，渠道 = 经主会话问答，2026-10-14；完整引录见 `adr-0012 §D11.0`）**：
  - 指令名：「**ctlz/cttz/ctpop**」
  - 范围：「**先就这三个吧**」⇒ `cls`/`clo`/`cto`/`parity`/`ffs`/`ffz` 等**首版不做**
  - 编码：「**ctlz/cttz/ctpop 的 opx：011-110/011-111/011-101**」
  - 前序已接受：① `ctlz(0)`/`cttz(0)` **定值 = 范围宽度（`hd+1`）**；② **不需要 `encode_onehot`**；③ **无后缀**（编码借 `MISC-octa` 格位）；④ `cttz` 的 `hd` 语义「保持 `[hd:0]` 上界」= 主会话建议，**用户 2026-10-14 确认 ✓**（见下）。
- **逐条确认（原话原样引录，渠道 = 经主会话问答，2026-10-14）**：用户原话「**D11全部认可**」⇒ `D11.1`–`D11.10` **逐条确认完成** ✓（含 `D11.4` 保持 `[hd:0]` 上界 ✓、`D11.9` 归位 = `SimRISC-04 §4.2` ✓）⇒ `D11` 已 `Accepted`（见 `adr-0012 §状态说明`）；**无未决项**。
- **授权（满足 `docs/Process-06 §2`）**：用户原话「**同样授权**」（渠道 = 经主会话问答，2026-10-14）⇒ `SPEC-143t` 与 `SPEC-142t` 的「**a/b授权**」**同样**——**授权修改 `ADR-0012` + `spec/SimRISC-00` + `contracts/opcodes.yaml`** ✓（本任务**不新增** `legality_rules.yaml` 规则，见 `D11.6`）。
- **新增硬要求（用户 2026-10-14；原话原样引录，渠道 = 经主会话问答）**：「**关于scope的事情，增加指令与里程碑并没有绑定关系，不必纠结类似问题，甚至于不必额外记录，只需在SimRISC版本记录中写明即可**」⇒ ① 新增指令与里程碑**无绑定关系**；② **不必额外记录**（**不**新增 `scope` 说明段；`scope` 只按 `m8` 落 `contracts/`）；③ **新增的 3 条指令须在 `SimRISC` 的「版本与变更记录」区写明**（`SimRISC-00` 与 `SimRISC-04`）。
- **本任务 = 执行落点**：把 `D11` 的决策**逐条落到全链**（`spec/` + `contracts/` + 生成器 + 向量 + MC + QEMU + 门控）。**`D11` 已逐条确认 ✓、`spec/` 授权已获 ✓、`D11.4`/`D11.9` 已裁决 ✓ ⇒ 无未决项**，可下发（须与 `SPEC-142t` 串行）。

## 目的

为 `SimRISC` 新增 **3 条** 位扫描/计数指令（`ctlz` 前导零 / `cttz` 末尾零 / `ctpop` 置位数），以**单条指令**覆盖 **8/16/32/64 位任意宽度**（由 `hd` 指定有效位上界），为后端 `int_ctlz`/`int_cttz`/`int_ctpop` 提供 ISA 支撑——替代当前的软件展开（`LLVM-079t`：`CTLZ`/`CTTZ`/`CTPOP` 走 `Expand`，展开为 `xnor.o`/`and.o`/`sub.uo`/`shr.uo`/`mul.uo`）。对比 RISC-V 的 `clz` + `clzw` **两条**才覆盖到 32 位，本方案一条即覆盖到任意宽度。

## 指令契约（**自包含**；与 `adr-0012 §D11` 一致）

### 1. 格式与编码

三条统一 `orri` 格式：`opx`（= `ha`，`bits[23:18]`）+ 两个寄存器 + 6 位立即数在 `hd[5:0]`；主 op = `MISC-octa` = `0x40`。

| 指令 | `id` | 子表 | `op` | `opx` | `mask` |
|---|---|---|---|---|---|
| `ctpop` | `ctpop_orri_rd` | `MISC-octa` | `0x40` | `011-101`（`0x1D` = 29） | `0xFFFC0000` |
| `ctlz` | `ctlz_orri_rd` | `MISC-octa` | `0x40` | `011-110`（`0x1E` = 30） | `0xFFFC0000` |
| `cttz` | `cttz_orri_rd` | `MISC-octa` | `0x40` | `011-111`（`0x1F` = 31） | `0xFFFC0000` |

- **`value` 以 `contracts/opcodes.yaml`（生成器 `tools/spec/generate_opcodes.py` 产出）为唯一真源，本任务书不复写**（用户 2026-10-15 口径：按位域写清楚，派生值由生成器算）。
- `opx` 在 `bits[23:18]`（= `ha`）；`value = op<<24 | opx<<18` **由生成器计算**（本任务书**不写具体值**）；`mask = 0xFFFC0000`（锁 `op` + `opx`）。
- 字段：`rdhb`（**目的**，`bits[17:12]`，bank `rd`）／`rdhc`（**源**，`bits[11:6]`，bank `rd`）／`hd`（`bits[5:0]`，**无符号立即数**，**有效位上界**）。**注**：`opcodes.yaml` 中该立即数字段惯用名 **`immu6`**（`role: imm`、`bank: imm`、`signed: false`，先例 `ext.uo_orri_rd`）。
- 汇编语法（`spec/Toolchain-01 §5` 的 `orri` 行 = `助记符 dst, src, immu6`）：`ctlz rdHB, rdHC, hd`（例：`ctlz rd8, rd9, 63`）。
- **不冲突**（现场已核，三条实证）：① `spec/SimRISC-00 §4.2 MISC-octa` 第 `011-xxx` 行**仅** `000`–`100` 有条目，`101`/`110`/`111` **三格为空**（reserved）；② `SPEC-069t` 的 reserved/已删集 = 每子表 8 条（`001-000…011` 4 逻辑 + `010/011-000/001` 2 ext × 2 格式），**不含 `011-101/110/111`**；③ `contracts/opcodes.yaml` 中 `op: '0x40'` 的 32 条，`ha` 集合 = `{8–11, 16–20, 24–28, 42–46, 48–54, 56–59, 61–62}` ⇒ **29/30/31 无条目**（对应 `value` 见真源，本任务书不复写）。

### 2. 语义（`hd` = 有效位上界，三条统一）

- **有效位** = `rdHC[hd:0]`（共 **`hd+1`** 位，`hd ∈ 0..63`）；`hd` 以上的位**不参与**运算。
- `ctlz`：从 bit `hd` **向下**数前导零（到首个 1 为止）⇒ 有效位内的前导零个数。伪代码：`n=0; for i = hd down to 0: if bit(i)==1 break; n++`。
- `cttz`：从 bit 0 **向上**数末尾零（到 bit `hd` 为止）⇒ 有效位内的末尾零个数。伪代码：`n=0; for i = 0 up to hd: if bit(i)==1 break; n++`。
- `ctpop`：`rdHC[hd:0]` 内 **1 的个数**。
- **`cttz` 的 `hd` 作「上界」（`[hd:0]`）—— 用户 2026-10-14 确认 ✓**（备选「下界」语义见 `D11.10(b)`，**已否**）。

### 3. 定值（全 0 / 无 1）

- `rdHC[hd:0]` **全 0** 时：`ctlz` = `cttz` = **`hd+1`**（= 有效位范围宽度，**消除 UB**）。口径与 RISC-V（`clz`/`ctz` 返回 XLEN）、x86（`lzcnt`/`tzcnt` 返回操作数宽度）、ARM（`CLZ(0)` = 32/64）一致；对比 C `__builtin_clz(0)` 为 **UB**。
- `ctpop(0)` = `0`（自然值，无特例）。

### 4. 合法性

- `hd ∈ 0..63`（6 位立即数域）⇒ **全部合法**，**无非法 `hd` 值** ⇒ **不新增** `encode_onehot`，**不新增**任何合法性规则。
- 沿用既有 **`dst_rd0`**：`rdhb != rd0`（目的不得为 `rd0`）。
- `rdhc` **可为 `rd0`**（读出 0 ⇒ 结果 = `hd+1` 或 0，合法）；**`rdhb == rdhc` 允许**（原地运算）。
- 先例：`ext.uo_orri_rd` = `rule_refs: [dst_rd0]` + `legality: [rdhb != rd0]`。

### 5. 结果语义与用途映射

- **结果 ∈ `0..64`，写满 64 位**（值语义；非「只写低位 / 高位保持」），与 `SPEC-069t` 值语义通则一致。
- ↔ LLVM `int_ctlz`/`int_cttz`/`int_ctpop`（1:1）↔ C++20 `std::countl_zero`/`countr_zero`/`popcount`。
- `ctlz` **单条**覆盖 `clz8`/`clz16`/`clz32`/`clz64`（`hd` = 7/15/31/63）——对比 RISC-V 需 `clz` + `clzw` 两条。
- **本任务不含 LLVM ISel 接入**（`int_ctlz` 等 → 单指令）：`D11.9` 未列，**另立任务**。

## 待用户确认项

**无未决项 ✓**（2026-10-14，全部已裁决）：

1. **`D11` 逐条确认 —— 已完成 ✓**：用户原话「**D11全部认可**」⇒ `D11.1`–`D11.10` **逐条确认完成**（`D11` 已 `Accepted`，见 `adr-0012 §状态说明`）。
2. **`spec/` 修改授权 —— 已获 ✓**（`docs/Process-06 §2`）：用户原话「**同样授权**」⇒ 与 `SPEC-142t` 的「**a/b授权**」同样；授权原话已留存本任务书「立项来源 / 用户裁定落纸」。
3. **`D11.4`（`cttz` 的 `hd` 语义）—— 已确认 ✓**：保持「**上界**（`[hd:0]`）」（用户 2026-10-14；备选「下界」见 `D11.10(b)`，已否）。
4. **`D11.9` 正文分册归位 —— 已确认 ✓**：**`spec/SimRISC-04 §4.2`（`Bit manipulating：位操作指令`）**（与 `rev` 总述同处；用户 2026-10-14）。
5. **`scope` 取值 —— 已定案 = `scope: m8`**（用户 2026-10-14；见 `adr-0012 §D10.6b`）。`opcodes.yaml` / `check_scope.py` 的 `scope` 写入**可执行**（按 `m8`）。

## 分阶段实现（照 `SPEC-142t` 三阶段；**一个任务书、三阶段验收**）

- **阶段 A（契约 / 编码层，单任务可验收）**：`spec/SimRISC-00` QFC `§4.2` 三格 + 例外说明一句 + 计数 + **「附录：版本与变更记录」区写明本批 3 条指令**（硬要求）；`spec/SimRISC-04 §4.2` 正文（**已确认**）+ 各册 `LEGALITY` 生成区（`tools/spec/gen_legality_list.py --apply`）+ `contracts/opcodes.yaml`（`tools/spec/generate_opcodes.py`）+ `.tao/contracts/contract-isa.md` / `contract-asm-list.md`（`tools/llvm/gen_asm_list.py`）+ `tests/vectors/**` + `inventory.md` + `tools/testcases/generate_isa_vectors.py`。
- **阶段 B（MC）**：`DADAOInstrInfo.td`（def/mnemonic/编码）、`DADAOAsmParser`（`orri` 受理）、`DADAOInstPrinter`、`MCCodeEmitter`/decode；`check-instrinfo` / `check-isa-coverage` 回绿。
- **阶段 C（QEMU）**：`insn.decode`（三条 token）+ `trans_ctlz`/`trans_cttz`/`trans_ctpop` + `translate.c` 分派；语义向量经 QEMU 跑通。
- **依赖关系**：**阶段 A → 阶段 B / 阶段 C**（编码/契约先行）；B/C 可并行（不同补丁树），同改 `contracts/` 或 `tests/vectors/` 时**串行**。
- **理由**：与 `D9`/`D10` 的「全链单任务」惯例一致；三阶段共享同一编码真源；阶段化验收让契约层先独立可验（Spec-first）。

## 接口规范

- **输入**：`adr-0012 §D11`（**决策（已由用户逐条确认 ✓）**，含用户原话）；`spec/SimRISC-00 §3.1/§4.2`（QFC 子表，**只读**，改须授权）；`contracts/opcodes.yaml` / `contracts/legality_rules.yaml`（**真源**）；`spec/Toolchain-01 §5`（`orri` 汇编语法）；`tools/spec/generate_opcodes.py`、`tools/spec/gen_legality_list.py`、`tools/llvm/gen_asm_list.py`、`tools/testcases/generate_isa_vectors.py`；`components/llvm-project/patches/llvm/lib/Target/DADAO/**`、`components/qemu/patches/target/dadao/**`。
- **输出**：`spec/SimRISC-00` + `spec/SimRISC-04`（**已授权 / 已确认**）、`contracts/opcodes.yaml`（**生成**）、`.tao/contracts/contract-isa.md`、`contract-asm-list.md`（**生成**）、`tests/vectors/**` + `inventory.md`、MC 补丁、QEMU 补丁、门控；完成区（**≤30 行**）+ 一键证据脚本（`.work/evidence/<本任务ID>/`）。
- **越界声明（硬性）**：改 `spec/**` **仅限**授权的 `SimRISC-00 §4.2` 三格 + 例外说明 + 计数 + `SimRISC-04 §4.2` 正文 / 生成区（**均已确认**），**以及** `SimRISC-00` / `SimRISC-04` 的「**附录：版本与变更记录**」区（硬要求）；**同一变更内**须更新 `manifests/spec-readonly.lock.toml` 对应册 `sha256`（`Process-06 §5`）。

## 验收标准

1. `**状态**` = `待开始`（开工前）→ `待验收`（实现后）；本任务书**自包含**；`**项目里程碑**` = `M8`。
2. **前置状态（已满足 ✓）**：`adr-0012 §D11` 的 `D11.1`–`D11.10` **已逐条确认**（原话「`D11全部认可`」）；**`spec/` 修改授权原话已在本任务书留存**（原话「`同样授权`」）；`D11.4`（`cttz` 上界）/`D11.9`（归位 = `SimRISC-04 §4.2`）**已裁决**（`scope` 已随 `D10.6b` 定案 = `m8`）——**本任务无未决项**。
3. **编码逐条**：三条 `op`/`opx`/`mask` 与「指令契约 §1」**逐字一致**；三条 `value` 以 `contracts/opcodes.yaml`（生成器产出）为**唯一真源**（本任务书**不复写**，用户 2026-10-15 口径）；`generate_opcodes.py` 生成结果与 `contracts/opcodes.yaml` **幂等**（重生成 diff = 0）；`validate-encoding` rc=0。
4. **语义逐条（独立 oracle，禁从 LLVM/QEMU 反推）**：以 **Python 大整数**独立实现三条语义（含 `hd` 边界），对**每条指令 × `hd` 代表集**（至少 `hd` = 7/15/31/63 与 `0`）以及边界（`rdHC=0`、`rdHC` 全 1、`rdHB==rdHC`、`rdHC=rd0`、`hd=0`、`hd=63`）产出期望值；向量经 QEMU 实跑**全部一致**。**端序 = 大端**（本项目为大端），端序敏感用例须显式覆盖。**计数现场统计、不写死**。
5. **定值逐条**：`rdHC[hd:0]` 全 0 ⇒ `ctlz` = `cttz` = **`hd+1`**（对 `hd` 各取值均验，含 `hd=63` ⇒ 64）；`ctpop(0)` = 0。
6. **合法性逐条**：`hd ∈ 0..63` **全部合法**（**无 `hd` 值触发 ILLI**——须含可达 FAIL 反例：把断言改成「存在非法 `hd`」应 FAIL）；`rdhb == rd0` ⇒ ILLI；`rdhc == rd0` / `rdhb == rdhc` ⇒ **不**报 ILLI；`contracts/legality_rules.yaml` **未新增**规则（diff 证）。每条断言均有**可达 FAIL 路径**（注入 ⇒ FAIL ⇒ `cp`+md5 还原 ⇒ 回绿）。
7. **同步面齐备**（`D11.9` 十项，缺项须显式标「本环不涉及 + 理由」）：`SimRISC-00 §4.2` 三格 + 例外说明 + 计数、`SimRISC-04 §4.2` 正文与生成区、`opcodes.yaml`、`contract-isa.md`/`contract-asm-list.md`、`tests/vectors/**` + `inventory.md`、MC、QEMU、门控；`legality_rules.yaml` **无新增**；ISel **不在本任务**（显式声明）。
8. **门控**：`make check`(L1)、`make check-modules`(L2) 各 **rc=0**；语义向量（`check-qemu-semantics` 或等价，含新增三条向量）rc=0；`check-isa-coverage` / `check-instrinfo` / `check-asm-list-drift` / `check-legality-drift` / `check-legality-invariants` / `check-rule-refs` / `check-scope` / `check-spec-readonly` 各 rc=0；`check-no-residue` / `check-knowledge-refs` / `tools/infra/check_issues.py` 各 rc=0。
9. **`spec/` 授权与锁**：`git diff --name-only` 与 `spec/` 清单交集**均为本任务书授权范围**；变动的只读册 `sha256` 已在**同一变更**内更新（`check-spec-readonly` rc=0）。
10. **一键证据脚本**：非交互、任一失败非零退出、逐项打印「检查名 + 期望/实际 + rc」、含**可达 FAIL** 自检（**计数不写死**）。完成区（**≤30 行**）与真实输出**逐条对齐**；长输出留 `.work/log/spec/**`（指针给出）；**禁** `cmd | tee` 吞码。
11. **版本记录（硬要求，用户 2026-10-14 原话「只需在SimRISC版本记录中写明即可」）**：新增的 3 条指令须在 `spec/SimRISC-00` 与 `spec/SimRISC-04` 的「**附录：版本与变更记录**」区**写明**（指令名 / 条数 / 日期），可 `grep` 核（门控 `tools/spec/check_spec_changelog.py` 保持 rc=0）。

## 硬约束（下发提示必带）

1. **临时目录** `/tmp/opencode/<本任务ID>/`；命令一律在 **workdir（= 仓库根）** 内、用**相对路径**；**禁**出界 `cd`（绝对 / `~` / `..`）；禁仓库内临时文件。
2. **不提交 git**（提交权归 architect）；显式 staging（**禁** `git add -A`/`.`）。
3. **前置边界（已满足 ✓）**：`D11` **已逐条确认**、**`spec/` 授权已获**、`D11.4`/`D11.9` **已裁决**（`scope` 已随 `D10.6b` 定案 = `m8`，无需再裁决）⇒ **可开工**；但**须与 `SPEC-142t` 串行**（见第 4 条）。
4. **与 `SPEC-142t` 串行**：两者同改 `contracts/opcodes.yaml` / `tests/vectors/**`（`AGENTS.md`「同改共享文件的任务一律串行」）⇒ **不得与 `SPEC-142t` 并行**；**先后顺序由主会话排定**；开工前须确认 `SPEC-142t` 的落地状态，避免同文件冲突。
5. **Spec-first**：期望值来自 `contracts/` / `contract-isa.md` 与本任务书契约，**不从 LLVM/QEMU 反推**；**独立 oracle** 用 Python 大整数独立派生。
6. **`spec/` 保护**：改 `spec/**` 仅限授权范围；同一变更内更新 `manifests/spec-readonly.lock.toml` 的 `sha256`（`Process-06 §5`）。
7. **完成区与真实输出逐条对齐**；**计数不写死**；事实与推测分开；复杂命令输出留 `.work/log/spec/**`。
8. **失败保留现场并继续推进**（自行处置：查证 / 绕行 / 有据重试并记录次数 / 登记后跳过）；**只在需用户语义裁定（新决策 / 需授权）时留问**，禁自拟自答；**不得以重试掩盖根因**。
9. **补丁导出纪律**：MC/QEMU 改动按 `docs/Process-01` 树形补丁集（一文件一补丁 + `git apply`），`check-patch-tree` 须绿。
10. **反例注入还原纪律**：**禁** `git checkout`/`restore`/`stash`/`git show <commit>:<path>`；一律 `cp` 备份 + md5 对账，或临时树注入。
11. 文本**不写**字面 `.work/<具体路径>`（用 `<>` 占位）；任务书**自包含**。
12. **版本记录（硬要求）**：新增指令须在 `spec/SimRISC-00` / `SimRISC-04` 的「**附录：版本与变更记录**」区**写明**（用户 2026-10-14 原话）；与「**不必额外记录**」并列——**不**新增 `scope` 说明段。

## 参考检索（`DADAO-0628`，**内容溯源，非执行必需**）

> 规划期只读检索 `.cache/refs/DADAO-0628/**`（**不复制代码、不作执行依赖**）。
>
> - **0628 做法**：ISA **无** `ctlz`/`cttz`/`ctpop`——`sail/`（含 `dadao_insts.sail`）与 `contracts/isa/` 对 `ctlz|cttz|ctpop|popcount` **`grep` 0 命中**（2026-10-14 现场）⇒ 0628 **未新增**此类指令；其唯一相关痕迹是 llvm-test-suite 用例 `popcount-clz-ctz` 失败，但 `ML-004b` 记录的**根因不同**（对齐 MALIGN / `codegen-call-clobbers-gprb-not-declared`），**并非缺指令**。
> - **本项目差异**：真源 = `spec/SimRISC-00` QFC 子表 + `contracts/opcodes.yaml`（生成器）+ `manifests/spec-readonly.lock.toml` 哈希锁 + L1 编码门控；本项目为**大端**。
> - **建议落点**：沿用本项目既有全链同步面（本任务书「指令契约」+ `D11.9` 十项），**不引入** 0628 的 sail 路径。

## 完成区

**⚠ 阶段 A 已知红（结构性；须架构裁定，见「新发现/坑」①）**：`check-instrinfo`(L1) rc=**2**（失败项**恰为** 3 条 `scope: m8` 记录缺 `.td` def ＝ 阶段 B 工作）；`check-interface`(L2) rc=**2**（缺 QEMU `trans_*` **恰为** 3 条 ＝ 阶段 C 工作）；`test-semihost` 依赖整个 `check`(L1) ⇒ **继承同一 red**（`make -o check test-semihost` rc=0，证 semihost 内容全绿）。**其余全部门控 rc=0**。根因：`validate_instrinfo.py` 的 **Check 2b** 系 `SPEC-142t` 阶段 B（2026-10-15 07:55）新增，要求「每条 `scope: m8` 记录恰有一个 `.td` def」——**晚于本任务书定稿**（2026-10-14 / 2026-10-15 07:40）⇒ 三阶段拆分与 Check 2b **结构性冲突**（`SPEC-142t` 阶段 A 无此冲突，因当时 Check 2b 尚不存在）。
**测试结果**：`./.work/evidence/SPEC-143t/run.sh` **PASS=54 FAIL=0**（rc=0）；`run.sh --inject` **PASS=11 FAIL=0**（5 组注入：①向量错值 ②spec 子表单元格改名 ③向量 `expected_fault` 置 ILLI ④`/tmp` opcodes 额外失败 ⑤合成日志多一 FAIL 项 —— 各使**目标断言** FAIL ⇒ `cp`+md5 还原 / 临时树 ⇒ 回绿）。
**修改文件**（`git diff --name-status -M`：14 M + 2 新 + 本任务书 = 17）：`spec/SimRISC-00`（MISC-octa `011-101/110/111` 三格 + 表下例外说明 + 附录）、`spec/SimRISC-04`（`§4.2.2` 语义 + `ASSEMBLY_LIST`/`LEGALITY` 生成区 + 册头分类计数 30→33 + 附录）；`contracts/opcodes.yaml`（生成，234 条）；`.tao/contracts/contract-isa.md`（`§2.8` 例外条 + `§6.4.4` + 附录 A.2 三行 + 新 A.9）+ `.tao/contracts/contract-asm-list.md`（生成）；`tests/vectors/bitcnt/bitcnt.yaml`（**新**）+ `tests/vectors/inventory.md`（非 M1 节）；`tools/testcases/generate_bitcnt_vectors.py`（**新**）+ `tools/testcases/generate_isa_vectors.py`（docstring 指针）；`tools/spec/generate_opcodes.py`、`check_scope.py`、`gen_legality_list.py`；`tools/llvm/gen_asm_list.py` + `llvm-isa-backend-matrix.{tsv,md}`（生成）；`manifests/spec-readonly.lock.toml`（2 册 sha256）。
**验收结果**（逐条对齐真实输出；日志 `.work/evidence/SPEC-143t/log/`、`.work/log/spec/SPEC-143t-*`）：
- **编码（现场机器核实；3 条逐条不抽样）**：`op=0x40`；`ha`= `0x1D`/`0x1E`/`0x1F`（= 行 `011-xxx` × 列 `xxx-101`/`110`/`111`）；`mask=0xFFFC0000`；`value` 由生成器派生 = `0x40740000`/`0x40780000`/`0x407C0000`（= `op<<24|opx<<18`；**本任务书未复写，真源 = `contracts/opcodes.yaml`**）；字段 = `rdhb`(dst,rd,`[17:12]`)/`rdhc`(src,rd,`[11:6]`)/`immu6`(imm,imm,`[5:0]`)；`scope=m8`；`rule_refs=['dst_rd0']`；**无** `decode`。QFC 子表单元格 ↔ yaml **差异 0**；同 opx 在 tetra/wyde/byte 三子表**均为空**（例外性核实）。
- **语义（独立 oracle，禁从 LLVM/QEMU 反推）**：`generate_bitcnt_vectors.py` 以 Python 大整数 **三条代码独立路径**（逐位循环 / 整数性质 `bit_length`+`x&-x` / MSB-first 位串）逐例互证，`--self-check` **1344 例全等**；向量 **414 cases**（encoding 3 + semantic 192 + boundary 216 + legality 3），`hd` **全量** 3×`0..63`（**192/192，不抽样**）、`hd` 全 64 取值**无 ILLI**；定值 `ctlz(0)=cttz(0)=hd+1`（含 `hd=63` ⇒ 64）、`ctpop(0)=0`；**大端**：逐 case 断言编码字大端字节序往返 + `op` 字节在最前；生成器 `--check` 逐字节一致（幂等）。
- **合法性**：`hd ∈ 0..63` **全部合法**（无非法 `hd` 值）；`rdhb=rd0` ⇒ ILLI（规则 `dst_rd0`）；`rdhc=rd0` / `rdhb==rdhc` **不**报错；`contracts/legality_rules.yaml` **无改动**（`git diff` 证）⇒ **未新增**任何合法性规则。
- **同步面**：`check-spec-readonly` rc=0（2 册 sha256 同变更内更新：SimRISC-00 `a9ec70cf…`→`05b965ee…`；SimRISC-04 `7d59f960…`→`000a12d0…`）；`check-spec-changelog`/`check-spec-refs`/`check-asm-list`/`check-asm-list-drift`/`check-asm-prose`/`check-spec-codeblocks`/`check-legality-drift`/`check-legality-invariants`/`check-scope`（m8=7、total=234）/`validate-encoding`/`check-rule-refs`/`check-isa-coverage`（矩阵重生成；三条 `td_def` 空 + ①层 `reject` = 阶段 B 依赖）/`check-spec-drift`/`check-patch-tree`/`check-index-blobs`/`check-cfx-aliases`/`check-dirs`/`check-no-residue`/`check-knowledge-*`/`check-contracts-dir`/`check-spec-numbering`/`check-components`/`check_issues`/`check-tasks` 各 rc=0。L2 其余子目标（`check-lit`/`check-qemu-smoke`/`test-codegen`/`test-elf`/`check-picolibc-tests`）逐项 rc=0。
- **版本记录（硬要求）**：`SimRISC-00`/`SimRISC-04` 附录 `-rc` 段均写明本批 3 条指令（`check-spec-changelog` rc=0）。
**新发现/坑**：①**`SPEC-142t` 阶段 B 新增的 Check 2b 与本任务书的三阶段拆分结构性冲突**（`m8` 记录被要求在同一变更内即有 `.td` def）⇒ 契约层（阶段 A）先行**必然**让 L1 `check-instrinfo` 红、且 `test-semihost` 因依赖 `check`(L1) 连带红；**须架构裁定**：接受阶段 A known-red（同 `SPEC-142t` 的 L2 口径）或把 3 条 `.td` def 提前进阶段 A。②`spec/SimRISC-00` 的例外说明须与**同子表无后缀**的 `rd2rd`/`rb2rb` 等寄存器组复制指令区分（首版误写「唯一例外」，自审已修）。③`gen_asm_list.classify()` **必须**显式接纳三条（否则落「其它」⇒ SimRISC-11，与正文归位 SimRISC-04 `§4.2.2` 及生成区矛盾）。④`README.md:73`「矩阵（227 条：①受理 217）」已陈旧（现 234 / ①221），本环**未改**（越界；`SPEC-142t` 亦未改）。⑤`check-isa-coverage` 的 ①层须 `llvm-mc`：三条现为 `reject`（阶段 B 后须 `make install-host` 再重生成矩阵，承 `SPEC-142t` B-a G1/G6 教训）。
**遗留问题**：①`check-instrinfo`(L1) / `check-interface`(L2) / `test-semihost` 三项 red **属阶段 B/C**（3 条 `.td` def / 3 条 QEMU `trans_*`）——**须架构裁定**（见「新发现/坑」①），本环**未弱化**任何门控；②阶段 B（MC）/阶段 C（QEMU）**未做**（任务书明确 ✗）；③`README.md` 陈旧计数未改（越界，见 ④）；④**未提交**（提交权归 architect）；**未越界**（未触 `components/**` / `contracts/legality_rules.yaml` / compiler-rt）。

## 审阅记录

#### 第 1 轮 engineer 自审

（自主逐行审查；对象 = 本环**新增/改动**的 `tools/**` 源码、`spec/` 正文与生成区、`contracts/`、向量与证据脚本。全局 `subagent_depth=1`，engineer 无法起嵌套子代理，故为自主逐行审查。）

**逐行审查意见与判决**

1. `generate_opcodes.py`（`build_misc_octa`）：`rec(mnem, mnem, "orri", op, f_orri("rdhb","rdhc","immu6"), ["rdhb != rd0"], S04_BIT, ha=ha, scope="m8")` ⇒ `id = {mnem}_orri_rd`；`op=0x40`、`ha=0x1D/0x1E/0x1F` ⇒ `mask=0xFFFC0000`、`value=op<<24|ha<<18` **由生成器派生**（未手写任何 value）。与「指令契约 §1」逐字一致。**正确**。
2. **未复写 `value`**：`spec/`/`.tao/contracts/`/本任务书只写**位域**（op/opx/mask/字段位置）；派生值仅由生成器产出、真源 = `contracts/opcodes.yaml`（用户 2026-10-15 口径 + `lessons §1.45`）。故 A.9 表**不含** `value` 列（与 A.8 的 `rev.*` 旧做法不同 ⇒ **披露**，见 F5）。**符合**。
3. `check_scope.py`：`EXPECTED_M8` 4→7、`EXPECTED_TOTAL` 231→234 + docstring 计数与 ADR 溯源同步；现场统计一致（`check-scope` PASS）。
4. `gen_asm_list.py::classify()` 新增 `ctlz/cttz/ctpop → "64位数据运算"`：**必需**（否则三条落「其它」⇒ SimRISC-11，与正文归位 SimRISC-04 `§4.2.2` / 生成区矛盾）。位置在 `.o` 后缀判据之前、其余分支之后 ⇒ 对既有 231 条**无副作用**（diff 仅 +4 行；`check-asm-list-drift`/`check-legality-drift` 逐字节 PASS）。**正确且最小**。
5. `generate_bitcnt_vectors.py` oracle：三条**代码独立**路径（逐位循环 / 整数性质 / MSB-first 位串）+ 定值断言 + 大端断言；无 `subprocess`（不调 LLVM/QEMU）；计数现场统计（414/192/64 均不写死）。**符合 Spec-first / 独立 oracle**。
6. 断言可达 FAIL：①向量错值 ⇒ `--check` FAIL；②spec 子表改名 ⇒ 单元格核对 FAIL；③向量 fault 化 ⇒ `check_bitcnt_hd.py` FAIL；④`/tmp` opcodes 额外失败 ⇒ `check_instrinfo_knownred.py` FAIL；⑤合成日志多一 FAIL 项 ⇒ `check_interface_knownred.py` FAIL。**五组各有可达 FAIL 且互不重复**（`--inject` 11/11 PASS）。
7. 还原纪律：①②③ 用 `cp` 备份 + md5 对账（**未**用 `git checkout`/`restore`/`stash`）；④⑤ 仅落 `/tmp/opencode/SPEC-143t/`（**不触仓库文件**）。**符合**。
8. 越界自查：`git diff --name-only` 与 `spec/` 交集 = `SimRISC-00`/`SimRISC-04`（**授权范围**）；未触 `components/**`（MC/QEMU 未动）、`contracts/legality_rules.yaml`（diff 证）、compiler-rt；`.tao/knowledge/` 未改（知识沉淀归 `/complete`）。**符合**。
9. `spec/` 保护（`Process-06 §5`）：变动的 2 册 sha256 **同一变更内**更新；`check-spec-readonly` rc=0。
10. 版本记录硬要求：2 册附录 `-rc` 段写明本批 3 条指令；`check-spec-changelog` rc=0。
11. `contract-isa.md` 新增文本逐段带 `[SimRISC-XX §…]` 引用；`check-spec-refs`（Check1+Check2）rc=0。

**Finding 处置**

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 首版 oracle 自检的不变式 `ctlz+cttz+ctpop == hd+1` **数学上不成立**（非连续全 1 值，如 `valid=0b101111,width=6` ⇒ 0+0+5=5≠6）⇒ `--self-check` 真实报错 | ✅已修 | 删该不变式，改为**第三条独立路径** `oracle_str()`（MSB-first 位串）+ 定值断言；docstring 同步「三条路径」 | `--self-check` rc=0（**1344 例**三路径逐例一致）；`--check` rc=0 |
| F2 SimRISC-00 例外说明初版写「**唯一例外**」，但同子表 `rd2rd`/`rb2rb`/`rd2ra`/`ra2rd` 等寄存器组复制指令**亦无位宽后缀** ⇒ 事实不准确 | ✅已修 | 3 处（`SimRISC-00` 表下说明 / `contract-isa §2.8` / `A.9`）改为「**例外**」并补区分（后者位宽**恒为整寄存器 64 位**，不随操作数变化） | 3 处 grep 复核；`check-spec-readonly` rc=0（sha256 同步重算：`05b965ee…`）；`check-spec-refs` rc=0 |
| F3 `check-instrinfo`(L1) 因 Check 2b 要求每条 `m8` 记录有 `.td` def 而红（= 阶段 B 工作），而任务书 §验收标准 8 要求其 rc=0 | ⏸延后（**结构性**；任务书定稿早于 Check 2b 引入 ⇒ **须架构裁定**） | **未改**任何门控（弱化需授权）；以「期望 rc=2 + 独立判定器核对**恰为** 3 项」显式断言 | `run.sh` §3 rc=2 且判定器 PASS；`--inject` ④ 证判定器可达 FAIL；`test-semihost` 连带红同源（`-o check` 则 rc=0） |
| F4 `check-interface`(L2) 因缺 3 条 QEMU `trans_*` 而红（= 阶段 C 工作） | ⏸延后（同上；同 `SPEC-142t` 阶段 A 的 L2 口径） | **未改**门控 | `run.sh` §3 rc=2 且「FAIL 恰 2 项、缺 `trans_*` 恰 3 条」判定器 PASS；`--inject` ⑤ 证可达 FAIL |
| F5 `A.9` 无 `value` 列（与既有 `A.8` 的 `rev.*` 表不一致） | ⏸披露不改 A.8（最小改动） | A.9 只列位域 + 真源指针（遵用户 2026-10-15 位域口径） | `--inject` ①/§1 编码核对 3/3；A.9 表 grep 无 value 列 |
| F6 `README.md:73` 陈旧计数（227/①217；现 234/①221） | ⏸不修（**越界**：不在本任务文件清单；`SPEC-142t` 亦未改） | 未改 | `git diff --name-only` 不含 `README.md` |

**判决**：全部 finding 已处置（F1/F2 已修；F3–F6 为**显式披露 / 结构性延后 / 越界不改**，其中 **F3 属跨阶段结构性冲突、须架构裁定**）。阶段 A 无未处置的**代码缺陷** ⇒ 状态置 `待验收`；**并请架构/用户裁定 F3**（接受阶段 A known-red，或将 3 条 `.td` def 提前进阶段 A）。

#### 第 1 轮 reviewer 审阅

（独立验收；全部判定基于 reviewer 自跑命令与退出码，非转述；长日志留 `/tmp/opencode/<任务ID>/review-a/`。）

**重跑记录（真实 rc）**
- `make check`(L1) rc=**2**：`ERROR` **恰 3 条**（`ctpop/ctlz/cttz_orri_rd` 的 `.td def 数 = 0`）、无其它失败（`=== Result: 3 errors ===`）⇒ 与口径①一致；独立判定器 `check_instrinfo_knownred.py` PASS。
- L2 逐子目标：`check-interface` rc=**2**（FAIL 恰 2 项、`MISSING trans_*` 恰 3 条，判定器 PASS）；`check-lit`/`check-qemu-smoke`/`test-codegen`/`test-elf`/`check-picolibc-tests` 各 rc=0；`test-semihost` rc=2（日志唯一失败=同 3 条 m8 缺 def）；`make -o check test-semihost` rc=**0** ⇒ 连带证实（口径③）。
- 其余指名门控 24 项逐项 rc=0：`check-scope`（现场 m8=7、total=234）、`check-rule-refs`、`validate-encoding`、`check-isa-coverage`、`check-spec-{changelog,refs,readonly,numbering,codeblocks,drift}`、`check-no-residue`、`check-tasks`、`check_issues.py`（33 open/5 closed）等。
- 证据脚本重跑：`run.sh` rc=0 **PASS=54 FAIL=0**、`run.sh --inject` rc=0 **PASS=11 FAIL=0**（与完成区逐字一致，输出真实性 ✓）。
- ⇒ **已知红恰为口径 3 项，多出红 0**。

**编码/位置（reviewer 自写 QFC 解析器，未复用 engineer 解析器）**：`op=0x40`（MISC-octa）；`opx`=`011-101/110/111`=29/30/31（`ha` 0x1D/0x1E/0x1F）；`mask=0xFFFC0000` 与 `value=op<<24|ha<<18` 自算 = yaml 实值；spec §4.2 单元格 ↔ `opcodes.yaml` **双向差异 0**（36↔36）；同 opx 在 tetra/wyde/byte **9 格全空** ✓。

**「只写位域」口径**：`ADR-0012 D11` 正文表、任务书 §1 表、`contract-isa` A.9 均无 `value` 列且明指真源 `contracts/opcodes.yaml` ✓。2 处 value 字面命中**定性非契约复写**（ADR 2026-10-14 历史流水行引录提案原文 + 任务书完成区机器核实记录带真源指针）⇒ 记 observation 供终审知悉，不计违规。

**语义/定值（第四种 oracle：256 项字节查表 + 高/低字节扫描，与三条既有路径不同实现）**：`bitcnt.yaml` **414 例全量**重算（3+192+216+3，现场统计）**差异 0**（不抽样）；`hd` 3×64 全量覆盖、全合法；定值 `ctlz/cttz(0)=hd+1`（含 `hd=63`⇒64）、`ctpop(0)=0`；结果 `0..64` 写满 64 位；大端（op 字节在前）逐例断言 ✓；oracle 自身经 2 万随机例对朴素参照差异 0（防我方实现 bug）。

**合法性**：`hd∈0..63` 全合法（逐例无 ILLI 标注）；legality 例唯一 ILLI 依据=`rdhb==rd0`（`dst_rd0`）；`rdhc==rd0`（读 0）/`rdhb==rdhc` 逐例不报错；`contracts/legality_rules.yaml` **不在** `git diff ef74e12 567ff21` 改动集（18 项=16M+2A，与 architect 留痕一致）⇒ 未新增规则 ✓。

**例外说明/版本记录/锁册**：`SimRISC-00` 表下例外说明（含与 `rd2rd`/`rb2rb` 的区分）+ `SimRISC-04 §4.2.2` + `contract-isa §2.8` 三处口径一致（F2 修复在位）；两册附录 `-rc` 均写明本批 3 条指令（`check-spec-changelog` rc=0）；锁册 `sha256` 独立重算 `05b965ee…`/`000a12d0…` 与 `spec-readonly.lock.toml` 一致（`check-spec-readonly` rc=0）。

**reviewer 新反例（engineer 5 组清单外：删覆盖用例）**：删 `cttz semantic hd=42` 1 例 ⇒ `generate_bitcnt_vectors --check` rc=**1**（「与真源重派生结果不一致」）⇒ `cp`+md5 还原（前后双 `61ed5ffa…`）⇒ 复验 rc=**0** 回绿 ✓。

**约束核验**：越界 0（`spec/` 改动交集=授权 2 册；未触 `components/**`/`legality_rules.yaml`/compiler-rt）；README 陈旧计数未改=越界披露合理（F6，`SPEC-142t` 同例）；`ISS-215` 已登记 open（待 B/C 转绿关闭）；工作区前后快照对账一致（`git status` 0 行、6 目标文件 md5 相等、`check-no-residue` rc=0）；未提交（提交权归 architect）✓。

**判决：Accepted（阶段 A）**——验收口径 3 项已知红之外全绿、无多出红、无未处置代码缺陷；F3/F4 属结构性延后（阶段 B/C 消除，`ISS-215` 跟踪），不计缺陷；任务级 `**状态**` 维持 `待验收`（B/C 未做，完成前不得置 `已验证`）。

## 阶段 A 验收口径（**架构裁定，2026-10-15**）

> **裁定对象** = 完成区「新发现/坑 ①」（F3：`check-instrinfo` 的 Check 2b 与三阶段拆分结构性冲突）+ F4（`check-interface`）。**裁定 = 接受「阶段 A 已知红」并用口径登记**（= 候选对策 **ⓒ**，见 `ISS-215`）；**不**弱化 / 修改任何门控。

**已知红（结构性必然，非缺陷）—— 恰 3 项**：

1. **L1 `check-instrinfo` rc=2**：失败项**恰 3 条** `scope: m8` 记录（`ctlz`/`cttz`/`ctpop`）**尚无 `.td` def** ⇒ **阶段 B 消除**。
2. **L2 `check-interface` rc=2**：失败项**恰 2 项**（缺 QEMU `trans_ctlz`/`trans_cttz`/`trans_ctpop` **恰 3 条**）⇒ **阶段 C 消除**。
3. **`test-semihost` rc=2 属连带**：其前置含 `check`(L1)，继承同一 red；`make -o check test-semihost` **rc=0** 已证 semihost 内容与本法无关（证据 = `.work/evidence/SPEC-143t/log/`）。

**阶段 A 验收口径** = **上述 3 项之外全绿**：L1 其余 + L2 其余 + 全部 `check-spec-*` / `validate-encoding` / **`check-scope`（`m8=7`、`total=234`）** / `check-rule-refs` / `check-isa-coverage` / `check-spec-readonly` / `check-no-residue` / `tools/infra/check_issues.py` / `check-tasks` 各 **rc=0**（架构 2026-10-15 现场复核：`check-instrinfo`/`check-interface` rc=2 且失败项恰如上、`check-scope`/`check-rule-refs`/`check-isa-coverage`/`validate-encoding`/`check-spec-readonly`/`check-no-residue`/`check-tasks`/`check_issues.py` 全 rc=0）。**不弱化**任何门控。

**阶段收口要求**：**阶段 B 完成后 `check-instrinfo` 须转绿**、**阶段 C 完成后 `check-interface` 须转绿**（`test-semihost` 随之转绿）；**此 3 项未全部转绿前不得置 `已验证`**（`ISS-215` 相应关闭）。

#### 阶段 A architect 提交与文件集审核留痕（2026-10-15；**只追加**）

- **档位**：**正常提交**（**不带 `WIP:`**，供 reviewer 独立验收；依据 = 完成区「测试结果 PASS=54 FAIL=0」+ 上「阶段 A 验收口径（架构裁定）」；**阶段级**，任务级 `**状态**` 维持 `待验收`、**不**置 `已验证`）。
- **提交**：分支 `SPEC-143t-A` 头提交（提交信息 = `SPEC-143t A: ctlz/cttz/ctpop 契约/编码层（MISC-octa 三格 + 例外说明 + hd 三统一语义 + 定值 hd+1 + 独立 oracle 向量；已知红：check-instrinfo/check-interface 待 B/C）`；**只 `commit`，未 `merge`、未 `push`**）。**注**：本留痕与提交同体 ⇒ **不内嵌 SHA**（SHA 随留痕内容变化而变、会自指失真）；SHA 以分支头 / 父会话回报为准。
- **文件集对账**（`git diff --cached --name-status -M` ↔ 完成区「修改文件」声明）：**18** 项 = **16 M + 2 A**，其中 **17** 项 = 完成区声明（**15 M + 2 新**：`tests/vectors/bitcnt/bitcnt.yaml`、`tools/testcases/generate_bitcnt_vectors.py`），**+1** 项 = architect 立项登记（`.tao/knowledge/issues.yaml` 增 `ISS-215`）⇒ **无漏提、无多提、无越界**（未触 `components/**` / `contracts/legality_rules.yaml` / compiler-rt）。
- **门控（架构 2026-10-15 现场复核，非转述）**：`check-instrinfo`(L1) rc=**2**（失败项**恰 3 条** = m8 缺 `.td` def）、`check-interface`(L2) rc=**2**（失败项**恰 2 项**）、`check-scope` rc=0（`m8=7`、`total=234`）、`check-rule-refs` rc=0、`check-isa-coverage` rc=0、`validate-encoding` rc=0、`check-spec-readonly` rc=0、`check-no-residue` rc=0、`check-tasks` rc=0、`tools/infra/check_issues.py` rc=0（33 open / 5 closed）。**不弱化**任何门控。

#### 阶段 A 收尾提交留痕（2026-10-15；**只追加**）

- **档位**：**正常提交**（**不带 `WIP:`**；依据 = 上「第 1 轮 reviewer 审阅」判决 `Accepted`〔**阶段级**〕；任务级 `**状态**` 维持 `待验收`、**不**置 `已验证`——与 `SPEC-142t` 阶段 A 收尾同例）。
- **提交**：分支 `SPEC-143t-A` 头提交（提交信息 = `SPEC-143t A: 阶段A收尾（reviewer Accepted；契约/编码层 + 独立 oracle 向量）+ 阶段进度更新`；**只 `commit`，未 `push`**）。**注**：本留痕与提交同体 ⇒ **不内嵌 SHA**（SHA 随留痕内容变化而变、会自指失真）；SHA 以分支头 / 父会话回报为准。
- **文件集对账**（`git diff --cached --name-status -M` ↔ 本笔范围）：**2** 项 = **2 M**，即 `.tao/tasks/spec/SPEC-143t-ctlz-cttz-ctpop落地.md`（第 1 轮 reviewer 审阅记录 + `**阶段进度**` 行 + `**状态**` 口径说明 + 本留痕）、`.tao/knowledge/milestones.md`（`SPEC-143t` 流水行：`**状态**` → `待验收` + 补「阶段 A 已完成并验收（2026-10-15，reviewer `Accepted`）」）⇒ **无漏提、无多提、无越界**（未触 `spec/**`、`components/**`、`contracts/**`、`tools/**`）。
- **门控（架构 2026-10-15 现场自跑，非转述；日志 = `/tmp/opencode/SPEC-143t/arch-*.log`）**：`make check`(L1) rc=**2**——`ERROR` **恰 3 条**（`ctpop_orri_rd`/`ctlz_orri_rd`/`cttz_orri_rd` 的 `M8` 记录 `.td def 数 = 0`）、无其它失败（`=== Result: 3 errors ===`）；`make check-interface`(L2) rc=**2**——FAIL **恰 2 项**、`MISSING trans_*` **恰 3 条**（`trans_ctpop/ctlz/cttz_orri_rd`）；`check-scope`（`m8=7`、`total=234`）/ `check-rule-refs` / `check-isa-coverage` / `validate-encoding` / `check-spec-readonly` / `check-no-residue` / `check-tasks` / `tools/infra/check_issues.py`（33 open / 5 closed）各 rc=**0** ⇒ 与「阶段 A 验收口径」逐条一致（**3 项已知红之外全绿**）。**不弱化**任何门控。
- **收尾检查**：① 门控 = 口径内 3 项已知红之外全绿 ✓；② 无临时残留（`git status --porcelain -uall` 仅本笔 2 项、无 `*_tmp*`/`_gate*`/`*.orig`/`*.rej`）✓；③ 证据在 `.work/evidence/SPEC-143t/`（`run.sh` / `run-full.log` / `log/**`）✓；④ 无未提交结果（提交后工作树干净）✓；⑤ 下一件 = **阶段 B（MC）**，由父会话续链 ✓。
