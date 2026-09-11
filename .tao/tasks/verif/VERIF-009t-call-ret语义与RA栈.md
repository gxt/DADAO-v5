# VERIF-009t: call/ret 语义 + RA stack

**模块**：verif
**项目里程碑**：M1
**依赖**：`VERIF-008t`、`QEMU-012t`

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `VERIF-008t` 的 `build_branch_test_binary()` 框架
  - `tests/vectors/isa/control-flow.yaml`
  - `.tao/knowledge/contract-isa.md` §5.3/§5.4（call 压栈、ret 弹栈）
  - `verif/opcodes.yaml`（`call-iiii`/`call-rrii`/`ret-riii` 编码）
- 输出：
  - `tests/scripts/build_test_binary.py`：新增 `emit_call_ret_pattern()` 与 `call_ret` behavior 分支
  - `tests/vectors/isa/control-flow.yaml`：新增 call/ret semantic 测试
- 约束：
  - 不修改现有 `build_test_binary` 主路径
  - `call_r` 的 encoding bits 必须从 `contract-isa.md` §5.3 手推，不能从 QEMU 行为反推
  - 保持既有 PASS 基线不退化

## 背景（完整）

### 目标

1. 新增 call/ret 语义测试向量（TDD：先写向量，再跑验证）。
2. 激活这些测试（在 `build_branch_test_binary` 框架上新增 `call_ret` pattern）。
3. 全套测试回归不破坏。

### 设计理由

`VERIF-008t` 完成了条件分支与 jump 的语义测试；call/ret 涉及 RA stack 压栈/弹栈，无法用普通 taken/not-taken pattern：

- `call_i`/`call_r`：执行时把返回地址（call 指令的下一条）压入 `ra[63]`，然后跳转；
- `ret`：从 `ra[63]` 读返回地址跳回。

需要专用三段 layout 验证「call 压栈 + ret 弹回」的完整往返。

### 关键概念 / 数据

**call 语义测试（taken 简化版）**：把 call 当作无条件跳转验证跳转发生，RA 值正确性由 ret 往返隐式验证。

**ret 组合 pattern**：

```
binary layout:
[call_i +2]           ← 调用 subr（跳过 ret_landing）
[ret_landing:]
  emit_exit(0)        ← ret 正确弹回时落这里 → PASS
[subr:]
  ret rd0, 0          ← 弹出 ra[63]（= &ret_landing），跳回
```

**地址算术（以 `contract-isa.md` §5.3/§5.4 为准）**：

- call 压栈 `ra[63] ← 返回地址`（call 指令的下一条地址）
- call 目标 = 当前 PC 相对偏移（v5 为相对 `rb0`，单位 word）
- ret 跳 `ra[63] + imm`（通常 imm=0）

0.4.1 的具体值（call 在 offset 0、imm=+2 → target=12、`ra[63]=4`）仅作算术形态参考，v5 须按 0.5.3 公式重算。

**builder 改动**：在 `build_branch_test_binary()` 中新增分支：`call` + `taken`（iiii/rrii）走无条件跳转；`ret`（或 `behavior == 'call_ret'`）调用 `emit_call_ret_pattern(buf, case)`。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-030a-call-ret-semantic.md`（完整转述：背景、call/ret 语义、三段 layout、builder 改动、测试向量规范、约束、验收、完成区、代码级 Architecture Review 的逐字节 PC 算术验证）
- DADAO-0628：`code-agent/tasks/DL-029a-control-flow-semantic-harness.md`（前置框架）

## 交付物

- `tests/scripts/build_test_binary.py`：`emit_call_ret_pattern()` + call/ret 调度
- `tests/vectors/isa/control-flow.yaml`：call_i taken、call_r taken、ret 组合 pattern
- 完成区附 PASS 条数与回归结果

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **助记符/格式**：0.4.1 `call_i=0x6C(iiii)`/`call_r=0x6D(rrii)`/`ret=0x6E(riii)`；0.5.3 对应 `call-iiii`/`call-rrii`/`ret-riii`，op/编码从 `verif/opcodes.yaml` 取，**不复制 0.4.1 编码**。
2. **返回地址公式**：0.4.1 修复后为 `ra[63] = pc_next + 4`；v5 以 `contract-isa.md` §5.3.3 压栈流程为准（须核对「下一条地址」定义）。
3. **ret 跳转**：0.4.1 `ret` 跳 `ra[63] + imm*4`；v5 以 `contract-isa.md` §5.4.1 弹栈流程为准。
4. **`emit_exit` 字节数**：0.4.1 依赖 `load_reg`+`halt` 固定 20B 做 PC 算术；v5 的 exit 段实现（`VERIF-004t` 改为写 exit port）字节数不同，`call_ret` layout 的偏移须按 v5 实际重算，不能照抄 `+5`/`+2`。
5. **QEMU call/ret 修复**：v5 的 call/ret 实现修复属 `qemu` 模块（`QEMU-012t`），本任务依赖其正确后再验收。
6. **RA 栈验证深度**：0.4.1 只做「call→ret→landing」往返隐式验证；v5 同样以往返路径隐式验证 RA push/pop，不新增 ra 状态比较（除非 `expected_state` 支持 ra，属后续）。

## 已知坑 / 结论

摘自 DADAO-0628 DL-030a 完成区与代码级 Architecture Review：

1. **call_ret layout 逐字节对齐**：0.4.1 `[call_i +5][emit_exit(0) 20B][ret][poison]`；PC 算术与 translate.c 一致才 PASS。v5 偏移须按自身 exit 段长度重算。
2. **`ra[63]` 压栈/弹栈正确性**由 `call→ret→ret_landing` 完整往返隐式验证：ret 能落回 exit 段即证明压栈/弹栈正确。
3. **call_r encoding 手推**：0.4.1 审查记录 `0x6D042000` 等；v5 必须从 `contract-isa.md` §5.3.2 手推，不能从 QEMU 反推。
4. **不修改主路径**：call/ret 走新增分支，算术/访存路径不动。
5. **回归基线**：0.4.1 `37/37 control-flow PASS`；v5 以自身 harness 为准，须保持既有 PASS 不退化。
6. **无条件 call 无 not_taken 变体**：call 无条件执行，不需要 not-taken 测试。
7. **ret 无独立编码测试语义**：ret 依赖 RA 栈有值，须用组合 pattern。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-030a-call-ret-semantic.md`
- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-029a-control-flow-semantic-harness.md`
- DADAO-0628：`.work/DADAO-0628/tests/scripts/build_test_binary.py`
- 本项目：`.tao/knowledge/contract-isa.md` §5.3/§5.4、`verif/opcodes.yaml`、`tests/vectors/isa/control-flow.yaml`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `emit_call_ret_pattern()` 实现三段 layout，`call_ret` behavior 可触发
2. call_i taken、call_r taken、ret 组合 pattern 均激活并 PASS
3. `call→ret→landing` 往返路径 PASS，证明 `ra[63]` 压栈/弹栈正确
4. `python3 tests/scripts/run_qemu_test.py tests/vectors/isa/control-flow.yaml` 0 FAIL，既有 PASS 基线不退化
5. call_r encoding 在完成区给出从 `contract-isa.md` §5.3.2 的手推依据
6. `rd-arith.yaml` 回归不破坏

## 完成区

**状态**：待开始
**Commit**：
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
