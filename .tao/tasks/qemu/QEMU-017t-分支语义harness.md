# QEMU-017t: 分支语义 harness 扩展

**模块**：qemu
**项目里程碑**：M1
**依赖**：`QEMU-015t`、`TESTCASES-008t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `QEMU-015t` 的 `tests/scripts/build_test_binary.py`、`tests/scripts/run_qemu_test.py`
  - `tests/vectors/isa/control-flow.yaml`（`TESTCASES-008t` 写入的 deferred semantic 桩）
  - `.tao/knowledge/contract-isa.md` §5（条件跳转/无条件跳转偏移语义）
  - `contracts/opcodes.yaml`（分支/跳转 0.5.3 编码与格式）
- 输出：
  - `tests/scripts/build_test_binary.py`：新增 `build_branch_test_binary()` 与 `branch_behavior` 调度
  - `tests/vectors/isa/control-flow.yaml`：激活 ≥16 条 branch/jump semantic 测试（由本任务与 `TESTCASES` 协同，数据修改以 `TESTCASES` 归属为准）
- 约束：
  - 只加函数，不改现有 `build_test_binary()` / `emit_state_compare()` 逻辑
  - `run_qemu_test.py` 不改（`branch_behavior` 由 builder 内部处理）
  - **offset 必须从 `contract-isa.md` §5 手推**，不能从 QEMU 行为反推

## 背景（完整）

### 目标

1. 扩展 `build_test_binary.py`：支持 branch/jump 语义测试的 binary layout。
2. 激活 `control-flow.yaml` 的 branch/jump semantic 测试（`TESTCASES-008t` 已标记为 deferred 的桩）。

### 设计理由

`emit_state_compare` 假设被测指令后顺序执行；分支/跳转 taken 时会跳过后续比较代码，两种场景都需要专用 binary layout。用 **poison pattern** 把「是否跳转」变成「是否踩到 `illi`」的可观测退出码。

### 关键概念 / 数据

**branch-taken pattern**（验证跳转实际发生）：

```
[setup registers]
[branch instruction]  ← target = PC + 2 words（跳过 poison）
[illi]                ← poison：NOT taken 路径进入 ILLI → 测试失败
[emit_exit(0)]        ← taken 路径正常退出
```

**branch-not-taken pattern**（验证条件不满足时不跳）：

```
[setup registers]
[branch instruction, imm=+1]  ← 若 taken，跳到 illi → ILLI → FAIL
[emit_exit(0)]                ← not taken 路径正常退出
[illi]                        ← poison：taken 路径进入 ILLI
```

**`branch_behavior` 字段**：`taken` / `not_taken`；`build_test_binary(case)` 检测到该字段时调用 `build_branch_test_binary(case)`。

**offset 字段**：从 `contract-isa.md` §5 与 `contracts/opcodes.yaml` 的格式字段手推（PC-relative 单位/基准须以 v5 合约与 `TESTCASES-008t` 结论为准）。

**覆盖范围**（每条 taken + not-taken）：`br.n`/`br.nn`/`br.z`/`br.nz`/`br.p`/`br.np`（riii，单寄存器）+ `br.eq`/`br.ne`（rrii，双寄存器），以及 `jump-iiii`/`jump-rrii`（无条件）。call/ret 由 `QEMU-018t` 处理。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-029a-control-flow-semantic-harness.md`（完整转述：背景、设计原则 poison pattern、`build_branch_test_binary` 改动、yaml 规范与覆盖矩阵、约束、验收、完成区、代码级 Architecture Review）
- DADAO-0628：`code-agent/tasks/DL-028a-control-flow-yaml-tdd.md`（deferred 桩来源）
- DADAO-0628：`tests/scripts/build_test_binary.py`（形态参考，禁止复制正文）

## 交付物

- `tests/scripts/build_test_binary.py`：`build_branch_test_binary()` + `branch_behavior` 调度
- `tests/vectors/isa/control-flow.yaml`：激活 ≥16 条 branch/jump semantic 测试（与 `TESTCASES` 协同）
- 完成区附激活前后 PASS/FAIL 与条数

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **助记符**：`brn/brnn/brz/brnz/brp/brnp` → `br.n/br.nn/br.z/br.nz/br.p/br.np`；`breq/brne` → `br.eq/br.ne`；`unimp` → `illi`。另有 0.5.3 新增 `br.z-rb`/`br.nz-rb`（本任务按 `TESTCASES-008t` 范围决定是否覆盖）。
2. **跳转偏移语义**：v5 `contract-isa.md` §5 为 `PC = rb0 + (imm << 2)`；分支/跳转/调用均相对 `rb0`。`rb0` 语义（当前 vs 下一条）以 v5 合约与 `TESTCASES-008t` 结论为准，**不得沿用 0.4.1 的 `pc_next` 假设**。
3. **branch target 公式修复属实现层**：0.4.1 在 `translate.c` 修 `pc_next→pc_next+4`；v5 该修复属 `qemu` 模块（`QEMU-012t`），本任务只保证向量与 harness 正确。
4. **编码来源**：0.4.1 yaml 里手写 `0x2A04XXXX` 等；v5 分支编码从 `contracts/opcodes.yaml` + 手推 offset 得出，不复制 0.4.1 字节。
5. **向量归属**：semantic 测试数据在 `TESTCASES-008t` 桩基础上激活；本任务以 harness 扩展为主，数据修改须与 `TESTCASES` 边界一致。

## 已知坑 / 结论

摘自 DADAO-0628 DL-029a 完成区与代码级 Architecture Review：

1. **poison pattern 正确性**：taken pattern 中 branch taken → 跳过 `illi` → exit=0；NOT taken → 踩 `illi` → ILLI。not-taken pattern 反之。
2. **offset 手推**：必须从 spec 手推（`DL-029a` 完成区发现并修复了 0.4.1 QEMU 的 branch target 公式 bug，`pc_next-4 → pc_next+4`），**不能从 QEMU 行为反推**。
3. **`jump-rrii` setup**：用 `rb` + `rd` 计算目标；0.4.1 用 `load_reg` + snapshot 偏移，v5 按 0.5.3 格式重算。
4. **调度不干扰算术路径**：`if 'branch_behavior' in case` 才走 branch builder，否则走原路径。
5. **0.4.1 基线 34/34 active PASS**（18 semantic + 10 encoding + 3 ILLI + 3 legality）；v5 以自身向量为准。
6. **call/ret 不在本任务**：`DL-029a` 明确 deferred 到 `DL-030a`（v5 对应 `QEMU-018t`）。
7. **encoding 测试不自跳**：条件分支 `imm=0` 等效 NOP，避免无限循环；semantic 测试才用 poison 偏移。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-029a-control-flow-semantic-harness.md`
- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-028a-control-flow-yaml-tdd.md`
- DADAO-0628：`.work/DADAO-0628/tests/scripts/build_test_binary.py`
- 本项目：`.tao/knowledge/contract-isa.md` §5、`contracts/opcodes.yaml`、`tests/vectors/isa/control-flow.yaml`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `build_branch_test_binary()` 实现 taken/not-taken 两种 layout，poison 用 `illi`
2. `branch_behavior` 调度存在，且不改变原有算术/访存路径
3. ≥16 条 branch/jump semantic 测试激活并 PASS（8 条条件分支各 2 + `jump-iiii`/`jump-rrii`）
4. `python3 tests/scripts/run_qemu_test.py tests/vectors/isa/control-flow.yaml`：encoding 测试继续 PASS + semantic 测试 PASS，0 FAIL
5. offset 计算在完成区给出从 `contract-isa.md` §5 的手推依据
6. `tests/vectors/isa/rd-arith.yaml` 回归不破坏

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
