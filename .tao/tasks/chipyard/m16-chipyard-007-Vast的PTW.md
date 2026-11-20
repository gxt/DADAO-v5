# m16-chipyard-007: Kaiwu-Vast 的 PTW（两级步查 + A/D）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m16-chipyard-006`（核参数与地址通路、`cfx_ptw` 寄存器面）
**可并行分片**：否（改 `dadao-wuming` 核 + 新增 PTW 模块）
**预估**：2–3 天
**档位**：大改
**状态**：待验收

## 背景与真源

DADAO 的页表是**两级、64 KiB 页**：`L1 索引 = VA[41:29]`、`L2 索引 = VA[28:16]`、页内 `[15:0]`；512 MiB **超页**在 L1 直接出（`SPF`）。PTE 为 **8 字节大端**，权限在 `[63:60]` 的 **HSJU**（H=63/S=62/J=61/U=60），另有 `frags[8]` 分片存在位、`R/W/X`、`A/D`。真源：`spec/DADAO-12 §2.2.1–§2.2.6`、`§4.5`；契约 `.tao/contracts/contract-tlb.md`（TLB-01…TLB-43）、`ADR-0040`（PTE/走查）、`ADR-0041`（TLB/A-D）、`ADR-0056`（子原因编码）。

**可参考**：rocket `PTW.scala` 的状态机骨架与多请求仲裁（`Vec(n, TLBPTWIO)`）——但 PTE 格式、权限位、异常码、A/D 语义**全部要重写**（见任务书模板中的「不能复用」清单，转抄自调研结论见 `discussing.md` 的 Vast 节）。

## 参考实现形态（BOOM/rocket，主会话 2026-11-19 调研）

- **TLB 在核内**、**PTW 在 tile 级（每核一个）**：BOOM 在 `v3/ifu/frontend.scala` 与 `v3/lsu/lsu.scala` 各 `new TLB(...)`；PTW 在 `v3/common/tile.scala` `Module(new PTW(ptwPorts.length)(...))`，`ptwPorts = ListBuffer(lsu.io.ptw, frontend.io.ptw, core.io.ptw_tlb)`。
- **类跨核复用、实例每核一份**（不是 SoC 共享）。
- PTW 的页表访存走**数据侧 cache 端口**（`HellaCacheIO` / `heccachePorts`）。
- ⇒ DADAO 按同构分工：**TLB 核内、PTW tile 级**；接口 = 「多条 PTW 请求端口 + 异常回传」。
- **待裁定**：PTW 的页表读在 DADAO 是否经 D-Cache（`DADAO-12 §2.2` 只规定用物理地址、不规定是否过 cache）——RTL 与 gem5 必须一致。


> **已恢复（用户 2026-11-19 反悔）：`WumingVast` 恢复开发，并按「最终上 FPGA」推进**——本任务继续；`gem5` 侧同步补 **FS + Timing（tiny/vast 两种机型）**，见 `m16-gem5-015`。

## 目标

1. **两级步查器**：按 `PTBR`（PA）+ 索引读 PTE；页表访问**走物理地址、不经 TLB**，且必须在 RAM/ROM 范围内（否则按 `CFXMEM` 处理，具体按 `§2.2` 核对）；
2. **PTE 解析**：`SPF`/`GPF`、HSJU、`R/W/X`、`frags`、`A/D`；超页（512 MiB）在 L1 直接结束走查；
3. **A/D 本地化 + 回写**：`A` 由取指/load 置位、`D` 由 store 置位；**淘汰/`clean`/`flush` 时回写 PTE**；回写失败 ⇒ `CFXMEM + [56] ADWBFAIL`，`cause_info` = **PTE 物理地址**，失败条目保留；
4. **异常**：未映射/分片缺失 ⇒ `CFXMEM`；HSJU 或 `R/W/X` 不符 ⇒ `CFXPERM`；均进**当前运行模式 monitor**（`§5.2`）；子原因位号从契约取，不写死；
5. **`cfx_ptw` 的执行语义**：`tlb_control` 写即执行（`op`/`scope`/`asidAny`）、`clean`/`invalid` 的**条目级 + 遇错即停**（`TLB-37`）；TLB 侧归 `003`，本任务先让命令在 PTW 侧可解析、可返回错误；
6. **不做 TLB**：本任务每次访存都步查（功能正确性优先），`003` 再加 TLB 并做「有 TLB vs 无 TLB」对拍。

## 验收（逐条贴真实 rc，每条须能 FAIL）

1. `make verilog CONFIG=WumingVastConfig` 能 elaborate、能跑最小镜像（1 页映射 + 取指/读写）；
2. **超页用例**：512 MiB 超页映射下访问页内多个 64 KiB 子页均命中；跨超页边界访问未映射 ⇒ `CFXMEM`；
3. **权限用例**：HSJU 不符 ⇒ `CFXPERM`；`R/W/X` 缺失分别给对应子原因（`NRPERM`/`NWPERM`/`NXPERM`，位号取自契约）；
4. **分片用例**：`frags` 某位为 0 的 64 KiB 页访问 ⇒ `CFXMEM` + 对应分片子原因；
5. **A/D 用例**：首次取指置 A、首次 store 置 A+D；`clean` 后 PTE 的 A/D 被写回；**回写失败**（页表放 BootROM 只读区）⇒ `CFXMEM + ADWBFAIL` 且 `cause_info == PTE PA`；
6. ≥3 路注入（① 索引位宽写错 ⇒ 用例红；② A/D 只置本地不回写 ⇒ clean 用例红；③ 回写失败静默丢弃 ⇒ 用例红），`cp`+md5 还原 + 重建回绿；
7. 与 gem5 对拍：同一镜像在 gem5 `--profile vast` 与 RTL 上**逐指令 trace 一致**（至少覆盖上述 2–5 的用例）。

## 待裁定

（无。PTE 布局/权限/异常码/回写语义均由 spec 与契约钉死；若实现中发现 spec 缺口，登记「待裁定」并**不改 spec**。）

## 裁定（用户 2026-11-20）

**验收第 7 条（与 gem5 `--profile vast` 逐指令对拍）→ 选择 B：移入 `m16-chipyard-011` 三方差分**。

- 本任务按**现有 RTL 侧证据**收尾：31 记录逐位、7 类故障、A/D 恰好 2 次、4 路注入；
- 对拍的落地要求已写入 `m16-chipyard-011` 的任务范围：**「PTW 逐指令对拍：RTL ↔ gem5 同镜像同页表」**，并先做 `tests/arch/` 的多平台签名机制；
- 本任务**不再声称第 7 条已过**，完成区与遗留均如实记录「未做、已移交 011」。

## 完成区

**测试结果**：证据脚本（运行期证据目录内的 `run.sh`）`PASS=…FAIL=0`：A 4/0、B **10/0**、C 1/0、D 7/0、E 4/0、F ①2/0 ②2/0 ③1/0 ④1/0（合计 6/0）、R 4/0；复合 `ONLY=A,B,C,D` **22/0**（分段与复合都实跑；`ONLY=`/`INJ_ONLY=` 可选段）。
**验收结果**（逐条贴真实 rc/事实）：
1. 走查正确性：`vastwalk.S` 在 `WumingVastConfig` 上 `SYS_EXIT(0)`；`check_vastwalk.py` 31 条 8 字节记录逐位相等（普通页 `VA = PA + 2 TiB`、512 MiB 超页两个 64 MiB 片段、经翻译取指落点置标记），大端 PTE 解析由 `gen_vastwalk_tables.py` 独立算出的 PTE 值逐位校验。
2. 故障路径（cause one-hot + 该 cause 独占 wyde 内**一位**子原因，`cause_info` = 访问 VA）：L1 `P=0,SP=0`→`[52] DGPTRAP`；L1 `P=0,SP=1`→`[53] DSPTRAP`；L1 `SPF` 位=0→`[55] DSPFTRAP`；L2 `P=0`→`[52]`；L2 `GPF` 位=0→`[54] DGPFTRAP`；HSJU（U-only/hypv）→`[35] NHPERM`；`W=0` 存→`[37] NWPERM`；`X=0` 取指→`[38] NXPERM`；`tlb_control` scope=`11`→`CFXREG`（wyde 全 0）。
3. A/D：首次读后 PTE 仍 `A=0`（本地挂起）→ `clean` 后 `A=1`；首次 store 后 `D=0`（本地）→ `clean` 后 `A=1,D=1`；再 `clean` 无挂起 ⇒ PTE 不变。宿主按事件计数：同一 PTE **恰好 2 次** `ad-wb`（值依次 `A=1,D=0`、`A=1,D=1`），全程 0 次 `ad-fail`。
4. 可达 FAIL：L2 索引位宽改错 1 位（`VA[28:16]`→`VA[29:17]`）⇒ 首读即 `CFXMEM` 缺页、探针不成活（`cp`+md5 还原 + 强制重编回绿）；另三路注入见「注入」。
5. 不回归：Tiny 首册 38 镜像在改前/改后二进制上 rc 全 0 且结果**逐字节相同**、每例 `cycle=` **完全相同**（md5 同）；`m16-chipyard-012` 的两册 `scmp`（`ftscmp_orrr_rf`/`foscmp_orrr_rf`）chipyard lane `2/2` rc=0 且逐字节相同；Tiny FIRRTL 中 `WumingPtw` 出现 **0** 次。
6. 门控：`check-patch-tree` 整体 rc=1 但 **chipyard 段 0 问题**；红项**现场统计**并按组件列出归属：本轮实测 `chipyard=0`、`chipyard:generators/testchipip=0`、`gem5=8`、`linux=14`（合计 22），`musl`/`busybox`/`picolibc`/`libc-test` 各 0；`gem5`/`linux` 两段的红项来自并行任务（`m16-gem5-018` 重建 gem5、`m14-linux-025` 改 linux 补丁集）的**在途工作树**，非本任务，且这两个数会随它们推进而变（第 1 轮复核期实测 14/15）⇒ 本任务只对 chipyard 段负责；`check-index-blobs` rc=0；`check-gem5-decode`（decode 表重生成比对）rc=0；补丁数 23→**24**（新增 `WumingPtw.scala.patch`）。
**注入**（真实重编后观测，`cp`+md5 还原 + 强制重编回绿）：① L2 索引位宽错 ⇒ 探针/仿真红；② A/D 只本地不回写（OR 不带挂起位）⇒ `SYS_EXIT(3)`；③ 强制 PTE 写失败（核不发写、直接按失败完成）⇒ 探针记录 `CFXMEM [56] ADWBFAIL` + `cause_info = 0x10030`（PTE PA），判据 `--expect-adwb` **rc=0**、同一流在默认期望下 **rc=1**（两侧都判）；④ ③ + 静默丢弃 ⇒ 同一判据 **rc=1**（用例红）。
**修改文件**：`components/chipyard/patches/…`（8 份重导 + 新增 `WumingPtw.scala.patch`，`series` 24 行；子模块补丁不变）；`components/chipyard/README.md`（新增本任务一节）；新增 `tools/chipyard/ptw/{vastwalk.S,vastwalk.lds,gen_vastwalk_tables.py,check_vastwalk.py}`；任务书。
**新发现/坑**：① chipyard 的 classpath 缓存与 Verilator 模型目录都**不以源码/.sv 为依赖** ⇒ 还原注入后必须删掉 `generated-src/chipyard.harness.TestHarness.<CONFIG>/chipyard.harness.TestHarness.<CONFIG>.fir` 与同名**模型目录**再重建（**两级名都带完整 `chipyard.harness.TestHarness.` 前缀**；第一版脚本漏了前缀 ⇒ 删除恒为空操作，「强制重建」形同虚设，见「返工 1」）；② `Cat` 高字节在前：A/D 位序写反时回写把 A 写成 D（探针第 3 点当场抓出）；③ Decoupled 的 A 通道不能用「同拍赋值的寄存器」驱动（会发上一条地址）；④ Tiny 上 `ptw.get` 在 Mux 里仍被求值 ⇒ `None.get`（elaborate 失败），必须整块 `if (useVM)`；⑤ Vast 的 PA RAM 不能走 AXI4+`SimDRAM`（`+loadmem` 同时喂 fesvr，非 RISC-V ELF 断言；TL→AXI 单拍写还触发 ToAXI4 计数断言）⇒ 改 TileLink 从端口；⑥ 把 `[0,2 GiB)` 腾给 PA RAM 要移开/去掉一批 RISC-V 外设（CLINT/PLIC/LLC/EICG/debug/bus error/UART/boot-addr/PRCI/tile-reset），改配置片段时必须确认落在 **Vast** 片段（本任务一度误落 Tiny 片段）；⑦ 探针数据页要做「页表自映射读」才能在不换出的情况下看内存里的 PTE（同 64 KiB 页、+8 偏移即该页 PTE）。
**遗留问题**：① **与 gem5 `--profile vast` 的逐指令对拍未做**（验收 7）——**本任务不声称该项已过**，验收标准的削减/改由 `m16-gem5-*` 先落对齐入口，均**须用户裁定**（architect 已在「待裁定」段登记）；理由：gem5 Vast 的装载/入口路径与 RTL 探针（核内 SRAM 起步 + `+loadmem` 装 PA）不同，需要单独一条对齐的镜像与进程，未在本任务时间盒内完成；② Vast BootROM 仍是 **64 KiB @`0xffff_ffff_0000`**（`spec/Kaiwu §1.1` 为 4 MiB @`0xffff_ffc0_0000`），随「大存储/地址图」任务；③ 无 I/D TLB（`m16-chipyard-008`）、无 cache（`009`/`010`）：走查器只有一个直通槽/侧，且 Vast 不发射投机预取；④ `ADWBFAIL` 的机器级路径仍不可达（PA RAM 全可写，`contract-tlb §11` ⑦ 已声明由实现层注入覆盖——本任务按此执行）；⑤ `call` 溢出/`ret` 回填等 MemRAS 路径经翻译时按「逐拍翻译 + 跨页重走查」实现，跨页中途失败的精确性与既有 `ldm`/`stm` 口径一致（非精确，软件可重入整条指令）。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：`WumingPtw.scala`（走查 FSM/PTE 解码/权限与子原因/A/D 与回写/命令）、`WumingCore.scala`（`sXlate`、取指与数据路由、逐拍翻译、`tlb_control` 编码校验、`enterHmonSub`）、`WumingParams.scala`/`WumingTile.scala`/`WumingLoadMem.*`/`DadaoConfigs.scala`（PA RAM 与地址图搬迁）、探针与判据、证据脚本。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `orValue` 把 A/D 位拼反（`Cat` 高字节在前）⇒ clean 回写把 A 写成 D | ✅已修 | `Cat(pte(63,4), aPend‖pte(3), dPend‖pte(2), pte(1,0))` | 探针第 3 点由红转绿；`ad-wb` 值 `…ffe9`/`…ffed` |
| F2 A 通道地址来自「同拍赋值的寄存器」⇒ 回写发到上一条请求的地址 | ✅已修 | A 通道改为状态组合驱动（`aPa`/`aWrite`），应答侧用 `sentPa` | 回写后读回 PTE 与新值一致（第 3/5 点） |
| F3 `enterHmonSub` 把子原因**索引**当 wyde one-hot 传给 `GewuCauseId.encode` ⇒ 帧写点具名致命 | ✅已修 | 传入 `(1.U << sub)(15,0)` | `GewuFile` well-formed 断言不再触发，9 类故障逐条正确 |
| F4 Tiny 上 `ptw.get` 在 `Mux` 里被求值 ⇒ `None.get`（Tiny elaborate 失败） | ✅已修 | 整块 `if (params.useVM) {…} else {…}` | Tiny `make verilog`+`make` rc=0、`%Error`=0 |
| F5 设备搬迁片段一度误落在 **Tiny** 的地址图里（会把 Tiny 的 CLINT/PLIC 等移走） | ✅已修 | 移回 `WithDadaoVastAddressMap` | Tiny 首册 38 镜像逐字节/逐例周期不变 |
| F6 证据脚本的重建走 chipyard 缓存 ⇒ 还原后仍跑注入版（假红/假绿各一次） | ✅已修 | `rebuild()` 先删 `.fir` 与 Verilator 模型目录 | 还原后 R 段探针 rc=0、判据 rc=0；注入段每路都是新生成物 |
| F7 探针把 L2B 组 VA 写成 `2 TiB + PA`（落进普通页表区）⇒ 故障例「无异常却过」 | ✅已修 | 改为 `VA = 6 << 29` 段，并在每个故障例前清帧槽（未发生 ⇒ 记录 0） | 9 类故障的 cause/info 逐条正确 |
| F8 `ADWB_ONLY` 镜像沿用带 ASSERT 的链接脚本 ⇒ 标号缺失链接失败 | ✅已修 | 该镜像用去掉 ASSERT 的同一 `.lds` 派生 | `vastadwb.elf` 链接成功、判据 3 记录 |
| F9 强制写失败注入把请求挂在总线上（不消费 D）⇒ 后续取指卡死 | ✅已修 | 注入改为「不发写、直接按失败完成」 | ③ 记录 `ADWBFAIL` + `info=0x10030`，探针正常退出 |

### 第 1 轮 reviewer 验收

**重跑（我自己的命令/输出/退出码，非采信完成区）**
1. `ONLY=A,B,C,D` 跑运行期证据目录内的 `run.sh` → `PASS=20 FAIL=0`、`RUN_EXIT=0`（31 记录逐位、`ad-wb`=2、`ad-fail`=0、Tiny FIRRTL `WumingPtw`=0、`--self-test` 19 条断言均有可达 FAIL）；但该次 Vast 重建日志实为 `make: Nothing to be done for 'verilog'`（见「脚本缺陷」）。
2. 我**自行强制重建**（删 `.fir`+模型目录后 `make verilog` rc=0、`make` rc=0、`%Error`=0，`.fir` 由源码重新 elaborate）→ `ONLY=D` → `PASS=7 FAIL=0`、`check_vastwalk: 31 record(s) match (A/D write-backs 2, no failure)`、同一 PTE `ad-wb`=2（值 `…ffe9`→`…ffed`）、`ad-fail`=0。
3. `ONLY=E` → `PASS=4 FAIL=0`、`E_EXIT=0`：首册 38/38 镜像 rc 全 0、结果逐字节相同（`diff` rc=0）、`cycle=` 逐条相同；`scmp` 两册 before/after `diff -r` rc=0。
4. 门控：`check_patch_tree.py` rc=1 但 chipyard 段 assertion=0、现场补丁数=24；`check_index_blobs.py` rc=0（一次 rc=1 后立即重跑 rc=0，未见与本任务相关的改动）；`gen_decode_table.py --check` rc=0。
5. 工程师脚本 `--inject INJ_ONLY=3` → `PASS=1 FAIL=0`、`F3_RC=0`（ADWBFAIL 帧 + `cause_info`=PTE PA 判据过），还原后 md5 复原。

**我的 4 路注入（`cp`+md5 还原、每路强制重建、回绿）**
① L2 索引 `VA[28:16]→VA[29:17]` → `D_RC=1`（探针 134、判据 2 problems、`ad-wb` 0）→ 还原重建 `D_RC=0`。
② A/D 回写只置 A 不置 D → `D_RC=1`，判据 `second write-back value …ffe9 != …ffed (A=1,D=1)`、探针 `SYS_EXIT(5)` → 还原重建 `D_RC=0`。
③ SPF 判断取反（`fragOk ^ superpage`）→ `D_RC=1`，日志 `excp cause=0x0080000000000002`（[55] DSPFTRAP）、`info=0x0000020040000000`（超页 VA）→ 还原重建 `D_RC=0`。
④ L1 索引 `VA[41:29]→VA[40:28]` → `D_RC=1` → 还原重建 `D_RC=0`，`.fir` 恢复 `bits(reqVa, 41, 29)`。

**硬口径核验**：L1=VA[41:29]、L2=VA[28:16]、64 KiB 页、SPF 按 `8+VA[28:26]`、GPF 按 `8+VA[15:13]`、PTE 8 字节大端（`addressOrder` 字节反转）、VA=PA+2 TiB、A/D 本地 + `orValue` 原子 OR，与 `DADAO-12 §2.2.1–§2.2.6` 一致；子原因 [52]/[53]/[54]/[55]/[35]/[37]/[38]/[56] 与 `§3.6` 逐条对上、HSJU 无隐含放宽（`§2.2.5`）、cause_info 取访问 VA、仅 ADWBFAIL 取 PTE PA。
**约束核验**：不改代码、不提交；收尾快照 `git status -uall`=0 行、chipyard 源码树干净、`WumingPtw.scala` md5=基线、无 `.preinject`/`.bak` 残留；术语「寄存器组」。

**地址图改造判定**：① `+loadmem` 两窗口实测可用——探针 9 个 PT_LOAD 同时落核心内 SRAM 与 PA RAM（含 1 GiB/1.06 GiB 两处），装载后 7925/7925 字回读逐字节相同；② 移址/去除的外设不挡 TLB/cache/三方差分（CLINT/PLIC 保留仅移址，LLC/EICG/debug/UART/bus-error/boot-addr/serial-TL 去掉），但 **Vast 侧已无 debug/UART**，后续若需须重新面对与 PA RAM 的地址冲突，应在相关任务书登记；③ 属多方案+跨模块+高代价+结论固化 ⇒ **建议补 ADR**（提请用户裁定，我不代决）。

**脚本缺陷（阻断）**：`run.sh` 的 `rebuild()` 两条 `rm` 目标名少了 `chipyard.harness.TestHarness.` 前缀 ⇒ 恒为空操作，完成区「坑①：必须删 `.fir` 与模型目录」与实现不符；实测只 `touch` 源码 `make verilog` 仍会重 elaborate（故其注入证据仍有效），但「强制重建」这一保障不存在，且无改动时 B 段打印 `Nothing to be done` 即绿、`%Error` 检查对 40 字节日志恒过。修法：改正两条 `rm` 路径，并在 B 段断言 `.fir`/模型目录 mtime 晚于本次运行。

**遗留判定**：验收第 7 条（与 gem5 `--profile vast` 逐指令对拍）**未做 ⇒ 构成验收缺口**；理由（装载/入口路径不同）成立但不改变「未验证」，应由 `m16-gem5-*` 先落对齐入口、收口任务补对拍；**验收标准的削减须用户裁定**，本审查不代决。

**文档级 finding（不阻断）**：完成区写「check-patch-tree linux 段 12 条」，其自跑 14 条、我跑 15 条，且 gem5 段 8 条未披露 ⇒ 交 architect 收尾改。

**判决：Needs Revision** —— 阻断项：① 证据脚本 `rebuild()` 强制重建失效（见「脚本缺陷」）；② 验收第 7 条未执行，须 architect/用户裁定补做或改验收。验收第 1–6 条在我自己的重跑与 4 路注入下全部通过。

**返工 1（第 1 轮 reviewer：Needs Revision）**
- **阻断 1 ✅ 已修（证据脚本的强制重建）**：`rebuild()` 的两条 `rm` 目标名改成完整前缀 `chipyard.harness.TestHarness.<CONFIG>`（`.fir` 与同名模型目录），并把删除结果（`fir=`/`model=`）与本次开始时间戳落盘；新增 `rebuild_problems()`，B 段逐条硬判：**删除发生**、`.fir` 与模型 `VTestDriver.mk` 的 mtime **晚于本次开始**、`make verilog`/`make` 日志**不含 `Nothing to be done`**，另现场打印构建日志字节数（防「40 字节日志恒过」）。
- **可达 FAIL 证明**：把两条 `rm` 路径改回漏前缀的旧名 ⇒ `ONLY=B` 红，`Vast 强制重建真的发生 … actual=fir-not-deleted model-not-deleted fir-stale(…) model-stale(…) elab-noop sim-noop`、`[INFO] Vast 构建日志 40 字节，含 Nothing to be done=1`、`Tiny … fir-not-deleted model-not-deleted`（`PASS=8 FAIL=2`）；`cp`+md5 还原后 `ONLY=B` 回绿（`PASS=10 FAIL=0`，Vast 构建日志 59924 字节、`Nothing to be done`=0、两个删除标记均为 1）。
- **阻断 2（不归本任务）**：验收第 7 条未做 ⇒ 验收标准削减须用户裁定（architect 登记在「待裁定」）；本任务**未做对拍、也不声称该项已过**。
- **文档级 ✅ 已修**：门控红项改为**现场统计 + 逐组件归属**（`chipyard=0`/`testchipip=0`/`gem5=8`/`linux=14`，并说明两个数会随并行任务变化），坑① 与实现逐字对齐（点名完整前缀）。
- **复跑（返工 1 后的真实输出）**：`ONLY=A,B,C,D` → `PASS=22 FAIL=0`（rc=0），其中 Vast 强制重建报告 `删 .fir+模型目录` 标记均为已删、`.fir`/`VTestDriver.mk` mtime 晚于本次开始、构建日志 **59924 字节**且 `Nothing to be done`=0，Tiny 同（90157 字节、no-op=0）；`ONLY=D` → `PASS=7 FAIL=0`（`31 record(s) match`、`ad-wb`=2、`ad-fail`=0）；`ONLY=E` → `PASS=4 FAIL=0`（38/38、逐字节相同）；`ONLY=R` → `PASS=4 FAIL=0`（还原后重建回绿）；`--inject` 四路 → `PASS=6 FAIL=0`（① 2/0、② 2/0、③ 1/0、④ 1/0），每路都走「注入→强制重建→观测→`cp`+md5 还原」。

### 第 2 轮 reviewer 验收

**阻断 1 —— 我自己复现可达 FAIL（不采信其记录）**
- 读脚本：`rebuild()` 与 `rebuild_problems()` 的 `tgt` 均为 `chipyard.harness.TestHarness.<CONFIG>`，两条 `rm` 目标即 `<gen>/<tgt>.fir` 与 `<gen>/<tgt>/`；删除结果与开始时刻落 meta；判据 6 条可失败（`fir-not-deleted`/`model-not-deleted`/`fir-stale`/`model-stale`/`elab-noop`/`sim-noop`），meta 缺失输出非空即 FAIL；B 段 `eq "" "$vb"`；日志字节数与 `Nothing to be done` 计数现场打印。
- 反例注入：把两条 `rm` 改回漏前缀旧名（注入前 `cp`+md5=`6869e2f3…`）→ `ONLY=B` → **`PASS=8 FAIL=2`、rc=1**，actual=`fir-not-deleted model-not-deleted fir-stale(mtime=1795131774<start=1795131968) model-stale(…) elab-noop sim-noop`，`[INFO] Vast 构建日志 40 字节，含 Nothing to be done=1`（Tiny 同）。
- 还原（md5 相等）→ `ONLY=A,B,C,D` → **`PASS=22 FAIL=0`、rc=0**：强制重建 actual=空、`[INFO] Vast 59924 字节 Nothing=0`、`Tiny 90157 字节 Nothing=0`、`31 record(s) match (A/D write-backs 2, no failure)`、自检 19 条断言均有可达 FAIL。

**回归（我亲跑，真实 rc）**：`ONLY=D` → `7/0` rc=0（31 记录、`ad-wb`=2、`ad-fail`=0）；`ONLY=E` → `4/0`、`E_EXIT=0`（38/38 镜像 rc 全 0、`diff` 逐字节相同）；`--inject` 四路 → **`6/0`、rc=0**（①134 与 11726、②3 与 3、③rc=0、④rc=1 且判据抓出 `record 1/2` 不符）；按脚本第 24 行新增用法警告补跑 `ONLY=R` → `4/0` rc=0，离开「源码已还原、二进制未重建」中间态。全程 `WumingPtw.scala` md5=`4f0b34ba…`、无 `.preinject`/`inject.bak` 残留（我的脚本备份已清理）。

**文档表述**：完成区第 6 条已改**现场统计 + 逐组件归属**，我实测同值 `chipyard=0`、`chipyard:generators/testchipip=0`、`gem5=8`、`linux=14`（合计 22），`llvm-project`/`qemu`/`musl`/`busybox`/`picolibc`/`libc-test`/`embench-iot` 各 0，并写明两个数随并行任务在途变化（第 1 轮实测 14/15）；坑① 与实现逐字对齐（点名完整 `chipyard.harness.TestHarness.` 前缀，并承认第一版漏前缀）。

**阻断 2 记录一致性（不归本轮判定）**：遗留①如实写「未做 … 本任务不声称该项已过 … 须用户裁定（architect 已在「待裁定」段登记）」，全文无「对拍已过」表述 ✓。

**约束核验**：本轮未改 RTL/补丁/工具（`git diff --name-only` 空、`git status -uall`=0 行）；只跑证据脚本与其反例注入；术语「寄存器组」；审阅记录无运行期路径。

**判决：Accepted** —— 阻断 1 已真修并由我的反例注入证否/证真各一次（注入 `PASS=8 FAIL=2` rc=1 → 还原 `PASS=22 FAIL=0` rc=0）；`22/0`、`7/0`、`4/0`、`6/0`、`4/0` 全部在我重跑下复现；阻断 2 如实记录待用户裁定。
