# TESTCASES-010t: 数据级覆盖率缺口消解（第一批：reg-arith/logic/shift-extend/compare）

**模块**：testcases
**项目里程碑**：M1
**依赖**：`TESTCASES-009t`
**状态**：已验证

## 执行环境

**执行环境**：本地
**日志路径**：`.work/log/testcases/TESTCASES-010t-*.log`（验证命令的完整输出；不得用已废弃的 `.tao/logs/`）
**临时产物**：`/tmp/opencode/TESTCASES-010t/`

## 接口规范

- 输入：
  - `tests/vectors/isa/reg-arith.yaml`、`reg-logic.yaml`、`reg-shift-extend.yaml`、`reg-compare.yaml`
  - `tests/vectors/inventory.md`（M1 覆盖矩阵）
  - `contracts/legality_rules.yaml`（24 条规则：18 active + 6 deferred）
  - `contracts/opcodes.yaml`（178 M1 身份）
  - `tools/testcases/generate_isa_vectors.py`（生成 6 个 `reg-*` 文件；本任务只影响其中 4 个）
  - `tools/testcases/validate_vectors.py`（数据级覆盖门控）
  - `.tao/knowledge/contract-isa.md`（ISA 合约，§3 数据类）
  - `.tao/knowledge/adr-0004-test-machine.md`（测试机地址图）
- 输出：
  - 修改后的 `tools/testcases/generate_isa_vectors.py`（追加 legality case 生成逻辑 + `add.si-rd`/`add.si-rb` 的 boundary case）
  - 重新生成的 `reg-arith.yaml`、`reg-logic.yaml`、`reg-shift-extend.yaml`、`reg-compare.yaml`
  - `tests/vectors/inventory.md`（无变化——本批次所有缺口均补 active case，不降级）
- 约束：
  - **不改** `contracts/`、`spec/`、`tests/scripts/`、`components/`
  - **不改** `generate_ctrl_br.py`、`generate_ctrl_jump_call_ret.py`、`generate_mem_vectors.py`、`generate_misc.py`（归 `011t`）
  - **不改** `validate_vectors.py`（门控转严归 `011t`）
  - 向量数据必须由**生成器**产出（生成器已入 `tools/testcases/`）
  - 期望值必须**独立派生**自 `spec/` 与 `contract-isa.md`
  - 不自行 commit

## 背景

### 问题根源

`TESTCASES-009t` 建立了数据级覆盖率门控。当前 `inventory.md` 对 177 个 M1 身份声明 `legality` ✓，但 `isa/*.yaml` 中仅 36 个身份有 active legality case。`009t` 登记 154 缺口（原计数），经 validator 修正（`deferred C-27` 不计缺口）后为 **149 缺口**。

本任务处理第一批：**reg-arith / reg-logic / reg-shift-extend / reg-compare** 四个文件的缺口，共 **114 条**（全部为 legality 缺口 + 2 条 boundary 缺口，均补 active case）。

### 目的

消解本批次 114 个数据级覆盖率缺口：**全部补 active case**（无降级）。

### 缺口精确构成

| 文件 | legality | boundary | overlap | 合计 | 处置 |
|------|----------|----------|---------|------|------|
| `reg-arith.yaml` | 45 | 2 | 0 | 47 | 全补 active |
| `reg-logic.yaml` | 16 | 0 | 0 | 16 | 全补 active |
| `reg-shift-extend.yaml` | 40 | 0 | 0 | 40 | 全补 active |
| `reg-compare.yaml` | 11 | 0 | 0 | 11 | 全补 active |
| **合计** | **112** | **2** | **0** | **114** | |

**剩余 35 缺口**（reg-cond-assign 10 + reg-imm-block 19 + ctrl-br 10 + ctrl-jump 1，含 br.* 新增 boundary 10、减 cs.* deferred 5）归 `TESTCASES-011t`。

## 逐条判据（机械形式）

### 判据 L（legality 缺口，112 条）

对每个有 `legality` ✓ 但无 active legality case 的 `(insn, format)`：

1. **查 `contracts/legality_rules.yaml`**：逐条扫描 `status: active` 规则，检查该 insn 是否受约束。
2. **判定**：存在 ≥1 条 active 规则适用 → **补 active legality case**。

**本批次适用的规则**（全部 active，engineer 须逐条复核）：

| 规则 id | fault | 适用格式 | 本批涉及 insn 数 |
|---------|-------|---------|----------------|
| `rd_dest_rd0` | ILLI | orrr（单目的 rdhb）/rrii/riii | ~96（add/sub/mul/div/rem/cmp/and/or/xor/xnor/shl/shr/ext 全部位宽变体 + add.si-rd/rela.si-rb） |
| `dual_dest_both_rd0` | ILLI | rrrr（双目的） | 6（add.uo/so/sub.uo/so/mul.uo/so-rd） |
| `dual_dest_same_reg` | ILLI | rrrr | 同上 6 条（可与上行合并为一条 case 或各建一条） |
| `rb_dest_rb0` | ILLI | orrr/riii（rb 目的） | 4（add.so-rb/sub.so-rb/add.si-rb/rela.si-rb 中的 rb 变体） |
| `shamt_overflow` | ILLI | orrr/orri（shl/shr） | 已由 `003t` 的 encoding 语义隐含，但无独立 legality case——本批补 |
| `ext_bit_overflow` | ILLI | orrr/orri（ext） | 同上 |

**构造原则**：每条 legality case 只验证一条 fault 规则。优先用 `rd_dest_rd0`（最通用、构造最简：`rdhb=rd0`）。同一格式的 insn 可复用同一 fault 类型和构造模式。

### 判据 B（boundary 缺口，2 条）

1. **`add.si-rd`（riii）**：`rdha = rdha + sign_extend(imms18)`。boundary case = 溢出边界（如 `rdha = INT64_MAX, imms18 = 1` → 溢出但无 fault，验证 wrap-around 语义）。**补 active boundary case**。
2. **`add.si-rb`（riii）**：`rbha = rbha + sign_extend(imms18)`。同理。**补 active boundary case**。

## 实现方式

### 生成器修改

修改 `tools/testcases/generate_isa_vectors.py`：

1. **为每个 `(insn, format)` in reg-arith/logic/shift-extend/compute 追加 legality case**：
   - `class: legality`、`status: active`、`expected_fault: ILLI`
   - `encoding.word`：该 insn 的合法编码（从 `opcodes.yaml` 取 mask/value），但操作数违规（如 `rdhb=0`）
   - `input_state`：最小预置（`rdhb=rd0` 不需要预置；除零需要 `rdhd=0`）
   - `expected_state: null`
   - `spec_cite`：引用 `legality_rules.yaml` 对应规则
2. **为 `add.si-rd`/`add.si-rb` 追加 boundary case**：溢出边界的期望值按 `contract-isa.md` §3.1.3 手算。
3. **重新运行生成器**重生成全部 6 个 `reg-*` 文件（确保不丢失既有 case）。

### Legality case 构造规范

每个 legality case 必须包含：
- `class: legality`、`status: active`、`expected_fault: ILLI`
- `encoding.word`：可正常解码到该 insn 的编码（`(word & mask) == value`），但操作数字段违规
- `input_state`：使 fault 条件成立的最小预置
- `expected_state: null`
- `spec_cite`：引用 `legality_rules.yaml` 对应规则的 `spec_cite`
- `notes`：说明触发条件（如「rdhb=rd0 → ILLI (rd_dest_rd0)」）

### 生成器重生成注意事项

- 修改生成器后重跑会**覆盖**整个 YAML 文件
- 须确保生成器**包含全部既有 case + 新增 case**，不得丢失 `003t`~`009t` 的数据
- 验证方法：运行生成器 → `git diff` 确认既有 case 内容未变（只新增）

## 下发前预检（AGENTS.md 四项）

1. **任务书内部一致性**：目标（114 gap 全补 active）与范围（4 文件）、约束（不改其它生成器/validator）、验收（gap=0）一致。✅
2. **依赖链实际可用性**：依赖 `TESTCASES-009t`（已验证）；`generate_isa_vectors.py` 可运行；`validate_vectors.py` 可运行。✅
   - ⚠️ **能力缺口（主会话预检发现，须注意）**：`generate_isa_vectors.py` **当前完全没有 legality 支持**（实测 `grep -c legality` = **0**），且 `reg-arith.yaml` 现 **0 条 legality case**。⇒ 本任务须**先给该生成器新增 legality case 生成能力**；可**镜像**已有的实现：`generate_mem_vectors.py`（16 处 legality）、`generate_ctrl_jump_call_ret.py`（16 处）、`generate_misc.py`（11 处）。**不要**重造风格。
   - ⚠️ 同样注意：`generate_ctrl_br.py` 也 **0 处 legality**（属 `011t` 范围，本任务不碰）。
3. **验收可执行性**：全部 8 条验收标准「现在可跑」。✅
4. **与 spec/vectors 一致**：缺口来自 `validate_vectors.py` 实测输出（2026-09-21）；规则来自 `legality_rules.yaml`。✅

## 验收标准

1. **本批次 gap = 0**：`python3 tools/testcases/validate_vectors.py 2>&1` 中，来自 reg-arith/logic/shift-extend/compare 的 `DATA COVERAGE GAP` 行数 = 0。**现在可跑。**

2. **独立全量重算**：新增 114 条 case 的 `expected_fault` 须**独立重算**——逐条核对 `legality_rules.yaml` 对应规则的 `fault` 字段是否为 ILLI，boundary 期望值按 `contract-isa.md` 公式手算。**不得以 validator 绿灯为唯一判据。现在可跑。**

3. **反例门控**：
   - 修改某条新增 legality case 的 `expected_fault` 为 `null` → validator 报错（F9③ 守卫）
   - 删除某条新增 active case → `validate_vectors.py` gap 计数增加
   - **现在可跑**

4. **既有 597+ 条向量零破坏**：
   - `git diff tests/vectors/isa/` 核对：既有 case 内容未被修改（只新增）
   - `python3 tools/testcases/validate_vectors.py` 零错误
   - `python3 tools/testcases/009t-audit.py` 仍 exit 0
   - **现在可跑**

5. **生成器一致性**：运行生成器 → `git diff` 确认产出与任务修改一致。**现在可跑。**

6. **`make check` PASS**。**现在可跑。**

7. **未自行 commit**。**现在可跑。**

## 已知坑 / 教训

1. **`mnemonic` vs `insn`**：向量 YAML 的 `mnemonic` 是基础助记符（如 `add.si`），`insn` 是含 bank 后缀的完整标识（如 `add.si-rd`）。生成器条件须用 `insn`。
2. **legality case 不得有 `expected_state`**：validator F9② 强制 `legality.expected_state == null`。
3. **生成器重生成会覆盖既有 case**：须确保生成器包含全部既有 case + 新增 case。
4. **`orrr` 的 `rdhb` 是目的字段**（非 `rdha`）：`rd_dest_rd0` 规则作用于 `rdhb`。
5. **`add.so-rb`/`sub.so-rb` 的目的字段是 `rbhb`**：`rb_dest_rb0` 规则作用于 `rbhb`。

## 参考

- 本项目：`contracts/legality_rules.yaml`、`contracts/opcodes.yaml`、`.tao/knowledge/contract-isa.md`
- 审计记录：`docs/testcases-009t-audit.md`
- 工具：`tools/testcases/validate_vectors.py`、`tools/testcases/009t-audit.py`
- 知识库：`.tao/knowledge/MEMORY.md`、`.tao/knowledge/deferred.md`

## 完成区

**测试结果**：通过 7/7（gap=0、独立重算、反例门控×3、零破坏、生成器一致性、make check）

**修改文件**：
- `tools/testcases/generate_isa_vectors.py`（新增 `gen_legality_rd0` + `gen_riii_boundary_overflow` + `gen_cs_overlap_deferred` + `generate_file` 调用）
- `tests/vectors/isa/reg-arith.yaml`（+47 case：45 legality + 2 boundary）
- `tests/vectors/isa/reg-logic.yaml`（+16 case：16 legality）
- `tests/vectors/isa/reg-shift-extend.yaml`（+40 case：40 legality）
- `tests/vectors/isa/reg-compare.yaml`（+11 case：11 legality）
- 合计 +114 case（112 legality + 2 boundary），`git diff --numstat`：4 文件 1610 行纯新增，0 删除

**验收结果**：

### 1. 本批次 gap = 0

```
$ python3 tools/testcases/validate_vectors.py 2>&1 | grep "DATA COVERAGE GAP" | grep -E '\(add\.|sub\.|mul\.|div\.|rem\.|rela\.|and\.|or\.|xor\.|xnor\.|shl\.|shr\.|ext\.|cmp\.' | wc -l
0

$ python3 tools/testcases/validate_vectors.py 2>&1 | tail -2
DATA COVERAGE: 40 gap(s) found (inventory declares ✓ but no active data case); see above for details
validate_vectors: 178/178 M1 identities covered OK (inventory sync OK; 15 data files, 711 cases; data coverage gaps: 40)
```

40 残余 gap 全部来自范围外文件（reg-imm-block 19、ctrl-br 10、ctrl-jump 1、reg-cond-assign 10），归 `011t`。

### 2. 独立全量重算（三方一致性核对）

**核对方式**：逐条核对三方一致性——① `spec_cite` 引用的规则 id ↔ ② 实际违规字段的 bank（来自 `opcodes.yaml` 的 `fields[].role=dst`）↔ ③ `legality_rules.yaml` 该规则的 `fault`。**不止核 fault 值**。

```
All 112 legality cases pass 3-way consistency check:
  rule id ↔ dst field bank ↔ fault ✓
  spec_cite contains rule spec_cite ✓
  expected_state=null ✓
```

规则归属分布：`rd_dest_rd0` **102** / `dual_dest_both_rd0` 6 / `rb_dest_rb0` **4**（= 112）。
- `rb_dest_rb0` 4 条：`add.so-rb`、`sub.so-rb`、`add.si-rb`、`rela.si-rb`（dst 字段 `rbhb`/`rbha`，bank=rb）
- `dual_dest_both_rd0` 6 条：`add.uo-rd`/`add.so-rd`/`sub.uo-rd`/`sub.so-rd`/`mul.uo-rd`/`mul.so-rd`（rrrr 双目的）

3 条关键 case 逐条验证：
```
add.si-rb       rule=rb_dest_rb0     spec_cite=SimRISC-02 §自增自减; SimRISC-02 §rb0 为目的寄存器约定
rela.si-rb      rule=rb_dest_rb0     spec_cite=SimRISC-02 §PC相对寻址; SimRISC-02 §rb0 为目的寄存器约定
cmp.uo-rb       rule=rd_dest_rd0     spec_cite=SimRISC-02 §比较操作; SimRISC-01 §rd0 为目的寄存器约定
```

2 条 boundary：`add.si-rd`/`add.si-rb` 溢出边界，`rdha/rbha=0x7FFFFFFFFFFFFFFF (INT64_MAX)`，`imms18=1`，期望值 `0x8000000000000000 (INT64_MIN)`——按 `contract-isa.md §3.1.3` 公式 `rdha = rdha + sign_extend(imms18)` 独立手算：`0x7FFFFFFFFFFFFFFF + 1 = 0x8000000000000000`（64 位 wrap-around），`expected_fault=null`（无 fault）。

### 3. 反例门控

**① expected_fault → null**：
```
/mnt/tao/DADAO-v5/tests/vectors/isa/reg-arith.yaml case[4]: legality case must have non-null expected_fault
validate_vectors: FAILED (1 error(s))
```

**② 删除一条 active case → gap 增加**：
```
DATA COVERAGE: 41 gap(s) found
```
（从 40 → 41，and.orrr 新增一条 gap）

**③ 还原**：
```
$ python3 tools/testcases/generate_isa_vectors.py && python3 tools/testcases/validate_vectors.py | grep "gap(s)"
DATA COVERAGE: 40 gap(s) found
```
还原证据：`git diff tests/vectors/isa/reg-logic.yaml | grep "^-" | grep -v "^---" | wc -l` = 0（无删除行）。

### 4. 既有向量零破坏

```
$ git diff --stat tests/vectors/isa/
 tests/vectors/isa/reg-arith.yaml        | 672 ++++++++++++++++++++++++++++++++
 tests/vectors/isa/reg-compare.yaml      | 154 ++++++++
 tests/vectors/isa/reg-logic.yaml        | 224 +++++++++++
 tests/vectors/isa/reg-shift-extend.yaml | 560 ++++++++++++++++++++++++++
 4 files changed, 1610 insertions(+)
```

纯新增，0 删除。`validate_vectors.py` 零错误（178/178 covered）。`009t-audit.py` exit 0（0 mismatches，711 cases，704 active + 5 deferred）。

### 5. 生成器一致性（已修正）

**方案 (A) 落实**：将 `reg-cond-assign.yaml` 的 5 条 deferred overlap case（C-27）纳入生成器（`gen_cs_overlap_deferred`），使生成器成为全部 6 个 `reg-*.yaml` 的唯一来源。

```
$ python3 tools/testcases/generate_isa_vectors.py 2>&1 && git diff --stat tests/vectors/isa/
 tests/vectors/isa/reg-arith.yaml        | 672 ++++++++++++++++++++++++++++++++
 tests/vectors/isa/reg-compare.yaml      | 154 ++++++++
 tests/vectors/isa/reg-logic.yaml        | 224 +++++++++++
 tests/vectors/isa/reg-shift-extend.yaml | 560 ++++++++++++++++++++++++++
 4 files changed, 1610 insertions(+)
```

**全部 6 个 `reg-*.yaml`**：`reg-cond-assign.yaml` 和 `reg-imm-block.yaml` 的 `git diff` = 0（生成器产出与提交内容完全一致）。4 个目标文件仅新增 1610 行。

### 6. make check

```
$ make check 2>&1 | tail -2
validate_vectors: 178/178 M1 identities covered OK (inventory sync OK; 15 data files, 711 cases; data coverage gaps: 40)
repository checks: PASS
```

### 7. 未自行 commit

`git log --oneline -1` 仍为 `a57589f`（预检补记），未新增 commit。

**新发现/坑**：
1. **Python 子串匹配陷阱**：`"cs.n" in "cs.ne-rd"` 为 True，导致 `gen_cs_overlap_deferred` 中条件分支顺序必须先检查 `"cs.ne"`/`"cs.eq"` 再检查 `"cs.n"`。已修复并验证。
2. **insn 名 `-rb` 后缀不可靠**：`-rb` 可能指 RB 源操作数而非 RB 目的。`cmp.uo-rb` 的 `-rb` 指 `rbhc`/`rbhd`（RB 源），其**目的**字段是 `rdhb`（bank=rd）。`_get_illi_rule_id` 必须按 `opcodes.yaml` 的 `fields[].role=dst` 的 `bank` 路由，不可用 insn 名子串。已修复（改为查 `rec["fields"]`）。
3. **生成器覆盖范围**：`generate_isa_vectors.py` 重生成全部 6 个 `reg-*.yaml`。原先 `reg-cond-assign.yaml` 的 5 条 deferred overlap case（009t 手动添加）无法被生成器重现——本任务通过新增 `gen_cs_overlap_deferred` 函数解决，使生成器成为唯一来源。
4. `_build_word_orrr(rec, 0, 0, rdhd)` 在 `rdhb=0` 时仍能正确构造 encoding word（`ha` 字段来自 `rec["ha"]`，不受 `rdhb` 影响）。
5. `cmp.uo-rb`（orrr 格式）的目的字段是 `rdhb`（bank=**rd**），`-rb` 后缀指 RB 源操作数（`rbhc`/`rbhd`）。见 `contracts/opcodes.yaml`（`rdhb role=dst bank=rd`）与 `contract-isa.md §比较操作`（`cmp.uo rdhb, rbhc, rbhd`）。适用规则为 `rd_dest_rd0`，非 `rb_dest_rb0`。
6. `ext.*` 的 orri 格式中 `hd=0` 是合法的扩展起始位（0 ≤ N），不触发 `ext_bit_overflow`，可安全用作 legality case 的 encoding word。
7. `div`/`rem` 的 legality case 中 `rdhd=1`（非零除数），避免触发 `div_by_zero` 而非目标规则 `rd_dest_rd0`。

**遗留问题**：
- 40 残余 gap（reg-imm-block 19 + ctrl-br 10 + ctrl-jump 1 + reg-cond-assign 10）归 `TESTCASES-011t`。

## 审阅记录

### 第 1 轮 engineer 自审

**发现问题**：
1. `reg-cond-assign.yaml` 的 5 条 deferred overlap case 被生成器覆盖丢失，需 `git checkout` 恢复——违反验收 #5「生成器一致性」。
2. `gen_cs_overlap_deferred` 中 `"cs.n" in "cs.ne-rd"` 子串匹配导致 cs.ne 使用错误的 input_state。

**处置**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 生成器无法重现 reg-cond-assign.yaml | ✅已修 | 新增 `gen_cs_overlap_deferred` + `deferred_overlap` 列表收集 + 末尾 extend | `git diff tests/vectors/isa/reg-cond-assign.yaml` = 0 |
| cs.n/cs.ne 子串匹配 bug | ✅已修 | 条件分支重排序：先 cs.ne/cs.eq，后 cs.n | `git diff` 确认 cs.ne input_state 正确（rd1=0x2A, rd2=0x63） |

### 第 1 轮 reviewer 验收（reviewer 独立重跑）

**审查对象（未提交工作区）**：`tools/testcases/generate_isa_vectors.py` + `tests/vectors/isa/reg-{arith,logic,shift-extend,compare}.yaml`
**日志落盘**：`.work/log/testcases/TESTCASES-010t-review-*.log`（临时产物在 `/tmp/opencode/TESTCASES-010t/`）
**审查基线**：`git log --oneline -1` = `a57589f`（无新 commit，未 commit 成立）

#### 1. 重跑记录（reviewer 亲自执行，非工程师转述）

验收 #1（本批 gap = 0，整体 40）：
```
$ python3 tools/testcases/validate_vectors.py 2>&1 | tail -1     # exit=0
validate_vectors: 178/178 M1 identities covered OK (inventory sync OK; 15 data files, 711 cases; data coverage gaps: 40)
$ grep -c "DATA COVERAGE GAP" <log>          # 40
```
将 40 条 gap 的 `(insn,format)` 逐个回映射到其所属文件：
```
reg-imm-block.yaml  19
ctrl-br.yaml        10
reg-cond-assign.yaml 10
ctrl-jump.yaml       1
→ 4 个目标文件命中数 = 0
```
✅ **本批 gap = 0，整体 40，残余全部落在 011t 范围**（与任务书声明一致）。

验收 #4（零破坏）：
```
$ make check; echo exit=$?                          # exit=0
repository checks: PASS
$ python3 tools/testcases/009t-audit.py; echo exit=$?    # exit=0
Total cases: 711 (active: 704, deferred: 5)
Recomputed 320/322 active semantic/boundary/overlap cases: 0 mismatches.
$ git diff --numstat tests/vectors/isa/ tools/testcases/generate_isa_vectors.py
672  0  tests/vectors/isa/reg-arith.yaml
154  0  tests/vectors/isa/reg-compare.yaml
224  0  tests/vectors/isa/reg-logic.yaml
560  0  tests/vectors/isa/reg-shift-extend.yaml
148  0  tools/testcases/generate_isa_vectors.py
```
✅ 纯新增 1610/0，`validate_vectors` 零 error，`009t-audit` exit 0，`make check` PASS。

验收 #5（生成器一致性）：亲自跑生成器后 6 个 `reg-*.yaml` **逐字节不变**（`sha256sum` 前后 diff 为空）；把 `reg-cond-assign.yaml` 移走后重跑生成器，产出的文件与 `HEAD` 版本 **byte-identical**，随后哈希核验全部 OK：
```
$ python3 tools/testcases/generate_isa_vectors.py; diff <(sha256sum before) <(sha256sum after)   # 空
$ mv .../reg-cond-assign.yaml /tmp/... && python3 tools/testcases/generate_isa_vectors.py
$ diff .../reg-cond-assign.yaml <(git show HEAD:.../reg-cond-assign.yaml)   # 空 → REGENERATED==HEAD
```
✅ 方案 (A) 成立：5 条 deferred overlap case 可被生成器重现；`reg-cond-assign.yaml`/`reg-imm-block.yaml` 零改动；4 目标文件仍 1610/0。

验收 #6（子串 bug）：`cs.n/cs.z/cs.p/cs.eq/cs.ne` 的 deferred overlap `input_state` 各自正确——
`cs.n` rd1=`0xFFFF…FF`、`cs.z` rd1=`0`、`cs.p` rd1=`1`、`cs.eq` rd1=rd2=`0x2A`、`cs.ne` rd1=`0x2A`/rd2=`0x63`（**未**被 `cs.n` 前缀误匹配）。✅

验收 #7（范围）：`git diff --name-only` = 任务书 + `generate_isa_vectors.py` + 4 个目标 YAML；`validate_vectors.py`/其余生成器/`inventory.md` 均未改动。✅

验收 #2（独立全量重算）：见下节。

#### 2. 独立全量重算（逐条，不抽样）

判据来源：`contracts/opcodes.yaml`（身份 mask/value、`fields[].role/bank/bits`）、`contracts/legality_rules.yaml`（各规则 `fault`）、`contract-isa.md §3.1.3/§4.5.2`。脚本：`/tmp/opencode/TESTCASES-010t/recompute.py`（自行解析，**不调用**工程师生成器逻辑）。

结果：
```
新增 case：112 legality + 2 boundary = 114       （与任务书完全一致）
4 文件既有 case 被删除数 = 0                     （纯新增）
112 条 legality：word 均通过 (word & mask) == value；expected_fault 均 = ILLI；
                 status 均 active；expected_state 均 null
2 条 boundary（手算）：
  add.si-rd: 0x7FFFFFFFFFFFFFFF + sign_extend(1) = 0x8000000000000000  fault=null  ✓
  add.si-rb: 0x7FFFFFFFFFFFFFFF + sign_extend(1) = 0x8000000000000000  fault=null  ✓
```
**但发现 3 条 legality 的规则归属（`spec_cite`/`notes`）错误**：
```
[FAIL] reg-arith.yaml   add.si-rb /riii : 引用 rd_dest_rd0，实际违规字段 rbha=0（bank=rb）
         → 适用规则应为 rb_dest_rb0（opcodes.yaml legality: 'rbha != rb0'）
[FAIL] reg-arith.yaml   rela.si-rb/riii : 引用 rd_dest_rd0，实际违规字段 rbha=0（bank=rb）
         → 适用规则应为 rb_dest_rb0（opcodes.yaml legality: 'rbha != rb0'）
[FAIL] reg-compare.yaml cmp.uo-rb/orrr : 引用 rb_dest_rb0，实际违规字段 rdhb=0（bank=rd）
         → 适用规则应为 rd_dest_rd0（opcodes.yaml legality: 'rdhb != rd0'）
```
引用规则分布：`rd_dest_rd0` 103 + `dual_dest_both_rd0` 6 + `rb_dest_rb0` 3；
**应有**分布：`rd_dest_rd0` 102 + `dual_dest_both_rd0` 6 + `rb_dest_rb0` 4（rb 目的共 4 条：add.so-rb/sub.so-rb/add.si-rb/rela.si-rb）。
即 3 条被 `-rb` 子串路由到错误的规则：`_get_illi_rule_id` 对 `riii + -rb` 未识别 rb 目的；对 `orrr + cmp.uo-rb` 误判为 rb 目的。

**重复项判定**：这 3 条的 `expected_fault` 仍为 ILLI（两条规则 fault 都是 ILLI），故不会造成期望值错误；但违反「构造规范」——`spec_cite` 须引用**对应规则**、`notes` 须说明**实际触发条件**。这 3 条 `notes` 与其实际触发字段相矛盾。

**旁证**：`contracts/opcodes.yaml` 中 `cmp.uo-rb` 的 fs[0]=`ha`(minor_op)、`rdhb`(role=dst, **bank=rd**)、`rbhc`/`rbhd`(src, rb)；`contract-isa.md` 第 621 行 `cmp.uo rdhb, rbhc, rbhd`（写入 `rdhb`）——`-rb` 后缀指 **RB 源操作数**，目的仍是 RD。故完成区「坑」#4 的断言与 spec 相反。

#### 3. 反例门控（reviewer 亲自注入并还原）

① 把 `add.uo-rd` legality 的 `expected_fault` 改为 `null`：
```
$ python3 tools/testcases/validate_vectors.py; echo exit=$?     # exit=1
.../reg-arith.yaml case[4]: legality case must have non-null expected_fault
validate_vectors: FAILED (1 error(s))
```
② 删除 `add.uo-rd` 的 active legality case：
```
DATA COVERAGE GAP: (add.uo-rd, rrrr) declares 'legality' ... no active legality case
DATA COVERAGE: 41 gap(s) found            # 40 → 41
```
③ 还原（**含重建**）：重跑生成器 → `sha256sum -c canonical.sha256` 6/6 OK；gap 回到 40；`git diff --numstat` 回到 1610/0。
✅ 反例门控三支均有效、可失败、可复原。

#### 4. 约束核验（逐条）

| 硬约束 | 结论 | 证据 |
|--------|------|------|
| 只碰 1 生成器 + 4 YAML | ✅ | `git diff --name-only`（+ 任务书本身） |
| 不改 `validate_vectors.py` | ✅ | `git diff` 空 |
| 不改其它生成器/其它 YAML/`inventory.md` | ✅ | `git diff` 空；`reg-cond-assign`/`reg-imm-block` diff=0 |
| 向量由生成器产出 | ✅ | 重跑生成器 byte-identical |
| 期望值独立派生 | ⚠️ **未完全** | ILLI/边界值正确，但 3 条规则归属错误（见上） |
| 不自行 commit | ✅ | HEAD 仍 `a57589f` |
| 本批 gap=0 | ✅ | 40 条 gap 无一条属 4 目标文件 |
| 反例门控 | ✅ | 三支均复现 |
| 零破坏 | ✅ | 1610/0、audit exit 0、make check PASS |

#### 5. 完成区核对

- 修改文件清单、1610/0、gap=40、boundary 手算、反例门控、生成器一致性、make check、无 commit：**均与 reviewer 实测一致**。
- 验收 #5 结论已由「幂等」改为**真实**的「重跑生成器产物一致」结论 —— ✅ 该项问题已消除。
- **验收 #2 的方法不充分**：完成区只核 `expected_fault == ILLI`，未核「引用规则是否与违规字段匹配」，因此漏掉上述 3 条。
- **完成区「坑」#4 为错误陈述**：称 `cmp.uo-rb` 是「rb 目的」并称 `-rb` 路由正确。实测/spec 均表明其目的字段为 `rdhb`（RD bank）。此条掩盖了真实缺陷，违反「完成区结论须与真实输出逐条对齐」。

#### 6. 判决：**Needs Revision**

验收命令块中，验收 #1/#3/#4/#5/#6/#7 全部通过；**验收 #2「独立全量重算」不通过**：112 条中有 3 条的规则归属错误、`notes` 与实际触发字段矛盾。

**需修复项（具体、最小）**：

1. `tools/testcases/generate_isa_vectors.py` 的 `_get_illi_rule_id(insn, fmt)` 按 insn 名子串路由，改为**按 opcodes 记录的 dst 字段 bank** 路由，例如：
   ```python
   def _get_illi_rule_id(rec):
       if rec["format"] == "rrrr":
           return "dual_dest_both_rd0"
       banks = {f["bank"] for f in rec["fields"]
                if f.get("role") == "dst" and f.get("bank") in ("rd", "rb")}
       return "rb_dest_rb0" if "rb" in banks else "rd_dest_rd0"
   ```
   （调用处传入 `rec` 而非 `(insn, fmt)`。）
2. 重跑生成器；预期 `legality` 规则分布变为 `rd_dest_rd0` 102 / `dual_dest_both_rd0` 6 / `rb_dest_rb0` 4；`add.si-rb`/`rela.si-rb` 的 `notes`/`spec_cite` 改为 `rb_dest_rb0`，`cmp.uo-rb` 改为 `rd_dest_rd0`。
3. 修正完成区「坑」#4：如实记录 `cmp.uo-rb` 目的字段为 `rdhb`（RD bank，见 `contracts/opcodes.yaml` 与 `contract-isa.md` §比较操作/第 621 行），`-rb` 指 RB 源；并更正验收 #2 的核对方法（须核「引用规则 == 违规字段归属」，不止核 fault 值）。
4. 修复后复查：`git diff --numstat` 仍应 ≈1610/0（行数可能微调，但 0 删除）；gap 仍 40；`009t-audit` exit 0；`make check` PASS；6 文件生成器一致。

> 说明：本缺陷非设计层/路线层阻断，属实现细节；主目标（114 gap 消解、零破坏、生成器唯一来源）已达成，仅规则归属需订正。

### 第 2 轮 engineer 返工（规则归属修复）

**修复内容**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| `_get_illi_rule_id` 按 insn 名 `-rb` 子串路由，不可靠 | ✅已修 | 改为查 `rec["fields"]` 中 `role=dst` 的 `bank` 字段：`rb` → `rb_dest_rb0`，`rrrr` → `dual_dest_both_rd0`，其余 → `rd_dest_rd0` | 分布变为 102/6/4 ✓ |
| `add.si-rb` 引用 `rd_dest_rd0`（应为 `rb_dest_rb0`） | ✅已修 | `dst=rbha, bank=rb` → 路由到 `rb_dest_rb0` | `spec_cite` 含 `rb0 为目的寄存器约定` ✓ |
| `rela.si-rb` 引用 `rd_dest_rd0`（应为 `rb_dest_rb0`） | ✅已修 | 同上 | 同上 |
| `cmp.uo-rb` 引用 `rb_dest_rb0`（应为 `rd_dest_rd0`） | ✅已修 | `dst=rdhb, bank=rd` → 路由到 `rd_dest_rd0` | `spec_cite` 含 `rd0 为目的寄存器约定` ✓ |
| 完成区「坑」#4 错误陈述 | ✅已修 | 改写为如实描述 `cmp.uo-rb` 目的字段为 `rdhb`（RD bank），`-rb` 指 RB 源 | 见「坑」#5 |
| 验收 #2 方法不充分（只核 fault） | ✅已修 | 改为三方一致性核对：rule id ↔ dst field bank ↔ fault | 112 条全部通过 ✓ |

**修复后复验**：
```
Rule distribution: rd_dest_rd0=102, dual_dest_both_rd0=6, rb_dest_rb0=4 ✓
112 legality cases pass 3-way consistency check ✓
validate_vectors: 178/178, 40 gaps (target files gap=0) ✓
009t-audit: 0 mismatches ✓
make check: PASS ✓
git diff: 4 files, 1610 insertions(+), 0 deletions ✓
Generator consistency: 6 files all match ✓
Counter-example gate: 3/3 pass ✓
```

### 第 2 轮 reviewer 验收（复验第 1 轮 5 项 Needs Revision）

**基线**：`git log --oneline -1` = `a57589f`（未新增 commit）。日志：`.work/log/testcases/TESTCASES-010t-review2-*.log`。

#### 1. 三方一致性逐条（112 条，不抽样，0 不一致）

自写脚本 `review2_threeway.py`（仅读 `contracts/opcodes.yaml` + `contracts/legality_rules.yaml` + 向量文件，**不调用**工程师生成器）：对每条新 legality case 独立推导「应引规则」= 依据 `fields[].role=dst` 的 `bank`（rrrr → 双目的；dst bank=rb → `rb_dest_rb0`；否则 → `rd_dest_rd0`），与实际 `notes` 所引比对，并核该规则在 `legality_rules.yaml` 的 `fault`、`spec_cite` 文本是否落入 case 的 `spec_cite`：

```
new cases total: 114  legality: 112  boundary: 2
cited-rule distribution: {'dual_dest_both_rd0': 6, 'rd_dest_rd0': 102, 'rb_dest_rb0': 4}
inconsistencies: 0
  3-way consistency: ALL PASS (0 mismatch)
```
✅ **不一致数 = 0**；分布 **102/6/4**（= 112）；另全部 word `(word&mask)==value`、fault=ILLI、status=active、expected_state=null 均通过。
2 条 boundary 手算复核：`0x7FFFFFFFFFFFFFFF + sign_extend(1) = 0x8000000000000000`，fault=null ✓。

#### 2. 第 1 轮 5 条问题逐条确认

| # | 第 1 轮问题 | 当前状态 | reviewer 证据 |
|---|------------|---------|--------------|
| 1 | `add.si-rb`/`rela.si-rb` 应引 `rb_dest_rb0` | ✅已修 | 实测 word `0x5B000000`/`0x5A000000`，notes=「(rb_dest_rb0)」，spec_cite 含「§rb0 为目的寄存器约定」 |
| 2 | `cmp.uo-rb`（dst `rdhb`, bank=rd）应引 `rd_dest_rd0` | ✅已修 | word `0x40A40000`，notes=「(rd_dest_rd0)」，spec_cite 含「§rd0 为目的寄存器约定」 |
| 3 | 归属分布应为 102/6/4 | ✅已修 | 实测 `rd_dest_rd0` 102 / `dual_dest_both_rd0` 6 / `rb_dest_rb0` 4 |
| 4 | 完成区「坑」#4 错误陈述须订正 | ✅已修 | 「坑」#4 已删除，新增「坑」#5 如实写明 `cmp.uo-rb` 目的字段为 `rdhb`（bank=rd）、`-rb` 指 RB 源；「坑」#2 亦记录 `-rb` 后缀不可靠 |
| 5 | 验收 #2 自验方法过浅，须改三方一致性 | ✅已修 | 完成区 #2 标题改为「独立全量重算（三方一致性核对）」，明确 ① rule id ↔ ② dst field bank ↔ ③ fault，并注明「不止核 fault 值」 |

#### 3. 回归（reviewer 亲自重跑）

```
$ python3 tools/testcases/validate_vectors.py; echo exit=$?     # exit=0
validate_vectors: 178/178 M1 identities covered OK (inventory sync OK; 15 data files, 711 cases; data coverage gaps: 40)
# 40 条 gap 按目标文件回映射：reg-imm-block 19 / ctrl-br 10 / ctrl-jump 1 / reg-cond-assign 10；4 目标文件命中 0
$ python3 tools/testcases/009t-audit.py; echo exit=$?           # exit=0
Recomputed 320/322 active semantic/boundary/overlap cases: 0 mismatches.
$ make check; echo exit=$?                                       # exit=0
repository checks: PASS
$ git diff --numstat tests/vectors/isa/ tools/testcases/generate_isa_vectors.py
672  0 reg-arith.yaml / 154  0 reg-compare.yaml / 224  0 reg-logic.yaml / 560  0 reg-shift-extend.yaml / 153  0 generate_isa_vectors.py   （0 删除）
```
✅ 本批 gap=0 / 整体 40 / audit exit 0 / make check PASS / 纯新增 0 删除。

#### 4. 生成器一致性（验收 #5）

```
$ sha256sum tests/vectors/isa/*.yaml > before; python3 tools/testcases/generate_isa_vectors.py
Wrote reg-arith.yaml: 187 cases / reg-logic: 64 / reg-shift-extend: 160 / reg-compare: 33
Wrote reg-cond-assign.yaml: 15 cases / reg-imm-block.yaml: 26 cases
$ diff before after      # 空 → 6 个 reg-*.yaml BYTE-IDENTICAL
$ git diff --numstat .../reg-cond-assign.yaml .../reg-imm-block.yaml   # 空 → diff=0
```
✅ 亲自跑生成器后 6 文件逐字节不变；`reg-cond-assign.yaml`/`reg-imm-block.yaml` 零改动；4 目标文件仍 1610/0。

#### 5. 反例门控（三组，reviewer 亲自注入并还原）

```
① fault→null：  reg-arith.yaml case[4]: legality case must have non-null expected_fault
                validate_vectors: FAILED (1 error(s))            (exit=1)
② 删 case：     删除 xor.o 的 active legality → DATA COVERAGE: 41 gap(s) found  (40→41)
③ 还原(含重建)：重跑生成器 → sha256sum -c 15/15 OK → gap 回 40 → numstat 回 1610/0
```
✅ 三组均有效、可失败、可复原（还原后 `git diff` 哈希核验通过）。

#### 6. 范围 / 无 commit

`git diff --name-only` = 任务书 + `tools/testcases/generate_isa_vectors.py` + 4 个目标 YAML；`validate_vectors.py`/其它生成器/`inventory.md` 未改；HEAD 仍 `a57589f`。✅

#### 7. 判决：**Accepted**

第 1 轮 3 条规则归属错误全部修复（三方一致性 0 不一致，分布 102/6/4）；完成区错误陈述已订正、验收 #2 方法已改为三方一致性；回归全绿、生成器一致、反例门控三组有效、范围与「不 commit」均守住。
验收命令块在 reviewer 独立重跑下全部通过，无约束违反。主会话可将任务状态改为 `已验证`（最终接受仍由架构师终审）。

> 备注（非阻断，供 011t 参考）：本批 `shamt_overflow`/`ext_bit_overflow` 未生成独立 legality case，均以 `rd_dest_rd0`（rdhb=rd0）覆盖同一 `(insn,format)` 的身份缺口；符合任务「构造原则：优先用 rd_dest_rd0 / 每条只验证一条规则」，不构成缺口。`cmp.uo-rb` 的目的字段判定以 `contracts/opcodes.yaml` 的 `fields` 为准（`rdhb` role=dst bank=rd）。