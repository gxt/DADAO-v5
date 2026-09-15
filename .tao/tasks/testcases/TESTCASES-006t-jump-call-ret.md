# TESTCASES-006t: `jump` / `call` / `ret` 向量

**模块**：testcases
**项目里程碑**：M1
**依赖**：`TESTCASES-005t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `tests/vectors/schema.md`（`TESTCASES-002t` 返工后：含 `expected_pc`）
  - `contracts/opcodes.yaml`（`jump`/`call`/`ret` 编码字段；`op=value>>24`、`ha=(value>>18)&0x3f`）
  - `.tao/knowledge/contract-isa.md` §5.3（无条件跳转）、§5.4（函数调用）、§5.5（函数返回）、§5.6（RegRAS 压栈/弹栈）、§1.3.4（RA 模型）、§9（RASOF/RASUF/IALIGN）
  - `.tao/knowledge/adr-0004-test-machine.md`（D2.1 复位 `ra0`–`ra63 = 0`；D6.5 `rb0` = 当前指令地址；D5.6 访问矩阵；D5.8 `0x87`）
- **输入说明（陈旧引用修正）**：仓库内**无任何 `tests/vectors/isa/*.yaml`**——上一版 `002t` 的向量数据已随返工**一并丢弃**。本任务按 `schema.md` **从零生成** 3 个目标文件，**不是**重组/修复既有文件。
- 输出（**本任务拥有的文件**，`tests/vectors/isa/`）：
  - `ctrl-jump.yaml`、`ctrl-call.yaml`、`ctrl-ret.yaml`
- 约束：
  - 期望值**手工派生自 `contract-isa.md`/`spec/`/ADR-0004**，不得从 LLVM/QEMU 反推
  - 覆盖率主键 `(insn, format)`；M1 scope 以 `excluded_m1 != true` 为准
  - **只生成/修改本任务 3 个目标文件**；**不改** `contracts/`；**不改** `ctrl-br`/`misc`/`reg-*`/`mem-*`
  - 参考仓库（`.work/DADAO-0628/`）的向量数据**仅内容溯源，不得作为执行依赖**（禁止复制数据正文）
  - 完成后不自行 commit

## 任务范围

### 1. 目标文件集（从零生成）

> **数据来源说明**：仓库内**无既有向量数据**（上一版已丢弃），本任务按 `schema.md` 从零生成下列文件；不再有「旧文件 → 新文件」的重组动作。

| 目标文件 | 覆盖身份 |
|---|---|
| `ctrl-jump.yaml` | `jump-iiii`/`jump-rrii`（2 个） |
| `ctrl-call.yaml` | `call-iiii`/`call-rrii`（2 个） |
| `ctrl-ret.yaml` | `ret-riii`（1 个） |

- `br.*`（`005t`）与 `swym`（`007t`）不在本任务。

### 2. F7 方案 (i)：用 `expected_pc` 表达 PC 效果（本任务核心）

- **背景（上一版丢弃数据的教训）**：`jump`/`call` 的语义只改 PC（`rb0`），`expected_state` 表达不了；上一版把 4 条 semantic（`jump-iiii`/`jump-rrii`/`call-iiii`/`call-rrii`）标为 deferred。本任务从零生成时**直接 active**。
- **裁决**：ADR-0004 D6.5 冻结 `rb0` = 当前指令地址（非自由变量）→ PC 效果**可算**。schema 新增 `expected_pc`（`002t`）→ **4 条生成即 active**，不再有 PC-only deferred。
- **要求**：
  - `jump-iiii`：`Addr = rb0 + (imms24<<2)`；`expected_pc = Addr`（`contract-isa.md` §5.3）；
  - `jump-rrii`：`Addr = rbha + rdhb + (imms12<<2)`；`expected_pc = Addr`（`§5.3`）；
  - `call-iiii`：`Addr = rb0 + (imms24<<2)`；`expected_pc = Addr`，且压栈效果见 §3；
  - `call-rrii`：`Addr = rbha + rdhb + (imms12<<2)`；`expected_pc = Addr`，压栈同 §3；
  - 地址为 48-bit 有效地址；`expected_pc` 为 48-bit hex。
- **立即数/寄存器选择**：目标地址须落在可预置/合法的布局（如 `imm=1` → 下一条；`jump-rrii` 用 `ha=rb0`/`hb=rd0`/`imms12=1`）；避免 addr=0（unmapped）与自跳。
- **validator 存在性规则**：`002t` 只校验 `expected_pc`「出现时」的合法性；本任务在数据补齐后，向 `tools/testcases/validate_vectors.py` 追加「改变 PC 的 active semantic/boundary 必须给出 `expected_pc`」的存在性规则（对 `ctrl-jump`/`ctrl-call`/`ctrl-ret` 生效），并验证真实树零误报。

### 3. `call` 的 RA 压栈用 `ra` 表达

- **效果**：`call` = PC 跳转 + RegRAS 压栈（压入返回地址 `PC+4`；`ra63` 高 16 位为引用计数，首次压栈设为 `0x0001`）——`contract-isa.md` §5.4/§5.6.1。
- **要求**：`ctrl-call.yaml` 的 semantic 用 `expected_state.ra` 表达压栈结果，例如：
  - 冷 RA（ADR-0004 D2.1 复位 `ra0`–`ra63 = 0`）：`expected_state.ra.ra63 = 0x0001_0000_0000_00XX`（高 16 = `0x0001`，低 48 = 返回地址 = 指令地址 + 4）；
  - 若输入预置了 `ra63`（递归/移位场景），按 §5.6.1 的三种情况推演（引用计数 +1 / 移位压栈）；
  - `ra0` 低 48 位非 0（MemRAS）时的溢出（RASOF）属 legality，不属本任务 semantic。
- **依据**：ADR-0004 D6.5 冻结布局可算 `PC+4`；`ra` 在 `expected_state` 可观测（schema 已支持）。
- **不得**把 PC 效果塞进 `expected_state`（PC 用 `expected_pc`）。

### 4. `ret` 语义（生成即 active，复核）

- **事实**：`ret` 语义可直接 active（写 `rd` + 弹 RA，`contract-isa.md` §5.5/§5.6.2），本任务生成后复核。
- **要求**：复核 `ret-riii` 的 semantic 是否与 `expected_pc` 一致：
  - `ret rdha, imms18`：`rdha = sign_extend(imms18)`；`PC = ra63` 低 48 位（弹栈后）；`expected_pc = 弹出的返回地址`；
  - 弹栈后 `ra63` 的移位效果按 §5.6.2 推演并写入 `expected_state.ra`；
  - `ret rd0, 0` 合法（`rd0` 为目的的例外）。
- **RASUF**（冷 RA 弹栈）仍属 legality（`expected_fault: RASUF`）；**encoding 例外**：`ret-riii` 因返回目标依赖 harness 布局、单指令不可构造，不生成 encoding case（**非**恒 fault；`002t` schema 已澄清，`inventory` 标注）。

### 5. F10：`ctrl-jump`/`ctrl-call`/`ctrl-ret` 的 encoding 向量修复

- **要求**：逐条修正 encoding，使 `word` 满足 `(word & mask) == value` 且可解码执行无 fault：
  - 相对立即数用 `imm=1`（目标=下一条，避免自跳）；`call` 同时压栈后落到下一条；
  - `jump-rrii`/`call-rrii` 用 `ha=rb0`（PC 可作基址）、`hb=rd0`、`imms12=1` → 目标 = `rb0+4` = 下一条；**不要**用 `rb0/rd0/0`（addr=0 → unmapped）；
  - `ret-riii` 不生成 encoding（见 §4）；
  - `expected_state: null`、`expected_pc: null`、`expected_fault: null`、`status: active`。
- **legality**：`jump-rrii`/`call-rrii` 的 addr=0 → 取指 unmapped `0x87`（`expected_fault: UNMAPPED`）；`ret-riii` 冷 RA → `RASUF`（`0x8B`）；`call-iiii` 深度溢出 → `RASOF`（`0x8A`）。复核齐备、notes 说明依据。

## 验收标准

1. `ctrl-jump.yaml`/`ctrl-call.yaml`/`ctrl-ret.yaml` 存在，覆盖 `jump-iiii`/`jump-rrii`/`call-iiii`/`call-rrii`/`ret-riii` 全部身份
2. **F7 全 active**：`jump`/`call` 的 4 条原 deferred semantic 已改 `status: active` 且带 `expected_pc`；无 PC-only deferred 残留（`deferred.md` 相应更新）
3. `jump`/`call` semantic 的 `expected_pc` = 按 §5.3/§5.4 手算的目标地址（48-bit）；notes 写明所用 PC/布局来源
4. `call` semantic 的 `expected_state.ra` 表达压栈结果（`ra63` 高 16 计数 + 低 48 返回地址 = PC+4），推演依据 §5.4/§5.6.1
5. `ret` semantic 复核通过：`rdha = sign_extend(imms18)`、`expected_pc` = 弹出返回地址、弹栈移位效果写入 `expected_state.ra`
6. `jump`/`call` 的 encoding 经推演确认可解码执行无 fault（不 ILLI/不自跳/unmapped）；`ret-riii` 不生成 encoding 且 inventory 标注理由（布局限制）
7. legality 齐备：`jump-rrii`/`call-rrii` → `UNMAPPED`；`ret-riii` 冷 RA → `RASUF`；`call` 溢出 → `RASOF`（如适用）
8. 未改 `contracts/`；未生成/未改动 `ctrl-br`/`misc`/`reg-*`/`mem-*`
9. `python3 tools/testcases/validate_vectors.py` 零错误；`make check` PASS
10. （下游）QEMU harness 就绪后，active 测试全 PASS；记录该运行验收依赖
11. 未自行 commit

## 背景（完整）

### 目标

从零生成 `ctrl-jump`/`ctrl-call`/`ctrl-ret`，并用 `expected_pc` + `expected_state.ra` 把 PC 与 RA 效果都变成可断言的 active 向量，消除 F7 的 PC-only deferred 缺口。

### 设计理由

- `expected_pc`（F7 方案 (i)）使「只改 PC」的指令可断言；`call` 的 RA 压栈本就可在 `expected_state.ra` 观测，故 F7 的 5 条全部可 active。
- `ret` 语义可直接 active，本任务复核其 `expected_pc`/弹栈效果。

### 关键概念 / 数据

- **地址公式**（`contract-isa.md` §5.3/§5.4）：`jump/call imms24` → `rb0 + (imms24<<2)`；`jump/call rbha,rdhb,imms12` → `rbha + rdhb + (imms12<<2)`。
- **RegRAS**（§1.3.4/§5.6）：`ra63` 栈顶，高 16 位 = 引用计数（0 = 无效），低 48 位 = 返回地址；`call` 压入 `PC+4`，首次压栈计数设 `0x0001`。
- **`ret`**（§5.5）：`rdha = sign_extend(imms18)`；`PC = ra63` 低 48 位；`ret rd0,0` 合法。
- **fault**：`RASOF 0x8A`/`RASUF 0x8B`/`IALIGN 0x8D`/`UNMAPPED 0x87`（ADR-0004 D5.8）。
- **`rb0` = 当前指令地址**（ADR-0004 D6.5），故 `PC+4` 与相对目标均可算。

### 上游引用

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-028a-control-flow-yaml-tdd.md`（内容溯源，非执行依赖）

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **助记符**：`jump`/`call`/`ret` 保留；格式/编码按 0.5.3 QFC 重建。
2. **地址公式**：v5 `PC = rb0 + (imm<<2)`；ADR-0004 D6.5 冻结 `rb0`=当前指令地址 → encoding 用 `imm=1`。
3. **故障语义**：`jump-rrii`/`call-rrii` addr=0 → unmapped `0x87`；`ret` 冷 RA → `RASUF 0x8B`；0628 的「addr=0 → ILLI」**不适用**。
4. **`expected_pc`（v5 新增）**：PC 效果用该字段；`call` 压栈用 `expected_state.ra`。
5. **实现层 PC bug 修复**属 qemu 模块，本任务只保证向量数据。

## 已知坑 / 结论

1. **`imm=1` 避免自跳**；`jump-rrii`/`call-rrii` 用 `rb0` 基址 + `imms12=1`。
2. **`call` 的返回地址 = PC+4**（`rb0` = 当前指令地址）。
3. **`ret-riii` 无 encoding**：返回目标依赖布局，单指令不可构造；覆盖率由 semantic/legality 满足（非恒 fault）。
4. **`ret` 弹栈移位**：§5.6.2 case 2 的 shift-down 语义须逐条推演（上一版曾按 shift-down 推出 `ra63` 变无效）。
5. **不自行 commit**：完成后等待审查。

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
