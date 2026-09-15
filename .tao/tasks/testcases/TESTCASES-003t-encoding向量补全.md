# TESTCASES-003t: encoding class 向量补全

**模块**：testcases
**项目里程碑**：M1
**依赖**：`TESTCASES-002t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `contracts/opcodes.yaml`（SPEC-003t：`op`/`mask`/`value`/`fields` 主键来源；**无独立 `ha` 字段**，`ha = (value >> 18) & 0x3f`）
  - `.tao/knowledge/contract-isa.md`（§2 指令编码、§2.5 操作数顺序、§4.1/§4.2/§4.9 存取合法性、§5 控制流、§9.1 ILLI 场景）
  - `contracts/legality_rules.yaml`（SPEC-008t：`rd_dest_rd0`/`store_src_rd0`/`rb_dest_rb0`/`rb_base_rb0_store`/`multi_immu6_zero` 等）
  - `.tao/knowledge/adr-0004-test-machine.md`（SPEC-006t：内存映射、unmapped → `0x87`）
  - `tests/vectors/schema.md`（TESTCASES-002t，字段规范）
  - `tests/vectors/isa/*.yaml`（TESTCASES-002t 初始向量）
- 输出：向各 `tests/vectors/isa/*.yaml` **追加** `class: encoding` 向量，使每个 M1 scope 指令身份 `(insn, format)` 至少 1 条 encoding 向量
- 约束：
  - 只追加，不删改现有向量
  - `input_state: {}`、`expected_state: null`、`expected_fault: null`
  - `encoding.word` 由 `contracts/opcodes.yaml` 的 `op`/`ha` + 字段最小合法值手算（公式 `(op<<24)|(ha<<18)|(hb<<12)|(hc<<6)|hd`，其中 `op = value>>24`、`ha = (value>>18) & 0x3f`）
  - **写 RD 为目的的指令，目的必须为非 0**（`rd0` 为目的 → ILLI）；**写 RB 为目的的指令，目的必须为非 0**（`rb0` 为目的 → ILLI）；源 `rd0`/`rb0` 合法用 0
  - multi load/store 的 `immu6` 必须 ≥1（=0 → ILLI）
  - **地址必须落在 ADR-0004 的 RAM/ROM 合法区**，不得用 addr=0（unmapped → `0x87`）
  - 完成后不自行 commit

## 背景（完整）

### 目标

为每个 `(op, ha)` / `insn` 至少补充 **1 条 `class: encoding` 向量**，使所有 M1 指令都有至少 1 条 encoding 向量落在对应 YAML 文件中。encoding class 的语义：验证该 32-bit instruction word 能被解码并无异常执行（无 ILLI/MALIGN/UNDI），不检查执行后寄存器状态。

### 设计理由

- 后续 QEMU/集成 harness 读取所有 `class: encoding` 向量，打包成 flat binary 喂给被测实现，以无 fault 断言指令可解码。
- 0628 现状：`class: encoding` 向量极少（仅 misc 2 条），其余 9 个文件为 0，harness 几乎空转。v5 从基座起就应补齐 encoding 层。

### 关键概念 / 数据

**encoding 向量格式**：

```yaml
- mnemonic: <mnemonic>
  insn: <insn>
  format: <format>
  class: encoding
  encoding:
    word: "0x????????"
  input_state: {}
  expected_state: null
  expected_fault: null
  status: active
  spec_cite: "SimRISC-00 §指令域说明"
  notes: "<可选>"
```

**`encoding.word` 计算规则**（来源：`contract-isa.md` §2.1/§2.2）：

```
word = (op << 24) | (ha << 18) | (hb << 12) | (hc << 6) | hd
```

- `op`、`ha` 从 `contracts/opcodes.yaml` 对应记录**推导**（`op = value>>24`、`ha = (value>>18)&0x3f`；该文件无独立 `ha` 字段）
- 操作数字段（hb/hc/hd）填最小合法值：
  - **写 RD 为目的**（`rdha`/`rdhb` 为 dst）：用 1（`rd0` 为目的 → ILLI）
  - **写 RB 为目的**（`rbha`/`rbhb` 为 dst）：用 1（`rb0` 为目的 → ILLI）
  - **源寄存器**：用 0（`rd0`/`rb0` 作为源合法）
  - **立即数**：用 0（但相对控制流的立即数见下方「特殊处理」）
  - **wyde-position**（rwii）：用 0（wp0）
  - **count 字段**（rrri，multi load/store）：用 1（count=0 → ILLI）

**rd0/rb0 合法性判据**（按 `contract-isa.md` §1.3/§9.1 与 `legality_rules.yaml`；v5 助记符）：

| 规则 | 受影响指令 |
|------|----------|
| **写 RD 目的 → 必须非 0** | 所有写 RD 的指令：`add.*`/`sub.*`/`mul.*`/`div.*`/`rem.*`/`shl.*`/`shr.*`/`ext.*`/`cmp.*`/`cs.*`/`ld.*`/`ldm.*`/`rd2rd`/`rb2rd`/`ra2rd`/`set.zw-rd`/`set.ow-rd`/`or.w-rd`/`andn.w-rd` |
| **写 RB 目的 → 必须非 0** | 写 RB 的指令：`add.si-rb`/`add.so-rb`/`sub.so-rb`/`rela.si-rb`/`set.zw-rb`/`or.w-rb`/`andn.w-rb`/`rd2rb`/`rb2rb`/`ld.o-rb`/`ldm.o-rb` |
| **store 的 `rdha` 是源但 `rd0` → ILLI** | `st.b-rd`/`st.w-rd`/`st.t-rd`/`st.o-rd`/`stm.b-rd`/`stm.w-rd`/`stm.t-rd`/`stm.o-rd`（`store_src_rd0`），`rdha` 用 1 |
| **store 的 `rbha` 为 `rb0` → ILLI** | `st.o-rb`/`stm.o-rb`（`rb_base_rb0_store`），`rbha` 用 1 |
| **`rd0` 作目的合法（例外）** | 仅 rrrr 双目的 `add.uo`/`add.so`/`sub.uo`/`sub.so`/`mul.uo`/`mul.so`（`rdha`/`rdhb` 中**一个**可为 rd0），以及 `ret rd0, 0` |
| **无 RD 目的的指令** | 分支 `br.*`、`jump`、`call`、`swym`、`illi`、`fence`、`st.o-ra`/`stm.o-ra`（目的为 RA 组，无 rd0 约定）；其 rd 操作数为源，可用 0 |
| multi load/store / 块赋值 | `immu6`（count）必须 ≥1 |

> 注意：`rd2rd`/`rb2rd`/`ra2rd` 的目的 `rdhb` 为 `rd0` **同样触发 ILLI**；`cmp.*-rb` 的 `rdhb` 为 `rd0` 亦然。二者不属「合法例外」。

**特殊处理**（依据 ADR-0004 D5.6/D6.5，不沿用 0628 的 flat-map 假设）：

- **相对控制流立即数**（`br.*`、`jump-iiii`、`call-iiii`）：地址公式 `Addr = rb0 + (imm << 2)`（`imm` 为**字**偏移，`<<2` 转字节）。ADR-0004 D6.5 冻结 **`rb0` = 当前指令地址**，故：
  - `imm=0` → `Addr = rb0` → 跳到**自身** → 自跳死循环（harness 超时 = inconclusive）；
  - `imm=1` → `Addr = rb0 + 4` → **下一条指令** → fall-through（等效 NOP）✅；
  - `imm=-1` → `Addr = rb0 - 4` → 上一条 → 同样死循环。

  故 encoding 向量必须用 **`imm=1`**；`call-iiii` 同时压入返回地址后落到下一条。（0628 的 `rb0`=下一条、`imm=0` 等效 NOP **不适用**。）
- **store 类**（`st.*`/`stm.*`）：`rdha` 为源，**必须非 0**（`store_src_rd0`）；写出地址必须落在 ADR-0004 RAM 区（如 `rb1 = 0xffff_0000_0000`），**不得用 addr=0**（unmapped → `0x87`）。
- **load 类**（`ld.*`/`ldm.*`）：目的必须非 0；基址指向 RAM 合法地址（见 009t）。
- **multi load/store**：`immu6 = 1`（=0 → ILLI）；地址同上。
- **`jump-rrii`/`call-rrii`（encoding，null fault）**：用 `ha = rb0`（PC 可作基址，`contract-isa.md` §5.3）、`hb = rd0`、`imms12 = 1` → 目标 = `rb0 + 4` = 下一条 → fall-through，`expected_fault: null`。**不要**用 `rb0/rd0/0`（addr=0 → unmapped `0x87`）；addr=0 的 fault 期望属 008t 的 legality 向量。
- **`ret-riii`**：冷 RA（ADR-0004 D2.1 `ra0`–`ra63=0`）→ **RASUF**（`0x8B`），无法构造 null-fault 的单指令 encoding 向量；改以 `class: legality` + `expected_fault: RASUF` 覆盖（见 008t），并在 inventory 显式标注该例外。
- **`rd2rb`/`rb2rd`/`rb2rb`**：目的 `rbhb` 必须非 0（`rb0` 为目的 → ILLI），`immu6 ≥ 1`。
- **`st.o-ra`/`stm.o-ra`/`ld.o-ra`/`ldm.o-ra`**：RA 组无 rd0/rb0 约定（`raha` 可为 `ra0`），但多存取 `immu6 ≥ 1`、地址须 8B 对齐且在 RAM。

### 上游引用

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-020a-encoding-vectors.md`（完整转述：背景、目标、encoding 格式、word 计算规则、rd0/rb0 ILLI 表、写入位置表、特殊处理、验收步骤，以及两轮 Architecture Review 的 P0 immu6=0 问题）

## 交付物

- 各 `tests/vectors/isa/*.yaml`：追加 encoding class 向量，覆盖 M1 scope 全部指令身份 `(insn, format)`
  - `rd-arith.yaml`、`rd-logic.yaml`、`rd-shift-extend.yaml`、`rd-compare.yaml`、`rd-cond-assign.yaml`、`rd-imm-block.yaml`、`rd-load-store.yaml`、`rb-ops.yaml`、`control-flow.yaml`、`misc.yaml`（文件集以 002t 实际组织为准）
- 不新建独立文件（除非某指令族在 002t 无对应文件，此时在 002t 组织内新增）

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **助记符**：`addi`→`add.si`、`ldo`→`ld.o`、`sto`→`st.o`、`setzw`→`set.zw`、`setow`→`set.ow`、`orw`→`or.w`、`andnw`→`andn.w`、`brz`→`br.z`、`brnz`→`br.nz`、`unimp`→`illi` 等；且同一助记符有 RD/RB 变体（`insn` 后缀 `-rd`/`-rb`）。
2. **写入位置表**按 0.5.3 QFC 表重建（opcode 分配完全改变），以 `contracts/opcodes.yaml` 为准。
3. **immu6/count 规则**：`immu6 = 0 → ILLI` 仍成立（0628 P0.1），v5 沿用；multi load/store 必须 count≥1。
4. **rd0/rb0 dest ILLI 规则**以 0.5.3 `contract-isa.md`/`legality_rules.yaml` 为准（0.4.1 的具体指令清单不照搬）；注意 store 的 `rdha` 是源但 `rd0` 同样 ILLI。
5. **RB 语义**：0.5.3 RB 全 64 位；RB dest 合法性按 0.5.3 判断。
6. **覆盖率身份**：v5 用 `(insn, format)`（`insn` 非唯一），encoding 向量必须带 `insn` + `format` 字段。
7. **相对控制流立即数**：ADR-0004 D6.5 冻结 `rb0` = 当前指令地址，故 0628 的「imm=0 → 等效 NOP」**不适用**；`imm=0` 会自跳死循环，v5 用 `imm=1` 落到下一条。
8. **测试机地址/故障**：以 ADR-0004 为准（RAM `0xffff_0000_0000`、unmapped `0x87`）；0628 的「addr=0 合法」「addr=0 → ILLI」**不适用**。

## 已知坑 / 结论

摘自 DADAO-0628 DL-020a 两轮 Architecture Review：

1. **P0：全部 rrri encoding 向量 `immu6=0`**（12/13 条），违反 spec `immu6=0 → ILLI`，会导致 harness 触发 ILLI 而非正常退出。→ 修正为 `immu6=1`（word += 1）。v5 必须从一开始就填 count≥1。
2. **word 计算**：`(op<<24)|(ha<<18)|(hb<<12)|(hc<<6)|hd`；字段最小合法值须避开 ILLI 目标。
3. **dest rd0/rb0 触发 ILLI**：encoding 向量须用非 0 目标；源 rd0/rb0 合法。
4. **store 写地址 0**：0628 在 flat-map 下合法；v5 **不适用**——addr=0 是 unmapped（`0x87`），store 基址必须指向 ADR-0004 RAM 区。
5. **只追加不删改**：不得破坏已有 semantic/boundary/legality 向量。
6. **最终 200 cases、87/87 opcode 覆盖**（0628 数据，仅作规模参考，不照搬）。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-020a-encoding-vectors.md`（完整转述）
- DADAO-0628：`.work/DADAO-0628/tests/vectors/isa/`（encoding 向量形态参考，禁止复制数据）
- 本项目：`contracts/opcodes.yaml`、`.tao/knowledge/contract-isa.md`、`contracts/legality_rules.yaml`、`tests/vectors/schema.md`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. M1 scope（`excluded_m1 != true`）内每个 `(insn, format)` 至少 1 条 active encoding 向量
   - **例外**：`ret-riii` 无法构造 null-fault 单指令 encoding 向量（冷 RA → RASUF），改以 `class: legality` + `expected_fault: RASUF` 覆盖，须在 inventory 显式标注
2. 每条 encoding 向量 `input_state: {}`（`jump-rrii`/`call-rrii` 例外，无需预置）、`expected_state: null`、`expected_fault: null`、`status: active`
3. 每条 `encoding.word` 与 `contracts/opcodes.yaml` 的 `(word & mask) == value` 一致
4. 写 RD/RB 为目的的指令均用非 0 目的；store 的 `rdha` 非 0；multi load/store 的 count ≥1
5. 相对控制流立即数用 1（避免自跳）；`jump-rrii`/`call-rrii` 用 `rb0` 基址；访存地址落在 ADR-0004 RAM/ROM 区，无 addr=0
6. 未删改已有向量
7. `python3 tools/testcases/validate_vectors.py` 零错误，覆盖数提升
8. `make check` PASS
9. 未自行 commit

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
