# TESTCASES-003t: 寄存器间传输与运算

**模块**：testcases
**项目里程碑**：M1
**依赖**：`TESTCASES-002t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `tests/vectors/isa/rd-arith.yaml`、`rd-logic.yaml`、`rd-shift-extend.yaml`、`rd-compare.yaml`、`rd-cond-assign.yaml`、`rd-imm-block.yaml`（`TESTCASES-002t` 产出的现有向量）
  - `tests/vectors/isa/rb-ops.yaml` 的 `add.so-rb`/`sub.so-rb`；`ra-ops.yaml` 的 `ra2rd`/`rd2ra`
  - `tests/vectors/schema.md`（`TESTCASES-002t` 返工后：含 `expected_pc`、encoding 豁免）
  - `contracts/opcodes.yaml`（`op`/`mask`/`value`/`fields`；无独立 `ha` 字段，`ha=(value>>18)&0x3f`）
  - `contracts/legality_rules.yaml`（`rd_dest_rd0`/`rb_dest_rb0`/`multi_immu6_zero` 等）
  - `.tao/knowledge/contract-isa.md` §3（数据类：算术/逻辑/移位扩展/比较/条件赋值/立即数与块赋值）、§2（编码/字段）、§9.1（ILLI）
  - `.tao/knowledge/adr-0004-test-machine.md`（D6.5 `rb0`=当前指令地址）
- 输出（**本任务拥有的文件**，`tests/vectors/isa/`）：
  - `reg-arith.yaml`、`reg-logic.yaml`、`reg-shift-extend.yaml`、`reg-compare.yaml`、`reg-cond-assign.yaml`、`reg-imm-block.yaml`
- 约束：
  - 期望值**手工派生自 `contract-isa.md`/`spec/`/ADR-0004**，不得从 LLVM/QEMU 反推
  - 覆盖率主键 `(insn, format)`；M1 scope 以 `excluded_m1 != true` 为准
  - **只动本任务拥有的目标文件与所涉源文件的拆分**；**不改** `contracts/`；**不改** `mem-*`/`ctrl-*`/`misc` 目标文件
  - 完成后不自行 commit

## 任务范围

### 1. 文件重组（旧 → 新；只描述目标，拆分动作在实现时执行）

| 动作 | 内容 |
|---|---|
| 新建 `reg-arith.yaml` | `rd-arith.yaml` 的 **add/sub/mul/div/rem 全位宽** + `add.si-rd`/`add.si-rb` + `rela.si-rb`；并入 `rb-ops.yaml` 的 `add.so-rb`/`sub.so-rb` |
| 新建 `reg-logic.yaml` | `rd-logic.yaml` 改名（and/or/xor/xnor） |
| 新建 `reg-shift-extend.yaml` | `rd-shift-extend.yaml` 改名（shl/shr/ext） |
| 新建 `reg-compare.yaml` | `rd-compare.yaml` + `rd-arith.yaml` 中的 `cmp.*`（合并去重，见下） |
| 新建 `reg-cond-assign.yaml` | `rd-cond-assign.yaml` 改名（cs.*） |
| 新建 `reg-imm-block.yaml` | `rd-imm-block.yaml` + `ra-ops.yaml` 的 `ra2rd`/`rd2ra`（set.zw/set.ow/or.w/andn.w + rd2rd/rb2rb/rb2rd/rd2rb/ra2rd/rd2ra） |
| 删除 | `rd-arith.yaml`、`rd-logic.yaml`、`rd-shift-extend.yaml`、`rd-compare.yaml`、`rd-cond-assign.yaml`、`rd-imm-block.yaml` |
| 保留（交 `004t`） | `rb-ops.yaml`（仅剩 `ld.o-rb`/`st.o-rb`/`ldm.o-rb`/`stm.o-rb`）、`ra-ops.yaml`（仅剩 `ld.o-ra`/`st.o-ra`/`ldm.o-ra`/`stm.o-ra`） |

- **`cmp.*` 去重**：`rd-arith.yaml` 与 `rd-compare.yaml` 均含 `cmp.ub`/`cmp.uo`/`cmp.sw`/`cmp.ut`/`cmp.uw`；并入 `reg-compare.yaml` 时按 `(insn, format, class)` 去重，冲突时以合约手算为准保留其一，不得产生重复身份。
- **拆分边界**：从 `rb-ops.yaml`/`ra-ops.yaml` 只**移出**本任务归属的 case，不得删除/改动其中的访存 case（归 `004t`）。

### 2. F1【阻断】`orrr` 移位/扩展向量修复（本任务核心）

- **现象**：`shl`/`shr`/`ext` 的 `orrr` 形式把 shamt **字面值**写进 `rdhd`。`contracts/opcodes.yaml` 声明该字段 `bank: rd`、`role: src`；`spec/SimRISC-01:347` 明确「移位量（shamt）取 `rdhd` 的低位（**寄存器形式，`orrr`**）」。
- **影响面**：`(insn, orrr)` 身份 **20 个**——`ext`×8 + `shr`×8 + `shl`×4；带 `expected_state` 的 **40 条**（semantic 20 + boundary 20）期望值**全错**。
- **修复要求**：
  1. `encoding.word` 的 `rdhd`（bits[5:0]）写**寄存器号**（源），并在 `input_state.rd` 预置该寄存器为 shamt 值；
  2. shamt 取值落在该指令 `N` 的有效范围（§3.4.1 表），**且 ≤ N**，使「取低位」与「整值判 `shamt>N`」两种读法结论一致；不得用触发 ILLI 的越界值；
  3. 目的 `rdhb`（bits[17:12]）非 `rd0`；`rdhc`（源）与 shamt 寄存器均须在 `input_state` 预置；
  4. 期望值按 §3.4.1/§3.4.2 重新手算（`rdhb` 低 N+1 位按移位/扩展结果，`rdhb[63:N+1]` 不变）；
  5. `notes` 写清「shamt = rd<k> 的值」，`spec_cite` 指 §3.4.1/§3.4.2；不得再出现「rdN(shamt=v)」式字段/寄存器混淆；
  6. 20 个 `(insn, orrr)` 身份保持 ≥1 active semantic，覆盖率不降。
- **内容溯源（非执行依赖）**：`.work/DADAO-0628/tests/vectors/isa/rd-shift-extend.yaml` 用寄存器形式（`shlu rd3,rd1,rd2`，预置 `rd2`）。
- **验收证据**：逐条列出 `input_state` 中 shamt 寄存器值 + 手算结果 + `spec_cite`。

### 3. F7：`rela.si-rb` semantic 改 active

- **依据**：`rela.si` 结果 = `(PC & ~0xfff) + (imms18<<12)` 写入 `rbha`，`rbha[63:48]` 保持（`contract-isa.md` §3.7 / `SimRISC-02 §PC相对寻址`）；ADR-0004 D6.5 冻结 `rb0` = **当前指令地址**（非自由变量）→ 期望值可算。
- **要求**：`reg-arith.yaml` 的 `rela.si-rb` semantic 改 `status: active` + `expected_state`（`rb2` 新值）+ `deferred_reason: null`；`spec_cite` 指 `SimRISC-02 §PC相对寻址`（+ ADR-0004 D6.5）；`notes` 写明所用 PC 地址及其布局来源。**不得猜测**地址。
- `rela.si` **不写 PC**（PC 由 `rb0` 提供、非本指令改变），故本任务**不使用** `expected_pc`；`expected_pc` 只用于 `005t`/`006t`。

### 4. F10：本任务文件的 encoding 向量修复

- **现象**：现有 `class: encoding` 向量的 `word` 等于 `opcodes.yaml` 的 `value`（操作数字段全 0），对 `encoding` 类定义「可解码执行**无 fault**」而言**不可执行**（如 `add.uo-rd` word=`0x50000000` → `rdha=rdhb=0` → ILLI）。
- **要求**：逐条修正本任务文件（`reg-*` 六个文件）中的 encoding 向量，使 `word` 满足 `(word & mask) == value` 且操作数字段取**最小合法值**、必要寄存器已预置，从而可解码执行且不触发任何 fault。
- **字段规则**（依据 `contract-isa.md` §2.1/§2.2、§3、§9.1 与 `legality_rules.yaml`）：
  - `word = (op<<24)|(ha<<18)|(hb<<12)|(hc<<6)|hd`；`op=value>>24`、`ha=(value>>18)&0x3f`；
  - **写 RD 为目的**用 1（`rd0` 为目的 → ILLI）；**写 RB 为目的**用 1（`rb0` 为目的 → ILLI）；**源寄存器**用 0；**立即数**用 0；**wyde-position** 用 0；**count（rrri）**用 1（=0 → ILLI）；
  - **`orrr` 移位/扩展**：`rdhd` 是**源寄存器**（不是字面 shamt），encoding 填 0（`rd0`，shamt=0）合法；`rdhb`（目的）必须非 0；
  - **例外**：rrrr 双目的 `add.uo`/`add.so`/`sub.uo`/`sub.so`/`mul.uo`/`mul.so` 允许一个目的为 `rd0`；
  - `set.zw`/`set.ow`/`or.w`/`andn.w` 的 RD/RB 目的均须非 0；块赋值 `rd2rd`/`rb2rd`/`ra2rd`/`rd2rb`/`rb2rb` 的目的 `rdhb`/`rbhb` 非 0 且 `immu6 ≥ 1`；
  - 每条 encoding case `expected_state: null`、`expected_pc: null`、`expected_fault: null`、`status: active`。
- **`cmp.*`**：目的 `rdhb` 非 0（`rd0` → ILLI）。

### 5. 机械守卫（F9①，与 F1 同任务落地）

> 说明：F9①（「active semantic/boundary 的 src 字段寄存器必被预置」守卫）与 F1 数据修复同属一处根因。为使其落地后**不产生红树**，将该守卫的实现放入本任务（`002t` 只做 F9②③④ 等基础设施）；本任务在修完 F1 数据后，向 `tools/testcases/validate_vectors.py` 追加该守卫并验证其通过。

- **通用守卫**：解析 `opcodes.yaml` 每条记录的 `fields`；对每条 **active semantic/boundary** case，word 中 `bank ∈ {rd,rb,ra}` 且 `role: src` 的字段所引用的寄存器（`rd0`/`rb0` 除外）必须已在 `input_state` 对应 bank 预置；未预置即报错。
- **定向守卫**：对 `format: orrr` 的 `shl`/`shr`/`ext`，shamt 寄存器（`word & 0x3f`）必须已预置，且其值 ≤ 该指令 `N`。
- **反造假**：在 `/tmp/opencode/TESTCASES-003t/` 副本注入错误（如把某 `orrr` 的 shamt 寄存器从 `input_state` 删除），确认 validator 捕获并 exit 1。

## 验收标准

1. `reg-arith.yaml`/`reg-logic.yaml`/`reg-shift-extend.yaml`/`reg-compare.yaml`/`reg-cond-assign.yaml`/`reg-imm-block.yaml` 存在，且覆盖本任务所属全部 M1 身份（含 `add.so-rb`/`sub.so-rb`、`ra2rd`/`rd2ra`）
2. 旧文件 `rd-arith.yaml`/`rd-logic.yaml`/`rd-shift-extend.yaml`/`rd-compare.yaml`/`rd-cond-assign.yaml`/`rd-imm-block.yaml` 已删除；`rb-ops.yaml`/`ra-ops.yaml` 中本任务归属的 case 已移出，访存 case 原样保留（交 `004t`）
3. **F1**：20 个 `(insn, orrr)` 的 40 条 semantic/boundary 期望值经独立手算复核，`notes` 无字段/寄存器混淆，shamt 寄存器已预置且值 ≤ N
4. **`rela.si-rb`** semantic 已 active 且期望值可回溯（`spec_cite` + notes 写明 PC 地址来源）
5. **F10**：本任务文件内每条 encoding 向量经语义推演确认「可解码执行且不触发任何 fault」（不 ILLI/unmapped），字段值 + 依据章节齐备
6. **F9①**：validator 新增 src 字段守卫 + `orrr` 定向守卫，注入测试全捕获，真实树零误报
7. 未删改 semantic/boundary/legality/overlap 向量的正确性（除 F1/F7/F10 明确的修复外）；未改 `contracts/`；未动 `mem-*`/`ctrl-*`/`misc`
8. `python3 tools/testcases/validate_vectors.py` 零错误，覆盖率输出 `178/178`（覆盖率门控按身份计，不因 encoding 豁免而下降）；`make check` PASS
9. 未自行 commit

## 背景（完整）

### 目标

按**方案 A（按运算族分，bank 混在文件内）**重组并修复寄存器类向量，使其成为独立 oracle：`(insn, format)` 覆盖完整、期望值可回溯合约、encoding 可执行无 fault、`orrr` 移位语义正确、`rela.si` 语义可算。

### 设计理由

- `orrr`/`orri` 共享 `insn`，按运算族归档后同族 `rd`/`rb` 变体集中在同一文件，便于逐族重算与审计（`009t` 兜底）。
- F1 是**确定性错误**（非 spec 歧义）：spec 明确 `orrr` 用寄存器形式；修复方向明确，无需 ADR。
- `rela.si` 的 PC 非自由变量（ADR-0004 D6.5），故 semantic 可 active。

### 关键概念 / 数据

**`orrr` 字段语义**（`contract-isa.md` §2.2/§3.4.1；`contracts/opcodes.yaml` 实测）：

| 字段 | bits | role | bank |
|---|---|---|---|
| `rdhb` | [17:12] | dst | rd |
| `rdhc` | [11:6] | src | rd |
| `rdhd` | [5:0] | src（**寄存器**，其低位为 shamt） | rd |

**`rela.si`**（`contract-isa.md` §3.7）：`rbha = (PC & ~0xfff) + (imms18<<12)`，`rbha[63:48]` 保持；PC = 当前指令地址（ADR-0004 D6.5）。

### 上游引用

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-027a-architect-direct-vector-fixes.md`、`DL-020a-encoding-vectors.md`、`DL-001d-vector-data.md`（内容溯源，非执行依赖）
- 本项目：`TESTCASES-002t` 的审阅记录（F1/F10 判决）、`contracts/opcodes.yaml`、`.tao/knowledge/contract-isa.md`、`contracts/legality_rules.yaml`、`tests/vectors/schema.md`

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **助记符**：`addi`→`add.si`、`setzw`→`set.zw`、`setow`→`set.ow`、`orw`→`or.w`、`andnw`→`andn.w`；同一助记符有 RD/RB 变体（`insn` 后缀 `-rd`/`-rb`）。
2. **写入位置表**按 0.5.3 QFC 表重建，以 `contracts/opcodes.yaml` 为准。
3. **immu6/count 规则**：`immu6 = 0 → ILLI` 沿用；块赋值/multi 必须 count≥1。
4. **rd0/rb0 dest ILLI** 以 0.5.3 合约/`legality_rules.yaml` 为准。
5. **RB 语义**：0.5.3 RB 全 64 位；0.4.1 的 48-bit 截断结论**不适用**。
6. **覆盖率身份**：v5 用 `(insn, format)`。
7. **`orrr` 的 `rdhd` 是寄存器**（F1 教训）：encoding 填 `rd0`（shamt=0）合法；semantic/boundary 用寄存器形式。
8. **文件组织**：v5 方案 A 的 `reg-*` 目标文件集（0628 的 `rd-arith`/`rd-shift-extend` 等仅作形态参考）。

## 已知坑 / 结论

1. **F1 教训**：`notes` 声称的 shamt 必须与 `encoding.word` 的 `rdhd` 解码一致；「字段/寄存器/期望」三重矛盾是最危险的假数据。
2. **orrr 越界**：orri（immu6 可 >N，且 `hd[5:3]`/`hd[5:4]`/`hd[5]` SBZ）才可构造越界 ILLI；orrr 的 shamt 用合法值。
3. **rd0 禁止出现在 `input_state`**：预置 rd0 会误触发 ILLI；validator 机械禁止。
4. **不删改非本任务范围向量**：不得破坏访存/控制流/系统向量。
5. **不自行 commit**：完成后等待审查。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-027a-architect-direct-vector-fixes.md`、`DL-020a-encoding-vectors.md`（内容溯源）
- 本项目：`contracts/opcodes.yaml`、`.tao/knowledge/contract-isa.md`、`contracts/legality_rules.yaml`、`tests/vectors/schema.md`
- 知识库：`.tao/knowledge/MEMORY.md`、`.tao/knowledge/deferred.md`

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

### 第 1 轮 engineer 自审
（待填写）

### 第 1 轮 reviewer 验收
（待填写）
