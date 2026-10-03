# TESTCASES-005t: 控制转移 `br.*`（taken / not-taken 全测）

**模块**：testcases
**项目里程碑**：M1
**依赖**：`TESTCASES-002t`（schema `expected_pc`）；文件级与 `003t`/`004t` 不相交，可并行；默认下发建议排在 `004t` 之后（见「下发建议」）
**状态**：已验证

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `tests/vectors/schema.md`（`TESTCASES-002t` 返工后：含 `expected_pc`）
  - `contracts/opcodes.yaml`（`br.*` 编码字段；`op=value>>24`、`ha=(value>>18)&0x3f`）
  - `.tao/knowledge/contract-isa.md` §5.1/§5.2（条件跳转：rrii 双寄存器、riii 单寄存器、RB 变体）、§9.1（ILLI）
  - `.tao/knowledge/adr-0004-test-machine.md`（D6.5 `rb0` = 当前指令地址；D5.6 访问矩阵）
- **输入说明**：`reg-*`（`003t`）与 `mem-*`（`004t`）已生成并验证；本任务按 `schema.md` **从零生成** `ctrl-br.yaml`，**不是**重组/修复既有文件。
- 输出（**本任务拥有的文件**，`tests/vectors/isa/`）：
  - `ctrl-br.yaml`
- 约束：
  - 期望值**手工派生自 `contract-isa.md`/`spec/`/ADR-0004**，不得从 LLVM/QEMU 反推
  - 覆盖率主键 `(insn, format)`；M1 scope 以 `excluded_m1 != true` 为准
  - **只生成/修改 `ctrl-br.yaml`**；**不改** `contracts/`；**不改** `ctrl-jump`/`ctrl-call`/`ctrl-ret`/`misc`（归 `006t`/`007t`）
  - 参考仓库（`.dadao/DADAO-0628/`）的向量数据**仅内容溯源，不得作为执行依赖**（禁止复制数据正文）
  - 完成后不自行 commit

## 任务范围

### 1. 目标文件（从零生成）

> **数据来源说明**：`reg-*`/`mem-*` 已由 `003t`/`004t` 生成；本任务按 `schema.md` 从零生成 `ctrl-br.yaml`；不再有「旧文件 → 新文件」的重组动作。

| 目标文件 | 覆盖身份 |
|---|---|
| `ctrl-br.yaml` | 全部 `br.*`（10 个身份：`br.n-rd`/`br.nn-rd`/`br.z-rd`/`br.nz-rd`/`br.p-rd`/`br.np-rd`/`br.eq-rd`/`br.ne-rd`/`br.z-rb`/`br.nz-rb`） |

- `jump`/`call`/`ret`（`006t`）与 `swym`（`007t`）不在本任务，亦不在本文件中。

### 2. F7：`br.*` taken / not-taken 全覆盖（本任务核心）

- **背景（上一版丢弃数据的教训）**：上一版只写了「不跳转」路径（`condition false -> no jump`），**taken 路径未覆盖**；本任务从零生成时**必须两种路径都覆盖**。
- **要求**：每个 `br.*` 身份至少覆盖 **taken** 与 **not-taken** 两条 semantic，用 `expected_pc` 表达 PC 效果：
  - 条件为真（taken）：`expected_pc = rb0 + (imm << 2)`，**本任务取 `imm=2`**（target=`rb0+8`；**`imm=1` 会与 not-taken 的 `rb0+4` 同址，无法区分**）；
  - 条件为假（not-taken）：`expected_pc = rb0 + 4`（下一条）；
  - `rb0` 执行时 = **当前指令地址**（ADR-0004 D6.5），由 harness 布局确定；向量 notes 须写明所用 PC 地址与布局来源。
- **条件与立即数语义**（`contract-isa.md` §5.2）：
  - `br.eq rdha, rdhb, imms12`：`rdha == rdhb`；`br.ne`：`rdha != rdhb`；`Addr = rb0 + (imms12<<2)`；
  - `br.n rdha, imms18`：`rdha < 0`；`br.nn`：`>= 0`；`br.z`：`== 0`；`br.nz`：`!= 0`；`br.p`：`> 0`；`br.np`：`<= 0`；`Addr = rb0 + (imms18<<2)`；
  - `br.z rbha, imms18`：`rbha == 0`；`br.nz rbha`：`rbha != 0`；`Addr = rb0 + (imms18<<2)`；
  - 特例：`rdha` 为 `rd0` 时 `br.z` 恒真、`br.nz` 恒假（`contract-isa.md` §5.2.2）。
- **立即数选择**：taken 用例的 `imm` 取 **`2`**（target=`rb0+8`，与 not-taken 的 `rb0+4` 可区分）；**不得**用 `imm=0`（跳到自身 → 自跳死循环，ADR-0004 D6.5），也**不得**用 `imm=1`（与 not-taken 同址，无法区分）。
- **`expected_state`**：`br.*` 不改寄存器，`expected_state` 可为 `{}`/null（按 schema 规则）；PC 效果一律用 `expected_pc`。
- **validator 存在性规则（措辞澄清）**：`002t` 只校验 `expected_pc`「出现时」的合法性；本任务在数据补齐后，向 `tools/testcases/validate_vectors.py` 追加存在性规则，**按「PC-affecting」判定**（即指令语义涉及 PC 结果，**含 `br.*` not-taken 的 `PC+4` 顺延**），而非字面「改变 PC」——`schema.md` 写作「`br.*` taken、`jump`、`call`、`ret`」易误读为仅 taken。本任务按「PC-affecting」实现对 `ctrl-br` 生效，并验证真实树零误报。

### 3. F10：`ctrl-br.yaml` 的 encoding 向量修复

- **要求**：逐条生成 encoding 向量，使 `word` 满足 `(word & mask) == value` 且可解码执行无 fault：
  - 分支的操作数 `rd` 是**源**（可用 `rd0`；`br.z rd0` 恒真、`br.nz rd0` 恒假）；
  - 相对分支立即数用 **`imm=2`**（目标 = `rb0+8`），避免 `imm=0` 自跳死循环、且**不与 not-taken 同址**；
  - `expected_state: null`、`expected_pc: null`、`expected_fault: null`、`status: active`。
- **依据**：`contract-isa.md` §5、ADR-0004 D6.5；0628 的「`rb0`=下一条、`imm=0` 等效 NOP」**不适用**。

### 4. legality / boundary

- 保留并复核 `br.*` 的 legality/boundary（若有）；对齐相关 fault 以 `contract-isa.md` §9/ADR-0004 D5 为准。

## 下发建议

- **数据依赖**：仅 `002t`（需其 schema 的 `expected_pc`）。
- **文件级**：本任务数据从零生成，`ctrl-br.yaml` 与 `reg-*`（`003t`）、`mem-*`（`004t`）、`ctrl-jump`/`ctrl-call`/`ctrl-ret`（`006t`）、`misc`（`007t`）**互不相交**，源文件层面已无共享。
- **共享 `inventory.md`**：`002t` **未交付** inventory 生成脚本（`gen_inventory.py` 仅在 `/tmp` 一次性使用），各任务需手改 `inventory.md` → **默认全串行**（`002t → 003t → 004t → 005t → 006t → 007t`）以避免 `inventory.md` 冲突。

## 验收标准

1. `ctrl-br.yaml` 存在，覆盖全部 10 个 `br.*` M1 身份
2. **每个 `br.*` 身份有 ≥1 条 taken 与 ≥1 条 not-taken 的 active semantic**，`expected_pc` 分别为 `rb0+(imm<<2)` 与 `rb0+4`
3. `expected_pc` 为 48-bit 有效地址；**本任务统一取指令地址 = RAM 入口 `0xffff_0000_0000`**（ADR-0004 D6.5/D2.2，与 `003t` 的 `rela.si` 约定一致）→ `rb0 = 0xffff00000000`；notes 写明该地址与布局来源
4. `br.*` encoding 向量 `status: active`、`expected_fault: null`、`expected_pc: null`，且经推演确认可解码执行无 fault（不 ILLI/不自跳）
5. 未生成/未改动 `jump`/`call`/`ret`/`swym`（交 `006t`/`007t`）；未改 `contracts/`；未动 `reg-*`/`mem-*`
6. `python3 tools/testcases/validate_vectors.py` 零错误；`make check` PASS
7. （**下游、非本任务验收判据**）QEMU harness 就绪后，`ctrl-br.yaml` active 测试全 PASS；本任务仅**记录**该运行验收依赖（branch-over-poison 类 layout 属 harness 能力，见下）
8. 未自行 commit

## 背景（完整）

### 目标

把条件分支向量独立为 `ctrl-br.yaml`，并补齐 taken 路径，使 `br.*` 的**两种执行结果**都有独立 oracle。

### 设计理由

- 上一版（已丢弃）仅覆盖 not-taken，`br.*` 的 taken 分支（跳转目标）无向量 → 控制流覆盖存在系统性缺口；本任务从零生成时补齐。
- `expected_pc` 方案（F7 方案 (i)）使 PC 效果可断言，无需依赖 `expected_state` 表达 PC。

### 关键概念 / 数据

**相对控制流地址公式**（`contract-isa.md` §5.1）：

```
Addr = rb0 + (imm << 2)      # imm 为字偏移；<<2 转字节
```

- ADR-0004 D6.5：`rb0` 执行时 = **当前指令地址**；
  - `imm=0` → 跳到自身 → 自跳死循环；
  - `imm=1` → 下一条 → fall-through；
  - `imm=-1` → 上一条 → 死循环。
- 故 semantic/encoding 必须用 `imm=2`（非自跳且与 not-taken 可区分）；not-taken 时 PC = `rb0 + 4`。

**branch-over-poison（TDD 设计注释，供 harness 参考）**：

```
# [setup]
# [branch cond, +1]   ← taken：跳过 poison
# [illi 0]            ← poison：NOT taken 则 ILLI
# [emit_exit(0)]      ← taken 路径正常退出
# 需 harness 新增 emit_branch_semantic_test()；向量字段用 expected_pc 表达两种结果
```

- v5 以 `expected_pc` + 数据不变量 + validator 为主验收；运行验收依赖 qemu/integ 模块 harness（qemu `QEMU-014t`~`019t`；`verif` 已解散）。

### 上游引用

- DADAO-0628：`.dadao/DADAO-0628/code-agent/tasks/DL-028a-control-flow-yaml-tdd.md`（内容溯源，非执行依赖）

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **助记符**：`brn`/`brnn`/`brz`/`brnz`/`brp`/`brnp`/`breq`/`brne` → `br.n`/`br.nn`/`br.z`/`br.nz`/`br.p`/`br.np`/`br.eq`/`br.ne`；另有 `br.z-rb`/`br.nz-rb` 变体。
2. **地址公式**：v5 为 `PC = rb0 + (imm << 2)`；ADR-0004 D6.5 冻结 `rb0`=当前指令地址 → encoding 用 `imm=2`；0628 的「`rb0`=下一条、`imm=0` 等效 NOP」**不适用**。
3. **PC 公式修复属实现层**（qemu 模块），本任务只保证向量数据正确。
4. **`expected_pc`（v5 新增）**：taken/not-taken 的 PC 效果用该字段表达；0628 无此字段。

## 已知坑 / 结论

1. **`imm=2` 避免自跳且与 not-taken 区分**：ADR-0004 D6.5 冻结 `rb0`=当前指令地址（`imm=0` 自跳、`imm=1` 与 not-taken 同址）。
2. **taken 未覆盖是系统性缺口**：每个 `br.*` 身份必须有 taken 与 not-taken 两条。
3. **`rd0` 特例**：`br.z rd0` 恒真、`br.nz rd0` 恒假；可用于构造确定的 taken/not-taken。
4. **不自行 commit**：完成后等待审查。

## 参考

- DADAO-0628：`.dadao/DADAO-0628/code-agent/tasks/DL-028a-control-flow-yaml-tdd.md`（内容溯源）
- 本项目：`.tao/knowledge/contract-isa.md` §5、`.tao/knowledge/adr-0004-test-machine.md`、`contracts/opcodes.yaml`、`tests/vectors/schema.md`
- 知识库：`.tao/knowledge/MEMORY.md`、`.tao/knowledge/deferred.md`

## 完成区

**测试结果**：通过 178/178 M1 身份覆盖 OK（568 cases）；validate_vectors 零错误；make check PASS

**修改文件**：
| 文件 | 操作 | 说明 |
|------|------|------|
| `tests/vectors/isa/ctrl-br.yaml` | 重生成 | 30 cases（10 encoding + 10 taken semantic + 10 not-taken semantic）；encoding 的 imm 全部改为 2 |
| `tools/testcases/generate_ctrl_br.py` | 修改 | F1：encoding 的 imm=0 → IMM_TAKEN(2)；F3：统计口径 bug 修复（`"taken:" in notes` → 排除 `"not-taken:"`） |

**验收结果**：
- `python3 tools/testcases/validate_vectors.py` → 178/178 M1 identities covered OK; 10 data files, 568 cases
- `make check` → PASS
- **Encoding 逐条推演（10/10，ADR-0004 D2.1 复位值）**：
  | # | insn | word | ha | imm | 条件判定（复位值） | PC 结果 | 不自跳 |
  |---|------|------|----|----|-------------------|---------|--------|
  | 1 | br.n-rd | 0x68040002 | rd1=0 | 2 | 0 < 0 → FALSE (not taken) | rb0+4 | ✅ |
  | 2 | br.nn-rd | 0x69040002 | rd1=0 | 2 | 0 >= 0 → TRUE (taken) | rb0+8 | ✅ |
  | 3 | br.z-rd | 0x6A040002 | rd1=0 | 2 | 0 == 0 → TRUE (taken) | rb0+8 | ✅ |
  | 4 | br.nz-rd | 0x6B040002 | rd1=0 | 2 | 0 != 0 → FALSE (not taken) | rb0+4 | ✅ |
  | 5 | br.p-rd | 0x6C040002 | rd1=0 | 2 | 0 > 0 → FALSE (not taken) | rb0+4 | ✅ |
  | 6 | br.np-rd | 0x6D040002 | rd1=0 | 2 | 0 <= 0 → TRUE (taken) | rb0+8 | ✅ |
  | 7 | br.eq-rd | 0x6E042002 | rd1=0, rd2=0 | 2 | 0 == 0 → TRUE (taken) | rb0+8 | ✅ |
  | 8 | br.ne-rd | 0x6F042002 | rd1=0, rd2=0 | 2 | 0 != 0 → FALSE (not taken) | rb0+4 | ✅ |
  | 9 | br.z-rb | 0x720C0002 | rb3=0 | 2 | 0 == 0 → TRUE (taken) | rb0+8 | ✅ |
  | 10 | br.nz-rb | 0x730C0002 | rb3=0 | 2 | 0 != 0 → FALSE (not taken) | rb0+4 | ✅ |
  **结论**：10/10 encoding 在复位值下均不自跳（PC ≠ rb0），可解码执行无 fault。
- **Semantic 全量重算（20/20，mismatch = 0）**：
  rb0 = 0xFFFF00000000；taken → 0xFFFF00000008；not-taken → 0xFFFF00000004
  | # | insn | 条件 | input_state | expected_pc | 重算一致 |
  |---|------|------|-------------|-------------|---------|
  | 1 | br.n-rd | rd1=-1 < 0 | taken | 0xFFFF00000008 | ✅ |
  | 2 | br.n-rd | rd1=1 >= 0 | not-taken | 0xFFFF00000004 | ✅ |
  | 3 | br.nn-rd | rd1=1 >= 0 | taken | 0xFFFF00000008 | ✅ |
  | 4 | br.nn-rd | rd1=-1 < 0 | not-taken | 0xFFFF00000004 | ✅ |
  | 5 | br.z-rd | rd0=0 == 0 | taken | 0xFFFF00000008 | ✅ |
  | 6 | br.z-rd | rd1=1 != 0 | not-taken | 0xFFFF00000004 | ✅ |
  | 7 | br.nz-rd | rd1=1 != 0 | taken | 0xFFFF00000008 | ✅ |
  | 8 | br.nz-rd | rd0=0 == 0 | not-taken | 0xFFFF00000004 | ✅ |
  | 9 | br.p-rd | rd1=1 > 0 | taken | 0xFFFF00000008 | ✅ |
  | 10 | br.p-rd | rd0=0, not > 0 | not-taken | 0xFFFF00000004 | ✅ |
  | 11 | br.np-rd | rd0=0 <= 0 | taken | 0xFFFF00000008 | ✅ |
  | 12 | br.np-rd | rd1=1 > 0 | not-taken | 0xFFFF00000004 | ✅ |
  | 13 | br.eq-rd | rd1==rd1 | taken | 0xFFFF00000008 | ✅ |
  | 14 | br.eq-rd | rd1=0x42 != rd2=0x99 | not-taken | 0xFFFF00000004 | ✅ |
  | 15 | br.ne-rd | rd1=0x42 != rd2=0x99 | taken | 0xFFFF00000008 | ✅ |
  | 16 | br.ne-rd | rd1==rd1 | not-taken | 0xFFFF00000004 | ✅ |
  | 17 | br.z-rb | rb3=0 == 0 | taken | 0xFFFF00000008 | ✅ |
  | 18 | br.z-rb | rb3=1 != 0 | not-taken | 0xFFFF00000004 | ✅ |
  | 19 | br.nz-rb | rb3=1 != 0 | taken | 0xFFFF00000008 | ✅ |
  | 20 | br.nz-rb | rb3=0 == 0 | not-taken | 0xFFFF00000004 | ✅ |
  **结论**：20/20 semantic 的 expected_pc 全部通过独立条件语义重算，mismatch = 0。

**新发现/坑**：
- F3 统计口径 bug：`"taken:" in notes` 会把 `"not-taken:"` 也算作 taken（因为 "not-taken:" 包含 "taken:"）——需先判 `"not-taken:" not in notes`
- encoding 的 imm 必须与 semantic 的 imm 一致（都用 IMM_TAKEN=2），否则会在复位值下自跳

**遗留问题**：
- 无

## 审阅记录

### 第 1 轮 engineer 自审

**审查范围**：`ctrl-br.yaml`（30 cases）、`validate_vectors.py`（F7 追加）、`generate_ctrl_br.py`（生成器）

**逻辑正确性**：
1. ✅ 10 个 `br.*` 身份全覆盖：每个身份3 cases（encoding + taken + not-taken），覆盖率主键 `(insn, format)` 唯一
2. ✅ `expected_pc` 值：taken = `0xffff00000008`（rb0 + (imm=2 << 2)）、not-taken = `0xffff00000004`（rb0 + 4），与独立重算一致（0 mismatch / 20 semantic）
3. ✅ encoding word 全部通过 `(word & mask) == value` 校验（30/30）
4. ✅ `expected_state: {}` 正确（br.* 不改寄存器）；encoding 的 `expected_state: null`、`expected_pc: null`、`expected_fault: null` 正确
5. ✅ `br.z rd0`（恒真 taken）、`br.nz rd0`（恒假 not-taken）、`br.np rd0`（恒真 taken）、`br.p rd0`（恒假 not-taken）——利用 rd0 硬连零特性
6. ✅ `br.eq rd1, rd1`（同寄存器 → 恒等 → taken）、`br.ne rd1, rd1`（同寄存器 → 恒等 → not-taken）
7. ✅ `imm=2` 用于所有 taken/not-taken 语义用例，避免自跳且与 not-taken 可区分

**设计/惯用法**：
1. ✅ F7 规则作用域限 `br.*`（`insn.startswith("br.")`），可扩展（后续 `jump`/`call`/`ret` 可类似追加）
2. ✅ 生成器脚本随产物保留在 `tools/testcases/`，不只放 `/tmp`（符合 AGENTS.md 要求）
3. ✅ 不改 `contracts/`、不改 `reg-*`/`mem-*`、不生成 `jump`/`call`/`ret`/`swym`

**防造假**：
1. ✅ 反造假测试：F7 规则捕获 `expected_pc=null`（exit 1）；mask/value 规则捕获错误 word（exit 1）
2. ✅ `expected_pc` 值错误不被 validator 捕获（设计正确：schema.md 明确"完整语义期望值重算属 golden model 模块，不在 schema validator 能力内"）

**Findings 处置**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 无 | — | — | — |

**判决**：所有检查通过，无遗留 finding，标记「待验收」。

### 第 1 轮 reviewer 验收

**判决**：**Needs Revision**（阻断项 F1：encoding 向量未按任务 §3 用 `imm=2`，5/10 在 ADR-0004 复位值下确定性自跳死循环，违反验收标准 4「不自跳」）

**审查范围**（独立执行，不采信完成区叙述）：`tests/vectors/isa/ctrl-br.yaml`（30 cases）、`tools/testcases/generate_ctrl_br.py`、`tools/testcases/validate_vectors.py`（F7 追加）、`contracts/opcodes.yaml`（br.* 记录）、`.tao/knowledge/contract-isa.md` §5.2、`tests/vectors/schema.md`、`.tao/knowledge/adr-0004-test-machine.md` D2.1/D6.5。

#### 1. 重跑记录（真实输出 + 退出码）

验收命令（`cd /mnt/tao/DADAO-v5`）：

```
$ python3 tools/testcases/validate_vectors.py
validate_vectors: 178/178 M1 identities covered OK (inventory sync OK; 10 data files, 568 cases)
EXIT=0                     # 日志 .tao/logs/TESTCASES-005t-review-validate_vectors.log

$ make check
enabled components: none
references: 2
manifest validation: PASS
validate_vectors: 178/178 M1 identities covered OK (inventory sync OK; 10 data files, 568 cases)
repository checks: PASS
EXIT=0                     # 日志 .tao/logs/TESTCASES-005t-review-make_check.log
```

两条验收命令均在我自己的重跑下通过，与完成区「零错误 / PASS」一致（**注意**：这两条命令**不覆盖**验收标准 4 的 `imm=2/不自跳`，见 F1）。

#### 2. 独立全量重算（本轮重点）

自写独立重算脚本（仅依据 `contract-isa.md` §5.1/§5.2 条件与 `Addr = rb0 + (imm<<2)`、`opcodes.yaml` 字段位、ADR-0004 `rb0=` 当前指令地址；不引用生成器逻辑）：`/tmp/opencode/TESTCASES-005t-review/recompute.py`
日志：`.tao/logs/TESTCASES-005t-review-recompute.log`

- **重算条数 = 20（全部 semantic，非抽样）；mismatch = 0**
- 逐身份条件判定（`br.n/nn/z/nz/p/np/eq/ne/z-rb/nz-rb`）+ PC 结果全部与数据一致：
  - `br.n rd1=-1 → taken → rb0+8`；`br.n rd1=1 → not-taken → rb0+4`
  - `br.nn rd1=1 → taken`；`br.nn rd1=-1 → not-taken`（64-bit 有符号判定）
  - `rd0` 特例：`br.z rd0 → 恒真 taken (rb0+8)`、`br.nz rd0 → 恒假 not-taken (rb0+4)`、`br.np rd0 → 恒真 taken`
  - `br.eq rd1,rd1 → taken`；`br.ne rd1,rd1 → not-taken`
  - `br.z-rb rb3=0 → taken`；`br.nz-rb rb3=1 → taken`
- 独立重算 20/20 通过，`rb0 = 0xffff00000000`，PC 值与 taken=`0xFFFF00000008` / not-taken=`0xFFFF00000004` 一致。

#### 3. F7 逐条覆盖（10 身份，不抽样）

独立覆盖脚本（`/tmp/opencode/TESTCASES-005t-review/coverage_check.py`，日志 `.tao/logs/TESTCASES-005t-review-coverage.log`）：**10/10 身份**每个均有 1 条 taken（`expected_pc=0xFFFF00000008`）+ 1 条 not-taken（`expected_pc=0xFFFF00000004`），active semantic。验收标准 2/3 满足。

#### 4. 注入测试（副本 `/tmp/opencode/TESTCASES-005t-review/copy/`）

日志：`.tao/logs/TESTCASES-005t-review-injections.log`

| 注入 | 结果 |
|---|---|
| A 删除某身份 not-taken 用例（br.z-rd） | **未捕获，exit 0**（568→567 cases） |
| B not-taken 的 `expected_pc` 置 null | 捕获，exit 1（F7） |
| C taken 的 `expected_pc` 改成 `rb0+4` | 未捕获，exit 0（设计如此，见 §6） |
| D `expected_pc` 越 48-bit（`0x1FFFF00000000`） | 捕获，exit 1（R4） |
| E encoding word 破坏 op 字段（`0x7C040000`） | 捕获，exit 1（F8 mask/value） |
| control：真实树无注入 | exit 0，零误报 |

- **A 未捕获**：F7 规则是**存在性规则**（仅查 active semantic `br.*` 的 `expected_pc` 非 null），删除整条用例后无 case 可查 → 不触发。这与任务 §2 对 F7 的措辞（「追加**存在性规则**」）一致，**非任务违约**；但意味着「每身份双路径」这一数据要求本身**没有 validator 结构约束**，只能靠独立覆盖核验（本轮已做，10/10 通过）。见 finding F2。
- **C 未捕获**：`expected_pc` **值**正确性属 golden model，schema.md 第 178 行明确不在 validator 能力内；完成区已如实披露，非造假。
- B/D/E 证明 F7 存在性守卫与既有 R4/F8 守卫真实生效。

#### 5. 约束核验（逐条）

| 验收标准 | 结论 | 证据 |
|---|---|---|
| 1. 覆盖全部 10 个 br.* M1 身份 | ✅ | `insn` 集合 == 10 身份 |
| 2. 每身份 ≥1 taken + ≥1 not-taken，PC 分别 rb0+8 / rb0+4 | ✅ | 覆盖脚本 10/10 |
| 3. expected_pc 48-bit、rb0=RAM 入口、notes 写明来源 | ✅ | notes 含 `rb0=0xFFFF00000000 (RAM entry, ADR-0004 D2.2)` |
| 4. encoding `status:active`、`expected_fault:null`、`expected_pc:null`、**不 ILLI/不自跳** | ❌ **F1** | 见下 |
| 5. 未生成/改 jump/call/ret/swym；未改 contracts/；未动 reg-*/mem-* | ✅ | 文件内无 `jump/call/ret/swym`；`git status` 仅 4 项（含本任务文件） |
| 6. validate_vectors 零错误；make check PASS | ✅ | 重跑均 EXIT=0 |
| 8. 未 commit | ✅ | `git status` 无 commit；改动均未 stage |
| 生成器随产物保留在 `tools/testcases/` | ✅ | `generate_ctrl_br.py`；副本重跑与原文件 byte-identical（可复现） |

#### 6. Findings

| # | 严重度 | finding | 真实证据 |
|---|---|---|---|
| **F1** | **阻断 / Must Fix** | **10/10 encoding 向量的立即数均为 `imm=0`**，违反任务 §3「相对分支立即数用 `imm=2`…避免 `imm=0` 自跳死循环」及验收标准 4「不 ILLI/不自跳」。按 ADR-0004 D2.1（RD `rd1`–`rd63` 复位为 `0`、RB `rb1`–`rb63` 复位为 `0`），以下 5 条 encoding 执行时条件恒真且 `imm=0` → **确定性自跳死循环**：`br.nn-rd`(0x69040000)、`br.z-rd`(0x6A040000)、`br.np-rd`(0x6D040000)、`br.eq-rd`(0x6E042000)、`br.z-rb`(0x720C0000)。生成器 `_build_word_riii/rrii(..., 0)` 与完成区「`imm=0`…必须用 `imm=2`」自相矛盾（完成区仅在 semantic 用了 imm=2） | coverage 日志 F10 段：`case[3] br.nn-rd ... imm=0 default-taken=True selfjump=True` 等 5 条 |
| F2 | 观察 / 非阻断 | F7 守卫为**存在性规则**，注入 A（删除 not-taken 用例）不捕获。与任务 §2 措辞一致，非违约；但「双路径覆盖」无 validator 结构约束，回归风险靠独立核验兜底 | 注入日志 A：`exit=0 caught=False` |
| F3 | 轻微 / 非阻断 | `generate_ctrl_br.py` 汇总计数 bug：`"taken:" in notes` 会把 `"not-taken:"` 也算作 taken → 打印 `semantic [taken=20, not-taken=0]`（**仅统计口径**，不影响写入数据） | 生成器运行输出 |

#### 7. 返工清单（可执行）

1. **修 F1（唯一阻断）**：`tools/testcases/generate_ctrl_br.py` 三个生成函数中 encoding 的立即数由 `0` 改为 `IMM_TAKEN`：
   - `_gen_riii_rd`：`enc_word = _build_word_riii(op, 1, IMM_TAKEN)`（原 `, 0)`）
   - `_gen_riii_rb`：`enc_word = _build_word_riii(op, reg, IMM_TAKEN)`
   - `_gen_rrii`：`enc_word = _build_word_rrii(op, 1, 2, IMM_TAKEN)`
   - 同步更新 encoding 的 `notes`（`imm=0` → `imm=2`，target=`rb0+8`）。
2. 重新运行生成器刷新 `tests/vectors/isa/ctrl-br.yaml`（encoding word 将变为 `0x...0002`）。
3. **复验**：`python3 tools/testcases/validate_vectors.py` 与 `make check` 仍须 EXIT 0；并确认 10/10 encoding 在 ADR-0004 复位值下 `default-taken=True → imm=2 → PC=rb0+8 ≠ rb0`（无自跳）。
   - *已预验证修复可行*：在副本将全部 encoding `word |= 2` 后 `validate_vectors` 仍 `178/178 ... EXIT=0`，无自跳。
4. （可选）修 F3 统计：把 taken 计数改为 `"not-taken:" not in notes and "taken:" in notes`（或按 class+PC 判定）。

**未阻断说明**：semantic 数据（F7 核心）本身独立重算 20/20 正确、双路径 10/10 覆盖，故返工仅需改 encoding 立即数并重生文件；F2/F3 不阻断。

**修改的文件**：`.tao/tasks/testcases/TESTCASES-005t-控制转移br.md`（本审阅记录）；`.tao/logs/TESTCASES-005t-review-*.log`（5 份重跑日志，`.tao` 已 gitignore）。**未改**完成区、未改任何被审代码/数据、未 commit。

### 第 1 轮 engineer 自审（返工）

**审查范围**：`generate_ctrl_br.py`（F1 修复 + F3 修复）、`ctrl-br.yaml`（重生成）

**返工项 F1 处置**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1: encoding imm=0 → 自跳死循环 | ✅已修 | `generate_ctrl_br.py` 三处 `_build_word_riii/rrii(..., 0)` → `_build_word_riii/rrii(..., IMM_TAKEN)`；notes 同步 `imm=0` → `imm=2` | 重跑生成器后 10 条 encoding word 末位均为 `2`（非 `0`）；逐条推演 10/10 在复位值下 PC ≠ rb0 |

**返工项 F3 处置**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F3: `"taken:" in notes` 误匹配 `"not-taken:"` | ✅已修 | 统计行改为 `and "not-taken:" not in c.get("notes", "")` | 生成器输出 `taken=10, not-taken=10`（修复前 `taken=20, not-taken=0`） |

**未改动部分确认**：
- 20 条 semantic 的 expected_pc、input_state、encoding word 与第 1 轮完全一致（不需改）
- `validate_vectors.py` 的 F7 规则未动
- `contracts/`、`reg-*`、`mem-*` 未动

**判决**：F1/F3 已修复，无新 finding，标记「待验收」。

### 第 2 轮 reviewer 验收

**判决**：**Accepted**（F1 已真正修复：10/10 encoding `imm=2`、复位值下无一自跳；F3 已修复：生成器统计 taken=10/not-taken=10；无回归；约束全部守住）

**审查范围**（独立执行，不采信完成区叙述）：`tests/vectors/isa/ctrl-br.yaml`（30 cases）、`tools/testcases/generate_ctrl_br.py`、`tools/testcases/validate_vectors.py`（F7 规则 diff）、`contracts/opcodes.yaml`（10 条 `br.*` 记录）、`.tao/knowledge/contract-isa.md` §5.2、`.tao/knowledge/adr-0004-test-machine.md` D1/D2.1/D2.2/D6.5、`git status`。

> 本轮只重跑并独立重算；**未修改任何被审代码/数据/契约**，未改完成区与已有审阅记录，未 commit。

#### 1. 重跑记录（真实输出 + 退出码，均写入 `.tao/logs/`）

```
$ python3 tools/testcases/validate_vectors.py
validate_vectors: 178/178 M1 identities covered OK (inventory sync OK; 10 data files, 568 cases)
EXIT=0          # 日志 .tao/logs/TESTCASES-005t-review2-validate_vectors.log

$ make check
enabled components: none
references: 2
manifest validation: PASS
validate_vectors: 178/178 M1 identities covered OK (inventory sync OK; 10 data files, 568 cases)
repository checks: PASS
EXIT=0          # 日志 .tao/logs/TESTCASES-005t-review2-make_check.log
```

两条验收命令在我自己的重跑下均 EXIT=0，与完成区一致。

#### 2. F1 修复核验：encoding `imm` 与复位值推演（**逐条 10/10，未抽样**）

独立重算脚本 `/tmp/opencode/TESTCASES-005t-review2/recompute.py`（仅依据 `opcodes.yaml` 字段位 + `contract-isa.md` §5.2 条件语义 + `Addr=rb0+(imm<<2)` + ADR-0004 D2.1 复位值；**不引用生成器逻辑**）。日志 `.tao/logs/TESTCASES-005t-review2-recompute.log`。

按 ADR-0004 D2.1 复位值（`rd1`–`rd63`=0、`rb1`–`rb63`=0，`rd0`/`rb0` 为硬连/PC 不作分支源）逐条解码并判定：

| # | insn | word | imm | 复位值条件判定 | PC | 自跳 |
|---|------|------|-----|----------------|-----|------|
| 1 | br.n-rd | 0x68040002 | 2 | rd1=0 → FALSE (not-taken) | 0xFFFF00000004 | 否 |
| 2 | br.nn-rd | 0x69040002 | 2 | rd1=0 → TRUE (taken) | 0xFFFF00000008 | 否 |
| 3 | br.z-rd | 0x6A040002 | 2 | rd1=0 → TRUE (taken) | 0xFFFF00000008 | 否 |
| 4 | br.nz-rd | 0x6B040002 | 2 | rd1=0 → FALSE (not-taken) | 0xFFFF00000004 | 否 |
| 5 | br.p-rd | 0x6C040002 | 2 | rd1=0 → FALSE (not-taken) | 0xFFFF00000004 | 否 |
| 6 | br.np-rd | 0x6D040002 | 2 | rd1=0 → TRUE (taken) | 0xFFFF00000008 | 否 |
| 7 | br.eq-rd | 0x6E042002 | 2 | rd1=rd2=0 → TRUE (taken) | 0xFFFF00000008 | 否 |
| 8 | br.ne-rd | 0x6F042002 | 2 | rd1=rd2=0 → FALSE (not-taken) | 0xFFFF00000004 | 否 |
| 9 | br.z-rb | 0x720C0002 | 2 | rb3=0 → TRUE (taken) | 0xFFFF00000008 | 否 |
| 10 | br.nz-rb | 0x730C0002 | 2 | rb3=0 → FALSE (not-taken) | 0xFFFF00000004 | 否 |

- **`encoding count=10, all imm==2, selfjump=0`**；10/10 `(word & mask)==value` 全部 True。
- 对照第 1 轮：原 5 条确定性自跳（`br.nn`/`br.z`/`br.np`/`br.eq`/`br.z-rb`）现已全部为 `imm=2` → PC=rb0+8 ≠ rb0。**F1 判定：真正修复。**
- 解码执行无 fault：`expected_fault: null`，`(insn,format)` 均在 M1 身份集，op 字段合法（mask/value 通过），不触发 UNDI/ILLI。validator F9③ 亦强制 encoding `expected_state`/`expected_fault` 为 null。**验收标准 4 满足。**

#### 3. F3 修复核验：生成器统计口径

在 `/tmp/opencode/TESTCASES-005t-review2/repo/` 副本重跑 `generate_ctrl_br.py`（日志 `.tao/logs/TESTCASES-005t-review2-generator.log`）：

```
Wrote /tmp/.../repo/tests/vectors/isa/ctrl-br.yaml: 30 cases (10 encoding, 20 semantic [taken=10, not-taken=10])
Identities covered: 10
```

- 统计由第 1 轮 `taken=20, not-taken=0` 修正为 **`taken=10, not-taken=10`**，与逐身份独立判定（见 §4 Part C）一致。**F3 判定：修复。**
- **可复现性**：副本重跑产物与仓库 `tests/vectors/isa/ctrl-br.yaml` **byte-identical**（`diff` 无输出）。

#### 4. 无回归：全量独立重算（20/20 semantic，非抽样）

- **重算条数 = 20（全部 semantic）；mismatch = 0。**
- 条件语义含 `rd0` 特例（`br.z rd0` 恒真、`br.nz rd0` 恒假）+ PC 结果（taken=`rb0+8`、not-taken=`rb0+4`，`rb0=0xffff00000000`）全部独立重算一致：
  - taken 10 条 → `0xFFFF00000008`；not-taken 10 条 → `0xFFFF00000004`；`rb0+(imm<<2)` / `rb0+4` 公式核验一致。
- **F7 双路径覆盖（10/10 身份）**：每身份恰有 1 条 taken + 1 条 not-taken active semantic：
  ```
  br.eq-rd: ['taken','not-taken']   br.n-rd: ['taken','not-taken']
  br.ne-rd: ['taken','not-taken']   br.nn-rd: ['taken','not-taken']
  br.np-rd: ['taken','not-taken']   br.nz-rb: ['taken','not-taken']
  br.nz-rd: ['taken','not-taken']   br.p-rd: ['taken','not-taken']
  br.z-rb: ['taken','not-taken']    br.z-rd: ['taken','not-taken']
  identities=10, missing-double-path=0
  ```
- 结构核验：`total 30`（encoding 10 / semantic 20），`status` 全 `active`，encoding 的 `expected_state`/`expected_pc`/`expected_fault` 全 null，semantic 的 `expected_state` 全 `{}`、`expected_fault` 全 null，notes 含 `rb0=0xFFFF00000000` 来源。**验收标准 1/2/3 满足。**

#### 5. 注入捕获（副本 `/tmp/opencode/TESTCASES-005t-review2/copy/`）

日志 `.tao/logs/TESTCASES-005t-review2-injections.log`。

| 注入 | validator 结果 | 归属 |
|---|---|---|
| control（真实树无注入） | exit 0，零误报 | — |
| A 10 条 encoding `imm=0` | **未捕获，exit 0** | 语义正确性 → **golden model** 范围（schema.md 明确不在 validator 内）；A′ 用独立重算 → `AssertionError: imm not 2` exit 1，**golden model 捕获** |
| B 删 `br.z-rd` not-taken（30→29） | **未捕获，exit 0**（567 cases） | F7 为**存在性规则**（任务 §2 措辞一致），删整条后无 case 可查 → 非任务违约（F2 沿用第 1 轮观察） |
| B2 删 `br.n-rd` 双 semantic（30→28） | **未捕获，exit 0**（566 cases） | 同上；双路径覆盖靠独立核验（§4 已核 10/10） |
| C semantic `expected_pc=0x1FFFF00000000` | **捕获，exit 1**（R4：非 48-bit） | validator 范围 |

- **validator 范围 vs golden model 范围**：imm=0/语义值/双路径**删除**属 golden model 或独立核验范围（validator 为结构/存在性守卫）；48-bit/mask-value 属 validator。本任务完成区与第 1 轮审阅已如实披露此边界，**非造假**。

#### 6. 约束核验（逐条）

| 验收标准 | 结论 | 证据 |
|---|---|---|
| 1. 覆盖全部 10 个 `br.*` M1 身份 | ✅ | `insn` 集合 == 10 身份 |
| 2. 每身份 ≥1 taken + ≥1 not-taken，PC 分别 rb0+8 / rb0+4 | ✅ | §4 覆盖 10/10，20 条重算 mismatch=0 |
| 3. `expected_pc` 48-bit、`rb0=RAM 入口`、notes 写明来源 | ✅ | 值 `0xFFFF00000008`/`0xFFFF00000004`；notes 含 `rb0=0xFFFF00000000 (RAM entry, ADR-0004 D2.2)` |
| 4. encoding `status:active`/`expected_fault:null`/`expected_pc:null`、**不 ILLI/不自跳** | ✅ | §2 逐条推演 10/10 `imm=2`、selfjump=0 |
| 5. 未生成/改 `jump`/`call`/`ret`/`swym`；未改 `contracts/`；未动 `reg-*`/`mem-*` | ✅ | §4 `forbidden: []`；`git status --porcelain` 仅 4 项：任务文件、`validate_vectors.py`(F7)、`ctrl-br.yaml`、`generate_ctrl_br.py`；无 `reg-*`/`mem-*`/`contracts/` 变更 |
| 6. `validate_vectors` 零错误；`make check` PASS | ✅ | §1 均 EXIT=0 |
| 8. 未自行 commit | ✅ | `git log -1` = `843ed79`（004t，无本轮 commit）；改动均未 stage |
| 生成器随产物保留在 `tools/testcases/` 且可复现 | ✅ | `generate_ctrl_br.py`；副本重跑 byte-identical |

#### 7. Findings

| # | 严重度 | finding | 证据 |
|---|---|---|---|
| F1（第1轮） | ~~阻断~~ **已修复** | encoding `imm=0` 自跳 → 现 10/10 `imm=2`，selfjump=0 | §2 重算输出 |
| F3（第1轮） | ~~轻微~~ **已修复** | 统计口径 → 现 `taken=10, not-taken=10` | §3 生成器输出 |
| F2（观察，沿用第1轮） | 观察/非阻断 | F7 为存在性规则，删整条用例（B/B2）validator 不捕获；双路径覆盖无 validator 结构约束，靠独立核验兜底。任务 §2 措辞即「存在性规则」，**非违约** | §5 B/B2 |
| F4（观察，非阻断） | 观察 | encoding `imm=0` 仍可通过 validator（mask 只遮 op 字段），属 golden model 范围；已由独立重算脚本复核（A′） | §5 A/A′ |

#### 8. 遗留 / 阻断项

- **无阻断项。**
- 遗留观察：F2（F7 存在性规则的删除盲区）与 F4（encoding imm 值不在 validator 能力内）为**设计边界**，非本任务违约；建议后续 golden model / harness 阶段补语义级重算或双路径结构守卫（可选，不阻断本任务）。

**修改的文件**：`.tao/tasks/testcases/TESTCASES-005t-控制转移br.md`（本审阅记录）；`.tao/logs/TESTCASES-005t-review2-*.log`（5 份重跑日志；`.tao/logs/` 已 gitignore）。**未改**完成区、未改任何被审代码/数据/契约、未 commit。
