# TESTCASES-002t: 向量基础设施（schema + inventory + validate_vectors.py）

**模块**：testcases
**项目里程碑**：M1
**依赖**：无
**状态**：已验证

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `contracts/opcodes.yaml`（SPEC-003t，256 条记录 = 178 条 M1 + 78 条 `excluded_m1`；含 `insn`/`mnemonic`/`format`/`op`/`mask`/`value`/`fields`/`legality`；`insn` 非唯一，唯一编码身份 `(op, ha)`，`op=value>>24`、`ha=(value>>18)&0x3f`）
  - `.tao/knowledge/contract-isa.md`（SimRISC 0.5.3：编码格式、语义、合法性、异常）
  - `contracts/legality_rules.yaml`（SPEC-008t，6 个 fault：ILLI/UNDI/MALIGN/IALIGN/RASOF/RASUF）
  - `.tao/knowledge/adr-0004-test-machine.md`（SPEC-006t：内存映射、复位值、exit 协议、fault 退出码含 `0x87` unmapped、D6.5 `rb0`=当前指令地址）
  - `002t` 上一版产物（`tests/vectors/schema.md`、`inventory.md`、`README.md`、`tools/testcases/validate_vectors.py`、`Makefile` 集成）已按用户决定**丢弃、不保留**——本任务**从零重新生成**；产物形态可只读参考 DADAO-0628（禁止复制数据正文）
- 输出（**本任务拥有**）：
  - `tests/vectors/schema.md`（新增 `expected_pc` 字段、encoding 恒 fault 豁免条款）
  - `tests/vectors/inventory.md`（新增 `format` 列 + 与 `opcodes.yaml` 的机械同步）
  - `tools/testcases/validate_vectors.py`（F9 补强）
  - `Makefile`（`check` 集成保持；如校验项变化需同步）
- 约束：
  - 期望值**手工派生自合约/spec/ADR**，不从 LLVM 输出或 QEMU 运行结果反推
  - 覆盖率主键用 **`(insn, format)`**（`insn` 单独不唯一：20 组 `orrr`/`orri` 共享 `insn`）；等价机器键为 `(op, ha)`
  - 覆盖率门控限定 **M1 scope = `opcodes.yaml` 中 `excluded_m1` 不为 true 的 178 条**；不得排除 RA 存取/块赋值或 `swym`/`illi`/`fence`
  - **本任务不改 `tests/vectors/isa/*.yaml` 的向量数据**（F1/F10 数据修复分别归 `003t`~`007t`）
  - **不改** `contracts/`
  - 完成后不自行 commit

## 返工范围（2026-09-15 最终裁决，用户逐条确认）

> 判决依据见「审阅记录 · 第 3 轮 architect 交叉复核 + 主会话统一判决」。本任务状态为 `已验证`——下列 R1–R5 已完成（engineer 返工 → reviewer 验收 `Accepted` → architect 交叉复核确认）。本节保留为返工范围的记录。

### R1【F2】`inventory.md` 增加 `format` 列

- **现象**：20 组 `orrr`/`orri` 共享 `insn`；现 inventory 首列表头写 `(insn, format)` 但单元格只填 `insn`，40 行不可区分（如 `ext.ub` 出现两次，无法判断 `orrr` 还是 `orri`），`(insn, format)` 主键的消歧动机未达成。
- **要求**：inventory 的 M1 表显式给出 `format`（首列拆为 `insn` + `format`，或新增列），使每行唯一对应 `(insn, format)`；`file` 列保留（下游重组任务负责更新为最终文件名）。

### R2【F3】`inventory` 与 `opcodes.yaml`/数据的机械同步校验

- **现象**：validator 各项校验无一读取 inventory；inventory 无生成器/无校验；0628 已知坑「inventory 过报/未更新」在 v5 无防护。
- **要求（二选一，优先 A）**：
  - A. validator 校验 inventory 的 M1 行集与 `opcodes.yaml` 的 M1 身份集一致（无缺、无多）；或
  - B. 提供 inventory 生成脚本（由 `opcodes.yaml` + 实际数据驱动）并规定重生成流程。
- 不得让 inventory 与数据静默漂移。

### R3【F6】`schema.md` 澄清 encoding 类对恒 fault 指令豁免

- 在 `class` 定义处补注：`encoding` 类要求「可解码执行无 fault」，对**恒 fault 指令**豁免——`illi`（恒 ILLI，`contract-isa.md` §8.2/§9.1）。其覆盖率由 `legality` active 满足，inventory 显式记 `—`。
- 附注（不同理由，不属「恒 fault」）：`ret-riii` 亦无 encoding case，因返回目标依赖 harness 布局、单指令不可构造；理由与处置见 `TESTCASES-006t`，不得混同。
- 同步 `.tao/knowledge/deferred.md` 的 `## testcases` 节（F6 备忘）。

### R4【F7 方案 (i)】`schema.md` 新增 `expected_pc` 字段

- **背景**：`jump`/`call` 的语义只改 PC（`rb0`），`expected_state` 表达不了；`br.*` 的 taken 路径亦然。ADR-0004 D6.5 冻结 `rb0` = **当前指令地址**（由 harness 布局确定，**不是自由变量**），故 PC 效果**可计算**。
- **要求**：schema 新增可选字段 `expected_pc`（48-bit hex，语义：指令 retire 后 PC 的期望值；`null`/缺省表示不断言 PC）。规则：
  - `class: semantic`/`boundary` 且指令改变 PC（`br.*` taken、`jump`、`call`、`ret`）时**应**给出 `expected_pc`（该**存在性**由 `005t`/`006t` 随数据强制，见下）；
  - `expected_pc` 为 48-bit 有效地址（`≤ 0xffff_ffff_ffff`，`bits[63:48]=0`）；
  - 与 `expected_state` 正交：寄存器/内存效果仍用 `expected_state` 表达，PC 效果用 `expected_pc`；
  - `class: legality`/`encoding` 不得带非 null `expected_pc`（与 `expected_state` 同规则）。
- validator 增加对应校验：**当 `expected_pc` 出现时**校验 48-bit、class 一致性、`legality`/`encoding` 不得带非 null `expected_pc`。
- **presence 要求的位置**：`semantic`/`boundary` 且**改变 PC**时必须给出 `expected_pc` 这一**存在性**规则，会立即命中现有 `br.*`（10 条 active semantic）与 `ret` semantic（均无 `expected_pc`）→ 与 F9① 同理，为避免 `002t` 红树，**该存在性规则由 `005t`（`ctrl-br`）/`006t`（`ctrl-jump`/`ctrl-call`/`ctrl-ret`）随数据一并追加**。
- **结果**：F7 的 5 条 PC-only（`jump-iiii`/`jump-rrii`/`call-iiii`/`call-rrii`/`rela.si-rb`）**全部改 active**，不再有 PC-only deferred；其中 `rela.si-rb` 属寄存器运算类，数据修复归 `003t`；`jump`/`call` 归 `006t`；`br.*` taken 归 `005t`。
- **本任务只落 schema + validator 支持**，不改数据；数据任务据本 schema 落地。
- **方案取舍（轻量记录，不立 ADR）**：
  - **选定**：`expected_pc` 作为**独立顶层字段**（与 `expected_state` 平级），语义 = 指令 retire 后 `rb0` 的期望值（48-bit）。
  - **否决「并入 `expected_state`」**：① `expected_state` 的语义是寄存器/内存 bank 快照（`rd`/`rb`/`ra`/`memory`），PC 不在任何 bank 内，硬塞需新增 `rb0` 键，而 schema 明文**禁止 `rb0` 条目**（rd0/rb0 不预置规则），会破坏既有不变量；② PC 是**条件可选**断言（仅改变 PC 的指令需要），独立字段可表达 `null`/缺省，避免污染每个 case 的 `expected_state`；③ 与 `input_state`/`expected_state` 正交，validator 可独立校验 48-bit/class 一致性。
  - **可选性**：本任务中 `expected_pc` 为**可选字段**；「改变 PC 的 active semantic/boundary 必须给出 `expected_pc`」的**存在性强制**不在本任务，留到 `005t`（`ctrl-br`）/`006t`（`ctrl-jump`/`ctrl-call`/`ctrl-ret`）随数据一并追加（避免在未修数据上产生红树，保持每任务可独立验收）。
  - **记录方式**：按 `adr-authoring.md`，本项属「v5 内部模块间格式约定 / 局部易改的实现细节」，判据 1（不可逆/高代价）与判据 4（外部契约）均不命中 → **不立 ADR**，以本节任务书记录为准。

### R5【F9】validator 补强（须在本任务内完成）

> **F9① 的位置（本次裁决）**：F9①（「active semantic/boundary 的 src 字段寄存器必被预置」+ `orrr` shamt 定向守卫）是 **F1 根因的机械化防护**，其落地会使现有 F1 数据（32 条，`rd-shift-extend.yaml`）立即报错。为避免 `002t` 因未修数据而红树、保持每任务可独立验收，**F9① 与 F1 修复同任务，归 `TESTCASES-003t`**；本任务只做 F9②③④ 等基础设施。`003t` 完成后再由 `003t` 向 validator 追加该守卫并验证。

- **②** `legality` 类 `expected_state` 必须为 `null`（非 null → 报错）。
- **③** `spec_cite` 必须为**非空字符串**（现仅检查字段存在）。
- **④** `semantic` 类 memory 地址越界由 warning 改为**阻断错误**（`semantic` 地址必须落在 ADR-0004 RAM 窗口）。
- **边界**：完整语义期望值重算（结果级校验）超出 schema validator 能力，属 golden model 模块，登记 `deferred.md`；本任务只保证 F9②③④ 与 `expected_pc` 等可机械判定的不变量；F9①（操作数字段守卫）见上，归 `003t`。
- **反造假**：对每项新校验在 `/tmp/opencode/TESTCASES-002t/` 副本注入错误，确认 validator 捕获并 exit 1（不得只改校验代码不验校验路径）。

### 不在本任务（明确边界）

- **F1 数据修复**（`orrr` 移位/扩展 20 身份、40 条 semantic/boundary 期望值重算 + `rela.si-rb` 改 active）→ `TESTCASES-003t`；
- **F9① 操作数字段守卫**（F1 的机械化防护，与 F1 同任务落地）→ `TESTCASES-003t`；
- **F10 encoding 向量修复**（各文件操作数字段）→ `003t`~`007t` 各自负责本任务文件；
- **F5 保留编码 → UNDI 的向量表达** → `TESTCASES-008t`（方案取舍见该任务书）。

## 验收标准

1. `tests/vectors/schema.md` 冻结全部字段（含 `rd`/`rb`/`ra`/`memory` 子结构与**新增 `expected_pc`**）与 5 类 class 定义、deferred 规则、覆盖要求
2. `schema.md` 含 encoding 类对恒 fault 指令（`illi`）的豁免条款；`ret-riii` 的例外理由区分清楚（布局限制，非恒 fault）
3. `tests/vectors/inventory.md` 以 `(insn, format)` 逐行可辨（含 `format` 列），覆盖矩阵完整（含 deferred reason），无静默缺席
4. `tools/testcases/validate_vectors.py` 实现 R2（inventory 同步）、R4（`expected_pc` 出现时的类型/48-bit/class 校验）、R5②③④ 校验；错误时 exit(1) 并列出文件+case 序号（`expected_pc` 的**存在性**规则由 `005t`/`006t` 追加）
5. **validator 新校验生效且精确**：注入测试全捕获；真实树 `python3 tools/testcases/validate_vectors.py` 零错误、`178/178` 覆盖与既有校验保持通过（F9① 守卫归 `003t`，本任务不引入其红树）
6. `make check` PASS（本任务完成时即全绿）
7. 本任务**未修改** `tests/vectors/isa/*.yaml` 的向量数据；未改 `contracts/`
8. C-27 类 overlap case 仍显式存在且 `status: deferred`
9. `input_state`/`expected_state` 中无 `rd0`/`rb0` 条目；semantic 向量地址落在 ADR-0004 RAM 区
10. 未自行 commit

## 背景（完整）

### 目标

在任何实现（LLVM/QEMU）字节被写入之前，生成 M1 scope 全量测试向量数据文件，并实现 schema 级 validator 作为 `make check` 门控。所有期望值（编码字节、寄存器状态、异常类型、测试机 fault 码）必须从 `.tao/knowledge/contract-isa.md`（及 `spec/`、`adr-0004-test-machine.md`）手工推导，**不得**从 LLVM 输出或 QEMU 运行结果反推。

本次为**返工**：上一版交付已**丢弃**，本任务**从零重建**向量基础设施（schema + inventory + validator），并按用户裁决直接纳入 `expected_pc`、inventory `format`/同步、F6 澄清、F9②③④ 补强；向量数据（`isa/*.yaml`）不属本任务，由 `003t`~`007t` 各自生成。

### 设计理由

- DADAO-0628 `0002-detailed-roadmap.md` 的 **TDD Contract**：spec first、independent oracle、no bootstrapping from implementations。实现写第一行前向量必须存在。
- **Vector Taxonomy**（5 类，各针对一条规范断言）：

  | class | 规范来源 | 数量目标 |
  |-------|---------|---------|
  | encoding | 附录 A mask/value + format 字段 | 每个 M1 `(insn, format)` ≥1 |
  | legality | 合法性条款 + 动态 fault（rd0/rb0/对齐/immu6/shamt/除零/RAS/unmapped 等） | 每个 fault 触发 ≥1（含 MALIGN/IALIGN/RASOF/RASUF/UNMAPPED） |
  | semantic | 各指令语义 | 每个 M1 `(insn, format)` ≥1 正常情况 |
  | boundary | signed-min / signed-max / zero / carry / overflow | 每个算术/移位 `(insn, format)` ≥1 |
  | overlap | src=dst、双目的、多寄存器范围 | 每个 overlap-legal `(insn, format)` ≥1 |

- **Ordering Rule**：编码表（SPEC-003t）先完成，向量生成才有参考；SPEC-003t 的 `validate_encoding.py` **不**校验向量 YAML，那是本任务的 `validate_vectors.py`。C-27（条件赋值快照）overlap 向量显式 deferred，但必须在 inventory 中出现，不得静默缺席。
- 向量数据与 validator 是后续 LLVM lit / QEMU harness / 集成测试的公共输入。

### 关键概念 / 数据

**向量 schema 字段**（`tests/vectors/schema.md` 须冻结；本次新增 `expected_pc`）：

```yaml
- mnemonic: ld.ub          # 必填：0.5.3 助记符（对应 opcodes.yaml 的 mnemonic）
  insn: ld.ub-rd           # 必填：opcode 身份（对应 opcodes.yaml 的 insn；单独不唯一）
  format: rrii             # 必填：格式；与 insn 组成覆盖率主键 (insn, format)（唯一）
  class: semantic          # 必填：encoding/legality/semantic/boundary/overlap
  encoding:
    word: "0x10040000"     # 必填：完整 32-bit 指令字（hex）
  input_state:             # 必填：执行前寄存器/内存状态（仅列相关字段）
    rd:
      rd1: "0x0000000000000001"
    rb:                    # 可选；键为 rb1..rb63（rb0 恒为 PC，不预置）
      rb1: "0x0000ffff00000000"
    ra:                    # 可选；键为 ra0..ra63
      ra63: "0x0001000000000000"
    memory:                # 可选；按地址列表，非连续
      - address: "0x0000ffff00000000"
        value: "0x0000000000000002"
  expected_state:          # 条件必填（见 class 定义）
    rd:
      rd1: "0x0000000000000002"
    rb: {}
    ra: {}
    memory:
      - address: "0x0000ffff00000000"
        value: "0x0000000000000002"
  expected_pc: null        # 【本次新增】48-bit hex 或 null；改变 PC 的 semantic/boundary 必填
  expected_fault: null     # null / ILLI / UNDI / MALIGN / IALIGN / RASOF / RASUF / UNMAPPED
  status: active           # active / deferred
  deferred_reason: null    # status=deferred 时必填（如 "C-27"）
  spec_cite: "SimRISC-01 §存取RD寄存器"  # 必填：语义来源（测试机约定引用 adr-0004 章节）
  notes: ""                # 可选
```

**寄存器/内存字段约定**（须在 `schema.md` 冻结）：

- `rd`/`rb`/`ra`：键为寄存器名（`rd1`…`rd63`/`rb1`…`rb63`/`ra0`…`ra63`），值为 64 位 hex；**不得出现 `rd0`/`rb0` 条目**（rd0 恒零、rb0 为 PC，预置无意义且会误触发 ILLI）。
- `memory`：元素为 `{address, value}`，`address` 为 48-bit 有效地址（48 位以上须为 0）；语义向量的地址必须落在 ADR-0004 的 RAM 区（返工后由 validator 阻断校验）。
- `expected_pc`：48-bit 有效地址；语义上等于「该指令 retire 后 `rb0` 的值」；`rb0` 执行时 = 当前指令地址（ADR-0004 D6.5），故相对跳转目标 = 当前地址 + `(imm<<2)`。
- `expected_fault` 的 `UNMAPPED` 表示 ADR-0004 D5.8 的 `0x87`（测试机约定，非 spec fault）；其余 6 个为 spec fault（`contract-isa.md` §9）。

**class 定义**（`expected_state` / `expected_pc` / `expected_fault`）：

| class | expected_state | expected_pc | expected_fault | 用途 |
|-------|---------------|-------------|----------------|------|
| encoding | null | null | null | word 与 opcodes.yaml mask/value 一致，可解码执行无 fault |
| legality | null | null | 非 null | **所有 fault 期望的 case**：静态非法（rd0/rb0/immu6=0/shamt 越界等 → ILLI/UNDI）与动态 fault（MALIGN/IALIGN/RASOF/RASUF/除零/INT_MIN÷−1/unmapped） |
| semantic | 必填 | 改变 PC 时必填 | null | 正常执行后寄存器/内存/PC 状态正确 |
| boundary | 必填 | 改变 PC 时必填 | null 或 ILLI | 边界值 |
| overlap | 必填或 null | 改变 PC 时必填 | null 或 ILLI | src=dst 等重叠 |

**status=deferred 规则**：`expected_state`/`expected_pc` 必须为 `null`，`deferred_reason` 必填；C-27 的 overlap case 必须出现在 inventory 中。

**覆盖率要求**：M1 scope（`excluded_m1 != true`，178 条）内每条指令身份 `(insn, format)` 至少各 1 条对应 class 的 case；算术类还需 boundary；条件赋值 overlap 类按 C-27 deferred。

**向量文件组织**（**方案 A：按运算族分，bank 混在文件内**，目标文件集见 `TESTCASES-001k`「文件拆分映射」）：

```
tests/vectors/isa/
  reg-arith.yaml          reg-logic.yaml          reg-shift-extend.yaml
  reg-compare.yaml        reg-cond-assign.yaml    reg-imm-block.yaml
  mem-rd.yaml             mem-rb.yaml             mem-ra.yaml
  ctrl-br.yaml            ctrl-jump.yaml          ctrl-call.yaml
  ctrl-ret.yaml           misc.yaml
```

**inventory.md 格式**：以 `(insn, format)` 为行的覆盖矩阵，列 = `file` / `encoding` / `legality` / `semantic` / `boundary` / `overlap` / `notes`，deferred 填写 reason（如 `C-27`），缺失必须显式记录（不得静默缺席）。

**`tools/testcases/validate_vectors.py` 校验内容**（须含但不少于）：

1. 必填字段存在（`mnemonic/insn/format/class/encoding/input_state/spec_cite`）
2. `class` ∈ {encoding, legality, semantic, boundary, overlap}
3. `status` ∈ {active, deferred}
4. deferred 一致性（`expected_state=null` 且 `deferred_reason` 非空）
5. `expected_fault` ∈ {null, ILLI, UNDI, MALIGN, IALIGN, RASOF, RASUF, UNMAPPED}
6. `encoding.word` 合法 hex 且 ≤ 0xFFFFFFFF
7. `(insn, format)` 存在于 `contracts/opcodes.yaml`（`insn` 单独不唯一，必须带 `format`）
8. `encoding.word` 与对应 opcode 的 `(word & mask) == value` 一致
9. **覆盖率门控**：M1 scope 内每个 `(insn, format)` 至少 1 条 active 向量，缺失报 `COVERAGE MISSING`
10. active semantic/boundary 必须有 `expected_state`；`rd`/`rb` 中不得出现 `rd0`/`rb0` 条目
11. `memory` 元素的 `address` 为 48-bit 有效地址；`semantic` 类的地址须落在 ADR-0004 RAM 区（**返工后改为阻断**）
12. **【本次新增】inventory 同步**（R2）：inventory M1 行集 == `opcodes.yaml` M1 身份集（或生成脚本）
13. **【本次新增】`expected_pc`**（R4）：类型/48-bit/class 一致性
14. **【本次新增】F9②③④**：legality `expected_state==null`；`spec_cite` 非空字符串；semantic memory 地址阻断
15. **【由 `003t` 追加】F9①**：active semantic/boundary 的 src 字段寄存器必被预置（+ `orrr` shamt 定向守卫）——与 F1 修复同任务，本任务不含

退出码：有错误 exit(1) 并列出文件 + case 序号；无错误 exit(0)。`Makefile` 的 `check` target 追加 `validate-vectors`（依赖 `contracts/opcodes.yaml` 存在）。

### 上游引用

- DADAO-0628：`.dadao/DADAO-0628/code-agent/tasks/DL-001d-vector-data.md`（完整转述：目标、schema 字段规范、5 类 class 与 deferred 规则、每条指令覆盖要求、`isa/` 文件组织、inventory 格式、validator 8 项校验、约束、以及三轮 Architecture Review 的 P0/P1 问题与修正）
- DADAO-0628：`.dadao/DADAO-0628/tests/vectors/schema.md`、`inventory.md`、`README.md`、`tests/vectors/isa/`（产物形态参考，禁止复制数据正文）
- DADAO-0628：`.dadao/DADAO-0628/scripts/validate_vectors.py`（validator 实现参考，禁止复制）
- DADAO-0628：`.dadao/DADAO-0628/code-agent/designs/0002-detailed-roadmap.md`（TDD Contract / Vector Taxonomy / Ordering Rule 段）

## 交付物

| 文件 | 说明 |
|------|------|
| `tests/vectors/schema.md` | 向量 YAML 字段规范（含**新增 `expected_pc`**、F6 豁免条款、5 类 class、deferred 规则） |
| `tests/vectors/inventory.md` | 以 `(insn, format)` 为行（**含 `format` 列**）的 M1 覆盖矩阵（含 deferred reason） |
| `tests/vectors/README.md` | 声明向量独立派生自 spec，不从 LLVM/QEMU 生成（沿用） |
| `tools/testcases/validate_vectors.py` | 向量 schema + 覆盖率 + inventory 同步 + `expected_pc` + F9 校验器 |
| `Makefile` | `check` target 的 `validate-vectors`（沿用/同步） |

> 本任务**不产出/不修改** `tests/vectors/isa/*.yaml` 的向量数据。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **助记符**：0.4.1 的 `add`/`muls`/… 全部替换为 0.5.3 命名（`.b/.w/.t/.o` + `s/u`；`ld.ub`/`st.o`/`set.zw`/`br.nz`/`illi` 等）。
2. **覆盖率身份**：0628 用 `(op, ha)`；v5 主键用 `(insn, format)`（256/256 唯一，等价 `(op, ha)`）。
3. **编码表路径**：0628 `tools/opcodes.yaml`；v5 `contracts/opcodes.yaml`。
4. **validator 路径**：0628 `scripts/validate_vectors.py`；v5 `tools/testcases/validate_vectors.py`。
5. **格式体系**：0.5.3 引入 MISC-byte/wyde/tetra/octa 子表（`orrr`/`orri`）。
6. **M1 scope 门控**：v5 以 `excluded_m1` 为唯一判据（178 M1 + 78 排除）。
7. **RB 语义**：0.5.3 RB 算术全 64 位；0.4.1 的 48-bit 截断规则**不适用**。
8. **测试机语义**：v5 新增 ADR-0004（`0x87` unmapped、地址图）；0628 的 `0x8000_0000` RAM 等**不适用**。
9. **deferred reason**：C-27 仍适用；**PC-only deferred 在 v5 采用 `expected_pc` 方案后不复存在**（F7 方案 (i)）。

## 已知坑 / 结论

摘自 DADAO-0628 DL-001d 三轮 Architecture Review：

1. **P0 数据错误**：`rela` 期望值漏加 offset；`addi-rb boundary` 违反 RB 高位保持规则。→ 每条期望值必须按语义逐条手算并附推导。
2. **P0 覆盖率缺口**：首轮 36 条指令零覆盖，validator 未内建覆盖率检查。→ v5 从第一版内建覆盖率门控。
3. **`(mnemonic, format)` 键碰撞**：→ v5 用 `(insn, format)` 作主键。
4. **inventory 过报 / 未更新**：→ inventory 必须由 opcodes.yaml 驱动、与数据同步（本次 R2 落实）。
5. **PyYAML 依赖**：无 JSON fallback；非阻断但应统一。
6. **notes 歧义**：立即数 `+256` 应写明是指令数还是字节数。
7. **不自行 commit**：完成后等待审查。
8. **spec 歧义不猜测**：无法手推期望值时在完成区标 `[OPEN]`，不猜。

## 参考

- DADAO-0628：`.dadao/DADAO-0628/code-agent/tasks/DL-001d-vector-data.md`（完整转述）
- DADAO-0628：`.dadao/DADAO-0628/tests/vectors/schema.md`、`inventory.md`、`README.md`、`tests/vectors/isa/`
- DADAO-0628：`.dadao/DADAO-0628/scripts/validate_vectors.py`
- 本项目：`contracts/opcodes.yaml`、`contracts/legality_rules.yaml`、`.tao/knowledge/contract-isa.md`、`.tao/knowledge/adr-0004-test-machine.md`
- 知识库：`.tao/knowledge/MEMORY.md`、`.tao/knowledge/deferred.md`

## 完成区

**测试结果**：通过 3/3 验证命令 + 20/20 注入用例。
- `python3 tools/testcases/validate_vectors.py` → `178/178`，exit 0。
- `make check` → PASS，exit 0。
- 反造假注入：20/20 捕获（16 负例全部 exit 1 且命中预期错误串；4 正例对照 exit 0，无假阳性）。
- 失败原因：无。

**修改文件**：
- 新增 `tests/vectors/schema.md`、`tests/vectors/inventory.md`、`tests/vectors/README.md`
- 新增 `tools/testcases/validate_vectors.py`
- 修改 `Makefile`（新增 `validate-vectors` target；`check: manifest-check validate-vectors`；`help`/`.PHONY` 同步）
- **未**新增/修改 `tests/vectors/isa/*.yaml`；**未**改 `contracts/`
- 日志（gitignored）：`.tao/logs/TESTCASES-002t-validate_vectors.log`、`-make-check.log`、`-inject.log`

**验收结果**（真实输出）：

```
$ python3 tools/testcases/validate_vectors.py
validate_vectors: 178/178 M1 identities covered OK (inventory sync OK; 0 data files, 0 cases)
exit=0

$ make check
enabled components: none
references: 2
manifest validation: PASS
validate_vectors: 178/178 M1 identities covered OK (inventory sync OK; 0 data files, 0 cases)
repository checks: PASS
exit=0

$ python3 /tmp/opencode/TESTCASES-002t/rework/inject_test.py
[PASS] baseline(no data)            exit=0 expect=0 substr='178/178'
[PASS] R2 missing row               exit=1 expect=1 substr='INVENTORY MISSING: M1 identity (fence, oiii)'
[PASS] R2 extra row                 exit=1 expect=1 substr='INVENTORY EXTRA: inventory.md row (fake, orrr)'
[PASS] R2 no declaration            exit=1 expect=1 substr='COVERAGE MISSING: (fence, oiii)'
[PASS] R4 expected_pc bad hex       exit=1 expect=1 substr='expected_pc not valid hex'
[PASS] R4 expected_pc > 48-bit      exit=1 expect=1 substr='expected_pc is not a 48-bit'
[PASS] R4 legality+expected_pc      exit=1 expect=1 substr='legality case must not carry non-null expected_pc'
[PASS] R4 encoding+expected_pc      exit=1 expect=1 substr='encoding case must not carry non-null expected_pc'
[PASS] R5② legality+state           exit=1 expect=1 substr='legality case must have expected_state == null'
[PASS] R5③ empty spec_cite          exit=1 expect=1 substr='spec_cite must be a non-empty string'
[PASS] R5④ semantic mem out of RAM  exit=1 expect=1 substr='outside ADR-0004 RAM window'
[PASS] word mask/value mismatch     exit=1 expect=1 substr='does not match'
[PASS] rd0 preset                   exit=1 expect=1 substr='must not preset rd0'
[PASS] missing required field       exit=1 expect=1 substr="missing required field 'mnemonic'"
[PASS] deferred non-null state      exit=1 expect=1 substr='status=deferred but expected_state is not null'
[PASS] invalid fault                exit=1 expect=1 substr='invalid expected_fault'
[PASS] non-M1 identity              exit=1 expect=1 substr='is not an M1 identity'
[PASS] positive: semantic+expected_pc exit=0 expect=0 substr='178/178'
[PASS] positive: encoding           exit=0 expect=0 substr='178/178'
[PASS] positive: legality unmapped  exit=0 expect=0 substr='178/178'

injection summary: 20/20 captured
```

**新发现/坑**：
- **覆盖率门控的「无数据」冲突（重要）**：任务书「校验内容 9」原意是「每个 M1 身份至少 1 条
  active 向量」，但本任务明确不产出 `isa/*.yaml`（数据归 `003t`~`007t`）。若按数据计覆盖率，
  空树必然 `0/178` → `make check` 红，与「验收标准 5/6」直接冲突。按用户裁决「以验收标准
  措辞为准」，本任务将覆盖率门控落到 **`inventory.md` 覆盖矩阵**（R2 方案 A）：validator
  校验 inventory 的 M1 行集与 `opcodes.yaml` 的 M1 身份集一致（无缺/无多/无重复），且每行
  至少声明一类覆盖（否则 `COVERAGE MISSING`），故空树输出 `178/178`。数据级逐身份 active
  覆盖由 `003t`~`007t` 各自验收 + `009t` 兜底；数据一旦出现，其逐 case 校验（检查 1–8、
  10–14）即生效。
- **`insn` 非唯一**：`ext.*`/`shr.*`/`shl.*` 的 `orrr`/`orri` 共 20 组共享 `insn`，共 40 条
  M1 记录；inventory 的 `format` 列是消歧关键（如 `ext.ub` 出现两次，`orrr`/`orri` 各一）。
- **`opcodes.yaml` 的 M1 身份唯一性**：178 条 `(insn, format)` 实测 178 唯一（脚本内已断言）；
  `(op, ha)` 为等价机器键。
- **`illi` 是唯一恒 fault 指令**：其 `encoding`/`semantic` 均不可构造，覆盖率只能由
  `legality` active 满足（F6）；`ret-riii` 无 encoding 是**布局限制**、非恒 fault，二者不得混同。
- **`swym` 无任何 fault**（§7 占位指令），故其 `legality` 为 `—`；这是 inventory 中唯一
  legality 不适用的非 illi 身份。
- **R5④ 作用域**：`semantic` 类才做 RAM 窗口阻断（`legality` 需能表达 `UNMAPPED` 越界地址，
  故不受限）；48-bit 地址校验对所有类生效。
- **0628 参考**：其 `scripts/validate_vectors.py` 以 `(mnemonic, format)` 为主键且仅检查
  mnemonic 存在、覆盖率从数据计——v5 不沿用（主键 `(insn, format)`、身份存在性 + 覆盖率
  由 inventory 驱动）。

**遗留问题**：
- **R3 的 `deferred.md` 同步**：`.tao/knowledge/deferred.md` 的 `## testcases` 节中 F6 条目
  **已存在且与 R3 要求一致**（「`illi` 豁免 encoding、覆盖率由 legality 满足、`ret-riii`
  理由不同」），故**未修改**该文件（遵守 engineer 规则「不直接写知识库」）。若主会话需
  增补措辞，请在 `/complete` 统一处理。
- **本任务不含**（明确边界，均已在 schema/validator 中留出接入点）：
  - F9①（active semantic/boundary 的 src 字段寄存器必被预置 + `orrr` shamt 定向守卫）→ `003t`；
  - `expected_pc` 的**存在性**强制（改变 PC 的 active semantic/boundary 必须给出）→ `005t`/`006t`；
  - F1/F10 数据修复 → `003t`~`007t`；
  - F5 保留编码 → UNDI 的向量层表达（`encoding.reserved`）→ `008t`。
- **`spec` 歧义**：无。本任务全部判定均可回溯 `contracts/opcodes.yaml` / `contract-isa.md` /
  ADR-0004，无 `[OPEN]`。

## 审阅记录

### 第 1 轮 engineer 自审

**审查范围**：`tools/testcases/validate_vectors.py`（393 行）、`tests/vectors/schema.md`、
`tests/vectors/inventory.md`（226 行）、`tests/vectors/README.md`、`Makefile` diff。

**逐项审查意见与判决**：

1. **逻辑正确性**
   - inventory 解析：以「表头含 `insn`+`format`」识别 M1 表，跳过分隔行；`_unquote` 去反引号。
     实测解析出 178 行、无重复。✅
   - `(insn, format)` 存在性：`key not in m1_keys` 即报错（含 excluded 身份，正确，向量限 M1）。✅
   - mask/value：`(wval & mask) == value`，与 `tools/spec/validate_encoding.py` 同式。✅
   - `expected_pc`：非 null 时才校验；48-bit 上限 `0xffff_ffff_ffff`；`legality`/`encoding`
     带非 null 即报错；`deferred` 时非 null 亦报错（与 schema 一致）。✅
   - F9②③④：legality `expected_state==null`；`spec_cite` 非空串；semantic memory RAM 阻断。✅
   - 边界：空 `isa/` 目录（本任务真实状态）不报错；`expected_state: null` 的
     `_check_state_banks` 早退；`memory: []` 合法。✅
2. **设计/惯用法**
   - PyYAML import 失败显式 `sys.exit`，与 `tools/spec/validate_encoding.py` 风格一致。✅
   - 未引入新外部依赖（仅标准库 + PyYAML，仓库既有）。✅
   - 覆盖率门控落在 inventory（R2 方案 A），符合任务裁决；已在 docstring 与 inventory 顶部
     显式说明，非「静默成功桩」。✅
   - `Makefile` 用独立 `validate-vectors` target 并以 `contracts/opcodes.yaml` 为前置，符合
     「依赖存在」要求。✅
3. **防造假**
   - 注入测试在 `/tmp/opencode/TESTCASES-002t/rework/inject/` 的 repo 副本执行（不污染真实仓库）；
     16 负例均 exit 1 且命中预期串，4 正例对照 exit 0。✅
   - 真实输出逐字贴入完成区，未估算。✅

**自审发现并已修正的问题**：
- 初版生成器把 `and.o`/`ext.uo` 等按裸助记符分类失败（助记符带位宽后缀）；改用
  `mnemonic.split('.')[0]` 基名分类后 178 条全分类成功。已复验。
- 注入脚本初版 `missing_field`/`pc_48bit`/`mem_out` 三处替换串不匹配；修正后 20/20 通过。

**判决**：无未修 finding。代码级自审通过，状态置 `待验收`。

### 第 1 轮 reviewer 验收

**审查者**：reviewer agent（mimo-v2.5-pro）
**审查日期**：2026-09-15
**审查范围**：`tools/testcases/validate_vectors.py`（393 行）、`tests/vectors/schema.md`（179 行）、`tests/vectors/inventory.md`（226 行）、`tests/vectors/README.md`、`Makefile` diff。

---

#### 一、重跑记录

**命令 1**：`python3 tools/testcases/validate_vectors.py`
```
validate_vectors: 178/178 M1 identities covered OK (inventory sync OK; 0 data files, 0 cases)
EXIT=0
```

**命令 2**：`make check`
```
enabled components: none
references: 2
manifest validation: PASS
validate_vectors: 178/178 M1 identities covered OK (inventory sync OK; 0 data files, 0 cases)
repository checks: PASS
EXIT=0
```

**命令 3**：反造假注入测试（`/tmp/opencode/TESTCASES-002t-review/` 副本）
```
[PASS] baseline(no data)                   exit=0 ✓
[PASS] R2 missing row                      exit=1 ✓
[PASS] R2 extra row                        exit=1 ✓
[PASS] R2 no coverage                      exit=1 ✓
[PASS] R4 expected_pc bad hex              exit=1 ✓
[PASS] R4 expected_pc > 48-bit            exit=1 ✓
[PASS] R4 legality+expected_pc            exit=1 ✓
[PASS] R4 encoding+expected_pc            exit=1 ✓
[PASS] R5② legality+state                 exit=1 ✓
[PASS] R5③ empty spec_cite                exit=1 ✓
[PASS] R5④ semantic mem out of RAM        exit=1 ✓
[PASS] word mask/value mismatch           exit=1 ✓
[PASS] rd0 preset                         exit=1 ✓
[PASS] missing required field             exit=1 ✓
[PASS] deferred non-null state            exit=1 ✓
[PASS] invalid fault                      exit=1 ✓
[PASS] non-M1 identity                    exit=1 ✓
[PASS] positive: semantic+expected_pc     exit=0 ✓
[PASS] positive: encoding                 exit=0 ✓
[PASS] positive: legality unmapped        exit=0 ✓

injection summary: 20/20 captured
```

---

#### 二、逐条核验 R1–R5

| 要求 | 核验结果 | 证据 |
|------|---------|------|
| **R1** inventory 含 `format` 列，20 组 orrr/orri 可辨 | ✅ 通过 | 表头含 `insn`+`format` 两列（line 16）；178 行 `(insn, format)` 全部唯一；20 组共享 `insn` 的 `orrr`/`orri`（如 `ext.ub`/`shr.sb`/`shl.uo`）各占两行，格式列明确区分。 |
| **R2** validator 校验 inventory M1 行集 == opcodes M1 身份集 | ✅ 通过 | validator 解析 inventory（`parse_inventory`），与 `load_opcodes` 的 M1 集做集合差（line 355-360）；缺失报 `INVENTORY MISSING`、多余报 `INVENTORY EXTRA`；注入删除 `fence/oiii` → exit 1 命中；注入新增 `fake/orrr` → exit 1 命中。 |
| **R3** schema.md 含 encoding 类对 illi 豁免条款，ret-riii 理由区分 | ✅ 通过 | `schema.md` line 118-131 专节「encoding 类对恒 fault 指令的豁免（F6）」：`illi` 恒 ILLI（§8.2/§9.1），encoding/semantic 豁免，由 legality 满足；`ret-riii` 例外理由明确标注「非恒 fault，返回目标依赖 harness 布局」，归 `006t`。inventory.md line 194 `ret-riii` 行 encoding 列 `—` 并注明理由。`deferred.md` 的 `## testcases` 节 F6 条目已存在且与 R3 一致，engineer 未重复修改（合理）。 |
| **R4** schema 新增 `expected_pc`；validator 校验出现时的类型/48-bit/class | ✅ 通过 | `schema.md` line 92-106 定义 `expected_pc`：48-bit hex，语义 = retire 后 `rb0`，与 `expected_state` 正交，`legality`/`encoding` 不得非 null，`deferred` 时必须 null。存在性强制明确标注归 `005t`/`006t`。validator line 293-306 实现 R4 校验；4 项注入测试全部捕获。 |
| **R5②** legality `expected_state == null` | ✅ 通过 | validator line 288-290；注入 `legality + expected_state非null` → exit 1 命中。 |
| **R5③** `spec_cite` 非空字符串 | ✅ 通过 | validator line 214-216；注入空串 → exit 1 命中。 |
| **R5④** semantic memory 地址越界阻断 | ✅ 通过 | validator line 143-146（`_check_memory`，`ram_required=True` 仅对 `semantic`）；注入地址 `0x000000000001`（不在 RAM 窗口 `[0xFFFF_0000_0000, 0xFFFF_00FF_FFFF]`）→ exit 1 命中。 |
| **F9① 不在本任务** | ✅ 确认 | validator 无 src 字段寄存器预置校验、无 `orrr` shamt 守卫；docstring line 29-30 明确标注归 `003t`。 |
| **`expected_pc` 存在性不在本任务** | ✅ 确认 | validator 仅在 `expected_pc` 出现（非 null）时校验，不强制其存在；schema.md line 101-102 标注归 `005t`/`006t`。 |

---

#### 三、覆盖率门控设计变更独立分析

**变更描述**：门控从「按数据计覆盖率（active case 逐身份）」改为「按 inventory 覆盖矩阵计（inventory 行集同步 + 每行至少声明一类覆盖）」，空树输出 `178/178`。

**独立分析**：

1. **是否弱化门控？** —— **否**。
   - inventory 是本任务冻结的「覆盖要求声明」，validator 校验：① inventory 的178行与 `opcodes.yaml` 的178个 M1 身份**一一对应**（无缺/无多/无重复）；② 每行**至少声明**一类覆盖（`✓`），否则报 `COVERAGE MISSING`。
   - 如果 inventory 声明了覆盖但无数据：`178/178` 仅表示「声明完整」，不表示「数据已填充」。数据级覆盖率（每个 `(insn, format)` 至少 1 条 active case）由 `003t`~`007t` 各自验收 + `009t` 兜底。
   - 反造假验证：将 `fence` 行全部改为 `—`（无覆盖声明）→ validator 报 `COVERAGE MISSING` exit 1。门控对「声明缺失」有效。

2. **是否与验收标准 5/6 意图冲突？** —— **否**。
   - 验收标准 5 原文：「真实树 `python3 tools/testcases/validate_vectors.py` 零错误、`178/178` 覆盖与既有校验保持通过」。任务书明确本任务**不产出 `isa/*.yaml`**，故「178/178」在空树下只能是 inventory 级门控。
   - 验收标准 6 原文：「`make check` PASS」。`make check` 包含 `validate-vectors`，空树 PASS 是预期行为。
   - 若按数据计门控，空树必然 `0/178` → `make check` 红，与验收标准直接矛盾。engineer 的设计是**唯一可行方案**。

3. **是否必须整改？** —— **否，可接受并登记**。
   - 理由：本任务是**基础设施任务**（schema + inventory + validator），不含向量数据。inventory 覆盖矩阵是**冻结的声明层**，validator 的门控确保声明层不漂移。数据级门控在数据出现后自然生效（validator 的 case-level 校验对每个 YAML 文件立即执行）。
   - **后续保障**：`003t`~`007t` 各自验收时须确认其文件内每个 `(insn, format)` 至少 1 条 active case；`009t`（集成里程碑）兜底全量数据级 `178/178`。

---

#### 四、约束核查

| 约束 | 核验结果 | 证据 |
|------|---------|------|
| 未新增/修改 `tests/vectors/isa/*.yaml` | ✅ | `ls tests/vectors/isa/` → 目录不存在；`git ls-files tests/vectors/isa/` → 空。 |
| 未改 `contracts/` | ✅ | `git diff HEAD -- contracts/` → 无输出。 |
| 未从 LLVM/QEMU 反推 | ✅ | 所有期望值依据 `contracts/opcodes.yaml` / `contract-isa.md` / ADR-0004，无反推痕迹。 |
| 未 commit | ✅ | `git log --oneline -3` → 最新 commit 为任务前的 `8a4cfa9`；`git status` 显示新增文件（`??`）和修改文件（`M` Makefile / 任务文件），但无新 commit。 |

---

#### 五、文件审查

| 文件 | 行数 | 审查意见 |
|------|------|---------|
| `tools/testcases/validate_vectors.py` | 393 | 逻辑正确：inventory 解析以 `(insn, format)` 为键、178行唯一；mask/value 校验与 `validate_encoding.py` 同式；R2 集合差精确；R4 的48-bit / class 一致性 / legality+encoding 禁止非 null 均实现；R5②③④ 均实现且作用域正确（R5④ 仅对 `semantic` 类强制 RAM 窗口）；退出码语义正确。 |
| `tests/vectors/schema.md` | 179 | 冻结完整：5类 class 定义含 `expected_pc` 列、encoding 类 F6 豁免条款、`ret-riii` 例外理由、deferred 规则、`expected_pc` 语义与可选性说明、RAM 窗口定义、文件组织。 |
| `tests/vectors/inventory.md` | 226 | 178行 M1 覆盖矩阵，含 `format` 列；`illi` encoding/semantic 标 `—`（F6）、`ret-riii` encoding 标 `—`（布局限制）、`swym` legality 标 `—`（占位无 fault）、`cs.*` overlap 标 `deferred C-27`；覆盖豁免与例外节完整。 |
| `tests/vectors/README.md` | — | 声明向量独立派生自 spec（沿用）。 |
| `Makefile` | 126 | `validate-vectors` target 以 `contracts/opcodes.yaml` 为前置；`check: manifest-check validate-vectors`；`.PHONY` 同步。 |

---

#### 六、Finding 表

| # | 严重度 | 描述 | 状态 |
|---|--------|------|------|
| F-01 | 信息 | 覆盖率门控从数据计改为 inventory 矩阵计 | 可接受（见第三节分析），后续由 `003t`~`007t` + `009t` 兜底数据级门控 |
| F-02 | 信息 | `deferred.md` 的 F6 条目已存在，engineer 未重复修改 | 合理（遵守 engineer 规则「不直接写知识库」） |

无阻断 finding。无 Needs Revision finding。

---

#### 七、判决

**Accepted**。

验收命令块在 reviewer 独立重跑下全部通过（`validate_vectors` exit 0 → `178/178`；`make check` exit 0 → PASS）；反造假注入 20/20 全部捕获；R1–R5 逐条核验通过；约束全部守住；覆盖率门控设计变更合理且已登记。

主会话可将任务状态改为 `已验证`。


### 第 3 轮 architect 交叉复核 + 主会话统一判决（历史，保留）

**复核者**：architect agent（deepseek-v4-flash）
**主会话独立复验**：`python3 tools/testcases/validate_vectors.py` → `178/178 opcodes covered OK (11 files, 549 cases)` exit 0；`make check` PASS。reviewer 的重跑、注入测试、约束核对**真实有效**，但判决过松。

**统一判决：Needs Revision（状态 `待验收` → `待返工`）**。reviewer 期望值抽查存在**抽样偏差**——12 条抽查中 `shl.ub`/`shr.sb` 命中的是 **`orri`（立即数形式）**，**无一条 `orrr`**，而 `orrr` 正是高风险族。

- **F1【阻断】**：`orrr` 移位/扩展把 shamt **字面值**写进 `rdhd`，但 `opcodes.yaml` 声明 `rdhd` 为 `bank=rd` 寄存器字段（`spec/SimRISC-01:347` 明确寄存器形式）→ 20 身份、40 条 semantic/boundary 期望值系统性错误。**修复归 `003t`**。
- **F2【中】**：`inventory.md` 缺 `format` 列 → 本任务 R1。
- **F3【中】**：inventory 无生成器/无校验 → 本任务 R2。
- **F4 更正**：F1 根因非 spec 歧义（spec 明确「寄存器形式」），是确定性错误。
- **F5**：`UNDI` 保留编码无身份 → 归 `008t`（R3 schema/validator 由 `008t` 落地）。
- **F6**：`illi` 恒 ILLI、encoding 类不可达 → 本任务 R3。
- **F7**：5 条 PC-only deferred → 本任务 R4（`expected_pc` 方案，全部 active）。
- **F8**：旧 `003t` 范围与 002t 重复 → 已重定（本次）。
- **F9**：validator 缺口 → 本任务 R5。
