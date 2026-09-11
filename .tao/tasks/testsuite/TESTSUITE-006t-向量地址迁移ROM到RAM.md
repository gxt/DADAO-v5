# TESTSUITE-006t: 语义向量内存地址迁移 ROM → RAM

**模块**：testsuite
**项目里程碑**：M1
**依赖**：`TESTSUITE-002t`、`SPEC-008t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `tests/vectors/isa/rd-load-store.yaml`、`tests/vectors/isa/rb-ops.yaml`（TESTSUITE-002t 向量）
  - `.tao/knowledge/adr-0004-test-machine.md`（SPEC-008t：内存映射 ROM/RAM/exit port）
  - `.tao/knowledge/contract-isa.md` §4（访存语义、有效地址计算）
- 输出：上述文件中所有 `class: semantic` 向量的 `rb2`（及 `rb0`）寄存器值、`input_state.memory[*].address`、`expected_state.memory[*].address` 由 ROM 地址迁移到 RAM scratch 区
- 约束：
  - **只修改** `class: semantic` 向量的地址字段；不改 `encoding.word`
  - **不改** 任何 `legality`/`boundary`/`encoding` 类向量
  - **不改** `expected_state.rd`/`rb` 的寄存器值（值不变，只是地址换了）
  - 新地址必须落在 ADR-0004 定义的 RAM 范围内
  - 期望地址必须按**有效地址公式** `EA = base + offset` 计算，不做 naive 线性映射
  - 完成后不自行 commit

## 背景（完整）

### 目标

将所有 load/store `class: semantic` 向量中指向 ROM 的地址字段，统一迁移到 RAM scratch 区，使 harness 的内存初始化与回读不再被 ROM 只读属性静默吞掉。

### 设计理由

0628 现象：

- QEMU patch 对 ROM 执行 `memory_region_set_readonly(rom, true)`——写入静默丢弃；
- `emit_memory_setup`：对 `input_state.memory` 执行 store 初始化测试内存 → 写入 ROM → 静默丢弃 → load 读到原始 ROM 内容而非期望值；
- `emit_state_compare`：对 `expected_state.memory` 执行 load 回读 → 读到原始 ROM 内容 → XOR ≠ 0 → 全部 FAIL。

故所有语义向量的内存地址必须放在**可写 RAM**。0628 涉及 2 个文件共 26 条 semantic 向量。

### 关键概念 / 数据

**地址映射规则**：

```
旧 base（ROM）：0x0000000000100000
新 base（RAM）：0x0000000087FF0000   （RAM 顶部 scratch 区）
old_addr = 0x100000 + offset  →  new_addr = 0x87FF0000 + offset
```

| 旧地址 | 新地址 | offset |
|--------|--------|--------|
| `0x0000000000100000` | `0x0000000087FF0000` | +0 |
| `0x0000000000100001` | `0x0000000087FF0001` | +1 |
| `0x0000000000100002` | `0x0000000087FF0002` | +2 |
| `0x0000000000100004` | `0x0000000087FF0004` | +4 |
| `0x0000000000100008` | `0x0000000087FF0008` | +8 |
| `0x00000000001000FF` | `0x0000000087FF00FF` | +255 |
| `0x0000000000100FFF` | `0x0000000087FF0FFF` | +4095 |

**例外：带负偏移的 store（如 `st.b`）**：若向量 `expected_state.memory.address` 原值等于 `base + offset`，迁移后必须等于 `new_base + offset`，而不是 naive 映射。

0628 实例：`stb rd1, rb2, -4`，EA = rb2 + (-4)。原 YAML 写 `0x100FFC`（= base + 0xFFC）与 EA 语义不一致（正确应为 `0x0FFFFC`）。迁移后：

```
rb2:  0x0000000000100000 → 0x0000000087FF0000
EA:   0x0000000000100FFC → 0x0000000087FEFFFC   （= 0x87FF0000 - 4）
```

不得用 naive 映射（`0x87FF0FFC`），必须用 `new_base + (-4)`。

### 上游引用

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-022c-vector-ram-addresses.md`（完整转述：背景三因、目标、地址映射规则与例外、逐向量改动表、约束、验收脚本、代码级 Architecture Review）
- DADAO-0628：`.work/DADAO-0628/docs/adr/0004-test-machine.md`（ROM 只读 / RAM 布局）

## 交付物

- `tests/vectors/isa/rd-load-store.yaml`：`class: semantic` 向量的 rb2/rb0 与 memory 地址迁移
- `tests/vectors/isa/rb-ops.yaml`：同上

（v5 向量为重新生成，具体条数与 case 序号以 TESTSUITE-002t 实际数据为准；迁移规则不变。）

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **助记符**：`ldo`→`ld.o`、`sto`→`st.o`、`stb`→`st.b`、`ldmo`→`ldm.o`、`stmo`→`stm.o` 等。
2. **内存映射来源**：以 v5 `adr-0004-test-machine.md`（SPEC-008t）为准——ROM `0x0010_0000`(64KB)、RAM `0x8000_0000`(128MB)、exit port `0x1000_0000`(8B)。RAM 范围 `[0x80000000, 0x87FFFFFF]`，故新 base `0x87FF0000` 仍合法；若 ADR-0004 最终取值不同，以 ADR 为准并同步更新映射。
3. **RB 语义**：0.5.3 有效地址为低 48 位，高 16 位在地址计算时忽略；地址值须为 48-bit 有效地址。
4. **向量条数/序号**：0628 的 26 条（23+3）与逐条索引表**不照搬**；v5 按实际 `class: semantic` case 重新枚举。
5. **例外通用化**：任何 `EA = base + offset`（含负偏移）都按公式计算，不限于 `stb`。

## 已知坑 / 结论

摘自 DADAO-0628 DL-022c 代码级 Architecture Review：

1. **ROM 只读 → 写入静默丢弃**：语义向量绝不能用 ROM 地址。
2. **新地址必须在 RAM**：`[0x80000000, 0x87FFFFFF]`；零地址（未映射）也不可。
3. **带偏移的期望地址必须按 EA 公式**：naive 线性映射会掩盖/引入 bug；0628 的 `stb` 例外即为此。
4. **只动 semantic**：`legality`/`boundary`/`encoding` 即使引用旧地址也不改。
5. **`encoding.word` 不变**：迁移只改寄存器/内存值，不触碰指令编码。
6. **`rela` 的 rb0=0x100000 是算术输入**（不做访存），不迁移。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-022c-vector-ram-addresses.md`（完整转述）
- DADAO-0628：`.work/DADAO-0628/docs/adr/0004-test-machine.md`
- 本项目：`.tao/knowledge/adr-0004-test-machine.md`（SPEC-008t）、`.tao/knowledge/contract-isa.md` §4
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `class: semantic` 向量中不再出现 ROM 范围地址（`[0x100000, 0x10FFFF]`）
2. 所有迁移后地址落在 RAM 范围 `[0x80000000, 0x87FFFFFF]`
3. 带偏移的期望地址按 `EA = new_base + offset` 计算（含负偏移例外）
4. `encoding.word` 与 `expected_state.rd/rb` 未被改动
5. `legality`/`boundary`/`encoding` 类向量未被改动
6. `python3 verif/validate_vectors.py` 零错误；`make check` PASS
7. 未自行 commit

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
