# VERIF-004t: harness 语义验证修复

**模块**：verif
**项目里程碑**：M1
**依赖**：`VERIF-003t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `VERIF-003t` 交付的 `tests/scripts/build_test_binary.py`、`tests/scripts/run_qemu_test.py`
  - `tests/vectors/isa/*.yaml`（`class`、`expected_state`、`expected_fault`、`status`）
  - `SPEC-006t` 的 Test Machine ADR（exit code 协议）
  - `verif/opcodes.yaml`（比较引擎所用 `xor`/`or`/`cs.z`/`br.*` 等指令的 0.5.3 编码）
- 输出：修改后的 `tests/scripts/build_test_binary.py`（新增/实现 `emit_state_compare()`）、`tests/scripts/run_qemu_test.py`（fault 路由 + CLI fail-closed）
- 约束：
  - 不改 vector YAML（仅改 harness 脚本）
  - 不改 QEMU 补丁：状态比较由 guest 代码原地完成，不依赖 QEMU state dump
  - 保留寄存器（比较临时/累加器）不得出现在向量的 `input_state`/`expected_state`；若冲突须改选
  - `status: deferred` 向量跳过
  - `expected_state: null` 的 encoding 向量不生成比较代码，仅执行后写 exit=0

## 背景（完整）

### 目标

把 smoke 级 harness 升级为**真正的语义验证器**：

1. `build_test_binary.py`：实现 `emit_state_compare()`，把预期寄存器状态嵌入 guest 代码**原地比较**，向 exit port 写 0（PASS）或非 0（FAIL）。
2. `run_qemu_test.py`：按 `class` + `expected_fault` 正确路由 pass/fail 判断。
3. CLI：任意 case FAIL 时 `sys.exit(1)`；0 case 或全 SKIP 时 fail-closed（`sys.exit(2)`）。

### 设计理由

`VERIF-003t` 的 harness 是 smoke test，不是语义验证器：`emit_state_dumper()` 为空、runner 完全不读 `expected_state`/`expected_fault`、exit=0 无条件 PASS、`expected_fault: ILLI` 的 legality case 反被判 FAIL、CLI 遇 FAIL 仍以 0 退出、0 case/全 SKIP 不报错。向量里的 `expected_state` 数据当前零验证，必须修。

### 关键概念 / 数据

**退出码协议（ADR 约定，精确值以 v5 ADR 为准）**

| 条件 | QEMU exit code |
|------|---------------|
| 正常 PASS（guest 写 0 到 exit port） | 0 |
| guest 内检测到比较失败（写非 0） | 1 |
| ILLI（精确异常） | 0x82 |
| MALIGN（精确异常） | 0x81 |
| UNDI（精确异常） | 0x83 |
| 未映射访问 | 0x8F |

**`_classify(exit_code, case)` 路由**

```python
FAULT_CODES = {'ILLI': 0x82, 'MALIGN': 0x81, 'UNDI': 0x83}
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
for each (reg, expected_value) in expected_state.rd / expected_state.rb:
    加载 expected 到 temp
    temp = expected XOR actual          # 相等则 0
    mismatch |= temp                    # 任一失配则 mismatch ≠ 0
if mismatch == 0: 写 exit=0（PASS）
else:             写 exit=1（FAIL）
```

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

1. **比较引擎指令编码**：0.4.1 硬编码 `xor`=`0x10280000`、`or`=`0x10240000`、`csz`=`0x22` 等；v5 必须从 `verif/opcodes.yaml` 取 0.5.3 的 `xor.o`/`or.o`（固定位宽 orrr）与 `cs.z`（rrrr）等编码，**禁止沿用 0.4.1 硬编码值**。
2. **分支指令**：`breq/brne` → 0.5.3 `br.eq`/`br.ne`（rrii），比较引擎/跳转偏移按 v5 格式重算。
3. **`unimp` → `illi`**：0.4.1 用 `unimp` 触发 ILLI 的路径，v5 对应 `illi`（`contract-isa.md` §7.2）。
4. **退出码精确值**：以 `SPEC-006t` 的 Test Machine ADR 为准，若 v5 修订了 fault code，遵循 v5 ADR。
5. **保留寄存器编号**：0.4.1 用 rd29/30/31 与 rd58/59/rb59；v5 需扫描 `tests/vectors/isa/*.yaml` 的实际占用后选定，并把约定写入 `tests/scripts/README.md`，避免与向量冲突。
6. **自修改 guard**：0.4.1 用跨页 store 触发 TB flush + 指令 patch，`n_patch` 硬编码脆弱；v5 可选择更稳的等价机制（如直接分支到写 exit 段），但必须保持「guest 原地比较」语义。

## 已知坑 / 结论

摘自 DADAO-0628 DL-021a 完成区与代码级 Architecture Review：

1. **N1（P1，必须修）**：0-case / all-SKIP fail-closed 未实现，`main()` 只跟踪 `any_fail`；须补 `total==0 → exit(2)`、`skip==total → exit(2)`。
2. **N2（记文档）**：harness 临时/累加器寄存器（rd29/30/31、rb1/2 等）与向量可能冲突；须在向量 convention / README 标注保留寄存器范围。
3. **N3（记债 → VERIF-006t）**：`emit_state_compare` 只处理 rd/rb，`expected_state` 只含 `memory` 时走 early-return 静默 PASS（10 条 store 向量零验证）。
4. **自修改 guard 脆弱**：`n_patch` 为硬编码指令数，改中间指令会破坏偏移；v5 实现须避免同类脆弱点或加断言。
5. **XOR+ORR 比较引擎正确**（0.4.1 审查）：全匹配 → 累加器 0；部分失配 → 累加器 ≠ 0；rd0 跳过（恒 0 无需比较）。
6. **故障路由全正确**：semantic 失配 → FAIL；ILLI expected 但 clean exit → FAIL；错 fault 类型 → FAIL。
7. **有效性验证**：必须实际篡改一条 `expected_state` 确认变 FAIL，证明比较真的生效（否则可能仍是空比较）。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-021a-harness-semantic.md`
- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-019a-phase3-harness.md`
- DADAO-0628：`.work/DADAO-0628/tests/scripts/build_test_binary.py`
- DADAO-0628：`.work/DADAO-0628/tests/scripts/run_qemu_test.py`
- 本项目：`.tao/knowledge/adr-0004-test-machine.md`、`verif/opcodes.yaml`、`.tao/knowledge/contract-isa.md` §5
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. encoding class 向量仍全 PASS（exit=0）
2. semantic class 向量按 `expected_state` 判定：正确时 PASS
3. legality class（`expected_fault: ILLI`）按 fault code 路由 → PASS（修复前为 FAIL）
4. 临时篡改一条 `expected_state` 后运行 → FAIL 且 CLI `exit=1`；改回后 PASS
5. 0 case 或全 SKIP → `exit=2`；全 PASS → `exit=0`
6. `make check` 不被本任务破坏（harness 修改不触碰 `validate_vectors` 路径）

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
