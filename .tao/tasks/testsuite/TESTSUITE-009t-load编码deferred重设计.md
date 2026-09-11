# TESTSUITE-009t: rd-load-store deferred 测试重设计（load encoding）

**模块**：testsuite
**项目里程碑**：M1
**依赖**：`TESTSUITE-006t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `tests/vectors/isa/rd-load-store.yaml`（TESTSUITE-002t/006t 向量，含 `status: deferred` 的 load encoding）
  - `.tao/knowledge/contract-isa.md` §4.1（load/store 合法性、对齐）、§2.2（格式）
  - `.tao/knowledge/adr-0004-test-machine.md`（内存映射、未映射区行为）
  - `verif/opcodes.yaml`（load 指令编码字段）
- 输出：重设计后的 `tests/vectors/isa/rd-load-store.yaml`（14 条 load encoding 由 deferred → active）
- 约束：
  - 只修改 `tests/vectors/isa/rd-load-store.yaml`（纯数据任务）
  - 不改实现源码；若需要实现侧改动（如 `ha=0 → ILLI` 检查不存在）另建任务
  - 基址必须指向 RAM 合法地址，不用未映射地址
  - 完成后不自行 commit

## 背景（完整）

### 目标

将 load encoding 测试从「零地址访问导致 hang」重新设计为**合法可执行的 active 测试**，全部激活。

### 设计理由

0628 `rd-load-store.yaml` 中有 14 条 load encoding 测试 `status: deferred`：

- 原设计用 `rb0=0`（零地址）作为 load base → addr=0 → 访问未映射区域 → QEMU 卡住，既不抛 ILLI 也不退出（无超时机制干净退出）。
- 根因：addr=0 物理上未映射（内存映射规定 `0x00000000-0x000FFFFF` 为 unmapped）；QEMU 访问未映射 MMIO 时卡住。

### 关键概念 / 数据

**方案 A（备选）：`ha=rd0 → ILLI`**

若合约规定 load 指令的 base 字段为 rd bank 且为 rd0 时触发 ILLI：改 `expected_fault: null → ILLI`、`status: deferred → active`。需先确认实现有 `if (ha==0) raise ILLI` 检查；若无则另建实现任务。

**方案 B（0628 采用）：使用有效基址**

- 在 `input_state` 中预置 `rb1 = 0x0000000080000000`（RAM/BINARY_BASE）
- 编码中 base 字段 = rb1（非 rb0），dest = rd1（非 rd0）
- `expected_fault: null`、`status: active`，加载合法 RAM 地址
- 加载值 = 测试 binary 自身内容（可接受）
- multi load 的 `immu6` 保持 ≥1（=0 → ILLI）

0628 采用的字段模式（仅描述结构，**不含具体 0.4.1 编码字**；v5 从 `verif/opcodes.yaml` 的 op/字段与 §2.2 公式重新手算）：

- 单 load：`ha(dest)=1(rd1)`、`hb(base)=1(rb1)`、`imms12=0`；
- 多 load：在单 load 模式上令 `immu6=1`（count=1，源用 rd0）；
- 所有 load 的 `input_state` 预置 `rb1 = BINARY_BASE`（RAM 起始）。

具体 `encoding.word` 由 `verif/opcodes.yaml` 对应 `insn` 的 op/ha 与 `(op<<24)|(ha<<18)|(hb<<12)|(hc<<6)|hd` 手算得出。

### 上游引用

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-034a-load-encoding-deferred.md`（完整转述：背景、目标、现状诊断、方案 A/B、load_reg 二进制中的加载地址、encoding bits 修复、约束、验收、完成区与代码级 Architecture Review）

## 交付物

- `tests/vectors/isa/rd-load-store.yaml`：14 条 load encoding 测试重设计为 active（方案 B），`input_state` 预置 rb1，encoding base/dest 字段调整，`immu6 ≥ 1`

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **助记符**：`ldbs`/`ldbu`/`ldws`/`ldwu`/`ldts`/`ldtu`/`ldo`/`ldmbs`/… → `ld.sb`/`ld.ub`/`ld.sw`/`ld.uw`/`ld.st`/`ld.ut`/`ld.o`/`ldm.sb`/…（`insn` 带 `-rd` 后缀）。
2. **内存映射**：以 v5 `adr-0004-test-machine.md`（SPEC-008t）为准——RAM `0x8000_0000`、ROM `0x0010_0000`、exit port `0x1000_0000`；`BINARY_BASE` 取 RAM 起始（如 `0x80000000`）。addr=0 未映射的结论不变。
3. **编码字段**：以 v5 `contract-isa.md` §2.2 与 `verif/opcodes.yaml` 的 `fields` 为准；load 的 base/dest 字段位置须独立核对，不从 0628 反推。
4. **RB 语义**：0.5.3 有效地址低 48 位。
5. **多寄存器**：`immu6`（count）仍须 ≥1。

## 已知坑 / 结论

摘自 DADAO-0628 DL-034a：

1. **addr=0 未映射**：QEMU 访问会 hang，既不抛 ILLI 也不退出；deferred 根因。
2. **方案 B 正确性**：`ha=1(rd1)` 目标非 rd0、`hb=1(rb1)` base 非 rb0、`immu6=1` 非 0，均避开 ILLI；rb1 预置 RAM 地址后 load 合法。
3. **方案 A 前提**：仅当合约/实现明确 `ha=0 → ILLI` 时才可用，且需实现侧检查存在。
4. **encoding.word 必须手算**：从合约/opcodes.yaml 推导，不从 QEMU 行为反推。
5. **不改实现**：若需实现改动，另建任务。
6. **0628 结果**：49/49 PASS（原 35 + 新激活 14），0 timeout。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-034a-load-encoding-deferred.md`（完整转述）
- DADAO-0628：`.work/DADAO-0628/tests/vectors/isa/rd-load-store.yaml`（形态参考，禁止复制数据）
- 本项目：`.tao/knowledge/contract-isa.md` §4.1、`.tao/knowledge/adr-0004-test-machine.md`、`verif/opcodes.yaml`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. 原 14 条 load encoding 全部 `status: active`，`expected_fault: null`
2. 每条 `input_state` 含 RAM 合法基址（rb1 预置），dest 非 rd0、base 非 rb0
3. multi load 的 `immu6 ≥ 1`
4. 每条 `encoding.word` 与 `verif/opcodes.yaml` 的 `(word & mask) == value` 一致
5. 只改 `tests/vectors/isa/rd-load-store.yaml`
6. `python3 verif/validate_vectors.py` 零错误；`make check` PASS
7. （下游）QEMU harness 就绪后，该文件全部 active 测试 PASS、0 timeout
8. 未自行 commit

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
