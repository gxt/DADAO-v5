# SPEC-143t: `ctlz`/`cttz`/`ctpop`（位扫描与计数）指令落地

**模块**：spec
**项目里程碑**：M8
**依赖**：`ADR-0012 D11`（**前置：`D11.1`–`D11.10` 逐条确认完成 + 用户明确授权改 `spec/`**〔`docs/Process-06 §2`〕，见「开工前置」；`D11` 目前仍是**提案**）；`SPEC-141t`（ISA 指令扩展预研，候选 `C2` = `clz`/`ctz`/`popcount`，**只读**来源）；`INFRA-078t`（compiler-rt 预研：缺口来源，**只读**）；`LLVM-079t`（现状：`CTLZ`/`CTTZ`/`CTPOP` 走 `Expand`，**只读**溯源）；`docs/Process-06`（`spec/` 目录保护）；`ADR-0012 D4`（`spec/` 只读策略）。**串行**：与 `SPEC-142t`（`rev.{o,t,w,b}` 落地）**须串行**（同改 `contracts/opcodes.yaml` / `tests/vectors/**`），先后由主会话排定。
**状态**：待开始

## 执行环境
**执行环境**：本地

> ⛔ **开工前置（未满足，不得下发）**：① `ADR-0012 D11` 的 `D11.1`–`D11.10` **须经用户逐条确认**（`D11` 现为**提案**）；② **须取得用户对改 `spec/` 的明确授权原话**（`docs/Process-06 §2`：`spec/` 下任何新增/修改/删除均须用户**事先**明确允许，未授权即 **BLOCKED**），授权原话须写入本任务书；③ 与 `SPEC-142t` 的**先后顺序须由主会话排定**（两者同改共享文件，不得并行）。以上三条满足前，本任务**不得 `/dispatch`**。

## 立项来源 / 用户裁定落纸

- **来源**：`ADR-0012 D11`（**2026-10-14 新增；提案**）＝ `SPEC-141t §候选` 预研候选 **`C2`（`clz`/`ctz`/`popcount`）** 的**落地路径 = 新增 ISA 指令**（用户 2026-10-14 经主会话问答裁定「**可以增加部分指令**」并指定实现范围，见 `adr-0012 §D11.0`）。
- **用户裁定原话（原样引录，渠道 = 经主会话问答，2026-10-14；完整引录见 `adr-0012 §D11.0`）**：
  - 指令名：「**ctlz/cttz/ctpop**」
  - 范围：「**先就这三个吧**」⇒ `cls`/`clo`/`cto`/`parity`/`ffs`/`ffz` 等**首版不做**
  - 编码：「**ctlz/cttz/ctpop 的 opx：011-110/011-111/011-101**」
  - 前序已接受：① `ctlz(0)`/`cttz(0)` **定值 = 范围宽度（`hd+1`）**；② **不需要 `encode_onehot`**；③ **无后缀**（编码借 `MISC-octa` 格位）；④ `cttz` 的 `hd` 语义「保持 `[hd:0]` 上界」= 主会话建议、用户未反对 ⇒ **仍标「待用户确认」**（见下）。
- **本任务 = 执行落点**：把 `D11` 的决策**逐条落到全链**（`spec/` + `contracts/` + 生成器 + 向量 + MC + QEMU + 门控）。**`D11` 未逐条确认 ⇒ 不得开工**；**待确认项未裁决 ⇒ 不得自行选定**（见「待用户确认项」）。

## 目的

为 `SimRISC` 新增 **3 条** 位扫描/计数指令（`ctlz` 前导零 / `cttz` 末尾零 / `ctpop` 置位数），以**单条指令**覆盖 **8/16/32/64 位任意宽度**（由 `hd` 指定有效位上界），为后端 `int_ctlz`/`int_cttz`/`int_ctpop` 提供 ISA 支撑——替代当前的软件展开（`LLVM-079t`：`CTLZ`/`CTTZ`/`CTPOP` 走 `Expand`，展开为 `xnor.o`/`and.o`/`sub.uo`/`shr.uo`/`mul.uo`）。对比 RISC-V 的 `clz` + `clzw` **两条**才覆盖到 32 位，本方案一条即覆盖到任意宽度。

## 指令契约（**自包含**；与 `adr-0012 §D11` 一致）

### 1. 格式与编码

三条统一 `orri` 格式：`opx`（= `ha`，`bits[23:18]`）+ 两个寄存器 + 6 位立即数在 `hd[5:0]`；主 op = `MISC-octa` = `0x40`。

| 指令 | `id` | 子表 | `op` | `opx` | `mask` | `value` |
|---|---|---|---|---|---|---|
| `ctpop` | `ctpop_orri_rd` | `MISC-octa` | `0x40` | `011-101`（`0x1D` = 29） | `0xFFFC0000` | `0x40740000` |
| `ctlz` | `ctlz_orri_rd` | `MISC-octa` | `0x40` | `011-110`（`0x1E` = 30） | `0xFFFC0000` | `0x40780000` |
| `cttz` | `cttz_orri_rd` | `MISC-octa` | `0x40` | `011-111`（`0x1F` = 31） | `0xFFFC0000` | `0x407C0000` |

- `value = op<<24 | opx<<18`；`mask` 锁 `op` + `opx`。
- 字段：`rdhb`（**目的**，`bits[17:12]`，bank `rd`）／`rdhc`（**源**，`bits[11:6]`，bank `rd`）／`hd`（`bits[5:0]`，**无符号立即数**，**有效位上界**）。**注**：`opcodes.yaml` 中该立即数字段惯用名 **`immu6`**（`role: imm`、`bank: imm`、`signed: false`，先例 `ext.uo_orri_rd`）。
- 汇编语法（`spec/Toolchain-01 §5` 的 `orri` 行 = `助记符 dst, src, immu6`）：`ctlz rdHB, rdHC, hd`（例：`ctlz rd8, rd9, 63`）。
- **不冲突**（现场已核，三条实证）：① `spec/SimRISC-00 §4.2 MISC-octa` 第 `011-xxx` 行**仅** `000`–`100` 有条目，`101`/`110`/`111` **三格为空**（reserved）；② `SPEC-069t` 的 reserved/已删集 = 每子表 8 条（`001-000…011` 4 逻辑 + `010/011-000/001` 2 ext × 2 格式），**不含 `011-101/110/111`**；③ `contracts/opcodes.yaml` 中 `op: '0x40'` 的 32 条，`ha` 集合 = `{8–11, 16–20, 24–28, 42–46, 48–54, 56–59, 61–62}` ⇒ **29/30/31 无条目**（`0x40740000`/`0x40780000`/`0x407C0000` 全文 0 命中）。

### 2. 语义（`hd` = 有效位上界，三条统一）

- **有效位** = `rdHC[hd:0]`（共 **`hd+1`** 位，`hd ∈ 0..63`）；`hd` 以上的位**不参与**运算。
- `ctlz`：从 bit `hd` **向下**数前导零（到首个 1 为止）⇒ 有效位内的前导零个数。伪代码：`n=0; for i = hd down to 0: if bit(i)==1 break; n++`。
- `cttz`：从 bit 0 **向上**数末尾零（到 bit `hd` 为止）⇒ 有效位内的末尾零个数。伪代码：`n=0; for i = 0 up to hd: if bit(i)==1 break; n++`。
- `ctpop`：`rdHC[hd:0]` 内 **1 的个数**。
- **⚠ `cttz` 的 `hd` 作「上界」为待确认项**（见「待用户确认项」；备选「下界」语义见 `D11.10(b)`，未采用）。

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

## 待用户确认项（**不得自行选定**）

1. **`D11` 逐条确认**：`D11.1`–`D11.10` **尚未逐条确认**（`ADR-0012 §D11` 为**提案**）⇒ **逐条确认完成**是本任务的前置。
2. **`spec/` 修改授权**（`docs/Process-06 §2`）：须用户**事先明确允许**并**留存授权原话**写入本任务书；未授权 ⇒ **BLOCKED**。
3. **`D11.4`（`cttz` 的 `hd` 语义）**：建议「**上界**（`[hd:0]`）」系主会话建议、用户**未反对**但**未明示确认**（见 `D11.0` 前序④）⇒ 确认前**不得**按上界写正文 / 向量。
4. **`D11.9` 正文分册归位**：建议 **`spec/SimRISC-04 §4.2`（`Bit manipulating：位操作指令`）**（现场依据：`ext.uo_orri_rd` 的 `spec_cite` 即该节）⇒ **待用户确认**；确认前不得写 `spec/SimRISC-04` 正文。
5. **`scope` 取值**（与 `D10.6b` **同一未决项** ⇒ 引用之）：建议 `scope: m8`；**确认前不得写入 `opcodes.yaml` / `check_scope.py`**。

## 分阶段实现（照 `SPEC-142t` 三阶段；**一个任务书、三阶段验收**）

- **阶段 A（契约 / 编码层，单任务可验收）**：`spec/SimRISC-00` QFC `§4.2` 三格 + 例外说明一句 + 计数 + changelog；`spec/SimRISC-04 §4.2` 正文（**依「待确认项 4」定案**）+ 各册 `LEGALITY` 生成区（`tools/spec/gen_legality_list.py --apply`）+ `contracts/opcodes.yaml`（`tools/spec/generate_opcodes.py`）+ `.tao/knowledge/contract-isa.md` / `contract-asm-list.md`（`tools/llvm/gen_asm_list.py`）+ `tests/vectors/**` + `inventory.md` + `tools/testcases/generate_isa_vectors.py`。
- **阶段 B（MC）**：`DADAOInstrInfo.td`（def/mnemonic/编码）、`DADAOAsmParser`（`orri` 受理）、`DADAOInstPrinter`、`MCCodeEmitter`/decode；`check-instrinfo` / `check-isa-coverage` 回绿。
- **阶段 C（QEMU）**：`insn.decode`（三条 token）+ `trans_ctlz`/`trans_cttz`/`trans_ctpop` + `translate.c` 分派；语义向量经 QEMU 跑通。
- **依赖关系**：**阶段 A → 阶段 B / 阶段 C**（编码/契约先行）；B/C 可并行（不同补丁树），同改 `contracts/` 或 `tests/vectors/` 时**串行**。
- **理由**：与 `D9`/`D10` 的「全链单任务」惯例一致；三阶段共享同一编码真源；阶段化验收让契约层先独立可验（Spec-first）。

## 接口规范

- **输入**：`adr-0012 §D11`（**提案 + 用户原话**）；`spec/SimRISC-00 §3.1/§4.2`（QFC 子表，**只读**，改须授权）；`contracts/opcodes.yaml` / `contracts/legality_rules.yaml`（**真源**）；`spec/Toolchain-01 §5`（`orri` 汇编语法）；`tools/spec/generate_opcodes.py`、`tools/spec/gen_legality_list.py`、`tools/llvm/gen_asm_list.py`、`tools/testcases/generate_isa_vectors.py`；`components/llvm-project/patches/llvm/lib/Target/DADAO/**`、`components/qemu/patches/target/dadao/**`。
- **输出**：`spec/SimRISC-00` + `spec/SimRISC-04`（依「待确认项 4」）、`contracts/opcodes.yaml`（**生成**）、`.tao/knowledge/contract-isa.md`、`contract-asm-list.md`（**生成**）、`tests/vectors/**` + `inventory.md`、MC 补丁、QEMU 补丁、门控；完成区（**≤30 行**）+ 一键证据脚本（`.work/evidence/<本任务ID>/`）。
- **越界声明（硬性）**：改 `spec/**` **仅限**授权的 `SimRISC-00 §4.2` 三格 + 例外说明 + 计数 + changelog，以及（经「待确认项 4」确认后的）`SimRISC-04 §4.2` 正文/生成区；**同一变更内**须更新 `manifests/spec-readonly.lock.toml` 对应册 `sha256`（`Process-06 §5`）；**未确认不得**动 `spec/` 正文。

## 验收标准

1. `**状态**` = `待开始`（开工前）→ `待验收`（实现后）；本任务书**自包含**；`**项目里程碑**` = `M8`。
2. **前置状态**：`adr-0012 §D11` 的 `D11.1`–`D11.10` **已逐条确认**；**`spec/` 修改授权原话已在本任务书留存**；`D11.4`/`D11.9`/`scope` 待确认项**已裁决**——**任一项未满足即不得开工**（若发现未满足 ⇒ 停下报告，不自行选定）。
3. **编码逐条**：三条 `value`/`mask`/`op`/`opx` 与「指令契约 §1」**逐字一致**；`generate_opcodes.py` 生成结果与 `contracts/opcodes.yaml` **幂等**（重生成 diff = 0）；`validate-encoding` rc=0。
4. **语义逐条（独立 oracle，禁从 LLVM/QEMU 反推）**：以 **Python 大整数**独立实现三条语义（含 `hd` 边界），对**每条指令 × `hd` 代表集**（至少 `hd` = 7/15/31/63 与 `0`）以及边界（`rdHC=0`、`rdHC` 全 1、`rdHB==rdHC`、`rdHC=rd0`、`hd=0`、`hd=63`）产出期望值；向量经 QEMU 实跑**全部一致**。**端序 = 大端**（本项目为大端），端序敏感用例须显式覆盖。**计数现场统计、不写死**。
5. **定值逐条**：`rdHC[hd:0]` 全 0 ⇒ `ctlz` = `cttz` = **`hd+1`**（对 `hd` 各取值均验，含 `hd=63` ⇒ 64）；`ctpop(0)` = 0。
6. **合法性逐条**：`hd ∈ 0..63` **全部合法**（**无 `hd` 值触发 ILLI**——须含可达 FAIL 反例：把断言改成「存在非法 `hd`」应 FAIL）；`rdhb == rd0` ⇒ ILLI；`rdhc == rd0` / `rdhb == rdhc` ⇒ **不**报 ILLI；`contracts/legality_rules.yaml` **未新增**规则（diff 证）。每条断言均有**可达 FAIL 路径**（注入 ⇒ FAIL ⇒ `cp`+md5 还原 ⇒ 回绿）。
7. **同步面齐备**（`D11.9` 十项，缺项须显式标「本环不涉及 + 理由」）：`SimRISC-00 §4.2` 三格 + 例外说明 + 计数、`SimRISC-04 §4.2` 正文与生成区、`opcodes.yaml`、`contract-isa.md`/`contract-asm-list.md`、`tests/vectors/**` + `inventory.md`、MC、QEMU、门控；`legality_rules.yaml` **无新增**；ISel **不在本任务**（显式声明）。
8. **门控**：`make check`(L1)、`make check-modules`(L2) 各 **rc=0**；语义向量（`check-qemu-semantics` 或等价，含新增三条向量）rc=0；`check-isa-coverage` / `check-instrinfo` / `check-asm-list-drift` / `check-legality-drift` / `check-legality-invariants` / `check-rule-refs` / `check-scope` / `check-spec-readonly` 各 rc=0；`check-no-residue` / `check-knowledge-refs` / `tools/infra/check_issues.py` 各 rc=0。
9. **`spec/` 授权与锁**：`git diff --name-only` 与 `spec/` 清单交集**均为本任务书授权范围**；变动的只读册 `sha256` 已在**同一变更**内更新（`check-spec-readonly` rc=0）。
10. **一键证据脚本**：非交互、任一失败非零退出、逐项打印「检查名 + 期望/实际 + rc」、含**可达 FAIL** 自检（**计数不写死**）。完成区（**≤30 行**）与真实输出**逐条对齐**；长输出留 `.work/log/spec/**`（指针给出）；**禁** `cmd | tee` 吞码。

## 硬约束（下发提示必带）

1. **临时目录** `/tmp/opencode/<本任务ID>/`；命令一律在 **workdir（= 仓库根）** 内、用**相对路径**；**禁**出界 `cd`（绝对 / `~` / `..`）；禁仓库内临时文件。
2. **不提交 git**（提交权归 architect）；显式 staging（**禁** `git add -A`/`.`）。
3. **前置边界**：`D11` **未逐条确认** ⇒ **不得开工**；**`spec/` 未授权** ⇒ **BLOCKED**；`D11.4`（`cttz` 语义）/ `D11.9`（分册归位）/ `scope` 未裁决 ⇒ **停下报告**，不自行选定。
4. **与 `SPEC-142t` 串行**：两者同改 `contracts/opcodes.yaml` / `tests/vectors/**`（`AGENTS.md`「同改共享文件的任务一律串行」）⇒ **不得与 `SPEC-142t` 并行**；**先后顺序由主会话排定**；开工前须确认 `SPEC-142t` 的落地状态，避免同文件冲突。
5. **Spec-first**：期望值来自 `contracts/` / `contract-isa.md` 与本任务书契约，**不从 LLVM/QEMU 反推**；**独立 oracle** 用 Python 大整数独立派生。
6. **`spec/` 保护**：改 `spec/**` 仅限授权范围；同一变更内更新 `manifests/spec-readonly.lock.toml` 的 `sha256`（`Process-06 §5`）。
7. **完成区与真实输出逐条对齐**；**计数不写死**；事实与推测分开；复杂命令输出留 `.work/log/spec/**`。
8. **失败保留现场并继续推进**（自行处置：查证 / 绕行 / 有据重试并记录次数 / 登记后跳过）；**只在需用户语义裁定（新决策 / 需授权）时留问**，禁自拟自答；**不得以重试掩盖根因**。
9. **补丁导出纪律**：MC/QEMU 改动按 `docs/Process-01` 树形补丁集（一文件一补丁 + `git apply`），`check-patch-tree` 须绿。
10. **反例注入还原纪律**：**禁** `git checkout`/`restore`/`stash`/`git show <commit>:<path>`；一律 `cp` 备份 + md5 对账，或临时树注入。
11. 文本**不写**字面 `.work/<具体路径>`（用 `<>` 占位）；任务书**自包含**。

## 参考检索（`DADAO-0628`，**内容溯源，非执行必需**）

> 规划期只读检索 `.cache/refs/DADAO-0628/**`（**不复制代码、不作执行依赖**）。
>
> - **0628 做法**：ISA **无** `ctlz`/`cttz`/`ctpop`——`sail/`（含 `dadao_insts.sail`）与 `contracts/isa/` 对 `ctlz|cttz|ctpop|popcount` **`grep` 0 命中**（2026-10-14 现场）⇒ 0628 **未新增**此类指令；其唯一相关痕迹是 llvm-test-suite 用例 `popcount-clz-ctz` 失败，但 `ML-004b` 记录的**根因不同**（对齐 MALIGN / `codegen-call-clobbers-gprb-not-declared`），**并非缺指令**。
> - **本项目差异**：真源 = `spec/SimRISC-00` QFC 子表 + `contracts/opcodes.yaml`（生成器）+ `manifests/spec-readonly.lock.toml` 哈希锁 + L1 编码门控；本项目为**大端**。
> - **建议落点**：沿用本项目既有全链同步面（本任务书「指令契约」+ `D11.9` 十项），**不引入** 0628 的 sail 路径。

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
