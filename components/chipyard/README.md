# chipyard 组件（chipyard）

Chipyard 是 DADAO 的 **RTL SoC 仿真平台 + 核迁入目标**（`ADR-0024 D1`，2026-11-08 就地修订：不再 `patchless`）。上游基线与补丁序列由 `manifests/components.lock.toml` 锁定（主仓 commit + `manifests/chipyard-submodules.lock.toml` 子模块快照，`ADR-0024 D2`）；工作树由 `make fetch` + `make apply-series` 在运行期组件源目录建立。

## 补丁集

- 形态：**树形补丁集**（`patches/<上游相对路径>.patch`，一文件一补丁），清单见 `series`；规范见 `docs/Process-01-组件补丁组织与构建编排.md`。
- 内容（M12 起）：`generators/dadao-wuming/**` 新增文件（DADAO「wuming」Tile 外壳 + 最小启动执行器 + 参数/配置片段 + Tiny bootrom 的 hex 资源与解码 + `+loadmem=` 加载器）、两处上游文件修改（根 `build.sbt` 的 `wuming` 项目接线、`generators/chipyard/.../config/fragments/PeripheralFragments.scala` 的 BootROM 资源名参数）。
- **子模块补丁集**（`m12-infra-003` 起）：子模块自身的源码改动不在本目录，而在 `submodules/<子模块 path>/{series,patches/}`，由 `manifests/components.lock.toml` 的 `[[component.submodule_patch]]` 声明（base = 子模块 lock 的 pin）；`make apply-series` 在子模块内生成自己的 `base+1` commit，本组件 commit 记录该 gitlink。规范见 `docs/Process-01 §14`。当前只有一条：`generators/testchipip`（`SimDRAM.cc` / `SimDRAM.v`，见下）。
- 构建与调试在主控机执行（用户 2026-11-10 裁定；`.tao/knowledge/nodes.md §10.1`）；长仿真仍归节点。

## testchipip 子模块补丁（`m12-infra-003`）

- `src/main/resources/testchipip/csrc/SimDRAM.cc`：`loadmem_memif_t::get_target_endianness()` 原固定返回 `endianness_little`，fesvr 开 `--enable-dual-endian` 后大端 ELF 仍会命中「system uses a little-endian memory system」并 throw。改为 **`+loadmem_be` plusarg 显式打开**才返回 `endianness_big`；**默认保持 little**，stock RISC-V 配置（小端）行为不变。
- `src/main/resources/testchipip/vsrc/SimDRAM.v`：`MEM_BASE` 参数原为无位宽默认值 `0`（按 32 位有符号推断），48 位基址经 DPI 传 `longint mem_base` 会被截断；改为 `64'h0` 使其为 64 位。
- 用途：把 `+loadmem=<elf>` 的预装通路接到 DADAO 的大端 ELF；本阶段 Tiny 配置不用 stock `SimDRAM`（主存是 banked scratchpad，见下节），补丁是为后续带 AXI 后备内存的配置准备。

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
- **为什么不用 stock `SimDRAM`**：① 当前 Tiny 设计**没有 `SimDRAM` 实例**——主存是 `BankedScratchpadKey → ScratchpadBank → TLRAM`（on-chip TL slave，不经 AXI），`ExtMem`/`ExtTLMem = None` 时 `WithBlackBoxSimMem` 无 AXI4 端口可绑；`+loadmem` 的写入目标是 SimDRAM 的 **host mmap backing**（`SimDRAM.cc` 的 `loadmem_memif`），写不到 SRAM。② fesvr 的 `load_elf` 在未开 `RISCV_ENABLE_DUAL_ENDIAN` 的构建里直接拒绝大端 ELF（本工具链 `config.h` 为 `#undef`，DADAO ELF 是 `ELFDATA2MSB`）；即便开启，`SimDRAM.cc` 的 `loadmem_memif_t::get_target_endianness()` 仍返回 little、dual-endian 分支仍 throw。故加载器自带 ELF 解析并用**绝对** `p_paddr`（无 `mem_base` 减法）。子模块补丁能力已由 `m12-infra-003` 补齐（见上「testchipip 子模块补丁」），该缺口不再挡路——Tiny 不用 stock `SimDRAM` 的**结构性理由仍是①**（无 `SimDRAM` 实例、`+loadmem` 只写 host backing）。
- **可观测出口**：Tiny 无 cfx/semihosting（属 `m12-chipyard-004`），最小程序 `tests/shared/bootrom/tiny_smoke.S` 以**未定义指令**收尾 ⇒ `WumingCoreStub` halt → `reportCease`。chipyard 默认不把 tile cease 接到 TestDriver，故 `WithWumingCeaseSuccess` 把 `HasTileNotificationSinks.tileCeaseSinkNode` 暴露成 `SuccessPort`，由 `WithTraceGenSuccess` 驱动 `chiptopSuccess` ⇒ TestDriver `$stop`（`$finish`，rc=0）；`+max-cycles` 仅作有界兜底。程序内的 SRAM 写/读回与每条取指/执行都经 `printf` 打印（需 `+verbose`）。

## semihosting 应答者（`m12-chipyard-004`）

- **通道 = DPI 导出端口**（不是预留 MMIO）。核内 `WumingCoreStub` 命中 `trap <any cfxha>, 0x3FF00+op`（判定只看 `immu18[17:8] == 0x3FF`，与 `cfxha` 无关）时，只把 `(op=immu18[7:0], arg=rb16, ret=rd8, pc=IP)` 抬到 tile 边界并等待一个 64 位标量；**核内没有任何宿主调用**。理由：请求/应答天然同步，无需地址图新增 MMIO 区间与轮询；应答者还要读 guest 内存（字符串/参数块），DPI 桥可像 `+loadmem` 加载器一样自带 TileLink 主端口，MMIO 方案仍需要这条总线且多一层协议。
- **实现**：`WumingSemi.scala`（LazyModule + TL 读引擎）+ `wuming/vsrc/WumingSemi.v`（DPI 桥）+ `wuming/csrc/WumingSemi.cc`（宿主模型）。应答者与核、加载器共用 tile 的 TL 端口 xbar；返回写 `rd8` 后核自行 `IP += 4`（`spec/Machine-v5 §5.4`，无 `escape`）。
- **服务集（最小 5 个，table-driven）**：`SYS_WRITEC(0x03)` / `SYS_WRITE0(0x04)` / `SYS_WRITE(0x05)` / `SYS_CLOCK(0x10)` / `SYS_EXIT(0x18)`。
  - `SYS_WRITEC`/`SYS_WRITE0` 逐字节写 stdout（不截断、不重编码）；无定义返回值按 gem5/QEMU 约定写 `0xdeadbeef`。
  - `SYS_WRITE` 读参数块〔句柄, 缓冲区指针, 字节数〕；**本阶段未实现 `SYS_OPEN`**，故句柄 `1`=stdout、`2`=stderr 是本 harness 的约定（非 spec 断言），其它句柄返回 `-1` 并告警。
  - `SYS_CLOCK` = 自进程启动的宿主 CPU 百分秒（与 QEMU `clock()/(CLOCKS_PER_SEC/100)` 同式），返回值单调不减（实现内做下界钳制）。
  - `SYS_EXIT` 读参数块〔原因码, 子码〕：原因码 `0x20026` 时宿主退出码 = 子码（`spec §7.1` guest `0x00–0x3F`=PASS、`0x40–0x7F`=FAIL），否则为 1；以进程退出实现**有界停机**，不依赖 TestDriver 超时。
  - **未实现服务号 ⇒ 明确报错并给出服务号（十六进制）后以非零退出**，不静默返回 0。
- **三平台**：`tests/shared/bootrom/semihost_smoke.S` 的同一 ELF 在 QEMU `dadao-tiny`、gem5 FS `tiny` 与本 harness 上 stdout 逐字节一致、退出码一致；`semihost_fail.elf` 验证 guest FAIL 段映射，`semihost_unimpl.elf` 验证未实现服务号报错，`semihost_write.elf` 覆盖 `SYS_WRITE`（QEMU/gem5 的 raw stdout 句柄语义不同——gem5 未 `SYS_OPEN` 时 `files[1]` 越界崩溃、QEMU 需先开 `:tt`——故 `SYS_WRITE` 单独成像，不进入三平台比对集）。

## 整数执行（`m12-chipyard-005`）

- **结构**：`WumingCoreStub` 退役，改为 `WumingCore`（取指/执行状态机）+ `WumingRegFile`（`rd`/`rb` 双 bank，各 64×64；`rd0` 读 0、写丢弃，`rb0` 读**当前指令地址**且只读）+ `WumingDecoder`（格式/合法性/操作数选择）+ `WumingALU`（组合逻辑整数运算）。
- **覆盖**：`orrr`/`orri`/`rrrr`/`riii`/`rrii`/`rwii`；SimRISC-04 的 `and/or/xor/xnor`、`shl/rol/shr.{uo,so}`、`ext.{uo,so}`、`cmp.{uo,so}`、`add.o/sub.o`（bbd/dbb）、`div/rem.{uo,so}`、`rrrr` 的 `add/sub/mul.{uo,so}`（128 位 `{hi,lo}`）；SimRISC-05 的 `add.si`（rd/rb）、`aip.si`、`cmp.uo` dbb；SimRISC-08 的 32 位同族（`.ut`/`.st`）。语义按规范（**不套 RISC-V**）：窄位宽结果按值语义零/符号扩展、**`rrrr` 无符号加减的高半是进位/借位（0 或 1）**、有符号加减的高半是 128 位和/差的高 64 位、乘法的两个变体都是完整 128 位积的高半、除零与 `INT_MIN/−1` 取规范定值。
- **非实现编码 = 显式异常，不是 NOP**：`contracts/legality_rules.yaml` 的 `dst_rd0`/`dst_rb0`/`dst_dual_same`/`encode_sbz` 触发 **ILLI**；`opcodes.yaml` 已定义但本里程碑未实现的编码（其他 ld/st 宽度、分支/call/ret、16/8 位子表、FP、原子/位操作）触发 **ILLI**；QFC 主表/子表空白单元格触发 **UNDI**。核在 `printf` 中打印 `fault ... ILLI|UNDI` 并 halt（cease）。
- **闭环不回归**：`ld.o`/`st.o`、`jump rrii`、semihosting `trap` 语义沿用 `m12-003/004`；BootROM→`+loadmem`→应用→`SYS_EXIT` 的路径不变。访存/控制流完整实现与 RAS 归 `m12-chipyard-006/007`。

## 双 TL 端口与 8-beat 取指（`m12-chipyard-018`）

- **两个独立 TileLink 客户端**（用户 2026-11-10 裁定「取指和访存应该用两个 tilelink，在 m12 中就拆」）：`WumingTile` 声明 `fetchMasterNode` 与 `dataMasterNode`（各 `IdRange(0, 3)`），都并入 tile 内 `portXbar`；`WumingCore` 对应两个 `TLBundle`（`imem` / `dmem`），各自独立 A/D 通道与状态。数据访问在 `MREQ`/`MWAIT` 停多久都不影响取指端口推进（独立 bench：数据响应延迟 200 拍期间取指端口照常预取）。
- **source 编号**：拆端口后按端口本地分配——取指 `0` = 需求取指、`1`/`2` = 两个预取槽；访存 `0`。跨节点由 xbar 重映射，不冲突。TileLink 禁止「响应未回收就复用 source」，所以预取在飞上限 = 空闲 source 数（2）：更深流水需更宽 `IdRange`（M13 评估）。
- **取指队列**：`fetchDepth = 8`（8 beat = 64 B，用户裁定），环形队列 + 顺序预取；命中 1 拍（`EXEC` 直接从队列译码），未命中才发需求取指。预取是投机的：`denied`/窗口外只丢弃不报异常；需求取指与数据访问的 `denied` 才记 `CFXMEM`。
- **12 态骨架**（`m12-006` §5.1）：`IDLE/FREQ/FWAIT/EXEC/TRAP/SEMI/EXC/MREQ/MWAIT/SLOW/FAULT/HALT`。周期口径 R1 = C：移位/位域运算走 `SLOW`（`EXEC` 锁操作数、`SLOW` 算并写回，2 拍），简单算术 1 拍；寄存器堆保持 2 写 3 读（R8 = 2R2W）。`EXC` 目前只记录 cause 后进 `FAULT`——cfx 帧/向量由 `m12-chipyard-019` 落地，`ldm/stm` 语义由 `008`。
- **诊断**：每条 `printf` 末尾带 `cycle=`（仿真时间戳，供周期验收直接量取）；`fault ... ILLI|UNDI|IALIGN|CFXMEM` 格式不变。

## 边界

- **保留** rocket-chip 库（Diplomacy / TileLink / `BaseTile`）与 chipyard 仿真设施（Verilator harness / BootROM / 内存模型 / `loadmem`）。
- **抛开** Rocket 核与 RISC-V 语义（CSR / misa / PMP / MMU / TLB / 异常码）；`WumingCoreParams` 不继承 `CoreParams`。

## 校验

```
make apply-series
make check-source-state
make check-patch-tree
```
