# m16-chipyard-013: chipyard 实现差异盘点（对照其它 generator；gewu / wuming × tiny/vast）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：无（**只读分析**：不占 chipyard 写者锁，可与在跑任务并行）
**可并行分片**：是
**预估**：3–4 h
**档位**：小改（只读 + 写结论）
**状态**：已验证

## 背景（用户 2026-11-20 裁定）

M14 做过「内核实现 vs `arch/riscv`/`arch/arm64`」的差异盘点；M16 对 chipyard 做同构的事——**把我们的 generator（`dadao-gewu` / `dadao-wuming`）与其它 generator 逐项对比**。

**用户明确要求**：
- **对照物 = 其它 generator**；
- **`gewu` 主要对照 `rocket`**；
- **`wuming` 也应主要对照 `rocket`**；
- **`tiny` 和 `vast` 都要做**。

## 对照物

- **主参照**：`rocket`（`chipyard/generators/rocket-chip/**`）——它是 chipyard 里最成熟的 RISC-V 核，`wuming`/`gewu` 都从它演化或并列存在。
- **补参照**：`boom`（乱序对照，仅看接口面）、`chipyard` 自身的 `DigitalTop`/`Subsystem` 组装层。
- **wuqing**：**当前仓内不存在**（`components/chipyard/patches/generators/` 只有 `chipyard`/`dadao-gewu`/`dadao-wuming`）⇒ 本盘点不涉及；**将来到位后按同一口径补一份**。

## 范围

- `components/chipyard/patches/generators/dadao-gewu/**`、`dadao-wuming/**`；
- `DadaoConfigs.scala` 里的 `WumingTinyConfig` / `WumingVastConfig`（**两机型都要**）；
- 对照 `generators/rocket-chip/**` 的 `Tile`/`Core`/`TLB`/`PTW`/`Cache`/`PMP`/`Debug`/`Interrupt`。

## 要做（**只读**）

按「同类机制」逐项对照，四类差异：
1. **缺失实现**：rocket 有、我们没有（如 **PMP**、**debug module**、**RoCC 接口**、**多核/一致性**、**L1 D/I cache**、**FPU 的完整 hardfloat 路径**）；
2. **语义不符**：有但做法不同（PTE 格式/端序、TLB 替换策略、A/D 处理、异常码映射、中断控制器接入）；
3. **旁路 / 折衷**：为省事走的近路（如「PA RAM 走 TileLink 从端口、放弃 AXI4+SimDRAM」「外设移出窗口」——**已知且待 ADR**，如实记录不评判）；
4. **配置缺口**：`WumingTinyConfig`/`WumingVastConfig` 相对 rocket 配置缺的通用项（`useVM`/`pgLevels` 的语义、`fragments`/HSJU、`cfx` 的 generator 组织方式）。

**两机型单列**：`WumingTinyConfig`（SRAM、无 MMU/PTW）与 `WumingVastConfig`（PTW/TLB/大存储）分别对照 rocket 的哪个配置（`RocketConfig`/`TinyRocketConfig`/`MediumRocketConfig` 之类），差异在哪。

## 产出格式

每条：`generators/dadao-<x>/<file>:<line>` ↔ `generators/rocket-chip/<file>:<line>` / 分类 / 影响（tiny / vast / 两者）/ 优先级 P0/P1/P2。

## 验收

1. 结论写进本任务书「盘点结论」段（≤80 行）；
2. **覆盖现场派生**：比对了多少个模块 / 机制 / 配置项（现场统计 + 枚举口径）；
3. **抽查 ≥5 条**：两侧 `sed -n` 贴原文（chipyard 源码在组件源树里只读）；
4. **两机型各给一段**：`WumingTinyConfig` / `WumingVastConfig` 各自对照结果；
5. **不改代码**：`git show --name-only HEAD` 只含本任务书；不 elab、不跑仿真。

## 盘点结论

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

## 完成区

**测试结果**：默认模式 12/12 全绿，**两态各验一次**——①未提交态（树上仅本任务书被改）`rc=0`；②提交态（树干净、HEAD=任务书提交）`rc=0`；另验「提交态＋台账 follow-up 提交」`rc=0`、`--inject` 6 路反例全如期 FAIL。未改代码、未 elab、未跑仿真。

**修改文件**：`.tao/tasks/chipyard/m16-chipyard-013-chipyard实现差异盘点.md`（「盘点结论」61 行未动；本「完成区」+「返工 1」；状态→待验收）。运行期证据（脚本）在证据目录内、不入库。

**验收结果**：
- 未提交态：`C9 未改代码（.tao 以外 0 改动） | actual=基线(06066c59..HEAD)+工作树 paths=[.tao/tasks/…盘点.md] | rc=0`
- 提交态：`C9 … | actual=基线(06066c59..HEAD)+工作树 paths=[.tao/tasks/…盘点.md] | rc=0`；提交态＋台账：`paths=[.tao/knowledge/milestones-m12.md .tao/tasks/…盘点.md] | rc=0`
- 反例（提交态把实现文件提交进基线范围）：`C9 … | actual=base=06066c59 越界=[generators/dadao-wuming/src/__probe.scala] | rc=FAIL`
- 其余：`C1 N=61`、`C4 bad=0 total=81`、`C5 rows=27 缺8 语7 旁7 配5 两者23 vast4 tiny0 P02 P112 P213 我方8 rocket17`、`C10 0/0`、`C11 n=6` 均 `rc=0`

**返工 1**（reviewer 第 1 轮 Needs Revision：C9 提交后假 FAIL；唯一阻断）
- 原因：旧 C9 只认「`git status` 恰为 ` M 本任务书`」⇒ architect 提交后树干净即恒红，与完成区声明不符（第四次同类：`m14-linux-036`/`038`/`042`/本次）。
- 修法：①判据改**基线提交范围**——`(merge-base(HEAD, master|origin/master)..HEAD) ∪ 工作树` 的路径必须全在 `.tao/` 下且含本任务书，出现 `components|generators|spec|tools|contracts|tests|docs|.work` 任一即红（提交态、台账 follow-up 提交都天然回绿）；②无基线时退化为 A(未提交)/B(提交) 二选一；③`git` 一律 `-c core.quotepath=false`（中文文件名默认转义成 `\346…`，干净 clone 会再假红）；④C9/C10 返回自身判决，不污染全局累计。
- 两态 rc：未提交 0／提交 0／提交+台账 0／提交+实现文件 1（提交态用一次性临时克隆验证：同 HEAD + 树干净 + 最终内容，不触碰任务仓）。
- 注入：`INJECT 探针文件（预期 FAIL）rc=1`（越界 `components/chipyard/.c9_probe`）→ 删除 → `INJECT 探针删除（预期回绿）rc=0`。
- 一并改正：原「12/12 全绿、C9 rc=0」只在未提交态成立，已改为上列两态表述。

**新发现/坑**：①共享源树含**未入库的 m16-007 WIP**（`WumingPtw.scala` 无补丁、`WumingCore` 1905 vs 补丁 1590 行）⇒ 只读盘必须以补丁树为准；②补丁树可由「新增文件型补丁只抽 `+` 行」重建（不 apply），行号与源文件一致（内容第 N 行 = 补丁第 N+6 行）；③同名异义：`WumingCompatCoreParams.useVM/pgLevels` 是 rocket 占位值，`TileParams.icache/dcache` 设 `Some` 也不会被 wuming tile 读取；④rocket **无硬件 A/D**（`leaf()` 要求 A=1）且 PTE 小端，不能作 A/D/端序参考实现；⑤建议沉淀「我方 vs rocket 对照速查 + 分级口径」「补丁树重建行号法」「C9 两态/基线判据」三条。

**遗留问题**：
- 返工 1 已处置（见上，`C9` 两态与注入证据齐备），无未修 finding。
- 标〔007〕/〔008〕的 4 条（TLB、A/D、端序-PTE、PA RAM）须在 007/008 落地后复核。
- `wuqing` 仓内不存在 ⇒ 未盘点；只读任务无 elab/实测数字。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查对象：本任务书「盘点结论」27 行 + 两机型段 + 覆盖段，逐条比对两侧原文（脚本 C4 覆盖 81 条主引用与全部行内缩写）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 3 处 rocket 侧引用漏写 `rc/` 前缀（`rocket/PMP.scala` 等）→ 不可解析 | ✅已修 | 补 `rc/` 前缀 | C4 `bad=0` |
| `cy/RocketConfigs.scala` 少 `config/` 层，3 处不可解析 | ✅已修 | 改 `cy/config/RocketConfigs.scala` | C4 `bad=0` |
| 裸 `:N` 缩写歧义（「多核」行 `:86` 实属 `WumingCore`；Tiny 段 `:95` 实属 `DadaoConfigs`） | ✅已修 | 两处写全前缀；检查器改为「归属本行**最近**前序文件」 | C4 重跑 `bad=0` |
| P0/P1/P2 无定义、cache 却定 P0 ⇒ 与「Tiny 无 P0」自相矛盾 | ✅已修 | 补分级定义；L1 D-cache 降 P1；声明改 P0 2/P1 12/P2 13 | C5 对账 `rc=0` |
| 「总表 1、2、5、6、7 行」用位置编号易错 | ✅已修 | 改为具名（PMP/debug/L1 D/L1 I/中断） | 人工复核 |
| 端序与 A/D 缺 spec 出处（结论只挂实现） | ✅已修 | 补 `spec/DADAO-21`、`spec/DADAO-12 §2.2.1/§2.2.5` | 抽查第 3 条仍指向同一行 |
| 计数字面量写死风险（改表后不报错） | ✅已修 | 脚本从表现场派生并与文字声明逐项对账；注入「删一行/假优先级」即 FAIL | `INJECT 删一行 rc=1`、`INJECT 假优先级 rc=1` |
| 「Vast 无 PA RAM」若按共享源树判定会与 007 WIP 冲突 | ✅保留并显式声明 | 口径段写「按补丁树判定、〔007〕待复核」 | 结论 57/58 行 |

判决：全部 finding 已修（无未修项），状态置「待验收」。

### 第 1 轮 reviewer 验收（2026-11-20）

**重跑记录（全部为 reviewer 本人执行的真实输出/退出码，摘录）**
1. 抽查 30+ 处两侧 `sed -n`（P0/P1/P2 各 ≥2），全部对上：`gw/GewuFile.scala:119`→`val MEM_ADWBFAIL = 8 // [56] PTE A/D write-back failed` ↔ `rc/rocket/PTW.scala:141`→`def leaf(dummy: Int = 0) = v && (r || (x && !w)) && a`；`wm/WumingCore.scala:584`→`val (_, memGetBits) = dataEdge.Get(DATA_SRC, memBeat(addrBits - 1, 0), lgSize)` ↔ `rc/rocket/HellaCache.scala:23`→`case class DCacheParams(`；`wm/WumingParams.scala:221`→`val nPMPs = 0` ↔ `rc/rocket/RocketCore.scala:39`→`nPMPs: Int = 8,`；`wm/WumingTile.scala:59`→`val fetchMasterNode: TLClientNode = ...` ↔ `rc/tile/LazyRoCC.scala:64`→`abstract class LazyRoCC(`；`wm/WumingCore.scala:272`→`// TileLink puts byte k of a beat in bits [8k+7, 8k] (little-endian lanes);` ↔ `rc/rocket/PTW.scala:304`→`val tmp = mem_resp_data.asTypeOf(new PTE())`；`rc/rocket/Configs.scala:165`→`class With1TinyCore`、`:183`→`scratch = Some(0x80000000L)`
2. **P0①（Vast 无 2 GiB PA RAM）成立**：补丁树 `cy/config/DadaoConfigs.scala:183`→`case ExtMem => None`，在 `class WithDadaoVastAddressMap`（:180）内，SRAM/hmon 复用 tiny 的 8 MiB/64 KiB ⇒ 确无 PA RAM；对照 `rc/subsystem/Configs.scala:269`→`case ExtMem => Some(...`（:271 `size = x"1000_0000"` = 256 MiB）
3. **P0②（端序/PTE）成立**：`spec/DADAO-21`→「DADAO 采用大端序（big-endian），多字节数据的最高有效字节存放在最低地址」；`spec/DADAO-12` §2.2.1→「页表项按目标端序（大端）存放于物理存储器」；rocket 侧 `PTW.scala:304` 由 TL 小端 beat `asTypeOf(new PTE())`
4. **「rocket 无硬件 A/D」成立**：`leaf()` 要求 `a=1`、`sw()` 还要求 `d=1`；PTW/TLB 全文 grep 无 A/D 写回（仅 `r_pte.a/d` 拷贝）⇒「PTW 对照不能以 rocket 为参考实现」成立
5. **两机型对照配置存在且形态相符**：`cy/config/RocketConfigs.scala:19`→`class TinyRocketConfig`（`With1TinyCore`；xLen=32/pgLevels=2/useVM=false/fpu=None）；`:11`→`class RocketConfig`（`WithNHugeCores(1)`，`rc/rocket/Configs.scala:15`，8 路 I+D＋FPU）
6. **覆盖抽验 2 项**：表 27 行；现场数得我方被引文件 8、rocket 17、机制轴 14；通读 7 补丁＋上游 2 补丁（DigitalTop/PeripheralFragments）均存在 ⇒ 17+17 ✓
7. **判定基准可辩护**：组件源码树 `git status --porcelain -uall` 为空（007 的 24 补丁在其分支、master series=23）；`盘点结论` 全文不引用在途 `WumingPtw`（仅完成区新发现①提示）⇒ 未把在途 WIP 当已交付，以补丁树为基准正确
8. **证据脚本重跑**：运行期证据目录内 `run.sh` 默认模式 `rc=1`，两次重跑一致，唯一红项 `C9 工作树只改本任务书 | actual= | rc=FAIL`（此时树已被 architect 提交、干净）；`run.sh --inject` `rc=0`（4 路反例如期 FAIL＋真任务书 md5 不变）；**reviewer 独立注入**：改 `wm/WumingParams.scala:221`→`:99999` → `C4 ... actual=bad=1 total=81 | rc=FAIL`、总 `rc=1`；`cp` 还原 → md5 `ce5783d1…` 相等、复跑输出与注入前逐行一致（`BASELINE_IDENTICAL`）
9. **门控**：`make check-knowledge-refs` `rc=0`（`PASS`，0 处具体运行期引用、0 悬空）；`make check-tasks` `rc=0`（①报告 1 条即本任务、不阻断）
10. **不改代码**：`git show --name-only --format= HEAD` 仅本任务书；工作树干净（注入前后 md5 对账）；组件源树只读、未 apply 未 make

**约束核验**：只读盘点 ✓；不改代码/不 elab/不跑仿真 ✓；结论 61 行 ≤80 ✓；两机型各一段 ✓；覆盖现场派生 ✓；术语「寄存器组」口径、结论段无禁词 ✓；本记录不含任何运行期路径 ✓。文档级观察（不阻断）：完成区新发现①的源码树路径属豁免形、118 行禁词为自指用例，均经 `check-knowledge-refs` 放行。

**判决：Needs Revision（唯一阻断项在证据脚本，结论内容无需返工）**
- 阻断：`run.sh` 的 C9 是「提交后未回绿」型假 FAIL——architect 提交后工作树干净 ⇒ 默认模式恒 `rc=1`，与完成区「12/12 全绿、`C9 … rc=0`」在 reviewer 重跑下不符；AGENTS「验证脚本反例门控」明令断言变更存在须带基线提交范围、提交后仍须回绿。
- 修改建议（engineer 改脚本，reviewer 不代写）：C9 同时接受两种态——① 树上仅本任务书被改；② 树干净且 `git show --name-only --format= HEAD` 只含本任务书（或断言改用基线提交范围）。改完默认模式须 `rc=0`，再回本 reviewer 复核。
- 其余全部通过：27 条行号抽验、两条 Vast P0、无硬件 A/D 结论、两机型对照、覆盖计数、不改代码、两门控均为 reviewer 自跑结果。
- 补充实测：写入本记录后 `run.sh` 复跑 `rc=0`（`ALL CHECKS PASSED`，此时树上仅本任务书被改、C9 转绿），`make check-knowledge-refs` `rc=0`、`make check-tasks` `rc=0`——证明 C9 依赖「树是否被提交过」这一瞬时状态，本记录提交后必然复现 `rc=1`，故仍须按上述建议修脚本。

### 第 2 轮 engineer 自审（返工 1：C9 提交后假 FAIL）

reviewer 唯一阻断项（结论内容无需返工）。逐条处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| C9 只认「`git status` 恰为 ` M 本任务书`」⇒ 提交后树干净即恒红 | ✅已修 | 判据改**基线提交范围**：`(merge-base(HEAD,master)..HEAD) ∪ 工作树` 路径必须全在 `.tao/` 且含本任务书 | 未提交态 `rc=0`／提交态 `rc=0` |
| 放宽后若不查实现文件，提交态会漏检「改了代码」 | ✅已加反例 | 老判据换成「`.tao/` 之外任一改动即红」 | 提交态注入 `generators/…/__probe.scala` → `越界=[…] rc=FAIL` |
| 中文文件名在干净 clone 里被转义成 `\346…` ⇒ 又一次假红 | ✅已修 | 所有 `git` 调用加 `-c core.quotepath=false` | 该 clone 的 `--name-only` 默认转义，复跑 `rc=0` |
| 收尾台账常单独一笔提交 ⇒「HEAD 只含本任务书」仍会误红 | ✅已修 | 判据只要求「`.tao/` 之外 0 改动」＋范围内含本任务书 | 提交+台账 `paths=[.tao/knowledge/milestones-m12.md …盘点.md] rc=0` |
| C9/C10 复用全局 `pass/fail` 污染累计 rc（注入自检要复调） | ✅已修 | 两函数返回自身判决，main 里 `|| rc_all=1` | `--inject` 6 路后总 `rc=0` |
| 完成区原「12/12 全绿、C9 rc=0」与提交态实测不符 | ✅已修 | 改成「两态各验一次」并加「返工 1」段 | 见完成区 |

判决：全部 finding 已修（无未修项）；27 条结论、两机型段、覆盖数**未动**；状态置「待验收」。

### 第 2 轮 reviewer 验收（2026-11-20，只核 C9 修复／两态／注入）

**重跑记录（reviewer 本人执行的真实输出与退出码，摘录）**
1. 读脚本核判据：`check_repo` 取 `merge-base(HEAD, master|origin/master)`，路径 = `git diff base..HEAD` ∪ `git status -uall`，须全在 `.tao/` 下且含本任务书；越界任一（`components|generators|spec|tools|contracts|tests|docs|.work`）即红；无基线时退化 A(未提交)/B(提交)；`git` 调用均带 `-c core.quotepath=false`——与派单描述一致。
2. **提交态自跑**：运行期证据目录内 `run.sh` 默认模式 `rc=0`／`ALL CHECKS PASSED`；`C9 … actual=基线(06066c59..HEAD)+工作树 paths=[.tao/tasks/chipyard/m16-chipyard-013-chipyard实现差异盘点.md] | rc=0`、`C10 … rc=0` ⇒ 第 1 轮唯一阻断消除。
3. 边界 A（在**一次性临时克隆**内做，任务仓零提交）：追加一笔仅 `.tao/` 的台账提交 ⇒ `C9 … paths=[.tao/knowledge/milestones-m12.md .tao/tasks/…盘点.md] | rc=0`，总 `rc=0` ✓（顺带验证中文文件名未被转义、无 `master` 时退到 `origin/master`）
4. 边界 B（同一临时克隆）：提交 `generators/dadao-wuming/src/__probe.scala` ⇒ `C9 … 越界=[generators/dadao-wuming/src/__probe.scala] | rc=FAIL`、`C10 … actual=1 | rc=FAIL`，总 `rc=1` ✓
5. **我独立注入（非脚本自测）**：树里放 `components/chipyard/.c9_probe` → `run.sh rc=1`（`越界=[components/chipyard/.c9_probe]`）；删除 → `run.sh rc=0`／`ALL CHECKS PASSED`；删除后 `git status -uall` 干净、探针文件不存在 ✓
6. 脚本自带 `--inject`：`rc=0`——4 路文件反例（坏行号／删表行／假优先级／禁词）均如期 `rc=1`，探针 FAIL `rc=1`＋删除回绿 `rc=0`，真任务书 md5 前后不变（`3fbe6967`）
7. **结论未动**：`git diff 915e7d48..HEAD` 只有完成区与审阅记录两处 hunk；「盘点结论」段在两版 md5 均为 `9d3c3af4…` ⇒ 27 条／两机型段／覆盖数／P0 2 条／「rocket 无硬件 A/D」与第 1 轮核过的一致
8. 不改代码：`git show --name-only --format= HEAD` 仅本任务书；组件源码树 `git status -uall` 干净（我全程只读、未 apply 未 make）
9. 门控：`make check-knowledge-refs` `rc=0`（`PASS`，0 处具体运行期引用、0 悬空）；`make check-tasks` `rc=0`（①报告 1 条即本任务，不阻断）

**约束核验**：不改代码／只读 ✓；边界测试全在一次性临时克隆内、任务仓零提交 ✓；本记录不含任何运行期路径 ✓；全文无「银行」（grep = NONE）✓。

**判决：Accepted** —— 第 1 轮唯一阻断（C9 提交后假 FAIL）已修：提交态 `rc=0`、台账 follow-up 提交态 `rc=0`、实现文件入范围 `rc=FAIL`、探针注入红→删→回绿均经 reviewer 自跑复现；结论内容未动、两门控真实 `rc=0`，证据脚本在 reviewer 自己的重跑下全绿。architect 提交本记录后复跑应仍 `rc=0`（判据已与「树是否被提交过」解耦），可 `/complete`。
