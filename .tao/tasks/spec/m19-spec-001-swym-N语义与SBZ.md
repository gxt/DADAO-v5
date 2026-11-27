# m19-spec-001: swym N 语义与 SBZ 合法性（12 位 N、1+N 拍、原子）

**模块**：spec
**项目里程碑**：M19
**依赖**：无
**可并行分片**：否
**预估**：2–4 h
**档位**：小改
**状态**：待开始

## 背景

用户 2026-11-27 裁定 `swym N` 的精确语义，用于 M19 及后续流水线/超标量的周期口径：

- `N = immu18[11:0]`，12 位有效；
- `immu18[17:12]` **SBZ**，非零 ⇒ `ILLI`；
- `swym 0` 为 1 拍 NOP；`swym N` 总时延 = **1 + N 拍**（N 是额外拍数，不是“执行 N 次 `swym 0`”）；
- **原子**：执行期间不取中断；完成后在下一个指令边界取中断；中断延迟上界 = 1 + N 拍；
- QEMU 不做时延建模（NOP）；gem5 / chipyard 实现时延与原子语义。

本任务只改语义与契约，不改实现。

## 目标

1. `spec/SimRISC-12 §2` 写死上述四条（N 位宽、SBZ/ILLI、1+N、原子中断语义）；同步 operation 注释。
2. `contracts/legality_rules.yaml` 增加 `swym` 高位 SBZ 规则（非零 ⇒ `ILLI`）。
3. `contracts/wuming-cycles.yaml` 的 `swym_oiii_imm` 从固定 `1` 改为 **动态 `1 + N`**（N 取 `immu18[11:0]`）。
4. 检查 `spec/SimRISC-00`/Toolchain 是否还有“约 N+1 倍”“实现可设上限”的旧表述，统一改为本口径。
5. 版本号是否升级、升到多少：**待用户确认**；未确认前只落内容，不擅自升号。

## 验收（逐条贴真实 rc）

1. `make check-legality-drift` / `check-legality-invariants` / `check-contract-relocs` 真实 rc=0（或给出基线红对照）。
2. `check-spec-refs`、`check-spec-numbering` 真实 rc=0；新条款在 `spec/SimRISC-12` 可 grep 到“12 位 / SBZ / 1 + N / 原子”。
3. **可达 FAIL ≥2 路**：① 注入“高位非零不报 ILLI”的规则，合法性门控转红；② 注入“cycles = 1”而非 `1+N`，对应契约检查/派生表转红（或给出可复现的静态断言）。
4. 不改 gem5 / chipyard / QEMU 源码；不升版本号（除非用户当轮确认）。

## 约束

独立 `git worktree`；**不提交 git**；只动 `spec/SimRISC-12`、`spec/SimRISC-00`（若需）、`contracts/legality_rules.yaml`、`contracts/wuming-cycles.yaml`；完成区不写具体 `.work/**` 路径。
