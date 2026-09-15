# TESTCASES-009t: rd-load-store deferred 测试重设计（load encoding）

**模块**：testcases
**项目里程碑**：M1
**依赖**：`TESTCASES-006t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `tests/vectors/isa/rd-load-store.yaml`（TESTCASES-002t/006t 向量，含 `status: deferred` 的 load encoding）
  - `.tao/knowledge/contract-isa.md` §4.1（load/store 合法性、对齐）、§2.2（格式）
  - `.tao/knowledge/adr-0004-test-machine.md`（内存映射、未映射区行为）
  - `contracts/opcodes.yaml`（load 指令编码字段）
- 输出：重设计后的 `tests/vectors/isa/rd-load-store.yaml`（原 deferred 的 load encoding 全部由 deferred → active；条数以 TESTCASES-002t 实际数据为准）
- 约束：
  - 只修改 `tests/vectors/isa/rd-load-store.yaml`（纯数据任务）
  - 不改实现源码；若需要实现侧改动，另建任务
  - 基址必须指向 RAM 合法地址（如 `rb1 = 0xffff_0000_0000`），不用未映射地址
  - 若预置的基址寄存器与 harness 的 SP（`rb1 = 0xffff_00ff_0000`，ADR-0004 D6.5）冲突，须在 notes 说明并改用不冲突的寄存器
  - 完成后不自行 commit

## 背景（完整）

### 目标

将 load encoding 测试从「零地址 unmapped 访问」重新设计为**合法可执行的 active 测试**，全部激活。

### 设计理由

0628 `rd-load-store.yaml` 中有 14 条 load encoding 测试 `status: deferred`：

- 原设计用 `rb0=0`（零地址）作为 load base → addr=0 → 访问 unmapped 区域。
- v5 根因（ADR-0004 D5.6）：addr=0 不在 ROM/RAM/Exit 任一区域 → **unmapped，退出码 `0x87`（确定性 fault）**；0628 的「QEMU 卡住、既不抛 ILLI 也不退出」是其旧内存映射下的现象，v5 **不适用**。无论 fault 还是 hang，addr=0 都不是合法的 encoding 期望，须改用 RAM 合法地址。

### 关键概念 / 数据

**方案 A（备选）：dest `rdha = rd0` → ILLI**

- `contract-isa.md` §4.1.1 + `legality_rules.yaml` `rd_dest_rd0`：load 的目的字段 `rdha` 为 `rd0` → **ILLI**（合约直接规定，无需实现侧额外检查）。
- 改 `expected_fault: null → ILLI`、`status: deferred → active`。因该 fault 由合约保证，**不依赖实现细节**。
- 局限：只验证「非法目的被拒」，未验证合法 load 路径，故仅作备选。

**方案 B（采用）：使用有效 RAM 基址**

- 在 `input_state` 中预置 `rb1 = 0xffff_0000_0000`（ADR-0004 RAM 基址 = `BINARY_BASE`）
- 编码中 base 字段 = rb1（非 rb0），dest = rd1（非 rd0）
- `expected_fault: null`、`status: active`，加载合法 RAM 地址
- 加载值 = 测试 binary 自身内容（可接受）
- multi load 的 `immu6` 保持 ≥1（=0 → ILLI）

0628 采用的字段模式（仅描述结构，**不含具体 0.4.1 编码字**；v5 从 `contracts/opcodes.yaml` 的 op/字段与 §2.2 公式重新手算）：

- 单 load：`ha(dest)=1(rd1)`、`hb(base)=1(rb1)`、`imms12=0`；
- 多 load：在单 load 模式上令 `immu6=1`（count=1，源用 rd0）；
- 所有 load 的 `input_state` 预置 `rb1 = 0xffff_0000_0000`（RAM 起始，ADR-0004 D2.2 加载基址）。

具体 `encoding.word` 由 `contracts/opcodes.yaml` 对应 `insn` 的 `op`/`ha`（`op=value>>24`、`ha=(value>>18)&0x3f`）与 `(op<<24)|(ha<<18)|(hb<<12)|(hc<<6)|hd` 手算得出。

### 上游引用

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-034a-load-encoding-deferred.md`（完整转述：背景、目标、现状诊断、方案 A/B、load_reg 二进制中的加载地址、encoding bits 修复、约束、验收、完成区与代码级 Architecture Review）

## 交付物

- `tests/vectors/isa/rd-load-store.yaml`：全部 load encoding 测试重设计为 active（方案 B，条数以 TESTCASES-002t 实际数据为准），`input_state` 预置 rb1，encoding base/dest 字段调整，`immu6 ≥ 1`

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **助记符**：`ldbs`/`ldbu`/`ldws`/`ldwu`/`ldts`/`ldtu`/`ldo`/`ldmbs`/… → `ld.sb`/`ld.ub`/`ld.sw`/`ld.uw`/`ld.st`/`ld.ut`/`ld.o`/`ldm.sb`/…（`insn` 带 `-rd` 后缀）。
2. **内存映射**：以 v5 `adr-0004-test-machine.md`（SPEC-006t）为准——boot ROM `0xffff_ffff_0000`（64 KiB）、RAM `0xffff_0000_0000`–`0xffff_00ff_ffff`（16 MiB）、exit port `0xffff_8000_0000`；`BINARY_BASE` = RAM 起始 `0xffff_0000_0000`。0628 的 `RAM 0x8000_0000`/`ROM 0x0010_0000`/`exit 0x1000_0000` 属已废弃的 `dadao-virt` 布局（ADR-0004 明确不沿用），**不得使用**。
3. **addr=0 语义**：ADR-0004 D5.6 → unmapped `0x87`（确定性）；0628 的「QEMU hang」**不适用**。
4. **编码字段**：以 v5 `contract-isa.md` §2.2 与 `contracts/opcodes.yaml` 的 `fields` 为准；load 的 base/dest 字段位置须独立核对，不从 0628 反推。
5. **RB 语义**：0.5.3 有效地址低 48 位。
6. **多寄存器**：`immu6`（count）仍须 ≥1。

## 已知坑 / 结论

摘自 DADAO-0628 DL-034a：

1. **addr=0 未映射**：ADR-0004 D5.6 → `0x87`（确定性 fault）；不是合法 encoding 期望，deferred 根因。
2. **方案 B 正确性**：`ha=1(rd1)` 目标非 rd0、`hb=1(rb1)` base 非 rb0、`immu6=1` 非 0，均避开 ILLI；rb1 预置 RAM 地址后 load 合法。
3. **方案 A 前提**：`rdha=rd0 → ILLI` 由合约（`rd_dest_rd0`）直接规定，不依赖实现侧检查；但仅覆盖非法路径。
4. **encoding.word 必须手算**：从合约/opcodes.yaml 推导，不从 QEMU 行为反推。
5. **不改实现**：若需实现改动，另建任务。
6. **0628 结果**：49/49 PASS（原 35 + 新激活 14），0 timeout；条数仅作规模参考，v5 以实际数据为准。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-034a-load-encoding-deferred.md`（完整转述）
- DADAO-0628：`.work/DADAO-0628/tests/vectors/isa/rd-load-store.yaml`（形态参考，禁止复制数据）
- 本项目：`.tao/knowledge/contract-isa.md` §4.1、`.tao/knowledge/adr-0004-test-machine.md`、`contracts/opcodes.yaml`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. 原 deferred 的 load encoding 测试全部 `status: active`、`expected_fault: null`
2. 每条 `input_state` 含 RAM 合法基址（`rb1 = 0xffff_0000_0000`），dest 非 rd0、base 非 rb0
3. multi load 的 `immu6 ≥ 1`
4. 每条 `encoding.word` 与 `contracts/opcodes.yaml` 的 `(word & mask) == value` 一致
5. 只改 `tests/vectors/isa/rd-load-store.yaml`
6. `python3 tools/testcases/validate_vectors.py` 零错误；`make check` PASS
7. （下游）QEMU harness 就绪后，该文件全部 active 测试 PASS、0 timeout
8. 未自行 commit

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
