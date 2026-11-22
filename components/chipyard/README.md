# chipyard 组件（chipyard）

Chipyard 是 DADAO 的 **RTL SoC 仿真平台 + 核迁入目标**（`ADR-0024 D1`，2026-11-08 就地修订：不再 `patchless`）。上游基线与补丁序列由 `manifests/components.lock.toml` 锁定（主仓 commit + `manifests/chipyard-submodules.lock.toml` 子模块快照，`ADR-0024 D2`）；工作树由 `make fetch` + `make apply-series` 在运行期组件源目录建立。

## 与其它 generator 的差异盘点（参考）

`chipyard-diff-vs-rocket.md`：`m16-chipyard-013` 只读盘点的结论索引——`dadao-gewu`/`dadao-wuming` 对照 **`rocket`**，**覆盖 tiny / vast 两机型**；`wuqing` 仓内未实现，将来到位按同一口径补。**只读分析的结论汇总，不是实现判据**。

## 补丁集

- 形态：**树形补丁集**（`patches/<上游相对路径>.patch`，一文件一补丁），清单见 `series`；规范见 `docs/Process-01-组件补丁组织与构建编排.md`。
- 内容（M12 起）：`generators/dadao-wuming/**` 新增文件（DADAO「wuming」Tile 外壳 + 最小启动执行器 + 参数/配置片段 + Tiny bootrom 的 hex 资源与解码 + `+loadmem=` 加载器）、两处上游文件修改（根 `build.sbt` 的 `wuming` 项目接线、`generators/chipyard/.../config/fragments/PeripheralFragments.scala` 的 BootROM 资源名参数）。M16 起另有 `generators/dadao-gewu/**`（cfx 寄存器堆 generator，`m16-chipyard-002`），根 `build.sbt` 的三个项目接线在同一份 `build.sbt.patch` 里。
- **子模块补丁集**（`m12-infra-003` 起）：子模块自身的源码改动不在本目录，而在 `submodules/<子模块 path>/{series,patches/}`，由 `manifests/components.lock.toml` 的 `[[component.submodule_patch]]` 声明（base = 子模块 lock 的 pin）；`make apply-series` 在子模块内生成自己的 `base+1` commit，本组件 commit 记录该 gitlink。规范见 `docs/Process-01 §14`。当前只有一条：`generators/testchipip`（`SimDRAM.cc` / `SimDRAM.v`，见下）。
- 构建与调试在主控机执行（用户 2026-11-10 裁定；`.tao/knowledge/nodes.md §10.1`）；长仿真仍归节点。

## testchipip 子模块补丁（`m12-infra-003`）

- `src/main/resources/testchipip/csrc/SimDRAM.cc`：`loadmem_memif_t::get_target_endianness()` 原固定返回 `endianness_little`，fesvr 开 `--enable-dual-endian` 后大端 ELF 仍会命中「system uses a little-endian memory system」并 throw。改为 **`+loadmem_be` plusarg 显式打开**才返回 `endianness_big`；**默认保持 little**，stock RISC-V 配置（小端）行为不变。
- `src/main/resources/testchipip/vsrc/SimDRAM.v`：`MEM_BASE` 参数原为无位宽默认值 `0`（按 32 位有符号推断），48 位基址经 DPI 传 `longint mem_base` 会被截断；改为 `64'h0` 使其为 64 位。
- 用途：把 `+loadmem=<elf>` 的预装通路接到 DADAO 的大端 ELF；本阶段 Tiny 配置不用 stock `SimDRAM`（主存是 banked scratchpad，见下节），补丁是为后续带 AXI 后备内存的配置准备。

## 地址图（`Kaiwu-Tiny`，`spec/Kaiwu §1.1`）

- **BootROM** `0xffff_ffff_0000` / 64 KiB / 复位向量 = 起始；**SRAM** `0xffff_ff00_0000` / 8 MiB / 唯一可写主存。两者都是 **48 位核内地址**；核 `useVM=false`（无 MMU/TLB），无 cfx / PTW。
- **实现方式 = 改 fragment 的既有字段，不新增 `AddressMap`**：chipyard 的地址图由 `BootROMLocated` + `BankedScratchpadKey` + 后备内存端口 `ExtMem`/`ExtTLMem` 三个来源拼出，`generators/chipyard/src/main/scala/config/DadaoConfigs.scala` 里的 `WithDadaoTinyAddressMap` 正好重定向这三处：
  - BootROM 几何/复位向量/镜像名经 `chipyard.config.WithBootROM`（`address`/`hang`/`contentFileName`）；该 fragment 另把 `appendDTB` 关掉（Tiny 的 BootROM 只有复位/启动 stub，无 DTB、无 image index table）。
  - SRAM 用 testchipip 的 **banked scratchpad**（`BankedScratchpadParams`，`busWhere = MBUS`、`dtsEnabled = true`）替换 chipyard 默认的 64 KiB scratchpad（`0x0800_0000`）；它就是 TileLink 从端口，不再另设内存模型。
  - `ExtMem` / `ExtTLMem` 都置 `None`：不开 AXI/TL 后备内存端口（Tiny 无 DRAM），harness 里的 `SimDRAM` 也随之消失。
- **BootROM 镜像**：补丁集不能携带二进制，故 Tiny bootrom 以 `generators/dadao-wuming/src/main/resources/dadao/bootrom/bootrom.tiny.hex`（文本 hex）入库，`wuming` 项目的 `resourceGenerators`（根 `build.sbt`）在构建时解码成 classpath 资源 `/dadao/bootrom/bootrom.tiny.img`；镜像内容与 `loadmem` 闭环由 `m12-chipyard-003` 负责。`m12-chipyard-028` 起该 hex 由 `tools/testcases/arch/build_tiny_bootrom.py` 重生成；`m16-chipyard-015` 跟随 `m15-testcases-021`（`LD64`/`LOAD_ADDR` 宏改规范伪指令 `set.rd`/`set.rb`）再生成一次 ⇒ 解码镜像 md5 **`a5d78816…`**、power 段 292 B（旧 344 B，宏展开指令数减少）、hmon 段 44 B/对齐 48 B，与 QEMU/gem5 的 `bootrom_tiny.bin` 同版。
  - **改 hex 后必须删 `.classpath_cache/chipyard.jar`**：仿真器只把 Scala/Verilog 源当依赖，资源变更不会让缓存 jar 失效 ⇒ 不删就会拿旧固件重新 elaborate（假绿）。
- **实测**：`WumingTile` 的 elaboration 行打印协商值，`Generated Address Map` 打印全图。

## 启动与 `+loadmem`（`m12-chipyard-003`）

- **启动约定 = 固定入口**：Tiny BootROM 是静态平铺 trampoline（`tests/shared/bootrom/bootrom.S`：装 SP、装应用入口、`jump`），入口取 `machine-tiny.inc` 的 `ENTRY = 0xffff_ff01_0100`。**不用 ELF `e_entry`**：ROM 里没有 ELF 解析器/image index table/DTB，无法在运行时得知 `e_entry`；固定入口与 `QEMU kaiwu-tiny` 的 raw-kernel 约定（`kernel_base + kernel_reserved`）同源，应用链接脚本（`tests/shared/bootrom/tiny_smoke.lds`）用同一常量。
- **`+loadmem=<elf>` 窗口**：ELF 的 `PT_LOAD` 必须落在 SRAM 窗口 `0xffff_ff00_0000` + 8 MiB（`WumingTinyAddressMap.sramBase/sramSize`，**无默认值**，未配置即 elaboration 报错）；`p_memsz - p_filesz` 尾部零填（`contract-elf §5/§6`）。
- **实现方式 = tile 内 TL 主端口上的加载器**（`WumingLoadMem`）：解析 ELF64 大端 `PT_LOAD`，把每个 8 字节字作为 TileLink 请求写到与核相同的端口（不足 8 字节的字用 `PutPartial` 掩码），随后**逐字回读比对**；只有回读全等才拉高 `initDone` 释放核（`WumingCoreStub.bootEnable`）。装载/回读失败打印 `[WumingLoadMem] ERROR:` 并以非零退出（load-stage error 语义）。
- **为什么不用 stock `SimDRAM`**：① 当前 Tiny 设计**没有 `SimDRAM` 实例**——主存是 `BankedScratchpadKey → ScratchpadBank → TLRAM`（on-chip TL slave，不经 AXI），`ExtMem`/`ExtTLMem = None` 时 `WithBlackBoxSimMem` 无 AXI4 端口可绑；`+loadmem` 的写入目标是 SimDRAM 的 **host mmap backing**（`SimDRAM.cc` 的 `loadmem_memif`），写不到 SRAM。② fesvr 的 `load_elf` 在未开 `RISCV_ENABLE_DUAL_ENDIAN` 的构建里直接拒绝大端 ELF（本工具链 `config.h` 为 `#undef`，DADAO ELF 是 `ELFDATA2MSB`）；即便开启，`SimDRAM.cc` 的 `loadmem_memif_t::get_target_endianness()` 仍返回 little、dual-endian 分支仍 throw。故加载器自带 ELF 解析并用**绝对** `p_paddr`（无 `mem_base` 减法）。子模块补丁能力已由 `m12-infra-003` 补齐（见上「testchipip 子模块补丁」），该缺口不再挡路——Tiny 不用 stock `SimDRAM` 的**结构性理由仍是①**（无 `SimDRAM` 实例、`+loadmem` 只写 host backing）。
- **可观测出口**：Tiny 无 cfx/semihosting（属 `m12-chipyard-004`），最小程序 `tests/shared/bootrom/tiny_smoke.S` 以**未定义指令**收尾 ⇒ `WumingCoreStub` halt → `reportCease`。chipyard 默认不把 tile cease 接到 TestDriver，故 `WithWumingCeaseSuccess` 把 `HasTileNotificationSinks.tileCeaseSinkNode` 暴露成 `SuccessPort`，由 `WithTraceGenSuccess` 驱动 `chiptopSuccess` ⇒ TestDriver `$stop`（`$finish`，rc=0）；`+max-cycles` 仅作有界兜底。程序内的 SRAM 写/读回与每条取指/执行都经 `printf` 打印（需 `+verbose`）。

## semihosting 应答者（`m12-chipyard-004`）

- **通道 = DPI 导出端口**（不是预留 MMIO）。核内 `WumingCoreStub` 命中 `trap <any cfxha>, 0x3FF00+op`（判定只看 `immu18[17:8] == 0x3FF`，与 `cfxha` 无关）时，只把 `(op=immu18[7:0], arg=rb16, ret=rd8, pc=IP)` 抬到 tile 边界并等待一个 64 位标量；**核内没有任何宿主调用**。理由：请求/应答天然同步，无需地址图新增 MMIO 区间与轮询；应答者还要读 guest 内存（字符串/参数块），DPI 桥可像 `+loadmem` 加载器一样自带 TileLink 主端口，MMIO 方案仍需要这条总线且多一层协议。
- **实现**：`WumingSemi.scala`（LazyModule + TL 读引擎）+ `wuming/vsrc/WumingSemi.v`（DPI 桥）+ `wuming/csrc/WumingSemi.cc`（宿主模型）。应答者与核、加载器共用 tile 的 TL 端口 xbar；返回写 `rd8` 后核自行 `IP += 4`（`spec/Kaiwu §5.4`，无 `escape`）。
- **服务集（最小 5 个，table-driven）**：`SYS_WRITEC(0x03)` / `SYS_WRITE0(0x04)` / `SYS_WRITE(0x05)` / `SYS_CLOCK(0x10)` / `SYS_EXIT(0x18)`。
  - `SYS_WRITEC`/`SYS_WRITE0` 逐字节写 stdout（不截断、不重编码）；无定义返回值按 gem5/QEMU 约定写 `0xdeadbeef`。
  - `SYS_WRITE` 读参数块〔句柄, 缓冲区指针, 字节数〕；**本阶段未实现 `SYS_OPEN`**，故句柄 `1`=stdout、`2`=stderr 是本 harness 的约定（非 spec 断言），其它句柄返回 `-1` 并告警。
  - `SYS_CLOCK` = 自进程启动的宿主 CPU 百分秒（与 QEMU `clock()/(CLOCKS_PER_SEC/100)` 同式），返回值单调不减（实现内做下界钳制）。
  - `SYS_EXIT` 读参数块〔原因码, 子码〕：原因码 `0x20026` 时宿主退出码 = 子码（`spec §7.1` guest `0x00–0x3F`=PASS、`0x40–0x7F`=FAIL），否则为 1；以进程退出实现**有界停机**，不依赖 TestDriver 超时。
  - **未实现服务号 ⇒ 明确报错并给出服务号（十六进制）后以非零退出**，不静默返回 0。
- **三平台**：`tests/shared/bootrom/semihost_smoke.S` 的同一 ELF 在 QEMU `kaiwu-tiny`、gem5 FS `tiny` 与本 harness 上 stdout 逐字节一致、退出码一致；`semihost_fail.elf` 验证 guest FAIL 段映射，`semihost_unimpl.elf` 验证未实现服务号报错，`semihost_write.elf` 覆盖 `SYS_WRITE`（QEMU/gem5 的 raw stdout 句柄语义不同——gem5 未 `SYS_OPEN` 时 `files[1]` 越界崩溃、QEMU 需先开 `:tt`——故 `SYS_WRITE` 单独成像，不进入三平台比对集）。

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

## 访存（`m12-chipyard-008`）

- **单元素 `ld`/`st`**（`spec/SimRISC-01 §1–§4`）：`ld.{ub,uw,ut,sb,sw,st}`、`st.{b,w,t}` 与 `ld.o`/`st.o` 的 rd/rb/ra 三种寄存器组（RF 寄存器组归 `m12-chipyard-011`，当前仍 ILLI）；地址 = `rbHB + imms12`，按访问宽度做 `MALIGN`，写回按宽度零/符号扩展。
- **`ldm`/`stm`**（`rrri`，1–63 个寄存器）：地址 = `rbHB + rdHC`（用**原始** `rdHC`），元素 i 在 `addr + i·W`；**按 8 字节 TileLink beat 分组**（元素自然不跨 beat）——`stm` 用整拍 `Put` + byte mask 打包，`ldm` 用整拍 `Get` 后逐元素提取。整段（对齐 + 地址窗口）在 `EXEC` **预检**、第一拍之前判定 ⇒ 精确 `MALIGN`/`CFXMEM`；中途 `denied`/`corrupt` ⇒ `CFXMEM` 进 hmon（非精确，软件可重入整条指令）。
- **地址合法性 = Tiny 三段窗口**（`spec/Kaiwu §1.1`：BootROM / SRAM / hmon SRAM）：窗口之外一律 `CFXMEM`。不能只看 `TLXbar` 协商出的 manager 集合——chipyard 在地址 0 还有 debug-controller 等外设，会让未映射访问被当成合法总线访问；取指/预取用同一口径。
- **`ra` 寄存器组**：`WumingRegFile` 增加第三组 64×64 寄存器（`ra0` 可读写）；RAS 的溢出/下溢与 `call`/`ret` 语义归 `m12-chipyard-009`。
- **字节序**：所有总线访问按 8 字节 beat 对齐，大端在 beat 内逐字节重组（`addressOrder`/`laneOrder`）；`st.b/.w/.t` 用 byte mask 只写目标字节，邻字节不变。

## 控制流与 RAS（`m12-chipyard-009`）

- **控制流全形式**（`spec/SimRISC-06`）：`br.{eq,ne}`（`rrii`，比较两个 rd）、`br.{n,nn,z,nz,p,np}`（rd 与 rb 形式）、`jump`（`iiii` 相对 / `rrii` 绝对）、`call`（`iiii`/`rrii`）、`ret rdHA, imms18`。目标地址按 `rb0 = 当前 IP` 做 64 位加法后取低 48 位；`ret` 的目的 rd 写符号扩展的 `imms18`，`rd0` 配非零立即数 ⇒ `ILLI`。
- **返回地址 = 当前 `call` 的地址 + 4**（两种形式一致），压栈/弹栈流程是 `spec/SimRISC-00 §2.4.1/§2.4.2` 的 C1/C2/C3a、D1/D2/D3，全部在 `EXEC` 组合完成（1 拍）。
- **RegRAS 状态在 `WumingRegFile` 内**：`ra1`–`ra63` 为 63 槽（`ra63` 是栈顶，`[63:48]` 递归计数、`[47:0]` 返回地址），`RACNT`（6 位）与 `MRPTR`（48 位）是独立寄存器，`ra0` 读出为 `{SBZ, RACNT, MRPTR}`、写入按 `[53:48]`/`[47:0]` 拆分（`[63:54]` 写无效）。压/弹由 `WumingRasOp` 单周期语义完成（PUSH/FOLD/SPILL/POP/DEC/REFILL/CONSUME）。
- **MemRAS**：C3b 把最旧条目写到 `MRPTR-8`（数据端口一次 8 字节 `Put`），D4b 从 `MRPTR` 读一条（一次 `Get`）再按条目递归计数决定 RASUF/consume/refill。两种情况都**先完成全部判定再改 RA 或内存**，中途 `denied`/`corrupt` 或窗口外 ⇒ `CFXMEM` 且 RAS 保持原状（精确异常）。
- **RASOF（`1<<10`）/RASUF（`1<<11`）** 是精确同步异常进 hmon：`call` 的 `cause_info` 是压不进去的返回地址，`ret` 的为 0，`excp_cause_ip` 停在触发指令。

## 位操作 / 原子 / 杂项（`m12-chipyard-010`）

- **位操作**（`spec/SimRISC-04 §1.5/§2.2`、`SimRISC-08/09/10`、`SimRISC-12 §3`）：`rev.o/.t/.w/.b`（块内单元顺序反转，`k` 须 one-hot 且 `k < S`，否则 `encode_onehot` ⇒ ILLI）、`rol.o/.t/.w/.b`（`orrr` 取 `rdHD` 低位 / `orri` 立即数越界 ⇒ ILLI）、`ctpop`/`ctlz`/`cttz`（`immu6` 是有效位上界 `hd`，全 0 时前导/末尾零 = `hd+1`）与 `clmul.o`（GF(2) 64×64→128，结果写 `{rdHA, rdHB}`）。`OPC-tetra/wyde/byte` 子表的 add/sub/cmp/mul/div/rem/shl/shr 一并补齐：窄位宽结果按值语义零/符号扩展，除法定值按宽度（除零 = 宽度掩码 / 全一，有符号溢出 = 宽度 `INT_MIN` 符号扩展），比较结果 −1 写 64 位全一。
- **原子**（`spec/SimRISC-12 §1`）：`lr`/`sc` 全部 24 条形式（`<lr|sc>.<b|w|t|o>.<nn|an|ar|nr>`）。地址 = `rbHD`，数据 = `rdHC`；`sc` 的成败写 `rdHB`（`rdHB = rd0` ⇒ ILLI），`lr` 的 `rdHB` 是 SBZ 字段（非零 ⇒ ILLI）。保留标记的键 = **精确地址 + 访问宽度**；`lr` 另存下读到的 8 字节字，`sc` 命中时重读该字比对，不一致即失败（spec 允许的 spurious failure，与 QEMU `ADR-0034 D6` 的字粒度+值比对一致）。异常进入、`sc` 的成败、另一条 `lr` 都清除标记；只有真正访存时才判 `CFXMEM`，对齐按访存宽度（`MALIGN`）先判。
- **窄 `lr` 高位保持（`m16-chipyard-014`，`spec/SimRISC-12 §1.1` + 用户 2026-11-19 裁定）**：`lr.{t,w,b}`（`.nn`/`.an`/`.ar` 共 9 条）只替换 `rdHC` 的低 32/16/8 位、**高位保持原值**（既不零扩展也不符号扩展）；`lr.o` 仍整 64 位写。写在解包拍的同一拍完成：`r2` 端口读目的寄存器旧值，写回数据 = `(old & ~mask) | (elem & mask)`（`memLdElemNarrow`），不增加状态与拍数；oracle = `idl/SimRISC-12.idl` 对应 9 条 body，与 QEMU `store_rd_narrow`、gem5 `executeLr()` 同式。
- **`swym` / `fence`**：`swym N` 是 1 拍 no-op（时延由实现定义）；`fence cfxHA, immu18` 校验 `immu18[17:12]`（SBZ）与 `cfxha` 是否保留 ⇒ ILLI，合法即 no-op（顺序单周期核天然满足屏障语义，`pred = succ = 0` 合法）。
- **杂项 / 整数补齐**（`spec/SimRISC-02`）：`cs.n/.z/.p`（第一类：**总是**把两个源之一写进目的）与 `cs.eq/.ne`（第二类：条件成立才写）与寄存器块赋值 `rd2rd`/`ra2rd`/`rd2ra`/`rb2rb`/`rd2rb`/`rb2rd`（`immu6` 个连续寄存器，一拍一个，新增 `sCopy` 状态：12 态 → 13 态）；`mreg_zero`/`mreg_range_overflow`/`mreg_range_overlap`/**`mreg_range_addr_overlap`**（`ldm`/`stm` 的地址寄存器落入传送范围；`stm` 允许、RA/RF 不适用）/`dst_rd0`/`dst_rb0` 全部静态判 ILLI。
- **周期（trace 实测）**：`fence`/`swym`/`cs.*` 1 拍；`ctpop`/`ctlz`/`cttz`/`rev`/`rol`/`clmul` 2 拍（R1 = C 的 `SLOW` 路径）；`rd2rd` 8 个寄存器 9 拍（n + 1）；`lr.o.nn` 9 拍、`sc.o.nn` 命中 17 拍（重读 + 写）、未命中 1 拍。

## FP 基础设施（`m12-chipyard-011`）

- **内部表示 = recFN**（`berkeley-hardfloat` 的语义，**不引入其依赖**，代码自写）：`sign ## exp(expWidth+1) ## sig(sigWidth-1)`，比 IEEE 多一位指数 ⇒ 次正规数在内部保持规格化，只有编解码面处理反规格化。`WumingFP.scala` 提供 `recFNFromFN`/`fNFromRecFN`/`rawFloatFromFN`/`rawFloatFromRecFN`（ft = 8/24、fo = 11/53）与 `signInject`。
- **单一舍入原语** `WumingRoundAnyRawFNToRecFN`（`spec/SimRISC-07 §1.4`）：五档方向（RNE/RTZ/RDN/RUP/RNA，编码同 hardfloat 便于逐例对照）+ `immu6` 六档解码（`0x01`/`0x02`/`0x04`/`0x08`/`0x10`/`0x20`，`0x20` 读 `rf0[33:32]`，其余值 ILLI，`ADR-0050` D2）；**tininess 取舍入后**；下溢只在「舍入后 tiny 且 inexact」置 `UF`，与 `NX` 独立；NaN 结果一律 **canonical quiet NaN**（符号 0、payload 全零；`m12-chipyard-030` 收口，此前把输入 payload 传播、窄化还把丢弃位 OR 进末位），sNaN 另置 `NV`。
- **`rf0`（FCSR）**（`spec/SimRISC-00 §2.3.1`）：`WumingFcsr` 保存 `[33:32]` 与 `[4:0]`，其余位读出为固定值（只读 qNaN 位 + SBZ），写入按 `[33:32]`/`[4:0]` 掩码；FP 操作抬起的标志按 `rf0[4:0]` 顺序**累积（sticky）**，软件写 `rf0` 即清零。`rf` 寄存器组（64×64）就位，`rf0` 由 FCSR 承担。**单精写入**（`m13-chipyard-001`）：写口带一位「本次写是 ft 结果」标志，只改 `[31:0]`、`[63:32]` 保持；因此 `ld.t`/`ldm.t` 写 `rf0` 只落到 `[4:0]`（`[33:32]` 舍入模式不动），见下文「单精写入宽度」。
- **分类与符号**：`ftcls`/`focls`（块形式，一拍一个元素，新增 `sCls` 状态：13 → 14 态；`SimRISC-07 §5` 位序 bit0 sNaN … bit9 +Inf，`[63:10]` 清零）；`ftsgnj`/`ftsgnn`/`fosgnj`/`fosgnn`（`copySign`/取反符号，`hd = rf0` 即 `abs`/`-abs`）。
- **rf 寄存器组的形式**：`ld/st/ldm/stm` 的 `rf` 变体（`ld.t rf` 只写低 32 位、高 32 位保持原值——不符号扩展也不零填，`m13-chipyard-001` 前是符号扩展）、`set.w rf`（只替换所选 wyde；`rf0` 上 `wp2` = 舍入模式、`wp0` = 标志、`wp1`/`wp3` 写无效）、`cs.* rf`、`rd2rf`/`rf2rd`（`rf0` 作源或目的均合法，目的侧走 FCSR 掩码；64 位二进制搬移）。其余 FP 形式（算术/转换/取整/最小最大/FMA/除开方）仍 ILLI，归 `012`–`015`。
- **周期（trace 实测）**：`ftcls`/`focls` = 1 + 元素个数；`ftsgnj`/`ftsgnn`/`fosgnj`/`fosgnn`、`set.w rf`、`cs.* rf` 1 拍；`rd2rf`/`rf2rd` = 1 + 个数；`ld.o rf` 13 拍（单拍数据往返）。
- **验证**：`idl/tools/idl_fp.py`（独立模型 + 精确有理数 oracle）、`tools/chipyard/fp_sweep.py`（分类/符号/rf 访存/FCSR/故障 5 组镜像）、`tools/chipyard/fp_unit/`（Verilator 单元台：同一组向量同时喂本实现与 hardfloat 实例，逐例比对值 + 标志）。

## FP 转换族（`m12-chipyard-012`）

- **单元**（`WumingFP.scala`，语义对齐 berkeley-hardfloat 的 `RecFNToIN` / `INToRecFN` / `rawFloatFromIN`，仍未引入其依赖）：`WumingRecFNToIN`（floa→整，`signedOut` 运行时选择，**饱和**而非报错——NaN/Inf/超范围 ⇒ 最大/最小值 + `NV`，`NX` 只用于有限的 inexact 结果）、`WumingINToRecFN`（整→浮，整数幅值规格化后交给**同一个舍入原语**，结构上不会 tiny/overflow ⇒ 只可能 `NX`）、`WumingF2F`（`ft2fo` 精确、`fo2ft` 六档；`fo2ft` 的**溢出按舍入方向**给出结果，见下文「`fo2ft` 溢出按舍入方向」）。三者合成 `WumingFPConvert`，`kind` 选单元、`signedOp` 选有无符号。
- **解码**（`WumingDecoder`）：20 条转换 = 15 条舍入六档（`immu6` one-hot，`0x20` 动态读 `rf0[33:32]`，其他值 ⇒ ILLI）+ 3 条 SBZ（`ft2fo`/`it2fo`/`ut2fo`，非 0 ⇒ ILLI）+ 2 条窗口复制（`ft2ft`/`fo2fo`，复用 `sCopy` 计数形式，`dst_rf0`/`mreg_zero`/两处范围/重叠均 ILLI）。f2i 目的为 `rd`（`dst_rd0`），其余目的为 `rf`（`dst_rf0`）。
- **标志**：`WumingCore` 在 `EXEC` 把转换单元的 5 位标志接到 `rf.io.fflags`，`WumingFcsr` 累积（sticky），软件写 `rf0` 清零 —— **`NV` 的硬件抬升路径自本任务起真实存在**；`DZ` 的通道（舍入原语的 `infiniteExc`）在单元台单独比对，其真实生产者是除法（`m12-chipyard-014`）。
- **周期（trace 实测）**：单寄存器转换 1 拍；`ft2ft`/`fo2fo` = 1 + 个数（与其它块复制一致）。
- **验证**：`idl/tools/idl_fp.py` 的 `f2i_exact`/`i2f_exact`/`f2f_exact`（精确值 + 一次舍入 + 饱和/标志判定，独立于 RTL）、`fp_unit/`（同一组向量喂本实现与 hardfloat `RecFNToIN`/`INToRecFN`，逐例比值与 5 位标志；另含 `infiniteExc`/DZ 通道）、`fp_sweep.py` 的 9 个 `cvt_*` 组（整核上跑并回读 `rf0`）、`inst_case_run.py`（把 `tests/inst/fp/convert.yaml` 驱动到本核，并与 QEMU 同镜像逐字节比对）。
- **与 QEMU 的一处已知差异**：sNaN 作 `ft2fo` 输入时本核（同 hardfloat / gem5）返回**规范 qNaN**，QEMU/softfloat 保留输入的 payload；spec 只要求「返回 qNaN」，故该组不进 QEMU 对照（`cvt_snan`）。

## FP 算术族（`m12-chipyard-013`）

- **单元**（`WumingFP.scala`，语义对齐 berkeley-hardfloat 的 `AddRecFN` / `MulRecFN` / `MulAddRecFN` / `CompareRecFN`，仍未引入其依赖）：`WumingAddRecFN`（加减）、`WumingMulRecFN`（乘）、`WumingMulAddRecFN`（融合乘加）、`WumingCompareRecFN`（quiet/signaling 比较）、`WumingMinMax`（最小最大），由 `WumingFPArith` 按 `kind`+`isFo` 选出。三种舍入运算都先把精确结果做成**定点整数**，再经**同一个**舍入原语 `WumingRoundAnyRawFNToRecFN` 一次舍入：加/减在对齐窗口（大于数精确、小数只丢到 sticky 位）内求和取 floor + sticky；乘法用 `2*sigWidth` 位精确积；FMA 用 `2*sigWidth+guard` 位窗口把精确积与加数对齐到同一刻度求和 —— 因此**只在最后舍入一次**（`spec/SimRISC-07 §2.5`），与「先乘后加」不同（`tests/inst/fp/arith.yaml` 用 spec 的 ft 反例与其 fo 类比各留一例对照）。
- **NaN 口径**：所有族的 NaN 结果都是 **canonical quiet NaN**（符号 0、payload 全零，`SimRISC-07 §1.4`；`m12-chipyard-030` 起加/减/乘/除也不再传播 qNaN payload），sNaN 或无效运算（`0×Inf`、`Inf+(−Inf)`）⇒ `NV` + canonical qNaN；FMA 的 NaN 结果按 `§2.5` **恒为 canonical qNaN**（与 QEMU 的 default-NaN 模式一致），**NaN 乘数即使另一因子是 Inf 也使积为 NaN**（Inf 规则的前提是「Inf × 有限非零数」），故 `qNaN×Inf+(−Inf)` 不置 `NV`。比较：无序 ⇒ **四种比较一律返回 canonical quiet NaN**（`m16-chipyard-012`，`spec/SimRISC-07 §4`；此前 signaling 形式返回 sNaN）；`NV` 按 IEEE 754-2019 §5.6.1 / §5.11 只由 signaling 形式对任何无序置、quiet 形式仅含 sNaN 时置（`m12-chipyard-024`；QEMU 同口径）。最小最大：单 NaN 返回那个数、双 NaN 返回 canonical qNaN、`−0 < +0`、sNaN 输入 ⇒ `NV`、不涉舍入（`§2.4`）。
- **解码**（`WumingDecoder`）：`orrr` 的 `ftadd/ftsub/ftmul`、`foadd/fosub/fomul`、`ftmin/ftmax/fomin/fomax`、`ftqcmp/ftscmp/foqcmp/foscmp`（目的 `rf0`/`rd0` ⇒ ILLI），以及 `rrrr` 单目的 `ftfma/fofma`（`opc 0x5E/0x5F`，`rfHA` 目的、三个源可与其重叠）。舍入方向恒取 `rf0[33:32]`。
- **标志**：`WumingCore` 把算术单元的 5 位标志接到 `rf.io.fflags` —— **`OF`/`UF`/`NX` 首次由算术指令抬起**（`NV` 的算术路径随 sNaN/无效运算一并到位），sticky 累积与软件清零沿用 `WumingFcsr`。
- **周期（trace 实测）**：`foadd`/`fomul`/`fofma`/`foqcmp`/`fomin`/`fomax` 各 **1 拍**。
- **验证**：`fp_unit/` 把同一组向量同时喂本实现与 hardfloat 的 `AddRecFN`/`MulRecFN`/`MulAddRecFN`/`CompareRecFN`（值 + 5 位标志逐例比对；hardfloat 的 signaling 比较对无序给 sNaN，`m16-chipyard-012` 起本核给 canonical quiet NaN，故比较的**值**按 `lt/eq/gt` + canonical 常数比对照、**标志**严格比）并比对 `idl_fp` 的精确 oracle（加/乘/FMA 用**精确整数尾数 + 指数**、比较/最小最大用单调键）；`fp_sweep.py` 的 12 个 `arith_*` 组（含 FMA 特殊值组）+ `cmp_nan` 组在整核上跑并回读 `rf0`，同一镜像在 QEMU 上逐字节比对（仅 `arith_nan` 因 sNaN payload 口径为模型only）；`tests/inst/fp/arith.yaml` 28 例（含 3 条 ILLI）在本核与 QEMU 上逐字节一致。

## FP 除法 / 开方 / 取余（`m12-chipyard-014`）

- **单元**（`WumingFP.scala`）：`WumingDivSqrtRecFN`（除法与开方共用一个数字迭代状态机，`start` 一个脉冲开始、`done` 一个脉冲结束）、`WumingRemRecFN`（IEEE 754 remainder），由 `WumingFpSlow` 按 `kind`+`isFo` 选出（`DIV`/`SQRT`/`REM`）。六个实例（每格式每操作一个）**只有被选中的那个被 `start`**，否则另一格式的长循环会让本格式的下一条指令静默丢掉。
- **算法**：除法把商的**精确截断** `Q = floor(|a|/|b| · 2^N)`（`N = sigWidth+2`）与「被截掉的那部分是否非零」一起交给同一舍入原语 —— 前者是 round 位以上的真数字、后者是 sticky，因此仍然只舍入一次；先取掉 `ma >= mb` 的整数商位（比值的整数部分只可能是 0/1），剩下 `< |b|` 的余数才开始移位。开方逐位做 restoring 开方（每位消耗两个基数位），radicand 按 `sigWidth+2+p` 移位、`p` 取使 `(ea−sigWidth−2−p)` 为偶数的奇偶位，`rem != 0` 即无理尾。取余是 restoring 长除：`rem = |a| mod |b|` 出来后只要「`2·rem` 与 `|b|` 比大小 + 商的奇偶」就能定就近取偶；**结果精确，不置 `NX`/`OF`/`UF`**。`d = ea − eb < 0` 时 `|a/b| < 2`，商只可能是 0 或 1（`d = −1` 时比较 `ma > mb`），**不进循环**。
- **特殊值**：`0/0`、`Inf/Inf`、`sqrt(负数)` ⇒ canonical qNaN + `NV`；**有限非零被除数 / ±0 ⇒ ±Inf + `DZ`**（`infiniteExc` 单独给 `DZ`，且该路径 `sExp=0` 时指数已由 `infiniteExc || in.isInf` 钉到 Inf；不置 `DZ` 的 ±Inf 结果（无穷被除数、`sqrt(+Inf)`）由 `rounder.in.isInf` 给 —— 两者各管一类形状，hardfloat 同法）—— 这是本族成为 `DZ` 首个**端到端**生产者；`Inf/0` 与 `NaN/0` 都不置 `DZ`；NaN 结果一律 canonical quiet NaN（`m12-chipyard-030` 起不再传播 qNaN payload，含除法/开方/取余），sNaN ⇒ canonical qNaN + `NV`；`forem` 的三个边界（`rfHC` 为 ±Inf、`rfHD` 为 ±0、sNaN）⇒ `NV` + qNaN，`rfHD` 为 ±Inf 或 `rfHC` 为 ±0 ⇒ 原样返回被除数；`rootn(±0, 2) = +0`（`SimRISC-07 §2.2` = IEEE 754-2019 §9.2.1），`−0` 源的开方结果符号被清 0、不置标志（与 hardfloat `squareRoot(−0) = −0` 是本任务唯一有意的值差异）。
- **解码**（`WumingDecoder`）：`orrr` 的 `ftdiv/ftrem/fodiv/forem`、`orri` 的 `ftroot/foroot`（`immu6` = n，**仅 n = 2**，其他 ⇒ ILLI）；六条都禁止 `rf0` 作目的（ILLI）。
- **核**（`WumingCore`）：新增第 14 个状态 `sFpSlow`；`EXEC` 一拍发 `start`、`sFpSlow` 等 `done`，`done` 那一拍写回 `rf` 并把 5 位标志送 `rf.io.fflags`（`nv`/`dz`/`of`/`uf`/`nx` 都由此族在指令级到达）。
- **周期（trace 实测）**：fo 的 `fodiv`/`foroot` **56 拍** = `sigWidth + 3`，与操作数无关（4 组除法 + 3 组开方逐例相同；ft 为 27）；`forem` = `sigWidth + (ea − eb) + 1` 拍（`ea − eb` = 1/10/100/1000 时实测 55/64/154/1054；余数提前为 0 时早退，但那是精确整除路径）。单元台自测的 tick 数同量级（div ft 26 / fo 55、rem 最长 1866）。
- **验证**：`fp_unit/` 把 div/sqrt 的三方对照（本实现 / hardfloat `DivSqrtRecFN_small` / `idl_fp` 精确 oracle）跑满（值 + 标志），`forem` 只有 oracle（hardfloat 无 remainder 模块）；`fp_sweep.py` 增 `div_ft/div_fo/sqrt_ft/sqrt_fo/rem_ft/rem_fo/divrem_special` 七组（均入 QEMU 三方对照）+ `divrem_nan` 组（模型only）+ 10 条合法性镜像；`tests/inst/fp/divrem.yaml` 32 例（26 语义 + 6 ILLI）在本核与 QEMU 上逐字节一致（sNaN payload 一例模型only）。

## `fo2ft` 溢出按舍入方向（`m12-chipyard-025` / `m12-chipyard-026`）

- **条款**（`spec/SimRISC-07 §1.4` = IEEE 754-2019 §7.4）：溢出 = **以无限指数范围**按所选方向舍入后的幅值大于 `ft_max = (2 − 2^−23) × 2^127`；结果形态由方向决定 —— RNE/RNA、正向 RUP、负向 RDN ⇒ `±Inf`，其余三格（RTZ 双向、正向 RDN、负向 RUP）⇒ `±ft_max`；两种情况都置 `OF|NX`。**因此「结果变成 Inf」与「溢出」不等价**：轻微溢出（`ft_max` 之上、`2^128` 中点之下）在把幅值舍下来的方向上只置 `NX`、不置 `OF`。
- **RTL**（`WumingF2F` → 舍入原语 `WumingRoundAnyRawFNToRecFN`）：`common_overflow = sRoundedExp >> (outExpWidth − 1) >= 3`（进位后的无界指数），`val pegMaxFiniteMagOut = overflow && !overflow_roundMagUp` 把方向决定落到「Inf 还是最大有限幅值」；旧的 `forceInfOnOverflow` 覆写已删除。
- **模型**（`idl/tools/idl_fp.py`）：`round_dyadic`/`_round_mag` 就是该条款的唯一实现，`f2f_exact` 不再有「恒 ±Inf」覆写参数（`m12-chipyard-026` 补回）。
- **向量**：单元台 `f2f fo2ft ovf` 40 例 = 8 形状（最大 double / 中点上方 1 ulp / 中点 tie / 恰为 `ft_max`，各双符号）× 5 档，期望值是从条款**逐格抄写**的常量表（不取自 oracle），与 RTL、hardfloat 三方对照；核上 `fp_sweep.py` 的 `cvt_ff_ovf` 38 例（severe 10 + mild 10 + 中点 10 + 动态 `0x20` 四码双向 8）逐例比 `rd` 与 `rf0`。
- **验证**：`make_patch chipyard` 从源树重导补丁（`m12-chipyard-026`，此前只合入了任务书 ⇒ 仓库补丁仍是旧行为，`ISS-405`）；`make check-patch-tree` / `check-source-state` / `apply-series` 幂等、L2 全绿。

## 融合乘加溢出按舍入方向（`m12-chipyard-029`）

- **条款**（`spec/SimRISC-07 §2.5` = IEEE 754-2019 §7.4，`m13-spec-006` 定稿）：溢出 = 以**无限指数范围**按 `rf0[33:32]` 所选方向舍入后的**精确和**幅值大于该格式最大有限值（`ft_max = (2 − 2^−23) × 2^127`、`fo_max = (2 − 2^−52) × 2^1023`）。形态由「精确和的符号 × 方向」共同决定 —— RNE、正向 RUP、负向 RDN ⇒ `±Inf`；RTZ 双向、正向 RDN、负向 RUP ⇒ `±max`；两种情况都置 `OF|NX`。轻微溢出（方向把幅值舍回 `max`）**不是溢出**，给 `±max` 且**只置 `NX`**；RNE 分界为 `max + ulp/2`（ft `2^103`、fo `2^970`）。融加族无 RNA 档。
- **RTL**（`WumingMulAddRecFN` → 舍入原语 `WumingRoundAnyRawFNToRecFN`）：精确积与加数在同一 `2*sigWidth+guard` 位窗口内求和后**一次**舍入，溢出由原语的 `common_overflow = sRoundedExp >> (outExpWidth − 1) >= 3`（进位后）与 `pegMaxFiniteMagOut = overflow && !overflow_roundMagUp` 决定 —— **RTL 不另设 Inf 覆写**（`fo2ft` 那套 `forceInfOnOverflow` 从未出现在本族），因此本任务**无需改行为**；实测 96 格（两格式 × 12 形状 × 双符号 × 四档）与条款逐格一致。模块注释已写明该条款并禁止再加 Inf 覆写（防回退）。
- **模型**（`idl/tools/idl_fp.py`）：`fma_exact` 走 `round_dyadic`/`_round_mag` 的同一套方向规则（无「恒 ±Inf」分支），`fma_exact` 文档注明轻微溢出只置 `NX`。
- **向量**：单元台新增 `fma ovf` 96 例 = 12 形状（最大乘 2 的严重溢出、`max` 上方 1/4 ulp 的轻微溢出、RNE 中点上下、恰为 `max`、精确 `2^128`/`2^1024`；各双符号）× 四档，期望值从条款**逐格抄写**成常量表（不取自 oracle），与 RTL、hardfloat、`idl_fp` 四方对照；核上 `fp_sweep.py` 的 `arith_fma_ft`/`arith_fma_fo` 各增 12 个溢出三元组（同形状、四档 × 双符号），逐例比 `rd` 与 `rf0`（各 92 例）。
- **验证**：单元台 `fma ovf` table/hf-value/hf-flag/oracle 四差 0；核上 `arith_fma_ft`/`arith_fma_fo` 逐字节一致；注入「溢出恒 ±Inf」与「轻微溢出也置 `OF`」两路 ⇒ 对应格红、模型注入 ⇒ oracle 红。

## 结果 NaN 统一 canonical 与 `rootn(±0,2)=+0`（`m12-chipyard-030`）

- **条款**（`spec/SimRISC-07 §1.4` / §2.2，用户 2026-11-13 裁定 R1/R2）：凡结果应为 quiet NaN 的情形一律 **canonical quiet NaN** —— 符号位 0、payload 全零（ft `0x7FC0_0000`、fo `0x7FF8_0000_0000_0000`）；`rootn(±0, 2)` 收严为 IEEE **`+0`**（§9.2.1 的 NOTE 明确它与 `squareRoot(−0) = −0` 不同）。IEEE §6.2.3 的 payload 传播只是 *should*、§6.3 不规定结果符号 ⇒ canonical 是允许的实现选择，不是偏离。
- **RTL**（`WumingFP.scala`）：舍入原语 `WumingRoundAnyRawFNToRecFN` 的 NaN 尾数只置 quiet 位（删掉 payload 计算）；`WumingAddRecFN`/`WumingMulRecFN`/`WumingRemRecFN`/`WumingDivSqrtRecFN` 不再向原语注入首 NaN 的 payload（`nanSrc`/`nanSig`/`nanSigZ` 全删）；`WumingDivSqrtRecFN` 的 root 零结果 `sign = rawA.sign && !rawA.isZero`。**不适用**（保持原状）：`ft2ft`/`fo2fo` 复制、min/max 单 NaN 返回数。比较的 signaling 形式当时仍是 sNaN 位型，`m16-chipyard-012` 起也改为 canonical quiet NaN（`spec/SimRISC-07 §4`）。
- **模型**（`idl/tools/idl_fp.py`）：`round_bits` 的 `nan_fract = quiet_bit`、`round_exact` 的 NaN 分支取 `_canon_qnan`、`add/mul/div/rem/sqrt_exact` 的 qNaN 分支取 canonical、`sqrt_exact` 的零分支返回 `+0`；自检 `selfcheck` 增「NaN 编码就是 canonical」的位级断言。
- **验证**：单元台新增 `spec points` 20 例（期望值**逐条从条款抄写**、不取自 oracle）：root ±0（四档方向）、root(负数) ⇒ canonical + `NV`、`ftadd(0x7FC1_2345,1.0)=0x7FC0_0000`、fo 侧带 payload 且负号 qNaN 的 `foadd`、`fo2ft(0xFFF8_0000_0000_0123)=0x7FC0_0000`、`ft2fo(qNaN payload)`、`foscmp(qNaN,1.0)=canonical`+`NV`（`m16-chipyard-012` 起；此前为 sNaN）、`foqcmp` 无序 canonical、min 单 NaN 返回数/双 NaN canonical；核上 `fp_sweep.py` 新增 `cvt_nan` 组 18 例并扩 `arith_nan`（ft+负号 qNaN）与 `divrem_nan`（root ±0 四档 × 双格式 × 双符号、qNaN payload 各类）。

## 边界
- **保留** rocket-chip 库（Diplomacy / TileLink / `BaseTile`）与 chipyard 仿真设施（Verilator harness / BootROM / 内存模型 / `loadmem`）。
- **抛开** Rocket 核与 RISC-V 语义（CSR / misa / PMP / MMU / TLB / 异常码）；`WumingCoreParams` 不继承 `CoreParams`。

## 校验

```
make apply-series
make check-source-state
make check-patch-tree
```

## FP 取整 / 缩放 / 符号（`m12-chipyard-015`）

- **单元**（`WumingFP.scala`）：`WumingFpRound`（`roundToIntegral`，`spec/SimRISC-07 §2.3` / IEEE 754-2019 §5.3.1）与 `WumingFpScale`（`scaleB`，`§2.1` / IEEE 754-2019 §9.2），由 `WumingFpMisc` 按 `op`+`isFo` 选出，单拍完成。
- **取整**：值 `sig * 2^qExp`；`qExp >= 0`（对 p 位有效数即 `|x| >= 2^p`）原样返回，否则用 `WumingFPAlu.place` 把 `2|x|` 截到整数刻度，得整数部分 + round 位 + sticky 位，按六档方向决定是否加一，再把整数精确编码回原格式（`±0` 保留输入符号）。`immu6` 是六档 one-hot（`0x01` RNE / `0x02` RNA / `0x04` RTZ / `0x08` RUP / `0x10` RDN / `0x20` 读 `rf0[33:32]`），只有 `0x20` 且结果 ≠ 输入才置 `NX`；NaN 一律 canonical qNaN（sNaN 另置 `NV`）；不置 `OF`/`UF`/`DZ`。
- **缩放**：只把 recoded 指数加上 `rd` 组的有符号 64 位整数 `n`（饱和到远超出可表示范围的两端，故不会改变结果），有效数与其余字段原样交给**同一个**舍入原语 `WumingRoundAnyRawFNToRecFN` ⇒ 全程只舍入一次（这正是 `scaleB` 与「乘一个 2 的幂」的区别：后者在 `2^n` 不可表示时会二次舍入）。`OF`/`UF`/`NX` 是原语的 IEEE 判据；`rd0` 读作零 ⇒ 指数 0；sNaN 置 `NV`（结果 payload 归一，softfloat/QEMU 保留 quieted payload，属已声明差异）。
- **符号**：`ftsgnj/j`、`fosgnj/j`（`§3`）沿用 `m12-011` 的 ALU 位操作路径（`WumingRecFN.signInject`），纯位操作、**不置任何标志**（含 sNaN 输入），`tests/inst/fp/sign.yaml` 逐例用 `rf2rd rd6, rf0` 断言 `rf0` 不动。
- **验证**：单元台 op 47–50（`rnd` 对精确 oracle 且断言静态档不受 `rf0[33:32]` 影响；`sclb` 在 `2^n` 可表示范围内对 hardfloat `MulRecFN` 值/标志全等，全程对 oracle）；核上 sweep（`fp_sweep.py` 的 `rnd_*` / `sclb_*` / `sign_flags`）与同镜像 QEMU 逐字节一致；`tests/inst/fp/roundint.yaml`、`sign.yaml` 经 `make check-inst` 门控（QEMU）。

## 单精写入宽度（`m13-chipyard-001`）

- **条款**（`spec/SimRISC-01 §4` 注、`spec/SimRISC-07 §1.3`「单精（ft）结果的写入宽度」、`contract-fp §1`；用户 2026-11-14 裁定）：**凡以 ft 寄存器为目的的指令只写低 32 位、`[63:32]` 保持原值**（不符号扩展、不零填）——`ld.t`/`ldm.t`、算术/取余/开方/取整/缩放/最小最大/转换到 ft、符号注入以及 **`ft2ft`** 复制；**不适用**：`fo2fo`、跨组复制 `rd2rf`/`rf2rd`、`ld.o`/`ldm.o`（64 位二进制搬移）。写 `rf0` 时低 32 位里只有 `[4:0]` 在可写域 ⇒ `[33:32]`（舍入模式）、`[31:22]`（只读 qNaN）与 `[21:5]`（SBZ）全部保持原值。
- **实现**：`WumingRegFile` 的 w0 写口新增 `w0Ft`：`sf(idx) := Cat(sf(idx)(63,32), data(31,0))`；`rf0` 侧 `WumingFcsr` 新 `writeFlagsOnly` 只更新 `[4:0]`（舍入模式不动）。`WumingDecoder` 逐族置 `w0Ft`：`ld.t`/`ldm.t`（RF 寄存器组的 tetra 装载，且 `memSigned` 改 false ⇒ 不再符号扩展）、`fpArith`/`fpFma`/`fpSlow`/`fpRoundInt`/`fpScaleB`/`signInject`/`cvtI2F` 的 ft 变体、`cvtF2F` 的 `fo2ft`、`fpCopy(false)`（`ft2ft`）；`fo2fo` 走 `fpCopy(true)` 保持 64 位。`ft2fo`（fo 结果）、`rd2rf`/`rf2rd`、`ld.o`/`ldm.o` 不置该位。
- **验证**（`fp_sweep.py` 新增 `ftwidth` 组 29 例，期望值按条款手写、每例先把目的高半填非零图案）：`ld.t rf0 ← 0xFFFF_FFFF ⇒ 0x7FF8_0000_7FC0_001F`；`ld.t rf5 ← 0xFFFF_FFFF/0x7FFF_FFFF/0` 高半保持；`ldm.t {rf0:rf1}`；`ftadd/ftsub/ftmul/ftfma/ftdiv/ftrem/ftroot/ftrnd/ftsclb/ftmin/ftmax/it2ft/ut2ft/io2ft/fo2ft/ftsgnj/ftsgnn` 各一例；`ft2ft` 单例与三元素块复制；反向对照 `ld.o`/`ldm.o`/`fo2fo`/`rd2rf`/`rf2rd` 仍 64 位。旧实现的同一镜像 24/29 例红（5 个反向对照绿），新实现 29/29 逐字节；四册 `tests/inst` 与 `fp_unit` 全绿。

## cfx 独立为 `dadao-gewu` generator（`m16-chipyard-002`）

- **形态**（`ADR-0053 D1/D2`）：cfx（机器级控制面：寄存器堆 + 判权 + 异常帧 + 向量 + `escape`/`power`/`hmon`）不再内联在 `WumingCore.scala`（原 152 行 cfx 相关代码、9 组寄存器），改为 in-tree generator `generators/dadao-gewu/`（sbt 项目名 `gewu`、包 `gewu`、`src/main/scala/gewu/GewuFile.scala` 含 `GewuFileIO` + `GewuFile extends Module`），根 `build.sbt` 三处接线：`lazy val gewu = freshProject("gewu", …).dependsOn(rocketchip)`、`baseProjects` 加入 `gewu`、`wuming` 改为 `.dependsOn(rocketchip, gewu)`。**依赖单向**：`generators/dadao-gewu/` 内 `wuming` 出现 0 次（静态 grep），后续核只需 `dependsOn(gewu)` 并接端口。
- **IO 契约**（`D3`，`GewuFileIO` 19 个字段）：cfx 读/写（`cfxha`/`cg`/`rc` 地址、`wdata`/`wEn`、`rdata`、`readOk`/`writeOk`）、异常入口（`excp.cause`/`causeIp`/`info`）、`escape`（`ha`/`off` → `escapeOk`）、重定向请求（`redirect.valid`/`target`/`cause`/`causeIp`/`info`/`isEscape`）、以及核侧要用的状态输出（`monitorHa`/`vector`/`frameValid`/`causeId`/`causeIp`/`causeInfo`/`prevMode`/`runMode`/`intrMask`）。输入**只接架构级事件**（「这条 cfx 写提交」「进入这条异常」「这条 `escape` 返回」），不接流水内部信号。
- **重定向归核**（`D4`）：`Gewu` 只出 `redirectReq`/`redirectTarget`，`ip`/flush 仍由 `WumingCore` 驱动；异常入口的落点是 `Gewu` 的 `vector` 寄存器输出（`enterHmon` 用 `ip := gewu.io.vector`），`escape` 提交走 `finish(gewu.io.redirect.target)`。两者不共用同一个 mux 选择信号：若入口落点也走「按 `escapeOk` 选目标」的 `redirect.target`，`escape` 目标 IALIGN 失败时同一拍会跳错地址并让 `finish` 的取值与 `excp` 事件形成组合环。
- **参数化**（`D5`）：新增 `GewuParams`（cfx 描述序列、帧归属 `monitor`、`dataBits`/`modeBits`/`sourceMaskBits`、`runModeReset`/`hypvMode`/`switchModeValue`），由 `WumingGewuParams` 从地址图注入；`gewu` 源码内**无**机器常量（无 `Seq.fill(`、无 mask 字面量、无 `cfx_hmon`/`cfx_power`/地址基址）。实现集与帧数即 `cfx` 序列长度。
- **术语**（`D6`）：模块/文件 `Gewu`，**寄存器名保持 `cfx_*`**（`spec/Kaiwu §3`、`ADR-0046`）；`GewuFile.scala` 文件头写明「Gewu ≡ cfx 寄存器堆（类比 Rocket `CSRFile`）」；`spec/` 不改名。**范围**（`D7`）：`WumingDecoder.scala` 的 cfx 指令类解码（35 行 / 42 处 `cfx`）留在核内，作为 `Gewu` 的输入信号。
- **sim**：新 md5 `bd5e75b3a64044b4cb69d20c298f080d`（`make verilog CONFIG=WumingTinyConfig -j32` + `make CONFIG=WumingTinyConfig -j32`，`JOBS=32`，两次独立重建字节相同；旧基线 `4e072a71…` 作废）。
- **验证**：改前/改后两版二进制跑同一批 **37** 个镜像（首轮 5 个 id / 29 镜像，补入 `cfx2rd_crrr_cfx` 后为 6 个 id / 37 镜像：`trap_ciii_cfx`/`escape_ciii_cfx`/`cfx2rc_crrr_cfx`/`cfx2rd_crrr_cfx`/`fodiv_orrr_rf`/`add.so_rrrr_rd`，链例 + 故障例）⇒ `semi.out` 逐字节、退出码、每一条 `cycle=` 值 **全部相同**；注入 5 路（`cfxVector` 写回 +4、`escape` 去掉当前-cfx 判据、`GewuParams` 帧归属/运行模式复位值、`redirectTarget` 接 0）均为真实重编后观测到的红，`cp`+md5 还原并重建后逐字节回绿；`escape` 的「帧有效」判据在本 profile 不可观测（帧无清零路径，`tests/inst/11-cfx/escape_ciii_cfx.S` 自记 GAP ③）。

## 寄存器复制 `rf2rf` 取代 `ft2ft`/`fo2fo`（`m13-chipyard-003`）

- **条款**（`spec/SimRISC-02 §1` + `contracts/opcodes.yaml::rf2rf_orri_rf`，`m13-spec-010`）：`rf2rf {rfHB:rfHB+immu6-1}, {rfHC:rfHC+immu6-1}` 是 `orri`/`rf`、`opc = 0x40`（OPC-octa）、`ha = 111-100`；**整 64 位逐位复制**（不换算、不舍入、不置标志），源 `rf0` 读出完整 64 位。ILLI（**在处理任何元素之前判定**、目的寄存器未被修改）：`immu6 = 0`（`mreg_zero`）、目的或源 `起始 + immu6 > 64`（`mreg_range_overflow`）、源/目的**任何**交集含完全重合（`mreg_range_overlap`）、**目的范围含 `rf0`**（`dst_rf0`）。同组复制 ⇒ 最多 31 个元素。
- **实现**：`WumingDecoder.blockCopy` 增 `forbidRf0Dst` 参数 —— 目的窗口自 `hb` 升序 ⇒ 含 `rf0` 当且仅当 `hb == 0`，故该规则就是对 `hb === 0` 的 ILLI；`0x40/0x3C` 用 `blockCopy(WumingBank.RF, WumingBank.RF, forbidRf0Dst = true)`。`rd2rf`/`rf2rd` 不变（`rf0` 可作目的，写入走 FCSR 掩码）。执行沿用 `sCopy`：每拍读源（r0 口）写目的（w0 口），`w0Ft` 不置 ⇒ `sf(idx) := data` 整 64 位落盘，六类非法在 `EXEC` 的 `execFault`（`d.ill`）里先于 `sCopy` 生效 ⇒ 精确、不部分生效。
- **删两条旧译码**：`0x44/0x02`（`ft2ft`）与 `0x44/0x0A`（`fo2fo`）回到空置槽位 ⇒ **UNDI（`0xF9`）**，与 QEMU（`insn.decode` 空白单元格 ⇒ UNDI）和 gem5（`FaultUNDI`）同口径；子表位图同步为 `octaRows[7] = 0x7F`（本行 7 格已定义，`0x40/0x3F` 仍空置）、`rfRows = 0x4B, 0x4B, 0x7F, …`（前两行去掉 000-010 / 001-010）。
- **sim**：新 md5 `4e072a711afdca8a36788f9a9958e896`（`make verilog CONFIG=WumingTinyConfig` 67 s + Verilator 增量重编 44 s，`JOBS=32`，旧基线 `079ae015…` 作废）。
- **验证**：`tests/inst/02-reg-copy/rf2rf_orri_rf.S` 三平台 7/7 镜像（链例 11 点 / 88 B 三方 rc=0 且字节流逐字节相同；6 个故障例三方 rc=`0xF8`）；chipyard 侧 n=3 探针（三元素逐位 + 源不变）三方 48 B 全等；退役编码探针 `0x44080000`/`0x44280000` 三方 rc=`0xF9`；注入 3 路（放行目的 `rf0` ⇒ 点 12 红；重叠放宽为「仅完全重合」⇒ 点 16 红；`0x02` 单元重新译码 ⇒ 退役编码探针红）均真实重编后观测、`cp`+md5 还原后回绿。

## 测试机整机名 `Kaiwu`（`m14-infra-004`）

- **补丁**：13 份随全仓改名机械替换（`Kaiwu`/`Kaiwu-Tiny`/`Kaiwu-Vast`、`spec/Kaiwu §…` 注记；`DadaoConfigs.scala` 的两处 SRAM 名 `kaiwu-tiny-sram`/`kaiwu-tiny-hmon-sram`）——**语义、几何、编码零改动**；`dadao-wuming`/`dadao-gewu` generator 名与类名不变。
- **sim 重建（必须）**：SRAM 名进 elaboration ⇒ 生成物变了，旧二进制不对应当前补丁态。`make verilog CONFIG=WumingTinyConfig -j32` + `make CONFIG=WumingTinyConfig -j32` ⇒ 新 md5 **`71574df4dbd0033b6c0a7b133239b95a`**（旧 `bd5e75b3…` 作废）。
- **构建环境坑**：必须在 chipyard 自带 conda 环境里构建（`PATH` 前置 conda `bin`、`RISCV=<conda>/riscv-tools`）——系统 JDK 21 下 sbt 1.8.2 报 `bad constant pool index`、`RISCV` 未设时生成物含 `-I/include` 且缺 `fesvr/*.h`。
- **验证**：`trap_ciii_cfx`/`escape_ciii_cfx` 2 个 id / 16 个镜像（链例 + 故障例）chipyard ↔ QEMU **逐字节相同**（`semi.out` + 退出码），新 sim 语义与改前一致。

## `excp_cause_id` 子原因 wyde（`m16-chipyard-003`）

- **编码**（`ADR-0056` D1–D4，`contract-see §6.1.1` = `DADAO-12 §3.6`）：`[15:0]` 大类 one-hot、`[31:16]` 留给未来大类的保留段、子原因放进**该 cause 独占的 16 位 wyde** —— `CFXPERM` → wyde2 `[47:32]`（低字节 8 位权限类，`[47:40]` 保留）、`CFXMEM` → wyde3 `[63:48]`（低字节 8 位缺失类、`[56] ADWBFAIL`、`[57] NONPTW`、`[63:58]` 保留）。wyde 归属互斥：另一 wyde 与非 `CFXMEM`/`CFXPERM` 的 cause 的两个 wyde **必须全 0**。
- **单一真源 = `gewu` 生成器**：`GewuCauseId` 持有 18 位表（wyde2 8 + wyde3 10，含 `encode`（按 cause 选 wyde）与 `wellFormed`（结构判据））。核只传 **wyde-local 位号**，因此子原因**不可能被手放到错的 wyde**；`WumingCore.CFXMEM_BIT`/`CFXPERM_BIT` 也引用该表，不再各写一份字面量。
- **写帧点校验（具名失败）**：`GewuFile` 是 `cg5 rc2` 的唯一写点；`excp.valid` 那拍调 `wellFormed`，违规由 `chisel3.assert` 具名致命（RTL 为 `$error("Assertion failed: GewuFile: malformed excp_cause_id 0x…")` + `$fatal`，仿真 rc=255）。漏填子原因、子原因放错 wyde、wyde 内两位、保留位被占都会**当场停仿真**，不会静默写进帧。
- **本 profile 的可达面**：`WumingTinyConfig` 无 MMU/TLB/PTBR（`WumingParams` 无 PTW 字段、核无 `cfx_ptw` 访问）⇒ `ptw_enable = 0` 恒成立 ⇒ **每一处 `CFXMEM` 都是 `[57] NONPTW`**（`enterHmonMem` 的默认，8 个判定点：取指窗口两处、`call` spill 目标、`ret` refill 目标、`lr`/`sc`、`ld`/`ldm` 预检、中途 `denied`/`corrupt`）。页表缺失 8 类与 `[56] ADWBFAIL` 在此 profile **结构性不可达**，也不发 `CFXPERM`（无来源掩码判权）⇒ 这些位需等 TLB 实现另立任务；表与校验器已就位，届时只需在判定点传对应位号。
- **`cause_info` 语义不变（D4）**：`CFXMEM` 恒为地址（中途失败用**该 beat 的地址**`memBeat`；`beatOf` 已按 8 B 对齐），`MALIGN` 为访存地址，`IALIGN` 为非法 IP，其余大类保持各自的指令编码语义。
- **sim 重建**：`make verilog CONFIG=WumingTinyConfig -j32` + `make CONFIG=WumingTinyConfig -j32`（`JOBS=32`，约 5 min）⇒ 交付二进制 md5 **`2fb79602f30916c363ecff17eb3c33c8`**（旧 `71574df4…` 作废）。**注意**：同一源码的 `make clean-sim` + 重建可产出不同字节（本次观测到 `e7234109…` 与 `2fb79602…`，同 RTL、同链接库、**行为逐字节相同**）⇒ `sim md5` 只作记录，身份判据取**行为**（`ISS-453`）。
- **验证载体**：`tools/chipyard/excp/causeid.S`（8 类异常各一例：数据/取指 `CFXMEM`、`ILLI`、`UNDI`、`MALIGN`、`CFXREG`、`CFXTRAP`、`IALIGN`；用 `aip.si` 现场写固件 hmon 的返回槽 `+0xF8`，回落点读 `+0xE0`/`+0xF0` 各记 8 B）+ `check_causeid.py`（**现场从合约解析位号**并与 `spec §3.6` 逐位互校；断言全 64 位相等、`[31:16]` 保留、非 `CFXMEM` 两 wyde 全 0、`cause_info` 恒为地址）。同一 ELF 在 chipyard / QEMU / gem5 上 **128 B 字节流逐字节相同**（`CFXMEM` ⇒ `0x0200000000000002`）。
- **既有工具的已知问题（非本任务引入）**：`tools/chipyard/excp/app.S`（`m12-chipyard-019`）在**改前基线**就失败（`rc=69`）：它按旧固件「`escape` 恒回 `trap+4`」写，而 `m12-chipyard-028` 起固件从 hmon `+0xF8` 取返回地址、`app.S` 从不写该槽 ⇒ 第一个异常就跳回 BootROM 并重启程序；另有 `cg3 rc0–rc3` 在 `GewuFile` 里被并成一份 mask（`DADAO-12 §3.1` 是四个独立 mask）导致读回互相污染。两处均与本任务无关，待各自任务修。

## `escape` 恢复 `inner_cfx_code`（`m16-chipyard-005`）

- **条款**（`spec/DADAO-12 §3.6` + `§5.2` 步骤 5–6 + `§5.3` 步骤 0–2，`m14-spec-009` 起）：`cg5 rc1` = `cfx_⟨cfxname⟩_excp_prev_cfx_code`（RW，初值 0）；异常进入时**在改写 `inner_cfx_code` 之前**保存它；`escape` 步骤 0 通过（`cfxha == inner_cfx_code` 且当前 cfx 的帧有效）后按步骤 2 恢复 `inner_cfx_code ← excp_prev_cfx_code`；`CFXESC`（帧/目标错误）**交给当前 cfx**，不属 monitor 路由。
- **核实结论 = 部分实现**（改动前）：`GewuFile.scala` 的 cg5 只有 `rc0`（`prevMode`，`isPrevMode` 判据），`cg5 rc1` 落到 CFXREG；**没有 `inner_cfx_code` 状态**——`escapeOk` 恒以 `io.monitorHa` 为"当前 cfx"、以 monitor 的帧为判据，`escape` 只从 `prevMode` 恢复运行模式；`enterHmon` 恒跳 monitor 的 `vector`（`CFXESC` 也交 monitor）。
- **实现**：`WumingParams`/`WumingGewuParams` 注入 `runCfxReset = cfx_power(63)`（复位地址是 `cfx_power_hypv_excp_vector`，`spec/Kaiwu §1`）；`GewuFile` 新增 `curCfx`（6 位 `inner_cfx_code`）与 per-cfx `prevCfx`（64 位寄存器：软件写整 64 位、恢复时取 `[5:0]`；与 `prevMode` 同在异常帧里）；异常进入 `prevCfx(entryIdx) := curCfx` → `curCfx := entryHa`；`escapeOk = ha === curCfx && curImplemented && hasFrame(curCfx 的帧)`，恢复 `runMode ← prevMode(curIdx)`、`curCfx ← prevCfx(curIdx)`；帧视图（`frameValid`/`cause*`/`prev*`）改为**当前 cfx 的帧**（未实现的当前代码回退 monitor，只影响 trace）。
- **`CFXESC` 交当前 cfx**：`GewuFileIO.excp` 增 `toCurrent`，新增输出 `entryVector`（= 入口目标 cfx 的 `cg3 rc10`）；`WumingCore.enterHmon` 增 `toCurrent` 参数并用 `entryVector` 落点（`escape` 失败那条传 `toCurrent = true`）。hmon 固件（`power → hmon → 应用`）与"应用再 `escape cfx_hmon` 必判 CFXESC"两条路径因此都按 spec 落点。
- **同拍定序**：`escape` 提交那拍若返回地址 IALIGN，硬件在同一拍「先恢复、再进入」。`GewuFile` 在 `excp.valid && escapeOk` 时把帧写成**恢复后**的 `prevCfx/prevMode`（否则该帧会声称来自 handler，下一次 `escape` 把核留在 hmon）。QEMU 同序（先恢复再 raise）。
- **sim 重建**：先 `export PATH=<chipyard>/.conda-env/bin:$PATH` + `export RISCV=<chipyard>/.conda-env/riscv-tools`（**必须**，见上条构建环境坑；系统 `java` 是 21，sbt 1.8.2 会报 `bad constant pool index`），再 `make verilog CONFIG=WumingTinyConfig -j32` + `make CONFIG=WumingTinyConfig -j32`（`JOBS=32`）⇒ 交付二进制 md5 **`df16728eac30323445a4e3ee5b7eca95`**（2026-11-19 在 `.conda-env` 下重建；旧 `9b6928e0…`/`eb5220f9…` 作废；`ISS-453`：md5 只作记录，身份判据取行为——重建后 `tests/inst/11-cfx` 5/5 通过）。**坑**：`cp -p` 还原源文件会带回旧 mtime ⇒ chipyard 的 classpath 缓存按时间戳判定会**不重编**（生成物仍是注入版）；还原后必须 `touch` 再重建。
- **验证**：`tools/chipyard/excp/prevcfx.S` + `check_prevcfx.py`（判据现场从 `spec/DADAO-12` 解析 `CFXTRAP`/`CFXESC` 位号、从 `.tao/contracts/contract-see.md` 解析 Tiny 的 `cfx_power`/`cfx_hmon` 编号）——断言 `cg5 rc1` boot 值 = 63、RW 往返、hmon 帧 `escape` 回应用、应用再 `escape cfx_hmon` 判 `CFXESC`（cause_ip = 被拦 `escape` 的地址、到达次数 = 2）；同一 ELF 在 chipyard 与 QEMU 上 **48 B 逐字节相同**。`tests/inst/11-cfx` 的 `cfx2rd`/`cfx2rc`/`trap`/`fence` 4 个载体 chipyard↔QEMU 逐字节相同；注入 2 路（不保存 `rc1`、不恢复 `curCfx`）为真实重编后的红，`cp`+md5+`touch` 还原后回绿。
- **既有差异（非本任务引入）**：`tests/inst/11-cfx/escape_ciii_cfx.S` 链例 12 把 hmon SRAM `+0xC0/+0xC8` 当"未调用/到达计数"哨兵，而本 profile 的 TLRAM 上电不为 0（实测 `+0xC8` = 随机值、QEMU = 0）⇒ 该链例在 chipyard 上结构性红；把两个槽显式清零的同一副本在 chipyard/QEMU 上 **96 B 逐字节全绿**（即语义已对齐，差别只在 SRAM 上电口径）。`tools/chipyard/excp/causeid.S` 自 `m15-testcases-007` 的宏层改造（故障链 + `__TEST_SECTIONS`）后**缺 `__TEST_SECTIONS` ⇒ 链接期 `undefined symbol: __fault_chain`**（与本次改动无关；该载体的 CFXREG 例已从 `cg5 rc1` 换成 `§3.6` 明写 reserved 的 `cg5 rc63`）。`trap cfx_power` 仍报 ILLI（`tests/inst/11-cfx/trap_ciii_cfx.S` 已记 GAP），不在本任务范围。

## Kaiwu-Vast 的两级页表走查（`m16-chipyard-007`）

- **条款**（`DADAO-12 §2.2.1–§2.2.6`/`§4.5`，`contract-tlb` TLB-12…TLB-24/TLB-31…TLB-37）：`L1 = VA[41:29]`、`L2 = VA[28:16]`、页内 `VA[15:0]`（**64 KiB 页**）；`SP = 1` 的 L1 条目是 **512 MiB 超页**并在 L1 结束走查（`SPF` 按 `VA[28:26]` 选 64 MiB 片段）；PTE **8 字节大端**；页表访问一律用 PA，且只许落在 PA RAM / BootROM。子原因按 spec 顺序 **缺页 → 小页缺失 → HSJU → R/W/X**，位号只从 `gewu.GewuCauseId` 取（`ADR-0056`，核里没有第二份表）。
- **形态**：新增 `WumingPtw.scala`（`WumingTile` 里每核一份，**只有 `useVM` 的机器实例化**）。走查器**借用核的数据端口**：核在 `sXlate` 里停住时数据口空闲，因此没有第三条 TileLink 客户端，也不需要地址图协商新端口。L1/L2 各一次 8 字节 `Get`；A/D 只用一次整拍 `Put`（原子 OR 后的 PTE）。
- **A/D（本地 + 回写）**：每个访问侧一个直通槽（I/D 各一），槽里保存整条叶子 PTE。填充时 `A_local = PTE.A`、`D_local = PTE.D`、挂起位清零（**填充不产生回写**）；访问（命中与触发填充同样）在 `A_local = 0` 时置本地 A 与挂起位，store 另置 D。挂起位只在 **clean / flush / 槽替换**时以原子 OR 回写内存，`invalid` 不回写；回写被总线拒绝 ⇒ `CFXMEM [56] ADWBFAIL`，`cause_info` = **PTE 物理地址**，条目与挂起位保留。`cfx_ptw_tlb_control` 的编码校验在核里（scope=`11` 或 `range`+`size=0` ⇒ `CFXREG`，`TLB-24`），`none` 无条件 no-op（`TLB-22`）；命令在写指令上同步完成（`TLB-37`）。
- **范围**：本任务只做到「走查 + 一个直通槽」，**不是** `008` 规定的 2×8 + 4 超页 I/D 表；每次访存仍是一次真实的两级走查（命中槽时省略），`008` 直接替换槽的组织。Vast 上**不发射投机预取**（投机取指不应触发走查），逐拍需求取指。
- **地址图（Vast 物理半边）**：PA RAM `[0, 2 GiB)` 作为 **TileLink 从端口**挂在 MBUS（`BankedScratchpad`，`kaiwu-vast-pa-ram`）——不走 AXI4/`SimDRAM`：本机没有宿主 DRAM 装载路径（镜像由 tile 自己的装载器流入，fesvr 的 `load_elf` 也拒绝非 RISC-V ELF）。为把 `[0, 2 GiB)` 腾出来，RISC-V 的 CLINT/PLIC、inclusive LLC（换 `WithBroadcastManager`）、debug 模块、bus error device、UART、boot-addr 寄存器、PRCI/clock-gater、tile-reset 控制全部移出该窗口或按 profile 去掉（DADAO 核从不访问它们，只有自己的窗口能到总线）。**Tiny 的地址图一字未改**（同一份 `DadaoConfigs.scala` 里另立 `WithDadaoVastAddressMap`）。
- **装载器**：`+loadmem=` 的 PT_LOAD 现在可落两个窗口（核内 SRAM 与 PA RAM），页表/映射目标因此能在核启动前由宿主装入；另有 `+wuming_loadmem=` 优先别名（给「`+loadmem` 同时会喂 stock SimDRAM」的机器用）。
- **验证**：`tools/chipyard/ptw/vastwalk.S`（+ `vastwalk.lds`）把 L1/L2/超页/故障表放在 PA 的固定地址，`gen_vastwalk_tables.py` 是**几何与期望 PTE 值的单一真源**，`check_vastwalk.py` 现场从 `contract-see §6.1.1` / `ADR-0056` 解析位号并与 `spec/DADAO-12 §3.6` 互校（`--self-test` 19 条可达 FAIL）。判据：31 条 8 字节记录逐位相等 + 同一 PTE 上**恰好两次** A/D 回写（clean 各一次，值 A=1/D=0 与 A=1/D=1）。实测（同一 ELF）：走查 `VA = PA + 2 TiB` 普通页、512 MiB 超页两片段、经翻译取指；故障 `DGPTRAP`/`DSPTRAP`/`DSPFTRAP`/`DGPFTRAP`、`NHPERM`/`NWPERM`/`NXPERM`、`CFXREG` 逐条与 spec 一致。**`ADWBFAIL` 机器级不可达**（本机 PA RAM 全可写，`contract-tlb §11` ⑦），由实现层注入覆盖：强制回写失败 ⇒ 报 `CFXMEM [56]` 且 `cause_info` = PTE PA；同一注入再加「静默丢弃」⇒ 判据红。
- **Tiny 零增益**：`WumingPtw` 只在 `useVM` 时实例化，Tiny 的 FIRRTL 里 `WumingPtw` 出现 **0** 次；首册 38 个镜像在改前/改后 Tiny 二进制上**逐字节相同**。

## Kaiwu-Vast 的 I/D TLB（`m16-chipyard-008`）

- **口径**（用户 2026-11-19，`contract-tlb` TLB-01/TLB-02/TLB-38）：**只设一级 TLB、分 I/D**（I/D 分离是设计）；普通页 **2 组 × 8 路**（组号 = `VA[16]`，64 KiB 页号 LSB），无 sectored；超页 **4 条全相联**；两者都按 **LRU** 替换（无效条目优先）；**无特殊条目**（rocket 的 special entry 为 PMP，DADAO 无 PMP）。TLB 属 `cfx_ptw`、per-hart，核内实例、类可复用。
- **形态**：新增 `WumingTlb.scala`（`WumingTlb` 参数化模块），`WumingPtw` 里实例化两份（`instruction = true/false`）。**I 表完全没有 D 状态**：条目 bundle 只有本地 A，D 的 `dLocal`/`dPend` 只在数据侧实例创建（FIRRTL 里 I 模块 **0** 个 `dLocal`/`dPend` 寄存器，D 模块有）；FIRRTL 结构由证据脚本逐模块判定。查找是**组合**的（命中在 2 拍内答复，不读 PTE）。
- **A/D 与回写**：填充把 PTE 的 A/D 复制成本地值并清挂起位（填充不回写）；命中/触发填充的访问在 A（store 另加 D）为 0 时置本地位与挂起位；挂起位只在 clean/flush/替换时回写。回写是 **PTE 的读—改—写 OR**（先 `Get` 当前 PTE，OR 上挂起位再 `Put`）——I、D 两表可能对同一 PTE 各持挂起位，覆盖式写回会抹掉对方刚写入的位（探针用「I 置 A、D 置 A+D 后 clean ⇒ PTE A=1,D=1」抓这个）。回写失败 ⇒ `CFXMEM [56] ADWBFAIL`、`cause_info` = PTE PA、条目与挂起位保留。
- **`cfx_ptw_tlb_control` 双表**：spec 里只有一个 TLB（没有 I/D 选择位），因此命令**先扫 I 表、再扫 D 表**（各 20 条：16 普通 + 4 超页）；`clean` 回写后保留、`invalid` 不回写直接删、`flush` 回写后删（失败不删）；`asidAny = 0` 只碰 `G = 0` 且 ASID 匹配的条目；**条目级 + 遇错即停**（`TLB-37`）。
- **LRU 实现**：每组一条 age 列（0 = MRU），不变量 = 有效条目的 age 恰为 `0..(有效数-1)` 的一个排列；命中把该条置 0、更年轻的 +1；填充把新条置 0、其余有效条 +1（**不能沿用被替换条的旧 age**，否则首次若干次填充都留在 0、淘汰顺序丢失——实测第一版即此现象）；删除时把更老的 −1 以保持排列。淘汰 = 同组内 age 最大，若有无效条目则优先用它。
- **核数据口纪律（本任务修）**：`sFreq` 的需求取指现在要求「地址已定」——`atDemand = state===sFreq && (!memWindow(ip) || vx.fetchDone)`。此前 Vast 在**请求翻译的同一拍**就把**上一次的** `fetchPa` 发上总线：走查要十几拍，假请求的 D 早已回收，看不出来；TLB 命中只要 2 拍，假请求还在飞、真取指又用 source 0 ⇒ TileLink「A channel re-used a source ID」。Tiny 不受影响（`useVM = false` 时该条件恒真，FIRRTL 正文逐字节不变）。
- **零增益**：`WumingTlb`/`WumingPtw` 都只在 `useVM` 时实例化，Tiny 的 FIRRTL 里两者出现 **0** 次；首册 38 个镜像在改前/改后 Tiny 二进制上仍逐字节相同。
- **验证**：`tools/chipyard/tlb/vasttlb.S`（+ `vasttlb.lds`）以 PA 固定地址放页表与数据，`gen_vasttlb_tables.py` 是几何、PTE 与数据 magic 的**单一真源**，`check_vasttlb.py` 比对 42 条 8 字节记录 + 日志（淘汰受害者序列、OR 回写次数与值、ADWBFAIL 帧结构；`--self-test` 21 条可达 FAIL）。覆盖：命中不重读 PTE（改内存 PTE 后仍读旧数据）、`invalid`+VA 后重步查、同 set 8 条共存 / 第 9 条淘汰 LRU、超页 4 条 + LRU（5 个超页交替 ⇒ 淘汰 S2 并重步查）、I 侧取指只置 A（clean 后 D 仍为 0）、I/D 双表 OR 合并（两次写回）、`invalid`/`clean`/`flush` × I/D 的 2×3 矩阵。注入：改全相联 / 去 I 侧 A 置位 / flush 只清 D 表，均判据红；ADWBFAIL 注入（D 侧命令回写不落地）⇒ 两次 `clean` 各报一次、PTE 停在 A=1/D=0、条目保留。

## Kaiwu-Vast 的 cfx0/cfx2 寄存器面（`m16-chipyard-019`）

- **范围**：只做 cfx0（umon）/ cfx2（smon）的**寄存器面**；U/S 模式进入路由
  与异常进入主控制流留给 `m16-chipyard-020`。
- **cfx 序列**：`WumingCfxHa` 新增 `umon = 0`、`smon = 2`；`WumingGewuParams` 只在
  `useVM`（Vast）时加入这两个 cfx（Tiny 不变）。cfx2 的空间块按
  `contract-see §3` 落为 64 KiB SRAM（地址图新增 `0x0bff_0000_0000` 的
  `kaiwu-vast-smon-sram`；`WumingCore.inSpecWindow` 同步放行该窗口）。
- **公共面**：`GewuCfxParams` 新增 `commonRows`（仅 cfx0/cfx2 打开）——
  `cg0`–`cg2` 的模式行（rc0–4 四个独立同步 mask + intr mask、rc8
  `switch_run_mode`、rc10 `excp_vector`，写丢低 2 位）、`cg3 rc12`
  `hypv_cg_reg_deleg`（复位全 1、bit3 恒 1）、`cg4` 的 id/version/计数/
  `scratch_regs_num`、`cg5 rc5 pending`、`cg6` 四个暂存寄存器、`cg8 rc1
  global_cfx_intr_mask`；保留 rc 与写 RO ⇒ `CFXREG`。cfx3/63 仍走原寄存器子集，
  行为不变。
- **两轴权限**：`cg0`–`cg3` 的四个同步 mask 由「四个名字共用一个向量」改为
  **四个独立寄存器**（`DADAO-12 §3`；`cfxreg` = rc2）。`cfx2rd`/`cfx2rc` 的
  `cfxreg` 轴**强制判定（`CFXPERM`）本任务未启用**：chipyard 的 BootROM 链以
  `cfx_power` 运行测试体，规范复位掩码只允许 `cfx_hmon`（bit3），启用后
  cfx0/cfx2（以及既有 cfx4/cfx5）全部不可达；判定随 `m16-chipyard-020` 的
  进入链/环境准备落地（见任务书「遗留问题」）。
- **验证**：`tests/arch/umon/cfx02_regs.S` + `check_cfx02_regs.py`（47 条记录，
  期望现场取自 `spec/DADAO-12` §2.1/§3.1/§3.3/§3.4/§3.6–§3.8 与
  `contract-see §3/§6.1`）；注入「Vast 去掉 cfx0」「Vast 去掉 cfx2」均判红，
  `cp`+md5 还原重建后回绿；Tiny `11-cfx`/`01-load-store` 与 016/017 的 cfx5
  探针不回归。

## Kaiwu-Vast 的 cfx5 寄存器面（`m16-chipyard-016`）

- **范围**：只接 `cfx_cache`（cfx5）的**寄存器文件**（`contract-cache` CACHE-03…CACHE-18/27），
  命令到 I/D 阵列的接线是下一件任务；`WumingCache` 阵列/维护端口不改。
- **寄存器**：`cg8 rc0 cache_exist`（RO，I/D 两位，Vast 读 `0b11`）、`rc8 cache_enable`
  （RW，复位 = exist、写按 exist 掩码）、`rc9 cache_ctrl`（WO，写即执行；
  `[15:14]` 选侧 / `[1:0]` 操作 / `[3:2]` 范围，判序与 no-op 按 CACHE-11…14，
  非法编码 ⇒ `writeOk=false` ⇒ `CFXREG`）、`rc10 cache_addr_start`（RW，只存
  `PA[55:0]`）、`rc11 cache_addr_size`（RW，整 64 位）。
- **归属**：寄存器状态在 `gewu`（`GewuCacheParams`）；`WumingParams` 只在 `useVM`
  的 Kaiwu-Vast 上把 cfx5 加入 cfx 序列，Tiny 保持 `cache = None` ⇒ 行未实现、
  `cfx2rd`/`cfx2rc` 报 `CFXREG`（CACHE-28）。`GewuFile.io.cache` 只把 enable/
  addr_start/addr_size/命令脉冲交给核，本任务无人消费（阵列接线下一件）。
- **验证**：`tests/arch/cache/cfx5_regs.S` + `check_cfx5_regs.py`（22 条记录，期望
  现场取自 `contract-cache`/`contract-see §6.1`/`contracts/opcodes.yaml`；`--self-test`
  对每条记录做可达 FAIL 证明）；注入「Vast 去掉 cfx5」/「addr_start 只存 42 位」
  均判据红，`cp`+md5 还原重建后回绿；Tiny 的 `11-cfx`（含 cfx5 ⇒ `CFXREG`）与
  `01-load-store` 改前/改后逐镜像字节相同。

## Kaiwu-Vast 的 cfx5 维护命令（`m16-chipyard-017`）

- **范围**：把 `cache_ctrl`（`cg8 rc9`，写即执行）接到 `WumingCache` 的 I/D
  `cmd` 端口；**不改**填充/替换算法，**不改** 016 的寄存器位域。
- **控制字**（`contract-cache` §3，`CACHE-09`…`CACHE-14`）：`[1:0]` 操作
  （none/clean/invalidate/flush）、`[3:2]` 范围（all/PA 单行/PA 区间/reserved）、
  `[15:14]` 选择（bit15 = I、bit14 = D）；非法编码仍由 `gewu` 的 `writeOk`
  拒绝 ⇒ `CFXREG`，核在 `sExec` 的 `cfxFault` 路径先走掉，命令不会产生。
- **执行**：核在 `sXlate` 里用一个子状态机（`kind = 4`）执行：消费 `gewu` 的
  写脉冲 → 按判序选侧（先 I 后 D，`CACHE-21`）→ 等 `cmdDone` → 下一条侧，
  全部完成才 `finish(ip+4)`（同步完成，`CACHE-24`）。`cache_enable` 对应位为 0
  的侧**不发出命令**（`CACHE-08`），I 侧 `clean` 是 no-op、根本不发（`CACHE-19`）。
  不新增核 FSM 状态（`Enum(16)` 不变 ⇒ Tiny 的 FSM 宽度不变）。
- **缓存侧**：`WumingCacheCmd` 增加 `scope`/`size`（`op` 语义不变）；
  `scope = 1` 按 set/tag 直接查一行；`scope = 0/2` **枚举全表**并按行的
  重建 PA 过滤（`all` 全收；区间按 `[addr, addr+size)` 相交，与 gem5 的
  tag-store 枚举同法，不随操作数大小扫地址空间）；`invalidate` 只丢不写回，
  `clean` 写回并保留，`flush` 写回后丢（`CACHE-19`/`CACHE-20`）。写回被总线
  拒绝时保留脏行并抬 `cmdError`/`cmdErrorAddr`，核报 `CFXMEM [56] ADWBFAIL`
  （本机全部可缓存内存都是可写 PA RAM，该路径不可达）。
- **维护丢弃不重排 age 列**：`dropLine` 只清 `valid`/`dirty`；被丢的 way 是下一次
  填充的首选，`fillAge` 在分配时重置它的 age。这样避免了「按动态 set/way 索引
  重排 1024 条 age」把生成的 age 更新逻辑放大一个数量级（实测 D 实例的
  `WumingCache.sv` 由 2.2 GB/2176 万行降到 12 MB/9.5 万行，Verilator 不再 OOM）；
  替换策略由实现决定（`CACHE-05`），`fill`/淘汰路径的 LRU 语义未改。
- **不可缓存/MMIO**（`CACHE-22`）：只有翻译后的内存窗口 beat 进缓存，
  核内窗口（SRAM/hmon/BootROM）从不成行；命令按 PA 枚举现有行，落在
  这些 PA 上自然无效果、不报异常。
- **验证**：`tests/arch/cache/cfx5_maint.S`（+ `gen_cfx5_maint_tables.py`
  单一真源、`check_cfx5_maint.py` 判据）。29 条记录 + 缓存日志时序；D 侧
  「是否写回」以**取指端口**为独立观测量（改代码行 → 命令 → `I|invalidate` →
  跳转执行到的立即数即内存内容），日志另断言 invalidate 无 `wb`、flush 后
  重新缺失、I|clean 不进 I 侧且 I 行仍在、`enable=0` 的命令未发出。注入
  「invalidate 先写回」与「I 侧不维护」各判红，`cp`+md5 还原并强制重建后回绿；
  Tiny 的 `11-cfx`/`01-load-store` 改前/改后逐镜像字节相同。

## Kaiwu-Vast 的 I-Cache（`m16-chipyard-010`）

- **口径**（用户 2026-11-20）：I/D 各 **8 路 × 128 组 × 64 B = 64 KiB**（本任务是 I 侧，D 侧是 `009`）；**只读、无 dirty、无写回、无写穿**（与 `008` 的 I-TLB 无 D 位同构）；**索引位在 64 KiB 页内**（line offset 6 + 组索引 7 = 13 < 16 ⇒ VIPT 无别名、每路 8 KiB）；缺失按 **8 个 64 位 beat** 填充；阻塞式（单未决缺失）。
- **共用类**：`WumingCache`/`WumingCacheParams`（自本任务起由 `009` 的 `WumingDcache` 泛化；**类定义只有一处**，核内两处实例化参数不同）。参数 `sets/ways/lineBytes/writeBack/withDirty/readOnly/label`；`readOnly = true` 在**展开期**去掉 dirty 位（tag bundle 里没有该字段）、淘汰回写、clean 回写和写穿 Put，A 通道只剩 `Get`；对只读实例发写请求会被显式拒绝（错误响应），不静默当成读。
- **接线**：`WumingCore` 在 `useVM` 时实例化（`WumingCacheParams(writeBack = false, withDirty = false, readOnly = true, label = "icache")`），缓存的 TileLink 主端口取代核的取指端口（`io.imem`），核的需求取指变成缓存请求；**翻译后**的取指走缓存，核内窗口（SRAM/hmon/BootROM）的取指仍直连总线（与 D 侧同一路由口径）。Vast 上仍不发射投机预取，因此同时只有一个请求在飞。缓存实例的第二请求口（PTW）与 clean/invalidate 口接空。
- **日志**：两个实例的 `printf` 带 `label`（`WumingCache[icache]` / `WumingCache[dcache]`），判据按标签各取一侧——503 行级的两个实例在同一份日志里可分辨，这是 I 侧"取指命中不访存"能被独立观测的前提。
- **零增益**：缓存只在 `useVM` 的机器实例化，Tiny 的 FIRRTL 里 `WumingCache` 出现 **0** 次；首册 38 个镜像在改前/改后 Tiny 二进制上仍逐字节相同。
- **验证**：`tools/chipyard/icache/vasticache.S`（+ `vasticache.lds`）在 PA 固定地址放十段**各 64 B = 一行**的代码块（A1..A8 同组 8 路、A9 同组第 9 行、C1 另一个组），`gen_vasticache_tables.py` 是几何/PTE/magic 的**单一真源**（`--check-geometry` 另核「A 行同组、C1 组 0、二者 6 位组相同」），`check_vasticache.py` 比对 12 条记录 + 日志事件（每块 1 填充 + 7 命中、8 路共存无淘汰、A9 淘汰 A1、A1 重填淘汰 A2、C1 不淘汰 A 行、组索引 64/0、无写事件、核内 SRAM 行 0 事件；`--self-test` 13 条可达 FAIL、`--structure` 结构断言、`--structure-test` 判据自检）。**命中不访存**的独立证据 = 核自己的 `fetchresp latency=`：块首拍（缺失）≥ 10 拍、其余拍（命中）≤ 4 拍。
- **结构断言**：Vast FIRRTL 里 `icache` 实例的模块 **0** 个 dirty 寄存器、**0** 条写回路径（`wb` 打印/状态不生成），`dcache` 实例两者都有（对照，防恒真）；两实例都是 8 个深度 128 的数据阵列。注入「I 侧改 `withDirty = true, writeBack = true`」⇒ 结构断言红（可达 FAIL）。

## Kaiwu-Vast 的 D-Cache（`m16-chipyard-009`；类名自 `010` 起为 `WumingCache`）

- **口径**（用户 2026-11-20）：I/D 各 **8 路 × 128 组 × 64 B = 64 KiB**（本任务是 D 侧，I 侧归 `010`）；**索引位在 64 KiB 页内**（line offset 6 + 组索引 7 = 13 < 16 ⇒ VIPT 无别名、每路 8 KiB）；**写回 + 写分配**、每行一个 dirty 位；**PTW 的页表读走 D-Cache 端口**；阻塞式（单未决缺失）首版；设计参照 `WumingTlb`（参数化类 + 每核实例 + Tiny 不实例化）。
- **形态**：新增 `WumingCache.scala`（`WumingCacheParams(sets/ways/lineBytes/writeBack/withDirty/readOnly/label)`；`m16-chipyard-010` 把当时的 `WumingDcache`/`WumingDcacheParams` 泛化为 I/D 共用类，本节的 D 侧参数不变）。数据阵列每路一个 `SyncReadMem`（行宽读端口 + 按 beat 的写掩码），tag/valid/dirty 与 LRU age 在寄存器里；查找 = 1 拍读组 + 1 拍比 tag，命中即答复，缺失按 8 个 64 位 beat 填充（填充只写整行）。写命中只改行并置 dirty；写缺失先写分配（填充后合并）；脏行在**淘汰或 clean** 时整行写回。写操作先看 manager 是否支持 `PutPartialSafe`（只读目标如 BootROM ⇒ 错误返回、不静默进缓存）。`writeBack = false` 走同一数据路径的写穿分支（证据注入用）。
- **接线**：`WumingCore` 在 `useVM` 时实例化，缓存的 TileLink 主端口取代核的数据端口（`io.dmem`），核的数据访问经请求/响应端口；**翻译后**的 beat 走缓存，核内窗口（SRAM/hmon/BootROM，`addr[47:42] ≠ 0`）直连总线——semihosting 应答者用自己的主端口读这些窗口，缓存它们会让宿主读到旧值。`WumingPtw` 的页表读与 A/D 读—改—写改走缓存的第二个端口（PTW 不再有 TileLink 主端口，也不再处理总线字节序）；核与 PTW 因此共享每一条物理行的唯一缓存副本——核经缓存写入的 PTE，走查立即读到。
- **内部 clean/invalidate**：缓存带 `cmd` 端口（`op` 1 = 按 PA 单行 clean【回写+保留】、2 = 单行 invalidate【不回写】、3 = 全表 flush【回写+失效】），`cmdDone`/`cmdError` 单拍返回；`cfx5` 接线另立任务，核当前把它驱动为空闲。
- **零增益**：缓存只在 `useVM` 的机器实例化，Tiny 的 FIRRTL 里 `WumingCache` 出现 **0** 次；首册 38 个镜像在改前/改后 Tiny 二进制上仍逐字节相同。
- **验证**：`tools/chipyard/dcache/vastdcache.S`（+ `vastdcache.lds`）把页表、同组 8 行数据、代码页与 PTW 新旧目标放在 PA 固定地址；`gen_vastdcache_tables.py` 是几何/PTE/magic/组索引的**单一真源**（cause one-hot 从 `contract-see §6.1` 现场解析），`check_vastdcache.py` 比对 35 条 8 字节记录 + 日志事件（组索引、受害者序列、写回顺序、PTW 命中；`--self-test` 11 条可达 FAIL）。覆盖：同址 1 缺失 + 4 命中；同组 8 行共存、第 9/10 行按 LRU 淘汰（受害者 B1→B2）；写后读命中不回内存；**写回时机以取指端口为独立观测量**（当时无 I-Cache）：把 `trap cfx_hmon` 指令字经缓存写入代码页后，淘汰前取指仍读到内存里的旧值（UNDI），强制淘汰（同组 8 次填充）后取指读到 `trap`（CFXTRAP）；PTW 读到核内经缓存写入的新 PTE（改 L2 PTE → `invalid/all` → 重走查 ⇒ 新映射的数据）。注入：替换策略改 MRU / `writeBack = false` / 组索引 6 位 ⇒ 均判据红；`cp`+md5 还原并强制重建后回绿。
