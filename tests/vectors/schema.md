# Test Vector Schema

`tests/vectors/isa/*.yaml` 的向量 schema。所有字段与语义期望值**独立派生自**锁定的
规范与合约（`spec/`、`.tao/knowledge/contract-isa.md`、`contracts/opcodes.yaml`、
`contracts/legality_rules.yaml`、`.tao/knowledge/adr-0004-test-machine.md`），
**不得**从 LLVM 汇编输出或 QEMU 运行结果反推。

每个 `isa/*.yaml` 文件是一个 YAML 列表，每个元素是一条 test case。

## 字段

### 必填字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `mnemonic` | string | 0.5.3 助记符（对应 `contracts/opcodes.yaml` 的 `mnemonic`） |
| `insn` | string | opcode 身份（对应 `contracts/opcodes.yaml` 的 `insn`；**单独不唯一**） |
| `format` | string | 指令格式；与 `insn` 组成覆盖率主键 `(insn, format)`（唯一） |
| `class` | string | 向量类别：`encoding` / `legality` / `semantic` / `boundary` / `overlap` |
| `encoding` | object | 见下「`encoding` 子结构」 |
| `input_state` | object | 执行前的寄存器/内存状态（仅列相关字段；可为空对象 `{}`） |
| `spec_cite` | string | 语义/合法性来源（规范章节；测试机约定引用 ADR-0004 章节）。**非空字符串** |

### 可选 / 条件字段

| 字段 | 类型 | 条件 | 说明 |
|------|------|------|------|
| `expected_state` | object 或 null | active `semantic`/`boundary`/`overlap` 必填；`encoding`/`legality` 及 deferred 必须为 `null` | 执行后的寄存器/内存状态 |
| `expected_pc` | string 或 null | 可选（本任务中）；`legality`/`encoding` 不得为非 null | 执行后 PC（`rb0`）的期望值，48-bit 有效地址 hex |
| `expected_fault` | string 或 null | 可选 | `null` / `ILLI` / `UNDI` / `MALIGN` / `IALIGN` / `RASOF` / `RASUF` / `UNMAPPED` |
| `status` | string | 可选，默认 `active` | `active` / `deferred` |
| `deferred_reason` | string | `status=deferred` 时必填（非空） | 暂缓原因（如 `"C-27"`） |
| `notes` | string | 可选 | 人类可读备注（如 `shamt = rd<k>`、PC 地址来源） |

### `encoding` 子结构

| 字段 | 类型 | 说明 |
|------|------|------|
| `encoding.word` | string | 完整 32-bit 指令字（hex，`≤ 0xFFFFFFFF`）；须满足 `(word & mask) == value` |
| `encoding.reserved` | boolean | **仅限保留编码 case**（`class: legality`、`expected_fault: UNDI`）。`true` = 该 word 是 QFC 主表 / MISC 子表的空白单元格（reserved），**无** `(insn, format)` 身份。缺省或 `false` = 正常编码 |

#### 保留编码 case（`encoding.reserved: true`）

保留编码（QFC 主表 / MISC 子表空白单元格）**无** `(insn, format)` 身份
（`contracts/opcodes.yaml` 只含已定义编码），故无法满足检查 7/8。
方案 A（`TESTCASES-008t`，已裁定）以 `encoding.reserved: true` 显式标记。

```yaml
- class: legality
  encoding:
    word: "0x08040001"       # 非全零；QFC 主表空白单元格
    reserved: true           # 显式声明：保留编码
  mnemonic: null             # 无已定义助记符
  insn: null                 # 无身份
  format: null               # 无格式
  input_state: {}
  expected_state: null
  expected_pc: null
  expected_fault: UNDI
  status: active
  spec_cite: "SimRISC-00 §SimRISC QFC; contract-isa §2.9/§8.2"
  notes: "QFC 主表 op=0x08（0000-1xxx 整行 reserved）"
```

**字段约束**（`encoding.reserved: true` 时）：

| 约束 | 说明 |
|------|------|
| `class` 必须为 `legality` | 保留编码 case 只能是 fault 期望 |
| `expected_fault` 必须为 `UNDI` | 保留编码触发 UNDI（§8.2），**不是** ILLI |
| `status` 必须为 `active` | 保留编码 case 不可 deferred |
| `word` 不得为 `0x00000000` | 全零字 = `illi` → ILLI（§8.3），非 UNDI |
| `mnemonic` / `insn` 为 `null` | 无已定义身份 |
| `format` 可为 `null` 或字符串 | 可选，用于定位子表 |
| `notes` 非空 | 须给出该 word 在 QFC/子表中的具体位置作为 reserved 依据 |
| `spec_cite` 非空 | 须引用 SimRISC-00 QFC / contract-isa §2.9/§8.2 |

**与 ILLI 的区分**：

| 场景 | fault | 依据 |
|------|-------|------|
| QFC/子表空白单元格（reserved 编码） | **UNDI** | §2.9/§8.2 |
| 全零字 `0x00000000`（`illi 0`） | **ILLI** | §8.3 |
| 已定义编码 + 非法操作数/SBZ 违规 | **ILLI** | §9.1 |
| M1 排除但已定义的编码（RF/cfx/LR-SC） | **ILLI** | ADR-0004 D5.1 |

## 状态字段约定

### `input_state` / `expected_state`

- `rd` / `rb` / `ra`：键为架构寄存器名（`rd1`…`rd63` / `rb1`…`rb63` / `ra0`…`ra63`），
  值为 64 位 hex 字符串。
- **不得出现 `rd0` / `rb0` 条目**：`rd0` 恒零、`rb0` 为 PC（ADR-0004 D6.5），
  预置无意义且会误触发 ILLI。
- `memory`：元素为 `{address, value}`；`address` 为 48-bit 有效地址
  （`≤ 0xffff_ffff_ffff`，即 `bits[63:48]=0`）。

```yaml
- mnemonic: ld.ub
  insn: ld.ub-rd
  format: rrii
  class: semantic
  encoding:
    word: "0x10041000"      # ld.ub rd1, rb1, 0（rdha=1、rbhb=1、imms12=0）
  input_state:
    rd:
      rd1: "0x0000000000000001"
    rb:
      rb1: "0x0000ffff00000000"
    memory:
      - address: "0x0000ffff00000000"
        value: "0x0000000000000002"
  expected_state:
    rd:
      rd1: "0x0000000000000002"
    rb: {}
    ra: {}
    memory: []
  expected_pc: null
  expected_fault: null
  status: active
  deferred_reason: null
  spec_cite: "SimRISC-01 §存取RD寄存器"
  notes: ""
```

### 内存地址范围（ADR-0004 D1）

- RAM 窗口：`[0xffff_0000_0000, 0xffff_00ff_ffff]`（16 MiB）。
- `semantic` 类的 `memory` 地址**必须**落在 RAM 窗口内（validator 阻断校验）。
- `legality` 类可表达 unmapped（`expected_fault: UNMAPPED`）等越界地址，不受此限。
- 非 RAM 地址（ROM `0xffff_ffff_0000`–`0xffff_ffff_ffff`、Exit port
  `0xffff_8000_0000`–`0xffff_8000_0007`）须显式引用 ADR-0004 章节。

### `expected_pc`（本版新增）

- 语义：**该指令 retire 后 `rb0` 的期望值**（48-bit 有效地址 hex；`null`/缺省表示不断言 PC）。
- 与 `expected_state` **正交**：寄存器/内存效果用 `expected_state` 表达，PC 效果用
  `expected_pc` 表达（`expected_state` 不预置 `rb0`，见上）。
- `rb0` 在执行时等于**当前指令地址**（ADR-0004 D6.5），故相对跳转目标 = 当前地址 +
  `(imm<<2)`，PC 效果可计算、非自由变量。
- 规则：
  - `class: semantic` / `boundary` / `overlap` 且指令改变 PC（`br.*` taken、`jump`、
    `call`、`ret`）时**应**给出 `expected_pc`；该**存在性**要求由 `TESTCASES-005t`
    （`ctrl-br`）/`006t`（`ctrl-jump`/`ctrl-call`/`ctrl-ret`）随数据一并强制。
  - `expected_pc` 出现（非 null）时须为 48-bit 有效地址。
  - `class: legality` / `encoding` **不得**带非 null `expected_pc`（与 `expected_state` 同规则）。
  - `status: deferred` 时 `expected_pc` 必须为 `null`。
- 本任务只落 schema + validator 支持，不改数据。

## class 定义

| class | expected_state | expected_pc | expected_fault | 用途 |
|-------|---------------|-------------|----------------|------|
| `encoding` | `null` | `null` | `null` | `word` 与 `opcodes.yaml` 的 mask/value 一致，且**可解码执行无 fault** |
| `legality` | `null` | `null` | 非 null | **所有 fault 期望的 case**：静态非法（rd0/rb0/immu6=0/shamt 越界等 → ILLI/UNDI）与动态 fault（MALIGN/IALIGN/RASOF/RASUF/除零/INT_MIN÷−1/unmapped） |
| `semantic` | 必填 | 改变 PC 时必填 | `null` | 正常执行后寄存器/内存/PC 状态正确 |
| `boundary` | 必填 | 改变 PC 时必填 | `null` 或 `ILLI` | 边界值（signed-min / signed-max / zero / carry / overflow） |
| `overlap` | 必填或 `null` | 改变 PC 时必填 | `null` 或 `ILLI` | src=dst、双目的、多寄存器范围重叠 |

### `encoding` 类对恒 fault 指令的豁免（F6）

`encoding` 类的定义是「**可解码执行无 fault**」，因此**恒 fault 指令无法构造
`encoding` case**：

- **`illi`**（`oiii`）：恒触发 ILLI（`contract-isa.md` §8.2/§9.1；全零字
  `0x00000000` 即 `illi 0` → ILLI，§8.3，**不是** UNDI）。故 `illi` **豁免**
  `encoding`（及 `semantic`）类，其覆盖率由 `legality` active
  （`expected_fault: ILLI`）满足；inventory 显式记 `—`。

**例外（理由不同，不得混同）**：`ret-riii` 亦无 `encoding` case，但**并非**恒 fault
——`ret` 的返回目标依赖 harness 布局、单指令不可构造。其理由与处置见
`TESTCASES-006t`；inventory 显式记 `—` 并注明理由。

### `status=deferred` 规则

- `expected_state` / `expected_pc` 必须为 `null`；
- `deferred_reason` 必须为非空字符串；
- C-27（条件赋值快照）的 `overlap` case 必须出现在 `inventory.md` 中，**不得静默缺席**。

## Fault 类型

| Fault | 含义 | 来源 |
|-------|------|------|
| `ILLI` | 非法指令 | `contract-isa.md` §9.1 |
| `UNDI` | 保留编码 | §8.2 |
| `MALIGN` | 内存访问非对齐 | §9 |
| `IALIGN` | 取指非对齐 | §9 |
| `RASOF` | RegRAS 溢出 | §9.2 |
| `RASUF` | RegRAS 下溢 | §9.2 |
| `UNMAPPED` | 地址未映射（测试机约定，退出码 `0x87`） | ADR-0004 D5.8 |

## 覆盖率要求

- **M1 scope**：`contracts/opcodes.yaml` 中 `excluded_m1 != true` 的 **178 条**。
  不得排除 RA 存取/块赋值或 `swym`/`illi`/`fence`。
- **主键 `(insn, format)`**（等价机器键 `(op, ha)`，`op = value>>24`、
  `ha = (value>>18)&0x3f`）。`insn` 单独不唯一（20 组 `orrr`/`orri` 共享 `insn`），
  **必须**带 `format`。
- 每个 M1 身份 `(insn, format)` 至少 1 条对应 class 的 case；算术/移位类还需
  `boundary`；条件赋值 `overlap` 按 C-27 deferred。
- 覆盖率与 `inventory.md` 机械同步：`inventory.md` 的 M1 行集必须与
  `opcodes.yaml` 的 M1 身份集一致（无缺、无多、无重复）——由
  `tools/testcases/validate_vectors.py` 校验。

## 文件组织（方案 A：按运算族分，bank 混在文件内）

```
tests/vectors/isa/
  reg-arith.yaml          reg-logic.yaml          reg-shift-extend.yaml
  reg-compare.yaml        reg-cond-assign.yaml    reg-imm-block.yaml
  mem-rd.yaml             mem-rb.yaml             mem-ra.yaml
  ctrl-br.yaml            ctrl-jump.yaml          ctrl-call.yaml
  ctrl-ret.yaml           misc.yaml
```

## 校验

`tools/testcases/validate_vectors.py` 对上述字段、class/fault 取值、`(insn, format)`
存在性与 mask/value 一致性、`expected_pc`、`inventory` 同步、覆盖率等做机械校验；
有错误时 `exit(1)` 并列出文件 + case 序号。完整语义期望值重算属 golden model
模块（见 `.tao/knowledge/deferred.md`），不在 schema validator 能力内。
