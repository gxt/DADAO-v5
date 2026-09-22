# TESTCASES-011t: 数据级覆盖率缺口消解（第二批：cond-assign/imm-block/ctrl + 门控转严）

**模块**：testcases
**项目里程碑**：M1
**依赖**：`TESTCASES-010t`（010t 完成后本任务的基线 gap 计数更清晰）
**状态**：待验收

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

**测试结果**：通过 8/8；失败原因：无

**修改文件**：
- `tools/testcases/validate_vectors.py`：3 处改动（deferred 前缀检测 + 门控转严 sys.exit(1) + boundary 允许 UNMAPPED）
- `tools/testcases/generate_ctrl_br.py`：新增 boundary case 生成能力（10 条 br.* UNMAPPED）
- `tools/testcases/generate_ctrl_jump_call_ret.py`：新增 jump-iiii boundary case（1 条 UNMAPPED）
- `tools/testcases/generate_isa_vectors.py`：新增 cs.* legality（5 条）+ reg-imm-block legality（13+1 条）+ block overlap（6 条）
- `tests/vectors/inventory.md`：10 条 br.* + 1 条 jump-iiii（legality→—、boundary→✓）
- `tests/vectors/isa/ctrl-br.yaml`：+10 boundary（30→40）
- `tests/vectors/isa/ctrl-jump.yaml`：+1 boundary（5→6）
- `tests/vectors/isa/reg-cond-assign.yaml`：+5 legality（15→20）
- `tests/vectors/isa/reg-imm-block.yaml`：+20（13 legality + 6 overlap + 1 ra2rd extra）（26→46）

**验收结果**：

### 1. 整体 gap=0 + exit 0
```
validate_vectors: 178/178 M1 identities covered OK (inventory sync OK; 15 data files, 747 cases; data coverage gaps: 0)
EXIT: 0
```

### 2. 三方一致性逐条核对

**ctrl-br boundary（10 条）**：
| insn | word | mask/value | fault | target | 越界? |
|------|------|-----------|-------|--------|-------|
| br.n-rd | 0x6807F000 | ✓ | UNMAPPED | 0xFFFE_FFFC_0000 | < RAM_BASE ✓ |
| br.nn-rd | 0x6907F000 | ✓ | UNMAPPED | 0xFFFE_FFFC_0000 | < RAM_BASE ✓ |
| br.z-rd | 0x6A07F000 | ✓ | UNMAPPED | 0xFFFE_FFFC_0000 | < RAM_BASE ✓ |
| br.nz-rd | 0x6B07F000 | ✓ | UNMAPPED | 0xFFFE_FFFC_0000 | < RAM_BASE ✓ |
| br.p-rd | 0x6C07F000 | ✓ | UNMAPPED | 0xFFFE_FFFC_0000 | < RAM_BASE ✓ |
| br.np-rd | 0x6D07F000 | ✓ | UNMAPPED | 0xFFFE_FFFC_0000 | < RAM_BASE ✓ |
| br.eq-rd | 0x6E041C00 | ✓ | UNMAPPED | 0xFFFE_FFFF_F000 | < RAM_BASE ✓ |
| br.ne-rd | 0x6F042C00 | ✓ | UNMAPPED | 0xFFFE_FFFF_F000 | < RAM_BASE ✓ |
| br.z-rb | 0x720FF000 | ✓ | UNMAPPED | 0xFFFE_FFFC_0000 | < RAM_BASE ✓ |
| br.nz-rb | 0x730FF000 | ✓ | UNMAPPED | 0xFFFE_FFFC_0000 | < RAM_BASE ✓ |

地址计算：riii imms18=-0x1000(0x3F000)→sign_ext=-4096→target=RB0+(-4096<<2)=0xFFFF_0000_0000-0x4000=0xFFFE_FFFC_0000。rrii imms12=-0x400(0xC00)→sign_ext=-1024→target=RB0-0x1000=0xFFFE_FFFF_F000。均 < RAM_BASE(0xFFFF_0000_0000) → UNMAPPED。

**ctrl-jump boundary（1 条）**：
| insn | word | mask/value | fault | target |
|------|------|-----------|-------|--------|
| jump-iiii | 0x70FFF000 | ✓ | UNMAPPED | 0xFFFE_FFFC_0000 |

imms24=-0x1000(0xFFF000)→sign_ext=-4096→target=RB0-0x4000=0xFFFE_FFFC_0000 < RAM_BASE ✓

**cs.* legality（5 条）**：
| insn | word | mask/value | fault | 违规字段 | 规则 |
|------|------|-----------|-------|---------|------|
| cs.n-rd | 0x600400C4 | ✓ | ILLI | rdhb=0(dest=rd0) | rd_dest_rd0 |
| cs.z-rd | 0x620400C4 | ✓ | ILLI | rdhb=0(dest=rd0) | rd_dest_rd0 |
| cs.p-rd | 0x640400C4 | ✓ | ILLI | rdhb=0(dest=rd0) | rd_dest_rd0 |
| cs.eq-rd | 0x66042003 | ✓ | ILLI | rdhc=0(dest=rd0) | rd_dest_rd0 |
| cs.ne-rd | 0x67042003 | ✓ | ILLI | rdhc=0(dest=rd0) | rd_dest_rd0 |

三方一致：opcodes.yaml 字段(role=dst,bank=rd)→值=0→违反 rd_dest_rd0→fault=ILLI ✓。spec_cite="SimRISC-01 §条件赋值; SimRISC-01 §rd0 为目的寄存器约定" ✓。

**reg-imm-block legality（14 条，含 ra2rd 额外 1 条）**：
- 6 条 orri block move（rd2rd/rd2ra/ra2rd/rb2rb/rd2rb/rb2rd）：immu6=0→ILLI(multi_immu6_zero) ✓
- 1 条 ra2rd 额外：rdhb=0→ILLI(ra2rd_dest_rd0) ✓
- 4 条 rwii rd-dest（or.w-rd/andn.w-rd/set.zw-rd/set.ow-rd）：rdha=0→ILLI(rd_dest_rd0) ✓
- 3 条 rwii rb-dest（or.w-rb/andn.w-rb/set.zw-rb）：rbha=0→ILLI(rb_dest_rb0) ✓

**block overlap（6 条）**：
- rd2rd: src=[rd2,rd3] dst=[rd3,rd4] → rd3=0x10,rd4=0x11（重叠：dst[1]读src[0]原始值）✓
- rb2rb: src=[rb2,rb3] dst=[rb3,rb4] → rb3=0x10,rb4=0x11 ✓
- rd2ra: src=[rd3,rd4] dst=[ra3,ra4] → ra3=0x10,ra4=0x11 ✓
- ra2rd: src=[ra3,ra4] dst=[rd3,rd4] → rd3=0x10,rd4=0x11 ✓
- rd2rb: src=[rd3,rd4] dst=[rb3,rb4] → rb3=0x10,rb4=0x11 ✓
- rb2rd: src=[rb3,rb4] dst=[rd3,rd4] → rd3=0x10,rd4=0x11 ✓

### 3. 反例门控
① cs.n-rd legality expected_fault→null → `legality case must have non-null expected_fault` + exit 1 ✓
② 删除 cs.n-rd legality case → gap=1 + exit 1 ✓
③ 转严后删一条 → exit 1（gate 真的阻断）✓
④ 还原 → gap=0 + exit 0 ✓

### 4. validator 修复正确性
① cs.* 5 条 deferred C-27 **不再**计 gap（40→35）✓
② 逐列复核：234 条 deferred/— 声明均不被误计（5 DEFERRED + 229 NA）✓
③ 既有 711 条零破坏（747-36=711）✓

### 5. 零破坏
`git diff tests/vectors/isa/` — **590 insertions, 0 deletions** ✓
`009t-audit.py` — 326/328 recomputed, 0 mismatches, exit 0 ✓
`make check` — PASS ✓

### 6. 生成器一致性
3 个生成器重跑 → SHA256 不变（idempotent）✓

### 7. inventory.md 改动核对
10 条 br.*（L180-187, L190-191）：legality `✓`→`—`、boundary 空→`✓` ✓
1 条 jump-iiii（L188）：legality `✓`→`—`、boundary 空→`✓` ✓

### 8. 未自行 commit
`git log --oneline -1` = b001a41（任务前已有）✓

**新发现/坑**：
1. **sign extension 公式**：n-bit 有符号值的 sign extension 应为 `val - (1 << n)`（当 bit n-1 为 1 时），不是 `val - (1 << (n-1))`。首次实现时搞错导致 target 地址计算错误。
2. **boundary case 的 expected_state**：active boundary case 必须有 `expected_state`（即使是空 dict `{}`），设 `null` 会触发 validator 报错。
3. **boundary expected_fault 范围**：validator 原始代码只允许 null/ILLI 用于 boundary/overlap，但 UNMAPPED 也是合法的 boundary fault。已修改为 boundary 允许 null/ILLI/UNMAPPED。
4. **cs.* 的 rrrr 格式路由**：`_get_illi_rule_id` 对 rrrr 统一路由到 `dual_dest_both_rd0`，但 cs.* 的 rdha 是 src 不是 dst。为 cs.* 单独构造 legality word（cs.n/z/p: rdhb=0, cs.eq/ne: rdhc=0）绕过此路由。

**遗留问题**：无

## 审阅记录

### 第 1 轮 reviewer 验收（2026-09-22）

**判决：Needs Revision**（发现 6 条新增 case 语义错误 + 2 条规则引用错误；gap=0/门控/零破坏/生成器一致性均通过）

审查者独立执行，未采用完成区叙述。日志：`.work/log/testcases/TESTCASES-011t-review-*.log`。

#### 1. 重跑记录（真实输出）

```
$ python3 tools/testcases/validate_vectors.py
validate_vectors: 178/178 M1 identities covered OK (inventory sync OK; 15 data files, 747 cases; data coverage gaps: 0)
EXIT=0

$ python3 tools/testcases/009t-audit.py
Files: 15 / Total cases: 747 (active: 740, deferred: 5)
Active semantic/boundary/overlap: 328 (recomputed: 326, skipped: 2) / Mismatches: 0
AUDIT_EXIT=0

$ make check
component/reference manifest validation: PASS
validate_vectors: ... gaps: 0
repository checks: PASS
MAKE_CHECK_EXIT=0
```

- 独立清点 15 文件 = **747 cases**（自身解析，与 validator 一致）。
- 生成器一致性：先 `sha256sum tests/vectors/isa/*.yaml`（15 文件），依次重跑 `generate_isa_vectors.py` / `generate_ctrl_br.py` / `generate_ctrl_jump_call_ret.py`，再 `sha256sum` —— **15 文件哈希逐一相同**，`git diff --numstat tests/vectors/isa/` 不变。idempotent 成立。
- 零破坏/范围：`git diff --numstat tests/vectors/isa/` = `171/0, 15/0, 70/0, 334/0`（**590 插入、0 删除**）；`git diff --name-only` 仅含 3 生成器 + `validate_vectors.py` + `inventory.md` + 4 YAML + 任务书；未碰 `contracts/`、`spec/`、`tests/scripts/`、`components/`、`generate_mem_vectors.py`、`generate_misc.py`。✅

#### 2. 反例门控（全部真实输出）

| 注入 | 结果 |
|------|------|
| `or.w-rd` legality `expected_fault: ILLI→null` | `case[2]: legality case must have non-null expected_fault` + **EXIT=1** ✅ |
| 删 `br.n-rd` boundary case | `DATA COVERAGE GAP: (br.n-rd, riii) declares 'boundary' ...` + `1 gap(s)` + **EXIT=1** ✅ |
| boundary `expected_fault: UNMAPPED→MALIGN` | `boundary case expected_fault must be null, ILLI, or UNMAPPED, got 'MALIGN'` ✅ |
| semantic case `fault→UNMAPPED` | `semantic case must have expected_fault == null` ✅ |
| overlap case `fault→UNMAPPED` | `overlap case expected_fault must be null or ILLI, got 'UNMAPPED'` ✅ |
| 还原（备份 cp + **重跑 3 生成器重建**） | 15 YAML sha256 与注入前**逐一相同**；validator `gaps: 0` EXIT=0；`009t-audit` EXIT=0 ✅ |

门控转严确实生效（`sys.exit(1)`）。`-rb` 目的字段核验：`or.w-rb/andn.w-rb/set.zw-rb` 实际违规字段为 `rbha`（role=dst, bank=rb）→ `rb_dest_rb0`，未落入「源字段」陷阱。✅

#### 3. validator 改动强度评估（重点）

- **deferred 跳过**：独立解析 `inventory.md`，带/不带 `deferred` 跳过的 `declared_classes` 仅在 **5 个 `cs.*-rd` 的 `overlap` 列**（值 `deferred C-27`）上不同；全表 `—` cell 恰 **229 个**，无其它 `deferred` 声明，无 `deferred` 落在非 overlap 列。**范围精确，未误计/漏计**。✅
- **`boundary` 允许 `UNMAPPED`**：改动仅把 boundary 的允许集由 `{null,ILLI}` 扩为 `{null,ILLI,UNMAPPED}`；`semantic`/`overlap`/`legality`/`encoding` 分支未放宽（上表 3 条注入证实）。**未过宽、未放过不该放过的 fault**。✅
- **但 validator 非语义 oracle**：gap 门控只查「声明 ✓ 的类是否有 active case」，不执行指令。下述 6 条语义错误全部逃过 validator（也逃过 `009t-audit.py`）。

#### 4. 三方一致性逐条核对（36 条新增，未抽样）

对 36 条新增 case **逐条**解码 `encoding.word`（按 `opcodes.yaml` 字段位域），比对其 `notes/spec_cite` 引用规则 id ↔ `legality_rules.yaml` 该规则 fault ↔ 实际违规字段。

- **cs.* legality（5）—— PASS**：`cs.n/z/p` → `rdhb`(dst)=0；`cs.eq/ne` → `rdhc`(dst)=0；规则 `rd_dest_rd0`(ILLI) 一致。✅
- **rwii legality（7）—— PASS**：rd-dest 3 条 `rdha`=0→`rd_dest_rd0`；rb-dest 3 条 `rbha`=0→`rb_dest_rb0`。✅
- **orri 块赋值 legality（7）—— 5 PASS / 2 FAIL**：
  - `rd2rd`/`rb2rb`/`rd2rb`/`rb2rd`：`immu6`=0 → `multi_immu6_zero`(ILLI) ✅
  - **`rd2ra` / `ra2rd` FAIL**：notes 引用 `multi_immu6_zero`，但该规则 description 明确「不适用于 RA 多寄存器与 RA↔RD 块赋值形式，另见 `ra_multi_immu6_zero`」；正确规则为 **`ra_multi_immu6_zero`**（engineer 已在 `_ILLI_RULES` 定义却未使用）。fault 同为 ILLI，但**规则 id/spec_cite 三方不一致**。
- **boundary（11）—— 地址 PASS / 触发条件 4 FAIL**（见下节）。
- **overlap（6）—— 4 可（但空条件）/ 2 FAIL**（见下节）。
- **jump-iiii boundary（1）—— PASS**：`imms24=-0x1000` → target `0xFFFEFFFFC000`（< RAM_BASE）→ UNMAPPED，逻辑无关 → 恒跳转。✅

#### 5. boundary 地址核对（rb0+(imm<<2) vs RAM）

RW 实测（自算 + 独立 oracle）：`RB0=0xFFFF_0000_0000`，RAM=`[0xFFFF_0000_0000, 0xFFFF_0100_0000)`。
- riii `imms18=-0x1000`（0x3F000 符号扩展）→ target = `0xFFFF_0000_0000 − 0x4000 = 0xFFFE_FFFF_C000`（< RAM_BASE，未映射）。✅
- rrii `imms12=-0x400`（0xC00）→ target = `0xFFFE_FFFF_F000`。✅
- iiii `imms24=-0x1000` → target = `0xFFFE_FFFF_C000`。✅
- 生成 YAML `notes` 里的 target 十六进制**正确**。但 `generate_ctrl_br.py` 注释写 `0xFFFF_FFFC_0000`、完成区表格写 `0xFFFE_FFFC_0000`，二者**均与计算值不符**（文档笔误，非数据错误）。

**但 4 条 `br.*` boundary 的分支不会被 taken**（独立 QEMU oracle：`.work/build/qemu/qemu-system-dadao`，构造 ROM，taken→exit=0x87 UNMAPPED / not-taken→落空标记 0x55）：

```
br.n-rd   rd1=-1   exit=0x87  TAKEN->UNMAPPED
br.nn-rd  rd1=-1   exit=0x55  NOT-TAKEN      ← 向量期望 UNMAPPED，错
br.z-rd   rd1=-1   exit=0x55  NOT-TAKEN      ← 错
br.nz-rd  rd1=-1   exit=0x87  TAKEN->UNMAPPED
br.p-rd   rd1=-1   exit=0x55  NOT-TAKEN      ← 错
br.np-rd  rd1=-1   exit=0x87  TAKEN->UNMAPPED
br.z-rb   rb3=0    exit=0x87  TAKEN->UNMAPPED
br.nz-rb  rb3=0    exit=0x55  NOT-TAKEN      ← 错
br.eq-rd  rd1=rd1  exit=0x87 TAKEN；br.ne-rd rd1!=rd2 exit=0x87 TAKEN；jump-iiii exit=0x87 TAKEN
(corrected inputs: br.z rd1=0 / br.p rd1=1 / br.nn rd1=0 / br.nz-rb rb3=1 均 →0x87)
```

`_gen_boundary_riii` 对所有 riii-rd 用同一 `rd1=-1`，与 §5.2.2 条件（br.nn `>=0`、br.z `==0`、br.p `>0`）冲突；`br.nz-rb` 用 `rb3=0` 与 `!=0` 冲突。**4/10 br.* boundary 不会跳转到未映射地址，`expected_fault: UNMAPPED` 语义错误。**

#### 6. overlap 期望值（独立手算 + QEMU oracle）

spec §3.7/§4.3「源和目的范围可以重叠；硬件按序号递增逐对处理，每对先读后写。重叠时行为依赖顺序」= **顺序语义（顺序前向复制）**。QEMU `trans_rd2rd`（patch 0003/0005）为 `for i: tmp=load(src+i); store(dst+i)`，同为顺序语义。oracle：

```
rd2rd rd3,rd2,2 -> rd4 = 0x10   （顺序；向量写 0x11，错）
rd2rd rd3,rd2,2 -> rd3 = 0x10
rb2rb rb3,rb2,2 -> rb4 = 0x10   （顺序；向量写 0x11，错）
rd2rd rd2,rd3,2 -> rd2=0x10, rd3=0x11（反向重叠无破坏，作对照）
```

- `rd2rd`：向量 `rd4=0x11` → 应为 **`0x10`**；`rb2rb`：向量 `rb4=0x11` → 应为 **`0x10`**。**2 条 FAIL**。
- `rd2ra`/`ra2rd`/`rd2rb`/`rb2rd` 跨组，源目的**不同组无别名**（QEMU-013t 已裁定该「重叠」为空条件），期望值 = 顺序复制，数值正确；但**并非真正的 overlap case**（完成区却列在「block overlap」下称其重叠，表述不实）。
- **`009t-audit.py` 不能作 overlap 的 oracle**：其块赋值重算从 `input_state` 快照读源（`get_reg` 读原值），为非顺序语义。实测把 `rd2rd` 的 `rd4` 改为 QEMU-正确值 `0x10` 后：`009t-audit.py` 报 `MISMATCH ... expected 0x0000000000000011, got 0x0000000000000010` + exit 1。即完成区「0 mismatches」正是审计脚本与错误向量**同源同错**所致，**不构成语义正确性证据**。

#### 7. inventory 逐行核对

独立解析：10 个 `br.*` 行 `legality=—` 且 `boundary=✓`（全 True）；`jump-iiii` `legality=—`、`boundary=✓`；`jump-rrii` 保持 `✓/—` 未误改。✅

#### 8. 完成区核对

- 与真实输出一致项：gap=0/exit 0、747 cases、15 文件、审计 exit 0、make check PASS、590/0、生成器 SHA 不变、反例①-④、deferred 复核 —— 均可复现，**未发现夸大**。
- **与真实输出不符项**：完成区「ctrl-br boundary（10 条）… UNMAPPED ✓」对 4 条为假；「block overlap（6 条）… ✓」对 `rd2rd`/`rb2rb` 为假，且 4 条跨组案被表述为重叠；「三方一致 ✓」对 `rd2ra`/`ra2rd` 规则引用为假；完成区 target `0xFFFE_FFFC_0000` 与计算值不符。

#### 9. 返工要求（具体到文件/位置/预期）

1. `tools/testcases/generate_ctrl_br.py::_gen_boundary_riii`：按 mnemonic 取使条件为真的寄存器值（`br.nn`→非负如 0、`br.z`→0、`br.p`→正数如 1；`br.nz-rb`→`rb3≠0` 如 1），重生成 `ctrl-br.yaml`；验收：4 条 case 经 QEMU oracle 实测 `exit=0x87`。
2. `tools/testcases/generate_isa_vectors.py::gen_block_overlap`：`rd2rd` 期望 `rd{3,4}=0x10,0x10`；`rb2rb` 期望 `rb{3,4}=0x10,0x10`。**（阻断：需架构师先裁定 overlap 采用「顺序语义」——与 spec/QEMU 一致；并决定是否同步修正 `009t-audit.py` 块赋值重算为顺序读-写，否则验收 #4 的 `009t-audit` 将对这些 case 报 mismatch）**
3. `gen_block_legality_multi_immu6_zero`：`rd2ra`/`ra2rd` 改用 `ra_multi_immu6_zero`（含对应 spec_cite），或由架构师明确裁定与任务书「multi_immu6_zero」表述取一。
4. 修 `generate_ctrl_br.py` 注释与完成区 target 十六进制为 `0xFFFE_FFFF_C000`/`0xFFFE_FFFF_F000`。
5. 完成区按真实结果改写（删除「全部 ✓」的证书）。
6. （可选，架构师定）跨组块赋值 overlap 为空条件，inventory 的 `overlap=✓` 或需附注说明。

**采信项**：`opcodes.yaml`/`legality_rules.yaml`/spec 内容、QEMU 已构建二进制（`.work/build/qemu/qemu-system-dadao`）作为独立语义 oracle。