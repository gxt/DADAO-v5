# QEMU-017t: 分支语义 harness 扩展

**模块**：qemu
**项目里程碑**：M1
**依赖**：`QEMU-015t`、`TESTCASES-005t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `QEMU-015t` 的 `tests/scripts/build_test_binary.py`、`tests/scripts/run_qemu_test.py`
  - `tests/vectors/isa/ctrl-br.yaml`、`tests/vectors/isa/ctrl-jump.yaml`（`TESTCASES-005t` 写入的 semantic 向量）
  - `.tao/knowledge/contract-isa.md` §5（条件跳转/无条件跳转偏移语义）
  - `contracts/opcodes.yaml`（分支/跳转 0.5.3 编码与格式）
- 输出：
  - `tests/scripts/build_test_binary.py`：新增 `build_branch_test_binary()` 与 `expected_pc` 调度
  - `tests/vectors/isa/ctrl-br.yaml`、`tests/vectors/isa/ctrl-jump.yaml`：激活 ≥16 条 branch/jump semantic 测试（由本任务与 `TESTCASES` 协同，数据修改以 `TESTCASES` 归属为准）
- 约束：
  - 只加函数，不改现有 `build_test_binary()` / `build_exit_section()` 逻辑
  - `run_qemu_test.py` 不改（`branch_behavior` 由 builder 内部处理）
  - **offset 必须从 `contract-isa.md` §5 手推**，不能从 QEMU 行为反推

## 背景（完整）

### 目标

1. 扩展 `build_test_binary.py`：支持 branch/jump 语义测试的 binary layout。
2. 激活 `ctrl-br.yaml`/`ctrl-jump.yaml` 的 branch/jump semantic 测试（`TESTCASES-005t` 已生成的向量）。

### 设计理由

`build_exit_section` 假设被测指令后顺序执行；分支/跳转 taken 时会跳过后续比较代码，两种场景都需要专用 binary layout。用 **poison pattern** 把「是否跳转」变成「是否踩到 `illi`」的可观测退出码。

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
[branch instruction, imm=+2]  ← 若 taken，跳到 illi → ILLI → FAIL
[emit_exit(0)]                ← not taken 路径正常退出
[illi]                        ← poison：taken 路径进入 ILLI
```

> ⚠️ **not-taken 的偏移必须是 `+2`（不是 0628 的 `+1`）**：v5 基址 = 分支指令**自身**地址（`Addr = rb0 + (imm<<2)`；实测 `translate.c:406` 的 `pc_next += 4` 发生在 `decode_insn` **之后**，故 `trans_br` 期间 `pc_next` 即分支自身地址）。`imm=+1` 会让 taken 落到 `emit_exit(0)` → **假 PASS**。0628 的 `pc_next` 基准下才是 `+1`——**不得沿用**。

**`expected_pc` 字段 —— v5 按「相对 BINARY_BASE 的位移（delta）」消费**（2026-09-21 用户裁定；补注 `ADR-0009 D6`）：

- **不把 `expected_pc` 当绝对地址直接比对**（`ADR-0009 D6` 原文即规定「不直接比对 `rb0`，用 poison 路径间接断言」）
- 令 `delta = expected_pc - BINARY_BASE`（`BINARY_BASE = 0xFFFF_0000_0000`）。实测向量中 `delta ∈ {4, 8}`：
  - `delta == 8`（2 words）→ **taken**：用 taken pattern（branch 目标跳过 poison `illi`）
  - `delta == 4`（1 word）→ **not-taken**：用 not-taken pattern（branch 的 poison 目标是 `illi`，落空则顺序到 `emit_exit(0)`）
- **为什么必须按 delta**：harness 前置 **loader**（`input_state` 非空时 1–4 words），测试指令实际地址 = `BINARY_BASE + loader_words*4` ≠ `BINARY_BASE`。实测 `ctrl-br[1]`（`br.n` taken）loader=4 words → 测试指令在 `0xffff00000010`，而向量 `expected_pc = 0xFFFF00000008`（按 BINARY_BASE 算）——**绝对比对必然错**
- **实测反证（改前）**：`ctrl-br` 20 条 semantic 现**全部真空 PASS**——`expected_pc` 被 harness **完全忽略**、`expected_state: {}` 为空 → `ACCUM=0` → 写 `0x00`；`--case 1`（taken）PASS 只因 `br.n` 跳进了 exit 段恰好写 PASS，**分支行为零验证**
- 调度：`build_test_binary(case)` 检测到 `expected_pc` 非 null 时走 `build_branch_test_binary(case)`；否则原路径不变

**offset 字段**：从 `contract-isa.md` §5 与 `contracts/opcodes.yaml` 的格式字段手推（PC-relative 单位/基准须以 v5 合约与 `TESTCASES-005t` 结论为准）。

**覆盖范围**（每条 taken + not-taken）：`br.n`/`br.nn`/`br.z`/`br.nz`/`br.p`/`br.np`（riii，单寄存器）+ `br.eq`/`br.ne`（rrii，双寄存器），以及 `jump-iiii`/`jump-rrii`（无条件）。call/ret 由 `QEMU-018t` 处理。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-029a-control-flow-semantic-harness.md`（完整转述：背景、设计原则 poison pattern、`build_branch_test_binary` 改动、yaml 规范与覆盖矩阵、约束、验收、完成区、代码级 Architecture Review）
- DADAO-0628：`code-agent/tasks/DL-028a-control-flow-yaml-tdd.md`（deferred 桩来源）
- DADAO-0628：`tests/scripts/build_test_binary.py`（形态参考，禁止复制正文）

## 交付物

- `tests/scripts/build_test_binary.py`：`build_branch_test_binary()` + `expected_pc` 调度（**唯一改动文件**）
- **不改 vector YAML**：`ctrl-br.yaml`（20 条 semantic）与 `ctrl-jump.yaml`（2 条 semantic）**已 `status: active` 且 `expected_pc` 已填**（`delta ∈ {4,8}`），harness 扩展后即被真正验证——本任务**无数据缺口**（数据归 TESTCASES）
- 完成区附「激活前后」对比：改前 22 条**真空 PASS** → 改后按 poison pattern **真实判定**（并给真实输出）

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **助记符**：`brn/brnn/brz/brnz/brp/brnp` → `br.n/br.nn/br.z/br.nz/br.p/br.np`；`breq/brne` → `br.eq/br.ne`；`unimp` → `illi`。另有 0.5.3 新增 `br.z-rb`/`br.nz-rb`（本任务按 `TESTCASES-005t` 范围决定是否覆盖）。
2. **跳转偏移语义**：v5 `contract-isa.md` §5 为 `PC = rb0 + (imm << 2)`；分支/跳转/调用均相对 `rb0`。`rb0` 语义（当前 vs 下一条）以 v5 合约与 `TESTCASES-005t` 结论为准，**不得沿用 0.4.1 的 `pc_next` 假设**。
3. **branch target 公式修复属实现层**：0.4.1 在 `translate.c` 修 `pc_next→pc_next+4`；v5 该修复属 `qemu` 模块（`QEMU-012t`），本任务只保证向量与 harness 正确。
4. **编码来源**：0.4.1 yaml 里手写 `0x2A04XXXX` 等；v5 分支编码从 `contracts/opcodes.yaml` + 手推 offset 得出，不复制 0.4.1 字节。
5. **向量归属**：semantic 测试数据在 `TESTCASES-005t` 基础上激活；本任务以 harness 扩展为主，数据修改须与 `TESTCASES` 边界一致。

## 已知坑 / 结论

摘自 DADAO-0628 DL-029a 完成区与代码级 Architecture Review：

1. **poison pattern 正确性**：taken pattern 中 branch taken → 跳过 `illi` → exit=0；NOT taken → 踩 `illi` → ILLI。not-taken pattern 反之。
2. **offset 手推**：必须从 spec 手推（`DL-029a` 完成区发现并修复了 0.4.1 QEMU 的 branch target 公式 bug，`pc_next-4 → pc_next+4`），**不能从 QEMU 行为反推**。
3. **`jump-rrii` setup**：用 `rb` + `rd` 计算目标；0.4.1 用 `load_reg` + snapshot 偏移，v5 按 0.5.3 格式重算。
4. **调度不干扰算术路径**：`if case.get('expected_pc') is not None` 才走 branch builder，否则走原路径。
5. **0.4.1 基线 34/34 active PASS**（18 semantic + 10 encoding + 3 ILLI + 3 legality）；v5 以自身向量为准。
6. **call/ret 不在本任务**：`DL-029a` 明确 deferred 到 `DL-030a`（v5 对应 `QEMU-018t`）。
7. **encoding 测试不自跳**：条件分支 `imm=0` 等效 NOP，避免无限循环；semantic 测试才用 poison 偏移。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-029a-control-flow-semantic-harness.md`
- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-028a-control-flow-yaml-tdd.md`
- DADAO-0628：`.work/DADAO-0628/tests/scripts/build_test_binary.py`
- 本项目：`.tao/knowledge/contract-isa.md` §5、`contracts/opcodes.yaml`、`tests/vectors/isa/ctrl-br.yaml`、`tests/vectors/isa/ctrl-jump.yaml`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

| # | 验收项 | 现在可跑 / BLOCKED | 说明 |
|---|--------|-------------------|------|
| 1 | `build_branch_test_binary()` 实现 taken/not-taken 两种 layout，poison 用 `illi`；not-taken 偏移为 **`+2`** | 现在可跑 | 代码审查 + 实测 |
| 2 | `expected_pc` 调度存在（非 null 时走 branch builder），且不改变原有算术/访存路径 | 现在可跑 | 代码审查 + `reg-arith` 回归 |
| 3 | 22 条 branch/jump semantic 测试**真实**判定并 PASS（`ctrl-br` 20 + `ctrl-jump` 2） | **现在可跑** | 原归因「需 `QEMU-008t` + harness（`020t`）」**已过时**（`008t` 已完成、`020t` 已关闭）。须给**改前真空 PASS → 改后真实 PASS** 的对比 |
| 4 | `run_qemu_test.py tests/vectors/isa/ctrl-br.yaml --batch`：encoding 继续 PASS + semantic PASS，0 FAIL | **现在可跑** | 同上 |
| 5 | offset 计算在完成区给出从 `contract-isa.md` §5 的手推依据（`Addr = rb0 + (imm<<2)`，基址=分支自身） | 现在可跑 | |
| 6 | `reg-arith.yaml` 回归不破坏 | **现在可跑** | 全量 batch 失败数须回到基线（24 `mem-rd` 窄 load + 3 `ctrl-call` + 2 `misc`；1 error `ctrl-ret`），**零新增** |
| 7 | **反例门控**：把 taken 向量的 `expected_pc` 由 `+8` 改 `+4`（或反之）→ 必须 FAIL；还原 → PASS | 现在可跑 | 证明 poison pattern 真的判定 taken/not-taken，非恒真 |

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
