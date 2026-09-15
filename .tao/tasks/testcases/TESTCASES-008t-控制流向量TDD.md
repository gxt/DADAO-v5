# TESTCASES-008t: control-flow 向量修复 + TDD 补全

**模块**：testcases
**项目里程碑**：M1
**依赖**：`TESTCASES-004t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `tests/vectors/isa/control-flow.yaml`（TESTCASES-002t 向量）
  - `.tao/knowledge/contract-isa.md` §5（条件跳转/无条件跳转/函数调用/函数返回）
  - `.tao/knowledge/adr-0004-test-machine.md`（exit 协议、fault 可观测）
  - `contracts/opcodes.yaml`（branch/jump/call/ret 编码与格式）
- 输出：修复后的 `tests/vectors/isa/control-flow.yaml`
- 约束：
  - encoding 类必须使其可被解码执行且不无限循环、不误触发非预期 fault
  - 依赖跳转目标有效性的语义测试，若 harness 尚不支持则 `status: deferred`（保留为后续 TDD 桩，不删除）
  - 完成后不自行 commit

## 背景（完整）

### 目标

修复 control-flow 的 encoding 测试使其全 PASS；将依赖 branch-over-poison layout 的 semantic 测试推迟（deferred）；补写缺失的 TDD 测试桩。

### 设计理由

0628 `control-flow.yaml` 现有 28 条测试全部 FAIL，故障分三类：

| 故障类型 | 原因 | 受影响测试 |
|---------|------|-----------|
| timeout | 条件分支 imm=0 → 跳自身 → 无限循环 | brnn/brz/brnp/jump_i/call_i 等 encoding 测试 |
| exit=0x88 | 无条件跳转 rb0=0 → 跳到 addr=0 → halt rd0 → ILLI | jump_r/call_r/ret encoding 测试 |
| exit=0x88 | semantic imm=256 → binary 只有 ~40 指令，跳出范围 | 所有 semantic 测试 |

核心规则：**encoding 测试只验证指令能被解码执行，不依赖跳转目标的有效性**。

> 上表为 0628 在其旧内存映射下的现象；v5 的故障期望以 ADR-0004（unmapped `0x87`）与 `contract-isa.md` §5.6.2（RASUF）为准，见下。

### 关键概念 / 数据

**0. 前置语义（ADR-0004 D6.5 已冻结）**

- `rb0` 在指令执行时等于**当前指令地址**（PC 语义）；`_start` 第一条 retire 后 `rb0` 变为 `0xffff_0000_0004`。
- 相对控制流地址公式 `Addr = rb0 + (imm << 2)`（`imm` 为**字**偏移，`<<2` 转字节）：
  - `imm=0` → `Addr = rb0` → 跳到**自身** → 自跳死循环（harness 超时 = inconclusive）；
  - `imm=1` → `Addr = rb0 + 4` → **下一条指令** → fall-through（等效 NOP）✅；
  - `imm=-1` → `Addr = rb0 - 4` → 上一条 → 同样死循环。

  故 encoding 向量必须用 **`imm=1`**。
- 0628 的「`rb0` = 下一条、`imm=0` 等效 NOP」结论**不适用**。

**1. 条件分支 encoding（riii / rrii）**

- 用 `imm=1`（见前置语义）：分支 taken → 下一条；not taken → 下一条。两种情形都推进，不循环。
- 8 条：`br.n`/`br.nn`/`br.z`/`br.nz`/`br.p`/`br.np`（riii）+ `br.eq`/`br.ne`（rrii）。
- v5 编码公式：`word = (op<<24) | (ha<<18) | (hb<<12) | (hc<<6) | hd`；riii 的 imm 在 `hb+hc+hd`，rrii 的 imm 在 `hc+hd`。分支的操作数 rd 是**源**（可用 rd0；`br.z rd0` 恒真、`br.nz rd0` 恒假）。

**2. 无条件跳转 encoding（iiii）**

- `jump-iiii`：`PC = rb0 + (imms24 << 2)`；用 `imms24 = 1` → 下一条（等效 NOP）。
- `call-iiii`：同上；同时压入返回地址，随后落到下一条。

**3. 寄存器间接跳转（rrii，fault 期望）**

- `jump-rrii`：`PC = rbha + rdhb + (imms12 << 2)`；`rbha=rb0`、`rdhb=rd0`、`imms12=0` → addr=0。
- ADR-0004 D5.6：addr=0 不在 ROM/RAM/Exit → **取指 unmapped → `0x87`**；**不是** ILLI（0628 的「addr=0 → `illi 0` → ILLI」在 v5 不适用）。
- 改法：`expected_fault: null → UNMAPPED`，保留原 word，notes 说明（addr=0 → unmapped `0x87`）。
- `call-rrii`：同上。

**4. return（riii，fault 期望）**

- `ret-riii`：`PC = ra63 低 48 位`；ADR-0004 D2.1 复位 `ra0`–`ra63 = 0`（`ra0=0` → 仅 RegRAS）。
- contract-isa §5.6.2：`ra63` 高 16 位 = 0 且 `ra0` 低 48 位 = 0 → **RASUF（`0x8B`）**；**不是** PC=0/ILLI。
- 改法：`expected_fault: null → RASUF`，notes 说明（RA cold → RegRAS 空 → RASUF）。

**5. semantic 测试处理**

- 所有 semantic/boundary 类统一改 `status: deferred`，notes 追加 `— deferred: 需 branch-over-poison harness`。
- **不删除**，它们是后续 harness 任务的 TDD 桩。

**6. 新增 legality 测试桩（TDD，fault 期望）**

- `jump-rrii rb0, rd0, 0`：addr=0 → 取指 unmapped → `expected_fault: UNMAPPED`（可 active 验证）
- `call-rrii rb0, rd0, 0`：addr=0 → 取指 unmapped → `expected_fault: UNMAPPED`
- `ret-riii rd0, 0`（冷 RA）：`expected_fault: RASUF`

**7. TDD 设计注释（branch-over-poison pattern）**

```
# TDD DESIGN NOTE:
# 分支语义测试使用 "branch-over-poison" pattern：
#   [setup]
#   [branch cond, +1]   ← 若 taken，跳过 poison
#   [illi 0]            ← poison：若 NOT taken 则 ILLI
#   [emit_exit(0)]      ← taken 路径：正常退出
# 需 harness 新增 emit_branch_semantic_test() 支持此 layout，
# 向量字段需新增 branch_taken: true/false 标记。
```

### 上游引用

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-028a-control-flow-yaml-tdd.md`（完整转述：背景三类故障、encoding 修复规则、semantic 处理、legality 桩、TDD 设计注释、验收、完成区与代码级 Architecture Review）

## 交付物

- `tests/vectors/isa/control-flow.yaml`：
  - encoding 向量修复（条件分支/`jump-iiii`/`call-iiii` 用 `imm=1` 免自跳）
  - `jump-rrii`/`call-rrii` 的 addr=0 case 改 `expected_fault: UNMAPPED`；`ret-riii` 冷 RA case 改 `expected_fault: RASUF`
  - semantic/boundary 改 `status: deferred`（保留桩）
  - 新增 3 条 legality 桩（`UNMAPPED`/`UNMAPPED`/`RASUF`）
  - 追加 branch-over-poison TDD 设计注释

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **助记符**：`brn`/`brnn`/`brz`/`brnz`/`brp`/`brnp`/`breq`/`brne` → `br.n`/`br.nn`/`br.z`/`br.nz`/`br.p`/`br.np`/`br.eq`/`br.ne`；`unimp`→`illi`；另有 `br.z-rb`/`br.nz-rb` 变体。
2. **地址公式**：v5 `contract-isa.md` §5 为 `PC = rb0 + (imm << 2)`；分支/跳转/调用均为相对 `rb0`（48-bit 地址，无溢出）。ADR-0004 D6.5 已冻结 **`rb0` = 当前指令地址**，故 `imm=0` → 自跳死循环，encoding 用 `imm=1`（目标=下一条）；0628 的「`rb0`=下一条、imm=0 等效 NOP」**不适用**。
3. **PC 公式修复属实现层**：0628 在 `translate.c` 修 not-taken PC（`pc_next → pc_next+4`）与 branch target（`pc_next-4 → pc_next+4`）；v5 该修复属 qemu 模块任务，**不在本任务**，本任务只保证向量数据正确。
4. **故障语义**：`jump-rrii`/`call-rrii` 的 addr=0 → 取指 unmapped `0x87`（`expected_fault: UNMAPPED`），`ret` 冷 RA → RASUF `0x8B`；0628 的「addr=0 → ILLI」**不适用**（ADR-0004 D5.6/D2.1 + contract-isa §5.6.2）。
5. **harness 依赖**：`emit_branch_semantic_test()` / `run_qemu_test.py` 在 v5 属 qemu/integ 模块（qemu `QEMU-014t`~`019t`；`verif` 已解散），本任务以数据正确性 + validator 为主验收。

## 已知坑 / 结论

摘自 DADAO-0628 DL-028a 完成区与代码级 Architecture Review：

1. **`imm=1` + branch 等效 NOP**：ADR-0004 D6.5 冻结 `rb0`=当前指令地址，`imm=1` → 目标=下一条；无论 taken 与否都推进，不触发无限循环。
2. **`jump-rrii`/`call-rrii` → `expected_fault: UNMAPPED`**：addr=0 → 取指 unmapped `0x87`（ADR-0004 D5.6），**不是 ILLI**。
3. **`ret-riii` 冷 RA → `expected_fault: RASUF`**：contract-isa §5.6.2（`ra63` 高 16=0 且 `ra0` 低 48=0 → RegRAS 空 → RASUF `0x8B`），**不是 ILLI**。
4. **semantic 不删除**：改为 deferred 作为后续 harness 的 TDD 桩。
5. **PC 公式 bug（实现层）**：not-taken 写 `pc_next`（不推进）会循环执行同一条；须写 `pc_next + 4`。
6. **最终 16/16 active PASS**（0628）；v5 以自身 harness 为准。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-028a-control-flow-yaml-tdd.md`（完整转述）
- DADAO-0628：`.work/DADAO-0628/tests/vectors/isa/control-flow.yaml`（形态参考，禁止复制数据）
- 本项目：`.tao/knowledge/contract-isa.md` §5、`contracts/opcodes.yaml`、`.tao/knowledge/adr-0004-test-machine.md`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. 所有 active encoding 向量可解码执行且不无限循环、不触发非预期 fault；相对控制流立即数用 `imm=1`
2. `jump-rrii`/`call-rrii` 的 `expected_fault: UNMAPPED`、`ret-riii` 的 `expected_fault: RASUF`，且 notes 说明原因
3. semantic/boundary 均为 `status: deferred` 且 `deferred_reason` 明确，测试桩未被删除
4. 新增 3 条 legality 桩（`UNMAPPED`/`UNMAPPED`/`RASUF`），`status`/`expected_fault` 自洽
5. 追加 branch-over-poison TDD 设计注释
6. `python3 tools/testcases/validate_vectors.py` 零错误；`make check` PASS
7. （下游）QEMU harness 就绪后，active 测试全 PASS；本任务记录该运行验收依赖
8. 未自行 commit

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
