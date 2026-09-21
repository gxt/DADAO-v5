# QEMU-018t: call/ret 语义 + RA stack

**模块**：qemu
**项目里程碑**：M1
**依赖**：`QEMU-017t`、`QEMU-012t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 预检订正（2026-09-21，下发前，含用户裁定）

> 本节为**下发前预检**结论，优先级高于下文旧文本；冲突时以本节为准。

**P1 — `expected_state.ra` 须按 loader 偏移重定位**（与 `expected_pc` 同构，补注 `ADR-0009 D6`）：
- RA 语义（§5.4/§5.6）：`ra63 = <count:16><返回地址:48>`；返回地址 = **call 自身地址 + 4**（实测 `.work/source/qemu/target/dadao/insn_trans/trans_ctrl.c.inc:607` 的 `pc_next + 4`）
- 向量按 **test@BINARY_BASE** 填 RA 值；harness 前置 loader（`input_state` 非空时 1–4 words）使 test 实际地址 = `BINARY_BASE + loader_bytes`
- **规则**：比对 `expected_state.ra` 时，把其**低 48 位**加上 `loader_bytes`（高 16 位 count **不变**）后再与实测比较。`loader_bytes == 0` 时退化为原值
- **实测根因证据**（3 条 `ctrl-call` FAIL 的**真因**，非 QEMU 缺陷）：

| 向量 | loader | test@ | 向量 RA | 实现实际 RA |
|---|---|---|---|---|
| `ctrl-call[1]`/`[5]` | 0w | `0xFFFF00000000` | `<1>…0004` | `<1>…0004` → PASS |
| `ctrl-call[2]`/`[6]` | 4w | `0xFFFF00000010` | `<2>…0004` | `<2>…0014` → FAIL |
| `ctrl-call[7]` | 4w | `0xFFFF00000010` | `<1>…0004` | `<1>…0014` → FAIL |

**P2 — `ret` 用 harness 合成的 `call→ret→landing` 往返**（**不改向量**）：
- 现状 `ctrl-ret[0]` **不可行**：它 preload `ra63 = <1>0xFFFF00000004`（虚构地址），`ret` 跳进去落在 **loader 区** → 执行垃圾 → **TIMEOUT**（基线里那 1 个 error）
- **合成 layout**（word 索引从 test 段起）：
  ```
  w0: call imm=2      → target = w2（ret）；ra63 = <1>(w1 地址)
  w1: exit 段（= landing，ret 弹回此处）
  w2: ret             ← **向量被测指令**（ret 弹栈 → 跳 w1 → 写 exit → PASS）
  ```
- **ret 用例不加载 `input_state.ra`**（ra63 由合成 call 真实压栈）⇒ loader=0 ⇒ test@BINARY_BASE ⇒ **无需重定位**，且 `expected_pc` 与向量既有值一致（landing = `BINARY_BASE+4`）
- `expected_state.ra = {ra63: 0}`（弹空）✓ 与向量一致

**P3 — 路由修正**：`QEMU-017t` 的 `expected_pc is not None` 调度**不限助记符**，会把 `ret`（`delta=4`）送进 **not-taken branch layout**（✗ 语义不适配）。本任务须为 **call**（无条件 → taken layout 可用）与 **ret**（→ P2 往返 layout）分别路由，不得复用 not-taken layout。

**P4 — 验收归因过时**：验收 #2/#3/#4/#6 的 BLOCKED 归因「需 `QEMU-012t` + harness（`020t`）」**已过时**——`012t` 已完成、`020t` 已关闭 → 全部**现在可跑**。

**P5 — 范围**：**纯 harness 改动**（`tests/scripts/build_test_binary.py`），**不改 vector YAML**。`ctrl-call` 5 条 semantic 与 `ctrl-ret[0]` **已存在**，经 P1/P2/P3 后即被真实验证。


## 接口规范

- 输入：
  - `QEMU-017t` 的 `build_branch_test_binary()` 框架
  - `tests/vectors/isa/ctrl-call.yaml`、`tests/vectors/isa/ctrl-ret.yaml`
  - `.tao/knowledge/contract-isa.md` §5.4/§5.5（call 压栈、ret 弹栈）
  - `contracts/opcodes.yaml`（`call-iiii`/`call-rrii`/`ret-riii` 编码）
- 输出：
  - `tests/scripts/build_test_binary.py`：新增 `emit_call_ret_pattern()` 与 `expected_pc`+`expected_state.ra` behavior 分支
  - `tests/vectors/isa/ctrl-call.yaml`、`tests/vectors/isa/ctrl-ret.yaml`：新增 call/ret semantic 测试
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

`QEMU-017t` 完成了条件分支与 jump 的语义测试；call/ret 涉及 RA stack 压栈/弹栈，无法用普通 taken/not-taken pattern：

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

**builder 改动**：在 `build_branch_test_binary()` 中新增分支：`call` + `expected_pc` 非 null（iiii/rrii）走无条件跳转；`ret`（或 `expected_state.ra` 非 null）调用 `emit_call_ret_pattern(buf, case)`。`expected_state.ra` 用于断言 call 压栈后 ra63 的值；`expected_pc` 用于断言 ret 弹出的返回地址。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-030a-call-ret-semantic.md`（完整转述：背景、call/ret 语义、三段 layout、builder 改动、测试向量规范、约束、验收、完成区、代码级 Architecture Review 的逐字节 PC 算术验证）
- DADAO-0628：`code-agent/tasks/DL-029a-control-flow-semantic-harness.md`（前置框架）

## 交付物

- `tests/scripts/build_test_binary.py`：call/ret 专用 layout + 调度 + `expected_state.ra` 重定位（**唯一改动文件**）
- **不改 vector YAML**（见 P5）
- 完成区附：5 条 `ctrl-call` semantic + `ctrl-ret[0]` 逐条 PASS 真实输出；「改前 3 FAIL + 1 error → 改后 0 FAIL」对比；回归结果

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **助记符/格式**：0.4.1 `call_i=0x6C(iiii)`/`call_r=0x6D(rrii)`/`ret=0x6E(riii)`；0.5.3 对应 `call-iiii`/`call-rrii`/`ret-riii`，op/编码从 `contracts/opcodes.yaml` 取，**不复制 0.4.1 编码**。
2. **返回地址公式**：0.4.1 修复后为 `ra[63] = pc_next + 4`；v5 以 `contract-isa.md` §5.6.1 压栈流程为准（须核对「下一条地址」定义）。
3. **ret 跳转**：0.4.1 `ret` 跳 `ra[63] + imm*4`；v5 以 `contract-isa.md` §5.6.2 弹栈流程为准。
4. **`emit_exit` 字节数**：0.4.1 依赖 `load_reg`+`halt` 固定 20B 做 PC 算术；v5 的 exit 段实现（`QEMU-015t` 改为写 exit port）字节数不同，`call_ret` layout 的偏移须按 v5 实际重算，不能照抄 `+5`/`+2`。
5. **QEMU call/ret 修复**：v5 的 call/ret 实现修复属 `qemu` 模块（`QEMU-012t`），本任务依赖其正确后再验收。
6. **RA 栈验证**：`expected_state.ra` 用于断言 call 压栈后 `ra[63]` 的值（返回地址）；`call→ret→landing` 完整往返隐式验证 RA push/pop。若 `expected_state.ra` 非 null，用 `ra2rd` 导出 RA 到 RD 后做 XOR 比对。

## 已知坑 / 结论

摘自 DADAO-0628 DL-030a 完成区与代码级 Architecture Review：

1. **call_ret layout 逐字节对齐**：0.4.1 `[call_i +5][emit_exit(0) 20B][ret][poison]`；PC 算术与 translate.c 一致才 PASS。v5 偏移须按自身 exit 段长度重算。
2. **`ra[63]` 压栈/弹栈正确性**由 `call→ret→ret_landing` 完整往返隐式验证：ret 能落回 exit 段即证明压栈/弹栈正确。
3. **call_r encoding 手推**：0.4.1 审查记录 `0x6D042000` 等；v5 必须从 `contract-isa.md` §5.4 手推，不能从 QEMU 反推。
4. **不修改主路径**：call/ret 走新增分支，算术/访存路径不动。
5. **回归基线**：0.4.1 `37/37 control-flow PASS`；v5 以自身 harness 为准，须保持既有 PASS 不退化。
6. **无条件 call 无 not_taken 变体**：call 无条件执行，不需要 not-taken 测试。
7. **ret 无独立编码测试语义**：ret 依赖 RA 栈有值，须用组合 pattern。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-030a-call-ret-semantic.md`
- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-029a-control-flow-semantic-harness.md`
- DADAO-0628：`.work/DADAO-0628/tests/scripts/build_test_binary.py`
- 本项目：`.tao/knowledge/contract-isa.md` §5.4/§5.5、`contracts/opcodes.yaml`、`tests/vectors/isa/ctrl-call.yaml`、`tests/vectors/isa/ctrl-ret.yaml`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

| # | 验收项 | 现在可跑 / BLOCKED | 说明 |
|---|--------|-------------------|------|
| 1 | call/ret 专用 layout 实现：`call` 无条件跳转 + `ret` 合成 `call→ret→landing` 往返 | **现在可跑** | 代码审查 + 字节级布局核对 |
| 2 | `expected_state.ra` **按 loader 偏移重定位**（低 48 位 + `loader_bytes`，count 不变）后比对 | **现在可跑** | 原归因已过时（P4）。须给 `ctrl-call[2]/[6]/[7]` 改前 FAIL → 改后 PASS |
| 3 | 5 条 `ctrl-call` semantic + `ctrl-ret[0]` **逐条** PASS（`call→ret→landing` 往返证明 RA 压/弹正确） | **现在可跑** | 同上；`ctrl-ret[0]` 改前 TIMEOUT → 改后 PASS |
| 4 | `run_qemu_test.py` 对 `ctrl-call.yaml`/`ctrl-ret.yaml` 0 FAIL（含 encoding/legality） | **现在可跑** | 临时目录 `--batch` |
| 5 | call_r encoding 在完成区给出从 `contract-isa.md` §5.4 的手推依据 | 现在可跑 | |
| 6 | 全量 `tests/vectors/isa/ --batch` 失败数由 29 → 26（消除 3 条 `ctrl-call`；`ctrl-ret` error 消除），**零新增** | **现在可跑** | 逐条核对；余 24 `mem-rd` 窄 load（→TESTCASES-010t）+ 2 `misc`（deferred） |
| 7 | **反例门控**：任取一条 call 向量，把 `expected_state.ra` 低 48 位改错 → FAIL；还原 → PASS。且把重定位规则关掉（不加 `loader_bytes`）→ `ctrl-call[2]` 必须 FAIL | **现在可跑** | 证明重定位真的生效、非恒真 |
| 8 | **往返门控**：把合成往返里的 `call` 目标改错（如 `imm=1`）→ `ctrl-ret[0]` 必须 FAIL | **现在可跑** | 证明 ret 往返非恒真 |

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
