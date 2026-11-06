# SPEC-194t: 转换指令舍入编码三分（ADR-0050 D1–D7）

**模块**：spec
**项目里程碑**：M11
**依赖**：`ADR-0050`（Accepted，2026-11-06 用户确认 D1–D7）
**状态**：待开始

## 依据

`ADR-0050` 已冻结：

- **D1**：18 条格式转换按「结果是否依赖舍入」分三类 —— 15 条六档 one-hot、3 条精确 SBZ、4 条复制保留计数
- **D2**：六档 = `0x01` RNE / `0x02` RNA / `0x04` RTZ / `0x08` RUP / `0x10` RDN / `0x20` dynamic（读 `rf0`）
- **D3**：精确转换（`ft2fo`、`it2fo`、`ut2fo`）低 6 位 SBZ
- **D4**：复制类（`ft2ft`、`fo2fo`、`rd2rf`、`rf2rd`）保留 1–63 计数
- **D5**：inexact ⇒ NX（只实现 Exact 族）；NaN/Inf/越界 ⇒ 饱和 + NV，不置 NX
- **D6**：工具链映射（C f2i cast → `0x04`；i2f/`fo2ft` → `0x20`；固定方向语言 → 静态档）
- **D7**：QEMU/gem5 按字段方向；旧「`immu6`=个数」的转换编码作废（不兼容）

## 目标

1. `contracts/opcodes.yaml`：15 条转换的 `immu6` 语义改 one-hot，`rule_refs` 改为 `dst_rd0`/`dst_rf0` + `encode_onehot`，删除 `mreg_zero`/`mreg_range_overflow`/`mreg_range_overlap`；3 条精确转换改为 `encode_sbz`（`immu6 == 0`），保留 `dst_rf0`；4 条复制完全不动。
2. `contracts/legality_rules.yaml`：`mreg_zero`/`mreg_range_overflow`/`mreg_range_overlap` 的覆盖范围描述收窄到「复制类与其它块指令」；`encode_onehot` 增列「转换族六档」；`encode_sbz` 增列「精确转换低 6 位」。
3. `spec/SimRISC-07`（格式转换指令节）：
   - 低 6 位语义按三类写明；
   - 六档方向定义与 `0x20` = dynamic；
   - NX/NV 口径（D5）；
   - 精确转换的 SBZ；
   - 删除「块转换/范围重叠」对转换族的适用（复制类保留）。
4. `.tao/contracts/contract-fp.md` §3/§12 同步（叙述 + 规则引用）。
5. `spec` 的 LEGALITY 块用 `tools/spec/gen_legality_list.py --apply` 重生成，`--verify` 必须一致。
6. 不改任何实现（LLVM/QEMU/gem5）与测试向量；实现迁移归 `INTEG-058t`。

## 范围 / 非范围

**在范围内**：`contracts/opcodes.yaml`、`contracts/legality_rules.yaml`、`spec/SimRISC-07-浮点运算.md`、`.tao/contracts/contract-fp.md`、本任务书、`milestones.md`。

**不在范围**：LLVM/QEMU/gem5 实现、`tests/**`、`tools/**`（除 `gen_legality_list` 的生成动作）、其它 spec 册。

## 验收标准

1. `make check-legality-drift` rc=0；`make check-legality-invariants` rc=0；`gen_legality_list.py --verify` rc=0。
2. `make check-scope`、`validate-encoding`、`check-isa-coverage`、`check-asm-list`、`check-asm-list-drift` rc=0。
3. `make check-spec-refs`、`check-spec-numbering`、`check-spec-changelog`、`check-spec-purity`、`check-spec-cite-targets` rc=0；`make check`（L1）rc=0。
4. 编码位值（`opc`/`ha`/`mask`/`value`）不变；只改 `immu6` 语义与合法性/叙述。
5. 抽样核对：15 条 one-hot、3 条 SBZ、4 条计数，逐条与 ADR-0050 D1 对照；计数（22 条）现场统计，不写死。
6. 完成区 ≤30 行；状态 `待验收`。

## 说明

- 本任务只改「规范与契约」，因此 `check-legality-drift`（spec LEGALITY 块 vs contracts）必须同步重生成，不能手改两块中的一块。
- 实现侧（LLVM 发码、QEMU/gem5 解码）在 `INTEG-058t` 落地前会与新契约不一致，属预期；本任务不跑依赖实现的语义门控（`check-inst` 等）作为验收项，但 L1 必须绿。
