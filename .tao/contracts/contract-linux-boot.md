# 启动 ABI 合约（Vast 内核装载 + 固定 boot info）

> **契约版本**：`0.2.0`（本契约自有版本线，不随 spec 册版本走；`0.2.0` = 内核 VA 窗口改 `[2 TiB, 3 TiB)`、`VA = PA + 2 TiB`）
>
> **来源**：规范正文 `spec/Machine-v5-测试机运行环境.md` `§6.3`（v5 自定册，0.4.7-rc）；装载模型继承 `.tao/adr/adr-0004-test-machine.md`（ADR-0004，Accepted，`§D2.2`/`§D2.3`：ELF + raw-bin 双路径）；冻结值经用户 **2026-11-13** 裁定「按提案冻结」、地址术语与启动模型经用户 **2026-11-13** 裁定「VA 为 ABI 地址」「M1 预建页表 + VA 入口」（渠道 = 经主会话问答，授权原话落纸于本任务书 §用户裁定）；内核窗口 `[2 TiB, 3 TiB)` 与 `VA = PA + 2 TiB` 偏置经用户 **2026-11-13** 更正裁定（渠道 = 经主会话问答；取代先前的低地址冻结值）。
>
> **引用（只指针，不复制正文）**：ELF 头字段与段对齐 `.tao/contracts/contract-elf.md`（§1.1、§1.3、§5.2）；端序与指针宽度 `.tao/contracts/contract-abi.md`（§1.7）；停机协议 `.tao/contracts/contract-semihosting.md`（§5）。
>
> **来源标注**：每条规范性断言句末标 `[Machine-01 §6.3]`（`Machine-01` = 仓库门控对 `spec/Machine-v5` 册的既有前缀）、`[contract-elf §N]`、`[DADAO-23 §3 启动与引导移交约定]`、`[用户裁定 2026-11-13]`；无上游依据的冻结值标 `[spec-decision]`，并在 `§7` 逐条列出。
>
> **范围**：`Machine-v5-Vast`（`dadao-vast`）上 K0 内核的启动 ABI——地址术语与启动模型（§1）、内存分区（§2）、装载路径与校验（§3）、固定 boot info 结构（§4）、进入时状态（§5）、边界（§6）。**不含**装载的执行实现（宿主写内存与 boot info、装 initramfs、把 `rb16`/`rb17` 交给 smon）。
>
> **说明**：本合约是 `spec/Machine-v5 §6.3` 的归一化投影，面向实现；与 `§6.3` 冲突时阻断实现，走变更流程（见 `docs/Process-02-合约编写规范.md`）。机器可读投影为 `contracts/linux-boot.yaml`，一致性由 `tools/linux/check_boot_contract.py` 机械校验。

---

## §1 角色、地址术语与启动模型

- 本合约**只适用于 `Machine-v5-Vast`**；`Machine-v5-Tiny` 的装载规则由 `Machine-v5 §6.2` 规定，不在本合约范围内。[Machine-01 §6.3][Machine-01 §6.2]
- 进入内核前的链路为 `power → hmon → smon`，进入后运行模式为 `supv`；本合约不改变该链路与「首张页表由 `smon` 建立」的归属（映射几何见 §1）。[Machine-01 §6.3][DADAO-23 §3 启动与引导移交约定]
- **地址术语**：ABI 中的地址**一律是 VA**——48 位核内地址里分区键 `addr[47:42] = 0` 的内存窗口，即 `addr[41:0]`（42 位有效）。**PA 只出现在三处**：页表项、`PTBR`（= `PPN << 16`）、宿主 loader 把数据写进内存的那一刻。[Machine-01 §6.3][用户裁定 2026-11-13]
- 因此入口地址、`rb16`/`rb17`、boot info 的地址字段、`kernel_base`、内核镜像区、initramfs 区与栈指针都按 **VA** 记；实现不得把这些值当 PA 使用。[Machine-01 §6.3][用户裁定 2026-11-13]
- **内核窗口偏置**：内核 VA 窗口内 `VA = PA + 2 TiB`（固定偏置）——内核空间不从 0 开始，用户空间独占低端 `[0, 2 TiB)`；`PTBR` 与页表项仍按 PA 记。[Machine-01 §6.3][用户裁定 2026-11-13]
- **启动模型 = M1（预建页表 + VA 入口）**：进入内核**之前**页表已预建——smon 建立首张页表并开启 PTW（`PTBR` 指向该表、`ptw_enable = 1`），映射 `VA [0x0200_0000_0000, 0x0200_2000_0000) → PA [0, 0x2000_0000)`（覆盖内核窗口基址起的前 512 MiB，含本合约的全部固定分区）；随后以 `rb16` 的 VA 入口进入内核。页表几何与表项属性见 `ADR-0043`（`D10`/`D11`）；**表项索引由 PTW 按 VA 求出**，本合约不写死索引值。[Machine-01 §6.3][用户裁定 2026-11-13]
- 页表**只由启动固件 `smon` 建立**（`Machine-v5 §6` 的首张页表：`smon` 交接时建立并开启 PTW）；宿主 loader **只把镜像装到对应 PA，不代写页表页**。M1 **不存在**「先关 MMU 再开」的中间态。[Machine-01 §6][用户裁定 2026-11-13]
- **硬约束**：DADAO 在 `ptw_enable = 0` 时对内存窗口的取指/访存**直接报 `CFXMEM`** ⇒ 内核不可能在 MMU 关状态下从 RAM 取指/访存，故进入时 `ptw_enable` 必须为 `1`。[Machine-01 §1.2][Machine-01 §6.3]

## §2 内存分区

Vast 的内存窗口为 `VA [0, 4 TiB)`（`addr[47:42] = 0`、`VA = addr[41:0]`），按用途划分为：用户 VA 空间 `[0, 2 TiB)`、内核 VA 窗口 `[2 TiB, 3 TiB)` = `[0x0200_0000_0000, 0x0300_0000_0000)`；`[3 TiB, 4 TiB)` 本合约不定义。内核窗口内 `VA = PA + 2 TiB`。内核装载与运行期占用窗口内下述固定 VA 分区；其余归内核页分配器。[Machine-01 §6.3][spec-decision]

| 区间（VA） | 大小 | 用途 |
|------|------|------|
| `[0x0200_0000_0000, 0x0200_0001_0000)` | 64 KiB | 首张页表页（`PTBR = 0`（PA）；由固件在移交前建立，见 `§6`） |
| `[0x0200_0001_0000, 0x0200_0002_0000)` | 64 KiB | boot info 页（固定 VA `0x0200_0001_0000`；其余字节为 0） |
| `[0x0200_0010_0000, 0x0200_0400_0000)` | 63 MiB | 内核镜像区（`kernel_base = 0x0200_0010_0000`，VA） |
| `[0x0200_0400_0000, 0x0200_0600_0000)` | 32 MiB | initramfs 区（上限 32 MiB，VA） |
| 其余 | — | 内核 VA 窗口内其余区间归内核页分配器 |

- 首张页表页与 boot info 页合占窗口内的**启动保留区** `[0x0200_0000_0000, 0x0200_0002_0000)`（PA 侧为 `[0, 0x0002_0000)`）；建立页表时**不得**覆盖 boot info 页。[Machine-01 §6.3][spec-decision]
- 启动保留区 `[0x0200_0000_0000, 0x0200_0002_0000)` 与 initramfs 区在内核接管后**须保留**，不得被页分配器回收或复用。[Machine-01 §6.3][spec-decision]

## §3 内核装载

### §3.1 两条装载路径

内核镜像有 **ELF** 与 **raw（loadmem）** 两条路径，**语义等价**：同一份内核源码经两条路径装载后，进入状态（§5）相同。[Machine-01 §6.3][spec-decision]

**地址与装载（两条路径共用）**：ELF 的 `p_vaddr` 与 raw 镜像基址都是 **VA**；loader 把每段写到该 VA 在首张页表里映射到的 **PA**（不读 `p_paddr`）。内核窗口内 `VA = PA + 2 TiB`（⇒ 目标 PA = `p_vaddr - 2 TiB`），两者是不同术语，实现不得混用。[Machine-01 §6.3][用户裁定 2026-11-13]

| 规则 | 规定 | 来源 |
|------|------|------|
| `ELF-FORMAT` | `ELFCLASS64`、大端（`EI_DATA = 2`）、`e_machine = 0x0DA0`、`ET_EXEC`；`e_flags` 版本字段 = 1（`contract-elf` §1.3） | `[contract-elf §1.1]` `[spec-decision]` |
| `ELF-PT-LOAD` | 只装载 `PT_LOAD` 段，其它类型的程序头段不装入 | `[Machine-01 §6.3]` `[spec-decision]` |
| `ELF-VA-TO-PA` | 每段按 `p_vaddr` 的映射写入对应 PA（`VA = PA + 2 TiB` ⇒ 目标 PA = `p_vaddr - 2 TiB`）；`p_paddr` 不作为装载地址 | `[Machine-01 §6.3]` `[contract-elf §5.2]` |
| `ELF-ALIGN` | 每段 `p_vaddr % 0x10000 == 0` 且 `p_align >= 0x10000`（64 KiB 页对齐） | `[contract-elf §5.3]` `[DADAO-12 §2.2 虚实地址转换]` |
| `ELF-RANGE` | 每段 `[p_vaddr, p_vaddr + p_memsz)` 落在内核镜像区的 VA 范围 `[0x0200_0010_0000, 0x0200_0400_0000)` 内 | `[Machine-01 §6.3]` `[spec-decision]` |
| `ELF-NO-OVERLAP` | 任何段不得与启动保留区 VA `[0x0200_0000_0000, 0x0200_0002_0000)`、BootROM 或 hmon SRAM 的映射区间重叠 | `[Machine-01 §6.3]` `[Machine-01 §1.1]` |
| `ELF-ENTRY` | `e_entry == 0x0200_0010_0000`（VA，= `kernel_base`） | `[Machine-01 §6.3]` `[spec-decision]` |
| `RAW-BASE` | 整体装入 VA `0x0200_0010_0000`（= `kernel_base`） | `[Machine-01 §6.3]` `[spec-decision]` |
| `RAW-ENTRY` | 镜像首字节即入口指令（VA 入口 `0x0200_0010_0000`），loader 不解析 ELF 头 | `[Machine-01 §6.3]` `[spec-decision]` |
| `RAW-LENGTH` | 镜像长度 ≤ 63 MiB | `[Machine-01 §6.3]` `[spec-decision]` |
| `RAW-BSS` | 扁平镜像不含 `.bss`；内核 `head.S` 在进入 C 代码前自清 `__bss_start..__bss_stop`，与 ELF 路径零填充等价 | `[Machine-01 §6.3]` `[spec-decision]` |

- ELF 路径下 `p_filesz` 字节取自文件，`p_memsz - p_filesz` 由 loader **零填充**（`.bss`）。[Machine-01 §6.3][contract-elf §6.1.2]

### §3.2 initramfs

| 规则 | 规定 | 来源 |
|------|------|------|
| `INITRAMFS-FORMAT` | `cpio`「newc」格式 | `[Machine-01 §6.3]` `[spec-decision]` |
| `INITRAMFS-BASE` | 装入 VA `0x0200_0400_0000`（= `initramfs_base`） | `[Machine-01 §6.3]` `[spec-decision]` |
| `INITRAMFS-LIMIT` | 长度 ≤ 32 MiB；实际字节数写入 `initramfs_size`（`0` ⇒ 无 initramfs） | `[Machine-01 §6.3]` `[spec-decision]` |

### §3.3 失败语义

| 规则 | 规定 | 来源 |
|------|------|------|
| `FAIL-HOST` | 任一校验失败 ⇒ loader 非零退出；不得静默降级、截断或改址装载 | `[Machine-01 §6.3]` `[spec-decision]` |
| `FAIL-KERNEL` | `magic`/`version`/`size` 任一不符 ⇒ 内核 `head.S` 显式失败（semihosting `SYS_EXIT` + 固定失败码） | `[contract-semihosting §5]` `[spec-decision]` |

- 固定失败码的码值属 K1 实现，本合约不规定；**不得**猜测或带病继续启动。[Machine-01 §6.3][spec-decision]

## §4 固定 boot info 结构

boot info 位于内核 VA 窗口的 **VA** `0x0200_0001_0000`（PA 侧 = VA − 2 TiB），总长 `size = 0x60` 字节；全部多字节字段**大端**，8 字节字段自然对齐；页内偏移 `0x60` 之后至该页末（页内偏移 `0x1_0000`）为 0。表中地址字段均为 **VA**，唯一例外是 `ptbr`——它是首张页表根的 **PA**（`PPN << 16`，K0 为 `0`）。[Machine-01 §6.3][spec-decision]

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

- **写入方与保护**：boot info 由**宿主 loader** 在移交前写入；`power`/`hmon`/`smon` **只读**、不得改写，建立页表时不得覆盖 boot info 页。[Machine-01 §6.3][spec-decision]
- `kernel_size` 只覆盖装载镜像；内核自身用链接符号 `_end` 保留含 `.bss` 的完整占用。[Machine-01 §6.3][spec-decision]

## §5 进入时状态

进入状态指**内核第一条指令处**（`IP` = 入口 VA `0x0200_0010_0000`）的寄存器与模式状态。[Machine-01 §6.3][spec-decision]

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

- `rb17` 与 `DADAO-23` 的「设备树地址」**同位**，但本机**不引入 DTB**：`rb17` 承载 boot info 的 VA，内核**不得按 DTB 解析**。[Machine-01 §6.3][DADAO-23 §3 启动与引导移交约定]
- `rb1`（SP）未定义 ⇒ 内核 `head.S` 须在任何栈使用前自建 early stack（栈指针按 VA）；`rd15` 与其它通用寄存器不得依赖。[Machine-01 §6.3][spec-decision]
- **其它 hart**：K0 只有 `hart_id = 0` 在线，其余 hart 的状态**未定义**（实现可保持停止或不复位）；内核不得等待、唤醒或依赖它们，SMP 启动与停核协议不在本合约。[Machine-01 §6.3][spec-decision]

## §6 边界与不定义范围

- 本合约**不定义**：TLB 填充/失效/ASID、cache/LLC、设备树（DTB）、UART、多核启动与 SMP 停核协议、MMU 关运行（`ptw_enable = 0` 时内核无法从 RAM 取指/访存）、用户 VA 空间 `[0, 2 TiB)` 的布局与用户态映射、`[3 TiB, 4 TiB)` 的用途、内核窗口内固定分区之外（`+512 MiB` 以上）的映射扩展；这些属后续里程碑，不引入。[Machine-01 §6.3][spec-decision]
- 与 `contract-elf` 的关系：ELF 头字段、段对齐、`PT_LOAD` 装载与 `.bss` 零填充**只引用** `contract-elf`（§1、§5、§6），本合约不复制其正文。[contract-elf §1.1][contract-elf §5.2][contract-elf §6.1.2]
- 与 `contract-abi` 的关系：端序与指针宽度只引用 `contract-abi`（§1.7），不重复定义。[contract-abi §1.7]
- 与 `contract-semihosting` 的关系：`SYS_EXIT` 语义只引用 `contract-semihosting`（§5），本合约只规定「必须显式失败」这一义务。[contract-semihosting §5]

## §7 冻结值清单（`[spec-decision]`）

以下取值在 `spec/Machine-v5 §6.3` 中**无上游 spec 依据**，属 v5 架构自定义，已由用户 2026-11-13 确认「按提案冻结」；地址术语与启动模型经用户同日裁定；改动须走 spec 变更流程并同笔更新本合约与 `contracts/linux-boot.yaml`。[Machine-01 §6.3][用户裁定 2026-11-13]

- ABI 地址一律 **VA**（`addr[41:0]`）；PA 仅用于页表项、`PTBR` 与 loader 写内存。[spec-decision]（用户 2026-11-13 裁定）
- 内核 VA 窗口 `[2 TiB, 3 TiB)`（用户空间 `[0, 2 TiB)`）；窗口内固定偏置 `VA = PA + 2 TiB`。[spec-decision]（用户 2026-11-13 裁定）
- 启动模型 M1 = **预建页表**（64 KiB 页、`VA [0x0200_0000_0000, 0x0200_2000_0000) → PA [0, 0x2000_0000)`、`PTBR = 0`、`ptw_enable = 1`）+ **VA 入口**（`rb16`）。[spec-decision]（用户 2026-11-13 裁定）
- 内核基址与入口 VA `0x0200_0010_0000`；内核镜像区上限 VA `0x0200_0400_0000`（63 MiB）。[spec-decision]
- boot info VA `0x0200_0001_0000`、`size = 0x60`、`magic = 0x4442_494E`（`DBIN`）、`version = 1`。[spec-decision]
- initramfs 区基准 VA `0x0200_0400_0000`，上限 32 MiB（末端 `0x0200_0600_0000`）。[spec-decision]
- 进入模式 `supv`；`rb17` 承载 boot info VA、`rb16` 承载入口 VA、SP 与其它通用寄存器未定义、其它 hart 状态未定义。[spec-decision]
- `flags` `bit0` = semihosting 控制台可用；`page_size_log2 = 16`；`hart_id = 0`；`cmdline_base`/`cmdline_size` 为保留字段（`0`）。[spec-decision]
