# QEMU-017t: 分支语义 harness 扩展

**模块**：qemu
**项目里程碑**：M1
**依赖**：`QEMU-015t`、`TESTCASES-005t`
**状态**：已验证

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
- 22/22 semantic 逐条 PASS（ctrl-br 20 + ctrl-jump 2）
- 12/12 encoding 逐条 PASS（ctrl-br 10 + ctrl-jump 2）
- 双向反例门控：taken+wrong delta → ILLI(0x88) FAIL ✓；not-taken+wrong delta → ILLI(0x88) FAIL ✓
- not-taken 偏移敏感性：imm=+1 → 假 PASS（taken 输入跳到 trampoline 而非 illi）；imm=+2 → 正确 FAIL
- 全量回归：597/562/29/5/1（与基线完全一致，零新增失败）

**修改文件**：
- `tests/scripts/build_test_binary.py`（唯一改动）
  - 新增 `encode_illi()`（L119-121）：illi 指令编码 0x00000000
  - 新增 `encode_jump_iiii(imms24)`（L123-126）：jump-iiii 指令编码，op=0x70
  - 新增 `build_branch_test_binary(case, dump_mode)`（L412-467）：分支/jump 语义测试 binary builder
    - TAKEN layout（delta=8）：`[loader][branch][illi][exit section]`
    - NOT-TAKEN layout（delta=4）：`[loader][branch][trampoline jump→exit][illi][exit section]`
  - 修改 `build_test_binary()`（L481-483）：`expected_pc` 非 null 时调度到 `build_branch_test_binary`

**验收结果**：

| # | 验收项 | 结果 | 证据 |
|---|--------|------|------|
| 1 | `build_branch_test_binary()` 实现 taken/not-taken 两种 layout，poison 用 `illi`；not-taken 偏移为 **`+2`** | ✓ | 代码审查 + layout 偏移验证输出（见下方） |
| 2 | `expected_pc` 调度存在（非 null 时走 branch builder），且不改变原有算术/访存路径 | ✓ | 代码 L481-483 调度；encoding 测试全 PASS；arithmetic 回归无新增失败 |
| 3 | 22 条 branch/jump semantic 测试**真实**判定并 PASS | ✓ | 改前真空 PASS → 改后真实 PASS 对比（改前：expected_pc 完全忽略，二进制不变；改后：双向反例 FAIL 证明 poison 生效） |
| 4 | encoding 继续 PASS + semantic PASS，0 FAIL | ✓ | 12 encoding + 22 semantic = 34/34 PASS |
| 5 | offset 计算从 `contract-isa.md` §5 手推 | ✓ | `Addr = rb0 + (imm<<2)`，基址=分支自身地址（v5）；imm=2 → target = PC+8 = +2 words |
| 6 | `reg-arith.yaml` 回归不破坏 | ✓ | 全量 597/562/29/5/1 零新增 |
| 7 | **反例门控**：taken↔not-taken delta 互换 → FAIL | ✓ | taken+delta4 → 0x88 FAIL；not-taken+delta8 → 0x88 FAIL |

**Layout 偏移验证**（NOT-TAKEN delta=4，loader=1 word）：
```
[0] 0x4C040001  ← loader (set.zw rd1, 1)
[1] 0x68040002  ← branch (br.n rd1, imm=2)
[2] 0x70000002  ← trampoline (jump imms24=2)
[3] 0x00000000  ← illi (poison)
[4] 0x4EF00000  ← exit section start
...
```
- branch target = word[1]+2 = word[3] = illi ✓
- trampoline target = word[2]+2 = word[4] = exit start ✓

**改前真空 PASS 证据**：
```python
# 改前 build_test_binary() 不检查 expected_pc，二进制与 expected_pc 值无关：
case['expected_pc'] = '0xFFFF00000008'  → blob = build(case)
case['expected_pc'] = '0xFFFF00000004'  → blob2 = build(case)
assert blob == blob2  # True — expected_pc 完全被忽略
```

**反例门控真实输出**：
```
=== Anti-example 1: taken input + wrong delta=4 ===
  taken+delta4: exit=0x88 → FAIL (Unexpected fault: ILLI (0x88))
=== Anti-example 2: not-taken input + wrong delta=8 ===
  not-taken+delta8: exit=0x88 → FAIL (Unexpected fault: ILLI (0x88))
=== Correct: taken+delta8 ===
  taken+delta8: exit=0x00 → PASS (Test passed)
=== Correct: not-taken+delta4 ===
  not-taken+delta4: exit=0x00 → PASS (Test passed)
```

**not-taken 偏移敏感性真实输出**：
```
=== Taken input, correct imm=2 (target = illi at +2): ===
  imm=2 (correct poison): exit=0x88 → FAIL (Unexpected fault: ILLI (0x88))
=== Taken input, WRONG imm=1 (target = trampoline at +1, not illi): ===
  imm=1 (false PASS risk): exit=0x00 → PASS (Test passed)
```
⇒ imm=+1（0628 的偏移）导致 taken 输入假 PASS；imm=+2（v5 的偏移）正确拦截。

**22 条 semantic 逐条结果**：
```
✓ ctrl-br[ 1] br.n     taken     → PASS
✓ ctrl-br[ 2] br.n     not-taken → PASS
✓ ctrl-br[ 4] br.nn    taken     → PASS
✓ ctrl-br[ 5] br.nn    not-taken → PASS
✓ ctrl-br[ 7] br.z     taken     → PASS
✓ ctrl-br[ 8] br.z     not-taken → PASS
✓ ctrl-br[10] br.nz    taken     → PASS
✓ ctrl-br[11] br.nz    not-taken → PASS
✓ ctrl-br[13] br.p     taken     → PASS
✓ ctrl-br[14] br.p     not-taken → PASS
✓ ctrl-br[16] br.np    taken     → PASS
✓ ctrl-br[17] br.np    not-taken → PASS
✓ ctrl-br[19] br.eq    taken     → PASS
✓ ctrl-br[20] br.eq    not-taken → PASS
✓ ctrl-br[22] br.ne    taken     → PASS
✓ ctrl-br[23] br.ne    not-taken → PASS
✓ ctrl-br[25] br.z-rb  taken     → PASS
✓ ctrl-br[26] br.z-rb  not-taken → PASS
✓ ctrl-br[28] br.nz-rb taken     → PASS
✓ ctrl-br[29] br.nz-rb not-taken → PASS
✓ ctrl-jump[ 1] jump-iiii  taken → PASS
✓ ctrl-jump[ 3] jump-rrii  taken → PASS
```

**新发现/坑**：
1. **not-taken layout 必须用 trampoline**：exit 段是多字（10 words），branch imm=2 的目标 = branch+2 words，会落入 exit 段内部而非 poison。必须在 branch 后插入单字 trampoline `jump-iiii` 跳到 exit 段，让 illi 精确占据 branch+2 的位置。
2. **v5 偏移 +2（非 0628 的 +1）**：v5 分支基址 = 分支自身地址（`translate.c` 的 `pc_next += 4` 在 `decode_insn` 之后），故 imm=1 → target = PC+4 = branch+1 word。0628 的 `+1` 会让 taken 分支跳到 trampoline 而非 illi，导致假 PASS。
3. **`jump-iiii` 编码**：`imms24` 直接填入 bits[23:0]（4×6bit 拼接），`(0x70 << 24) | (imms24 & 0xFFFFFF)` 即可。
4. **exit 段不改**：`build_exit_section` 在 `expected_state={}` 时 ACCUM=0 → br.nz 不跳 → 写0x00 PASS。branch 语义由 poison pattern 承担，exit 段只负责写退出码。

**遗留问题**：
- **交接给 `QEMU-018t`**：`expected_pc is not None` 的调度**不限助记符**，故 `ctrl-call`/`ctrl-ret` 的 semantic 用例也会被路由进 `build_branch_test_binary()`。`call` 与 taken layout 同构无碍；但 **`ret`（`delta=4`）用 not-taken layout 语义不适配**，`018t` 须为 call/ret 设计专用 layout（`ADR-0009 D6` 已规定 call/ret 用「`call→ret→landing` 往返」隐式验证 RA）。

## 审阅记录

### 第 1 轮 reviewer 验收（2026-09-21，独立重跑）

**审查对象**：`tests/scripts/build_test_binary.py` 工作区改动（未提交，`git diff` = 71 行纯新增、0 删除）；对照任务验收 1–7、约束、`ADR-0009 D6` 补注、`contract-isa.md §5`。
**审查手段**：全部由 reviewer 亲自重跑，不采信完成区转述；日志 `.tao/logs/QEMU-017t-review-*.log` 与 `.work/log/qemu/QEMU-017t-review-*.log`。

#### 1. 双向反例门控（最关键，防恒真）

在 `/tmp/opencode/QEMU-017t/anti/` 造副本（**未改仓库 YAML**），副本与源逐字段比对 `DIFFERS=True`：

```
$ python3 run_cases_reviewer.py /tmp/opencode/QEMU-017t/anti/taken_wrong_nt.yaml
  [ 0] br.n class=semantic epc=0xFFFF00000004 exit=0x88 -> FAIL (Unexpected fault: ILLI (0x88))
  taken_wrong_nt.yaml: passed=0 failed=1                       # EXIT=1
$ python3 run_cases_reviewer.py /tmp/opencode/QEMU-017t/anti/nt_wrong_taken.yaml
  [ 0] br.n class=semantic epc=0xFFFF00000008 exit=0x88 -> FAIL (Unexpected fault: ILLI (0x88))
  nt_wrong_taken.yaml: passed=0 failed=1                       # EXIT=1
```

- 注入有效性：副本 `expected_pc` 由 `...008→...004` / `...004→...008`，`DIFFERS_1/2=True`（`tests/vectors/isa/ctrl-br.yaml` 零改动）。
- 正确配对 PASS：`ctrl-br[1]`（taken，delta=8）与 `ctrl-br[2]`（not-taken，delta=4）均 `exit=0x00 → PASS`。
- **结论**：v1「not-taken 恒真」缺陷已消除——taken 输入谎报 delta=4 现**真实 FAIL 0x88**，不再 PASS。

#### 2. 字节级布局核对（反解析，22/22 条）

`verify_layout_reviewer.py` 逐字解码，确认 `branch@len(loader)`、`branch 目标==illi 所在字`、`trampoline 目标==exit 段首字`、`illi==0x00000000`、`word[目标]==build_exit_section()[0]=0x4EF00000`；不-taken layout 逐字为 `[loader][branch imm=2][jump-iiii 0x70000002(imms24=2)][illi 0x00000000][exit 0x4EF00000...]`（`ctrl-br[2]` 实拍：`[1]branch(op=0x68,imm=2) [2]tramp=0x70000002(tgt=4) [3]illi=0x00000000 [4]exit0=0x4EF00000`）。**22 条全部 OK**。

- **任务书自相矛盾（非 engineer 缺陷）**：任务验收 2 的 `delta/4 == imm` 仅对 taken 成立（12 条：delta=8→imm=2 ✓）；10 条 not-taken 为 `delta=4` 而 `imm=2`，这是**验收 1 与背景明确要求的 `+2`**（delta=4 是顺序落空 PC，不是分支目标）。故按正确不变量核验：taken `imm*4==delta` 且目标==exit；not-taken `imm==2` 且目标==illi、trampoline imms24==2 且目标==exit。全部通过。
- 源码佐证（`translate.c:397-407`）：`decode_insn(ctx, insn)` 在 `ctx->base.pc_next += 4` **之前**，`gen_branch_taken` 取 `ctx->base.pc_next` → v5 基址 = 分支自身地址，`+2` 正确（`contract-isa.md §5` 的 `Addr = rb0 + (imm<<2)` 与之一致）。

#### 3. 偏移敏感性（证明 `+2` 是承重的）

- taken 输入 + not-taken layout + branch `imm=1`（0628 偏移，`/tmp` 副本）→ **假 PASS**：
  `exit=0x00 -> PASS`（跳 trampoline 而非 illi）。
- 同输入 + `imm=2` → `exit=0x88 -> FAIL`（正确拦截）。
- 临时改源码 `encode_jump_iiii(2)→(1)`（trampoline +1）：`ctrl-br[2] exit=0x88 FAIL`，`ctrl-br[1]` 仍 PASS；**已还原**，`sha256sum -c` = `OK`，还原后 `ctrl-br[2]` 复跑 `exit=0x00 → PASS`，`git status` 与还原前一致（仅 engineer 的 2 文件）。

#### 4. 22 semantic + 12 encoding 逐条（reviewer 亲跑）

- `ctrl-br.yaml`：30/30 PASS（10 encoding + 20 semantic）。
- `ctrl-jump.yaml`：5/5 PASS（2 encoding + 2 semantic + 1 legality，`exit=0x87 Expected UNMAPPED`）。
- 逐条清单见 `.tao/logs/QEMU-017t-review-ctrl-br-percase.log` / `-ctrl-jump-percase.log`；22 条 semantic 索引 1,2,4,5,7,8,10,11,13,14,16,17,19,20,22,23,25,26,28,29 + `ctrl-jump[1,3]` 全 `exit=0x00 → PASS`。

#### 5. 全量回归（`tests/vectors/isa/ --batch`）

```
$ python3 tests/scripts/run_qemu_test.py tests/vectors/isa/ --batch
Results: 597 total, 562 passed, 29 failed, 5 deferred, 1 errors     # EXIT=1
$ diff <baseline QEMU-016t-batch-review1.log> <QEMU-017t-review-batch.log>
IDENTICAL TO BASELINE
```

失败清单与基线**逐字节一致**：24 `mem-rd`（窄 load）+ 3 `ctrl-call`（[2],[6],[7]）+ 2 `misc`（[3],[5]），1 error `ctrl-ret[0]`（Timeout）。**零新增**。

#### 6. 约束核验（逐条）

| 约束 | 结果 | 证据 |
|------|------|------|
| 只改 `build_test_binary.py`（代码） | ✓ | `git status --porcelain` 仅 engineer 任务书 md + 该脚本 |
| `build_exit_section()` 未改 | ✓ | 与 HEAD 逐段 md5 一致（`c9e09bac…`） |
| `build_loader()`/`build_test_section()` 未改 | ✓ | md5 与 HEAD 一致（`79ca8492…`/`e3bbd1bf…`） |
| 算术/访存路径不受影响 | ✓ | `build_test_binary()` 仅新增 `expected_pc is not None` 前置调度；全量回归逐字节=基线 |
| `run_qemu_test.py` 不改 | ✓ | `git diff --name-only` 为空 |
| `tests/vectors/` 零改动 | ✓ | `git status --porcelain tests/vectors/` 为空 |
| 未 commit | ✓ | `git log` HEAD 仍为 `d30adaa` |
| 无临时文件入库/无 untracked | ✓ | `git status --porcelain` 无 `??` |
| offset 从 §5 手推、非 QEMU 反推 | ✓ | 代码 docstring/完成区给 `Addr = rb0 + (imm<<2)`、基址=分支自身；源码 `translate.c` 佐证 |

#### 7. 完成区核对

逐条对齐、无转述/夸大：
- 「22/22 semantic、12/12 encoding PASS」✓（reviewer 独立复跑一致）
- 双向反例 `0x88 FAIL` ✓；偏移敏感性 `imm=+1 → 假 PASS` ✓
- 全量 `597/562/29/5/1` 零新增 ✓
- Layout 偏移验证块（`[0]0x4C040001…[4]0x4EF00000`）✓ 与实拍逐字一致
- 「改前真空 PASS」：reviewer 用 `git show HEAD:` 的旧 builder 独立复现——`expected_pc` 仅在 8/4 间变化 blob **完全相同**，且 20 条 ctrl-br semantic 旧 builder **全 `exit=0x00 → PASS`**（真空），**claim 属实**
- 函数行号（`encode_illi` L119-121、`encode_jump_iiii` L123-126、`build_branch_test_binary` L412-467、调度 L481-483）✓ 与文件一致

#### 8. 反例门控自身有效性

reviewer 的验证手段**能失败**：第 1 项两条谎报副本均真实 `FAIL 0x88`（EXIT=1）；第 3 项 `imm=1` 假 PASS 与 `imm=2` FAIL 形成对照；第 3 项源码注入经 `sha256sum -c` 证明注入→还原闭环。

#### 观察（非阻断，供架构师）

- 调度条件 `expected_pc is not None` **不限助记符**，故 `ctrl-call`（delta=8）与 `ctrl-ret`（delta=4）semantic 也被路由进 `build_branch_test_binary`（本任务规格即如此写，且属 `QEMU-018t` 范围）。实测结果与基线一致（`ctrl-call[2,6,7]` FAIL、`ctrl-ret[0]` INCONCLUSIVE，零新增）；`call` 无条件跳转与 taken layout 同构，`call[1],[5]` 反而走完整 exit 比对后 PASS。**不影响本任务验收**，但 `QEMU-018t` 需注意 `ret` 用 not-taken layout 语义不适配。
- 任务验收 2 的 `delta/4 == imm` 表述需订正（见 §2）。

#### 判决

**Accepted**。22 语义 + 12 编码在我独立重跑下全部 PASS；双向反例真实 FAIL、偏移敏感性证 `+2` 承重且注入可失败；全量回归与基线逐字节一致、零新增；硬约束逐条守住；完成区与真实输出逐条对齐。唯一发现的 `delta/4 == imm` 表述问题属**任务书文本**自相矛盾（与验收 1 冲突），非 engineer 产出缺陷。
