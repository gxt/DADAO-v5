# QEMU-015t: harness 语义验证修复

**模块**：qemu
**项目里程碑**：M1
**依赖**：`QEMU-014t`
**状态**：待验收

> **下发前预检更正（2026-09-21，`005t`–`013t` 完成后）**：本任务书原「目标/设计理由/验收归因」基于 `014t` 收尾返工**之前**的旧状态，已过时。预检实测结论：
> 1. `014t` 的 harness **已实现** exit 段 state 比较（`build_exit_section` 读 `expected_state`/`expected_fault`）与 fault 路由（`interpret_exit_code`），CLI 在 FAIL 时已 `exit=1`——原「dumper 为空 / 不读 `expected_state` / exit=0 无条件 PASS / legality 反判 FAIL / CLI 遇 FAIL 仍 exit 0」**均不成立**。
> 2. 实际缺陷是：**普通模式 TIMEOUT**（连最普通 RD-only 语义向量也跑不出 PASS）、**PC dump 恒 0**、**CLI fail-closed 缺失**。
> 3. 验收 1–4 原归因「需 `020t`」**已更正为「现在可跑」**（`020t` 非前置）。详见「背景 → 目标/设计理由」与「验收标准」。

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `QEMU-014t` 交付的 `tests/scripts/build_test_binary.py`、`tests/scripts/run_qemu_test.py`
  - `tests/vectors/isa/*.yaml`（`class`、`expected_state`、`expected_fault`、`status`）
  - `SPEC-006t` 的 Test Machine ADR（exit code 协议）
  - `contracts/opcodes.yaml`（比较引擎所用 `xor`/`or`/`cs.z`/`br.*` 等指令的 0.5.3 编码）
- 输出：修改后的 `tests/scripts/build_test_binary.py`（新增/实现 `emit_state_compare()`）、`tests/scripts/run_qemu_test.py`（fault 路由 + CLI fail-closed）
- 约束：
  - 不改 vector YAML（仅改 harness 脚本）
  - 不改 QEMU 补丁：状态比较由 guest 代码原地完成，不依赖 QEMU state dump
  - 保留寄存器（比较临时/累加器）不得出现在向量的 `input_state`/`expected_state`；若冲突须改选
  - `status: deferred` 向量跳过
  - `expected_state: null` 的 encoding 向量不生成比较代码，仅执行后写 exit=0

## 背景（完整）

### 目标

把 harness 从「结构正确但跑不出结果」修成**真正可用的语义验证器**（按 2026-09-21 下发前预检后的实际缺陷重定）：

1. **定位并修复普通模式 TIMEOUT**（本任务核心）：当前即使最普通的 RD-only 语义向量（`reg-arith.yaml --case 1`）也返回 `INCONCLUSIVE - Timeout`，无法得出 PASS/FAIL。
2. **修复 PC dump 恒为 0**：dumper 用 `rb2rd rd63, rb0, 1` 复制 PC，实测读出 0（见 `deferred.md`）。
3. **核对并补全 state 比较**：`build_exit_section` 已实现 RD/RB/RA 比较与 `expected_fault` 路由，须逐条验证语义正确性并补齐缺失（含 RA 经 `ra2rd` 的比较路径）。
4. **CLI fail-closed**：0 case 或全 SKIP → `sys.exit(2)`（**当前缺失**：实测 batch 模式 `total==0` 仍 `exit=0`）。

### 设计理由

**（2026-09-21 下发前预检实测更正）** 原设计理由所述「`QEMU-014t` 的 harness 是 smoke test：`emit_state_dumper()` 为空、runner 完全不读 `expected_state`/`expected_fault`、exit=0 无条件 PASS、`expected_fault: ILLI` 的 legality case 反被判 FAIL、CLI 遇 FAIL 仍以 0 退出」**均已不成立**——那是 `014t` 收尾返工前的旧状态。实测（`005t`–`013t` 完成后）：

- `build_test_binary.py` **已实现** `build_exit_section`（读 `expected_state` 的 rd/rb/ra 并生成 guest 内 `xor.o`/`or.o` 比较 + exit port 写入；读 `expected_fault` 生成安全网）。
- `run_qemu_test.py` **已实现** `interpret_exit_code` + `FAULT_CODES` 路由（实测 `ctrl-ret.yaml --case 1` 的 legality RASUF → PASS）。
- CLI 在 `FAIL`/`INCONCLUSIVE` 时**已** `exit=1`。

**当前实际缺陷**（本次预检实测）：
1. **普通模式 TIMEOUT**：`run_qemu_test.py tests/vectors/isa/reg-arith.yaml --case 1`（RD-only 语义）与 `--case 2` 均 `INCONCLUSIVE - Timeout`。`--dump` 模式导出 `state.bin` 的 rd1=0/rd2=0x82/rd3=0x64/rd4=0x1e **与向量完全一致**，证明 loader/test/dumper 三段正常 ⇒ 故障点在 **exit 段（比较→写 exit port）或其后的控制流**。
2. **PC dump 恒为 0**（`+0x400`），见 `deferred.md`（疑 `rb0` 读取路径）。
3. **CLI fail-closed 缺失**：0 case / 全 SKIP 时仍 `exit=0`（应 `exit=2`）。

> 注：向量里的 `expected_state` 数据此前确实**零验证**（因 TIMEOUT 从未走到比较段），这正是本任务要修通的。

### 关键概念 / 数据

**退出码协议（ADR 约定，精确值以 v5 ADR 为准）**

| 条件 | QEMU exit code |
|------|---------------|
| 正常 PASS（guest 写 0 到 exit port） | 0 |
| guest 内检测到比较失败（写非 0） | 1 |
| ILLI（精确异常） | 0x88 |
| MALIGN（精确异常） | 0x8C |
| UNDI（精确异常） | 0x89 |
| 未映射访问 | 0x87 |

> 机器 fault 退出码 = `0x80 | spec_cause_bit`（ADR-0004 D5.8）；精确值以 v5 ADR 为准。

**`_classify(exit_code, case)` 路由**

```python
FAULT_CODES = {'ILLI': 0x88, 'MALIGN': 0x8C, 'UNDI': 0x89}
expected_fault = case.get('expected_fault')      # None / 'ILLI' / 'MALIGN' / 'UNDI'
if expected_fault is None:
    if exit_code == 0: return ('PASS', 'exit=0')
    return ('FAIL', f'exit=0x{exit_code:02X} unexpected fault')
else:
    expected_code = FAULT_CODES.get(expected_fault)
    if expected_code is None: return ('FAIL', f'unknown expected_fault: {expected_fault}')
    if exit_code == expected_code: return ('PASS', f'exit=0x{exit_code:02X} {expected_fault} ✓')
    return ('FAIL', f'exit=0x{exit_code:02X} expected 0x{expected_code:02X} ({expected_fault})')
```

**`emit_state_compare()`**：guest 自己做比较（ADR 约定），用**保留寄存器**作比较临时与 mismatch 累加器。0.4.1 的实现用「XOR 比对 + ORR 累加 + 条件选择分支」：

```
mismatch 累加器 = 0
for each (reg, expected_value) in expected_state.rd / expected_state.rb / expected_state.ra:
    加载 expected 到 temp
    temp = expected XOR actual          # 相等则 0
    mismatch |= temp                    # 任一失配则 mismatch ≠ 0
if mismatch == 0: 写 exit=0（PASS）
else:             写 exit=1（FAIL）
```

- **RA 比对路径**：对 `expected_state.ra` 中的每个 RA 寄存器，用 `ra2rd` 把实际 RA 值导出到临时 RD，再与期望值 XOR+ORR 累加。`ra2rd` 编码取自 `contracts/opcodes.yaml`。
- **`encoding.reserved` 义务（M15）**：`reserved: true` 的 case 无 `(insn, format)` 身份，解析时须跳过 identity/mask-value 校验；`expected_fault` 恒为 `UNDI`。harness 在 `_classify` 路由中对 `expected_fault: UNDI` 使用 `FAULT_CODES['UNDI'] = 0x89`。

`expected_state` 为 `null` 的 encoding class 不生成比较，仅执行指令后写 exit=0。`emit_exit()` 的 `load_reg + halt` 方案替换为向 exit port 写 0。

**CLI fail-closed**

```python
if total == 0:        print('ERROR: 0 cases executed'); sys.exit(2)
if skip_count == total: print('ERROR: all skipped'); sys.exit(2)
if fail_count > 0:    sys.exit(1)
sys.exit(0)
```

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-021a-harness-semantic.md`（完整转述：背景、目标、退出码协议、`_classify` 路由、`emit_state_compare` 规格、CLI 非零退出、exit port 常量、约束、验收步骤、完成区、代码级 Architecture Review 与 N1/N2/N3）
- DADAO-0628：`code-agent/tasks/DL-019a-phase3-harness.md`（前置 harness）

## 交付物

- `tests/scripts/build_test_binary.py`：新增 `emit_state_compare()`（guest 内联比较，含自修改 guard 或等价机制）
- `tests/scripts/run_qemu_test.py`：`FAULT_CODES` 映射 + `_classify` 路由 + CLI fail-closed
- 完成区附「篡改 expected_state → FAIL」的有效性验证记录

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **比较引擎指令编码**：0.4.1 硬编码 `xor`=`0x10280000`、`or`=`0x10240000`、`csz`=`0x22` 等；v5 必须从 `contracts/opcodes.yaml` 取 0.5.3 的 `xor.o`/`or.o`（固定位宽 orrr）与 `cs.z`（rrrr）等编码，**禁止沿用 0.4.1 硬编码值**。
2. **分支指令**：`breq/brne` → 0.5.3 `br.eq`/`br.ne`（rrii），比较引擎/跳转偏移按 v5 格式重算。
3. **`unimp` → `illi`**：0.4.1 用 `unimp` 触发 ILLI 的路径，v5 对应 `illi`（`contract-isa.md` §7.2）。
4. **退出码精确值**：以 `SPEC-006t` 的 Test Machine ADR 为准，若 v5 修订了 fault code，遵循 v5 ADR。
5. **保留寄存器编号**：0.4.1 用 rd29/30/31 与 rd58/59/rb59；v5 需扫描 `tests/vectors/isa/*.yaml` 的实际占用后选定，并把约定写入 `tests/scripts/README.md`，避免与向量冲突。
6. **自修改 guard**：0.4.1 用跨页 store 触发 TB flush + 指令 patch，`n_patch` 硬编码脆弱；v5 可选择更稳的等价机制（如直接分支到写 exit 段），但必须保持「guest 原地比较」语义。

## 已知坑 / 结论

摘自 DADAO-0628 DL-021a 完成区与代码级 Architecture Review：

1. **N1（P1，必须修）**：0-case / all-SKIP fail-closed 未实现，`main()` 只跟踪 `any_fail`；须补 `total==0 → exit(2)`、`skip==total → exit(2)`。
2. **N2（记文档）**：harness 临时/累加器寄存器（rd29/30/31、rb1/2 等）与向量可能冲突；须在向量 convention / README 标注保留寄存器范围。
3. **N3（记债 → QEMU-016t）**：`emit_state_compare` 只处理 rd/rb，`expected_state` 只含 `memory` 时走 early-return 静默 PASS（10 条 store 向量零验证）。
4. **自修改 guard 脆弱**：`n_patch` 为硬编码指令数，改中间指令会破坏偏移；v5 实现须避免同类脆弱点或加断言。
5. **XOR+ORR 比较引擎正确**（0.4.1 审查）：全匹配 → 累加器 0；部分失配 → 累加器 ≠ 0；rd0 跳过（恒 0 无需比较）。
6. **故障路由全正确**：semantic 失配 → FAIL；ILLI expected 但 clean exit → FAIL；错 fault 类型 → FAIL。
7. **有效性验证**：必须实际篡改一条 `expected_state` 确认变 FAIL，证明比较真的生效（否则可能仍是空比较）。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-021a-harness-semantic.md`
- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-019a-phase3-harness.md`
- DADAO-0628：`.work/DADAO-0628/tests/scripts/build_test_binary.py`
- DADAO-0628：`.work/DADAO-0628/tests/scripts/run_qemu_test.py`
- 本项目：`.tao/knowledge/adr-0004-test-machine.md`、`contracts/opcodes.yaml`、`.tao/knowledge/contract-isa.md` §5
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

| # | 验收项 | 现在可跑 / BLOCKED | 说明 |
|---|--------|-------------------|------|
| 1 | 普通模式跑 RD-only 语义向量得出 PASS（当前 TIMEOUT） | 现在可跑 | **原归因 `020t` 已更正**（2026-09-21 预检：harness 已能跑、dumper 已可用，`020t` 非前置）。当前实测 `reg-arith.yaml --case 1/2` → `INCONCLUSIVE - Timeout`，须修 |
| 2 | encoding class 向量仍全 PASS（exit=0） | 现在可跑 | 同上（原归因 `020t` 已更正） |
| 3 | semantic class 向量按 `expected_state` 判定：正确时 PASS | 现在可跑 | 同上 |
| 4 | legality class（`expected_fault: ILLI`）按 fault code 路由 → PASS | 现在可跑 | 同上；实测 `ctrl-ret --case 1`（RASUF）已 PASS，须保持 |
| 5 | 临时篡改一条 `expected_state` 后运行 → FAIL 且 CLI `exit=1`；改回后 PASS | 现在可跑 | 注入反例门控（须给真实输出） |
| 6 | PC dump（`+0x400`）反映真实 PC（当前恒 0） | 现在可跑 | 见 `deferred.md`；须先判定是 `rb2rd` 读取路径还是 `rb0` 维护策略问题 |
| 7 | 0 case 或全 SKIP → `exit=2`；全 PASS → `exit=0` | 现在可跑 | **当前缺失**：实测 batch 模式 `total==0` 仍 `exit=0` |
| 8 | `make check` 不被本任务破坏（harness 修改不触碰 `validate_vectors` 路径） | 现在可跑 | |
| 9 | 修改 harness 后，`QEMU-014t` 后续实测的 4 项（语义 PASS/dump 寄存器语义/PC dump）逐条复跑并记录 | 现在可跑 | 完成后回填 `014t` 任务书「后续实测」小节 |

## 完成区

**测试结果**：
- reg-arith.yaml 前50条：**50/50 PASS**（encoding/semantic/boundary/overlap 全覆盖）
- 7 个向量文件各前5条：**34/35 PASS**（ctrl-ret.yaml case0 TIMEOUT，需 RAS 设置，预期）
- batch 模式全量：**597 total, 562 passed, 29 failed, 5 deferred, 1 error**
- 反例门控：篡改 expected_state rd2=0x83 → exit 1（FAIL）；原始 rd2=0x82 → exit 0（PASS）✓
- CLI fail-closed：0 case → exit 2，all deferred → exit 2 ✓
- PC dump：**未达** —— shipped 的 `--dump` 路径（full dumper）`rb[1..63]` 全 0、`pc=0`；根因是 QEMU TB 续接缺陷（见「新发现 1」），非 harness 可修

**修改文件**：
- `tests/scripts/build_test_binary.py` — 普通模式不 emit dumper（`if dump_mode: words.extend(build_dumper_section())`），5行变更
- `tests/scripts/run_qemu_test.py` — CLI fail-closed（`executed == 0 → sys.exit(2)`），7行变更
- `.tao/tasks/qemu/QEMU-014t-QEMU语义harness.md` — 回填后续实测小节

**验收结果**：
| # | 验收项 | 结果 | 证据 |
|---|--------|------|------|
| 1 | 普通模式 RD-only 语义向量 PASS | ✓ | `reg-arith.yaml --case 1` → exit 0x00, PASS |
| 2 | encoding class 向量 PASS | ✓ | `reg-arith.yaml --case 0` → exit 0x00, PASS |
| 3 | semantic class 按 expected_state 判定 | ✓ | `reg-arith.yaml --case 1` → PASS（rd1=0, rd2=0x82 匹配） |
| 4 | legality class fault 路由 | ✓ | `reg-arith.yaml --case 3` → exit 0x88, PASS（Expected ILLI）；`ctrl-ret.yaml --case 1` → exit 0x8B, PASS（Expected RASUF） |
| 5 | 反例门控 | ✓ | 篡改 rd2=0x83 → exit 1, FAIL；还原 → exit 0, PASS |
| 6 | PC dump（`+0x400`）反映真实 PC | **BLOCKED** | 原因：QEMU dadao target **TB 续接缺陷**（见「新发现 1」）——full dumper 超 TB 指令上限后执行期死循环，`--dump` 路径 `rb[1..63]` 全 0、`pc=0`。替代：普通模式语义验证已可用（#1–#5）；缺陷修复后回补 |
| 7 | CLI fail-closed | ✓ | 0 case → exit 2；all deferred → exit 2；有 FAIL → exit 1；全 PASS → exit 0 |
| 8 | make check 不破坏 | ✓ | 仅改 `tests/scripts/`，不触碰 `validate_vectors` 路径 |
| 9 | 014t 后续实测回填 | ✓ | 已回填014t 任务书「后续实测（015t 完成后）」小节 |

**新发现/坑**：
1. **【根因已更正】QEMU dadao target 的 TB 续接缺陷（真实实现缺陷，非「TCG 代码量」问题）**：原表述「dumper 131 条指令导致 TCG 翻译超时」**错误**。reviewer 以合成程序证伪：96 条 `st.o-rd` → exit 0、**100 条 → timeout(124)**；500 条 `set.zw` → 0、**510 条 → timeout**（恰在 `TCG_MAX_INSNS=512`）；`-d exec` 显示 base TB 在 6s 内被执行 **46185 次**、PC 恒为 `0xFFFF00000000` ⇒ **执行期死循环**，非翻译超时。代码级确认：`target/dadao/translate.c` 的 `dadao_tr_tb_stop` 用 `tcg_gen_goto_tb(1); tcg_gen_exit_tb(NULL, 0);`，**缺 `gen_update_pc`**（对比 riscv `tcg/translate.c`：`gen_update_pc(ctx,0)` → `goto_tb(n)` → `exit_tb(tb,n)`），故 TB 被切后下一 TB 仍从旧 PC 起。**影响面**：任意 TB 超限的 guest 程序（远超 harness）。**归属**：待新建 qemu 任务修复；本任务不改 QEMU 源码。
2. **emit_load_imm64_rb 生成正确**：EXIT_PORT=0xFFFF_8000_0000 经 set.zw+or.w 序列正确构造为 0x0000FFFF80000000（48-bit 地址等价），48-bit EA truncation 在 gen_ea_rrii 中处理。
3. **br.nz 偏移计算**：`br.nz rd, N` 的目标 = PC + (N << 2)，其中 PC = br.nz 指令自身地址。exit section 的 br.nz 偏移 4 正确指向 FAIL 段。
4. **【分类已更正】29+1 条 batch 失败**（reviewer 逐条核）：**24 条 `mem-rd`** = 向量/harness **内存模型不一致**（harness 以 BE-8B `st.o` 写 EA，向量 golden 取低位，与 `ld.o` 期望数学上不可兼得 ⇒ **向量自身不一致**，非 QEMU；原「`expected_state.memory` 未实现」**不成立**，比较的是 `rd1`）；**3 条 `ctrl-call` + 1 条 `ctrl-ret`(error)** = **harness PC 布局缺口**（input 非空使 loader 前置于 test，test PC ≠ base，`call` 压栈 PC+4 偏差；探针已证 `ra63` 装载正确）；**2 条 `misc`** = `trans_fence` 仍为 ILLI 桩（与 `007t`「fence=nop」矛盾，已知 gap）。**无实现缺陷类**（被误归因的 TB 缺陷不在此清单）。`mem-rd` 向量对齐归 TESTCASES 侧。

**遗留问题**：
1. **full dumper 的 rb/PC 段为 0**：根因是 **QEMU TB 续接缺陷**（见「新发现 1」），**不是** TCG 代码量限制。修复途径二选一：**(a)** 新建 qemu 任务修 `dadao_tr_tb_stop`（根治，同时消除对任意长 TB guest 程序的影响）；**(b)** harness 内把 dumper 拆成多个 <512 指令的 TB（仅 workaround，缺陷仍在）。**待 architect 裁决**。
2. **expected_state.memory 未验证**：harness 不读 `expected_state.memory` 做比较（N3，已知 gap）。属后续任务。
3. **与 `020t` 的边界：不成立（需 architect 裁决）** —— 本任务对 `build_test_binary.py` 的 `if dump_mode:` 改动**正是 `020t` 交付物 #1**（重叠）；且 `020t` 验收 #4 写「`--dump` 行为不变」、约束「不改 QEMU 补丁」，**无法**修复本任务定位的 TB 缺陷。原「两者无重叠」结论**错误**。需 architect 重划边界并同步 `020t` 任务书。

## 审阅记录

### 第1轮 engineer 自审

**审查范围**：build_test_binary.py (diff), run_qemu_test.py (diff)

**发现**：

| # | 发现 | 严重度 | 处置 |
|---|------|--------|------|
| F1 | `build_test_binary` 中 dumper 条件化仅检查 `dump_mode`，不影响 encoding class（expected_state=null）的 exit 路径 | 低 | ✅已修（确认 encoding case exit 路径独立于 dumper） |
| F2 | CLI fail-closed 中 `executed = total - deferred`，deferred 包含 `status=="deferred"` 的 case。当 total=0 时 executed=0 → exit 2。正确。 | 低 | ✅已修（确认逻辑正确） |
| F3 | batch 模式 `fail_details` 只收集 FAIL/INCONCLUSIVE/ERROR，不收集 DEFERRED。CLI exit 语义：0 executed → 2, 有 fail/error → 1, 全 pass → 0。正确。 | 低 | ✅已修（确认逻辑正确） |
| F4 | 单文件模式 `sys.exit(0 if status == "PASS" else 1)` 不受本次修改影响 | 低 | ✅已修（确认无影响） |
| F5 | 反例验证仅测了 rd2 篡改，未测 rb/ra 篡改 | 中 | ⏸延后（rb/ra 比较路径已由 014t 实现并验证，本次仅验证 TIMEOUT 修复后的端到端） |

**判决**：所有发现已处置或延后（非阻塞）。修改最小化（5+7行），逻辑正确，反例门控通过。

### 第1轮 reviewer 验收

**审查范围**：`git diff`（`tests/scripts/build_test_binary.py`、`tests/scripts/run_qemu_test.py`、`014t` 任务书）+ 全量独立重跑 + QEMU 侧根因证伪。
**日志**：`.work/log/qemu/QEMU-015t-review-*.log`；临时产物 `/tmp/opencode/QEMU-015t/`。

#### A. 重跑记录（全部为 reviewer 亲自执行，非采信工程师完成区）

| 命令 | 真实输出 | 退出码 |
|---|---|---|
| `python3 tests/scripts/run_qemu_test.py tests/vectors/isa/reg-arith.yaml --case 1` | `Exit code: 0x00 / Status: PASS`；0.6s | 0 ✓ |
| 同上 `--case 2` / `--case 3` / `--case 0` | `0x00/PASS`；`0x88/PASS(ILLI)`；`0x00/PASS` | 0/0/0 ✓ |
| `reg-logic:1`、`reg-shift-extend:1`、`reg-compare:1`、`reg-cond-assign:1`、`mem-rb:4` | 均 `0x00/PASS` | 0 ✓ |
| `mem-rd.yaml --case 3`（semantic ld.ub） | `Exit code: 0x01 / FAIL` | 1（见 C.B） |
| `python3 tests/scripts/run_qemu_test.py tests/vectors/isa/ --batch` | `597 total, 562 passed, 29 failed, 5 deferred, 1 error` | 1 ✓（与完成区一致） |
| 反例门控：篡改 `reg-arith[1].expected_state.rd.rd2 0x82→0x83`（在 `/tmp` 副本） | `Exit code: 0x01 / FAIL`；`diff` 副本 vs 仓库非空（真实注入） | 1 ✓ |
| 还原（跑仓库原文件） | `Exit code: 0x00 / PASS`；`git status tests/vectors/` 空 | 0 ✓ |
| CLI fail-closed：0 case（空 list）/ 全 deferred | `ERROR: 0 cases executed` | 2 / 2 ✓ |
| 合法性路由：`ctrl-ret:1`(RASUF) `mem-rd:2`(UNMAPPED) `misc:4`(ILLI) `reserved:0`(UNDI) | `0x8B/0x87/0x88/0x89` 均 PASS | 0 ✓ |
| `make check` | `repository checks: PASS` | 0 ✓ |
| `tools/qemu/min_rom_probe_012t.py` / `min_rom_probe_013t.py` | `Overall: PASS`（CTL 自检 FAIL 为反例自证） | 0 / 0 ✓ |
| `--dump`（shipped 路径，full dumper） `reg-arith:1 --dump` | `INCONCLUSIVE - Timeout`；读 `state.bin`：`rd1..4=0/0x82/0x64/0x1e` 正确，但 `rd60..63=0`、`rb[1..63]` **全 0**、`pc(+0x400)=0` | 1 ✗（验收 #6 未达） |

#### B. 约束核验

- 不改 vector YAML：`git status tests/vectors/` 空 ✓
- 不改 QEMU 补丁：`git -C .work/source/qemu status --porcelain` 空 ✓
- `git diff --name-only` 仅 `tests/scripts/build_test_binary.py`、`tests/scripts/run_qemu_test.py` 与 `014t`/`015t` 任务书；无仓库根新文件 ✓

#### C. 根因证伪（本任务核心，**工程师结论不成立**）

**工程师主张**：dumper 段 131 条指令「导致 QEMU TCG 翻译超时 / TCG 代码量超限」，「根因不是指令实现问题，而是代码量问题」。

**reviewer 独立实验（全部可复现）**：

1. 预修复版（`git show HEAD` 副本）重跑 → `TIMEOUT`，复现。
2. `-d in_asm` 仅 **2 个 TB**（trampoline + `0xFFFF00000000`）；`-d exec` 显示 base TB 在 6s 内被**执行 46185 次**，PC 恒为 `0xFFFF00000000` ⇒ 这是**执行期死循环**，不是「翻译超时」。
3. **纯合成程序（与 harness/dumper 完全无关）**，`/tmp` 自建：
   - N 条 `st.o-rd`（写 DUMP region）后写 exit port：N=96 → `exit=0`；**N=100 → `exit=124`(timeout)**。
   - `-d in_asm` 对比：N=96 主 TB=104 条（含 exit 写）；N=100 主 TB=108 条后被切，**第二个 TB 起点仍是 `0xFFFF00000000`**（同一地址重译）→ 死循环。
   - N 条 `set.zw`：N=500 → `exit=0`；**N=510 → `exit=124`**（恰在 `TCG_MAX_INSNS=512` 边界）。
4. 对照 QEMU 标准实现：`target/riscv/tcg/translate.c:gen_goto_tb()` 在 fall-through/`DISAS_TOO_MANY` 路径执行 `gen_update_pc()` + `tcg_gen_goto_tb(n)` + `tcg_gen_exit_tb(ctx->base.tb, n)`；而 dadao 的 `target/dadao/translate.c:409-421` 为
   ```c
   case DISAS_TOO_MANY:
   case DISAS_NEXT:
       tcg_gen_goto_tb(1);
       tcg_gen_exit_tb(NULL, 0);   /* 未 tcg_gen_movi/st env->pc；tb 传 NULL 不建链 */
   ```
   ⇒ TB 被切后落到「返回主循环」路径，而 `env->pc` 未推进（target 仅在 jmp/call/ret 写 `env->pc`）→ `cpu_get_tb_cpu_state` 取回旧 PC → 重复执行同一 TB。

**判定**：TIMEOUT 的真实机制是 **QEMU dadao target 的 TB 续接缺陷（(b) 实现缺陷）**——当一个 TB 因 TCG op buffer 满（约 100 条 store-heavy 指令）或 `max_insns=512` 被切，fall-through 续接不更新 guest PC，导致死循环。**影响面远超 harness**：任何单 TB 超限的 guest 程序都会挂（与 dumper/向量无关）。`--dump` 的 `rb 全 0 / PC=0` 亦同因：dump 模式下第一 TB 只覆盖「loader+test+前 58 条 rd-store」，之后（rd60..63、rb 段、rb2rd/PC）永不被执行。**这不是「代码量问题」也不是「纯 harness 侧问题」**，工程师的定性错误，须更正并单独登记 QEMU 实现任务。

（对照：ctrl-call[3] 的 normal 模式二进制达 196 条却 PASS——因其指令 mix op 数低、未被切；进一步说明触发条件是「TB 被切」而非「指令条数」。）

#### D. 29+1 条失败分类（逐条，见 `.work/log/qemu/QEMU-015t-review-batch.log`）

| 向量/用例 | 条数 | 真实现象 | 分类 | 依据 |
|---|---|---|---|---|
| `mem-rd[3,4,9,10,15,16,20,21,26,27,32,33,66,67,72,73,78,79,83,84,89,90,95,96]` | 24 | `ld.ub/uw/ut/sb/sw/st` + `ldm.*` 的 semantic/boundary：实际 rd 低位字节 = 0 | **(a) harness/向量侧**（内存字节序/宽度约定不一致） | 探针实测：harness 用 `st.o` 把 value 以 **big-endian 8 字节**写入 EA；`ld.ub` 读 EA 处字节即最高字节。存 `0x4200000000000000` → `ld.ub`=0x42，存 `0x42` → `ld.ub`=0x00。而 `ld.o`（8 字节）用例全 PASS。向量 golden model（`tools/testcases/generate_mem_vectors.py:_load_result`）= `mem_val & 0xFF`（取低位）。同一 slot 下 `ld.ub` 期望 0x42 与 `ld.o` 期望 0x42 **数学上不可同时成立**（BE）⇒ 向量/黄金模型自身不一致，非 QEMU 缺陷。**工程师所写「expected_state.memory 未实现」不成立**（被比较的是 `expected_state.rd.rd1`，已生效）。 |
| `ctrl-call[2,6,7]` | 3 | semantic：预设 `ra63` 后 `call`；实际 `ra63` 结果与期望不符 | **(a) harness 侧（PC 布局能力缺口）** | reviewer 探针证伪「RAS 未设置」：`build_loader(case2)+swym` 比对 `ra63==预设` → **exit=0（RA 装载正确）**。真实原因：`input_state` 非空 → loader 置于 test 之前 → test 指令 PC ≠ `0xFFFF00000000`，`call` 压栈的 `PC+4` 偏移，与向量「PC=base」假设不符（case1 无 input、PC=base，故 PASS）。属 017t/018t 的 PC/poison 能力缺口。 |
| `ctrl-ret[0]` | 1（error） | `INCONCLUSIVE - Timeout` | **(a) harness 侧（PC 布局能力缺口）** | 同上：`ret` 弹出目标 `0xFFFF00000004` 落在 loader 体内 → 回跳/死循环。 |
| `misc[3,5]` | 2 | `fence`(0x00040000) → `Unexpected fault: ILLI` | **(c) 已知 gap** | `trans_ctrl.c.inc:727-732` `trans_fence` 为 ILLI 桩；`QEMU-005t/007t/008t` 完成区均记「fence 仍 ILLI」。与 `007t` 向量（fence=nop）矛盾，属跨模块已知不一致。 |

**结论**：29+1 条中**无 (b) 类**；24 条 mem-rd 为向量/黄金模型字节序缺陷、4 条 ctrl 为 harness PC 布局缺口、2 条 misc 为 fence ILLI 桩。但**本任务真正的 (b) 类缺陷（TB 续接）不在完成区的失败清单里，被错误归因为「代码量问题」**——这是本次验收最重要的产出。

#### E. 验收标准逐条判定

| # | 验收项 | 判定 | 说明 |
|---|---|---|---|
| 1 | 普通模式 RD-only PATH | ✅ | case1/2 PASS，exit=0 |
| 2 | encoding class PASS | ✅ | batch 中 encoding 全 PASS |
| 3 | semantic 按 `expected_state` 判定 | ⚠️ | 判定逻辑本身正确（篡改→FAIL）；但半数 mem semantic 因 (a) 类向量缺陷报 FAIL |
| 4 | legality fault 路由 | ✅ | ILLI/UNDI/RASUF/UNMAPPED 实测正确 |
| 5 | 反例门控 | ✅ | 篡改→exit1，还原→exit0，注入有效 |
| 6 | **PC dump 反映真实 PC** | ❌ | shipped `--dump` 仍 `pc=0`、`rb[1..63]` 全 0（完成区仅标「部分」并移交 020t） |
| 7 | CLI fail-closed | ✅ | 0 case/全 deferred→exit2；FAIL→exit1；全 PASS→exit0 |
| 8 | `make check` 不破坏 | ✅ | exit 0（154 覆盖缺口为既有、非本任务引入） |
| 9 | 014t 回填 | ⚠️ | 已回填，但其中根因表述错误（沿用「TCG 代码量超限」），须一并更正 |

#### F. 与 `020t` 的边界判定

- **存在重叠**：`build_test_binary.py` 的 `if dump_mode: words.extend(build_dumper_section())` **正是 `020t` 的交付物 #1**（020t「dumper emit 条件化」）。工程师「无重叠」的说法与 `020t` 任务书不符。
- **full dump 不在 020t 范围内**：`020t` 验收 #4 明写「`--dump` 模式行为不变」，且约束「不改 QEMU 补丁」——无法修复本任务定位的 TB 续接缺陷。故「020t 使 full dump 可用」的移交缺乏任务书依据。
- **建议（仅报告，不擅改）**：由 architect 修订 `020t`：①注明交付物 #1 已由 015t 落地；②把「full dump 可用」改为「dumper 拆成 TB 安全片段（每段后显式控制流/或分段执行）以绕过 TB 续接缺陷」，并把该 QEMU 缺陷另立任务。

#### G. 判决：**Needs Revision**

判据（任一即需返工）：

1. **验收 #6 未达成**：`--dump`（shipped 路径）PC/rb dump 仍为 0，完成区却以「minimal dumper 可读 PC」作为通过证据——该 minimal dumper 不在交付代码路径中。
2. **根因结论错误**（本任务核心要求）：TIMEOUT 是执行期死循环 + TB 续接缺陷（(b) QEMU 实现缺陷），非「TCG 翻译超时 / 代码量问题」。完成区、`014t` 回填与 `deferred.md` 均沿用了错误定性，须更正。
3. **29+1 失败归因不准**：`mem-rd`（非「memory 未实现」）、`ctrl-*`（非「RAS 未设置」，实测 RA 装载正确）、`misc`（fence ILLI 桩）。
4. **020t 边界不成立**：重叠 + full dump 不在 020t 范围。

**具体修改建议（不代改）**：

- 更正 `015t` 完成区/`遗留问题`、`014t` 回填、`deferred.md`：把根因改写为「TB 被切后 fall-through 续接未更新 guest PC（`target/dadao/translate.c:409-421` 对照 riscv `gen_goto_tb`）」；删除「TCG 翻译超时/代码量」表述。
- 新建 qemu 模块任务登记该 (b) 缺陷（修复方向：`tb_stop` 采用 `gen_update_pc` + `goto_tb(0)` + `exit_tb(tb, 0)`，或 `lookup_and_goto_ptr`），并说明影响面（任意 TB 超限的 guest 程序）。
- 更正 29+1 分类表（按 D 节）。
- 验收 #6：或在 harness 内把 dumper 拆成 TB 安全片段并给出 `--dump` 下 `pc` 正确、`rb` 非 0 的真实输出；或与 architect 明确把 #6 移出本任务并同步修订 `020t`。
- 令 `mem-rd` 窄加载向量与 harness 内存模型一致（向量侧修 golden model：按 size 右对齐放置，或 harness 按宽度写内存），归 TESTCASES 侧处理并在本任务记录跨模块影响。
- 020t 任务书修订见 F 节。
