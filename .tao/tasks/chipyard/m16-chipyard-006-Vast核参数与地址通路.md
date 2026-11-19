# m16-chipyard-006: Kaiwu-Vast 核参数与地址通路（地基）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：无（本任务先做地基）；后续 `m17-chipyard-002`（PTW）、`003`（TLB）依赖本任务
**可并行分片**：否（改 `dadao-wuming` generator + `DadaoConfigs.scala`）
**预估**：2–3 天
**档位**：大改
**状态**：待开始

## 背景

`WumingTinyConfig` 是唯一能 elaborate 的 DADAO 配置：`useVM = false`、`WumingCompatCoreParams` 里 `useVM=false`/`pgLevels=3`（RISC-V 残留）/`nL2TLBEntries=0`，核内**没有 PTBR/ASID/`ptw_enable`**，也不访问 `cfx_ptw`；取指/访存直连 `imem`/`dmem`。Vast 要在此基础上换掉整条地址通路。

**用户已定口径（2026-11-19）**：只设一级 TLB、分 I/D；普通页 16 条 = 2 组 × 8 路、不设 sectored；超页 4 条全相联 + LRU；无特殊条目；I-TLB 无 dirty 位；gem5 与 chipyard 在这些方面保持统一。

## 目标

1. **新增 `WumingVastConfig`（及 `WumingVastParams`）**：不破坏 `WumingTinyConfig`（Tiny 的全部既有向量与 md5 判据必须不变）；
2. **`useVM = true` 的核参数**：`WumingCompatCoreParams.useVM`、`pgLevels` 按 DADAO（2 级）语义处理（若上游字段不可改，则显式注释「字段保留、语义不用」）；
3. **核内三个新状态**：`PTBR`、`ASID`、`ptw_enable`，来源 = `cfx_ptw`（cg12 rc0–rc3）；
4. **地址路由**：`addr[47:42] ≠ 0` ⇒ 核内空间（不走 PTW/TLB）；`= 0` 且 `ptw_enable=0` ⇒ `CFXMEM`（子原因 `[57] NONPTW`）；`= 1` ⇒ 进 TLB/PTW（本任务先直连「步查器占位」= 未映射 ⇒ `CFXMEM`）；
5. **`cfx_ptw` 寄存器面**：`cg12 rc0 = tlb_control`（WO、写即执行）、`rc1 = tlb_asid`（`[15:0]`，`[63:16]` 读 0）、`rc2 = tlb_addr_start`（`VA[41:0]`）、`rc3 = tlb_addr_size`；本任务只做**寄存器与读回**，执行语义归 `003`；
6. **行为等价兜底**：`ptw_enable = 0` 时 `WumingVastConfig` 的行为应与 Tiny **逐条一致**（可用 Tiny 的既有向量回归）。

## 验收（逐条贴真实 rc，每条须能 FAIL）

1. `make verilog CONFIG=WumingTinyConfig` + `make CONFIG=WumingTinyConfig` ⇒ **Tiny 的 sim md5 与行为不变**（跑既有 `tests/inst` 首册冒烟）；
2. `make verilog CONFIG=WumingVastConfig` + `make CONFIG=WumingVastConfig` ⇒ 能 elaborate、能跑一个最小镜像（`ptw_enable=0` 路径）；
3. **寄存器面构造用例**：读 `cg12 rc1` 的高位为 0、`rc0` 写不报错；`rc2/rc3` 可读回；
4. **路由用例**：`addr[47:42]≠0` 的访存不走 PTW；`ptw_enable=0` 的用户地址 ⇒ `CFXMEM + NONPTW`（子原因位号现场取自 `ADR-0056`/`contract-see`）；
5. ≥2 路注入（① `ptw_enable` 恒 1 ⇒ 路由用例红；② `CFXMEM` 子原因位号写错 ⇒ 用例红），`cp`+md5 还原 + 重建回绿；
6. 术语「寄存器组」；任务书自包含。

## 待裁定

（无。TLB/PTW 结构已由用户裁定；`pgLevels` 的上游字段若与 DADAO 两级冲突，按「字段保留 + 注释」处置，不擅自改上游参数语义。）

## 完成区

（待填）
