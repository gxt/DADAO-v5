# TESTCASES-005t: 控制转移 `br.*`（taken / not-taken 全测）

**模块**：testcases
**项目里程碑**：M1
**依赖**：`TESTCASES-002t`（schema `expected_pc`）；文件级与 `003t`/`004t` 不相交，可并行；默认下发建议排在 `004t` 之后（见「下发建议」）
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `tests/vectors/isa/control-flow.yaml`（`TESTCASES-002t` 产出：`br.*`/`jump`/`call`/`ret`/`swym`）
  - `tests/vectors/schema.md`（`TESTCASES-002t` 返工后：含 `expected_pc`）
  - `contracts/opcodes.yaml`（`br.*` 编码字段；`op=value>>24`、`ha=(value>>18)&0x3f`）
  - `.tao/knowledge/contract-isa.md` §5.1/§5.2（条件跳转：rrii 双寄存器、riii 单寄存器、RB 变体）、§9.1（ILLI）
  - `.tao/knowledge/adr-0004-test-machine.md`（D6.5 `rb0` = 当前指令地址；D5.6 访问矩阵）
- 输出（**本任务拥有的文件**，`tests/vectors/isa/`）：
  - `ctrl-br.yaml`
- 约束：
  - 期望值**手工派生自 `contract-isa.md`/`spec/`/ADR-0004**，不得从 LLVM/QEMU 反推
  - 覆盖率主键 `(insn, format)`；M1 scope 以 `excluded_m1 != true` 为准
  - **只动 `ctrl-br.yaml` 与 `control-flow.yaml` 的 `br.*` 拆分**；**不改** `contracts/`；**不改** `ctrl-jump`/`ctrl-call`/`ctrl-ret`/`misc`（归 `006t`/`007t`）
  - 完成后不自行 commit

## 任务范围

### 1. 文件重组（旧 → 新；只描述目标）

| 动作 | 内容 |
|---|---|
| 新建 `ctrl-br.yaml` | 从 `control-flow.yaml` 拆出全部 `br.*`（10 个身份：`br.n-rd`/`br.nn-rd`/`br.z-rd`/`br.nz-rd`/`br.p-rd`/`br.np-rd`/`br.eq-rd`/`br.ne-rd`/`br.z-rb`/`br.nz-rb`） |
| 保留（交 `006t`） | `control-flow.yaml` 中的 `jump-*`/`call-*`/`ret-*` 暂留原文件，由 `006t` 拆出 |
| 保留（交 `007t`） | `control-flow.yaml` 中的 `swym` 暂留原文件，由 `007t` 移入 `misc.yaml` |

- 本任务**不删除** `control-flow.yaml`（仍被 `006t`/`007t` 消费）。

### 2. F7：`br.*` taken / not-taken 全覆盖（本任务核心）

- **事实**：`TESTCASES-002t` 只写了「不跳转」路径（`condition false -> no jump`），**taken 路径未覆盖**。
- **要求**：每个 `br.*` 身份至少覆盖 **taken** 与 **not-taken** 两条 semantic，用 `expected_pc` 表达 PC 效果：
  - 条件为真（taken）：`expected_pc = rb0 + (imm << 2)`；
  - 条件为假（not-taken）：`expected_pc = rb0 + 4`（下一条）；
  - `rb0` 执行时 = **当前指令地址**（ADR-0004 D6.5），由 harness 布局确定；向量 notes 须写明所用 PC 地址与布局来源。
- **条件与立即数语义**（`contract-isa.md` §5.2）：
  - `br.eq rdha, rdhb, imms12`：`rdha == rdhb`；`br.ne`：`rdha != rdhb`；`Addr = rb0 + (imms12<<2)`；
  - `br.n rdha, imms18`：`rdha < 0`；`br.nn`：`>= 0`；`br.z`：`== 0`；`br.nz`：`!= 0`；`br.p`：`> 0`；`br.np`：`<= 0`；`Addr = rb0 + (imms18<<2)`；
  - `br.z rbha, imms18`：`rbha == 0`；`br.nz rbha`：`rbha != 0`；`Addr = rb0 + (imms18<<2)`；
  - 特例：`rdha` 为 `rd0` 时 `br.z` 恒真、`br.nz` 恒假（`contract-isa.md` §5.2.2）。
- **立即数选择**：taken 用例的 `imm` 取使目标为**本文件内可预置/合法**地址的值（如 `imm=1` → 下一条），避免自跳死循环（`imm=0` → 跳到自身，ADR-0004 D6.5）。不得用 `imm=0` 构造 semantic。
- **`expected_state`**：`br.*` 不改寄存器，`expected_state` 可为 `{}`/null（按 schema 规则）；PC 效果一律用 `expected_pc`。
- **validator 存在性规则**：`002t` 只校验 `expected_pc`「出现时」的合法性；本任务在数据补齐后，向 `tools/testcases/validate_vectors.py` 追加「改变 PC 的 active semantic/boundary 必须给出 `expected_pc`」的存在性规则（对 `ctrl-br` 生效），并验证真实树零误报。

### 3. F10：`ctrl-br.yaml` 的 encoding 向量修复

- **要求**：逐条修正 encoding 向量，使 `word` 满足 `(word & mask) == value` 且可解码执行无 fault：
  - 分支的操作数 `rd` 是**源**（可用 `rd0`；`br.z rd0` 恒真、`br.nz rd0` 恒假）；
  - 相对分支立即数用 **`imm=1`**（目标 = 下一条），避免 `imm=0` 自跳死循环；
  - `expected_state: null`、`expected_pc: null`、`expected_fault: null`、`status: active`。
- **依据**：`contract-isa.md` §5、ADR-0004 D6.5；0628 的「`rb0`=下一条、`imm=0` 等效 NOP」**不适用**。

### 4. legality / boundary

- 保留并复核 `br.*` 的 legality/boundary（若有）；对齐相关 fault 以 `contract-isa.md` §9/ADR-0004 D5 为准。

## 下发建议

- **数据依赖**：仅 `002t`（需其 schema 的 `expected_pc`）。
- **文件级**：`ctrl-br.yaml` 与 `reg-*`（`003t`）、`mem-*`（`004t`）不相交，**可与之并行**；但与 `006t`/`007t` 共享 `control-flow.yaml`，故 `005t → 006t → 007t` 三者在源文件上必须串行。
- **共享 `inventory.md`**：本任务需更新 `ctrl-br` 行的 `file` 列；若 `002t` 提供 inventory 生成脚本，则各任务只重生成不手改，并行安全；否则默认全串行（`002t → 003t → 004t → 005t → 006t → 007t`）以避免 `inventory.md` 冲突。

## 验收标准

1. `ctrl-br.yaml` 存在，覆盖全部 10 个 `br.*` M1 身份
2. **每个 `br.*` 身份有 ≥1 条 taken 与 ≥1 条 not-taken 的 active semantic**，`expected_pc` 分别为 `rb0+(imm<<2)` 与 `rb0+4`
3. `expected_pc` 为 48-bit 有效地址；notes 写明所用 PC 地址与布局来源（ADR-0004 D6.5）
4. `br.*` encoding 向量 `status: active`、`expected_fault: null`、`expected_pc: null`，且经推演确认可解码执行无 fault（不 ILLI/不自跳）
5. 未改动 `control-flow.yaml` 的 `jump`/`call`/`ret`/`swym`（交 `006t`/`007t`）；未改 `contracts/`；未动 `reg-*`/`mem-*`
6. `python3 tools/testcases/validate_vectors.py` 零错误；`make check` PASS
7. （下游）QEMU harness 就绪后，`ctrl-br.yaml` active 测试全 PASS；本任务记录该运行验收依赖（branch-over-poison 类 layout 属 harness 能力，见下）
8. 未自行 commit

## 背景（完整）

### 目标

把条件分支向量独立为 `ctrl-br.yaml`，并补齐 taken 路径，使 `br.*` 的**两种执行结果**都有独立 oracle。

### 设计理由

- `002t` 仅覆盖 not-taken，`br.*` 的 taken 分支（跳转目标）无向量 → 控制流覆盖存在系统性缺口。
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
- 故 semantic/encoding 必须用 `imm=1`（或其它非自跳值）；not-taken 时 PC = `rb0 + 4`。

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

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-028a-control-flow-yaml-tdd.md`（内容溯源，非执行依赖）

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **助记符**：`brn`/`brnn`/`brz`/`brnz`/`brp`/`brnp`/`breq`/`brne` → `br.n`/`br.nn`/`br.z`/`br.nz`/`br.p`/`br.np`/`br.eq`/`br.ne`；另有 `br.z-rb`/`br.nz-rb` 变体。
2. **地址公式**：v5 为 `PC = rb0 + (imm << 2)`；ADR-0004 D6.5 冻结 `rb0`=当前指令地址 → encoding 用 `imm=1`；0628 的「`rb0`=下一条、`imm=0` 等效 NOP」**不适用**。
3. **PC 公式修复属实现层**（qemu 模块），本任务只保证向量数据正确。
4. **`expected_pc`（v5 新增）**：taken/not-taken 的 PC 效果用该字段表达；0628 无此字段。

## 已知坑 / 结论

1. **`imm=1` 避免自跳**：ADR-0004 D6.5 冻结 `rb0`=当前指令地址。
2. **taken 未覆盖是系统性缺口**：每个 `br.*` 身份必须有 taken 与 not-taken 两条。
3. **`rd0` 特例**：`br.z rd0` 恒真、`br.nz rd0` 恒假；可用于构造确定的 taken/not-taken。
4. **不自行 commit**：完成后等待审查。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-028a-control-flow-yaml-tdd.md`（内容溯源）
- 本项目：`.tao/knowledge/contract-isa.md` §5、`.tao/knowledge/adr-0004-test-machine.md`、`contracts/opcodes.yaml`、`tests/vectors/schema.md`
- 知识库：`.tao/knowledge/MEMORY.md`、`.tao/knowledge/deferred.md`

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

### 第 1 轮 engineer 自审
（待填写）

### 第 1 轮 reviewer 验收
（待填写）
