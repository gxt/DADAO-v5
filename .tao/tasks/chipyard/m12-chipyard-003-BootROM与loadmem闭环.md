# m12-chipyard-003: BootROM + `loadmem` 最小闭环

**模块**：chipyard
**项目里程碑**：M12
**状态**：待开始
**依赖**：`m12-chipyard-002`（Tiny 地址图已落地）

## 背景与事实

- Tiny 地址图（`002` 已落地）：BootROM `0xffff_ffff_0000` / 64 KiB（复位向量 = 起始）、SRAM `0xffff_ff00_0000` / 8 MiB。
- chipyard 侧 `+loadmem=<elf>` 由 `SimDRAM.cc` 的 `memory_init` 解析，`load_elf()` 直接把段写进 backing memory（`memif_t::write` = memcpy），**不经总线、不跑仿真**；`bss` 由 loader 零填。
- 现有 bootrom：`tests/shared/bootrom/step5/` 生成 Tiny bootrom（`002` 已以文本 hex 入库并构建期解码为 classpath 资源）。

## 目标

1. **BootROM 启动路径**：复位从 `0xffff_ffff_0000` 取指，bootrom stub 计算/跳转到 SRAM 内的应用入口（以 ELF `e_entry` 或约定固定入口为准，二者择一并写明理由）。
2. **`loadmem` 装载**：`+loadmem=<elf>` 把应用 ELF 的 `.text/.rodata/.data` 落到 `0xffff_ff00_0000` 起的 SRAM；`bss` 零填；**目标基址必须与 Tiny 地址图一致**（不得依赖 `SimDRAM` 的默认 `mem_base`）。
3. **最小闭环**：跑一个不含 syscall 的最小程序（如若干条整数指令 + 写 SRAM + 触发可见结果），用 chipyard TestHarness 的**现有可观测出口**（`+max-cycles` / TestDriver `$stop` / 预留 MMIO 之一）作为结果标记；**semihosting 属 `004`，本任务不做**。
4. 文档：`components/chipyard/README.md` 记录 `loadmem` 目标窗口与启动约定。

## 验收标准

1. `+loadmem=<elf>` 后 SRAM `0xffff_ff00_0000` 起的内容与 ELF 段逐字节一致（用 `SimDRAM` backing memory dump 或等价手段证明）
2. 复位后能到达应用入口（打印取指地址序列，证明从 bootrom → SRAM 的跳转）
3. 最小程序产生预期可观测结果（与 QEMU `dadao-tiny` 跑同一镜像的结果一致，或说明差异根因）
4. Verilator 构建 rc=0（`server207`）；有界运行不崩
5. `make apply-series` / `check-source-state` / `check-patch-tree` / L1 / L2 rc=0
6. 一键证据脚本（运行期证据目录下的 `run.sh`，含可达 FAIL 注入）
7. 完成区 ≤30 行、无运行期路径

## 非范围

- semihosting 应答者（`004`）
- 核内部指令实现（`005` 起）
- 改 `spec/Machine-v5` 地址图

## 说明

- **`loadmem` 的基址风险**：`SimDRAM.cc` 的 `loadmem_memif_t` 以 `mem_base` 为起点做 `taddr - start`；若 `mem_base` 与 SRAM 基址不一致，镜像会落到错误位置。必须先读码确认 `mem_base` 的来源并显式对齐。
- 构建/运行在 `server207`；仓库修改在主控机。
