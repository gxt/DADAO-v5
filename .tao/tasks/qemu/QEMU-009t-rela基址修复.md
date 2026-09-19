# QEMU-009t: rela 基址定向回归验证

**模块**：qemu
**项目里程碑**：M1
**依赖**：`QEMU-008t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `QEMU-008t` 产出的 `translate.c` 中 `trans_rela`（或对应 `trans_*`）
  - `.tao/knowledge/contract-isa.md` §4.7（PC 相对寻址）、§1.3.2（rb0=PC，只读）
  - `contracts/opcodes.yaml`（`rela.si-rb` 编码与 fields）、`contracts/legality_rules.yaml`
  - `tests/vectors/isa/reg-arith.yaml`（rela semantic/encoding 向量）
- 输出：验证报告（完成区记录），**不改任何补丁**（不修订 `series`）
- 约束：
  - **验证任务，不改补丁**：只对 `QEMU-008t` 实现中 `trans_rela` 的行为做定向回归验证
  - 验证基址取 `rb[0]`（PC），不得取 `rb[ha]`（目标寄存器自身）
  - 验证 `rbha` 目的为 rb0 → ILLI
  - 验证结果按 §4.7 公式，高 16 位按 spec 处理
  - 给出可机械判定的命令与期望

## 背景（完整）

### 目标

对 `QEMU-008t` 实现的 `rela.si` 做定向回归验证：确认基址计算使用 `rb[0]`（PC）而非 `rb[ha]`（自引用），结果符合 §4.7 公式。本任务**不修改任何补丁**，只验证实现任务已正确的行为，并给出可机械判定的验收命令与期望。

### 设计理由

- `rela.si` 是 PC 相对地址加载，语义基址必须是 PC（rb0），与目标寄存器无关。
- 若 `QEMU-008t` 实现正确，本任务直接 PASS；若发现缺陷，登记为遗留并由后续修复任务处理。
- 定向回归验证确保关键公式有明确的验收依据，避免「实现正确但无验证证据」。

### 关键概念 / 数据

- **公式（§4.7）**：`rbha = (PC & ~0xFFF) + sign_extend(imms18 << 12)`；`imms18 << 12` 得 30 位有符号偏移，`PC & ~0xFFF` 为 4KB 对齐基址；**高 16 位保持不变**（以 spec 原文为准，并与 `reg-arith.yaml` 向量核对）。
- **验证方法**：运行 `python3 tests/scripts/run_qemu_test.py tests/vectors/isa/reg-arith.yaml --filter mnemonic:rela`，检查 rela semantic/encoding 向量全 PASS。
- **基址验证**：若向量中包含 `rbha` 非 rb0 的 rela case，验证其计算基址为 `rb[0]`（PC）而非 `rb[ha]`。
- **ILLI 验证**：`ha == 0` 的 rela legality case 应返回 ILLI（`exit=0x88`）。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-024a-qemu-trans-rela-fix.md`（完整转述：背景、任务范围、验收条件、完成区与代码级 Architecture Review）。

## 交付物

- 验证报告（完成区记录）：rela 基址公式正确性、ILLI 触发、向量 PASS/FAIL 统计
- **不改补丁、不修订 series**

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **任务性质**：v5 本任务为**验证任务**（不改补丁）；0628 `DL-024a` 为修复任务（改补丁）。
2. **指令与格式**：0628 的 `rela` 与 v5 `rela.si`（riii，op 0x5A）不同。
3. **公式**：0628 用 `(rb[0] & ~0xFFF) + (imm18 << 12)` 且 48 位截断；v5 按 §4.7 `(PC & ~0xFFF) + sign_extend(imms18 << 12)`，且**高 16 位保持不变**。
4. **向量**：v5 rela 向量在 `tests/vectors/isa/reg-arith.yaml`，期望值独立手推自 §4.7。

## 已知坑 / 结论

1. **自引用 bug**：初版 `tcg_gen_ld_i64(base, …, rb[a->ha])` 用目标寄存器自身作基址；验证须确认基址为 `rb[0]`。
2. **48 位截断 vs 高 16 保持**：0628 对结果做了 48 位截断；v5 §4.7 要求高 16 位保持不变，须按 v5 spec 与向量核对。
3. **向量恢复**：rela semantic/encoding 需为 `active` 且全量 PASS。
4. **若发现缺陷**：登记为遗留（完成区），由后续修复任务处理；本任务不自行改补丁。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-024a-qemu-trans-rela-fix.md`
- 本项目：`.tao/knowledge/contract-isa.md` §4.7、§1.3.2；`contracts/opcodes.yaml`；`tests/vectors/isa/reg-arith.yaml`
- 本项目：`.tao/tasks/qemu/QEMU-008t-控制流与RB.md`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

| # | 验收项 | 现在可跑 / BLOCKED | 说明 |
|---|--------|-------------------|------|
| 1 | 运行 `python3 tests/scripts/run_qemu_test.py tests/vectors/isa/reg-arith.yaml --filter mnemonic:rela` 并记录输出 | BLOCKED | 原因：需 `QEMU-008t` 实现 rela 语义 + harness 普通模式可用（`020t`）。替代：最小 ROM 探针验证 rela 基址公式 |
| 2 | rela semantic/encoding 向量全 PASS（exit=0） | BLOCKED | 同上 |
| 3 | rela legality case（`ha == 0`）返回 ILLI（exit=0x88） | BLOCKED | 同上 |
| 4 | 完成区含真实运行输出与 PASS/FAIL 统计 | 现在可跑 | |
| 5 | 若发现 `trans_rela` 行为与 §4.7 不一致，在完成区登记为遗留（含具体偏差描述） | 现在可跑 | |

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
