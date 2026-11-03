# GEM5-016t: FS Machine-v5-Node（gem5 FS Node：4 MiB BootROM / 2 GiB RAM / hmon / PTW / hypv）

**模块**：gem5
**项目里程碑**：M11
**依赖**：`GEM5-015t`（gem5 FS Tiny：FS workload/TLB/MMU/semihosting/MachineFault 与 `configs/dadao/fs.py`；已验证并入 `master`）、`GEM5-014t`（SE 平台骨架与 SE 隔离基线，已验证）、`QEMU-080t`（Machine-v5-Node 系统机，已验证；同模式对照真源）、`SPEC-183t`（`spec/Machine-v5-测试机运行环境.md` 几何/装载/cfx/semihosting 真源，已验证）、`TESTCASES-092t`/`TESTCASES-093t`/`TESTCASES-094t`（Node inst/arch/L3 资产，已验证；只读复用）
**状态**：已验证

## 执行环境
**执行环境**：本地（仓库根；从 `master` 建独立 `git worktree` + 分支 `GEM5-016t`；组件源树 `.work/source/gem5` 内收敛为 base+1 个 dadao 提交，不 merge、不 push）。开工前必须确认 `GEM5-015t` 已 `已验证` 且已合入 `master`；否则本任务 **BLOCKED**，不得在未落地的 Tiny FS 上另起一套并行 FS。

## 用户已定口径（2026-11-04，主会话转达）

- **只做 gem5 FS `Machine-v5-Node`**：4 MiB BootROM `0xffff_ffc0_0000`–`0xffff_ffff_ffff`、复位 `0xffff_ffff_0000`（ROM 内偏移 `0x3f_0000`）、PA RAM 2 GiB `[0, 2 GiB)`；hmon/smon/pmem SRAM 与 `hmon`/`PTW`/`hypv` 启动链。
- **Node 页表按测试资产/QEMU-080t 口径落地 identity**：L1 index **0–3** 共 4 个 512 MiB 超页，VA=PA `[0, 2 GiB)`，`SPF=0xFF`；测试本体入口 `0x10_0000`、`SP=0x7fff_0000`。**不按 `spec/Machine-v5 §6` 的 `0x0200_0000_0000` 口径改实现**；冲突按 `ISS-340` 登记，不擅自改 `spec/`。
- **smon 保留、M11 不验收**：保留 smon SRAM（`0x0bff_0000_0000`，64 KiB）、cfx2 寄存器/向量字段与 `power → hmon → smon` 路径的机器能力，但不启动 smon、不把 smon 纳入本任务验收。
- **复用测试资产**：`tests/shared/machine-profiles.yaml`（`node`）、`tests/shared/bootrom/step5/{power,hmon,smon}.S` + `.lds`、`tests/shared/linker/dadao-node.lds`、`tests/shared/crt0/minimal_crt0.s`、`tests/shared/asm/machine-node.inc`、`tests/arch/umon/**`、`tools/testcases/**`、`tools/qemu/semantics_gate.py`；**只读，不改**。
- **同模式对照 = QEMU system Node**（`qemu-system-dadao -M dadao-m1,profile=node,bootrom-image=…`），不对 QEMU user；**QEMU 通过集合 ⊆ gem5 通过集合**，gem5 通过而 QEMU 未通过只记录、不直接判 gem5 绿。
- **真实执行范围 = 完整 `inst` + `arch` + `embench`（system E2E）**；**不跑 picolibc**（Node `picolibc=false`）。
- **SE 文件语义不动**：`GEM5-014t` 的 SE 路径与 `GEM5-015t` 的 Tiny FS 路径均不得改变语义；Node 逻辑用 workload/profile 判定隔离，不用全局开关。
- **CPU/时序**：`AtomicSimpleCPU`，`mem_mode=atomic`；**无 cache、无时序、无多核/NUMA、无 GDB/checkpoint/KVM、无平台设备**。
- **改动范围（硬）**：只 `components/gem5/**`（补丁/`series`/`changelog.md`/`README.md`）+ 本任务书 + `.tao/knowledge/milestones.md`。**不改** `components/qemu/**`、`components/{llvm-project,musl,picolibc,embench-iot}/**`、`spec/**`、`tests/**`、`contracts/**`、`.tao/contracts/**`、`.tao/adr/**`、`Makefile`、`manifests/**`、`tools/**`、`docs/**`；**不复制 0628/QEMU 代码**（0628 只读，仅吸收结论并标「内容溯源，非执行必需」）。
- **不可成立的 BLOCKED 必须经用户裁定**：不得自行跳过、降低期望、改测试资产或把 QEMU 红算作 gem5 绿；BLOCKED 须附 spec 引用、根因与现场日志。

## 现状与问题根源（2026-11-04 现场核对，只读）

1. **gem5 侧还没有 FS Node**：`GEM5-015t` 仅规划 FS Tiny（64 KiB BootROM + 8 MiB SRAM、identity 段检查、fault→退出码、25 项 semihosting），当前 `待开始`；其 FS 文件/接口是本任务的起点。Node 所需的 4 MiB BootROM、2 GiB PA RAM、hmon/smon/pmem SRAM、PTW/TLB、monitor/cfx 寄存器、DMA、时间/中断均未实现。
2. **fault 路径当前全部 panic，且不分模式**：`faults.hh` 的 `IllegalInstruction`/`MalignInstruction`/`UnimplementedInstruction` 与 `inst.cc::mapExecFault` 对 `RasOverflow/RasUnderflow/CfxReg/CfxEsc` 均 `panic`；`Gem5B1Context::trapTo` 只接 `trap cfx0,0`（SE syscall），其余（含 Node 的 `trap cfx_hmon`/`cfx_umon`）`panic`；`escapeFrom` 恒 `false`。Node 要求同步 fault **进入 current-mode monitor**（hypv→hmon、supv→smon、user→umon），由 hmon 的 exit/resume 策略决定退出码；**不能**沿用 Tiny 的「fault 直接退出」。
3. **PTW/TLB 完全缺失**：SE 的 `DadaoISA::TLB` 是宿主页表直通，Tiny FS 是 identity + 段检查；Node 需要真实页表步进（64 KiB 普通页 / 512 MiB 超页）、`PTBR`/`ptw_enable`/ASID/TLB 控制、HSJU/R/W/X、SPF/GPF、A/D 回写、`PTWERR`、`cfx_ptw` 异常路由。
4. **cfx 寄存器文件/监视器/权限/DMA 未实现**：Node 的 power/hmon 代码依赖 `cfx2rc/cfx2rd` 访问 cfx3/cfx4/cfx17/cfx63 的 cg3/cg5/cg8/cg9/cg12/cg15 寄存器；hmon 还要用 cfx_pmem DMA 把页表模板写到 PA 0，再开 PTW、设 `cfx_umon` 向量。arch 套件还覆盖 cfx0/1/2/3/63 寄存器面、cg7 描述符、deleg、cfx15/18 时间/hart、异步中断仲裁。现有 B6 只有指令级 `trap`/`escape`/`cfx2rd`/`cfx2rc` 的骨架，无真实寄存器文件与 monitor 进入/退出。
5. **QEMU Node 已提供同模式参考且测试资产已收口**：`QEMU-080t` 实现 4 MiB BootROM、2 GiB RAM、hmon/PTW/hypv、identity 4×512 MiB 超页、DMA；`TESTCASES-092t`/`093t`/`094t` 已把 Node 全量 `inst`（`968 = 963 passed / 5 deferred / skipped_profile=44`）、`arch-smoke`（10/10）、13 个 L3 探针与 `run_m5_e2e` 收口到可执行/可判定状态。本任务不改 QEMU/测试，只在 gem5 侧重做同模式机器。
6. **冲突已登记**：`spec/Machine-v5 §6` 写 L1 `0x1000`–`0x1003` / VA `0x0200_0000_0000`–`0x0200_7fff_ffff`；测试资产 `hmon.S` 与 QEMU-080t 按用户口径落地 **identity**（L1 0–3、VA=PA）。`ISS-340` 已登记该冲突，本任务沿用 identity、**不改 spec**（见「说明 §1」）。
7. **可构建基线**：`.work/source/gem5` = gem5 `v25.1.0.1` / `c8222cc6` + 1 个 dadao 补丁提交；`build/DADAO/gem5.opt` 可增量。Node 新增 SimObject 会重生成 `params/**`，预计增量重编 **15–40 分钟**；2 GiB `SimpleMemory` 会增加宿主内存占用，需在证据脚本中申报。

## 目标

在 `GEM5-015t` 的 FS Tiny 基础上补齐 **Machine-v5-Node 的 FS 平台**，让 `tests/inst`、`tests/arch`、Embench（system E2E）在 gem5 FS 上真实执行，并与 QEMU system Node 在**同一 case/check 上通过/失败与退出码一致**：

1. Node 几何/复位：4 MiB BootROM、2 GiB PA RAM、hmon/smon/pmem SRAM、复位 `0xffff_ffff_0000`、`ptw_enable=0`、`PTBR=0`、TLB 空、`hypv/cfx63`。
2. 启动链：power（cfx63/hypv）校验 4 MiB image index table、装 hmon 到 hmon SRAM、设 H 向量并 `trap cfx_hmon` → hmon 建 4 个 identity 超页 PTE、经 cfx_pmem DMA 写 PA 0、失效 TLB、`PTBR=0`、`ptw_enable=1`、设 `cfx_umon` hypv 向量 → 测试本体在 hypv 执行。
3. PTW/TLB：超页 + 普通页 + SPF/GPF + HSJU/R/W/X + A/D + `PTWERR` + `cfx_ptw` 异常优先级；TLB 命中/填充/clean/invalid/flush。
4. cfx/monitor：cfx0/1/2/3/63 寄存器文件、cfx4 PTW、cfx17 pmem SRAM + cg15 DMA、cfx15/18 时间/hart、异步中断仲裁、cg7/deleg；`trap`/`escape`/`cfx2rd`/`cfx2rc` 与运行模式切换；cfx5 未实现 ⇒ `CFXREG`；reserved cfxha ⇒ `ILLI`/`CFXMEM`。
5. QEMU system Node 同模式对照：`inst` 全量、`arch`（smoke + 13 探针）、`embench`（O0/O2）；**QEMU 通过集合 ⊆ gem5**，逐条归因。
6. 零退化：SE（`GEM5-014t`）与 Tiny FS（`GEM5-015t`）语义不变；B0–B7 解码/执行计数不变（`GEM5-013t`）。

## 接口规范

### 0. profile、几何与复位（Node，冻结；`spec/Machine-v5 §1/§1.1`；`tests/shared/machine-profiles.yaml` `node`）

| 区域 | 基址 | 大小 | 访问 | 说明 |
| --- | --- | --- | --- | --- |
| BootROM | `0xffff_ffc0_0000` | 4 MiB | 取指/读；写按只读区处理 | 偏移 0 image index table；末 64 KiB（`0xffff_ffff_0000` 起）为复位/启动代码 |
| PA RAM | `0`（PA 空间） | 2 GiB | 经 PTW 读写/取指 | 物理 `[0, 2 GiB)`；**不设核内地址别名** |
| hmon SRAM | `0x0fff_0000_0000` | 64 KiB | 读写/取指 | H-mode 向量默认起始；`hmon` 自己设 `SP` |
| smon SRAM | `0x0bff_0000_0000` | 64 KiB | 读写/取指 | **保留**；M11 不启动、不验收 |
| cfx_pmem SRAM | `0x47ff_0000_0000` | 64 KiB | `ld/st` | cfx_pmem 内部偏移 `0x3ff_0000_0000`；越界 ⇒ `CFXMEM` |

- **复位**：`PC = rb0 = 0xffff_ffff_0000`；`rb1–rb63 = 0`；`rd* = 0`；`ra* = 0`；`rf0 = 0x7FF8_0000_7FC0_0000`；`rf1–rf63 = 0`。`inner_run_mode = hypv`、`inner_cfx_code = 63`、`ptw_enable = 0`、`PTBR = 0`、TLB 空、ASID = 0；cfx 复位值按 `spec/DADAO-12`/`DADAO-13`。**平台不得代设 `SP`**（由 power 设置）。
- **物理内存零初值**：所有 `SimpleMemory` 匿名零映射；不得用镜像外的旧内容或非零填充。
- **配置常量唯一真源**：`configs/dadao/fs.py --profile node` 的几何常量必须与 `tests/shared/machine-profiles.yaml` 的 `node` 逐项相等（`bootrom_base/size`、`reset_pc`、`ram_base/size/end`、`entry/sp`、`kernel_base/kernel_reserved`、hmon/smon/pmem SRAM）。`--dump-geometry` 输出 `GEM5_GEOMETRY key=value`，供证据脚本机械比对；**禁止手写副本漂移**。

### 1. 访问路由与 fault（Node；`spec/Machine-v5 §1.2/§3/§4`；对照 `QEMU-080t`）

- `addr[47:42] == 0`（PA 窗口）：
  - `ptw_enable = 0` ⇒ 数据/取指一律 `CFXMEM`（`0x81`），**不直通 PA**；
  - `ptw_enable = 1` ⇒ 先 TLB、未命中页表步进；页表异常进入 `cfx_ptw`（cfx4）当前模式向量，**不是**直接退出码。
- `addr[47:42] != 0` 的核内空间：仅实现 cfx2/3/17/63 的 SRAM/ROM 窗口；段内越界 ⇒ `CFXMEM`；保留 cfx（6–14、19–61）的普通 `ld/st` ⇒ `CFXMEM`；`trap`/`escape`/`cfx2rd`/`cfx2rc` 到 reserved cfxha ⇒ `ILLI`（`0x88`）；未实现的 cfx5 寄存器 ⇒ `CFXREG`（`0x84`）。`power` 段 BootROM 之外、无 cfx 归属的 unmapped 访问按测试机约定 `0x87`（与 QEMU Node 对齐）。
- **BootROM 只读**：写 BootROM 必须产生机器 fault（不得静默成功）。具体退出码/路由按 `spec` 与 QEMU Node 实测对齐；若 spec 不清，保留现场并提交用户裁定，不按 RISC-V/ARM 经验补全。
- **Node fault 进入 monitor，不直接退出**：同步 fault 按当前运行模式进入 `cfx_hmon`（hypv）/`cfx_smon`（supv）/`cfx_umon`（user）；保存 `excp_cause`/`excp_cause_info`/`excp_cause_ip`、prev mask/mode，切换 `inner_run_mode`/`inner_cfx_code`，跳到该 cfx 当前模式的 `excp_vector`。只有 hmon 的 exit 策略可用 semihosting `SYS_EXIT` 产生 guest 退出码；**Tiny FS 的「fault 直接退出」语义保持 `GEM5-015t` 原样**，不得被 Node 路径污染。
- **fault 码表**（Node hmon exit 策略与 Tiny 共用测试资产；`ADR-0004 D5.8`）：CFXMEM `0x81`、CFXREG `0x84`、ILLI `0x88`、UNDI `0x89`、RASOF/RASUF `0x8A/0x8B`、MALIGN `0x8C`、IALIGN `0x8D`；Node 的页表异常按 `cfx_ptw` cause 位进入向量，不直接映射为上述退出码。

### 2. BootROM 与装载（`spec/Machine-v5 §6`；对照 `QEMU-080t §1/§3`）

- **`--bootrom <flat>`**：Node 必须**恰好 4 MiB**，装在 `0xffff_ffc0_0000`，其余 ROM 保持零；机器 PC = `0xffff_ffff_0000`。`4 MiB ± 1 字节`/`± 1 页` ⇒ `fatal` 非零退出，打印实际大小与期望值。`--bootrom` 与 legacy `--bios` 不得同给。
- **`--kernel <file>`（可选）**：
  - **raw**：Node `kernel_base = entry = 0x10_0000`、`kernel_reserved = 0`；长度 ≤ `2 GiB − 0x10_0000`，装到 `0x10_0000`；入口由 BootROM/hmon 的 `cfx_umon` 向量决定，**不使用 raw 文件的入口**。
  - **ELF**：`loader::Dadao` 识别；`ELFCLASS64`/`ELFDATA2MSB`/`ET_EXEC`/`e_flags & 0xff == 1`/无 `PT_INTERP`；全部 `PT_LOAD`：`p_vaddr == p_paddr`、`p_filesz ≤ p_memsz`、`[p_vaddr, p_vaddr+p_memsz)` ⊆ PA RAM `[0, 2 GiB)`（Node **不接受** ROM 段；与 Tiny 的 ROM crt 不同）；BSS 由 `MemoryImage` 零填充。`e_entry` 不得覆盖复位 PC；body 入口由 hmon 设置。
  - 任一校验失败 ⇒ `fatal()` 打印文件/段/字段/值 + 非零退出；不得跳过、裁剪或静默重定位。
- **装载顺序**：先 `memory` 零初始化，再 `--bootrom`，再 `--kernel`（若给）；`DadaoFsWorkload::initState()` 用 `system->physProxy` 写镜像后逐线程 `resetThread()+activate()`；`getEntry()` Node = 复位 PC（不是 `e_entry`）。
- **guest 退出**：semihosting `SYS_EXIT`/`SYS_EXIT_EXTENDED` 的低 8 位传播到 host `$?`；`300 ⇒ 44`。首个退出锁定，不再执行后续指令。

### 3. 运行模式、monitor 与 cfx 寄存器（`spec/Machine-v5 §2/§3/§4`；`spec/DADAO-12 §3/§4/§5`；`spec/DADAO-13`）

- **模式**：Node 启用 `hypv`/`supv`/`user`，`jail` 不启用；复位 `hypv`。`trap` 进入目标 cfx 的当前模式向量，并按目标 cfx 的 `switch_run_mode`/`switch_cfx_mask` 切换；`escape` 恢复 prev mode/mask 与 `escape_num`，返回 `excp_cause_ip + (imms18<<2)`（`imms18[17:1] != 0` ⇒ `ILLI`；帧/目标错误 ⇒ `CFXESC`）。
- **cfx 集合（Node）**：`cfx0`（umon）、`cfx1`（jmon）、`cfx2`（smon）、`cfx3`（hmon）、`cfx4`（ptw）、`cfx17`（pmem）、`cfx15`（hart）/`cfx18`（time）、`cfx63`（power）；`cfx5`（cache）为已分配未实现 ⇒ `CFXREG`。smon（cfx2）的 SRAM/向量/寄存器保留，M11 不启动。
- **共有寄存器**：cg0–cg7 按 `DADAO-12 §3`；cg0–cg3 为 user/jail/supv/hypv 模式寄存器（`excp_vector`、`switch_run_mode`、`switch_cfx_mask`、四类同步 mask、`cfx_intr_mask`、`cg_reg_deleg` 等）；cg4–cg6 配置/现场/暂存；cg7 为 16×4 内部空间描述（只读，写 ⇒ `CFXREG`）。RO/RW、数组、reset 值按 spec；非法组合/保留 rc ⇒ `CFXREG`。
- **cfx2rd/cfx2rc**：目标 cfx 的寄存器文件；保留 cfxha ⇒ `ILLI`；未实现 cfx ⇒ `CFXREG`；`cfx2rd` 目的 `rd0` 丢弃写不 ILLI；`cfx2rc` 源 `rd0` 为 0；跨 cfx 权限按 `cfx` mask/deleg 判定，拒绝 ⇒ `CFXPERM`。
- **power 描述符**：cfx63 的 cg7 BootROM 空间描述符必须为 Node 4 MiB（`start`/`size` 与 `spec/Machine-v5 §1.1` 逐项一致）；`space_power` 探针按 spec 派生期望。
- **cfx_pmem DMA**（`DADAO-12 §4.9`）：见 §5。
- **cfx15/18 时间/hart**（arch 面）：`cfx_hart` cg8 rc0 `hart_id`、rc2 `cycle`、rc3 `insn` 64 位；`cfx_time` 1 GHz、64 位；AtomicSimpleCPU 下按指令边界递增，单调、可读；不得返回常量或 32 位截断。
- **异步中断仲裁**（arch 面，`INTEG-051t`）：pending 存在目标 cfx 的 cg5 rc5（TIMER `1<<10`→cfx_hart、PMEM_DMA `1<<8`→cfx_pmem）；最低目标 cfxha 优先；mask/pending 保留与补投按 spec；单 hart，不得引入多核模型。

### 4. PTW/TLB 与页表（`spec/DADAO-12 §2.2.1–§2.2.6/§4.5`）

- 新增 Node 专用 TLB/MMU（可扩展现有 FS TLB，但 **SE 文件 `tlb.*`/`mmu.hh` 语义不动**）：`DadaoNodeTlb : BaseTLB`、`DadaoNodeMMU : BaseMMU`、`DadaoNodeAtomicSimpleCPU`。
- `cfx_ptw` 寄存器：cg8 rc8 `ptw_enable`（0/1）、cg9 rc0 `ptbr`（唯一，PPN[55:16]，64 KiB 对齐）、cg12 rc0 `tlb_control`（clean/invalid/flush × all/VA/range × ASID_ANY）、cg12 rc1 `tlb_asid`、cg12 rc2 `tlb_addr_start`、cg12 rc3 `tlb_addr_size`。写 PTBR/ASID/`ptw_enable` 不隐含 TLB 失效。
- 页表步进：L1 index `VA[41:29]` × 8；L2 index `VA[28:16]` × 8；普通页 64 KiB、超页 512 MiB；PTE 位按 `§2.2.3/§2.2.4`（HSJU/R/W/X/G/A/D/SP/SPF/GPF/P）；`PPN[28:16]` 超页强制清零。
- **identity 首张页表**：`PTBR=0`，L1 PTE 0–3，PPN `0/0x2000/0x4000/0x6000`，`SPF=0xFF`，flags `P/SP/D/A/G/X/W/R = 0xEF`，HSJU=`0xF`；VA=PA `[0,2 GiB)`。hmon 的模板由 cfx_pmem DMA 写到 PA 0；测试本体入口 `0x10_0000`、`SP=0x7fff_0000`。
- 异常优先级严格按 `§2.2.6`：`ptw_enable=0`→CFXMEM；L1 `P=0`（SP=1→ISPTRAP/DSPTRAP；SP=0→IGPTRAP/DGPTRAP）；SPF 位 0→ISPFTRAP/DSPFTRAP；L2 `P=0`→IGPTRAP/DGPTRAP；GPF 位 0→IGPFTRAP/DGPFTRAP；HSJU 不符→NU/NJ/NS/NHPERM；R/W/X 不符→NX/NW/NRPERM。取指用 `I` 前缀、数据用 `D` 前缀，均进 `cfx_ptw`。
- A/D：填充时取 PTE.A/D 作为 local，不产生回写；读/取指置 A，写置 A/D；`clean`/`flush`/替换时原子 OR 回写 PTE；缺页/权限失败不填充、不更新 A/D；回写失败 ⇒ `PTWERR`（`1<<7`，cause_info=PTE PA）。
- TLB：命中不重读 PTE；miss 成功才填充； `clean` 保留、`invalid` 不写回删除、`flush` 回写后删除；ASID/G 匹配按 spec；条目数/替换策略由实现决定，但须覆盖探测用例。

### 5. cfx_pmem DMA（`spec/DADAO-12 §4.9`）

- 64 KiB SRAM 在 `0x47ff_0000_0000`，CPU 用 `ld/st`；越界 ⇒ `CFXMEM`。
- cg15：rc0 `dma_src`、rc1 `dma_dst`、rc2 `dma_size`（30 位，`1..2^29`）、rc3 `dma_ctrl`（START 自清、DIR 0=CFX→PA/1=PA→CFX、IRQ_EN）、rc4 `dma_status`（BUSY RO、DONE/ERROR W1C、ERR_CODE one-hot RO）。
- 地址：CFX 侧取低 42 位、PA 侧取低 56 位，高位忽略；DIR=0 时源为 pmem SRAM、目的为 PA；DIR=1 反之。DMA 可读 RAM/BootROM、只可写 RAM；其余 PA 属 `PA_FAULT`。
- 异步：START 后 BUSY=1，完成清 BUSY、置 DONE 或 ERROR；BUSY 期间对 src/dst/size/ctrl 的写入（含 START）与 DONE/ERROR W1C 被忽略；ERROR W1C 清 ERR_CODE。`IRQ_EN=1` 时 DONE/ERROR 触发 `PMEM_DMA`（`1<<8`）；mask 时置 pending。
- hmon 的启动路径必须真实走 DMA：写 pmem SRAM 模板 → cg15 START（DIR=0，32 B）→ 轮询 BUSY → 再开 PTW；**不得**由宿主/平台代写 PA 0。

### 6. CPU/System/配置（无时序）

- 复用 `GEM5-014t` 的 `DadaoISA`/`DadaoDecoder`/`DadaoInterrupts` 与 `GEM5-015t` 的 FS 组件；Node 新增 `DadaoNodeTlb`、`DadaoNodeMMU`、`DadaoNodeAtomicSimpleCPU`、Node workload/profile 参数。
- `System(mem_mode='atomic')`、`SystemXBar`、多个 `SimpleMemory`（BootROM 4 MiB、PA RAM 2 GiB、hmon/smon/pmem 各 64 KiB），`range` 精确；`system.mem_ranges` 同步；`system.system_port` → `membus.cpu_side_ports`；`system.workload = DadaoFsWorkload(profile='node', ...)`；`cpu.createInterruptController()`、`cpu.createThreads()`；`Root(full_system=True, system=system)`。
- **无** cache、无平台设备（UART/RTC/CLINT/PCI）、无 GDB、无 checkpoint、无 multi-core、无 KVM；`mem_mode=atomic` 唯一模式；2 GiB `SimpleMemory` 的宿主内存占用须在证据中申报。
- `configs/dadao/fs.py` 扩展 CLI：`--profile {tiny,node}`（默认 tiny，保持 015 兼容）、`--bootrom <file>`、`--kernel <file>`、`--semihost {on,off}`、`--semihost-argv`/`--semihost-arg`、`--semihost-system {deny,native}`、`--console-out <path>`、`--max-ticks <n>`、`--dump-geometry`、`--dump-semihost-services`、`--trace-cpu <path>`（输出 QEMU `-d cpu` 子集 `PC:`/`MODE:` 块，供 `run_m5_e2e` 的 bootrom 观测）、`--outdir`（gem5 既有）。
- 退出：`exit_event = m5.simulate()`；`getCause() == "exiting with last active thread context"` ⇒ `sys.exit(exit_event.getCode() & 0xff)`；否则打印 cause 并 `sys.exit(125)`。**禁**在仓库内落 `m5out/`；证据统一 `--outdir /tmp/opencode/GEM5-016t/**`。

### 7. 同模式对照驱动（证据层，不入 git）

- 提供 **QEMU→gem5 参数映射 shim**（`.work/evidence/GEM5-016t/**` 或 `/tmp/opencode/GEM5-016t/**`，**不进仓库**），接受并只映射：
  - `-M dadao-m1` / `-machine dadao-m1[,profile=node][,bootrom-image=…]`
  - `-bios <file>`（仅 Tiny/legacy；Node 4 MiB 用 `bootrom-image`）
  - `-kernel <file>`、`-semihosting-config enable=on,target=native[,arg=…][,chardev=…]`
  - `-chardev file,id=…,path=…`、`-display none`、`-nographic`、`-monitor none`
  - `-d cpu` + `-D <log>`（写出与 `run_m5_e2e.parse_cpu_log()` 兼容的 `PC: <hex>` / `MODE: <n>` 块）
  - **未知参数 ⇒ rc=2**，不得静默丢弃；不得改变判据（只看 guest 退出码/控制台/逐 check 结果）。
  - 映射到 `gem5.opt --outdir … configs/dadao/fs.py --profile node --bootrom … --kernel …`。
- **embench 的 profile 缺口**：`run_embench_e2e.py` 固定 `-M dadao-m1 -kernel <elf>`，不传 bootrom；证据层用 **QEMU Node wrapper**（给 QEMU 命令注入 `profile=node,bootrom-image=…`）和 **gem5 shim 环境**（`GEM5_SHIM_PROFILE=node`、`GEM5_SHIM_BOOTROM=…`）补齐，映射逐项写入证据；不得改 `tools/**`。
- 至少 **1 条**用例必须**绕过 shim**、直接 `gem5.opt configs/dadao/fs.py --profile node …` 运行，证明结论不只依赖映射层。
- 对照口径：QEMU 基线 = 开工时 `master` 安装根 `qemu-system-dadao`（含 `QEMU-080/082`），记录 md5；**QEMU 通过集合 ⊆ gem5 通过集合**；gem5 通过而 QEMU 未通过 ⇒ 记录并另立 QEMU 调试任务，不阻断本任务；gem5-only 失败 ⇒ 本任务缺陷。

### 8. SE 隔离与 Tiny 回归

- `src/arch/dadao/{process,se_workload,tlb,mmu}.*` 与 `configs/dadao/se.py` 的 SE 语义/文本门控保持 `GEM5-014t` 不变；Node 逻辑一律用 `DadaoFsWorkload` + profile 判定，**不得**用全局开关波及 SE。
- `configs/dadao/se.py` 的 `hello`/`fail` fixture rc/stdout 与 `GEM5-014t` 基线一致；`ISA::inUserMode()` SE 仍 `true`，Node 按当前模式返回。
- `GEM5-015t` 的 Tiny FS 行为（64 KiB BootROM/8 MiB SRAM/raw 前缀/`SP`/fault 直接退出）保持；Node 路径不得复用 Tiny 的 `MachineFault` 直接退出语义。

## 文件范围

**新增/修改补丁**（`components/gem5/patches/`，一文件一补丁；由 `python3 tools/infra/make_patch.py gem5` 导出，禁手改）：

- 新增 Node FS 专用源（命名可调，但须独立于 SE 文件）：`src/arch/dadao/node_ptw.{hh,cc}`（PTW/TLB/PTE/A-D）、`node_cfx.{hh,cc}`（cfx 寄存器文件/monitor/trap/escape/权限）、`node_pmem.{hh,cc}`（pmem SRAM + cg15 DMA）、`node_platform.{hh,cc}`（cfx15/18 时间/hart、异步中断仲裁）、`node_workload.{hh,cc}`（或扩展 015 的 `fs_workload` 以支持 profile）。
- Python SimObject：`src/arch/dadao/DadaoNodeTlb.py`、`DadaoNodeMMU.py`、`DadaoNodeWorkload.py`、`DadaoNodeAtomicSimpleCPU.py`（命名可调）。
- 配置：`configs/dadao/fs.py`（扩展 `--profile node`/几何/装载/trace；Tiny 路径保持）。
- 修改：`src/arch/dadao/SConscript`（`Source()`/`SimObject()`）、`isa.hh`/`isa.cc`（Node reset/mode/cfx 状态/`inUserMode()`）、`faults.hh`（Node fault/页表异常类）、`inst.cc`（`trapTo`/`escapeFrom`/`mapExecFault` 的 Node 分支；SE/Tiny 分支逐字保留）、`DadaoCPU.py`/`DadaoMMU.py`/`DadaoTlb.py`（仅新增 Node 子类，SE 类不改）。
- `components/gem5/series`（+N，字典序）、`changelog.md`（`## M11` 追加 `- **<日期> GEM5-016t**` + 摘要缩进行 + `  - 执行者：engineer`）、`README.md`（Node FS 段：几何/启动链/CLI/边界/已知限制）。

**仓库侧**：本任务书、`.tao/knowledge/milestones.md`。**不改**：见「用户已定口径」硬范围；证据/临时物只落 `.work/evidence/GEM5-016t/**`、`.work/log/gem5/**`、`/tmp/opencode/GEM5-016t/**`（均不入 git）。

## 验收标准

1. **补丁/源树/构建/对象注册**：`make check-patch-tree` rc=0（gem5 作用域；补丁数现场统计，`series` 行数 = 磁盘 patch 数且字典序）；`make check-source-state` rc=0（gem5 HEAD = base+1、worktree 干净）；`make build-gem5` rc=0；`gem5.opt --help` rc=0；`gem5.opt --list-sim-objects` 含 Node workload/TLB/MMU/CPU（Python 别名以 probe 导入 + 实跑为等价证据）；`configs/dadao/fs.py --profile node --dump-geometry` rc=0。
2. **几何/复位/零初值**：`--dump-geometry` 与 `tests/shared/machine-profiles.yaml` `node` 逐项相等（BootROM 首址/大小、复位 PC、PA RAM 首址/大小/末址、`entry`/`sp`、`kernel_base`/`kernel_reserved`、hmon/smon/pmem SRAM）；guest 观测复位后 `rb0 == 0xffff_ffff_0000`、`rb1 == 0`、`rf0 == 0x7FF8_0000_7FC0_0000`、其余 GPR/RA=0；`ptw_enable=0`/`PTBR=0`/TLB 空；未写内存读回零；smon SRAM 存在但未被启动。
3. **BootROM/装载**：`--bootrom` 4 MiB 接受并从 `0xffff_ffff_0000` 执行；`4 MiB ± 1 字节`/`± 1 页` ⇒ rc≠0 且打印实际/期望大小；`--bootrom` 与 `--bios` 同给 ⇒ rc≠0；raw `-kernel` 落 `0x10_0000`、无前缀、`SP` 由 power 设为 `0x7fff_0000`；ELF（`dadao-node.lds`）`PT_LOAD` 落 PA RAM、`e_entry` 不覆盖复位 PC、越界/`ET_DYN`/非大端/`PT_INTERP`/ROM 段 ⇒ rc≠0 且报具体项。
4. **启动链（power→hmon→body）**：真实执行 `tests/shared/bootrom/step5/bootrom_step5.bin`（或 `make build-bootrom` 产物），guest 观测 power（`0xffff_ffff_*`）→ hmon（`0x0fff_*`）→ body `0x10_0000`（hypv）；`PTBR=0`、`ptw_enable=1`、L1 4 项 PTE（PPN `i*0x2000`、`SPF=0xFF`、flags `0xEF`）、`entry=0x10_0000`、`SP=0x7fff_0000`；`INTEG-046t` 探针通过。
5. **PTW/超页/普通页/异常**：超页命中、普通页（64 KiB）命中、越界/缺页/`SPF`/`GPF`/HSJU/R/W/X 拒绝各至少一例，进入 `cfx_ptw` 且 cause 正确；A/D 更新与 `clean`/`invalid`/`flush` 回写、TLB 填充/失效、`PTWERR` 各至少一例；`ptw_enable=0` 时 `addr[47:42]==0` ⇒ `CFXMEM`；`INTEG-039t`/`INTEG-040t` 探针通过。
6. **cfx/monitor/权限/DMA/时间/中断**：cfx0/1/2/3/63 寄存器面、cfx4 PTW、cfx17 pmem SRAM+cg15 DMA、cfx15/18 时间/hart 实测可达；cfx5 ⇒ `0x84`；reserved cfxha ⇒ `ILLI`/`CFXMEM`；`trap`/`escape`/`cfx2rd`/`cfx2rc` 与 hypv/supv/user 模式切换、mask/deleg/cg7 按 spec；smon cfx2/SRAM 保留；异步仲裁按 `INTEG-051t`；`INTEG-042t`/`INTEG-044t`/`INTEG-045t`/`INTEG-047t`/`INTEG-048t`/`INTEG-049t`/`INTEG-050t`/`INTEG-051t` 探针通过。
7. **`arch` 同模式一致**：`DADAO_TEST_PROFILE=node` + `run_m5_e2e.py --qemu <gem5-shim> --bootrom <step5> --vectors-dir tests/arch/umon --expected …` **10/10**；`check-arch` 的 13 个 `ARCH_CFX_PROBES` 逐个 rc=0（或逐 check 与 QEMU 基线一致）；QEMU Node 的通过集合（逐 case/check，现场 `--list` 派生）⊆ gem5 通过集合；差异逐条归因「测试资产 / spec 不清（用户裁定）/ gem5 缺陷（本任务修）/ QEMU 缺陷（另立任务）」。
8. **`inst` 同模式一致**：`DADAO_TEST_PROFILE=node` + `tools/qemu/semantics_gate.py --vectors tests/inst --qemu <gem5-shim> --trampoline <bootrom_step5_inst.bin> --jobs 8` 产出与 QEMU Node 基线相同的口径（基线现场统计：**968 = 963 passed / 5 deferred / skipped_profile=44**；以开工实测为准，不写死）；**QEMU 通过集合 ⊆ gem5**、无 gem5-only 失败；差异逐条归因。
9. **Embench（system E2E）**：`run_embench_e2e.py --profile node --opt O0,O2 --qemu <gem5-shim>`（与 QEMU Node wrapper 同命令）全部 benchmark 的 guest 退出码 0（22 × 2 档，现场统计）；`--inject` 自检返回 **1**（证明判据可失败）；不得用 `check-tset-embench-smoke` 的 qemu-user 结果代替 Node system E2E。
10. **SE 与 B0–B7 零退化**：`configs/dadao/se.py` 的 `hello`/`fail` fixture rc/stdout 与 `GEM5-014t` 基线一致；SE 源文件 diff 为空/语义不变；`make check-gem5-decode` rc=0（264/264、388/388、28/28、2/2、failures 0）；`python3 tools/gem5/check_converge.py` rc=0 且 B1–B7 计数不变（`[FAIL] 0`）；`GEM5-015t` Tiny 基线不退化。
11. **L1/L2/隔离/台账**：`make check`（L1）rc=0 或「本任务红 = 0」且逐条基线复现；L2（`make check-modules`）rc=0，若被共享 `install-host`/gate.lock 阻塞则记 BLOCKED + 现场（不得伪装 PASS）；`git diff --name-only <base>` 只命中 `components/gem5/**` + 本任务书 + `milestones.md`；`check-component-changelog`/`check-milestones-fresh`/`check-tasks`/`check-no-residue` rc=0；无 `m5out/`、无 `*_tmp*`/`*.orig`/`*.rej`。
12. **证据/注入/完成区**：`.work/evidence/GEM5-016t/**` 一键脚本（`run.sh`、`run.EXIT`、`REPORT.md`、日志）+ `run.sh --inject` 覆盖「必测反例」每类「注入 → FAIL（rc≠0/错误行）→ `cp` 备份 + md5 对账还原 → 回绿」；完成区 ≤30 行；状态 `待验收`。
13. **BLOCKED 纪律**：任何无法在 gem5 Node 上成立的用例/能力，必须给出「spec 引用 + 根因 + 现场日志 + 为什么不是实现缺陷」，登记 BLOCKED 并经用户明确裁定；不得自行跳过、改期望、改测试资产或把 QEMU 红算作 gem5 绿。

## 必测反例（每类必须有可达 FAIL，不是上限）

1. **BootROM 大小/复位偏移**：临时把 4 MiB 改成 64 KiB（或复位偏移 `0x3f_0000` 改错）⇒ 启动/几何/`INTEG-046t` FAIL；还原回绿。
2. **PA RAM 大小**：临时把 2 GiB 改成 1 GiB ⇒ 高端 PTW/ELF 或 `INTEG-039t` FAIL；还原回绿。
3. **identity 超页 SPF**：临时把 hmon 的 `SPF=0xFF` 改成 `0x1F`（或 PPN 错位）⇒ body 取指/PTW FAIL；还原回绿。
4. **PTW 开关/路由**：让 `ptw_enable=0` 时 `addr[47:42]==0` 直通 PA（或 `ptw_enable=1` 仍走段检查）⇒ `INTEG-039t`/`INTEG-040t`/inst fault 类 FAIL；还原回绿。
5. **TLB A/D/失效**：不更新 A/D 或让 `invalid` 不删条目 ⇒ `INTEG-040t` FAIL；还原回绿。
6. **cfx_pmem DMA**：把 DIR 反向/不置 DONE/不写 PA 0 ⇒ hmon 启动挂死或 `INTEG-042t` FAIL；还原回绿。
7. **monitor 进入/escape**：把 `trap cfx_hmon` 目标/模式/向量写错（或 `escape` 返回地址错）⇒ power→hmon→body 断链 / arch FAIL；还原回绿。
8. **cfx2rd/保留 cfx**：让 reserved cfxha 的 `cfx2rd` 返回 0 而非 `ILLI` ⇒ `INTEG-044t`/`INTEG-045t` FAIL；还原回绿。
9. **semihosting 返回寄存器**：返回写 `rd16` 而非 `rd8`（或退出码不取低 8 位）⇒ 控制台/退出码用例 FAIL；还原回绿。
10. **Node raw 入口**：把 raw `-kernel` 装到 `e_entry`/错误基址 ⇒ `check-inst` Node 段大面积 FAIL；还原回绿。
11. **SE 隔离**：让 Node 的 fault/cfx 路径在 SE 生效（或 `inUserMode()` 恒 false）⇒ SE `hello`/`fail` 或 decoder 断言 FAIL；还原回绿。
12. **cfx5/未实现 cfx**：把 cfx5 误注册为可用（或 `CFXREG` 返回 0）⇒ `INTEG-044t`/`INTEG-049t` FAIL；还原回绿。

## 证据

- `.work/evidence/GEM5-016t/**`：`run.sh`（构建 → 几何/寄存器静态比对 → BootROM/raw/ELF fixtures → `INTEG-046t` boot chain → PTW/TLB/DMA/cfx/arch smoke + 13 probes → `inst` Node 全量 + QEMU 基线逐 case 对照 → embench O0/O2 + `--inject` → SE/B0–B7 → L1/L2 → 隔离），逐项落 `*_EXIT=<rc>`；日志 `.work/log/gem5/**` 与 `/tmp/opencode/GEM5-016t/**`（gem5 `--outdir` 只落此处）。
- `REPORT.md`：**数字全部脚本现场生成**（补丁数、sim-object 列表、几何 dump、bootrom 大小边界、PTW/PTE/SPF 观测、arch 逐 check、inst 968 口径、embench 分类、B0–B7 计数、注入表「注入前 md5 / 注入 rc / 还原后 md5 / 回绿 rc」）。
- **QEMU 基线**：开工时 `master` 的 `qemu-system-dadao` md5 + `check-inst`/`check-arch-smoke`/13 探针/`run_m5_e2e`/embench 的真实 rc 与逐 case 结果；不得用旧二进制/旧日志冒充。
- **工具链/依赖缺失**（`.dadao/cross-toolchain/bin/{clang,ld.lld,llvm-mc,llvm-objcopy,qemu-system-dadao}`、`.work/source/{gem5,embench-iot}`、`scons`）⇒ **rc=2 BLOCKED**，不得伪造 PASS。

## 说明（冲突登记 / 风险 / 非目标 / 溯源）

### 1. Node identity 与 `spec/Machine-v5 §6` 的冲突（已登记，不在本任务改 spec）

- `spec/Machine-v5 §6` 写 L1 index `0x1000`–`0x1003`、VA `0x0200_0000_0000`–`0x0200_7fff_ffff`；测试资产 `tests/shared/bootrom/step5/hmon.S` 与 `QEMU-080t` 按用户口径落地 **identity**（L1 0–3、VA=PA `[0,2 GiB)`、`entry=0x10_0000`、`SP=0x7fff_0000`、`SPF=0xFF`）。`ISS-340` 已登记该冲突（open）。
- 本任务按 **identity** 实现，**不修改 `spec/`、`tests/`、`contracts/`**；若用户要求改以 `spec §6` 为准，则 Node 测试资产/入口/SP/hmon PTE 必须同步改，超出本任务范围 ⇒ 停下请示，不擅自两边都「通过」。

### 2. 风险

- **R1 高位地址/2 GiB 内存**：BootROM 末地址 `0x1_0000_0000_0000` 与 `AddrRange`/`SimpleMemory` 边界；2 GiB `SimpleMemory` 的宿主内存占用需在证据中申报，必要时用 `--max-ticks`/超时保护。
- **R2 启动链时序**：`system->physProxy` 依赖 `system_port` 连接；hmon 的 DMA/TLB/PTW 顺序必须与 `hmon.S` 逐指令一致，不能由宿主代劳。
- **R3 AtomicSimpleCPU 下的异步中断**：无时序，`cfx15/18` 计数器与 `INTEG-050t`/`INTEG-051t` 的交付粒度需实测；若 gem5 无法在 atomic 下满足 spec，先保留现场、登记并提交用户裁定（不得伪绿）。
- **R4 TLB/A-D/PTW 与 atomic 访存**：`translateTiming`/`translateAtomic`/`translateFunctional` 三条路径都要走 Node 翻译；fault 传播与 A/D 回写需实测。
- **R5 cfx 寄存器面大**：arch 13 探针覆盖广，按 spec 表逐项实现；无法确定归属的寄存器/非法组合必须查 spec，不按 QEMU 实测反推。
- **R6 构建/组件串行**：gem5 组件同一时刻只一个写者；新增 SimObject 触发 params 重生成，构建 15–40 分钟，用 background + 日志 + `*_EXIT`，禁 `setsid nohup` 后失联。
- **R7 QEMU 基线可能含历史 BLOCKED**（如 `space_power`）：以开工实测为准；若仍 BLOCKED，登记并另立 QEMU 任务，不阻断 gem5 自身 spec 派生断言。

### 3. 非目标

- smon 启动/验收（保留 SRAM/cfx2 能力，不跑路径）；picolibc；多核/NUMA；cache/时序；UART/RTC/CLINT/PCI 等平台设备；GDB/checkpoint/KVM；动态链接/TLS/线程；Linux 内核启动；`spec §6` 的 `0x0200...` 窗口（除非用户另行裁定）。

### 4. 参考对照（内容溯源，非执行必需）

- gem5 上游 `src/arch/riscv/bare_metal/fs_workload.*`（Workload/physProxy/resetThread/activate 形态）与 `src/arch/riscv/semihosting.*`（BaseSemihosting 适配）；**不复制代码**。
- `DADAO-0628` 的 QEMU/gem5 是单几何 + 宿主代劳启动，无 Node 4 MiB BootROM/hmon identity-PTW；**仅作内容溯源，非执行依赖**，不复用其常量/代码/测试。
- v5 真源：`spec/Machine-v5 §1/§1.1/§1.2/§2/§3/§4/§5/§6`、`spec/DADAO-12 §2.2/§3/§4.5/§4.9`、`ADR-0004`、`ADR-0020`、`ADR-0043`、`ADR-0045`、`ISS-340`；QEMU-080t 只作同模式行为对照。

### 5. 待确认口径（本册已按推荐值写，用户可否决）

- ① BootROM 写的具体 fault 码/路由：按 spec + QEMU Node 实测对齐，spec 不清则请示。
- ② `cfx15/18` 在 AtomicSimpleCPU 下的计数器粒度与异步交付点：以满足 `INTEG-050t`/`INTEG-051t` 的 spec 语义为准，必要时请示。
- ③ embench 的 QEMU/gem5 wrapper 仅补 `profile=node,bootrom-image`（脚本不暴露 profile），映射逐项入证据。
- ④ 若 `GEM5-015t` 落地时调整了 FS 文件命名/接口，本任务以 015 的实际接口为准，不复制 015 任务书文本。

## 完成区

**测试结果**：`.work/evidence/GEM5-016t/run.sh` 全部 phase 分三批跑（early=meta/geometry/bootrom/reset 16/16、full=ptw/cfx/arch/inst/embench/se_tiny/decode 21/21、l1l2 2/2），每批 `run.EXIT=0`（详见 `REPORT.md` 与 `.work/log/gem5/GEM5-016t-*.log`）：arch smoke **10/10**；13 个 ARCH_CFX_PROBES 全绿（integ039t 37/37、integ040t 34/34、integ042t 25/25、integ046t 16/16、044t/045t/049t/integ044t/048t/049t RESULT PASS、integ047t 6/6、integ050t 16/16、integ051t 14/14）；inst Node **968=963 passed/5 deferred/skipped_profile=44**（与 QEMU 基线同口径，0 failed）；Embench **38/38**（O0/O2，19 bench×2）；Tiny 子集 44/44；SE hello→42 / fail→7；decode 264/264+388/388+28/28+2/2、converge 264/264+1848/1848；几何 17 项与 `machine-profiles.yaml node` 逐项相等；BootROM 4 MiB±1 字节/±1 页、无 bootrom、`--bios` 全 rc≠0 且报实际/期望；复位 10 项实测（rb0=reset_pc、rb1/rd1/ra0=0、rf0=0x7FF8…、mode=3/cfxcode=63/ptbr=0/ptw=0）；未写 RAM 读回 0。注入 12 类（`run.sh --inject`）：10 类首轮通过；`inj_identity_spf`/`inj_reserved_cfx2rd` 的**注入器**修正后重跑通过（`GEM5-016t-inject-rerun.log`）；每类均「注入红 → `cp`+md5 还原 → 回绿」。
**修改文件**：`components/gem5/patches/**`（新增 8 + 修改 10；`series` 97）、`components/gem5/{series,changelog.md,README.md}`、`.tao/tasks/gem5/GEM5-016t-FS-Machine-v5-Node.md`、`.tao/knowledge/milestones.md`；证据/临时物在 `.work/evidence/GEM5-016t/**`、`.work/log/gem5/**`、`/tmp/opencode/GEM5-016t/**`（不入 git）。组件源树 `.work/source/gem5` 收敛为 base+1（`f86efab`），clean。
**验收结果**：`check-patch-tree` rc=0（302 patches 全组件）、`check-source-state` gem5 `count=1 clean=True`、`make build-gem5` rc=0、`gem5.opt --help` rc=0、`--list-sim-objects`（200 列 pty）含 `DadaoNodeTlb`/`DadaoNodeMMU`（Python 别名由 live config 导入 + Node 实跑为等价证据）；`--dump-geometry` 17 项。L1 `make -k check` rc=2，唯一红 = `check-knowledge-refs`（157 条其它任务 `.work/**` 悬空；隔离 worktree 无其产物；**本任务悬空 0**）；L2 `check-modules` **BLOCKED**（隔离 worktree 无 `.work/build/llvm`/install-host，会触发 LLVM 全量重建；已在证据中登记，不伪 PASS；等价功能门控 inst/arch/探针已用 shim 直接跑）。`git diff --name-only master` 只命中 `components/gem5/**` + 本册 + `milestones.md`；无 `m5out/`、无 `*_tmp*`/`*.orig`/`*.rej`、无 `.inject-backup` 残留。
**新发现/坑**：① gem5 全局 tick = 1 ps：cfx_time/DMA/timer 的 ns 必须 `(curTick-base)/1000`，事件 deadline 要 ×1000（首轮 DMA 用了 1000 tick=1 ns 导致 BUSY 不可观测）；② `-d cpu` 兼容 trace 必须按 QEMU TB 边界发（首条/控制转移后/PC 非顺序/异常强制），逐指令发会让探针的「最后一个 block」看到 exit_seq 覆盖后的 rd8；③ gem5 `--list-sim-objects` 在非 tty 下崩（ioctl），需 `script`+`stty cols`；④ 隔离 worktree 的 `.work/source` 是 symlink，`build_gem5.py` 末尾建 `.work/build/gem5` 的相对 symlink 会 ValueError ⇒ 预建目录规避（env 修正，不改仓）；⑤ PTW 的 PTE 可驻 BootROM（只读）：读要允许、A/D 回写失败 ⇒ PTWERR（否则 fatal）；⑥ `trap`/`escape`/`cfx2rd`/`cfx2rc` 的 B6 静态检查（保留 cfxha ⇒ Illegal）与 QEMU 的「进当前 monitor」不同，Node 必须在 `inst.cc` 先拦截这 4 个 id；⑦ cg7/`GVER`/`GCM` 探针字段 QEMU 也不产出（探针未用，无需伪造）；⑧ 组件源树 `.work/source/gem5` 是**跨 worktree 共享**的：本任务 amend 后 HEAD=`f86efab`，主工作树的旧补丁集在合并前与之不匹配（`check-patch-tree` 在别处会红）⇒ 合并前勿在其它 worktree 跑 gem5 门控。
**遗留问题**：① L1 `check-knowledge-refs` 157 条其它任务 `.work/**` 悬空 = 隔离 worktree 基线（GEM5-015t 同类 150 条），本任务 0 条；② L2 `check-modules` BLOCKED = 隔离 worktree 无 `.work/build/llvm`/install-host（env），未执行全量 LLVM 重建；③ `spec/Machine-v5 §6` 的 `0x0200...` 与 identity 口径冲突仍按 `ISS-340` 登记、本任务不改 spec；④ `fp` 数值类既有 B7 差异（GEM5-015t picolibc math_test）与本任务无关，Node 不跑 picolibc。
**收口结论**：reviewer 第 1 轮 **Accepted**（本人重跑三批 `run.EXIT=0` + `--phase bootchain` 16/16 + QEMU 五元组/13 探针/arch 逐个同数 + 12 类注入与独立几何注入均「注入红 → `cp`+md5 还原 → 回绿」），`**状态**` 置 `已验证`，`milestones.md` 同步。F1–F6 全为文档/证据级、不返工（逐条见审阅记录「收口」）。**未伪称全绿**：L2 `check-modules` 仍 **BLOCKED**（隔离 worktree 无 `.work/build/llvm`/install-host），L1 唯一红 `check-knowledge-refs`（157/153 条均属其它任务、本任务 0）。

## 审阅记录

#### 第 1 轮 engineer 自审
- 范围审查：改动只涉及 `components/gem5/**` 与本任务书/`milestones.md`；未改 `spec/`、`tests/`、`contracts/`、`tools/`、`Makefile`、`manifests/`、`components/{qemu,llvm-project,...}`。SE/Tiny 分支逐字保留（`fs_tlb.*`/`se_*` 未改；`fs_workload` 的 tiny 行为由 profile 判据保持，`fs.py` tiny 的 `--dump-geometry` 键/序不变）。
- 逻辑审查：PTW 优先级（P→SPF→HSJU→R/W/X）逐条对照 `spec/DADAO-12 §2.2.6`；A/D 只在成功访问/填充时置位、clean/flush/替换回写、invalid 不写回；PTWERR 保留条目（探针 `ptwerr_clean_keeps_entry` 实测二次 clean 仍错）；DMA ERR_CODE 一组一热、BUSY 期间写忽略；async 只投递一个源并按 cfxha 升序；monitor 进入的 mask 重定向一次（与 QEMU 同）。
- 反造假：全部结论取自 `run.sh` 实跑输出/退出码；未用 `git checkout` 还原注入（`cp`+md5）；覆盖计数现场统计（968/963/5/44、38、37、34、25、16、14 均来自日志）。
- 自审发现（均由实测暴露并已修，非未修 finding）：

  | finding | 处置 | 改了什么 | 复验证据 |
  | --- | --- | --- | --- |
  | gem5 全局 tick 是 1 ps，DMA/timer 用 tick 当 ns | ✅已修 | `node_cfx.cc`：`nodeTimeValue=(curTick-base)/1000`、事件 deadline ×1000、DMA 延迟 1 µs | integ042t `dma_busy_start_ignored` 25/25 |
  | 逐指令 trace 让探针的「最后 block」看到 exit_seq 覆盖后的寄存器 | ✅已修 | `isa.cc`/`inst.cc`：按 QEMU TB 边界（首条/控制转移后/PC 非顺序/异常强制）发 dump | integ040t 34/34、integ042t 25/25 |
  | 页表可驻 BootROM（只读）：读允许、A/D 回写失败 ⇒ PTWERR | ✅已修 | `node_tlb.cc` PTE 读放宽到 RAM∪ROM、回写限 RAM 失败即 PTWERR；`node_cfx.cc` clean/flush 同 | integ040t `ptwerr_*` 34/34 |
  | B6 静态检查（保留 cfxha ⇒ Illegal）与 QEMU 的 monitor 路由不同 | ✅已修 | `inst.cc` Node 先拦截 `trap/escape/cfx2rd/cfx2rc` | run_m5_e2e 10/10（`m5_perm_reserved_illi`） |

- 判决：上述均已复验；未发现未修 finding；已标 `待验收`。

#### 第 1 轮 reviewer 验收（2026-11-04；判决全部基于本人命令输出，日志留 `.work/log/gem5/GEM5-016t-reviewer-*`）

**重跑记录（rc = 真实退出码）**
1. `./.work/evidence/GEM5-016t/run.sh --phase meta --phase geometry --phase bootrom --phase reset` → `run.EXIT=0`，SUMMARY **16/16**（patch_tree / source_state / build_gem5 / gem5_help / sim_objects_node=DadaoNodeTlb,DadaoNodeMMU / python_aliases / 几何 17 项 / 4 MiB ±1 字节 ±1 页 / `--bios` / 无 bootrom / reset 10 项 / RAM 零初值 全 rc=0）。
2. `run.sh --phase ptw --phase cfx --phase arch --phase inst --phase embench --phase se_tiny --phase decode` → `run.EXIT=0`，**21/21**：integ039t 37/37、integ040t 34/34、integ042t 25/25、044t/045t/049t/integ044t/integ048t/integ049t `RESULT: PASS`、integ047t 6/6、integ050t 16/16、integ051t 14/14；arch `Results: 10/10 passed`；inst `968 total, 963 passed, 0 failed, 5 deferred, skipped_profile=44`；embench `38/38`（源树现场 19 benchmark×2）+ `--inject` `INJECT: PASS`；SE rc=42/7 + hello；tiny `44 total, 44 passed, 0 failed`；decode/converge rc=0。
3. `run.sh --phase l1 --phase l2` → `run.EXIT=0`，**2/2**：`make -k check` **rc=2**、唯一红 `check-knowledge-refs`；L2 `clang_present=False` → BLOCKED。
4. `run.sh --phase bootchain` → `run.EXIT=0`，integ046t **16/16**（三批未含此项，本人补跑）。
5. `make check-inst`（真 QEMU，本人跑）rc=0：node `968/963/0/5/skipped=44`、tiny `44/44`；13 探针 × 真 QEMU 逐个同数；arch 10 向量 × 真 QEMU `Results: 10/10 passed, 0 failed` ⇒ **QEMU 五元组与通过集合 ⊆ gem5**。
6. 本人另跑 `make -k check` rc=2：唯一红 `check-knowledge-refs`，悬空 **153**（本人先跑 `make check-inst` 落了 4 个 `.work/log/qemu/check-inst*.log`，故少于开工时点的 157；逐条列出**全部属其它任务、`GEM5-016t` 悬空 0**）。
7. `run.sh --inject`（12 类，本人重跑）→ `run.EXIT=0`：每类 `:injected` 目标检查 FAIL（rc=1 / `0/1 passed` / rc=135 / rc=137 / rc=-6），`:restored` `md5_same=True` 且回绿；跑前跑后 82 个源文件 md5 全同、无 `.inject-backup`。
8. **独立注入（不在 engineer 12 类内）**：几何常量漂移（node `sp` 0x7fff0000→0x7ffe0000，临时树副本 + `GEM5_CONFIG`）：注入 → `run.sh --phase geometry --phase bootrom --phase reset` **rc=1**（`CHECK geometry_matches_profile: … actual=mismatch=sp rc=1`，9/10）；还原 → **rc=0 10/10**；原 `fs.py` md5 前后 `952b78c49550f8940833f1f32243c2c0` 未变。
9. 证据脚本未覆盖项由本人补验：ELF 正例 rc=0；ET_DYN / 非大端 / PT_INTERP / ROM 段 / 越界段 / `e_flags&0xff≠1` 均 **rc=1** 且打印具体项（`e_entry=复位 PC` 被前序 `outside PA RAM` 拦下，仍 rc=1 + 具体值）；复位首块 **256 个 RD/RB/RF/RA** 全符（rb0=`0xffff_ffff_0000`、rf0=`0x7FF8_0000_7FC0_0000`、其余 0）、mode=3/cfxcode=63/ptbr=0/ptw=0；启动链 power(`0xffff_ffff_0000`)→hmon SRAM(`0x0fff_0000_0000`, 251 块)→body `0x10_0000`，body 块 rb1=`0x7fff0000`；`make check-gem5-decode` rc=0 `264/264+388/388+28/28+2/2, failures 0`、`check_converge.py` rc=0 `ids 264/264, boundary 1848/1848`。
10. fault 路径对照：`ptw_off_still_cfxmem` 在 QEMU/gem5 均 PASS、exit `0x81`，两边 CPU trace 在 fault 后均未跳 `cfx_hmon` 向量（QEMU 末块 `0x100c`、gem5 末块 `0x1000`）。

**约束核验**：`git diff --name-only master` + untracked 仅 `components/gem5/**`、本任务书、`milestones.md`；`tests/ spec/ contracts/ tools/ Makefile/ manifests/ docs/ components/qemu` 零 diff；分支 0 新 commit（HEAD=master tip）。gem5 **97** 补丁 = series 97 行（`LC_ALL=C sort -c` 通过、disk==series），全组件 302、`check-patch-tree` rc=0；源树 `f86efab` = base+1 且 `git status` 空、`check-source-state` rc=0。SE/Tiny 文件（`fs_tlb.*`/`fs_mmu.hh`/`se_*`/`process.*`/`se.py`）不在 diff；`inst.cc`/`fs_workload.cc` 的 Node 分支以 `isNode`/`nodeState().active` 门控，Tiny/SE 分支逐字保留。`ISS-340` 与 `issues.yaml`/`spec/**` 零 diff。无 `m5out/`、`*_tmp*`、`*.orig`、`*.rej`；开工/收尾 `git status -uall` 与 5 个目标文件 md5 逐行一致。完成区 **7 行**（≤30）、状态 `待验收`。L2 BLOCKED 属实：`LLVM_BUILD ?= .work/build/llvm` 本 worktree 无（主 worktree 有），`check-arch-smoke: install-host → build-mc → $(LLVM_CONFIGURE)+ninja -C $(LLVM_BUILD)` 会触发 LLVM 全量重建；证据记 BLOCKED、未伪 PASS。写入本记录后补跑 `make check-tasks check-milestones-fresh check-component-changelog check-no-residue check-run-artifacts` → rc=0（无 FAIL）。

**findings（均不阻断，交 architect 收口）**：F1 `run.sh` 无 ELF fixtures（任务书「证据」列了 `BootROM/raw/ELF fixtures`，验收项 3 的 ELF 子项缺一键证据；本人已补验行为正确）；F2 `bootrom_vs_bios_rejected` 的 rc=2 来自 argparse 未知参数（`fs.py` 无 `--bios`），非「同给冲突」规则；F3 `arch_smoke`/`embench_o0_o2`/`tiny_inst_subset` 只比 `n==m`、不校验绝对计数 10/38/44（本人实测已核）；F4 REPORT §4 自称「13 探针 + 046t」只列 12 行，三批跑未含 `--phase bootchain`；F5 任务书 §1「Node fault 进入 monitor、只有 hmon 的 SYS_EXIT 产生 guest 退出码」与实现及同模式参考 QEMU-080t 不一致（QEMU `dadao_cpu_do_interrupt` 仅 `PTW_FAULT`/`CFXPERM` 走向量，其余直接 `qemu_system_shutdown_request_with_code`；gem5 `MachineFault::invoke`→`exitSimLoopNow`；ADR-0004 D6.1 支持直接映射）⇒ 建议统一任务书措辞，不判实现缺陷；F6 `.work/log/gem5/*` 0 字节残留（具体路径词改用通配，避免删文件后悬空）。

**判决：Accepted** —— 验收命令块在我自己的重跑下全部通过（三批 `run.EXIT=0` + bootchain 16/16、QEMU 五元组与 13 探针/arch 逐个同数、12 类注入与本人独立注入均「注入红 → cp/md5 还原 → 回绿」），硬约束无违反；F1–F6 记 finding 交 architect（按文档级/证据覆盖口径不另开返工轮）。

#### 收口（architect，2026-11-04）
- **判决采纳**：reviewer 第 1 轮 **Accepted**，无未回应 finding；`**状态**` `待验收`→`已验证`，`milestones.md` 同步为 `已验证 | 2026-11-04 05:35`。
- **F1（证据覆盖）**：`run.sh` 无 ELF fixture 一键化 ⇒ 登记为**证据覆盖缺口**，不返工；行为正确性已有 reviewer 手验记录（正例 rc=0、ET_DYN/非大端/PT_INTERP/ROM 段/越界段/`e_flags` 均 rc=1 并打印具体项），后续补 fixture 归证据脚本演进。
- **F2（项名不实）**：`bootrom_vs_bios_rejected` 实际 rc=2 来自 argparse 未知参数（`fs.py` 无 `--bios`）⇒ 结论「同给冲突不可接受」成立口径改为「无 `--bios` ⇒ 参数拒绝」；**文档级**，不返工。
- **F3（断言偏弱）**：`arch_smoke`/`embench_o0_o2`/`tiny_inst_subset` 仅比 `n==m` ⇒ 绝对值 10/38/44 由 reviewer 实测核对，证据脚本断言强度登记为改进项；**不返工**（结论已有独立实测支撑）。
- **F4（报告不全）**：`REPORT.md §4` 缺 `probe_integ046t` 行（三批未含 `--phase bootchain`）⇒ 已按 `GEM5-016t-integ046t.log` 补记 `16/16 passed`，并注明该 phase 为 reviewer 补跑；**证据级**，不返工。
- **F5（任务书措辞）**：§1「fault 进 monitor、仅 hmon `SYS_EXIT` 产退出码」与实现/QEMU-080t 及 `ADR-0004 D6.1` 不符（实为 fault 直接映射退出码，仅 `PTW_FAULT`/`CFXPERM` 走向量）⇒ 判**措辞待统一**，不改实现、不在本册擅改语义；真实行为以本轮证据（`ptw_off_still_cfxmem` 两侧 exit `0x81`）为准，措辞统一归后续文档修订。
- **F6（残留）**：`0` 字节日志文件已删除；`check-knowledge-refs` 对可判定 `.work/**` 路径做存在性检查，故原路径词改用通配（`.work/log/gem5/*`），仅改 token、不改 finding/判决。
- **不越界声明**：本收口只改本任务书 + `milestones.md`；`spec/`（含 `ISS-340` 既有登记）、`tests/`、`contracts/`、`tools/`、`Makefile`、`manifests/` 零改动。

#### 提交与同步（architect，2026-11-04）
- **档位**：reviewer 最新判决 **Accepted** ⇒ **正常提交**（非 `WIP:`）。
- **文件集对账**（显式 staging 23 项，无 `git add -A`）：新增补丁 **8**（`DadaoNodeCPU/MMU/Tlb.py`、`node_cfx.{cc,hh}`、`node_mmu.hh`、`node_tlb.{cc,hh}`）+ 修改补丁 **10**（`fs.py`/`DadaoFsWorkload.py`/`SConscript`/`fs_machine.{cc,hh}`/`fs_workload.{cc,hh}`/`inst.cc`/`isa.{cc,hh}`）+ `series`/`README.md`/`changelog.md` + 本册 + `milestones.md` = 完成区「修改文件」逐项一致；**漏提 0 / 多提 0 / 越界 0**（`grep -vE '^(components/gem5/|.tao/tasks/gem5/GEM5-016t-|.tao/knowledge/milestones.md)'` 无命中）。`git diff --cached --shortstat` = 23 files, +2642/−152；`series` 97 行 = 补丁 97 个。
- **提交**：`GEM5-016t: FS Machine-v5-Node`，落本任务分支 `GEM5-016t`（提交号见 `git log --oneline -1 GEM5-016t`；本记录随该提交入库，收口时 amend 过一次仅为写入本段）。
- **同步**：`git merge master`（`master` = `133a90b5`）→ `Already up to date.`（master 为本分支祖先），**无冲突**，HEAD 未产生 merge 提交。
- **门控（同步后在最终树重跑）**：L1 `make -k check` **rc=2**，唯一红 `check-knowledge-refs`（**153** 悬空，逐条属其它任务；**本任务 0**——首次复跑 154 含本册 1 条，因删 0 字节文件使原路径词悬空，已改通配并复跑至 0）。关键门控：`check-patch-tree` rc=0（302 patches）/ `--source-state` rc=0（gem5 `f86efab` count=1 clean）/ `check-milestones-fresh` rc=0（37 行）/ `check-tasks` rc=0（①漏收尾 1 = `TESTCASES-090t`，非本任务）/ `check-component-changelog` rc=0 / `check-no-residue` rc=0 / `check-run-artifacts` rc=0 / `check-dirs` rc=0。
- **BLOCKED 如实**：L2 `check-modules` 仍 **BLOCKED**（隔离 worktree 无 `.work/build/llvm`/install-host，会触发 LLVM 全量重建），**未伪称 L2/arch 全绿**；等价功能证据为 L3 账本 inst/arch/探针（QEMU/gem5 同数）。**未 push、未 merge 到 master**（本地合并由主会话执行）。
