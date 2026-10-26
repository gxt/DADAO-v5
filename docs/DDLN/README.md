# Dadao Lecture Notes (DDLN)

面向本科课程的 DADAO 讲义（lecnotes）。

## 指令系统

| 篇目 | 内容 |
| --- | --- |
| `A001` 指令系统--设计理念 | **设计理念 TAO**：设计顺序与 DRY；指令系统设计（8/6/6/6/6、取消 CZSO、立即数赋值、多寄存器、条件赋值）；寄存器设计（分组、RB、RAS、rf0）。 |
| `A002` 指令系统--指令编码 | **指令编码**：32 位定长、`8/6/6/6/6`、12 种操作数格式、`opc`/`opx`、立即数拼接、位宽子表、ILLI/UNDI、伪指令。 |
| `A003` 指令系统--寄存器设计 | **寄存器设计**：`rd`/`rb`/`rf`/`ra` 四组 × 64 个；RD/RB 分离；0 号寄存器；`rd0` 只读、`rb0` = IP；多寄存器块复制。 |
| `A004` 指令系统--条件判断 | **条件判断**：CZSO 的动机与代价；六种条件 N/NN/Z/NZ/P/NP；`br.eq`/`br.ne`；`cmp` 的 -1/0/1；`cs.*` 与 `cmovcc`。 |
| `A005` 指令系统--立即数处理 | **立即数处理**：分片拼接 vs 常量池；`rwii` 的 16 位片 + wyde-position；`set.*` 伪指令；不同寄存器组的变体。 |
| `A006` 指令系统--访存与地址运算 | **访存与地址运算**：48 位地址；RB 高 16 位溢出标记；`add.o`/`sub.o`/`aip`；load 符号/零扩展；`ldm`/`stm`；对齐；大端序。 |
| `A007` 指令系统--整数运算 | **整数运算**：`.s`/`.u` 与双目的 128 位；8/16/32 位值语义；`cmp` 三值；乘除；除零/溢出定值；`add.si`。 |
| `A008` 指令系统--位操作 | **位操作**：`and.o`/`or.o`/`xor.o`/`xnor.o`；`shl`/`shr`/`rol`；`rev`；`ctlz`/`cttz`/`ctpop`；`clmul.o`；`ext`。 |
| `A009` 指令系统--浮点运算 | **浮点运算**：IEEE 754 状态位；min/max；FMA；`rf0`（qNaN + FCSR）；格式转换；比较/分类；除零。 |
| `A010` 指令系统--控制流 | **控制流**：相对分支；`br.eq`/`br.ne`；六种条件；`jump`/`call`；RAS（RegRAS + MemRAS）；`ra0`；`ret`。 |
| `A011` 指令系统--原子操作 | **原子操作**：LR/SC；acquire/release 后缀；`sc` 0/1；`fence` pred/succ；保留粒度；对齐；保留清除。 |

## 资源管理

| 篇目 | 内容 |
| --- | --- |
| `C001` 资源管理--核芯功能扩展 | **核芯功能扩展**：资源即 cfx 而非 MMIO；`cfxha` 6 位编号（monitor、地址转换、存储、时间、设备分区）；`trap`/`escape`/`cfx2rd`/`cfx2rc`；`CFXMEM`/`CFXREG`/`ILLI` 三种错误；测试机实现 `cfx0/1/2/3/63`。 |
| `C002` 资源管理--异常与cfx切换 | **异常与 cfx 切换**：进入保存 prev mode/mask、切 `switch_*`、跳 cfx 向量；`escape` 按 `excp_cause_ip + (imms18 << 2)` 返回；`excp_pending` 的 OR 语义与写 0 清；`nonmaskable`；`ILLI`/`PERM` 两层权限；多 hart 隔离。 |
| `C003` 资源管理--cfx寄存器模型 | **cfx 寄存器模型**：`cg`/`rc` 两级编号；`cg0`–`cg7` 通用（version、mask、switch、vector、exception、scratch、SRAM）、`cg8`+ 专有；scratch 2–64 个；只能用 `cfx2rd`/`cfx2rc`，且只连 `rd`。 |
| `C004` 资源管理--cfx存储模型 | **cfx 存储模型**：`cfxld`/`cfxst` 在 cfx 内部 SRAM 与内存间传块；64 B 对齐、长度 `immu12 × 64`；`block_sel` + `sram_addr` 定位；当前 deferred（未实现即 `ILLI`）；无 descriptor/中断，不是 DMA。 |
| `C005` 资源管理--运行模式与资源委派 | **运行模式与资源委派**：`user`/`jail`/`supv`/`hypv`；`jail` 为受限用户态、独立 `jmon`；`hypv` 用 `cg3`；`hypv_cg_reg_deleg` 位图（bit=0 放行 supv、bit3 固定 1）；委派与 cfx mask 两层闸门；嵌套时 `hmon`/`smon` 分工。 |
| `C006` 资源管理--存储层次 | **存储层次**：`cache`（invalid I/D、flush D）、`llc`（跨 hart 共享、invalid all）、`pmem`（最多 64 个不连续 DRAM 区域，`start`/`size`/`attr`）；device 不算 `pmem`；`prefetchable`/`coherent`；改页表 → 清 TLB → 清 cache 的次序。 |
| `C007` 资源管理--虚实地址转换 | **虚实地址转换**：48 位 VA = 6 位 PTBR + 13 位 L1 + 13 位 L2 + 16 位页内；64 个 PTBR、两级 64 KiB 页表；`ptw` 管页表/权限、`tlb` 管翻译缓存与维护；超页 L1 `SP=1`、512 MiB 对齐；TLB 异常是 `ptw` 原因子集。 |
| `C008` 资源管理--时钟与计数 | **时钟与计数**：`timer` cfx（`timer_ctrl` 的 enable/mode/dir + 8 个计数器，one-shot/periodic，增/减计数）；`hart` cfx（`hart_id`、cycle、insn，per-hart）；多 hart 共同 timebase 与中断路由。 |
| `C009` 资源管理--外部设备 | **外部设备**：`uart` cfx（`uart_exist`、32 组 × 64 个寄存器）；`power` cfx（关机/硬复位/软复位）；设备存储不走 `pmem`、由设备 cfx 管理；设备中断置 pending 后按 cfx 路由。 |

## 运行平台

| 篇目 | 内容 |
| --- | --- |
| `D001` 运行平台--平台与载体 | **平台与载体**：运行环境（裸机 / 用户态 / 完整系统）× 载体（功能模拟器 / RTL / FPGA / ASIC）× 粒度（功能 / 周期 / 性能）；按验收目标（语义 / ABI / 系统 / 时序）选择；各环境的库、链接与宿主接口。 |
| `D002` 运行平台--测试机运行环境 | **测试机运行环境**：48 位核内地址高 6 位选 `cfxha`；单段 16 MiB RAM @ `0xFC00_0000_0000`；复位向量 `0xffff_ffff_0000`；`CFXMEM` 与 `unmapped` 的分工；只启用 hypv/user、实现 `cfx0/1/2/3/63`；global mask 与 switch mask；semihosting（`immu18[17:8] == 0x3FF`，`0x3FF00–0x3FFFF`；`SYS_EXIT`）与一般 trap（`< 0x3FF00`）两条路径。 |

## 发展历程

| 篇目 | 内容 |
| --- | --- |
| `Z001` 发展历程--古法编程 | **DADAO 的发展历程**：0.1（2021）→ 0.2（2022）→ 0.3（2023）→ 0.4（2023）→ 202406 各版本更新；含本科毕设与课程致谢。 |
| `Z002` 发展历程--用AI编程-v4 | **DADAO-0628**：用 AI Agent 从零实现软件栈；四路 ISA 验证链；与前身 `gxt/DADAO` 的关系。贡献者：隋岩。 |
| `Z003` 发展历程--用AI编程-v5 | **DADAO-v5**：用 AI Agent 从零实现软件栈的里程碑（M1–M9）。 |
