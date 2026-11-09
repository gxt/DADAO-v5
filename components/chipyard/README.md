# chipyard 组件（chipyard）

Chipyard 是 DADAO 的 **RTL SoC 仿真平台 + 核迁入目标**（`ADR-0024 D1`，2026-11-08 就地修订：不再 `patchless`）。上游基线与补丁序列由 `manifests/components.lock.toml` 锁定（主仓 commit + `manifests/chipyard-submodules.lock.toml` 子模块快照，`ADR-0024 D2`）；工作树由 `make fetch` + `make apply-series` 在运行期组件源目录建立。

## 补丁集

- 形态：**树形补丁集**（`patches/<上游相对路径>.patch`，一文件一补丁），清单见 `series`；规范见 `docs/Process-01-组件补丁组织与构建编排.md`。
- 内容（M12 起）：`generators/dadao-wuming/**` 新增文件（DADAO「wuming」Tile 外壳 + 最小启动执行器 + 参数/配置片段 + Tiny bootrom 的 hex 资源与解码 + `+loadmem=` 加载器）、两处上游文件修改（根 `build.sbt` 的 `wuming` 项目接线、`generators/chipyard/.../config/fragments/PeripheralFragments.scala` 的 BootROM 资源名参数）。
- 构建全部在构建节点执行（`.tao/knowledge/nodes.md §10.1`）：主控机只维护补丁集与台账。

## 地址图（`Machine-v5-Tiny`，`spec/Machine-v5 §1.1`）

- **BootROM** `0xffff_ffff_0000` / 64 KiB / 复位向量 = 起始；**SRAM** `0xffff_ff00_0000` / 8 MiB / 唯一可写主存。两者都是 **48 位核内地址**；核 `useVM=false`（无 MMU/TLB），无 cfx / PTW。
- **实现方式 = 改 fragment 的既有字段，不新增 `AddressMap`**：chipyard 的地址图由 `BootROMLocated` + `BankedScratchpadKey` + 后备内存端口 `ExtMem`/`ExtTLMem` 三个来源拼出，`generators/chipyard/src/main/scala/config/DadaoConfigs.scala` 里的 `WithDadaoTinyAddressMap` 正好重定向这三处：
  - BootROM 几何/复位向量/镜像名经 `chipyard.config.WithBootROM`（`address`/`hang`/`contentFileName`）；该 fragment 另把 `appendDTB` 关掉（Tiny 的 BootROM 只有复位/启动 stub，无 DTB、无 image index table）。
  - SRAM 用 testchipip 的 **banked scratchpad**（`BankedScratchpadParams`，`busWhere = MBUS`、`dtsEnabled = true`）替换 chipyard 默认的 64 KiB scratchpad（`0x0800_0000`）；它就是 TileLink 从端口，不再另设内存模型。
  - `ExtMem` / `ExtTLMem` 都置 `None`：不开 AXI/TL 后备内存端口（Tiny 无 DRAM），harness 里的 `SimDRAM` 也随之消失。
- **BootROM 镜像**：补丁集不能携带二进制，故 Tiny bootrom 以 `generators/dadao-wuming/src/main/resources/dadao/bootrom/bootrom.tiny.hex`（文本 hex）入库，`wuming` 项目的 `resourceGenerators`（根 `build.sbt`）在构建时解码成 classpath 资源 `/dadao/bootrom/bootrom.tiny.img`；镜像内容与 `loadmem` 闭环由 `m12-chipyard-003` 负责。
- **实测**：`WumingTile` 的 elaboration 行打印协商值，`Generated Address Map` 打印全图。

## 启动与 `+loadmem`（`m12-chipyard-003`）

- **启动约定 = 固定入口**：Tiny BootROM 是静态平铺 trampoline（`tests/shared/bootrom/bootrom.S`：装 SP、装应用入口、`jump`），入口取 `machine-tiny.inc` 的 `ENTRY = 0xffff_ff01_0100`。**不用 ELF `e_entry`**：ROM 里没有 ELF 解析器/image index table/DTB，无法在运行时得知 `e_entry`；固定入口与 `QEMU dadao-tiny` 的 raw-kernel 约定（`kernel_base + kernel_reserved`）同源，应用链接脚本（`tests/shared/bootrom/tiny_smoke.lds`）用同一常量。
- **`+loadmem=<elf>` 窗口**：ELF 的 `PT_LOAD` 必须落在 SRAM 窗口 `0xffff_ff00_0000` + 8 MiB（`WumingTinyAddressMap.sramBase/sramSize`，**无默认值**，未配置即 elaboration 报错）；`p_memsz - p_filesz` 尾部零填（`contract-elf §5/§6`）。
- **实现方式 = tile 内 TL 主端口上的加载器**（`WumingLoadMem`）：解析 ELF64 大端 `PT_LOAD`，把每个 8 字节字作为 TileLink 请求写到与核相同的端口（不足 8 字节的字用 `PutPartial` 掩码），随后**逐字回读比对**；只有回读全等才拉高 `initDone` 释放核（`WumingCoreStub.bootEnable`）。装载/回读失败打印 `[WumingLoadMem] ERROR:` 并以非零退出（load-stage error 语义）。
- **为什么不用 stock `SimDRAM`**：① 当前 Tiny 设计**没有 `SimDRAM` 实例**——主存是 `BankedScratchpadKey → ScratchpadBank → TLRAM`（on-chip TL slave，不经 AXI），`ExtMem`/`ExtTLMem = None` 时 `WithBlackBoxSimMem` 无 AXI4 端口可绑；`+loadmem` 的写入目标是 SimDRAM 的 **host mmap backing**（`SimDRAM.cc` 的 `loadmem_memif`），写不到 SRAM。② fesvr 的 `load_elf` 在未开 `RISCV_ENABLE_DUAL_ENDIAN` 的构建里直接拒绝大端 ELF（本工具链 `config.h` 为 `#undef`，DADAO ELF 是 `ELFDATA2MSB`）；即便开启，`SimDRAM.cc` 的 `loadmem_memif_t::get_target_endianness()` 仍返回 little、dual-endian 分支仍 throw。改 testchipip 需**子模块补丁能力**（`m12-infra-003`）。故加载器自带 ELF 解析并用**绝对** `p_paddr`（无 `mem_base` 减法）。
- **可观测出口**：Tiny 无 cfx/semihosting（属 `m12-chipyard-004`），最小程序 `tests/shared/bootrom/tiny_smoke.S` 以**未定义指令**收尾 ⇒ `WumingCoreStub` halt → `reportCease`。chipyard 默认不把 tile cease 接到 TestDriver，故 `WithWumingCeaseSuccess` 把 `HasTileNotificationSinks.tileCeaseSinkNode` 暴露成 `SuccessPort`，由 `WithTraceGenSuccess` 驱动 `chiptopSuccess` ⇒ TestDriver `$stop`（`$finish`，rc=0）；`+max-cycles` 仅作有界兜底。程序内的 SRAM 写/读回与每条取指/执行都经 `printf` 打印（需 `+verbose`）。

## 边界

- **保留** rocket-chip 库（Diplomacy / TileLink / `BaseTile`）与 chipyard 仿真设施（Verilator harness / BootROM / 内存模型 / `loadmem`）。
- **抛开** Rocket 核与 RISC-V 语义（CSR / misa / PMP / MMU / TLB / 异常码）；`WumingCoreParams` 不继承 `CoreParams`。

## 校验

```
make apply-series
make check-source-state
make check-patch-tree
```
