# chipyard 组件变更记录

> 粒度：**按任务一条**，追加式。**体例 = 列表式（不用表格）+ 按里程碑分节**：每条 = `- **<日期> <任务号或 —>**`，**摘要另起缩进行** `  - 摘要：<摘要正文>`；节 = `## M<k>`（节序 M1→M2→…）。补丁集的生成/应用/校验规范见 `docs/Process-01-组件补丁组织与构建编排.md §10`。

## M12

- **2026-11-08 `m12-chipyard-001`**
  - 摘要：**chipyard 首次进入 v5 补丁集**（`ADR-0024 D1` 就地修订，用户裁定 B）：新增 `generators/dadao-wuming/**`（`WumingTile extends BaseTile`、自声明 `TLClientNode`/`TLIdentityNode`、`WumingCoreParams` 不继承 `CoreParams`、桩核）、`generators/chipyard/src/main/scala/config/DadaoConfigs.scala`（`WumingTinyConfig`）、根 `build.sbt` 的 `wuming` 项目与 chipyard 依赖、`PeripheralFragments.WithBootROM` 的 BootROM 资源名参数。
  - 执行者：engineer

- **2026-11-09 `m12-chipyard-002`**
  - 摘要：**落地 `Machine-v5-Tiny` 48 位核内地址图**（`spec/Machine-v5 §1.1`）：新增 `WithDadaoTinyAddressMap` fragment（BootROM `0xffff_ffff_0000`/64 KiB/复位向量=起始、SRAM `0xffff_ff00_0000`/8 MiB 经 `BankedScratchpadKey` 落到 MBUS、`ExtMem`/`ExtTLMem` 关掉、BootROM 不附 DTB），`WumingTinyConfig` 改用该 fragment 并把 BootROM 镜像名指向 `/dadao/bootrom/bootrom.tiny.img`；Tiny bootrom 以文本 hex（`bootrom.tiny.hex`）+ `build.sbt` 的 `resourceGenerators` 解码入库（补丁集不能带二进制）；桩核改为「复位向量取指 + SRAM 写读回」三拍探针，`testAddress` 由 `0x8000_0000` 改为 SRAM 基址。
  - 执行者：engineer

- **2026-11-09 `m12-chipyard-003`**
  - 摘要：**BootROM → SRAM `+loadmem` 最小闭环**：`WumingCoreStub` 由三拍探针改为最小启动执行器（`set.zw`/`or.w`/`jump`/`ld.o`/`st.o` 子集，IP=当前指令地址、rb0/rd0 约定按 `spec/SimRISC-00`），到达子集外编码即 halt → `reportCease`；新增 `WumingLoadMem`（tile 内 TileLink 主端口加载器，自带大端 ELF64 `PT_LOAD` 解析、`p_memsz` 零填、SRAM 窗口校验、逐字回读比对，回读通过才释放核；不用 stock `SimDRAM`——Tiny 无 SimDRAM 实例、其 `+loadmem` 只写 host backing，且 fesvr 大端受限）；`WumingCoreParams` 新增 `loadMemBase/loadMemSize`（无默认，`WumingTinyConfig` 从地址图传入）；新增最小程序 `tests/shared/bootrom/tiny_smoke.{S,lds}`（`make build-bootrom` 产出 ELF）；新增 `iobinders/WumingSuccess.scala`（把 tile cease 接到 TestDriver `$stop`——chipyard 默认不连）。
  - 执行者：engineer

- **2026-11-09 `m12-chipyard-004`**
  - 摘要：**harness 侧 semihosting 应答者（最小 5 服务）**：核内 `WumingCoreStub` 识别 `trap` 的 semihosting tag（`immu18[17:8]==0x3FF`）并把 `(op, rb16, rd8, IP)` 经 **DPI 导出端口**抬到 tile 边界（核内无宿主调用）；新增 `WumingSemi`（LazyModule + TileLink 读引擎）、`wuming/vsrc/WumingSemi.v`（DPI 桥）、`wuming/csrc/WumingSemi.cc`（table-driven 宿主模型：WRITEC/WRITE0/WRITE/CLOCK/EXIT，未实现服务号显式报错，`SYS_EXIT` 以进程退出码实现有界停机）。另新增 `tests/shared/bootrom/semihost_smoke.{S,lds}` + 消息 include 与四个 `--defsym` 变体（三平台 smoke、guest FAIL、未实现服务、`SYS_WRITE`）。
  - 执行者：engineer
