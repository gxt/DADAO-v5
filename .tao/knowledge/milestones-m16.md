# 项目里程碑

> **项目里程碑 = M16**（M16 台账的唯一断言；`check-milestones-fresh` 按本断言把任务号路由到本页；M12–M15、M17 各另有分册）

> **本页只维护 M16 任务台账**：历史任务见 `.tao/archive/`；当前讨论/规划见 `.tao/knowledge/discussing.md`。

> **M16 目标（用户 2026-11-19 重申）**：**对齐 `gem5` 的 `TimingSimpleCPU` 与 `chipyard-wuming`（RTL）**，覆盖 **两个机型：`tiny` 与 `vast`**。
> **M16 定位（用户 2026-11-13）**：范围只做 **Timing**（`Minor`/`O3` 对应 `wuqing`/`wuxing`，等其 RTL 出现后再开）。设计取向：**保留 gem5 `TimingSimpleCPU` 原汁原味**，只加「每指令延迟」——钩子默认 0、`timing.cc` 仅 1 行、延迟表由周期模型文档现场生成；块传送用微操作展开；访存交给 `NoncoherentXBar` + `SimpleMemory`。`AtomicSimpleCPU` 不动，只作零成本基线。
> **范围扩展（用户 2026-11-16）**：本页同时收录 gem5 / chipyard 侧的 **ISA 语义对齐**任务（`ADR-0056` 子原因编码、`DADAO-12 §5.2` 同步异常路由），编号沿用 `m16-<module>-NNN`；这些任务与时序模型无关，不得混算进 `m16-chipyard-001` 的周期复测口径。

本页分三张**任务表**，**表位置 = 任务状态**（不另设状态列）：

| 表 | 收录 | 列 |
| --- | --- | --- |
| 待开始（未开工） | 尚未派单的 `待开始` | `编号` / `预估时间` / `一句改动` |
| 进行中（已派单） | 已派单未合并：`待开始`（实现中）、`待验收`、`待返工` | `编号` / `派单时间` / `预估时间` / `一句改动` |
| 已验证 | `已验证` | `编号` / `完成时间` / `一句改动` |

## 待开始（未开工）

| 编号 | 预估时间 | 一句改动 |
| --- | --- | --- |
| m16-chipyard-031 | 1–2 h | RTL `cfx_power_ctrl` 写侧（写接受 + `§4.12` 副作用；ISS-525 RTL 部分） |
| m16-testcases-024 | 1–1.5 h | `tests/arch` 收尾二：临时目录清理 + `check_ptw_rtl --mode` + 单平台假不一致（ISS-m16-007/010） |
| m16-chipyard-030 | 2–4 h | `cfx15.S` 偶发挂死（flake）定位（ISS-m16-011） |

## 进行中（已派单：待开始 / 待验收 / 待返工）

| 编号 | 派单时间 | 预估时间 | 一句改动 |
| --- | --- | --- | --- |
| m16-testcases-023 | 2026-11-25 22:06 | 1–2 h | 删除 ADWBFAIL 用例（页表必须在内存；DIV-14 删除、DIV-04/ISS-515 收口） |

## 已验证

| 编号 | 完成时间 | 一句改动 |
| --- | --- | --- |
| m16-testcases-022 | 2026-11-25 22:06 | PTW RTL 扁平 cause 回归（009/011/013 转绿；`ISS-m16-006` 关闭；case13 SIGUPD 修复） |
| m16-gem5-025 | 2026-11-25 20:56 | gem5 `cfx_pmem` 面 + `cfx_power_ctrl` 副作用（bit0 关机/1、2 复位）+ rc6 对齐 + Tiny 掩码面；DIV-06/18 删除 |
| m16-chipyard-028 | 2026-11-25 17:52 | RTL `cg9 rc6` 对齐 spec-006（RW、复位 2、进入取该值；89/40/40 槽，QEMU+RTL 三方） |
| m16-chipyard-029 | 2026-11-25 15:55 | Vast `cfx15` 不收敛根因：旧 ELF（m17 前探针）误报；当期探针+当期 RTL 80/40/40（无 RTL 缺陷） |
| m16-qemu-007 | 2026-11-25 15:26 | QEMU `cg9 rc6` 回归 spec-006（写落地、进入取该值；`arch-hart-001` 89 槽） |
| m16-gem5-026 | 2026-11-25 14:24 | gem5 异步捕获缓冲（R2：`cg9` 七槽、掩码归 monitor、一帧多源；`DIV-17` 删除，三方 6/6） |
| m16-testcases-021 | 2026-11-25 11:32 | 证据脚本与探针收尾（恒真式、profile、`SEL_I/D`、11-cfx 注释；`runlimit` 原件+RLIMIT） |
| m16-qemu-006 | 2026-11-25 11:31 | QEMU `cfx_pmem` 寄存器面 + `cfx_power_ctrl` 写侧（Tiny 门控）+ `cg9 rc6` 写忽略 |
| m16-testcases-020 | 2026-11-25 10:02 | `tests/arch` 收尾（cfx5 I+D 同选 21 槽；`runlimit` 10 s/128 MiB/1 MiB；未装载监视器 17 KB） |
| m16-testcases-019 | 2026-11-25 08:13 | PTW S/U 覆盖 + `arch-ptw-013` signature（QEMU+gem5 三模式；RTL known-red 待 022） |
| m16-infra-002 | 2026-11-25 05:57 | `chipyard_engine` 可选 `+verbose` + L1 门控 `check-arch-self-test`（spec 任务收尾） |
| m16-chipyard-027 | 2026-11-25 05:23 | RTL 缺面补齐（power `cg4/cg6`、cfx5 S/U 可达、`addr_start` 56 位；DIV-13/16 删除） |
| m16-testcases-014 | 2026-11-25 02:15 | cfx32 pmem 完成中断 + 同界多源（R2：55/10 槽、一次进入并集；QEMU+RTL 两方，DIV-17） |
| m16-testcases-013 | 2026-11-25 01:25 | cfx15 timer 中断（R2：80/40 槽、覆盖语义、`escape` 拒绝；QEMU+RTL 逐槽，gem5 登记 DIV-17） |
| m16-spec-003 | 2026-11-24 23:58 | DMA 与 D-cache 一致性（裁定 A：软件 clean/invalidate）+ contract power 块值订正 |
| m16-testcases-009 | 2026-11-24 23:40 | cfx5 用例三方跑（4 case/61 槽；hmon 三方 144/96/128 B 全同；off 口径；DIV-15/16） |
| m16-chipyard-023 | 2026-11-24 22:14 | RTL cfx34 time（`cg10` freq/value 只读、无中断；三方逐槽、H/S/U；DIV-06 收窄） |
| m16-chipyard-022 | 2026-11-24 18:12 | RTL cfx32 pmem（寄存器面 + DMA + 源 cfxha 32 捕获投递；同界多源一次进入；H85/S8/U8 槽） |
| m16-chipyard-026 | 2026-11-24 14:39 | RTL 异步捕获缓冲（R2：每次进入整体覆盖、无帧门控、`escape imms18=2 ⇒ CFXESC`；Tiny 43 镜像逐字节同基线） |
| m16-chipyard-025 | 2026-11-24 12:15 | RTL Vast 4 MiB BootROM（窗口 + 稀疏镜像 `SparseTLROM` + 启动路径；DIV-12 删除；零间隙门控） |
| m16-chipyard-024 | 2026-11-24 00:37 | RTL 异步模型修订（cg9 七槽只读、掩码归 monitor、源位图单帧仲裁；DIV-10 删、DIV-11 改写、DIV-15 删） |
| m16-chipyard-018 | 2026-11-23 20:55 | cfx4 RTL PTW/TLB 探针纳管三方（15 case：12 ok/3 gap；DIV-14；旧目录删除；dcache 生成器断链修复） |
| m16-testcases-016 | 2026-11-23 18:21 | cfx63 power 基础用例三方（28 槽寄存器面 + 移交三值；三模式；DIV-12/13 登记） |
| m16-testcases-012 | 2026-11-23 17:24 | fence 基础验证三方（012 三模式 QEMU/gem5 + hmon RTL，013 hmon 三方；保留集/hb 逐条；未覆盖 5 条已登记） |
| m16-testcases-018 | 2026-11-23 16:32 | `tests/arch` 命名规范化（env-* 目录、`.S`、check/gen 前缀、引用同步；改名逐字节 md5 对账、3 路注入） |
| m16-chipyard-021 | 2026-11-23 16:00 | RTL cfx15 hart（cg8 + 新增 cg9 16 rc + hart-first TIMER 投 cfx_hart/supv；H 58 槽、U/S 14 槽） |
| m16-chipyard-020 | 2026-11-23 12:44 | RTL cfx0/2 同步模式路由（U/S 进入、switch_run_mode、同步帧、两轴 CFXPERM；异步按 ADR-0060 移交 021/022） |
| m16-testcases-017 | 2026-11-23 09:18 | env 权限准备 + BootROM hmon 源（三模式 cfx5/cfx4 签名一致；回归 26/26；45 项 + 5 路注入） |
| m16-gem5-024 | 2026-11-23 07:24 | cfx5 进 kCfxhaMap（9→10），通用 cg0–cg7 + cg8 专属、两轴权限/trap/escape；25/25 + 43/43 |
| m16-chipyard-019 | 2026-11-23 00:51 | RTL cfx0/2 寄存器面（A；47 记录、Tiny 38/38 不回归；CFXPERM 判定留 020） |
| m16-qemu-005 | 2026-11-23 00:46 | cfx5 通用 `cg0–cg7`（含 `cg3 rc12` deleg；supv 可访问；16/16 + 29/29） |
| m16-qemu-003 | 2026-11-23 00:12 | cfx5 命令接线（D clean/invalidate/flush、all/单行/区间；I 侧由 RAM 写自动失效；26/26 + 46/46） |
| m16-qemu-002 | 2026-11-22 23:16 | 影子 D-Cache 数据通路（8×128×64 B；DMA/装载直连；10/10 + 29/29） |
| m16-chipyard-017 | 2026-11-22 22:08 | RTL cfx5 命令接线（D/I clean/invalidate/flush、all/单行/区间、I 先 D；探针 29 记录/118 事件） |
| m16-qemu-004 | 2026-11-22 22:06 | QEMU fence 保留集对齐（`6–14, 16–31, 35–61`；三载体 56 B 签名同；ISS-432 关闭） |
| m16-gem5-023 | 2026-11-22 22:04 | off 下 cfx5 no-op（exist=0、五寄存器可访问、合法命令无效果、非法 CFXREG；on 不回归） |
| m16-testcases-015 | 2026-11-22 21:29 | `tests/arch` hmon/smon/umon 运行模式环境（三模式签名一致；26 条未迁移清单） |
| m16-qemu-001 | 2026-11-22 21:26 | QEMU `cache-model=off/on` + cfx5 寄存器面（off 合法 no-op/非法 CFXREG；32/32 + 51/51） |
| m16-spec-002 | 2026-11-22 20:20 | CACHE-27 补 `cache-model` 维度（off=存在/no-op、非法仍 CFXREG；on=0b11/真维护）；版本不升 |
| m16-gem5-022 | 2026-11-22 18:25 | I 侧自修改证伪成功（正确构造单行/区间均 0x10，去 clean D 才 0x92）+ monitor 交接 flush；021 结论作废记 ISS-514 |
| m16-infra-001 | 2026-11-22 18:10 | 新增评测节点 `zzx-NF5280` 并引导到就绪（L1 红集与主控机逐项相同；inst 双门控 PASS；修引导脚本 step 6 乱序） |
| m16-chipyard-016 | 2026-11-22 17:09 | RTL cfx5 寄存器面（`cache_exist=0b11`、enable/start/size、ctrl WO；22 条记录；Tiny 不回归） |
| m16-gem5-021 | 2026-11-22 16:59 | gem5 cfx5 命令（D 侧 clean/invalidate/flush、范围/使能/异常；I 侧结论已由 022 证伪并修正，见 ISS-514） |
| m16-testcases-011 | 2026-11-22 16:36 | picolibc clock 探针归位（`picolibc_clock_probe.c` + 单独驱动；ansibench 只留四件） |
| m16-testcases-007 | 2026-11-22 16:13 | `check-arch` 与 `check-arch-smoke` 同一代表集（10 smoke + 25 服务 + carrier 15 条 29/29） |
| m16-testcases-008 | 2026-11-22 14:47 | `unit` 允许 `system` 并登记 `unit-gem5-hmon-001`（473 条索引；KNOWN-RED 记 ISS-509） |
| m16-testcases-010 | 2026-11-22 14:45 | cfx4 PTW/TLB 15 条纳管（QEMU/gem5 各 29/29；`arch-ptw-001..015`） |
| m16-testcases-006 | 2026-11-22 13:33 | `tests/arch` 落点与驱动骨架（`run_arch.py`、`machine: vast`、驱动型 case、Tiny hmon 迁出；24 PASS + 1 SKIP） |
| m16-gem5-020 | 2026-11-22 13:31 | gem5 cache 前置：flags + `initiateAcc` + `--caches`/L1（64 KiB）；off 38/38+10/10、on dcache 93/17 且签名同 |
| m16-testcases-004 | 2026-11-22 12:22 | Vast arch 三平台盘点（9 cfx × 3、151 条引用；RTL 仅 cfx3/4/63，cfx5 无命令面）+ `tests/arch/PLAN.md` + Process-09 §1/§3/§5/§6/§7.1 修订 |
| m16-testcases-005 | 2026-11-22 12:10 | 签名脚本 `signature.py` 迁 `tests/shared/`（6 处引用；`check-inst-asm` 38/38、`check-arch-smoke` PASS） |
| m16-testcases-003 | 2026-11-22 00:45 | `lr`/`sc` 保留语义三平台对齐（ISS-443 异常清保留 + ISS-435 精确粒度；ISS-440 记 GAP） |
| m16-chipyard-010 | 2026-11-21 22:08 | Vast I-Cache（8 路×128 组×64 B，readOnly；`WumingCache` 单一实现；Tiny 零增益） |
| m16-chipyard-009 | 2026-11-21 14:21 | Vast D-Cache（8 路 × 128 组 × 64 B = 64 KiB；写回+dirty+写分配；PTW 页表读走缓存端口；Tiny 零增益） |
| m16-chipyard-015 | 2026-11-21 02:37 | 重生成签入 `bootrom.tiny.hex` 至 `a5d78816…`（跟随 `m15-testcases-021`；power 段 344→292 B） |
| m16-chipyard-014 | 2026-11-21 02:19 | 窄 `lr` 高位保持（写回拍同拍合并；9 条实测、`.o` 不回归、拍数不变） |
| m16-chipyard-008 | 2026-11-21 00:07 | I/D TLB（2×8 + 4 超页 FA/LRU、I 无 D 位、双表失效 I→D；验收 1 登记缺口） |
| m16-spec-001 | 2026-11-20 22:20 | `cfx_cache`（cfx5）寄存器与语义（重定义 `cg8 rc9`；`addr_start` `PA[55:0]`；新建 cache 契约；Kaiwu §3.2） |
| m16-testcases-002 | 2026-11-20 18:01 | 签名机制抽到 `tests/shared`（inst 委托 + `signature.py`；ptw 3 例接线；272 流 md5 全同） |
| m16-chipyard-007 | 2026-11-20 15:43 | Vast PTW 两级步查（L1/L2/超页/大端 PTE/A-D 回写；第 7 条移入 011） |
| m16-gem5-019 | 2026-11-20 12:47 | gem5 实现差异盘点（25 条；2 CPU×2 机型；checkpoint 静默丢状态） |
| m16-chipyard-013 | 2026-11-20 12:29 | chipyard 实现差异盘点（27 条；Vast 无 2 GiB PA RAM、rocket 无硬件 A/D） |
| m16-gem5-018 | 2026-11-20 02:40 | 块传送 `beats` 按起始相位（8 B 相位零回归；`ldm.ub` N=8 相位 2 ⇒ 24） |
| m16-chipyard-012 | 2026-11-20 02:29 | RTL `scmp` 无序改 canonical（四方一致达成；FP 单元台 oracle 同步） |
| m16-gem5-017 | 2026-11-20 01:10 | 配置命名统一：`se.py` + `--cpu-type`，删 `se_timing.py`（series 106） |
| m16-gem5-015 | 2026-11-20 00:55 | FS 加 `--cpu-type {atomic,timing}`（tiny/vast 两机型；`functionalFsAccess`；周期 FS==SE） |
| m16-gem5-016 | 2026-11-20 00:45 | 周期表 08/09/10 拆行（移位=2；逐册行成为拍数来源；clmul 判 A/2） |
| m16-chipyard-006 | 2026-11-20 00:30 | Vast 核参数与地址通路（`useVM`/PTBR·ASID/`ptw_enable`/`cfx_ptw` 寄存器面/地址路由；Tiny 零增益） |
| m16-gem5-014 | 2026-11-19 17:52 | Vast 一级 I/D TLB（2×8 + 4 超页 LRU、双表失效、A/D OR 合并） |
| m16-chipyard-005 | 2026-11-19 02:00 | RTL 补 `inner_cfx_code`/`prevCfx`（cg5 rc1 RW、CFXESC 交当前 cfx；sim md5 `9b6928e0`） |
| m16-gem5-013 | 2026-11-19 01:45 | gem5 补 `prevCfxCode`（trap 保存/escape 恢复/cg5 rc1 RW）；删恢复行 ⇒ `0x7E` |
| m16-gem5-012 | 2026-11-18 19:09 | C/D 周期表分行给值（ld=9/st=10、`stm` 用 `n_base=1`、`ldm` 不带；容差 ±1→0） |
| m16-chipyard-004 | 2026-11-18 11:20 | `stm` 偏置实测（362 样本）：**固定 +1、与 N 无关**；附带发现 beats 相位算法（N19） |
| m16-gem5-011 | 2026-11-17 14:55 | semihost 默认关（fs.py on→off，与 ARM/RISC-V 一致）+ 触发/传参/服务表/宿主边界文档化 |
| m16-chipyard-001 | 2026-11-17 14:03 | 周期模型全量复测回填（272 镜像/190131 样本；ld=9/st=10、乘除=1、RAS 实测；R2/R3 按裁定作废） |
| m16-chipyard-003 | 2026-11-17 08:16 | chipyard 侧子原因（`GewuCauseId` + 校验器；仅 `NONPTW` 可达；三方 cmp 逐字节一致） |
| m16-gem5-009 | 2026-11-17 07:59 | gem5 侧子原因 18 位 + `checkCauseId`（F1 修 `Fault::invoke` PC 前进、向量首条不再双执）；与 QEMU 全宽一致 |
| m16-gem5-010 | 2026-11-17 01:40 | gem5 侧 `Kaiwu-Vast` 同步异常路由对齐 `§5.2`（staged 真删、帧四项与 QEMU 逐字段同；`check-arch` 由 qemu-005 验收覆盖） |
| m16-chipyard-002 | 2026-11-16 04:16 | cfx 独立为 `dadao-gewu` generator（`GewuFileIO`/`GewuFile` 参数化、重定向归 core；sim md5 `bd5e75b3…`，37 镜像 cycle 逐条相同） |
| m16-gem5-007 | 2026-11-15 12:20 | 对标脚手架 `compare_chipyard.py` + M17 报告（三例 3.10/3.68/3.95×；差距 80–87% 来自 gem5 无 icache 的取指） |
| m16-testcases-001 | 2026-11-15 09:20 | 跑批进度看板 `progress.py`（done/run+ETA/孤儿标 unlogged）+ `run_embench_e2e.py --jsonl-out` 逐例增量落盘 |
| m16-gem5-006 | 2026-11-15 07:05 | 访存时序（XBar+SimpleMemory；Timing 数据侧 functional 已披露；C 类 13/13 ≤1 拍；D 类 BLOCKED 转绿） |
| m16-gem5-005 | 2026-11-15 05:40 | 块传送计拍（多元素 `1×N + 8×⌈N·w/8⌉`、`rd2rd` 类 `1+N`；N=2/4/9 与 chipyard 逐条相等；D 类端到端待 006） |
| m16-gem5-008 | 2026-11-14 15:30 | 周期表 provenance 落地（provisional 48 行不进时序模型；B3 全占位） |
| m16-gem5-004 | 2026-11-14 07:40 | 动态类接入（B1/B2/B3/B5/`swym`/ras-kind/trap-target/range；逐类差异 0） |
| m16-gem5-003 | 2026-11-14 05:10 | 静态类接入（`enable_wuming_cycles` 默认关；表值−1；逐族差异 0） |
| m16-gem5-002 | 2026-11-14 02:00 | 周期分类表 264/264（18 类；生成器 + `check-wuming-cycles` 门控） |
| m16-gem5-001 | 2026-11-14 00:35 | 每指令延迟钩子（默认 0；`advanceInst` 尾部单 hunk；行为逐字节不变） |
