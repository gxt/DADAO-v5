# QEMU-009t: rela 用 rb[0] 作基址修复

**模块**：qemu
**项目里程碑**：M1
**依赖**：`QEMU-008t`

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `QEMU-008t` 产出的 `translate.c` 中 `trans_rela`（或对应 `trans_*`）
  - `.tao/knowledge/contract-isa.md` §4.11（PC 相对寻址）、§1.3.2（rb0=PC，只读）
  - `verif/opcodes.yaml`（`rela.si-rb` 编码与 fields）、`verif/legality_rules.yaml`
  - `tests/vectors/isa/rb-ops.yaml`（rela semantic/encoding 向量）
- 输出：修订后的 `components/qemu/patches/0005-dadao-ctrl-flow.patch`（或等价补丁）、向量状态更新
- 约束：
  - 基址取 `rb[0]`（PC），不得取 `rb[ha]`（目标寄存器自身）
  - `rbha` 目的为 rb0 → ILLI
  - 结果按 §4.11 公式，高 16 位按 spec 处理（不得照抄 0628 的 48 位截断写法）
  - 完成后不自行 commit

## 背景（完整）

### 目标

修正 `rela.si` 的基址计算：spec 明确基址为 `rb[0]`（PC），目标为 `rb[ha]`；初版误用 `rb[ha]`（自引用）。0628 对应任务 `DL-024a` 将 `trans_rela` 的基址 load 从 `rb[ha]` 改为 `rb[0]`，并把 2 条 rela 向量从 `deferred` 改回 `active`，经代码级评审 Accepted。

### 设计理由

- `rela.si` 是 PC 相对地址加载，语义基址必须是 PC（rb0），与目标寄存器无关；自引用会产生错误的地址。
- 同一 bug 曾导致 rela 的 encoding 测试超时/失败，须一并恢复向量。

### 关键概念 / 数据

- **公式（§4.11）**：`rbha = (PC & ~0xFFF) + sign_extend(imms18 << 12)`；`imms18 << 12` 得 30 位有符号偏移，`PC & ~0xFFF` 为 4KB 对齐基址，可覆盖 512MB 内的 PC 相对寻址；**高 16 位保持不变**（以 spec 原文为准，并与 `rb-ops.yaml` 向量核对）。
- **QEMU 实现要点**：基址 load 用 `offsetof(CPUDADAOState, rb[0])`；对基址做 4KB 对齐（`& ~0xFFF`）；偏移 `(int64_t)a->imm18 << 12`；结果按 §4.11 写 `rb[ha]`；`ha == 0` → ILLI。
- **0628 参考实现**（仅语义参考，不照抄）：base load 改为 `rb[0]`，`& 0x0000FFFFFFFFFFFF` 48 位掩码，`& ~0xFFF` 对齐，`+ (imm18 << 12)`，再 48 位截断，写 `rb[ha]`。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-024a-qemu-trans-rela-fix.md`（完整转述：背景、任务范围、验收条件、完成区与代码级 Architecture Review）。

## 交付物

- 修订后的 `components/qemu/patches/0005-dadao-ctrl-flow.patch`：`trans_rela` 基址改为 `rb[0]`。
- `tests/vectors/isa/rb-ops.yaml`：rela semantic/encoding 从 `deferred` 改回 `active`（若 `QEMU-008t` 尚未改）。
- `components/qemu/patches/series`：序号不变或追加（以 v5 实际序列为准）。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **指令与格式**：0628 的 `rela` 与 v5 `rela.si`（riii，op 0x5A）不同；`trans_*` 名按 v5 decodetree。
2. **公式**：0628 用 `(rb[0] & ~0xFFF) + (imm18 << 12)` 且 48 位截断；v5 按 §4.11 `(PC & ~0xFFF) + sign_extend(imms18 << 12)`，且**高 16 位保持不变**——不得直接沿用 0628 的整 64 位覆盖。
3. **向量**：v5 rela 向量在 `tests/vectors/isa/rb-ops.yaml`，期望值须独立手推自 §4.11。
4. **补丁组织**：0628 将 rela 修复并入后续补丁（`0012-dadao-rela-pc-base.patch`）；v5 可修订 `0005` 或单独追加，以 `series` 实际为准。

## 已知坑 / 结论

摘自 0628 `DL-024a` 完成区与代码级 Architecture Review：

1. **自引用 bug**：初版 `tcg_gen_ld_i64(base, …, rb[a->ha])` 用目标寄存器自身作基址；修复为 `rb[0]`。
2. **48 位截断 vs 高 16 保持**：0628 对结果做了 48 位截断；v5 §4.11 要求高 16 位保持不变，须按 v5 spec 与向量核对，不可照抄。
3. **向量恢复**：rela semantic/encoding 需从 `deferred` 改回 `active` 并全量 PASS。
4. **不引入回退**：修复不得导致其他向量失败。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-024a-qemu-trans-rela-fix.md`
- 本项目：`.tao/knowledge/contract-isa.md` §4.11、§1.3.2；`verif/opcodes.yaml`；`tests/vectors/isa/rb-ops.yaml`
- 本项目：`.tao/tasks/qemu/QEMU-008t-控制流与RB.md`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `trans_rela`（v5 名）基址取自 `rb[0]`，不再自引用 `rb[ha]`
2. 结果符合 §4.11（含高 16 位处理）；`ha == 0` → ILLI
3. `rb-ops.yaml` 中 rela semantic/encoding 为 `active` 且运行 PASS
4. `make build-qemu` PASS；不引入其他向量回退
5. 完成区含真实构建/运行输出；未自行 commit

## 完成区

**状态**：待开始
**Commit**：
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
