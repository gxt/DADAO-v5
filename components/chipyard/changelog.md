# chipyard 组件变更记录

> 粒度：**按任务一条**，追加式。**体例 = 列表式（不用表格）+ 按里程碑分节**：每条 = `- **<日期> <任务号或 —>**`，**摘要另起缩进行** `  - 摘要：<摘要正文>`；节 = `## M<k>`（节序 M1→M2→…）。补丁集的生成/应用/校验规范见 `docs/Process-01-组件补丁组织与构建编排.md §10`。

## M12

- **2026-11-11 `m12-chipyard-009`**
  - 摘要：**控制流全形式 + 返回地址栈**（`spec/SimRISC-06`、`spec/SimRISC-00 §2.4`）：解码器补 `br.eq`/`br.ne`（`rrii`）、相对 `jump`（`iiii`）、`call`（`iiii`/`rrii`）与 `ret rdHA, imms18`（`rd0` 配非零立即数 ⇒ ILLI）；`WumingRegFile` 把 `ra` 银行升级为 RegRAS（`ra1`–`ra63` + `RACNT`/`MRPTR`，`ra0` 读出 `{SBZ,RACNT,MRPTR}`、写入拆分、`[63:54]` 写无效），新增单周期 RAS 操作（PUSH/FOLD/SPILL/POP/DEC/REFILL/CONSUME）；`WumingCore` 在 `EXEC` 组合完成 C1/C2/C3a 与 D1/D2/D3，C3b 溢出走数据端口 8 字节存储、D4b 下溢走 8 字节读取，两者都先判定后修改（精确异常）；新增 `RASOF`/`RASUF`（`1<<10`/`1<<11`）进 hmon。返回地址 = 当前 `call` 地址 + 4。
  - 执行者：engineer

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

- **2026-11-09 `m12-chipyard-005`**
  - 摘要：**真核起点：寄存器堆 + 解码器 + 整数 ALU**。`WumingCoreStub` 由 `WumingCore` 替换（`WumingRegFile` / `WumingDecoder` / `WumingALU` 三个子模块）：`rd`/`rb` 双 bank，`rd0` 读 0、`rb0` 读当前 IP（只读），`rrrr` 双目的；解码 `orrr`/`orri`/`rrrr`/`riii`/`rrii`/`rwii` 六种格式，覆盖 SimRISC-04（64 位算术/逻辑/移位/扩展/比较/乘除）、SimRISC-05（`add.o`/`sub.o`/`cmp.uo` dbb、`add.si`/`aip.si`）与 SimRISC-08（32 位同族）；`ld.o`/`st.o`/`jump rrii`/semihosting `trap` 沿用而不回归。非实现编码不再静默：已定义未实现 ⇒ ILLI，QFC/子表空白 ⇒ UNDI（`contracts/legality_rules.yaml`），并实现 `dst_rd0`/`dst_rb0`/`dst_dual_same`/`encode_sbz` 合法性检查。ALU 口径按 `spec/SimRISC-04 §1.1`：`rrrr` 无符号加减的高半是**进位/借位（0 或 1）**、有符号加减的高半是 128 位和/差的高 64 位、乘法的两个变体都是完整 128 位积的高半。
  - 执行者：engineer

- **2026-11-10 `m12-chipyard-007`**
  - 摘要：**Tiny 固定 BootROM 固件 + `power → hmon → 应用` 移交**。新增 `tests/shared/bootrom/tiny/{power.S,hmon.S,*.lds}`（power 校验 image index table → 逐 8 字节复制 hmon 段到 `0x0fff_0000_0000` → 幂等写 `cg3 rc10` → `trap cfx_hmon, 0x30001` → hmon 校验 `CFXTRAP`+magic → `escape ...,+4` → 跳固定入口；hmon handler 共 56 B）与 `tools/testcases/arch/build_tiny_bootrom.py`（64 KiB 镜像：power 8 KiB / hmon 8 KiB / 保留 40 KiB 全零 / 表 8 KiB，链接断言 + 构建期校验，超限即失败），镜像以稀疏文本 hex 入库、`build.sbt` 资源生成器解码；应用侧新增 `tiny_crt.S`（入口设 SP，与测试程序同一 ELF）。SoC：hmon SRAM 为第二个独立 TL 从设备（64 KiB，`ARWXC`），`WumingLoadMem` 增装载契约（`e_entry` 必须 = 固定入口、`PT_LOAD` 命中 BootROM 或 hmon SRAM ⇒ 显式失败）；核内补最小 cfx_hmon 移交面（`br.*`/`trap→CFXTRAP`/`escape`/`cfx2rd`/`cfx2rc`、cause 帧、`excp_vector`），五类同步异常与完整寄存器组仍归 `m12-019`。
  - 执行者：engineer

- **2026-11-10 `m12-chipyard-018`**
  - 摘要：**取指/访存拆成两个 TileLink 客户端 + 8-beat 取指队列 + 12 态状态机骨架**。`WumingTile` 新增 `fetchMasterNode`/`dataMasterNode`（各 `IdRange(0, 3)`，都进 tile 内 `portXbar`），`WumingCore` 改为 `imem`/`dmem` 两个 `TLBundle`（A/D 通道与请求状态各自独立）；`WumingCoreParams` 新增 `fetchDepth = 8`，核内改为 8-beat 环形取指队列 + 顺序预取（source 0 需求、1/2 预取槽，命中 1 拍、投机 `denied` 不报错）；状态机按 `m12-006 §5.1` 落 12 态（`IDLE/FREQ/FWAIT/EXEC/TRAP/SEMI/EXC/MREQ/MWAIT/SLOW/FAULT/HALT`），R1 = C（移位/位域走 `SLOW` 2 拍、简单算术 1 拍），`EXC` 暂只记 cause 后进 `FAULT`（cfx 帧/向量归 `m12-019`）；诊断 `printf` 增 `cycle=`。273 例与 `m12-005` 逐字节一致（md5 `2d4d9465…`）。
  - 执行者：engineer

- **2026-11-10 `m12-chipyard-020`**
  - 摘要：**取指预取优化：4 个预取槽 + 数据优先仲裁 + SRAM 往返延迟计数**。`WumingTile` 取指客户端 `IdRange(0, 3)` → `IdRange(0, 5)`（1 需求 + 4 预取；`fetchDepth` 仍 8，source 回收/flush-stale 语义不变），`WumingCore` 的预取槽由 A/B 两个具名寄存器改为 4 槽 `Vec`（源 ID = 槽号 + 1，回复按源匹配）；**数据优先**：`MREQ`/`MWAIT`（数据端口有未完成请求）期间不发起新预取，已发出的不清空、回复仍入队；发射条件由 `qCount =/= 0 && !waitBeat` 放宽为 `qCount =/= 0 || waitBeat`（FWAIT 等已在途 beat 时继续填充槽位，否则 4 槽无效）；新增需求取指往返延迟计数器（A 握手 → D 回包拍数，`fetchresp`/`prefetch ... lat=` 诊断可见）。实测跨 beat 代价中位 8 → 1 拍（注入回 2 槽：中位 5、102/204 次 > 2 拍），SRAM 往返 4/6 拍 ⇒ 4 槽（需求 3）足够；273 例 md5 不变。
  - 执行者：engineer

- **2026-11-11 `m12-chipyard-019`**
  - 摘要：**cfx 寄存器组 + 五类同步异常进 hmon**。`WumingCore` 实现 `cfx_hmon`(cfx3)/`cfx_power`(cfx63) 的 `cg3`（四类同步 mask、`cfx_intr_mask`、`switch_run_mode` 恒 3、`excp_vector` 写忽略低 2 位）、`cg5`（`excp_prev_run_mode`、cause 帧）、`cg7`（16 块空间描述，只读写 `CFXREG`）与 `cg8 rc1`（未实现 ⇒ `CFXREG`）；`cg3` 仅 hypv 可访问，其它运行模式 ⇒ `CFXREG`；`CFXMEM`/`ILLI`/`UNDI`/`MALIGN`/`IALIGN` 五类同步异常写 `excp_cause_*` 并跳到 `excp_vector`（不再进 `FAULT`），`escape` 恢复 `excp_prev_run_mode`；未 backing 的访存/取指按 `TLEdge` 的 **safe** 合法性判 `CFXMEM`（fast 版对未映射地址会误报合法）。
  - 执行者：engineer

- **2026-11-11 `m12-chipyard-008`**
  - 摘要：**访存族：全宽度 `ld`/`st` + `ldm`/`stm`**。`WumingRegFile` 增加 **`ra` 银行**（第三组 64×64，`ra0` 可读写；RAS 语义归 `009`），读写口改为 2 位 bank 选择（rd/rb/ra）；`WumingDecoder` 覆盖 `SimRISC-01` 全部整数宽度（`ld.{ub,uw,ut,sb,sw,st}`/`st.{b,w,t}` + `ld.o`/`st.o` 的 rd/rb/ra 银行）与 `ldm`/`stm`（`rrri`，`mreg_zero`/`mreg_range_overflow`/`dst_rd0`/`dst_rb0` 合法性）；`WumingCore` 新增统一访存序列：**8 字节 beat 分组**（`stm` 逐元素打包 + byte-mask `Put`，`ldm` 逐元素提取写回）、**整段预检**（对齐 + Tiny 三段窗口，第一拍前）⇒ 精确 `MALIGN`/`CFXMEM`，中途 `denied`/`corrupt` ⇒ `CFXMEM` 进 hmon（可重入）；地址合法性改为 **Tiny 三段窗口**判定（`spec/Machine-v5 §1.1`），不再只看协商 manager 集合（否则地址 0 的 debug-controller 会把未映射访问变合法）。`tools/chipyard/mem_sweep.py` 驱动 `tests/inst/base/mem-*.yaml`（167 例：90 语义/边界 + 77 故障），`inst_sweep.py` 的「已定义未实现」探针改到 RF 银行形式（`ld.t rf`，FP 归 `011`）。
  - 执行者：engineer

- **2026-11-09 `m12-infra-003`**
  - 摘要：**子模块补丁集试点（testchipip）**：`generators/testchipip` 新增子模块补丁集 `submodules/testchipip/{series,patches/}`——`SimDRAM.cc` 的 `loadmem_memif_t::get_target_endianness()` 改为由 `+loadmem_be` plusarg 显式返回 `endianness_big`（默认 little 不变，stock RISC-V 配置行为不动），`SimDRAM.v` 的 `MEM_BASE` 默认值改为 `64'h0`（原无位宽 32 位推断会截断 48 位基址）；组件补丁集与子模块补丁集的分工/声明/门控见 `docs/Process-01 §14`。
  - 执行者：engineer
