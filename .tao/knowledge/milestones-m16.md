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

## 进行中（已派单：待开始 / 待验收 / 待返工）

| 编号 | 派单时间 | 预估时间 | 一句改动 |
| --- | --- | --- | --- |
| m16-testcases-006 | 2026-11-22 12:23 | 中 | `tests/arch` 落点与驱动骨架（`run_arch.py`、`machine: vast`、Tiny hmon 迁出） |

## 已验证

| 编号 | 完成时间 | 一句改动 |
| --- | --- | --- |
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
