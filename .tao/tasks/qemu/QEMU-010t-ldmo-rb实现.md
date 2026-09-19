# QEMU-010t: ldmo_rb 实现

**模块**：qemu
**项目里程碑**：M1
**依赖**：`QEMU-009t`、`SPEC-006t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `QEMU-009t` 产出的 `translate.c`（RB 存取已实现，`ldm.o-rb` 仍为 ILLI 桩）
  - `.tao/knowledge/contract-isa.md` §4.2（存取 RB 寄存器：`ldm.o-rb`/`stm.o-rb`）、§1.5（48 位有效地址）
  - `.tao/knowledge/adr-0004-test-machine.md`（MALIGN 可观测）
  - `contracts/opcodes.yaml`（`ldm.o-rb` 的 op/格式/legality）、`tests/vectors/isa/mem-rb.yaml`
- 输出：修订后的 `components/qemu/patches/0006-dadao-ctrl-flow.patch`、向量状态更新
- 约束：
  - 参考对称的 `stm.o-rb` 实现
  - EA = `(rb[hb] + rd[hc]) mod 2^48`
  - 循环 `immu6` 次，每次 8 字节大端 load，地址 `& 0x0000FFFFFFFFFFFF`
  - ILLI 检查按 §4.2：`rbha == rb0`、`immu6 == 0`、`rbha + immu6 > 64`
  - 8 字节对齐，未对齐 → MALIGN
  - 完成后不自行 commit

## 背景（完整）

### 目标

将 `ldm.o-rb`（RB 多寄存器加载，0628 名 `ldmo_rb`）从 ILLI 桩替换为真实实现，与 `stm.o-rb` 对称。0628 对应任务 `DL-025a` 将 `trans_ldmo_rb` 从 `GEN_ILLEGAL_INSN` 替换为完整实现，经代码级评审 Accepted（N1：`hc+hd>64` 未检查，与既有 `do_ldm` 一致）。

### 设计理由

- RB 多重加载是 RB 存取的核心组成，`stm.o-rb` 已实现，加载侧缺失会导致非对称与向量失败。
- 地址计算遵循 §1.5 的 48 位有效地址；对齐遵循 §4.2 的 8 字节要求。

### 关键概念 / 数据

- **语义（§4.2）**：`ldm.o-rb rbha, rbhb, rdhc, immu6`：从 `rbhb + rdhc` 地址加载 `immu6` 个连续 RB 寄存器到 `rbha` 起。
- **EA**：`EA = (rb[hb] + rd[hc]) & 0x0000FFFFFFFFFFFF`；循环内 `EA_i = (EA + i×8) & 0x0000FFFFFFFFFFFF`。
- **ILLI**：`rbha == rb0`；`immu6 == 0`；`rbha + immu6 > 64`。
- **对齐**：8 字节，`MO_ALIGN_8`；未对齐 → MALIGN 精确（见 `QEMU-007t`）。
- **decodetree**：`ldm.o-rb`（0628 `ldmo_rb`）的 pattern 已在 `QEMU-004t` 生成，本任务不改 `insn.decode`。
- **0628 参考实现**（仅语义参考）：ILLI 检查 → base/idx 各自 48 位掩码 → 相加后再掩码 → 循环 `immu6` 次 `mov`/`addi i*8`/`qemu_ld(MO_BE|MO_UQ|MO_ALIGN_8)`/写 `rb[ha+i]`。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-025a-qemu-ldmo-rb-impl.md`（完整转述：背景、任务范围、验收条件、完成区与代码级 Architecture Review，含 N1）。

## 交付物

- 修订后的 `components/qemu/patches/0006-dadao-ctrl-flow.patch`：`trans_ldm_o_rb`（v5 名）实现。
- `tests/vectors/isa/mem-rb.yaml`：`ldm.o-rb` 向量从 `deferred` 改回 `active`（按 v5 向量实际）。
- `components/qemu/patches/series`：序号不变或追加（以 v5 实际序列为准）。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **助记符/格式**：0628 `ldmo_rb`（rrri）→ v5 `ldm.o-rb`（op 0x3A，rrri）；`trans_*` 名按 v5 decodetree。
2. **源/目标约定**：v5 `ldm.o-rb rbha, rbhb, rdhc, immu6`，目标为 RB bank；`rdhc` 为单一索引寄存器。
3. **`hc+hd>64` 检查**：0628 任务曾要求但实现未做（N1），因其 `rdhc` 为单一索引而非范围；v5 以 §4.2 与 `contracts/legality_rules.yaml` 为准，不盲目照搬。
4. **对齐/异常**：以 v5 ADR-0004 D4 与 `QEMU-007t` 的 MALIGN 机制为准。
5. **补丁组织**：0628 将 `ldmo_rb` 改动留在工作树，后并入较大补丁；v5 修订 `0006` 或单独追加。

## 已知坑 / 结论

摘自 0628 `DL-025a` 完成区与代码级 Architecture Review：

1. **`ha == 0` → ILLI**：RB 目的为 rb0（PC）非法。
2. **`hd == 0` → ILLI**：加载个数为 0 非法。
3. **`ha + hd > 64` → ILLI**：目标 bank 越界。
4. **EA 48 位截断**：EA 计算结果截断到 48 位（`& 0x0000FFFFFFFFFFFF`）；`rb[hb]`/`rd[hc]` 的值本身为 64 位，参与 EA 计算时由 EA 截断覆盖（不对寄存器值做截断）。
5. **大端 + ALIGN_8**：`MO_BE | MO_UQ | MO_ALIGN_8`。
6. **N1（`hc+hd>64`）**：0628 未检查，与既有 `do_ldm` 一致；v5 按自身 legality 规则决定。
7. **向量地址**：0628 曾用 `ldmo rb1,rb0,rd0,1`（地址 0）；v5 向量须在有效内存图内（ADR-0004），避免超时。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-025a-qemu-ldmo-rb-impl.md`
- 本项目：`.tao/knowledge/contract-isa.md` §4.2、§1.5；`contracts/opcodes.yaml`；`contracts/legality_rules.yaml`
- 本项目：`.tao/tasks/qemu/QEMU-006t-RD存取与MALIGN.md`（MALIGN 精确异常已并入 006t）、`.tao/tasks/qemu/QEMU-008t-控制流与RB.md`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

| # | 验收项 | 现在可跑 / BLOCKED | 说明 |
|---|--------|-------------------|------|
| 1 | `trans_ldm_o_rb`（v5 名）由 ILLI 桩替换为完整实现，与 `stm.o-rb` 对称 | 现在可跑 | `make build-qemu` + 代码审查 |
| 2 | ILLI 检查（`rbha==rb0`、`immu6==0`、`rbha+immu6>64`）先于写；EA 48 位截断；大端 8 字节 load | 现在可跑 | 代码审查 |
| 3 | 未对齐 → MALIGN 精确 | 现在可跑 | 最小 ROM 探针 |
| 4 | `mem-rb.yaml` 中 `ldm.o-rb` 向量为 `active` 且运行 PASS | BLOCKED | 原因：harness 普通模式需 `020t`。替代：最小 ROM 探针 |
| 5 | `make build-qemu` PASS；不引入其他向量回退 | 现在可跑 | 构建 |
| 6 | 完成区含真实构建/运行输出；未自行 commit | 现在可跑 | |

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
