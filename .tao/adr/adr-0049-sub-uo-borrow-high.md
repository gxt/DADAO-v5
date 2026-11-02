# ADR-0049: `sub.uo` 的 `rdHA` 定义为借位 0/1（修正“128 位高半”表述冲突）

**状态**：Accepted（2026-10-26，用户原话裁定）
**日期**：2026-10-26
**决策者**：用户（2026-10-26，原话见 `## 状态说明`）
**关联**：`spec/SimRISC-04 §1.1`、`spec/SimRISC-00 附录 0.5.6-rc`、`.tao/contracts/contract-isa.md §6.1.1`、`manifests/spec-readonly.lock.toml`；QEMU `trans_sub_uo_rrrr_rd`、LLVM `sub_uo_rd`、`tools/testcases/{generate_isa_vectors,009t-audit}.py`、`tests/vectors/isa/reg-arith.yaml`、`components/golden/*`；任务 `GOLDEN-001t`

## Context（背景）

`sub.uo {rdHA, rdHB}, rdHC, rdHD` 是无符号双目的 64 位减法。规范原文同时包含两种不能同时成立的表述：

- `spec/SimRISC-04 §1.1` 总述：“`rdHA` 存放结果的高 64 位，`rdHB` 存放结果的低 64 位。”
- 同节变体说明与指令表：“源操作数按零扩展（ZX）至 128 位……`rdHA` 为进位/借位（0 或 1）”；`sub.uo … @@ ZX，rdHA = 借位`。
- `.tao/contracts/contract-isa.md §6.1.1` 在同一行写 `rdha:rdhb = rdhc − rdhd`，又写 `rdha` 为借位（0 或 1）。

不借位（`rdHC ≥ rdHD`）时两种说法都得到 `rdHA = 0`；借位（`rdHC < rdHD`）时，128 位结果高半为全 1，而借位标志为 1。例如 `0 − 1`：

| 解释 | `rdHA` | `rdHB` |
| --- | --- | --- |
| 128 位结果高半 | `0xFFFFFFFFFFFFFFFF` | `0xFFFFFFFFFFFFFFFF` |
| 借位 0/1 | `0x0000000000000001` | `0xFFFFFFFFFFFFFFFF` |

现场各部分的既有假设并不一致：

| 部分 | 现状 | 倾向 |
| --- | --- | --- |
| QEMU `trans_sub_uo_rrrr_rd` | `hi = (rdhc < rdhd)` | 借位 0/1 |
| `docs/DDLN/A-指令系统/DD-A007` | `.uo` 的 `rdHA` 是进位/借位；`.so` 是高 64 位 | 借位 0/1 |
| `tools/testcases/generate_isa_vectors.py` | `hi = (a − b) >> 64` | 128 位高半 |
| `tools/testcases/009t-audit.py` | 无符号分支把 `hi` 归一到 0/1 | 借位 0/1 |
| `tests/vectors/isa/reg-arith.yaml` | 只有正数与相等边界，无借位用例 | 未覆盖 |
| LLVM 后端 | 只用 `sub.uo {rd0, dst}, …`，高位丢弃 | 中立 |
| golden | 借位且高目的非 `rd0` 时抛 `SpecificationGap` | 拒绝作答 |

该选择影响多字减法链、编译器 lowering、QEMU 行为与外部契约；命中 `docs/Process-03` 的“外部契约 / 跨模块 / 多方案 / 结论固化”判据，立本 ADR。

## Decision（决策）

### D1 — `sub.uo` 的 `rdHA` = 借位（0/1）

- `rdHB = (rdHC − rdHD) mod 2^64`。
- `rdHA = 1` 当且仅当 `rdHC < rdHD`，否则 `0`。
- **不写** 128 位结果的全 1 高半；需要 128 位有符号高半时使用 `sub.so`。
- `add.uo` 的 `rdHA` 仍为进位（0/1）；`add.so`/`sub.so`/`mul.uo`/`mul.so` 的 `rdHA` 仍为高 64 位、`rdHB` 为低 64 位。
- 理由：与 `spec/SimRISC-04` 的变体说明、QEMU 现行实现和 DDLN 解释一致；`add.uo` 的进位与 128 位结果高半恰好重合，而 `sub.uo` 的借位与全 1 高半不应混为一谈；不改变 QEMU 现有行为。
- 该接口也是未来 i128/i256 多字运算的基元：借位 + 低 64 位可以链式组合；若返回 128 位高半，多字减法组合不自然。

## Rationale（理由）

- 若选“128 位高半”，QEMU、DDLN 与既有“借位 0/1”文字都要改，且会改变已实现的功能模型行为，外部影响更大。
- 若继续保留 `SpecificationGap`，golden 对借位输入没有参考答案，无法支撑交付与 reviewer 验收。
- 借位与低 64 位差足以构成完整、可组合的多字减法接口；需要 128 位有符号高半的场景由 `sub.so` 覆盖。

**被否方案（记录）**：

- 方案 A：`rdHA` = 128 位结果高 64 位（借位时全 1）。否决：与 QEMU/DDLN/变体说明冲突，需改功能模型行为。
- 保留 `SpecificationGap`。否决：交付不能对借位输入给出 golden 答案。

## Consequences（影响）

- `spec/SimRISC-04 §1.1` 总述与变体说明、`spec/SimRISC-00` 附录 `0.5.6-rc` 同步；版本仍为 `0.5.6-rc`（未发布，不归档）。
- `.tao/contracts/contract-isa.md §6.1.1` 的 `sub.uo` 行改为“低 64 位差 + 0/1 借位”，并删除 `rdha:rdhb = rdhc − rdhd` 对 `sub.uo` 的表述。
- golden 去掉 `SpecificationGap`，按借位实现；单测补 `0−1`、`5−7`、`rdha=rd0` 用例。
- 向量生成器 `generate_isa_vectors.py` 改为借位；`009t-audit.py` 原本已按无符号借位归一，无需改语义；`reg-arith.yaml` 新增两条借位向量。
- QEMU 不改（已按借位实现）；LLVM 不改（只用 `rd0` 高位，结果不受影响）；DDLN 不改（已描述借位）。
- `manifests/spec-readonly.lock.toml` 同笔重算 `SimRISC-00`、`SimRISC-04` 的 sha256。

## 状态说明

- **用户原话**（2026-10-26）：
  > 「选择B，并进行同步、ADR」
- 据此将 `D1` 置 `Accepted`；同步范围由同一原话授权（含 `spec/` 修改）。
- 授权原话同时落纸于 `GOLDEN-001t` 任务书与 `manifests/spec-readonly.lock.toml` 注释。
