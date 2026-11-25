# arch scope — Kaiwu-Vast cfx 用例（`tests/arch/`）

本目录**只测 Kaiwu-Vast**（`system` 平台）。QEMU / gem5 / chipyard 是同一 scope 的
三种**承载**，不是三个 scope；用例、驱动、签名薄壳与盘点数据都在本目录内。

- cfx 范围：**0/2/3/4/5/15/32/34/63**（umon/smon/hmon/ptw/cache/hart/pmem/time/power）；
  不含 Tiny、linux-user、jmon/llc/uart。
- 判据：**同一用例在三平台逐槽签名一致**；期望值独立派生自 `spec/` 与
  `.tao/contracts/`，不从实现反推。
- 门控：`tests/arch.yaml` 的 `level: smoke` 代表集由 `run_arch.py` 在 L2/L3
  （`check-arch-smoke` / `check-arch`）现场派生并执行；full 与三平台差分按需/里程碑收口。

## 驱动

```sh
python3 tests/arch/run_arch.py --cfx 4 --platforms qemu --cache-model off
python3 tests/arch/run_arch.py --level smoke --platforms qemu --cache-model off
python3 tests/arch/run_arch.py --case arch-umon-011 --mode smon --platforms qemu
# smoke 不测 cache（off）；cfx5 的 on 用例进按需的 check-arch-vast
python3 tests/arch/run_arch.py --self-test
python3 tests/arch/run_arch.py --list
```

- `--cfx`：0/2/3/4/5/15/32/34/63，可逗号分隔；非法值退出 2。
- `--level`：`smoke` / `full` / `all`（缺省）。按 `tests/arch.yaml` 的 `level`
  **现场派生**代表集；所选集合为空 ⇒ 退出 2（fail-closed，不当作 vacuous 通过）。
- `--platforms`：`qemu` / `gem5` / `chipyard` 逗号列表。`qemu` 与 `gem5`（driver 经
  `tools/testcases/parity/qemu_gem5_shim.py`，`-machine kaiwu-vast`）已接；
  `chipyard`（RTL）由 cfx 目录内的 `check_<cfx>_rtl.py` 承载（`kind: driver`，
  仿真器由 `--chipyard-sim` 指定；**cfx4** 由 `m16-chipyard-018`、**cfx34** 由
  `m16-chipyard-023`、**cfx5** 由 `m16-testcases-009`、**cfx15** 由
  `m16-testcases-013`、**cfx32** 由 `m16-testcases-014` 接入，其余 cfx 仍
  fail-closed）；没有 RTL
  承载的 cfx **fail-closed**（`PlatformError` ⇒ 非零退出），禁止静默降级为
  「其余平台通过」。`rtl-coverage.yaml` 登记的 `gap` 记 `GAP`（不当作通过）。
- `--cache-model`：缺省 `on`；传 `off` 退出 2。**唯一例外**是 `modes.yaml` 显式
  写 `cache_model: "off"` 的用例（`arch-cache-004` 的 CACHE-27 off 分支）：
  `run_arch` 按该字段覆盖全局值，RTL 无开关时由 `cache/rtl-coverage.yaml` 记 gap。
- `--case`：只跑 `tests/arch.yaml` 里的一个 id，用于单点复现。
- `--mode`：`hmon` / `smon` / `umon`（缺省 `hmon`），选择运行模式环境
  （hypv/supv/user）。用例的允许集（`tests/arch/modes.yaml`）不含该模式 ⇒ 打印 `N/A` + 原因；
  全部被排除 ⇒ 退出 2（fail-closed）。只有声明多模式的 `kind: driver` 才接
  `--mode`；`kind: asm` 收到非 `hmon` 时**显式**报错，不静默按 hmon 跑。
- `--self-test`：不启动模拟器，只校验索引的 `machine/kind`、各 `expected.yaml` 的
  签名流结构、驱动的 `--selfcheck`，以及 gem5 承载与 chipyard 的 fail-closed 探针。
- `--list`：打印 `cfx × case × platform` 计划表，不执行。
- 产物：运行期证据目录下每 case × 平台一份 `signature.bin` + `run.json`
  （进程命令、rc、stdout/stderr 日志路径）；不写固定绝对路径。

退出码：`0` 全通过；`1` 任一用例/平台失败或 SKIP；`2` 用法/配置错误。

## 目录

| 目录/文件 | cfx | 内容 |
|------|-----|------|
| `run_arch.py` | — | 唯一驱动（`--cfx/--platforms/--cache-model/--level/--self-test/--list`） |
| `common/` | — | arch 内共享薄壳：`signature.py` 转调 `tests/shared/signature.py`（含逐槽差异登记读取）；`platform.py` 的 qemu/gem5（driver 经 shim）/chipyard（RTL 承载 = 目录内 `check_<cfx>_rtl.py`；已接 cfx4 / cfx34 / cfx5 / cfx15 / cfx32，其余 cfx fail-closed）后端 |
| `common/env-{hmon,smon,umon}/` | — | **运行模式环境**（每个模式一个目录，`env.S`；共享 `common/env.lds`）：进入模式、栈、异常向量、退出与签名区；body 与模式解耦（`m16-testcases-015`，见 `common/env-README.md` / `common/env-MIGRATION.md`） |
| `umon/` | `cfx0`（user monitor） | SEE/semihosting 执行向量 + cfx 级权限反例（`m5_*.S`，10 条）+ `expected.yaml`；代表迁移用例 `umon_mode_regs.body.S` + 驱动 `common/check_mode_env.py`（`arch-umon-011`，三模式）；**fence 基础验证** `umon_fence.py`（载体）/ `check_fence.py`（驱动，`arch-umon-012` 放行面三模式、`arch-umon-013` 保留面 hmon）+ `gen_fence_rtl.py` / `check_fence_rtl.py`（按需 RTL 承载，`fence_rtl.lds`）；**cfx0+cfx2 寄存器面 RTL 探针** `cfx02_regs.S` + `check_cfx02_regs.py`（`m16-chipyard-019`，47 条记录）；**U/S/H 模式进入路由 RTL 探针** `mode_entry.S` + `check_mode_entry.py`（`m16-chipyard-020`，同一份 case 链接 TMODE=0/2/3，14/21/14 槽）；cfx0/cfx2 两个 RTL 探针暂未登记 `tests/arch.yaml`——chipyard 后端目前只接 cfx4（`check_ptw_rtl.py`），且 hmon 模式环境只在 QEMU/gem5 载体上可用 |
| `ptw/` | `cfx4`（TLB/PTW） | 15 条 TLB/PTW 探针：载体/生成器 `ptw_carrier_tlb.py`（`m16-testcases-010` 由 `tools/testcases/arch/` 迁入）、期望清单 `expected.yaml`（大类 + 子原因符号 + `cause_info` 语义 + 已接线签名流期望 + 来源 §；`checks_by_mode` 承载 011 的 S/U 轴）、驱动型入口 `check_tlb.py`（`kind: driver`）；**H/S/U 三模式**（`m16-testcases-019`：镜像 = 载体固件段 + 共享 `common/env-<mode>` + body，`cfx_access: [umon, smon, ptw, pmem, power]`），QEMU 与 gem5（shim）逐条跑。**RTL 承载**（`m16-chipyard-018`）：`ptw_sig.S` + `gen_ptw_sig_tables.py` + `check_ptw_rtl.py`（cfx4 的 15 条映射见 `rtl-coverage.yaml`；013 于 `m16-testcases-019` 提升为 signature）；`ptw_regs.S`/`ptw_walk.S`/`ptw_tlb.S`（及各自 `check_ptw_*.py`/`gen_ptw_*_tables.py`）由 `tools/chipyard/{ptw,tlb}/` 迁入，是 RTL 的额外检查点 |
| `cache/` | `cfx5`（cache） | **三方用例**（`m16-testcases-009`，`arch-cache-001` 于 `m16-testcases-020` 补 I+D 同选 21 槽）：`arch-cache-001/002/003` 由 `check_cache.py`（QEMU/gem5，env 三模式）与 `check_cache_rtl.py`（RTL，`cache_rtl.S`）跑同一槽序；`arch-cache-004` 是 `cache-model=off` 分支（QEMU/gem5；RTL 记 `rtl-coverage.yaml` 的 gap）。唯一期望源 `cache_oracle.py` + `expected.yaml`。另有 RTL 专项探针 `cfx5_regs.S`/`check_cfx5_regs.py`（`m16-chipyard-016`）与 `cfx5_maint.S`/`gen_cfx5_maint_tables.py`/`check_cfx5_maint.py`（`m16-chipyard-017`，缓存日志时序），不登记进索引 |
| `hart/` | `cfx15`（cfx_hart） | cg8 管理寄存器 + cg9 七槽捕获缓冲（R2：每次进入整体覆盖）+ 源位图/掩码/TIMER 投递 + jump 目标精确点；`arch-hart-001`（hmon，89 槽；含 `cg9 rc6` 写 0/1/3 读回与异步进入取 rc6）/ `arch-hart-002`（smon/umon，40 槽），同一份 `cfx15.S`；QEMU + gem5 + RTL 三方逐槽（归一化签名，gem5 的 R2 异步面由 `m16-gem5-026` 补齐）；驱动 `check_hart.py` / `check_hart_rtl.py`（`m16-testcases-013`） |
| `power/` | `cfx63`（power） | 寄存器面（`cg7` BootROM 块）+ power→hmon 移交：`arch-power-001`（hmon/smon/umon 各一次，35 槽）+ `arch-power-002`（属性拒绝面，只 hmon，3 槽）；载体/驱动 `power_vast.py` / `check_power.py`，RTL 承载 `gen_power_rtl.py` / `check_power_rtl.py`（`power_rtl.lds`） |
| `pmem/` | `cfx32`（cfx_pmem） | **DMA 完成中断 + 同界多源**（`m16-testcases-014`）：`arch-pmem-001`（hmon，55 槽：DMA/状态/一致性 clean+invalidate（A）/ILLI/捕获/`escape imms18=2 ⇒ CFXESC`/同界 TIMER+DMA 一次进入/ack/覆盖）+ `arch-pmem-002`（smon/umon，10 槽：完成落在目标模式、各写自己 monitor 掩码）；载体 `pmem_dma.S` + 驱动 `check_pmem_dma.py`（QEMU/gem5）与 `check_pmem_rtl.py`（RTL），判据 `pmem_oracle.py`，QEMU+gem5+RTL 三方逐槽（gem5 的 R2 异步面由 `m16-gem5-026` 补齐）。另有 RTL 寄存器面探针 `pmem.S` + `check_pmem.py`（`m16-chipyard-022`），不进索引；寄存器面 `cg8/12/13/14` 三承载已同口径（QEMU `m16-qemu-006`、gem5 `m16-gem5-025`、RTL `m16-chipyard-022`，`DIV-06` 已删除） |

| `time/` | `cfx34`（cfx_time） | **per-system 全局时间计数器**（只读、**无中断**）：`arch-time-001`（`time_freq` 与 RO 再读、`time_value` 的单调/严格递增/增量有界/epoch、与 `cfx_hart cycle` 同基准；hmon/smon/umon 各一次，7 槽）+ `arch-time-002`（`cg10 rc2/rc63` 保留 rc、`rc0/rc1` 的 RO 写 ⇒ `CFXREG`；只 hmon，6 槽）；载体 `time{,_reject}.body.S` + 驱动 `check_time.py`，判据只有一份（`time_oracle.py`），RTL 承载 `time_rtl.S` + `check_time_rtl.py`（`m16-chipyard-023`：**三平台同一 case 逐槽比较**） |
其余 cfx 按已有用例增建（`smon/`、`hmon/`、`cache/`、`hart/`、`pmem/`、`time/`、
`power/`）；**不建**空壳子目录。Tiny 的 hmon 用例已迁出 arch（见下）。

## fence 基础验证（`m16-testcases-012`，cfx0）

`fence cfxHA, immu18` 按 `cfxha` 选资源域（`cfx0` = all cfx），`immu18` 的
`hb`（`[17:12]`）SBZ、`pred`（`[11:6]`）/`succ`（`[5:0]`）为六位访问类型掩码
（`cr/cw/ci/co/mr/mw`）。保留 cfxha 或 `hb ≠ 0` ⇒ `ILLI`
（`spec/SimRISC-11 §5`；合法集见 `contracts/opcodes.yaml` 的
`fence_ciii_cfx`）。

| case | 内容 | 模式 | 尺寸 |
|------|------|------|------|
| `arch-umon-012` | 放行面：`cfx0` 零掩码/全掩码、六个资源域各一位、指定 cfx（3/4/5/32/33/34）、允许集边界（15/62/63） | hmon/smon/umon 各一次 | 17 槽 |
| `arch-umon-013` | 保留面：采样 16/17/18、边界 6/14/31/35/61、`hb=1` 与 `hb` 全 1 | hmon（原因见 `modes.yaml`） | 10 槽 |

- 载体 `umon/umon_fence.py` 现场生成 4 MiB BootROM 镜像（power → hmon 预置
  页表/PTW → body），QEMU 与 gem5（经 `qemu_gem5_shim.py`）跑**同一份字节**；
  模式切换沿用 `common/env-README.md` 的协议（`cfx_hmon` 的 `<mode>` 行
  `switch_run_mode` + `excp_vector` + `trap cfx_hmon`），并用 `-d cpu` 的 `MODE:`
  现场核对 body 实际运行模式（不由 body 自述）。
- 签名槽 = 一个 probe：`0` = fence 正常执行；`ILLI` = 异常（精确值现场从
  `contract-see §6.1` 派生）。放行面在 smon/umon 用「fence 之后写槽」作见证；
  保留面需要当前模式监视器记录 cause（`DADAO-12 §5.2`），故只在 hmon。
- **RTL 按需**：`gen_fence_rtl.py` 从同一张探针表生成 `.S`，
  `check_fence_rtl.py` 经 `tools/testcases/lib/chipyard_engine.py` 在
  `WumingVastConfig` 上跑并逐槽比对（RTL 测试体固定 hypv、同步异常固定进
  hmon；`+loadmem` + semihosting）。`run_arch.py` 的 chipyard 后端接
  cfx4/cfx34/cfx5/cfx15/cfx32（`m16-chipyard-018`/`023`/`m16-testcases-009`/`013`/
  `014`），其它 cfx 仍 fail-closed，故这些 RTL 探针不进
  `run_arch` 的常规路径。

**未覆盖项（显式登记，不假装全覆盖；用户 2026-11-22 裁定完整覆盖暂不做）**：

- 全部 cfxha（0–63）× `pred` × `succ` 六位组合的穷举（6 × 6 × 6 × 6 位域组合）
  不做；只取每个资源域一位、`pred = succ`、以及零掩码/全掩码。
- `pred ≠ succ` 的交叉组合、单侧掩码（只 `pred` 或只 `succ`）不做。
- 资源域掩码的**顺序/可见性语义**不测：本实现（QEMU/gem5/RTL）均为「本 hart
  已顺序执行」的 no-op 语义，DMA 不等待（`spec/SimRISC-11 §5`），无 Guest 侧
  可观测差异；只在「不产生异常」层面覆盖。
- cfx1（jmon）在 arch 范围外（`tests/arch/README.md` 顶部 cfx 范围），只按其
  编码合法性间接落在允许集里（未单列 probe）。
- 保留集只采样 6/14/16/17/18/31/35/61（含边界），其余保留编号不逐个跑。

## cfx4 RTL 承载（`m16-chipyard-018`，cfx4）

RTL（chipyard `WumingVastConfig`）接入 `m16-testcases-010` 的同一组 case id /
期望：`run_arch.py --cfx 4 --platforms qemu,gem5,chipyard` 逐槽比较，三方
（QEMU / gem5 / RTL）一致才算通过。映射与缺口在 `ptw/rtl-coverage.yaml`
（`signature` / `guest` / `partial` / `gap` 四类，`gap` 必须写原因与
`close_when`；`check_ptw_rtl.py --selfcheck` 与 `tests/arch.yaml` 的 15 条
双向核对，`gap` 不会被当成 PASS）。

| 面 | 载体 | 说明 |
|----|------|------|
| 签名（002/006/007/013） | `ptw/ptw_sig.S` + `gen_ptw_sig_tables.py` | 与 QEMU 载体同一组数据地址/PTE 值 ⇒ 逐字节相同（`007` 的回写失败两槽按 DIV-14 登记；`013` 的 cfx_pmem 旁路 3 槽） |
| guest（001/003/004/005/008/009/010/011/012） | 同上（`PTW_CASE=1..13`） | guest 内断言（非零退出 = 该影像第 N 条断言失败）；签名流 0 槽 |
| 额外检查点 | `ptw/ptw_regs.S`、`ptw/ptw_walk.S`、`ptw/ptw_tlb.S` | 由 `tools/chipyard/{ptw,tlb}/` 迁入（`m16-chipyard-018`）；寄存器面/两级走查/I-D TLB 的独立判据与自检保留。`ptw_walk` 31 槽、`ptw_tlb` 54 槽（loadmem 约 13 min）；`ptw_regs` 保持既有 TL `A' channel re-used a source ID` 断言（KNOWN-RED，非本任务引入） |
| 缺口（014/015） | — | 014：A/D 回写失败（RTL 的 PA RAM 全可写，DIV-04/DIV-14）；015：ILLI 的 `cause_info`（需只读内存窗口页）。013 已由 `m16-chipyard-022` 的 SRAM 窗口 + `m16-testcases-019` 的 `PTW_CASE=13` 提升为 signature |

- 判据来源：几何/PTE/数据 magic 与 QEMU 载体同一组值；cause 编码现场从
  `contract-see §6.1/§6.1.1` 解析并与 `spec/DADAO-12 §3.6` 互校；
  `gen_ptw_sig_tables.py --selfcheck` 与 `expected.yaml` 逐槽双向核对。
- 签名机制：汇编侧 `tests/shared/asm/signature.inc`（`SIG_BEGIN`/`SIGUPD`/
  `SIG_DUMP`），host 侧 `tests/shared/signature.py`（`parse`/`compare`）；
  `ptw_regs/walk/tlb` 的 `__REC` 即 `SIGUPD`，host 侧不再自带解析器。
- **H/S/U**：RTL 固定 BootROM（`spec/Kaiwu §6.2`）把测试体交付为 `cfx_hmon` +
  `hypv`；PTE 的 `H` 位在 `ptw_sig.S` 的 011 里覆盖（H=0 ⇒ `NHPERM`，H=1 放行），
  `S`/`U` 位不改变 hypv 的判定（与 QEMU/gem5 的 `pte_leaf(hsju=…)` 同口径）。
  `hmon`/`smon`/`umon` **三模式**由 `modes.yaml` 登记（`m16-testcases-019`）：
  镜像用共享 `common/env-{hmon,smon,umon}` 进入/退出，body 与 PTW 实现不变；
  测试页 PTE 的 HSJU 取 `H|S|U` ⇒ 签名流与模式无关，三方逐槽同一组值。
  PTE 的 S/U 轴在 `arch-ptw-011` 的 `checks_by_mode` 里逐模式构造。RTL 的
  step5 测试路径仍只交付 hmon/hypv（`tests/ee-vast/README.md`），故 RTL 承载
  只跑 hmon 一次。
- **RTL 差异**：`expected-divergences.yaml` 的 `slots`（scope 含 chipyard、
  `close_when` 必填）；QEMU/gem5 侧仍按规范值判，RTL 侧按登记值判；例外被修好
  时 RTL 承载判红，提示删除条目（DIV-14）。
- **不回归**：Tiny 无 PTW，本任务不触碰 Tiny 路径；RTL 的既有探针（cfx0/2、
  cfx5、cfx15、power）不在本任务的判据内。

## cfx63 power 基础用例（`m16-testcases-016`，cfx63）

power 阶段的寄存器面与 power→hmon 移交（`trap cfx_hmon`）由 `tests/arch/power/`
覆盖；载体复用 `node_probe_prelude` 的 step5 同序启动链（power → hmon → body），
QEMU 与 gem5 跑**同一份 4 MiB BootROM 字节**。

| case | 内容 | 模式 | 尺寸 |
|------|------|------|------|
| `arch-power-001` | 移交帧（`prev_cfx` = 63、`prev_mode` = hypv、`cause_id` = `CFXTRAP`、`cause_ip` 落在 BootROM 窗口）+ `cg7` 块 0 四字段 + 块 1–15 `desc` + 块 15 `start/size/attr` + 收尾 `cg5 rc1` 的 RW 回读 | hmon/smon/umon 各一次 | 28 槽 |
| `arch-power-002` | 属性拒绝面：`cg7` 写 ⇒ `CFXREG`、`cfx_power_ctrl`（`cg8 rc1`，WO）读 ⇒ `CFXREG`、`cg8 rc2` 读 ⇒ `CFXREG` | hmon（原因见 `modes.yaml`） | 3 槽 |

- 期望值全部现场派生：cfx 编号取 `contract-cfx-aliases.md §1`、`cg7` 位号取
  `DADAO-12 §3.8`、`desc/start/size/attr` 取 `spec/Kaiwu §3` 并与
  `contracts/machine.yaml`（vast）双向核对、cause 编号取 `contract-see §6.1`、
  模式编码取 `spec/Kaiwu §7.1`。`expected.yaml` 只是登记，`--selfcheck` 双向核对。
- **复位 `inner_cfx_code = 63` 的可观测形式**是 power→hmon 帧里的
  `excp_prev_cfx_code`（`DADAO-12 §5.2` 第 5/6 步）⇒ `hmon_prev_cfx` 槽。
- smon 的 `cg` 授权：载体在 hypv 把 `cfx_power cg3 rc12`（`cg_reg_deleg`）写成
  `0x8`（`§3.4` 的整组开放）并回读校验，收尾还原；回读不符 ⇒ `SYS_EXIT(0xE3)`
  （fail-closed，不是 PASS）。umon 不需要（`user` 不查 deleg）。
- 运行模式由 QEMU/gem5 的 `-d cpu` 的 `MODE:` **现场观测**（不由 body 自述；
  窗口限定为 body 的 `-dfilter`）；失败路径统一走 `common/runlimit.py`：
  短超时（缺省 10 s，`DADAO_ARCH_TIMEOUT` 放宽）+ `-d cpu` dump 上限
  （缺省 128 MiB，`DADAO_ARCH_DUMP_MAX` 调整，运行中即终止）+ 失败后截断
  （`ISS-522` 的教训：不复制「60 s + 全量 dump 写爆磁盘」的形态）。
- **RTL 按需**：`gen_power_rtl.py` 从同一张探针表生成 `.S`，
  `check_power_rtl.py` 经 `chipyard_engine` 在 `WumingVastConfig` 上跑并逐槽比对
  （RTL 测试体固定 `cfx_power`/hypv ⇒ `arch-power-001` 只跑一次）。`run_arch.py`
  的 chipyard 后端未接 cfx63，故 cfx63 的 RTL 仍不进 `run_arch` 的常规路径。
  `tools/chipyard/excp/prevcfx.S` 的检查点（`cfx_hmon cg5 rc1` 的 boot 保存值 =
  `cfx_power` 编号、RW 回读、还原）已并入同一张探针表（槽 0/26/27），不再有两套判据。

**三方差异（登记在 `expected-divergences.yaml`，不静默跳过）**：

- RTL 的 `cfx_power cg7` 块 0 自 `m16-chipyard-025` 起按 `spec/Kaiwu §3`
  描述 **4 MiB** BootROM（`start = 0x3ff_ffc0_0000`、`size = 0x40_0000`）；
  原 **DIV-12**（RTL 64 KiB vs 规范 4 MiB）已删除，`arch-power-001` 的
  `space0_start`/`space0_size` 两槽三方逐槽一致。
- **DIV-13 已删除**（`m16-chipyard-027`）：RTL 的 `cfx_power` 已在 Vast 打开
  `commonRows`，`cg4`（`cfx_id = 63`、计数）/`cg6`（scratch RW）进入
  `arch-power-001` 的比较面；`cg4 rc1 version` 是 HW 值（spec/合约不规定），
  不入判据，仍由 `--diagnose` 报告。

**未覆盖项（显式登记，不假装全覆盖）**：

1. `cfx_power_ctrl` 的**写侧**：规范为 WO（写 0 应被接受）。QEMU 已在
   `m16-qemu-006` 实现（Vast 接受写、Tiny 按 `spec/Kaiwu §3` 仍 `CFXREG`）；
   gem5 已在 `m16-gem5-025` 按 `§4.12` 落副作用（bit0/1/2 ⇒ 结束仿真，复位
   约定为「结束 + harness 重启」；写 0 无动作）；RTL 仍未实现 ⇒ 三方未齐前
   不写进 `arch-power-*` 的签名判据（不拿实现现状当期望），`--diagnose`
   逐方报告并登记差异。
2. 电源语义本身（`bit0/1/2` = 关机/硬复位/软复位）：写入即停机/复位，没有
   「执行后仍可观测」的判据（任务书「不做」第 1 条）。
3. `cfx_power` 的 `cg3` 行（hypv 向量/switch 模式）不复位断言：`DADAO-12 §3.4`
   把无 SRAM cfx 的 `hypv_excp_vector` 初值留给平台/实现。
4. 移交后 **hmon 的 `escape` 回 power** 不测：`D14`（`ADR-0043`）声明 power
   不恢复，无可观测语义。
5. `cfx_power` 的 `cg7` 只读面只采样 `desc`（块 1–15 全部）与块 15 的
   `start/size/attr`；块 1–14 的 `start/size/attr` 不逐个跑（`exists=0` 时三字段读
   0 的规则由块 15 与块 0 覆盖）。

## 命名规范

- 目录：`tests/arch/<cfx>/`，cfx 名用 `DADAO-12 §3`（`umon/smon/hmon/ptw/cache/hart/pmem/time/power`）；**不建** `data/` 子目录。
- 汇编载体：`<prefix>_<name>.S`（统一大写 `.S`，即使不预处理）；历史 `m5_*` 前缀保留。
- 链接脚本：`<prefix>_<name>.lds`。
- 驱动：`check_<prefix>_<name>.py`；生成器：`gen_<prefix>_<name>.py`；载体：`<cfx>_<name>.py`。
- body：`<prefix>_<name>.body.S`；env：`common/env-{hmon,smon,umon}/env.S`，共享 `common/env.lds`。
- 期望：`<cfx>/expected.yaml`；全局差异：`tests/arch/expected-divergences.yaml`；模式/权限元数据：`tests/arch/modes.yaml`。
- **禁止**：`data/` 子目录；`tools/` 下新增 arch 专用脚本；随意名（`carrier_*`、`mode_regs.body.S` 等）；新增用例必须登记 `tests/arch.yaml`。
- 根 `tests/arch/README.md` 维护本目录总表；每个 cfx 目录可选一份说明。

## 索引字段

`tests/arch.yaml`（`id` / `file` / `platforms: [system]` / `level` / `requires`，外加）：

- `machine: vast`（arch 条目**必填**，只能 `vast`；Tiny/user 由其它 scope 负责）；
- `kind: asm | driver`（arch 条目**必填**）。`asm` 的 `file` 是 `.s`/`.S` 执行向量；
  `driver` 的 `file` 是本目录内的驱动（如 `arch/ptw/check_tlb.py`），由
  `run_arch.py` 调起。
- 运行模式允许集登记在**并列清单** `tests/arch/modes.yaml`（`m16-testcases-015`）：
  `cases.<id>.modes`（`hmon`/`smon`/`umon`）与 `cases.<id>.reasons`（被排除模式的
  **显式原因**）。与 `tests/arch.yaml` 的 id 集合**双向**核对；缺项/多项/非法
  模式/缺原因由 `run_arch.py`（含 `--self-test`）报红。不写进 `tests/arch.yaml`
  是因为该文件的字段受 `check-tests-index` 白名单约束（未知字段即红）。
- `cases.<id>.cache_model`（可选，`on`/`off`）：该用例的 `cache-model` 机器维度；
  缺省跟随 `run_arch --cache-model`，`off` 只用于 CACHE-27 的 off 分支
  （`arch-cache-004`）。
- `cases.<id>.cfx_access`（可选，`m16-testcases-017`）：该用例在目标模式下需要
  访问的 cfx 列表（`umon`/`smon`/`hmon`/`ptw`/`cache`/`hart`/`pmem`/`time`/`power`）。
  环境据此在**降模式之前**（仍在 hypv、源 cfx = cfx_hmon）打开目标 cfx 的
  `<mode>` 行来源掩码（`DADAO-12 §3`，只清源 cfx 位）与 `cg_reg_deleg`
  （supv 侧前提），并把**未声明**的 cfx 收窄（源 cfx 位置 1 ⇒ 未声明访问
  `CFXPERM`），退出还原打开的项并回读校验；声明由 `common/platform.py` 的
  `--cfx-access` 交给驱动、驱动再落成逐 cfx 的 `--defsym ENV_CFX_ACCESS_<n>=1`。
  非法/重复/空列表、或只有 `hmon` 的用例上声明 ⇒ `run_arch.py` 报配置错误。
  语义、失败码与已知边界见 `common/env-README.md`。
- 门控：`make check-tests-index`（L1，静态）校验字段、`machine/kind` 取值与
  `file` 存在；条数现场统计，不写死。

## 观测通道

**签名流 = 观测点的判据载体**：每个观测点把实测 8 字节写进
`tests/shared/asm/signature.inc` 约定的签名区（预填 `0xdeadbeef`；漏跑 ⇒ host 报
「槽 N 未写」），收尾整段输出，host 侧用 `tests/shared/signature.py` 按槽比对。
机制只有一份：汇编侧 `signature.inc`、host 侧 `signature.py`；`tests/arch` 的
word-builder 探针用同一个 `.py` 的 `Emitter`，`common/signature.py` 只做薄壳重导出。

退出码（semihosting `SYS_EXIT`：`0x00` 通过、`0x01`–`0x7F` = 镜像内第 N 条断言失败）
只作**镜像级兜底**：已接线的检查以签名流比对为准。`ptw` 的
`arch-ptw-002/006/007` 已接线，期望值登记在 `expected.yaml` 的 `signature:` 并由
驱动 `--selfcheck` 双向核对。

## 门控

```sh
make check-arch-smoke   # L2：level=smoke 代表集（run_arch.py 现场派生）+ 25 服务 + ptw/tlb carrier
make check-arch         # L3：与 check-arch-smoke 同一套检查（用户 2026-11-22 裁定）
```

- 代表集条数由 `tests/arch.yaml` 的 `level: smoke` **现场派生**，不写死；代表集为空 /
  `run_arch.py` 或索引缺失 / 任一 case 失败 ⇒ 非零（fail-closed，不得 `|| true`）。
- cfx4 PTW/TLB carrier（`ARCH_PTW_CARRIER = tests/arch/ptw/ptw_carrier_tlb.py`，15 条）
  **并入 `check-arch-smoke`**；`check-arch` 只依赖 smoke + echo，两目标同跑。
- 旧 `ARCH_CFX_PROBES`（010 后 14 项、无 `tlb`）**不再被 `check-arch` 调用**；
  文件与变量保留，**待 cfx4 迁移任务处理**（`m16-testcases-007`）。
- 25 服务覆盖（`min_rom_probe_046t`）仍是 `check-arch-smoke` 的一部分。
- full 集（`run_arch.py --level full` 的 `arch-ptw-*` 跨平台逐槽比对）**不进** L2/L3，
  按需/里程碑收口跑 `run_arch.py`；L2/L3 的 ptw 面由 carrier 的 15 条 QEMU 探针承担。

## Tiny hmon 已迁出

`arch-hmon-001` 与 `tests/arch/hmon/` 已迁到 `tests/unit/gem5/tiny_hmon/`
（驱动 `tests/unit/gem5/check_tiny_hmon.py`；`m16-testcases-006`）。Tiny hmon 的
**QEMU 同契约探针** `tools/testcases/arch/min_rom_probe_integ007t.py` 仍保留在
`ARCH_CFX_PROBES` 变量内，但该变量**不再被 `check-arch` 调用**——待 cfx4 迁移任务处理。

## 前置

`make install-host`（工具链 + QEMU 取自安装根，ADR-0016 D9）与
`make build-bootrom`（Vast step5 固件与 K1 boot 链在 `tests/ee-vast/`）。
