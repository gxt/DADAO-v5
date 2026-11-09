# m12-chipyard-005: 解码器 + 整数 ALU + 寄存器堆

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m12-chipyard-004`（semihosting 已通，可观测输出）
**可并行分片**：否（单核实现，单写者）
**状态**：待开始

## 背景

- `m12-chipyard-001`~`004` 已完成：骨架、Tiny 地址图、bootrom+loadmem、harness semihosting。
- 当前 `WumingCoreStub` 只覆盖 **5 类指令**（`set.zw`/`or.w`/`jump` 等），是为跑通闭环的最小执行器；真核从本任务开始。
- 本任务只做**整数执行的最小可用集**：解码、整数 ALU、寄存器堆；访存/控制流在 `006`，位操作/原子/杂项在 `007`。

## 目标

1. **寄存器堆**：`rd`（64 位）、`ra`/`rb` 双 bank。**`rd0` 恒读 0**（作为目的：`rrrr` 双目的允许其一为 `rd0` 并丢弃该半结果，但不能同时为 `rd0`；其余格式目的为 `rd0` ⇒ ILLI）。**`rb0` = 当前正在执行的指令地址（`IP`，非下一条）**，只读；**作为显式目的 ⇒ ILLI**（`spec/SimRISC-00 §2.2`）。
2. **解码器**：至少覆盖 `orrr`/`orri`/`rrrr` 三种格式与 `SimRISC-04`（64 位数据运算）、`SimRISC-08`（32 位）、`SimRISC-05`（地址运算）中的**算术/逻辑/移位**指令。
   - **合法性**：**保留编码 ⇒ UNDI**、**非法组合 ⇒ ILLI**（按 `contracts/legality_rules.yaml` 的 `excp_undi` / ILLI 规则，不得静默当 NOP）。
3. **整数 ALU**：加/减/与/或/异或/移位/比较；**溢出与进位语义按 `spec/SimRISC-04`**（不套用 RISC-V）。
4. **接入**：替换 `WumingCoreStub` 中对应的 5 类指令桩，保持 bootrom→应用→semihosting 闭环不回归。

## 验收标准

1. `tests/inst` 中**本任务覆盖的指令族**在 chipyard 上逐例与 QEMU `dadao-tiny` 一致（状态/退出码；不比时序）
2. 覆盖的用例数按 `--list` 现场统计并与报告一致（不写死）
3. `rd0`/`rb0` 的读 0 / 写丢弃有专门断言（含「写 rd0 后再读」）
4. **保留编码 ⇒ UNDI**（`legality_rules.yaml` 的 `excp_undi`）；**非法组合 ⇒ ILLI**（`dst_rd0`/`dst_rb0`/`dst_dual_same`/`encode_sbz`/未实现）；两类各有至少 3 例注入式验证
5. Verilator 构建 rc=0（`server207`）；有界运行不崩；bootrom→loadmem→semihosting 闭环不回归
6. `make apply-series` / `check-source-state` / `check-patch-tree` / L1 / L2 rc=0
7. 一键证据脚本（运行期证据目录下的 `run.sh`，含可达 FAIL 注入）
8. 完成区 ≤30 行、无运行期路径

## 非范围

- 访存（`006`）、控制流/RAS（`007`）、位操作/原子/杂项（`007`）
- FP（`008`–`012`）
- T0/T1 冒烟（`013`/`014`）
- 不实现 cfx（Tiny 无 cfx；`trap` 仅 semihosting）

## 说明

- 参考实现 `.cache/refs/DADAO/SOC-chipyard/` 的 `wuming_1stage/{dpath,cpath,regfile,consts}.scala` 可作结构参考（**只读溯源，非执行依赖**）。
- 构建/运行在 `server207`；仓库修改在主控机；节点操作后 `make sync-node-repo`。
