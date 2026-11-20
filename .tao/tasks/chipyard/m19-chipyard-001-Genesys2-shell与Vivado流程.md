# m19-chipyard-001: Genesys2 shell 与 Vivado 流程（wuming-Tiny 上板骨架）

**模块**：chipyard
**项目里程碑**：M19
**依赖**：`m16-chipyard-010`（I-Cache）；Vivado 环境就绪（用户 2026-11-20：装在部分节点，装完更新 `nodes.md`）
**可并行分片**：否（改 chipyard 生成器）
**预估**：3–5 天
**档位**：大改
**状态**：待开始

## 背景

用户 2026-11-20 定：**FPGA-Tiny 提前到 gem5 Minor + wuqing 之前**。已核 `chipyard` 的 `fpga/fpga-shells/xilinx/` 只有 `vc707`/`arty`/`arty_a7_100`/`nexys_video`/`vcu118`/`zcu102`/`alinx_axku040`——**没有 Genesys2（XC7K325T）**，须新写 shell，不是改参数就能烧。

板卡资源（`discussing.md`）：50,950 logic slices（≈203,800 LUT6 / 407,600 FF）、445 块 RAMB36（≈1.91 MiB）、840 DSP、1 GiB DDR3（本机型 Tiny **不接 DDR**）。

## 目标

1. 新增 Genesys2 shell（时钟/复位/UART/引脚约束），参考 `nexys_video`（7 系列）与 `vc707`；
2. Vivado 版本**锁进 `manifests/`**（组件锁纪律），构建脚本入仓且可重跑；
3. `WumingTinyConfig` 综合 + 实现 + 上板，跑 1 个最小镜像（`SYS_EXIT` 回显）；
4. 资源报告（LUT/FF/BRAM/DSP）与综合/实现耗时落盘。

## 验收（逐条贴真实 rc）

1. 比特流生成 + 板上 `SYS_EXIT(0)`，串口回传可见；
2. 资源数字从 Vivado 报告**现场解析**（不手抄），与报告逐项一致；
3. **可达 FAIL ≥2 路**：① 引脚约束错 ⇒ 上板无输出；② 时钟约束缺失 ⇒ 时序报告红；
4. `check-patch-tree` chipyard 段 0 问题；`check-component-changelog` rc=0。

## 约束

独立 `git worktree`；**不提交 git**；综合/实现是长任务（落 PID/日志/`*_EXIT`）；**硬件操作（下载/复位）前须用户确认**；改动只在 `dadao-wuming` 的 harness/FPGA 层，不动核内执行逻辑；完成区不写具体 `.work/**` 路径。
