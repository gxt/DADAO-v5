# TESTCASES-010t: 数据级覆盖率缺口消解（第一批：reg-arith/logic/shift-extend/compare）

**模块**：testcases
**项目里程碑**：M1
**依赖**：`TESTCASES-009t`
**状态**：待开始

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
- 审计记录：`.tao/knowledge/testcases-009t-audit.md`
- 工具：`tools/testcases/validate_vectors.py`、`tools/testcases/009t-audit.py`
- 知识库：`.tao/knowledge/MEMORY.md`、`.tao/knowledge/deferred.md`

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

（按轮次追加，每次返工新增一轮）