# DADAO Supervisor Execution Environment（SEE）

> **版本：0.8.0-rc**（与 SBI 版本号一致，同步更新。基于 SimRISC 0.5.5 指令系统设计）

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
| 15 | hart | Hart 管理、本地计数与异步中断投递（含异步现场） |
| 16-31 | reserved | 保留（per-task 段，未分配） |
| 32 | pmem | 物理存储器管理 |
| 33 | llc | 最后一级缓存，跨 hart 共享 |
| 34 | time | 全局时间计数器 |
| 35-61 | reserved | 保留，未定义 |
| 62 | uart | 串口控制器 |
| 63 | power | 电源管理 |

每个核芯功能扩展提供自己特有的功能调用，并负责响应和处理所管理设备的中断，因此，异常的进入和退出也都隶属于某个核芯功能扩展：

- 执行期同步异常先进入当前运行模式的 monitor（`cfx_umon`/`cfx_jmon`/`cfx_smon`/`cfx_hmon`），由 monitor 自行处理或 `trap` 分发到源 cfx；显式 `trap` 仍隶属目标 cfx，`escape` 仍隶属当前 cfx
- 地址转换过程中触发的异常（页表步进与 TLB 命中）先进入当前运行模式 monitor：未映射与 A/D 回写失败归 `CFXMEM`，权限拒绝归 `CFXPERM`；不再由 `cfx_ptw` 处理
- 异步中断统一进入 `cfx_hart`（cfxha 15，hart-first），与同步异常分流：不进入当前运行模式 monitor，也不直接进入源 cfx；异步源以**源 cfxha** 标识（TIMER=15、PMEM_DMA=32），不占 `excp_cause_id`；异步现场与 pending 在 `cfx_hart cg9`（§4.7），来源掩码在**当前运行模式 monitor** 的 `cg8 rc1`（§4.1–§4.4），入口为 `cfx_hart` 的 supv 单向量（§5.4）

多核系统中各资源的作用域：

| 资源 | 作用域 |
|------|:--:|
| rd/rb/rf/ra、inner_* | per-hart |
| cfx0-cfx15 | per-hart |
| cfx16-cfx31 | per-task |
| cfx32-cfx63 | per-system |

> `per-task`：`cfx16`–`cfx31` 由内核或进程在**申请后使用**，使用完毕**释放**；持有期间即使发生进程上下文切换，该 cfx 的状态与运行不受影响，**不需要**随上下文切换保存/恢复。

> `inner_*` 为硬件内部寄存器（不对外暴露），用于异常处理流程中的中间状态保存。`inner_run_mode`（2 位）记录当前运行模式（0=user, 1=jail, 2=supv, 3=hypv），`inner_excp_cause_*` 等用于现场保存。同步异常全部不可屏蔽，不使用异常原因掩码与不可屏蔽掩码；异步中断的来源过滤按**当前运行模式 monitor** 的 `cg8 rc1`（§4.1–§4.4），pending 与现场由 `cfx_hart` 的 `cg9` 承担（§4.7）。同步语义见 §5.2，异步语义见 §5.4。

## 2. 地址空间

CPU 地址固定为 48 位。高 6 位 `addr[47:42]` 是地址空间分区键：`0` 为内存窗口，`1..63` 为 cfx 1–63 的核内地址空间。内存窗口的虚拟地址（VA）为 42 位（`VA[41:0]`，高 6 位固定 0）；物理地址（PA）为 56 位。CPU 地址与物理地址是两个不同的地址空间：内存窗口不直通物理存储器，必须经页表转换；cfx 核内地址也不等同于物理地址。

`ptw_enable` 控制内存窗口是否翻译：`0` 时不翻译，`addr[47:42] = 0` 的访存触发 CFXMEM；`1` 时按页表转换。cfx 核内地址（`addr[47:42] = 1..63`）直接 `ld/st`，不经 `ptw_enable`。

### 2.1 核内地址空间

48 位核内地址的高 6 位（`addr[47:42]`）指定了核芯功能扩展编号（cfxha）。`addr[47:42] = 0` 的地址属于内存窗口（见 §2.2），不属于任何 cfx 的内部空间；因此 `cfx0`（umon）没有内部地址空间。`cfx1`–`cfx63` 的内部空间各为 42 位（`addr[41:0]`）。

已分配的核内地址空间如下：

| cfx num | cfx name | 起始地址 | 地址大小 | 空间类型 |
|:---:|------|------|------|------|
| 2 | smon | `0x0bff_0000_0000` | 64 KiB | SRAM |
| 3 | hmon | `0x0fff_0000_0000` | 64 KiB | SRAM |
| 32 | pmem | `0x83ff_0000_0000` | 64 KiB | SRAM |
| 63 | power | 自 `2^48` 向下；末 64 KiB 起点 `0xffff_ffff_0000` | **≥64 KiB**（具体由平台规范规定） | BootROM |

说明：

- `cfx_power_hypv_excp_vector = 0xffff_ffff_0000` 为硬件复位后的启动地址，位于 BootROM 的**末 64 KiB 起点**（镜像内偏移 = BootROM 大小 − 64 KiB）；BootROM 为自 `2^48` 向下的连续非易失区，大小 **≥64 KiB**、由平台规范规定，可由 CPU 直接取指执行；复位向量不变。`cfx_power` 的 BootROM 空间块 `attr` 必须含 `X=1`（复位向量位于该块内，CPU 直接取指执行）；smon/hmon/pmem 的 SRAM 块按各自异常向量取指需求给出 `X`。
- `cfx2`（smon）与 `cfx3`（hmon）的 SRAM 各 64 KiB；S-mode 与 H-mode 异常向量默认等于各自的起始地址。`cfx_power` 是否设 SRAM 由平台规范规定（不属本册架构约束）。
- 各 cfx 的内部空间（起始偏移、字节大小、空间类型）由该 cfx 自身的 cg7（§3.8）描述；本表每行必须与对应 cfx 的 cg7 某个空间块一致（`start = 起始地址 − (cfxha << 42)`、`size` 相等、空间类型对应）。校验示例：smon/hmon/pmem 的 `start` 均为 `0x3ff_0000_0000`；power 的 `start = 2^42 − size`、`size ≥ 0x1_0000`，且 `start + size = 2^42` 边界合法（`size = 64 KiB` ⇒ `start = 0x3ff_ffff_0000`；`size = 4 MiB` ⇒ `start = 0x3ff_ffc0_0000`）。
- 对核内地址空间进行非法访问时，会触发对应核芯功能扩展的 CFXMEM 异常。核芯功能扩展由地址高 6 位 `addr[47:42]`（即 cfxha）确定。
- 保留 cfx（6–14、16–31、35–61）的普通 `ld/st` 触发 CFXMEM；`trap`/`escape` 到保留 cfx 触发 ILLI。
- cfxha 5 为 `cfx_cache`；未实现的已分配 cfx 由实现约定其未实现行为（测试机按未实现 cfx 处理）。
- cfx_pmem 的 64 KiB SRAM 固定在内部偏移 0x3ff_0000_0000（§4.9），CPU 用普通 `ld/st` 访问；SRAM 之外的核内偏移触发 CFXMEM。
- 屏障指令 `fence cfxHA, immu18` 用 `cfxHA` 选择资源域：`cfx0` 与 `cfx_umon` 都表示 **all cfx**，`cfx1`–`cfx63` 表示指定 cfx；`immu18` 中的 `cr`/`cw`/`ci`/`co` 位作用于所选 cfx 的 memory/IO 访问，`mr`/`mw` 位作用于系统内存。屏障只约束本 hart 的访问顺序/可见性，不等待 DMA。
- cfx1–cfx63 的访问权限按 §1 两轴模型与 §3/§5 的四类同步 mask、monitor 的异步来源掩码（`cg8 rc1`）判定；每个 cfx 的 `cg0`–`cg3` 按当前运行模式分别配置来源 cfx。

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
- TLB 命中时不重读 PTE，直接用条目中的 SPF/GPF、HSJU 与 R/W/X 检查：小页标记位为 0 触发 `CFXMEM`，HSJU 或 R/W/X 不符触发 `CFXPERM`；检查顺序与 §2.2.6 相同。TLB 命中产生的异常按当前运行模式 monitor 路由（见 §2.2.6、§5.2）。
- 命中且权限符合时跳过第三步（页表步进），更新 A/D（见 §4.5）后进入第四步（形成最终物理地址）。
- 未命中时继续执行第三步；只有步进得到的 PTE 有效且全部检查通过后才把结果填入 TLB（缺页/权限失败不填充，也不更新 A/D）。替换策略由实现决定；替换或失效带未回写 A/D 的条目时须回写（§4.5）。

**第三步：页表步进**

- 用 `VA[41:29]` × 8 计算 L1 页表项偏移，从 PTBR 基址读取 8 字节 PTE。
- 若 Present 位为 0（`P = 0`）且 Superpage 位为 1（`SP = 1`），则为超页缺失，触发 `CFXMEM`（当前运行模式 monitor）。
- 若 Present 位为 0（`P = 0`）且 Superpage 位为 0（`SP = 0`），则该条目不是超页，按 §2.2.2 报 `CFXMEM`。
- 若 Present 位为 1 且 Superpage 位为 0（`SP = 0`），则该条目不是超页，按 §2.2.2 走二级页表。
- 若 Present 位为 1 且 Superpage 位为 1（`SP = 1`），则检查 SPF 字段中对应小页的标记位（`VA[28:26]` 选位；见 §2.2.3）；若对应位为 0，触发 `CFXMEM`（当前运行模式 monitor）。
- 小页存在时依次检查 HSJU 与读/写/执行权限（见 §2.2.5），任一不符触发 `CFXPERM`。

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
- 若 Present 位为 0（`P = 0`），触发 `CFXMEM`（`SP = 1` 时按 §2.2.1 报超页缺失）。
- 若 Present 位为 1 且 Superpage 位为 1（`SP = 1`），则该条目为超页，按 §2.2.1 处理。
- 若 Present 位为 1 且 Superpage 位为 0（`SP = 0`），生成二级页表的访问地址并读取 8 字节 L2 PTE：
  - 一级页表项给出的物理页号作为二级页表基址 `PA[55:16]`
  - 用 `VA[28:16]` × 8 计算二级页表的索引，即 L2 页表项偏移 `L2PA[15:3]`
- 若 L2 表项 Present 位为 0，触发 `CFXMEM`。
- 若 L2 表项 Present 位为 1，则检查 GPF 字段中对应小页的标记位（`VA[15:13]` 选位；见 §2.2.4）；若对应位为 0，触发 `CFXMEM`。
- 小页存在时依次检查 HSJU 与读/写/执行权限（见 §2.2.5），任一不符触发 `CFXPERM`。

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

- `HSJU` 是当前运行模式的访问许可掩码：U-mode 对应 `bit60`、J-mode 对应 `bit61`、S-mode 对应 `bit62`、H-mode 对应 `bit63`。当前运行模式对应的位为 1 才允许访问，否则触发 `CFXPERM`（当前运行模式 monitor）。硬件不做「S 模式自动覆盖 U 页」「H 模式自动覆盖 S 页」之类的隐含放宽；用户页/内核页的组合策略由操作系统决定，架构不强制。
- `R`/`W`/`X` 与 HSJU 正交：取指要求 `X = 1`（否则 `CFXPERM`），读要求 `R = 1`（否则 `CFXPERM`），写要求 `W = 1`（否则 `CFXPERM`）。
- 同一访问可同时违反多个条件时，只报 §2.2.6 规定的最高优先级异常。

**A/D 位**

`A`（Access）与 `D`（Dirty）由硬件在 TLB 条目中维护，经 `CLEAN`/`FLUSH`（或条目替换）以原子 OR 回写到 PTE：

- 条目填充时取 PTE 的 `A`/`D` 作为本地的 `A_local`/`D_local`，回写挂起位 `A_dirty`/`D_dirty` 清零——**填充本身不产生回写**。
- 权限通过的访问：读/取指在 `A_local = 0` 时置 `A_local = 1`、`A_dirty = 1`；写在置 `A` 的同时，`D_local = 0` 时置 `D_local = 1`、`D_dirty = 1`。该规则对「命中」与「本次访问触发填充」同样适用（填充只拷贝 PTE 的 `A`/`D`，本次访问随即按访问类型置位）。
- 缺页/权限失败：不更新 A/D，也不填充条目。
- `CLEAN`/`FLUSH`/条目替换：只把挂起的 `A`/`D` 位原子 OR 回写 PTE（保留其他字段），回写后清挂起位；`CLEAN` 保留条目，`FLUSH` 回写后删除条目，`INVALID` 不写回直接删除。
- 回写失败按当前运行模式 monitor 的 `CFXMEM` 处理（`cause_info` = PTE 物理地址，见 §4.5）；页表页必须可写。软件清 `A`/`D` 后必须显式 invalidate 对应条目。

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

**页表步进内部优先级**（`P = 0` / 超页缺失 → SPF/GPF 对应位 = 0 → HSJU 不符 → R/W/X 不符；每步给出的子原因位见 §3.6 子原因位表，与 cause 同时置位）：

1. `ptw_enable = 0` → `CFXMEM`（不发生页表步进）；**非页表类，子原因 `[57] NONPTW`（wyde3）**
2. L1 `P = 0`：`SP = 1`（超页缺失）→ `CFXMEM` + `[49] ISPTRAP`/`[53] DSPTRAP`；`SP = 0` → `CFXMEM` + `[48] IGPTRAP`/`[52] DGPTRAP`
3. L1 `P = 1`、`SP = 1`、SPF 对应小页位 = 0 → `CFXMEM` + `[51] ISPFTRAP`/`[55] DSPFTRAP`
4. L2 `P = 0`（普通页缺失）→ `CFXMEM` + `[48] IGPTRAP`/`[52] DGPTRAP`
5. L2 `P = 1`、GPF 对应小页位 = 0 → `CFXMEM` + `[50] IGPFTRAP`/`[54] DGPFTRAP`
6. HSJU 不符 → `CFXPERM` + `[32] NUPERM`/`[33] NJPERM`/`[34] NSPERM`/`[35] NHPERM`（按当前运行模式选取其一）
7. R/W/X 不符 → `CFXPERM` + `[36] NRPERM`/`[37] NWPERM`/`[38] NXPERM`（按访问类型选取其一：读/写/取指）

取指用 `I` 前缀的子原因、数据读写用 `D` 前缀的子原因。仅触发优先级最高的异常，后续检查不再执行；`[15:0]` 的 cause 与对应 wyde 的子原因同时写入 `excp_cause_id`（两者各自 one-hot）。`CFXMEM` 的非页表来源（`ptw_enable = 0`、cfx 空间非法访问/取指、未实现 cfx 的普通 `ld/st`、存储块故障）子原因为 `[57] NONPTW`。A/D 回写失败不属于上述步进判定：按 §2.2.5 与 §4.5 报当前运行模式 monitor 的 `CFXMEM` + `[56] ADWBFAIL`，`cause_info` = PTE 物理地址。cfx 访问被来源掩码拒绝（`cfxtrap`/`cfxreg`/`cfxexe`）同样不属页表步进，报 `CFXPERM` + `[39] NCFXPERM`。页表未映射（缺页/超页缺失/小页缺失）与 A/D 回写失败归 `CFXMEM`（wyde3），HSJU 或 R/W/X 不符归 `CFXPERM`（wyde2），目标均为当前运行模式 monitor（§5.2）；异常原因编号、子原因位表与 `cause_info` 口径见 §3.6。

## 3. 共有寄存器设计规范

cg0-cg7 为共有寄存器设计，不同的核芯功能扩展设计规范相同。

### 3.1 cg0 - user mode 寄存器

每个核芯功能扩展中针对用户模式（user）有以下寄存器（cg=0）：

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 0 | 0 | user cfxtrap cfx mask | cfx_⟨cfxname⟩_user_cfxtrap | `0xFFFF_FFFF_FFFF_FFF7`（hmon 自身 `0x7FFF_FFFF_FFFF_FFF7`） | RW | `trap`/`escape` 控制转移，0=允许，1=屏蔽。位索引=源 cfx；自身 cfxha 对应位硬件忽略 |
| 0 | 1 | user cfxmem cfx mask | cfx_⟨cfxname⟩_user_cfxmem | 同上 | RW | 直接 `ld/st` 访问该 cfx 的 SRAM/MMIO，0=允许，1=屏蔽。位索引=源 cfx；自身对应位忽略 |
| 0 | 2 | user cfxreg cfx mask | cfx_⟨cfxname⟩_user_cfxreg | 同上 | RW | `cfx2rd`/`cfx2rc` 访问，0=允许，1=屏蔽。位索引=源 cfx；自身对应位忽略 |
| 0 | 3 | user cfxexe cfx mask | cfx_⟨cfxname⟩_user_cfxexe | 同上 | RW | 直接跳转/取指进入该 cfx，0=允许，1=屏蔽。位索引=源 cfx；自身对应位忽略 |
| 0 | 8 | user switch run mode | cfx_⟨cfxname⟩_user_switch_run_mode | 2 (S-mode) | RW | 从user陷入时切换的运行模式 |
| 0 | 9 | reserved | — | — | — | 保留；访问触发 `CFXREG` |
| 0 | 10 | user excp vector | cfx_⟨cfxname⟩_user_excp_vector | 0 | RW | 从user陷入时的异常向量入口地址 |
| 0 | 11 | reserved | — | — | — | 保留；访问触发 `CFXREG` |

`rc0`–`rc3` 为**四类同步来源 mask**，位索引均为**源 cfxha**，`0=允许`、`1=屏蔽`；`rc4` 不定义（保留，访问触发 `CFXREG`）；异步来源掩码见**当前运行模式 monitor** 的 `cg8 rc1`（§4.1–§4.4）。访问自身 cfx 时只绕过 cfx 轴（位测试），仍使用当前运行模式对应的寄存器行（模式轴）。`rc5`–`rc7` 保留，访问触发 `CFXREG`。

为支持用户程序通过系统调用陷入操作系统内核，硬件应至少支持 `cfx_umon_user_*` 这一组寄存器或 `cfx_smon_user_*` 这一组寄存器。

用户 `trap` 按 cfxha 路由：目标为 `cfx_smon` 时使用 `cfx_smon_user_*`（目标的 `cfxtrap` mask 须允许源 cfx），目标为 `cfx_umon` 时使用 `cfx_umon_user_*`。非 trap 的 U-mode 异常固定进入 `cfx_umon`。

### 3.2 cg1 - jail mode 寄存器

jail mode 为受限用户模式，MVP 阶段与 user mode 行为一致。受限规则（如禁止指令、二阶段翻译等）留待后续版本定义。

每个核芯功能扩展中针对监狱模式（jail）有以下寄存器（cg=1）：

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 1 | 0 | jail cfxtrap cfx mask | cfx_⟨cfxname⟩_jail_cfxtrap | `0xFFFF_FFFF_FFFF_FFF7`（hmon 自身 `0x7FFF_FFFF_FFFF_FFF7`） | RW | `trap`/`escape` 控制转移，0=允许，1=屏蔽。位索引=源 cfx；自身对应位忽略 |
| 1 | 1 | jail cfxmem cfx mask | cfx_⟨cfxname⟩_jail_cfxmem | 同上 | RW | 直接 `ld/st` 访问该 cfx，0=允许，1=屏蔽。位索引=源 cfx；自身对应位忽略 |
| 1 | 2 | jail cfxreg cfx mask | cfx_⟨cfxname⟩_jail_cfxreg | 同上 | RW | `cfx2rd`/`cfx2rc` 访问，0=允许，1=屏蔽。位索引=源 cfx；自身对应位忽略 |
| 1 | 3 | jail cfxexe cfx mask | cfx_⟨cfxname⟩_jail_cfxexe | 同上 | RW | 直接跳转/取指进入该 cfx，0=允许，1=屏蔽。位索引=源 cfx；自身对应位忽略 |
| 1 | 8 | jail switch run mode | cfx_⟨cfxname⟩_jail_switch_run_mode | 2 (supv) | RW | 从jail陷入时切换的运行模式 |
| 1 | 9 | reserved | — | — | — | 保留；访问触发 `CFXREG` |
| 1 | 10 | jail excp vector | cfx_⟨cfxname⟩_jail_excp_vector | 0 | RW | 从jail陷入时的异常向量入口地址 |
| 1 | 11 | reserved | — | — | — | 保留；访问触发 `CFXREG` |

### 3.3 cg2 - supv mode 寄存器

每个核芯功能扩展中针对主管模式（supv）有以下寄存器（cg=2）：

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 2 | 0 | supv cfxtrap cfx mask | cfx_⟨cfxname⟩_supv_cfxtrap | `0xFFFF_FFFF_FFFF_FFF7`（hmon 自身 `0x7FFF_FFFF_FFFF_FFF7`） | RW | `trap`/`escape` 控制转移，0=允许，1=屏蔽。位索引=源 cfx；自身对应位忽略 |
| 2 | 1 | supv cfxmem cfx mask | cfx_⟨cfxname⟩_supv_cfxmem | 同上 | RW | 直接 `ld/st` 访问该 cfx，0=允许，1=屏蔽。位索引=源 cfx；自身对应位忽略 |
| 2 | 2 | supv cfxreg cfx mask | cfx_⟨cfxname⟩_supv_cfxreg | 同上 | RW | `cfx2rd`/`cfx2rc` 访问，0=允许，1=屏蔽。位索引=源 cfx；自身对应位忽略 |
| 2 | 3 | supv cfxexe cfx mask | cfx_⟨cfxname⟩_supv_cfxexe | 同上 | RW | 直接跳转/取指进入该 cfx，0=允许，1=屏蔽。位索引=源 cfx；自身对应位忽略 |
| 2 | 8 | supv switch run mode | cfx_⟨cfxname⟩_supv_switch_run_mode | 2 (supv) | RW | 从supv陷入时切换的运行模式 |
| 2 | 9 | reserved | — | — | — | 保留；访问触发 `CFXREG` |
| 2 | 10 | supv excp vector | cfx_⟨cfxname⟩_supv_excp_vector | 0 | RW | 从supv陷入时的异常向量入口地址 |
| 2 | 11 | reserved | — | — | — | 保留；访问触发 `CFXREG` |

### 3.4 cg3 - hypv mode 寄存器

每个核芯功能扩展中针对超管模式（hypv）有以下寄存器（cg=3）。这部分寄存器的读写，只有当前运行环境是 hypv 时才能进行，否则触发 CFXREG 异常。

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 3 | 0 | hypv cfxtrap cfx mask | cfx_⟨cfxname⟩_hypv_cfxtrap | `0xFFFF_FFFF_FFFF_FFF7`（hmon 自身 `0x7FFF_FFFF_FFFF_FFF7`） | RW | `trap`/`escape` 控制转移，0=允许，1=屏蔽。位索引=源 cfx；自身对应位忽略 |
| 3 | 1 | hypv cfxmem cfx mask | cfx_⟨cfxname⟩_hypv_cfxmem | 同上 | RW | 直接 `ld/st` 访问该 cfx，0=允许，1=屏蔽。位索引=源 cfx；自身对应位忽略 |
| 3 | 2 | hypv cfxreg cfx mask | cfx_⟨cfxname⟩_hypv_cfxreg | 同上 | RW | `cfx2rd`/`cfx2rc` 访问，0=允许，1=屏蔽。位索引=源 cfx；自身对应位忽略 |
| 3 | 3 | hypv cfxexe cfx mask | cfx_⟨cfxname⟩_hypv_cfxexe | 同上 | RW | 直接跳转/取指进入该 cfx，0=允许，1=屏蔽。位索引=源 cfx；自身对应位忽略 |
| 3 | 8 | hypv switch run mode | cfx_⟨cfxname⟩_hypv_switch_run_mode | 3 (hypv) | RW | 从hypv陷入时切换的运行模式 |
| 3 | 9 | reserved | — | — | — | 保留；访问触发 `CFXREG` |
| 3 | 10 | hypv excp vector | cfx_⟨cfxname⟩_hypv_excp_vector | 该 cfx 内部 SRAM 的起始地址（无内部 SRAM 者由平台/实现定义） | RW | 从hypv陷入时的异常向量入口地址；**写入忽略低 2 位**（`value[1:0] ← 0`，按 4 字节对齐落盘），不产生异常 |
| 3 | 11 | reserved | — | — | — | 保留；访问触发 `CFXREG` |
| 3 | 12 | hypv cg reg delegation | cfx_⟨cfxname⟩_hypv_cg_reg_deleg | 全1 | RW | cg访问授权，bit=0时允许supv访问。bit3固定为1 |

`rc0`–`rc3` 为四类同步来源 mask，位索引=源 cfx，`0=允许`、`1=屏蔽`，自身只绕过 cfx 轴；`rc4` 不定义（保留，访问触发 `CFXREG`）。`rc5`–`rc7` 保留，访问触发 `CFXREG`。`cfx0`–`cfx3` 的 `cg8 rc1` 为 `cfx_<monitor>_async_intr_mask`（本运行模式的异步来源掩码，位索引 = 源 cfxha，`0=允许`/`1=屏蔽`，复位全 1；见 §4.1–§4.4）。

`rc10`（`hypv_excp_vector`）的初值与写入：

- **初值**：该 cfx **内部 SRAM 的起始地址**（有内部 SRAM 的 cfx 见 §2.1 核内地址空间表）；**无内部 SRAM 的 cfx**（如 `cfx_power` 的 BootROM、`cfx_umon`/`cfx_jmon`）由平台/实现定义。有内部 SRAM 的 cfx，其 HBI 初始化入口应位于该 SRAM 起始（即初值所指），据此满足 HBI §3「各 cfx 的 `hypv_excp_vector` 复位值应指向其 HBI 初始化入口」。
- **写入忽略低 2 位**：`value[1:0] ← 0`（4 字节对齐落盘），**不产生异常**；读回为落盘值（低 2 位为 0）。

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

每个核芯功能扩展都有以下异常现场寄存器（cg=5）：

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 5 | 0 | excp prev run mode | cfx_⟨cfxname⟩_excp_prev_run_mode | 0 | RW | 异常前运行模式，硬件陷入时保存，软件可写 |
| 5 | 1 | excp prev cfx code | cfx_⟨cfxname⟩_excp_prev_cfx_code | 0 | RW | 异常前当前核芯功能扩展编号，硬件陷入时保存，软件可写 |
| 5 | 2 | excp cause id | cfx_⟨cfxname⟩_excp_cause_id | 0 | HW | 异常原因编号（分层：`[15:0]` 为同步 cause one-hot；`[31:16]` 保留，异步源**不占** `excp_cause_id`；wyde2 `[47:32]`/wyde3 `[63:48]` 为子原因，见下），硬件在异常进入时写入 |
| 5 | 3 | excp cause ip | cfx_⟨cfxname⟩_excp_cause_ip | 0 | RW | 异常发生前的指令指针，硬件陷入时保存，软件可写 |
| 5 | 4 | excp cause info | cfx_⟨cfxname⟩_excp_cause_info | 0 | HW | 发生异常的辅助信息（`CFXMEM`/`CFXPERM` 恒为地址，见下） |
| 5 | 5 | excp pending | cfx_⟨cfxname⟩_excp_pending | 0 | RW | 待处理**同步**异常位图（one-hot，OR 语义），写 0 清位；异步 pending 见 `cfx_hart cg9 rc4`（§4.7） |
| 5 | 63 | reserved | — | — | — | 保留；访问触发 `CFXREG` |

异常原因编号 `cfx_⟨cfxname⟩_excp_cause_id` 为**分层编码**（64 位）：低 16 位是**同步 cause one-hot**；`[31:16]` 保留（**异步源不占** `excp_cause_id`）；子原因按 16 位 **wyde**（双字节）分段——**wyde2 `[47:32]` 专供 `CFXPERM`、wyde3 `[63:48]` 专供 `CFXMEM`**，每个同步 cause 独占一个 wyde。各核芯功能扩展的异常原因表只定义该核芯功能扩展可处理的**同步** cause 位；异步源以**源 cfxha** 标识（见下）。

**（一）`[15:0]`：同步 cause one-hot**。表中未列出的位属于保留或未使用，若硬件错误触发此类位，表示该核芯功能扩展出现不可恢复的错误。`1 << 3` 为 `CFXESC`（escape 帧/目标错误，每个 cfx）；`1 << 4` 至 `1 << 6` 保留用于未来扩展（debug 异常等）；`1 << 7` 在 `cfx0`–`cfx3` 为 `CFXPERM`（两轴权限拒绝），在 `cfx_ptw` 保留（见 §4.5）。`[15:0]` 为**同步** one-hot；异步源不占本段。

**（二）`[31:16]`：保留（异步源标识不占 `excp_cause_id`）**。异步中断**没有独立的 cause 编号**：源身份 = **源 cfxha**（`TIMER` = 15、`PMEM_DMA` = 32），投递到 `cfx_hart` 后由 `cfx_hart cg9` 的 `async_src_frame`（§4.7）按源 cfxha 位集合给出本帧源集合。**约束**：一个源 cfx 至多一个异步 cause；同源内的差异（`DONE`/`ERROR`、`ISTATUS` 等）回源 cfx 寄存器区分。本段保留给未来新的大类 cause，当前必须全 0、子原因编码不得占用；同一 `excp_cause_id` 从不携带异步源。

**（三）wyde2 `[47:32]`：`CFXPERM` 的子原因**。低字节 `[39:32]`（8 位，字节对齐）为 one-hot 权限原因；高字节 `[47:40]` **保留（必须 0）**。

| 位号 | 名称 | 触发条件 |
|------|------|---------|
| `[32]` | NUPERM | HSJU 的 `U` 位 = 0 且当前运行模式为 `user` |
| `[33]` | NJPERM | HSJU 的 `J` 位 = 0 且当前运行模式为 `jail` |
| `[34]` | NSPERM | HSJU 的 `S` 位 = 0 且当前运行模式为 `supv` |
| `[35]` | NHPERM | HSJU 的 `H` 位 = 0 且当前运行模式为 `hypv` |
| `[36]` | NRPERM | 读访问且页的 `R` = 0 |
| `[37]` | NWPERM | 写访问且页的 `W` = 0 |
| `[38]` | NXPERM | 取指且页的 `X` = 0 |
| `[39]` | NCFXPERM | cfx 访问被来源掩码拒绝（`cfxtrap`/`cfxreg`/`cfxexe`） |

**（四）wyde3 `[63:48]`：`CFXMEM` 的子原因**。低字节 `[55:48]`（8 位，字节对齐）为 one-hot 缺失原因；高字节 `[63:56]` 中 `[56]` 为 A/D 回写失败、`[57]` 为非页表类访存故障，`[63:58]` **保留（必须 0）**。

| 位号 | 名称 | 触发条件 |
|------|------|---------|
| `[48]` | IGPTRAP | 取指：L1 `P = 0` 且 `SP = 0`，或 L2 `P = 0`（普通页缺失） |
| `[49]` | ISPTRAP | 取指：L1 `P = 0` 且 `SP = 1`（超页缺失） |
| `[50]` | IGPFTRAP | 取指：L2 `P = 1` 且 GPF 对应小页位 = 0（普通页小页缺失） |
| `[51]` | ISPFTRAP | 取指：L1 `P = 1`、`SP = 1` 且 SPF 对应小页位 = 0（超页小页缺失） |
| `[52]` | DGPTRAP | 数据读写：L1 `P = 0` 且 `SP = 0`，或 L2 `P = 0` |
| `[53]` | DSPTRAP | 数据读写：L1 `P = 0` 且 `SP = 1`（超页缺失） |
| `[54]` | DGPFTRAP | 数据读写：L2 `P = 1` 且 GPF 对应小页位 = 0 |
| `[55]` | DSPFTRAP | 数据读写：L1 `P = 1`、`SP = 1` 且 SPF 对应小页位 = 0 |
| `[56]` | ADWBFAIL | PTE 物理写失败（`clean`/`flush`/条目替换的回写，见 §2.2.5、§4.5） |
| `[57]` | NONPTW | 非页表类访存故障：cfx 空间非法访问/取指、未实现 cfx 的普通 `ld/st`、核内存储块故障、`ptw_enable = 0` 的访存 |

**（五）wyde 归属与用法**：

- **wyde 归属互斥**：`CFXPERM` 下**只有 wyde2 有效、wyde3 必须全 0**；`CFXMEM` 下**只有 wyde3 有效、wyde2 必须全 0**；其它任何 cause 下**两个 wyde 都必须全 0**；子原因位非 0 而归属不符，按「未列出位被错误触发」处理（不可恢复错误）。
- **handler 取值**：拿到 `CFXPERM` 时子原因 = `(cause_id >> 32) & 0xFFFF`；拿到 `CFXMEM` 时子原因 = `(cause_id >> 48) & 0xFFFF`。
- 两类 cause 下各自 wyde 内**恰一位**为 1（one-hot）；取指用 `I` 前缀、数据读写用 `D` 前缀。

**（六）`CFXMEM`/`CFXPERM` 的 `excp_cause_info` 恒为地址**（一个 cause 只有一种 info 类型，处理程序不按子原因再分支）：

- `CFXMEM`：访存地址；`ADWBFAIL` 时 = **PTE 物理地址**；`NONPTW` 时 = **被访问的核内地址**。
- `CFXPERM`：页表或 `cfxmem` 权限拒绝 = **触发访存的地址**；`cfxexe` 拒绝 = **目标 IP**；`cfxtrap`/`cfx2rd`/`cfx2rc` 的来源掩码拒绝（`NCFXPERM`）= **触发指令的地址**，与 `excp_cause_ip` 同值——这是**刻意的统一**（不是冗余或错误），使处理程序在任一 `CFXPERM` 下都按地址解释 `info`。

其它 cause 的 `cause_info` 语义不变（见各核芯功能扩展的异常原因表）。

### 3.7 cg6 - 暂存寄存器

每个核芯功能扩展都有暂存寄存器（cg=6），数量由 `cfx_⟨cfxname⟩_scratch_regs_num`（cg=4, rc=6）指定，硬件实现至少 2 个、最多 64 个。

暂存寄存器从 rc=0 开始连续分配。`cfx_⟨cfxname⟩_scratch_regs_num` = N 时，有效的暂存寄存器为 rc=0 至 rc=N−1。读写不存在或超出数量的暂存寄存器（rc ≥ N）触发 CFXREG 异常。

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 6 | 0−(N−1) | scratch regs | cfx_⟨cfxname⟩_scratch_regs[0..N−1] | 未定义 | RW | 暂存寄存器（软件用） |

### 3.8 cg7 - 内部空间描述寄存器

每个核芯功能扩展用 cg7 描述自身的核内空间（§2.1 的 42 位内部地址空间）。每 **4 个 rc 描述一个空间**，空间块编号 `i = 0..15`，共 **16 块**，正好用完 `rc0–rc63`（`rc = 4i + 0..3`）。

- `rc4i+0`（描述字）：`bit0 = exists`；`bit1 = SRAM`、`bit2 = ROM`、`bit3 = MMIO`、`bit4 = DRAM`、`bit5 = OTHER`（存在时 one-hot）；其余位保留、读 0。
- `rc4i+1`（start）：42 位内部起始偏移；该空间的完整核内地址 = `(cfxha << 42) | start`。
- `rc4i+2`（size）：空间字节数；须满足 `start + size ≤ 2^42`。
- `rc4i+3`（attr）：`bit0 = R`、`bit1 = W`、`bit2 = X`、`bit3 = cacheable`、`bit4 = shareable`、`bit5 = volatile/device`；其余位保留、读 0。
- `exists = 0` 时 `start`/`size`/`attr` 读 0；`exists = 1` 时类型位恰好一个为 1（实现须静态保证，不存在软件可写的非法编码）。
- 未实现的空间填 `exists = 0`；实现须静态给出 16 块表。
- cg7 **全部只读**；对任意 cg7 rc 的写访问触发 `CFXREG`。
- cg7 只描述空间，**不做传输控制**；核内存储块批量传输指令仍为已删除指令，不再定义其行为。

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 7 | 4i+0 | space desc | cfx_⟨cfxname⟩_space_desc[i] | HW | RO | 空间块 `i`（`i = 0..15`）描述字：bit0=exists；bit1=SRAM；bit2=ROM；bit3=MMIO；bit4=DRAM；bit5=OTHER（exists=1 时 one-hot）；其余位保留读 0 |
| 7 | 4i+1 | space start | cfx_⟨cfxname⟩_space_start[i] | HW | RO | 空间块 `i` 的 42 位内部起始偏移；完整核内地址由 (cfxha << 42) 与该 start 拼接；exists=0 时读 0 |
| 7 | 4i+2 | space size | cfx_⟨cfxname⟩_space_size[i] | HW | RO | 空间块 `i` 的字节数；须满足 start + size ≤ 2^42；exists=0 时读 0 |
| 7 | 4i+3 | space attr | cfx_⟨cfxname⟩_space_attr[i] | HW | RO | 空间块 `i` 的属性：bit0=R；bit1=W；bit2=X；bit3=cacheable；bit4=shareable；bit5=volatile/device；其余位保留读 0；exists=0 时读 0 |

## 4. 专有寄存器设计规范

cg8-cg63 为专有寄存器设计，不同的核芯功能扩展设计规范不同。此外，不同核芯功能扩展的异常编号不同，也在这部分分别说明。

### 4.1 cfx_umon - user monitor

**专有寄存器表**

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 8 | 1 | async intr mask | cfx_umon_async_intr_mask | 全1 | RW | 本运行模式的异步来源掩码；位索引 = 源 cfxha（TIMER=15、PMEM_DMA=32），0=允许、1=屏蔽；投递时按**当前运行模式**取对应 monitor 的该寄存器求值（§5.4） |

`trap`/`escape` **不保存、不恢复**该掩码（它是来源策略，不是异常现场）。

**异常原因表**

| excp cause id | 名称      | 触发条件      | 是否可屏蔽 | excp cause info                |
| --------   | ------  | --------- | ---------- | ---------                   |
| `1 << 0`   | CFXTRAP | 功能调用      | 否 | 指令编码                        |
| `1 << 1`   | CFXMEM  | 访问核内地址空间或内部存储块故障 | 否 | 访存地址（A/D 回写失败时 = PTE 物理地址；非页表类 = 被访问的核内地址）；子原因见 §3.6 wyde3 |
| `1 << 2`   | CFXREG   | 非法核芯功能扩展寄存器访问 | 否 | 指令编码         |
| `1 << 3`   | CFXESC   | escape 帧或目标错误 | 否 | 指令编码         |
| `1 << 7`   | CFXPERM  | cfx 两轴权限拒绝 | 否 | 地址：页表/`cfxmem` 权限拒绝 = 访存地址；`cfxexe` 拒绝 = 目标 IP；`cfxtrap`/`cfx2rd`/`cfx2rc` 拒绝 = 触发指令地址（与 `excp_cause_ip` 同值）；子原因见 §3.6 wyde2 |
| `1 << 8`   | ILLI    | 非法指令      | 否 | 指令编码                        |
| `1 << 9`   | UNDI    | 未定义指令     | 否 | 指令编码                        |
| `1 << 10`  | RASOF   | RAS上溢     | 否 | 准备压栈的返回地址                   |
| `1 << 11`  | RASUF   | RAS下溢     | 否 | 全零（无效）                      |
| `1 << 12`  | MALIGN  | 非对齐访存    | 否 | 访存地址                        |
| `1 << 13`  | IALIGN  | 取指未对齐    | 否 | IP 值                          |

### 4.2 cfx_jmon - jail monitor

**专有寄存器表**

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 8 | 1 | async intr mask | cfx_jmon_async_intr_mask | 全1 | RW | 本运行模式的异步来源掩码；位索引 = 源 cfxha，0=允许、1=屏蔽；投递时按当前运行模式取对应 monitor 的该寄存器求值（§5.4） |

异常原因编码与 cfx_umon 一致；`CFXMEM`/`CFXPERM` 的 `cause_info` 恒为地址，子原因见 §3.6（wyde3 / wyde2）。

### 4.3 cfx_smon - supervisor monitor

**专有寄存器表**

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 8 | 1 | async intr mask | cfx_smon_async_intr_mask | 全1 | RW | 本运行模式的异步来源掩码；位索引 = 源 cfxha，0=允许、1=屏蔽；投递时按当前运行模式取对应 monitor 的该寄存器求值（§5.4） |

异常原因编码与 cfx_umon 一致；`CFXMEM`/`CFXPERM` 的 `cause_info` 恒为地址，子原因见 §3.6（wyde3 / wyde2）。

### 4.4 cfx_hmon - hypervisor monitor

**专有寄存器表**

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 8 | 1 | async intr mask | cfx_hmon_async_intr_mask | 全1 | RW | 本运行模式的异步来源掩码；位索引 = 源 cfxha，0=允许、1=屏蔽；投递时按当前运行模式取对应 monitor 的该寄存器求值（§5.4） |

hmon 为 hypv 下的同步异常处理核芯功能扩展，处理 hypv 下的同步异常。hmon 核芯功能扩展的寄存器的读写，只有当前运行环境是 hypv 时才能进行，否则触发 CFXREG 异常。

异常原因编码与 cfx_umon 一致（表见 §4.1）；`CFXMEM`/`CFXPERM` 的 `cause_info` 与子原因见 §3.6（wyde3 / wyde2）。

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

PTE 格式、两级页表步进、HSJU/R/W/X 页权限与异常优先级见 §2.2.1–§2.2.6。TLB 并入本核芯功能扩展：没有独立的 TLB 核芯功能扩展，也没有 `tlb_enable`/`tlb_exist`；TLB 命中时产生的异常按当前运行模式 monitor 路由（见 §2.2.6、§5.2）。

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
- 回写只把挂起的 `A`/`D` 位做**原子 OR** 写入 PTE（保留其他字段）；回写成功后清挂起位。页表页必须可写；回写失败（PTE 物理写失败）按当前运行模式 monitor 的 `CFXMEM` 处理，`cause_info` = PTE 物理地址，失败条目保留。软件清 A/D 后必须显式失效对应条目。

**失效接口（正交语义）**

- `cfx_ptw_tlb_control` 的三个维度互相独立：操作（`[1:0]`）、地址范围（`[3:2]`）、ASID（`bit4` = `ASID_ANY`，`1` = 所有 ASID，`0` = 匹配 `cfx_ptw_tlb_asid`）。
- **判序**：先判操作（`[1:0]`），再判地址范围与操作数。
  - `00 = none`：**无条件 no-op**——不报异常，且不检查地址范围编码与 `size`（`地址范围 = 11` 或 `range` 且 `size = 0` 在该操作下同样不报异常）；`ASID_ANY`/start/size 均被忽略。
  - `01 = clean`：回写 A/D，保留条目。`10 = invalid`：只删除条目，不回写。`11 = flush`：回写 A/D 后删除条目；回写失败时**不删除该条目**，按当前运行模式 monitor 的 `CFXMEM` 处理（`cause_info` = PTE 物理地址）。这三种操作才校验地址范围编码。
- 地址范围（仅 `clean`/`invalid`/`flush` 生效）：`00 = all` 忽略 start/size；`01 = VA` 只匹配包含 `tlb_addr_start` 的条目（忽略 size）；`10 = range` 匹配与 `[start, start+size)` 相交的条目；`11 = reserved` 或 `range` 且 `size = 0` ⇒ `CFXREG`（非法操作数）。
- ASID 维度与 `G`：`ASID_ANY = 1` 时包含 `G = 1` 的条目；`ASID_ANY = 0` 时只处理 `G = 0` 且 ASID 匹配的条目，**不碰 `G` 条目**。
- 正常完成（含 `none`）不产生异常；只有 `clean`/`invalid`/`flush` 的非法编码/操作数触发 `CFXREG`。

**异常原因表**

| excp cause id | 名称     | 触发条件      | 是否可屏蔽 | excp cause info |
| --------   | ------ | --------- | ---------- | ---------    |
| `1 << 0`   | CFXTRAP  | 功能调用      | 否 | 指令编码         |
| `1 << 3`   | CFXESC   | escape 帧或目标错误 | 否 | 指令编码         |

`cfx_ptw` 不再定义页表异常原因：页表未映射与 A/D 回写失败归当前运行模式 monitor 的 `CFXMEM`，页表权限拒绝（HSJU 或 R/W/X 不符）归 `CFXPERM`（§2.2.6、§5.2）；两者的 `cause_info` 恒为地址、子原因见 §3.6（wyde3 / wyde2；`cfx_ptw` 自身只报 `CFXTRAP`/`CFXESC`，故其两个 wyde 恒为 0）。表中未列出的位（含 `1 << 1`/`1 << 2`/`1 << 7` 等）为保留。

### 4.6 cfx_cache - cache organization

`cfx_cache` 管理本 hart 的指令 cache（I）与数据 cache（D）。cache 以**物理地址（PA）**为键（不是按 VA 索引），故控制字没有 ASID 维度；cache 的容量、行大小、组数与替换策略由实现决定。

**专有寄存器表**

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 8 | 0 | cache exist | cfx_cache_exist | — | RO | 硬件设置：bit0 = 有 I-cache；bit1 = 有 D-cache；其余位保留、读 0 |
| 8 | 8 | cache enable | cfx_cache_enable | 同 cache_exist | RW | 软件配置：bit0 = I、bit1 = D，0 = 关闭、1 = 开启；复位后每一位等于对应的 cache_exist 位（已存在的 I/D cache 默认开启）；cache_exist 位为 0 的位置写 1 无效果、读回 0；其余位保留、读 0 |
| 8 | 9 | cache ctrl | cfx_cache_ctrl | 0 | WO | `[1:0]` 操作 = `00 = none`、`01 = clean`、`10 = invalidate`、`11 = flush`；`[3:2]` 范围 = `00 = all`、`01 = PA 单行`、`10 = PA 区间`、`11 = reserved`；`[15:14]` 选择（bit15 = I、bit14 = D）；其余位保留、写忽略 |
| 8 | 10 | cache addr start | cfx_cache_addr_start | 0 | RW | 维护范围的起始物理地址（完整 `PA[55:0]`）；`[63:56]` 保留、读 0、写忽略 |
| 8 | 11 | cache addr size | cfx_cache_addr_size | 0 | RW | 维护范围的字节数（`PA 区间` 用，其它范围忽略） |

`cg8` 的其余 rc 保留，读写触发 `CFXREG`。

**维护命令语义**

`cfx_cache_ctrl` 是写即执行的命令寄存器（WO，无完成状态位）；该写指令**同步完成**——指令返回即生效，其后的访存必见维护结果。

- **判序**：先判 `[15:14]` 选择位、再判 `[1:0]` 操作，最后才判 `[3:2]` 范围与操作数。
  - `[15:14] = 00`（两侧都不选）：**无条件 no-op**，不报异常，且**不检查**范围编码与 `addr_size`。
  - `[1:0] = 00`（`none`）：**无条件 no-op**，不报异常，且**不检查**范围编码与 `addr_size`；`addr_start`/`addr_size`/选择位均被忽略。
  - 只有「选中至少一侧」且操作不是 `none` 时才校验范围编码与 `addr_size`。
- **非法编码/操作数**（仅在需要校验时）：`[3:2] = 11`（reserved），或 `[3:2] = 10`（`PA 区间`）且 `addr_size = 0` ⇒ `CFXREG`（`cause_info` = 指令编码）。
- **三档范围**（仅在被选中且操作非 `none` 时生效）：`all` 忽略 `addr_start`/`addr_size`，作用于被选中一侧的全部 cache；`PA 单行` 只作用于**包含** `addr_start` 的那个 cache 行（忽略 `addr_size`）；`PA 区间` 作用于与 `[addr_start, addr_start + addr_size)` **相交**的 cache 行。三档的范围匹配一律按 **56 位物理地址**逐位比较（`addr_start` 即完整 PA，见下表 `cg8 rc10`）。
- **两侧的三种操作**：
  - **I 侧**：`clean` = no-op（I-cache 无 dirty 状态）；`invalidate` = 丢弃；`flush` 等价 `invalidate`。
  - **D 侧**：`clean` = 写回并清 dirty；`invalidate` = 丢弃（其中的脏数据随之丢失，**不写警告、不报异常**）；`flush` = 写回后丢弃。
- **两侧全选的判序**：`[15:14] = 11` 时先处理 I 侧、再处理 D 侧；两侧各自按所选范围匹配，互相独立。
- **使能**：`cfx_cache_enable` 对应位 = 0 时，该侧**不被维护**（`clean`/`invalidate`/`flush` 对该侧都无效果、不改变其内容）；编码与 `addr_size` 的校验**不受使能影响**（仍按上文判序执行，非法即 `CFXREG`）。
- **不适用地址**：`addr_start`（`PA 区间` 时连同整个区间）落在不可缓存或 MMIO/device 的 PA 上时，命令对该部分**无效果、不报异常**——判定依据是 `cg7` 空间描述（`attr.cacheable = 0`，或空间类型为 MMIO，见 §3.8）；内存窗口（`addr[47:42] = 0`）没有 `cg7` 空间描述，其可缓存性由实现决定。区间跨越可缓存与不可缓存部分时，只作用于可缓存部分。
- **per-hart**：`cfx_cache` 的寄存器与维护命令都是 per-hart 状态，命令只作用于执行该写指令的 hart；跨 hart 的维护传播与一致性不在本节定义。
- **正常完成不报异常**：`none`、两侧都不选、`cache_enable` 对应位为 0（该侧不被维护）这几种情形，以及各操作的正常路径，都不产生异常；非法编码仍按上文报 `CFXREG`；`cfx_cache` 自身只报下表的 `CFXTRAP`/`CFXESC`，不新增异常原因，也不因 `invalidate` 丢脏数据报任何异常。

**异常原因表**

| excp cause id | 名称     | 触发条件      | 是否可屏蔽 | excp cause info |
| --------   | ------ | --------- | ---------- | ---------    |
| `1 << 0`   | CFXTRAP  | 功能调用      | 否 | 指令编码         |
| `1 << 1`   | CFXMEM   | 访问核内地址空间或内部存储块故障 | 否 | 访存地址（非页表类，子原因 `[57] NONPTW`，见 §3.6 wyde3） |
| `1 << 2`   | CFXREG   | 非法核芯功能扩展寄存器访问 | 否 | 指令编码         |
| `1 << 3`   | CFXESC   | escape 帧或目标错误 | 否 | 指令编码         |

### 4.7 cfx_hart - hart management

管理独立的指令流水线（hart）。多核时每个 hart 有独立的 cfx_hart。

**专有寄存器表**

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 8 | 0 | hart id | cfx_hart_hart_id | — | RO | 硬件设置，hart 编号（0-based） |
| 8 | 1 | — | — | — | — | 保留 |
| 8 | 2 | cycle | cfx_hart_cycle | 0 | RO | 本地周期数（64 位） |
| 8 | 3 | insn | cfx_hart_insn | 0 | RO | 退休指令数（64 位） |
| 8 | 4 | timer cmp | cfx_hart_timer_cmp | 0 | RW | 64 位定时器比较值（绝对时间，单位同 cfx_time_value） |
| 8 | 5 | timer ctrl | cfx_hart_timer_ctrl | 0 | RW | bit0=ENABLE，bit1=IMASK，bit2=ISTATUS（RO）；其余保留 |
| 8 | 6 | — | — | — | — | 保留 |
| 8 | 7 | — | — | — | — | 保留 |
| 9 | 0–15 | 异步现场寄存器组 | — | — | — | `cfx_hart` 专有，7 槽 + `rc7`–`rc15` reserved，逐项见下表 |

**cg9 异步现场寄存器（`cfx_hart` 专有）**

`cg9` 是 `cfx_hart`（cfxha 15）专有的**异步现场寄存器组**；其他 cfx 不实现 `cg9`（访问 ⇒ `CFXREG`）。本表 7 槽，`rc7`–`rc15` reserved（访问触发 `CFXREG`）。

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 9 | 0 | async prev run mode | cfx_hart_async_prev_run_mode | 0 | HW/RW | 异步前运行模式（2 位）；硬件进入时写，软件可写（快照/重建用） |
| 9 | 1 | async prev cfx code | cfx_hart_async_prev_cfx_code | 0 | HW/RW | 异步前当前核芯功能扩展编号（6 位）；硬件进入时写，软件可写 |
| 9 | 2 | async cause ip | cfx_hart_async_cause_ip | 0 | HW/RW | 异步精确点 = **已提交指令之后的 `rb0`**（48 位，4 字节对齐；跳转即目标）；硬件进入时写，软件可写 |
| 9 | 3 | async src frame | cfx_hart_async_src_frame | 0 | HW/RO | 本帧源集合（64 位位图，位 = 源 cfxha）；**非 0 = 有效帧**；硬件进入时写，合法 `escape` 返回时清 0 释放帧；软件写忽略 |
| 9 | 4 | async src pending | cfx_hart_async_src_pending | 0 | HW/RO | 未投递源集合（64 位位图，位 = 源 cfxha）；源事件置位、投递即清、源 ack 即落；软件写忽略 |
| 9 | 5 | async excp vector | cfx_hart_async_excp_vector | 0 | RW | supv 异步向量入口（48 位，4 字节对齐；写忽略低 2 位、不产生异常） |
| 9 | 6 | async switch run mode | cfx_hart_async_switch_run_mode | 2 | RW | 异步进入时切换的运行模式；固定 supv（2） |
| 9 | 7–15 | reserved | — | — | — | 保留；访问触发 `CFXREG` |

- **有效帧判据** = `async_src_frame != 0`；**from_user** = `async_prev_run_mode == user`（`rc0`）。
- `async_prev_run_mode` 取 2 位（0=user、1=jail、2=supv、3=hypv）；`async_prev_cfx_code` 取 6 位（cfxha）；`async_cause_ip`/`async_excp_vector` 取 48 位核内地址（按 4 字节对齐落盘）。
- `rc3`/`rc4` 两个位图**只由硬件写、软件只读**；`rc0`–`rc2` 为 `HW/RW`（硬件进入时写、软件可读写，供快照/重建）；`rc5`/`rc6` 为软件可读写配置。

`cfx_time_value >= cfx_hart_timer_cmp` 且 `ENABLE=1` 时置 `ISTATUS`；`IMASK=0` 时触发 TIMER 中断。写新的 `timer_cmp` 即清除本次条件（并落 `async_src_pending` 的 bit 15）；写全 1 关闭。

**异步中断入口与返回（hart-first）**

`cfx_hart` 是所有异步源（`TIMER` = 本 cfx、`PMEM_DMA` = `cfx_pmem`）的**唯一投递目标**（§5.4）：源身份 = **源 cfxha**（15/32），不占 `excp_cause_id`；入口为 **supv 单向量**——向量 = `cg9 rc5`（`async_excp_vector`）、目标模式 = `cg9 rc6`（`async_switch_run_mode`，固定 supv）、现场 = `cg9`；来源掩码不在本 cfx，而由**当前运行模式 monitor** 的 `cg8 rc1` 求值（§4.1–§4.4、§5.4）。**一帧多源**：同一指令边界上所有 pending 且放行的源一次性进入同一帧（`async_src_frame` 位图并集），`async_src_pending` 扣除对应位，`excp_async_num` 每次进入 +1、与源个数无关。**无嵌套**：帧活动期（`async_src_frame != 0`）到达的新事件只置 `async_src_pending`，不进入。**pending 跟随源**：源事件置位、投递即清、源 ack 即落（`timer_cmp` 重装 / `dma_status` W1C），不计数、软件不写。返回用 `escape cfx_hart` 并以 `imms18` bit1 = 1 选 `cg9` 现场（§5.1、§5.4）：合法返回即由硬件清 `async_src_frame` 释放帧，恢复 `async_prev_run_mode`/`async_prev_cfx_code` 并以 `async_cause_ip` 续跑，**不重放**被中断指令。本 cfx 的 `excp_async_num`（`cg4 rc4`）计异步进入次数，`escape_num`（`cg4 rc5`）计退出次数。

**异常原因表**

| excp cause id | 名称     | 触发条件      | 是否可屏蔽 | excp cause info |
| --------   | ------ | --------- | ---------- | ---------    |
| `1 << 0`   | CFXTRAP  | 功能调用      | 否 | 指令编码         |
| `1 << 1`   | CFXMEM   | 访问核内地址空间或内部存储块故障 | 否 | 访存地址         |
| `1 << 2`   | CFXREG   | 非法核芯功能扩展寄存器访问 | 否 | 指令编码         |
| `1 << 3`   | CFXESC   | escape 帧或目标错误 | 否 | 指令编码         |
| `1 << 8`   | IPI       | 核间中断      | 可 | 中断源 hart ID（低 6 位有效，高 58 位保留为 0） |

异步源（`TIMER`/`PMEM_DMA`）**不占本表**：源身份 = 源 cfxha，见 `cg9 async_src_frame` 的位（§5.4）；`IPI` 为可屏蔽的核间中断，沿用本表行。

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
| `1 << 3`   | CFXESC   | escape 帧或目标错误 | 否 | 指令编码         |

### 4.9 cfx_pmem - physical memory management

cfx_pmem 管理物理存储器（Physical Memory, PM）区域，最多支持 64 个不连续 PM 区域。PM 仅指普通 DRAM 存储器，与 device 或 MMIO 无关——device 的存储空间由各设备核芯功能扩展自行管理。

cfx_pmem 内含一段 **64 KiB SRAM**，固定在 cfx_pmem 内部偏移 0x3ff_0000_0000（核内地址 = cfxha 32、低 42 位偏移）。CPU 用普通 `ld/st` 同步访问该 SRAM；访问超出 64 KiB 的核内偏移触发 CFXMEM。cfx 访问权限不在本章定义。

SRAM 与物理存储器（PA）之间的块搬运由 cfx_pmem 的 DMA 完成（不新增指令，不设 per-cfx DMA）：

- **方向**：`CFX→PA`（SRAM 读到 PA）或 `PA→CFX`（PA 读到 SRAM）。
- **地址**：`dma_src`/`dma_dst` 为 64 位；CFX 侧只取低 42 位、PA 侧只取低 56 位，高位**忽略**（不因高位非 0 报错）。
- **长度**：`dma_size` 为 30 位，合法范围 `1..2^29`（512 MiB）。实际传输还受 64 KiB SRAM 范围、PA 56 位不溢出与目标可访问性约束。
- **异步**：写 `dma_ctrl.START=1` 后 `dma_status.BUSY=1`，完成后硬件清 BUSY 并置 DONE（或 ERROR）；完成前软件不得复用 SRAM 与寄存器。
- **单 hart**：`PMEM_DMA` 作为异步源统一投递到本 hart 的 `cfx_hart`（cfxha 15，§5.4），不进入 `cfx_pmem` 自身入口；多 hart 的接收者规则后续定义。

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
| `1 << 3`   | CFXESC   | escape 帧或目标错误 | 否 | 指令编码         |

**异步源标识（不占 `excp_cause_id`）**：`PMEM_DMA` 是异步源，**没有独立的 cause 编号**；源身份 = 本 cfx 的 cfxha（32），在 `cfx_hart cg9 async_src_frame` 中对应 bit 32。`dma_ctrl.IRQ_EN=1` 时 `DONE` 或 `ERROR` 置位触发，投递目标为 `cfx_hart`（§5.4）；被当前运行模式 monitor 的掩码屏蔽或 `cfx_hart` 帧活动期时置 `cfx_hart cg9 async_src_pending` 的 bit 32。异步进入**不携带 `cause_info`**：handler 按帧内位回本源读 `cfx_pmem_dma_status`（`cg15 rc4`，含 `ERR_CODE`）区分完成/出错。

> shareability、inner/outer cacheability 等进阶属性留待多核 SMP 阶段再定义。当前单核 MVP 仅需 prefetchable 和 coherent 位即可满足。

### 4.10 cfx_time - 全局时间计数器

`cfx_time` 为 **per-system** 全局时间计数器，所有 hart 共享同一时间基准；只提供时间读数，不产生中断。每 hart 的定时器比较与中断由 `cfx_hart` 提供。

**专有寄存器表**

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 10 | 0 | time freq | cfx_time_freq | — | RO | 计数频率（Hz），硬件设置 |
| 10 | 1 | time value | cfx_time_value | 0 | RO | 64 位全局时间计数值，自由运行 |
| 10 | 2-63 | — | — | — | — | 保留 |

**异常原因表**

| excp cause id | 名称          | 触发条件      | 是否可屏蔽 | excp cause info |
| --------   | ------      | --------- | ---------- | ---------    |
| `1 << 0`   | CFXTRAP     | 功能调用      | 否 | 指令编码         |
| `1 << 1`   | CFXMEM      | 访问核内地址空间或内部存储块故障 | 否 | 访存地址         |
| `1 << 2`   | CFXREG      | 非法核芯功能扩展寄存器访问 | 否 | 指令编码         |
| `1 << 3`   | CFXESC   | escape 帧或目标错误 | 否 | 指令编码         |

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
| `1 << 3`   | CFXESC   | escape 帧或目标错误 | 否 | 指令编码         |
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
| `1 << 3`   | CFXESC   | escape 帧或目标错误 | 否 | 指令编码         |
| `1 << 8`   | POWEROFF    | 硬件关机      | 否 | 全零         |
| `1 << 9`   | HARD_RESET | 硬件重启      | 否 | 全零         |
| `1 << 10`  | SOFT_RESET | 软件重启      | 否 | 指令编码         |

## 5. 异常进入与异常退出

**重要**：异常原因编码（`excp cause id`）分层——`[15:0]` **同步 cause one-hot** 在各核芯功能扩展间 **独立编址**（例如 `1<<8` 在 cfx_umon 中为 ILLI、在 cfx_hart 中为 IPI，互不干扰）；`[31:16]` **保留**，**异步源不占 `excp_cause_id`**（源身份 = 源 cfxha，见 §5.4）。每个 cfx 的同步 cause 空间为 0-15，硬件通过 cfxha 区分目标。

**精确异常**：除下段的**多元素内存指令例外**外，所有同步异常和异步中断均为精确异常——同步异常的 `cause_ip` 指向触发指令、指令未完成（目标寄存器/内存/RA 未更新，无副作用）；异步中断在**指令边界**识别、被中断指令**已提交**（`rb0` 已更新；`call` 已写 `ra63`、`ret` 已弹栈），返回点是提交后的 `rb0`（§5.4）。页表步进异常（页表未映射 `CFXMEM`、权限拒绝 `CFXPERM`）同为精确——访存未执行。IALIGN 为精确异常——取指前检测 IP[1:0] ≠ 00，IP 停留在非法地址。浮点指令不触发异常，始终按 IEEE 754 标准返回结果，异常状态记录在 rf0[4:0] 中。

**多元素内存指令例外（允许部分生效）**：取数存数类的多元素内存指令 `ldm.*`/`stm.*`（含 rf 形式 `ldm.t`/`ldm.o`/`stm.t`/`stm.o`，见 SimRISC-01）——**不要求**无副作用：处理多个元素的过程中若触发同步异常（如 `MALIGN`/`CFXMEM`/`CFXPERM`），异常进入时**允许此前已处理的元素已经生效**，即目的寄存器或内存可能已被部分更新。本条只解除「无副作用」要求，**不改变**异常原因、触发条件与 `excp_cause_ip`：**异常原因码必须与触发元素一致**，`excp_cause_ip` 仍指向该指令；软件因此不得假定这类指令异常时目的寄存器/内存保持原状。本例外成立的前提是**地址寄存器不被传送过程改写**：`ldm` 的基址/索引寄存器落入传送范围已被禁止（违反 ⇒ `ILLI`，见 SimRISC-01），`stm` 不写寄存器 ⇒ 无论异常落在哪个元素，地址都不随已生效元素改变。**单元素** `ld`/`st`（`rrii` 形式）仍须精确，本例外不适用；多元素指令即使异常源自页表步进或地址窗口检查，也按本条允许部分生效，而非按上段「页表步进异常访存未执行」处理。

**寄存器类多元素指令不适用本条（仍须精确）**：`rd2rd`/`rb2rb`/`rb2rd`/`rd2rb`/`ra2rd`/`rd2ra`、`rd2rf`/`rf2rd`/`rf2rf`（见 SimRISC-02）与 `ftcls`/`focls`（见 SimRISC-07）均为**精确异常**：其非法条件（见 SimRISC-02 / SimRISC-07 的限制列表）在**处理任何元素之前**判定，异常进入时**不修改**目的寄存器，IP 指向该指令、异常原因码正确。同寄存器组的块复制（`rd2rd`/`rb2rb`/`rf2rf`）**禁止源/目的范围重叠**，其余形态跨寄存器组、结构性不可重叠；禁止重叠可避免后续元素读到前面元素留下的中间态、使结果依赖元素处理顺序。

**精确是允许的更强行为，非必需**：实现可以在执行前对全部元素做**整段预检**，任一检查失败即不产生任何副作用，从而让上述多元素内存指令表现为精确。这是**允许的更强行为**；软件**不得依赖**它——未做整段预检的实现同样合规，同一程序在该实现上可能观察到部分生效。

**中断信号为电平触发**：硬件源持续有效且掩码放行时，中断在指令边界检查。mask 解除后若 pending 仍置 1，在下一指令边界进入。同一指令边界上所有 pending 且放行的源**一次性进入同一帧**（`async_src_frame` 位图并集），不按 cfxha 串行投递，也不拆成多帧（§5.4）。

**系统控制例外**：POWEROFF/HARD_RESET/SOFT_RESET 为系统控制动作，不适用一般异常处理的 IP/寄存器保存语义。

**异常嵌套由软件解决**：各核芯功能扩展如可能发生同 cfx 嵌套异常，应在进入功能处理函数前保存当前异常现场（`excp_prev_*`、`excp_cause_*`），退出时恢复。硬件不阻止同 cfx 嵌套，但若软件未保存现场，再次进入会覆盖上一次的现场数据。

### 5.1 指令行为说明

trap/escape/cfx2rd/cfx2rc 指令可以在任意运行模式下执行。若 cfxha 为 reserved 核芯功能扩展（6-14、16-31、35-61），硬件触发 ILLI 异常。对于常见的操作系统而言，并不希望由 user/jail 直接陷入或访问 hmon 到 power 之间的核芯功能扩展，则需要在这些核芯功能扩展的初始化代码中，设置好 `cfxtrap`/`cfxreg`/`cfxmem`/`cfxexe` 的来源 mask（缺省只允许 hmon）。

`escape` 指令的第一个参数 `cfxha` 必须是**当前执行的 cfx**；返回的 cfx、运行模式和指令指针全部取自当前 cfx 的**所选帧**——同步异常帧为 `cg5`（§3.6），异步现场为 `cfx_hart cg9`（§4.7）。若 `cfxha` 非当前 cfx（目标错误）或所选帧无效（同步帧 `excp_cause_id = 0`；异步现场 `async_src_frame = 0`，或当前 cfx 无 `cg9`），硬件在切换前触发当前 cfx 的 `CFXESC`，不改变 cfx/运行模式。

`escape` 指令的第二个参数：**编码层** `imms18`（指令字偏移），其中 `imms18[0]` 为字节偏移的 bit2、`imms18[1]` 为**帧选择位**（0 = `cg5` 同步异常帧，1 = `cg9` 异步现场），`imms18[17:2]` 为 **SBZ**（手工编码非零 ⇒ `ILLI`）。合法 `imms18` 集合为 **`{0, 1, 2}`**：`0` = `cg5` 帧、字节偏移 0；`1` = `cg5` 帧、字节偏移 +4；`2` = `cg9` 异步现场、偏移恒 0（`cg9` **只允许偏移 0**）；`3`（`cg9` 帧 + 偏移 +4）⇒ `ILLI`。帧选择位为 0 时 `Addr = excp_cause_ip + (imms18 << 2)`，为 1 时 `Addr = async_cause_ip`。**汇编层** `imms20` 以字节为单位（`imms20 = imms18 << 2`），合法值 **`{0, 4, 8}`**，其中 `8` 表示选 `cg9` 现场、实际偏移 0。偏移是编译期固定的立即数，不支持任意地址跳转。常见用法如下：

| 用例 | 指令 | 返回位置 |
|------|------|---------|
| 重新执行触发异常的指令（`cg5` 帧） | `escape cfxha, [excp_cause_ip, 0]` | cause_ip |
| 跳过触发指令（继续执行，`cg5` 帧） | `escape cfxha, [excp_cause_ip, 4]` | cause_ip + 4 |
| 异步中断返回（`cg9` 现场） | `escape cfx_hart, [async_cause_ip, 8]` | async_cause_ip（偏移 0） |

`escape` 选 `cg5` 帧时恢复 `excp_prev_run_mode`、`excp_prev_cfx_code`，并把 `excp_cause_ip`（加固定偏移）作为返回地址；选 `cg9` 现场时恢复 `async_prev_run_mode`、`async_prev_cfx_code`，把 `async_cause_ip` 作为返回地址，并由硬件**清 `async_src_frame` 释放本帧**（§4.7）。`escape` **不保存、不恢复**任何中断来源掩码（同步/异步皆然）：来源掩码是策略，不是异常现场。

### 5.2 异常进入流程

X-mode（任意运行模式）下发生同步异常时，硬件自动执行以下操作序列。**执行期同步异常先进入当前运行模式的 monitor**；monitor 是第一处理者，可自行处理并 `escape`，也可 `trap` 到源 cfx。异步中断的进入/退出见 §5.4，与同步异常彻底分流。

- 同步异常：当前运行模式到 monitor 的对应关系：`U-mode → cfx_umon (cfx0)`、`J-mode → cfx_jmon (cfx1)`、`S-mode → cfx_smon (cfx2)`、`H-mode → cfx_hmon (cfx3)`；使用**异常前**运行模式对应的 `<mode>_*` 寄存器行。

**（一）同步异常路由（全部不可屏蔽）**

| 触发或条件 | 异常原因 | 目标 cfx |
| --- | --- | --- |
| `trap`/`cfx2rd`/`cfx2rc`，`cfxha` 为 reserved（`6–14`、`16–31`、`35–61`） | `ILLI` | 当前运行模式 monitor |
| `trap`/`cfx2rd`/`cfx2rc`，目标 cfx 的 `<mode>_cfxtrap`/`<mode>_cfxreg` 拒绝源 cfx | `CFXPERM` | 当前运行模式 monitor |
| `trap` 合法且被允许 | `CFXTRAP` | 目标 `cfxha` |
| `cfx2rd`/`cfx2rc` 合法且被允许 | 无（正常寄存器访问） | 不进入本流程 |
| 非法核芯功能扩展寄存器访问 | `CFXREG` | 当前运行模式 monitor（不进入被访问的核芯功能扩展） |
| 两轴权限拒绝（`cfxtrap`/`cfxmem`/`cfxreg`/`cfxexe` 来源 mask 拒绝）或页表权限拒绝（HSJU 或 R/W/X 不符） | `CFXPERM` | 当前运行模式 monitor |
| 核内地址空间或内部存储故障 | `CFXMEM` | 当前运行模式 monitor |
| 非 `trap`/`escape`/`cfx2*` 路径的 `ILLI`/`UNDI`/`RASOF`/`RASUF`/`MALIGN`/`IALIGN` | 同名原因 | 当前运行模式 monitor |
| `escape` 帧错误或目标错误 | `CFXESC` | 当前核芯功能扩展（保持既有语义，不属于 monitor 路由） |

- `CFXMEM` 至少覆盖：`ptw_enable = 0` 且 `addr[47:42] = 0` 的普通访存；reserved cfx（`6–14`、`16–31`、`35–61`）的普通 `ld/st`；SRAM/MMIO 越界或非法核内偏移；页表**未映射**（L1/L2 `P = 0`、SPF/GPF 对应小页位为 0、fragment 缺失）；A/D 回写失败（PTE 物理写失败）。
- A/D 回写失败按当前运行模式 monitor 的 `CFXMEM` 处理，`cause_info` = PTE 物理地址；不进入 `cfx_ptw` 自己的异常入口，也不归 `CFXPERM`。
- 页表**未映射**归 `CFXMEM`，页表**权限**拒绝（HSJU 或 R/W/X 不符）归 `CFXPERM`，两者目标均为当前运行模式 monitor。
- reserved cfx 的普通 `ld/st` 归 `CFXMEM`，`trap`/`escape` 归 `ILLI`，两者目标均为当前运行模式 monitor。

**（二）monitor 异常编号**

monitor 的异常原因使用 DADAO 位索引（`excp_cause_id = 1 << n`）：

| 名称 | 位索引 |
| --- | --- |
| `CFXTRAP` | 0 |
| `CFXMEM` | 1 |
| `CFXREG` | 2 |
| `CFXESC` | 3 |
| `CFXPERM` | 7 |
| `ILLI` | 8 |
| `UNDI` | 9 |
| `RASOF` | 10 |
| `RASUF` | 11 |
| `MALIGN` | 12 |
| `IALIGN` | 13 |

monitor 不再有独立的页表异常原因：页表未映射与 A/D 回写失败归 `CFXMEM`，页表权限拒绝归 `CFXPERM`；A/D 回写失败的 `cause_info` = PTE 物理地址。

**（三）异常进入步骤**

1. **确定异常原因与目标 cfx**：同步异常按（一）与（二）确定（`CFXTRAP` 目标为目标 `cfxha`，`CFXESC` 目标为当前核芯功能扩展）。
2. **同步异常不可屏蔽**：同步异常全部不可屏蔽，不查任何异常原因掩码。
3. **更新陷入计数**：按异常类型递增目标 cfx 的 `trap_num`（`trap` 指令）或 `excp_sync_num`（其它同步异常）。
4. **保存现场**：把 `excp_prev_run_mode`（异常前运行模式）、`excp_prev_cfx_code`（异常前的当前核芯功能扩展编号 `inner_cfx_code`，**在本步之后才被第 5 步改写**）、`excp_cause_ip`（触发指令地址）、`excp_cause_id`、`excp_cause_info` 写入目标 cfx 的 `cg5`。**不保存任何中断来源掩码**（`trap`/`escape` 不搬移 monitor 的 `cg8 rc1`）。
5. **模式/目标切换**：`inner_run_mode` 取目标 cfx 的 `<mode>_switch_run_mode`，`inner_cfx_code` 取目标 cfx。
6. **跳转至异常向量**：跳转至目标 cfx 的 `<mode>_excp_vector`。该地址与普通访存规则一致：`ptw_enable=0` 或地址 `addr[47:42] != 0` 时为核内地址，`ptw_enable=1` 且 `addr[47:42] = 0` 时为虚拟地址。软件须保证异常向量所在页不会发生页缺失，硬件不提供向量缺失的恢复机制。

**（四）伪代码**

```
// 注：伪代码中 cause 为 one-hot 值（如 CFXTRAP = 1<<0 = 1，ILLI = 1<<8 = 256）；
//     异常原因表中 `1 << n` 的 n 即位索引，cause = 1 << n。
//     同步异常全部不可屏蔽；异步中断的进入/退出见 §5.4。
// 1. 确定异常原因与目标 cfx
// temp_monitor_code 为伪代码临时变量：当前运行模式 monitor（U-mode→0、J-mode→1、S-mode→2、H-mode→3）
case inner_run_mode of
    U-mode: temp_monitor_code <= 0
    J-mode: temp_monitor_code <= 1
    S-mode: temp_monitor_code <= 2
    H-mode: temp_monitor_code <= 3

if instruction ∈ {TRAP, CFX2RD, CFX2RC}:
    if cfxha ∈ {6..14, 16..31, 35..61}:
        cause          <= ILLI
        temp_cfx_code  <= temp_monitor_code         // reserved → 当前运行模式 monitor
    elif instruction == TRAP
       and (cfx_⟨cfxname⟩_<mode>_cfxtrap & (1 << inner_cfx_code)) != 0:
        cause          <= CFXPERM                   // 目标 cfxtrap mask 拒绝源 cfx → 当前 monitor
        temp_cfx_code  <= temp_monitor_code
    elif instruction ∈ {CFX2RD, CFX2RC}
       and (cfx_⟨cfxname⟩_<mode>_cfxreg & (1 << inner_cfx_code)) != 0:
        cause          <= CFXPERM                   // 目标 cfxreg mask 拒绝源 cfx → 当前 monitor
        temp_cfx_code  <= temp_monitor_code
    elif instruction == TRAP:
        cause          <= CFXTRAP                   // 合法且被允许 → 目标 cfx
        temp_cfx_code  <= cfxha
    else:
        ; CFX2RD/CFX2RC 合法且被允许 → 正常寄存器访问，不进入本流程
        return
elif instruction == ESCAPE:
    ; escape 帧错误/目标错误 → 当前 cfx（§5.3），不属于 monitor 路由
    cause          <= CFXESC
    temp_cfx_code  <= inner_cfx_code
elif sync_cause ∈ {CFXREG, CFXPERM, CFXMEM, ILLI, UNDI, RASOF, RASUF, MALIGN, IALIGN}:
    ; 同步异常（非 trap/escape/cfx2* 路径）一律进入当前运行模式 monitor
    temp_cfx_code  <= temp_monitor_code

// 2. 同步异常全部不可屏蔽，不查任何异常原因掩码

// 3. 更新陷入计数
if cause == CFXTRAP:
    cfx_⟨cfxname⟩_trap_num        <= cfx_⟨cfxname⟩_trap_num + 1
else:
    cfx_⟨cfxname⟩_excp_sync_num   <= cfx_⟨cfxname⟩_excp_sync_num + 1

// 4. 保存现场（不保存/恢复任何中断来源掩码）
cfx_⟨cfxname⟩_excp_prev_run_mode  <= inner_run_mode
cfx_⟨cfxname⟩_excp_prev_cfx_code  <= inner_cfx_code
cfx_⟨cfxname⟩_excp_cause_ip       <= inner_excp_cause_ip     // 同步为触发指令地址
cfx_⟨cfxname⟩_excp_cause_id       <= inner_excp_cause_id
cfx_⟨cfxname⟩_excp_cause_info     <= inner_excp_cause_info

// 5. 模式/目标切换
inner_run_mode <= cfx_⟨cfxname⟩_<mode>_switch_run_mode
inner_cfx_code <= temp_cfx_code

// 6. 跳转至异常向量
inner_inst_pointer <= cfx_⟨cfxname⟩_<mode>_excp_vector
```

同步异常全部不可屏蔽，不查异常原因掩码；异步中断的进入与退出见 §5.4。

### 5.3 异常退出流程

通过 `escape` 指令完成同步异常退出（`cg5` 帧，`imms18[1] = 0`）；`cfxha` 必须是当前执行的核芯功能扩展（`inner_cfx_code`）。异步现场（`cg9` 帧）的返回见 §5.4；两种帧的编码与合法性检查统一见 §5.1。下面的步骤和伪代码描述 `escape` 在 `cg5` 帧上的硬件语义：

0. **检查目标/帧**：若 `imms18[17:2] != 0`（SBZ 非零）或 `imms18 = 3`（`cg9` 现场且偏移 +4，非法），触发 ILLI；若 `cfxha` 为 reserved，触发 ILLI；若 `cfxha` 非当前 cfx，或所选帧无效（`cg5`：`excp_cause_id = 0`），在切换任何状态前触发当前 cfx 的 `CFXESC`。
1. **恢复运行模式与当前 cfx**：依据 `cfx_⟨cfxname⟩_excp_prev_run_mode` / `cfx_⟨cfxname⟩_excp_prev_cfx_code`，还原为异常发生前的运行模式与当前核芯功能扩展（`inner_cfx_code`）。
2. **更新退出计数并跳转**：`cfx_⟨cfxname⟩_escape_num` 递增 1；返回地址 = `excp_cause_ip + ((imms18 & 1) << 2)`（编译期固定偏移）。
3. **不恢复任何来源掩码**：`trap`/`escape` 不保存、不恢复 `cfx_<monitor>_async_intr_mask`（`cg8 rc1`），也不恢复其它 cfx 屏蔽状态。

```
// 0. 检查目标/帧（本节仅 cg5 同步帧；imms18[1] = 0）
if imms18[17:2] != 0:
    cause <= ILLI                            // SBZ 非零
    ; 进入当前模式 monitor
    goto check_nonmaskable
if imms18 == 3:
    cause <= ILLI                            // cg9 现场只允许偏移 0（本帧选择位为 0 时不会命中）
    ; 进入当前模式 monitor
    goto check_nonmaskable
if cfxha ∈ {6..14, 16..31, 35..61}:
    cause <= ILLI
    ; 进入当前模式 monitor
    goto check_nonmaskable
frame_ok <= (cfx_⟨cfxname⟩_excp_cause_id != 0)          // cg5 同步帧
if cfxha != inner_cfx_code or !frame_ok:
    cause <= CFXESC                            // 当前 cfx 帧/目标错误
    ; 进入当前 cfx（CFXESC 为不可屏蔽）
    temp_cfx_code <= inner_cfx_code
    goto check_nonmaskable

// 1. 恢复运行模式与当前 cfx（取自 cg5 帧）
inner_run_mode   <= cfx_⟨cfxname⟩_excp_prev_run_mode
inner_cfx_code   <= cfx_⟨cfxname⟩_excp_prev_cfx_code
// 2. 更新退出计数并跳转
cfx_⟨cfxname⟩_escape_num <= cfx_⟨cfxname⟩_escape_num + 1
inner_inst_pointer       <= cfx_⟨cfxname⟩_excp_cause_ip + ((imms18 & 1) << 2)
```

### 5.4 异步中断进入与退出

异步中断由 `cfx_hart`（cfxha 15）统一承接（hart-first），与同步异常分流：不进入当前运行模式 monitor，也不直接进入源 cfx。本节冻结进入/退出语义；源内动作（如 TIMER 计数、DMA 完成）仍由源 cfx 定义。

**（一）源身份与来源掩码**

- **源身份 = 源 cfxha**：`TIMER` = 15（本 cfx）、`PMEM_DMA` = 32（`cfx_pmem`）。异步源**不占 `excp_cause_id`**，没有独立 cause 编号；一个源 cfx 至多一个异步 cause，同源内的差异（`DONE`/`ERROR`、`ISTATUS`）回源 cfx 寄存器区分。
- **来源掩码归 monitor**：`cfx0`/`cfx1`/`cfx2`/`cfx3`（`umon`/`jmon`/`smon`/`hmon`）的 `cg8 rc1` 为 `cfx_<monitor>_async_intr_mask`：位 = 源 cfxha，`0=允许`、`1=屏蔽`，复位全 1。投递时按**当前运行模式**取该模式 monitor 的掩码求值（U→umon、J→jmon、S→smon、H→hmon）。
- **没有全局掩码/运行期行/保存掩码**：`cfx_hart cg9` 只放现场与两个位图；`trap`/`escape` 不保存、不恢复来源掩码。

**（二）pending 语义（跟随源事件）**

- `cfx_hart cg9 rc4`（`async_src_pending`）表达"该源当前有未投递事件"：源事件到达时硬件置对应位；投递时清除该位；源在源 cfx 被 ack（`timer_cmp` 重装 / `dma_status` W1C）后自动落位。
- **不计数**（事件幂等）且**软件不写**：两个位图均为 HW 写 / SW 只读，软件写忽略、不产生异常。

**（三）一帧多源（无嵌套）**

- 在同一指令边界上，所有 `async_src_pending` 中置位且被当前运行模式掩码**放行**的源，**一次性**进入**同一帧**：`async_src_frame` = 这些位的并集，`async_src_pending` 扣除这些位，`excp_async_num` **每次进入 +1**（与源个数无关）。
- **不串行、不嵌套**：不允许把同一 IP 的多个源拆成两帧串行投递。帧活动期（`async_src_frame != 0`）到达的新事件只置 `async_src_pending`，不再次进入；`escape` 释放帧后由硬件按下一指令边界补投。

**（四）精确点**

- 异步在**指令边界**识别；被中断指令**已提交**（`rb0` 已更新；`call` 已写 `ra63`、`ret` 已弹栈）。
- `async_cause_ip` = **提交后的 `rb0`**（跳转即目标）；`escape` 用它返回、**不重放**被中断指令。因此"跳转指令执行后、目标指令取指前到期"的异步，返回点是跳转目标。

**（五）进入步骤**

```
// 源侧（任一指令边界之外）：事件到达即置 pending 位，与当前模式无关
cfx_hart_async_src_pending <= cfx_hart_async_src_pending | (1 << src_cfxha)

// 指令边界（当前指令已提交）：
case inner_run_mode of
    U-mode: temp_mask <= cfx_umon_async_intr_mask
    J-mode: temp_mask <= cfx_jmon_async_intr_mask
    S-mode: temp_mask <= cfx_smon_async_intr_mask
    H-mode: temp_mask <= cfx_hmon_async_intr_mask

temp_allowed <= cfx_hart_async_src_pending & ~temp_mask
if cfx_hart_async_src_frame == 0 and temp_allowed != 0:
    cfx_hart_async_src_frame             <= temp_allowed      // 一帧多源：位图并集
    cfx_hart_async_src_pending          <= cfx_hart_async_src_pending & ~temp_allowed
    cfx_hart_async_prev_run_mode        <= inner_run_mode
    cfx_hart_async_prev_cfx_code        <= inner_cfx_code
    cfx_hart_async_cause_ip             <= rb0               // 已提交指令之后
    inner_run_mode                      <= cfx_hart_async_switch_run_mode   // 固定 supv
    inner_cfx_code                      <= 15
    inner_inst_pointer                  <= cfx_hart_async_excp_vector
    cfx_hart_excp_async_num             <= cfx_hart_excp_async_num + 1
// 否则：无放行源或帧活动期 ⇒ 不进入，pending 保留
```

**（六）handler 取值（异步无 `cause_info`）**

- 异步进入**不携带 `cause_info`**：`async_src_frame` 的位集合即"本帧有哪些源"；handler 按帧内位回**源 cfx**读寄存器或调用该 cfx 的系统功能——`TIMER` → `cfx_hart cg8 rc5`（`ISTATUS`）、`PMEM_DMA` → `cfx_pmem cg15 rc4`（`dma_status`，含 `ERR_CODE`）。
- `from_user` = `async_prev_run_mode == user`；`async_prev_run_mode`/`async_prev_cfx_code` 为 HW/RW，软件可在 `escape` 前重建现场。

**（七）退出（`escape` 返回并释放帧）**

- 返回用 `escape cfx_hart, [async_cause_ip, 8]`（`imms18 = 2`，帧选择位 `imms18[1] = 1`、偏移恒 0）；编码与合法性检查见 §5.1。
- 若 `cfxha != inner_cfx_code`、当前 cfx 非 `cfx_hart`，或 `async_src_frame = 0`，在切换任何状态前触发当前 cfx 的 `CFXESC`。
- 合法返回：恢复 `async_prev_run_mode`/`async_prev_cfx_code`，`inner_inst_pointer <= async_cause_ip`，`cfx_hart_escape_num` 递增，并由硬件**清 `async_src_frame`**（合法返回即释放帧）。**没有**"软件写 0 丢弃帧"的路径；需要换上下文就先改写 `prev_*`/`async_cause_ip` 再 `escape`。`escape` 不恢复任何来源掩码。
- **计数**：`cfx_hart` 的 `excp_async_num`（`cg4 rc4`）按进入次数计（一帧 +1），`escape_num`（`cg4 rc5`）按退出次数计。
- **pending 不迁移**：`async_src_pending` 记在 per-hart 的 `cfx_hart`（单一归处），跨模式切换不搬移；任务退出时其 pending 丢弃，依赖源重触发。
- 异步中断的抢占顺序与多 hart 接收规则列入后续修订；本节冻结"统一投递 `cfx_hart`""一帧多源""处理期间不嵌套""合法 `escape` 释放帧"四条。

---

## 附录：版本与变更记录

> **发布动作**：把顶部 `-rc` 段去 `-rc` 并补发布日期；`-rc` 段只在确有未发布改动时新开。

### 0.8.0-rc（未发布）

- 异步中断模型修订（内容改，版本仍 0.8.0-rc）：异步来源掩码由 `cfx_hart cg9` 改为**当前运行模式 monitor** 的 `cg8 rc1`（`cfx_<monitor>_async_intr_mask`：位 = 源 cfxha、`0=允许`/`1=屏蔽`、复位全 1），删除 `cg0`–`cg3` 的 `rc4` 与 `cfx_hart` 的五个来源掩码及保存掩码；`trap`/`escape` 不再保存/恢复掩码。源身份统一为**源 cfxha**（`TIMER`=15、`PMEM_DMA`=32），取消宏 cause 17/18，异步不占 `excp_cause_id`。`cfx_hart cg9` 精简为 7 槽（`prev_run_mode`/`prev_cfx_code`/`cause_ip`/`src_frame`/`src_pending`/`excp_vector`/`switch_run_mode`，`rc7`–`rc15` 保留），`src_frame`/`src_pending` 硬件写、软件只读；同一指令边界上的多个 pending 且放行的源一次性进入同一帧（位图并集），无嵌套；pending 跟随源事件（投递即清、源 ack 即落、不计数）；异步无 `cause_info`。第 5 章新增「异步中断进入与退出」专节，`§5.2`/`§5.3` 收窄为同步并指向该节。`escape` 编码不变。

- 异步中断投递由「先入当前运行模式 monitor」改为 **hart-first**：所有异步源（`TIMER`、`PMEM_DMA`）统一投递 `cfx_hart`（cfxha 15），入口为其 **supv 单向量**（`async_excp_vector` 与 `async_switch_run_mode` 固定 supv）；异步现场、五个来源掩码与 pending 集中在 `cfx_hart` 新增的 `cg9`（16 项，`§3.9`），**无嵌套**（帧活动期只置 pending）、**pending 不迁移**（per-hart 单归处），软件可**快照**整组 `cg9`、**写 0 释放帧**或**重建**现场后返回。`escape` 增加**帧选择位 `imms18[1]`**（0 = `cg5` 同步帧、1 = `cg9` 异步现场）：合法 `imms18 ∈ {0, 1, 2}`（`3` ⇒ `ILLI`）、`imms18[17:2]` 为 SBZ、`cg9` 只允许偏移 0，汇编层 `imms20 ∈ {0, 4, 8}`（`§5.1`/`§5.3` 同步）。`cg0`–`cg3` 的 `rc4`（`<mode>_cfx_intr_mask`）与 `cfx0`–`cfx3` 的 `cg8 rc1`（`global_cfx_intr_mask`）的**异步用途作废**（字段保留、不参与投递判定）。`§1`/`§3.1`–`§3.4`/`§3.9`/`§4.1`–`§4.4`/`§4.7`/`§4.9`/`§5.1`/`§5.2`/`§5.3` 同步。版本号保持 0.8.0-rc（不升号）。

- 异步中断 cause 号由 `[15:0]`（`TIMER = 1<<10`、`PMEM_DMA = 1<<8`）改为**宏 cause 空间 `[31:16]`**（`TIMER = 1<<17`、`PMEM_DMA = 1<<18`），解决与同步 cause（`RASOF = 1<<10`、`ILLI = 1<<8`）撞号；`[31:16]` 宏 cause 与 `[15:0]` 同步 one-hot 互斥、跨 cfx 全局编号。`§3.6`/`§4.7`/`§4.9`/`§5.2` 同步；`cause_info` 语义不变（TIMER=0、PMEM_DMA=`dma_status`）。不兼容语义变更，版本升 **0.8.0**；投递模型见上一列表项（hart-first）。

- `cfx_cache`（cfx5）的寄存器与命令语义重定义：`cache_exist`/`cache_enable` 的位定义补为 **bit0 = I、bit1 = D**；`cache_ctrl` 由旧的 bit0/bit1/bit2 数值编码改为 `[1:0]` 操作（`none`/`clean`/`invalidate`/`flush`）+ `[3:2]` 范围（`all`/`PA 单行`/`PA 区间`/reserved）+ `[15:14]` 选择（bit15 = I、bit14 = D）；新增 `cache_addr_start`（完整 56 位物理地址 `PA[55:0]`，`[63:56]` 保留）与 `cache_addr_size`（字节数），范围匹配按 56 位 PA 比较。维护命令同步完成、per-hart；两侧全选时先 I 后 D；I 侧 `clean` 为 no-op；`invalidate` 丢弃脏数据且不写警告、不报异常；`cache_enable` 对应位为 0 时该侧不被维护（编码与 `addr_size` 的校验不受使能影响）；不可缓存/MMIO 的 PA 无效果、不报异常。异常原因表不变。

- `DADAO-13` 的第 1、2 章正文并入本册：`cg3` 寄存器表与 `rc10` 初值/写入口径并入 `§3.4 cg3 - hypv mode 寄存器`，hmon 说明段并入 `§4.4 cfx_hmon - hypervisor monitor`；hmon 异常原因表不再重复，引 `§4.1`/`§3.6`。依据原话：「请把 DADAO-13 的第一章第二章移动至 DADAO-12，DADAO-13 只保留个引用就行。」

- 屏障指令 `fence cfxHA, immu18`：`cfx0`/`cfx_umon` 表示 all cfx，`cfx1`–`cfx63` 指定 cfx；资源域顺序只约束本 hart，不等待 DMA。
- cfx 编号调整：`cfx5` 为 `cache`（原 `cfx6` 迁入）；`cfx6`–`cfx14`、`cfx19`–`cfx61` 保留。
- `cfx_pmem` 增加 64 KiB SRAM（内部偏移 0x3ff_0000_0000，CPU 用 `ld/st` 访问）与 SRAM ↔ 物理存储器 DMA：`cg15` 寄存器 `dma_src`/`dma_dst`/`dma_size`/`dma_ctrl`/`dma_status`；方向 `CFX→PA`/`PA→CFX`，CFX 侧 42 位、PA 侧 56 位（高位忽略），`size` 30 位、合法 `1..2^29`；`START` 自清、`BUSY`/`DONE`/`ERROR`/`ERR_CODE`（W1C 与错误码）异步完成；`BUSY` 期间写寄存器与 W1C 被忽略。
- `cfx_pmem` 增加异步可屏蔽异常 `PMEM_DMA`（cause 号见本 rc 第 2 条列表项）：`IRQ_EN=1` 时 `DONE`/`ERROR` 触发，`cause_info` 携带 `dma_status`；被屏蔽或 `cfx_hart` 帧活动期时置 `cfx_hart cg9` 的 `async_pending`。当前单 hart 统一投递 `cfx_hart`。
- cfx 访问改为「运行模式 + cfx 资源」两轴模型：`cg0`–`cg3` 的 `rc0`–`rc3` 为 `cfxtrap`/`cfxmem`/`cfxreg`/`cfxexe` 四类 64 位同步来源 mask，`rc4` 原为 `cfx_intr_mask`（本 rc 后异步用途作废，字段保留）；位索引=源 cfx，0=允许、1=屏蔽，自身只绕过 cfx 轴。删除 `global_version` 与旧 `global_cfx_mask`；`cfx0`–`cfx3` 的 `cg8`/`rc1` 原为 `global_cfx_intr_mask`（异步用途同样作废，字段保留）。
- 四类同步 mask 初值：power 与普通 cfx `0xFFFF_FFFF_FFFF_FFF7`，hmon 自身 `0x7FFF_FFFF_FFFF_FFF7`；两类中断 mask 初值全 1。
- 新增同步异常 `CFXESC`（`1 << 3`，所有 cfx）与 `CFXPERM`（`1 << 7`，`cfx0`–`cfx3`）：权限拒绝进入当前模式 monitor，escape 帧/目标错误进入当前 cfx；reserved cfxha 仍为 ILLI。
- `escape` 的 `cfxha` 固定为当前 cfx，返回 cfx/mode/IP 取自异常帧，偏移为编译期固定立即数；`trap` 进入时自动保存并屏蔽 `global_cfx_intr_mask`，`escape` 恢复。
- `escape` 的 `cg5` 帧偏移合法集收窄为 **0 / +4**（`imms18[0]` 为字节偏移 bit2）；`imms18[17:2]` 为 SBZ，手工编码非零 ⇒ `ILLI`（先于任何状态切换）；`cg9` 帧的帧选择位与合法集见本 rc 首个列表项。`excp_cause_ip` 仍为 RW，本约束不构成任意返回安全边界。
- 异步中断按 `cfx_hart cg9` 的全局来源掩码（`rc8`）与运行期来源掩码（`rc9`–`rc12`）两级过滤，被屏蔽或帧活动期时置 `async_pending`。

- 版本号与 SBI 同步（SBI 删除 `immu18` 保留值 `0x3FFFF`）。
- 地址空间改为 48 位 CPU 地址 + 高 6 位分区：`0` 为内存窗口，`1..63` 为 cfx 1–63 核内空间；VA 42 位、PA 56 位，取消 64 位物理地址与高 16 位拼接。
- PTBR 由 64 项数组改为**单份** `cfx_ptw_ptbr`（只存 `PPN[55:16]`，64 KiB 对齐，无 valid 位）；删除 `pahi`/`pthi`/`ptbr_enable` 位图与四种模式的 PTBR 权限位图。
- 新增 `cfx_ptw_enable`：0 时 `addr[47:42] = 0` 访存触发 CFXMEM（不直通物理存储器），1 时按页表转换；写 PTBR / 写 1 均不隐含 TLB invalidate；复位 PTBR=0、使能=0。
- 保留 cfx（6–14、19–61）的普通 `ld/st` → CFXMEM；`trap`/`escape` 到保留 cfx 仍为 ILLI。
- 页表项统一为 64 位：`HSJU[63:60]`、`PPN[55:16]`（超页 `PPN[55:29]`）、`SPF/GPF[15:8]`、flags `[7:0]`（`P/SP/D/A/G/X/W/R`）；保留位忽略、超页 PPN 非对齐低位强制清零。
- 两级页表：L1/L2 均 64 KiB、8192 项；`VA[41:29]`/`VA[28:16]` 选索引、`VA[15:0]` 为页内偏移；超页 512 MiB、普通页 64 KiB，PA 56 位。
- 页访问权限：HSJU 掩码 + R/W/X 正交检查；异常优先级为「页缺失 → 小页缺失 → HSJU → R/W/X」；页表步进与 TLB 命中异常都进入 `cfx_ptw`。
- PTE `bit4` 由保留改为 **Global（`G`）**：叶子 `G=1` 为全局页、TLB 中跨 ASID 复用；非叶子 `G` 忽略。
- TLB 并入 `cfx_ptw`：删除独立 `cfx_tlb`（`cfxha 5` 未分配）与 `tlb_exist`/`tlb_enable`；16 位 ASID（`cfx_ptw_tlb_asid`）；`cfx_ptw_tlb_control`（`op/地址范围/ASID_ANY` 正交）+ start/size 失效接口；写 PTBR/ASID/使能均不隐含失效。
- A/D 由硬件在 TLB 条目中维护：填充不产生回写，读/取指置 `A`、写置 `A`/`D`，`CLEAN`/`FLUSH`/替换时原子 OR 回写，`INVALID` 不写回；回写失败报 `cfx_ptw` 的 `PTWERR`（`1 << 7`，`cause_info` = PTE 物理地址）。
- DMA 与 cfx 访问权限不在本版本变更范围内。
- 正文术语统一：地址空间分区一律写作 `addr[47:42]`（地址高 6 位），不再使用讨论期简写。
- 核内地址空间同步启动分层：新增 `cfx2`（`smon`）64 KiB SRAM（`0x0bff_0000_0000`）与 `cfx3`（`hmon`）64 KiB SRAM（`0x0fff_0000_0000`）；唯一非易失 BootROM 自 `2^48` 向下、大小 ≥64 KiB（由平台规范规定），复位向量仍为 `0xffff_ffff_0000`（BootROM 末 64 KiB 起点）；`cfx63`（`power`）是否设 SRAM 由平台规范规定。
- `cg7` 改为内部空间描述寄存器：每 4 个 rc 描述一个内部空间（存在 + 类型 one-hot / 42 位起始偏移 / 字节大小 / R-W-X-cacheable-shareable-volatile 属性），16 块用完 `rc0`–`rc63`；寄存器按数组 `space_{desc,start,size,attr}[i]` 命名（`i=0..15`，`rc=4i+0..3`），全部只读、写触发 `CFXREG`；不再使用块选择与块内地址寄存器。
- 删除核内存储块批量传输指令的行为说明与异常进入分支/伪代码：该类指令已从指令系统删除，不再定义其异常流。
- 保留 cfx 统一为 `6–14`、`19–61`。
- `cfx_hart` 计数寄存器由 128 位 `cycle_lo`/`cycle_hi`/`insn_lo`/`insn_hi`（`cg8 rc2`–`rc5`）收为 64 位单寄存器 `cycle`/`insn`（`rc2`/`rc3`）；定时器比较/控制前移至 `rc4`/`rc5`，`rc6`/`rc7` 保留。`cfx_time` 的 `time_freq`/`time_value` 前移至 `cg10 rc0`/`rc1`，`rc2`–`rc63` 保留。
- BootROM 口径收口：`cfx_power` BootROM 只规定 **≥64 KiB**，实际大小与 `power` 是否设 SRAM 由平台规范规定；复位向量固定 `0xffff_ffff_0000`（BootROM 末 64 KiB 起点，镜像内偏移 = 大小 − 64 KiB）。
- cfxha 重编号与作用域统一（2026-11-05）：`cfx_pmem`/`cfx_llc`/`cfx_time` 改为 **32/33/34**；保留集改为 **`6–14`、`16–31`、`35–61`**；作用域新增 **`cfx16`–`cfx31` per-task**（申请后使用、用完释放，不随上下文切换保存/恢复），`cfx32`–`cfx63` per-system、`cfx0`–`cfx15` per-hart 不变；`cfx_pmem` SRAM 核内基址随之变为 **`0x83ff_0000_0000`**（内部偏移仍 `0x3ff_0000_0000`）。
- 异常进入流程重写：同步异常统一按「当前运行模式 monitor」路由（`CFXPERM`/`CFXREG`/`CFXMEM`/`ILLI` 等）；`CFXTRAP` 仍进入目标 cfx，`CFXESC` 仍进入当前 cfx；删除同步异常的独立 cfx 屏蔽层；同步异常全部不可屏蔽，不再使用异常原因掩码与不可屏蔽掩码；未映射页归当前 monitor 的 `CFXMEM`，页权限拒绝归 `CFXPERM`；monitor 原因编号沿用 DADAO 位索引，不再使用 `PTWERR` 作为 monitor 原因；异步中断统一进入 `cfx_hart`（现场/来源掩码/pending 在 `cg9`，帧活动期不嵌套，见本 rc 首个列表项）；具体调度细节列入后续修订。
- 删除无效屏蔽寄存器定义：`switch_cfx_mask`（`cg0`–`cg3` `rc9`）、`excp_cause_mask`（`cg0`–`cg3` `rc11`）、`excp_prev_cfx_mask`（`cg5` `rc1`）、`excp_cause_nonmaskable`（`cg5` `rc63`）保留编号并标为 `reserved`（访问 ⇒ `CFXREG`）；删除内部 `inner_cfx_mask`；`escape` 不再恢复 cfx 屏蔽状态，`global_cfx_intr_mask` 的 trap 保存/escape 恢复保留（不影响异步投递）；monitor 的 `cfx_intr_mask`/`excp_pending` 保留编号（异步投递不再使用）。
- 页表异常原因表同步：页表未映射（L1/L2 `P = 0`、SPF/GPF 对应小页位为 0、fragment 缺失）与 A/D 回写失败归当前运行模式 monitor 的 `CFXMEM`（A/D 的 `cause_info` = PTE 物理地址），HSJU 与 R/W/X 不符归 `CFXPERM`；删除 `cfx_ptw` 的 `PTWERR`/`NUPERM`–`NRPERM`/`IGPTRAP`–`DSPFTRAP` 原因，`§4.5` 只保留 `CFXTRAP`/`CFXESC`，`§3.6` 的 `1 << 7` 在 `cfx_ptw` 标保留；`§2.2` 对应步骤只改原因名与目标，优先级顺序不变。
- 异常原因编号改为**分层编码**：`excp_cause_id[15:0]` 为 cause one-hot（11 项，编码与位索引一字不变），`[31:16]` 保留给未来新的大类 cause（当前必须全 0），子原因按 **wyde** 分段——wyde2 `[47:32]` 专供 `CFXPERM`（低字节 `[39:32]` 8 位权限原因、`[47:40]` 保留）、wyde3 `[63:48]` 专供 `CFXMEM`（低字节 `[55:48]` 8 位缺失类、`[56] ADWBFAIL`、`[57] NONPTW`、`[63:58]` 保留）。`CFXPERM` 时 wyde3 必须全 0、`CFXMEM` 时 wyde2 必须全 0、其它 cause 两个 wyde 都必须全 0（归属不符按未列出位被错误触发处理）；handler 分别用 `(cause_id >> 32) & 0xFFFF` / `(cause_id >> 48) & 0xFFFF` 取子原因。`CFXMEM`/`CFXPERM` 的 `cause_info` 恒为地址（`cfxtrap`/`cfx2rd`/`cfx2rc` 拒绝时 = 触发指令地址，与 `excp_cause_ip` 同值）。`§3.6` 增两个 wyde 的表，`§2.2.6` 七步优先级逐步对应子原因位，`§4.1`–`§4.6` 的 `CFXMEM`/`CFXPERM` 行注明 `cause_info` 与子原因指针；退出码编码不受影响（仍取低位 cause 索引）。
- `§2.1` 校验示例笔误修正：`size = 64 KiB` ⇒ `start = 0x3ff_ffff_0000`、`size = 4 MiB` ⇒ `start = 0x3ff_ffc0_0000`（原文各少一组 `FF`）；`start = 2^42 − size` 规则不变。
- 多元素**内存**指令的精确性例外：`ldm.*`/`stm.*`（含 rf 形式，SimRISC-01）不再要求无副作用——处理多个元素的过程中触发同步异常时，此前已处理的元素**允许已经生效**，目的寄存器/内存可能已被部分更新；异常原因码仍须与触发元素一致、`excp_cause_ip` 仍指向该指令。寄存器类多元素指令（`rd2rd`/`rb2rb`/`rb2rd`/`rd2rb`/`ra2rd`/`rd2ra`、`rd2rf`/`rf2rd`/`rf2rf`、`ftcls`/`focls`）**不适用**该例外、仍为精确异常；整段预检是**允许的更强行为**、软件不得依赖；单元素 `ld`/`st` 仍须精确。
- `ldm` 的地址寄存器不得落入传送范围：传送范围在 RD 组时索引寄存器为 `rdHC`、在 RB 组时基址寄存器为 `rbHB`（`起始 <= 地址寄存器 < 起始 + immu6`）⇒ `ILLI`；`stm` 允许该重叠（只读传送范围、不写寄存器）；RA/RF 形式结构性不可能重叠。原「允许重叠、地址按原始 `rdHC` 计算」口径作废，本例外改以「地址寄存器不被传送过程改写」为前提。
- `cg5 rc1` 由 `reserved` 改为 `excp prev cfx code`（`cfx_⟨cfxname⟩_excp_prev_cfx_code`，RW，初值 0）：`§5.2` 第 5 步硬件陷入时保存异常前的 `inner_cfx_code`，`§5.3` 第 2 步 `escape` 恢复，使 `inner_cfx_code` 与 `inner_run_mode` 同进退。动机：同步异常帧内到达异步事件（如 `TIMER`）时，`§5.2` 第 6 步会把 `inner_cfx_code` 改写为目标 cfx，该帧随后的 `escape` 命中 `§5.3` 第 0 步的目标错误检查（`cfxha != inner_cfx_code` ⇒ `CFXESC`），无法返回被中断的上下文；影响：`escape` 后 `inner_cfx_code` 回到进入前值（嵌套各层逐层回退），`§3.6` 表与 `§5.2`/`§5.3` 伪代码同步。

### 0.7.2（2026-10-26）

- `cfx_time`：per-system 全局时间计数器（`cfx_time_freq`、`cfx_time_value`），只提供时间读数、不产生中断。
- `cfx_hart` 增加每 hart 定时器：`timer_cmp`（比较值）与 `timer_ctrl`（ENABLE/IMASK/ISTATUS），到期触发异步 TIMER 异常（`1 << 10`）；`rc1` 声明为保留。
- 同步异常一律不可屏蔽（含 `SOFT_RESET`）；异常原因掩码只对异步中断生效，异常进入流程第 5 步仅在异步路径设置 pending。
- U-mode `trap` 目标为 `cfx_smon` 时使用 `cfx_smon_user_*`；其余 U-mode 异常固定进入 `cfx_umon`。
- `cg7` 按预留设计：核内存储块批量传输指令尚未启用，未实现的机器对这两条指令 decode ILLI。
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
