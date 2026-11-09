# m12-chipyard-007: Tiny 的 `cfx_power` + `cfx3 hmon`（异常进向量）

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m12-chipyard-006`（状态机设计，含 hmon）
**可并行分片**：否（单核实现，单写者）
**状态**：待开始

## 用户裁定（2026-11-09）

- **Tiny 实现 `cfx_power`（cfx63）+ `cfx3 hmon`**（决策 1 = B）
- hmon SRAM **复用 `0x0fff_0000_0000`**（64 KiB，同 Vast，决策 2 = A）
- **无 PTW/页表**（决策 3 = A）
- **同步异常不经 `trap` 指令**，直接进 hmon 向量；与 semihosting 的 `trap` 无冲突
- **三平台 Tiny 的 semihosting `trap` 统一写 `trap cfx_hmon`**（实现上仍只看 `immu18`，不判断 cfxha）
- `trap` 判定：`immu18 ∈ 0x3FF00–0x3FFFF` ⇒ semihosting；`cfxha=3` + 其它 `immu18` ⇒ 进 hmon

## 目标

1. **`cfx_power`（cfx63）**：Tiny 的启动移交路径 `power → hmon`（与 Vast 同构），按 `DADAO-12 §5.2` 的 trap 移交语义。
2. **`cfx3 hmon`**：
   - hmon 寄存器组（`excp_cause`/`excp_vector`/四类同步 mask/`cfx_intr_mask`/`switch_run_mode`）
   - 同步异常（ILLI/UNDI/`CFXMEM`/`MALIGN`/`IALIGN`）进 hmon 向量：**IP 停留语义按 `DADAO-12 §5`**（IALIGN 时 IP 停在非法地址，不写回 `nextIp`）
   - hmon 可 `escape` 回测试本体（用户态/hypv 测试体）
3. **`trap` 区分**：`immu18` 区间判定 semihosting vs hmon；semihosting 统一用 `trap cfx_hmon`。
4. **地址图**：Tiny 增加 hmon SRAM `0x0fff_0000_0000`（64 KiB），与 BootROM/SRAM 并存。
5. **回归**：bootrom 启动、loadmem、semihosting 闭环、005 的 273 例整数测试**全部不回归**。

## 验收标准

1. `cfx_power → hmon` 移交可观测（打印/断言移交前后的运行模式与 PC）
2. 五类同步异常各至少 3 例进 hmon 向量，`excp_cause` 正确
3. **IALIGN 时 IP 停在非法地址**（专门断言）
4. semihosting 的 `trap cfx_hmon` 与 `trap cfx63` 都能工作（`immu18` 判定不依赖 cfxha）
5. 005 的 273 例整数测试**零回归**（逐字节一致）
6. Verilator 构建 rc=0（**主控机**）；`apply-series`/`check-source-state`/`check-patch-tree`/L1/L2 rc=0
7. 一键证据脚本（运行期证据目录下的 `run.sh`，含可达 FAIL 注入）
8. 完成区 ≤30 行、无运行期路径

## 非范围

- QEMU/gem5 的 Tiny hmon（按用户决策，**排在 M13 前置**）
- 访存/控制流/FP（`008` 起）
- smon（Tiny 不实现）

## 说明

- 与 `006` 的设计定稿保持一致；若实现中发现设计需调整，**停下报告**（不要自行改设计）。
- **构建与调试在主控机**（用户 2026-11-10：chipyard 后续构建/调试一律主控机）；小规模仿真也在主控机。**长仿真才上节点**（且节点须自行构建，Verilator 产物机器相关，不跨机复制）。仓库修改在主控机；节点操作后 `make sync-node-repo`。
