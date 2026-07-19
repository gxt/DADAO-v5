# DADAO Supervisor Execution Environment（SEE）

> **版本：0.7.1**（与 SBI 版本号一致，同步更新。基于 SimRISC 0.5.3 指令系统设计）

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

| cfxcode | cfxname | 说明 |
|:---:|------|------|
| 0 | umon | 处理 user 模式下的同步异常 |
| 1 | jmon | 处理 jail 模式下的同步异常 |
| 2 | smon | 处理 supv 模式下的同步异常 |
| 3 | hmon | 处理 hypv 模式下的同步异常 |
| 4 | ptw | 页表步进，管理页表 |
| 5 | tlb | TLB 管理 |
| 6 | cache | Cache 管理 |
| 7-14 | reserved | 保留，未定义 |
| 15 | hart | Hart 管理和本地计数 |
| 16 | llc | 最后一级缓存，跨 hart 共享 |
| 17 | pmem | 物理存储器管理 |
| 18 | timer | 定时器/计数器 |
| 19-61 | reserved | 保留，未定义 |
| 62 | uart | 串口控制器 |
| 63 | power | 电源管理 |

每个核芯功能扩展提供自己特有的功能调用，并负责响应和处理所管理设备的中断，因此，异常的进入和退出也都隶属于某个核芯功能扩展：

- 指令执行过程中，核芯触发的同步异常，根据指令执行时的运行模式，分别由 `cfx_umon`/`cfx_jmon`/`cfx_smon`/`cfx_hmon` 进行异常处理
- 地址转换过程中，地址转换部件触发的异常，由 `cfx_ptw` 或 `cfx_tlb` 进行异常处理
- 外部设备触发的异常，根据中断源，分别由相应的核芯功能扩展进行处理

多核系统中各资源的作用域：

| 资源 | 作用域 |
|------|:--:|
| rd/rb/rf/ra、inner_* | per-hart |
| cfx0-cfx15 | per-hart |
| cfx16-cfx63 | per-system |

> `inner_*` 为硬件内部寄存器（不对外暴露），用于异常处理流程中的中间状态保存。`inner_run_mode`（2 位）记录当前偏移运行模式（0=user, 1=jail, 2=supv, 3=hypv），`inner_cfx_mask`（64 位，per-hart）和 `inner_excp_cause_*` 等用于异常屏蔽判断与现场保存。详细语义见 §5 异常进入伪代码。

## 2. 地址空间

CPU 内部地址总线固定为 48 位，若对应的 PTBR 未开启，则不会发生地址转换，此时，仅可以访问核芯内部的资源，可称之为核内地址空间；若对应的 PTBR 开启，则会发生地址转换，则称之为虚拟地址空间。

CPU 外部地址总线固定为 64 位，只有对应的 PTBR 开启，通过地址转换，才会生成访问主存或 IO 的 64 位地址，统称之为物理地址空间。

### 2.1 核内地址空间

48 位核内地址的高 6 位（bits[47:42]）指定了核芯功能扩展编号（cfxcode）。

已分配的核内地址空间如下：

| cfxcode      | 地址空间起始地址          | 地址空间大小          | regname |
| --------  | ------      | --------- | ---------- |
| 63        |  `0xffff_ffff_0000`       | 64KiB             | cfx_power_hypv_excp_vector |

说明：

- cfx_power_hypv_excp_vector 为硬件复位后的启动地址，这部分地址空间可由 CPU 直接取指并执行
- 对核内地址空间进行非法访问时，会触发对应核芯功能扩展的 CFXMEM 异常。核芯功能扩展由地址高 6 位 `addr[47:42]`（即 cfxcode）确定。

### 2.2 虚实地址转换

虚拟地址空间有效位数为 48 位，物理地址空间的有效位数为 64 位。虚拟地址的高 16 位（bits[63:48]）在地址转换过程中被硬件忽略，寄存器中保持原值不变。

#### 2.2.1 超页的地址转换

48位的虚拟地址划分为三个字段：

- `VA[47:42]` -> PTBR index（64 个寄存器，每个寄存器存放一级页表的物理页号，即 `bits[63:16]` ）
- `VA[41:29]` -> L1 index（一级页表的索引，每个一级页表 2^13 个页表项，每个表项 8 字节，即 64KiB）
- `VA[28:00]` -> 页内偏移（超页的页内偏移为 29 位，即 512MiB）

虚拟地址到物理地址的转换分为四步：

**第一步：访问 PTBR**

- 首先，检查当前运行模式是否允许访问该 PTBR 对应的地址空间 —— 通过 `cfx_ptw_user/jail/supv/hypv_perm` 寄存器判断。
  - 若不允许，触发 NUPERM/NJPERM/NSPERM/NHPERM 异常。
- 其次，检查 `cfx_ptw_ptbr_enable` 寄存器中的该 PTBR 对应位是否为 0，若为 0，则不进行地址转换，直接使用 48 位地址访问核芯内部资源。
- 最后，根据 `VA[47:42]` 选择对应的 `cfx_ptw_ptbr` ，该 PTBR 提供 64 位一级页表基地址（bits[63:16] × 64KiB 对齐）。

**第二步：TLB 查找**

- 若 `cfx_tlb_enable` 对应位置 1，则查 TLB。以 `VA[47:42]` 选择对应 TLB 集合，集合内以 L1 index（`VA[41:29]`）作为索引键。
- TLB 命中时直接检查 PTE 中的 SPF/GPF 字段（超页为 SPF 8位、普通页为 GPF 8位）和 R/W/X 权限。SPF/GPF 中对应小页的标记位为 0 触发对应 PFTRAP 异常，权限不符触发 NRPERM/NWPERM/NXPERM 异常。TLB 产生的这些异常属于 cfx_ptw 异常原因的子集，应通过调用 cfx_ptw 的功能来处理。
- 若 TLB 命中且权限符合，则跳过第三步（页表步进），直接进入第四步（形成最终物理地址）。
- 若 TLB 未命中，则继续执行第三步。步进完成后将结果填入对应集合的 TLB。

**第三步：页表步进**

- 用 `VA[41:29]` × 8 计算 L1 页表项偏移，读取 8 字节。
- 若 Superpage 位为 0，则为二级页表 + 普通页，参见 普通页的地址转换。
- 若 Present 位为 0，且 Superpage 位为 1，则触发 ISPTRAP/DSPTRAP 异常。
- 若 Present 位为 1，且 Superpage 位为 1，则进一步检查 SPF 字段中对应小页的标记位；若对应位为 0，则触发 ISPFTRAP/DSPFTRAP 异常。
- 若 Present 位为 1，且 Superpage 位为 1，且 SPF 字段中对应小页的标记位为 1，则检查读/写/执行权限，若权限不符，则触发 NRPERM/NWPERM/NXPERM 异常。
  - 权限检查（R/W/X）也可在地址计算完成后进行。

**第四步：形成最终物理地址**

- 64 位物理地址由以下三部分拼接而成：
  - 根据 `VA[47:42]` 选择对应 `cfx_ptw_pahi` 作为高 16 位，即 `PA[63:48]`
  - 根据 L1 页表项得到的 PPN（bits[47:16]，共32位），取其高19位得到 `PA[47:29]`；低13位 PPN[28:16] 因超页 512MiB 对齐而强制为零
  - 因为是超页，其虚拟地址的页内偏移 `VA[28:00]` 即为物理地址的页内偏移 `PA[28:00]`。

#### 2.2.2 普通页的地址转换

48位的虚拟地址划分为四个字段：

- `VA[47:42]` -> PTBR index（64 个寄存器，每个寄存器内容为一级页表的物理页号，即 `bits[63:16]` ）
- `VA[41:29]` -> L1 index（一级页表的索引，每个一级页表 2^13 个页表项，每个表项 8 字节，即 64KiB）
- `VA[28:16]` -> L2 index（二级页表的索引，每个二级页表 2^13 个页表项，每个表项 8 字节，即 64KiB）
- `VA[15:00]` -> 页内偏移（普通页的页内偏移为 16 位，即 64KiB）

虚拟地址到物理地址的转换分为四步：

**第一步：访问 PTBR**

- 首先，检查当前运行模式是否允许访问该 PTBR 对应的地址空间 —— 通过 `cfx_ptw_user/jail/supv/hypv_perm` 寄存器判断。
  - 若不允许，触发 NUPERM/NJPERM/NSPERM/NHPERM 异常。
- 其次，检查 `cfx_ptw_ptbr_enable` 寄存器中的该 PTBR 对应位是否为 0，若为 0，则不进行地址转换，直接使用 48 位地址访问核芯内部资源。
- 最后，根据 `VA[47:42]` 选择对应的 `cfx_ptw_ptbr` ，该 PTBR 提供 64 位一级页表基地址（bits[63:16] × 64KiB 对齐）。

**第二步：TLB 查找**

- 若 `cfx_tlb_enable` 对应位置 1，则查 TLB。以 `VA[47:42]` 选择对应 TLB 集合，集合内以 L1 index（`VA[41:29]`）和 L2 index（`VA[28:16]`）作为索引键。
- TLB 命中时直接检查 PTE 中的 SPF/GPF 字段（超页为 SPF 8位、普通页为 GPF 8位）和 R/W/X 权限。SPF/GPF 中对应小页的标记位为 0 触发对应 PFTRAP 异常，权限不符触发 NRPERM/NWPERM/NXPERM 异常。TLB 产生的这些异常属于 cfx_ptw 异常原因的子集，应通过调用 cfx_ptw 的功能来处理。
- 若 TLB 命中且权限符合，则跳过第三步（页表步进），直接进入第四步（形成最终物理地址）。
- 若 TLB 未命中，则继续执行第三步。步进完成后将结果填入对应集合的 TLB。

**第三步：页表步进**

- 用 `VA[41:29]` × 8 计算 L1 页表项偏移，读取 8 字节。
- 若 Superpage 位为 1，则为一级页表 + 超页，参见 超页的地址转换。
- 若 Present 位为 0，且 Superpage 位为 0，则触发 IGPTRAP/DGPTRAP 异常。
- 生成二级页表的访问地址，读取 8 字节：
  - 根据 `VA[47:42]` 选择对应 `cfx_ptw_pthi` 作为高 16 位，即 `L2PA[63:48]`（pthi 用于页表结构的物理地址高位，与第四步最终数据页物理地址使用的 pahi 不同）
  - 根据 L1 页表项得到的 PPN ，作为中间 32 位，即 `L2PA[47:16]`
  - 用 `VA[28:16]` × 8 计算二级页表的索引，即 L2 页表项偏移 `L2PA[15:3]`
- 若 Present 位为 0，则触发 IGPTRAP/DGPTRAP 异常。
- 若 Present 位为 1，则进一步检查 GPF 字段中对应小页的标记位；若对应位为 0，则触发 IGPFTRAP/DGPFTRAP 异常。
- 若 Present 位为 1，且 GPF 字段中对应小页的标记位为 1，则检查读/写/执行权限，若权限不符，则触发 NRPERM/NWPERM/NXPERM 异常。
  - 权限检查（R/W/X）也可在地址计算完成后进行。

**第四步：形成最终物理地址**

- 64 位物理地址由以下三部分拼接而成：
  - 根据 `VA[47:42]` 选择对应 `cfx_ptw_pahi` 作为高 16 位，即 `PA[63:48]`
  - 根据 L2 页表项得到的 PPN ，共32位，得到 `PA[47:16]`
  - 因为是普通页，其虚拟地址的页内偏移 `VA[15:00]` 即为物理地址的页内偏移 `PA[15:00]`。

#### 2.2.3 一级页表条目格式

**下一级为二级页表时**

| 位           | 含义        | 英文缩写 | 说明                 |
| ----------- | ----------- | ------ | ------------------ |
| bits[63:48] | 保留         | —      | 须写 0 |
| bits[47:16] | 物理页号     | PPN    | 指向二级页表，64KiB对齐 |
| bits[15:2]  | 保留         | —      | 须写 0 |
| bit1        | Superpage   | SP = 0 | 0不是超页，1是超页（仅L1时有效） |
| bit0        | Present     | P      | 0无效，1有效            |

**下一级为超页时**

| 位           | 含义        | 英文缩写 | 说明                 |
| ----------- | ----------- | ------ | ------------------ |
| bits[63:56] | 小页在内存标记 | SPF     | SPF字段的每一位对应一个小页是否在内存中，0不在内存，1在内存 |
| bits[55:48] | 保留         | —      | 须写 0 |
| bits[47:16] | 物理页号     | PPN    | 指向物理页，512 MiB对齐；非对齐的低位强制清零 |
| bits[15:8]  | 保留         | —      | 须写 0 |
| bit7        | READ        | R      | 0不可读，1可读           |
| bit6        | WRITE       | W      | 0不可写，1可写           |
| bit5        | EXEC        | X      | 0不可执行，1可执行         |
| bit4        | 保留         | —      | 须写 0 |
| bit3        | Access      | A      | 0未被访问，1有访问         |
| bit2        | Dirty       | D      | 0未被修改，1有修改         |
| bit1        | Superpage   | SP = 1 | 0不是超页，1是超页（仅L1时有效） |
| bit0        | Present     | P      | 0无效，1有效            |

超页大小为2^29字节（512 MiB），划分为8个小页，每个小页大小为2^26字节（64 MiB）。超页的虚拟地址和物理地址需要 512 MiB 对齐，其内部小页 64 MiB 对齐。

物理超页分配由操作系统负责预留对应的物理地址空间；物理超页从外存加载时，由操作系统决定具体加载的小页位置与数量。

A 位和 D 位为访问和修改标记，由硬件负责更新。硬件在更新 TLB 内条目的同时，对主存中的 PTE 表项执行原子读-修改-写，将对应位置 1。

#### 2.2.4 二级页表条目格式

| 位           | 含义        | 英文缩写 | 说明                 |
| ----------- | ----------- | ------ | ------------------ |
| bits[63:56] | 小页在内存标记 | GPF     | GPF字段的每一位对应一个小页是否在内存中，0不在内存，1在内存 |
| bits[55:48] | 保留         | —      | 须写 0 |
| bits[47:16] | 物理页号  | PPN    | 指向物理页，64KiB对齐；非对齐的低位强制清零 |
| bits[15:8]  | 保留         | —      | 须写 0 |
| bit7        | READ        | R      | 0不可读，1可读           |
| bit6        | WRITE       | W      | 0不可写，1可写           |
| bit5        | EXEC        | X      | 0不可执行，1可执行         |
| bit4        | 保留         | —      | 须写 0 |
| bit3        | Access      | A      | 0未被访问，1有访问         |
| bit2        | Dirty       | D      | 0未被修改，1有修改         |
| bit1        | 保留         | —      | 须写 0 |
| bit0        | Present     | P      | 0无效，1有效            |

A 位和 D 位为访问和修改标记，由硬件负责更新。硬件在更新 TLB 内条目的同时，对主存中的 PTE 表项执行原子读-修改-写，将对应位置 1。

普通页大小为2^16字节（64 KiB），划分为8个小页（GPF, Page Fragment），每个小页大小为2^13字节（8 KiB）。普通页的虚拟地址和物理地址需要 64 KiB 对齐，其内部小页 8 KiB 对齐。

物理页分配由操作系统负责预留对应的物理地址空间；物理页从外存加载时，由操作系统决定具体加载的小页位置与数量。

#### 2.2.5 操作系统页管理

**Global 位**

页表项中不再设置 Global 位。TLB 按 VA[47:42]（PTBR 索引）划分为 64 个独立集合，每个 PTBR 独占一个集合。进程切换时，只需 invalid 该 PTBR 对应集合的 TLB 表项，其他 PTBR 的 TLB 缓存不受影响。需要在多个地址空间共享的页（如内核页），在各 PTBR 各自的页表中映射相同物理页即可，无需 G 位标记。

**小页（Fragment）**

超页（512 MiB）和普通页（64 KiB）均划分为 8 个小页，分别由 L1 PTE 的 SPF 字段和 L2 PTE 的 GPF 字段指示各小页是否已在物理内存中。SPF/GPF 的 bit[56] 对应页面内最低地址片段（超页 offset 0-64MiB，普通页 offset 0-8KiB），bit[63] 对应最高地址片段，按地址递增排列。Fragment 机制节省外存 I/O 而非物理内存——物理页完整空间须预先分配。若操作系统不需要按需加载，可将 SPF/GPF 全部置 1，此时等同于无 fragment 的整页加载。

**进程上下文切换**

操作系统在切换进程时须执行以下步骤：

1. 通过 cfx_tlb 将旧进程的 PTBR 对应 TLB 集合 invalid（`tlb_addr_start[47:42]` = 旧 PTBR 编号，`tlb_addr_size` = 0x40000000000（2^42））
2. 通过 cfx_ptw 设置新进程的 PTBR（`SBI_PTW_SET_PTBR`）
3. 通过 cfx_tlb 使能新 PTBR 的 TLB（设置 `cfx_tlb_enable` 对应位置 1）
4. 保存和恢复暂存寄存器（cg6）

#### 2.2.6 异常检查优先级

当多个异常条件同时满足时，硬件按以下顺序检查，触发第一个满足条件的异常：

**跨类别优先级**（指令执行流水线从前到后）：

1. IALIGN——取指前检测 PC[1:0] ≠ 00
2. ILLI/UNDI——译码阶段
3. MALIGN——地址计算后、访存前
4. 页表异常——TLB/PTW 访存阶段（以下细表）
5. FPEXCP——浮点执行阶段（指令完成后检测，若同时有页表异常则页表异常优先）

**页表步进内部优先级**：

1. PTBR 模式权限不符 → NUPERM/NJPERM/NSPERM/NHPERM
2. L1 Present = 0 → IGPTRAP/DGPTRAP（超页则 ISPTRAP/DSPTRAP）
3. L1 Present = 1, SPF 字段中对应标记位 = 0（仅超页）→ 对应 I/DPFTRAP
4. L2 Present = 0（普通页）→ IGPTRAP/DGPTRAP
5. L2 Present = 1, GPF 字段中对应标记位 = 0（普通页）→ 对应 I/DPFTRAP
6. 权限不符（R/W/X）→ NRPERM/NWPERM/NXPERM

仅触发优先级最高的异常，后续检查不再执行。

## 3. 共有寄存器设计规范

cg0-cg7 为共有寄存器设计，不同的核芯功能扩展设计规范相同。

### cg0 - user mode 寄存器

每个核芯功能扩展中针对用户模式（user）有以下12个寄存器（cg=0）：

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 0 | 0 | user global version | cfx_⟨cfxname⟩_user_global_version | 0x00090002 | RO | AEE 版本号：`(major<<32)\|(minor<<16)\|patch`，当前 0.9.2。全局寄存器 |
| 0 | 1 | user global cfx mask | cfx_⟨cfxname⟩_user_global_cfx_mask | 全1 | RW | 全局核芯功能扩展掩码，0=可触发，1=屏蔽。自身 cfxcode 对应位硬件忽略 |
| 0 | 2 | user cfx2rd cfx mask | cfx_⟨cfxname⟩_user_cfx2rd_cfx_mask | 全1 | RW | cfx2rd 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxcode 对应位硬件忽略 |
| 0 | 3 | user cfx2rc cfx mask | cfx_⟨cfxname⟩_user_cfx2rc_cfx_mask | 全1 | RW | cfx2rc 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxcode 对应位硬件忽略 |
| 0 | 4 | user cfxld cfx mask | cfx_⟨cfxname⟩_user_cfxld_cfx_mask | 全1 | RW | cfxld 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxcode 对应位硬件忽略 |
| 0 | 5 | user cfxst cfx mask | cfx_⟨cfxname⟩_user_cfxst_cfx_mask | 全1 | RW | cfxst 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxcode 对应位硬件忽略 |
| 0 | 6 | user trap cfx mask | cfx_⟨cfxname⟩_user_trap_cfx_mask | 全1 | RW | trap 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxcode 对应位硬件忽略 |
| 0 | 7 | user escape cfx mask | cfx_⟨cfxname⟩_user_escape_cfx_mask | 全1 | RW | escape 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxcode 对应位硬件忽略 |
| 0 | 8 | user switch run mode | cfx_⟨cfxname⟩_user_switch_run_mode | 2 (S-mode) | RW | 从user陷入时切换的运行模式 |
| 0 | 9 | user switch cfx mask | cfx_⟨cfxname⟩_user_switch_cfx_mask | 全1 | RW | 从user陷入时采用的异常掩码，0=可触发，1=屏蔽 |
| 0 | 10 | user excp vector | cfx_⟨cfxname⟩_user_excp_vector | 0 | RW | 从user陷入时的异常向量入口地址 |
| 0 | 11 | user excp mask | cfx_⟨cfxname⟩_user_excp_cause_mask | 全1 | RW | user异常原因掩码，0=可触发，1=屏蔽 |

`user global` 开头的寄存器为全局寄存器，即所有核芯功能扩展共享同一个寄存器。

为支持用户程序通过系统调用陷入操作系统内核，硬件应至少支持 `cfx_umon_user_*` 这一组寄存器或 `cfx_smon_user_*` 这一组寄存器。

### cg1 - jail mode 寄存器

jail mode 为受限用户模式，MVP 阶段与 user mode 行为一致。受限规则（如禁止指令、二阶段翻译等）留待后续版本定义。

每个核芯功能扩展中针对监狱模式（jail）有以下12个寄存器（cg=1）：

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 1 | 0 | jail global version | cfx_⟨cfxname⟩_jail_global_version | 0x00090002 | RO | jail 版本号，MVP 阶段与 user 版本号相同。全局寄存器 |
| 1 | 1 | jail global cfx mask | cfx_⟨cfxname⟩_jail_global_cfx_mask | 全1 | RW | 全局核芯功能扩展掩码，0=可触发，1=屏蔽。自身 cfxcode 对应位硬件忽略 |
| 1 | 2 | jail cfx2rd cfx mask | cfx_⟨cfxname⟩_jail_cfx2rd_cfx_mask | 全1 | RW | cfx2rd 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxcode 对应位硬件忽略 |
| 1 | 3 | jail cfx2rc cfx mask | cfx_⟨cfxname⟩_jail_cfx2rc_cfx_mask | 全1 | RW | cfx2rc 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxcode 对应位硬件忽略 |
| 1 | 4 | jail cfxld cfx mask | cfx_⟨cfxname⟩_jail_cfxld_cfx_mask | 全1 | RW | cfxld 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxcode 对应位硬件忽略 |
| 1 | 5 | jail cfxst cfx mask | cfx_⟨cfxname⟩_jail_cfxst_cfx_mask | 全1 | RW | cfxst 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxcode 对应位硬件忽略 |
| 1 | 6 | jail trap cfx mask | cfx_⟨cfxname⟩_jail_trap_cfx_mask | 全1 | RW | trap 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxcode 对应位硬件忽略 |
| 1 | 7 | jail escape cfx mask | cfx_⟨cfxname⟩_jail_escape_cfx_mask | 全1 | RW | escape 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxcode 对应位硬件忽略 |
| 1 | 8 | jail switch run mode | cfx_⟨cfxname⟩_jail_switch_run_mode | 2 (supv) | RW | 从jail陷入时切换的运行模式 |
| 1 | 9 | jail switch cfx mask | cfx_⟨cfxname⟩_jail_switch_cfx_mask | 全1 | RW | 从jail陷入时采用的异常掩码，0=可触发，1=屏蔽 |
| 1 | 10 | jail excp vector | cfx_⟨cfxname⟩_jail_excp_vector | 0 | RW | 从jail陷入时的异常向量入口地址 |
| 1 | 11 | jail excp mask | cfx_⟨cfxname⟩_jail_excp_cause_mask | 全1 | RW | 异常原因掩码，0=可触发，1=屏蔽 |

`jail global` 开头的寄存器为全局寄存器，即所有核芯功能扩展共享同一个寄存器。

### cg2 - supv mode 寄存器

每个核芯功能扩展中针对主管模式（supv）有以下12个寄存器（cg=2）：

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 2 | 0 | supv global version | cfx_⟨cfxname⟩_supv_global_version | 0x00070001 | RO | SEE 版本号：`(major<<32)\|(minor<<16)\|patch`，当前 0.7.1。全局寄存器 |
| 2 | 1 | supv global cfx mask | cfx_⟨cfxname⟩_supv_global_cfx_mask | 全1 | RW | 全局核芯功能扩展掩码，0=可触发，1=屏蔽。自身 cfxcode 对应位硬件忽略 |
| 2 | 2 | supv cfx2rd cfx mask | cfx_⟨cfxname⟩_supv_cfx2rd_cfx_mask | 全1 | RW | cfx2rd 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxcode 对应位硬件忽略 |
| 2 | 3 | supv cfx2rc cfx mask | cfx_⟨cfxname⟩_supv_cfx2rc_cfx_mask | 全1 | RW | cfx2rc 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxcode 对应位硬件忽略 |
| 2 | 4 | supv cfxld cfx mask | cfx_⟨cfxname⟩_supv_cfxld_cfx_mask | 全1 | RW | cfxld 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxcode 对应位硬件忽略 |
| 2 | 5 | supv cfxst cfx mask | cfx_⟨cfxname⟩_supv_cfxst_cfx_mask | 全1 | RW | cfxst 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxcode 对应位硬件忽略 |
| 2 | 6 | supv trap cfx mask | cfx_⟨cfxname⟩_supv_trap_cfx_mask | 全1 | RW | trap 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxcode 对应位硬件忽略 |
| 2 | 7 | supv escape cfx mask | cfx_⟨cfxname⟩_supv_escape_cfx_mask | 全1 | RW | escape 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxcode 对应位硬件忽略 |
| 2 | 8 | supv switch run mode | cfx_⟨cfxname⟩_supv_switch_run_mode | 2 (supv) | RW | 从supv陷入时切换的运行模式 |
| 2 | 9 | supv switch cfx mask | cfx_⟨cfxname⟩_supv_switch_cfx_mask | 全1 | RW | 从supv陷入时采用的异常掩码，0=可触发，1=屏蔽 |
| 2 | 10 | supv excp vector | cfx_⟨cfxname⟩_supv_excp_vector | 0 | RW | 从supv陷入时的异常向量入口地址 |
| 2 | 11 | supv excp mask | cfx_⟨cfxname⟩_supv_excp_cause_mask | 全1 | RW | 异常原因掩码，0=可触发，1=屏蔽 |

`supv global` 开头的寄存器为全局寄存器，即所有核芯功能扩展共享同一个寄存器。

### cg3 - hypv mode 寄存器

H-mode 寄存器（cg=3）定义见 HEE 文档 §1。

### cg4 - 核芯功能扩展配置寄存器

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

### cg5 - 异常现场寄存器

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

所有异常原因编码为 one-hot（64 位），各核芯功能扩展的异常原因表定义该核芯功能扩展可处理的异常位。表中未列出的位属于保留或未使用，若硬件错误触发此类位，表示该核芯功能扩展出现不可恢复的错误。`1 << 3` 至 `1 << 7` 保留用于未来扩展（debug 异常等）。

### cg6 - 暂存寄存器

每个核芯功能扩展都有暂存寄存器（cg=6），数量由 `cfx_⟨cfxname⟩_scratch_regs_num`（cg=4, rc=6）指定，硬件实现至少 2 个、最多 64 个。

暂存寄存器从 rc=0 开始连续分配。`cfx_⟨cfxname⟩_scratch_regs_num` = N 时，有效的暂存寄存器为 rc=0 至 rc=N−1。读写不存在或超出数量的暂存寄存器（rc ≥ N）触发 CFXREG 异常。

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 6 | 0−(N−1) | scratch regs | cfx_⟨cfxname⟩_scratch_regs[0..N−1] | 未定义 | RW | 暂存寄存器（软件用） |

### cg7 - 内部存储控制寄存器

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

### cfx_umon - user monitor

**异常原因表**

| excp cause id | 名称      | 触发条件      | 是否可屏蔽 | excp cause info                |
| --------   | ------  | --------- | ---------- | ---------                   |
| `1 << 0`   | CFXTRAP | 功能调用      | 否 | 指令编码                        |
| `1 << 1`   | CFXMEM  | 访问核内地址空间或内部储存块故障 | 否 | 访存地址                        |
| `1 << 2`   | CFXREG   | 非法核芯功能扩展寄存器访问 | 否 | 指令编码         |
| `1 << 8`   | ILLI    | 非法指令      | 否 | 指令编码                        |
| `1 << 9`   | UNDI    | 未定义指令     | 否 | 指令编码                        |
| `1 << 10`  | RASOF   | RAS上溢     | 否 | 准备压栈的返回地址                   |
| `1 << 11`  | RASUF   | RAS下溢     | 否 | 全零（无效）                      |
| `1 << 12`  | MALIGN  | 非对齐访存    | 否 | 访存地址                        |
| `1 << 13`  | IALIGN  | 取指未对齐    | 否 | PC 值                          |
| `1 << 32`  | FPEXCP  | 浮点异常      | 可 | 异常结果（浮点运算部件给出，通常为qNaN或sNaN） |

### cfx_jmon - jail monitor

异常原因编码与 cfx_umon 一致。

### cfx_smon - supervisor monitor

异常原因编码与 cfx_umon 一致。

### cfx_hmon - hypervisor monitor

异常原因编码与 cfx_umon 一致。详细定义见 HEE 文档 §2。

### cfx_ptw - page table walker

**专有寄存器表**

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 8 | 0 | ptw user perm | cfx_ptw_user_perm | 全0 | RW | user的PTBR权限位图，0=禁止，1=允许 |
| 8 | 1 | ptw jail perm | cfx_ptw_jail_perm | 全0 | RW | jail的PTBR权限位图 |
| 8 | 2 | ptw supv perm | cfx_ptw_supv_perm | 全1 | RW | supv的PTBR权限位图 |
| 8 | 3 | ptw hypv perm | cfx_ptw_hypv_perm | 全1 | RW | hypv的PTBR权限位图 |
| 8 | 8 | ptw ptbr enable | cfx_ptw_ptbr_enable | 全0 | RW | PTBR使能位图，0=disable，1=enable |
| 9 | 0-63 | ptw ptbr | cfx_ptw_ptbr[0..63] | 0 | RW | 页表基地址物理地址高48位（bits[63:16]），低16位强制为0（64KiB 对齐） |
| 10 | 0-63 | ptw pthi | cfx_ptw_pthi[0..63] | 0 | RW | 页表结构物理地址高16位 |
| 11 | 0-63 | ptw pahi | cfx_ptw_pahi[0..63] | 0 | RW | 物理地址高16位 |

**异常原因表**

| excp cause id | 名称     | 触发条件      | 是否可屏蔽 | excp cause info |
| --------   | ------ | --------- | ---------- | ---------    |
| `1 << 0`   | CFXTRAP  | 功能调用      | 否 | 指令编码         |
| `1 << 1`   | CFXMEM   | 访问核内地址空间或内部储存块故障 | 否 | 访存地址         |
| `1 << 2`   | CFXREG   | 非法核芯功能扩展寄存器访问 | 否 | 指令编码         |
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

### cfx_tlb - TLB management

**专有寄存器表**

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 8 | 0 | tlb exist | cfx_tlb_exist | — | RO | 硬件设置，指示对应VA空间是否有TLB |
| 8 | 8 | tlb enable | cfx_tlb_enable | 同 tlb_exist | RW | 软件配置，0=关闭，1=开启。复位后每一位等于对应 tlb_exist 位的值（即已存在 TLB 的集合默认开启） |
| 12 | 0 | tlb control | cfx_tlb_control | 0 | WO | bit0=invalid all；bit1=invalid by addr range |
| 12 | 1 | — | — | — | — | 保留 |
| 12 | 2 | tlb addr start | cfx_tlb_addr_start | 0 | RW | TLB操作的起始虚拟地址 |
| 12 | 3 | tlb addr size | cfx_tlb_addr_size | 65536 | RW | TLB操作的地址范围大小 |

TLB 按虚拟地址的 VA[47:42]（PTBR 索引）划分为 64 个独立集合，每个集合对应一个 PTBR 的 TLB 表项。硬件实现可简化集合数量，但必须与软件约定一致。

TLB 操作的目标集合由 `tlb_addr_start[47:42]` 指定，集合内的 VA 范围由 `tlb_addr_start[41:16]` 和 `tlb_addr_size` 限定。invalid all 操作作用于全部 64 个集合。

**异常原因表**

| excp cause id | 名称     | 触发条件      | 是否可屏蔽 | excp cause info |
| --------   | ------ | --------- | ---------- | ---------    |
| `1 << 0`   | CFXTRAP  | 功能调用      | 否 | 指令编码         |
| `1 << 1`   | CFXMEM   | 访问核内地址空间或内部储存块故障 | 否 | 访存地址         |
| `1 << 2`   | CFXREG   | 非法核芯功能扩展寄存器访问 | 否 | 指令编码         |
| `1 << 12`  | NXPERM   | 执行不可执行页   | 否 | 取指地址         |
| `1 << 13`  | NWPERM   | 写不可写页     | 否 | 读写地址         |
| `1 << 14`  | NRPERM   | 读不可读页     | 否 | 读写地址         |
| `1 << 18`  | IGPFTRAP | 取指普通页小页缺失 | 否 | 取指地址         |
| `1 << 19`  | ISPFTRAP | 取指超页小页缺失  | 否 | 取指地址         |
| `1 << 22`  | DGPFTRAP | 数据读写普通页小页缺失 | 否 | 读写地址         |
| `1 << 23`  | DSPFTRAP | 数据读写超页小页缺失 | 否 | 读写地址         |

TLB 产生的上述异常是 cfx_ptw 异常原因的子集。TLB handler 应通过调用 cfx_ptw 的功能（如 SBI_PTW_HANDLE_FAULT 等）来处理，并在 ptw 处理完成返回后，根据返回值对 TLB 表项执行相应的 invalid 或填充操作。

### cfx_cache - cache organization

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
| `1 << 1`   | CFXMEM   | 访问核内地址空间或内部储存块故障 | 否 | 访存地址         |
| `1 << 2`   | CFXREG   | 非法核芯功能扩展寄存器访问 | 否 | 指令编码         |

### cfx_hart - hart management

管理独立的指令流水线（hart）。多核时每个 hart 有独立的 cfx_hart。

**专有寄存器表**

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 8 | 0 | hart id | cfx_hart_hart_id | — | RO | 硬件设置，hart 编号（0-based） |
| 8 | 2 | cycle lo | cfx_hart_cycle_lo | 0 | RO | 本地周期数低64位 |
| 8 | 3 | cycle hi | cfx_hart_cycle_hi | 0 | RO | 本地周期数高64位 |
| 8 | 4 | insn lo | cfx_hart_insn_lo | 0 | RO | 指令计数低64位 |
| 8 | 5 | insn hi | cfx_hart_insn_hi | 0 | RO | 指令计数高64位 |

**异常原因表**

| excp cause id | 名称     | 触发条件      | 是否可屏蔽 | excp cause info |
| --------   | ------ | --------- | ---------- | ---------    |
| `1 << 0`   | CFXTRAP  | 功能调用      | 否 | 指令编码         |
| `1 << 1`   | CFXMEM   | 访问核内地址空间或内部储存块故障 | 否 | 访存地址         |
| `1 << 2`   | CFXREG   | 非法核芯功能扩展寄存器访问 | 否 | 指令编码         |
| `1 << 8`   | IPI       | 核间中断      | 可 | 中断源 hart ID（低 6 位有效，高 58 位保留为 0） |

### cfx_llc - last level cache

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
| `1 << 1`   | CFXMEM   | 访问核内地址空间或内部储存块故障 | 否 | 访存地址         |
| `1 << 2`   | CFXREG   | 非法核芯功能扩展寄存器访问 | 否 | 指令编码         |

### cfx_pmem - physical memory management

cfx_pmem 管理物理存储器（Physical Memory, PM）区域，最多支持 64 个不连续 PM 区域。PM 仅指普通 DRAM 存储器，与 device 或 MMIO 无关——device 的存储空间由各设备核芯功能扩展自行管理。

**专有寄存器表**

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 8 | 0 | pmem exist | cfx_pmem_exist | — | RO | 硬件设置，指示PM区域是否存在 |
| 12 | 0-63 | pmem start | cfx_pmem_start[0..63] | 0 | RW | PM区域起始物理地址 |
| 13 | 0-63 | pmem size | cfx_pmem_size[0..63] | 0 | RW | PM区域大小（0=未使用） |
| 14 | 0-63 | pmem attr | cfx_pmem_attr[0..63] | 0 | RW | bit0=prefetchable，bit1=coherent |

多个 PM 区域可以不连续。若区域地址重叠，按编号小的优先级高。硬件访问物理地址时，按 PM 编号从 0 开始匹配，匹配到的第一个区域的属性决定该访问的行为（预取策略、Cache 一致性等）。

**异常原因表**

| excp cause id | 名称     | 触发条件      | 是否可屏蔽 | excp cause info |
| --------   | ------ | --------- | ---------- | ---------    |
| `1 << 0`   | CFXTRAP  | 功能调用      | 否 | 指令编码         |
| `1 << 1`   | CFXMEM   | 访问核内地址空间或内部储存块故障 | 否 | 访存地址         |
| `1 << 2`   | CFXREG   | 非法核芯功能扩展寄存器访问 | 否 | 指令编码         |

> shareability、inner/outer cacheability 等进阶属性留待多核 SMP 阶段再定义。当前单核 MVP 仅需 prefetchable 和 coherent 位即可满足。

### cfx_timer - timer/counter

**专有寄存器表**

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 10 | 7 | timer ctrl | cfx_timer_ctrl | 0 | RW | bit0=enable(1=启动)，bit1=mode(0=one-shot,1=periodic)，bit2=dir(0=decrement,1=increment)，bits[63:3]保留 |
| 10 | 8-15 | timer regs | cfx_timer_regs[0..7] | 0 | RW | 定时器计数器 |

**异常原因表**

| excp cause id | 名称          | 触发条件      | 是否可屏蔽 | excp cause info |
| --------   | ------      | --------- | ---------- | ---------    |
| `1 << 0`   | CFXTRAP     | 功能调用      | 否 | 指令编码         |
| `1 << 1`   | CFXMEM      | 访问核内地址空间或内部储存块故障 | 否 | 访存地址         |
| `1 << 2`   | CFXREG      | 非法核芯功能扩展寄存器访问 | 否 | 指令编码         |
| `1 << 10`  | TIMER       | 本地定时器     | 可 | 全零         |

### cfx_uart - uart

**专有寄存器表**

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 8 | 1 | uart exist | cfx_uart_exist | — | RO | 硬件设置，指示UART是否有效 |
| 32 | 0-63 | uart0 regs | cfx_uart_uart0_regs[0..63] | — | RW | 参照硬件协议 |
| 33 | 0-63 | uart1 regs | cfx_uart_uart1_regs[0..63] | — | RW | 参照硬件协议 |
| ... | ... | ... | ... | ... | ... | ... |
| 63 | 0-63 | uart31 regs | cfx_uart_uart31_regs[0..63] | — | RW | 参照硬件协议 |

UART寄存器的读写操作通过 `cfx2rd`/`cfx2rc` 指令完成。若寄存器的读写宽度为8位或16位，则单独分配一个64位寄存器号。

**异常原因表**

| excp cause id | 名称      | 触发条件      | 是否可屏蔽 | excp cause info |
| --------   | ------  | --------- | ---------- | ---------       |
| `1 << 0`   | CFXTRAP     | 功能调用      | 否 | 指令编码          |
| `1 << 1`   | CFXMEM  | 访问核内地址空间或内部储存块故障 | 否 | 访存地址 |
| `1 << 2`   | CFXREG  | 非法核芯功能扩展寄存器访问 | 否 | 指令编码 |
| `1 << 32`  | UART0   | UART0中断    | 可 | 全零              |
| `1 << 33`  | UART1   | UART1中断    | 可 | 全零              |
| `1 << 34`  | UART2   | UART2中断    | 可 | 全零              |
| ...        | ...     | ...        | 可 | 全零              |
| `1 << 63`  | UART31  | UART31中断   | 可 | 全零              |

### cfx_power - power management

**专有寄存器表**

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 8 | 1 | power ctrl | cfx_power_ctrl | 0 | WO | bit0=关机，bit1=硬复位，bit2=软复位 |

**异常原因表**

| excp cause id | 名称          | 触发条件      | 是否可屏蔽 | excp cause info |
| --------   | ------      | --------- | ---------- | ---------    |
| `1 << 0`   | CFXTRAP     | 功能调用      | 否 | 指令编码         |
| `1 << 1`   | CFXMEM      | 访问核内地址空间或内部储存块故障 | 否 | 访存地址         |
| `1 << 2`   | CFXREG      | 非法核芯功能扩展寄存器访问 | 否 | 指令编码         |
| `1 << 8`   | POWEROFF    | 硬件关机      | 否 | 全零         |
| `1 << 9`   | HARD_RESET | 硬件重启      | 否 | 全零         |
| `1 << 10`  | SOFT_RESET | 软件重启      | 可 | 指令编码         |

## 5. 异常进入与异常退出

**重要**：异常原因编码（`excp cause id`，即 `1 << n` 中的位索引 `n`）在各核芯功能扩展间 **独立编址**，不存在跨 cfx 冲突。例如 `1<<8` 在 cfx_umon 中为 ILLI，在 cfx_ptw 中为 NUPERM，在 cfx_hart 中为 IPI——它们属于不同 cfx 的异常表，互不干扰。每个 cfx 的异常原因编码空间为 0-63，硬件通过 cfxcode 区分目标。

**精确异常**：所有同步异常和异步中断均为精确异常——PC 指向触发指令（同步）或下一条指令边界（异步），指令未完成，目标寄存器/内存/RA 未更新（无副作用）。页表步进异常（GPTRAP/SPTRAP/PFTRAP/NxPERM）同为精确——访存未执行。IALIGN 为精确异常——取指前检测 PC[1:0] ≠ 00，PC 停留在非法地址。FPEXCP 被屏蔽时结果寄存器按 IEEE 754 写入正常计算结果，设置 pending 位，mask 解除后触发异常；未被屏蔽时与其他同步异常一致，硬件保证无副作用。

**中断信号为电平触发**：硬件源持续有效且 mask 开启时，中断在指令边界检查并触发。mask 解除后若 pending 仍置 1，在下一指令边界触发中断。多个 pending 位同时置 1 或不同 cfx 同时产生中断时，低编号 cfxcode 优先。

**系统控制例外**：POWEROFF/HARD_RESET/SOFT_RESET 为系统控制动作，不适用一般异常处理的 PC/寄存器保存语义。

**异常嵌套由软件解决**：各核芯功能扩展如可能发生同 cfx 嵌套异常，应在进入功能处理函数前保存当前异常现场（`excp_prev_*`、`excp_cause_*`），退出时恢复。硬件不阻止同 cfx 嵌套，但若软件未保存现场，再次进入会覆盖上一次的现场数据。

### 指令行为说明

trap/escape/cfxld/cfxst/cfx2rd/cfx2rc 指令可以在任意运行模式下执行。若 cfxcode 为 reserved 核芯功能扩展（7-14、19-61），硬件触发 ILLI 异常。对于常见的操作系统而言，并不希望由 user/jail 直接陷入或访问 hmon 到 power 之间的核芯功能扩展，则需要在这些核芯功能扩展的初始化代码中，设置好屏蔽位（缺省为屏蔽）。

escape 指令的第一个参数会指定 cfxcode，通常该参数应该和当前的核芯功能扩展编号相同，但是硬件实现并不检查其一致性，因此可以采用不同的核芯功能扩展编号，从而可以跳过多层核芯功能扩展的调用，直接跳到需要返回的指令指针。可以通过检查 `cfx_⟨cfxname⟩_trap_num + cfx_⟨cfxname⟩_excp_sync_num + cfx_⟨cfxname⟩_excp_async_num` 是否与 `cfx_⟨cfxname⟩_escape_num` 匹配，来判断是否有此类现象存在。

escape指令的第二个参数，imms18 按指令字偏移（×4 字节），常见用法如下：

| 用例 | 指令 | 返回位置 |
|------|------|---------|
| 重新执行触发异常的指令 | `escape cfxcode, 0` | cause_ip |
| 跳过触发指令（继续执行） | `escape cfxcode, 1` | cause_ip + 4 |
| 跳过 N 条指令（N 可为负数表示回退） | `escape cfxcode, N` | cause_ip + N×4 |

**跨 cfx escape 的安全约束**：escape 指定非当前 cfxcode 时，硬件不保存跳过的中间 cfx 现场。`excp_prev_run_mode` 和 `excp_prev_cfx_mask` 恢复的是**最初 trap 进入当前调用链时的值**（非最近一次 trap 的）。调用链 A→B→C 中，若 B 中使用 `escape cfx_A, N`，硬件直接恢复到 A 的 prev 现场，B 的现场（excp_prev_*/excp_cause_*）被静默丢弃。软件必须保证被跳过的 cfx 不再需要返回（即 B 的调用链已终结，B 不会再次被 escape 回）。

### 异常进入流程

X-mode（任意运行模式）下发生异常时，硬件自动执行以下操作序列：

1. **确定核芯功能扩展**：
   - 特权指令：
     - trap/cfx2rd/cfx2rc 按 cfxcode 路由；
     - cfxld/cfxst 访问 cfx 内部存储块，仅触发 CFXMEM，按 cfxcode 路由
     - 若 cfxcode 为 reserved（7-14、19-61），触发 ILLI 进入当前 monitor；若 cfxcode 合法但指令 cfx mask 禁止，同样触发 ILLI
   - 其它指令执行触发的 ILLI/UNDI/RASOF/RASUF/FPEXCP/IALIGN/MALIGN 异常：
     - 根据发生异常前的运行模式（U-mode/J-mode/S-mode/H-mode）分别判断进入 cfx_umon/cfx_jmon/cfx_smon/cfx_hmon 核芯功能扩展
   - 页表步进中产生的异常（PTBR 权限、页缺失等）：判断应进入 cfx_ptw 核芯功能扩展
   - TLB 命中时产生的异常（权限不符、fragment 缺失）：判断应进入 cfx_tlb 核芯功能扩展
   - CFXMEM（核内地址空间非法访问，仅在对应 PTBR 未开启时触发）：根据核内地址高 6 位 bits[47:42] 指定的 cfxcode 作为目标核芯功能扩展
   - 异步中断：根据中断源判断进入对应的核芯功能扩展
2. **判断是否为不可屏蔽异常**：检查 `cfx_⟨cfxname⟩_excp_cause_nonmaskable` 对应位，若置1则该异常不可屏蔽，跳过步骤3-5直接进入步骤6
3. **判断 inner_cfx_mask 是否屏蔽**：若目标 cfx 非自身，检查 `inner_cfx_mask` 第 cfxcode 位。若为1，同步异常触发 ILLI，异步中断设置 pending
4. **判断 global_cfx_mask 是否屏蔽**：若目标 cfx 非自身，检查 `cfx_⟨cfxname⟩_<mode>_global_cfx_mask` 第 cfxcode 位。若为1，同步异常触发 ILLI，异步中断设置 pending
5. **判断异常原因是否被屏蔽**：检查 `cfx_⟨cfxname⟩_<mode>_excp_cause_mask` 对应位，若为1则该异常原因被屏蔽
    - 同步异常中仅 FPEXCP 可被屏蔽——被屏蔽时目的寄存器已按 IEEE 754 写入正常结果，只需设置 `cfx_⟨cfxname⟩_excp_pending` 对应位（与异步中断一致），后续 mask 解除时触发。其余同步异常均为不可屏蔽，不存在此路径
    - 异步中断若被屏蔽，则处于待处理状态（pending），并将对应位置1到 `cfx_⟨cfxname⟩_excp_pending` 寄存器中（OR语义，不影响其他pending位）。软件可通过写0清除对应pending位。
6. **更新陷入计数**：根据异常类型递增 `cfx_⟨cfxname⟩_trap_num`（trap 指令）、`cfx_⟨cfxname⟩_excp_sync_num`（同步异常）或 `cfx_⟨cfxname⟩_excp_async_num`（异步中断）
7. **保存现场**：`cfx_⟨cfxname⟩_excp_prev_run_mode` 记录异常前的运行模式，`cfx_⟨cfxname⟩_excp_prev_cfx_mask` 保存异常前的核芯功能扩展掩码
8. **模式切换**：将运行模式和核芯功能扩展掩码改为 `cfx_⟨cfxname⟩_<mode>_switch_run_mode` 和 `cfx_⟨cfxname⟩_<mode>_switch_cfx_mask` 寄存器的值
9. **保存异常信息**：
    - `cfx_⟨cfxname⟩_excp_cause_ip`：发生异常的指令地址（同步异常为触发异常的指令地址，异步中断为下一条指令地址）
    - `cfx_⟨cfxname⟩_excp_cause_id`：异常编号
    - `cfx_⟨cfxname⟩_excp_cause_info`：异常辅助信息
10. **跳转至异常向量**：跳转到 `cfx_⟨cfxname⟩_<mode>_excp_vector` 寄存器指示的异常处理程序地址。该地址与普通访存规则一致：若对应 PTBR 未开启则为核内地址，若 PTBR 开启则为虚拟地址。软件须保证异常向量所在页不会发生页缺失，硬件不提供向量缺失的恢复机制。

```
// 注：伪代码中 cause 为 one-hot 值（如 CFXTRAP = 1<<0 = 1，ILLI = 1<<8 = 256）；
//     异常原因表中 `1 << n` 的 n 即位索引，cause = 1 << n。
// 1. 确定核芯功能扩展
if instruction ∈ {TRAP, ESCAPE, CFXLD, CFXST, CFX2RD, CFX2RC}:
    if cfxcode ∈ {7..14, 19..61}:
        cause      <= ILLI
        ; reserved→ILLI，重定向到当前运行模式的 monitor (cfx0-3)
        case inner_run_mode of
            U-mode: temp_cfx_code <= 0
            J-mode: temp_cfx_code <= 1
            S-mode: temp_cfx_code <= 2
            H-mode: temp_cfx_code <= 3
    elif cfxcode != inner_cfx_code and cfx_⟨cfxname⟩_<mode>_<instr>_cfx_mask & (1 << cfxcode):
        cause      <= ILLI
        ; 指令类型 cfx mask 禁止 → ILLI，重定向到当前模式 monitor
        case inner_run_mode of
            U-mode: temp_cfx_code <= 0
            J-mode: temp_cfx_code <= 1
            S-mode: temp_cfx_code <= 2
            H-mode: temp_cfx_code <= 3
    elif instruction == TRAP:
        cause          <= CFXTRAP                 // 功能调用
        temp_cfx_code  <= cfxcode
    elif instruction ∈ {CFX2RD, CFX2RC}:
        ; cause 已由硬件执行阶段确定（CFXREG），此处仅路由
        temp_cfx_code  <= cfxcode
    elif instruction ∈ {CFXLD, CFXST}:
        ; cfxld/cfxst 访问核芯功能扩展内部存储块，仅触发 CFXMEM
        temp_cfx_code  <= cfxcode
    // ESCAPE（非 reserved）：由异常退出流程处理，不在此处路由
elif sync:
    case inner_run_mode of
        U-mode: temp_cfx_code <= 0
        J-mode: temp_cfx_code <= 1
        S-mode: temp_cfx_code <= 2
        H-mode: temp_cfx_code <= 3
elif mem_access:
    if cause == CFXMEM:                         // 核内地址空间异常
        if addr[47:42] ∈ {7..14, 19..61}:       // reserved cfxcode → ILLI
            cause          <= ILLI
            case inner_run_mode of
                U-mode: temp_cfx_code <= 0
                J-mode: temp_cfx_code <= 1
                S-mode: temp_cfx_code <= 2
                H-mode: temp_cfx_code <= 3
        else:
            temp_cfx_code  <= addr[47:42]       // 正常路由
    elif from_tlb:                              // TLB命中时产生的异常 → cfx_tlb
        temp_cfx_code  <= 5
    else:
        temp_cfx_code  <= 4                      // 页表步进异常 → cfx_ptw
else:
    temp_cfx_code          <= intr_cfx               // 异步中断 → 硬件固定路由

// 2. 判断是否为不可屏蔽异常
check_nonmaskable:
if (cfx_⟨cfxname⟩_excp_cause_nonmaskable & cause) == 0:

    // 3. 判断 inner_cfx_mask 是否屏蔽（自身 cfxcode 不检查）
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

    // 4. 判断 global_cfx_mask 是否屏蔽（自身 cfxcode 不检查）
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
    //    同步异常中仅 FPEXCP 可被屏蔽，被屏蔽时目的寄存器已写入正常结果
    if (cfx_⟨cfxname⟩_<mode>_excp_cause_mask & cause) != 0:
        cfx_⟨cfxname⟩_excp_pending ← cfx_⟨cfxname⟩_excp_pending | cause   // 同步可屏蔽或异步：设置 pending
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

### 异常退出流程

通过 `escape` 指令完成异常退出。`escape` 指令编码中指定了核芯功能扩展编号 `cfxcode`。伪代码中 `⟨cfxname⟩` 指当前执行 escape 的 cfx（即 `inner_cfx_code`）。下面的步骤和伪代码描述 `escape` 指令的硬件语义：

0. **检查 escape cfx mask**：若目标 cfxcode 非自身，检查 `cfx_⟨cfxname⟩_<mode>_escape_cfx_mask` 第 cfxcode 位。若为 1，触发 ILLI 异常（escape 被禁止）
1. **恢复核芯功能扩展掩码**：根据 `cfx_⟨cfxname⟩_excp_prev_cfx_mask` 寄存器的值恢复核芯功能扩展掩码
2. **恢复运行模式**：依据 `cfx_⟨cfxname⟩_excp_prev_run_mode` 还原为异常发生前的运行模式
3. **更新退出计数**：`cfx_⟨cfxname⟩_escape_num` 递增 1
4. **计算返回地址并跳转**：根据 `cfx_⟨cfxname⟩_excp_cause_ip` 寄存器的地址和 `escape` 指令的 `imms18`（指令字偏移）作为偏移值，计算出返回地址并跳转

```
// 0. 检查 escape cfx mask（自身 cfxcode 不检查）
if cfxcode != inner_cfx_code:
    if (cfx_⟨cfxname⟩_<mode>_escape_cfx_mask & (1 << cfxcode)) != 0:
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
