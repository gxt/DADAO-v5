# ADR-0039: DADAO RTL 升级到 SimRISC 0.5.5

**状态**：Accepted
**日期**：2026-10-27
**关联**：DADAO-v5 `8f669181`、`contracts/opcodes.yaml`、`contracts/legality_rules.yaml`、`RTL-007k`、`RTL-008t`、`RTL-009t`、`RTL-010t`

## Context（背景）

DADAO-v5 上游已正式从 SimRISC 0.5.4 更新到 0.5.5。上游同期包含大量
M9、LLVM、QEMU 和测试目录重组变化。当前项目只维护单周期整数 Core，
浮点（floating point，FP）仍不在实现范围。

结构化比较结果：

```text
0.5.4 total = 264
0.5.5 total = 266

M1  = 156 -> 156
FP  =  64 ->  66
```

M1 的指令身份、mask/value、字段和合法性规则没有变化。新增两条编码是
`ftfma`/`fofma`，属于 `scope: fp`。

## Decision（决策）

- **D1 — 版本基线**：项目契约基线升级为 **SimRISC 0.5.5**，上游快照
  commit 为 `8f669181`。
- **D2 — 整数范围保持**：Core 继续实现 `scope: m1` 的 156 条指令。
- **D3 — 浮点保持范围外**：Core 不实现 `scope: fp` 的 66 条指令。
  Decoder 识别这些编码并按 FP scope fault 处理；不新增 RF 数据通路。
- **D4 — schema 适配**：0.5.5 将 opcode 字段名从 `op` 改为 `opc`。
  RTL 工具读取 `opc`，并兼容旧 `op`。
- **D5 — cmp 语义修正**：`cmp.ub`、`cmp.uw`、`cmp.ut` 的 `-1`
  结果为 64 位全 1，不再按窄位宽零扩展；源操作数仍先截断到对应宽度。
- **D6 — 派生表重生成**：decoder 从 264 条更新为 266 条；decoder
  oracle 和保留编码覆盖同步重生成。新增两条 FP 编码占用原保留格，
  reserved 总数由 370 变为 368。
- **D7 — 非目标上游变化**：M9 原子指令、LLVM/QEMU、测试目录重组和 FP
  FMA 执行语义不在本次 Core 更新中实现。

## Rationale（理由）

- M1 编码未变化，保持单周期整数 Core 的既有边界可以避免无必要的架构
  改动。
- `cmp.u*` 是本次唯一直接影响现有整数执行结果的语义变化，必须更新
  RTL、oracle 和测试期望。
- `opc` 是机器可读契约的字段重命名，工具必须跟随，否则保留格检查会
  把编码误判为缺失。
- FP 两条 FMA 编码仍应由 decoder 识别为范围外，而不是误报为完全未定义
  的 `UNDI`。

## Consequences（影响）

- `DADAOALU`、ALU 单元测试和 ALU oracle 需要同步。
- `DADAODecoderTable`、`DADAODecoderOracleTable` 和
  `DADAOReservedCoverageTable` 需要重生成。
- `check_dadao_cell_coverage.py`、decoder oracle 和 static legality
  检查器的版本计数需要更新。
- `manifests/rtl.lock.toml` 和 `tools/rtl/clab-env.sh` 声明
  SimRISC `0.5.5`。
