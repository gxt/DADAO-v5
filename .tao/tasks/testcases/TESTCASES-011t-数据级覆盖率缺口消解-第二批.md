# TESTCASES-011t: 数据级覆盖率缺口消解（第二批：cond-assign/imm-block/ctrl + 门控转严）

**模块**：testcases
**项目里程碑**：M1
**依赖**：`TESTCASES-010t`（010t 完成后本任务的基线 gap 计数更清晰）
**状态**：待开始

## 执行环境

**执行环境**：本地
**日志路径**：`.work/log/testcases/TESTCASES-011t-*.log`（验证命令的完整输出；不得用已废弃的 `.tao/logs/`）
**临时产物**：`/tmp/opencode/TESTCASES-011t/`

## 接口规范

- 输入：
  - `tests/vectors/isa/reg-cond-assign.yaml`、`reg-imm-block.yaml`、`ctrl-br.yaml`、`ctrl-jump.yaml`
  - `tests/vectors/inventory.md`
  - `contracts/legality_rules.yaml`、`contracts/opcodes.yaml`
  - `tools/testcases/generate_isa_vectors.py`（reg-cond-assign/reg-imm-block）
  - `tools/testcases/generate_ctrl_br.py`（ctrl-br）
  - `tools/testcases/generate_ctrl_jump_call_ret.py`（ctrl-jump）
  - `tools/testcases/validate_vectors.py`（门控转严 + validator 逻辑修复）
  - `.tao/knowledge/contract-isa.md`（§3.5 条件赋值、§3.6/§3.7 块赋值、§5.2 分支、§5.3 跳转）
  - `.tao/knowledge/adr-0004-test-machine.md`（地址图：UNMAPPED = `0x87`）
- 输出：
  - 修改后的 3 个生成器 + 重新生成的 4 个 YAML 文件
  - 更新的 `tests/vectors/inventory.md`（br.* `legality` → `—`、br.* `boundary` → `✓`）
  - 修改后的 `tools/testcases/validate_vectors.py`（gap 检测逻辑修复 + 门控转严）
- 约束：
  - **不改** `contracts/`、`spec/`、`tests/scripts/`、`components/`
  - **不改** `generate_mem_vectors.py`、`generate_misc.py`
  - 向量数据必须由**生成器**产出
  - 期望值必须**独立派生**自 `spec/` 与 `contract-isa.md`
  - 不自行 commit

## 背景

### 问题根源

紧接 `TESTCASES-010t`（消解 reg-arith/logic/shift-extend/compare 的 114 缺口），本任务处理剩余 **35 缺口** + 修复 validator 逻辑缺陷 + 门控转严。

### 目的

1. 消解本批次 35 个数据级覆盖率缺口
2. 修复 `validate_vectors.py` 的 gap 检测逻辑（`deferred <reason>` 被误计为缺口）
3. 将数据级覆盖门控从「只报不拦」改为「阻断（exit 1）」

### 缺口精确构成（本批次）

**现有缺口（010t 完成后剩余）**：

| 文件 | legality | boundary | overlap | 合计 |
|------|----------|----------|---------|------|
| `reg-cond-assign.yaml` | 5 | 0 | 5（deferred C-27） | 10 |
| `reg-imm-block.yaml` | 13 | 0 | 6 | 19 |
| `ctrl-br.yaml` | 10 | 0 | 0 | 10 |
| `ctrl-jump.yaml` | 1 | 0 | 0 | 1 |
| **合计** | **29** | **0** | **11** | **40** |

**处置后的变化**：

| 变化 | 数量 | 说明 |
|------|------|------|
| validator 修复（deferred 不计缺口） | −5 | 5 个 cs.* overlap `deferred C-27` 不再被误计 |
| br.* legality `✓` → `—` | −10 | 无 legality 规则适用（见判据 L-br） |
| br.* 新增 boundary `✓` | +10 | 跳到未映射地址 → UNMAPPED |
| **处置后总缺口** | **35** | 29−5−10+10 + (6 overlap 保持) = 19 legality + 10 boundary + 6 overlap |

**逐项分解**：

| 缺口 | 数量 | 处置 |
|------|------|------|
| reg-cond-assign legality（cs.*） | 5 | 补 active case（`rdhb=rd0` → ILLI） |
| reg-cond-assign overlap（cs.* deferred C-27） | 5 | **不补 case**；修 validator 使 `deferred` 不计 gap |
| reg-imm-block legality（块赋值 + rwii） | 13 | 补 active case |
| reg-imm-block overlap（块赋值） | 6 | 补 active overlap case |
| ctrl-br legality | 10 | **改 inventory `✓` → `—`**（无 legality 规则适用） |
| ctrl-br boundary（**新增**） | 10 | **补 active boundary case**（跳到未映射地址 → UNMAPPED） |
| ctrl-jump legality（jump-iiii） | 1 | 补 active case（IALIGN/UNMAPPED） |

## 逐条判据（机械形式）

### 判据 L-br（br.* legality → `—`，10 条）

**用户裁定（2026-09-21）**：`br.*` 的 `legality` 列 `✓` → **`—`（不适用）**。

**依据**：
- `contract-isa.md §5.2.2`：`br.cond` 目标 = `rb0 + (imms18 << 2)`，低 2 位**恒零**（编码保证）→ **不触发 IALIGN**
- `contract-isa.md §5.1`：跳转地址计算仅在**低 48 位**进行，溢出丢弃 → 不越界
- 分支指令不写寄存器、不访存 → 无 `rd_dest_rd0`/`data_malign` 等规则适用
- **无任何 `status: active` 的 legality 规则适用于 `br.*`**
- 主会话实测：`br.z rd0, -0x1000`（目标 = BINARY_BASE − 0x4000，未映射）→ exit `0x87`（UNMAPPED），说明**目标地址可越界但触发的是 UNMAPPED（boundary），不是 IALIGN（legality）**

**操作**：修改 `inventory.md` 中 10 个 `br.*` 行的 `legality` 列：`✓` → `—`。

**注意区分**：`jump-rrii`/`call-rrii` 的目标含 `+rdhb` ⇒ **可能不对齐** ⇒ 仍有 `instruction_align`（IALIGN）规则 ✓。**不要**把 `br.*` 与 `jump-rrii` 混为一谈。

### 判据 B-br（br.* boundary → `✓`，10 条新增）

**用户裁定**：`br.*` 补 `boundary` case——**跳到未映射地址 → UNMAPPED（`0x87`）**。

**依据**：
- `ADR-0004 D5`：`dadao_cpu_tlb_fill` 对 `MMU_INST_FETCH` 在地址未映射时返回 UNMAPPED
- 测试机 RAM = `0xFFFF_0000_0000`（16 MiB）；`rb0 = 0xFFFF_0000_0000`
- 构造：`imm = 负值且绝对值足够大` → `rb0 + (imm << 2)` 落在 RAM 之外 → UNMAPPED
- **注意**：imm 必须使目标落在**有效48位地址空间内但未映射**（如 `rb0 − 0x4000` = `0xFFFF_FFFF_C000`，超出 RAM 但仍在 48 位范围内）

**操作**：
1. 修改 `inventory.md` 中 10 个 `br.*` 行的 `boundary` 列：添加 `✓`
2. 修改 `generate_ctrl_br.py`：为每个 `br.*` 追加 boundary case（`expected_fault: UNMAPPED`）

### 判据 L（legality 缺口，19 条）

**reg-cond-assign（5 条：cs.n/z/p/eq/ne）**：
- `cs.*`（rrrr）受 `rd_dest_rd0`（`rdhb` 为 rd0 → ILLI）约束
- **判定：补 active legality case**

**reg-imm-block（13 条）**：
- `rd2rd`/`rb2rb`/`rb2rd`/`rd2rb`/`ra2rd`/`rd2ra`（orri）：受 `multi_immu6_zero`（`immu6=0` → ILLI）约束
- `ra2rd` 还受 `ra2rd_dest_rd0`（`rdhb=rd0` → ILLI）约束
- `set.zw-rd`/`set.ow-rd`/`set.zw-rb`/`or.w-rd`/`or.w-rb`/`andn.w-rd`/`andn.w-rb`（rwii）：受 `rd_dest_rd0`/`rb_dest_rb0` 约束
- **判定：全补 active legality case**

**ctrl-jump（1 条：jump-iiii）** —— **预检订正（2026-09-21，用户裁定：与 `br.*` 一致归 boundary）**：
- `jump-iiii`（iiii）目标 = `rb0 + (imms24 << 2)`（`contract-isa.md:744`）⇒ **恒 4 对齐** ⇒ **无 IALIGN**；`:747`「绝对跳转地址位宽为 48 位，不产生溢出」⇒ **无越界**
- 其**唯一** fault 路径 = 目标落**未映射地址** → **UNMAPPED**（主会话实测：`jump -0x1000` → `Expected UNMAPPED, got UNMAPPED` ✓）
- ⇒ **判定（与 `br.*` 一致）**：`inventory.md` 中 `jump-iiii` 的 `legality` 列 `✓` → **`—`（不适用）**；**`boundary` 列置 `✓` 并补 1 条 boundary case**（`expected_fault: UNMAPPED`，构造 imm 使目标落在 RAM 之外但在 48 位地址空间内）
- ⚠️ **不要**与 `jump-rrii` 混同：后者目标含 `+rdhb` ⇒ **可能不对齐** ⇒ 有 `instruction_align`（IALIGN）规则 ✓（其 legality case 已存在，非本任务缺口）

### 判据 O（overlap 缺口，6 条）

**6 个块赋值**（`rd2rd`/`rd2ra`/`ra2rd`/`rb2rb`/`rd2rb`/`rb2rd`，orri）：
- overlap case = 两条块赋值的范围有重叠
- **判定：补 active overlap case**

**5 个 cs.* overlap**（deferred C-27）：
- 已有 5 条 `status: deferred` 的 overlap case
- **不补新 case**；由 validator 修复处理（见下）

### 判据 V（validator 逻辑修复）

**问题**：`validate_vectors.py` 的 gap 检测把 `deferred <reason>` 也计为缺口（`DECL_NA` 集合不含 `deferred` 前缀），与消解定义矛盾。

**修复方案**：修改 `validate_vectors.py` 的 `declared_classes` 构建逻辑——只对**声明为 `✓`（或非 `deferred`/非 `—`/非 `n/a`）**的类计入 `declared_classes`。具体：在判定 `cells[ci].lower() not in DECL_NA` 之前，先检查该 cell 是否以 `deferred` 开头（不区分大小写）——若是，则跳过（不计入 `declared_classes`）。

**验证**：修复后 `cs.*` 的 5 个 overlap gap 不再出现；总 gap 计数减少 5。

**⚠ 须复核**：`inventory.md` 中**其它** `deferred <reason>` / `—` 声明是否也被误计——逐列核对，不得只改 `cs.*` 一处。

### 判据 G（门控转严）

**用户裁定**：gap 消解后把 `validate_vectors.py` 的数据级覆盖门控改为**阻断**（遇缺口 `exit 1`）。

**实现**：在 `validate_vectors.py` 的 gap 报告逻辑中，将 `if data_coverage_gaps:` 分支从「打印 stderr + 继续 exit 0」改为「打印 stderr + `sys.exit(1)`」。

**关键约束**：只对「声明为 `✓` 而无 active case」计缺口；`deferred <reason>` / `—` 不计（由判据 V 保证）。

**归属**：由本任务（`011t`）一并实现（与 validator 修复同文件）。

## 实现方式

> ⚠️ **生成器能力缺口（主会话预检发现）**：实测 `generate_ctrl_br.py` 的 legality/boundary 支持均为 **0**；`generate_ctrl_jump_call_ret.py` legality=16 但 **boundary=0**。⇒ 本任务须为这两个生成器**新增 boundary case 生成能力**（`br.*` 10 条 + `jump-iiii` 1 条，均 `expected_fault: UNMAPPED`）。可**镜像** `generate_isa_vectors.py`（boundary=30）或 `generate_mem_vectors.py` 的既有风格；`generate_isa_vectors.py` 已具备 boundary 能力（用于 6 条块赋值 overlap 与 13 条 legality）。


### 生成器修改

| 生成器 | 改动 |
|--------|------|
| `tools/testcases/generate_isa_vectors.py` | 为 reg-cond-assign 的 5 个 cs.* 追加 legality case；为 reg-imm-block 的 13 个 insn 追加 legality case；为 6 个块赋值追加 overlap case |
| `tools/testcases/generate_ctrl_br.py` | 为 10 个 `br.*` 追加 boundary case（`expected_fault: UNMAPPED`，目标地址在 RAM 之外）；不改 legality（inventory 已改 `—`） |
| `tools/testcases/generate_ctrl_jump_call_ret.py` | 为 `jump-iiii` 追加 legality case（`expected_fault: UNMAPPED`） |

### inventory.md 修改

| 行 | 列 | 变更 |
|----|-----|------|
| 10 个 `br.*`（L180–191） | `legality` | `✓` → `—` |
| 10 个 `br.*`（L180–191） | `boundary` | （空/—） → `✓` |

### validate_vectors.py 修改

1. **gap 检测逻辑修复**：`deferred` 前缀的 cell 不计入 `declared_classes`
2. **门控转严**：gap > 0 时 `sys.exit(1)`

### Legality case 构造规范

同 `010t`（每条只验证一条 fault 规则；`expected_state: null`；`expected_fault` 引用 `legality_rules.yaml`）。

### Boundary case 构造规范

- `br.*` boundary：`expected_fault: UNMAPPED`；`encoding.word` 使目标 = `rb0 + (imm << 2)` 落在 RAM 之外；`expected_state: null`
- 块赋值 overlap：`expected_state` 反映重叠写入的最终值（最后一次写入为准）

## 下发前预检（AGENTS.md 四项）

1. **任务书内部一致性**：目标（35 gap + validator fix + gate tightening）与范围/约束/验收一致。✅
2. **依赖链实际可用性**：依赖 `010t`（reg-arith 等 4 文件的 gap 已消解）；生成器可运行。✅
3. **验收可执行性**：全部 8 条验收标准「现在可跑」。✅
4. **与 spec/vectors 一致**：br.* boundary 依据 `ADR-0004 D5`（UNMAPPED）；jump-iiii legality 依据 `contract-isa.md §5.3`。✅

## 验收标准

1. **全部 gap = 0**：`python3 tools/testcases/validate_vectors.py` 输出 `data coverage gaps: 0` 且 exit 0。**现在可跑。**

2. **独立全量重算**：新增 case 的期望值须**独立重算**——legality `expected_fault` 对照 `legality_rules.yaml`；boundary `expected_fault` 对照 `ADR-0004 D5`；overlap `expected_state` 按最后一次写入手算。**不得以 validator 绿灯为唯一判据。现在可跑。**

3. **反例门控**：
   - 修改某条新增 case 的 `expected_fault` 为错误值 → validator 报错
   - 删除某条新增 active case → validator **exit 1**（转严后）
   - 注入一个 `✓` 声明但无 active case 的副本 → validator exit 1
   - **现在可跑**

4. **既有 597+ 条向量零破坏**：
   - `git diff tests/vectors/isa/` 核对：既有 case 内容未被修改
   - `python3 tools/testcases/009t-audit.py` 仍 exit 0
   - **现在可跑**

5. **门控转严生效**：
   - gap = 0 时 exit 0；gap > 0 时 exit 1
   - `deferred`/`—` 声明不计入 gap
   - **现在可跑**（注入反例验证）

6. **生成器一致性**：运行生成器 → `git diff` 确认产出一致。**现在可跑。**

7. **`make check` PASS**。**现在可跑。**

8. **未自行 commit**。**现在可跑。**

## 已知坑 / 教训

1. **`br.*` 与 `jump-rrii` 不可混为一谈**：`br.*` 目标恒 4 对齐（无 IALIGN）；`jump-rrii` 目标含 `+rdhb` 可能不对齐（有 IALIGN）。
2. **`br.*` boundary 的 UNMAPPED 依据**：`ADR-0004 D5`——`dadao_cpu_tlb_fill` 对 `MMU_INST_FETCH` 在未映射地址返回 UNMAPPED（`0x87`）。构造 imm 使目标落在 RAM 之外。
3. **overlap case 的 `expected_fault` 可为 null 或 ILLI**：validator 允许。
4. **块赋值 overlap 语义**：重叠写入的最终值 = 最后一次写入。
5. **`cs.*` overlap (C-27)**：已有 5 条 deferred case，不补新 case；由 validator 修复处理。
6. **生成器重生成会覆盖既有 case**：须确保包含全部既有 + 新增。
7. **validator 修复须全量复核**：不得只改 `cs.*` 一处，须逐列核对所有 `deferred`/`—` 声明。
8. **`mnemonic` vs `insn`**：生成器条件须用 `insn` 区分 bank 变体。

## 参考

- 本项目：`contracts/legality_rules.yaml`、`contracts/opcodes.yaml`、`.tao/knowledge/contract-isa.md`、`.tao/knowledge/adr-0004-test-machine.md`
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