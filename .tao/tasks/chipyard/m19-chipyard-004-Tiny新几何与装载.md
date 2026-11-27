# m19-chipyard-004: chipyard Tiny 新几何与装载（8K ROM / 8K hmon / 256K SRAM）

**模块**：chipyard
**项目里程碑**：M19
**依赖**：`m19-spec-002`
**可并行分片**：否
**预估**：4–8 h
**档位**：中改
**状态**：待开始

## 背景

`WumingTinyConfig` 当前是 BootROM 64 KiB / SRAM 8 MiB / hmon 64 KiB、entry `0xFFFF_FF01_0100`。按 `m19-spec-002` 改为：ROM 8 KiB、SRAM 256 KiB、hmon 8 KiB、entry `MAIN_SRAM_BASE+0x2000`、raw 基址 `0x2000`、header/mailbox/exit/DUMP/signature 地址按新布局。

## 目标

1. `DadaoConfigs.scala` / `WithDadaoTinyAddressMap`：BootROM 8 KiB、SRAM 256 KiB、hmon 8 KiB；`appEntry=0xFFFF_FF00_2000`。
2. `WumingParams` / `WumingTile`：`loadMemBase/Size`、`loadMemEntry`、`hmonBase/Size`、`bootromBase/Size` 按新值；`+loadmem` 窗口 256 KiB。
3. BootROM 资源：`bootrom.tiny.hex` 按 8 KiB 布局重生成（power@0、hmon@0x800、table@0x1F00）；classpath 镜像名不变。
4. 头区/DUMP/signature 仅作为地址常量与测试资产约定；本任务不实现 TSI。
5. 保持 `WumingVastConfig` 不变。

## 验收（逐条贴真实 rc）

1. `make verilog`（WumingTinyConfig）rc=0；Verilator `+loadmem` 装载新 entry 成功。
2. 生成的地址图/参数打印：BootROM 0x2000、RAM 0x40000、hmon 0x2000、entry 0x2000。
3. **可达 FAIL ≥2 路**：① 把 RAM 写回 8 MiB ⇒ 参数/窗口断言红；② 把 entry 写回 0x10100 ⇒ 装载/启动用例红。
4. `check-patch-tree` chipyard 段 0 problem；`check-component-changelog` rc=0。
5. 不改 QEMU/gem5；不接板。

## 约束

独立 `git worktree`；**不提交 git**；只动 `dadao-wuming`/`DadaoConfigs`/bootrom 资源与必要补丁；完成区不写具体 `.work/**` 路径。
