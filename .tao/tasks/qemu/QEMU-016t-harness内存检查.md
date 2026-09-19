# QEMU-016t: harness `expected_state.memory` 验证

**模块**：qemu
**项目里程碑**：M1
**依赖**：`QEMU-015t`、`TESTCASES-004t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `QEMU-015t` 的 `tests/scripts/build_test_binary.py`（`emit_state_compare()`）
  - `tests/vectors/isa/*.yaml` 中带 `expected_state.memory` 的 store 向量
  - `TESTCASES-006t` 迁移后的 RAM 地址向量
  - `contracts/opcodes.yaml`（`ld.ub`/`ld.uw`/`ld.ut`/`ld.o` 等 load 指令编码）
- 输出：修改后的 `tests/scripts/build_test_binary.py`（`emit_state_compare()` 新增 memory 比对路径）
- 约束：
  - memory 比对使用**无符号** load（按宽度选 `ld.ub`/`ld.uw`/`ld.ut`/`ld.o`），对 raw 存储字节做 zero-extend 比对
  - 不修改 `n_patch`、不改 guard patching 节
  - 支持单条向量多个 memory entry（多字/多宽 store）
  - 不改 vector YAML

## 背景（完整）

### 目标

在 `emit_state_compare()` 中新增 memory 验证路径：对 `expected_state.memory` 每条 entry，把目标地址装入临时 RB，用宽度对应的**无符号** load 读实际内存到临时 RD，与期望值 XOR 后 ORR 进 mismatch 累加器。

### 设计理由

`QEMU-015t` 的 `emit_state_compare()` 只比较寄存器（`rd`/`rb`）；当 `expected_state` 只含 `memory` 时走 early-return 直接 `emit_exit(0)` 静默 PASS。所有 store 语义向量的 `expected_state.memory` 零验证——无论 QEMU 写了什么值都会通过，等于没测。

### 关键概念 / 数据

**变更 1 — 提取 memory 列表**：在函数开头 `rd`/`rb` 提取之后新增

```
memory = expected_state.get('memory', []) if expected_state else []
```

**变更 2 — early-return 条件**

```
旧：if not rd and not rb:
新：if not rd and not rb and not memory:
```

**变更 3 — memory 比对循环**（放在 rb 比对循环之后、guard patching 之前）：对每条 entry（含 `address`、`value`）：

```
load_reg(out, 'rb', TEMP_RB, int(entry['address'], 16))   # rb ← address
# 访存宽度按写入指令推导：从被测向量的 mnemonic 判断 store 宽度
#   st.b → 1B, st.w → 2B, st.t → 4B, st.o → 8B
#   stm.* → 按元素宽度（同上）
#   不依赖 schema 的 memory.width 字段（schema 不含 width）
width = derive_width_from_mnemonic(case['mnemonic'])
if   width == 1: 无符号字节 load   # ld.ub  rd, rb, 0
elif width == 2: 无符号 wyde load  # ld.uw  rd, rb, 0
elif width == 4: 无符号 tetra load # ld.ut  rd, rb, 0
else:            octa load         # ld.o   rd, rb, 0
expected_val = int(entry['value'], 16)
load_reg(out, 'rd', TEMP_RD_EXP, expected_val)   # rd ← expected
xor TEMP_RD_EXP, TEMP_RD_EXP, TEMP_RD            # = actual XOR expected
or  MISMATCH_ACC, MISMATCH_ACC, TEMP_RD_EXP      # 累加失配
```

具体 op/ha 与寄存器编号从 `contracts/opcodes.yaml` 与 `QEMU-015t` 选定的保留寄存器约定取得，**不硬编码 0.4.1 数值**。

**ROM store 行为（ADR-0004 D5.6）**：对 ROM 区域（`0xffff_ffff_0000`–`0xffff_ffff_ffff`）的 store 触发 **ILLI（`0x88`）**，不是静默丢弃。harness 中涉及 ROM 地址的 store 向量须期望 `expected_fault: ILLI`，不得沿用 0628「只读区写入静默丢弃」行为。

**约束**：`n_before = len(out)//4` 在 guard patching 节开头采样（memory 循环之后），新增 memory 指令不影响 `n_patch`；每条 memory entry 独立循环。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-022b-harness-memory-check.md`（完整转述：背景、目标、变更 1/2/3、约束、验收步骤、完成区、代码级 Architecture Review 与 P0/N1）
- DADAO-0628：`code-agent/tasks/DL-022c-vector-ram-addresses.md`（ROM→RAM 地址迁移前置）

## 交付物

- `tests/scripts/build_test_binary.py`：`emit_state_compare()` 的 memory 比对路径
- 完成区附「篡改一条 `expected_state.memory.value` → FAIL」的有效性验证记录

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **load 助记符/编码**：0.4.1 用 `ldbu/ldwu/ldtu/ldo`（op=0x40/0x41/0x42/0x33）；0.5.3 对应 `ld.ub`/`ld.uw`/`ld.ut`/`ld.o`，编码从 `contracts/opcodes.yaml` 取，**不复制 0.4.1 op 值**。
2. **store 助记符**：0.4.1 的 `stb/stw/stt/sto/stmo/stmb/stmw/stmt` → 0.5.3 的 `st.b`/`st.w`/`st.t`/`st.o`/`stm.*`；向量由 `TESTCASES` 交付。
3. **地址**：0.4.1 有 P0——10 条 store 向量用 ROM 地址导致写入被静默丢弃；v5 由 `TESTCASES-006t` 完成 RAM 地址迁移后再验证（本任务依赖它）。
4. **比较引擎**：0.5.3 的 `xor.o`/`or.o` 编码与 0.4.1 不同，从 `contracts/opcodes.yaml` 取；保留寄存器编号沿用 `QEMU-015t` 的 v5 约定。
5. **QEMU ROM store 行为**：v5 按 ADR-0004 D5.6——ROM store → ILLI（`0x88`），不是静默丢弃（0628 行为）。涉及 ROM 地址的向量须期望 ILLI fault。

## 已知坑 / 结论

摘自 DADAO-0628 DL-022b 完成区与代码级 Architecture Review：

1. **P0 — ROM 地址导致误判**：0.4.1 store 向量 `rb_base=0x100000`（ROM 只读），QEMU 静默丢弃写入，readback 得原始 ROM → XOR≠0 → 全 FAIL。**v5 按 ADR-0004 D5.6：ROM store → ILLI（`0x88`）**，不是静默丢弃。涉及 ROM 地址的 store 向量须期望 `expected_fault: ILLI`。RAM 地址迁移由 `TESTCASES-006t` 完成。
2. **必须用无符号 load**：`expected_state.memory.value` 是 raw 存储字节，比对时 zero-extend 即可，不能用带符号 load。
3. **early-return 修正**是防止静默 PASS 的关键：`and not memory`。
4. **临时寄存器复用**：0.4.1 用 `rb30`/`rd30`/`rd31`，若向量 `expected_state.rb` 含 `rb30` 或 `rd` 含 `rd30`/`rd31` 会误判；v5 须扫描向量占用后选保留寄存器并记入 convention。
5. **`n_patch` 不变**：memory 循环在采样点之前，不影响 guard patch 偏移；不得改动 patching 节。
6. **多 entry 支持**：多字/多宽 store 向量有 2 条以上 memory entry，须逐条循环比对。
7. **有效性验证**：篡改 `expected_state.memory.value` 后必须 FAIL，否则说明 memory 比对未真正生效。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-022b-harness-memory-check.md`
- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-021a-harness-semantic.md`
- DADAO-0628：`.work/DADAO-0628/tests/scripts/build_test_binary.py`
- 本项目：`contracts/opcodes.yaml`、`tests/vectors/isa/`、`.tao/knowledge/adr-0004-test-machine.md`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

| # | 验收项 | 现在可跑 / BLOCKED | 说明 |
|---|--------|-------------------|------|
| 1 | 纯 memory 向量（无 rd/rb 期望）不再静默 PASS，memory 比对路径被激活 | BLOCKED | 原因：需 `QEMU-015t` 完成 + harness 可用（`020t`）。替代：代码审查 |
| 2 | 所有 store 语义向量在 RAM 地址迁移完成后 PASS | BLOCKED | 同上 |
| 3 | 篡改一条 `expected_state.memory.value` → FAIL；改回 → PASS | BLOCKED | 同上 |
| 4 | 多 entry 向量（如 `stm.*`）所有 entry 均被比对 | BLOCKED | 同上 |
| 5 | `n_patch`/guard patching 节未被修改（diff 确认） | 现在可跑 | diff |
| 6 | 全量 semantic 向量回归 PASS | BLOCKED | 需 harness 可用（`020t`） |

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
