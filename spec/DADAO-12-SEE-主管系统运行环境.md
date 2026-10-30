# DADAO Supervisor Execution Environment（SEE）

> **版本：0.7.3-rc**（与 SBI 版本号一致，同步更新。基于 SimRISC 0.5.5 指令系统设计）

本文档定义DADAO主管系统运行环境（Supervisor Execution Environment, SEE）的体系结构规范，涵盖地址空间组织、处理器资源管理、核芯功能扩展设计、外设资源抽象及运行模式定义等内容。

## 1. 运行模式与核芯功能扩展

DADAO定义了四种运行模式，用两位编码：

| 编码     | 模式     | 缩写 | 权限     | 说明         |
| ------ | ------ | ------ | ------ | ------     |
| 0b00   | 用户模式（U-mode） | user | 用户态    | 普通应用程序运行模式 |
| 0b01   | 监狱模式（J-mode） | jail | 用户态    | 受限应用程序运行模式 |
| 0b10   | 主管模式（S-mode） | supv | 特权态    | 主管系统运行模式   |
| 0b11   | 超管模式（H-mode） | hypv | 特权态    | 超管系统运行模式   |

处理器核芯主要负责指令执行，所有资源管理划归到某个核芯功能扩展（Core Feature eXtension，简称 `cfx`）中进行，最多支持 64 个核芯功能扩展，外设资源及IO空间亦通过 `cfx` 进行统一管理。

| cfxha | cfxname | 说明 |
|:---:|------|------|
| 0 | umon | 处理 user 模式下的同步异常 |
| 1 | jmon | 处理 jail 模式下的同步异常 |
| 2 | smon | 处理 supv 模式下的同步异常 |
| 3 | hmon | 处理 hypv 模式下的同步异常 |
| 4 | ptw | 页表步进，管理页表与 TLB |
| 5 | cache | Cache 管理 |
| 6-14 | reserved | 保留，未定义 |
| 15 | hart | Hart 管理和本地计数 |
| 16 | llc | 最后一级缓存，跨 hart 共享 |
| 17 | pmem | 物理存储器管理 |
| 18 | time | 全局时间计数器 |
| 19-61 | reserved | 保留，未定义 |
| 62 | uart | 串口控制器 |
| 63 | power | 电源管理 |

每个核芯功能扩展提供自己特有的功能调用，并负责响应和处理所管理设备的中断，因此，异常的进入和退出也都隶属于某个核芯功能扩展：

- 指令执行过程中，核芯触发的同步异常，根据指令执行时的运行模式，分别由 `cfx_umon`/`cfx_jmon`/`cfx_smon`/`cfx_hmon` 进行异常处理
- 地址转换过程中，地址转换部件触发的异常（页表步进与 TLB 命中），均由 `cfx_ptw` 进行异常处理
- 外部设备触发的异常，根据中断源，分别由相应的核芯功能扩展进行处理

多核系统中各资源的作用域：

| 资源 | 作用域 |
|------|:--:|
| rd/rb/rf/ra、inner_* | per-hart |
| cfx0-cfx15 | per-hart |
| cfx16-cfx63 | per-system |

> `inner_*` 为硬件内部寄存器（不对外暴露），用于异常处理流程中的中间状态保存。`inner_run_mode`（2 位）记录当前运行模式（0=user, 1=jail, 2=supv, 3=hypv），`inner_cfx_mask`（64 位，per-hart）和 `inner_excp_cause_*` 等用于异常屏蔽判断与现场保存。详细语义见 §异常进入流程。

## 2. 地址空间

CPU 地址固定为 48 位。高 6 位 `addr[47:42]` 是地址空间分区键：`0` 为内存窗口，`1..63` 为 cfx 1–63 的核内地址空间。内存窗口的虚拟地址（VA）为 42 位（`VA[41:0]`，高 6 位固定 0）；物理地址（PA）为 56 位。CPU 地址与物理地址是两个不同的地址空间：内存窗口不直通物理存储器，必须经页表转换；cfx 核内地址也不等同于物理地址。

`ptw_enable` 控制内存窗口是否翻译：`0` 时不翻译，`addr[47:42] = 0` 的访存触发 CFXMEM；`1` 时按页表转换。cfx 核内地址（`addr[47:42] = 1..63`）直接 `ld/st`，不经 `ptw_enable`。

### 2.1 核内地址空间

48 位核内地址的高 6 位（`addr[47:42]`）指定了核芯功能扩展编号（cfxha）。`addr[47:42] = 0` 的地址属于内存窗口（见 §2.2），不属于任何 cfx 的内部空间；因此 `cfx0`（umon）没有内部地址空间。`cfx1`–`cfx63` 的内部空间各为 42 位（`addr[41:0]`）。

已分配的核内地址空间如下：

| cfx num | cfx name | 起始地址 | 地址大小 | 空间类型 |
|:---:|------|------|------|------|
| 3 | hmon | `0x0fff_0000_0000` | 64 KiB | SRAM |
| 17 | pmem | `0x47ff_0000_0000` | 64 KiB | SRAM |
| 63 | power | `0xffff_ffff_0000` | 64 KiB | BootROM |

说明：

- cfx_power_hypv_excp_vector 为硬件复位后的启动地址，这部分地址空间可由 CPU 直接取指并执行
- 对核内地址空间进行非法访问时，会触发对应核芯功能扩展的 CFXMEM 异常。核芯功能扩展由地址高 6 位 `addr[47:42]`（即 cfxha）确定。
- 保留 cfx（6–14、19–61）的普通 `ld/st` 触发 CFXMEM；`trap`/`escape` 到保留 cfx 触发 ILLI。
- cfxha 5 为 `cfx_cache`；未实现的已分配 cfx 由实现约定其未实现行为（测试机按未实现 cfx 处理）。
- cfx_pmem 的 64 KiB SRAM 固定在内部偏移 0x3ff_0000_0000（§4.9），CPU 用普通 `ld/st` 访问；SRAM 之外的核内偏移触发 CFXMEM。
- 屏障指令 `fence cfxHA, immu18` 用 `cfxHA` 选择资源域：`cfx0` 与 `cfx_umon` 都表示 **all cfx**，`cfx1`–`cfx63` 表示指定 cfx；`immu18` 中的 `cr`/`cw`/`ci`/`co` 位作用于所选 cfx 的 memory/IO 访问，`mr`/`mw` 位作用于系统内存。屏障只约束本 hart 的访问顺序/可见性，不等待 DMA。
- cfx1–cfx63 的访问权限不在本章定义。

### 2.2 虚实地址转换

内存窗口的虚拟地址划分：CPU 地址高 6 位 `addr[47:42] = 0` 时，`VA = addr[41:0]`（42 位）。物理地址 PA 为 56 位。

`ptw_enable` 选择内存窗口的访问方式：

- `ptw_enable = 0`：不进行地址转换；`addr[47:42] = 0` 的普通访存（含取指）触发 **CFXMEM**，目标是当前运行模式的 cfx；不得直通物理存储器。复位值 0。
- `ptw_enable = 1`：按唯一 PTBR 指向的页表进行地址转换（见后续小节）。

**单 PTBR**：`cfx_ptw_ptbr` 只有一份（不是 64 项数组），只存 `PPN[55:16]`（40 位）；页表物理基址 = `PPN << 16`，即 64 KiB 对齐。PTBR 没有 valid 位；PTBR = 0 表示物理基址为 PA 0，是否使用由 `ptw_enable` 决定。PTBR 的 `[15:0]` 强制为 0，`[63:56]` 保留为 0。

写 PTBR、写 ASID 或写 `ptw_enable = 1` 均由软件直接完成，**不隐含 TLB invalidate**；软件须显式 invalidate TLB（§4.5）。复位时 PTBR = 0、ASID = 0、`ptw_enable = 0`、TLB 为空。

#### 2.2.1 超页的地址转换

42 位的虚拟地址在超页步进中划分为两个字段：

- `VA[41:29]` -> L1 index（一级页表索引，每个一级页表 2^13 个页表项，每个表项 8 字节，即 64KiB）
- `VA[28:00]` -> 页内偏移（超页的页内偏移为 29 位，即 512MiB）

页表项按目标端序（大端）存放于物理存储器（pmem）。页表访问使用物理地址（PA），**不经过**地址转换（PTW/TLB）；软件须保证 PTBR、页表页与映射目标都落在物理存储器中。

虚拟地址到物理地址的转换分为四步：

**第一步：检查 PTW 开关并使用 PTBR**

- 检查 `ptw_enable`：为 0 时不会进入本流程（`addr[47:42] = 0` 的访存直接 CFXMEM）。
- 使用唯一的 `cfx_ptw_ptbr` 作为一级页表基地址（`PPN[55:16]`，64KiB 对齐）。不再按 `VA[47:42]` 选择 PTBR，也不再检查 PTBR 模式权限。

**第二步：TLB 查找**

- TLB 属于 `cfx_ptw`，没有独立的 TLB 使能位：`ptw_enable = 1` 即参与查找，`ptw_enable = 0` 时地址转换整体旁路（见第一步）。
- TLB 按「虚拟地址所在页 + ASID」匹配：条目的虚拟页必须覆盖本次访问地址，且条目 `G = 0` 时条目 ASID 等于 `cfx_ptw_tlb_asid`，`G = 1` 时跨 ASID 匹配（见 §2.2.5）。
- TLB 命中时不重读 PTE，直接用条目中的 SPF/GPF、HSJU 与 R/W/X 检查：小页标记位为 0 触发对应 `I/DPFTRAP` 异常，HSJU 或 R/W/X 不符触发对应 PERM 异常；检查顺序与 §2.2.6 相同。TLB 命中产生的异常属于 `cfx_ptw` 异常原因的子集，直接进入 `cfx_ptw`。
- 命中且权限符合时跳过第三步（页表步进），更新 A/D（见 §4.5）后进入第四步（形成最终物理地址）。
- 未命中时继续执行第三步；只有步进得到的 PTE 有效且全部检查通过后才把结果填入 TLB（缺页/权限失败不填充，也不更新 A/D）。替换策略由实现决定；替换或失效带未回写 A/D 的条目时须回写（§4.5）。

**第三步：页表步进**

- 用 `VA[41:29]` × 8 计算 L1 页表项偏移，从 PTBR 基址读取 8 字节 PTE。
- 若 Present 位为 0（`P = 0`）且 Superpage 位为 1（`SP = 1`），则为超页缺失，触发 `ISPTRAP`/`DSPTRAP` 异常。
- 若 Present 位为 0（`P = 0`）且 Superpage 位为 0（`SP = 0`），则该条目不是超页，按 §2.2.2 报 `IGPTRAP`/`DGPTRAP` 异常。
- 若 Present 位为 1 且 Superpage 位为 0（`SP = 0`），则该条目不是超页，按 §2.2.2 走二级页表。
- 若 Present 位为 1 且 Superpage 位为 1（`SP = 1`），则检查 SPF 字段中对应小页的标记位（`VA[28:26]` 选位；见 §2.2.3）；若对应位为 0，触发 `ISPFTRAP`/`DSPFTRAP` 异常。
- 小页存在时依次检查 HSJU 与读/写/执行权限（见 §2.2.5），任一不符触发对应 PERM 异常。

**第四步：形成最终物理地址**

- 物理地址由以下两部分拼接而成：
  - 一级页表项给出的物理页号作为 `PA[55:29]`（超页 512MiB 对齐；`PPN[28:16]` 非零时由硬件强制清零，不产生异常）
  - 超页的虚拟地址页内偏移 `VA[28:00]` 即为物理地址的页内偏移 `PA[28:00]`

#### 2.2.2 普通页的地址转换

42 位的虚拟地址在普通页步进中划分为三个字段：

- `VA[41:29]` -> L1 index（一级页表索引，每个一级页表 2^13 个页表项，每个表项 8 字节，即 64KiB）
- `VA[28:16]` -> L2 index（二级页表索引，每个二级页表 2^13 个页表项，每个表项 8 字节，即 64KiB）
- `VA[15:00]` -> 页内偏移（普通页的页内偏移为 16 位，即 64KiB）

虚拟地址到物理地址的转换分为四步：

**第一步：检查 PTW 开关并使用 PTBR**

- 检查 `ptw_enable`：为 0 时不会进入本流程（`addr[47:42] = 0` 的访存直接 CFXMEM）。
- 使用唯一的 `cfx_ptw_ptbr` 作为一级页表基地址（`PPN[55:16]`，64KiB 对齐）。不再按 `VA[47:42]` 选择 PTBR，也不再检查 PTBR 模式权限。

**第二步：TLB 查找**

- 若 `ptw_enable = 1`，先查 TLB；匹配键为「虚拟地址所在页 + ASID」，组织方式与匹配规则同 §2.2.1 第二步。
- TLB 命中时直接检查条目中的 GPF、HSJU 与 R/W/X 权限（语义同 §2.2.1 第二步）。
- 若 TLB 命中且权限符合，则跳过第三步（页表步进），更新 A/D（§4.5）后直接进入第四步（形成最终物理地址）。
- 若 TLB 未命中，则继续执行第三步；只有步进成功后才把结果填入 TLB。

**第三步：页表步进**

- 用 `VA[41:29]` × 8 计算 L1 页表项偏移，从 PTBR 基址读取 8 字节 PTE。
- 若 Present 位为 0（`P = 0`），触发 `IGPTRAP`/`DGPTRAP` 异常（`SP = 1` 时按 §2.2.1 报超页缺失）。
- 若 Present 位为 1 且 Superpage 位为 1（`SP = 1`），则该条目为超页，按 §2.2.1 处理。
- 若 Present 位为 1 且 Superpage 位为 0（`SP = 0`），生成二级页表的访问地址并读取 8 字节 L2 PTE：
  - 一级页表项给出的物理页号作为二级页表基址 `PA[55:16]`
  - 用 `VA[28:16]` × 8 计算二级页表的索引，即 L2 页表项偏移 `L2PA[15:3]`
- 若 L2 表项 Present 位为 0，触发 `IGPTRAP`/`DGPTRAP` 异常。
- 若 L2 表项 Present 位为 1，则检查 GPF 字段中对应小页的标记位（`VA[15:13]` 选位；见 §2.2.4）；若对应位为 0，触发 `IGPFTRAP`/`DGPFTRAP` 异常。
- 小页存在时依次检查 HSJU 与读/写/执行权限（见 §2.2.5），任一不符触发对应 PERM 异常。

**第四步：形成最终物理地址**

- 物理地址由以下两部分拼接而成：
  - 二级页表项给出的物理页号作为 `PA[55:16]`
  - 普通页的虚拟地址页内偏移 `VA[15:00]` 即为物理地址的页内偏移 `PA[15:00]`

#### 2.2.3 一级页表条目格式

一级页表条目（L1 PTE）为 64 位，按 `SP` 区分「指向二级页表」与「超页」两种用途：

| 位           | 含义        | 英文缩写 | 说明                 |
| ----------- | ----------- | ------ | ------------------ |
| bits[63:60] | 访问模式掩码  | HSJU   | H/S/J/U 各一位（H=bit63、S=bit62、J=bit61、U=bit60）；当前模式对应位为 1 才可访问（见 §2.2.5） |
| bits[59:56] | 保留         | —      | 软件须写 0，硬件忽略 |
| bits[55:16] | 物理页号     | PPN    | 超页为 `PPN[55:29]`（512MiB 对齐）；指向二级页表时为 `PPN[55:16]`（64KiB 对齐） |
| bits[15:8]  | 超页小页存在位 | SPF   | 仅超页有效；bit8 对应页面内最低 64MiB 片段，bit15 对应最高片段，按地址递增排列；0 不在内存，1 在内存 |
| bit7        | READ        | R      | 0不可读，1可读           |
| bit6        | WRITE       | W      | 0不可写，1可写           |
| bit5        | EXEC        | X      | 0不可执行，1可执行         |
| bit4        | Global      | G      | 1=全局页（TLB 中跨 ASID 复用），0=按 ASID 匹配；见 §2.2.5 |
| bit3        | Access      | A      | 0未被访问，1有访问（维护见 §4.5） |
| bit2        | Dirty       | D      | 0未被修改，1有修改（维护见 §4.5） |
| bit1        | Superpage   | SP     | 0下一级为二级页表，1为超页 |
| bit0        | Present     | P      | 0无效，1有效            |

**下一级为二级页表（`SP = 0`、`P = 1`）**

- `PPN[55:16]` 为二级页表物理基址（64KiB 对齐），`[15:0]` 为 0。
- 非叶子条目只使用 `P` 与 `SP`；HSJU/R/W/X/A/D/SPF 在该条目上不使用，页表步进不检查。
- `P = 0` 时其余字段全部忽略。

**下一级为超页（`SP = 1`）**

- 超页大小为2^29字节（512 MiB），划分为8个小页，每个小页大小为2^26字节（64 MiB）。超页的虚拟地址和物理地址需要 512 MiB 对齐，其内部小页 64 MiB 对齐。
- `SPF` 的 bit8 对应超页内最低地址片段（offset 0–64MiB），bit15 对应最高片段（offset 448–512MiB），按地址递增排列；`VA[28:26]` 选择对应位（`bit = 8 + VA[28:26]`）。
- `PPN[28:16]` 须为 0；软件写入非零值时硬件强制清零，不产生异常。
- `P = 0` 表示超页缺失；此时 `SPF` 等其余字段忽略。

物理超页分配由操作系统负责预留对应的物理地址空间；物理超页从外存加载时，由操作系统决定具体加载的小页位置与数量。

#### 2.2.4 二级页表条目格式

| 位           | 含义        | 英文缩写 | 说明                 |
| ----------- | ----------- | ------ | ------------------ |
| bits[63:60] | 访问模式掩码  | HSJU   | 语义同一级页表条目（见 §2.2.5） |
| bits[59:56] | 保留         | —      | 软件须写 0，硬件忽略 |
| bits[55:16] | 物理页号  | PPN    | 指向物理页，64KiB对齐 |
| bits[15:8]  | 普通页小页存在位 | GPF | bit8 对应页面内最低 8KiB 片段，bit15 对应最高片段，按地址递增排列；0 不在内存，1 在内存 |
| bit7        | READ        | R      | 0不可读，1可读           |
| bit6        | WRITE       | W      | 0不可写，1可写           |
| bit5        | EXEC        | X      | 0不可执行，1可执行         |
| bit4        | Global      | G      | 1=全局页（TLB 中跨 ASID 复用），0=按 ASID 匹配；见 §2.2.5 |
| bit3        | Access      | A      | 0未被访问，1有访问（维护见 §4.5） |
| bit2        | Dirty       | D      | 0未被修改，1有修改（维护见 §4.5） |
| bit1        | 保留         | —      | 软件须写 0，硬件忽略 |
| bit0        | Present     | P      | 0无效，1有效            |

普通页大小为2^16字节（64 KiB），划分为8个小页（GPF, Page Fragment），每个小页大小为2^13字节（8 KiB）。普通页的虚拟地址和物理地址需要 64 KiB 对齐，其内部小页 8 KiB 对齐。`GPF` 的 bit8 对应普通页内最低地址片段（offset 0–8KiB），bit15 对应最高片段（offset 56–64KiB）；`VA[15:13]` 选择对应位（`bit = 8 + VA[15:13]`）。

物理页分配由操作系统负责预留对应的物理地址空间；物理页从外存加载时，由操作系统决定具体加载的小页位置与数量。

#### 2.2.5 操作系统页管理

**页访问权限（HSJU / R / W / X）**

- `HSJU` 是当前运行模式的访问许可掩码：U-mode 对应 `bit60`、J-mode 对应 `bit61`、S-mode 对应 `bit62`、H-mode 对应 `bit63`。当前运行模式对应的位为 1 才允许访问，否则分别触发 `NUPERM`/`NJPERM`/`NSPERM`/`NHPERM`。硬件不做「S 模式自动覆盖 U 页」「H 模式自动覆盖 S 页」之类的隐含放宽；用户页/内核页的组合策略由操作系统决定，架构不强制。
- `R`/`W`/`X` 与 HSJU 正交：取指要求 `X = 1`（否则 `NXPERM`），读要求 `R = 1`（否则 `NRPERM`），写要求 `W = 1`（否则 `NWPERM`）。
- 同一访问可同时违反多个条件时，只报 §2.2.6 规定的最高优先级异常。

**A/D 位**

`A`（Access）与 `D`（Dirty）由硬件在 TLB 条目中维护，经 `CLEAN`/`FLUSH`（或条目替换）以原子 OR 回写到 PTE：

- 条目填充时取 PTE 的 `A`/`D` 作为本地的 `A_local`/`D_local`，回写挂起位 `A_dirty`/`D_dirty` 清零——**填充本身不产生回写**。
- 权限通过的访问：读/取指在 `A_local = 0` 时置 `A_local = 1`、`A_dirty = 1`；写在置 `A` 的同时，`D_local = 0` 时置 `D_local = 1`、`D_dirty = 1`。该规则对「命中」与「本次访问触发填充」同样适用（填充只拷贝 PTE 的 `A`/`D`，本次访问随即按访问类型置位）。
- 缺页/权限失败：不更新 A/D，也不填充条目。
- `CLEAN`/`FLUSH`/条目替换：只把挂起的 `A`/`D` 位原子 OR 回写 PTE（保留其他字段），回写后清挂起位；`CLEAN` 保留条目，`FLUSH` 回写后删除条目，`INVALID` 不写回直接删除。
- 回写失败见 §4.5 `PTWERR`；页表页必须可写。软件清 `A`/`D` 后必须显式 invalidate 对应条目。

**Global 位**

- 叶子 PTE 的 `G = 1` 表示全局页：该页在 TLB 中跨 ASID 复用，`G = 0` 的页按 ASID 匹配。L1 非叶子条目的 `G` 无意义，软件写 0、硬件忽略。
- 软件必须保证 `G = 1` 的页在所有地址空间中映射一致。
- 切换地址空间后，软件必须显式 invalidate TLB——写 PTBR、写 ASID 或写 `ptw_enable` 都不隐含 TLB 失效。失效操作与 `G` 的关系见 §4.5。

**小页（Fragment）**

超页（512 MiB）和普通页（64 KiB）均划分为 8 个小页，分别由 L1 PTE 的 SPF 字段和 L2 PTE 的 GPF 字段指示各小页是否已在物理内存中。Fragment 机制节省外存 I/O 而非物理内存——物理页完整空间须预先分配。若操作系统不需要按需加载，可将 SPF/GPF 全部置 1，此时等同于无 fragment 的整页加载。

**保留位与 PPN 低位**

保留位（`[59:56]`；L1 非叶子条目的 `[15:0]`、L2 的 `bit1`）由软件写 0、硬件忽略，不产生异常。（`bit4` 为 `G`，不再是保留位。）`PPN` 中超出对应页大小对齐要求的低位（超页的 `PPN[28:16]`）由硬件强制清零，不产生异常。

**进程上下文切换**

操作系统在切换进程时须执行以下步骤：

1. 写入新进程的 ASID（`cfx_ptw_tlb_asid`）或新进程的 PTBR（`cfx_ptw_ptbr`）
2. 显式 invalidate TLB（写 ASID/PTBR 均不隐含失效；见 §4.5）
3. 置 `ptw_enable = 1`
4. 保存和恢复暂存寄存器（cg6）

#### 2.2.6 异常检查优先级

当多个异常条件同时满足时，硬件按以下顺序检查，触发第一个满足条件的异常：

**跨类别优先级**（指令执行流水线从前到后）：

1. IALIGN——取指前检测 IP[1:0] ≠ 00
2. ILLI/UNDI——译码阶段
3. MALIGN——地址计算后、访存前
4. 页表异常——TLB/PTW 访存阶段（以下细表）

**页表步进内部优先级**（`P = 0` / 超页缺失 → SPF/GPF 对应位 = 0 → HSJU 不符 → R/W/X 不符）：

1. `ptw_enable = 0` → CFXMEM（不发生页表步进）
2. L1 `P = 0`：`SP = 1`（超页缺失）→ `ISPTRAP`/`DSPTRAP`；`SP = 0` → `IGPTRAP`/`DGPTRAP`
3. L1 `P = 1`、`SP = 1`、SPF 对应小页位 = 0 → `ISPFTRAP`/`DSPFTRAP`
4. L2 `P = 0`（普通页缺失）→ `IGPTRAP`/`DGPTRAP`
5. L2 `P = 1`、GPF 对应小页位 = 0 → `IGPFTRAP`/`DGPFTRAP`
6. HSJU 不符 → `NUPERM`/`NJPERM`/`NSPERM`/`NHPERM`（按当前运行模式）
7. R/W/X 不符 → 取指 `NXPERM`、写 `NWPERM`、读 `NRPERM`

仅触发优先级最高的异常，后续检查不再执行。取指异常用 `I` 前缀（`IGPTRAP`/`ISPTRAP`/`IGPFTRAP`/`ISPFTRAP`）并进入 cfx_ptw，数据读写异常用 `D` 前缀（`DGPTRAP`/`DSPTRAP`/`DGPFTRAP`/`DSPFTRAP`），异常原因编号与 `excp_cause_info` 见 §4.5 cfx_ptw 异常原因表；页表步进或 TLB 命中产生的异常都进入 `cfx_ptw`（§5.2）。

## 3. 共有寄存器设计规范

cg0-cg7 为共有寄存器设计，不同的核芯功能扩展设计规范相同。

### 3.1 cg0 - user mode 寄存器

每个核芯功能扩展中针对用户模式（user）有以下12个寄存器（cg=0）：

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 0 | 0 | user global version | cfx_⟨cfxname⟩_user_global_version | 0x00090003 | RO | AEE 版本号：`(major<<32)\|(minor<<16)\|patch`，当前 0.9.3。全局寄存器 |
| 0 | 1 | user global cfx mask | cfx_⟨cfxname⟩_user_global_cfx_mask | 全1 | RW | 全局核芯功能扩展掩码，0=可触发，1=屏蔽。自身 cfxha 对应位硬件忽略 |
| 0 | 2 | user cfx2rd cfx mask | cfx_⟨cfxname⟩_user_cfx2rd_cfx_mask | 全1 | RW | cfx2rd 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxha 对应位硬件忽略 |
| 0 | 3 | user cfx2rc cfx mask | cfx_⟨cfxname⟩_user_cfx2rc_cfx_mask | 全1 | RW | cfx2rc 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxha 对应位硬件忽略 |
| 0 | 4 | user cfxld cfx mask | cfx_⟨cfxname⟩_user_cfxld_cfx_mask | 全1 | RW | cfxld 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxha 对应位硬件忽略 |
| 0 | 5 | user cfxst cfx mask | cfx_⟨cfxname⟩_user_cfxst_cfx_mask | 全1 | RW | cfxst 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxha 对应位硬件忽略 |
| 0 | 6 | user trap cfx mask | cfx_⟨cfxname⟩_user_trap_cfx_mask | 全1 | RW | trap 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxha 对应位硬件忽略 |
| 0 | 7 | user escape cfx mask | cfx_⟨cfxname⟩_user_escape_cfx_mask | 全1 | RW | escape 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxha 对应位硬件忽略 |
| 0 | 8 | user switch run mode | cfx_⟨cfxname⟩_user_switch_run_mode | 2 (S-mode) | RW | 从user陷入时切换的运行模式 |
| 0 | 9 | user switch cfx mask | cfx_⟨cfxname⟩_user_switch_cfx_mask | 全1 | RW | 从user陷入时采用的异常掩码，0=可触发，1=屏蔽 |
| 0 | 10 | user excp vector | cfx_⟨cfxname⟩_user_excp_vector | 0 | RW | 从user陷入时的异常向量入口地址 |
| 0 | 11 | user excp mask | cfx_⟨cfxname⟩_user_excp_cause_mask | 全1 | RW | user异常原因掩码，0=可触发，1=屏蔽 |

`user global` 开头的寄存器为全局寄存器，即所有核芯功能扩展共享同一个寄存器。

为支持用户程序通过系统调用陷入操作系统内核，硬件应至少支持 `cfx_umon_user_*` 这一组寄存器或 `cfx_smon_user_*` 这一组寄存器。

用户 `trap` 按 cfxha 路由：目标为 `cfx_smon` 时使用 `cfx_smon_user_*`（需清除 `user global cfx_mask` 对应位），目标为 `cfx_umon` 时使用 `cfx_umon_user_*`。非 trap 的 U-mode 异常固定进入 `cfx_umon`。

### 3.2 cg1 - jail mode 寄存器

jail mode 为受限用户模式，MVP 阶段与 user mode 行为一致。受限规则（如禁止指令、二阶段翻译等）留待后续版本定义。

每个核芯功能扩展中针对监狱模式（jail）有以下12个寄存器（cg=1）：

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 1 | 0 | jail global version | cfx_⟨cfxname⟩_jail_global_version | 0x00090003 | RO | jail 版本号，MVP 阶段与 user 版本号相同。全局寄存器 |
| 1 | 1 | jail global cfx mask | cfx_⟨cfxname⟩_jail_global_cfx_mask | 全1 | RW | 全局核芯功能扩展掩码，0=可触发，1=屏蔽。自身 cfxha 对应位硬件忽略 |
| 1 | 2 | jail cfx2rd cfx mask | cfx_⟨cfxname⟩_jail_cfx2rd_cfx_mask | 全1 | RW | cfx2rd 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxha 对应位硬件忽略 |
| 1 | 3 | jail cfx2rc cfx mask | cfx_⟨cfxname⟩_jail_cfx2rc_cfx_mask | 全1 | RW | cfx2rc 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxha 对应位硬件忽略 |
| 1 | 4 | jail cfxld cfx mask | cfx_⟨cfxname⟩_jail_cfxld_cfx_mask | 全1 | RW | cfxld 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxha 对应位硬件忽略 |
| 1 | 5 | jail cfxst cfx mask | cfx_⟨cfxname⟩_jail_cfxst_cfx_mask | 全1 | RW | cfxst 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxha 对应位硬件忽略 |
| 1 | 6 | jail trap cfx mask | cfx_⟨cfxname⟩_jail_trap_cfx_mask | 全1 | RW | trap 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxha 对应位硬件忽略 |
| 1 | 7 | jail escape cfx mask | cfx_⟨cfxname⟩_jail_escape_cfx_mask | 全1 | RW | escape 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxha 对应位硬件忽略 |
| 1 | 8 | jail switch run mode | cfx_⟨cfxname⟩_jail_switch_run_mode | 2 (supv) | RW | 从jail陷入时切换的运行模式 |
| 1 | 9 | jail switch cfx mask | cfx_⟨cfxname⟩_jail_switch_cfx_mask | 全1 | RW | 从jail陷入时采用的异常掩码，0=可触发，1=屏蔽 |
| 1 | 10 | jail excp vector | cfx_⟨cfxname⟩_jail_excp_vector | 0 | RW | 从jail陷入时的异常向量入口地址 |
| 1 | 11 | jail excp mask | cfx_⟨cfxname⟩_jail_excp_cause_mask | 全1 | RW | 异常原因掩码，0=可触发，1=屏蔽 |

`jail global` 开头的寄存器为全局寄存器，即所有核芯功能扩展共享同一个寄存器。

### 3.3 cg2 - supv mode 寄存器

每个核芯功能扩展中针对主管模式（supv）有以下12个寄存器（cg=2）：

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 2 | 0 | supv global version | cfx_⟨cfxname⟩_supv_global_version | 0x00070002 | RO | SEE 版本号：`(major<<32)\|(minor<<16)\|patch`，当前 0.7.2。全局寄存器 |
| 2 | 1 | supv global cfx mask | cfx_⟨cfxname⟩_supv_global_cfx_mask | 全1 | RW | 全局核芯功能扩展掩码，0=可触发，1=屏蔽。自身 cfxha 对应位硬件忽略 |
| 2 | 2 | supv cfx2rd cfx mask | cfx_⟨cfxname⟩_supv_cfx2rd_cfx_mask | 全1 | RW | cfx2rd 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxha 对应位硬件忽略 |
| 2 | 3 | supv cfx2rc cfx mask | cfx_⟨cfxname⟩_supv_cfx2rc_cfx_mask | 全1 | RW | cfx2rc 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxha 对应位硬件忽略 |
| 2 | 4 | supv cfxld cfx mask | cfx_⟨cfxname⟩_supv_cfxld_cfx_mask | 全1 | RW | cfxld 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxha 对应位硬件忽略 |
| 2 | 5 | supv cfxst cfx mask | cfx_⟨cfxname⟩_supv_cfxst_cfx_mask | 全1 | RW | cfxst 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxha 对应位硬件忽略 |
| 2 | 6 | supv trap cfx mask | cfx_⟨cfxname⟩_supv_trap_cfx_mask | 全1 | RW | trap 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxha 对应位硬件忽略 |
| 2 | 7 | supv escape cfx mask | cfx_⟨cfxname⟩_supv_escape_cfx_mask | 全1 | RW | escape 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxha 对应位硬件忽略 |
| 2 | 8 | supv switch run mode | cfx_⟨cfxname⟩_supv_switch_run_mode | 2 (supv) | RW | 从supv陷入时切换的运行模式 |
| 2 | 9 | supv switch cfx mask | cfx_⟨cfxname⟩_supv_switch_cfx_mask | 全1 | RW | 从supv陷入时采用的异常掩码，0=可触发，1=屏蔽 |
| 2 | 10 | supv excp vector | cfx_⟨cfxname⟩_supv_excp_vector | 0 | RW | 从supv陷入时的异常向量入口地址 |
| 2 | 11 | supv excp mask | cfx_⟨cfxname⟩_supv_excp_cause_mask | 全1 | RW | 异常原因掩码，0=可触发，1=屏蔽 |

`supv global` 开头的寄存器为全局寄存器，即所有核芯功能扩展共享同一个寄存器。

### 3.4 cg3 - hypv mode 寄存器

H-mode 寄存器（cg=3）定义见 HEE。

### 3.5 cg4 - 核芯功能扩展配置寄存器

每个核芯功能扩展都有以下7个通用寄存器（cg=4）：

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 4 | 0 | cfx cfx_id | cfx_⟨cfxname⟩_cfx_id | HW | RO | 核芯功能扩展标识符 |
| 4 | 1 | cfx version | cfx_⟨cfxname⟩_version | HW | RO | 版本号 |
| 4 | 2 | cfx trap num | cfx_⟨cfxname⟩_trap_num | 0 | HW | trap指令陷入该核芯功能扩展的次数 |
| 4 | 3 | cfx excp sync num | cfx_⟨cfxname⟩_excp_sync_num | 0 | HW | 除trap外同步异常陷入该核芯功能扩展的次数 |
| 4 | 4 | cfx excp async num | cfx_⟨cfxname⟩_excp_async_num | 0 | HW | 异步中断陷入该核芯功能扩展的次数 |
| 4 | 5 | cfx escape num | cfx_⟨cfxname⟩_escape_num | 0 | HW | escape退出该核芯功能扩展的次数 |
| 4 | 6 | cfx scratch regs num | cfx_⟨cfxname⟩_scratch_regs_num | HW | RO | 暂存寄存器数量，至少2，最多64 |

### 3.6 cg5 - 异常现场寄存器

每个核芯功能扩展都有以下7个异常寄存器（cg=5）：

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 5 | 0 | excp prev run mode | cfx_⟨cfxname⟩_excp_prev_run_mode | 0 | RW | 异常前运行模式，硬件陷入时保存，软件可写 |
| 5 | 1 | excp prev cfx mask | cfx_⟨cfxname⟩_excp_prev_cfx_mask | 0 | RW | 异常前核芯功能扩展掩码，硬件陷入时保存，软件可写 |
| 5 | 2 | excp cause id | cfx_⟨cfxname⟩_excp_cause_id | 0 | HW | 异常原因编号（one-hot），硬件在异常进入时写入 |
| 5 | 3 | excp cause ip | cfx_⟨cfxname⟩_excp_cause_ip | 0 | RW | 异常发生前的指令指针，硬件陷入时保存，软件可写 |
| 5 | 4 | excp cause info | cfx_⟨cfxname⟩_excp_cause_info | 0 | HW | 发生异常的辅助信息 |
| 5 | 5 | excp pending | cfx_⟨cfxname⟩_excp_pending | 0 | RW | 待处理异常/中断位图（one-hot，OR语义），写0清位 |
| 5 | 63 | excp cause nonmaskable | cfx_⟨cfxname⟩_excp_cause_nonmaskable | HW | RO | 不可屏蔽异常掩码，硬件根据异常原因表静态设置 |

所有异常原因编码为 one-hot（64 位），各核芯功能扩展的异常原因表定义该核芯功能扩展可处理的异常位。表中未列出的位属于保留或未使用，若硬件错误触发此类位，表示该核芯功能扩展出现不可恢复的错误。`1 << 3` 至 `1 << 6` 保留用于未来扩展（debug 异常等）；`1 << 7` 由 `cfx_ptw` 用作 `PTWERR`（§4.5），`1 << 8` 由 `cfx_pmem` 用作 `PMEM_DMA`（§4.9），其余核芯功能扩展保留。

### 3.7 cg6 - 暂存寄存器

每个核芯功能扩展都有暂存寄存器（cg=6），数量由 `cfx_⟨cfxname⟩_scratch_regs_num`（cg=4, rc=6）指定，硬件实现至少 2 个、最多 64 个。

暂存寄存器从 rc=0 开始连续分配。`cfx_⟨cfxname⟩_scratch_regs_num` = N 时，有效的暂存寄存器为 rc=0 至 rc=N−1。读写不存在或超出数量的暂存寄存器（rc ≥ N）触发 CFXREG 异常。

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 6 | 0−(N−1) | scratch regs | cfx_⟨cfxname⟩_scratch_regs[0..N−1] | 未定义 | RW | 暂存寄存器（软件用） |

### 3.8 cg7 - 内部存储控制寄存器

**本组为预留设计**：`cfxld`/`cfxst` 当前**未启用**，未实现的机器对这两条指令 decode **ILLI**；§5.1/§5.2 中相关表述**待启用后生效**。

每个核芯功能扩展可根据自身需求实现零个或多个内部存储块（SRAM），用于 cfxld/cfxst 指令在内存与核芯功能扩展内部之间的批量数据传输。

- 内部存储块的数量与每块大小由各核芯功能扩展的硬件实现决定，每块为一段连续的字节可寻址空间。
- 内部存储块可映射为核内地址空间；核内地址空间也可通过内部存储块机制进行访问；具体方式由各核芯功能扩展自行定义。
- 对cfx的内部存储块进行非法访问时，例如访问不存在的地址，或试图写只读的区域，会触发对应核芯功能扩展的 CFXMEM 异常。
- cfxld/cfxst 通过 cfx_⟨cfxname⟩_sram_block_sel 选择目标块，通过 cfx_⟨cfxname⟩_sram_addr 指定块内传输起始偏移。

每个核芯功能扩展都有以下内部存储控制寄存器（cg=7）：

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 7 | 0 | cfx sram block select | cfx_⟨cfxname⟩_sram_block_sel | 0 | RW | cfxld/cfxst 的目标内部存储块编号 |
| 7 | 1 | cfx sram address | cfx_⟨cfxname⟩_sram_addr | 0 | RW | 块内字节偏移 |

## 4. 专有寄存器设计规范

cg8-cg63 为专有寄存器设计，不同的核芯功能扩展设计规范不同。此外，不同核芯功能扩展的异常编号不同，也在这部分分别说明。

### 4.1 cfx_umon - user monitor

**异常原因表**

| excp cause id | 名称      | 触发条件      | 是否可屏蔽 | excp cause info                |
| --------   | ------  | --------- | ---------- | ---------                   |
| `1 << 0`   | CFXTRAP | 功能调用      | 否 | 指令编码                        |
| `1 << 1`   | CFXMEM  | 访问核内地址空间或内部存储块故障 | 否 | 访存地址                        |
| `1 << 2`   | CFXREG   | 非法核芯功能扩展寄存器访问 | 否 | 指令编码         |
| `1 << 8`   | ILLI    | 非法指令      | 否 | 指令编码                        |
| `1 << 9`   | UNDI    | 未定义指令     | 否 | 指令编码                        |
| `1 << 10`  | RASOF   | RAS上溢     | 否 | 准备压栈的返回地址                   |
| `1 << 11`  | RASUF   | RAS下溢     | 否 | 全零（无效）                      |
| `1 << 12`  | MALIGN  | 非对齐访存    | 否 | 访存地址                        |
| `1 << 13`  | IALIGN  | 取指未对齐    | 否 | IP 值                          |

### 4.2 cfx_jmon - jail monitor

异常原因编码与 cfx_umon 一致。

### 4.3 cfx_smon - supervisor monitor

异常原因编码与 cfx_umon 一致。

### 4.4 cfx_hmon - hypervisor monitor

异常原因编码与 cfx_umon 一致。详细定义见 HEE。

### 4.5 cfx_ptw - page table walker

**专有寄存器表**

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 8 | 8 | ptw enable | cfx_ptw_enable | 0 | RW | PTW 使能：0=关闭（`addr[47:42] = 0` 的访存触发 CFXMEM，TLB 旁路），1=开启（先查 TLB，未命中走页表）。写 1 不隐含 TLB invalidate |
| 9 | 0 | ptw ptbr | cfx_ptw_ptbr | 0 | RW | 唯一 PTBR（单份，无数组）：只存 `PPN[55:16]`；`[15:0]` 强制为 0（64KiB 对齐），`[63:56]` 保留为 0；无 valid 位 |
| 12 | 0 | tlb control | cfx_ptw_tlb_control | 0 | WO | TLB 失效/回写命令（写即同步执行，无完成状态）：`[1:0]` 操作 = `00=none`/`01=clean`/`10=invalid`/`11=flush`；`[3:2]` 地址范围 = `00=all`/`01=VA`/`10=range`/`11=reserved`；`bit4=ASID_ANY`；其余保留 |
| 12 | 1 | tlb asid | cfx_ptw_tlb_asid | 0 | RW | 当前地址空间标识 ASID：`[15:0]`（16 位，所有值可用），`[63:16]` 读 0 |
| 12 | 2 | tlb addr start | cfx_ptw_tlb_addr_start | 0 | RW | 失效操作的起始虚拟地址（`VA[41:0]`） |
| 12 | 3 | tlb addr size | cfx_ptw_tlb_addr_size | 0 | RW | 失效操作的地址范围大小（字节） |

PTE 格式、两级页表步进、HSJU/R/W/X 页权限与异常优先级见 §2.2.1–§2.2.6。TLB 并入本核芯功能扩展：没有独立的 TLB 核芯功能扩展，也没有 `tlb_enable`/`tlb_exist`；TLB 命中时产生的同类异常直接进入 `cfx_ptw`。

**TLB 与 ASID**

- TLB 条目保存虚拟页、页大小、ASID、`G`、PPN、HSJU、R/W/X、SPF/GPF 与本地 A/D；条目数、组织与替换策略由实现决定。
- `ptw_enable = 1` 时 TLB 参与查找，`ptw_enable = 0` 时地址转换整体旁路（TLB 不参与）；复位时 TLB 为空，`cfx_ptw_tlb_asid = 0`。
- 匹配条件 = `(ASID 匹配) AND (地址匹配)`：条目的虚拟页覆盖被访问地址；`G = 0` 时条目 ASID 须等于 `cfx_ptw_tlb_asid`，`G = 1` 时跨 ASID 匹配。
- 命中时不重读 PTE；miss 走页表步进，只有 PTE 有效且全部检查通过才填充。替换带未回写 A/D 的条目时须先回写。
- 写 PTBR、写 ASID、写 `ptw_enable` 都不隐含 TLB 失效（§2.2.5）。

**A/D 维护与回写**

- 条目填充：`A_local = PTE.A`、`D_local = PTE.D`、`A_dirty = D_dirty = 0`（填充本身不产生回写）。
- 读/取指命中且权限通过：`A_local = 0` ⇒ `A_local = 1`、`A_dirty = 1`；写命中且权限通过：`A_local = 0` ⇒ `A_local = 1`、`A_dirty = 1`，且 `D_local = 0` ⇒ `D_local = 1`、`D_dirty = 1`。
- 缺页/权限失败：不更新 A/D，不填充条目。
- 回写只把挂起的 `A`/`D` 位做**原子 OR** 写入 PTE（保留其他字段）；回写成功后清挂起位。页表页必须可写；软件清 A/D 后必须显式失效对应条目。

**失效接口（正交语义）**

- `cfx_ptw_tlb_control` 的三个维度互相独立：操作（`[1:0]`）、地址范围（`[3:2]`）、ASID（`bit4` = `ASID_ANY`，`1` = 所有 ASID，`0` = 匹配 `cfx_ptw_tlb_asid`）。
- **判序**：先判操作（`[1:0]`），再判地址范围与操作数。
  - `00 = none`：**无条件 no-op**——不报异常，且不检查地址范围编码与 `size`（`scope = 11` 或 `range` 且 `size = 0` 在该操作下同样不报异常）；`ASID_ANY`/start/size 均被忽略。
  - `01 = clean`：回写 A/D，保留条目。`10 = invalid`：只删除条目，不回写。`11 = flush`：回写 A/D 后删除条目；回写失败时**不删除该条目**并报 `PTWERR`。这三种操作才校验地址范围编码。
- 地址范围（仅 `clean`/`invalid`/`flush` 生效）：`00 = all` 忽略 start/size；`01 = VA` 只匹配包含 `tlb_addr_start` 的条目（忽略 size）；`10 = range` 匹配与 `[start, start+size)` 相交的条目；`11 = reserved` 或 `range` 且 `size = 0` ⇒ `CFXREG`（非法操作数）。
- ASID 维度与 `G`：`ASID_ANY = 1` 时包含 `G = 1` 的条目；`ASID_ANY = 0` 时只处理 `G = 0` 且 ASID 匹配的条目，**不碰 `G` 条目**。
- 正常完成（含 `none`）不产生异常；只有 `clean`/`invalid`/`flush` 的非法编码/操作数触发 `CFXREG`。

**异常原因表**

| excp cause id | 名称     | 触发条件      | 是否可屏蔽 | excp cause info |
| --------   | ------ | --------- | ---------- | ---------    |
| `1 << 0`   | CFXTRAP  | 功能调用      | 否 | 指令编码         |
| `1 << 1`   | CFXMEM   | 访问核内地址空间或内部存储块故障 | 否 | 访存地址         |
| `1 << 2`   | CFXREG   | 非法核芯功能扩展寄存器访问 | 否 | 指令编码         |
| `1 << 7`   | PTWERR   | A/D 回写失败  | 否 | 出错的 PTE 物理地址 |
| `1 << 8`   | NUPERM   | U-mode无权访问  | 否 | 访存地址         |
| `1 << 9`   | NJPERM   | J-mode无权访问  | 否 | 访存地址         |
| `1 << 10`  | NSPERM   | S-mode无权访问  | 否 | 访存地址         |
| `1 << 11`  | NHPERM   | H-mode无权访问  | 否 | 访存地址         |
| `1 << 12`  | NXPERM   | 执行不可执行页   | 否 | 取指地址         |
| `1 << 13`  | NWPERM   | 写不可写页     | 否 | 读写地址         |
| `1 << 14`  | NRPERM   | 读不可读页     | 否 | 读写地址         |
| `1 << 16`  | IGPTRAP  | 取指普通页缺失  | 否 | 取指地址         |
| `1 << 17`  | ISPTRAP  | 取指超页缺失    | 否 | 取指地址         |
| `1 << 18`  | IGPFTRAP | 取指普通页小页缺失 | 否 | 取指地址         |
| `1 << 19`  | ISPFTRAP | 取指超页小页缺失  | 否 | 取指地址         |
| `1 << 20`  | DGPTRAP  | 数据读写普通页缺失 | 否 | 读写地址         |
| `1 << 21`  | DSPTRAP  | 数据读写超页缺失  | 否 | 读写地址         |
| `1 << 22`  | DGPFTRAP | 数据读写普通页小页缺失 | 否 | 读写地址         |
| `1 << 23`  | DSPFTRAP | 数据读写超页小页缺失 | 否 | 读写地址         |

### 4.6 cfx_cache - cache organization

**专有寄存器表**

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 8 | 0 | cache exist | cfx_cache_exist | — | RO | 硬件设置，指示对应VA空间是否有cache |
| 8 | 8 | cache enable | cfx_cache_enable | 同 cache_exist | RW | 软件配置，0=关闭，1=开启。复位后每一位等于对应 cache_exist 位的值（即已存在 I/D-Cache 的集合默认开启） |
| 8 | 9 | cache ctrl | cfx_cache_ctrl | 0 | WO | bit0=invalid icache；bit1=invalid dcache；bit2=flush dcache |

**异常原因表**

| excp cause id | 名称     | 触发条件      | 是否可屏蔽 | excp cause info |
| --------   | ------ | --------- | ---------- | ---------    |
| `1 << 0`   | CFXTRAP  | 功能调用      | 否 | 指令编码         |
| `1 << 1`   | CFXMEM   | 访问核内地址空间或内部存储块故障 | 否 | 访存地址         |
| `1 << 2`   | CFXREG   | 非法核芯功能扩展寄存器访问 | 否 | 指令编码         |

### 4.7 cfx_hart - hart management

管理独立的指令流水线（hart）。多核时每个 hart 有独立的 cfx_hart。

**专有寄存器表**

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 8 | 0 | hart id | cfx_hart_hart_id | — | RO | 硬件设置，hart 编号（0-based） |
| 8 | 1 | — | — | — | — | 保留 |
| 8 | 2 | cycle lo | cfx_hart_cycle_lo | 0 | RO | 本地周期数低64位 |
| 8 | 3 | cycle hi | cfx_hart_cycle_hi | 0 | RO | 本地周期数高64位 |
| 8 | 4 | insn lo | cfx_hart_insn_lo | 0 | RO | 指令计数低64位 |
| 8 | 5 | insn hi | cfx_hart_insn_hi | 0 | RO | 指令计数高64位 |
| 8 | 6 | timer cmp | cfx_hart_timer_cmp | 0 | RW | 64 位定时器比较值（绝对时间，单位同 cfx_time_value） |
| 8 | 7 | timer ctrl | cfx_hart_timer_ctrl | 0 | RW | bit0=ENABLE，bit1=IMASK，bit2=ISTATUS（RO）；其余保留 |

`cfx_time_value >= cfx_hart_timer_cmp` 且 `ENABLE=1` 时置 `ISTATUS`；`IMASK=0` 时触发 TIMER 中断。写新的 `timer_cmp` 即清除本次条件；写全 1 关闭。

**异常原因表**

| excp cause id | 名称     | 触发条件      | 是否可屏蔽 | excp cause info |
| --------   | ------ | --------- | ---------- | ---------    |
| `1 << 0`   | CFXTRAP  | 功能调用      | 否 | 指令编码         |
| `1 << 1`   | CFXMEM   | 访问核内地址空间或内部存储块故障 | 否 | 访存地址         |
| `1 << 2`   | CFXREG   | 非法核芯功能扩展寄存器访问 | 否 | 指令编码         |
| `1 << 8`   | IPI       | 核间中断      | 可 | 中断源 hart ID（低 6 位有效，高 58 位保留为 0） |
| `1 << 10`  | TIMER     | 本地定时器比较匹配 | 可 | 全零 |

### 4.8 cfx_llc - last level cache

最后一级缓存（LLC）管理，跨 hart 共享。

**专有寄存器表**

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 8 | 0 | llc exist | cfx_llc_exist | — | RO | 硬件设置，指示是否有 LLC |
| 8 | 8 | llc ctrl | cfx_llc_ctrl | 0 | WO | bit0=invalid all LLC |

**异常原因表**

| excp cause id | 名称     | 触发条件      | 是否可屏蔽 | excp cause info |
| --------   | ------ | --------- | ---------- | ---------    |
| `1 << 0`   | CFXTRAP  | 功能调用      | 否 | 指令编码         |
| `1 << 1`   | CFXMEM   | 访问核内地址空间或内部存储块故障 | 否 | 访存地址         |
| `1 << 2`   | CFXREG   | 非法核芯功能扩展寄存器访问 | 否 | 指令编码         |

### 4.9 cfx_pmem - physical memory management

cfx_pmem 管理物理存储器（Physical Memory, PM）区域，最多支持 64 个不连续 PM 区域。PM 仅指普通 DRAM 存储器，与 device 或 MMIO 无关——device 的存储空间由各设备核芯功能扩展自行管理。

cfx_pmem 内含一段 **64 KiB SRAM**，固定在 cfx_pmem 内部偏移 0x3ff_0000_0000（核内地址 = cfxha 17、低 42 位偏移）。CPU 用普通 `ld/st` 同步访问该 SRAM；访问超出 64 KiB 的核内偏移触发 CFXMEM。cfx 访问权限不在本章定义。

SRAM 与物理存储器（PA）之间的块搬运由 cfx_pmem 的 DMA 完成（不新增指令，不设 per-cfx DMA）：

- **方向**：`CFX→PA`（SRAM 读到 PA）或 `PA→CFX`（PA 读到 SRAM）。
- **地址**：`dma_src`/`dma_dst` 为 64 位；CFX 侧只取低 42 位、PA 侧只取低 56 位，高位**忽略**（不因高位非 0 报错）。
- **长度**：`dma_size` 为 30 位，合法范围 `1..2^29`（512 MiB）。实际传输还受 64 KiB SRAM 范围、PA 56 位不溢出与目标可访问性约束。
- **异步**：写 `dma_ctrl.START=1` 后 `dma_status.BUSY=1`，完成后硬件清 BUSY 并置 DONE（或 ERROR）；完成前软件不得复用 SRAM 与寄存器。
- **单 hart**：`PMEM_DMA` 直接投递到本 hart 的 cfx_pmem 异常入口；多 hart 的接收者规则后续定义。

**专有寄存器表**

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 8 | 0 | pmem exist | cfx_pmem_exist | — | RO | 硬件设置，指示PM区域是否存在 |
| 12 | 0-63 | pmem start | cfx_pmem_start[0..63] | 0 | RW | PM区域起始物理地址 |
| 13 | 0-63 | pmem size | cfx_pmem_size[0..63] | 0 | RW | PM区域大小（0=未使用） |
| 14 | 0-63 | pmem attr | cfx_pmem_attr[0..63] | 0 | RW | bit0=prefetchable，bit1=coherent |
| 15 | 0 | dma src | cfx_pmem_dma_src | 0 | RW | 64 位源地址（CFX 侧取低 42 位，PA 侧取低 56 位） |
| 15 | 1 | dma dst | cfx_pmem_dma_dst | 0 | RW | 64 位目的地址（同上） |
| 15 | 2 | dma size | cfx_pmem_dma_size | 0 | RW | 传输字节数，30 位，合法 `1..2^29` |
| 15 | 3 | dma ctrl | cfx_pmem_dma_ctrl | 0 | RW | bit0=START（自清）、bit1=DIR（0=CFX→PA，1=PA→CFX）、bit2=IRQ_EN；其余 SBZ |
| 15 | 4 | dma status | cfx_pmem_dma_status | 0 | RW | bit0=BUSY（RO）、bit1=DONE（W1C）、bit2=ERROR（W1C）、bit3-15=ERR_CODE（one-hot，RO）；其余保留 |

cg15 其余 rc 保留，读写触发 CFXREG。`dma_ctrl` 写入时 START 自清（读回 0）；`DIR`/`IRQ_EN` 读回最后写入值。`BUSY=1` 期间对 cg15 的 `dma_src`/`dma_dst`/`dma_size`/`dma_ctrl` 写入被忽略（含 START），`dma_status` 的 DONE/ERROR W1C 被忽略；寄存器读出不受影响。`DONE`、`ERROR` 为粘滞位，只由 W1C 清除（`START` 不清除）；`ERROR` W1C 时一并清除 `ERR_CODE`。

多个 PM 区域可以不连续。若区域地址重叠，按编号小的优先级高。硬件访问物理地址时，按 PM 编号从 0 开始匹配，匹配到的第一个区域的属性决定该访问的行为（预取策略、Cache 一致性等）。

**ERR_CODE（`dma_status[15:3]`，one-hot）**

| 位 | 名称 | 触发条件 |
|----|------|---------|
| bit3 | SIZE | `dma_size=0` 或 `dma_size > 2^29` |
| bit4 | CFX_RANGE | CFX 侧地址 + size 超出 64 KiB SRAM 范围 |
| bit5 | PA_RANGE | PA + size 超出 56 位物理地址空间 |
| bit6 | PA_FAULT | PA 不属于可访问的物理存储器，或写不可写的物理存储器（如 ROM） |

错误在 `START` 时判定：校验失败的传输不启动（BUSY 保持 0），硬件置 `ERROR` 与对应 `ERR_CODE`。

**异常原因表**

| excp cause id | 名称     | 触发条件      | 是否可屏蔽 | excp cause info |
| --------   | ------ | --------- | ---------- | ---------    |
| `1 << 0`   | CFXTRAP  | 功能调用      | 否 | 指令编码         |
| `1 << 1`   | CFXMEM   | 访问核内地址空间或内部存储块故障 | 否 | 访存地址         |
| `1 << 2`   | CFXREG   | 非法核芯功能扩展寄存器访问 | 否 | 指令编码         |
| `1 << 8`   | PMEM_DMA | DMA 完成（DONE）或出错（ERROR） | 可 | `dma_status`（含 `ERR_CODE`） |

`PMEM_DMA` 为异步异常：`dma_ctrl.IRQ_EN=1` 时 `DONE` 或 `ERROR` 置位触发；被掩码屏蔽时对应位置入 `cfx_pmem_excp_pending`（`1 << 8`）。`cause_info` 携带触发时的 `dma_status` 值。

> shareability、inner/outer cacheability 等进阶属性留待多核 SMP 阶段再定义。当前单核 MVP 仅需 prefetchable 和 coherent 位即可满足。

### 4.10 cfx_time - 全局时间计数器

`cfx_time` 为 **per-system** 全局时间计数器，所有 hart 共享同一时间基准；只提供时间读数，不产生中断。每 hart 的定时器比较与中断由 `cfx_hart` 提供。

**专有寄存器表**

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 10 | 7 | time freq | cfx_time_freq | — | RO | 计数频率（Hz），硬件设置 |
| 10 | 8 | time value | cfx_time_value | 0 | RO | 64 位全局时间计数值，自由运行 |

**异常原因表**

| excp cause id | 名称          | 触发条件      | 是否可屏蔽 | excp cause info |
| --------   | ------      | --------- | ---------- | ---------    |
| `1 << 0`   | CFXTRAP     | 功能调用      | 否 | 指令编码         |
| `1 << 1`   | CFXMEM      | 访问核内地址空间或内部存储块故障 | 否 | 访存地址         |
| `1 << 2`   | CFXREG      | 非法核芯功能扩展寄存器访问 | 否 | 指令编码         |

### 4.11 cfx_uart - uart

**专有寄存器表**

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 8 | 1 | uart exist | cfx_uart_exist | HW | RO | 硬件设置，指示UART是否有效 |
| 32 | 0-63 | uart0 regs | cfx_uart_uart0_regs[0..63] | HW | RW | 参照硬件协议 |
| 33 | 0-63 | uart1 regs | cfx_uart_uart1_regs[0..63] | HW | RW | 参照硬件协议 |
| ... | ... | ... | ... | ... | ... | ... |
| 63 | 0-63 | uart31 regs | cfx_uart_uart31_regs[0..63] | HW | RW | 参照硬件协议 |

UART寄存器的读写操作通过 `cfx2rd`/`cfx2rc` 指令完成。若寄存器的读写宽度为8位或16位，则单独分配一个64位寄存器号。

**异常原因表**

| excp cause id | 名称      | 触发条件      | 是否可屏蔽 | excp cause info |
| --------   | ------  | --------- | ---------- | ---------       |
| `1 << 0`   | CFXTRAP     | 功能调用      | 否 | 指令编码          |
| `1 << 1`   | CFXMEM  | 访问核内地址空间或内部存储块故障 | 否 | 访存地址 |
| `1 << 2`   | CFXREG  | 非法核芯功能扩展寄存器访问 | 否 | 指令编码 |
| `1 << 32`  | UART0   | UART0中断    | 可 | 全零              |
| `1 << 33`  | UART1   | UART1中断    | 可 | 全零              |
| `1 << 34`  | UART2   | UART2中断    | 可 | 全零              |
| ...        | ...     | ...        | 可 | 全零              |
| `1 << 63`  | UART31  | UART31中断   | 可 | 全零              |

### 4.12 cfx_power - power management

**专有寄存器表**

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 8 | 1 | power ctrl | cfx_power_ctrl | 0 | WO | bit0=关机，bit1=硬复位，bit2=软复位 |

**异常原因表**

| excp cause id | 名称          | 触发条件      | 是否可屏蔽 | excp cause info |
| --------   | ------      | --------- | ---------- | ---------    |
| `1 << 0`   | CFXTRAP     | 功能调用      | 否 | 指令编码         |
| `1 << 1`   | CFXMEM      | 访问核内地址空间或内部存储块故障 | 否 | 访存地址         |
| `1 << 2`   | CFXREG      | 非法核芯功能扩展寄存器访问 | 否 | 指令编码         |
| `1 << 8`   | POWEROFF    | 硬件关机      | 否 | 全零         |
| `1 << 9`   | HARD_RESET | 硬件重启      | 否 | 全零         |
| `1 << 10`  | SOFT_RESET | 软件重启      | 否 | 指令编码         |

## 5. 异常进入与异常退出

**重要**：异常原因编码（`excp cause id`，即 `1 << n` 中的位索引 `n`）在各核芯功能扩展间 **独立编址**，不存在跨 cfx 冲突。例如 `1<<8` 在 cfx_umon 中为 ILLI，在 cfx_ptw 中为 NUPERM，在 cfx_hart 中为 IPI——它们属于不同 cfx 的异常表，互不干扰。每个 cfx 的异常原因编码空间为 0-63，硬件通过 cfxha 区分目标。

**精确异常**：所有同步异常和异步中断均为精确异常——IP 指向触发指令（同步）或下一条指令边界（异步），指令未完成，目标寄存器/内存/RA 未更新（无副作用）。页表步进异常（`I/DGPTRAP`、`I/DSPTRAP`、`I/DPFTRAP`、`NRPERM`/`NWPERM`/`NXPERM`）同为精确——访存未执行。IALIGN 为精确异常——取指前检测 IP[1:0] ≠ 00，IP 停留在非法地址。浮点指令不触发异常，始终按 IEEE 754 标准返回结果，异常状态记录在 rf0[4:0] 中。

**中断信号为电平触发**：硬件源持续有效且 mask 开启时，中断在指令边界检查并触发。mask 解除后若 pending 仍置 1，在下一指令边界触发中断。多个 pending 位同时置 1 或不同 cfx 同时产生中断时，低编号 cfxha 优先。

**系统控制例外**：POWEROFF/HARD_RESET/SOFT_RESET 为系统控制动作，不适用一般异常处理的 IP/寄存器保存语义。

**异常嵌套由软件解决**：各核芯功能扩展如可能发生同 cfx 嵌套异常，应在进入功能处理函数前保存当前异常现场（`excp_prev_*`、`excp_cause_*`），退出时恢复。硬件不阻止同 cfx 嵌套，但若软件未保存现场，再次进入会覆盖上一次的现场数据。

### 5.1 指令行为说明

trap/escape/cfxld/cfxst/cfx2rd/cfx2rc 指令可以在任意运行模式下执行（`cfxld`/`cfxst` 当前未启用）。若 cfxha 为 reserved 核芯功能扩展（6-14、19-61），硬件触发 ILLI 异常。对于常见的操作系统而言，并不希望由 user/jail 直接陷入或访问 hmon 到 power 之间的核芯功能扩展，则需要在这些核芯功能扩展的初始化代码中，设置好屏蔽位（缺省为屏蔽）。

escape 指令的第一个参数会指定 cfxha，通常该参数应该和当前的核芯功能扩展编号相同，但是硬件实现并不检查其一致性，因此可以采用不同的核芯功能扩展编号，从而可以跳过多层核芯功能扩展的调用，直接跳到需要返回的指令指针。可以通过检查 `cfx_⟨cfxname⟩_trap_num + cfx_⟨cfxname⟩_excp_sync_num + cfx_⟨cfxname⟩_excp_async_num` 是否与 `cfx_⟨cfxname⟩_escape_num` 匹配，来判断是否有此类现象存在。

escape指令的第二个参数：**编码层** `imms18`（指令字偏移），`Addr = excp_cause_ip + (imms18 << 2)`；**汇编层** `imms20` 以字节为单位，值须 `%4==0`。常见用法如下：

| 用例 | 指令 | 返回位置 |
|------|------|---------|
| 重新执行触发异常的指令 | `escape cfxha, [excp_cause_ip, 0]` | cause_ip |
| 跳过触发指令（继续执行） | `escape cfxha, [excp_cause_ip, 4]` | cause_ip + 4 |
| 跳过 N 条指令（N 可为负数表示回退） | `escape cfxha, [excp_cause_ip, N*4]` | cause_ip + N×4 |

**跨 cfx escape 的安全约束**：escape 指定非当前 cfxha 时，硬件不保存跳过的中间 cfx 现场。`excp_prev_run_mode` 和 `excp_prev_cfx_mask` 恢复的是**最初 trap 进入当前调用链时的值**（非最近一次 trap 的）。调用链 A→B→C 中，若 B 中使用 `escape cfx_A, [excp_cause_ip, N*4]`，硬件直接恢复到 A 的 prev 现场，B 的现场（excp_prev_*/excp_cause_*）被静默丢弃。软件必须保证被跳过的 cfx 不再需要返回（即 B 的调用链已终结，B 不会再次被 escape 回）。

### 5.2 异常进入流程

X-mode（任意运行模式）下发生异常时，硬件自动执行以下操作序列：

1. **确定核芯功能扩展**：
   - 特权指令：
     - trap/cfx2rd/cfx2rc 按 cfxha 路由；
     - cfxld/cfxst 访问 cfx 内部存储块（待启用），仅触发 CFXMEM，按 cfxha 路由
     - 若 cfxha 为 reserved（6-14、19-61），触发 ILLI 进入当前 monitor；若 cfxha 合法但指令 cfx mask 禁止，同样触发 ILLI
   - 其它指令执行触发的 ILLI/UNDI/RASOF/RASUF/IALIGN/MALIGN 异常：
      - 根据发生异常前的运行模式（U-mode/J-mode/S-mode/H-mode）分别判断进入 cfx_umon/cfx_jmon/cfx_smon/cfx_hmon 核芯功能扩展
   - 页表相关异常（页表步进或 TLB 命中时产生的页缺失、权限不符、fragment 缺失、A/D 回写失败等）：判断应进入 cfx_ptw 核芯功能扩展
   - CFXMEM（核内地址空间非法访问：`ptw_enable=0` 的 `addr[47:42] = 0` 访存，或保留 cfx 的普通 `ld/st`）：`addr[47:42] = 0` 时目标是当前运行模式的 cfx；否则根据核内地址高 6 位 bits[47:42] 指定的 cfxha 作为目标核芯功能扩展
   - 异步中断：根据中断源判断进入对应的核芯功能扩展
2. **判断是否为不可屏蔽异常**：检查 `cfx_⟨cfxname⟩_excp_cause_nonmaskable` 对应位，若置1则该异常不可屏蔽，跳过步骤3-5直接进入步骤6
3. **判断 inner_cfx_mask 是否屏蔽**：若目标 cfx 非自身，检查 `inner_cfx_mask` 第 cfxha 位。若为1，同步异常触发 ILLI，异步中断设置 pending
4. **判断 global_cfx_mask 是否屏蔽**：若目标 cfx 非自身，检查 `cfx_⟨cfxname⟩_<mode>_global_cfx_mask` 第 cfxha 位。若为1，同步异常触发 ILLI，异步中断设置 pending
5. **判断异常原因是否被屏蔽**：检查 `cfx_⟨cfxname⟩_<mode>_excp_cause_mask` 对应位，若为1则该异常原因被屏蔽
    - 异步中断若被屏蔽，则处于待处理状态（pending），并将对应位置1到 `cfx_⟨cfxname⟩_excp_pending` 寄存器中（OR语义，不影响其他pending位）。软件可通过写0清除对应pending位。
    - （同步异常均为不可屏蔽，已在步骤 2 跳过步骤 3–5；本步只对异步中断生效。）
6. **更新陷入计数**：根据异常类型递增 `cfx_⟨cfxname⟩_trap_num`（trap 指令）、`cfx_⟨cfxname⟩_excp_sync_num`（同步异常）或 `cfx_⟨cfxname⟩_excp_async_num`（异步中断）
7. **保存现场**：`cfx_⟨cfxname⟩_excp_prev_run_mode` 记录异常前的运行模式，`cfx_⟨cfxname⟩_excp_prev_cfx_mask` 保存异常前的核芯功能扩展掩码
8. **模式切换**：将运行模式和核芯功能扩展掩码改为 `cfx_⟨cfxname⟩_<mode>_switch_run_mode` 和 `cfx_⟨cfxname⟩_<mode>_switch_cfx_mask` 寄存器的值
9. **保存异常信息**：
    - `cfx_⟨cfxname⟩_excp_cause_ip`：发生异常的指令地址（同步异常为触发异常的指令地址，异步中断为下一条指令地址）
    - `cfx_⟨cfxname⟩_excp_cause_id`：异常编号
    - `cfx_⟨cfxname⟩_excp_cause_info`：异常辅助信息
10. **跳转至异常向量**：跳转到 `cfx_⟨cfxname⟩_<mode>_excp_vector` 寄存器指示的异常处理程序地址。该地址与普通访存规则一致：`ptw_enable=0` 或地址 `addr[47:42] != 0` 时为核内地址，`ptw_enable=1` 且 `addr[47:42] = 0` 时为虚拟地址。软件须保证异常向量所在页不会发生页缺失，硬件不提供向量缺失的恢复机制。

```
// 注：伪代码中 cause 为 one-hot 值（如 CFXTRAP = 1<<0 = 1，ILLI = 1<<8 = 256）；
//     异常原因表中 `1 << n` 的 n 即位索引，cause = 1 << n。
// 1. 确定核芯功能扩展
if instruction ∈ {TRAP, ESCAPE, CFXLD, CFXST, CFX2RD, CFX2RC}:
    if cfxha ∈ {7..14, 19..61}:
        cause      <= ILLI
        ; reserved→ILLI，重定向到当前运行模式的 monitor (cfx0-3)
        case inner_run_mode of
            U-mode: temp_cfx_code <= 0
            J-mode: temp_cfx_code <= 1
            S-mode: temp_cfx_code <= 2
            H-mode: temp_cfx_code <= 3
    elif cfxha != inner_cfx_code and cfx_⟨cfxname⟩_<mode>_<instr>_cfx_mask & (1 << cfxha):
        cause      <= ILLI
        ; 指令类型 cfx mask 禁止 → ILLI，重定向到当前模式 monitor
        case inner_run_mode of
            U-mode: temp_cfx_code <= 0
            J-mode: temp_cfx_code <= 1
            S-mode: temp_cfx_code <= 2
            H-mode: temp_cfx_code <= 3
    elif instruction == TRAP:
        cause          <= CFXTRAP                 // 功能调用
        temp_cfx_code  <= cfxha
    elif instruction ∈ {CFX2RD, CFX2RC}:
        ; cause 已由硬件执行阶段确定（CFXREG），此处仅路由
        temp_cfx_code  <= cfxha
    elif instruction ∈ {CFXLD, CFXST}:
        ; cfxld/cfxst 访问核芯功能扩展内部存储块，仅触发 CFXMEM
        temp_cfx_code  <= cfxha
    // ESCAPE（非 reserved）：由异常退出流程处理，不在此处路由
elif sync:
    case inner_run_mode of
        U-mode: temp_cfx_code <= 0
        J-mode: temp_cfx_code <= 1
        S-mode: temp_cfx_code <= 2
        H-mode: temp_cfx_code <= 3
elif mem_access:
    if cause == CFXMEM:                         // 核内地址空间异常
        if addr[47:42] == 0:                    // 内存窗口（ptw_enable=0）→ 当前模式 monitor
            case inner_run_mode of
                U-mode: temp_cfx_code <= 0
                J-mode: temp_cfx_code <= 1
                S-mode: temp_cfx_code <= 2
                H-mode: temp_cfx_code <= 3
        else:
            temp_cfx_code  <= addr[47:42]       // 保留 cfx 的普通 ld/st → 按 cfxha 路由
    else:
        temp_cfx_code  <= 4                      // 页表相关异常（页表步进或 TLB 命中）→ cfx_ptw
else:
    temp_cfx_code          <= intr_cfx               // 异步中断 → 硬件固定路由

// 2. 判断是否为不可屏蔽异常
check_nonmaskable:
if (cfx_⟨cfxname⟩_excp_cause_nonmaskable & cause) == 0:

    // 3. 判断 inner_cfx_mask 是否屏蔽（自身 cfxha 不检查）
    if temp_cfx_code != inner_cfx_code
       and (inner_cfx_mask & (1 << temp_cfx_code)) != 0:
        if sync:  cause ← ILLI                      // 同步异常被 inner mask 屏蔽 → ILLI
                  case inner_run_mode of            // 重定向到当前模式 monitor
                      U-mode: temp_cfx_code <= 0
                      J-mode: temp_cfx_code <= 1
                      S-mode: temp_cfx_code <= 2
                      H-mode: temp_cfx_code <= 3
                  goto check_nonmaskable            // 继续异常进入流程
        else:     cfx_⟨cfxname⟩_excp_pending ← cfx_⟨cfxname⟩_excp_pending | cause
                  return

    // 4. 判断 global_cfx_mask 是否屏蔽（自身 cfxha 不检查）
    if temp_cfx_code != inner_cfx_code
       and (cfx_⟨cfxname⟩_<mode>_global_cfx_mask & (1 << temp_cfx_code)) != 0:
        if sync:  cause ← ILLI                      // 同步异常被 global mask 屏蔽 → ILLI
                  case inner_run_mode of            // 重定向到当前模式 monitor
                      U-mode: temp_cfx_code <= 0
                      J-mode: temp_cfx_code <= 1
                      S-mode: temp_cfx_code <= 2
                      H-mode: temp_cfx_code <= 3
                  goto check_nonmaskable            // 继续异常进入流程
        else:     cfx_⟨cfxname⟩_excp_pending ← cfx_⟨cfxname⟩_excp_pending | cause
                  return

    // 5. 判断异常原因是否被屏蔽
    //    异步中断被屏蔽时设置 pending
    if (cfx_⟨cfxname⟩_<mode>_excp_cause_mask & cause) != 0:
        cfx_⟨cfxname⟩_excp_pending ← cfx_⟨cfxname⟩_excp_pending | cause   // 仅异步中断会到达此处（同步异常均不可屏蔽，步骤 2 已跳过）
        return

// 6. 更新陷入计数
if cause == CFXTRAP:
    cfx_⟨cfxname⟩_trap_num        <= cfx_⟨cfxname⟩_trap_num + 1
elif not sync:                                    // 异步中断
    cfx_⟨cfxname⟩_excp_async_num  <= cfx_⟨cfxname⟩_excp_async_num + 1
else:                                             // 同步异常（非trap）
    cfx_⟨cfxname⟩_excp_sync_num   <= cfx_⟨cfxname⟩_excp_sync_num + 1

// 7. 保存现场
cfx_⟨cfxname⟩_excp_prev_run_mode  <= inner_run_mode
cfx_⟨cfxname⟩_excp_prev_cfx_mask  <= inner_cfx_mask

// 8. 模式切换
inner_run_mode           <= cfx_⟨cfxname⟩_<mode>_switch_run_mode
inner_cfx_mask           <= cfx_⟨cfxname⟩_<mode>_switch_cfx_mask
inner_cfx_code            <= temp_cfx_code

// 9. 保存异常信息
cfx_⟨cfxname⟩_excp_cause_ip       <= inner_excp_cause_ip     // 同步异常为触发指令地址，异步中断为下一条指令地址
cfx_⟨cfxname⟩_excp_cause_id       <= inner_excp_cause_id     // 异常编号
cfx_⟨cfxname⟩_excp_cause_info     <= inner_excp_cause_info   // 异常辅助信息

// 10. 跳转至异常向量
inner_inst_pointer           <= cfx_⟨cfxname⟩_<mode>_excp_vector
```

### 5.3 异常退出流程

通过 `escape` 指令完成异常退出。`escape` 指令编码中指定了核芯功能扩展编号 `cfxha`。伪代码中 `⟨cfxname⟩` 指当前执行 escape 的 cfx（即 `inner_cfx_code`）。下面的步骤和伪代码描述 `escape` 指令的硬件语义：

0. **检查 escape cfx mask**：若目标 cfxha 非自身，检查 `cfx_⟨cfxname⟩_<mode>_escape_cfx_mask` 第 cfxha 位。若为 1，触发 ILLI 异常（escape 被禁止）
1. **恢复核芯功能扩展掩码**：根据 `cfx_⟨cfxname⟩_excp_prev_cfx_mask` 寄存器的值恢复核芯功能扩展掩码
2. **恢复运行模式**：依据 `cfx_⟨cfxname⟩_excp_prev_run_mode` 还原为异常发生前的运行模式
3. **更新退出计数**：`cfx_⟨cfxname⟩_escape_num` 递增 1
4. **计算返回地址并跳转**：根据 `cfx_⟨cfxname⟩_excp_cause_ip` 寄存器的地址和 `escape` 指令的 `imms18`（指令字偏移）作为偏移值，计算出返回地址并跳转

```
// 0. 检查 escape cfx mask（自身 cfxha 不检查）
if cfxha != inner_cfx_code:
    if (cfx_⟨cfxname⟩_<mode>_escape_cfx_mask & (1 << cfxha)) != 0:
        cause      <= ILLI                          // escape 被禁止 → ILLI
        ; 重定向到当前模式 monitor
        case inner_run_mode of
            U-mode: temp_cfx_code <= 0
            J-mode: temp_cfx_code <= 1
            S-mode: temp_cfx_code <= 2
            H-mode: temp_cfx_code <= 3
        ; 跳转至异常进入流程步骤 2
        goto check_nonmaskable

// 1. 恢复核芯功能扩展掩码
inner_cfx_mask               <= cfx_⟨cfxname⟩_excp_prev_cfx_mask
// 2. 恢复运行模式
inner_run_mode               <= cfx_⟨cfxname⟩_excp_prev_run_mode
// 3. 更新退出计数
cfx_⟨cfxname⟩_escape_num             <= cfx_⟨cfxname⟩_escape_num + 1
// 4. 计算返回地址并跳转
inner_inst_pointer           <= cfx_⟨cfxname⟩_excp_cause_ip + (imms18 << 2)
```

---

## 附录：版本与变更记录

> **发布动作**：把顶部 `-rc` 段去 `-rc` 并补发布日期；`-rc` 段只在确有未发布改动时新开。

### 0.7.3-rc（未发布）

- 屏障指令 `fence cfxHA, immu18`：`cfx0`/`cfx_umon` 表示 all cfx，`cfx1`–`cfx63` 指定 cfx；资源域顺序只约束本 hart，不等待 DMA。
- cfx 编号调整：`cfx5` 为 `cache`（原 `cfx6` 迁入）；`cfx6`–`cfx14`、`cfx19`–`cfx61` 保留。
- `cfx_pmem` 增加 64 KiB SRAM（内部偏移 0x3ff_0000_0000，CPU 用 `ld/st` 访问）与 SRAM ↔ 物理存储器 DMA：`cg15` 寄存器 `dma_src`/`dma_dst`/`dma_size`/`dma_ctrl`/`dma_status`；方向 `CFX→PA`/`PA→CFX`，CFX 侧 42 位、PA 侧 56 位（高位忽略），`size` 30 位、合法 `1..2^29`；`START` 自清、`BUSY`/`DONE`/`ERROR`/`ERR_CODE`（W1C 与错误码）异步完成；`BUSY` 期间写寄存器与 W1C 被忽略。
- `cfx_pmem` 增加异步可屏蔽异常 `PMEM_DMA`（`1 << 8`）：`IRQ_EN=1` 时 `DONE`/`ERROR` 触发，`cause_info` 携带 `dma_status`；被屏蔽时置 `cfx_pmem_excp_pending`。当前单 hart 直接投递 `cfx_pmem`。

- 版本号与 SBI 同步（SBI 删除 `immu18` 保留值 `0x3FFFF`）；本册正文不变。
- 地址空间改为 48 位 CPU 地址 + 高 6 位分区：`0` 为内存窗口，`1..63` 为 cfx 1–63 核内空间；VA 42 位、PA 56 位，取消 64 位物理地址与高 16 位拼接。
- PTBR 由 64 项数组改为**单份** `cfx_ptw_ptbr`（只存 `PPN[55:16]`，64 KiB 对齐，无 valid 位）；删除 `pahi`/`pthi`/`ptbr_enable` 位图与四种模式的 PTBR 权限位图。
- 新增 `cfx_ptw_enable`：0 时 `addr[47:42] = 0` 访存触发 CFXMEM（不直通物理存储器），1 时按页表转换；写 PTBR / 写 1 均不隐含 TLB invalidate；复位 PTBR=0、使能=0。
- 保留 cfx（7–14、19–61）的普通 `ld/st` → CFXMEM；`trap`/`escape` 到保留 cfx 仍为 ILLI。
- 页表项统一为 64 位：`HSJU[63:60]`、`PPN[55:16]`（超页 `PPN[55:29]`）、`SPF/GPF[15:8]`、flags `[7:0]`（`P/SP/D/A/G/X/W/R`）；保留位忽略、超页 PPN 非对齐低位强制清零。
- 两级页表：L1/L2 均 64 KiB、8192 项；`VA[41:29]`/`VA[28:16]` 选索引、`VA[15:0]` 为页内偏移；超页 512 MiB、普通页 64 KiB，PA 56 位。
- 页访问权限：HSJU 掩码 + R/W/X 正交检查；异常优先级为「页缺失 → 小页缺失 → HSJU → R/W/X」；页表步进与 TLB 命中异常都进入 `cfx_ptw`。
- PTE `bit4` 由保留改为 **Global（`G`）**：叶子 `G=1` 为全局页、TLB 中跨 ASID 复用；非叶子 `G` 忽略。
- TLB 并入 `cfx_ptw`：删除独立 `cfx_tlb`（`cfxha 5` 未分配）与 `tlb_exist`/`tlb_enable`；16 位 ASID（`cfx_ptw_tlb_asid`）；`cfx_ptw_tlb_control`（`op/scope/ASID_ANY` 正交）+ start/size 失效接口；写 PTBR/ASID/使能均不隐含失效。
- A/D 由硬件在 TLB 条目中维护：填充不产生回写，读/取指置 `A`、写置 `A`/`D`，`CLEAN`/`FLUSH`/替换时原子 OR 回写，`INVALID` 不写回；回写失败报 `cfx_ptw` 的 `PTWERR`（`1 << 7`，`cause_info` = PTE 物理地址）。
- DMA 与 cfx 访问权限不在本版本变更范围内。
- 正文术语统一：地址空间分区一律写作 `addr[47:42]`（地址高 6 位），不再使用讨论期简写。

### 0.7.2（2026-10-26）

- `cfx_time`：per-system 全局时间计数器（`cfx_time_freq`、`cfx_time_value`），只提供时间读数、不产生中断。
- `cfx_hart` 增加每 hart 定时器：`timer_cmp`（比较值）与 `timer_ctrl`（ENABLE/IMASK/ISTATUS），到期触发异步 TIMER 异常（`1 << 10`）；`rc1` 声明为保留。
- 同步异常一律不可屏蔽（含 `SOFT_RESET`）；异常原因掩码只对异步中断生效，异常进入流程第 5 步仅在异步路径设置 pending。
- U-mode `trap` 目标为 `cfx_smon` 时使用 `cfx_smon_user_*`；其余 U-mode 异常固定进入 `cfx_umon`。
- `cg7` 内部存储控制按预留设计：`cfxld`/`cfxst` 尚未启用，未实现的机器对这两条指令 decode ILLI。
- 为 cg0–cg3 增加 `rc0` 版本号寄存器。
- `pending` 统一：删除 timer/uart/power 专有 pending，`cfx_pending`→`excp_pending`（cg5 rc5）。
- 删除 FPEXCP 异常。
- 与上游 SimRISC 0.5.5 基线对齐。
- 版本号常量同步：`user_global_version` = 0.9.3、`supv_global_version` = 0.7.2（jail 同 user）。
- 标题章节号统一为 `N` / `N.M` / `N.M.K`。
- 汇编格式迁移新格式；术语 `cfxcode`→`cfxha`。
- RO 寄存器初始值统一标记为 HW。
- 特权模型与 SimRISC 对齐（`RASUP`→`RASUF`、删冗余 ILLI 声明）。
- 术语「储存块」→「存储块」。
- 多项审查修复（溢出检测 / 跳转表 / 引导 / 掩码 / 注释）。
- 正文术语 `PC` 统一为 **`IP`**（`IP` = 当前正在执行的指令的地址，见 SimRISC-00）：IALIGN 检测（`IP[1:0] ≠ 00`）、异常向量现场值、精确异常现场语义各处。

### 0.7.1（上游基线；导入日 2026-07-14，发布日不详）

- 上游 DADAO 主管系统运行环境（SEE）基线（基于 SimRISC 0.4.1）。
