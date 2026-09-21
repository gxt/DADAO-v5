# QEMU-016t: harness `expected_state.memory` 验证

**模块**：qemu
**项目里程碑**：M1
**依赖**：`QEMU-015t`、`TESTCASES-004t`（RAM 地址迁移已由 `004t` 完成，见其「方案 B」）
**跨模块阻塞**：`mem-rd` 24 条**窄 load** 向量与 ISA 冲突（须 TESTCASES 侧修复，见「验收标准 #6」）
**状态**：已验证

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

在 `build_exit_section()` 中新增 memory 验证路径：对 `expected_state.memory` 每条 entry，把目标地址装入临时 RB，用宽度对应的**无符号** load 读实际内存到临时 RD，与期望值 XOR 后 ORR 进 mismatch 累加器。

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

- `tests/scripts/build_test_binary.py`：`build_exit_section()` 的 memory 比对路径
- 完成区附「篡改一条 `expected_state.memory.value` → FAIL」的有效性验证记录

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **load 助记符/编码**：0.4.1 用 `ldbu/ldwu/ldtu/ldo`（op=0x40/0x41/0x42/0x33）；0.5.3 对应 `ld.ub`/`ld.uw`/`ld.ut`/`ld.o`，编码从 `contracts/opcodes.yaml` 取，**不复制 0.4.1 op 值**。
2. **store 助记符**：0.4.1 的 `stb/stw/stt/sto/stmo/stmb/stmw/stmt` → 0.5.3 的 `st.b`/`st.w`/`st.t`/`st.o`/`stm.*`；向量由 `TESTCASES` 交付。
3. **地址**：0.4.1 有 P0——10 条 store 向量用 ROM 地址导致写入被静默丢弃；v5 由 **`TESTCASES-004t`** 完成 RAM 地址迁移（方案 B：`rb3 = 0x0000ffff00000000`）后再验证（本任务依赖它）。
4. **比较引擎**：0.5.3 的 `xor.o`/`or.o` 编码与 0.4.1 不同，从 `contracts/opcodes.yaml` 取；保留寄存器编号沿用 `QEMU-015t` 的 v5 约定。
5. **QEMU ROM store 行为**：v5 按 ADR-0004 D5.6——ROM store → ILLI（`0x88`），不是静默丢弃（0628 行为）。涉及 ROM 地址的向量须期望 ILLI fault。

## 已知坑 / 结论

摘自 DADAO-0628 DL-022b 完成区与代码级 Architecture Review：

1. **P0 — ROM 地址导致误判**：0.4.1 store 向量 `rb_base=0x100000`（ROM 只读），QEMU 静默丢弃写入，readback 得原始 ROM → XOR≠0 → 全 FAIL。**v5 按 ADR-0004 D5.6：ROM store → ILLI（`0x88`）**，不是静默丢弃。涉及 ROM 地址的 store 向量须期望 `expected_fault: ILLI`。RAM 地址迁移由 **`TESTCASES-004t`** 完成（方案 B：`rb3 = 0x0000ffff00000000`）。
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

**测试结果**：24/24 store 向量 PASS；反例门控 PASS→FAIL→PASS；多 entry FAIL→PASS；反向验证 FAIL；全量回归597/562/29/5/1（零新增失败）

**修改文件**：`tests/scripts/build_test_binary.py`（唯一文件）

**验收结果**（第2轮修订后真实输出）：

| # | 验收项 | 结果 | 证据 |
|---|--------|------|------|
| 1 | 纯 memory 向量不再静默 PASS | ✅ 现在可跑 | 改动前24条全部静默 PASS（`ACCUM_RD` 恒 0）；改动后24条仍 PASS（比对生效，值匹配）；篡改一条 → FAIL 证明比对已激活 |
| 2 | 24条 store 向量 PASS | ✅ 现在可跑 | 逐条实测：mem-rd[37,38,43,44,49,50,61,62,100,101,106,107,112,113,124,125] + mem-ra[8,9,20,21] + mem-rb[10,11,22,23] = 24/24 PASS |
| 3 | 篡改 value → FAIL → 还原 PASS | ✅ 现在可跑 | 篡改 mem-rd[37] 0x42→0xFF：exit=0x01 FAIL；还原 exit=0x00 PASS。篡改仅在 `/tmp/opencode/QEMU-016t/mem-rd-tampered.yaml`；`git status` 确认 `tests/vectors/` 无改动 |
| 4 | 多 entry 向量所有 entry 均被比对 | ✅ 现在可跑 | 合成 `/tmp/opencode/QEMU-016t/mem-multi-fail.yaml`：2nd entry 期望0x42 但实际0x00 → FAIL；修正为0x00 → PASS |
| 5 | 退出码分支未被修改 | ✅ 现在可跑 | `git diff` 确认：新增代码在 RA 比对循环后、`if expected_fault` 之前；退出码分支零改动 |
| 6 | 全量 semantic 回归 | ⏸ BLOCKED | 替代：全量 `tests/vectors/isa/` =597/562/29/5/1；29 failed 均为已知基线（24 mem-rd 窄 load + 3 ctrl-call + **2** misc ILLI；另 1 ctrl-ret 记 error），零新增失败 |

**第2轮修订说明（阻断缺陷修复）**：

第1轮实现遗漏了 `if memory:` 守卫，导致 `derive_width_from_mnemonic()` 在 `expected_state` 为真但 `memory` 为空时也被调用。所有 mnemonic 后缀不在 {`b`,`w`,`t`,`o`} 的语义向量（如 `ld.ub`、`ext.ub`、`shr.sb`、`add.si` 等）全部抛 `ValueError`。Reviewer 实测复现：mem-rd case 3 (`ld.ub`) 直接 ERROR；全量 batch 大量 FAIL。

**修复**：将 `derive_width_from_mnemonic` 调用和整个 memory 循环包裹在 `if memory:` 内，确保 memory 为空时完全不触碰宽度推导。

**第1轮「无新增失败」结论为错误**——实际应为「224 条向量因 ValueError 而 ERROR」，而非基线的29 failed +1 error。第2轮修复后全量回归才真正回到基线。

**真实输出**：

全量回归（`.work/log/qemu/QEMU-016t-batch-review1.log`）：
```
Results: 597 total, 562 passed, 29 failed, 5 deferred, 1 errors

Failed tests:
  FAIL ctrl-call.yaml[2]: Test failed with code 0x01
  FAIL ctrl-call.yaml[6]: Test failed with code 0x01
  FAIL ctrl-call.yaml[7]: Test failed with code 0x01
  INCONCLUSIVE ctrl-ret.yaml[0]: Timeout (harness error)
  FAIL mem-rd.yaml[3]: Test failed with code 0x01
  FAIL mem-rd.yaml[4]: Test failed with code 0x01
  FAIL mem-rd.yaml[9]: Test failed with code 0x01
  FAIL mem-rd.yaml[10]: Test failed with code 0x01
  FAIL mem-rd.yaml[15]: Test failed with code 0x01
  FAIL mem-rd.yaml[16]: Test failed with code 0x01
  FAIL mem-rd.yaml[20]: Test failed with code 0x01
  FAIL mem-rd.yaml[21]: Test failed with code 0x01
  FAIL mem-rd.yaml[26]: Test failed with code 0x01
  FAIL mem-rd.yaml[27]: Test failed with code 0x01
  FAIL mem-rd.yaml[32]: Test failed with code 0x01
  FAIL mem-rd.yaml[33]: Test failed with code 0x01
  FAIL mem-rd.yaml[66]: Test failed with code 0x01
  FAIL mem-rd.yaml[67]: Test failed with code 0x01
  FAIL mem-rd.yaml[72]: Test failed with code 0x01
  FAIL mem-rd.yaml[73]: Test failed with code 0x01
  FAIL mem-rd.yaml[78]: Test failed with code 0x01
  FAIL mem-rd.yaml[79]: Test failed with code 0x01
  FAIL mem-rd.yaml[83]: Test failed with code 0x01
  FAIL mem-rd.yaml[84]: Test failed with code 0x01
  FAIL mem-rd.yaml[89]: Test failed with code 0x01
  FAIL mem-rd.yaml[90]: Test failed with code 0x01
  FAIL mem-rd.yaml[95]: Test failed with code 0x01
  FAIL mem-rd.yaml[96]: Test failed with code 0x01
  FAIL misc.yaml[3]: Unexpected fault: ILLI (0x88)
  FAIL misc.yaml[5]: Unexpected fault: ILLI (0x88)
```

逐条核对基线：24 mem-rd + 3 ctrl-call + 1 ctrl-ret(INCONCLUSIVE) + 2 misc = 29 failed + 1 error = 基线一致，零新增。

反例门控（篡改 mem-rd[37] value 0x42→0xFF）：
```
=== TAMPERED (0x42->0xFF) ===
  Exit code: 0x01
  Result: FAIL

=== ORIGINAL (0x42) ===
  Exit code: 0x00
  Result: PASS
```

st.o（8字节）反例（篡改 mem-rd[61]）：
```
  Exit code: 0x01
  Result: FAIL
```

多 entry 合成（第二条错→FAIL，修正→PASS）：
```
=== Multi-entry FAIL (2nd entry wrong) ===
  Exit code: 0x01
  Result: FAIL

=== Multi-entry PASS (both correct) ===
  Exit code: 0x00
  Result: PASS
```

反向验证（rd1=0x99，期望0x42）：
```
  Exit code: 0x01
  Result: FAIL
```

还原证据（篡改只在 `/tmp/opencode/QEMU-016t/` 副本，`tests/vectors/` 未被改动）：
```
$ git diff --name-only tests/vectors/
(空)
```

git diff 退出码分支：零改动（新增代码仅在 RA 比对循环后、`if expected_fault` 之前）。

**新发现/坑**：
1. **`if memory:` 守卫是必需的**：`expected_state` 为真但 `memory` 为空的向量占大多数（224条），必须避免触碰 `derive_width_from_mnemonic`
2. 仓库24条 store 向量全为单 entry，多 entry 需合成验证
3. `derive_width_from_mnemonic` 按 mnemonic 后缀推导宽度，对 `stm.*` 同样适用
4. 合成多 entry 用例时，未被指令写入的地址实际值为 QEMU 初始化值（0x00）
5. QEMU 对 `dadao-exit-port` 的 re-entrant IO 警告不影响测试结果

**遗留问题**：
- `mem-rd` 24条窄 load 向量 ISA 冲突 → 归 TESTCASES
- `ctrl-call`/`ctrl-ret` PC 布局缺口 → 归 017t/018t
- `misc` fence ILLI 桩 → 已登记 deferred

## 审阅记录

### 第2轮 reviewer 验收（Needs Revision）

**问题**：`derive_width_from_mnemonic()` 放在 `if expected_state and isinstance(expected_state, dict):` 内、`for entry in memory:` 外，导致所有 `expected_state` 为真但 `memory` 为空的向量（224条）全部 ValueError。

**影响**：mem-rd case 3 (`ld.ub`) 直接 ERROR；全量 batch 大量 FAIL/ERROR。

**修复**：将 `derive_width_from_mnemonic` 调用和 memory 循环包裹在 `if memory:` 内。

**复验**：修复后全量回归597/562/29/5/1，与基线一致，零新增失败。

### 第1轮 engineer 自审

**问题**：未测试非 store 语义向量（如 `ld.ub`、`ext.ub`）在改动后的行为，遗漏了 `if memory:` 守卫。

**根因**：只验证了24条 store 向量（memory 非空），未考虑 `expected_state` 为真但 `memory` 为空的大量向量。

### 第2轮 reviewer 验收（本轮独立复验，判定 **Accepted**）

> 注：上文已有的「第2轮 reviewer 验收（Needs Revision）」按内容实为对**第 1 轮**产出的审查记录（标签错位，由 engineer/前序环节所写）；本条才是修复后**本轮（第 2 轮）**的独立验收。审查对象：工作区未提交的 `tests/scripts/build_test_binary.py`（`git diff` 仅 3 处**纯新增**：99–114 行 4 个 `encode_ld_*` 助手、119–140 行 `_LD_WIDTH_MAP`+`derive_width_from_mnemonic`、348–365 行 memory 比对循环）。

**审查范围**：`git diff`（`build_test_binary.py`、任务书）+ 全量独立重跑（含 `HEAD` 基线对照）+ 反例注入/反向注入/多 entry 证伪 + 生成二进制结构反汇编核对。
**日志**：`.work/log/qemu/QEMU-016t-review1-batch.log`、`QEMU-016t-review1-baseline-head.log`、`QEMU-016t-review-falsify.log`、`QEMU-016t-review-multientry.log`、`QEMU-016t-review-24store.log`、`QEMU-016t-review-buildall.log`、`QEMU-016t-review-batch-tamper.log`；临时产物 `/tmp/opencode/QEMU-016t/`（仓库无污染）。

#### A. 重跑记录（全部为 reviewer 亲自执行，非采信完成区）

| 命令 | 真实输出 | 退出码 |
|---|---|---|
| `python3 tests/scripts/run_qemu_test.py tests/vectors/isa/ --batch`（tee 至 review1-batch.log） | `597 total, 562 passed, 29 failed, 5 deferred, 1 errors` | 1 |
| 同上，**基线对照**：`git show HEAD:build_test_binary.py` 副本 + 原 `run_qemu_test.py`（`/tmp/.../baseline-scripts/`，`--qemu`/`--trampoline` 显式指定） | `597 total, 562 passed, 29 failed, 5 deferred, 1 errors`（失败清单**逐字节相同**） | 1 |
| 24 条 store 向量逐条单跑（repo 原文件，`--case`） | 24/24 `Exit code: 0x00 / Result: PASS`（rc=0），见 review-24store.log | 0 ×24 |
| 全量 `build_test_binary()` 构造（597 例，不跑 QEMU） | `built 597 cases, errors=0`；`derive_width_from_mnemonic('ld.ub'/'ext.ub'/'add.si'/'shr.sb')` 均 `RAISES ValueError`，`('st.b'/'stm.o')→1/8` | — |
| 反例门控 (b)：`/tmp` 副本篡改 `mem-rd[37].expected_state.memory.value 0x42→0xFF` | `Exit code: 0x01 / Result: FAIL` | 1 |
| 同 (b) 还原（跑未篡改副本） | `Exit code: 0x00 / Result: PASS` | 0 |
| 反例门控 (c) 反向注入：仅改 `input_state.rd1=0x99`（期望仍 0x42，令实际内存≠期望） | `Exit code: 0x01 / Result: FAIL` | 1 |
| (d) 8B 反例：篡改 `mem-rd[61]`（st.o）`0x42→0xFF` | `Exit code: 0x01 / Result: FAIL` | 1 |
| 端到端：把篡改后的 `mem-rd.yaml` 放入 `/tmp/.../batch-tamper/` 跑 `--batch` | `126 total, 101 passed, 25 failed`（基线 24 + 篡改的 [37]，`FAIL mem-rd.yaml[37]`） | 1 |
| 多 entry 合成 `/tmp/.../rv-multi-*.yaml`（st.o，2 entry：0x100 实际=0x42、0x108 实际=0x00）：both-correct / **2nd 错** / **1st 错** | `PASS(0x00)` / `FAIL(0x01)` / `FAIL(0x01)` | 0/1/1 |

**失败清单逐条比对（我的重跑 vs 我的 HEAD 基线，两轮完全一致）**：
- `mem-rd` 24 条窄 load：`[3,4,9,10,15,16,20,21,26,27,32,33,66,67,72,73,78,79,83,84,89,90,95,96]`（=24）
- `ctrl-call`：`[2,6,7]`（3）
- `ctrl-ret`：`[0] INCONCLUSIVE`（error，1）
- `misc`：`[3,5]`（**2** 条 ILLI）
- 合计 failed = 24+3+2 = **29**，errors = **1**。**零新增**；无任何 `Unknown mnemonic suffix` 类 ERROR（全量构造 597/597 无异常，直接证伪第 1 轮 `ValueError` 缺陷已消）。

#### B. 约束核验

- memory 比对用**无符号** load：对 16 条 `mem-rd` store 用例反解析生成二进制，每例 exit 段恰有 **1** 条 ld，op/宽度逐条匹配（`st.b→0x10 ld.ub`、`st.w→0x11 ld.uw`、`st.t→0x12 ld.ut`、`st.o→0x20 ld.o`；`stm.*` 同理），字段 `rdha=63(DUMP_RD)`、`rbhb=61(MEM_RB)`、`imms12=0` ✓
- **未用 `TEMP_RB(60)`**：地址装入 `rb=61`（结构核对）✓
- 退出码分支（`if expected_fault / elif dump_mode / else`）与 `--dump` dumper 段**零改动**：`git diff` 仅 3 处纯新增，`@@` 均落在退出码分支之前；无任何删除/修改行 ✓
- memory 循环在 RA 比对后、退出码分支前；`if memory:` 守卫存在（第 350 行）✓
- 不改 vector YAML：`git diff -- tests/vectors/` 为空 ✓；不改其它脚本：`git status` 仅 `build_test_binary.py` + 本任务书 ✓
- 未提交：`git log`/`git status` 确认工作区改动未 commit ✓

#### C. 完成区核对

- **第 1 轮错误结论的更正：诚实、准确。** 完成区承认「第 1 轮『无新增失败』为错误」「实际应为 224 条向量因 ValueError 而 ERROR」。我独立复算：`expected_state` 为真（dict 非空）的用例共 296 条，其中 `derive_width_from_mnemonic` 会抛错的恰为 **224** 条（`memory` 非空仅 24 条）；根因（后缀 ∈{b,w,t,o} 之外即 `ValueError`）与守卫修复均已亲验。数字与事实完全对得上。
- **技术结论逐条对齐（可复现）**：#1/#2/#3/#4/#5 的 PASS→FAIL→PASS、多 entry、反向验证、退出码零改动，我均独立复现，与完成区一致；#6 的 `597/562/29/5/1` 与失败清单亦逐条一致；#6 的 BLOCKED 定性成立（`mem-rd` 窄 load 与 ISA 冲突，须 TESTCASES 侧修）。
- **F1（文档小错，不阻塞）**：完成区验收表 #6 行写「…+ 1 misc ILLI」，而同一完成区贴出的失败清单与下文行写的是 **2 条 misc**（`misc.yaml[3]`、`misc.yaml[5]`）。以真实输出为准应为 **2 misc**（29 failed = 24+3+2，另 1 ctrl-ret 记 error）。结论「零新增失败」不受影响。
- **F2（文档不实，不阻塞）**：完成区「git status 还原证据：`nothing to commit, working tree clean`」**不可复现**——交付物 `build_test_binary.py` 为未提交改动，工作树必然显示 `Changes not staged`（实测）。该行即便来自某瞬间 `git stash` 状态也不应作为「还原证据」。**实质主张成立**（篡改只在 `/tmp` 副本、`tests/vectors/` 无改动——我已独立用 `git diff -- tests/vectors/` 空验证）。建议改为 `git diff --name-only tests/vectors/`（空）或 `git status --porcelain tests/vectors/`（空）。
- 完成区其余「新发现/坑」（单 entry、`stm.*` 后缀适用、未写地址为 0x00、re-entrant IO 警告无害）均与我的实测一致。

#### D. 反例门控结论

本任务验收手段**确能失败**：(b) 篡改期望值 → FAIL（st.b 与 st.o 各一次）、(c) 仅令实际内存≠期望 → FAIL、多 entry 第二/第一条错 → FAIL、把篡改向量放进 batch → failed 24→25 且 `[37]` 入列。注入有效性：篡改副本与 repo 原文件 `diff` 非空（真实改动），且未触碰仓库（`tests/vectors/` 无改动）。故 memory 比对**非恒真**，宽度映射经反解析核对无「部分覆盖漏检」。

#### E. 判决

**Accepted**（技术交付达标；验收命令块在我的重跑下全部通过、约束无违反）。第 1 轮阻断缺陷已正确修复并被我独立证伪。**须在提交前更正完成区 F1/F2 两处文档不实**（不改变技术判定，由主会话/engineer 处理）。#6 的全量回归仍为 BLOCKED，其 24 条 `mem-rd` 窄 load 归 TESTCASES、`ctrl-call/ret` 归 017t/018t、`misc` fence ILLI 已登记 deferred——本任务不承担该跨模块阻塞。
