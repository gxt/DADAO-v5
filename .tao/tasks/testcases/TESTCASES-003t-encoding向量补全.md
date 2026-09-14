# TESTCASES-003t: encoding class 向量补全

**模块**：testcases
**项目里程碑**：M1
**依赖**：`TESTCASES-002t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `verif/opcodes.yaml`（SPEC-003t：op/ha/mask/value 主键来源）
  - `.tao/knowledge/contract-isa.md`（§2 指令编码、§2.5 操作数顺序、§4.1/§4.2 存取合法性）
  - `tests/vectors/schema.md`（TESTCASES-002t，字段规范）
  - `tests/vectors/isa/*.yaml`（TESTCASES-002t 初始向量）
- 输出：向各 `tests/vectors/isa/*.yaml` **追加** `class: encoding` 向量，使每个 M1 scope opcode 身份至少 1 条 encoding 向量
- 约束：
  - 只追加，不删改现有向量
  - `input_state: {}`、`expected_state: null`、`expected_fault: null`
  - `encoding.word` 由 `verif/opcodes.yaml` 的 op/ha + 字段最小合法值手算（公式 `(op<<24)|(ha<<18)|(hb<<12)|(hc<<6)|hd`）
  - 目标 rd0/rb0 会触发 ILLI 的指令必须填非 0 目标；源 rd0/rb0 合法用 0
  - multi load/store 的 `immu6` 必须 ≥1（=0 → ILLI）
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

- `op`、`ha` 从 `verif/opcodes.yaml` 对应记录读取
- 操作数字段（hb/hc/hd）填最小合法值：
  - **目标寄存器**（dest rd/rb）：若 rd0/rb0 为目标会触发 ILLI，用 1；否则用 0
  - **源寄存器**：用 0（rd0/rb0 作为源合法）
  - **立即数**：用 0
  - **wyde-position**（rwii）：用 0（wp0）
  - **count 字段**（rrri，multi load/store）：用 1（count=0 语义未定义/ILLI）

**目标 rd0/rb0 → ILLI 的指令**（按 `contract-isa.md` §4.1/§4.2 与 `verif/legality_rules.yaml`；v5 助记符）：

| 规则 | 受影响指令 |
|------|----------|
| rd0 作目的 → ILLI | 算术/移位/扩展/比较/条件赋值等写 rd 的指令（`add.*`/`sub.*`/`mul.*`/`div.*`/`shl.*`/`shr.*`/`ext.*`/`cmp.*`/`cs.*` 等） |
| rb0 作目的 → ILLI | 写 rb 的指令（`add.si-rb`/`add.so-rb`/`sub.so-rb`/`rela.si-rb`/`or.w-rb`/`andn.w-rb`/`set.zw-rb`/`rd2rb`/`rb2rb` 等） |
| rd0 作目的合法 | 分支（目标为 PC）、`jump`/`call`/`ret`、store 类（`st.*`/`stm.*`）、`rd2rd`、`cmp.*-rb` |
| multi load/store | `immu6`（count）必须 ≥1 |

**特殊处理**：

- **store 类**（`st.*`/`stm.*`）：encoding 向量写出到地址 0；测试机 flat-map 覆盖整个地址空间时合法；`expected_fault: null`
- **multi load/store**：count 字段填 1（仅搬一次），避免越界；地址用 0
- **`jump-iiii`/`call-iiii`**：target imm 用 0（跳回地址附近，flat-map 下不 fault）
- **`ret`**：RA 栈初值 0，PC=0 在 flat-map 内合法；`input_state: {}` 即可
- **`rd2rb`/`rb2rd`/`rb2rb`**：ha/hb 用有效但不触发 ILLI 的值

### 上游引用

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-020a-encoding-vectors.md`（完整转述：背景、目标、encoding 格式、word 计算规则、rd0/rb0 ILLI 表、写入位置表、特殊处理、验收步骤，以及两轮 Architecture Review 的 P0 immu6=0 问题）

## 交付物

- 各 `tests/vectors/isa/*.yaml`：追加 encoding class 向量，覆盖 M1 scope 全部 opcode 身份
  - `rd-arith.yaml`、`rd-logic.yaml`、`rd-shift-extend.yaml`、`rd-compare.yaml`、`rd-cond-assign.yaml`、`rd-imm-block.yaml`、`rd-load-store.yaml`、`rb-ops.yaml`、`control-flow.yaml`、`misc.yaml`（文件集以 002t 实际组织为准）
- 不新建独立文件（除非某指令族在 002t 无对应文件，此时在 002t 组织内新增）

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **助记符**：`addi`→`add.si`、`ldo`→`ld.o`、`sto`→`st.o`、`setzw`→`set.zw`、`setow`→`set.ow`、`orw`→`or.w`、`andnw`→`andn.w`、`brz`→`br.z`、`brnz`→`br.nz`、`unimp`→`illi` 等；且同一助记符有 RD/RB 变体（`insn` 后缀 `-rd`/`-rb`）。
2. **写入位置表**按 0.5.3 QFC 表重建（opcode 分配完全改变），以 `verif/opcodes.yaml` 为准。
3. **immu6/count 规则**：`immu6 = 0 → ILLI` 仍成立（0628 P0.1），v5 沿用；multi load/store 必须 count≥1。
4. **rd0/rb0 dest ILLI 规则**以 0.5.3 `contract-isa.md`/`legality_rules.yaml` 为准（0.4.1 的具体指令清单不照搬）。
5. **RB 语义**：0.5.3 RB 全 64 位；RB dest 合法性按 0.5.3 判断。
6. **覆盖率身份**：v5 用 `insn`，encoding 向量必须带 `insn` 字段。

## 已知坑 / 结论

摘自 DADAO-0628 DL-020a 两轮 Architecture Review：

1. **P0：全部 rrri encoding 向量 `immu6=0`**（12/13 条），违反 spec `immu6=0 → ILLI`，会导致 harness 触发 ILLI 而非正常退出。→ 修正为 `immu6=1`（word += 1）。v5 必须从一开始就填 count≥1。
2. **word 计算**：`(op<<24)|(ha<<18)|(hb<<12)|(hc<<6)|hd`；字段最小合法值须避开 ILLI 目标。
3. **dest rd0/rb0 触发 ILLI**：encoding 向量须用非 0 目标；源 rd0/rb0 合法。
4. **store 写地址 0**：flat-map 下合法；不得据此推断真实内存映射（v5 以 ADR-0004 为准）。
5. **只追加不删改**：不得破坏已有 semantic/boundary/legality 向量。
6. **最终 200 cases、87/87 opcode 覆盖**（0628 数据，仅作规模参考，不照搬）。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-020a-encoding-vectors.md`（完整转述）
- DADAO-0628：`.work/DADAO-0628/tests/vectors/isa/`（encoding 向量形态参考，禁止复制数据）
- 本项目：`verif/opcodes.yaml`、`.tao/knowledge/contract-isa.md`、`verif/legality_rules.yaml`、`tests/vectors/schema.md`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. M1 scope 内每个 `insn` 至少 1 条 `class: encoding` 向量
2. 每条 encoding 向量 `input_state: {}`、`expected_state: null`、`expected_fault: null`、`status: active`
3. 每条 `encoding.word` 与 `verif/opcodes.yaml` 的 `(word & mask) == value` 一致
4. 目标 rd0/rb0 会触发 ILLI 的指令均用非 0 目标；multi load/store 的 count ≥1
5. 未删改已有向量
6. `python3 verif/validate_vectors.py` 零错误，覆盖数提升
7. `make check` PASS
8. 未自行 commit

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
