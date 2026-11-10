# Machine-v5：测试机运行环境（v5 自定）

> **状态**：当前（0.4.3-rc，未发布；0.4.0 发布 2026-11-08，0.3.1 生效于 2026-10-16〔用户裁定：正文术语 `PC` → `IP`〕；完整版本记录见文末「附录：版本与变更记录」）
>
> **版本与变更记录细则**：版本号 `x.y.z`——**`x=0` 表示尚未正式发布；正式发布后 `x≥1`**；**大改动 `y+1`、有影响的小改 `z+1`**；当前版本见上行「状态」。
>
> **变更记录见文末「附录：版本与变更记录」**（格式 = 「版本（日期）」小标题 + 列表项；**不用表格、不写「依据」**）。
>
> **定位**：本册是 v5 自定规范，定义 **DADAO-v5 测试机（`dadao-tiny` / `dadao-vast`）运行环境与 semihosting** 的规范正文——面向 QEMU 机器模型、bootrom 固件、harness 与测试向量。上游 `spec/DADAO-*` 与 `spec/SimRISC-*` 仍为**上游基线**；本册不改其架构语义。
>
> **标注约定**：正文中「**测试机约定**」项**无上游 spec 依据**，属 v5 架构自定义；有上游出处的语义给出 `[DADAO-NN §x]`/`[SimRISC-NN §x]` 引用。`cfx0/1/2/3/63` 等实现范围一律为**测试机约定**，不构成对上游 `DADAO-12`/`DADAO-13` 的架构限制。

---

## 1. 内存映射与复位

CPU 地址固定为 48 位；高 6 位 `addr[47:42]` 为分区键：`0` 为内存窗口（受 `ptw_enable` 控制），`1..63` 为 cfx 1–63 的核内地址空间（`cfx0` 没有内部空间）。[DADAO-12 §2.1 核内地址空间][DADAO-12 §2.2 虚实地址转换]

v5 测试机分 **`Machine-v5-Tiny`**（宿主装载的精简 FS 平台）与 **`Machine-v5-Vast`**（完整系统节点；当前单核，可扩展多核/NUMA）两个 **profile**，由机器属性选择。两 profile 的**复位地址相同**，均为 `cfx_power_hypv_excp_vector = 0xffff_ffff_0000`（cfxha 63 / `power`，位于各自 BootROM 的末 64 KiB），该地址可由 CPU 直接取指并执行。[DADAO-12 §2.1 核内地址空间]

- **Tiny**：实现 **`cfx_power`（cfx63，启动移交）** 与 **`cfx3 hmon`（同步异常向量）**；`addr[47:42]` 由两个 cfxha 段构成——`0x3F`（cfxha 63：BootROM/SRAM）与 `0x03`（cfxha 3：hmon SRAM）。不设 PTW/页表、不实现 smon，**不能进入 `user`/`jail`/`supv`**，运行期固定在名义 `hypv`；只承担非 cfx 指令测试、Embench 与 picolibc 测试集。semihosting 的 `trap` 判定只依赖 `immu18`（见 `§5.1`），一般 `trap cfx_hmon` 进入 hmon 向量（见 `§4.4`）。
- **Vast**：内存窗口 `addr[47:42] = 0` 由 PTW 按页表转换到 56 位 PA；核内空间含 hmon/smon/pmem SRAM；启动链 `power → hmon → 测试本体（hypv）`，`power → hmon → smon` 路径保留给内核/smon 测试。

### 1.1 核内地址空间划分（测试机约定）

v5 测试机使用的核内地址空间按 profile 划分如下（均为 48 位核内有效地址；地址区间为**测试机约定**）。

**`Machine-v5-Tiny`**

| 区域 | 起始 | 大小 | cfxha / cfxname | 说明 |
|------|------|------|-----------------|------|
| **BootROM** | `0xffff_ffff_0000` | 64 KiB | 63 / `power` | 唯一非易失启动源；复位向量 = 起始 = `0xffff_ffff_0000`（镜像偏移 0）；内容全部为复位/启动 stub（`power` 移交 `hmon`） |
| **SRAM** | `0xffff_ff00_0000` | 8 MiB | 63 / `power` | 可写主存；应用 `.text/.rodata/.data/.bss` 由宿主 loader 装入，**不塞 BootROM** |
| **hmon SRAM** | `0x0fff_0000_0000` | 64 KiB | 3 / `hmon` | hmon **启动时显式写入** `cfx_hmon_hypv_excp_vector = 0x0fff_0000_0000`（不依赖复位默认值，见 `§4.4`）；内部偏移 `0x3ff_0000_0000`，越界 ⇒ `CFXMEM`；与 BootROM/SRAM 分属不同 cfxha 段，互不重叠 |

- Tiny 实现 `cfx_power`（cfx63）的启动移交与 `cfx3 hmon` 的异常向量/寄存器；`smon`（cfx2）与其它 cfx 不实现。
- BootROM 与 SRAM 之间的 `0xffff_ff80_0000`–`0xffff_fffe_ffff` 不映射；cfxha 63 段内 BootROM/SRAM 之外、cfxha 3 段内 hmon SRAM 之外、以及其它 cfxha 段 ⇒ `CFXMEM`。

**`Machine-v5-Vast`**

| 区域 | 起始 | 大小 | cfxha / cfxname | 说明 |
|------|------|------|-----------------|------|
| **BootROM** | `0xffff_ffc0_0000` | 4 MiB | 63 / `power` | 唯一非易失启动源；复位向量 `0xffff_ffff_0000`（镜像内偏移 `0x3f_0000`，即末 64 KiB 起点） |
| **PA RAM** | `0`（PA 空间） | 2 GiB | —（内存窗口） | 物理存储器 `[0, 2 GiB)`；CPU 只能经 PTW 从 VA 访问（§1.2），不设核内地址别名 |
| **hmon SRAM** | `0x0fff_0000_0000` | 64 KiB | 3 / `hmon` | H-mode 异常向量默认等于起始地址；内部偏移 `0x3ff_0000_0000`，越界 ⇒ `CFXMEM` |
| **smon SRAM** | `0x0bff_0000_0000` | 64 KiB | 2 / `smon` | S-mode 异常向量默认等于起始地址；内部偏移 `0x3ff_0000_0000`，越界 ⇒ `CFXMEM`；M11 保留不使用 |
| **cfx_pmem SRAM** | `0x83ff_0000_0000` | 64 KiB | 32 / `pmem` | cfx_pmem 内部偏移 `0x3ff_0000_0000`；CPU 用 `ld/st` 访问，越界 ⇒ `CFXMEM` |

- **BootROM 尺寸**：上游 `DADAO-12` 只要求 `cfx_power` BootROM **≥64 KiB**，实际大小由本册按 profile 规定（Tiny 64 KiB、Vast 4 MiB）；复位向量两 profile 均为 `0xffff_ffff_0000`（末 64 KiB 起点，镜像内偏移 = 大小 − 64 KiB）。
- **不做双映射**：Tiny 的 SRAM 只在 cfxha 63 段的 `0xffff_ff00_0000`、hmon SRAM 只在 cfxha 3 段的 `0x0fff_0000_0000`；Vast 的 PA RAM 只在 `[0, 2 GiB)` 并仅经页表 VA 映射。两 profile 都不设「同一存储的多地址别名」。
- **`power` 不设 SRAM**：两 profile 的 `power` 分区都不设 SRAM；这是**本机约定**，不构成对上游 `DADAO-12` 的架构限制。
- **legacy `-bios` 复位窗口**：`-bios` 路径仍按 64 KiB 复位窗口（`0xffff_ffff_0000` 起）装载，既有探针/e2e 语义不变；Tiny 的 BootROM 恰为该窗口。

### 1.2 越界访问与越界取指异常（含取指路径）

- **spec 层语义（`CFXMEM`）**：对核内地址空间进行非法访问时触发 `CFXMEM`；其异常原因编号为 `1 << 1`，执行期同步异常按 `DADAO-12 §5.2` 进入当前运行模式 monitor（`CFXTRAP`/`CFXESC` 除外，见 `§7.1`）。[DADAO-12 §2.1 核内地址空间][DADAO-12 §4. 专有寄存器设计规范][DADAO-12 §5.2 异常进入流程]

- **层次与适用**：`CFXMEM` 适用于核内地址空间模型内的非法访问/取指（cfxha 段内的非法子区间、越界访问/取指），按 `§7.1` 的 monitor 段编码归当前 monitor。
- **精确路由（按 profile）**：
  - **Tiny**：无 PTW（`ptw_enable` 恒 0）。`addr[47:42] == 0` 的普通访存/取指 ⇒ `CFXMEM`，**不直通物理存储器**；cfxha 63 段内 BootROM/SRAM 之外、cfxha 3 段内 `hmon SRAM` 之外、以及其它 cfxha 段 ⇒ `CFXMEM`。同步异常进入当前运行模式 monitor——Tiny 唯一 monitor 为 `cfx3 hmon`（运行模式恒 `hypv`），**经 hmon 向量**处理（见 `§4.4`）。
  - **Vast**：`addr[47:42] == 0` 且 `ptw_enable=1`：按单 PTBR 走页表（PTE 格式/页表步进/页权限/TLB 见 `DADAO-12 §2.2.1–§2.2.6`、`§4.5`）；页表步进与 TLB 命中产生的异常先进入当前运行模式 monitor：未映射与 A/D 回写失败 ⇒ `CFXMEM`，权限拒绝 ⇒ `CFXPERM`（见 `DADAO-12 §2.2.6`、`§5.2`）。`ptw_enable=0`（仅复位后 power/hmon 的早期初始化）时仍按上一条报 `CFXMEM`。
  - 保留 cfx（判定见下条）的普通 `ld/st` ⇒ 当前运行模式 monitor 的 `CFXMEM`；`trap`/`escape` 到保留 cfx ⇒ 当前运行模式 monitor 的 `ILLI`。
  - **reserved cfx 集（全册唯一定义）**：以 `DADAO-12 §1` 的 cfxha 编号表为**唯一真源**——**表中 `cfxname = reserved` 的编号即保留 cfx**（含 `per-task` 段中尚未分配的编号）；已分配编号及其 `cfxname` 同样以该表为准。本册**不重复列举编号**，以免与上游漂移。[DADAO-12 §1. 运行模式与核芯功能扩展][DADAO-12 §2.1 核内地址空间]
  - 其余未映射地址（Vast 的 `power` 段 BootROM 之外）⇒ 当前运行模式 monitor 的 `CFXMEM`。
- **取指路径同等对待**：越界**取指**与越界**数据访问**同属非法核内地址访问，**均须报异常**，不得只覆盖数据访问路径；不得静默继续或静默丢弃。
- 两 profile 的几何与上述路由由 `QEMU-079t`（Tiny）/`QEMU-080t`（Vast）落地，并以 `check-interface` 断言固化；旧「唯一 RAM 段 + PA 别名 + 固定容量」口径随本版 profile 划分作废。

---

## 2. 运行模式

DADAO 定义四种运行模式（两位编码）：`user`（`0b00`）、`jail`（`0b01`）、`supv`（`0b10`）、`hypv`（`0b11`）；`user`/`jail` 为普通用户态，`supv`/`hypv` 为特权态。[DADAO-12 §1. 运行模式与核芯功能扩展]

`hypv`（超管模式）的 cg3 寄存器（含 `cfx_⟨cfxname⟩_hypv_cfxtrap` 等四类同步 mask、`cfx_⟨cfxname⟩_hypv_cfx_intr_mask`、`switch_run_mode`、`excp_vector`）定义见 HEE。[DADAO-13 §1. cg3 - hypv mode 寄存器]

`trap`/`escape`/`cfx2rd`/`cfx2rc` 可在**任意运行模式**下执行；是否允许由各核芯功能扩展的 cfx mask 与指令类型 cfx mask 控制。[SimRISC-11]

异常进入后，硬件把运行模式改为 `cfx_⟨cfxname⟩_<mode>_switch_run_mode` 的值（异常进入流程步骤 6）。[DADAO-12 §5. 异常进入与异常退出][DADAO-12 §3. 共有寄存器设计规范]

- **运行模式范围（按 profile）**：`Machine-v5-Tiny` 不提供模式切换路径——复位后即在特权态（名义 `hypv`；复位时 cfxha 63 / `power`，移交后 cfxha 3 / `hmon`）执行，运行模式恒 `hypv`，**不能进入 `user`/`jail`/`supv`**，不实现 smon；`Machine-v5-Vast` 启用 `hypv`、`supv` 与 `user`，`jail` 不启用。
- **`switch_run_mode`（按 profile）**：`Machine-v5-Vast` 取 `cfx_⟨cfxname⟩_<mode>_switch_run_mode` 的值作为异常进入后的运行模式（上段步骤 6）；`Machine-v5-Tiny`（**测试机约定**）该寄存器的**写入被忽略**（寄存器保存值保持 `3`，`hypv`），**读回为寄存器保存值**；异常进入一律强制 `hypv`（`inner_run_mode ← 3`），运行模式不变。[DADAO-12 §5.2 异常进入流程][DADAO-13 §1. cg3 - hypv mode 寄存器]
- **异常承载（按 profile）**：`Machine-v5-Vast` 由 `hmon`（cfx3）承载 hypv 异常、`smon`（cfx2）承载 supv 异常；`Machine-v5-Tiny` 由 `hmon`（cfx3）承载唯一的 hypv 同步异常（无 smon），异常经 hmon 向量处理（见 `§4.4`）。
- **启动链（按 profile）**：`Machine-v5-Tiny` 为 power（hypv/cfx63）→ hmon（hypv/cfx3）→ 测试本体（hypv）：power 在 BootROM 以 `trap cfx_hmon` 按 `DADAO-12 §5.2` 的 `CFXTRAP` 移交 hmon；hmon **显式写入**自身异常向量（`cfx_hmon_hypv_excp_vector = 0x0fff_0000_0000`，不依赖复位默认值）并配置权限后转测试本体。全程运行模式为 `hypv`，不做模式切换。`Machine-v5-Vast` 为 power（hypv/cfx63）→ hmon（hypv/cfx3）→ 测试本体（hypv）；`power → hmon → smon`（supv/cfx2）路径保留：power 从 BootROM 装载 hmon 并 `trap` 移交；hmon 配置 smon 的 S-mode 向量/权限后 `trap` 移交；smon 建立第一张页表、开启 PTW 并接管运行期。M11 测试不覆盖 smon。
- **legacy `-bios` 路径**：仍按 64 KiB 复位窗口（`0xffff_ffff_0000` 起）装载，既有探针/e2e 语义不变。

---

## 3. cfx 与权限

每个核芯功能扩展提供 cg0–cg7 共有寄存器，规范相同；其中 cg0–cg3 为 `user`/`jail`/`supv`/`hypv` 各自的 12 个模式寄存器，cg4–cg6 为配置/现场/暂存寄存器。`cg7` 为内部空间描述寄存器（[DADAO-12 §3.8]）：每 4 个 rc 描述一个内部空间，字段按**数组** `space_{desc,start,size,attr}[i]`（`i = 0..15`）定义，未实现空间以 `exists=0` 表示，全部只读、写触发 `CFXREG`。[DADAO-12 §3. 共有寄存器设计规范]

- 每个 cfx 的 `cfxtrap`/`cfxmem`/`cfxreg`/`cfxexe`（`rc0`–`rc3`）为四类 64 位同步来源 mask，`rc4` 为 `cfx_intr_mask`：**0=允许，1=屏蔽**，位索引=源 cfx；自身只绕过 cfx 轴。`cfx0`–`cfx3` 的 `cg8`/`rc1` 为 `global_cfx_intr_mask`。[DADAO-12 §3. 共有寄存器设计规范]
- `switch_run_mode` 为陷入时切换的运行模式。[DADAO-12 §3. 共有寄存器设计规范]
- reserved cfxha（集见 `§1.2`）的 `trap`/`escape` 触发当前运行模式 monitor 的 `ILLI`；权限拒绝触发 `CFXPERM`（`1<<7`，进入当前模式 monitor），escape 帧/目标错误触发 `CFXESC`（`1<<3`，进入当前 cfx）。[DADAO-12 §4. 专有寄存器设计规范]
- HSJU 或 R/W/X 不符属于页表/PTW 层权限异常：当前运行模式对应的 HSJU 位为 0，或取指/读/写分别不满足 X/R/W 时触发 `CFXPERM`（当前运行模式 monitor）；地址转换第一步已不再按 `VA[47:42]` 选择 PTBR，也不再有 PTBR 模式权限位图。[DADAO-12 §2.2.5 操作系统页管理][DADAO-12 §4.5 cfx_ptw]
- **两个权限层次**：页表/PTW 层权限（HSJU 或 R/W/X 不符）与 **cfx 访问权限**（`cfxtrap`/`cfxmem`/`cfxreg`/`cfxexe` mask 拒绝，见 `§5` 异常进入流程）是**不同层次**，不可混同；两者失败后均归当前运行模式 monitor 的 `CFXPERM`（原因名收敛，权限来源不同）。[DADAO-12 §4. 专有寄存器设计规范]

- **测试机 cfx 实现范围（按 profile）**：
  - **`Machine-v5-Tiny`**：实现 **`cfx_power`（cfx63，启动移交）** 与 **`cfx3`（`hmon`，同步异常向量）**，提供其 cg0–cg7 共有寄存器与异常向量；`cfx_power`（cfx63）用于启动移交（`power → hmon`）。**不实现 `cfx2`（smon）/`cfx32`（pmem）/`cfx4`（ptw）/`cfx5`（cache）/`cfx33`（llc）/`cfx34`（time）等其它 cfx**。cfx 寄存器访问与 `cfx2rd`/`cfx2rc` 对未实现 cfx ⇒ `CFXREG`；非 semihosting 的 `trap cfx_hmon`（`cfxha=3`，`immu18 < 0x3FF00`）按 `DADAO-12 §5.2` 进入 hmon 向量（`CFXTRAP`）；`trap`/`escape` 到未实现 cfx ⇒ `ILLI`（进入 hmon 向量，见 `§4.4`）。**semihosting 判定只看 `immu18`（`§5.1`），与 `cfxha` 无关**。
  - **`Machine-v5-Vast`**：实现 **`cfx0`/`cfx1`/`cfx2`/`cfx3`/`cfx63`**（`umon`/`jmon`/`smon`/`hmon`/`power`）以及 **`cfx4`（`ptw`）的 PTW/TLB 寄存器**（`cfx_ptw_ptbr`、`cfx_ptw_enable`、`cfx_ptw_tlb_*`）、**页表步进**、**TLB 命中/填充/失效**与 **A/D 回写**（`DADAO-12 §2.2`、`§4.5`）；并实现 **`cfx32`（`pmem`）的 64 KiB SRAM 与 `cg15` DMA**（`DADAO-12 §2.1`、`§4.9`）。`cfx5`（`cache`）为已分配未实现，测试机按未实现 cfx 处理（访问其寄存器 ⇒ `CFXREG`）。
  - 上述范围为**测试机约定**（控制首版成本），**不构成对上游 `DADAO-12`/`DADAO-13` 架构的 cfx 数量/编号限制**。[DADAO-12 §1. 运行模式与核芯功能扩展]
- **测试机 `cfx_pmem` DMA 约定（仅 Vast）**：DMA 只在 `cfx_pmem` SRAM 与物理存储器之间搬运，异步完成（软件须轮询 `dma_status.BUSY` 或使能 `IRQ_EN`）；DMA 可读 RAM 与 boot ROM、只可写 RAM，其余 PA 属 `PA_FAULT`；`PMEM_DMA`（`1 << 8`）直接投递本 hart 的 `cfx_pmem` 异常入口（单 hart）。[DADAO-12 §4.9]
- 对**不存在**的核芯功能扩展（其 cfx 寄存器）的访问触发 **`CFXREG`**；reserved cfxha（集见 `§1.2`）的 `trap`/`escape` 仍按 `§5` 触发当前运行模式 monitor 的 `ILLI`。[DADAO-22 §3. 系统信息（smon）][DADAO-12 §5. 异常进入与异常退出]

- **`cfx_power`（cfx63）的 `cg7` 与 `cg8`/`rc1`（测试机约定）**：
  - **`cg7` 空间块 0 = BootROM**：`desc` = `exists|ROM`（`0x5`）、`start = BootROM 起始地址 − (63 << 42)`、`size` = BootROM 字节数、`attr` = `R|X`（`0x5`）；其余空间块 `exists = 0`（`start`/`size`/`attr` 读 0）。按 profile：`Machine-v5-Tiny` ⇒ `start = 0x3ff_ffff_0000`、`size = 0x1_0000`（64 KiB）；`Machine-v5-Vast` ⇒ `start = 0x3ff_ffc0_0000`、`size = 0x40_0000`（4 MiB）。两者均满足 `start + size = 2^42`。[DADAO-12 §3.8 cg7][DADAO-12 §2.1 核内地址空间]
  - **`cg8`/`rc1`（`cfx_power_ctrl`，WO；`bit0`=关机、`bit1`=硬复位、`bit2`=软复位）**：`Machine-v5-Tiny` **未实现**该寄存器，访问 ⇒ `CFXREG`（显式失败，不设静默成功的桩）。[DADAO-12 §4.12 cfx_power]

---

## 4. `trap`/`escape` 与异常进入流程

### 4.1 一般 `trap` → 异常进入流程 → cfx 向量

`trap cfxha, immu18` 的 `cfxha` 指定服务提供者（目标核芯功能扩展），`immu18` 为功能编号。[DADAO-22 §1. 调用约定]

当 `immu18 < 0x3FF00`（即不在 semihosting 区 `0x3FF00–0x3FFFF`）时，为**一般 trap**：先过权限检查，允许后**走 `DADAO-12 §5` 异常进入流程**（步骤 1–10，含步骤 10「跳转至异常向量」`inner_inst_pointer <= cfx_⟨cfxname⟩_<mode>_excp_vector`）——即**进入该 cfx 的异常向量**。[DADAO-12 §5. 异常进入与异常退出]

`Machine-v5-Tiny` 的一般 trap：`cfxha = 3` 且 `immu18 < 0x3FF00` 时按本节进入 hmon 向量（`CFXTRAP`，见 `§3`/`§4.4`）；`cfxha` 为未实现 cfx ⇒ `ILLI`（同步异常进 hmon 向量，见 `§4.4`）；`cfx_power`（cfx63）按 `DADAO-12 §5.2` 的通用 trap 规则处理。

### 4.2 `escape` → 异常退出流程

`escape` 指令完成异常退出：恢复 `excp_prev_run_mode`、递增 `escape_num`，并以 `escape` 的 `imms18`（指令字偏移）计算返回地址并跳转——`Addr = excp_cause_ip + (imms18 << 2)`。[DADAO-12 §异常退出流程] 汇编层写 `escape cfxha, [excp_cause_ip, imms20]`，`imms20` 以字节为单位、**只允许 0 或 4**（`imms18 ∈ {0, 1}`）；`imms18[17:1]` 为 SBZ，手工编码非零 ⇒ `ILLI`（先于任何状态切换）。[SimRISC-11]

被调方通过 `escape cfxha, [excp_cause_ip, 4]` 返回 trap 指令的下一条指令（`excp_cause_ip + 4`）。[DADAO-22 §1. 调用约定]

- **返回/目标 cfx 恒为当前 cfx（帧中不保存 `prev_cfx`）**：`DADAO-12 §5.3` 原文为「`escape` 指令编码中指定了 `cfxha`，它必须是当前执行的核芯功能扩展（`inner_cfx_code`）；返回 cfx、运行模式与 IP 均取自当前 cfx 的异常帧」；其硬件语义（`§5.3` 步骤 0–3）在 `cfxha != inner_cfx_code` 时先报**当前 cfx** 的 `CFXESC`，通过后只恢复 `global_cfx_intr_mask` 与 `excp_prev_run_mode`、递增 `escape_num` 并更新 `IP`，**不改变 `inner_cfx_code`**；异常帧中也没有保存 `prev_cfx` 的寄存器。故 `escape` 的目标 cfx 恒为**当前 cfx**（即发起 `escape` 的 cfx）。[DADAO-12 §5.3 异常退出流程]

### 4.3 两条路对照

| 路径 | 触发条件 | 处理 | 返回 |
|------|----------|------|------|
| **一般 trap** | `immu18 < 0x3FF00`（不在 `0x3FF00–0x3FFFF`） | 走 `DADAO-12 §5` 异常进入流程，**进入 cfx 向量** | 由被调方 `escape` 返回 |
| **semihosting** | `0x3FF00 ≤ immu18 ≤ 0x3FFFF`（`immu18[17:8] == 0x3FF`） | 实现层**译码短路**，**不进入向量**（同构 RISC-V `RISCV_EXCP_SEMIHOST`） | 直接 **IP 步进**返回（见 `§5`） |

一般 trap 与 semihosting 分离，**不得把 semihosting 混入向量路径**（否则实现者会误让 semihosting 进入向量）。`Machine-v5-Tiny` 的一般 trap 判定见 `§4.1`；`immu18` 的区间判定与 `cfxha` 无关（`§5.1`）。

### 4.4 同步异常进入 hmon（`Machine-v5-Tiny`）

`Machine-v5-Tiny` 运行模式恒为 `hypv`，故 `DADAO-12 §5.2` 的「当前运行模式 monitor」= `cfx3 hmon`：执行期同步异常不经 `trap` 指令、**直接进入 hmon 向量**，处理流程与现场寄存器（`excp_cause_id`/`excp_cause_ip`/`excp_cause_info`/`excp_prev_run_mode`）按 `DADAO-12 §5.2` 的异常进入流程。[DADAO-12 §5.2 异常进入流程]

- **五类同步异常与 `excp_cause`**（`excp_cause_id` = one-hot，位索引见 `§7.1`）：

| 名称 | `excp_cause_id` | 进入 hmon 的时机 / `excp_cause_info` |
|------|-----------------|--------------------------------------|
| `CFXMEM` | `1 << 1` | 核内地址空间非法访问/取指（`§1.2` 路由）时；`info` = 访存地址 |
| `ILLI` | `1 << 8` | 译码阶段遇到非法指令（含对未实现 cfx 的 `trap`/`escape`）时；`info` = 指令编码 |
| `UNDI` | `1 << 9` | 译码阶段遇到未定义指令时；`info` = 指令编码 |
| `MALIGN` | `1 << 12` | 地址计算后、访存前发现非对齐访存时；`info` = 访存地址 |
| `IALIGN` | `1 << 13` | 取指前检测 `IP[1:0] ≠ 00` 时；`info` = `IP` 值 |

- **`excp_cause_info` 的规定范围**：本册只规定上表 5 类（`CFXMEM`/`ILLI`/`UNDI`/`MALIGN`/`IALIGN`）的 `info`；其余异常原因（`CFXTRAP`/`CFXESC`/`CFXPERM`/`CFXREG`/`RASOF`/`RASUF`）的 `info` 按 `DADAO-13 §2`，本册不另行规定；未规定者为 0。[DADAO-13 §2. cfx_hmon]
- **IALIGN 的 IP 停留语义**：`IALIGN` 为精确异常——**IP 停留在非法地址**，`excp_cause_ip` 记录该非法 `IP`，硬件**不写回下一条指令地址**；处理方式由 hmon 决定（与 `DADAO-12 §5` 的精确异常定义一致）。[DADAO-12 §5. 异常进入与异常退出]
- **进入目标**：目标 cfx = `cfx3 hmon`，`inner_inst_pointer <= cfx_hmon_hypv_excp_vector`；该向量由 hmon **启动时显式写入** `0x0fff_0000_0000`（hmon SRAM 起始，`§1.1`），**不依赖复位默认值**——`DADAO-13 §1` 规定该寄存器初值由平台/实现定义；`excp_prev_run_mode` = `hypv`；模式切换**强制 `hypv`**（`cfx_hmon_hypv_switch_run_mode` 的写入被忽略、**寄存器保存值保持 `3`**，读回该保存值，见 `§2`）。[DADAO-12 §5.2 异常进入流程][DADAO-13 §1. cg3 - hypv mode 寄存器]
- **返回**：hmon 用 `escape cfx_hmon, [excp_cause_ip, 0]`（重试）或 `escape cfx_hmon, [excp_cause_ip, 4]`（跳过）返回（`§4.2`）；`IALIGN` 时 `excp_cause_ip` 即非法地址，是否重试/跳过由 hmon 软件决定。

---

## 5. semihosting

semihosting 是 v5 测试机提供的「guest 经 `trap` 请求宿主 I/O」机制；本节为其**规范正文**（服务号值语义取自 Arm Semihosting；v5 特有部分标测试机约定）。

- **两 profile 均提供 semihosting**。semihosting 判定只依赖 `immu18`（`§5.1`），与 `cfxha` 无关：`immu18 ∈ 0x3FF00–0x3FFFF` 时短路到宿主；只有非 semihosting 的 `trap` 才进入 cfx 向量。
- **`Machine-v5-Tiny`**：semihosting 统一写 `trap cfx_hmon`（`§5.1`；其它 `cfxha` 亦等效）；非 semihosting 的 `trap cfx_hmon` 进入 hmon 向量（`§4.4`），与 semihosting **无冲突**。Tiny 只用 semihosting 完成控制台与退出闭环（控制台/调试输出与 `SYS_EXIT`）；运行期同步异常由 hmon 处理（`§4.4`）。`Machine-v5-Vast` 同样以 semihosting 作宿主 I/O 与停机协议。

### 5.1 判定（入口 tag）

- **判定**：`trap cfxHA, immu18` 中 **`immu18[17:8] == 0x3FF`**（即 `0x3FF00–0x3FFFF`）⇒ 该 `trap` 为 **semihosting 调用**（**与 `cfxha` 无关**）。
- **调用形如 `trap cfx_hmon, 0x3FF00`**（两 profile 统一写法）：semihosting 服务号仍占 `immu18` 低 8 位（`0x3FF00 + op`）；判定只依赖 `immu18[17:8]`，与 `cfxha` 无关——任意 `cfxha` 等效（如 Tiny 的 `trap cfx63, 0x3FF00` 同样按 semihosting 处理）。
- **语义/理由说明（架构自定义）**：该 tag 判定**无上游 spec 依据、属 v5 架构自定义**——`spec/DADAO-22` 只规定 `cfxha` 为服务提供者、`immu18` 为功能编号；`spec/SimRISC-11` 只规定 `immu18` 为功能编号；二者**均无 semihosting 语义**。故本机制在 v5 中由测试机定义，guest/实现共同遵守此 tag。[DADAO-22 §1. 调用约定][SimRISC-11]
- **两条路**：`immu18[17:8] == 0x3FF`（`0x3FF00–0x3FFFF`）走 semihosting 短路（本节）；`immu18 < 0x3FF00` 走一般 trap 进入向量（见 `§4.1`）——`Machine-v5-Tiny` 的启动移交目标为 `cfx_hmon`（`cfxha=3`），`cfxha` 为未实现 cfx ⇒ `ILLI`（见 `§3`/`§4.4`）。

### 5.2 调用约定（传参/返回寄存器）

v5 semihosting 为**恒 64 位**、**大端**。寄存器映射如下：

| 角色 | v5 寄存器 | 说明 |
|------|-----------|------|
| **操作号（标量）** | `rd16`（= `rda0`） | 服务号（见 `§5.3`） |
| **参数块指针（地址）** | `rb16`（= `rba0`） | 指向 64 位字段组成的参数块 |
| **返回值** | `rd8` | 标量返回；指针返回才用 `rb8`，semihosting 不用 |

- 号 → `rd16`、参数块指针 → `rb16`、返回 → `rd8`；对齐共享层 `common_semi_arg(cs,0)`=号、`common_semi_arg(cs,1)`=参数块指针。
- **不另设 `rd15`**：`rd15` 是 `umon`/`jmon` 系统调用号，semihosting 不使用。[DADAO-21 §系统调用规范]
- 传参复用 ABI 约定（数据参数 `rd16–rd31`、地址参数 `rb16–rb31`）；三组寄存器各自独立计数。[DADAO-22 §1. 调用约定][DADAO-21 §参数寄存器：Parameter registers]
- 参数块字段为 **64 位**，按 target 端序读取（v5 **大端**）。

### 5.3 服务表（完整 25 个）

v5 semihosting **服务集 = 完整 25 个**，号值采用 **Arm Semihosting 号值**；服务号值↔入参/出参的权威表即下表。

- 表中「参数块」= `rb16` 指向的 64 位字段块；「无参数」= 参数寄存器须为 0。
- 各服务的语义与字段布局遵循 Arm Semihosting（`Semihosting for AArch32 and AArch64`，`Release 2.0`）。
- `SYS_SYNCCACHE (0x19)` 在 Arm Semihosting `Release 2.0` 中列为保留号；v5 沿用共享层既有号值并纳入服务集。

| 号值 | 名称 | 功能 | 入参 / 返回 |
|------|------|------|-------------|
| `0x01` | `SYS_OPEN` | 打开宿主文件 | 参数块〔文件名指针, 打开模式, 文件名长度〕；返回句柄，失败 `−1` |
| `0x02` | `SYS_CLOSE` | 关闭文件 | 参数块〔句柄〕；返回 `0` 成功 / `−1` 失败 |
| `0x03` | `SYS_WRITEC` | 写单个字符 | 参数寄存器 = 字符指针；无返回 |
| `0x04` | `SYS_WRITE0` | 写以 0 结尾字符串 | 参数寄存器 = 字符串指针；无返回 |
| `0x05` | `SYS_WRITE` | 写缓冲区到文件 | 参数块〔句柄, 缓冲区指针, 字节数〕；返回未写字节数 |
| `0x06` | `SYS_READ` | 从文件读入缓冲区 | 参数块〔句柄, 缓冲区指针, 字节数〕；返回未填字节数 |
| `0x07` | `SYS_READC` | 读控制台字符 | 无参数；返回读到的字节 |
| `0x08` | `SYS_ISERROR` | 判断错误状态 | 参数块〔状态字〕；返回 `0`（非错误）/ 非 `0` |
| `0x09` | `SYS_ISTTY` | 判断交互设备 | 参数块〔句柄〕；返回 `1`/`0` |
| `0x0a` | `SYS_SEEK` | 文件定位 | 参数块〔句柄, 绝对字节位置〕；返回 `0` / 负值 |
| `0x0c` | `SYS_FLEN` | 文件长度 | 参数块〔句柄〕；返回长度 / `−1` |
| `0x0d` | `SYS_TMPNAM` | 取临时文件名 | 参数块〔缓冲区指针, 标识符, 缓冲区长度〕；返回 `0` / `−1` |
| `0x0e` | `SYS_REMOVE` | 删除文件 | 参数块〔路径名指针, 长度〕；返回 `0` / 非 `0` |
| `0x0f` | `SYS_RENAME` | 重命名文件 | 参数块〔旧名指针, 旧名长度, 新名指针, 新名长度〕；返回 `0` / 非 `0` |
| `0x10` | `SYS_CLOCK` | 自启动起百分秒 | 无参数；返回百分秒数 / `−1` |
| `0x11` | `SYS_TIME` | 自 1970-01-01 起的秒 | 无参数；返回秒数（按无符号解释） |
| `0x12` | `SYS_SYSTEM` | 执行宿主命令 | 参数块〔命令串指针, 长度〕；返回状态（见 `§5.6` 风险） |
| `0x13` | `SYS_ERRNO` | 取宿主 errno | 无参数；返回宿主 `errno` |
| `0x15` | `SYS_GET_CMDLINE` | 取命令行 | 参数块〔缓冲区指针, 缓冲区长度〕；返回 `0` / `−1` |
| `0x16` | `SYS_HEAPINFO` | 取堆/栈参数 | 参数块〔heap_base, heap_limit, stack_base, stack_limit〕 |
| `0x18` | `SYS_EXIT` | 报告退出 | 64 位：参数块〔原因码, 子码〕；不返回（见 `§5.5`） |
| `0x19` | `SYS_SYNCCACHE` | 同步 Cache | 无参数；Cache 一致性同步 |
| `0x20` | `SYS_EXIT_EXTENDED` | 报告退出（带退出码） | 参数块〔原因码, 退出码〕；不返回（见 `§5.5`） |
| `0x30` | `SYS_ELAPSED` | 已流逝的 target ticks | 64 位：参数块〔64 位 ticks〕；返回 `0` / `−1` |
| `0x31` | `SYS_TICKFREQ` | tick 频率 | 无参数；返回 ticks/秒 / `−1` |

### 5.4 返回机制

semihosting **无 `escape` 指令**：服务完成后由实现层直接**前移 IP**（`IP += 4`，跳过 `trap`）并写回返回寄存器（`rd8`）；guest 侧不需 `escape` 返回。

- 该机制与一般 trap 的 `escape cfxha, [excp_cause_ip, 4]` 返回（`§4.2`）不同：semihosting 不进入向量，故不适用通用 `escape` 返回约定。[DADAO-22 §1. 调用约定]

### 5.5 停机（`SYS_EXIT` 取代 exit port）

- semihosting **`SYS_EXIT`（`0x18`）/`SYS_EXIT_EXTENDED`（`0x20`）取代 exit port** 作为停机协议。
- 常规应用退出使用原因码 `ADP_Stopped_ApplicationExit`（`0x20026`）；`SYS_EXIT_EXTENDED` 的第二个字段为退出状态码。退出码须忠实传播到 host `$?`，沿用确定性 halt 机制（写入后即锁定退出码）。
- **迁移范围 = 全部**：M1–M4 所有依赖 exit port 的向量/harness 已迁 `SYS_EXIT`（`TESTCASES-034t`）；exit-port MMIO 设备已于 C1 step2（`QEMU-053t`）删除——机器模型不再保留 exit port。

### 5.6 已知风险（`SYS_SYSTEM`）

`SYS_SYSTEM`（`0x12`，执行宿主命令）为**已登记的已知安全风险**：命令在宿主上执行，可能产生非预期后果；v5 **不因此拒绝该服务**（服务集 = 完整 25 个），而以默认 `gdb`/沙箱、`native` 显式开启作为缓解手段。

---

## 6. 加载与 bootrom

M5 的 QEMU 提供**新 bootrom**（固件），用于**初始权限/向量配置**；bootrom 用**自有工具链**编译（LLVM 新指令的首个真实用户）。

- **BootROM（按 profile）**：`Machine-v5-Tiny` 为 64 KiB（`0xffff_ffff_0000`–`0xffff_ffff_ffff`），内容**全部**为复位/启动 stub，**无 image index table**；`Machine-v5-Vast` 为 4 MiB（`0xffff_ffc0_0000`–`0xffff_ffff_ffff`），偏移 0 放 image index table、其后放 ELF 镜像，末 64 KiB（`0xffff_ffff_0000` 起）留给复位/启动代码。复位向量两 profile 均为 `0xffff_ffff_0000`。[DADAO-12 §2.1 核内地址空间]
- **装载语义 — `Machine-v5-Tiny`**：应用为 ELF 时，crt/启动 stub 段在 BootROM（`0xffff_ffff_0000`）、应用 `.text/.rodata/.data/.bss` 在 SRAM（`.text` 起 `0xffff_ff01_0100`），`e_entry` 在 BootROM；宿主按 `PT_LOAD` 分别装入 BootROM 与 SRAM，`.bss` 由 picolibc `__start` 在 SRAM 清零。raw `-kernel` 镜像基址 `0xffff_ff01_0000`，镜像前 `0x100` 字节须全零（保留区），应用入口 `0xffff_ff01_0100`，`SP = 0xffff_ff7e_ff00`；**raw 与 ELF 统一入口 `0xffff_ff01_0100`、统一 `SP`**。Tiny 无 PTW/页表；BootROM 内的启动 stub（`power`，cfx63）以 `trap cfx_hmon` 按 `DADAO-12 §5.2` 的 `CFXTRAP` 移交 hmon，hmon **显式写入**自身异常向量（`§4.4`）并配好权限后转测试本体（`§2`）。
- **装载语义 — `Machine-v5-Vast`**：4 MiB BootROM 经 bootrom 镜像装载路径（机器属性 `bootrom-image`）装入；`power` 从 BootROM 把 hmon 装入 hmon SRAM，`power → hmon → smon` 交接后由 smon 建立**首张页表**：把 64 KiB 全零页表页写到 PA 0（`PTBR=0`），在 L1 index `0`–`3` 写 4 个 512 MiB 超页 PTE，映射 `VA [0, 2 GiB) → PA [0, 2 GiB)`（合计 2 GiB）；每项 `H=1`、`S=1`、`U=J=0`、`R=W=X=1`、`P=1`、`SP=1`、`A=D=1`（A/D 硬件维护）、`SPF=0xFF`；随后写 `cfx_ptw_ptbr=0` 并置 `cfx_ptw_enable=1` 开启 PTW。本册只规定该首张页表，不规定测试镜像的段布局、起始执行位置或 SP。
- **legacy `-bios` 路径**：仍按 64 KiB 复位窗口（`0xffff_ffff_0000` 起）装载，既有探针/e2e 语义不变。
- **模式移交**：`Machine-v5-Tiny` 运行模式始终为 `hypv`，但存在 `power → hmon → 测试本体` 的 cfx/启动移交（同 `§2`）；`Machine-v5-Vast` 为 power → hmon → 测试本体（hypv），`power → hmon → smon` 路径保留（同 `§2`）。
- **并存关系**：`-bios` bootrom 启动路径与 M4 的 ELF 单镜像路径**并存、非替代**——两条启动路径各自可自动化。

---

## 7. 退出

- v5 测试机的程序停机协议为 semihosting **`SYS_EXIT`/`SYS_EXIT_EXTENDED`**（见 `§5.5`），**取代** exit port。
- exit-port MMIO 设备已在 C1 step2（`QEMU-053t`）**随旧 RAM 段一并删除**。

### 7.1 退出码（测试机约定）

- **完整退出码表（测试机约定）**：`$?` 单值区分 guest pass/fail 与机器 fault；机器 fault 按来源分「其它 cfx」与「monitor」两段。

| 范围 | 段 | 位域 | 含义 |
|------|----|------|------|
| `0x00`–`0x3F` | guest | — | PASS |
| `0x40`–`0x7F` | guest | — | FAIL（guest 自定义失败码） |
| `0x80`–`0xBF` | 其它 cfx | `bit7=1, bit6=0, bit5:0=cfxHA` | 目标/当前 cfx 的同步异常退出码 |
| `0xC0`–`0xFF` | monitor | `bit7=1, bit6=1, bit5:4=运行模式, bit3:0=异常位索引` | 当前运行模式 monitor 的同步异常退出码 |

- **monitor 段编码**：`bit5:4` 为运行模式——`user`=`00`、`jail`=`01`、`supv`=`10`、`hypv`=`11`；当前运行模式对应 monitor：`user→cfx0`（`umon`）、`jail→cfx1`（`jmon`）、`supv→cfx2`（`smon`）、`hypv→cfx3`（`hmon`）。[DADAO-12 §5.2 异常进入流程]
- **monitor 段异常位索引（11 项）**：`bit3:0` 取 DADAO 异常位索引，逐项如下；每行使用 `0xC0`–`0xFF` 的 monitor 范围。

| 位索引 | 范围 | 位域 | 含义 |
|--------|------|------|------|
| 0 | `0xC0`–`0xFF` | `bit3:0=0` | `CFXTRAP` |
| 1 | `0xC0`–`0xFF` | `bit3:0=1` | `CFXMEM` |
| 2 | `0xC0`–`0xFF` | `bit3:0=2` | `CFXREG` |
| 3 | `0xC0`–`0xFF` | `bit3:0=3` | `CFXESC` |
| 7 | `0xC0`–`0xFF` | `bit3:0=7` | `CFXPERM` |
| 8 | `0xC0`–`0xFF` | `bit3:0=8` | `ILLI` |
| 9 | `0xC0`–`0xFF` | `bit3:0=9` | `UNDI` |
| 10 | `0xC0`–`0xFF` | `bit3:0=10` | `RASOF` |
| 11 | `0xC0`–`0xFF` | `bit3:0=11` | `RASUF` |
| 12 | `0xC0`–`0xFF` | `bit3:0=12` | `MALIGN` |
| 13 | `0xC0`–`0xFF` | `bit3:0=13` | `IALIGN` |

- **`CFXTRAP`/`CFXESC` 的目标 cfx 编码**：`CFXTRAP`（位索引 0）进入**目标 cfx**、`CFXESC`（位索引 3）进入**当前 cfx** 时，退出码按「其它 cfx」段编码（`0x80`–`0xBF`，`bit7=1`、`bit6=0`、`bit5:0` = 对应 cfx 的 cfxHA），**不**按 monitor 段编码；monitor 表中的 0/3 仅保留位索引定义。
- **同步异常落点**：除上述两条外，执行期同步异常均进入**当前运行模式 monitor**，按 monitor 段编码：`CFXMEM`/`CFXREG`/`CFXPERM`/`ILLI`/`UNDI`/`RASOF`/`RASUF`/`MALIGN`/`IALIGN`。[DADAO-12 §5.2 异常进入流程]
- **未映射与 A/D 回写失败**：无映射的核内地址访问/取指归当前运行模式 monitor 的 `CFXMEM`；A/D 回写失败同样归当前运行模式 monitor 的 `CFXMEM`（`cause_info` = PTE 物理地址）。[DADAO-12 §2.2.5 操作系统页管理][DADAO-12 §2.2.6 异常检查优先级]
- **reserved cfx**：reserved cfx（集见 `§1.2`）的普通 `ld/st` 归当前运行模式 monitor 的 `CFXMEM`；其 `trap`/`escape` 归当前运行模式 monitor 的 `ILLI`。[DADAO-12 §5.2 异常进入流程]
- **`Machine-v5-Tiny`**：运行模式恒 `hypv`，同步异常先进入 `cfx3 hmon`（`§4.4`）；若未被 hmon 处理而作为机器 fault 终止，按 monitor 段的 `hypv` 编码（`0xF0`–`0xFF`）。
- **编码冻结、不得重排**：退出码分段与 monitor/其它 cfx 位域一经生效**不得重排**；monitor 位索引沿用 DADAO 异常位索引，新增原因不得改变既有索引。[DADAO-12 §5.2 异常进入流程]

---

## 附录：版本与变更记录

> **发布动作**：把顶部 `-rc` 段去 `-rc` 并补发布日期，再于其上方新开空 `-rc` 段。

### 0.4.3-rc（未发布）

- Tiny `switch_run_mode` 口径澄清（2026-11-10 用户裁定）：写入被忽略、**寄存器保存值保持 `3`**，读回为保存值（不是「读回恒 3」的常量语义）。

- **reserved cfx 集**：改为引用上游——保留 cfx 即 `DADAO-12 §1` 编号表中 `cfxname = reserved` 的编号（含 `per-task` 段中尚未分配的编号）；本册**不再列举编号**，以免与上游漂移。
- **`excp_cause_info` 覆盖面**：本册只规定 `CFXMEM`/`ILLI`/`UNDI`/`MALIGN`/`IALIGN` 五类的 `info`；其余原因按 `DADAO-13 §2`，未规定者为 0。
- **`escape` 返回 cfx**：异常帧不保存 `prev_cfx`，`escape` 的目标 cfx 恒为当前 cfx（引 `DADAO-12 §5.3` 原文与步骤 0–3）。
- **Tiny `cfx_power` 寄存器**：`cg7` 空间块 0 = BootROM（`start = BootROM 起始地址 − (63 << 42)`、`size` 按 profile、`attr = R|X`）；`cg8`/`rc1`（power ctrl）Tiny 未实现 ⇒ `CFXREG`。
- **Tiny `switch_run_mode`**：该寄存器写入被忽略（保存值保持 `3`，`hypv`），读回为寄存器保存值；异常进入强制 `hypv`，运行模式不变。

### 0.4.2（未发布，被 0.4.3-rc 取代）

- **Tiny 引入 `cfx_power` + `cfx3 hmon`**：Tiny 从「不实现任何 cfx」改为实现 `cfx_power`（cfx63，启动移交）与 `cfx3 hmon`（同步异常向量）；新增 hmon SRAM `0x0fff_0000_0000`（64 KiB，cfxha 3），`addr[47:42]` 不再恒 `0x3F`；仍无 PTW/页表、不实现 smon。
- **启动链与异常**：Tiny 启动链改为 `power → hmon → 测试本体`；hmon 启动时显式写入 `cfx_hmon_hypv_excp_vector = 0x0fff_0000_0000`（`DADAO-13 §1` 规定其初值由平台/实现定义，不依赖复位默认值）；`CFXMEM`/`ILLI`/`UNDI`/`MALIGN`/`IALIGN` 进 hmon 向量（`excp_cause` 见 `§4.4`），`IALIGN` 时 IP 停留在非法地址；删除「fault 直接映射退出码」口径。
- **semihosting**：`trap` 判定只依赖 `immu18`（`0x3FF00–0x3FFFF` 为 semihosting）；示例统一写 `trap cfx_hmon`，非 semihosting 的 `trap cfx_hmon` 进 hmon 向量。

### 0.4.1（未发布，被 0.4.2-rc 取代）

- **profile 与机器命名**：profile 概念 `Node` → `Vast`（`Machine-v5-Node` → `Machine-v5-Vast`），机器名 `dadao-m1` → `dadao-tiny` / `dadao-vast`（语义不变）。

### 0.4.0（2026-11-08）

**① 平台 profile：Tiny / Vast**

- **两个 profile**：`Machine-v5-Tiny` = BootROM 64 KiB + SRAM 8 MiB、无 cfx / 无 PTW / 无 hmon 与异常路径、`trap` 只作 semihosting 开关；`Machine-v5-Vast` = BootROM 4 MiB + PA RAM 2 GiB、hmon / PTW / hypv，smon 路径保留。两者复位地址均为 `0xffff_ffff_0000`。
- **删除旧几何约定**：单一几何、物理地址与核内地址别名、双映射两步过渡全部作废；`power` 不设 SRAM 改为本机约定（不是架构禁令）；`DADAO-12` 只要求 BootROM ≥ 64 KiB，实际尺寸由本册按 profile 规定。
- **BootROM 尺寸按 profile**：Tiny 64 KiB、Vast 4 MiB；复位向量仍在 BootROM 末 64 KiB 起点。
- **Tiny 装载约定**：raw 镜像基址 `0xffff_ff01_0000`（镜像前 `0x100` 全零）、应用入口 `0xffff_ff01_0100`、`SP 0xffff_ff7e_ff00`；ELF 的 crt / 启动 stub 落 BootROM、应用段落 SRAM，raw 与 ELF 统一入口与 `SP`。
- **cfx 实现范围按 profile**：Tiny 不实现任何 cfx（含 `cfx_power`），只保留 semihosting；Vast 实现 `cfx0/1/2/3/63`、`cfx4`（PTW/TLB）、`cfx32`（SRAM/DMA）与时间类 cfx。

**② 启动链与内存布局**

- **启动链**：power（hypv/cfx63）→ hmon（hypv/cfx3）→ 测试本体（hypv）；`power → hmon → smon`（supv/cfx2）路径保留——power 从 BootROM 装载 hmon，hmon 移交 smon，smon 建立首张页表并开启 PTW。
- **hmon / smon SRAM**：各 64 KiB（`0x0fff_0000_0000` / `0x0bff_0000_0000`），H/S-mode 异常向量默认等于各自起始地址。
- **Vast 首张页表**：由 smon 在交接后建立；`PTBR=0`、L1 index `0`–`3` 四个 512 MiB 超页，`VA [0, 2 GiB) → PA [0, 2 GiB)`；每项 `H=1`、`S=1`、`U=J=0`、`R=W=X=1`、`P=1`、`SP=1`、`A=D=1`、`SPF=0xFF`；随后开启 PTW。

**③ 地址空间与页表（PTW / TLB）**

- **Step 1（无 PTW）**：`addr[47:42] = 0` 且 `ptw_enable=0` 的访存 / 取指 ⇒ `CFXMEM`；保留 cfx（6–14、16–31、35–61）的普通 `ld/st` ⇒ `CFXMEM`。
- **Step 2（页表步进）**：`ptw_enable=1` 时按单 PTBR 走两级页表（64 KiB 页 / 512 MiB 超页），检查 HSJU 与 R/W/X，页表异常进入 `cfx_ptw`。
- **Step 3（TLB 与 A/D）**：TLB 并入 `cfx_ptw`（命中 / 填充 / ASID / G / 失效接口），A/D 回写落地；A/D 回写失败以 `PTWERR`（`1 << 7`）报告；`cfxha 5`（原 `tlb`）不再分配，按未实现 cfx 报 `CFXREG`。
- **`cfx4` 实现范围**：由 Step 1 的寄存器子集（唯一 `cfx_ptw_ptbr`、`cfx_ptw_enable`）扩展到页表步进与页权限；PTBR 模式权限位图的描述删除。
- **页表异常路由**：页表步进与 TLB 命中产生的异常先进入当前运行模式 monitor——未映射与 A/D 回写失败 ⇒ `CFXMEM`，HSJU 或 R/W/X 不符 ⇒ `CFXPERM`；`cfx_ptw` 不再是页表异常目标；页表 / PTW 层权限与 cfx 访问权限仍是两个层次，失败原因名统一为 `CFXPERM`。
- **术语统一**：地址空间分区一律写 `addr[47:42]`（地址高 6 位），不再使用讨论期简写。

**④ 异常**

- **`escape` 偏移合法集**：0 / +4（`imms18 ∈ {0, 1}`）；`imms18[17:1]` 为 SBZ，非零 ⇒ `ILLI`（§4.2）。

**⑤ 退出码**

- **三段式退出码**：guest `0x00`–`0x3F` / `0x40`–`0x7F`；其它 cfx `0x80`–`0xBF`（`bit5:0` = cfxHA）；monitor `0xC0`–`0xFF`（`bit5:4` = 运行模式、`bit3:0` = DADAO 异常位索引）。补全 monitor 11 个位索引，删除旧的单公式派生与「未映射」独立码。
- **退出码表位置**：由 §1.2（越界访问与越界取指异常）迁至 §7.1（退出码（测试机约定））；§1.2 只保留内存 / 越界异常语义，退出码分段、位域、monitor 位索引与落点逐字不变。

**⑥ cfx 体系**

- **两轴权限模型**：四类同步来源 mask + `cfx_intr_mask` / `global_cfx_intr_mask`；权限拒绝 ⇒ `CFXPERM`，escape 帧 / 目标错误 ⇒ `CFXESC`。
- **cfx 编号**：`cfx5`（`cache`）为已分配未实现；保留 cfx 改为 `6`–`14`、`19`–`61`。
- **`cg7` 内部空间描述**：`cg0`–`cg7` 为共有寄存器；每 4 个 rc 描述一个内部空间（存在 + 类型 one-hot / 42 位起始偏移 / 字节大小 / R-W-X-cacheable-shareable-volatile 属性），16 块用满 `rc0`–`rc63`；寄存器按数组 `space_{desc,start,size,attr}[i]`（`i = 0..15`）定义，未实现空间以 `exists=0` 表示，全部只读、写触发 `CFXREG`。
- **`cfx_pmem` 与 `cg15` DMA**：新增 64 KiB SRAM（`0x83ff_0000_0000`，cfxha 32、内部偏移 `0x3ff_0000_0000`）；DMA 可读 RAM / boot ROM、只能写 RAM。
- **扩展指令清单**：`cfxld` / `cfxst` 已从指令系统删除，只余 `trap` / `escape` / `cfx2rd` / `cfx2rc`（及 `fence`）。

**⑦ semihosting**

- **入口判定**：改为 `immu18[17:8] == 0x3FF`（`0x3FF00–0x3FFFF`），原按 `immu18` 高位两比特的判定作废；§4.1 / §4.3 的一般 trap / semihosting 分界、§5.1 判定与调用示例同步；`HBI_<name>_INIT`（`0x30001`）落在该区之外，按一般 trap 进入目标 cfx 向量。

**⑧ 其它**

- **legacy `-bios`**：仍按 64 KiB 复位窗口装载，与镜像装载路径并存。
- **册名**：`Machine-01` → `Machine-v5`（标题同步为「`Machine-v5：测试机运行环境`」；正文语义不变）。

### 0.3.1（2026-10-16）

- 正文术语 `PC` 统一为 **`IP`**（`IP` = 当前正在执行的指令的地址，见 SimRISC-00）：§4.3 两条路对照与 §5.4 返回机制（semihosting 走 `IP += 4`）。

### 0.3.0（2026-10-11）

- §1.1：唯一 RAM 段基址由全 0（`0x0000_0000_0000`，cfxha 0）迁到 `0xFC00_0000_0000`（cfxha 63 / `power`）；容量不变（16 MiB）。

### 0.2.1（2026-10-09）

- §1.1 收敛为 RAM@0 唯一 RAM 段（删旧 RAM 段与 exit-port；§5.5/§7 记 exit-port 已删）。

### 0.2.0（2026-10-09）

- semihosting 返回寄存器统一为 `rd8`（§5.2/§5.4；指针返回 `rb31`→`rb8`）。

### 0.1.1（2026-10-08）

- §1 越界路由 / RAM@0 容量口径。

### 0.1.0（2026-10-07）

- 初版：测试机运行环境与 semihosting 正文（内存映射 / 复位、运行模式、cfx / 权限、`trap`/`escape`/异常进入、semihosting 25 服务、加载 / bootrom、退出）。
