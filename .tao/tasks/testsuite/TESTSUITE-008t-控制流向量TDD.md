# TESTSUITE-008t: control-flow 向量修复 + TDD 补全

**模块**：testsuite
**项目里程碑**：M1
**依赖**：`TESTSUITE-004t`

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `tests/vectors/isa/control-flow.yaml`（TESTSUITE-002t 向量）
  - `.tao/knowledge/contract-isa.md` §5（条件跳转/无条件跳转/函数调用/函数返回）
  - `.tao/knowledge/adr-0004-test-machine.md`（exit 协议、fault 可观测）
  - `verif/opcodes.yaml`（branch/jump/call/ret 编码与格式）
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
| exit=0x82 | 无条件跳转 rb0=0 → 跳到 addr=0 → halt rd0 → ILLI | jump_r/call_r/ret encoding 测试 |
| exit=0x82 | semantic imm=256 → binary 只有 ~40 指令，跳出范围 | 所有 semantic 测试 |

核心规则：**encoding 测试只验证指令能被解码执行，不依赖跳转目标的有效性**。

### 关键概念 / 数据

**1. 条件分支 encoding（riii / rrii）**

- 0628 最终保留 `imm=0`：分支目标 = `rb0 + (imm << 2)`；按 harness/实现约定 `rb0` 语义，`imm=0` 时目标为当前指令的下一条 → 等效 NOP → exit=0。
- 8 条：`br.n`/`br.nn`/`br.z`/`br.nz`/`br.p`/`br.np`（riii）+ `br.eq`/`br.ne`（rrii）。
- v5 编码公式：`word = (op<<24) | (ha<<18) | (hb<<12) | (hc<<6) | hd`；riii 的 imm 在 `hb+hc+hd`，rrii 的 imm 在 `hc+hd`。

**2. 无条件跳转 encoding（iiii）**

- `jump-iiii`：`PC = rb0 + (imms24 << 2)`；imm=0 → 下一条（等效 NOP）。
- `call-iiii`：同上。

**3. 寄存器间接跳转 encoding（rrii）**

- `jump-rrii`：`PC = rbha + rdhb + (imms12 << 2)`；rb0=0、rd0=0 → addr=0 → 执行 `illi 0` → ILLI。
- 推荐改法：`expected_fault: null → ILLI`，保留原 word，并在 notes 说明（rb0=0 → addr=0 → illi）。
- `call-rrii`：同上。

**4. return encoding（riii）**

- `ret-riii`：`PC = ra63 低 48 位`；RA 栈冷（0）→ PC=0 → `illi` → ILLI。
- 改 `expected_fault: null → ILLI`，notes 说明（RA cold = 0）。

**5. semantic 测试处理**

- 所有 semantic/boundary 类统一改 `status: deferred`，notes 追加 `— deferred: 需 branch-over-poison harness`。
- **不删除**，它们是后续 harness 任务的 TDD 桩。

**6. 新增 legality 测试桩（TDD）**

- `jump-rrii rb0,rd0,0`：addr=0 → ILLI（可 active 验证）
- `call-rrii rb0,rd0,0`：addr=0 → ILLI
- `ret-riii rd0,0`：RA=0 → ILLI

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
  - encoding 向量修复（条件分支/`jump-iiii`/`call-iiii` 免自跳；`jump-rrii`/`call-rrii`/`ret-riii` 期望 ILLI）
  - semantic/boundary 改 `status: deferred`（保留桩）
  - 新增 3 条 legality 桩
  - 追加 branch-over-poison TDD 设计注释

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **助记符**：`brn`/`brnn`/`brz`/`brnz`/`brp`/`brnp`/`breq`/`brne` → `br.n`/`br.nn`/`br.z`/`br.nz`/`br.p`/`br.np`/`br.eq`/`br.ne`；`unimp`→`illi`；另有 `br.z-rb`/`br.nz-rb` 变体。
2. **地址公式**：v5 `contract-isa.md` §5 为 `PC = rb0 + (imm << 2)`；分支/跳转/调用均为相对 `rb0`（48-bit 地址，无溢出）。`rb0` 是当前还是下一条，须与 v5 harness/实现约定核对（0628 取「下一条」，imm=0 → 等效 NOP）。
3. **PC 公式修复属实现层**：0628 在 `translate.c` 修 not-taken PC（`pc_next → pc_next+4`）与 branch target（`pc_next-4 → pc_next+4`）；v5 该修复属 qemu 模块任务，**不在本任务**，本任务只保证向量数据正确。
4. **harness 依赖**：`emit_branch_semantic_test()` / `run_qemu_test.py` 在 v5 属 qemu/verif 模块（待规划），本任务以数据正确性 + validator 为主验收。

## 已知坑 / 结论

摘自 DADAO-0628 DL-028a 完成区与代码级 Architecture Review：

1. **imm=0 + branch 等效 NOP**：只要分支目标为下一条，无论 taken 与否都推进，不触发无限循环。
2. **jump_r/call_r/ret 改 `expected_fault: ILLI`**：rb0=0 / RA cold=0 → addr=0 → `illi 0` → ILLI，使 QEMU 故障码与预期一致。
3. **semantic 不删除**：改为 deferred 作为后续 harness 的 TDD 桩。
4. **PC 公式 bug（实现层）**：not-taken 写 `pc_next`（不推进）会循环执行同一条；须写 `pc_next + 4`。
5. **最终 16/16 active PASS**（0628）；v5 以自身 harness 为准。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-028a-control-flow-yaml-tdd.md`（完整转述）
- DADAO-0628：`.work/DADAO-0628/tests/vectors/isa/control-flow.yaml`（形态参考，禁止复制数据）
- 本项目：`.tao/knowledge/contract-isa.md` §5、`verif/opcodes.yaml`、`.tao/knowledge/adr-0004-test-machine.md`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. 所有 active encoding 向量可解码执行且不无限循环、不触发非预期 fault
2. `jump-rrii`/`call-rrii`/`ret-riii` 的 `expected_fault: ILLI` 且 notes 说明原因
3. semantic/boundary 均为 `status: deferred` 且 `deferred_reason` 明确，测试桩未被删除
4. 新增 3 条 legality 桩，`status`/`expected_fault` 自洽
5. 追加 branch-over-poison TDD 设计注释
6. `python3 verif/validate_vectors.py` 零错误；`make check` PASS
7. （下游）QEMU harness 就绪后，active 测试全 PASS；本任务记录该运行验收依赖
8. 未自行 commit

## 完成区

**状态**：待开始
**Commit**：
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
