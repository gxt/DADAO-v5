# chipyard 组件（chipyard）

Chipyard 是 DADAO 的 **RTL SoC 仿真平台 + 核迁入目标**（`ADR-0024 D1`，2026-11-08 就地修订：不再 `patchless`）。上游基线与补丁序列由 `manifests/components.lock.toml` 锁定（主仓 commit + `manifests/chipyard-submodules.lock.toml` 子模块快照，`ADR-0024 D2`）；工作树由 `make fetch` + `make apply-series` 在运行期组件源目录建立。

## 补丁集

- 形态：**树形补丁集**（`patches/<上游相对路径>.patch`，一文件一补丁），清单见 `series`；规范见 `docs/Process-01-组件补丁组织与构建编排.md`。
- 内容（M12 起）：`generators/dadao-wuming/**` 新增文件（DADAO「wuming」Tile 外壳 + 桩核 + 参数/配置片段 + Tiny bootrom 的 hex 资源与解码）、两处上游文件修改（根 `build.sbt` 的 `wuming` 项目接线、`generators/chipyard/.../config/fragments/PeripheralFragments.scala` 的 BootROM 资源名参数）。
- 构建全部在构建节点执行（`.tao/knowledge/nodes.md §10.1`）：主控机只维护补丁集与台账。

## 地址图（`Machine-v5-Tiny`，`spec/Machine-v5 §1.1`）

- **BootROM** `0xffff_ffff_0000` / 64 KiB / 复位向量 = 起始；**SRAM** `0xffff_ff00_0000` / 8 MiB / 唯一可写主存。两者都是 **48 位核内地址**；核 `useVM=false`（无 MMU/TLB），无 cfx / PTW。
- **实现方式 = 改 fragment 的既有字段，不新增 `AddressMap`**：chipyard 的地址图由 `BootROMLocated` + `BankedScratchpadKey` + 后备内存端口 `ExtMem`/`ExtTLMem` 三个来源拼出，`generators/chipyard/src/main/scala/config/DadaoConfigs.scala` 里的 `WithDadaoTinyAddressMap` 正好重定向这三处：
  - BootROM 几何/复位向量/镜像名经 `chipyard.config.WithBootROM`（`address`/`hang`/`contentFileName`）；该 fragment 另把 `appendDTB` 关掉（Tiny 的 BootROM 只有复位/启动 stub，无 DTB、无 image index table）。
  - SRAM 用 testchipip 的 **banked scratchpad**（`BankedScratchpadParams`，`busWhere = MBUS`、`dtsEnabled = true`）替换 chipyard 默认的 64 KiB scratchpad（`0x0800_0000`）；它就是 TileLink 从端口，不再另设内存模型。
  - `ExtMem` / `ExtTLMem` 都置 `None`：不开 AXI/TL 后备内存端口（Tiny 无 DRAM），harness 里的 `SimDRAM` 也随之消失。
- **BootROM 镜像**：补丁集不能携带二进制，故 Tiny bootrom 以 `generators/dadao-wuming/src/main/resources/dadao/bootrom/bootrom.tiny.hex`（文本 hex）入库，`wuming` 项目的 `resourceGenerators`（根 `build.sbt`）在构建时解码成 classpath 资源 `/dadao/bootrom/bootrom.tiny.img`；镜像内容与 `loadmem` 闭环由 `m12-chipyard-003` 负责。
- **实测**：`WumingTile` 的 elaboration 行打印协商值，`Generated Address Map` 打印全图；`WumingCoreStub` 复位后先从复位向量取一拍、再对 SRAM 写读回，作为「能取指 + 可写主存」的可观测证据。

## 边界

- **保留** rocket-chip 库（Diplomacy / TileLink / `BaseTile`）与 chipyard 仿真设施（Verilator harness / BootROM / 内存模型 / `loadmem`）。
- **抛开** Rocket 核与 RISC-V 语义（CSR / misa / PMP / MMU / TLB / 异常码）；`WumingCoreParams` 不继承 `CoreParams`。

## 校验

```
make apply-series
make check-source-state
make check-patch-tree
```
