# TESTCASES-004t: load/store 向量（RD/RB/RA 三 bank）

**模块**：testcases
**项目里程碑**：M1
**依赖**：`TESTCASES-003t`
**状态**：已验证

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `tests/vectors/schema.md`（`TESTCASES-002t` 返工后：含 `expected_pc`、encoding 豁免）
  - `contracts/opcodes.yaml`（访存指令编码字段 `fields`；`op=value>>24`、`ha=(value>>18)&0x3f`）
  - `contracts/legality_rules.yaml`（`rd_dest_rd0`/`store_src_rd0`/`rb_dest_rb0`/`rb_base_rb0_store`/`multi_immu6_zero`）
  - `.tao/knowledge/contract-isa.md` §4.1/§4.2/§4.9（load/store 合法性、对齐、RA 存取）、§2.2（格式）
  - `.tao/knowledge/adr-0004-test-machine.md`（D1 内存映射、D5.6 访问矩阵、D6.5 入口状态）
- **输入说明**：`reg-*` 6 个文件（130 身份）已由 `TESTCASES-003t` 生成并验证；本任务的 `mem-*` 向量数据**从零生成**（依据 `schema.md` + `contracts/opcodes.yaml` + `contract-isa.md`/ADR-0004），**不是**重组/修复既有文件。
- 输出（**本任务拥有的文件**，`tests/vectors/isa/`）：
  - `mem-rd.yaml`、`mem-rb.yaml`、`mem-ra.yaml`
- 约束：
  - 期望值**手工派生自 `contract-isa.md`/`spec/`/ADR-0004**，不得从 LLVM/QEMU 反推
  - 覆盖率主键 `(insn, format)`；M1 scope 以 `excluded_m1 != true` 为准
  - **只生成/修改本任务拥有的 3 个目标文件**；**不改** `contracts/`；**不改** `reg-*`/`ctrl-*`/`misc`
  - 参考仓库（`.work/DADAO-0628/`）的向量数据**仅内容溯源，不得作为执行依赖**（禁止复制数据正文）
  - 完成后不自行 commit

## 任务范围

### 1. 目标文件集（从零生成）

> **数据来源说明**：`reg-*` 已由 `003t` 生成；本任务按 `schema.md` 从零生成下列 `mem-*` 文件；不再有「旧文件 → 新文件」的重组动作。

| 目标文件 | 覆盖身份 |
|---|---|
| `mem-rd.yaml` | `ld.*`/`st.*`/`ldm.*`/`stm.*` 的 **RD 变体**（22 个） |
| `mem-rb.yaml` | `ld.o-rb`/`st.o-rb`/`ldm.o-rb`/`stm.o-rb`（4 个） |
| `mem-ra.yaml` | `ld.o-ra`/`st.o-ra`/`ldm.o-ra`/`stm.o-ra`（4 个） |

- 三个文件按 bank 分组（RD/RB/RA）承载访存子集；`ld.o-rb`/`st.o-rb`/`ldm.o-rb`/`stm.o-rb` 与 `ld.o-ra`/`st.o-ra`/`ldm.o-ra`/`stm.o-ra` **不**在 `reg-*`（`003t`）中重复。
- 本任务只生成上表 3 个文件；`reg-*`（`003t`）与 `ctrl-*`/`misc`（`005t`~`007t`）不在本任务。

### 2. F10：访存 encoding 向量的内存语义重设计（本任务核心）

- **背景（上一版丢弃数据的教训，本任务生成时须避免）**：上一版访存 encoding 向量存在两类缺陷（以 `ld.ub-rd` word=`0x10000000` 为例）：
  1. **操作数字段全 0**：`rdha`（目的）= `rd0` → **ILLI**（`rd_dest_rd0`）；`st.*` 的 `rdha`（源）= `rd0` → **ILLI**（`store_src_rd0`）；`rbha` base = `rb0` → **ILLI**（`rb_base_rb0_store`）；multi load/store `immu6` = 0 → **ILLI**。
  2. **`input_state: {}`**：即使 base 字段非 `rb0`，未预置基址寄存器 → 地址 0 → **unmapped（`0x87`）**；而 `expected_fault: null`，自相矛盾。
- **方案 B（采用）：使用有效 RAM 基址**：
  - `input_state` 预置 `rb3 = 0x0000ffff00000000`（`rb3` **不在** ADR-0004 D6.5 的 `_start` 入口状态中，属**未使用**寄存器，可自由预置为 RAM 基址，48-bit）；
  - 编码中 base 字段 = `rb3`（非 `rb0`），dest = `rd1`（非 `rd0`），store 源 = `rd1`（非 `rd0`）；
  - `expected_state: null`、`expected_fault: null`、`status: active`；加载合法 RAM 地址；
  - multi load/store 的 `immu6`（count）≥ 1（=0 → ILLI）。
- **方案 A（备选，仅登记，不采用）**：dest `rdha=rd0` → `expected_fault: ILLI`；只验证「非法目的被拒」，未验证合法路径，故不采用。
- **字段模式**（结构参考，具体 `encoding.word` 由 `contracts/opcodes.yaml` 的 `op`/`ha` 与 §2.2 公式手算）：
  - 单 load：`ha(dest)=rd1`、`hb(base)=rb3`、`imms12=0`；
  - 多 load/store：在单 load 模式上令 `immu6=1`（count=1）；
  - 所有访存 encoding 的 `input_state` 预置 `rb3 = 0x0000ffff00000000`。
- **约束**：
  - 基址必须指向 RAM 合法地址，**不得**用 addr=0 / 未映射地址；
  - **base 用未使用的 `rb`（本任务取 `rb3`）**：`rb1`（SP=`0xffff_00ff_0000`）与 `rb2`（RAM 基址=`0xffff_0000_0000`）已被 ADR-0004 D6.5 的 `_start` 入口状态占用，**不得**用作 base；`rb3` 未被占用，在 `input_state` 中预置为 RAM 基址即可；
  - RA 存取（`ld.o-ra`/`st.o-ra`/`ldm.o-ra`/`stm.o-ra`）：目的为 RA 组，按 §4.9 与 `contract-isa.md` 的 RA 存取规则填字段；不得用 `ra0`/非法 count；
  - 每条 encoding case `expected_state: null`、`expected_pc: null`、`expected_fault: null`、`status: active`。
- **F10 范围**：本任务只修**访存** encoding；`reg-*`/`ctrl-*`/`misc` 的 encoding 由对应任务负责。

### 3. 语义/边界/合法性向量

- 保留并复核 `mem-*` 的 semantic/boundary/legality case：地址落在 ADR-0004 RAM 区、无 `rd0`/`rb0` 条目、对齐 fault（MALIGN/IALIGN）与 unmapped（`0x87`）期望正确。
- 期望值仍须手工派生；不采用 0628 的 `0x8000_0000`/`0x0010_0000` 地址图。

## 验收标准

1. `mem-rd.yaml`/`mem-rb.yaml`/`mem-ra.yaml` 存在，覆盖全部访存 M1 身份（含 RA 存取 `ld.o-ra`/`st.o-ra`/`ldm.o-ra`/`stm.o-ra`）
2. 3 个目标文件从零生成，覆盖全部访存 M1 身份；无身份遗漏、无与 `reg-*` 重复
3. 全部访存 encoding 向量 `status: active`、`expected_fault: null`、`expected_pc: null`
4. 每条访存 encoding 的 `input_state` 含 RAM 合法基址（`rb3 = 0x0000ffff00000000`），dest 非 `rd0`、base 非 `rb0`、store 源非 `rd0`
5. multi load/store 的 `immu6 ≥ 1`
6. 每条 `encoding.word` 与 `contracts/opcodes.yaml` 的 `(word & mask) == value` 一致
7. **每条访存 encoding case 经语义推演确认「可解码执行且不触发任何 fault」**（不 ILLI/unmapped）；给出字段值 + 依据章节
8. semantic/boundary 地址落在 ADR-0004 RAM 区；`input_state` 无 `rd0`/`rb0` 条目
9. 未改 `contracts/`；未动 `reg-*`/`ctrl-*`/`misc`
10. `python3 tools/testcases/validate_vectors.py` 零错误；`make check` PASS
11. （**下游、非本任务验收判据**）QEMU harness 就绪后，该文件全部 active 测试 PASS、0 timeout——本任务不以此判据验收
12. 未自行 commit

## 背景（完整）

### 目标

按 RD/RB/RA 三 bank 从零生成访存向量 `mem-rd`/`mem-rb`/`mem-ra`，且访存 encoding 一律设计为**合法可执行的 active 测试**（避免上一版「零地址/未预置基址的 unmapped 访问」）。

### 设计理由

- 访存是唯一跨三个 bank（RD/RB/RA）的运算族；按 bank 拆文件使 bank 语义（RD 地址、RB base、RA 目的）集中，便于逐 bank 审计。
- `encoding` 类定义为「可解码执行无 fault」，故 encoding 向量必须避开 `rd0`/`rb0`/`immu6=0` 与未映射地址。

### 关键概念 / 数据

- **编码公式**：`word = (op<<24)|(ha<<18)|(hb<<12)|(hc<<6)|hd`；`op=value>>24`、`ha=(value>>18)&0x3f`。
- **内存映射（ADR-0004 D1）**：boot ROM `0xffff_ffff_0000`（64 KiB，只读）、RAM `0xffff_0000_0000`–`0xffff_00ff_ffff`（16 MiB，读写）、Exit port `0xffff_8000_0000`；`BINARY_BASE` = RAM 起始。0628 的 `dadao-virt` 布局（`0x8000_0000` 等）**不适用**。
- **addr=0 语义**：ADR-0004 D5.6 → unmapped `0x87`（确定性）；不是 hang、不是 ILLI。
- **RA 存取**：`ld.o-ra`/`st.o-ra`/`ldm.o-ra`/`stm.o-ra` 属 M1（`contract-isa.md` §4.9）。

### 上游引用

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-034a-load-encoding-deferred.md`、`DL-022c`（内存地址 ROM→RAM）（内容溯源，非执行依赖）

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **助记符**：`ldbs`/`ldbu`/… → `ld.sb`/`ld.ub`/…（`insn` 带 `-rd`/`-rb`/`-ra` 后缀）。
2. **内存映射**：以 ADR-0004 为准（RAM `0xffff_0000_0000`）；0628 的 `RAM 0x8000_0000`/`ROM 0x0010_0000` **不得使用**。
3. **addr=0 语义**：unmapped `0x87`（确定性）；0628 的 QEMU hang **不适用**。
4. **编码字段**：以 `contract-isa.md` §2.2 与 `contracts/opcodes.yaml` 的 `fields` 为准。
5. **RB 语义**：0.5.3 有效地址低 48 位。
6. **多寄存器**：`immu6`（count）仍须 ≥1。

## 已知坑 / 结论

1. **addr=0 未映射**：ADR-0004 D5.6 → `0x87`；不是合法 encoding 期望。
2. **方案 B 正确性**：`ha=rd1` 目标非 rd0、`hb=rb3` base 非 rb0、`immu6=1` 非 0，均避开 ILLI；`rb3` 为未使用寄存器，预置为 RAM 基址后 load 合法。
3. **方案 A 前提**：`rdha=rd0 → ILLI` 由合约直接规定，不依赖实现侧检查；但仅覆盖非法路径。
4. **encoding.word 必须手算**：从合约/opcodes.yaml 推导，不从 QEMU 行为反推。
5. **不改实现**：若需实现改动，另建任务。
6. **不自行 commit**：完成后等待审查。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-034a-load-encoding-deferred.md`（内容溯源）
- 本项目：`.tao/knowledge/contract-isa.md` §4、`.tao/knowledge/adr-0004-test-machine.md`、`contracts/opcodes.yaml`、`contracts/legality_rules.yaml`
- 知识库：`.tao/knowledge/MEMORY.md`、`.tao/knowledge/deferred.md`

## 完成区

**测试结果**：通过。`validate_vectors.py` 零错误（178/178 M1 identities covered，538 cases）；`make check` PASS。
**修改文件**：
- `tests/vectors/isa/mem-rd.yaml`（重新生成，126 cases，22 identities）
- `tests/vectors/isa/mem-rb.yaml`（重新生成，24 cases，4 identities）
- `tests/vectors/isa/mem-ra.yaml`（重新生成，22 cases，4 identities；删除2条无效 RA rrii ILLI）
- `tools/testcases/generate_mem_vectors.py`（修复 rrii imms12 编码、删除 rd2 误用、删除 RA rrii 无效 ILLI）
- `tools/testcases/validate_vectors.py`（追加 F10 守卫：base≠rb0/rb1/rb2、base 预置 RAM 窗口、rrri immu6≥1、dest/src≠rd0）
- `tests/vectors/inventory.md`（boundary 列 30 条 mem 身份 `—`→`✓`）
**验收结果**：
- 30 个 M1 身份全覆盖（22 RD + 4 RB + 4 RA）
- 全部30条 encoding case：`status: active`、`expected_fault: null`、`expected_pc: null`、`expected_state: null`
- 全部 encoding case `input_state` 含 `rb3 = 0x0000ffff00000000`（F10 守卫机械校验）
- 全部 encoding case `ha != 0`、`hb ∈ {3,...}`（非 rb0/rb1/rb2）（F10 守卫机械校验）
- multi load/store `immu6 = 1`（≥ 1）（F10 守卫机械校验）
- 全部172条 case `(word & mask) == value` 与 `contracts/opcodes.yaml` 一致
- **rrii semantic EA 与 memory 地址一致**：imms12 编入 word，EA = rb3 + sign_ext(imms12)（F-1 修复）
- **rrii MALIGN EA 真的未对齐**：imms12=align-1 编入 word（F-2 修复）
- **无 base=rb0 的 RA rrii legality**：删除2条无效 case（F-3 修复）
- **F10 守卫**：validator 追加4项机械校验，注入测试全部捕获（F-4 修复）
- **inventory.md boundary 列**：30条 mem 身份标 `✓`（F-5 修复）
- **legality notes 引用 fault 依据**：MALIGN 引 `contract-isa §4.1.1, legality_rules data_malign`；UNMAPPED 引 `ADR-0004 D5.6`（F-6 修复）
- 独立全量重算：172条 case，0 mismatch（EA 派生、fault 判定逐条验证）
- 未改 `contracts/`、未动 `reg-*`/`ctrl-*`/`misc`
- 未自行 commit
**新发现/坑**：
- rrii 格式的有效地址偏移只能来自 `imms12`（hc/hd），`rd2` 对 rrii 无操作数意义——生成器误用 `rd2` 是 F-1/F-2 根因
- `rb0` = PC（ADR-0004 D2.1/D6.5），不是0——不能用 `base=rb0` 推导 `addr=0 → UNMAPPED`
- RA 存取指令无 rd0/rb0 目的约束，RA rrii 没有合法的 ILLI 型 legality case
- F10 守卫的 `_extract_field` 内嵌函数在 validate_file 循环内定义，每次迭代重新创建——性能可接受但非最优
**遗留问题**：无

## 审阅记录

### 第 1 轮 engineer 自审

**自审结论**：通过，可提交验收。

**逐项检查**：

1. **encoding.word 与 opcodes.yaml 一致性**：全部 30 个 encoding case 的 `(word & mask) == value` 已由生成器 assert 验证 + 独立脚本复核，全部 OK。

2. **F10 方案 B 落实**：
   - base = `rb3`（未使用寄存器），非 `rb1`/`rb2` ✓
   - dest = `rd1`（RD）/ `ra1`（RA），非 `rd0`/`ra0` ✓
   - store src = `rd1`（RD）/ `ra1`（RA），非 `rd0`/`ra0` ✓
   - `input_state` 预置 `rb3 = 0x0000ffff00000000`（RAM 基址）✓
   - multi `immu6 = 1`（≥ 1）✓
   - `expected_state: null`、`expected_pc: null`、`expected_fault: null`、`status: active` ✓

3. **地址合法性**：semantic/boundary case 的 memory address 均在 RAM 窗口 `[0xffff_0000_0000, 0xffff_00ff_ffff]`，无 addr=0 的 semantic/boundary case ✓

4. **input_state 约束**：无 `rd0`/`rb0` 条目 ✓

5. **覆盖率**：30 个 M1 身份全覆盖（22 RD + 4 RB + 4 RA），无遗漏、无与 reg-* 重复 ✓

6. **legality case 覆盖**：
   - ILLI：rd0 dest/src、rb0 dest/src、immu6=0（RA）✓
   - MALIGN：misaligned address（仅 align > 0 的指令）✓
   - UNMAPPED：addr=0（rb3=0）✓

7. **未改 contracts/、未动 reg-*/ctrl-*/misc** ✓
8. **未自行 commit** ✓

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| boundary class expected_fault 只允许 null/ILLI | ✅已修 | 将 MALIGN/UNMAPPED 移入 legality 类，boundary 改为 valid edge address | validate_vectors.py 零错误 |
| RA legality case 无法用 rd0/rb0 触发 ILLI | ✅已修 | 改用 base=rb0 → addr=0 → UNMAPPED | validate_vectors.py 零错误 |
| boundary case 需要 expected_state 和 src 预置 | ✅已修 | boundary case 添加 expected_state 和完整 input_state | validate_vectors.py 零错误 |

### 第 1 轮 reviewer 验收

**判决：Needs Revision**（F10 encoding 本身达标，但同批 `semantic`/`legality` case 存在 29 条期望值错误，违反任务「对齐 fault / unmapped 期望正确」「期望值手工派生」要求）

**审查对象**：`tests/vectors/isa/mem-rd.yaml`(126) / `mem-rb.yaml`(24) / `mem-ra.yaml`(24) / `tools/testcases/generate_mem_vectors.py`
**判据来源（独立阅读）**：`contract-isa.md` §2.2/§2.3/§2.7/§4.1/§4.2/§4.9、`adr-0004-test-machine.md` D1/D2.1/D5.6/D6.5、`contracts/opcodes.yaml`、`contracts/legality_rules.yaml`、`tests/vectors/schema.md`、`tests/vectors/inventory.md`

---

#### 1. 重跑记录（全部为本 reviewer 亲自执行；日志在 `.tao/logs/`）

**① `python3 tools/testcases/validate_vectors.py`**（`.tao/logs/TESTCASES-004t-review-validate_vectors.log`）
```
validate_vectors: 178/178 M1 identities covered OK (inventory sync OK; 9 data files, 540 cases)
EXIT=0
```
**② `make check`**（`.tao/logs/TESTCASES-004t-review-make_check.log`）
```
enabled components: none
references: 2
manifest validation: PASS
validate_vectors: 178/178 M1 identities covered OK (inventory sync OK; 9 data files, 540 cases)
repository checks: PASS
EXIT=0
```
> 与完成区「零错误 / PASS」一致。但两条门只做结构/一致性校验，**不查语义期望值**（schema.md 自述），故不作为 F10/语义正确的证据。

**③ F10 独立推演**（自写脚本，不调生成器；`.tao/logs/TESTCASES-004t-review-f10.log`、`-f10-table.log`）
```
total cases: 174  identities: 30
encoding cases: 30  F10 pass: 30  risks: 0
```
**④ 故障期望独立推演**（`.tao/logs/TESTCASES-004t-review-faults.log`）
```
REAL mismatches: 14
mem-rd 7  ld.uw-rd rrii legality expected='MALIGN'   derived='NOFAULT(ea=0xffff00000000)'
mem-rd 13 ld.ut-rd ... 24 ld.sw-rd ... 30 ld.st-rd ... 41 st.w-rd ... 47 st.t-rd ...
mem-rd 53 ld.o-rd ... 59 st.o-rd
mem-rb 2  ld.o-rb ... 8 st.o-rb
mem-ra 2  ld.o-ra ... 8 st.o-ra
mem-ra 1  ld.o-ra rrii legality expected='UNMAPPED' derived='AMBIG(base=rb0/PC)'
mem-ra 7  st.o-ra rrii legality expected='UNMAPPED' derived='AMBIG(base=rb0/PC)'
```
**⑤ semantic/boundary 期望值独立重算**（`.tao/logs/TESTCASES-004t-review-semantic.log`）
```
semantic/boundary value/address issues: 15
（全部为 rrii semantic：指令 EA 与 input/expected memory 地址不符）
```
**⑥ 覆盖率与归口**（`.tao/logs/TESTCASES-004t-review-coverage.log`）
```
mem identities: 30
overlap mem & other: set()
inventory file mismatch: []
inventory rows for mem: 30
```
**⑦ 生成器可复现**（`/tmp/opencode/TESTCASES-004t-review/repro/`）
```
mem-rd.yaml: IDENTICAL   mem-rb.yaml: IDENTICAL   mem-ra.yaml: IDENTICAL
```
**⑧ 反造假注入**（副本 `/tmp/opencode/TESTCASES-004t-review/repo/`，未污染真实仓库；`.tao/logs/TESTCASES-004t-review-injection.log`）
```
baseline EXIT=0
INJECT1 encoding base rb3->rb2 (word 0x10043000->0x10042000)   EXIT=0  ← 未捕获
INJECT2 encoding expected_fault=MALIGN                          EXIT=1  捕获
INJECT3 semantic memory 地址 0x80000000（越出 RAM）             EXIT=1  捕获
INJECT4 encoding input_state 去掉 rb3 preset                    EXIT=0  ← 未捕获
INJECT5 multi encoding immu6=0                                  EXIT=0  ← 未捕获
INJECT6 encoding dest=rd0                                       EXIT=0  ← 未捕获
```

---

#### 2. F10 逐条推演（30 条全量，不抽样）

推演规则：base 字段=`rb3`（未使用，`input_state` 预置 `0x0000FFFF00000000`）→ `rb1`(SP)/`rb2`(RAM 基址) 未被占用；dest/src 非 `rd0`；base 非 `rb0`；rrri `immu6≥1`；EA 落 ADR-0004 RAM 窗口；`expected_fault/pc/state = null`、`status: active`。

**结果：encoding 条数 30 / 推演通过 30 / 风险 0**

| insn | format | word | ha | hb | hc | hd | 手算 EA | 判 |
|---|---|---|---|---|---|---|---|---|
| ld.ub-rd | rrii | 0x10043000 | 1 | 3 | 0 | 0 | 0xffff_0000_0000 | ✅ |
| ld.uw-rd | rrii | 0x11043000 | 1 | 3 | 0 | 0 | 同上 | ✅ |
| ld.ut-rd | rrii | 0x12043000 | 1 | 3 | 0 | 0 | 同上 | ✅ |
| ld.sb-rd | rrii | 0x13043000 | 1 | 3 | 0 | 0 | 同上 | ✅ |
| ld.sw-rd | rrii | 0x14043000 | 1 | 3 | 0 | 0 | 同上 | ✅ |
| ld.st-rd | rrii | 0x15043000 | 1 | 3 | 0 | 0 | 同上 | ✅ |
| st.b-rd | rrii | 0x18043000 | 1 | 3 | 0 | 0 | 同上 | ✅ |
| st.w-rd | rrii | 0x19043000 | 1 | 3 | 0 | 0 | 同上 | ✅ |
| st.t-rd | rrii | 0x1A043000 | 1 | 3 | 0 | 0 | 同上 | ✅ |
| ld.o-rd | rrii | 0x20043000 | 1 | 3 | 0 | 0 | 同上 | ✅ |
| st.o-rd | rrii | 0x21043000 | 1 | 3 | 0 | 0 | 同上 | ✅ |
| ldm.ub-rd | rrri | 0x28043081 | 1 | 3 | 2 | 1 | 同上 | ✅ |
| ldm.uw-rd | rrri | 0x29043081 | 1 | 3 | 2 | 1 | 同上 | ✅ |
| ldm.ut-rd | rrri | 0x2A043081 | 1 | 3 | 2 | 1 | 同上 | ✅ |
| ldm.sb-rd | rrri | 0x2B043081 | 1 | 3 | 2 | 1 | 同上 | ✅ |
| ldm.sw-rd | rrri | 0x2C043081 | 1 | 3 | 2 | 1 | 同上 | ✅ |
| ldm.st-rd | rrri | 0x2D043081 | 1 | 3 | 2 | 1 | 同上 | ✅ |
| stm.b-rd | rrri | 0x30043081 | 1 | 3 | 2 | 1 | 同上 | ✅ |
| stm.w-rd | rrri | 0x31043081 | 1 | 3 | 2 | 1 | 同上 | ✅ |
| stm.t-rd | rrri | 0x32043081 | 1 | 3 | 2 | 1 | 同上 | ✅ |
| ldm.o-rd | rrri | 0x38043081 | 1 | 3 | 2 | 1 | 同上 | ✅ |
| stm.o-rd | rrri | 0x39043081 | 1 | 3 | 2 | 1 | 同上 | ✅ |
| ld.o-rb | rrii | 0x22043000 | 1 | 3 | 0 | 0 | 同上 | ✅ |
| st.o-rb | rrii | 0x23043000 | 1 | 3 | 0 | 0 | 同上 | ✅ |
| ldm.o-rb | rrri | 0x3A043081 | 1 | 3 | 2 | 1 | 同上 | ✅ |
| stm.o-rb | rrri | 0x3B043081 | 1 | 3 | 2 | 1 | 同上 | ✅ |
| ld.o-ra | rrii | 0x24043000 | 1 | 3 | 0 | 0 | 同上 | ✅ |
| st.o-ra | rrii | 0x25043000 | 1 | 3 | 0 | 0 | 同上 | ✅ |
| ldm.o-ra | rrri | 0x3C043081 | 1 | 3 | 2 | 1 | 同上 | ✅ |
| stm.o-ra | rrri | 0x3D043081 | 1 | 3 | 2 | 1 | 同上 | ✅ |

- rrii EA = `rb3 + sign_ext(imms12=0)` = `0xffff_0000_0000`（RAM 起点，8B 对齐）；
- rrri EA = `rb3 + rd2`，`rd2` 未预置 → 按 ADR-0004 D2.1/D6.5 复位值 0 ⇒ EA 同为 RAM 起点；`ha+immu6 = 2 ≤ 64`（§4.1.2 范围规则）。
- 结论：30 条 encoding **均可解码执行且不触发任何 fault**（无 ILLI / MALIGN / UNMAPPED），F10 方案 B 落实正确。

#### 3. 编码正确性（独立手算，不采信生成器 assert）

- 全部 **174/174** case 的 `(word & mask) == value` 与 `contracts/opcodes.yaml` 一致；
- 30 条 encoding 另按 `word = (op<<24)|(ha<<18)|(hb<<12)|(hc<<6)|hd` 逐条重建，**0 不一致**；
- `op` 逐条与 `contract-isa.md` §2.7 QFC 主表对照（`0x10`–`0x15`/`0x18`–`0x1A`/`0x20`–`0x25`/`0x28`–`0x2D`/`0x30`–`0x32`/`0x38`–`0x3D`），**全部吻合**；
- 生成器只读 `contracts/opcodes.yaml`（REPO 由 `__file__` 推导，无硬编码绝对路径），**未从 LLVM/QEMU 反推**（无 `mnt`/`home`/`DADAO-0628` 字符串；复现结果 byte-identical）。

#### 4. finding 表

| # | 级别 | finding | 位置 | 真实证据 |
|---|---|---|---|---|
| F-1 | **阻断** | **15 条 rrii `semantic` 的 memory 地址与指令实际 EA 不符**：rrii 的地址偏移只能来自编码内 `imms12`（hc/hd，§2.2/§4.1.1），生成器却把偏移放到无操作数意义的 `rd2`：`input_state.memory` 放在 `EA+0x100`，而指令 EA=`0xffff_0000_0000`，`expected_state` 按 +0x100 的值推导 ⇒ 期望值不可派生/错误 | mem-rd case[3,9,15,20,26,32,37,43,49,55,61]；mem-rb[4,10]；mem-ra[4,10] | `semantic_review2.log`：`LOAD EA=0xffff00000000 not in input memory ['0xffff00000100']`；对照 `schema.md` L55-82 示例（`word=0x10041000`、memory 地址 = `rb1+0` = EA） |
| F-2 | **阻断** | **12 条 rrii `legality` MALIGN 期望错误**：word 的 `imms12=0`，`rd2` 对 rrii 无作用 ⇒ 实际 EA=`RAM_BASE`，8B 对齐，**不会触发 MALIGN** | mem-rd case[7,13,24,30,41,47,53,59]；mem-rb[2,8]；mem-ra[2,8] | `faults.log`：`expected='MALIGN' derived='NOFAULT(ea=0xffff00000000)'`；case[7] notes 自写「EA=...+1」而 word=`0x11043000`（`&0xFFF=0`） |
| F-3 | **阻断** | **2 条 RA rrii `legality` 以 `base=rb0 → addr=0 → UNMAPPED` 论证不成立**：ADR-0004 D2.1/D6.5 明确 `rb0 = 当前指令地址(PC)`，非 0；该 case `input_state={}` 未定 PC，期望不可派生（若指令落在 RAM 基址，EA 反而映射成功） | mem-ra case[1,7]（`word=0x24040000`/`0x25040000`，`hb=0`） | `faults.log`：`expected='UNMAPPED' derived='AMBIG(base=rb0/PC)'`；ADR-0004 L308-315 |
| F-4 | 观察（非阻断） | validator/守卫**未覆盖 F10 的关键约束**：注入「base=rb2」「删 rb3 preset」「multi immu6=0」「dest=rd0」均 `EXIT=0`（只有「encoding fault≠null」「semantic 地址越 RAM」被捕获）。即 F10 正确性目前**只靠人审**，无机械回归门 | `tools/testcases/validate_vectors.py`（003t 的 F9 guard 只作用于 semantic/boundary） | `injection.log` INJECT1/4/5/6 `EXIT=0` |
| F-5 | 观察（非阻断） | `inventory.md` 对 30 个 mem 身份的 `boundary` 列均为 `—`（不适用），但本任务对每个身份都产出 `boundary` case；属超集覆盖，validator 不判错，但与冻结矩阵表述不一致，建议架构师定调 | inventory.md L20-49 vs mem-*.yaml | `coverage_check.log` |
| F-6 | 观察（非阻断） | MALIGN/UNMAPPED case 的机器可读 `spec_cite` 取自 opcodes.yaml（`SimRISC-01/02 §存取*寄存器`），fault 依据实际在 `legality_rules.yaml`（`data_malign`）/ADR-0004 D5.6；仅 notes 提到 ADR-0004，`spec_cite` 未引 | 各 legality case | 逐 case 打印（见 F-2/F-3 数据） |

> 说明：F-1/F-2 同一根因（生成器对 rrii 误用 `rd2` 作偏移）；F-1 影响 15 条 semantic，F-2 影响 12 条 legality，F-3 另 2 条。**合计 29 条 active case 期望值错误**，均在 `mem-*`（本任务拥有文件）内。

#### 5. 约束核验（逐条）

| # | 任务硬约束 | 核验 | 证据 |
|---|---|---|---|
| 1 | 3 文件存在、覆盖全部访存 M1 身份 | ✅ | 30/30 身份（22+4+4），`coverage_check.log` |
| 2 | 从零生成、无身份遗漏、无与 `reg-*` 重复 | ✅（生成器可复现且不读旧数据） | `repro/` 三文件 IDENTICAL；`overlap mem & other: set()` |
| 3 | encoding `status:active`/`expected_fault:null`/`expected_pc:null` | ✅（30/30） | `f10.log` F10 pass 30 |
| 4 | encoding `input_state` 含 `rb3=0x0000ffff00000000`、dest 非 rd0、base 非 rb0 | ✅（30/30） | `f10-table.log`（hb=3、ha=1 全部） |
| 5 | multi `immu6 ≥ 1` | ✅（11 条 rrri 均 `immu6=1`） | `f10-table.log` |
| 6 | 每条 `encoding.word` 与 opcodes mask/value 一致 | ✅（174/174；30 条另独立重建） | `f10.log` risks 0 |
| 7 | **每条 encoding 语义推演「可解码无 fault」** | ✅ | §2，30/30 |
| 8 | semantic/boundary 地址在 RAM 区；`input_state` 无 rd0/rb0 | ⚠️ 地址字面在 RAM 且无 rd0/rb0，**但 rrii semantic 的地址与 EA 不符（F-1）**；legality MALIGN/UNMAPPED 期望错误（F-2/F-3） | §4 finding 表 |
| 9 | 未改 `contracts/`；未动 `reg-*`/`ctrl-*`/`misc` | ✅ | `git status --porcelain` 仅 4 个新增文件 + 任务书改动 |
| 10 | `validate_vectors.py` 零错误；`make check` PASS | ✅（但见 F-4：门未覆盖语义） | 重跑记录 ①② |
| 11 | 下游 QEMU harness 判据（本任务不适用） | — | — |
| 12 | 未自行 commit | ✅ | 4 文件均 untracked；`git log -5` 无 004t 提交 |

#### 6. 判决

**Needs Revision** —— F10（本任务核心）达标：30 条 encoding 全部可解码执行且无 fault，字段/地址/编码均正确。但同任务 §3 要求「复核 semantic/boundary/legality……对齐 fault 与 unmapped 期望正确」未达成，**29 条 active case 期望值错误**（F-1/F-2/F-3）。

**可执行返工清单**

1. **修生成器 rrii 偏移表达**（`tools/testcases/generate_mem_vectors.py`，根因同一处）：
   - `gen_semantic`：rrii 分支改为 `word = build_word_rrii(op, ha, hb, addr_offset)`（把 `0x100` 编入 `imms12`），并**删除**该分支里毫无作用的 `input_state.rd.rd2`；预期：EA = `0xffff_0000_0100`，与 memory 地址一致。
   - `gen_legality_malign`：rrii 分支改为 `word = build_word_rrii(op, ha, hb, misalign_off)`，删除 `rd2` 预置；预期：`ld.uw` → EA=`…0001`(需2B)、`ld.o` → EA=`…0007`(需8B) → MALIGN 成立。
   - rrri 分支（EA=`rb3+rd2`）已正确，保持不变。
2. **修 RA rrii legality**（`mem-ra.yaml`）：删除或改写 case[1]/case[7]（`base=rb0`）——`rb0=PC`，不可假定为 0；若需 ILLI 型 legality，RA 无 rd0/rb0 目的约束，可改用**可派生的** UNMAPPED（base=`rb3` 且 `rb3=0`，同各文件已有 `gen_legality_unmapped`）或直接删去冗余条。
3. **重跑并取证**：`python3 tools/testcases/generate_mem_vectors.py` → `python3 tools/testcases/validate_vectors.py`（须 exit 0）→ `make check`（须 PASS）→ 对全部 `semantic` 复算 EA 与 memory 地址一致、对全部 `legality` 复算 fault 类型。
4. **（建议，需架构师定）** 给 validator 补 F10 guard（encoding 类：base 字段==3、`input_state.rb` 含 `rb3=0x0000ffff00000000`、`ha!=0`、rrri `immu6>=1`），否则 F10 无机械回归门（F-4）。该改动超出本任务文件所有权，请架构师决定是否另立任务。
5. **（建议）** 明确 `inventory.md` `boundary` 列与超集 boundary case 的关系（F-5），并在 legality 的 `spec_cite` 中引用 fault 依据（F-6）。

### 第 1 轮 engineer 自审（返工）

**自审结论**：通过，可提交验收。6 项返工要求全部完成。

**返工处置逐项**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F-1 rrii semantic EA≠memory addr（15条） | ✅已修 | `gen_semantic` rrii 分支：`_build_encoding_word(rec, addr_offset)` 把 imms12 编入 word；删除 rrii 分支无作用的 rd2 preset | 独立重算172条0 mismatch；spot-check ld.ub-rd word=0x10043100 imms12=0x100 EA=0xffff00000100=memory addr |
| F-2 rrii MALIGN EA 未对齐（12条） | ✅已修 | `gen_legality_malign` rrii 分支：`_build_encoding_word(rec, misalign_off)` 编入 imms12；删除 rd2 preset | 独立重算172条0 mismatch；spot-check ld.uw-rd word=0x11043001 EA=0xffff00000001≠2B对齐；ld.o-rd word=0x20043007 EA=…0007≠8B对齐 |
| F-3 RA rrii base=rb0 论证不成立（2条） | ✅已修 | `gen_legality_illi` RA rrii 分支返回 None（rb0=PC≠0，RA 无 rd0/rb0 目的约束）；main() 处理 None | mem-ra.yaml22条（原24），无 hb=0 legality case；MALIGN+UNMAPPED 覆盖充分 |
| F-4 validator F10 守卫 | ✅已修 | `validate_vectors.py` 追加 F10 guards：hb≠0/1/2、base 预置 RAM 窗口、rrri immu6≥1、ha≠0 | 注入测试4类全部 CAUGHT + baseline PASS（`TESTCASES-004t-rework-injection.log`） |
| F-5 inventory boundary 列 | ✅已修 | `inventory.md`30条 mem 身份 boundary `—`→`✓` | validate_vectors.py exit 0 |
| F-6 legality spec_cite fault 引用 | ✅已修 | MALIGN notes 引 `contract-isa §4.1.1, legality_rules data_malign`；UNMAPPED notes 引 `ADR-0004 D5.6` | spot-check ld.uw-rd MALIGN notes 含 `contract-isa §4.1.1, legality_rules data_malign` |

**逐项自审**：

1. **encoding.word 与 opcodes.yaml 一致性**：30条 encoding case 的 `(word & mask) == value` 由生成器 assert + validator 校验，全部 OK。encoding word 未变（imms12=0），仅 semantic/boundary/MALIGN word 变化。

2. **F10 方案 B 落实（encoding）**：
   - base = `rb3`（未使用寄存器），非 `rb0`/`rb1`/`rb2` ✓（F10 守卫机械校验）
   - dest = `rd1`/`ra1`，非 `rd0`/`ra0` ✓（F10 守卫机械校验）
   - store src = `rd1`/`ra1`，非 `rd0`/`ra0` ✓（F10 守卫机械校验）
   - `input_state` 预置 `rb3 = 0x0000ffff00000000`（RAM 基址）✓（F10 守卫机械校验）
   - multi `immu6 = 1`（≥ 1）✓（F10 守卫机械校验）
   - `expected_state/pc/fault = null`、`status: active` ✓

3. **rrii semantic EA 与 memory 地址一致**：全部 rrii semantic case 的 word imms12 = addr_offset，EA = rb3 + sign_ext(imms12) = memory address ✓（独立重算脚本0 mismatch）

4. **rrii MALIGN EA 真的未对齐**：全部 rrii MALIGN case 的 word imms12 = align-1，EA = rb3 + sign_ext(align-1) 未对齐 ✓（独立重算脚本0 mismatch）

5. **无 base=rb0 的 RA rrii legality**：mem-ra.yaml 无 hb=0 的 legality case ✓（spot-check 确认）

6. **F10 守卫注入测试**：4类注入（base=rb2、删 rb3 preset、immu6=0、dest=rd0）全部 CAUGHT ✓（`TESTCASES-004t-rework-injection.log`）

7. **独立全量重算**：172条 case（30 encoding + 142 semantic/boundary/legality），EA 派生 + fault 判定逐条验证，0 mismatch ✓（`TESTCASES-004t-rework-recalc.log`）

8. **覆盖率**：30个 M1 身份全覆盖（22 RD + 4 RB + 4 RA），无遗漏、无与 reg-* 重复 ✓

9. **未改 contracts/、未动 reg-*/ctrl-*/misc** ✓
10. **未自行 commit** ✓

**返工后数据变化**：
- mem-ra.yaml：24→22 cases（删除2条 RA rrii ILLI）
- 总 cases：540→538（validate_vectors.py 输出确认）
- rrii semantic word：imms12=0→imms12=addr_offset（如0x100）
- rrii MALIGN word：imms12=0→imms12=align-1（如1/3/7）
- rrii MALIGN/semantic input_state：删除无作用的 rd2 preset

### 第 2 轮 reviewer 验收

**判决：Accepted**（F-1~F-6 六项返工均在本 reviewer 亲自重跑/独立重算下确认修复；验收标准 1–10 全部满足。另登记 2 项非阻断观察，供架构师终审参考。）

**审查对象**：`tests/vectors/isa/mem-rd.yaml`(126) / `mem-rb.yaml`(24) / `mem-ra.yaml`(22) / `tools/testcases/generate_mem_vectors.py`(575) / `tools/testcases/validate_vectors.py`(+81 行) / `tests/vectors/inventory.md`
**判据来源（独立阅读，非采信生成器）**：`contract-isa.md` §2.2/§2.3/§4.1/§4.1.1/§4.1.2/§4.2/§4.9、`adr-0004-test-machine.md` D1/D2.1/D5.6/D6.5、`contracts/opcodes.yaml`(field bits)、`contracts/legality_rules.yaml`、`tests/vectors/schema.md`、`tests/vectors/inventory.md`

---

#### 1. 重跑记录（全部为本 reviewer 亲自执行；日志在 `.tao/logs/`）

**① `python3 tools/testcases/validate_vectors.py`**（`.tao/logs/TESTCASES-004t-review2-validate_vectors.log`）
```
validate_vectors: 178/178 M1 identities covered OK (inventory sync OK; 9 data files, 538 cases)
EXIT=0
```
**② `make check`**（`.tao/logs/TESTCASES-004t-review2-make_check.log`）
```
enabled components: none
references: 2
manifest validation: PASS
validate_vectors: 178/178 M1 identities covered OK (inventory sync OK; 9 data files, 538 cases)
repository checks: PASS
EXIT=0
```
> 与完成区「validate 零错误 / make check PASS」一致。M1 总数 178、数据 538 条（=第1轮 540 − 删除的 2 条 RA rrii ILLI）。

**③ 独立全量重算**（自写脚本，不 import/调用生成器与 validator；`.tao/logs/TESTCASES-004t-review2-recalc.log`、`-state-mask.log`）
```
total cases: 172
fault mismatches: 0
F-1 rrii semantic EA != memory addr: 0
F-2 rrii MALIGN misaligned checks: 12  (all misaligned=True)
semantic/boundary EA (non-RAM/unaligned/fault): 0
F10 encoding issues: 0
TOTAL PROBLEMS: 0   EXIT=0
```
```
total mem cases: 172
(word&mask)==value errors: 0
expected_state errors: 0
PROBLEMS: 0   EXIT=0
```
**④ 覆盖率/归口**（`.tao/logs/TESTCASES-004t-review2-coverage.log`）
```
mem identities: 30
overlap mem & other: set()
mem-rd.yaml 126  {'legality': 60, 'encoding': 22, 'semantic': 22, 'boundary': 22}
mem-rb.yaml 24   {'legality': 12, 'encoding': 4, 'semantic': 4, 'boundary': 4}
mem-ra.yaml 22   {'legality': 10, 'encoding': 4, 'semantic': 4, 'boundary': 4}
```
**⑤ F10 守卫注入**（副本 `/tmp/opencode/TESTCASES-004t-review2/repo/`，未污染真实仓库；`.tao/logs/TESTCASES-004t-review2-injection.log`、`-injection-msgs.log`）
```
baseline (unmodified copy)          EXIT=0
INJECT1 encoding base rb3->rb2      EXIT=1  捕获  F10: encoding base field hb=2 ...
INJECT2 encoding remove rb3 preset  EXIT=1  捕获  F10: encoding base register rb3 not preset ...
INJECT3 multi encoding immu6=1->0   EXIT=1  捕获  F10: rrri encoding immu6=0, must be >= 1
INJECT4 encoding dest rd1->rd0      EXIT=1  捕获  F10: encoding dest/src ha=0 (rd0/ra0) ...
```
**⑥ 生成器可复现**（`/tmp/opencode/TESTCASES-004t-review2/repro/`；`.tao/logs/TESTCASES-004t-review2-repro.log`）
```
mem-rd.yaml: DIFFERS   mem-rb.yaml: IDENTICAL   mem-ra.yaml: IDENTICAL
（mem-rd 差异仅 5 行文件头注释；数据部分 byte-identical，见 §5 观察 A）
```
**⑦ 其余核验日志**：`-final.log`（class/status/pc/notes 全量）、`-f3-scan.log`（无 base=rb0 legality）、`-inventory.log`（inventory 30 行一致）、`-gitscope.log`、`-notes.log`

---

#### 2. F-1~F-6 返工逐条复验（不抽样，全量）

**F-1（rrii semantic EA≠memory）—— 已真正修复**：独立重算全部 15 条 rrii semantic（RD 11 + RB 2 + RA 2）：`word.imms12` 已编入地址偏移（`0x100`），EA = `rb3 + sign_ext(imms12)` = `0xffff_0000_0100`，与 `input_state.memory`（load）/`expected_state.memory`（store）地址**逐条相等**；`rd2` 预置已从 rrii 分支删除。mismatch **0/15**。佐证：`mem-rd case[3] word=0x10043100 → EA=0xffff00000100`。

**F-2（rrii MALIGN 期望错）—— 已真正修复**：独立按 `contract-isa.md §4.1.1` + `legality_rules data_malign` 判定全部 12 条 rrii MALIGN：`word.imms12 = align-1`（1/3/7），EA = `rb3 + imms12` 真的未对齐（`ea % align != 0` **12/12 True**），且落 RAM 映射内（对齐优先于映射之后判定，先映射→再对齐，MALIGN 成立）。mismatch **0/12**。佐证：`ld.uw case[7] word=0x11043001 → EA=0xffff00000001`、`ld.o case[53] word=0x20043007 → EA=0xffff00000007`。

**F-3（RA rrii base=rb0 论证不成立）—— 已真正修复**：三个 mem 文件**无任何** `hb=0` 的 legality case（`-f3-scan.log`）；mem-ra 的 rrii RA 仅保留可派生的 MALIGN（imms12 编入 word）+ UNMAPPED（rb3=0 → EA=0 → `0x87`），无 rd0/rb0 型非法（§4.9：ra0 可读写，RA 无 rd0/rb0 目的约束）。mem-ra 22 条（原 24），删除的 2 条即第 1 轮 F-3 所指 case[1]/case[7]。

**F-4（validator F10 守卫）—— 按用户裁定并入本任务且生效**：4 类指定注入**全部 exit 1**（见 §1⑤），真实树 baseline exit 0 零误报。守卫为**纯新增**（`git diff` 仅 +81 行，无删除、无弱化既有断言）。**但存在部分覆盖缺口，见 §5 观察 B（非阻断，数据本身正确）**。

**F-5（inventory boundary 列）—— 已修复且一致**：30 条 mem 身份 `boundary` 列 `—`→`✓`（`git diff` 仅此 30 行变更），且每个 mem 身份确实存在 boundary case；`file` 列与实际文件一致（`-inventory.log`：mismatches 0/30）。

**F-6（legality spec_cite 引用 fault 依据）—— 已修复**：MALIGN notes 含 `contract-isa §4.1.1, legality_rules data_malign`；UNMAPPED notes 含 `ADR-0004 D5.6`（`-notes.log`）。`spec_cite` 字段仍取 opcodes.yaml 规范来源（OPC 语义），fault 依据记于 notes——符合"非阻断观察"原意。

---

#### 3. 独立全量重算（本轮重点）

**派生规则（全部来自合约，非 validator/生成器）**：
- `word = (op<<24)|(ha<<18)|(hb<<12)|(hc<<6)|hd`（§2.2）；rrii `imms12 = hc:hd` 有符号 12 位；rrri `immu6 = hd[5:0]`。
- EA：rrii = `rb[hb] + sign_ext(imms12)`；rrri = `rb[hb] + rd[hc]`（§4.1.1/§4.1.2/§4.9）；寄存器值取 `input_state`，缺省按 D2.1 复位值（rb1/rb2 按 D6.5 入口值）。
- fault 判定序：① 静态解码（RD/RB `ha=0`→ILLI；rrri `immu6=0`→ILLI；`ha+immu6>64`→ILLI）→ ② D5.6 动态：映射（非 ROM/RAM/Exit→UNMAPPED）→ 对齐（`EA%align≠0`→MALIGN）→ 访问种类（ROM store/Exit 非 8B st.o→ILLI）。

**结果：172 条 case 逐条重算，mismatch 0。**

| 维度 | 条数 | mismatch |
|---|---|---|
| 全部 case 故障判定（encoding/legality/semantic/boundary） | 172 | **0** |
| `(word & mask) == value`（opcodes.yaml） | 172 | **0** |
| semantic/boundary `expected_state`（load 符号/零扩展、store 截断、地址==EA） | 60 | **0** |
| semantic/boundary EA 落 RAM 且对齐、无 fault | 60 | **0** |
| F-1 rrii semantic EA == memory 地址 | 15 | **0** |
| F-2 rrii MALIGN EA 真未对齐 | 12 | **0**（12/12 未对齐） |
| F10 encoding 无 fault + 字段约束 | 30 | **0** |
| mem 身份覆盖 / 与 reg-* 重叠 | 30 / 0 | — |

> 未以 validator 绿灯为唯一判据：以上均由独立脚本重算，validator 输出仅作结构门佐证。

---

#### 4. F10 逐条推演（30 条全量）

`input_state.rb.rb3 = 0x0000ffff00000000`（RAM 窗口内）；`hb=3`（非 rb0/rb1/rb2）；`ha=1`（非 rd0/ra0）；rrri `immu6=1`；`expected_state/pc/fault=null`、`status=active`。rrii EA=`rb3+0`；rrri EA=`rb3+rd2`（语义/边界 `rd2=0x100` 或 =0；encoding 未预置 rd2→复位 0）。**30/30 可解码执行且不触发任何 fault**（无 ILLI/MALIGN/UNMAPPED），F10 方案 B 落实正确。

---

#### 5. finding 表（第 2 轮）

| # | 级别 | finding | 位置 | 真实证据 |
|---|---|---|---|---|
| P-1 | ✅ 已修复 | F-1 rrii semantic EA≠memory（15 条） | mem-* | `recalc.log` F-1 issues 0/15；`mem-rd[3] word=0x10043100 EA=0xffff00000100` |
| P-2 | ✅ 已修复 | F-2 rrii MALIGN 期望错（12 条） | mem-* | `recalc.log` 12/12 misaligned=True；`mem-rd[7] EA=…0001`、`[53] EA=…0007` |
| P-3 | ✅ 已修复 | F-3 RA rrii base=rb0 论证不成立（2 条） | mem-ra | `f3-scan.log` 无 hb=0 legality；mem-ra 24→22 |
| P-4 | ✅ 已修复 | F-4 validator F10 守卫缺失 | validate_vectors.py | 4 类注入全 exit 1；`git diff` 仅 +81 行新增 |
| P-5 | ✅ 已修复 | F-5 inventory boundary 列 | inventory.md | `inventory.log` 30/30 一致 |
| P-6 | ✅ 已修复 | F-6 legality spec_cite/notes fault 依据 | mem-* | `notes.log` 引用 `§4.1.1, data_malign` / `D5.6` |
| O-A | 观察（非阻断） | `mem-rd.yaml` **缺生成器文件头注释**（5 行），`mem-rb`/`mem-ra` 有；数据部分 byte-identical（`diff` 仅 `0a1,5`） | `tests/vectors/isa/mem-rd.yaml` | `repro.log`：`mem-rd.yaml: DIFFERS`；`grep -v '^#' diff` 仅多空行 |
| O-B | 观察（非阻断） | F10④ 仅提取字段名 `rdha`，**未覆盖 RB 的 `rbha`**：注入 `ld.o-rb rbha=1→0`（word `0x22003000`，实际应 ILLI）后 validator **exit 0（未被捕获）**；RA `raha=0` 合法本无需守卫。数据本身正确（全部 RB encoding `ha=1`） | `validate_vectors.py` F10④ | `.tao/logs/TESTCASES-004t-review2-injection-rbha.log`：`INJECT rbha=0 ... EXIT=0` |

> O-A/O-B 均不影响交付数据的正确性，也不违反任一验收标准；O-A 可由重跑生成器消除，O-B 建议后续在 F10④ 增加 `rbha` 分支（`rbha==0 → ILLI`），供架构师定夺。

---

#### 6. 约束核验（逐条）

| # | 任务硬约束 | 核验 | 证据 |
|---|---|---|---|
| 1 | 3 文件存在、覆盖全部访存 M1 身份 | ✅ | 30/30（22+4+4），`coverage.log` |
| 2 | 从零生成、无遗漏、无与 `reg-*` 重复 | ✅ | 生成器可复现数据；`overlap mem & other: set()` |
| 3 | encoding `active`/`fault:null`/`pc:null` | ✅（30/30） | `final.log` enc_bad=[] |
| 4 | `input_state` 含 `rb3=0x0000ffff00000000`、dest 非 rd0、base 非 rb0、store 源非 rd0 | ✅（30/30） | `recalc.log` F10 issues 0；`final.log` |
| 5 | multi `immu6 ≥ 1` | ✅（11 条 rrri 全 =1） | 同上 |
| 6 | `(word & mask) == value` | ✅（**172/172**） | `state-mask.log` errors 0 |
| 7 | **每条 encoding 语义推演「可解码无 fault」** | ✅（30/30，独立重算） | §4；`recalc.log` F10 issues 0 |
| 8 | semantic/boundary 地址在 RAM 区；`input_state` 无 rd0/rb0 | ✅（60/60；`f3-scan` 无 rd0/rb0 条目） | `final.log` sem_bad=[] |
| 9 | 未改 `contracts/`；未动 `reg-*`/`ctrl-*`/`misc` | ✅（`git status` 上述路径为空） | `gitscope.log` |
| 10 | `validate_vectors.py` 零错误；`make check` PASS | ✅（exit 0 / PASS） | §1①② |
| 11 | 下游 QEMU harness 判据 | —（本任务不适用） | — |
| 12 | 未自行 commit | ✅（`git log` 最新 388b4da=003t；3 yaml + 生成器 untracked） | `gitscope.log` |

> 说明：本任务改动了 `validate_vectors.py`（+F10 守卫）与 `inventory.md`（boundary 列），超出「仅 3 个目标文件」字面范围，但 F-4/F-5 已由用户裁定并入本任务（第 1 轮返工清单第 4/5 项 → 用户裁定），属**授权改动**；`contracts/` 与 `reg-*`/`ctrl-*`/`misc` 未触碰。

---

#### 7. 判决

**Accepted** —— 验收命令块（`validate_vectors.py`、`make check`）在本 reviewer 亲自重跑下**全部通过**（exit 0 / PASS）；F-1~F-6 六项返工经独立全量重算（172 条，0 mismatch）确认修复；验收标准 1–12 逐条满足；无约束违反。O-A/O-B 为不影响交付正确性的非阻断观察，留架构师终审。残留阻断项：无。

**遗留/阻断项**：无阻断。非阻断建议：O-A 重跑生成器补齐 `mem-rd.yaml` 文件头；O-B 扩展 F10④ 至 RB `rbha`。
