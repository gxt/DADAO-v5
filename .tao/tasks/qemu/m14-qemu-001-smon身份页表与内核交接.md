# m14-qemu-001: Vast 最小 smon —— 身份映射页表与内核交接

**模块**：qemu
**项目里程碑**：M14
**依赖**：`m14-spec-001`（已合入：`spec/Machine-v5 §6.3`、`.tao/contracts/contract-linux-boot.md`、`contracts/linux-boot.yaml`、ADR-0051 Accepted）；`m14-linux-002`（提供 vmlinux 作**可选**集成输入，未合入前该项登记 BLOCKED，本任务以最小 raw 探针镜像承担主验收）；与其它 **qemu 组件任务串行**（组件单写者，同改 `hw/dadao/dadao-machine.c` 补丁）
**可并行分片**：否（组件单写者；同一条 BootROM/探针链与同一 machine 装载路径）
**预估**：4–6 h（不含节点 QEMU 重建等待）
**状态**：已验证

## 执行环境
**执行环境**：主控机（仓库改动、补丁导出、本机构建/探针）+ 远端 `server207`（评测节点：`apply-series` 重建 QEMU 并复跑同一探针；`server208` 可替代，二者不并用）

## 背景

M14 K0 已冻结启动 ABI（`m14-spec-001`，`spec/Machine-v5 §6.3`；ADR-0051 Accepted）：ABI 地址一律 **VA**；启动模型 **M1** = 进入内核前身份映射页表**已预建**、`PTBR = 0`、`ptw_enable = 1`；**页表只由 `smon` 固件建立**，宿主 loader 只装镜像、不写页表页；进入内核时 `rb16` = 入口 VA、`rb17` = boot info VA、`rb3 = 0`、`supv`、异步全屏蔽。

QEMU 侧现状（K1 缺口）：

- `dadao-vast` 已有 `power → hmon → 测试本体（hypv）` 的 step5 链：**hmon 自己建首张页表**并 `trap cfx_umon` 进测试本体；BootROM 里虽有 smon ELF 条目（type 2），但 smon 从未被装载/进入。
- `bootrom-image + -kernel` 路径只做通用「段落在 RAM 内」检查：不校验 §6.3 的内核镜像区/入口/对齐/保留区，**不写 boot info**，也不要求 `e_entry = 0x0000_0200_0010_0000`。
- 因此「内核以 `supv`、PTW 已开、VA 入口、boot info 就位」这一 K1 最小闭环在 QEMU 上尚不存在。

本任务只做**「smon 交接 + 最小可进入内核」**：smon 建表开 PTW、把 boot info 交给内核、以 VA 入口进 `supv`；不做控制台/中断/定时器（归后续 K1 任务），不装 initramfs（归 `m14-infra-002`）。

> **内核 VA 窗口（用户 2026-11-13 修订，覆盖本册此前所有低地址）**：内核空间 = `[2 TiB, 3 TiB)`；四段地址整体 +2 TiB：
> 页表页 `0x0000_0200_0000_0000`、boot info `0x0000_0200_0001_0000`、内核区 `[0x0000_0200_0010_0000, 0x0000_0200_0400_0000)`、initramfs `[0x0000_0200_0400_0000, 0x0000_0200_0600_0000)`；
> 映射 = `VA[0x200_0000_0000, +512MiB) → PA[0, 512MiB)`（偏置 2 TiB），**不再是全域身份映射**；用户空间 = `[0, 2 TiB)`。下文出现的旧低地址一律按此替换。

## 目标

1. **QEMU 装载规则（§6.3.2）**：`dadao-vast` 的 `bootrom-image + -kernel` 路径按 §6.3 校验内核镜像（ELF 7 条 / raw 4 条），任一不符 ⇒ **非零退出并具名报错**（禁降级/截断/改址）。
2. **宿主 loader 写 boot info（§6.3.3）**：装载校验通过后在 **VA `0x0000_0200_0001_0000`**（内核窗口偏置 2 TiB ⇒ 物理地址 = VA − 2 TiB）写入 15 字段、**大端**、`size = 0x60`，页内其余字节保持 0；`kernel_size` 按路径现场计算；K1 无 initramfs（`initramfs_size = 0`）。
3. **最小 smon 固件（cfx2 / `supv`）**：从 `trap cfx_smon, 0x30001` 进入；只读校验 boot info；经 `cfx_pmem` DMA 把 **64 KiB 页表**（**1 个 512 MiB 超页 PTE**：`VA[0x200_0000_0000,+512MiB) → PA[0,512MiB)`，其余全 0）写入 **PA 0**；失效 TLB、写 `PTBR = 0`、置 `ptw_enable = 1` 并回读确认。
4. **内核交接**：smon 以 `escape cfx_smon, [excp_cause_ip, 0]` 进入内核 **VA 入口** `0x0000_0200_0010_0000`；进入时 `rb16 = kernel_base`、`rb17 = 0x0000_0200_0001_0000`、`rb3 = 0`、`supv`、异步全屏蔽、`hart 0`。
5. **boot hmon 变体**：只负责「装 smon + 配置 cfx_smon + 委派 `cfx_pmem`/`cfx_ptw` 给 `supv` + `trap cfx_smon`」，**不得**再自建页表、**不得**写 PA 0。
6. **失败语义**：loader 侧任何前置错误 ⇒ 进程非零退出；smon/hmon 侧任何前置错误 ⇒ semihosting `SYS_EXIT` + **固定失败码**，**不进入内核**；全程无静默降级。
7. **可失败验证**：≥3 路 loader 反例 + ≥2 路 smon 反例 + ≥2 路源码注入（`cp`+md5 还原），每路可达 FAIL。
8. **补丁可重建**：主控机改组件源树 → `make_patch.py qemu` 导出补丁 → 节点 `apply-series` 重放并重建 QEMU → 复跑同一探针，结果一致。

> 本任务**返回一条可执行的最小内核启动链**：「QEMU 装镜像 + 写 boot info + smon 建表开 PTW + 以 VA 入口进 `supv`」，并把它做成可失败、可复现的门控级证据。

## 接口规范

### 1 地址与内存分区（本任务冻结值，来源 `spec/Machine-v5 §6.3.1`）

ABI 地址一律 **VA**：`addr[47:42] = 0` 的内存窗口，`VA = addr[41:0]`；PA 只出现在**页表项**、**`PTBR`**、**loader 写内存的那一刻**。K0 的内核窗口带 **2 TiB 偏置**（`VA = PA + 2 TiB`），VA 与 PA 数值**不相等**，术语与数值都不得混用。

| 区间（VA） | 大小 | 用途 |
|------|------|------|
| `[0x0000_0200_0000_0000, 0x0000_0200_0001_0000)` | 64 KiB | 首张页表页（`PTBR = 0`；**只由 smon 写**） |
| `[0x0000_0200_0001_0000, 0x0000_0200_0002_0000)` | 64 KiB | boot info 页（固定 VA `0x0000_0200_0001_0000`；`0x60` 之后至页末为 0） |
| `[0x0000_0200_0010_0000, 0x0000_0200_0400_0000)` | 63 MiB | 内核镜像区（`kernel_base = 0x0000_0200_0010_0000`） |
| `[0x0000_0200_0400_0000, 0x0000_0200_0600_0000)` | 32 MiB | initramfs 区（K1 不装：`initramfs_size = 0`，`initramfs_base` 仍写 `0x0000_0200_0400_0000`） |

### 2 启动链分工（本任务实现口径）

- **power**（复用 `tests/shared/bootrom/step5/power.S` 与其 `.lds`，**不改**）：校验 BootROM image index table → 把 type 1（hmon ELF）装入 hmon SRAM → 写 `cfx_hmon.hypv_excp_vector`/`switch_run_mode = hypv` → `trap cfx_hmon, 0x30001`。
- **boot hmon**（新增 K1 变体）：校验 `CFXTRAP` + magic → 用 ROM 内共享例程查表 type 2 并以 `elf_loader` 把 **smon ELF 装入 smon SRAM**（`0x0bff_0000_0000`）→ 写 `cfx_smon.hypv_excp_vector = smon e_entry`、`cfx_smon.hypv_switch_run_mode = supv` → 把 `cfx_smon` 需要的 `supv` 权限打开（`cfx_pmem` / `cfx_ptw` / `cfx_smon` 的 `supv_cfxreg` 与 `supv_cg_reg_deleg` 位 2 清零，`cfx_pmem.supv_cfxmem` 位 2 清零，供 smon 用 `st`/`cfx2rc`）→ `trap cfx_smon, 0x30001`。**禁止**建页表、**禁止**写 PA `0`、**禁止**改 boot info。
- **smon**（新增最小固件）：校验 trap cause/magic → 只读校验 boot info → 建表写 PA 0 → TLB 失效 → `PTBR = 0`、`ptw_enable = 1` → 回读确认 → 从 boot info 取 `kernel_base` → 置移交寄存器（`rb16 = kernel_base`、`rb17 = 0x0000_0200_0001_0000`、`rb3 = 0`）→ 写本 cfx 异常帧 `excp_prev_run_mode = supv`、`excp_cause_ip = 入口 VA` → `escape cfx_smon, [excp_cause_ip, 0]`（不写 `excp_prev_run_mode` 会按 `trap` 保存的 `hypv` 返回，**必须显式改**）。**禁止**改写 boot info、**禁止**写 `[0x0000_0200_0001_0000, 0x0000_0200_0002_0000)`。
- **内核入口**：见 §5。QEMU **不得**在 bootrom 路径按 `e_entry` 直接设 PC（唯一一次入口跳转由 smon 完成）。

### 3 首张页表期望值（页表页内容逐项核）

`i = 0..3`：`PTE_i = 0xC000_0000_0000_0000 | (i << 29) | 0x0000_0000_0000_FFEF`

- `bits[63:60] = 0xC`（`H=1`、`S=1`、`U=J=0`），`bits[55:16] = i << 13`（超页 PPN = `i × 512 MiB`），`bits[15:8] = 0xFF`（SPF 全片段存在），`bits[7:0] = 0xEF`（`R=W=X=1`、`G=1`、`A=D=1`、`SP=1`、`P=1`）。
- 依据：`spec/Machine-v5 §6`（首张页表位清单 + 4 × 512 MiB 覆盖 `VA [0, 2 GiB)`）、`spec/DADAO-12 §2.2.3`（PTE 位定义）；`G=1` 未被 `§6` 点名，以 ADR-0043 D10 为据（若评审不接受，须同笔改 ADR 与探针，**不得单方改期望值**）。
- 页表页 `L1[4..8191]` 全 0（64 KiB 全零页写 PA 0）；`PTBR = 0`。

### 4 boot info（15 字段，VA `0x0000_0200_0001_0000`，大端，`size = 0x60`）

| 偏移 | 宽度 | 字段 | K1 装载期取值 |
|---|---|---|---|
| `0x00` | 4 | `magic` | `0x4442_494E`（`DBIN`） |
| `0x04` | 2 | `version` | `1` |
| `0x06` | 2 | `size` | `0x0060` |
| `0x08` | 8 | `ram_base` | `0x0000_0200_0000_0000` |
| `0x10` | 8 | `ram_size` | `0x8000_0000`（2 GiB） |
| `0x18` | 8 | `kernel_base` | `0x0000_0200_0010_0000`（= 入口 VA） |
| `0x20` | 8 | `kernel_size` | ELF：`max(p_vaddr + p_memsz) - 0x0000_0200_0010_0000`；raw：镜像文件字节数 |
| `0x28` | 8 | `initramfs_base` | `0x0000_0200_0400_0000` |
| `0x30` | 8 | `initramfs_size` | `0`（K1 不装 initramfs） |
| `0x38` | 8 | `cmdline_base` | `0` |
| `0x40` | 8 | `cmdline_size` | `0` |
| `0x48` | 8 | `ptbr` | `0`（页表根 PA；低 16 位为 0） |
| `0x50` | 4 | `page_size_log2` | `16`（64 KiB 页） |
| `0x54` | 4 | `hart_id` | `0` |
| `0x58` | 8 | `flags` | `0x1`（bit0 = semihosting 控制台可用） |

- **写入方**：**宿主 loader（QEMU machine 模型）** 在移交前写；`power`/`hmon`/`smon` 只读。派单要点中「按 §6.3 写 boot info」按此执行（口径见「待裁定 1」）。
- **smon 只读校验（本任务自决口径，不改契约）**：`magic == 0x4442_494E`；`version == 1`；`size >= 0x60`（`size` 为 16 位 ⇒ 不可能越过 64 KiB 页）；`kernel_base == 0x0000_0200_0010_0000` 且 64 KiB 对齐；`ram_base == 0x0000_0200_0000_0000`（内核窗口起点 VA）且 `ram_size == 0x8000_0000`；`page_size_log2 == 16`；`hart_id == 0`；`initramfs_size == 0`（K1）。任一不符 ⇒ 固定失败码退出，**不进入内核**。

### 5 进入内核时状态（内核第一条指令处）

| 项 | 期望值 |
|---|---|
| `IP` | `0x0000_0200_0010_0000`（VA） |
| 运行模式 | `supv`（`MODE = 2`） |
| 当前 cfx | `smon`（`CFXCODE = 2`） |
| PTW | `ptw_enable = 1`；`PTBR = 0`；64 KiB 页、`VA [0,2 GiB) → PA [0,2 GiB)` 身份映射 |
| `rb16` | `0x0000_0200_0010_0000`（入口 VA；移交后不再有意义） |
| `rb17` | `0x0000_0200_0001_0000`（boot info VA；**不是** DTB） |
| `rb3` | `0` |
| `rb1`（SP）/`rd15`/其它通用寄存器 | 未定义（内核自建 early stack） |
| 异步中断 | 全屏蔽（`cfx_smon.global_cfx_intr_mask` 与 `supv_cfx_intr_mask` 全 1） |
| hart | 仅 `hart_id = 0` 在线 |

### 6 宿主 loader（QEMU）装载规则（仅 `bootrom-image + -kernel` 路径生效）

- **ELF 路径 7 条**（任一不符 ⇒ `error_report` + `exit(1)`，消息点名规则与偏离值）：
  `ELF-FORMAT`（ELF64、大端、`e_machine = 0x0DA0`、`ET_EXEC`、`e_flags` 版本字段 = 1）、`ELF-PT-LOAD`（只装 `PT_LOAD`）、`ELF-VA-TO-PA`（装载地址语义取 `p_vaddr`；K0 内核窗口下 `p_vaddr = p_paddr + 2 TiB`（固定偏置），二者不等即按本条拒绝——上游 `load_elf` 按 `p_paddr` 放置在此前提下数值等价）、`ELF-ALIGN`（`p_vaddr % 0x10000 == 0` 且 `p_align >= 0x10000`）、`ELF-RANGE`（每段 `[p_vaddr, p_vaddr + p_memsz)` ⊆ `[0x0000_0200_0010_0000, 0x0000_0200_0400_0000)`）、`ELF-NO-OVERLAP`（不得与 `[0x0000_0200_0000_0000, 0x0000_0200_0002_0000)`、BootROM、hmon/smon SRAM 重叠）、`ELF-ENTRY`（`e_entry == 0x0000_0200_0010_0000`）。
- **raw 路径 4 条**：`RAW-BASE`（整体装入 `0x0000_0200_0010_0000`）、`RAW-ENTRY`（首字节即入口，不解析 ELF 头）、`RAW-LENGTH`（≤ 63 MiB）、`RAW-BSS`（不含 `.bss`，由内核自清；loader 只校验不解释）。
- **boot info 写入**：在装载校验**通过之后**写 15 字段（表见 §4），16 位/32 位/64 位字段一律大端；`0x60` 之后不写（RAM 复位为 0）。写入失败 ⇒ `exit(1)`。
- **复位行为**：`PC` 保持复位向量（`0xffff_ffff_0000`），**不**按 `e_entry` 改写。
- **范围边界（避免回归）**：上述 §6.3 校验与 boot info 写入放在**新的 K1 装载函数**内、只在 `dadao-vast` 的 `bootrom-image + -kernel` 路径执行；改既有的 `load_elf_kernel` / `load_raw_kernel` 语义（含 Tiny 与 Vast legacy `-bios` path B）不在本任务范围。Vast 无固件的 legacy ELF 直跳路径（`-kernel` ELF 且无 `bootrom-image`/`-bios`）保持既有语义不动（避免 M4–M13 既有测试回归），登记为遗留。

### 7 失败语义与失败码

- **loader（host 层）**：进程 `exit(1)` + 具名消息（规则名 + 实际值）；不装半截镜像、不写 boot info。
- **hmon（guest，semihosting `SYS_EXIT`）**：image index table / ELF 失败码沿用 step5 `0xB1`–`0xB6`；smon ELF 装载失败见 `0xB3`–`0xB5`；magic/cause 不符 `0xB8`（沿用既有口径，不新增冲突码）。
- **smon（guest，semihosting `SYS_EXIT`；码值为本任务自决，须在完成区与源注释、探针脚本三处一致）**：`0xC1` `magic`/`version` 不符；`0xC2` `size < 0x60`；`0xC3` `kernel_base` 未对齐或越界；`0xC4` initramfs 字段越界（K1 `size != 0` 即按越界处理）；`0xC5` 页表 DMA 失败或回读不符；`0xC6` `PTBR`/`ptw_enable` 回读不符；`0xC7` RAM 几何/页大小/hart 不符。
- 任一 guest 侧失败 ⇒ **不得** `escape` 进内核；探针须断言「内核窗口从未出现执行块」。

### 8 观测通道与探针内核寄存器映射

- **QEMU 侧**：`-d cpu -dfilter <power,hmon,smon,kernel 四窗口>`；最后一个 dump 块给出 `MODE` / `CFXCODE` / `PTBR` / `PTW_ENABLE`，并给出 `CFX02` 的 `TRAPN`/`ESCN`（证明 smon 真的被执行过、真的 `escape` 过一次，而不是模型伪造）。
- **探针内核（最小 raw 镜像）**：进入后先保存 `rb16`/`rb17`/`rb3`，再逐项回读并在退出前写入下述寄存器（`rd16` 必须留给 `SYS_EXIT` 参数块，不得占用）：

| 寄存器 | 内容 | 寄存器 | 内容 |
|---|---|---|---|
| `rd5`–`rd15` | boot info 前 11 字段（`magic`…`cmdline_size`，按 §4 顺序） | `rd17`–`rd20` | `ptbr` / `page_size_log2` / `hart_id` / `flags` |
| `rd21`–`rd24` | `PTE0`–`PTE3`（经 VA 0 回读） | `rd25`–`rd27` | `rb16` / `rb17` / `rb3` |
| `rd28` | 页表页非零 8 字节项数（期望 4） | `rd29` | boot info 页 `[0x60, 0x0000_0200_0001_0000)` 非零 8 字节项数（期望 0） |
| `rd30` | 探针自检失败掩码（0 = 全通过） | — | — |

- 探针退出码：0 = 全部自检通过；`0xD0 | n` = 第 n 项自检失败（n 自 1 起，清单写进 `tests/shared/bootrom/k0/README.md`）。
- **期望值来源**：15 字段与取值来自 `contracts/linux-boot.yaml`（现场解析，不抄实现）；`kernel_size` 期望 = 探针镜像现场字节数；PTE 期望按 §3 公式现场生成；`ram_size`/分区边界同 YAML。**禁止**从 QEMU 输出反推期望值。

### 9 构建/运行入口（只写脚本名与 make 目标）

- 主控机：`make build-qemu` → `make install-host`；探针 `python3 tools/qemu/k0_boot_probe.py --qemu <安装根>/qemu-system-dadao`（`<安装根>` 由 `tools/infra/paths.py` 解析）。
- 固件由探针脚本现场构建：`llvm-mc` + `ld.lld` 汇编 `step5/power.S`（原样复用）与新增 `k0/hmon.S`、`k0/smon.S`、`k0/probe_kernel.S`，用既有 `tools/testcases/arch/build_step5_bootrom.py` 打包 4 MiB BootROM（该脚本不改）。
- 节点：`python3 tools/infra/make_patch.py qemu`（导出补丁）→ 任务分支 commit 以 `git bundle` 送节点 → 节点 `make apply-series`（旧 `base+1` 与补丁集不符时先按 `docs/Process-01 §7` 恢复到 manifest base，**禁** `-f` 绕过）→ `make build-qemu` → `make install-host` → 同一探针 → `make sync-node-repo`。

## 范围（改哪些文件）

- `hw/dadao/dadao-machine.c`（组件源树）→ 导出 `components/qemu/patches/hw/dadao/dadao-machine.c.patch`：Vast bootrom 路径的 §6.3 装载校验 + boot info 写入 + `kernel_size` 计算 + 保留区/入口/对齐拒绝。
- `components/qemu/changelog.md`（M14 一条）。
- `tests/shared/bootrom/k0/`（新建）：`hmon.S`、`hmon.lds`、`smon.S`、`smon.lds`、`probe_kernel.S`、`probe_kernel.lds`、`README.md`（分工、失败码、探针寄存器映射、注入开关）。
- `tools/qemu/k0_boot_probe.py`（新建）：构建固件/探针 → 跑 QEMU → 解析 dump → 逐项断言；`--inject`、`--kernel <vmlinux>`（可选）。
- `tests/shared/machine-profiles.yaml`：仅 Vast 段 `smon: reserved` → `smon: true`（K1 起 smon 实际被使用；该字段无消费者，门控只要求键存在）。
- 本任务书。

**不改**：`spec/`、`contracts/`、`.tao/contracts/`、`Makefile`（若确需新 make 目标 ⇒ 登记 BLOCKED 交主会话/`m14-infra-003`）、`tests/shared/bootrom/step5/**`（既有固件与产物，避免 `check-arch` 回归）、QEMU 其它源文件（除非 §6.3 校验必须，须披露）。

## 验收标准

1. **主探针 rc=0**：`python3 tools/qemu/k0_boot_probe.py` rc=0，打印现场断言数（PASS/FAIL 计数**现场统计**、不写死），且逐项含：
   a. guest 退出码 0，`rd30 == 0`；
   b. 最后 dump 块 `MODE=2`、`CFXCODE=2`、`PTBR=0`、`PTW_ENABLE=1`，且 `CFX02` 的 `GIM` 与 `M2 INTRMASK` 均为 `0xffff_ffff_ffff_ffff`（异步全屏蔽）；
   c. `rd5`–`rd15`/`rd17`–`rd20` 与 `contracts/linux-boot.yaml` + 现场 `kernel_size` **逐字段相等**（不等时打印字段名/期望/实际）；
   d. `rd21`–`rd24` 与 §3 公式现场生成的 `PTE0`–`PTE3` 逐字相等；`rd28 == 4`、`rd29 == 0`（页表页其余全零、boot info 页未被覆盖）；
   e. `rd25 == 0x0000_0200_0010_0000`、`rd26 == 0x0000_0200_0001_0000`、`rd27 == 0`；
   f. 执行块窗口顺序 `power → hmon → smon → kernel` 各 ≥1 且不回退；`CFX02` 的 `TRAPN ≥ 1` 且 `ESCN == 1`（smon 真执行、真 `escape` 一次）。
2. **vmlinux 集成**（可选）：`--kernel <m14-linux-002 的 vmlinux>` 时，出现内核窗口执行块且该时刻 `MODE=2`/`PTBR=0`/`PTW_ENABLE=1`；若 `m14-linux-002` 未合入或 vmlinux 尚不能运行 ⇒ 完成区登记 **BLOCKED（原因 + 已有替代证据）**，不计入 PASS 必要条件（派单要点允许「最小 raw 镜像」）。
3. **loader 反例 ≥3 路，均可达 FAIL**（用运行期临时目录构造坏镜像，不改仓库）：① ELF `e_entry = 0x10_0004`；② ELF 段落在 `[0x0000_0200_0001_0000, 0x0000_0200_0002_0000)`（会覆盖 boot info）；③ ELF 段越出 `[0x0000_0200_0010_0000, 0x0000_0200_0400_0000)`（或 raw > 63 MiB）。每条断言 QEMU **rc≠0**、stderr 点名对应规则、无内核窗口执行块。
4. **smon 反例 ≥2 路，均可达 FAIL**（测试专用 hmon 变体 `--defsym` 用 `cfx_pmem` DMA 改写 boot info，仅注入变体，**生产 smon/hmon 源不含该路径**）：① `size = 0x20`；② `kernel_base = 0x10_0001`（未对齐）。断言 guest 退出码 = §7 对应失败码、stderr/dump 无内核执行块。
5. **源码注入 ≥2 路（注入→FAIL→`cp`+md5 还原→重建回绿）**：① `dadao-machine.c` 把 `kernel_base` 字段偏移 `0x18` 改为 `0x20` ⇒ 验收 1c FAIL；② `k0/smon.S` 把 `PTE2` 的 PPN 改错 ⇒ 验收 1d FAIL。两路均贴注入前/后 md5 与重建后的回绿输出；**禁** `git checkout/restore/stash` 还原。
6. **零回归**：`make check-inst`（Vast 计数与基线一致，贴现场数字）、`make check-arch`、`make check-arch-smoke`、`make check-qemu-forms`、`make check-patch-tree`（qemu problem=0）、`make check-source-state`（qemu clean + base+1）、L1/L2（红项逐条归属非本任务）。既有 step5 BootROM 镜像与产物 **md5 不变**。
7. **补丁可重建 + 节点一致**：`python3 tools/infra/make_patch.py qemu` 幂等（`0 written / N unchanged`，N 现场）；节点 `make apply-series` rc=0、`make build-qemu`/`make install-host` rc=0、同一探针 rc=0 且断言数/关键值一致；结束后 `make sync-node-repo` rc=0（或登记 BLOCKED 并给出未执行原因，交主会话续派）。
8. **一键证据脚本**：运行期证据目录下 `run.sh` 一条命令覆盖 1–7；自身含 `--inject` 自检；每条断言有可达 FAIL 路径（禁恒真/双写同值）；基线钉**派单前 commit 常量**（不取 `HEAD`）。
9. 完成区 ≤30 行、审阅记录每轮 ≤40 行；完成区/任务书无运行期路径（源码/构建/安装/临时/家目录）。

## 说明

- **本任务不给内核加能力**：不实现控制台/中断/定时器/SMP/TLB 规范/设备树；内核异常处理行为不在验收范围（K1 后续任务）。
- **boot info 写入方**：按 `spec/Machine-v5 §6.3.3` 与 `contract-linux-boot §4`「宿主 loader 写、`power`/`hmon`/`smon` 只读」执行；派单要点中的措辞差异见「待裁定 1」。
- **smon 的只读校验是附加安全**：契约只要求内核 `head.S` 对 `magic`/`version`/`size` 显式失败（`FAIL-KERNEL`）；本任务让 smon 也校验并在失败时退出（为满足「boot info 越界 ⇒ smon 非零退出」反例），**不替代**内核校验义务。
- **既有 Vast 测试路径**：step5 BootROM + raw 测试本体走同一 `bootrom-image + -kernel` 路径，本任务新增的 boot info 写入会占用 `[0x0000_0200_0001_0000, 0x1_0060)`（既有测试只把它当 scratch RAM，写后即覆盖）；必须由验收 6 证明零回归。若出现不可兼容的既有语义冲突，**登记「待裁定」并保留现场**，不得私自加开关改变既有 argv 语义。
- **页表写者唯一**：QEMU loader 不写页表页；hmon 不建表；只有 smon 写 PA 0。探针用 `rd28`/`rd29` 与 `CFX02` 计数机械核验这一点。
- **权限前提**：hmon 能读 BootROM、能写 smon SRAM，依赖 `spec/DADAO-13 §1` 的默认两轴 mask（默认值 `0x…FFF7` ⇒ 源 cfx=3（hmon）在任意目标 cfx 的位 3 为「允许」）；若实现发现某轴仍需显式清零，按最小开户处理并在完成区留证（不得放宽到 `supv`/`user`）。
- **参考对照（内容溯源，非执行必需）**：参考仓库 `DADAO-0628` 的 `KL-110a`/`KL-112a`（hypv→supv 移交）与 `KL-149a`（linked image + reset handoff）只借「先建表开 PTW、再由移交路径进 S-mode」的阶段划分；其 `cfx_power` 移交、`0x80000000` 链接地址、flat `Image`、ROM trampoline 均**不采用**（本项目用 `trap/escape cfx_smon` + `0x0000_0200_0010_0000` + boot info）。不复制其代码。
- 既有可复用资产（v5 自有，允许复用/改造）：`tests/shared/bootrom/step5/{power.S,hmon.S,smon.S}`（建表/DMA/移交的写法）、`tools/testcases/arch/build_step5_bootrom.py`（image index table 打包）、`tools/testcases/arch/min_rom_probe_integ046t.py`（`-d cpu` 解析与 `-dfilter`）、`tools/testcases/arch/node_probe_prelude.py`（Vast 装载与工具路径）。

## 待裁定

1. ~~**boot info 写入方口径**~~ **已定（主会话，2026-11-13）**：按 `spec/Machine-v5 §6.3.3` 与 `contract-linux-boot §4`——**宿主 loader 写 boot info，`power`/`hmon`/`smon` 只读**；派单要点里「smon 写 boot info」的措辞作废（写错了，以契约/ADR-0051 D3 为准）。
2. **smon 只读校验**（本任务自决）：契约未强制 smon 校验，本任务加只读校验以支撑反例；不改写 boot info、不替代内核 `head.S` 的校验义务。评审若认为越界可要求删段，但不构成契约变更。
3. **PTE `G=1`**（本任务自决）：`spec/Machine-v5 §6` 未点名 `G`；按 ADR-0043 D10 断言 `G=1`。若评审要求只核 §6 清单位，探针退化为掩码比较即可（不需用户裁定）。
4. **节点**：默认 `server207`（`server208` 可替代，不同时占）；若两节点均忙/不可用，验收 7 登记 BLOCKED 并说明，不阻塞其余项。

5. **首张页表的 L1 索引措辞（本任务自决；建议改文档措辞，须用户/主会话裁定）**：`spec/Machine-v5 §6.3`、`.tao/contracts/contract-linux-boot.md §2` 与 `ADR-0051 D6` 均写「smon 在 L1 index `0` 写 1 个 512 MiB 超页 PTE，映射 `VA [0x0200_0000_0000, +512 MiB)`」，但 `spec/DADAO-12 §2.2.1/§2.2.3` 规定 L1 索引 = `VA[41:29]` ⇒ `0x0200_0000_0000 >> 29 = 4096`。按字面写 index 0 会映射 `VA [0, 512 MiB)`（用户空间），内核窗口反而不映射 ⇒ 内核第一条指令即 `CFXMEM`、无法启动。本任务按「映射的 VA 范围」（文义真源）实现：PTE 落在 L1 index `4096`，页内其余 8191 项为 0。
   - 选项 A（推荐）：三处文档的「L1 index `0`」改为「L1 index `VA[41:29]`（= 4096）」，硬件语义不变。
   - 选项 B：保留文档、改硬件索引定义（破坏 42 位 VA 的页表索引，不可取）。
   - 临时处置：按 A 的语义实现并记录于 `tests/shared/bootrom/k0/README.md`；文档属 spec/契约正文，改动须用户裁定，本任务不改。

6. **验收 1d / §3 / §5 的旧口径（与 5 同根因，本任务自决）**：任务书 §3「4 个 PTE（`i=0..3`）覆盖 `VA [0, 2 GiB)`」与 §5「`VA [0, 2 GiB) → PA [0, 2 GiB)` 身份映射」是「内核窗口 +2 TiB 修订」之前的文本。本任务按 `spec/Machine-v5 §6.3.4` 与 `contracts/linux-boot.yaml::startup_model`（`superpage_size` + `prebuilt_page_table`）断言 **1 个 512 MiB 超页**：`rd28 == 1`、`PTE[4096] = 0xC000_0000_0000_FFEF`、`PTE[4097..4099] = 0`。若坚持任务书字面（4 个 PTE、`rd28 == 4`），须同笔改 spec/契约/ADR，且与「内核窗口下内核不可达」冲突。

## 硬约束（子代理必读）

1. 必须在独立 `git worktree` 内作业（分支名 = 任务号）；禁改主工作树；临时文件放运行期临时目录（`/tmp/opencode/<任务ID>/`）。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；断言数/计数/补丁数写现场值。
4. 只动「范围」列出的文件；越界须披露。
5. 失败保留现场并继续推进；只有需要用户语义裁定才写「待裁定」并返回主会话。
6. 组件源树（`hw/dadao/dadao-machine.c`）改动后必须 `python3 tools/infra/make_patch.py qemu` 导出补丁并自证幂等；禁手工 `cp` 伪造补丁。
7. 命令作用域 = workdir（仓库根），用相对路径；换目录用工具 `workdir`。
8. 反例注入一律「注入→FAIL→`cp`+md5 还原→重建回绿」；**禁** `git checkout/restore/stash` 还原。
9. 复杂命令输出留运行期日志目录；QEMU dump 只对指定窗口开 `-dfilter`，禁全量 `-d cpu` 灌满磁盘。
10. 证据脚本基线钉**派单前 commit 常量**，不得取 `HEAD`（WIP 提交会前移 HEAD 使比对恒真）。
11. 组件单写者：本任务独占 QEMU 源树与 BootROM 构建；节点重建后用 `make sync-node-repo` 收口（或登记 BLOCKED）。
12. 不得写入未经主会话转达的用户裁定；自决事项标「自决」并落完成区。

## 完成区

**测试结果**：
- `k0_boot_probe.py` 全量 **101 PASS / 0 FAIL**（现场统计：main 37 + raw 37 + loader 负例 21 + smon 负例 6）；`--only main --inject` 45 PASS（两路源码注入「注入→红→`cp`+md5→回绿」）；`--only vmlinux --kernel <vmlinux>` 4 PASS；一键证据脚本 47 项 CHECK 全 PASS（含脚本自身 `--inject` 自检：改一行期望→红→还原→绿）。
- L2 `make check-modules` rc=0；`make check-inst` **1141 total / 1135 passed / 1 failed（= 既有 `divrem.yaml[23]`）/ 5 deferred / 44 skipped**。
- rc=0 项：`check-arch`、`check-arch-smoke`、`check_qemu_trans`（264/264）、`check-qemu-forms`、`check-component-changelog`、`gen_machine_inc --check`、`make_patch` 幂等（0 written / 66 unchanged）。
- `check_patch_tree` qemu 段 0 问题、`--source-state` qemu OK（HEAD=base+1、clean）；安装根 == 构建树（md5 相同）；step5 固件产物 md5 全不变。

**修改文件**：`components/qemu/patches/hw/dadao/dadao-machine.c.patch`（源树 `hw/dadao/dadao-machine.c`：K1 装载 + boot info）、`components/qemu/changelog.md`（M14 一条）、`tests/shared/machine-profiles.yaml`（Vast `smon: reserved → true`）、`tests/shared/bootrom/k0/{hmon.S,hmon.lds,smon.S,smon.lds,probe_kernel.S,probe_kernel.lds,README.md}`（新）、`tools/qemu/k0_boot_probe.py`（新）、本任务书；与 `git status -uall` 一致（4 改 + 8 新）。

**验收结果**：
- main 现场：guest rc=0、`MODE=2`、`CFXCODE=2`、`PTBR=0`、`PTW_ENABLE=1`、`GIM`/`M2 INTRMASK` 全 `1`、`PTE[4096]=0xC000_0000_0000_FFEF`（`4097..4099`=0）、`rd28=1`、`rd29=0`、`rb16=0x200_0010_0000`/`rb17=0x200_0001_0000`/`rb3=0`、四窗口 `[0,1,2,3]`、`CFX02 TRAPN=1 / ESCN=1`；boot info 15 字段逐字段相等（现场 `kernel_size=0x498`）。
- loader 负例 7 路，各 `rc=1` + 具名 + 无内核执行块：`ELF-ENTRY` / `ELF-NO-OVERLAP` / `ELF-RANGE` / `ELF-ALIGN` / `ELF-VA-TO-PA` / `ELF-FORMAT` / `RAW-LENGTH`。
- smon 负例 3 路：`size=0x20→0xC2`、`kernel_base|1→0xC3`、`hart_id=5→0xC7`（末路兼证注入字节真落盘），均无内核执行块。
- 注入：`machine.c` boot info `kernel_base` 偏移 `0x18→0x20` ⇒ 1c 红；`smon.S` PTE PPN `0→0x2000` ⇒ 1d 红；md5 见审阅记录 F5/F6。
- vmlinux：进入内核窗口时 `MODE=2`/`PTBR=0`/`PTW_ENABLE=1`（vmlinux 不自行退出，按入口 4 字节窗口断言）。

**新发现/坑**：① DMA 的 cfx 地址按 42 位掩码只覆盖 pmem SRAM，hmon/smon SRAM 地址掩码后与 pmem 同窗 ⇒「DMA 到 monitor SRAM」实际写 pmem（本次两处踩到，已写入 `k0/README.md`）；② semihosting 参数块走 QEMU 恒等 debug 翻译（只覆盖 RAM/ROM/monitor SRAM），PTW 开启后传 VA 读不到块，探针须传 PA（观测通道细节，不属启动 ABI）；③ `cp`/`copy2` 还原源码带回旧 mtime ⇒ 增量构建不重编、「回绿」假红，还原后须刷新 mtime；④ `-d cpu` 在 chained TB 上会带上一块 PC（窗口交错），「阶段不回退」改判「首次出现顺序 + 内核进入后无早期阶段 + CFX02 计数」；⑤ LLVM `--defsym` 只收十进制有符号 64 位（`0xC000…FFEF` 须转负数）；⑥ L1 其余红项属并行会话（其它组件 patch tree、musl 工具链戳、两条历史运行期证据路径引用、本任务台账尚未移入「进行中」），逐条已归属非本任务。

**遗留问题**：
- **待裁定 5/6**：spec/契约/ADR 的「L1 index `0`」与 `VA[41:29]` 索引规则冲突；任务书 §3/§5/验收 1d（4 个 PTE、`rd28==4`）是 +2 TiB 修订前口径。实现按 spec（1 个超页、PTE 在 index 4096、`rd28==1`），文档改动须用户裁定。
- **节点重建（验收 7）BLOCKED**：未执行节点 `apply-series` + `build-qemu`/`install-host` + 同探针复跑；补丁已幂等导出、主控机全链绿，交主会话续派。
- vmlinux 能进入内核窗口但不自行退出（控制台/中断归后续 K1 任务）；本任务只断言入口态。
- smon 未打开 `cfx_smon_supv_*_cfx_mask`（SBI 面）；K0 内核不调 SBI，归后续 K1 任务。

## 审阅记录

### 第 1 轮 engineer 自审

自审范围：K1 装载与 boot info（`dadao-machine.c`）、`k0/{hmon,smon,probe_kernel}.S` + `.lds`、`tools/qemu/k0_boot_probe.py`、`k0/README.md`、`machine-profiles.yaml`；逐行复核 + 现场反复复跑。

- **F1（已修）** smon 常量拼装：用 `LD64` 四段 16 位字手拼 `0x0200_0000_0000` 时把 `0x0200` 写成 `0x0002`（少两位），`ram_base` 比对必失。处置：`smon.S` 全部常量改用 `set.rd` 全 64 位立即数。复验：`--only main` 的 `boot info ram_base` 由 FAIL 转 PASS。
- **F2（已修）** boot info 读回通道：把 DMA 目标写成 smon SRAM（`0x0bff…`）——DMA 的 cfx 地址按 42 位掩码只覆盖 pmem SRAM，实际写进 pmem，读 smon SRAM 得 0 ⇒ `0xC1`。处置：暂存/回读一律用 pmem SRAM，并在清页前完成读取与校验。复验：`main` 由 0xC1 转 0x00。
- **F3（已修）** 清页循环 `stm.o {rd8:rd63}` 要求这 56 个寄存器全 0，而此前已用的 `rd9/rd20/rd2` 非零 ⇒ 页表页残留 736 个非零 8 字节字。处置：清页前显式 `set.rd` 清零 rd8–rd63。复验：`page table non-zero words` 由 0x2E0 转 1。
- **F4（已修）** 读回 DMA 把 `PMEM_BASE+0x8000` 当 PA 传给 DIR=1 的 `dma_src` ⇒ DMA ERROR（`0xC5`）。处置：`dma_src` 用 PA `0x8000`（= `PTE_INDEX*8`）。复验：`main` 由 0xC5 转 0x00。
- **F5（已修）** 源码注入 ① 用 `shutil.copy2` 还原会带回原 mtime，增量构建判定「未变化」不重编 ⇒ 「回绿」假红。处置：还原后 `os.utime` 刷新 mtime 再重建。复验：`inject machine-kernel-base-offset: green again` PASS。
- **F6（已修）** 源码注入 ② 不触发固件重建（`rerun()` 复用启动时构建的 BootROM）⇒ 注入不生效、假绿。处置：`rerun()` 每次从源重建固件。复验：`inject smon-pte-ppn: probe FAILs` PASS。
- **F7（已修）** `-d cpu` 的 chained-TB 记录会带上一块 PC（power/hmon 块交错），逐块「不回退」断言不可靠。处置：改成「四窗口各 ≥1 + 首次出现严格递增 + 内核进入后无早期阶段 + CFX02 TRAPN=1/ESCN=1」。复验：`main` 1f 三项 PASS。
- **F8（已修）** smon 反例的注入槽位放在 hmon SRAM（DMA 掩码后落到 pmem 别处）⇒ 注入值实际为 0，`0xC2/0xC3` 属「凑巧正确」。处置：槽位改 pmem SRAM，并新增 `SMON_NEG_CASE=3`（`hart_id = 5`，合法值为 0）——零填充会使 smon 变绿，故该路证明注入字节真的落盘。复验：`smon neg hart_id = 5` 得 `0xC7`。
- **F9（⏸ 待裁定）** 任务书 §3/§5/验收 1d（4 个 PTE、`rd28==4`）与 `spec/Machine-v5 §6.3.4`（1 个 512 MiB 超页）冲突；且文档「L1 index 0」与 `VA[41:29]` 索引规则冲突。处置：按 spec 实现（PTE 在 L1 index 4096、`rd28==1`），登记「待裁定 5/6」交主会话，未单方改 spec/契约。
- **F10（❌ 不修，有据）** 内核探针把 semihosting 参数块的 **PA** 传给 `rb16`：QEMU 的 debug 翻译是恒等映射（`target/dadao/cpu.c::dadao_cpu_translate_for_debug`），传 VA 会让 `SYS_EXIT` 读块失败。属观测通道实现细节、不属启动 ABI，已在 `probe_kernel.S` 头注释与 `k0/README.md` 记录。

判决：F1–F8 已修并有复验；F9 为文档口径冲突（需用户/主会话裁定，实现按 spec）；F10 有据不修。无未修的代码缺陷。

### 第 1 轮 reviewer 验收

**重跑（全部亲跑，rc=取真实退出码）**：
- 探针 `python3 tools/qemu/k0_boot_probe.py` → **rc=0，101 PASS / 0 FAIL**（现场统计 main 37 + raw 37 + loader 21 + smon 6，与完成区逐项吻合）。main 段：guest rc=0、`MODE=2/CFXCODE=2/PTBR=0/PTW_ENABLE=1`、GIM 与 M2 INTRMASK 全 `ff..ff`、boot info 15 字段逐字段与 `contracts/linux-boot.yaml` 相等（`kernel_size=0x498`＝现场 raw 字节数 1176，ELF 口径由脚本强制相等）、`initramfs_size=0`、**`PTE[4096]=0xC000_0000_0000_FFEF`（4097..4099=0）、页表页非零字=1、boot info 页尾非零字=0**、`rb16=0x200_0010_0000/rb17=0x200_0001_0000/rb3=0`、四窗口 `[0,1,2,3]`、`TRAPN=1/ESCN=1`。
- **独立构造 4 条违规镜像**（自写 `review/neg4.py`，不复用探针负例）：`ELF-ENTRY`/`ELF-ALIGN`/`ELF-RANGE`/`RAW-LENGTH` 均 **rc=1 + 诊断点名规则 + 无内核执行块**，`ALL_NAMED_REJECTIONS_OK=True`。
- 门控：`check-inst` **rc=2，红集恰 `divrem.yaml[23]`**（1141/1135/1/5/44）；`check-arch` rc=0（含 smoke 两段 PASS）；`check-modules`(L2) rc=0；`check_qemu_trans` rc=0 **264/264**；`check-qemu-forms` rc=0；`check-component-changelog` rc=0；`make_patch qemu` **0 written / 66 unchanged** rc=0；`check_patch_tree` qemu 段 **0 assertion**（整树 24 问题全属 llvm/gem5/chipyard 在飞）；`--source-state` **qemu: OK**（base+1 clean）；安装根==构建树 `a4ec042d…`；step5 产物重建前后 md5 `3ec4ab3e…/4cb5208d…` 不变（step5 源不在改动集）。
- **证据脚本**：审 `<运行期证据目录>/run.sh`（`BASE_COMMIT=6a531824` 派单常量非 HEAD；每条断言可达 FAIL、无 pipe 吞码、selfinject 自检有效）后重跑 `run.sh --inject` → 46 PASS / **1 FAIL / 1 BLOCKED**。唯一 FAIL = `source state` **整树 rc=1**，根因＝并行会话审查期间改脏 gem5 源树（mtime 04:26/04:29，8 文件 M），**qemu 段仍 OK**；46+source-state 当时绿=47，与完成区「47 项全 PASS」自洽。node replay BLOCKED 已披露（任务书待裁定 4 允许）。
- **独立注入 1 路（自设计，非其 2 路）**：`dadao-machine.c` boot info `page_size_log2` 写值 `DADAO_K0_PAGE_SHIFT` → `- 4`，md5 `7756efb7→ddaa303c` → 重建（build/install rc=0，二进制 `a4ec042d→0083d0db`）→ 探针 **rc=1（22 FAIL；smon 按 §7 以 `0xC7` 拒绝、无内核执行块）** → `cp`+md5 还原（`7756efb7` 相等、源树 clean）→ 重建回绿 **37 PASS/0 FAIL、二进制回 `a4ec042d`**。全程未用 `git checkout/restore/stash`。
- 快照对账：审前后 `git status -uall` 均 0 行；4 个目标文件 md5 与注入前快照 `md5sum -c` 全 OK；`git diff c6c61e7e..HEAD` = 13 项（12 工程师 + 1 台账）与完成区声明一致，无越界。完成区 26 行、第 1 轮自审 18 行；任务书无具体运行期路径。

**索引自洽性（第 4 点）**：`spec/DADAO-12 §2.2.1` 定 L1 index=`VA[41:29]` ⇒ `0x0200_0000_0000>>29=4096`；而 `contract-linux-boot §2`/`Machine-v5 §6.3.4` 声明的映射区间是 `VA[0x0200_0000_0000,+512MiB)`。字面 index 0 映射的是 `VA[0,512MiB)` 用户空间，**与合约自述的映射区间直接矛盾**且内核首条指令即不可达。**实现（index 4096、1 超页、其余 8191 项 0）与合约「映射区间」自洽**；三处文档「L1 index 0」为笔误，已由主会话记 `discussing.md` 待用户裁定，本审查不改 spec/契约。

**判决：Accepted**（主会话可置 `已验证`）。阻断项为零；以下为不阻断 findings：F-a `run.sh` 的 source-state 断言按**整树 rc** 判（标签却写 qemu），共享树下会被他组件打红，建议改同脚本 patch-tree 式的 qemu 段归属；F-b 验收 7 节点重建 BLOCKED 待续派；F-c 待裁定 5/6 文档三处 index 措辞待用户裁定。
