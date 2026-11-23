# SEE/HEE 运行环境合约（M5）

> **版本：0.8.0-rc** [DADAO-12 §1. 运行模式与核芯功能扩展][DADAO-22 §1. 调用约定]
>
> **来源**：`spec/DADAO-12-SEE-主管系统运行环境.md`（0.8.0-rc）、`spec/DADAO-13-HEE-超管系统运行环境.md`（0.1.4-rc）、`spec/DADAO-22-SBI-主管系统二进制接口.md`（0.8.0-rc）、`spec/DADAO-23-HBI-超管系统二进制接口.md`（0.1.4-rc）、`spec/DADAO-21-ABI-应用程序二进制接口.md`（0.9.2）、`spec/SimRISC-11-其它.md`（0.5.4）；测试机运行环境正文 `spec/Kaiwu-测试机运行环境.md`（v5 自定）；决策 `.tao/adr/adr-0020-see-semihosting.md`（`ADR-0020`，Accepted）与 `.tao/adr/adr-0004-test-machine.md`（`ADR-0004`，Accepted，rev. 2026-10-07 `R1`/`R3`）。
>
> **范围**：M5 SEE/HEE 运行环境——运行模式、核内地址空间与复位、cfx 与权限、`trap`/`escape` 与异常进入/退出、SBI 调用约定；**M14 K2 起**增内核侧异常/中断口径（§6）。semihosting 的服务表/调用约定见 `contract-semihosting.md`。
>
> **v5 扩展（M14）**：§6（`excp_cause_info` 覆盖范围、`escape` 返回 cfx、异步中断的内核入口、内核侧 IE 单旋钮、时间口径缺口）**不在 SEE/HEE 正文内**，按 `DADAO-12`/`DADAO-13`/`Kaiwu` 与 `ADR-0045` 归一化；**版本号不随之变动**（`check-spec-drift` 不变量：spec-sourced 合约版本 == 上游册版本），变更记录见 §7。
>
> **来源标注**：每条规范性断言句末以 `[DADAO-NN §章节名]`/`[SimRISC-XX §章节名]` 标注 spec/ 来源；测试机约定标 `[ADR-0020 DN]`/`[ADR-0004 DN]`/`[Machine-01 §N]`；不写行号。
>
> **说明**：本合约由 spec/ 归一化投影而来，面向实现；与 spec/ 冲突时阻断实现，走变更流程（见 `docs/Process-02-合约编写规范.md`）。

---

## §1 运行模式

- DADAO 定义四种运行模式（两位编码）：`user`（`0b00`）、`jail`（`0b01`）、`supv`（`0b10`）、`hypv`（`0b11`）。[DADAO-12 §1. 运行模式与核芯功能扩展]
- `hypv`（超管模式）的 cg3 寄存器定义见 SEE §3.4（含 `hypv_switch_run_mode`/`hypv_excp_vector`）。[DADAO-12 §3.4 cg3 - hypv mode 寄存器]
- `trap/escape/cfx2rd/cfx2rc` 可在**任意运行模式**下执行；是否允许由 `cfxtrap`/`cfxreg` 等来源 mask 控制。[SimRISC-11 §指令域与执行条件]
- 异常进入时运行模式切换为 `cfx_⟨cfxname⟩_<mode>_switch_run_mode`（异常进入流程步骤 6）。[DADAO-12 §5. 异常进入与异常退出][DADAO-12 §3. 共有寄存器设计规范]
- v5 测试机按 profile 分述：`Kaiwu-Tiny` 固定特权态（名义 `hypv`/cfxha 63）、不能进入 `user`/`jail`/`supv`；**有 `cfx_power`（启动）+ `cfx3 hmon`（同步异常进 hmon 向量）**，无 smon；`Kaiwu-Vast` 启用 `hypv`/`supv`/`user`，启动链为 power(cfx63/hypv) → hmon(cfx3/hypv) → 测试本体(hypv)，`power → hmon → smon`(cfx2/supv) 路径保留、M11 不覆盖；`jail` 两 profile 均不启用。[ADR-0043 D1/D4/D5/D8/D9][Machine-01 §2]

## §2 核内地址空间与复位

- CPU 地址固定 48 位；高 6 位 `addr[47:42]` 为分区键：`0` 为内存窗口（`ptw_enable` 控制是否翻译），`1..63` 为 cfx 1–63 核内空间；`cfx0` 无内部空间。[DADAO-12 §2.1 核内地址空间][DADAO-12 §2.2 虚实地址转换]
- 内存窗口 VA 为 42 位（`VA[41:0]`），物理地址 PA 为 56 位。[DADAO-12 §2.2 虚实地址转换]
- 单 PTBR `cfx_ptw_ptbr`（只存 `PPN[55:16]`，64 KiB 对齐，无 valid 位）；`cfx_ptw_enable=0` 时 `addr[47:42] = 0` 访存 ⇒ `CFXMEM`，`1` 时按页表转换；写 PTBR/写 1 不隐含 TLB invalidate；复位 PTBR=0、使能=0。[DADAO-12 §2.2 虚实地址转换][DADAO-12 §4.5 cfx_ptw - page table walker]
- 页表项 64 位：`HSJU[63:60]`、`PPN[55:16]`（超页 `PPN[55:29]`）、`SPF/GPF[15:8]`、flags `[7:0]`（`P/SP/D/A/G/X/W/R`）；L1/L2 均 64 KiB、8192 项，`VA[41:29]`/`VA[28:16]` 选索引、`VA[15:0]` 为页内偏移；PA 56 位。保留位忽略、超页 PPN 非对齐低位强制清零。[DADAO-12 §2.2.1 超页的地址转换][DADAO-12 §2.2.2 普通页的地址转换][DADAO-12 §2.2.3 一级页表条目格式][DADAO-12 §2.2.4 二级页表条目格式]
- 页权限：HSJU 要求当前模式对应位为 1，且 R/W/X 与 HSJU 正交（取指 X、读 R、写 W）；异常优先级「页缺失 → SPF/GPF 对应位 = 0 → HSJU → R/W/X」，只报最高优先级异常；页表未映射与 A/D 回写失败 ⇒ `CFXMEM`（当前运行模式 monitor），HSJU 或 R/W/X 不符 ⇒ `CFXPERM`（当前运行模式 monitor），`cfx_ptw` 不再是页表异常目标。[DADAO-12 §2.2.5 操作系统页管理][DADAO-12 §2.2.6 异常检查优先级]
- **TLB（并入 `cfx_ptw`）**：无 `tlb_enable`/`tlb_exist`，`ptw_enable=1` 即参与查找、`0` 时旁路；按「虚拟页 + ASID（`cfx_ptw_tlb_asid`，16 位）」匹配，`G=1` 跨 ASID 复用；命中不重读 PTE，miss 走页表步进且只有成功才填充；写 PTBR/ASID/使能都不隐含失效。[DADAO-12 §2.2.1 超页的地址转换][DADAO-12 §4.5 cfx_ptw - page table walker][ADR-0041 D3/D5/D8/D9]
- **TLB 失效**：`cfx_ptw_tlb_control` 三维正交——`op`（`00=none`/`01=clean`/`10=invalid`/`11=flush`）、`scope`（`00=all`/`01=VA`/`10=range`/`11=reserved`）、`ASID_ANY`（bit4）；`all` 忽略 start/size、`VA` 只看 start、`range` 用 `[start,start+size)`；`scope=11` 或 `range` 且 `size=0` ⇒ `CFXREG`（仅 `clean`/`invalid`/`flush`；`op=none` 优先按 no-op）；`ASID_ANY=1` 含 `G`、`0` 跳过 `G`；正常完成不报异常。[DADAO-12 §4.5 cfx_ptw - page table walker][ADR-0041 D3.1/D3.2/D6]
- **A/D**：填充取 PTE 的 A/D 为本地值、不产生回写；读/取指置 A，写置 A/D；缺页/权限失败不更新；`clean`/`flush`/替换时原子 OR 回写 PTE（`clean` 保留、`flush` 删除、`invalid` 不写回）；回写失败按当前运行模式 monitor 的 `CFXMEM` 处理（`cause_info` = PTE 物理地址）且保留条目。[DADAO-12 §2.2.5 操作系统页管理][DADAO-12 §4.5 cfx_ptw - page table walker][ADR-0041 D4/D7/D10]
- 硬件复位启动地址 = `cfx_power_hypv_excp_vector = 0xffff_ffff_0000`（cfxha 63 / `power`），可由 CPU 直接取指执行；BootROM 大小由平台 profile 规定：`Kaiwu-Tiny` 64 KiB（`0xffff_ffff_0000`–`0xffff_ffff_ffff`）、`Kaiwu-Vast` 4 MiB（`0xffff_ffc0_0000`–`0xffff_ffff_ffff`）；复位向量两 profile 均为末 64 KiB 起点，既有 `-bios` 仍按 64 KiB 复位窗口装载。[DADAO-12 §2.1 核内地址空间][ADR-0043 D1/D2][Machine-01 §1]
- v5 测试机地址划分按 profile（**测试机约定**）：`Kaiwu-Tiny` 为 BootROM 64 KiB + SRAM 8 MiB（cfxha 63，`0xffff_ff00_0000`–`0xffff_ff7f_ffff`）+ **hmon SRAM 64 KiB（cfxha 3，`0x0fff_0000_0000`）**，无 PTW；`Kaiwu-Vast` 为 BootROM 4 MiB + PA RAM 2 GiB（`[0, 2 GiB)`，首张页表 4 个 512 MiB 超页，`VA [0, 2 GiB)` → PA `[0, 2 GiB)`）；两 profile 都不设同一存储的多地址别名；exit port 已删。[ADR-0020 D15][ADR-0004 R3][ADR-0043 D10][Machine-01 §1]
- **hmon/smon SRAM**：hmon（cfx3）`0x0fff_0000_0000`、smon（cfx2）`0x0bff_0000_0000`，各 64 KiB，内部偏移 `0x3ff_0000_0000`，越界 ⇒ `CFXMEM`；power 不设 SRAM。[ADR-0043 D4/D5]
- 核内地址空间非法访问触发 `CFXMEM`（`1<<1`），目标为当前运行模式 monitor；测试机退出码按三段编码（guest PASS `0x00`；guest FAIL `0x01`–`0x7F`，值 = 失败点序号 1–127；其它 cfx `0x80`–`0xBF`；monitor `0xC0`–`0xFF`），完整位域见 `spec/Kaiwu §7.1`；保留 cfx（6–14、16–31、35–61）的普通 `ld/st` 归当前 monitor 的 `CFXMEM`。[DADAO-12 §2.1 核内地址空间][DADAO-12 §4. 专有寄存器设计规范][ADR-0004 D5.8]
- 越界**取指**与越界数据访问**同等报异常**，不得静默；退出码分段与 monitor/其它 cfx 位域冻结不重排。[ADR-0020 D15][ADR-0004 D5.8]
- **`cfx_pmem` SRAM 与 DMA**：`cfx_pmem`（cfxha 32）内含 64 KiB SRAM（内部偏移 0x3ff_0000_0000，核内起始 `0x83ff_0000_0000`），CPU 用普通 `ld/st` 访问、越界 ⇒ `CFXMEM`；DMA 只在 SRAM ↔ PA 间搬运，`cg15` 寄存器为 `dma_src`/`dma_dst`/`dma_size`/`dma_ctrl`/`dma_status`；CFX 侧取低 42 位、PA 侧取低 56 位（高位忽略），`size` 30 位、合法 `1..2^29`。[DADAO-12 §2.1 核内地址空间][DADAO-12 §4.9 cfx_pmem - physical memory management][ADR-0042 D3/D6/D7.1–D7.3]
- **`cfx_pmem` DMA 控制/状态**：`dma_ctrl` bit0 `START`（自清）/bit1 `DIR`（0=CFX→PA，1=PA→CFX）/bit2 `IRQ_EN`；`dma_status` bit0 `BUSY`、bit1 `DONE`（W1C）、bit2 `ERROR`（W1C，同时清 `ERR_CODE`）、bit3–15 `ERR_CODE`（one-hot：`SIZE`/`CFX_RANGE`/`PA_RANGE`/`PA_FAULT`）；`BUSY=1` 时 cg15 写与 DONE/ERROR W1C 被忽略；`PMEM_DMA` 是异步源、**不占 `excp_cause_id`**（源身份 = 本 cfx 的 cfxha 32，见 §3 的「异步中断来源掩码」条）；`IRQ_EN=1` 时 DONE/ERROR 触发、作为异步源**统一投递 `cfx_hart`**（`spec/DADAO-12 §5.4`），被**当前运行模式 monitor** 的 `cg8 rc1` 掩码屏蔽或 `cfx_hart` 帧活动期时置 `cfx_hart cg9 rc4` 的 `async_src_pending` bit 32；**不携带 `cause_info`**，handler 回本源读 `dma_status`（含 `ERR_CODE`）。[DADAO-12 §4.9 cfx_pmem - physical memory management][DADAO-12 §4.7 cfx_hart - hart management][DADAO-12 §5.4 异步中断进入与退出][ADR-0042 D7.2/D7.4][ADR-0061 D2/D5/D8]
- **`cfx_pmem` DMA 的 SBI 封装**：FID 6 `SBI_PMEM_DMA_START`（`rd16` = dir、`rd17` = src、`rd18` = dst、`rd19` = size；只检查 `BUSY`，忙返回 `−5`，否则写 `cg15` `rc0`–`rc3` 并返回 0；不校验地址/长度）、FID 7 `SBI_PMEM_DMA_STATUS`（返回原始 `dma_status`，不另造错误码、不做 W1C）、FID 8 `SBI_PMEM_DMA_WAIT`（预留，返回 `SBI_ERR_NOT_SUPPORTED`）；`START` 返回 0 仅表示调用完成且当时不忙，调用方须读 `STATUS` 判定传输结果。[DADAO-22 §9. 物理存储器管理（cfx_pmem）]

## §3 cfx 与权限

- 每个 cfx 提供 cg0–cg7 共有寄存器；`cg0`–`cg3` 的 `rc0`–`rc3` 为 `cfxtrap`/`cfxmem`/`cfxreg`/`cfxexe` 四类同步来源 mask，另有 `switch_run_mode`/`excp_vector`；`rc4` **不定义（保留，访问 ⇒ `CFXREG`）**；异步来源掩码在 `cfx0`–`cfx3` 的 `cg8 rc1`（`cfx_umon/jmon/smon/hmon_async_intr_mask`）；`cfx_hart` 另有 `cg9` 异步现场寄存器组（7 槽 + `rc7`–`rc15` reserved，见 `DADAO-12 §4.7`）。[DADAO-12 §3. 共有寄存器设计规范][DADAO-12 §4.7 cfx_hart - hart management][ADR-0061 D5/D7]
- 两轴授权：最终允许 = 运行模式允许 AND cfx 资源允许；`self` 只绕过 cfx 轴（位测试），仍使用当前运行模式的寄存器行。mask 位索引为源 cfx，0=允许、1=屏蔽。[ADR-0045 D1/D2][DADAO-12 §3. 共有寄存器设计规范]
- 四类同步 mask 初值：power 与普通 cfx `0xFFFF_FFFF_FFFF_FFF7`，hmon 自身 `0x7FFF_FFFF_FFFF_FFF7`；`cfx0`–`cfx3` 的 `cg8 rc1`（异步来源掩码）初值全 1；`cg0`–`cg3 rc4` 不定义（保留）。[ADR-0045 D4][DADAO-12 §3. 共有寄存器设计规范][ADR-0061 D5]
- 权限拒绝触发 `CFXPERM`（`1<<7`，进入当前模式 monitor），不再是 ILLI；escape 帧/目标错误触发 `CFXESC`（`1<<3`，进入当前 cfx）。[ADR-0045 D6/D7][DADAO-12 §4. 专有寄存器设计规范]
- **cg 级授权**：每个 cfx 的 `cfx_⟨cfxname⟩_hypv_cg_reg_deleg`（`cg3 rc12`，复位全 1、RW）为 64 位位图，bit 索引 = cg 编号（0–63），`bit=0` 允许 `supv` 访问该 cg、`bit=1` 拒绝；`bit3` 硬件固定 1（软件写 0 无效、读回恒 1），故 `supv` 访问任何 cfx 的 cg3 恒被拒；`supv` 访问**任何** cfx（含自身）都查**目标 cfx** 的该位图（**不豁免 self**），拒绝走 `CFXPERM`（无 cg3 例外）；`hypv` 不受该位图约束，`user`/`jail` 不参与该检查（其 cg3 仍由寄存器组合规则报 `CFXREG`）。软件约定：需开放的 cfx 由 `hmon` 写 `cg3 rc12 = 0x8` 整组开放（唯一置位为恒 1 的 bit3），不逐 cg 清位；`cfx_power` 例外——其 deleg 保持 `~0`，仅写 `cg2 rc1` 的 bit2=0（cfxmem 轴）供 `smon` 读 BootROM，不改 deleg 语义。[DADAO-12 §3.4 cg3 - hypv mode 寄存器][DADAO-23 §3. 启动与引导移交约定]
- reserved cfxha（`6`–`14`、`16`–`31`、`35`–`61`）触发 `ILLI`。[DADAO-12 §5. 异常进入与异常退出]
- 异步中断来源掩码 = **当前运行模式 monitor** 的 `cg8 rc1`（`cfx_umon_async_intr_mask`/`cfx_jmon_async_intr_mask`/`cfx_smon_async_intr_mask`/`cfx_hmon_async_intr_mask`）：位索引 = **源 cfxha**（`TIMER` ⇒ 15、`PMEM_DMA` ⇒ 32），`0=允许`、`1=屏蔽`，复位全 1；**投递目标 = `cfx_hart`**（hart-first，`spec/DADAO-12 §5.4`）；被屏蔽或 `cfx_hart` 帧活动期时置 `cfx_hart cg9 rc4`（`async_src_pending`，位 = 源 cfxha）pending，mask 解除后补投。`trap`/`escape` **不保存、不恢复**该掩码（策略不是现场）；`cg0`–`cg3 rc4` 不定义（保留）。[ADR-0061 D2/D5/D6][DADAO-12 §5.4 异步中断进入与退出][DADAO-12 §4.1 cfx_umon - user monitor][DADAO-12 §4.7 cfx_hart - hart management]
- 访问**未实现**的核芯功能扩展（其 cfx 寄存器）触发 `CFXREG`。[DADAO-22 §3. 系统信息（smon）]
- HSJU 或 R/W/X 不符属于页表/PTW 层权限异常：当前运行模式对应的 HSJU 位为 0，或取指/读/写分别不满足 X/R/W 时触发 `CFXPERM`（当前运行模式 monitor）；地址转换第一步不再按 `VA[47:42]` 选择 PTBR，也无 PTBR 模式权限位图。[DADAO-12 §2.2.5 操作系统页管理][DADAO-12 §4.5 cfx_ptw - page table walker]
- **两层权限不可混同**：页表/PTW 层权限（HSJU 或 R/W/X 不符）与 cfx 访问权限（`cfxtrap`/`cfxmem`/`cfxreg`/`cfxexe` mask 拒绝）分属不同层次；两者失败后均归当前运行模式 monitor 的 `CFXPERM`（原因名收敛，权限来源不同）。[ADR-0020 D9][ADR-0045 D6][DADAO-12 §4. 专有寄存器设计规范]
- v5 测试机 cfx 实现范围按 profile（**测试机约定**、非上游架构限制）：`Kaiwu-Tiny` **实现 `cfx_power`（cfx63，启动）+ `cfx3 hmon`（异常）**，不实现 smon/PTW；semihosting 的 `trap` 按 `immu18 ∈ 0x3FF00–0x3FFFF` 判定，与 cfxha 无关；`Kaiwu-Vast` 为 `cfx0/1/2/3/63` 以及 `cfx4` 的 PTW/TLB 寄存器（`cfx_ptw_ptbr`/`cfx_ptw_enable`/`cfx_ptw_tlb_*`）、页表步进、TLB 命中/填充/失效与 A/D 回写，加上 `cfx32` 的 64 KiB SRAM 与 `cg15` DMA，以及 `cfx15` 单 hart 定时器 + `cfx34` 全局时间，还有 `cfx5`（`cache`）的寄存器与维护命令（寄存器面与命令语义见 `contract-cache.md`）；范围外未实现 cfx 触发 `CFXREG`。[ADR-0020 D9][Machine-01 §3]
- **cg7 内部空间描述**：每个 cfx 用 cg7 描述自身核内空间——每 4 个 rc 一个空间块、`i=0..15` 共 16 块（`rc = 4i+0..3`，寄存器名 `cfx_⟨cfxname⟩_space_desc[i]`/`space_start[i]`/`space_size[i]`/`space_attr[i]`）：desc（bit0=`exists`；bit1=SRAM/bit2=ROM/bit3=MMIO/bit4=DRAM/bit5=OTHER，存在时 one-hot）、start（42 位内部偏移，完整地址 `(cfxha << 42) | start`）、size（`start + size ≤ 2^42`）、attr（bit0=R/bit1=W/bit2=X/bit3=cacheable/bit4=shareable/bit5=volatile）；`exists=0` 时 start/size/attr 读 0；cg7 全部只读，写任意 rc ⇒ `CFXREG`；cg7 只描述空间、不做传输控制。`Kaiwu-Vast` 实测块：smon/hmon `start=0x3ff_0000_0000 size=0x1_0000 attr=R|W|X`、pmem 同 start/size 而 `X=0`、power `start=0x3_ffc0_0000 size=0x40_0000 attr=R|X`；其余已实现 cfx（umon/jmon/ptw）无空间（16 块全 `exists=0`），未实现 cfx 访问仍 `CFXREG`；`Kaiwu-Tiny` 实现 `cfx_power`（cfx63）与 `cfx3 hmon` 两个 cfx：hmon 的 cg7 描述 hmon SRAM（`start=0x3ff_0000_0000 size=0x1_0000`），`cfx_power` 的 cg7 描述 BootROM（`0x3_ffc0_0000`+`0x40_0000`，R|X）；其余 cfx 未实现（访问其寄存器 ⇒ `CFXREG`）。[DADAO-12 §3.8 cg7 - 内部空间描述寄存器][Machine-01 §3]（块值 = 测试机约定）
- **`cfx_time`（cfxha 34）**：per-system、64 位、只读、自由运行、不产生中断；`cg10 rc0 = cfx_time_freq = 1_000_000_000`（1 GHz 测试机约定），`cg10 rc1 = cfx_time_value`（64 位，复位后从 0 起算），`rc2`–`rc63` 保留（读写 ⇒ `CFXREG`）；QEMU 以 `QEMU_CLOCK_VIRTUAL` ns 建模，1 count = 1 ns。[DADAO-12 §4.10 cfx_time - 全局时间计数器][DADAO-22 §10. 全局时间（cfx_time）]（频率/1 ns 为测试机约定）
- **`cfx_hart`（cfxha 15，单 hart）**：`cg8 rc0 = hart_id = 0`（RO）；`rc1` 保留；`rc2 = cycle`（RO，64 位）、`rc3 = insn`（RO，64 位），测试机约定 cycle = 自复位起的虚拟时钟 ns（1 count = 1 ns，与 `cfx_time_value` 同基准、单 hart 下读数相等）、insn = 已执行指令数（每指令派发时累加、64 位自然回绕、不依赖 `-icount`）；写 `rc2`/`rc3` ⇒ `CFXREG`；`rc4 = timer_cmp`（RW，64 位绝对时间，单位同 `cfx_time_value`；写新值取消旧 deadline 并清 `ISTATUS`（未投递事件随之取消），全 1 = 关闭）、`rc5 = timer_ctrl`（RW：bit0 ENABLE、bit1 IMASK、bit2 ISTATUS 只读；读回 = `ctrl[1:0] | ISTATUS << 2`，其余位读回 0）；`rc6`/`rc7` 保留；到期触发可屏蔽 `TIMER`（源身份 = 本 cfx 的 cfxha 15；**不占 `excp_cause_id`**、无 `cause_info`），compare 匹配置 `ISTATUS`、`IMASK=0` 时经统一仲裁投递给**本 hart 的 `cfx_hart`**（即投递给自身 cfx；投递成功才清源位），`IMASK=1` 时源本地 gate（`ISTATUS` 保留、不投递），解除 IMASK 且 `ISTATUS=1` 时重踢补投；`cg9` 异步现场（7 槽：`rc0` `async_prev_run_mode`、`rc1` `async_prev_cfx_code`、`rc2` `async_cause_ip`、`rc3` `async_src_frame`（HW/RO）、`rc4` `async_src_pending`（HW/RO）、`rc5` `async_excp_vector`、`rc6` `async_switch_run_mode`（固定 supv）、`rc7`–`rc15` reserved，见 `DADAO-12 §4.7`）归本 cfx；`SBI_HART_GET_ID`（FID 0）/`SBI_HART_SET_TIMER`（FID 1，`rd16` = 64 位绝对时间）为对应 SBI；不实现 IPI/多 hart。[DADAO-12 §4.7 cfx_hart - hart management][DADAO-22 §7. Hart管理（cfx_hart）]（cycle/insn/ns 基准为测试机约定）
- **异步边界（测试机约定）**：`TIMER` 与 `PMEM_DMA` 均为异步可屏蔽源，经 `CPU_INTERRUPT_HARD` 与 `dadao_cpu_exec_interrupt()` 的**唯一仲裁入口**投递到 **`cfx_hart`**（cfxha 15），再由 `cfx_enter(async)` 经 `cfx_hart cg9 rc5`（`async_excp_vector`）进入 supv 异步向量（`cg9 rc6` 固定 supv）；源身份 = 源 cfxha（15/32），pending/掩码/一帧多源按「统一异步中断（测试机约定）」执行；`TIMER` 的 IMASK 源本地 gate 只表现为 `ISTATUS` 保留、不新建位图。[ADR-0046 D2 方法依据][DADAO-12 §4.7 cfx_hart - hart management][DADAO-12 §4.9 cfx_pmem - physical memory management][DADAO-12 §5.4 异步中断进入与退出]
- **统一异步中断（测试机约定，hart-first）**：异步源身份 = **源 cfxha**（`TIMER` = 15、`PMEM_DMA` = 32），**不占 `excp_cause_id`**；delivery pending 只记在 `cfx_hart cg9 rc4`（`async_src_pending`，位 = 源 cfxha）——源事件到达置位、投递时清位、源在源 cfx 被 ack（`timer_cmp` 重装 / `dma_status` W1C）后落位。投递目标 = `cfx_hart`（hart-first），入口 = `cfx_hart cg9 rc5`（`async_excp_vector`）的 supv 单向量，目标模式 = `cg9 rc6`（固定 supv）。**一帧多源**：同一指令边界上所有 pending 且被**当前运行模式 monitor 的 `cg8 rc1`** 放行的源一次性进入同一帧（`async_src_frame` 位图并集），`async_src_pending` 扣除这些位、`excp_async_num` 每帧 +1（与源个数无关），不串行也不拆帧。**无嵌套**：帧活动期（`async_src_frame != 0`）到达的新事件只置 pending、不再进入；合法 `escape` 返回时硬件清 `async_src_frame` 释放帧，随后按下一指令边界补投。`dadao_cpu_exec_interrupt()` 只有一处仲裁入口，按上述规则一次进入一帧。**pending 不随模式切换迁移**（记在 per-hart 的 `cfx_hart`，单一归处、无迁移动作；任务退出丢弃、依赖源重触发）；**不引入** `async_enable` 类源内总开关。`async_src_frame`/`async_src_pending` 硬件写、软件只读（写忽略）；软件可快照 `rc0`–`rc2` 并改写 `prev_*`/`async_cause_ip` 后 `escape`，但**不能**写 0 丢弃帧。[DADAO-12 §5.4 异步中断进入与退出][DADAO-12 §4.7 cfx_hart - hart management][ADR-0061 D2/D3/D5/D6/D7]

## §4 `trap`/`escape` 与异常进入/退出

- `trap cfxha, immu18`：`cfxha` 为服务提供者、`immu18` 为功能编号。[DADAO-22 §1. 调用约定]
- 一般 trap（`immu18 < 0x3FF00`）走 `DADAO-12 §5` 异常进入流程步骤 1–10，进入目标 cfx 异常向量。[DADAO-12 §5. 异常进入与异常退出][ADR-0020 D10]
- `escape cfxha, [excp_cause_ip, imms20]` 完成异常退出；编码层 `imms18[0]` 为偏移 bit2、`imms18[1]` 为**帧选择位**（0=`cg5` 同步帧、1=`cg9` 异步现场）、`imms18[17:2]` 为 SBZ；合法 `imms18 ∈ {0, 1, 2}`（`cg5` 偏移 0/+4、`cg9` 偏移 0），`imms18 = 3` ⇒ `ILLI`；`Addr = excp_cause_ip + ((imms18 & 1) << 2)`（`cg9` 取 `async_cause_ip`）；`cfxha` 必须是当前 cfx，返回 cfx/mode/IP 取自所选帧，偏移固定；目标/帧错误 ⇒ `CFXESC`。[DADAO-12 §5. 异常进入与异常退出][DADAO-12 §5.1 指令行为说明][SimRISC-11 §退出指令][ADR-0045 D8][ADR-0060 D4]
- 被调方经 `escape cfxha, [excp_cause_ip, 4]` 返回 trap 下一条指令。[DADAO-22 §1. 调用约定]
- **两条路分离**：semihosting（`immu18[17:8] == 0x3FF`，即 `0x3FF00–0x3FFFF`）经实现层短路、不进入向量、IP 步进返回，见 `contract-semihosting.md`；不得混入向量路径。[ADR-0020 D10][Machine-01 §4]

## §5 SBI 调用约定

- 调用方 `trap cfxha, immu18` 陷入目标 cfx；被调方经 `escape cfxha, [excp_cause_ip, 4]` 返回。[DADAO-22 §1. 调用约定]
- 参数传递与 ABI 传参规范一致（参见 `contract-abi.md`）。[DADAO-22 §1. 调用约定][DADAO-21 §传参：Parameter Passing]
- 参数寄存器：`rd16–rd31`（数据）、`rb16–rb31`（地址）、`rf16–rf31`（浮点）；三组独立计数、从 16 起递增。[DADAO-21 §参数寄存器：Parameter registers]
- 标量返回值用 `rd8`；指针返回值用 `rb8`。[DADAO-21 §标量类型返回值：Scalar type return]
- 系统调用号存于 `rd15`，与 `immu18` 为两个独立层次。[DADAO-21 §系统调用规范]
- 错误码：`0 = SBI_SUCCESS`、`−1 = SBI_ERR_FAILED`、`−2 = SBI_ERR_NOT_SUPPORTED`、`−3 = SBI_ERR_INVALID_PARAM`、`−4 = SBI_ERR_NO_DEVICE`、`−5 = SBI_ERR_BUSY`（资源忙，可重试）。[DADAO-22 §1. 调用约定]

## §6 内核侧异常与中断（v5 扩展，M14 K2）

- **定位**：本节归一化 v5 内核（K2）消费的四类事实——异常现场 `info` 语义、`escape` 的返回目标、异步中断的内核入口、内核侧中断使能旋钮，外加时间口径的**两处缺口**；上游语义不重定义，与 `spec/` 冲突时以 `spec/` 为准并阻断实现。[spec-decision]
- **与 §3 的分工**：§3 已冻结的寄存器级口径（两级 mask、pending 归属、统一异步中断仲裁、`cfx_time`/`cfx_hart` 寄存器语义）本节**只写指针**、不重抄，避免两处漂移。[contract-see §3]

### §6.1 `excp_cause_info` 的覆盖范围与子原因位（11 项 cause + 18 位子原因；未规定者为 0）

- **本表 = monitor 视角的同步原因表**：`cfx_umon`/`cfx_jmon`/`cfx_smon`/`cfx_hmon` 同构；`excp_cause_id` 分层——`[15:0]` **同步 cause** 在各 cfx **独立编址**（`1 << 8` 在 `cfx_umon` 为 `ILLI`、在 `cfx_hart` 为 `IPI`），查 `info` 语义前须先按**目标 cfx** 选表，不得跨 cfx 套用同名同步 cause；`[31:16]` **保留**，**异步源不占 `excp_cause_id`**（源身份 = 源 cfxha），不随 cfx 选表。[DADAO-12 §5. 异常进入与异常退出][DADAO-12 §3.6 cg5 - 异常现场寄存器][DADAO-12 §5.4 异步中断进入与退出][ADR-0061 D2]
- **可解析形态**：下表一 cause 一行、列序固定（`excp_cause_id` / 名称 / `info` 语义 / 取值与单位 / 来源 / 子原因），`info` 语义列**逐字**取上游表述，供静态比对脚本现场解析。[spec-decision][DADAO-12 §4.1 cfx_umon - user monitor]

| `excp_cause_id` | 名称 | `info` 语义 | 取值与单位 | 来源 | 子原因 |
|-----------------|------|------------|------------|------|--------|
| `1 << 0` | `CFXTRAP` | 指令编码 | 32 位指令字（触发 `trap` 的指令本身） | `[DADAO-12 §4.1 cfx_umon - user monitor]` | — |
| `1 << 1` | `CFXMEM` | 访存地址 | 48 位 CPU 地址（A/D 回写失败时为 PTE 物理地址；非页表类为被访问的核内地址） | `[DADAO-12 §4.1 cfx_umon - user monitor]` `[DADAO-12 §5.2 异常进入流程]` | **wyde3 `[63:48]`**：缺失类 `[48..55]` 之一，或 `[56]` `ADWBFAIL`、`[57]` `NONPTW`；`[63:58]` 保留；**wyde2 必须全 0**；逐位见 §6.1.1 |
| `1 << 2` | `CFXREG` | 指令编码 | 32 位指令字（非法寄存器访问指令） | `[DADAO-12 §4.1 cfx_umon - user monitor]` | — |
| `1 << 3` | `CFXESC` | 指令编码 | 32 位指令字（`escape` 指令本身） | `[DADAO-12 §4.1 cfx_umon - user monitor]` | — |
| `1 << 7` | `CFXPERM` | 地址 | 48 位 CPU 地址（页表/`cfxmem` 权限拒绝）或目标 `IP` / 触发指令地址（`cfxexe` / `cfxtrap`、`cfx2rd`、`cfx2rc`；后者与 `excp_cause_ip` 同值）；恒为地址 | `[DADAO-12 §4.1 cfx_umon - user monitor]` `[DADAO-12 §3.6 cg5 - 异常现场寄存器]` | **wyde2 `[47:32]`**：`[32..39]` 内存权限类之一（含 `[39]` `NCFXPERM`）；`[47:40]` 保留；**wyde3 必须全 0**；逐位见 §6.1.1 |
| `1 << 8` | `ILLI` | 指令编码 | 32 位指令字 | `[DADAO-12 §4.1 cfx_umon - user monitor]` | — |
| `1 << 9` | `UNDI` | 指令编码 | 32 位指令字 | `[DADAO-12 §4.1 cfx_umon - user monitor]` | — |
| `1 << 10` | `RASOF` | 准备压栈的返回地址 | 被压栈保护的返回地址（压栈前的 `IP`） | `[DADAO-12 §4.1 cfx_umon - user monitor]` | — |
| `1 << 11` | `RASUF` | 全零（无效） | `0`（不携带信息） | `[DADAO-12 §4.1 cfx_umon - user monitor]` | — |
| `1 << 12` | `MALIGN` | 访存地址 | 48 位 CPU 地址 | `[DADAO-12 §4.1 cfx_umon - user monitor]` | — |
| `1 << 13` | `IALIGN` | IP 值 | 非法 `IP`（`IP[1:0] ≠ 00`，异常时 IP 停留于该地址） | `[DADAO-12 §4.1 cfx_umon - user monitor]` | — |

- **未规定者为 0**：上表之外的 cause（含保留位）`info` 为 0；`Kaiwu §4.4` 另列的 5 项（`CFXMEM`/`ILLI`/`UNDI`/`MALIGN`/`IALIGN`）与本表逐项同义，**不是**第二套口径。[Machine-01 §4.4 同步异常进入 hmon][DADAO-12 §4.1 cfx_umon - user monitor]
- **异步源的 `info` 不走本表、也不经 `cause_info`**：源身份 = **源 cfxha**（`TIMER` = 15、`PMEM_DMA` = 32），handler 按 `cfx_hart cg9 rc3`（`async_src_frame`）的位回源 cfx 读寄存器——`TIMER` → `cfx_hart cg8 rc5`（`ISTATUS`）、`PMEM_DMA` → `cfx_pmem cg15 rc4`（`dma_status` 含 `ERR_CODE`），详见 §3 与 §6.3。[DADAO-12 §4.7 cfx_hart - hart management][DADAO-12 §4.9 cfx_pmem - physical memory management][DADAO-12 §5.4 异步中断进入与退出][ADR-0061 D2/D8]
- **内核侧消费口径**：`CFXTRAP` 的 `info` 为触发指令字，`immu18 = info & 0x3FFFF`（该等式属合约内推导，见 `contract-syscall §8`）；诊断打印须先按目标 cfx 与 cause 选列，再解释 `info` 的单位。[contract-syscall §8][DADAO-12 §3.6 cg5 - 异常现场寄存器]
- **子原因位按 wyde 分段（18 位 one-hot，每个 cause 独占一个 wyde）**：**wyde2 `[47:32]` 专供 `CFXPERM`**（低字节 `[39:32]` 8 位权限原因、`[47:40]` 保留）；**wyde3 `[63:48]` 专供 `CFXMEM`**（低字节 `[55:48]` 8 位缺失类、`[56]` `ADWBFAIL`、`[57]` `NONPTW`、`[63:58]` 保留）。**仅 `CFXMEM`（`1 << 1`）与 `CFXPERM`（`1 << 7`）有效**，且对应 wyde 内**恰一位**为 1：`CFXPERM` 时 **wyde3 必须全 0**、`CFXMEM` 时 **wyde2 必须全 0**；**其它任何 cause 下两个 wyde 都必须全 0**（归属不符 ⇒ 按「未列出位被错误触发」处理）。`[31:16]` 保留给未来新的大类 cause，当前必须全 0、子原因不得占用。`CFXMEM` 的页表类走缺失类或 `ADWBFAIL`，**非页表类（cfx 空间非法访问/取指、未实现 cfx 的普通 `ld/st`、存储块故障、`ptw_enable = 0` 访存）用 `NONPTW`**；`CFXPERM` 走内存权限类或 `NCFXPERM`。[DADAO-12 §3.6 cg5 - 异常现场寄存器][ADR-0056 D2]
- **handler 取值（规范用法）**：拿到 `CFXPERM` 时子原因 = `(cause_id >> 32) & 0xFFFF`；拿到 `CFXMEM` 时子原因 = `(cause_id >> 48) & 0xFFFF`；一个 cause 只查一个 wyde，另一 wyde 恒为 0。[DADAO-12 §3.6 cg5 - 异常现场寄存器][ADR-0056 D2]
- **`CFXMEM`/`CFXPERM` 的 `info` 恒为地址**：一个 cause 只有一种 `info` 类型，处理程序不按子原因再分支——`CFXMEM` = 访存地址（`ADWBFAIL` 时 = PTE 物理地址）；`CFXPERM` = 页表/`cfxmem` 权限拒绝的访存地址、`cfxexe` 拒绝的目标 `IP`、`cfxtrap`/`cfx2rd`/`cfx2rc` 拒绝的**触发指令地址**（与 `excp_cause_ip` 同值，刻意统一）。[DADAO-12 §3.6 cg5 - 异常现场寄存器][ADR-0056 D4]

### §6.1.1 子原因位表（wyde2 `[47:32]` / wyde3 `[63:48]`，与 `DADAO-12 §3.6` 逐位一致）

- **取值形态**：下标为 `cause_id` 的绝对位号；与低 16 位 cause **同时**写入 `excp_cause_id`（两者各自 one-hot）；取指用 `I` 前缀、数据读写用 `D` 前缀；wyde 归属互斥（`CFXPERM`→wyde2、`CFXMEM`→wyde3），不得跨 wyde。[DADAO-12 §3.6 cg5 - 异常现场寄存器][DADAO-12 §2.2.6 异常检查优先级]

| 子原因位 | wyde | 名称 | 目标 cause | 触发条件 |
|----------|------|------|-----------|---------|
| `[32]` | wyde2 | `NUPERM` | `CFXPERM` | HSJU 的 `U` 位 = 0 且当前运行模式为 `user` |
| `[33]` | wyde2 | `NJPERM` | `CFXPERM` | HSJU 的 `J` 位 = 0 且当前运行模式为 `jail` |
| `[34]` | wyde2 | `NSPERM` | `CFXPERM` | HSJU 的 `S` 位 = 0 且当前运行模式为 `supv` |
| `[35]` | wyde2 | `NHPERM` | `CFXPERM` | HSJU 的 `H` 位 = 0 且当前运行模式为 `hypv` |
| `[36]` | wyde2 | `NRPERM` | `CFXPERM` | 读访问且页的 `R` = 0 |
| `[37]` | wyde2 | `NWPERM` | `CFXPERM` | 写访问且页的 `W` = 0 |
| `[38]` | wyde2 | `NXPERM` | `CFXPERM` | 取指且页的 `X` = 0 |
| `[39]` | wyde2 | `NCFXPERM` | `CFXPERM` | cfx 访问被来源掩码拒绝（`cfxtrap`/`cfxreg`/`cfxexe`） |
| `[48]` | wyde3 | `IGPTRAP` | `CFXMEM` | 取指：L1 `P = 0` 且 `SP = 0`，或 L2 `P = 0`（普通页缺失） |
| `[49]` | wyde3 | `ISPTRAP` | `CFXMEM` | 取指：L1 `P = 0` 且 `SP = 1`（超页缺失） |
| `[50]` | wyde3 | `IGPFTRAP` | `CFXMEM` | 取指：L2 `P = 1` 且 GPF 对应小页位 = 0（普通页小页缺失） |
| `[51]` | wyde3 | `ISPFTRAP` | `CFXMEM` | 取指：L1 `P = 1`、`SP = 1` 且 SPF 对应小页位 = 0（超页小页缺失） |
| `[52]` | wyde3 | `DGPTRAP` | `CFXMEM` | 数据读写：L1 `P = 0` 且 `SP = 0`，或 L2 `P = 0` |
| `[53]` | wyde3 | `DSPTRAP` | `CFXMEM` | 数据读写：L1 `P = 0` 且 `SP = 1`（超页缺失） |
| `[54]` | wyde3 | `DGPFTRAP` | `CFXMEM` | 数据读写：L2 `P = 1` 且 GPF 对应小页位 = 0 |
| `[55]` | wyde3 | `DSPFTRAP` | `CFXMEM` | 数据读写：L1 `P = 1`、`SP = 1` 且 SPF 对应小页位 = 0 |
| `[56]` | wyde3 | `ADWBFAIL` | `CFXMEM` | PTE 物理写失败（`clean`/`flush`/条目替换的回写） |
| `[57]` | wyde3 | `NONPTW` | `CFXMEM` | 非页表类访存故障：cfx 空间非法访问/取指、未实现 cfx 的普通 `ld/st`、核内存储块故障、`ptw_enable = 0` 的访存 |

### §6.2 `escape` 的返回 cfx 恒为当前 cfx（跨 cfx 返回不存在）

- **帧内保存 `excp_prev_cfx_code`，但软件不能借此指定返回 cfx**：`cg5` 有 `excp_prev_run_mode`/`excp_prev_cfx_code`（`rc1`）/`excp_cause_id`/`excp_cause_ip`/`excp_cause_info`/`excp_pending` 六个字段（旧 cfx 屏蔽字段已删、对应 `rc` 作 `reserved`）；`excp_prev_cfx_code` 在硬件陷入时保存进入前的 `inner_cfx_code`、`escape` 时恢复，故「异常前在哪个 cfx」由硬件记录而非软件选择。[DADAO-12 §3.6 cg5 - 异常现场寄存器][DADAO-12 §5.2 异常进入流程][DADAO-12 §5.3 异常退出流程]
- **返回目标 = 当前 cfx**：`escape` 的 `cfxha` 必须是 `inner_cfx_code`，返回的 cfx / 运行模式 / `IP` **全部**取自当前 cfx 的**所选帧**（同步 `cg5`：`excp_prev_cfx_code`/`excp_prev_run_mode`/`excp_cause_ip`；异步 `cfx_hart cg9`：`async_prev_cfx_code`/`async_prev_run_mode`/`async_cause_ip`）⇒ **跨 cfx 返回不存在**，内核的 trap 入口只允许 `escape <当前 cfx>`（不得指望「从 `smon` 帧返回 `umon`」）。[DADAO-12 §5.1 指令行为说明][DADAO-12 §5.3 异常退出流程][DADAO-12 §4.7 cfx_hart - hart management][ADR-0045 D8]
- **帧选择位与合法编码**：`imms18[1]` 为**帧选择位**（0 = `cg5` 同步帧、1 = `cg9` 异步现场），`imms18[0]` 为字节偏移 bit2，`imms18[17:2]` 为 SBZ；合法 `imms18 ∈ {0, 1, 2}`（`0`/`1` = `cg5` 偏移 0/+4，`2` = `cg9` 偏移 0），`imms18 = 3`（`cg9` 偏移 +4）⇒ `ILLI`；`cg9` **只允许偏移 0**。汇编层 `imms20 = imms18 << 2 ∈ {0, 4, 8}`。[DADAO-12 §5.1 指令行为说明]
- **失败即 `CFXESC`**：`cfxha != inner_cfx_code`（目标错误）或所选帧无效（`cg5`：`excp_cause_id = 0`；`cg9`：当前 cfx 非 `cfx_hart` 或 `async_src_frame = 0`）⇒ **切换任何状态之前**触发当前 cfx 的 `CFXESC`（`1 << 3`），cfx / 运行模式不变；`imms18[17:2]` 非零（SBZ）、`imms18 = 3` 或 `cfxha` 为 reserved ⇒ `ILLI`。[DADAO-12 §5.1 指令行为说明][DADAO-12 §5.4 异步中断进入与退出][DADAO-12 §4.7 cfx_hart - hart management]
- **返回 IP 可软件改写**：`cg5 rc3`（`excp_cause_ip`）与 `cfx_hart cg9 rc2`（`async_cause_ip`）均为 RW「软件可写」，故内核可在 `escape` 前把任意返回 IP 写进帧；`escape` 的 `imms18[0]` 只对 `cg5` 帧提供 `+0`/`+4` 两种**相对**偏移，`cg9` 现场固定偏移 0。「先改写帧 IP、再按固定偏移返回」是本合约由两处独立规定组合出的效果，上游未明文写出。[DADAO-12 §3.6 cg5 - 异常现场寄存器][DADAO-12 §4.7 cfx_hart - hart management][DADAO-12 §5.1 指令行为说明][spec-decision]

### §6.3 异步中断的内核入口（hart-first：`TIMER`/`PMEM_DMA` → `cfx_hart` 的 supv 单向量）

- **入口寄存器**：`TIMER`（源 `cfx_hart` = cfxha 15）与 `PMEM_DMA`（源 `cfx_pmem` = cfxha 32）按 hart-first **统一投递 `cfx_hart`**（`spec/DADAO-12 §5.4`）。向量 = `cfx_hart cg9 rc5`（`async_excp_vector`，复位 `0` ⇒ **内核必须自写**，否则首帧跳向地址 `0`——不是内核代码地址）、目标模式 = `cfx_hart cg9 rc6`（`async_switch_run_mode`，固定 `supv`）、现场 = `cfx_hart cg9 rc0`–`rc2` 与两个位图 `rc3`/`rc4` ⇒ **异步与同步是两套独立向量、独立帧**（同步仍走当前运行模式 monitor 的 `<mode>_excp_vector` + `cg5`）；handler 按 `cfx_hart cg9 rc3`（`async_src_frame`）的源 cfxha 位区分异步源。[DADAO-12 §4.7 cfx_hart - hart management][DADAO-12 §5.4 异步中断进入与退出][contract-see §3]
- **源身份（无 cause 编号）**：异步源**不占 `excp_cause_id`**，身份 = **源 cfxha**（`TIMER` = 15、`PMEM_DMA` = 32）；一个源 cfx 至多一个异步 cause，同源内的 DONE/ERROR 等差异回源 cfx 寄存器区分。`[31:16]` 保留、当前必须全 0。[DADAO-12 §3.6 cg5 - 异常现场寄存器][DADAO-12 §5.4 异步中断进入与退出][ADR-0061 D2]
- **帧有效性与无嵌套**：有效帧判据 = `async_src_frame != 0`（`cg9 rc3`）；`from_user` = `async_prev_run_mode == user`（`cg9 rc0`，2 位），内核据此决定是否先切到该 hart 的 per-hart 软件栈变量指向的内核栈、再 adopt 进 `task_pt_regs`。帧活动期到达的新事件只置 `async_src_pending`（`cg9 rc4`，位 = 源 cfxha）、不再进入（硬件不支持嵌套）。帧**只由合法 `escape` 返回释放**（硬件清 `async_src_frame`），软件不能写 0 丢弃；`src_frame`/`src_pending` 均 HW 写、SW 只读（写忽略）。[DADAO-12 §4.7 cfx_hart - hart management][DADAO-12 §5.4 异步中断进入与退出][ADR-0061 D4/D6]
- **向量/现场写入按 4 字节对齐落盘**：`async_excp_vector`（`cg9 rc5`）与 `supv_excp_vector`/`hypv_excp_vector`（`cg2 rc10`/`cg3 rc10`）同构——写入忽略低 2 位（`value[1:0] ← 0`）、不产生异常；`async_cause_ip`（`cg9 rc2`）同样按 4 字节对齐落盘。[DADAO-12 §4.7 cfx_hart - hart management][DADAO-12 §3.4 cg3 - hypv mode 寄存器][spec-decision]
- **返回**：`escape cfx_hart, [async_cause_ip, 8]`（`imms18 = 2`，帧选择位 `imms18[1] = 1`）原地续跑——`async_cause_ip` = **已提交指令之后的 `rb0`**（下一条指令地址，跳转即目标），`cg9` 现场偏移**恒 0**；合法返回恢复 `async_prev_run_mode`/`async_prev_cfx_code` 并释放帧，**不重放**被中断指令。`cg5` 帧的 `[..., 4]` 语义不适用于 `cg9`（`imms18 = 3` ⇒ `ILLI`）。[DADAO-12 §5.1 指令行为说明][DADAO-12 §5.4 异步中断进入与退出][contract-see §6.2][ADR-0061 D9/D10]
- **帧不借掩码**：来源掩码是**当前运行模式 monitor** 的 `cg8 rc1`（§6.4），不随帧保存/恢复；`cfx_hart cg9` 不再有全局/运行期/保存掩码，防重入由 `async_src_frame != 0` 承担。[ADR-0061 D5/D7][DADAO-12 §5.4 异步中断进入与退出][contract-see §3]

### §6.4 内核侧 IE（中断使能）单旋钮

- **硬件没有 IE 状态位**：异步侧只有 `cfx0`–`cfx3` 的 `cg8 rc1`（`cfx_<monitor>_async_intr_mask`，位 = 源 cfxha、复位全 1、`0=允许`/`1=屏蔽`）；`cg0`–`cg3 rc4` 不定义（保留）；无 PS.IE 类架构状态位。[DADAO-12 §4.1 cfx_umon - user monitor][DADAO-12 §4.7 cfx_hart - hart management][ADR-0061 D5]
- **单旋钮 = `cfx_smon_async_intr_mask`（`cg8 rc1`）**：投递时按**当前运行模式**取 monitor 行求值（§5.4 步骤），内核在 `supv` 运行 ⇒ 旋钮 = `cfx_smon_async_intr_mask`。`local_irq_disable`/`enable` = 置位/清位内核关心的源位（`TIMER` ⇒ bit 15、`PMEM_DMA` ⇒ bit 32），`local_irq_save` = 读回该寄存器整字作 `flags`，`restore` = 写回保存值。行只由**运行模式**选定，与 `inner_cfx_code` 无关。[DADAO-12 §5.4 异步中断进入与退出][DADAO-12 §4.3 cfx_smon - supervisor monitor][ADR-0061 D5]
- **编号只有一套**：mask 位索引 = **源 cfxha**（`cfx_hart` ⇒ bit 15、`cfx_pmem` ⇒ bit 32）；`excp_cause_id` 不再承载异步源，故不存在第二套编号；`0 = 允许`、`1 = 屏蔽`。[DADAO-12 §3.6 cg5 - 异常现场寄存器][DADAO-12 §5.4 异步中断进入与退出][ADR-0061 D2/D5]
- **掩码不随帧保存/恢复**：`trap`/`escape` 不读写该掩码（策略不是现场）；帧活动期的防重入由 `async_src_frame != 0` 承担，软件无需也不得借掩码实现互斥。[ADR-0061 D5/D7][DADAO-12 §4.7 cfx_hart - hart management]
- **屏蔽只阻止投递**：屏蔽期或帧活动期事件仍置 `cfx_hart cg9 rc4`（`async_src_pending`），mask 写 / `escape` / 新源事件之后由硬件重踢补投；内核**不自建**软件 pending 位图。**pending 不随模式切换迁移**（记在 per-hart 的 `cfx_hart`，单一归处、无迁移动作；任务退出丢弃、依赖源重触发）。[contract-see §3][DADAO-12 §4.7 cfx_hart - hart management][DADAO-12 §5.4 异步中断进入与退出]
- **决策层**：本口径是 `ADR-0061 D2/D3/D5/D6` 在**内核侧的软件映射**，不新立决策；改口径须回到 `ADR-0061` 并逐条确认。[ADR-0061 D2/D3/D5/D6]

### §6.5 内核时间口径（只补缺口，寄存器语义见 §3）

- **指针（不重抄）**：`cfx_time`（`cg10 rc0 = freq`、`rc1 = value`，1 GHz、1 count = 1 ns）与 `cfx_hart` 定时器（`cg8 rc4 = timer_cmp` 绝对时间、写 `cmp` 取消旧 deadline 并清 `TIMER` pending；`cg8 rc5` 的 `ENABLE`/`IMASK`/`ISTATUS`）已由 §3 冻结。[contract-see §3][DADAO-12 §4.7 cfx_hart - hart management][DADAO-12 §4.10 cfx_time - 全局时间计数器]
- **缺口一 = 读写的放行前提**：内核可直接 `cfx2rd`/`cfx2rc` 这两个 cfx 的上述寄存器，前提是固件已按两轴放行——目标 cfx 的 `supv_cfxreg`（`cg2 rc2`）的「源 cfx = 内核」位清 0，且 `hypv_cg_reg_deleg`（`cg3 rc12`）放开对应 cg（`cfx_hart` 需 cg8、`cfx_time` 需 cg10）；未放行 ⇒ `CFXPERM`。[DADAO-12 §3.4 cg3 - hypv mode 寄存器][DADAO-12 §3.3 cg2 - supv mode 寄存器][contract-see §3]
- **缺口二 = `escape` 后的补投**：mask 写、`escape`、新源事件之后的 pending 重踢与补投由**硬件**完成，内核无需（也不得）软件代投；`IMASK = 1` 只置 pending、不投递。[contract-see §3][DADAO-12 §4.7 cfx_hart - hart management]

### §6.6 职责边界

- 本节只归一化 v5 内核侧口径，不重定义上游语义；`spec/` 正文的修订走 `docs/Process-02` 的变更流程（上游补文须另立 spec 面任务并同笔重算锁文件；`m14-spec-007` 即此类：`DADAO-12 §3.6` 子原因编码已入册、锁已同笔重算）。[spec-decision]

---

- **异步来源掩码沿革（2026-11-17 → 2026-11-23）**：源轴读法先收敛到「**当前运行模式 monitor**」，其载体随后落在 `cfx0`–`cfx3 cg8 rc1` 的 `cfx_<monitor>_async_intr_mask`（`DADAO-12 §4.1`–`§4.4`）；旧的 `cg0`–`cg3 rc4` 不定义（保留）。[DADAO-12 §4.1 cfx_umon - user monitor][DADAO-12 §4.7 cfx_hart - hart management]

## 附录 A：来源对照

| 本合约 § | 内容 | spec/ 来源 |
|----------|------|-----------|
| §1 | 运行模式（四模式）、任意模式执行核芯功能扩展指令、switch_run_mode | `DADAO-12 §1. 运行模式与核芯功能扩展`、`§5. 异常进入与异常退出`、`§3.4 cg3 - hypv mode 寄存器`；`SimRISC-11 §指令域与执行条件` |
| §2 | 核内地址空间 / 复位向量 / CFXMEM / cfx_pmem SRAM+DMA / 测试机划分 | `DADAO-12 §2.1 核内地址空间`、`§4. 专有寄存器设计规范`、`§4.9 cfx_pmem - physical memory management`；`ADR-0020 D15`、`ADR-0004 D5.8`/`R3`；`ADR-0042 D3/D6/D7` |
| §3 | cfx 共有寄存器 / 同步 mask（`rc4` 不定义） / monitor 异步来源掩码（`cg8 rc1`） / PERM 层次 / 未实现 cfx / cfx_time / cfx_hart 定时器、计数与 `cg9` 异步现场（7 槽） / 统一异步（hart-first、一帧多源） | `DADAO-12 §3. 共有寄存器设计规范`、`§3.8 cg7 - 内部空间描述寄存器`、`§4.7 cfx_hart - hart management`、`§4.9 cfx_pmem - physical memory management`、`§4.10 cfx_time - 全局时间计数器`、`§5. 异常进入与异常退出`、`§5.4 异步中断进入与退出`、`§2.2.1 超页的地址转换`、`§2.2.2 普通页的地址转换`；`DADAO-22 §3. 系统信息（smon）`、`§7. Hart管理（cfx_hart）`、`§10. 全局时间（cfx_time）`；`ADR-0020 D9`、`ADR-0046 D2`、`ADR-0061 D2/D3/D5/D6/D7` |
| §4 | trap/escape 路由、异常进入/退出 | `DADAO-12 §5. 异常进入与异常退出`、`§异常退出流程`；`DADAO-22 §1. 调用约定`；`SimRISC-11 §退出指令`；`ADR-0020 D10` |
| §5 | SBI 调用约定、参数/返回寄存器、错误码 | `DADAO-22 §1. 调用约定`；`DADAO-21 §参数寄存器：Parameter registers`、`§标量类型返回值：Scalar type return`、`§系统调用规范` |
| §6 | 内核侧异常/中断：`excp_cause_info` 11 项 + 子原因位 wyde2/wyde3（`CFXPERM`/`CFXMEM`，共 18 位）+ 未规定者为 0、`escape` 的所选帧与帧选择位（`cg5` 同步帧 / `cfx_hart cg9` 异步现场）、异步内核入口（`cg9 rc5` supv 单向量、`rc6` 固定 supv、`rc0`–`rc4` 现场/位图）、内核 IE 单旋钮（`cfx_smon_async_intr_mask`，`cg8 rc1`）、时间口径指针与两处缺口 | `DADAO-12 §4.1 cfx_umon - user monitor`、`§3.4 cg3 - hypv mode 寄存器`、`§4.7 cfx_hart - hart management`；`DADAO-12 §3.1`/`§3.3`/`§3.6`/`§2.2.6`/`§5.4`/`§4.10`/`§5`/`§5.1`/`§5.2`/`§5.3`；`Kaiwu §4.4`；`ADR-0045 D3`/`D8`/`D9`；`ADR-0056 D2`/`D4`；`ADR-0061 D2/D3/D5/D6`；`contract-syscall §8` |

---

## §7 变更记录（v5 扩展；不改版本号）

- **0.7.3-rc + `cfx5`（cache）由未实现改为 Vast 实现（2026-11-20，`m16-spec-001`）**：§3 的测试机实现范围条目把 `cfx5`（`cache`）从「已分配未实现、按未实现 cfx 处理（`CFXREG`）」改为「`Kaiwu-Vast` 实现其寄存器与维护命令、`Kaiwu-Tiny` 不实现」，寄存器面与命令语义改指 `contract-cache.md`（`DADAO-12 §4.6` 同步重定义 `cache_ctrl` 为选择/操作/范围三维控制字）。版本号仍为 **0.7.3-rc**（上游册 `DADAO-12` 版本未变，`check-spec-drift` 不变量）。[DADAO-12 §4.6 cfx_cache - cache organization][Machine-01 §3.2 cache（cfx5）的测试机约定]
- **0.7.3-rc + 引用落点随册并入（2026-11-17）**：`DADAO-13` 的 cg3 寄存器表与 hmon 说明段正文已并入 `DADAO-12 §3.4 cg3 - hypv mode 寄存器` / `§4.4 cfx_hmon - hypervisor monitor`（`DADAO-13` `§1`/`§2` 只保留引用、章节编号作锚点）；本合约相应把 cg3 与同步原因表的来源指针由 `DADAO-13 §1`/`§2` 改指 `DADAO-12`（hmon 原因表与 `cfx_umon` 同表 ⇒ 引 `§4.1`、子原因仍引 `§3.6`）。条文语义未变，版本号仍为 **0.7.3-rc**（两册版本未变）。[DADAO-12 §3.4 cg3 - hypv mode 寄存器][DADAO-12 §4.4 cfx_hmon - hypervisor monitor]
- **0.7.3-rc + M14 K2 扩展（2026-11-15）**：新增 §6「内核侧异常与中断」——① `excp_cause_info` 的 11 项语义表 + 「本表之外为 0」+ `TIMER` 的 `info = 0`；② `escape` 的返回 cfx 恒为当前 cfx（帧内无 `prev_cfx`，跨 cfx 返回不存在）；③ 异步中断的内核入口 = `cfx_hart` 的 `supv` 行（`cg2 rc10`/`rc8`）、异步帧借走 `global_cfx_intr_mask`；④ 内核 IE 单旋钮 = `cfx_smon_supv_cfx_intr_mask`（`cg2 rc4`），`global_cfx_intr_mask` 只作一次性模式级放行；⑤ 时间口径指针与两处缺口（放行前提、`escape` 后补投）。附录 A 增 §6 一行。版本号仍随 SEE 册 `DADAO-12` 为 **0.7.3-rc**（`check-spec-drift` 不变量：spec-sourced 合约版本 == 上游册版本）。[DADAO-12 §5. 异常进入与异常退出][m14-spec-005]
- **0.7.3-rc + 子原因位（2026-11-16，`m14-spec-007`）**：§6.1 增「子原因」列与 §6.1.1 子原因位表（**wyde2 `[47:32]` 专供 `CFXPERM`**：`[39:32]` 8 位权限原因、`[47:40]` 保留；**wyde3 `[63:48]` 专供 `CFXMEM`**：`[55:48]` 8 位缺失类、`[56] ADWBFAIL`、`[57] NONPTW`、`[63:58]` 保留；`[31:16]` 保留给未来新的大类 cause），与 `DADAO-12 §3.6` 逐位一致；`CFXMEM`/`CFXPERM` 的 `info` 改为**恒为地址**（`CFXPERM` 的 `cfxtrap`/`cfx2rd`/`cfx2rc` 拒绝 = 触发指令地址，与 `excp_cause_ip` 同值）；非页表类 `CFXMEM` 用 `NONPTW`，归属互斥（`CFXPERM`→wyde2、`CFXMEM`→wyde3，另一 wyde 全 0）。版本号仍为 **0.7.3-rc**（上游册版本未变）。[DADAO-12 §3.6 cg5 - 异常现场寄存器][ADR-0056 D2][ADR-0056 D4]
- **0.7.3-rc + IE 旋钮口径收敛（2026-11-16，`m14-linux-010`，用户裁定）**：§6.4 的旋钮改为**当前运行模式 monitor** 的 `<mode>_cfx_intr_mask`——按 `DADAO-12 §5.2` 步骤 3 的字面读法（`cfx_<monitor>_<mode>_cfx_intr_mask`），内核运行在 `supv` ⇒ `cfx_smon cg2 rc4`；**删去**「当前 cfx = `cfx_smon`」这一实例表述（`escape` 不恢复 `inner_cfx_code`，首投后当前 cfx 仍是投递目标，选择依据只有运行模式，`ISS-454`/`ISS-455`）；`global_cfx_intr_mask` 明确为**模式级放行**。附录 A 的 §6 行同步。版本号仍为 **0.7.3-rc**（上游册 `DADAO-12` 版本未变，`check-spec-drift` 不变量）。[DADAO-12 §5.2 异常进入流程][DADAO-12 §5.3 异常退出流程][ADR-0045 D3][ISS-455][ISS-454]
- **0.7.3-rc + `escape` 恢复 `inner_cfx_code`（2026-11-18，`m14-spec-009`，用户裁定 B）**：`cg5 rc1` 由 `reserved` 改为 `excp prev cfx code`（`cfx_⟨cfxname⟩_excp_prev_cfx_code`，RW，初值 0）——`§5.2` 第 5 步硬件陷入时保存 `inner_cfx_code`、`§5.3` 第 2 步 `escape` 恢复；§6.2 第 1 条改为「帧内保存 `excp_prev_cfx_code`、软件不能指定返回 cfx」，§6.4 旋钮条的理由改为「cfx 与运行模式同进退」，附录 A 的 §6 行同步。动机：同步异常帧内投递异步事件后该帧 `escape` 必报 `CFXESC`（`ISS-454` 的 F36）。版本号仍为 **0.7.3-rc**（上游册 `DADAO-12` 版本未变，`check-spec-drift` 不变量）。[DADAO-12 §3.6 cg5 - 异常现场寄存器][DADAO-12 §5.2 异常进入流程][DADAO-12 §5.3 异常退出流程][ADR-0045 D8]
- **§6 内的推导登记**：`cg2 rc10` 写入忽略低 2 位（按 `cg3 rc10` 同构）、异步帧的 `global_cfx_intr_mask` 保存/置全 1（把 `ADR-0045 D9` 的 trap 保护扩到异步帧）、`cg5 rc3` 可写 + 固定偏移的组合效果，三处上游未明文，均标 `[spec-decision]` 并在条文内写清推导链。[spec-decision][ADR-0045 D9][m14-spec-005]
- **追加方式**：此后按「日期 + 改动摘要 + 落点（§）/ 关联 ADR / ISS」追加；上游 spec 正文变更仍走 `docs/Process-02` 的同步流程，本记录只记 v5 扩展口径。[contract-syscall §12]
- **0.7.3-rc + monitor-first 异步口径同步（2026-11-22，用户裁定，`ADR-0059 R2`）**：`spec/DADAO-12 §5.2（三）（四）（五）` 已是 **monitor-first**（异步先入当前运行模式 monitor、mask/pending 都在 monitor、处理期间不嵌套、monitor 可自行处理或 `trap` 到源 cfx），本合约 §3/§6.3/§6.4 原「目标 cfx 直接投递、pending 只记目标 cfx、`TIMER` 进 `cfx_hart` 行」与 spec 不一致，本次**内容对齐**：§3 的「统一异步中断仲裁」「异步边界」「`cfx_pmem` DMA 投递」「`cfx_hart` timer 投递」与 §6.3（异步入口 = monitor 的 `<mode>_excp_vector`、与同步同向量同帧、cause 编号同号不同义）、§6.4（mask 位索引 = 来源 cfxha、pending 归 monitor）改为 monitor-first；**版本号未升**（`check-spec-drift` 不变量：spec-sourced 合约版本 == 上游册版本，内容同步待用户认可后另议）。[DADAO-12 §5. 异常进入与异常退出][ADR-0045 D3/D9][ADR-0042 D7.4]
- **0.7.3-rc + 异步 cause 号改 17/18（2026-11-23，用户裁定）**：异步源 cause 号由 `[15:0]`（`TIMER=1<<10`、`PMEM_DMA=1<<8`）改为**宏 cause 空间 `[31:16]`**（`TIMER=1<<17`、`PMEM_DMA=1<<18`），解决 monitor-first 下与同步 cause（`RASOF=1<<10`、`ILLI=1<<8`）撞号；§3/§6.1/§6.3/§6.4 的 cause 编号同步，删除「待 spec 明文化」悬空句；mask 位索引不变（仍来源 cfxha 15/32）。**版本号未升**（内容同步 17/18，版本号待用户认可）。[DADAO-12 §3.6 cg5 - 异常现场寄存器][DADAO-12 §5.2 异常进入流程]
- **0.8.0-rc + 版本升号（2026-11-23，用户裁定）**：monitor-first 异步投递 + 异步 cause 17/18 为**不兼容语义变更**，`spec/DADAO-12`（SEE）与 `spec/DADAO-22`（SBI）册头版本同升 **0.8.0-rc**（`y+1`；SEE↔SBI 互锁）。本合约版本与来源行、`contract-cache.md`/`contract-tlb.md` 的来源行同步改 `0.8.0-rc`；`spec/.manifests.toml` 的 SEE/SBI 锁哈希同笔重算。[DADAO-12 §5. 异常进入与异常退出][DADAO-12 §3.6 cg5 - 异常现场寄存器]
- **0.8.0-rc + 异步投递改 hart-first / 新增 `cfx_hart cg9` / `escape` 帧选择位（2026-11-23，用户裁定）**：异步投递由「先入当前运行模式 monitor」改为 **hart-first**——所有异步源统一投递 `cfx_hart`（cfxha 15）、入口为其 **supv 单向量**（`cg9 rc6` 向量、`rc7` 固定 supv、`rc0`–`rc4` 现场），现场/五个来源掩码（`rc8`–`rc12`）/pending（`rc5`）全在新增 `cg9`（16 项，`DADAO-12 §4.7 cfx_hart - hart management`）；无嵌套（帧活动期只置 pending）、pending 记 per-hart `cfx_hart` 不迁移、软件可快照/写 0 释放/重建。`escape` 增**帧选择位 `imms18[1]`**（0=`cg5`、1=`cg9`）：合法 `imms18 ∈ {0,1,2}`、`3 ⇒ ILLI`、`imms18[17:2]` SBZ、`cg9` 只允许偏移 0。§3（统一仲裁/异步边界/`cfx_hart` 定时器投递/`cfx_pmem` DMA 投递）、§6.2（帧选择位与帧有效性）、§6.3（异步内核入口）、§6.4（IE 单旋钮 = `cfx_hart cg9 rc11`）同步；monitor 的 `<mode>_cfx_intr_mask`（`cg0`–`cg3 rc4`）与 `global_cfx_intr_mask`（`cg8 rc1`）**异步用途作废**（字段保留、不参与判定）。版本号仍为 **0.8.0-rc**（上游册 `DADAO-12` 版本未变，`check-spec-drift` 不变量）。[DADAO-12 §4.7 cfx_hart - hart management][DADAO-12 §5.1 指令行为说明][DADAO-12 §5.4 异步中断进入与退出][ADR-0060 D0/D1/D2/D3/D4]
- **0.8.0-rc + pending 不随模式切换迁移（2026-11-23，用户裁定）**：§3 的「统一异步中断仲裁」与 §6.4 的「屏蔽只阻止投递」补同一口径——**pending 不随模式切换迁移**：事件到达时记入当时 mode monitor 的 `cg5 rc5`、之后运行模式切换不搬移，只有该 monitor 再次成为当前模式才投递，任务退出时其 pending 丢弃、依赖源重触发。版本不变（已 0.8.0-rc）。[DADAO-12 §5.2 异常进入流程][DADAO-12 §3.6 cg5 - 异常现场寄存器]
- **0.8.0-rc + 异步模型修订：掩码归 monitor、源索引统一 cfxha、`cg9` 精简为 7 槽（2026-11-23，用户裁定）**：异步来源掩码由 `cfx_hart cg9` 改为 `cfx0`–`cfx3` 的 `cg8 rc1`（`cfx_<monitor>_async_intr_mask`，位 = 源 cfxha、`0=允许`/`1=屏蔽`、复位全 1），删除 `cg0`–`cg3 rc4`、`cg9` 的五个来源掩码与 `async_saved_global_intr_mask`；`trap`/`escape` 不再保存/恢复掩码。源身份统一为源 cfxha（`TIMER`=15、`PMEM_DMA`=32），取消宏 cause 17/18，异步不占 `excp_cause_id` 且无 `cause_info`。`cfx_hart cg9` 精简为 7 槽（`rc0`–`rc2` 现场、`rc3 src_frame`、`rc4 src_pending`、`rc5` 向量、`rc6` 固定 supv，`rc7`–`rc15` reserved），两个位图 HW 写/SW 只读；同一指令边界上的多个 pending 且放行的源一次性进入同一帧（位图并集），无嵌套；pending 跟随源事件（投递即清、源 ack 即落、不计数）；合法 `escape` 返回即释放帧。§2/§3/§6.1/§6.2/§6.3/§6.4 同步，版本号仍为 **0.8.0-rc**（上游册版本未变）。[DADAO-12 §4.1 cfx_umon - user monitor][DADAO-12 §4.7 cfx_hart - hart management][DADAO-12 §5.4 异步中断进入与退出][ADR-0061 D2/D3/D5/D6/D7/D8/D9/D10]
