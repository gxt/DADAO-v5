# Kaiwu：测试机运行环境（v5 自定）

> **状态**：当前（0.4.7-rc，未发布；0.4.0 发布 2026-11-08，0.3.1 生效于 2026-10-16：正文术语 `PC` → `IP`；完整版本记录见文末「附录：版本与变更记录」）
>
> **版本与变更记录细则**：版本号 `x.y.z`——**`x=0` 表示尚未正式发布；正式发布后 `x≥1`**；**大改动 `y+1`、有影响的小改 `z+1`**；当前版本见上行「状态」。
>
> **变更记录见文末「附录：版本与变更记录」**（格式 = 「版本（日期）」小标题 + 列表项；**不用表格、不写「依据」**）。
>
> **定位**：本册是 v5 自定规范，定义 **DADAO-v5 测试机（`kaiwu-tiny` / `kaiwu-vast`）运行环境与 semihosting** 的规范正文——面向 QEMU 机器模型、bootrom 固件、harness 与测试向量。上游 `spec/DADAO-*` 与 `spec/SimRISC-*` 仍为**上游基线**；本册不改其架构语义。
>
> **标注约定**：正文中「**测试机约定**」项**无上游 spec 依据**，属 v5 架构自定义；有上游出处的语义给出 `[DADAO-NN §x]`/`[SimRISC-NN §x]` 引用。`cfx0/1/2/3/63` 等实现范围一律为**测试机约定**，不构成对上游 `DADAO-12`/`DADAO-13` 的架构限制。

---

## 1. 内存映射与复位

CPU 地址固定为 48 位；高 6 位 `addr[47:42]` 为分区键：`0` 为内存窗口（受 `ptw_enable` 控制），`1..63` 为 cfx 1–63 的核内地址空间（`cfx0` 没有内部空间）。[DADAO-12 §2.1 核内地址空间][DADAO-12 §2.2 虚实地址转换]

v5 测试机分 **`Kaiwu-Tiny`**（宿主装载的精简 FS 平台）与 **`Kaiwu-Vast`**（完整系统节点；当前单核，可扩展多核/NUMA）两个 **profile**，由机器属性选择。两 profile 的**复位地址相同**，均为 `cfx_power_hypv_excp_vector = 0xffff_ffff_0000`（cfxha 63 / `power`，位于各自 BootROM 的末 64 KiB），该地址可由 CPU 直接取指并执行。[DADAO-12 §2.1 核内地址空间]

- **Tiny**：实现 **`cfx_power`（cfx63，启动移交）** 与 **`cfx3 hmon`（同步异常向量）**；`addr[47:42]` 由两个 cfxha 段构成——`0x3F`（cfxha 63：BootROM/SRAM）与 `0x03`（cfxha 3：hmon SRAM）。不设 PTW/页表、不实现 smon，**不能进入 `user`/`jail`/`supv`**，运行期固定在名义 `hypv`；只承担非 cfx 指令测试、Embench 与 picolibc 测试集。semihosting 的 `trap` 判定只依赖 `immu18`（见 `§5.1`），一般 `trap cfx_hmon` 进入 hmon 向量（见 `§4.4`）。
- **Vast**：内存窗口 `addr[47:42] = 0` 由 PTW 按页表转换到 56 位 PA；核内空间含 hmon/smon/pmem SRAM；启动链 `power → hmon → 测试本体（hypv）`，`power → hmon → smon` 路径保留给内核/smon 测试。

### 1.1 核内地址空间划分（测试机约定）

v5 测试机使用的核内地址空间按 profile 划分如下（均为 48 位核内有效地址；地址区间为**测试机约定**）。

**`Kaiwu-Tiny`**

| 区域 | 起始 | 大小 | cfxha / cfxname | 说明 |
|------|------|------|-----------------|------|
| **BootROM** | `0xffff_ffff_0000` | 64 KiB | 63 / `power` | 唯一非易失启动源；复位向量 = 起始 = `0xffff_ffff_0000`（镜像偏移 0）；内容是**固定启动固件镜像**（power stub + hmon 运行段 + image index table，见 `§6.2`），**hmon 代码/数据编入该镜像** |
| **SRAM** | `0xffff_ff00_0000` | 8 MiB | 63 / `power` | 可写主存；应用 `.text/.rodata/.data/.bss` 由宿主 loader 装入，**不塞 BootROM** |
| **hmon SRAM** | `0x0fff_0000_0000` | 64 KiB | 3 / `hmon` | hmon 运行段目标；由 power 从 BootROM 复制（`§6.2`），宿主不下发；异常向量初值 = 起始地址（`DADAO-12 §3.4`）；内部偏移 `0x3ff_0000_0000`，越界 ⇒ `CFXMEM`；与 BootROM/SRAM 分属不同 cfxha 段，互不重叠 |

- Tiny 实现 `cfx_power`（cfx63）的启动移交与 `cfx3 hmon` 的异常向量/寄存器；`smon`（cfx2）与其它 cfx 不实现。
- BootROM 与 SRAM 之间的 `0xffff_ff80_0000`–`0xffff_fffe_ffff` 不映射；cfxha 63 段内 BootROM/SRAM 之外、cfxha 3 段内 hmon SRAM 之外、以及其它 cfxha 段 ⇒ `CFXMEM`。

**`Kaiwu-Vast`**

| 区域 | 起始 | 大小 | cfxha / cfxname | 说明 |
|------|------|------|-----------------|------|
| **BootROM** | `0xffff_ffc0_0000` | 4 MiB | 63 / `power` | 唯一非易失启动源；复位向量 `0xffff_ffff_0000`（镜像内偏移 `0x3f_0000`，即末 64 KiB 起点） |
| **PA RAM** | `0`（PA 空间） | 2 GiB | —（内存窗口） | 物理存储器 `[0, 2 GiB)`；CPU 只能经 PTW 从 VA 访问（§1.2），不设核内地址别名；内部分区（页表页 / boot info / 内核 / initramfs）见 `§6.3` |
| **hmon SRAM** | `0x0fff_0000_0000` | 64 KiB | 3 / `hmon` | H-mode 异常向量默认等于起始地址；内部偏移 `0x3ff_0000_0000`，越界 ⇒ `CFXMEM` |
| **smon SRAM** | `0x0bff_0000_0000` | 64 KiB | 2 / `smon` | S-mode 异常向量默认等于起始地址；内部偏移 `0x3ff_0000_0000`，越界 ⇒ `CFXMEM`；M11 保留不使用 |
| **cfx_pmem SRAM** | `0x83ff_0000_0000` | 64 KiB | 32 / `pmem` | cfx_pmem 内部偏移 `0x3ff_0000_0000`；CPU 用 `ld/st` 访问，越界 ⇒ `CFXMEM` |

- **BootROM 尺寸**：上游 `DADAO-12` 只要求 `cfx_power` BootROM **≥64 KiB**，实际大小由本册按 profile 规定（Tiny 64 KiB、Vast 4 MiB）；复位向量两 profile 均为 `0xffff_ffff_0000`（末 64 KiB 起点，镜像内偏移 = 大小 − 64 KiB）。
- **不做双映射**：Tiny 的 SRAM 只在 cfxha 63 段的 `0xffff_ff00_0000`、hmon SRAM 只在 cfxha 3 段的 `0x0fff_0000_0000`；Vast 的 PA RAM 只在 `[0, 2 GiB)` 并仅经页表 VA 映射。两 profile 都不设「同一存储的多地址别名」。
- **`power` 不设 SRAM**：两 profile 的 `power` 分区都不设 SRAM；这是**本机约定**，不构成对上游 `DADAO-12` 的架构限制。
- **legacy `-bios` 复位窗口**：`-bios` 路径仍按 64 KiB 复位窗口（`0xffff_ffff_0000` 起）装载，既有探针/e2e 语义不变；Tiny 的 BootROM 恰为该窗口。

### 1.2 越界访问与越界取指异常（含取指路径）

- **spec 层语义（`CFXMEM`）**：对核内地址空间进行非法访问时触发 `CFXMEM`；其异常原因编号为 `1 << 1`，执行期同步异常按 `DADAO-12 §5.2` 进入当前运行模式 monitor（`CFXTRAP`/`CFXESC` 除外，见 `§7.1`）。[DADAO-12 §2.1 核内地址空间][DADAO-12 §4. 专有寄存器设计规范][DADAO-12 §5.2 异常进入流程]

- **层次与适用**：`CFXMEM` 适用于核内地址空间模型内的非法访问/取指（cfxha 段内的非法子区间、越界访问/取指），归当前运行模式 monitor（退出码编码见 `§7.1`）。
- **精确路由（按 profile）**：
  - **Tiny**：无 PTW（`ptw_enable` 恒 0）。`addr[47:42] == 0` 的普通访存/取指 ⇒ `CFXMEM`，**不直通物理存储器**；cfxha 63 段内 BootROM/SRAM 之外、cfxha 3 段内 `hmon SRAM` 之外、以及其它 cfxha 段 ⇒ `CFXMEM`。同步异常进入当前运行模式 monitor——Tiny 唯一 monitor 为 `cfx3 hmon`（运行模式恒 `hypv`），**经 hmon 向量**处理（见 `§4.4`）。
  - **Vast**：`addr[47:42] == 0` 且 `ptw_enable=1`：按单 PTBR 走页表（PTE 格式/页表步进/页权限/TLB 见 `DADAO-12 §2.2.1–§2.2.6`、`§4.5`）；页表步进与 TLB 命中产生的异常先进入当前运行模式 monitor：未映射与 A/D 回写失败 ⇒ `CFXMEM`，权限拒绝 ⇒ `CFXPERM`（见 `DADAO-12 §2.2.6`、`§5.2`）。`ptw_enable=0`（仅复位后 power/hmon 的早期初始化）时仍按上一条报 `CFXMEM`。
  - 保留 cfx（判定见下条）的普通 `ld/st` ⇒ 当前运行模式 monitor 的 `CFXMEM`；`trap`/`escape`/`cfx2rd`/`cfx2rc` 到保留 cfx ⇒ 当前运行模式 monitor 的 `ILLI`（口径见 `§3`）。
  - **reserved cfx 集（全册唯一定义）**：以 `DADAO-12 §1` 的 cfxha 编号表为**唯一真源**——**表中 `cfxname = reserved` 的编号即保留 cfx**（含 `per-task` 段中尚未分配的编号）；已分配编号及其 `cfxname` 同样以该表为准。本册**不重复列举编号**，以免与上游漂移。[DADAO-12 §1. 运行模式与核芯功能扩展][DADAO-12 §2.1 核内地址空间]
  - 其余未映射地址（Vast 的 `power` 段 BootROM 之外）⇒ 当前运行模式 monitor 的 `CFXMEM`。
- **取指路径同等对待**：越界**取指**与越界**数据访问**同属非法核内地址访问，**均须报异常**，不得只覆盖数据访问路径；不得静默继续或静默丢弃。
- 两 profile 的几何与上述路由以机器接口断言固化；旧「唯一 RAM 段 + PA 别名 + 固定容量」口径随本版 profile 划分作废。

---

## 2. 运行模式

DADAO 定义四种运行模式（两位编码）：`user`（`0b00`）、`jail`（`0b01`）、`supv`（`0b10`）、`hypv`（`0b11`）；`user`/`jail` 为普通用户态，`supv`/`hypv` 为特权态。[DADAO-12 §1. 运行模式与核芯功能扩展]

`hypv`（超管模式）的 cg3 寄存器（含 `cfx_⟨cfxname⟩_hypv_cfxtrap` 等四类同步 mask、`cfx_⟨cfxname⟩_hypv_cfx_intr_mask`、`switch_run_mode`、`excp_vector`）定义见 `DADAO-12 §3.4`。[DADAO-12 §3.4 cg3 - hypv mode 寄存器]

`trap`/`escape`/`cfx2rd`/`cfx2rc` 可在**任意运行模式**下执行；是否允许由各核芯功能扩展的 cfx mask 与指令类型 cfx mask 控制。[SimRISC-11]

异常进入后，硬件把运行模式改为 `cfx_⟨cfxname⟩_<mode>_switch_run_mode` 的值（异常进入流程步骤 6）。[DADAO-12 §5. 异常进入与异常退出][DADAO-12 §3. 共有寄存器设计规范]

- **运行模式范围（按 profile）**：`Kaiwu-Tiny` 不提供模式切换路径——复位后即在特权态（名义 `hypv`；复位时 cfxha 63 / `power`，移交后 cfxha 3 / `hmon`）执行，运行模式恒 `hypv`，**不能进入 `user`/`jail`/`supv`**，不实现 smon；`Kaiwu-Vast` 启用 `hypv`、`supv` 与 `user`，`jail` 不启用。
- **`switch_run_mode`（按 profile）**：`Kaiwu-Vast` 取 `cfx_⟨cfxname⟩_<mode>_switch_run_mode` 的值作为异常进入后的运行模式（上段步骤 6）；`Kaiwu-Tiny`（**测试机约定**）该寄存器的**写入被忽略**（寄存器保存值保持 `3`，`hypv`），**读回为寄存器保存值**；异常进入一律强制 `hypv`（`inner_run_mode ← 3`），运行模式不变。[DADAO-12 §5.2 异常进入流程][DADAO-12 §3.4 cg3 - hypv mode 寄存器]
- **异常承载（按 profile）**：`Kaiwu-Vast` 由 `hmon`（cfx3）承载 hypv 异常、`smon`（cfx2）承载 supv 异常；`Kaiwu-Tiny` 由 `hmon`（cfx3）承载唯一的 hypv 同步异常（无 smon），异常经 hmon 向量处理（见 `§4.4`）。
- **启动链（按 profile）**：`Kaiwu-Tiny` 为 power（hypv/cfx63）→ hmon（hypv/cfx3）→ 测试本体（hypv）：BootROM 内的 power stub 把编入同一镜像的 hmon 运行段复制到 hmon SRAM（`§6.2`），以 `trap cfx_hmon` 按 `DADAO-12 §5.2` 的 `CFXTRAP` 移交 hmon；hmon 入口校验 magic、按需配置权限后 `escape cfx_hmon, [excp_cause_ip, 4]` 返回 power stub，power 跳固定应用入口 `0xffff_ff01_0100`（`§6`）。hmon 异常向量初值即 hmon SRAM 起始（`DADAO-12 §3.4`），入口内显式写入同值属幂等、不是向量可用的前提。全程运行模式为 `hypv`，不做模式切换。`Kaiwu-Vast` 为 power（hypv/cfx63）→ hmon（hypv/cfx3）→ 测试本体（hypv）；`power → hmon → smon`（supv/cfx2）路径保留：power 从 BootROM 装载 hmon 并 `trap` 移交；hmon 配置 smon 的 S-mode 向量/权限后 `trap` 移交；smon 建立第一张页表、开启 PTW 并接管运行期。M11 测试不覆盖 smon。
- **legacy `-bios` 路径**：仍按 64 KiB 复位窗口（`0xffff_ffff_0000` 起）装载，既有探针/e2e 语义不变。

---

## 3. cfx 与权限

每个核芯功能扩展提供 cg0–cg7 共有寄存器，规范相同；其中 cg0–cg3 为 `user`/`jail`/`supv`/`hypv` 各自的 12 个模式寄存器，cg4–cg6 为配置/现场/暂存寄存器。`cg7` 为内部空间描述寄存器（[DADAO-12 §3.8]）：每 4 个 rc 描述一个内部空间，字段按**数组** `space_{desc,start,size,attr}[i]`（`i = 0..15`）定义，未实现空间以 `exists=0` 表示，全部只读、写触发 `CFXREG`。[DADAO-12 §3. 共有寄存器设计规范]

- 每个 cfx 的 `cfxtrap`/`cfxmem`/`cfxreg`/`cfxexe`（`rc0`–`rc3`）为四类 64 位同步来源 mask，`rc4` 为 `cfx_intr_mask`：**0=允许，1=屏蔽**，位索引=源 cfx；自身只绕过 cfx 轴。`cfx0`–`cfx3` 的 `cg8`/`rc1` 为 `global_cfx_intr_mask`。[DADAO-12 §3. 共有寄存器设计规范]
- `switch_run_mode` 为陷入时切换的运行模式。[DADAO-12 §3. 共有寄存器设计规范]
- 权限拒绝触发 `CFXPERM`（`1<<7`，进入当前模式 monitor），escape 帧/目标错误触发 `CFXESC`（`1<<3`，进入当前 cfx）；reserved cfxha 的 `trap`/`escape`/`cfx2rd`/`cfx2rc` 见下条。[DADAO-12 §4. 专有寄存器设计规范]
- **`trap`/`escape`/`cfx2rd`/`cfx2rc` 到不同 cfxha 的两条互斥口径**（`§1.2`/`§7.1` 与实现共同遵守）：
  - **目标为 reserved cfxha**（集见 `§1.2`）⇒ 当前运行模式 monitor 的 **`ILLI`**，四条指令同规（`fence` 到 reserved cfx 同 ⇒ `ILLI`，见 `SimRISC-11 §5`）。据此，reserved 判定**先于**「该 cfx 是否实现」的判定。
  - **目标为非 reserved** 时按寄存器层判定：`cfx2rd`/`cfx2rc` 的目标为**已分配但本 profile 未实现**的 cfx（如 Tiny 的 `cfx5`），或为已实现 cfx 的**未定义 cg/rc** ⇒ 当前运行模式 monitor 的 **`CFXREG`**（`1<<2`；`excp_cause_info` = 指令编码）。
  - `trap`/`escape` 到**非 reserved 的未实现 cfx** 不属上一条：按本节「测试机 cfx 实现范围」处理（Tiny ⇒ `ILLI`，`DADAO-12 §2.1` 允许实现约定未实现行为）。
  - 依据（上游原文）：`DADAO-12 §5.1`「`trap`/`escape`/`cfx2rd`/`cfx2rc` 指令可以在任意运行模式下执行。若 `cfxha` 为 reserved 核芯功能扩展，硬件触发 ILLI 异常。」（原文在该句括注保留编号，本册按 `§1.2` 引用上游编号表，不重复列举）；`DADAO-12 §5.2（一）` 路由表两行「`trap`/`cfx2rd`/`cfx2rc`，`cfxha` 为 reserved ⇒ `ILLI` ⇒ 当前运行模式 monitor」「非法核芯功能扩展寄存器访问 ⇒ `CFXREG` ⇒ 当前运行模式 monitor（不进入被访问的核芯功能扩展）」。
  - 两条**不冲突**：reserved 是**编号层**判定（`ILLI`），cg/rc 与实现是**寄存器层**判定（`CFXREG`）；同一 cfxha、同一指令只命中其中一条。[DADAO-12 §5.1 指令行为说明][DADAO-12 §5.2 异常进入流程]
- HSJU 或 R/W/X 不符属于页表/PTW 层权限异常：当前运行模式对应的 HSJU 位为 0，或取指/读/写分别不满足 X/R/W 时触发 `CFXPERM`（当前运行模式 monitor）；地址转换第一步已不再按 `VA[47:42]` 选择 PTBR，也不再有 PTBR 模式权限位图。[DADAO-12 §2.2.5 操作系统页管理][DADAO-12 §4.5 cfx_ptw]
- **两个权限层次**：页表/PTW 层权限（HSJU 或 R/W/X 不符）与 **cfx 访问权限**（`cfxtrap`/`cfxmem`/`cfxreg`/`cfxexe` mask 拒绝，见 `§5` 异常进入流程）是**不同层次**，不可混同；两者失败后均归当前运行模式 monitor 的 `CFXPERM`（原因名收敛，权限来源不同）。[DADAO-12 §4. 专有寄存器设计规范]

- **测试机 cfx 实现范围（按 profile）**：
  - **`Kaiwu-Tiny`**：实现 **`cfx_power`（cfx63，启动移交）** 与 **`cfx3`（`hmon`，同步异常向量）**，提供其 cg0–cg7 共有寄存器与异常向量；`cfx_power`（cfx63）用于启动移交（`power → hmon`）。**不实现 `cfx2`（smon）/`cfx32`（pmem）/`cfx4`（ptw）/`cfx5`（cache）/`cfx33`（llc）/`cfx34`（time）等其它 cfx**。cfx 寄存器访问与 `cfx2rd`/`cfx2rc` 对未实现 cfx ⇒ `CFXREG`；非 semihosting 的 `trap cfx_hmon`（`cfxha=3`，`immu18 < 0x3FF00`）按 `DADAO-12 §5.2` 进入 hmon 向量（`CFXTRAP`）；`trap`/`escape` 到未实现 cfx ⇒ `ILLI`（进入 hmon 向量，见 `§4.4`）。**semihosting 判定只看 `immu18`（`§5.1`），与 `cfxha` 无关**。
  - **`Kaiwu-Vast`**：实现 **`cfx0`/`cfx1`/`cfx2`/`cfx3`/`cfx63`**（`umon`/`jmon`/`smon`/`hmon`/`power`）以及 **`cfx4`（`ptw`）的 PTW/TLB 寄存器**（`cfx_ptw_ptbr`、`cfx_ptw_enable`、`cfx_ptw_tlb_*`）、**页表步进**、**TLB 命中/填充/失效**与 **A/D 回写**（`DADAO-12 §2.2`、`§4.5`）；并实现 **`cfx32`（`pmem`）的 64 KiB SRAM 与 `cg15` DMA**（`DADAO-12 §2.1`、`§4.9`），以及 **`cfx5`（`cache`）的寄存器与维护命令**（`DADAO-12 §4.6`；本机约定见 `§3.2`）。
  - 上述范围为**测试机约定**（控制首版成本），**不构成对上游 `DADAO-12`/`DADAO-13` 架构的 cfx 数量/编号限制**。[DADAO-12 §1. 运行模式与核芯功能扩展]
- **测试机 `cfx_pmem` DMA 约定（仅 Vast）**：DMA 只在 `cfx_pmem` SRAM 与物理存储器之间搬运，异步完成（软件须轮询 `dma_status.BUSY` 或使能 `IRQ_EN`）；DMA 可读 RAM 与 boot ROM、只可写 RAM，其余 PA 属 `PA_FAULT`；`PMEM_DMA`（`1 << 8`）直接投递本 hart 的 `cfx_pmem` 异常入口（单 hart）。[DADAO-12 §4.9]
- 对**不存在**的核芯功能扩展（其 cfx 寄存器）的访问触发 **`CFXREG`**；reserved cfxha（集见 `§1.2`）的 `trap`/`escape`/`cfx2rd`/`cfx2rc` 仍按 `§1.2`/`§5` 触发当前运行模式 monitor 的 `ILLI`（口径见本节「两条互斥口径」）。[DADAO-22 §3. 系统信息（smon）][DADAO-12 §5. 异常进入与异常退出]

- **`cfx_power`（cfx63）的 `cg7` 与 `cg8`/`rc1`（测试机约定）**：
  - **`cg7` 空间块 0 = BootROM**：`desc` = `exists|ROM`（`0x5`）、`start = BootROM 起始地址 − (63 << 42)`、`size` = BootROM 字节数、`attr` = `R|X`（`0x5`）；其余空间块 `exists = 0`（`start`/`size`/`attr` 读 0）。按 profile：`Kaiwu-Tiny` ⇒ `start = 0x3ff_ffff_0000`、`size = 0x1_0000`（64 KiB）；`Kaiwu-Vast` ⇒ `start = 0x3ff_ffc0_0000`、`size = 0x40_0000`（4 MiB）。两者均满足 `start + size = 2^42`。[DADAO-12 §3.8 cg7][DADAO-12 §2.1 核内地址空间]
  - **`cg8`/`rc1`（`cfx_power_ctrl`，WO；`bit0`=关机、`bit1`=硬复位、`bit2`=软复位）**：`Kaiwu-Tiny` **未实现**该寄存器，访问 ⇒ `CFXREG`（显式失败，不设静默成功的桩）。[DADAO-12 §4.12 cfx_power]

### 3.1 TLB 的测试机约定

TLB 属 `cfx_ptw`，其匹配键、命中检查、填充条件、A/D 维护与失效接口按 `DADAO-12 §2.2.1–§2.2.6`、`§4.5` 执行（见 `§1.2`、`§6.3.5`）；下列四条为本机的**测试机约定**，不改变上游语义。[DADAO-12 §2.2.1 超页的地址转换][DADAO-12 §2.2.5 操作系统页管理][DADAO-12 §4.5 cfx_ptw - page table walker]

- **失效同步完成**：`cfx_ptw_tlb_control` 的写指令**同步完成**——指令返回即生效，其后的访存必见失效结果（无 busy/done 位、无异步完成信号）。`clean`/`flush` 触发的 A/D 回写失败**在该写指令上**报当前运行模式 monitor 的 `CFXMEM`（`cause_info` = PTE 物理地址），且**不得部分完成**——按**条目级**解释：处理失败的条目保持原状（`flush` 失败不删除该条目、`clean` 失败不清其挂起位），**其后条目一律不处理、保持原状**（遇错即停；一条指令最多报一处失败）。[DADAO-12 §4.5 cfx_ptw - page table walker][spec-decision]（用户 2026-11-16 确认）
- **per-hart**：TLB 与 `cfx_ptw_tlb_control` 都是 **per-hart** 状态，失效命令只作用于执行该指令的 hart；跨 hart 的失效传播与一致性不在本册范围（多 hart 机型另行规定）。[DADAO-12 §4.5 cfx_ptw - page table walker][spec-decision]（用户 2026-11-16 确认）
- **I/D 分表与命令作用域**：本机 TLB 的组织为 **I/D 两表**（每核各一；I 表条目无 D 状态，取指命中只置 A）——`DADAO-12 §4.5` 明写「条目数、组织与替换策略由实现决定」，故不构成对上游的偏离。`cfx_ptw_tlb_control` **不引入 I/D 选择位**，一条命令作用于两表：判序 **I 表先、D 表后**；跨两表仍按「条目级 + 首错即停、一条指令最多报一处失败」（`cause_info` 取该失败条目的 PTE 物理地址）；`scope=VA` / `range` 对两表**各自匹配**（同一 VA 在 I/D 的 PTE 可以不同）。[DADAO-12 §4.5 cfx_ptw - page table walker][spec-decision]（用户 2026-11-20 确认）
- **实现范围**：本机的 TLB 建模由 **QEMU** 机器模型承担；`tests/arch` 的 PTW/TLB 探针是**跨实现判据**，其它实现不在本册验收面。[spec-decision]（用户 2026-11-16 确认）

### 3.2 cache（cfx5）的测试机约定

`cfx_cache` 的寄存器、控制字编码与维护命令语义按 `DADAO-12 §4.6` 执行；下列为本机的**测试机约定**，不改变上游语义。[DADAO-12 §4.6 cfx_cache - cache organization]

- **实现范围（仅 Vast）**：`Kaiwu-Vast` 实现 `cfx5`（`cache`）的寄存器与维护命令——按 `DADAO-12 §4.6` 的位定义，I 侧与 D 侧**均存在** ⇒ `cache_exist` 读回 `0b11`、`cache_enable` 复位值同；cache 的容量、行大小、组数与替换策略**由实现决定**，本册不规定。[DADAO-12 §4.6 cfx_cache - cache organization][spec-decision]（用户 2026-11-20 确认 `cfx5` 由 Vast 实现、Tiny 不实现）
- **`Kaiwu-Tiny` 不实现 `cfx5`**：访问其寄存器与 `cfx2rd`/`cfx2rc` ⇒ `CFXREG`；`trap`/`escape` 到 `cfx5` ⇒ `ILLI`（口径见 `§3` 的两条互斥口径与 `§4.4`）。[DADAO-12 §4.6 cfx_cache - cache organization][spec-decision]（用户 2026-11-20 确认）
- **维护命令同步完成**：写 `cfx_cache_ctrl` 的指令**同步完成**——指令返回即生效，其后的访存必见维护结果；无 busy/done 位、无异步完成信号。[DADAO-12 §4.6 cfx_cache - cache organization][spec-decision]（用户 2026-11-20 确认）
- **per-hart**：`cfx_cache` 的寄存器与维护命令都是 **per-hart** 状态，只作用于执行该写指令的 hart；跨 hart 的维护传播与一致性不在本册范围。[DADAO-12 §4.6 cfx_cache - cache organization][spec-decision]（用户 2026-11-20 确认）
- **I/D 选择位与两侧判序**：`cfx_cache_ctrl[15:14]` 中 **bit15 = I、bit14 = D**（`11` = 两侧全选、`10` = 只 I、`01` = 只 D、`00` = no-op）；两侧全选时**先 I 后 D**，两侧各自按所选范围匹配，互不影响。[DADAO-12 §4.6 cfx_cache - cache organization][spec-decision]（用户 2026-11-20 确认）

---

## 4. `trap`/`escape` 与异常进入流程

### 4.1 一般 `trap` → 异常进入流程 → cfx 向量

`trap cfxha, immu18` 的 `cfxha` 指定服务提供者（目标核芯功能扩展），`immu18` 为功能编号。[DADAO-22 §1. 调用约定]

当 `immu18 < 0x3FF00`（即不在 semihosting 区 `0x3FF00–0x3FFFF`）时，为**一般 trap**：先过权限检查，允许后**走 `DADAO-12 §5` 异常进入流程**（步骤 1–10，含步骤 10「跳转至异常向量」`inner_inst_pointer <= cfx_⟨cfxname⟩_<mode>_excp_vector`）——即**进入该 cfx 的异常向量**。[DADAO-12 §5. 异常进入与异常退出]

`Kaiwu-Tiny` 的一般 trap：`cfxha = 3` 且 `immu18 < 0x3FF00` 时按本节进入 hmon 向量（`CFXTRAP`，见 `§3`/`§4.4`）；`cfxha` 为未实现 cfx ⇒ `ILLI`（同步异常进 hmon 向量，见 `§4.4`）；`cfx_power`（cfx63）按 `DADAO-12 §5.2` 的通用 trap 规则处理。

### 4.2 `escape` → 异常退出流程

`escape` 指令完成异常退出：恢复 `excp_prev_run_mode`、递增 `escape_num`，并以 `escape` 的 `imms18`（指令字偏移）计算返回地址并跳转——所选帧为 `cg5` 同步异常帧时 `Addr = excp_cause_ip + (imms18 << 2)`，为 `cg9` 异步现场时 `Addr = async_cause_ip`（偏移恒 0）。[DADAO-12 §异常退出流程] 汇编层写 `escape cfxha, [excp_cause_ip, imms20]`，`imms20` 以字节为单位、合法值 **`{0, 4, 8}`**（`imms18 = imms20 >> 2 ∈ {0, 1, 2}`；`8` 选 `cg9` 现场、实际偏移 0，仅 `cfx_hart`）；编码层 `imms18[1]` 为帧选择位（0 = `cg5`、1 = `cg9`），`imms18[17:2]` 为 SBZ、`imms18 = 3` ⇒ `ILLI`（先于任何状态切换）。[SimRISC-11]

被调方通过 `escape cfxha, [excp_cause_ip, 4]` 返回 trap 指令的下一条指令（`excp_cause_ip + 4`）。[DADAO-22 §1. 调用约定]

- **`escape` 的目标 cfx 恒为当前 cfx；退出后当前 cfx 恢复为异常前的值**：`DADAO-12 §5.3` 原文为「`escape` 指令编码中指定了 `cfxha`，它必须是当前执行的核芯功能扩展（`inner_cfx_code`）；返回 cfx、运行模式与 IP 均取自当前 cfx 的异常帧」；其硬件语义（`§5.3` 步骤 0–3）在 `cfxha != inner_cfx_code` 时先报**当前 cfx** 的 `CFXESC`；通过后恢复 `global_cfx_intr_mask`、`excp_prev_run_mode` **与 `inner_cfx_code ← excp_prev_cfx_code`**（`cg5 rc1`，异常进入时保存，见 `§3.6`），递增 `escape_num` 并更新 `IP`。故 `escape` 的**目标**恒为当前 cfx（即发起 `escape` 的 cfx），而**退出后的当前 cfx** 恢复为异常发生前的值。任何帧内到达的异步事件会改写 `inner_cfx_code`，该恢复保证本帧后续 `escape` 仍能正确匹配目标。[DADAO-12 §5.3 异常退出流程]

### 4.3 两条路对照

| 路径 | 触发条件 | 处理 | 返回 |
|------|----------|------|------|
| **一般 trap** | `immu18 < 0x3FF00`（不在 `0x3FF00–0x3FFFF`） | 走 `DADAO-12 §5` 异常进入流程，**进入 cfx 向量** | 由被调方 `escape` 返回 |
| **semihosting** | `0x3FF00 ≤ immu18 ≤ 0x3FFFF`（`immu18[17:8] == 0x3FF`） | 实现层**译码短路**，**不进入向量**（同构 RISC-V `RISCV_EXCP_SEMIHOST`） | 直接 **IP 步进**返回（见 `§5`） |

一般 trap 与 semihosting 分离，**不得把 semihosting 混入向量路径**（否则实现者会误让 semihosting 进入向量）。`Kaiwu-Tiny` 的一般 trap 判定见 `§4.1`；`immu18` 的区间判定与 `cfxha` 无关（`§5.1`）。

### 4.4 同步异常进入 hmon（`Kaiwu-Tiny`）

`Kaiwu-Tiny` 运行模式恒为 `hypv`，故 `DADAO-12 §5.2` 的「当前运行模式 monitor」= `cfx3 hmon`：执行期同步异常不经 `trap` 指令、**直接进入 hmon 向量**，处理流程与现场寄存器（`excp_cause_id`/`excp_cause_ip`/`excp_cause_info`/`excp_prev_run_mode`）按 `DADAO-12 §5.2` 的异常进入流程。[DADAO-12 §5.2 异常进入流程]

- **五类同步异常与 `excp_cause`**（`excp_cause_id` = one-hot，位索引见 `§7.1`）：

| 名称 | `excp_cause_id` | 进入 hmon 的时机 / `excp_cause_info` |
|------|-----------------|--------------------------------------|
| `CFXMEM` | `1 << 1` | 核内地址空间非法访问/取指（`§1.2` 路由）时；`info` = 访存地址 |
| `ILLI` | `1 << 8` | 译码阶段遇到非法指令（含对未实现 cfx 的 `trap`/`escape`）时；`info` = 指令编码 |
| `UNDI` | `1 << 9` | 译码阶段遇到未定义指令时；`info` = 指令编码 |
| `MALIGN` | `1 << 12` | 地址计算后、访存前发现非对齐访存时；`info` = 访存地址 |
| `IALIGN` | `1 << 13` | 取指前检测 `IP[1:0] ≠ 00` 时；`info` = `IP` 值 |

- **`excp_cause_info` 的规定范围**：本册只规定上表 5 类（`CFXMEM`/`ILLI`/`UNDI`/`MALIGN`/`IALIGN`）的 `info`；其余异常原因（`CFXTRAP`/`CFXESC`/`CFXPERM`/`CFXREG`/`RASOF`/`RASUF`）的 `info` 按 `DADAO-12 §4.1`（`cfx_umon`/`jmon`/`smon`/`hmon` 同表），本册不另行规定；未规定者为 0。[DADAO-12 §4.1 cfx_umon - user monitor]
- **IALIGN 的 IP 停留语义**：`IALIGN` 为精确异常——**IP 停留在非法地址**，`excp_cause_ip` 记录该非法 `IP`，硬件**不写回下一条指令地址**；处理方式由 hmon 决定（与 `DADAO-12 §5` 的精确异常定义一致）。[DADAO-12 §5. 异常进入与异常退出]
- **进入目标**：目标 cfx = `cfx3 hmon`，`inner_inst_pointer <= cfx_hmon_hypv_excp_vector`；该向量初值 = hmon SRAM 起始 `0x0fff_0000_0000`（`§1.1`，`DADAO-12 §3.4` 规定有内部 SRAM 的 cfx 以该 SRAM 起始为初值）；hmon 入口显式写入同值属幂等，**不是**向量可用的前提；`excp_prev_run_mode` = `hypv`；模式切换**强制 `hypv`**（`cfx_hmon_hypv_switch_run_mode` 的写入被忽略、**寄存器保存值保持 `3`**，读回该保存值，见 `§2`）。[DADAO-12 §5.2 异常进入流程][DADAO-12 §3.4 cg3 - hypv mode 寄存器]
- **返回**：hmon 用 `escape cfx_hmon, [excp_cause_ip, 0]`（重试）或 `escape cfx_hmon, [excp_cause_ip, 4]`（跳过）返回（`§4.2`）；`IALIGN` 时 `excp_cause_ip` 即非法地址，是否重试/跳过由 hmon 软件决定。

---

## 5. semihosting

semihosting 是 v5 测试机提供的「guest 经 `trap` 请求宿主 I/O」机制；本节为其**规范正文**（服务号值语义取自 Arm Semihosting；v5 特有部分标测试机约定）。

- **两 profile 均提供 semihosting**。semihosting 判定只依赖 `immu18`（`§5.1`），与 `cfxha` 无关：`immu18 ∈ 0x3FF00–0x3FFFF` 时短路到宿主；只有非 semihosting 的 `trap` 才进入 cfx 向量。
- **`Kaiwu-Tiny`**：semihosting 统一写 `trap cfx_hmon`（`§5.1`；其它 `cfxha` 亦等效）；非 semihosting 的 `trap cfx_hmon` 进入 hmon 向量（`§4.4`），与 semihosting **无冲突**。Tiny 只用 semihosting 完成控制台与退出闭环（控制台/调试输出与 `SYS_EXIT`）；运行期同步异常由 hmon 处理（`§4.4`）。`Kaiwu-Vast` 同样以 semihosting 作宿主 I/O 与停机协议。

### 5.1 判定（入口 tag）

- **判定**：`trap cfxHA, immu18` 中 **`immu18[17:8] == 0x3FF`**（即 `0x3FF00–0x3FFFF`）⇒ 该 `trap` 为 **semihosting 调用**（**与 `cfxha` 无关**）。
- **调用形如 `trap cfx_hmon, 0x3FF00`**（两 profile 统一写法）：`immu18[17:8] == 0x3FF` 是 **semihosting 的固定标记**，`immu18[7:0]` **不**携带服务号；**服务号由 `rd16` 给出**（`§5.2`）、参数块指针在 `rb16`、返回值在 `rd8`；判定只依赖 `immu18[17:8]`，与 `cfxha` 无关——任意 `cfxha` 等效（如 Tiny 的 `trap cfx63, 0x3FF00` 同样按 semihosting 处理）。
- **语义/理由说明（架构自定义）**：该 tag 判定**无上游 spec 依据、属 v5 架构自定义**——`spec/DADAO-22` 只规定 `cfxha` 为服务提供者、`immu18` 为功能编号；`spec/SimRISC-11` 只规定 `immu18` 为功能编号；二者**均无 semihosting 语义**。故本机制在 v5 中由测试机定义，guest/实现共同遵守此 tag。[DADAO-22 §1. 调用约定][SimRISC-11]
- **两条路**：`immu18[17:8] == 0x3FF`（`0x3FF00–0x3FFFF`）走 semihosting 短路（本节）；`immu18 < 0x3FF00` 走一般 trap 进入向量（见 `§4.1`）——`Kaiwu-Tiny` 的启动移交目标为 `cfx_hmon`（`cfxha=3`），`cfxha` 为未实现 cfx ⇒ `ILLI`（见 `§3`/`§4.4`）。

### 5.2 调用约定（传参/返回寄存器）

v5 semihosting 为**恒 64 位**、**大端**。寄存器映射如下：

| 角色 | v5 寄存器 | 说明 |
|------|-----------|------|
| **操作号（标量）** | `rd16`（= `rda0`） | 服务号（见 `§5.3`） |
| **参数块指针（地址）** | `rb16`（= `rba0`） | 指向 64 位字段组成的参数块 |
| **返回值** | `rd8` | 标量返回；指针返回才用 `rb8`，semihosting 不用 |

- 号 → `rd16`、参数块指针 → `rb16`、返回 → `rd8`；对齐共享层 `common_semi_arg(cs,0)`=号、`common_semi_arg(cs,1)`=参数块指针。
- **指针一律为物理地址（PA）**：`rb16` 的参数块指针，以及 `SYS_WRITEC`（字符指针）/`SYS_WRITE0`（字符串指针）由参数寄存器直接给出的指针，**都是物理地址**，**不经页表翻译**；`§5.3` 服务表中其它「指针」字段同此口径。（测试机约定；用户 2026-11-15 裁定）
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
- **迁移范围 = 全部**：所有依赖 exit port 的向量/harness 已迁 `SYS_EXIT`；exit-port MMIO 设备已于 C1 step2 删除——机器模型不再保留 exit port。

### 5.6 已知风险（`SYS_SYSTEM`）

`SYS_SYSTEM`（`0x12`，执行宿主命令）为**已登记的已知安全风险**：命令在宿主上执行，可能产生非预期后果；v5 **不因此拒绝该服务**（服务集 = 完整 25 个），而以默认 `gdb`/沙箱、`native` 显式开启作为缓解手段。

---

## 6. 加载与 bootrom

M5 的 QEMU 提供**新 bootrom**（固件），用于**初始权限/向量配置**；bootrom 用**自有工具链**编译（LLVM 新指令的首个真实用户）。

- **BootROM（按 profile）**：`Kaiwu-Tiny` 为 64 KiB（`0xffff_ffff_0000`–`0xffff_ffff_ffff`），内容是**固定启动固件镜像**——power 启动 stub、hmon 运行段、image index table 三段（布局与容量见 `§6.2`）；**hmon 的代码/数据编入该镜像**，宿主不下发 hmon 段。`Kaiwu-Vast` 为 4 MiB（`0xffff_ffc0_0000`–`0xffff_ffff_ffff`），偏移 0 放 image index table、其后放 ELF 镜像，末 64 KiB（`0xffff_ffff_0000` 起）留给复位/启动代码。复位向量两 profile 均为 `0xffff_ffff_0000`。[DADAO-12 §2.1 核内地址空间]
- **装载语义 — `Kaiwu-Tiny`**：镜像 = **固定 BootROM 固件 + 应用**两件。固件经 `bootrom-image`（或 legacy `-bios`）原样装入 `0xffff_ffff_0000`，**恰好 64 KiB**；应用（raw 或 ELF）**只装 SRAM**：`.text` 起 `0xffff_ff01_0100`，raw 镜像基址 `0xffff_ff01_0000`（镜像前 `0x100` 字节须全零，保留区），`.bss` 由 picolibc `__start` 在 SRAM 清零。**`crt`（启动代码）与测试程序一起链接成同一个应用 ELF，整体落在 SRAM**（BootROM 内不含 crt）；入口 **raw 与 ELF 统一 `0xffff_ff01_0100`**（即 crt 入口）、`SP = 0xffff_ff7e_ff00`（由 crt 在入口设置）；power stub 在 hmon 移交返回后跳到该固定入口（`§6.2`）。**宿主 loader 不得向 BootROM 或 hmon SRAM 下发 `PT_LOAD`**（前者会覆盖固件、后者会预置 hmon），`e_entry` 不等于固定入口亦属装载错误；两者均须**显式失败**，不得静默忽略。Tiny 无 PTW/页表。
- **装载语义 — `Kaiwu-Vast`**：4 MiB BootROM 经 bootrom 镜像装载路径（机器属性 `bootrom-image`）装入；`power` 从 BootROM 把 hmon 装入 hmon SRAM，`power → hmon → smon` 交接后由 smon 建立**首张页表**并开启 PTW（`PTBR` = 页表页 PA、`ptw_enable = 1`）：该表覆盖内核窗口基址起的前 512 MiB（`VA [0x0200_0000_0000, 0x0200_2000_0000) → PA [0, 0x2000_0000)`，`VA = PA + 2 TiB`，含 `§6.3` 所需的前 96 MiB），窗口内其余区间不映射、由内核按需扩展。页表格式与地址转换按 `DADAO-12 §2.2`。本册只规定该首张页表，不规定**测试镜像**的段布局、起始执行位置或 SP；**内核镜像**的装载路径（VA）、内存窗口分区、boot info 与进入时状态见 `§6.3`。
- **legacy `-bios` 路径**：仍按 64 KiB 复位窗口（`0xffff_ffff_0000` 起）装载；Tiny 下它与 `bootrom-image` 装载的是**同一固定固件镜像**（应用走 `-kernel` 的 SRAM 段），不再携带应用专用 ROM trampoline。
- **模式移交**：`Kaiwu-Tiny` 运行模式始终为 `hypv`，但存在 `power → hmon → 测试本体` 的 cfx/启动移交（同 `§2`）；`Kaiwu-Vast` 为 power → hmon → 测试本体（hypv），`power → hmon → smon` 路径保留（同 `§2`）。
- **并存关系**：`-bios`/`bootrom-image` 固件启动路径与 ELF 单镜像路径**并存、非替代**——两条启动路径各自可自动化（Tiny 的 ELF 路径同样需要固件镜像，见上）。

### 6.1 image index table（两 profile 共用格式）

BootROM 镜像的段表两 profile **同格式、大端**（DADAO 为大端）；表在镜像内的固定偏移按 profile 规定（`Kaiwu-Vast` 偏移 0；`Kaiwu-Tiny` 见 `§6.2`）。

**表头（16 字节）**

| 偏移 | 宽度 | 字段 | 规定 |
|------|------|------|------|
| 0 | 4 | `magic` | `0x4442_4F54`（`DBOT`） |
| 4 | 2 | `version` | `1` |
| 6 | 2 | `count` | 表项数（Tiny = 1，Vast = 2） |
| 8 | 4 | `boot_magic` | power 移交 hmon 的 `trap cfx_hmon` 立即数 `immu18`（两 profile 均为 `0x30001`） |
| 12 | 4 | `reserved` | `0` |

**表项（32 字节 × `count`，自偏移 16 起，按 `type` 升序）**

| 偏移 | 宽度 | 字段 | 规定 |
|------|------|------|------|
| 0 | 4 | `type` | `1` = hmon，`2` = smon |
| 4 | 4 | `flags` | `bit0` = 必需段（缺失即启动失败）、`bit1` = 装入（1 = 复制到目标，0 = 只校验）、`bit2` = 结构校验（1 = 校验 ELF 头/程序头/段边界）；`bit31:3` 必须为 0 |
| 8 | 8 | `offset` | payload 在镜像内的偏移，16 字节对齐且落在 BootROM 内 |
| 16 | 8 | `size` | payload 字节数，8 字节对齐 |
| 24 | 8 | `reserved` | `0` |

- **payload 形态与目标地址**：`Kaiwu-Vast` 的表项是 **ELF 镜像**（power 校验 ELF 头并按 `PT_LOAD` 装入、BSS 清零，目标地址由 ELF 给出）；`Kaiwu-Tiny` 的表项是**扁平分段**（无 ELF 头，按 `offset`/`size` 整段复制到固定目标，见 `§6.2`）。
- **失败语义**：表头/表项校验失败（`magic`/`version`/`count`/`reserved` 不符、`type`/`flags` 非法、`offset`/`size` 越界或未对齐）⇒ power **停在 BootROM 的 park 循环**（不进入 hmon、不静默继续）；构建器对同一条件报错并以**非零**退出。

### 6.2 `Kaiwu-Tiny` 的 hmon 装载契约

**镜像布局（64 KiB，偏移 0 即复位向量）**

| 镜像偏移 | 内容 | 规定 |
|----------|------|------|
| `0x0000`–`0x1FFF` | power 启动 stub（扁平分段，链接在复位向量 `0xffff_ffff_0000`） | **上限 8 KiB**；偏移 0 即复位指令 |
| `0x2000`–`0x3FFF` | hmon 运行段（扁平分段，链接在 `0x0fff_0000_0000`） | **上限 8 KiB**；段首即 hmon 入口（= hmon SRAM 起始） |
| `0x4000`–`0xDFFF` | **保留区** | 必须全零；不装入、不执行 |
| `0xE000`–`0xFFFF` | image index table（`§6.1` 格式，`count = 1`、`type = 1`） | **8 KiB**；表项指向 hmon 段；未用字节为 0 |

**power 的装载与移交顺序**

1. 校验表头与 hmon 表项（`§6.1` 失败语义），取 `offset`/`size`/`flags`；
2. **逐 8 字节**把 hmon 段从 BootROM 复制到 hmon SRAM：目标 `0x0fff_0000_0000`，长度 = `size`；`offset`、`size` 均 8 字节对齐（构建器补零），复制使用 8 字节对齐的 `ld`/`st`（不做非对齐访问）；
3. **写后取指的可见性（实现义务，不新增指令语义）**：power 须保证该批写入在 hmon 首次取指前对同一 hart 可见——Tiny 无 cache 时自然满足；有 I-cache 的实现须在跳转前自行处理（本机约定：这是启动期一次性写入，不属自修改代码路径）；
4. 写 `cfx_hmon_hypv_excp_vector = 0x0fff_0000_0000`；该寄存器初值已等于 hmon SRAM 起始（`DADAO-12 §3.4`），此步幂等、可省；
5. 写 `cfx_hmon_hypv_switch_run_mode`（Tiny 下写入被忽略、保存值保持 `3`，见 `§2`）；
6. `trap cfx_hmon, <boot_magic>`（= 表头 `boot_magic`）按 `DADAO-12 §5.2` 的 `CFXTRAP` 进入 hmon 向量；
7. hmon 入口校验 `CFXTRAP` 与 magic、按需配置权限，`escape cfx_hmon, [excp_cause_ip, 4]` 返回 power stub（`§4.2`；`escape` 退出后 `inner_cfx_code` 恢复为异常进入前的值，即 `cfx_power`）；
8. power 跳固定应用入口 `0xffff_ff01_0100`，不返回。

**复制目标与长度上限**：目标固定为 hmon SRAM 起始 `0x0fff_0000_0000`；单段长度上限 = **8 KiB**（镜像预算；hmon SRAM 本身 64 KiB，故 SRAM 不是约束）。表项须满足 `size ≤ 56 KiB`、`offset + size` 落在 BootROM 内且两值 8 字节对齐，否则**构建期失败**、power 运行时按 `§6.1` 失败语义 park（不截断、不静默继续）。hmon SRAM 未被表项覆盖的字节为 0（宿主不预置）。

**容量结论（64 KiB 是否够用）**：够用——预算为 power ≤ 8 KiB + hmon ≤ 8 KiB + 保留区 40 KiB + 表 8 KiB = 64 KiB；**hmon 上限 8 KiB 是校验阈值（超限即构建失败），不是目标尺寸**——最小 handler 预计 1–3 KiB。超限的处置顺序：① 把 hmon 拆成多个表项（逐段复制，消除段间空洞）；② 仍不足则增大 BootROM 尺寸——这会改动 profile 几何、`cg7` BootROM 块与 64 KiB `-bios` 复位窗口惯例，属**平台决策**，本册不单方面改。构建器须以链接断言/构建期检查强制上述上限，超限即构建失败。

**QEMU 先行验证接口（实现顺序约定）**：先在 QEMU 落地并用同一镜像跑通 `power → hmon → 应用`，gem5 / chipyard 复用**同一 BootROM 镜像与同一张表**（不各写一套）。QEMU 侧需要先具备的行为与字段：

1. `bootrom-image` 机器属性对 **Tiny 也生效**：镜像恰好 64 KiB、原样装入 `0xffff_ffff_0000`，复位 `IP` 保持 `0xffff_ffff_0000`（不按应用 `e_entry` 改写）；
2. `-kernel`（raw 或 ELF）只接受 SRAM 段：`PT_LOAD` 落在 BootROM 或 hmon SRAM ⇒ 报错退出；raw 基址 `0xffff_ff01_0000`、前 `0x100` 字节保留；
3. `e_entry` 必须等于 `0xffff_ff01_0100`，否则报错退出；
4. hmon SRAM 复位为 0 且**对 CPU 可写**（power 复制路径可用），宿主不向该段装任何内容；
5. **不需要**解析段表——表由 BootROM 内的 power 固件解析；QEMU 只负责原样装入固件与上述装载检查。

### 6.3 `Kaiwu-Vast` 内核装载与启动 ABI

本节冻结 **K0 内核在 `Kaiwu-Vast` 上如何被装载、进入内核时看到什么**，即该 profile 的**启动 ABI**：地址术语、启动模型、装载路径与校验规则、内存窗口分区、固定 boot info 结构、进入时状态。装载的**执行**（宿主写内存与 boot info、装 initramfs、把 `rb16`/`rb17` 交给 smon）属实现层，不在本节。[spec-decision]（用户 2026-11-13 确认：按提案冻结）

**地址术语（本节硬约定）**：ABI 中的地址**一律是 VA**——48 位核内地址里分区键 `addr[47:42] = 0` 的内存窗口（`§1`），即 **`addr[41:0]`**（42 位有效）。**PA 只出现在三处**：页表项、`PTBR`（= `PPN << 16`，指出首张页表根的 PA）、宿主 loader 把数据写进内存的那一刻（写到该 VA 映射到的 PA）。入口地址、`rb16`/`rb17`、boot info 的地址字段、`kernel_base`、内核镜像区、initramfs 区与栈指针都按 **VA** 记。[spec-decision]（用户 2026-11-13 裁定：VA 为 ABI 地址）

**内核窗口偏置（本节硬约定）**：内核 VA 窗口内 `VA = PA + 2 TiB`（固定偏置）——内核空间**不从 0 开始**，用户空间独占低端 `[0, 2 TiB)`；`PTBR` 与页表项仍按 PA 记。[spec-decision]（用户 2026-11-13 裁定：内核空间 `[2 TiB, 3 TiB)`、四项冻结地址整体 +2 TiB）

**启动模型（预建页表 + VA 入口）**：进入内核**之前**页表已**预建**——smon 预建首张页表并开启 PTW（`PTBR` 指向该表、`ptw_enable = 1`），映射 `VA [0x0200_0000_0000, 0x0200_2000_0000) → PA [0, 0x2000_0000)`（覆盖内核窗口基址起的前 512 MiB，含本节所需的全部固定分区）；随后以 `rb16` 的 VA 入口进入内核。页表格式与地址转换按 `DADAO-12 §2.2`。页表**只由启动固件 `smon` 建立**（`§6`：`power → hmon → smon` 交接中建立首张页表并开启 PTW）；**宿主 loader 只把镜像装到对应 PA，不代写页表页**。M1 **不存在**「先关 MMU 跑一段再开」的中间态。[spec-decision]（用户 2026-11-13 裁定：M1 预建页表 + VA 入口）

**硬约束（为何必须 PTW 已开）**：DADAO 在 `ptw_enable = 0` 时对内存窗口（`addr[47:42] = 0`）的取指/访存**直接报 `CFXMEM`**（`§1.2`）——内核不可能在 MMU 关的状态下从 RAM 取指或访存。因此进入内核时 `ptw_enable` 必须为 `1`。[spec-decision]

`Kaiwu-Tiny` 不适用本节（其装载规则见 `§6.2`）。本节与 `§1.1`/`§2`/`§6` 的既有 profile 几何与启动链条款**并存**（`§6` 的 Vast 首张页表按本节的 `+2 TiB` 偏置同步，不改变「`smon` 建表、`PTBR = 0`」归属），其它语义不变。

#### 6.3.1 内存窗口分区

Vast 的内存窗口为 `VA [0, 4 TiB)`（`addr[47:42] = 0`、`VA = addr[41:0]`，见 `§1`），按用途划分为：**用户 VA 空间 `[0, 2 TiB)`**、**内核 VA 窗口 `[2 TiB, 3 TiB)`** = `[0x0200_0000_0000, 0x0300_0000_0000)`；`[3 TiB, 4 TiB)` 本节不定义。内核窗口内 `VA = PA + 2 TiB`。内核装载与运行期占用窗口内四段**固定 VA 分区**（页表页 / boot info 页 / 内核镜像区 / initramfs 区），其余归内核页分配器。[spec-decision]（用户 2026-11-13 裁定）

| 区间（VA） | 大小 | 用途 |
|------|------|------|
| `[0x0200_0000_0000, 0x0200_0001_0000)` | 64 KiB | 首张页表页（`PTBR = 0`（PA）；由固件在移交前建立，见 `§6`） |
| `[0x0200_0001_0000, 0x0200_0002_0000)` | 64 KiB | boot info 页（固定 VA `0x0200_0001_0000`；其余字节为 0） |
| `[0x0200_0010_0000, 0x0200_0400_0000)` | 63 MiB | 内核镜像区（`kernel_base = 0x0200_0010_0000`，VA） |
| `[0x0200_0400_0000, 0x0200_0600_0000)` | 32 MiB | initramfs 区（上限 32 MiB，VA） |
| 其余 | — | 内核 VA 窗口内其余区间归内核页分配器 |

- 首张页表页与 boot info 页合占窗口内的**启动保留区** `[0x0200_0000_0000, 0x0200_0002_0000)`（PA 侧为 `[0, 0x0002_0000)`）；建立页表时**不得**覆盖 boot info 页（`§6`）。[spec-decision]
- 启动保留区 `[0x0200_0000_0000, 0x0200_0002_0000)` 与 initramfs 区在内核接管后**须保留**，不得被页分配器回收或复用。[spec-decision]

#### 6.3.2 内核装载

内核镜像有 **ELF** 与 **raw（loadmem）** 两条装载路径，**语义等价**：同一份内核源码经两条路径装载后，进入状态（`§6.3.4`）相同。[spec-decision]

**地址与装载（两条路径共用）**：ELF 的 `p_vaddr` 与 raw 镜像基址都是 **VA**；loader 把每段写到该 VA 在首张页表里映射到的 **PA**（不读 `p_paddr`）。内核窗口内 `VA = PA + 2 TiB`（故目标 PA = `p_vaddr - 2 TiB`），两者是不同术语，实现不得混用。[spec-decision]

**ELF 路径**（7 条校验；任一不符 ⇒ 装载失败，见本节末「失败语义」）：

- **`ELF-FORMAT`**：`ELFCLASS64`、大端（`EI_DATA = 2`）、`e_machine = 0x0DA0`、`ET_EXEC`；`e_flags` 版本字段 = 1（按 `contract-elf` `§1.3`）。[spec-decision]
- **`ELF-PT-LOAD`**：只装载 `PT_LOAD` 段，其它类型的程序头段不装入。[spec-decision]
- **`ELF-VA-TO-PA`**：每段按 `p_vaddr` 的映射写入对应 PA（`VA = PA + 2 TiB` ⇒ 目标 PA = `p_vaddr - 2 TiB`）；`p_paddr` 不作为装载地址。[spec-decision]
- **`ELF-ALIGN`**：每段 `p_vaddr % 0x10000 == 0` 且 `p_align >= 0x10000`（64 KiB 页对齐）。[DADAO-12 §2.2 虚实地址转换]
- **`ELF-RANGE`**：每段 `[p_vaddr, p_vaddr + p_memsz)` 落在内核镜像区的 VA 范围 `[0x0200_0010_0000, 0x0200_0400_0000)` 内。[spec-decision]
- **`ELF-NO-OVERLAP`**：任何段不得与启动保留区 VA `[0x0200_0000_0000, 0x0200_0002_0000)`、BootROM 或 hmon SRAM 的映射区间重叠。[spec-decision]
- **`ELF-ENTRY`**：`e_entry == 0x0200_0010_0000`（VA，= `kernel_base`）。[spec-decision]

`p_filesz` 字节取自文件，`p_memsz - p_filesz` 由 loader **零填充**（`.bss`）。[contract-elf §6.1.2]

**raw（loadmem）路径**（扁平镜像，4 条规则）：

- **`RAW-BASE`**：整体装入 VA `0x0200_0010_0000`（= `kernel_base`）。[spec-decision]
- **`RAW-ENTRY`**：镜像首字节即入口指令（VA 入口 `0x0200_0010_0000`），loader 不解析 ELF 头。[spec-decision]
- **`RAW-LENGTH`**：镜像长度 ≤ 63 MiB（内核镜像区容量）。[spec-decision]
- **`RAW-BSS`**：扁平镜像**不含** `.bss`；内核 `head.S` 须在进入 C 代码前自行把 `__bss_start..__bss_stop` 清零，行为与 ELF 路径的 loader 零填充等价。[spec-decision]

**initramfs**（3 条规则）：

- **`INITRAMFS-FORMAT`**：`cpio`「newc」格式。[spec-decision]
- **`INITRAMFS-BASE`**：装入 VA `0x0200_0400_0000`（= `initramfs_base`）。[spec-decision]
- **`INITRAMFS-LIMIT`**：长度 ≤ 32 MiB；实际字节数写入 boot info 的 `initramfs_size`（`0` ⇒ 无 initramfs）。[spec-decision]

**失败语义**（host/loader 层，不是 guest fault）：

- **`FAIL-HOST`**：任一校验失败（格式/端序/机器号/`ET_EXEC`、`e_entry` 不符、段越界或重叠、`p_vaddr` 未按页对齐、对齐不足、initramfs 超限、boot info 无法写入）⇒ loader **非零退出**；不得静默降级、截断或改址装载。[spec-decision]
- **`FAIL-KERNEL`**：boot info 的 `magic`/`version`/`size` 任一不符 ⇒ 内核 `head.S` **显式失败**（semihosting `SYS_EXIT` + 固定失败码；码值属实现，本册不规定），不得猜测或继续（停机协议见 `§5.5`）。[spec-decision]

#### 6.3.3 固定 boot info 结构

boot info 位于内核 VA 窗口的 **VA** `0x0200_0001_0000`（PA 侧 = VA − 2 TiB），总长 `size = 0x60` 字节；全部多字节字段**大端**，8 字节字段自然对齐；页内偏移 `0x60` 之后至该页末（页内偏移 `0x1_0000`）为 0。表中地址字段均为 **VA**，唯一例外是 `ptbr`——它是首张页表根的 **PA**（`PPN << 16`，K0 为 `0`）。[spec-decision]

| 偏移 | 宽度 | 字段 | 值 | 语义 |
|------|------|------|----|------|
| `0x00` | 4 | `magic` | `0x4442_494E` | ASCII `DBIN` |
| `0x04` | 2 | `version` | `1` | 内核只接受 `1`；不匹配须显式失败 |
| `0x06` | 2 | `size` | `0x0060` | 总字节数；更大 ⇒ 忽略尾部未知字段 |
| `0x08` | 8 | `ram_base` | `0x0200_0000_0000` | 内存窗口基址（VA；内核窗口起点） |
| `0x10` | 8 | `ram_size` | `0x8000_0000` | 内存窗口大小（2 GiB） |
| `0x18` | 8 | `kernel_base` | `0x0200_0010_0000` | = `e_entry` / raw 首字节地址（VA） |
| `0x20` | 8 | `kernel_size` | 运行期 | 装载镜像字节数：ELF = `max(p_vaddr + p_memsz) - kernel_base`；raw = 文件字节数 |
| `0x28` | 8 | `initramfs_base` | `0x0200_0400_0000` | initramfs 装入地址（VA） |
| `0x30` | 8 | `initramfs_size` | 运行期 | 实际字节数（`0` ⇒ 无 initramfs） |
| `0x38` | 8 | `cmdline_base` | `0` | K0 无命令行，保留字段（VA） |
| `0x40` | 8 | `cmdline_size` | `0` | K0 无命令行，保留字段 |
| `0x48` | 8 | `ptbr` | `0` | 首张页表根 PA（`PPN << 16`；低 16 位为 0） |
| `0x50` | 4 | `page_size_log2` | `16` | 64 KiB 页（`2^16` 字节） |
| `0x54` | 4 | `hart_id` | `0` | K0 单核 |
| `0x58` | 8 | `flags` | `0x1` | `bit0 = 1`：semihosting 控制台可用；其余位 0，内核须忽略未知位 |

- **写入方与保护**：boot info 由**宿主 loader** 在移交前写入；`power`/`hmon`/`smon` **只读**、不得改写，建立页表时不得覆盖 boot info 页。[spec-decision]
- `kernel_size` 只覆盖装载镜像；内核自身用链接符号 `_end` 保留含 `.bss` 的完整占用。[spec-decision]

#### 6.3.4 进入时状态

进入状态指**内核第一条指令处**的状态（`IP` = 入口 VA `0x0200_0010_0000`）。[spec-decision]

| 项 | 值 |
|----|----|
| 运行模式 | `supv` |
| PTW | 开启（预建页表，`PTBR = 0`（PA），`ptw_enable = 1`，64 KiB 页，`VA [0x0200_0000_0000, 0x0200_2000_0000) → PA [0, 0x2000_0000)`，`VA = PA + 2 TiB`） |
| `rb17` | `0x0200_0001_0000`（boot info VA） |
| `rb16` | `0x0200_0010_0000`（入口 VA） |
| `rb1`（SP） | 未定义（内核自建 early stack，栈为 VA） |
| `rb3`（rbtp） | `0` |
| `rd15` 与其它通用寄存器 | 未定义 |
| 异步中断 | 全部屏蔽 |
| hart | 仅 `hart_id = 0` 在线；其它 hart 状态未定义（K0 不启动、不得依赖） |
| cache / LLC | 不引入、不假设一致性 |

- 启动链沿用 `§2`/`§6` 的 `power → hmon → smon`：smon 建立首张页表并开启 PTW 后，按 `DADAO-23` 的移交流程 `escape cfx_smon, [excp_cause_ip, 0]` 进入内核的 VA 入口（`rb16`）。[DADAO-23 §3 启动与引导移交约定]
- `rb17` 与 `DADAO-23` 的「设备树地址」**同位**，但本机**不引入 DTB**：`rb17` 承载 boot info 的 VA，内核**不得按 DTB 解析**。[DADAO-23 §3 启动与引导移交约定][spec-decision]
- `rb1`（SP）未定义 ⇒ 内核 `head.S` 须在任何栈使用前自建 early stack（栈指针按 VA）；`rd15` 与其它通用寄存器不得依赖。[spec-decision]
- **其它 hart**：K0 只有 `hart_id = 0` 在线，其余 hart 的状态**未定义**（实现可保持停止或不复位）；内核不得等待、唤醒或依赖它们，SMP 启动与停核协议不在本册。[spec-decision]

#### 6.3.5 不定义范围

本节**不定义**：cache/LLC、设备树（DTB）、UART、多核启动与 SMP 停核协议、MMU 关运行（`ptw_enable = 0` 时内核无法从 RAM 取指/访存，见本节开头）、用户 VA 空间 `[0, 2 TiB)` 的布局与用户态映射、`[3 TiB, 4 TiB)` 的用途、内核窗口内固定分区之外（`+512 MiB` 以上）的映射扩展；这些本节不引入。[spec-decision]

- **TLB**：TLB 的匹配键、命中检查、填充条件、A/D 维护与失效接口**不在本节定义**，按 `DADAO-12 §2.2.1–§2.2.6`、`§4.5` 与 `§3.1` 执行；内核无需在本节的启动 ABI 之外另立 TLB 契约。[DADAO-12 §2.2.5 操作系统页管理][DADAO-12 §4.5 cfx_ptw - page table walker][spec-decision]

---

## 7. 退出

- v5 测试机的程序停机协议为 semihosting **`SYS_EXIT`/`SYS_EXIT_EXTENDED`**（见 `§5.5`），**取代** exit port。
- exit-port MMIO 设备已在 C1 step2 **随旧 RAM 段一并删除**。

### 7.1 退出码（测试机约定）

- **本节只定编码**：约束退出码的**分段、位域与语义映射**；退出码的**产生方**（异常 handler、宿主 loader、运行时或其它组件）属**实现设计**，本册不规定、也不据此限定实现结构。
- **完整退出码表（测试机约定）**：`$?` 单值区分 guest pass/fail 与机器 fault；机器 fault 按编码分「其它 cfx」与「monitor」两段（段名只描述编码范围）。

| 范围 | 段 | 位域 | 含义 |
|------|----|------|------|
| `0x00` | guest | — | PASS |
| `0x01`–`0x7F` | guest | — | FAIL，值 = 失败点序号 1–127 |
| `0x80`–`0xBF` | 其它 cfx | `bit7=1, bit6=0, bit5:0=cfxHA` | 目标/当前 cfx 的同步异常退出码 |
| `0xC0`–`0xFF` | monitor | `bit7=1, bit6=1, bit5:4=运行模式, bit3:0=异常位索引` | 当前运行模式 monitor 的同步异常退出码 |

- **guest 段编码**：PASS 只有 `0x00` 一个值；FAIL 取 `0x01`–`0x7F`，值即**失败点序号**（1–127）——一个测试镜像内最多 127 个检查点，哪个检查点失败就报它的号。
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

- **`CFXTRAP`/`CFXESC` 的编码选择**：退出码表示 `CFXTRAP`（位索引 0）或 `CFXESC`（位索引 3）时，按「其它 cfx」段编码（`0x80`–`0xBF`，`bit7=1`、`bit6=0`、`bit5:0` = 对应 cfx 的 cfxHA），**不**按 monitor 段编码；monitor 表中的 0/3 仅保留位索引定义。
- **语义映射**：`bit5:4` 取运行模式编码、`bit3:0` 取 DADAO 异常位索引（见上表），二者组合即该退出码所指的「运行模式 + 异常原因」；异常原因与运行模式的归属由异常路由（`§1.2`/`§4.4`、`DADAO-12 §5.2`）定义，本节只约束编码。
- **`Kaiwu-Tiny` 的编码范围**：运行模式恒 `hypv` ⇒ monitor 段取 `bit5:4 = 11`（`0xF0`–`0xFF`）。
- **编码冻结、不得重排**：退出码分段与 monitor/其它 cfx 位域**自本版起**一经生效**不得重排**；monitor 位索引沿用 DADAO 异常位索引，新增原因不得改变既有索引。[DADAO-12 §5.2 异常进入流程]

---

## 附录：版本与变更记录

> **发布动作**：把顶部 `-rc` 段去 `-rc` 并补发布日期，再于其上方新开空 `-rc` 段。

### 0.4.7-rc（未发布）

- **`cfx5`（`cache`）由「已分配未实现」改为 `Kaiwu-Vast` 实现**（用户 2026-11-20 确认 `cfx5` 由 Vast 实现、Tiny 不实现）：Vast 实现其寄存器（`cache_exist` 按 §4.6 位定义 I/D 两侧均存在 ⇒ 读回 `0b11`、`cache_enable`、`cache_ctrl`、`cache_addr_start`、`cache_addr_size`）与维护命令；`Kaiwu-Tiny` 仍不实现（⇒ `CFXREG`/`ILLI`）。新增 `§3.2 cache（cfx5）的测试机约定`：维护命令同步完成、per-hart、`ctrl[15:14]` 的 I/D 选择位（bit15 = I、bit14 = D）与两侧全选「先 I 后 D」；cache 几何由实现决定、本册不规定；`§3` 的实现范围条目同步。版本号不变（0.4.7-rc）。

- **测试机整机名定为 `Kaiwu`（开物），本册随之改名**（用户 2026-11-16 裁定）：册名 `Kaiwu-测试机运行环境.md`，正文整机名 `Kaiwu`、两机型 `Kaiwu-Tiny` / `Kaiwu-Vast`，QEMU 机器串 `kaiwu-tiny` / `kaiwu-vast`（不保留旧名别名）；两机型几何、复位地址、cfx 范围、异常/退出码与 semihosting 语义**逐字不变**，版本号不变。

- **内核 VA 窗口改为 `[2 TiB, 3 TiB)`**（用户 2026-11-13 裁定：内核空间不从 0 开始；用户空间 `[0, 2 TiB)`；渠道 = 主会话问答）：`§6.3` 的四段固定分区整体迁入内核窗口，窗口内 `VA = PA + 2 TiB`——首张页表页 VA `0x0200_0000_0000`（`PTBR` 仍为页表页 PA 0）、boot info VA `0x0200_0001_0000`（PA 侧不变）、内核镜像区 VA `[0x0200_0010_0000, 0x0200_0400_0000)`（`kernel_base` / `e_entry` / `raw` 基址同步）、initramfs 区 VA `[0x0200_0400_0000, 0x0200_0600_0000)`；boot info 的 `ram_base` 改记内核窗口起点（VA `0x0200_0000_0000`）。`§6` 的 Vast 首张页表由「全域 4 个 512 MiB 超页」改为「内核窗口基址段 1 个 512 MiB 超页」（`VA [0x0200_0000_0000, 0x0200_2000_0000) → PA [0, 0x2000_0000)`）；物理侧（PA RAM 2 GiB、内核镜像 PA 起点 0、boot info PA `0x1_0000`、页表页 PA 0）不变。`§6.3` 的启动模型改为「预建带偏置页表 + VA 入口」，不再是身份映射。

- **semihosting 指针语义固定为 PA**（用户 2026-11-15 裁定）：`§5.2` 明写参数块指针与 `SYS_WRITEC`/`SYS_WRITE0` 的指针一律为**物理地址、不经页表翻译**，`§5.3` 服务表的其它指针字段同此口径。

- **TLB 的 I/D 分表与命令作用域（用户 2026-11-20 确认）**：`§3.1` 增第四条——本机 TLB 为 I/D 两表（`DADAO-12 §4.5` 的「组织由实现决定」允许），`cfx_ptw_tlb_control` 不引入 I/D 选择位、一条命令作用于两表，判序 **I 表先、D 表后**，跨两表「条目级 + 首错即停、最多报一处失败」，`scope=VA`/`range` 对两表各自匹配；同时把首条「其余条目照常处理」订正为「其后条目一律不处理」（与 `contract-tlb` TLB-37 的遇错即停一致）。版本号不变（0.4.7-rc）。

- **TLB 排除项撤销 + 三条测试机约定**（用户 2026-11-16 确认）：`§6.3.5` 的排除项删去「TLB 填充/失效/ASID」，改为指向 `DADAO-12 §2.2.1–§2.2.6`、`§4.5`；新增 `§3.1`——`cfx_ptw_tlb_control` 的写指令**同步完成**（回写失败在该写指令上报 `CFXMEM`、按条目级不得部分完成）、TLB 与失效命令 **per-hart**（跨 hart 一致性不在本册范围）、TLB 建模由 QEMU 机器模型承担且 `tests/arch` 探针为跨实现判据。版本不变（0.4.7-rc）。

### 0.4.6（未发布，被 0.4.7-rc 取代；本段所列地址为旧值，已作废）

- **新增「`Kaiwu-Vast` 内核装载与启动 ABI」（`§6.3`）**：冻结内核镜像的 ELF / raw 两条装载路径与校验规则（ELF 7 条、raw 4 条、initramfs 3 条、失败语义 2 条）、内存窗口四段固定 VA 分区（页表页 / boot info 页 / 内核镜像区 / initramfs 区）、固定 boot info 结构（VA `0x0001_0000`、`size = 0x60`、大端、15 个字段）、进入内核时的状态（`supv`、PTW 开启、`rb17` = boot info VA、`rb16` = 入口 VA、SP 未定义、其它 hart 状态未定义）。**地址术语**：ABI 地址一律 VA（`addr[41:0]`），PA 只用于页表项、`PTBR` 与 loader 写内存的那一刻；`p_vaddr` 是 VA、由 loader 按映射写入对应 PA（K0 身份映射下数值相等）。**启动模型 = 预建页表 + VA 入口**：进入内核前身份映射页表已预建且 `ptw_enable = 1`（`ptw_enable = 0` 时访存/取指直接 `CFXMEM`，不存在 MMU 关运行）。明确本机**不引入设备树**：`rb17` 与 HBI 移交约定的「设备树地址」同位，但承载 boot info，内核不得按 DTB 解析。装载的执行（宿主写内存与 boot info、装 initramfs、交给 smon）不在本版规定。

### 0.4.5（未发布，被 0.4.6-rc 取代）

- **guest 退出码重新分段**：PASS 收窄为 `0x00` 一个值，FAIL 扩为 `0x01`–`0x7F`（值 = 失败点序号 1–127，一个测试镜像最多 127 个检查点）；`0x80`–`0xBF` 与 `0xC0`–`0xFF` 两段的编码、位域与 monitor 位索引逐字不变。理由：PASS 只需一个值，原 `0x01`–`0x3F` 无用途，而 FAIL 只 64 个点限制了单镜像的检查点数。

### 0.4.4（未发布，被 0.4.5-rc 取代）

- `crt` 与测试程序一起链接、整体落 SRAM（用户 2026-11-10）；BootROM 内不含 crt，入口 `0xffff_ff01_0100`。

- Tiny BootROM 布局按用户 2026-11-10 裁定重划：power stub 8 KiB（`0x0000–0x1FFF`）、hmon 段 8 KiB（`0x2000–0x3FFF`，**校验阈值非目标尺寸**）、保留区 40 KiB 全零（`0x4000–0xDFFF`）、image index table 8 KiB（`0xE000–0xFFFF`）。

- **Tiny hmon 装载契约**：hmon 的代码/数据**编入 BootROM 镜像**（power stub + hmon 运行段 + image index table，`§6.1`/`§6.2`）；power 把 hmon 段复制到 hmon SRAM 后 `trap` 移交。宿主 loader **不再下发 hmon 段**、也不再向 BootROM 装应用段——应用（raw/ELF）只装 SRAM，入口固定 `0xffff_ff01_0100`；表校验/装载失败即显式失败（park，不静默继续）。容量结论：64 KiB 预算 = power ≤ 4 KiB + hmon ≤ 56 KiB + 表 4 KiB，够用。QEMU 先行验证，gem5/chipyard 共用同一镜像与同一张表。
- **`cfx2rd`/`cfx2rc` 到不同 cfxha 的口径**：reserved cfxha ⇒ `ILLI`；已分配但未实现的 cfx、以及已实现 cfx 的未定义 cg/rc ⇒ `CFXREG`；两条为编号层/寄存器层判定，互斥不冲突（引 `DADAO-12 §5.1`、`§5.2（一）`）。
- **hmon 异常向量初值**：随 `DADAO-13` 改为「有内部 SRAM 的 cfx 以该 SRAM 起始为初值」；hmon 入口显式写入同值改为幂等、不再是向量可用的前提。
- **退出码只定编码**：`§7.1` 删去「落点/由谁产生」类表述，只保留编码表、位域与语义映射；分段、位域与 monitor 位索引逐字不变。

### 0.4.3（未发布，被 0.4.4-rc 取代）

- Tiny `switch_run_mode` 口径澄清（2026-11-10）：写入被忽略、**寄存器保存值保持 `3`**，读回为保存值（不是「读回恒 3」的常量语义）。

- **reserved cfx 集**：改为引用上游——保留 cfx 即 `DADAO-12 §1` 编号表中 `cfxname = reserved` 的编号（含 `per-task` 段中尚未分配的编号）；本册**不再列举编号**，以免与上游漂移。
- **`excp_cause_info` 覆盖面**：本册只规定 `CFXMEM`/`ILLI`/`UNDI`/`MALIGN`/`IALIGN` 五类的 `info`；其余原因按 `DADAO-12 §4.1`，未规定者为 0。
- **`escape` 返回 cfx**：`escape` 的**目标** cfx 恒为当前 cfx；异常帧保存 `excp_prev_cfx_code`（`cg5 rc1`，进入时保存），`escape` 退出后**当前 cfx 恢复为异常前的值**（引 `DADAO-12 §5.3` 原文与步骤 0–2）。
- **Tiny `cfx_power` 寄存器**：`cg7` 空间块 0 = BootROM（`start = BootROM 起始地址 − (63 << 42)`、`size` 按 profile、`attr = R|X`）；`cg8`/`rc1`（power ctrl）Tiny 未实现 ⇒ `CFXREG`。
- **Tiny `switch_run_mode`**：该寄存器写入被忽略（保存值保持 `3`，`hypv`），读回为寄存器保存值；异常进入强制 `hypv`，运行模式不变。

### 0.4.2（未发布，被 0.4.3-rc 取代）

- **Tiny 引入 `cfx_power` + `cfx3 hmon`**：Tiny 从「不实现任何 cfx」改为实现 `cfx_power`（cfx63，启动移交）与 `cfx3 hmon`（同步异常向量）；新增 hmon SRAM `0x0fff_0000_0000`（64 KiB，cfxha 3），`addr[47:42]` 不再恒 `0x3F`；仍无 PTW/页表、不实现 smon。
- **启动链与异常**：Tiny 启动链改为 `power → hmon → 测试本体`；hmon 启动时显式写入 `cfx_hmon_hypv_excp_vector = 0x0fff_0000_0000`（`DADAO-12 §3.4` 规定其初值由平台/实现定义，不依赖复位默认值；该初值口径已由 `0.4.4-rc` 改为「初值 = hmon SRAM 起始」）；`CFXMEM`/`ILLI`/`UNDI`/`MALIGN`/`IALIGN` 进 hmon 向量（`excp_cause` 见 `§4.4`），`IALIGN` 时 IP 停留在非法地址；删除「fault 直接映射退出码」口径。
- **semihosting**：`trap` 判定只依赖 `immu18`（`0x3FF00–0x3FFFF` 为 semihosting）；示例统一写 `trap cfx_hmon`，非 semihosting 的 `trap cfx_hmon` 进 hmon 向量。

### 0.4.1（未发布，被 0.4.2-rc 取代）

- **profile 与机器命名**：profile 概念 `Node` → `Vast`（`Kaiwu-Node` → `Kaiwu-Vast`），机器名 `dadao-m1` → `kaiwu-tiny` / `kaiwu-vast`（语义不变）。

### 0.4.0（2026-11-08）

**① 平台 profile：Tiny / Vast**

- **两个 profile**：`Kaiwu-Tiny` = BootROM 64 KiB + SRAM 8 MiB、无 cfx / 无 PTW / 无 hmon 与异常路径、`trap` 只作 semihosting 开关；`Kaiwu-Vast` = BootROM 4 MiB + PA RAM 2 GiB、hmon / PTW / hypv，smon 路径保留。两者复位地址均为 `0xffff_ffff_0000`。
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

- **`escape` 偏移合法集**：`{0, 4, 8}`（`imms18 ∈ {0, 1, 2}`；`8` = `cg9` 异步现场、偏移恒 0）；`imms18[17:2]` 为 SBZ，`imms18 = 3` ⇒ `ILLI`（§4.2）。

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
- **册名**：`Machine-01` → `Kaiwu`（标题同步为「`Kaiwu：测试机运行环境`」；正文语义不变）。

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
