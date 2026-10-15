# SPEC-143t: `ctlz`/`cttz`/`ctpop`（位扫描与计数）指令落地

**模块**：spec
**项目里程碑**：M8
**依赖**：`ADR-0012 D11`（**前置已全部满足 ✓**：`D11.1`–`D11.10` 用户 2026-10-14 **逐条确认** ✓〔原话「**D11全部认可**」〕+ **改 `spec/` 授权** ✓〔原话「**同样授权**」，与 `SPEC-142t` 的「a/b授权」同样〕——见「开工前置」与 `adr-0012 §状态说明`；`D11` 已 `Accepted`）；`SPEC-141t`（ISA 指令扩展预研，候选 `C2` = `clz`/`ctz`/`popcount`，**只读**来源）；`INFRA-078t`（compiler-rt 预研：缺口来源，**只读**）；`LLVM-079t`（现状：`CTLZ`/`CTTZ`/`CTPOP` 走 `Expand`，**只读**溯源）；`docs/Process-06`（`spec/` 目录保护）；`ADR-0012 D4`（`spec/` 只读策略）。**串行**：与 `SPEC-142t`（`rev.{o,t,w,b}` 落地）**须串行**（同改 `contracts/opcodes.yaml` / `tests/vectors/**`），先后由主会话排定。
**状态**：已验证
**阶段进度**：A ✅ 已验证；B MC ✅ 已验证；C QEMU ✅ 已验证（2026-10-15）

> **`**状态**` 口径**：本任务 = **一个任务书、三阶段验收**（照 `SPEC-142t`）⇒ `**状态**` 表**任务级**进度（**三阶段全部验收通过后**置 `已验证`）；**阶段级**进度见上行 `**阶段进度**`。

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

### 阶段 B（MC）—— 完成（2026-10-15；`check-instrinfo` 转绿 ✓）

**测试结果**：`./.work/evidence/SPEC-143t/run-b.sh` **PASS=26 FAIL=0**（rc=0）；`run-b.sh --inject` **PASS=14 FAIL=0**（4 组注入，均在**临时副本/临时目录**：①还原的**纯 `.td`** 删 `ctlz_orri_rd` def ⇒ `validate_instrinfo --td` rc=1（`ERROR` **恰 1 条** = 注入点）；以「未注入的同一还原文本 ⇒ rc=0」作回绿基线 ✓；②MC 检查器期望值改 1 位 ⇒ **恰 1 条** `[FAIL]`；③临时目录 `gen-orri.s` 删 ctlz 用例 ⇒ `check_lit_gen` rc=1（`missing=['ctlz_orri_rd']`）；④临时副本 `check-interface` 日志删 1 条 `MISSING:` ⇒ 判定器 rc=1。5 个仓库文件 md5 前后逐字节相同）。子检查器 `check_bitcnt_mc.py` **PASS=93 FAIL=0**。

**修改文件**（`git status --porcelain -uall` = **6**，除本任务书）：`components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOInstrInfo.td.patch`（**+36 行**，`make_patch.py` 导出；`new file` hunk `1549→1585`）；`components/llvm-project/changelog.md`（`Process-01 §10` 追加一行）；`tools/llvm/llvm-isa-backend-matrix.tsv`（3 条 `td_def`/①层重生成）；`tools/llvm/llvm-isa-backend-matrix.md`（同计数 + 3 行）；`tests/llvm/lit/MC/DADAO-gen/gen-orri.s`（+3 用例，生成器重生成）；`tests/llvm/lit/MC/DADAO/gen-fast.s`（快档代表 4 行，生成器重生成）。`series` 仍 **71**（一文件一补丁）。**未改** AsmParser/InstPrinter/MCCodeEmitter/Disassembler（既有 `orri` 路径复用）。

**验收结果**（真实 rc；日志 `.work/log/llvm/SPEC-143t-b-*.log`、`SPEC-143t-B-*.log`、`.work/evidence/SPEC-143t/log/`）：
- **重建（启动证据，长任务）**：`setsid nohup bash -c 'JOBS=8 make build-mc …'`（外层 PID **1132045** / `make` **1132047** / `ninja -j8` **1132079**，16 核**未**用全核）；`.EXIT` = **`SPEC-143t_B_EXIT=0`**（45/45 步 + `build-mc: PASS`；11:18:13→11:22:2x ≈ **4 min**，**增量**）。随后 `make install-host`（`ISS-210` 强制）rc=0（`.EXIT` = `SPEC-143t_B_INSTALL_EXIT=0`，≈**130 s**）。
- **两处二进制**（`ISS-210` 防假绿）：构建树与安装根 `llvm-mc` md5 **同为 `94559d13…`**，且**两处都**以 rc=0 汇编三条（逐条）。
- **编码逐条（三方，不抽样）**：`ctpop rd8, rd9, 63` 字 `0x4074827F`、`& 0xFFFC0000` = **`0x40740000`**；`ctlz` `0x4078827F` ⇒ **`0x40780000`**；`cttz` `0x407C827F` ⇒ **`0x407C0000`** —— 与 `op<<24|ha<<18` 派生、`opcodes.yaml` `value`、任务书 §1 给定**三方相等**；字段逐位核对（`op=0x40`、`ha=29/30/31`、`rdhb=8`、`rdhc=9`、`hd=63`）。
- **往返**：`llvm-mc -filetype=obj` ⇒ `llvm-objdump -d` 3/3 文本 + 字节 == `--show-encoding`；再汇编 ⇒ 文本/字节幂等。
- **`hd` 合法域**：三条 × **全 64 取值**逐例汇编 **accept 64/64、reject 0**（契约：无非法 `hd`）；`hd=64`/`-1` rc=1 拒绝（既有 `immu6` 范围）；`rdhc=rd0`/`rdhb==rdhc` 受理；`rd0` 作目的 MC 层受理——**未新增**汇编期合法性检查（`ISS-211` 口径 ⇒ 归阶段 C 执行层）。
- **门控**：**`check-instrinfo` rc=0（`M8 records: 7` / 7/7 各有唯一 `.td` def）＝ 本阶段核心指标转绿 ✓**；**L1 `make check` rc=0（全绿 ✓）**；L2 `make check-modules` rc=**2** —— **仅** `check-interface`（FAIL 恰 2 项、缺 `trans_*` 恰为本任务 3 条，判定器 rc=0）；L2 其余 6 子目标（`check-lit`/`check-qemu-smoke`/`test-codegen`/`test-elf`/`test-semihost`/`check-picolibc-tests`）**逐项 rc=0**（**`test-semihost` 随 L1 转绿 ✓**）。
- **生成物同步**：`check-isa-coverage` rc=0（① accept **221→224**、reject 13→10；三条 ①层 `reject`→`accept ok`、`td_def` 空→id）；`check_lit_gen` rc=0（**64 passed / 0 failed**）；`check-patch-tree`（4 组件 128 补丁）/`check-index-blobs`/`validate-encoding`/`check-asm-list`/`check-asm-list-drift`/`check-scope`/`check-rule-refs`/`check-legality-drift`/`check-legality-invariants`/`check-spec-readonly`/`check-spec-changelog`/`check-fp-contract`/`check-no-residue` 各 rc=0；`check-source-state` OK（source HEAD `152cfb152b68`、count=1、clean=True）。
- **幂等**：`make_patch.py llvm-project` ⇒ `0 written, 71 unchanged`；`gen_isa_coverage.py` / `generate_lit_vectors.py` 重跑后 **6 个仓库文件 md5 全不变**。

**新发现/坑**：①`generate_lit_vectors.py` 的**快档**代表按「形态排序首条」机械选取 ⇒ 新增记录会**改变代表**（本环 `orri` 立即数形态 `ext.so`→`ctlz`，`gen-fast.s` 4 行替换）——该文件是**生成物**，须随生成器重生成（非手工挑拣）。②`check_lit_gen`（L3 面）在本环前**即为红**（阶段 A 新增 3 条后 `gen-orri.s` 缺 3 用例，62/2）⇒ 属阶段 A 完成区**未列**的第 4 项 known-red（阶段 A 口径仅覆盖 L1/L2）；本阶段随生成物重生成转绿。③`validate_instrinfo.py --td` 收**纯 `.td`**（非补丁）⇒ 反例注入须先按 `parse_patch` 口径还原纯文本（本环注入①如此，并以「未注入 ⇒ rc=0」双向验证）。④`check-instrinfo` 的 join key 是 `(mnemonic,format,op,ha)`、**不**校验 def 名 == `opcodes.yaml` `id`；本环 def 名按 id 命名（`<id>`）以便矩阵 `td_def` 列可读。

**遗留问题**：①L2 `check-interface` 2 FAIL 仍待**阶段 C**（QEMU `trans_*(231/234)`）+ 任务书验收 4「向量经 QEMU 实跑一致」待阶段 C；②**ISel 接入**不在本任务（`D11.9` 未列，另立）；③`ISS-215` 待阶段 C 完成后一并关闭；④`ISS-210`（重建后必 `make install-host`）本环已执行、issue 状态归主会话；⑤**未提交**（提交权归 architect）；**未越界**（只 MC：`.td` 补丁 + 生成物 + `changelog.md`；未触 QEMU / `spec/**` / `contracts/**` / compiler-rt）。

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

#### 第 2 轮 engineer 自审（阶段 B / MC，2026-10-15）

（自主逐行审查；对象 = 本环 `.td` 补丁增量、`changelog.md` 一行、生成物（矩阵/lit）、以及本环**新写**的 3 个证据脚本。全局 `subagent_depth=1`，engineer 无法起嵌套子代理，故为自主逐行审查。）

**逐行审查意见与判决**

1. `.td` 三条 def：`DADAOOrri<"ctpop">/<"ctlz">/<"cttz">`，`op=0x40`、`ha=0x1D/0x1E/0x1F`、操作数 `(outs GPRD:$rb)/(ins GPRD:$rc, immu6:$imm6)`、`Pattern=[]` —— 与 `contracts/opcodes.yaml` 三条记录的 `op`/`ha`/`format=orri` 及 `ext.uo_orri_rd` 先例**逐字一致**；**无**位宽后缀（D11.3）；三处**独立**于 yaml 的数值核对：汇编码字 `& mask` == `op<<24|ha<<18` == yaml `value`（§2，逐条）。**正确**。
2. **未新增汇编期合法性检查**：注释显式写明「every 6-bit `hd` legal；`contracts/legality_rules.yaml` unchanged；`dst_rd0` 归执行层」——与 `ISS-211` 口径一致；实测 `hd=64/-1` 仅被**既有** `immu6` 范围检查拒绝、`rd0` 作目的 MC 层受理（§4）。**符合**（未改 AsmParser）。
3. 复用面核实：AsmParser（`orri` matcher 由 TableGen 生成，无需白名单）/InstPrinter（flat 打印）/MCCodeEmitter（通用 `getMachineOpValue`）/Disassembler 均**未改**；实测 `--show-encoding` + `objdump -d` 双路径字节一致（§1/§3）⇒ 「不需改即可工作」有实证，非假设。
4. 补丁纪律（`Process-01 §6`）：改动在 `.work/source/llvm-project` 进行 → E4 收敛 `base+1` → `make_patch.py` 导出（`0 written, 71 unchanged` 幂等）→ `check-patch-tree`/`check-index-blobs`/`check-source-state` 全绿；`series` 未变、**一文件一补丁**、**未手工编辑补丁**。**符合**。
5. 生成物同步：「改 `opcodes.yaml`/`.td` ⇒ 必须重生成矩阵与 lit 生成物」——两生成器重跑后 **6 文件 md5 不变**（幂等）+ `--check` 类门控 rc=0。**符合**（承 `SPEC-142t` 阶段 B 教训）。
6. 证据脚本可达 FAIL：4 组注入各命中**不同**目标断言（①`check-instrinfo` ②MC 编码 ③`check_lit_gen` 覆盖 ④`check-interface` 判定器），且**各有回绿基线**（①还原文本 rc=0；②先验 pristine rc=0；③未注入目录由全量模式 rc=0 佐证；④全量模式判定器 rc=0）。**无恒真断言**；计数全部现场统计（`len(MNEMONICS)`、`accept=64/64`、`PASS/FAIL` 由脚本计数）。
7. 还原纪律：注入**只**落 `/tmp/opencode/SPEC-143t/`（临时副本/临时目录），**无** `git checkout/restore/stash`；另以 5 个仓库文件 **md5 前后对账**证明未被触碰。**符合**。
8. 防造假：`check_bitcnt_mc.py` 期望值三方来源（位域公式 / yaml / 任务书），**不**从 `llvm-mc` 输出反推；`hd` 域 192 例**全量**（非抽样）；工具一致性以 **md5** 判（防 `ISS-210` 假绿）。**符合**。
9. 越界自查：`git diff --name-only` = 6 文件，**均**属「MC 面 + 其生成物 + 组件 changelog」；**未触** `spec/**`、`contracts/**`、QEMU、compiler-rt；`.tao/knowledge/` 未改（沉淀归 `/complete`）。**符合**。
10. 首版自审发现并当场修（见下表 F1/F2）。

**Finding 处置**

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 注入①把**补丁文件**直接喂 `validate_instrinfo.py --td` ⇒ 解析出 0 个 def、165 条 `ERROR`（**FAIL 理由失真**，属"假红"而非目标反例） | ✅已修 | `run-b.sh` 注入①改为先按 `parse_patch` 口径还原**纯 `.td`**，再删 `ctlz_orri_rd` def；加「未注入的还原文本 ⇒ rc=0」回绿基线 | 注入① `ERROR` **恰 1 条**且 = `M8 记录 ctlz_orri_rd 的 .td def 数 = 0`；基线 rc=0（`--inject` PASS=14 FAIL=0） |
| F2 证据脚本把 `3`/`ctlz_orri_rd` 等**字面**写进断言（计数硬编码、def 名与 id 约定重复） | ✅已修 | 改 `len(MNEMONICS)`；`td_def` 期望改取记录 `id`（现场派生） | `check_bitcnt_mc.py` PASS=93 FAIL=0；§6 打印现场值 |
| F3 阶段 A 完成区列「known-red 恰 3 项」，但本环发现 `check_lit_gen`（L3 面）**亦**为红（阶段 A 新增记录后生成物未重生成） | ⏸披露（**不**改阶段 A 记录，只追加本阶段说明） | 未改阶段 A 文本；在本阶段「新发现/坑」②如实写明口径差异 | `check_lit_gen` 本环 rc=1→**rc=0（64 passed）**；阶段 A 口径原文仍可查 |
| F4 `gen-fast.s`（**快档**，L2 `check-lit` 用）因新增记录**代表变更**而 4 行改写 | ⏸不改判据（**生成物按生成器输出为准**），仅登记 | 未手工编辑；由 `generate_lit_vectors.py` 重生成 | 重跑 md5 不变（幂等）；`make check-lit` rc=0 |

**判决**：全部 finding 已处置（F1/F2 已修；F3/F4 为显式披露/生成物口径登记）。阶段 B **无未处置代码缺陷**；核心指标（`check-instrinfo` 转绿 + L1 全绿）已由真实 rc 达成，L2 唯一失败项 = 阶段 C 工作项 ⇒ 状态置 `待验收`。

#### 第 2 轮 reviewer 审阅（阶段 B / MC，2026-10-15）

（独立验收；判定全部基于 reviewer 自跑命令与退出码，非转述；日志 `/tmp/opencode/<任务ID>/review-b/`。）

**重跑记录（真实 rc）**
- 核心指标：`make check-instrinfo` rc=**0**（`M8 records: 7`、7/7 各有唯一 `.td` def）；`make check`(L1) rc=**0** 全绿（`repository checks (L1): PASS`）。
- L2：`make -k check-modules` rc=**2**，全日志 `Error` **仅 1 处** = `check-interface`（FAIL 恰 2 项 = `QEMU trans ↔ opcodes.yaml`/`trans_* 定义数`、`MISSING` **恰 3 条** = `trans_ctpop/ctlz/cttz_orri_rd`）⇒ **唯一 FAIL 目标 = `check-interface`**，无多出红；其余 6 子目标逐项 PASS（`check-lit` 107/107、`check-qemu-smoke`/`test-codegen`/`test-elf`/`test-semihost`（含 L1 无回归前置）/`check-picolibc-tests` 各 PASS）。
- 两处二进制（`ISS-210` 破假绿）：安装根与构建树 `llvm-mc` md5 **同 = `94559d13…`**，`--show-encoding` 三条各 rc=0、编码逐字节相同。
- 编码三方（reviewer 自算脚本，未复用 engineer 解析）：`ctpop/ctlz/cttz` `word & 0xFFFC0000` = **`0x40740000/0x40780000/0x407C0000`** == `op<<24|opx<<18`（opx 29/30/31）== `opcodes.yaml` `value` == 验收口径给定；字段 `(op,ha,rdhb,rdhc,hd)=(0x40, 29/30/31, 8, 9, 63)` 逐位 ✓。
- 往返：`-filetype=obj` ⇒ `llvm-objdump -d` 3/3 助记符+操作数+字节与 `--show-encoding` 一致；再汇编文本/字节幂等 ✓。
- `hd` 边界：三条 × 0..63 **accept 64/64、reject 0**（契约：无非法 `hd` ✓）；`hd=64`/`-1` rc=1 拒绝（既有 `immu6` 范围检查）；`rd0` 作目的 rc=0 **受理**（`ISS-211` 口径：MC 层不查合法性 ✓）；`rdhc=rd0`/`rdhb==rdhc` 受理 ✓。
- 证据脚本重跑：`run-b.sh` rc=0 **PASS=26 FAIL=0**、`run-b.sh --inject` rc=0 **PASS=14 FAIL=0**（与完成区逐字一致；注入①–④各命中不同目标断言、仓库 5 文件 md5 前后不变）；`check_bitcnt_mc.py` PASS=93 FAIL=0。
- **reviewer 新反例（engineer 清单外）**：矩阵 `llvm-isa-backend-matrix.tsv` 的 `ctlz_orri_rd` 行 `td_def` 改 `…_INJECT` ⇒ `check_bitcnt_mc.py` rc=**1**（FAIL 恰 1 条 = §6 矩阵断言注入点）⇒ `cp`+md5 还原（前后双 `fc0ca400…`）⇒ 复验 rc=**0**（93/0）回绿 ✓。
- 门控联动：`check-asm-list`/`check-asm-list-drift`/`check-isa-coverage`/`validate-encoding`/`check-patch-tree`/`check-index-blobs`/`check-spec-readonly` 逐项 rc=**0** ✓。

**约束核验**：越界 0（`git diff HEAD~1 HEAD` = 6 文件 + 本任务书，均 MC 面 + 生成物 + 组件 `changelog.md`；未触 `spec/**`/`contracts/**`/QEMU/compiler-rt）；补丁纪律（`series`=71、一文件一补丁、`check-patch-tree` 绿、未手工编辑补丁）；注入还原全 `cp`+md5（无 `git checkout/restore/stash`）；工作区前后快照对账（5 目标文件 md5 全相等、`git status` 干净、完成区「修改文件」6 项与提交集逐一对上）；未提交（提交权归 architect）✓。

**遗留判定**：L2 `check-interface` 2 FAIL = 缺 3 条 QEMU `trans_*` ⇒ **归阶段 C**（与「阶段 A 验收口径」收口要求一致，非缺陷）；`ISS-215` 保持 `open`、待阶段 C 转绿后关闭 ✓；ISel 接入不在本任务（`D11.9` 未列）✓；无新增遗留、无未处置 finding。

**判决：Accepted（阶段 B / MC）**——核心指标（`check-instrinfo` 转绿 + L1 全绿）与 L2 唯一 FAIL 目标均经 reviewer 独立重跑证实、无多出红、无未处置缺陷；任务级 `**状态**` 维持 `待验收`（阶段 C 未做，3 项转绿前不得置 `已验证`）。

#### 阶段 B architect 收尾提交留痕（2026-10-15；**只追加**）

- **档位**：**正常提交**（**不带 `WIP:`**；依据 = 上「第 2 轮 reviewer 审阅」判决 `Accepted`〔**阶段级**〕）；任务级 `**状态**` **维持 `待验收`**、不置 `已验证`（阶段 C 未做）。
- **提交**：分支 `SPEC-143t-B` 头提交（提交信息 = `SPEC-143t B: 阶段B收尾（reviewer Accepted；check-instrinfo 转绿、L1 全绿）+ 阶段进度更新`；**只 `commit`，未 `push`**）。**注**：本留痕与提交同体 ⇒ **不内嵌 SHA**（SHA 以分支头 / 父会话回报为准）。
- **文件集对账**（`git diff --cached --name-status -M` ↔ 本笔范围）：**2** 项 = **2 M**，即 `.tao/tasks/spec/SPEC-143t-ctlz-cttz-ctpop落地.md`（第 2 轮 reviewer 审阅记录 + `**阶段进度**` 行 + 本留痕）、`.tao/knowledge/milestones.md`（`SPEC-143t` 流水行补「阶段 B（MC）已完成并验收（2026-10-15）」）⇒ **无漏提、无多提、无越界**（未触 `spec/**`、`components/**`、`contracts/**`、`tools/**`）。
- **门控（架构 2026-10-15 现场自跑，非转述；日志 = `/tmp/opencode/SPEC-143t/arch-b/`）**：`make check`(L1) rc=**0** 全绿（`repository checks (L1): PASS`）；`make check-instrinfo` rc=**0**（`Result: 0 errors`、164 def 唯一）；`make -k check-modules`(L2) rc=**2**——全日志 `Error` **恰 1 处** = `check-interface`（FAIL **恰 2 项**、`MISSING trans_*` **恰 3 条** = `trans_ctpop/ctlz/cttz_orri_rd`），其余 6 子目标逐项 PASS（`check-lit` **107/107**、`check-qemu-smoke`/`test-codegen`/`test-elf`/`test-semihost`/`check-picolibc-tests`（fail=0））；证据脚本 `run-b.sh` rc=**0**（`PASS=26 FAIL=0`）、`run-b.sh --inject` rc=0。**不弱化**任何门控。
- **收尾检查**：① 门控 = **仅剩 1 类已知红**（`check-interface`，阶段 C 消除；`check-instrinfo` 已转绿、L1 全绿、`test-semihost` 随 L1 转绿）✓；② 无临时残留（`git status --porcelain -uall` 仅本笔；无 `*_tmp*`/`_gate*`/`*.orig`/`*.rej`）✓；③ 证据在 `.work/evidence/SPEC-143t/`（`run-b.sh` / `run-b-*.log` / `*.EXIT` / `log/**`）✓；④ 无未提交结果 ✓；⑤ 下一件 = **阶段 C（QEMU）**，由父会话续链 ✓。
- **merge 落地**：`git merge --ff-only SPEC-143t-B` FF 落地 `master`，随后删分支 `SPEC-143t-B`（**未 `push`**）。

### 阶段 C（QEMU `ctlz`/`cttz`/`ctpop` 执行支持，2026-10-15；`check-interface` 转绿 ✓）

**测试结果**：`./.work/evidence/SPEC-143t/run-c.sh` **PASS=29 FAIL=0**（rc=0，`run-c.EXIT`）；`run-c.sh --inject` **PASS=19 FAIL=0**（rc=0；4 组注入**各有可达 FAIL**：①向量副本篡改 semantic 期望 ⇒ `failed=1` ②合法 `hd` 例改标「期望 ILLI」⇒ rc=1 ③源树 `ctlz` 左移量固定（忽略 `hd`）+ 重建 ⇒ **`failed=98`** ④源树关掉 `dst_rd0` + 重建 ⇒ **`failed=3`**（恰 3 条 ILLI）；③④均 `cp`+md5 还原（前后双 `3a62874d…`）⇒ 重建 ⇒ 回绿 ⇒ 组件源树 `git status` 空）。独立 oracle `check_bitcnt_qemu.py --self-check` **1728 例**（**第三种实现**：SWAR popcount / 平移·掩码二分 clz·ctz / 大端掩码 ↔ 生成器三路径 = **四路一致** + 定值 + 值域）。
**修改文件**（`git status --porcelain -uall` = **6**，除本任务书）：`components/qemu/patches/target/dadao/insn.decode.patch`（M，256→259 行：+3 pattern、头计数 231→234）、`components/qemu/patches/target/dadao/insn_trans/trans_bitcnt.c.inc.patch`（**新**，88 行 = 全文 82 行）、`components/qemu/patches/target/dadao/translate.c.patch`（M，492→493 行 = +1 `#include`）、`components/qemu/series`（35→36）、`components/qemu/changelog.md`（+1 行）、`components/qemu/README.md`（规模 35→36、`insn_trans` 11→12）。
**验收结果**（真实 rc；日志 `.work/log/qemu/SPEC-143t-C-*.log` + `.EXIT`、`.work/evidence/SPEC-143t/`）：
- **重建（长任务）**：`setsid nohup bash -c 'JOBS=8 make build-qemu …'`（外层 PID **1193177**；22 步**增量**，16 核未用全核）`.EXIT` = **`SPEC-143t_C_EXIT=0`**；随后 **`make install-host`**（`ISS-210` 强制）`setsid nohup`（PID 1193623）`.EXIT` = **`SPEC-143t_C_INSTALL_EXIT=0`**。
- **两处二进制**（`ISS-210` 防假绿）：安装根与构建树 `qemu-system-dadao` md5 **同为 `131de0aedb6ec5e67574e1c0750eb9c2`**（注入③④各两次重建后仍相同 ⇒ 还原字节精确）。
- **核心指标**：**`make check-modules`(L2) rc=0**（`module checks (L2): PASS`；`check-interface` **83/83**，`QEMU trans_* 定义数 234 == opcodes.yaml 条目数 234`）**＝ 阶段 C 核心指标转绿 ✓（最后 2 项红消除）**；`check_qemu_trans --strict` ⇒ **234/234 (M1 155/155)** rc=0；`make check`(L1) rc=0 全绿；`check-qemu-semantics`(L3) rc=0（**149/149**，无回归）。
- **语义 e2e（独立期望，全量不抽样）**：798 例（semantic **576** = 3 条 × `hd` 0..63 **全量** × 3 源值；boundary 219 含 **192 例全 0 定值**；legality 3）⇒ QEMU 实跑 **798/798 passed**（`hd` 敏感例 **365**）；阶段 A 向量 `tests/vectors/bitcnt` **414/414 passed**。
- **定值/边界**：全 0 ⇒ `ctlz` = `cttz` = `hd+1`（**含 `hd=63` ⇒ 64**）、`ctpop` = 0（192 例）；`hd=0`（bit0=0/1）、`hd=63`（全 1 / 仅 bit0 / 仅 bit63）、`rdhc=rd0`、`rdhb==rdhc`、大端锚点 `0x0123456789ABCDEF`（结果写满 64 位）逐例通过。
- **`ILLI`**：`rdhb=rd0`（`dst_rd0`，照既有 `rev`/`orri` 先例 `gen_exception_illegal`）三条逐条单跑**真实退出码** = **`0x88`**；反向对照 `rdhc=rd0` 三条 rc=0 且退出码 **≠ `0x88`**（证 `hd ∈ 0..63` / `rdhc` 均不触发 ILLI ⇒ 无 `hd` 相关 ILLI 分支）。
- **静态/一致性**：`validate_decodetree.py`（YAML 234 ↔ pattern 234、错误 0）rc=0；`make_patch.py qemu` ⇒ `3 written, 33 unchanged`（幂等）；`check-patch-tree`（4 组件 **129** 补丁）/`check-index-blobs`(93)/`check-source-state`（qemu HEAD `c3a1edaebbaa`、count=1、clean=True）/`check-no-residue`/`check-knowledge-refs` 各 rc=0。
**新发现/坑**：①**自审抓到 oracle 自身 bug**：第三方 `clz_bisect` 未把有效窗口顶到 bit63 ⇒ `hd=0,src=1` 误得 63（`--self-check` **真实 FAIL**）⇒ 修（先 `v <<= 64-width` 再二分）；②`insn.decode` 头计数由生成器**硬编码 `256`**、提交版按**现场数**（今 234）维护（承 `SPEC-142t` 阶段 C F4 惯例）——**未改生成器**（越界/另立）；③证据脚本计数若用**多字节正则**抓取会返回多行（`63`/`365`）而失真 ⇒ 改由生成器输出**机器可读 `STATS …` 行** + 「STATS == cases.json」交叉断言；④组件源树导出走 `Process-01 §6.4` 的 `git reset --soft HEAD~` + `git add -A` + `git commit`（E4 收敛，**非**注入还原手段；注入还原一律 `cp`+md5）；⑤QEMU 侧**零 helper 改动**（`tcg_gen_clzi/ctzi/ctpop_i64` 均为 TCG 内置，含软件回退）。
**遗留问题**：①**未提交**（提交权归 architect；分支 = `SPEC-143t-C`）；**未越界**（只 `components/qemu/**`：补丁 + `series` + `changelog` + `README`；未触 `spec/**`、`contracts/**`、`components/llvm-project/**`、compiler-rt）；②**ISel 接入**（`int_ctlz/cttz/ctpop` → 单指令）不在本任务（`D11.9` 未列，另立）；③`ISS-215`（`check-interface` 2 FAIL）本阶段已转绿 ⇒ **建议主会话/architect 闭合**；④阶段 C 待 reviewer 独立验收（任务级 `**状态**` 维持 `待验收`）。


#### 第 3 轮 engineer 自审（阶段 C / QEMU，2026-10-15）

（自主逐行审查；对象 = 本环 `insn.decode` 3 条 pattern、`insn_trans/trans_bitcnt.c.inc`（82 行）、`translate.c` 的 1 行 `#include`、`series`/`changelog.md`/`README.md`、证据脚本 `check_bitcnt_qemu.py` + `run-c.sh`。全局 `subagent_depth=1`，无法起嵌套子代理，故为自主逐行审查。）

**逐行审查意见与判决**

1. `bitcnt_mask(hd)` = `~(uint64_t)0 >> (63 - hd)`：`hd ∈ 0..63` ⇒ 位移量 `0..63` ⇒ **无** `1ULL << 64` 的 UB；`hd=0` ⇒ `1`、`hd=63` ⇒ 全 64 位。**正确**。
2. `bitcnt_legal`：**仅** `a->hb == 0` ⇒ `gen_exception_illegal`（`dst_rd0`，照 `rev_legal`/既有 `orri` 先例）；**无** `hd` 相关分支（契约：`hd` 全合法）。**正确**。
3. `trans_ctlz_orri_rd`：`shli(t, rdhc, 63 - hd)` 把有效窗口顶到 bit63 后 `tcg_gen_clzi_i64(rdhb, t, hd + 1)` ⇒ 非零 = 窗口内前导零（`≤ hd`）、全 0 时按 `xlen = hd+1` 取**定值**（非 64）；`hd=63` ⇒ 位移 0 = 全 64 位。**正确**（64 个 `hd` × 全 0 的 192 例实证）。
4. `trans_cttz_orri_rd`：`andi` 掩码 + `tcg_gen_ctzi_i64(rdhb, t, hd + 1)` ⇒ 全 0 得 `hd+1`；`trans_ctpop_orri_rd`：掩码 + `tcg_gen_ctpop_i64` ⇒ 自然值、无特例。**正确**。
5. **值语义**：三条均 `store_rd(a->hb, rdhb)` 写满 64 位（非「只写低位」）；`store_rd` 对 `rd0` 静默忽略——但 `rd0` 作目的已被 `bitcnt_legal` 先行 ILLI（静默路径不可达）。**正确**。
6. `translate.c`：`#include` 紧随 `trans_rev.c.inc`（与该文件既有 include 群一致）；hunk 头/`index` 行由 `make_patch.py` 自动生成（**非**手改），`check-patch-tree` 断言⑥/⑨ 与 `check-index-blobs` 独立复算通过。**正确**。
7. `insn.decode`：3 条 pattern 与 `generate_decodetree.py` **现场产出逐字节一致**（仅头计数与既有 `# 0x5A` 人工注记不同）⇒ 无插入位置漂移；`validate_decodetree` 234/234。**正确**。
8. 独立 oracle（`check_bitcnt_qemu.py`）：与阶段 A 生成器**代码独立**（SWAR / 平移·掩码二分 / 大端掩码 vs 逐位 / 整数性质 / 位串）；**无** subprocess、不读 QEMU 产物。**符合 Spec-first / independent oracle**。
9. **可达 FAIL（逐断言）**：注入 A（篡改 semantic 期望）⇒ `failed=1`；注入 B（合法 `hd` 标为「期望 ILLI」）⇒ rc≠0（证 ILLI 断言非恒真）；注入 C（源树 `ctlz` 忽略 `hd` + 重建）⇒ **98 FAIL**（证 QEMU **实现本身**被比对）；注入 D（源树关 `dst_rd0` + 重建）⇒ **3 FAIL**（证 ILLI 路径被比对）。**符合**。
10. 证据脚本纪律：无 `tee`；收尾 `rc=0; [ FAIL = 0 ] || rc=1; exit $rc`；覆盖/计数**现场统计**（`STATS` 行 + `cases.json` + 日志抓取）；两处 md5 相等判（防 `ISS-210` 假绿）。**符合**。
11. 还原纪律：注入③④用 `cp` 备份 + md5 对账（前后 `3a62874d…`），**未**用 `git checkout/restore/stash`；导出走 `Process-01 §6.4` 的 E4 收敛（**非**还原手段，已披露）。**符合**。
12. 越界自查：`git status --porcelain -uall` = 6 项，与 `spec/`、`contracts/`、`components/llvm-project/**` 交集**空**；未改 `helper.c`（TCG 内置，无 helper 需求）。**符合**。

**Finding 处置**

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 第三方 oracle `clz_bisect` 未把有效窗口顶到 bit63 ⇒ `hd=0,src=1` 误得 63（**自检真实报错**） | ✅已修 | 二分前先 `v = (v << (64 - width)) & MASK64` | `--self-check` rc=0（**1728 例**四路一致 + 定值 + 值域） |
| F2 `run-c.sh` 用**多字节正则**抓计数 ⇒ `grep -oE` 返回两行（`63`/`365`），打印失真 | ✅已修 | 生成器新增机器可读 `STATS cases=… hd_sensitive=…` 行；脚本改抓该行 + 加「STATS == cases.json」断言 | 现场打印 `cases=798（STATS 798），hd 敏感=365`；`run-c.sh` PASS=29 FAIL=0 |
| F3 `insn.decode` 头计数生成器硬编码 `256` vs 现场 `234` | ⏸披露不改（既有惯例；改生成器越界/另立） | 提交版按现场数维护（231→**234**） | `validate_decodetree` 234/234；「新发现/坑」② |
| F4 组件元数据随补丁集变化（`README.md` 规模、`insn_trans` 计数） | ✅已更新（`Process-01 §2`：README 须简明反映补丁集） | 35→36 份、11→12 个 `insn_trans/*.c.inc` | 现场 `wc -l series` = 36；与 `SPEC-142t` 阶段 C 同例 |

**判决**：全部 finding 已处置（F1/F2/F4 已修，F3 为既有惯例披露）。本环**未发现** `ctlz`/`cttz`/`ctpop` 的 QEMU 执行**缺陷**（798/798 独立向量 + 414/414 阶段 A 向量经独立 oracle 全等；`ILLI` 真实退出码 `0x88`）。核心指标（**`check-interface` 234/234 + L2 rc=0 + L1 rc=0**）已由真实 rc 达成，阶段 C 完成 ⇒ 状态置 `待验收`（任务级维持 `待验收`，待 reviewer 独立验收）。

#### 第 3 轮 reviewer 审阅（阶段 C / QEMU，2026-10-15）

（独立验收；全部判定基于 reviewer 自跑命令与退出码，非转述；日志 `/tmp/opencode/SPEC-143t/review-c/`。）

**重跑记录（真实 rc）**
- 核心指标：`make check`(L1) rc=**0**（`repository checks (L1): PASS`）；`make check-modules`(L2) rc=**0**（`module checks (L2): PASS`，check-interface **83/83** FAIL=0、trans_* 234==234、check-lit **107/107**、test-codegen/elf/semihost/picolibc-tests 全 PASS）；`check_qemu_trans --strict` rc=0（**234/234**, M1 155/155）；`check-interface` rc=0；`check-patch-tree` rc=0（4 组件 **129** 补丁）；`check-index-blobs` rc=0（93 new-file）；`validate_decodetree` rc=0（234/234）；`validate-encoding` rc=0（234 条）；`check-spec-readonly` rc=0（21 册）；`check-no-residue` rc=0；`check-tasks` rc=0。
- 语义 e2e（**reviewer 第四种独立 oracle：十进制字符串长除法逐位抽取 + 列表运算**，与 engineer 的 SWAR/二分/掩码及阶段 A 三路径、第 1 轮字节查表均不同）：3 条 × `hd` 0..63 **全量** × **7 源值** = **1344 例**（不抽样）+ 全 0 定值 192 + 非 ILLI 12 + ILLI 6 = **1554 例** QEMU 实跑 **1554/1554 passed**（rc=0）；含 `hd=0`、`hd=63`、全 0 ⇒ `ctlz`=`cttz`=`hd+1`（含 63⇒64）、`ctpop`(0)=0、大端锚点 `0x0123456789ABCDEF`、7 个源值（含全 0/全 1/MSB+LSB/高低字各异/F0F0.../DEADBEEF...）。oracle 自检：**1344 例**长除法 ↔ `bin()` 参照逐例相等 + 值域 + 定值断言全过；编码自算 `word = op<<24|opx<<18|rdhb<<12|rdhc<<6|hd` = yaml `value` 三字一致。
- `ILLI` 自建：`rdhb=rd0` × `hd∈{0,63}` × 3 指令 = 6 例真实退出码 **`0x88`**（harness `PASS`）；`rdhc=rd0` 3 例 rc=0 退出 `0x00`（非 0x88）；`rdhb==rdhc` 原地合法 rc=0 退出 `0x00`；1344 语义例（rdhb=rd1）全无 ILLI（hd 0..63 全合法）。
- 无回归：`check-qemu-semantics`(L3) rc=0（**149/149**）；`check-lit-full` rc=0（**12/12**）；`test-codegen`/`test-elf`/`test-semihost`/`check-picolibc-tests`(18 pass/0 fail) 各 rc=0。
- 证据脚本重跑：`run-c.sh` rc=0 **PASS=29 FAIL=0**（输出与完成区逐字一致；QEMU 二进制 md5=`131de0aedb6ec5e67574e1c0750eb9c2` 安装根=构建树 ✓）。
- **reviewer 新反例（engineer A–D 清单外 + 第 1 轮删除用例外）**：篡改 `tests/vectors/bitcnt/bitcnt.yaml` idx=202（ctlz hd=63 src=0x7FFF…FFFF 期望 1→0）⇒ QEMU 实跑 **413/414 failed=1**（rc=1）⇒ `cp`+md5 还原（前后双 `61ed5ffa…`）⇒ **414/414 passed rc=0** 回绿 ✓。
- 工作区快照对账：`git status --porcelain -uall` = **0 行**（干净）；7 目标文件 md5 前后一致；边界 0 项命中（未触 `spec/**`/`contracts/**`/`components/llvm-project/**`/`.tao/knowledge/`）；未提交（提交权归 architect）✓。

**约束核验**
- 临时目录 `/tmp/opencode/SPEC-143t/review-c/` ✓；命令仓库内相对路径 ✓；禁 `git checkout/restore/stash` 还原（`cp`+md5）✓。
- 越界 0（`git diff HEAD~1 HEAD` = 6 组件文件 + 任务书，均 QEMU 面；未触 `spec/**`/`contracts/**`/LLVM/compiler-rt）。
- 补丁纪律（`series`=36、一文件一补丁、`check-patch-tree`/`check-index-blobs` 绿、未手工编辑补丁）✓。
- 完成区对齐：`git show --stat HEAD` = 7 文件 +147/-8；6 项组件变更加任务书与完成区逐一对上；`series` 35→36、README 35→36、`insn_trans` 11→12、`insn.decode` 头计数 231→234、`translate.c` 486→487 行、`trans_bitcnt.c.inc.patch` 88 行 ✓。
- 未弱化门控（阶段 A/B 的3项已知红已全消除：`check-instrinfo` 转绿=阶段 B，`check-interface` 转绿=阶段 C，`test-semihost` 随 L1 转绿）✓。
- `Tcg_gen_clzi_i64` 源码语义确认：clz 全 64 位 + 全 0 返回 arg2 = hd+1 ⇒ `trans_ctlz` 实现正确 ✓。

**判决：Accepted（阶段 C / QEMU）**——全部核心指标（L1/L2/L3 全绿 + check-interface 234/234 + check_qemu_trans 234/234）经 reviewer 独立重跑证实、语义 1554/1554 全过（第四种独立 oracle）、ILLI 自建用例实证、无回归、新反例注入 FAIL→还原→回绿、无多出红、无未处置缺陷。任务级 `**状态**` 维持 `待验收`（待 architect `/complete` 收尾终审）。

**遗留判定**：① ISel 接入不在本任务（`D11.9` 未列）✓；② `insn.decode` 头计数硬编码 256 属既有惯例（`SPEC-142t` 阶段 C F4 同例）✓；③ `ISS-215` 建议闭合：阶段 B/C 已全部完成、L1+L2+L3 全绿、3 项已知红全消除，结构性冲突已解除——建议 architect 收尾时关闭 `ISS-215`（status: open → resolved）。
