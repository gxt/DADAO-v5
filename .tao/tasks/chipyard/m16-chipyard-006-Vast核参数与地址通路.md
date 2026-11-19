# m16-chipyard-006: Kaiwu-Vast 核参数与地址通路（地基）

**已恢复（用户 2026-11-19 反悔）：WumingVast 继续开发；下方「暂停与可复用清单」仍然有效**

**模块**：chipyard
**项目里程碑**：M16
**依赖**：无（本任务先做地基）；后续 `m16-chipyard-007`（PTW）、`m16-chipyard-008`（TLB）依赖本任务
**可并行分片**：否（改 `dadao-wuming` generator + `DadaoConfigs.scala`）
**预估**：2–3 天
**档位**：大改
**状态**：待验收

## 背景

`WumingTinyConfig` 是唯一能 elaborate 的 DADAO 配置：`useVM = false`、`WumingCompatCoreParams` 里 `useVM=false`/`pgLevels=3`（RISC-V 残留）/`nL2TLBEntries=0`，核内**没有 PTBR/ASID/`ptw_enable`**，也不访问 `cfx_ptw`；取指/访存直连 `imem`/`dmem`。Vast 要在此基础上换掉整条地址通路。

**用户已定口径（2026-11-19）**：只设一级 TLB、分 I/D；普通页 16 条 = 2 组 × 8 路、不设 sectored；超页 4 条全相联 + LRU；无特殊条目；I-TLB 无 dirty 位；gem5 与 chipyard 在这些方面保持统一。

## 目标

1. **新增 `WumingVastConfig`（及 `WumingVastParams`）**：不破坏 `WumingTinyConfig`（Tiny 的全部既有向量与 md5 判据必须不变）；
2. **`useVM = true` 的核参数**：`WumingCompatCoreParams.useVM`、`pgLevels` 按 DADAO（2 级）语义处理（若上游字段不可改，则显式注释「字段保留、语义不用」）；
3. **核内三个新状态**：`PTBR`、`ASID`、`ptw_enable`，来源 = `cfx_ptw`（cg12 rc0–rc3）；
4. **地址路由**：`addr[47:42] ≠ 0` ⇒ 核内空间（不走 PTW/TLB）；`= 0` 且 `ptw_enable=0` ⇒ `CFXMEM`（子原因 `[57] NONPTW`）；`= 1` ⇒ 进 TLB/PTW（本任务先直连「步查器占位」= 未映射 ⇒ `CFXMEM`）；
5. **`cfx_ptw` 寄存器面**：`cg12 rc0 = tlb_control`（WO、写即执行）、`rc1 = tlb_asid`（`[15:0]`，`[63:16]` 读 0）、`rc2 = tlb_addr_start`（`VA[41:0]`）、`rc3 = tlb_addr_size`；本任务只做**寄存器与读回**，执行语义归 `003`；
6. **行为等价兜底**：`ptw_enable = 0` 时 `WumingVastConfig` 的行为应与 Tiny **逐条一致**（可用 Tiny 的既有向量回归）。

## 验收（逐条贴真实 rc，每条须能 FAIL）

1. `make verilog CONFIG=WumingTinyConfig` + `make CONFIG=WumingTinyConfig` ⇒ **Tiny 的 sim md5 与行为不变**（跑既有 `tests/inst` 首册冒烟）；
2. `make verilog CONFIG=WumingVastConfig` + `make CONFIG=WumingVastConfig` ⇒ 能 elaborate、能跑一个最小镜像（`ptw_enable=0` 路径）；
3. **寄存器面构造用例**：读 `cg12 rc1` 的高位为 0、`rc0` 写不报错；`rc2/rc3` 可读回；
4. **路由用例**：`addr[47:42]≠0` 的访存不走 PTW；`ptw_enable=0` 的用户地址 ⇒ `CFXMEM + NONPTW`（子原因位号现场取自 `ADR-0056`/`contract-see`）；
5. ≥2 路注入（① `ptw_enable` 恒 1 ⇒ 路由用例红；② `CFXMEM` 子原因位号写错 ⇒ 用例红），`cp`+md5 还原 + 重建回绿；
6. 术语「寄存器组」；任务书自包含。

## 待裁定

（无。TLB/PTW 结构已由用户裁定；`pgLevels` 的上游字段若与 DADAO 两级冲突，按「字段保留 + 注释」处置，不擅自改上游参数语义。）

## 暂停与可复用清单

**暂停（用户 2026-11-19）：WumingVast 不做，转 wuqing 路线。** 本任务停在此处，不再改代码、不再重建；下列清单供 wuqing 路线取用。

### A. 已实现并验证过的部分（精确到文件 / class / 字段）

1. **`cfx_ptw` 寄存器面** — `generators/dadao-gewu/src/main/scala/gewu/GewuFile.scala`：
   - `case class GewuPtwParams(cfxId: Int)`；`GewuParams.ptw: Option[GewuPtwParams] = None`（含 `require`：`ptw.cfxId` 必须是已实现 cfx）
   - `class PtwState(dataBits: Int) extends Bundle`：`enable`/`ptbr`/`tlbAsid`/`tlbAddrStart`/`tlbAddrSize`/`tlbControl`/`tlbControlData`；`io.ptw: Option[PtwState]`
   - `private class PtwRegs`：`enable`(1 位)、`ptbr`(40 位 = `PPN[55:16]`)、`asid`(16 位)、`addrStart`(42 位)、`addrSize`(64 位)、`control`/`controlData`(WO 写成「一拍脉冲」)
   - `private class PtwRows`：六行解码 `isEnable`(cg8 rc8)/`isPtbr`(cg9 rc0)/`isControl`(cg12 rc0)/`isAsid`(cg12 rc1)/`isStart`(cg12 rc2)/`isSize`(cg12 rc3) + `anyRead`/`anyWrite`/`isCfx`
   - 读回 `ptwRdata`（PTBR 读回 `[63:56]=0, [55:16]=PPN, [15:0]=0`；ASID/start 高位补 0；`tlb_control` 不在读集 ⇒ 读为 CFXREG）；写块 `for { rows <- ptwRows; regs <- ptwRegs } { … }`；输出 `for (b <- io.ptw; r <- ptwRegs) { … }`
   - 行号取自 `DADAO-12 §4.5` 专有寄存器表，与 `contract-tlb` TLB-03/TLB-04 一致
2. **无内部空间 cfx 的通用处置** — 同文件：`spaceStart`（`spaceDesc & 1 == 0 ⇒ 0`）、`anySpaceMissing` 门控的 `cg7Rdata`（`exists=0 ⇒ start/size/attr` 读 0）
3. **地址路由** — `generators/dadao-wuming/src/main/scala/wuming/common/WumingCore.scala`（Wuming 专用）：`private val ptwEnable = gewu.io.ptw.map(_.enable).getOrElse(false.B)`；`private def memWindow(x) = x(47, 42) === 0.U`；`private def inSpecWindow(x)`（原三窗测试改名）；`private def specBacked(x) = if (params.useVM) !memWindow(x) && inSpecWindow(x) else inSpecWindow(x)`；`def enterMemFault(addr, isFetch)`：`!memWindow || !ptwEnable ⇒ CFXMEM + [57] NONPTW`，否则取指 `[48] IGPTRAP` / 数据 `[52] DGPTRAP`（`ptw_enable=1` 步查占位的「未映射」报法，`contract-tlb §11 ⑨b`），`!params.useVM` 时一律 NONPTW（Tiny 原行为）；调用点 6 处（取指、`call` spill、`ret` MemRAS、`lr`、`sc`、`ld/st/ldm/stm`）
4. **机级参数与配置** — `WumingParams.scala` / `DadaoConfigs.scala`：`WumingCoreParams.useVM: Boolean = false`（本核自己的字段，非 rocket 的）；`WumingCompatCoreParams` 的 `useVM = false` 与 `pgLevels = 3` 两处标「字段保留、语义不用」；`WumingCfxHa.ptw = 4`；`WumingGewuParams` 里 `ptw = if (p.useVM) Some(GewuPtwParams(4)) else None` 并按 `useVM` 追加 `cfx_ptw` 的 `GewuCfxParams`（`spaceDesc = 0`）；`object WumingVastParams`（`useVM = true`）、`object WumingVastAddressMap`、`class WithDadaoVastAddressMap`、`class WumingVastConfig`
5. **判据与探针** — `tools/chipyard/ptw/`：`check_vastptw.py`（位号**现场**从 `contract-see §6.1.1` 解析并与 `ADR-0056 D2` 互校，19 记录逐位比对 + wyde 结构规则 + `--self-test` 12 条反例）；`vastptw.S`/`vastptw.lds`（11 个寄存器/核内检查点 + 4 个故障用例，链接脚本回读校验 `aip` 偏移）

### B. 与核无关、wuqing 可直接复用

- **`cfx_ptw` 寄存器面整块**（A.1 + A.2）：`GewuPtwParams`/`PtwState`/`PtwRegs`/`PtwRows`/`ptwRdata`/写块/`io.ptw` 输出。只依赖 `GewuParams`（cfx 表 + `dataBits`），不碰取指/访存、不假设核的地址位宽；**`cg8 rc8`(enable) / `cg9 rc0`(PTBR) / `cg12 rc0–rc3`(tlb control·asid·addr_start·addr_size) 逐行照 `DADAO-12 §4.5`**，任何核都能接。
- **`Option` 开关范式**：`gp.ptw = None` ⇒ 行解码/状态/端口全部不生成、该 cfx 行按 CFXREG 处理、RTL 零增长（Tiny 侧现场核过：`ptw` 计数 0）。wuqing 若不必每台机都有 PTW，可原样沿用。
- **判据的位号现场解析**（`contract_table`/`adr_table`/`bit_table`）：与核无关，换探针也能用。
- **探针的寄存器面 11 个检查点**（`cg8 rc8` 复位/写 1/写 0、`cg9 rc0` 掩码、`cg12 rc1·rc2` 宽度、`cg12 rc3` 全程往返、`tlb_control` 两写、`cg7` 两块读 0）可搬进 wuqing 的探针（改 `cfxha` 与返回槽即可）。

### C. 作废（Wuming 专用，暂停后不再维护）

- `WumingCore.scala` 的整条路由改造（A.3：`ptwEnable`/`memWindow`/`specBacked` 的 `useVM` 分支/`enterMemFault` 与 6 处调用点）——绑死 Wuming 的 `sFreq`/`sExec`/`sMreq` 状态机与三条核内窗，wuqing 不能直接挪。
- `WumingCoreParams.useVM` 字段、`WumingVastParams`、`WumingVastAddressMap`/`WithDadaoVastAddressMap`/`WumingVastConfig`（含 `kaiwu-vast-*` device 名）、`WumingGewuParams` 里「`useVM` ⇒ 追加 `cfx_ptw`」的分支。
- 本任务的 Tiny/Vast 回归口径（首册 38 镜像逐字节、`ptw` 计数 0）只对 Wuming 有效。

### D. 已知未完成项（暂停时现状）

- **reviewer 阻断 B1 — 已修（返工 1）**：审阅记录 F7 行改为运行期措辞，具体 `.work/**` 路径已删 ⇒ `make check-knowledge-refs` 本分支 rc=0、具体路径 0（详见完成区「返工 1」）。
- **reviewer 阻断 B2 — 已修（返工 1）**：证据脚本 B 段删掉恒真断言，改为两条现场可判据（路由谓词现场计数、`CFXMEM` 三个原因字现场解析位号后比对）；已用「删掉路由分支 ⇒ 重建 ⇒ 红」证明可达 FAIL（详见完成区「返工 1」）。
- 非阻断 finding a–e **未处理**（暂停前记录，仍原样）：目标 3 括注笔误、R 段不重建 Tiny、4 条 `%Error` 读旧日志、探针「写全 1」激励验不了切片位置、A 段 `check-patch-tree` 只断言 chipyard 段。
- 功能面未做：Vast 物理半边（4 MiB BootROM + 2 GiB PA RAM）、`ptw_enable = 1` 的真实两级步查、TLB（原计划归 `m16-chipyard-007`/`008`；本任务只有「未映射」占位）。
- 已验证现状（供接手判断）：证据脚本 A–E+R+G `PASS=58 FAIL=0`；注入 `PASS=25 FAIL=0`；首册 38 镜像「改前 / 改后 / Tiny vs Vast」三组逐字节 0 差异；Tiny RTL `ptw` 计数 0；Vast `make verilog` + `make` rc=0、`%Error`=0。

## 完成区

**测试结果**：证据脚本（运行期证据目录内 `run.sh`）A–E+R+G 全绿 `PASS=59 FAIL=0`（返工 1 后：删 1 条恒真断言、加 2 条真判据；返工前为 58/0）；注入段 `PASS=25 FAIL=0`（返工 1 未改注入段，故未重跑）。
**验收结果**（逐条，真实 rc 见运行期日志目录）：
1. Tiny 不回归：首册 38 镜像在改前二进制 `df16728e…`、改后 `6172527f…`、最终重建上各 38/38；三方结果字节流逐镜像相同（38 镜像 / 6128 B，差异 0）。Tiny 的 FIRRTL 与 SV 里 `ptw` 计数 = 0（本特性零增益）。md5 只作记录：同一源码重建即变（`ISS-453`），身份判据取行为。
2. Vast：`make verilog WumingVastConfig` + `make WumingVastConfig` 均 rc=0、`%Error`=0，sim `0d699e30…`；最小镜像（首册 38/38 + 探针）全部走 `ptw_enable = 0` 路径。
3. 寄存器面 9 个检查点逐位相等（enable 0/1/0、PTBR 写全 1 读 `0xffffffffff0000`、ASID 读 `0xffff`、start 读 `0x3ffffffffff`、size 整 64 位往返、`rc0` 两写不报错、`cg7` 读 0）。
4. 路由 4 例：`ptw_enable=1` 数据 `CFXMEM`+`[52]`、取指 `[48]`；`=0` 数据/取指均 `CFXMEM`+`[57] NONPTW`，`cause_info` = 被访问 VA；`ptw_enable=1` 时 hmon SRAM 读写照常（`addr[47:42]≠0` 不进 PTW）。位号现场取自 `contract-see §6.1.1` 并与 `ADR-0056` 互校。
5. 注入 3 路（`ptw_enable` 恒 1 / 子原因改 `[54]` / `addr[47:42]` 判据恒真）各「重建→红→`cp`+md5 还原→重建→绿」，还原后流与参考逐字节相同。
6. 术语「寄存器组」；任务书自包含。
**修改文件**：`components/chipyard/patches/…/{DadaoConfigs,GewuFile,WumingCore,WumingParams}.scala.patch`（4 份重导，补丁数 23、`series` 同步）；新增 `tools/chipyard/ptw/{vastptw.S,vastptw.lds,check_vastptw.py}`；任务书（含 007/008 旧编号引用改号）。
**新发现/坑**：① rocket `CoreParams.useVM=true` 与 DADAO 42 位 VA/56 位 PA 不相容（`BaseTile.vaddrBits` 要 VA>PA、`Core` 要 `pgLevels≥3`）⇒ 语义放本核 `useVM`，compat 字段与 `pgLevels` 注「字段保留、语义不用」；② 无内部空间的 cfx 令 `spaceStart` 为负 ⇒ `exists=0` 取 0；③ `Bool.pad` 不可用 ⇒ `Cat`；④ 特性须按参数生成，否则 Tiny RTL 也变；⑤ `/tmp` 是共享 tmpfs，被并行构建占满时会截断 `cp` 备份并清空源文件（已从 HEAD 恢复并加校验收敛）；⑥ `make_patch` 磁盘满时会写空 `series` 并非零退出 ⇒ 加「series 行数 == 补丁数」门控；⑦ `set.rd` 立即数 >64 位静默截断 ⇒ 探针立即数 ≤16 位十六进制。
**遗留问题**：Vast 的物理半边（4 MiB BootROM + 2 GiB PA RAM、`ptw_enable=1` 真实步查）随 `m16-chipyard-007`；本任务 `ptw_enable=1` 是「未映射占位」（按 `contract-tlb` ⑨b 报缺失类），Vast 暂复用 Tiny 的核内三窗（device 名 `kaiwu-vast-*`）。`trap cfx_ptw` 仍按既有 GAP 报 ILLI。

**返工 1（2026-11-19，收 reviewer 第 1 轮两条阻断）**：
- **B1 ✅ 已修**：审阅记录 F7 行的具体 `.work/**` 路径已删，改为运行期措辞 ⇒ `make check-knowledge-refs` **rc=0**（`具体路径 (不可复现): 0`、悬空 0）。
- **B2 ✅ 已修**：证据脚本 B 段删掉恒真断言（原 `grep -q 'WumingCore'`），改为两条现场可判据——① 每个故障点的路由谓词 `(|(addr[47:42])) | ~io_ptw_enable`（= `!memWindow || !ptwEnable`，现场计数 **4** 处）；② `CFXMEM` 三个原因字（`1<<1 | 子原因位`，位号现场从 `contract-see §6.1.1` 解析并互校 `ADR-0056`）在 RTL 中齐全（**3/3**）。
- **B2 可达 FAIL 证明**（删实现 ⇒ 红）：删掉 `enterMemFault` 的路由分支（并顺手把取指缺失类改成 `ISPTRAP`）→ 重建 → `route predicate sites = 0`、cause words `2/3`、`PASS=9 FAIL=5`、**rc=1**；`cp`+md5 还原（md5 相等）→ 重建 → `PASS=14 FAIL=0`、**rc=0**、组件源树 `git status` 空。
- **合并态（`git merge master` → `8962a12e`）后重跑**：全量证据脚本 `PASS=59 FAIL=0`、rc=0；合并后重建 Tiny（elab/sim rc=0、`%Error` 0/0）再跑首册 ⇒ **38 镜像 0 差异 / 6128 B**、38/38；Tiny vs Vast 同 0 差异；Vast 真 elaborate（touch 内容不变的源后）elab/sim rc=0、`%Error` 0/0，探针 19 记录判据 PASS（`ONLY=B,D` 19/0）。
- **门控**：`check-knowledge-refs` **0**、`check-index-blobs` **0**、`check-idl-sync`（render）**0**；`check-patch-tree` 整体 rc=2 但 **chipyard 段 0 问题**（linux 25 + gem5 8 项；同一时刻 master 上为 chipyard 8、linux 0 —— 共享组件源树跨分支并发所致，非本任务）。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：`GewuFile.scala`（ptw 状态/行解码/读回/写/输出）、`WumingCore.scala`（`ptwEnable`/`memWindow`/`specBacked`/`enterMemFault` 与 6 处调用点）、`WumingParams.scala`（`useVM`/`pgLevels`/`WumingVastParams`/`WumingGewuParams`）、`DadaoConfigs.scala`（Vast 地址图与 config）、探针与判据、证据脚本。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `GewuFile` 无条件建 `cfx_ptw` 寄存器 ⇒ Tiny RTL 增死逻辑（md5 变、FIRRTL 出现 `ptw`） | ✅已修 | 状态/行解码/读回/写全部改成 `gp.ptw.isDefined` 驱动的 `Option` 块；`io.ptw` 也是 `Option[PtwState]` | Tiny FIRRTL/SV `ptw` 计数 = 0（B 段两断言） |
| F2 `cfx_ptw` 的 `cg7` 读会被 ptw 读路径截走（返回 0 而非 base 数据） | ✅不修（已核：`PtwRows.isCfx` 是六行解码的或，非「ha 命中」） | — | 探针检查点 8/9 走 base 路径读出 0（`exists=0` 规则），cfg 内 `cg3/cg5` 读亦走 base（代码级核对） |
| F3 `spaceStart` 对无空间 cfx 为负 ⇒ elaborate 失败 | ✅已修 | `exists=0` 时返回 0 | Vast elaboration rc=0（B 段） |
| F4 `Bool.pad` 编译/elaborate 报错 | ✅已修 | `Cat(0.U(n-1), bool)` | Vast elaboration rc=0 |
| F5 探针期望值 `0x00FFFFFFFFFFFF0000`（18 位十六进制）被 `set.rd` 截断 ⇒ 检查点 4 假红 | ✅已修 | 改成 `0xFFFFFFFFFF0000`（= `(1<<40-1)<<16`，判据侧同式现场算） | 探针 19/19 记录通过（D 段） |
| F6 注入脚本用 `cp` 备份但未校验；磁盘满时备份被截断 ⇒ 还原清空源文件 | ✅已修 | 备份后校 md5（不等即拒）、还原前校备份完整（否则拒写）、磁盘余量前置（<1 GiB 整跑退出 3）、注入改为 `--inject` 显式开启 | 注入段 25/25 PASS，3 路还原 md5 全等且流逐字节回绿 |
| F7 证据脚本把证据树建在 tmpfs（任务根下另有实目录部分）⇒ 两套证据树、改前二进制「missing」 | ✅已修 | 把 source/log/evidence 三个目录统一为指向共享工作区的链接，证据树单一 | E 段「pre-change … present」通过 |
| F8 B 段用「sim 比源文件新」判身份（mtime 会被恢复操作刷新） | ✅已修 | 改为「组件工作树 clean」+ 源级/FIRRTL 级结构判据 + 行为判据 | B 段全绿 |
| F9 段计数写死（`__CHECK_RD` 计数含注释、自检 PASS 行数写死） | ✅已修 | 改成按行锚定的计数与「0 行 FAIL」判据，计数现场统计打印 | G/C 段 |

### 第 1 轮 reviewer 验收（2026-11-19，大改；真 elaborate + 真跑）

**重跑记录（reviewer 亲自执行，退出码均现场取）**
1. 合并态：`git diff master...HEAD --stat` = 10 文件（chipyard 4 份补丁 + `tools/chipyard/ptw/` 3 份 + 任务书 006/007/008），无越界；工作树 `git status -uall` 空、HEAD `edcc5113` 未变；组件源树 `git status` 空。
2. 独立重建（4 个补丁文件 md5 与组件 HEAD 逐字节相同后 touch 触发真 elaborate）：Tiny 与 Vast 的 `make verilog`/`make` 均 rc=0、`%Error`=0/0；Vast sim md5 `0d699e30…` 与完成区一致，Tiny `905971ac…`（md5 只作记录，ISS-453）。
3. Tiny 零增益（现场 `grep -c ptw`）：`GewuFile.sv`=0、pre-firtool FIRRTL=0、gen-collateral 内含 `ptw` 文件数=0、`WumingCore.sv` 的 `io_ptw_enable`=0；Vast 侧对应 2 / 25 / 6。
4. 证据脚本整跑 A–E+R+G：`PASS=58 FAIL=0`、rc=0；首册现场 38 镜像——改前二进制 vs 本轮重建 Tiny 0 差异/6128 B、Tiny vs Vast 0 差异/6128 B、三份均 38/38；探针 19 记录、判据 PASS；判据自检独立跑 rc=0（12 PASS/0 FAIL）。
5. 注入：脚本自带 3 路按 `INJ_ONLY=1,2,3` 重跑 ⇒ `PASS=25 FAIL=0`、rc=0（inj1/inj2 `oracle rc=1`、inj3 `guest rc=124 + oracle rc=1`，三路均 md5 相等还原→重建→回绿）；另加 reviewer 独立 2 路（**均不在其 3 路内**）：① `enterMemFault` 的 I/D 子原因前缀互换 ⇒ oracle rc=1（record 11/13）；② `cfx_ptw_enable` 读回取反 ⇒ guest rc=1、流 0 B、oracle rc=1；两路同样 `cp`+md5 还原→重建→oracle rc=0，组件源树回空。
6. 静态门控（逐个跑，真实 rc）：`check-source-state`/`check-tasks`/`check-no-residue`/`check-component-changelog`/`check-disk`/`check-writer-guards`=0；`check-patch-tree`=2（27 项全在 linux 段、chipyard 段 0；master 同门控 32 项同红 ⇒ 非本任务）；`check-milestones-fresh`=1（另一在途任务的行，master 上 PASS）；`check-knowledge-refs`=**1（本任务引入，见 B1）**；`make check`=2（止于 linux 段，另一次等待共享 gate 锁 15 min 未获）。
7. 磁盘：`df -h /tmp` 前 16G/5.5G/11G/34%、后 485M/16G/3%（期间无占满）；组件 `WumingCore.scala` 与 `git show HEAD:` md5 相等（`f762e98d…`，磁盘事故后已恢复）。

**约束核验**
- 范围 ✅｜Tiny 不回归 ✅（逐镜像 0 差异 + RTL `ptw`=0）｜Vast elab+跑 ✅（双 rc=0、`%Error`=0、38/38 且与 Tiny 逐字节同）｜注入 ≥2 路且含非其 3 路 ✅｜磁盘/还原纪律 ✅。
- 路由语义 ✅：与 `contract-tlb` TLB-40/41/42/43、§11 ⑨b、`contract-see §6.1.1`、`ADR-0056 D2` 逐条对齐；位号由判据现场解析（NONPTW=57、DGPTRAP=52、IGPTRAP=48、CFXMEM=1<<1），与我直接读表一致；`ptw_enable=1` 占位报缺失类 **[48]/[52] 符合 spec**（=⑨b「L1 P=0 普通页缺失」）。
- 寄存器面 ✅ **非偏离**：`DADAO-12 §4.5` 专有寄存器表原文「`8 8 ptw enable cfx_ptw_enable RW`、`9 0 ptw ptbr cfx_ptw_ptbr RW`、`12 0/1/2/3 tlb control·asid·addr_start·addr_size`」⇒ cg8 rc8、cg9 rc0、cg12 rc0–3 正是 spec；实现与 spec 一致，**任务书目标 3 的「（cg12 rc0–rc3）」括注是笔误**（finding a）。
- `pgLevels`/`useVM` 处置 ✅ 可接受：已核 rocket `tile/Core.scala:132`（xLen=64 且上游 `useVM` ⇒ `require(pgLevels>=3)`）与 `tile/BaseTile.scala:203`（`require(v==xLen || xLen>v && v>paddrBits)`），DADAO 42 位 VA / 56 位 PA / 两级表确实走不通上游路径；两处均标「字段保留、语义不用」，语义只读本核 `WumingCoreParams.useVM`，误用会被 `require` 立即打断，未来误用风险可控。

**判决：Needs Revision**（2 项阻断，各改一行即可，其余全绿）
- **B1（门控）**：本分支 `make check-knowledge-refs` rc=1、唯一红项 = 本任务审阅记录 F7 行含具体 `.work/**` 路径（master 同门控 rc=0、具体路径 0）⇒ 违反 AGENTS「任务书（含完成区/审阅记录）不得出现具体运行期路径」。改法：该行改运行期措辞（如「证据脚本把证据树建在 tmpfs（根下另有实目录部分）」），删去两处 `.work/…` 字样；预期 `make check-knowledge-refs` rc=0、具体路径 0。
- **B2（脚本恒真）**：证据脚本 B 段「generated RTL carries the route mux (ptw_enable decides the window)」一条实际只 `grep -q 'WumingCore' …/WumingCore.sv`，恒真、无可达 FAIL 路径（AGENTS「验证脚本反例门控：禁恒真」）。改法：删该条，或改成真实判据（断言 `io_ptw_enable` 参与的选择表达式在该 SV 中存在），保留紧邻的 `io_ptw_enable` 断言；预期「删掉路由选择」时该条能红。

**非阻断 finding（交 architect 收尾处理）**：a) 任务书目标 3 括注与 §4.5 不符；b) 脚本 R 段不重建 Tiny，`tiny-final` 与 `tiny-after` 是同一二进制的重跑，完成区「三方」表述偏大；c) B 段 4 条 `%Error` 读的是上一次 rebuild 的日志、与当前二进制无绑定（D/E 实跑兜底，故不阻断）；d) 探针 `cg8 rc8`/`cg9 rc0`/`cg12 rc1·rc2` 全用「写全 1」激励，只能验位宽、验不了切片位置（仅 `rc3` 用非平凡值）；e) 证据脚本 A 段对 `check-patch-tree` 只断言 chipyard 段（整体 rc=2 被打印但不断言）——master 同红，属 linux 组件在途问题，合并后需复核 L1。

**采信说明**：完成区的 58/0、25/0、38 镜像/6128 B、位号、寄存器地址、`%Error`、补丁数 23 与 series 同步，均由我重跑核对为真；「改前 `df16728e…`」核为备份二进制真实 md5（mtime 早于本任务起点）。

### 第 2 轮 reviewer 验收（2026-11-19/20，大改；合并态 + 独立注入）

**重跑记录（reviewer 亲自执行，rc 现场取）**
1. **B1 ✓**：本分支 `make check-knowledge-refs` **rc=0**、`具体路径 (不可复现): 0`、悬空 0（master 同门控亦 rc=0）；另用我自己的正则 `\.work/[A-Za-z0-9_]` 与 `/(tmp|mnt|home|root)/[A-Za-z0-9_.-]` 全文扫任务书（含完成区/审阅记录）⇒ **0 命中**（仅 `.work/**`、`.work/…` 通配与「删去…字样」删除语境）。
2. **B2 读码**：B 段两条新判据 = ① 路由谓词 `(|(x[47:42])) | ~_gewu_io_ptw_enable` 现场计数 ≥1；② `CFXMEM` 三原因字（位号现场从 `contract-see §6.1.1` 解析、互校 `ADR-0056`）3/3 —— 均非恒真、各有可达 FAIL。
3. **reviewer 独立注入 2 路（均不在脚本 3 路内）**：① `enterMemFault` 删 `|| !ptwEnable` ⇒ 重建 ⇒ B 段 `route predicate sites = 0`、FAIL=4、**rc=1**，探针 oracle **rc=1**（record 15/17）；② `enterHmonMem` 默认子原因 NONPTW→IGPTRAP ⇒ 重建 ⇒ `cause words 2/3`、FAIL=2、**rc=1**。两路均 `cp`+md5 还原（md5=`f762e98d…` 相等，**未用** checkout/restore/stash）⇒ 重建 ⇒ B 段 PASS=14 FAIL=0、**rc=0**、探针 oracle rc=0、组件源树 `git status` 空。
4. 脚本自带注入 `--inject`：**PASS=25 FAIL=0、rc=0**（inj1/2 oracle rc=1、inj3 guest rc=124+oracle rc=1；三路 md5 相等还原→重建→回绿）。
5. **合并态全量**：`bash .work/evidence/m16-chipyard-006/run.sh` ⇒ **PASS=59 FAIL=0、rc=0**（首版 10 条红全部 = 并发 qemu 写者致 `writer-guard REFUSED rc=75` 拒跑首册，非交付物缺陷；该写者结束后重跑全绿）。首册 38 镜像 / 6128 B 三方两两 **0 差异**、38/38；`route predicate sites = 4`、cause words 3/3。
6. **独立重建**：Tiny 与 Vast 的 `make verilog` + `make` 均 **rc=0、`%Error`=0/0**；4 份补丁源 md5 与注入前快照逐字节相同。
7. **合并态范围**：`git diff master...HEAD --stat` = 10 文件（chipyard 4 补丁 + `tools/chipyard/ptw/` 3 件 + 任务书 006/007/008），无越界；组件源树 `git status` 空；工作树快照前后均 0 行、逐行对账无差异。
8. 磁盘 `df -h /tmp` 全程余量 ≥5.2G；术语「银行」0 违例（「寄存器组」）；finding a–e 任务书如实标「未处理」；证据脚本基线为固定 md5/常量（无 `HEAD`/`merge-base`，`Process-07 §5b` 合规）。

**约束核验**：B1 ✓｜B2 ✓｜合并态（§5a）✓｜Tiny 不回归 ✓｜Vast elab+跑 ✓｜注入 ≥4 路（脚本 3 + 独立 2）✓｜还原纪律 ✓｜本轮未改代码（注入仅 `cp` 还原，快照 0 差异）✓。

**判决：Accepted** —— 两条阻断在我自己的重跑下确证已修且判据真有可达 FAIL；合并态全量 rc=0；其余验收条目全部现场复核为真。非阻断 a–e 按任务书如实标「未处理」，交 architect 收尾处理。

**采信/未验证边界**：以上 1–8 均为我亲自执行的真实输出；完成区「改前二进制 `df16728e…`」「补丁数 23/series 同步」采信自第 1 轮已核记录。
