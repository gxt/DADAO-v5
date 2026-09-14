# TESTCASES-002t: 向量 schema + inventory + validate_vectors.py

**模块**：testcases
**项目里程碑**：M1
**依赖**：`SPEC-003t`、`SPEC-008t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `contracts/opcodes.yaml`（SPEC-003t，256 条记录，唯一 `insn` 身份 + op/ha/mask/value/fields/legality）
  - `.tao/knowledge/contract-isa.md`（SimRISC 0.5.3：编码格式、语义、合法性、异常）
  - `contracts/legality_rules.yaml`（SPEC-008t，ILLI/UNDI/MALIGN/IALIGN/RASOF/RASUF 条件）
- 输出：`tests/vectors/schema.md`、`tests/vectors/inventory.md`、`tests/vectors/README.md`、`tests/vectors/isa/*.yaml`（初始全量向量）、`tools/testcases/validate_vectors.py`、`Makefile`（`check` 集成）
- 约束：
  - 期望值**手工派生自合约/spec**，不从 LLVM 输出或 QEMU 运行结果反推
  - 覆盖率主键用 opcode 身份 `insn`（v5 唯一），不用 `(mnemonic, format)`
  - 覆盖率门控限定 **M1 scope**，排除浮点/原子/系统/特权/RA 多存取等
  - deferred case 必须显式存在（不得静默缺席）
  - 完成后不自行 commit

## 背景（完整）

### 目标

在任何实现（LLVM/QEMU）字节被写入之前，生成 M1 scope 全量测试向量数据文件，并实现 schema 级 validator 作为 `make check` 门控。所有期望值（编码字节、寄存器状态、异常类型）必须从 `.tao/knowledge/contract-isa.md`（及 `spec/`）手工推导，**不得**从 LLVM 输出或 QEMU 运行结果反推。

### 设计理由

- DADAO-0628 `0002-detailed-roadmap.md` 的 **TDD Contract**：spec first、independent oracle、no bootstrapping from implementations。实现写第一行前向量必须存在。
- **Vector Taxonomy**（5 类，各针对一条规范断言）：

  | class | 规范来源 | 数量目标 |
  |-------|---------|---------|
  | encoding | 附录 A mask/value + format 字段 | 每 M1 opcode ≥1 |
  | legality | 合法性条款（rd0/rb0/对齐/immu6 等） | 每个 ILLI 触发 ≥1 |
  | semantic | 各指令语义 | 每 opcode ≥1 正常情况 |
  | boundary | signed-min / signed-max / zero / carry / overflow | 每个算术/移位 opcode ≥1 |
  | overlap | src=dst、双目的、多寄存器范围 | 每个 overlap-legal opcode ≥1 |

- **Ordering Rule**：编码表（SPEC-003t）先完成，向量生成才有参考；SPEC-003t 的 `validate_encoding.py` **不**校验向量 YAML，那是本任务的 `validate_vectors.py`。C-27（条件赋值快照）overlap 向量显式 deferred，但必须在 inventory 中出现，不得静默缺席。
- 向量数据与 validator 是后续 LLVM lit / QEMU harness / 集成测试的公共输入。

### 关键概念 / 数据

**向量 schema 字段**（`tests/vectors/schema.md` 须冻结）：

```yaml
- mnemonic: ld.ub          # 必填：0.5.3 助记符（对应 opcodes.yaml 的 mnemonic）
  insn: ld.ub-rd           # 必填：opcode 身份（对应 opcodes.yaml 的 insn，唯一）
  format: rrii             # 必填：格式
  class: semantic          # 必填：encoding/legality/semantic/boundary/overlap
  encoding:
    word: "0x10040000"     # 必填：完整 32-bit 指令字（hex）
  input_state:             # 必填：执行前寄存器/内存状态（仅列相关字段）
    rd:
      rd1: "0x0000000000000001"
  expected_state:          # 条件必填（见 class 定义）
    rd:
      rd1: "0x0000000000000002"
  expected_fault: null     # null / ILLI / UNDI / MALIGN / IALIGN / RASOF / RASUF
  status: active           # active / deferred
  deferred_reason: null    # status=deferred 时必填（如 "C-27"）
  spec_cite: "SimRISC-01 §存取RD寄存器"  # 必填：语义来源
  notes: ""                # 可选
```

**class 定义**（`expected_state` / `expected_fault`）：

| class | expected_state | expected_fault | 用途 |
|-------|---------------|----------------|------|
| encoding | null | null | word 与 opcodes.yaml mask/value 一致，可解码执行无 fault |
| legality | null | 通常 ILLI | 非法操作数/立即数 |
| semantic | 必填 | null | 正常执行后寄存器/内存状态正确 |
| boundary | 必填 | null 或 ILLI | 边界值 |
| overlap | 必填或 null | null 或 ILLI | src=dst 等重叠 |

**status=deferred 规则**：`expected_state` 必须为 `null`，`deferred_reason` 必填；C-27 的 overlap case 必须出现在 inventory 中。

**覆盖率要求**：M1 scope 内每条指令身份（`insn`）至少各 1 条对应 class 的 case；算术类还需 boundary；条件赋值 overlap 类按 C-27 deferred。

**向量文件组织**（建议，按 0.5.3 指令族分组，可按需拆分）：

```
tests/vectors/isa/
  rd-arith.yaml         # add/sub/mul/div/rem 全位宽（.ub/.uw/.ut/.uo/.sb/...）
  rd-logic.yaml         # and/or/xor/xnor
  rd-shift-extend.yaml  # shl/shr/ext 全位宽
  rd-compare.yaml       # cmp.*
  rd-cond-assign.yaml   # cs.n/cs.z/cs.p/cs.eq/cs.ne
  rd-imm-block.yaml     # set.ow/set.zw/or.w/andn.w + rd2rd/rd2rb/rb2rd/rb2rb
  rd-load-store.yaml    # ld.*/st.*/ldm.*/stm.*
  rb-ops.yaml           # RB 算术/比较/立即数/块赋值
  control-flow.yaml     # br.*/jump/call/ret
  misc.yaml             # swym/illi/fence
```

**inventory.md 格式**：以 opcode 身份 `insn` 为行的覆盖矩阵，列 = `encoding/legality/semantic/boundary/overlap`，deferred 填写 reason（如 `C-27`），缺失必须显式记录（不得静默缺席）。

**`tools/testcases/validate_vectors.py` 校验内容**（须含但不少于）：

1. 必填字段存在（`mnemonic/insn/format/class/encoding/input_state/spec_cite`）
2. `class` ∈ {encoding, legality, semantic, boundary, overlap}
3. `status` ∈ {active, deferred}
4. deferred 一致性（`expected_state=null` 且 `deferred_reason` 非空）
5. `expected_fault` ∈ {null, ILLI, UNDI, MALIGN, IALIGN, RASOF, RASUF}
6. `encoding.word` 合法 hex 且 ≤ 0xFFFFFFFF
7. `insn` 存在于 `contracts/opcodes.yaml`
8. `encoding.word` 与对应 opcode 的 `(word & mask) == value` 一致
9. **覆盖率门控**：M1 scope 内每个 `insn` 至少 1 条 active 向量，缺失报 `COVERAGE MISSING`
10. active semantic/boundary 必须有 `expected_state`

退出码：有错误 exit(1) 并列出文件 + case 序号；无错误 exit(0)。`Makefile` 的 `check` target 追加 `validate-vectors`（依赖 `contracts/opcodes.yaml` 存在）。

### 上游引用

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-001d-vector-data.md`（完整转述：目标、schema 字段规范、5 类 class 与 deferred 规则、每条指令覆盖要求、`isa/` 文件组织、inventory 格式、validator 8 项校验、约束、以及三轮 Architecture Review 的 P0/P1 问题与修正）
- DADAO-0628：`.work/DADAO-0628/tests/vectors/schema.md`、`inventory.md`、`README.md`、`tests/vectors/isa/`（产物形态参考，禁止复制数据正文）
- DADAO-0628：`.work/DADAO-0628/scripts/validate_vectors.py`（validator 实现参考，禁止复制）
- DADAO-0628：`.work/DADAO-0628/code-agent/designs/0002-detailed-roadmap.md`（TDD Contract / Vector Taxonomy / Ordering Rule 段）

## 交付物

| 文件 | 说明 |
|------|------|
| `tests/vectors/schema.md` | 向量 YAML 字段规范（字段名、类型、约束、必填性、5 类 class、deferred 规则） |
| `tests/vectors/inventory.md` | 以 `insn` 为行的 M1 覆盖矩阵（含 deferred reason） |
| `tests/vectors/README.md` | 声明向量独立派生自 spec，不从 LLVM/QEMU 生成 |
| `tests/vectors/isa/*.yaml` | M1 scope 初始全量向量（5 类），每条期望值附手算依据 |
| `tools/testcases/validate_vectors.py` | 向量 schema + 覆盖率校验器，`make check` 门控 |
| `Makefile` | `check` target 追加 `validate-vectors` |

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **助记符**：0.4.1 的 `add`/`muls`/`mulu`/`divs`/`divu`/`cmps`/`cmpu`/`exts`/`extz`/`shrs`/`shru`/`shlu`/`ldo`/`sto`/`setzw`/`setow`/`orw`/`andnw`/`brn`/`brnn`/`brz`/`brnz`/`brp`/`brnp`/`breq`/`brne`/`jump`/`call`/`ret`/`unimp` 等，全部替换为 0.5.3 命名（`.b/.w/.t/.o` + `s/u`；`ld.ub`/`st.o`/`set.zw`/`br.nz`/`illi` 等）。
2. **覆盖率身份**：0628 用 `(op, ha)`；v5 `opcodes.yaml` 有唯一 `insn` 字段（如 `ld.o-rd`/`ld.o-rb`/`or.w-rd`/`or.w-rb`），覆盖率主键用 `insn` 更精确，schema 必须含 `insn` 字段。
3. **编码表路径**：0628 `tools/opcodes.yaml`；v5 `contracts/opcodes.yaml`（SPEC-003t）。
4. **validator 路径**：0628 `scripts/validate_vectors.py`；v5 `tools/testcases/validate_vectors.py`（与 `tools/spec/validate_encoding.py` 同目录）。
5. **格式体系**：0.5.3 引入 MISC-byte/wyde/tetra/octa 子表（`orrr`/`orri`），向量文件组织与 opcode 分组需按 0.5.3 QFC 表重建。
6. **M1 scope 门控**：v5 `opcodes.yaml` 含 256 条（含浮点 RF、原子 AMO、系统/特权等），覆盖率门控必须显式限定 M1 scope（排除 RF/AMO/系统/特权/RA 多存取/rd2ra/ra2rd 等），否则会要求为 excluded 指令造向量。
7. **RB 语义**：0.5.3 RB 算术为全 64 位（无 48-bit 截断/高 16 位保持规则），0.4.1 中相关期望值规则与结论**不适用**。
8. **deferred reason**：C-27 仍适用（条件赋值快照）；其余 deferred 由 v5 实际合法性/异常条件决定，需从 `contract-isa.md`/`legality_rules.yaml` 派生。

## 已知坑 / 结论

摘自 DADAO-0628 DL-001d 三轮 Architecture Review：

1. **P0 数据错误**：`rela` 期望值漏加 offset（应 `base + sext18<<12`）；`addi-rb boundary` 违反 RB 高位保持规则。→ 教训：每条期望值必须按语义逐条手算并附推导；v5 中 RB 规则不同，更须以 0.5.3 为准。
2. **P0 覆盖率缺口**：首轮 36 条指令零覆盖（41% 缺失），validator 未内建覆盖率检查。→ v5 必须从第一版就内建覆盖率门控。
3. **`(mnemonic, format)` 键碰撞**：7 对 RD/RB 变体共享键，导致假全覆盖。→ v5 用唯一 `insn` 作主键，从根上避免。
4. **inventory 过报 / 未更新**：inventory 行数与实际数据不一致。→ inventory 必须由 opcodes.yaml 驱动、与数据同步。
5. **PyYAML 依赖**：无 JSON fallback；非阻断但应统一。
6. **notes 歧义**：立即数 `+256` 应写明是指令数还是字节数（`imm=256 (1024 bytes)`）。
7. **不自行 commit**：完成后等待审查。
8. **spec 歧义不猜测**：无法手推期望值时在完成区标 `[OPEN]`，不猜。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-001d-vector-data.md`（完整转述）
- DADAO-0628：`.work/DADAO-0628/tests/vectors/schema.md`
- DADAO-0628：`.work/DADAO-0628/tests/vectors/inventory.md`
- DADAO-0628：`.work/DADAO-0628/tests/vectors/README.md`
- DADAO-0628：`.work/DADAO-0628/tests/vectors/isa/`
- DADAO-0628：`.work/DADAO-0628/scripts/validate_vectors.py`
- DADAO-0628：`.work/DADAO-0628/code-agent/designs/0002-detailed-roadmap.md`（TDD Contract / Vector Taxonomy 段）
- 本项目：`contracts/opcodes.yaml`、`contracts/legality_rules.yaml`、`.tao/knowledge/contract-isa.md`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `tests/vectors/schema.md` 冻结全部字段与 5 类 class 定义、deferred 规则、覆盖要求
2. `tests/vectors/inventory.md` 以 `insn` 为行、覆盖矩阵完整（含 deferred reason），无静默缺席
3. `tests/vectors/isa/*.yaml` 存在，M1 scope 每个 `insn` ≥1 active 向量
4. `tools/testcases/validate_vectors.py` 实现上述 10 项校验，错误时 exit(1) 并列出文件+case 序号
5. `python3 tools/testcases/validate_vectors.py` 零错误，输出 `N/N opcodes covered OK`
6. `make check` 包含并执行 `validate-vectors`，PASS
7. 所有期望值可回溯到 `contract-isa.md`/`spec/`（case 内附推导依据），无 LLVM/QEMU 生成痕迹
8. C-27 类 overlap case 显式存在且 `status: deferred`
9. 未自行 commit

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
