# chipyard 实现与其它 generator 的差异盘点（结论索引）

> **性质**：`m16-chipyard-013 chipyard 实现差异盘点` 的**结论汇总**（只读分析的产出），**不是实现判据**——判据在 `spec/` 与 `.tao/contracts/`。逐条原文在本任务书「盘点结论」段（`.tao/tasks/chipyard/m16-chipyard-013-chipyard实现差异盘点.md`）。
> **对照物**：其它 generator——主参照 **`rocket`**（`generators/rocket-chip/**`）；`gewu` 与 `wuming` 都对照 rocket。
> **范围**：`dadao-gewu` / `dadao-wuming` × **tiny / vast 两机型**；`wuqing` 仓内未实现，将来到位按同一口径补。
> **整改权**：由用户逐项决定；本页只做索引与分流。

**口径**：我方 = **组件补丁树** `components/chipyard/patches/generators/**`（`git show` 可复核的入库态，含 m16-006/012）；行号 = 该文件全文行号（新增文件补丁形如 `@@ -0,0 +1,N @@`，内容第 N 行在补丁第 N+6 行）。rocket 侧 = 组件源树 `generators/rocket-chip/**`（只读、commit 锁定）。路径前缀：`gw/` = `generators/dadao-gewu/src/main/scala/gewu/`，`wm/` = `generators/dadao-wuming/src/main/scala/wuming/common/`，`cy/` = `generators/chipyard/src/main/scala/`，`rc/` = `generators/rocket-chip/src/main/scala/`。
**在跑**：`m16-007`（Vast PTW）/`m16-008`（ID-TLB）**未入库**，其 WIP 只在共享源树里 ⇒ 本表按补丁树判定；PTW/TLB 行标 `〔007〕`/`〔008〕`，落地后须复核。
**分类**：缺失 = rocket 有我方无；语义 = 有但语义不同；旁路 = 为省事走的近路（如实记录、不评判）；配置 = 参数/装配缺口。
**优先级**：P0 = 机型验收直接相关（正确性/可跑/主存通路）；P1 = 能力缺口，本里程碑须排期；P2 = 记录/待 ADR/暂不影响。

### 差异总表（我方 ↔ rocket / 分类 / 影响 / 优先级）
- PMP：`gw/GewuFile.scala:414`（无 PMP；权限模型是 cfx 源掩码）＋`wm/WumingParams.scala:221`（nPMPs=0）↔ `rc/rocket/RocketCore.scala:39`（nPMPs=8；`rc/rocket/PMP.scala:143` 检查器、`rc/rocket/TLB.scala:416` 实例化）／缺失／两者／P2
- debug+trigger：`wm/WumingParams.scala:206`（useDebug=false；:223 nBreakpoints=0）↔ `rc/rocket/CSR.scala:670`（debug_csrs；`rc/rocket/RocketCore.scala:37`）／缺失／两者／P2
- RoCC：`wm/WumingTile.scala:59`（仅 2 个 TL client，无 rocc 节点）↔ `rc/tile/LazyRoCC.scala:64`（opcodes/atl/tl/stl 节点）／缺失／两者／P2
- 多核/一致性：`wm/WumingParams.scala:278`（WithNWumingTiles 带 n，配置恒 1；`wm/WumingCore.scala:86` lr/sc 单 hart）↔ `rc/rocket/Configs.scala:15`（WithNHugeCores(n)）／缺失／两者／P1
- L1 D-cache：`wm/WumingCore.scala:584`（每次访存一条 8 B Get/Put）↔ `rc/rocket/HellaCache.scala:23`（DCacheParams/nMSHRs/64 B block）／缺失／两者／P1
- L1 I-cache：`wm/WumingCore.scala:246`（8 beat 取指队列）↔ `rc/rocket/ICache.scala:46`（ICacheParams 64×4×64 B）／缺失／两者／P1
- 中断源/控制器：`wm/WumingTile.scala:42`（intSinkNode 终止，`:47` 无 tile 内源）↔ `rc/tile/Interrupts.scala:37`＋`rc/subsystem/HasTiles.scala:211`／缺失／两者／P1
- TLB 替换/无效化：`gw/GewuFile.scala:386`（tlb_control 写即执行）〔008〕↔ `rc/rocket/TLB.scala:615`（SetAssocLRU＋PseudoLRU）、`rc/rocket/PTW.scala:232`（sfence）／缺失／vast／P1
- 异常码编码：`gw/GewuFile.scala:96`（one-hot 分层 cause）↔ `rc/rocket/Instructions.scala:821`（MCAUSE 0…0x17）／语义／两者／P1
- 异常进入/返回帧：`gw/GewuFile.scala:696`（cfx 帧＋强制 hypv＋escape 恢复）↔ `rc/rocket/CSR.scala:959`（cause/delegation/tvec/debug/NMI）／语义／两者／P1
- 寄存器访问合法性：`gw/GewuFile.scala:507`（readOk/writeOk 双轴）↔ `rc/rocket/CSR.scala:924`（read_illegal/CSR 映射）／语义／两者／P2
- 端序：`wm/WumingCore.scala:272`（TL 小端 lane ↔ DADAO 大端逐字节倒序〔`spec/DADAO-21` 大端；PTE 亦大端 `spec/DADAO-12` §2.2.1，〔007〕〕）↔ `rc/rocket/PTW.scala:304`（`mem_resp_data.asTypeOf(new PTE())` 小端）／语义／两者／P0
- A/D 位：`gw/GewuFile.scala:119`（`[56] ADWBFAIL` 子原因＝硬件置位/回写，`spec/DADAO-12` §2.2.5）↔ `rc/rocket/PTW.scala:141`（`leaf()` 要求 A=1，无硬件置位）／语义／vast／P1
- 原子：`wm/WumingCore.scala:86`（仅 lr/sc，单 hart 保留标记）↔ `rc/rocket/AMOALU.scala:54`（AMO）／语义／两者／P2
- 地址合法性：`wm/WumingCore.scala:438`（三窗口＋`addr[47:42]=0` 内存窗口）↔ `rc/rocket/TLB.scala:416`（PMA/PMP 检查）／语义／两者／P2
- 主存组织：`cy/config/DadaoConfigs.scala:95`（SRAM/hmon 为 MBUS 上 TL 从端口）↔ `cy/config/AbstractConfig.scala:19`（AXI4 ExtMem＋SimDRAM）／旁路／两者／P2
- PA RAM：`cy/config/DadaoConfigs.scala:183`（Vast 亦 `ExtMem => None`，无 PA RAM）↔ `rc/subsystem/Configs.scala:269`（默认 256 MiB ExtMem）／旁路／vast／P0
- 加载器/主机模型：`wm/WumingTile.scala:94`（tile 内 TL client 加载器）↔ `cy/config/AbstractConfig.scala:20`（SerialTL＋SimTSI）／旁路／两者／P2
- fence 语义：`wm/WumingCore.scala:101`（fence/swym 识别为 no-op）↔ `rc/rocket/RocketCore.scala:612`（sfence/fence.i 走 TLB/ICache）／旁路／两者／P1
- 外设落位：`cy/config/DadaoConfigs.scala:180`（Vast 图只改 BootROM/ExtMem）↔ `rc/subsystem/Configs.scala:59`（Debug/CLINT/PLIC 默认件）／旁路／vast／P2
- FP 实现：`wm/WumingFP.scala:21`（自研 RecFN，hardfloat 非依赖）↔ `rc/tile/FPU.scala:298`（hardfloat 库）／旁路／两者／P2
- LLC 借用：`cy/config/DadaoConfigs.scala:141`（两侧均继承 AbstractConfig 的 LLC；`cy/config/AbstractConfig.scala:124`）↔ `cy/config/RocketConfigs.scala:21`（tiny 走 incoherent、去 L2）／旁路／两者／P2
- `useVM`/`pgLevels` 同名异义：`wm/WumingParams.scala:202`（:246 pgLevels=3 仅占位）↔ `rc/tile/BaseTile.scala:204`（useVM 决定 vaddrBits）＋`rc/rocket/RocketCore.scala:18`（pgLevels）、`rc/rocket/RocketCore.scala:20`（useVM）／配置／两者／P1
- HSJU：`wm/WumingParams.scala:143`（modeBits=2，:152 只到 hypv）↔ `rc/rocket/RocketCore.scala:21`（useUser/useSupervisor/useHypervisor）／配置／两者／P1
- TileParams 缓存字段被忽略：`wm/WumingParams.scala:258`（icache=None；:259 dcache=None，且 tile 不读）↔ `rc/tile/RocketTile.scala:49`（`require(icache.isDefined)`）／配置／两者／P1
- cfx 组织：`gw/GewuFile.scala:249`（独立 generator＋GewuParams 注入）↔ `rc/rocket/CSR.scala:494`（reg_pmp/CSR 留在核内）／配置／两者／P2
- fragments 粒度：`wm/WumingParams.scala:250`（WumingTileParams 单层、无 per-能力变体）↔ `rc/rocket/Configs.scala:62`（WithN{Big,Med,Small}Cores 各带 cache/FPU 组合）／配置／两者／P2

### WumingTinyConfig（对照 `TinyRocketConfig` = `With1TinyCore`）
- 对照配置：`cy/config/RocketConfigs.scala:19` → `rc/rocket/Configs.scala:165`（xLen=32/sv32/useVM=false/fpu=None/DCache scratch 0x8000_0000/无 L2）；我方 `cy/config/DadaoConfigs.scala:114`（64 位、无 MMU/PTW、SRAM+hmon+BootROM 三窗口）。
- 相同：无地址翻译、主存不是 DRAM；FP 上两者都不可比（rocket `fpu=None`，我方 FP 单元恒在核内，见「FP 实现」行）。
- 差异①：主存是 MBUS 上 8 MiB TL scratchpad（`cy/config/DadaoConfigs.scala:95`），rocket tiny 主存是 DCache scratchpad（`rc/rocket/Configs.scala:183`）——同一件事的两种落法。
- 差异②：rocket tiny 仍有 ICache/DCache/PMP/debug/CLINT/PLIC；我方全缺（总表 PMP/debug/L1 D/L1 I/中断 五行）。
- 差异③：我方 Tiny 只实现 cfx_hmon/cfx_power（`wm/WumingParams.scala:134`），无 `cfx_ptw` ⇒ `addr[47:42]=0` 恒 `CFXMEM [57] NONPTW`（`wm/WumingCore.scala:457`＋`enterMemFault`）。
- 差异④：我方 Tiny 亦继承 AbstractConfig 的 LLC（`cy/config/AbstractConfig.scala:124`），而 core 无 cache/coherence ⇒ 该 LLC 无可观测作用。
- 结论：Tiny 无能力缺口 P0——总表两条 P0 中「端序」对 Tiny 是核对项（beat 大端搬取已实现）、「PA RAM」不适用 ⇒ Tiny 的实际排期是 P1 = D/I cache、中断接入、HSJU；P2 = PMP/debug/RoCC/LLC。

### WumingVastConfig（对照 `RocketConfig` = `WithNHugeCores`）
- 对照配置：`cy/config/RocketConfigs.scala:11` → `rc/rocket/Configs.scala:15`（64 位/Sv39/FPU/8 路 I+D/ExtMem 256 MiB）。
- 相同：64 位＋页表翻译＋大物理内存的意图一致。
- 差异①（P0）：补丁树里 Vast 与 Tiny 同图、`ExtMem => None`（`cy/config/DadaoConfigs.scala:183`），**没有 2 GiB PA RAM** ⇒ `ptw_enable=1` 无路可走〔007 在跑〕。
- 差异②（P0）：页表几何/端序不同——DADAO 2 级/42 位 VA/56 位 PA/64 KiB 页、PTE 大端；rocket Sv39/3 级/4 KiB/小端（`rc/rocket/RocketCore.scala:18`、`rc/rocket/PTW.scala:304`）。
- 差异③（P1）：A/D 我方硬件置位并原子 OR 回写（失败即 `[56] ADWBFAIL`），rocket 要求软件先置 A（`rc/rocket/PTW.scala:141`）。
- 差异④（P1）：TLB 我方是 `cfx_ptw_tlb_control` 命令面〔008〕，rocket 是 PLRU 组相联＋sfence.VMA（`rc/rocket/TLB.scala:615`）。
- 差异⑤（P2）：Vast 现以 LLC＋coherent topology 作一致性根（`cy/config/AbstractConfig.scala:124`），核心无 cache ⇒ 语义不可比；debug/CLINT/PLIC/UART 仍在 0x0/0x0200_0000 等，PA RAM 落地会压到它们，须移窗口（`cy/config/DadaoConfigs.scala:180`）。
- 结论：Vast 的 P0 = PA RAM 落地＋端序/PTE；P1 = A/D 回写、TLB、中断；P2 = 一致性根与外设窗口（均待 ADR）。

### 覆盖现场派生（脚本从本节现场统计，口径＝机制轴 × 文件 × 表行）
- 表 27 行，引用我方 8 文件、rocket 17 文件；另通读我方 7 文件（ALU/Decoder/FPUnitHarness/LoadMem/RegFile/Semi/WumingSuccess）与上游改动 2 处（DigitalTop/PeripheralFragments），无对应差异故不入表 ⇒ 比对文件合计 17＋17。
- 机制轴 14：异常、中断、内存保护、MMU/PTW、TLB、L1 缓存、原子、调试、加速器接口、一致性、FP、端序、装配、地址映射。
- 分布：缺失 8、语义 7、旁路 7、配置 5；影响 两者 23、vast 4、tiny 0（Tiny 专属差异见上节，表内按「两者」归并）；优先级 P0 2、P1 12、P2 13。
- 未覆盖：`wuqing` 仓内不存在 ⇒ 本盘点不涉及，**将来到位后按同一口径补一份**。
