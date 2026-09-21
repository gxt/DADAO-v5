# QEMU-015t: harness 语义验证修复

**模块**：qemu
**项目里程碑**：M1
**依赖**：`QEMU-014t`
**状态**：待开始

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
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
