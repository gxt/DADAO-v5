# QEMU-016t: harness `expected_state.memory` 验证

**模块**：qemu
**项目里程碑**：M1
**依赖**：`QEMU-015t`、`TESTCASES-004t`（RAM 地址迁移已由 `004t` 完成，见其「方案 B」）
**跨模块阻塞**：`mem-rd` 24 条**窄 load** 向量与 ISA 冲突（须 TESTCASES 侧修复，见「验收标准 #6」）
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `QEMU-015t` 的 `tests/scripts/build_test_binary.py`（**`build_exit_section()`**，比对逻辑内联于此）
  - `tests/vectors/isa/*.yaml` 中带 `expected_state.memory` 的 store 向量
  - `TESTCASES-004t` 迁移后的 RAM 地址向量（`rb3 = 0x0000ffff00000000`）
  - `contracts/opcodes.yaml`（`ld.ub`/`ld.uw`/`ld.ut`/`ld.o` 等 load 指令编码）
- 输出：修改后的 `tests/scripts/build_test_binary.py`（**`build_exit_section()`** 新增 memory 比对路径）
- 约束：
  - memory 比对使用**无符号** load（按宽度选 `ld.ub`/`ld.uw`/`ld.ut`/`ld.o`），对 raw 存储字节做 zero-extend 比对
  - 不改动退出码分支（`if expected_fault / elif dump_mode / else`）本身；memory 循环插在其**之前**
  - 支持单条向量多个 memory entry（多字/多宽 store）
  - 不改 vector YAML

## 背景（完整）

### 目标

在 `emit_state_compare()` 中新增 memory 验证路径：对 `expected_state.memory` 每条 entry，把目标地址装入临时 RB，用宽度对应的**无符号** load 读实际内存到临时 RD，与期望值 XOR 后 ORR 进 mismatch 累加器。

### 设计理由

`QEMU-015t` 的 `build_exit_section()` 只比较寄存器（`rd`/`rb`/`ra`）。当 `expected_state` 只含 `memory`（`rd`/`rb`/`ra` 均为空 dict）时，三个比对循环都不执行 → `ACCUM_RD` 恒为 0 → 写出 PASS（`0x00`）**静默通过**。仓库中 24 条 store 向量（`mem-rd` 16 + `mem-ra` 4 + `mem-rb` 4）的 `expected_state.memory` **零验证**——无论 QEMU 写了什么值都会通过，等于没测。

### 关键概念 / 数据

**变更 1 — 提取 memory 列表**：在函数开头 `rd`/`rb` 提取之后新增

```
memory = expected_state.get('memory', []) if expected_state else []
```

**变更 2 — 无 early-return 需改**（核实：v5 `build_exit_section()` **没有** `if not rd and not rb` 的 early-return；静默 PASS 由「三个比对循环都不执行 ⇒ `ACCUM_RD` 恒 0」产生）。本任务只需**新增 memory 比对循环**，无需改动任何 early-return 条件。

**变更 3 — memory 比对循环**（插在 **ra 比对循环之后、退出码分支之前**）：对每条 entry（含 `address`、`value`）：

```
# 地址装入 MEM_RB(61)。⚠️ 不得用 TEMP_RB(60)——它在 build_exit_section 开头
#   已被装入 exit port 地址，复用会破坏后续退出码写入。
words.extend(emit_load_imm64_rb(MEM_RB, int(entry['address'], 16)))   # rb61 ← address

# 访存宽度按被测向量的 mnemonic 推导（st.b→1B, st.w→2B, st.t→4B, st.o→8B；
#   stm.* → 按元素宽度，同上）。不依赖 schema 的 memory.width（schema 不含 width）。
width = derive_width_from_mnemonic(case['mnemonic'])

# 用宽度对应的**无符号** load 读实际内存到 DUMP_RD(63)：
#   1B→ld.ub(op 0x10)  2B→ld.uw(0x11)  4B→ld.ut(0x12)  8B→ld.o(0x20)
#   编码：op<<24 | rdha<<18 | rbhb<<12 | imms12
words.append(encode_ld_<size>(DUMP_RD, MEM_RB, 0))    # rd63 ← mem[rb61 + 0]

expected_val = int(entry['value'], 16)
words.extend(emit_load_imm64_rd(TEMP_RD, expected_val))          # rd60 ← expected
words.append(encode_xor_o(TEMP_RD, TEMP_RD, DUMP_RD))            # = actual XOR expected
words.append(encode_or_o(ACCUM_RD, ACCUM_RD, TEMP_RD))           # 累加失配
```

**寄存器约定**（`ADR-0009 D4` + `build_test_binary.py` 现状，**不得硬编码 0628 的 `rd30`/`rd31`/`rb30`**）：

| 常量 | 编号 | 用途 |
|---|---|---|
| `MEM_RB` | 61 | 内存地址（比对用） |
| `TEMP_RD` | 60 | 期望值 |
| `DUMP_RD` | 63 | 实际值（load 结果） |
| `ACCUM_RD` | 61 | XOR+ORR 累加器（RD bank，与 `MEM_RB` 不同 bank，无冲突） |

已核实：`tests/vectors/isa/*.yaml` **全量扫描无任何向量占用 rd60–63 / rb60–63**（`expected_state` 与 `input_state` 均无）。

**编码来源**：`contracts/opcodes.yaml` —— `ld.ub-rd` op=`0x10` / `ld.uw-rd` `0x11` / `ld.ut-rd` `0x12` / `ld.o-rd` `0x20`（`format: rrii`，字段 `rdha[23:18]`/`rbhb[17:12]`/`imms12[11:0]`）。**必须用无符号 load**（`ld.sb/sw/st` 为 signed，不可用）。

**ROM store 行为（ADR-0004 D5.6）**：对 ROM 区域（`0xffff_ffff_0000`–`0xffff_ffff_ffff`）的 store 触发 **ILLI（`0x88`）**，不是静默丢弃。harness 中涉及 ROM 地址的 store 向量须期望 `expected_fault: ILLI`，不得沿用 0628「只读区写入静默丢弃」行为。

**约束**：memory 循环内**每条 entry 独立处理**（各自装地址、各自 load 比对）；循环插在退出码分支之前，**不改动**退出码分支与 `--dump` 的 dumper 段。注：v5 harness **无** `n_patch` / guard patching 节（0628 机制），该约束不适用。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-022b-harness-memory-check.md`（完整转述：背景、目标、变更 1/2/3、约束、验收步骤、完成区、代码级 Architecture Review 与 P0/N1）
- DADAO-0628：`code-agent/tasks/DL-022c-vector-ram-addresses.md`（ROM→RAM 地址迁移前置）

## 交付物

- `tests/scripts/build_test_binary.py`：`emit_state_compare()` 的 memory 比对路径
- 完成区附「篡改一条 `expected_state.memory.value` → FAIL」的有效性验证记录

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **load 助记符/编码**：0.4.1 用 `ldbu/ldwu/ldtu/ldo`（op=0x40/0x41/0x42/0x33）；0.5.3 对应 `ld.ub`/`ld.uw`/`ld.ut`/`ld.o`，编码从 `contracts/opcodes.yaml` 取，**不复制 0.4.1 op 值**。
2. **store 助记符**：0.4.1 的 `stb/stw/stt/sto/stmo/stmb/stmw/stmt` → 0.5.3 的 `st.b`/`st.w`/`st.t`/`st.o`/`stm.*`；向量由 `TESTCASES` 交付。
3. **地址**：0.4.1 有 P0——10 条 store 向量用 ROM 地址导致写入被静默丢弃；v5 由 **`TESTCASES-004t`** 完成 RAM 地址迁移（方案 B：`rb3 = 0x0000ffff00000000`）后再验证（本任务依赖它）。
4. **比较引擎**：0.5.3 的 `xor.o`/`or.o` 编码与 0.4.1 不同，从 `contracts/opcodes.yaml` 取；保留寄存器编号沿用 `QEMU-015t` 的 v5 约定。
5. **QEMU ROM store 行为**：v5 按 ADR-0004 D5.6——ROM store → ILLI（`0x88`），不是静默丢弃（0628 行为）。涉及 ROM 地址的向量须期望 ILLI fault。

## 已知坑 / 结论

摘自 DADAO-0628 DL-022b 完成区与代码级 Architecture Review：

1. **P0 — ROM 地址导致误判**：0.4.1 store 向量 `rb_base=0x100000`（ROM 只读），QEMU 静默丢弃写入，readback 得原始 ROM → XOR≠0 → 全 FAIL。**v5 按 ADR-0004 D5.6：ROM store → ILLI（`0x88`）**，不是静默丢弃。涉及 ROM 地址的 store 向量须期望 `expected_fault: ILLI`。RAM 地址迁移由 `TESTCASES-006t` 完成。
2. **必须用无符号 load**：`expected_state.memory.value` 是 raw 存储字节，比对时 zero-extend 即可，不能用带符号 load。
3. **early-return 修正**是防止静默 PASS 的关键：`and not memory`。
4. **临时寄存器复用**：0.4.1 用 `rb30`/`rd30`/`rd31`（v5 编号不同，**不得照搬**）。v5 沿用 `ADR-0009 D4` scratch：`MEM_RB`=61（地址）、`TEMP_RD`=60（期望值）、`DUMP_RD`=63（实际值）、`ACCUM_RD`=61。**已全量扫描确认无向量占用 rd60–63 / rb60–63**。⚠️ **不得用 `TEMP_RB`(60) 装内存地址**——它在 `build_exit_section` 开头已装入 exit port 地址。
5. **插入位置**：memory 循环须在退出码分支之前（本任务在 `build_exit_section()` 内联实现）。v5 harness **无** `n_patch`/guard patching 节——0628 的该约束**不适用**。
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
| 1 | 纯 memory 向量（无 rd/rb/ra 期望）不再静默 PASS，memory 比对路径被激活 | 现在可跑 | 24 条带 `expected_state.memory` 的 store 向量（`mem-rd` 16 + `mem-ra` 4 + `mem-rb` 4）；**当前实测静默 PASS**（`ACCUM_RD` 恒 0） |
| 2 | 24 条 store 向量在 memory 比对启用后 PASS | 现在可跑 | RAM 地址迁移已由 `TESTCASES-004t` 完成（`rb3 = 0x0000ffff00000000`）；须给出**逐条**实测结果 |
| 3 | 篡改一条 `expected_state.memory.value` → FAIL；改回 → PASS | 现在可跑 | 反例门控，须附真实输出；**还原须含重建**（AGENTS.md） |
| 4 | 多 entry 向量所有 entry 均被比对 | 现在可跑 | 仓库向量**全为单 entry**（全量扫描确认）→ 须用**合成**多 entry 用例验证，并说明合成来源与还原 |
| 5 | 退出码分支未被修改（diff 确认） | 现在可跑 | diff |
| 6 | 全量 semantic 回归 PASS | **BLOCKED** | 原因：`mem-rd` **24 条窄 load** 向量与 ISA 冲突（ISA **大端+右对齐**，向量 golden 假定窄值在**低地址**；实测全 FAIL），须 **TESTCASES 侧先修**。替代：本任务以「#1–#5 + 24 条 store 向量 PASS」为准；全量回归待 TESTCASES 修复后由 `021m` 承担 |

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
