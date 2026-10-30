# SEE/HEE 运行环境合约（M5）

> **版本：0.7.1** [DADAO-12 §1. 运行模式与核芯功能扩展][DADAO-22 §1. 调用约定]
>
> **来源**：`spec/DADAO-12-SEE-主管系统运行环境.md`（0.7.1）、`spec/DADAO-13-HEE-超管系统运行环境.md`（0.1.2）、`spec/DADAO-22-SBI-主管系统二进制接口.md`（0.7.1）、`spec/DADAO-21-ABI-应用程序二进制接口.md`（0.9.2）、`spec/SimRISC-11-其它.md`（0.5.4）；测试机运行环境正文 `spec/Machine-01-测试机运行环境.md`（v5 自定）；决策 `.tao/adr/adr-0020-see-semihosting.md`（`ADR-0020`，Accepted）与 `.tao/adr/adr-0004-test-machine.md`（`ADR-0004`，Accepted，rev. 2026-10-07 `R1`/`R3`）。
>
> **范围**：M5 SEE/HEE 运行环境——运行模式、核内地址空间与复位、cfx 与权限、`trap`/`escape` 与异常进入/退出、SBI 调用约定。semihosting 的服务表/调用约定见 `contract-semihosting.md`。
>
> **来源标注**：每条规范性断言句末以 `[DADAO-NN §章节名]`/`[SimRISC-XX §章节名]` 标注 spec/ 来源；测试机约定标 `[ADR-0020 DN]`/`[ADR-0004 DN]`/`[Machine-01 §N]`；不写行号。
>
> **说明**：本合约由 spec/ 归一化投影而来，面向实现；与 spec/ 冲突时阻断实现，走变更流程（见 `docs/Process-02-合约编写规范.md`）。

---

## §1 运行模式

- DADAO 定义四种运行模式（两位编码）：`user`（`0b00`）、`jail`（`0b01`）、`supv`（`0b10`）、`hypv`（`0b11`）。[DADAO-12 §1. 运行模式与核芯功能扩展]
- `hypv`（超管模式）的 cg3 寄存器定义见 HEE（含 `hypv_switch_run_mode`/`hypv_excp_vector`）。[DADAO-13 §1. cg3 - hypv mode 寄存器]
- `trap`/`escape`/`cfx2rd`/`cfx2rc`/`cfxld`/`cfxst` 可在**任意运行模式**下执行；是否允许由 cfx mask 与指令类型 cfx mask 控制。[SimRISC-11 §指令域与执行条件]
- 异常进入时运行模式/掩码切换为 `cfx_⟨cfxname⟩_<mode>_switch_run_mode` 与 `switch_cfx_mask`（异常进入流程步骤 8）。[DADAO-12 §5. 异常进入与异常退出][DADAO-12 §3. 共有寄存器设计规范]
- v5 测试机只启用 `hypv`/`user`，**本版不启用 `supv`**、不涉及 `smon`。[ADR-0020 D12][ADR-0004 R1][Machine-01 §2]

## §2 核内地址空间与复位

- CPU 地址固定 48 位；高 6 位 `addr[47:42]` 为分区键：`0` 为内存窗口（`ptw_enable` 控制是否翻译），`1..63` 为 cfx 1–63 核内空间；`cfx0` 无内部空间。[DADAO-12 §2.1 核内地址空间][DADAO-12 §2.2 虚实地址转换]
- 内存窗口 VA 为 42 位（`VA[41:0]`），物理地址 PA 为 56 位。[DADAO-12 §2.2 虚实地址转换]
- 单 PTBR `cfx_ptw_ptbr`（只存 `PPN[55:16]`，64 KiB 对齐，无 valid 位）；`cfx_ptw_enable=0` 时 `addr[47:42] = 0` 访存 ⇒ `CFXMEM`，`1` 时按页表转换；写 PTBR/写 1 不隐含 TLB invalidate；复位 PTBR=0、使能=0。[DADAO-12 §2.2 虚实地址转换][DADAO-12 §4.5 cfx_ptw - page table walker]
- 页表项 64 位：`HSJU[63:60]`、`PPN[55:16]`（超页 `PPN[55:29]`）、`SPF/GPF[15:8]`、flags `[7:0]`（`P/SP/D/A/G/X/W/R`）；L1/L2 均 64 KiB、8192 项，`VA[41:29]`/`VA[28:16]` 选索引、`VA[15:0]` 为页内偏移；PA 56 位。保留位忽略、超页 PPN 非对齐低位强制清零。[DADAO-12 §2.2.1 超页的地址转换][DADAO-12 §2.2.2 普通页的地址转换][DADAO-12 §2.2.3 一级页表条目格式][DADAO-12 §2.2.4 二级页表条目格式]
- 页权限：HSJU 要求当前模式对应位为 1，且 R/W/X 与 HSJU 正交（取指 X、读 R、写 W）；异常优先级「页缺失 → SPF/GPF 对应位 = 0 → HSJU → R/W/X」，只报最高优先级异常；页表步进与 TLB 命中产生的异常都进入 `cfx_ptw`。[DADAO-12 §2.2.5 操作系统页管理][DADAO-12 §2.2.6 异常检查优先级]
- **TLB（并入 `cfx_ptw`）**：无 `tlb_enable`/`tlb_exist`，`ptw_enable=1` 即参与查找、`0` 时旁路；按「虚拟页 + ASID（`cfx_ptw_tlb_asid`，16 位）」匹配，`G=1` 跨 ASID 复用；命中不重读 PTE，miss 走页表步进且只有成功才填充；写 PTBR/ASID/使能都不隐含失效。[DADAO-12 §2.2.1 超页的地址转换][DADAO-12 §4.5 cfx_ptw - page table walker][ADR-0041 D3/D5/D8/D9]
- **TLB 失效**：`cfx_ptw_tlb_control` 三维正交——`op`（`00=none`/`01=clean`/`10=invalid`/`11=flush`）、`scope`（`00=all`/`01=VA`/`10=range`/`11=reserved`）、`ASID_ANY`（bit4）；`all` 忽略 start/size、`VA` 只看 start、`range` 用 `[start,start+size)`；`scope=11` 或 `range` 且 `size=0` ⇒ `CFXREG`（仅 `clean`/`invalid`/`flush`；`op=none` 优先按 no-op）；`ASID_ANY=1` 含 `G`、`0` 跳过 `G`；正常完成不报异常。[DADAO-12 §4.5 cfx_ptw - page table walker][ADR-0041 D3.1/D3.2/D6]
- **A/D**：填充取 PTE 的 A/D 为本地值、不产生回写；读/取指置 A，写置 A/D；缺页/权限失败不更新；`clean`/`flush`/替换时原子 OR 回写 PTE（`clean` 保留、`flush` 删除、`invalid` 不写回）；回写失败报 `PTWERR`（`1 << 7`，`cause_info` = PTE 物理地址）且保留条目。[DADAO-12 §2.2.5 操作系统页管理][DADAO-12 §4.5 cfx_ptw - page table walker][ADR-0041 D4/D7/D10]
- 硬件复位启动地址 = `cfx_power_hypv_excp_vector = 0xffff_ffff_0000`（cfxha 63 / `power`，64 KiB），可由 CPU 直接取指执行。[DADAO-12 §2.1 核内地址空间]
- v5 测试机地址划分（RAM@0 / 旧 RAM 段过渡保留 / exit port 过渡保留 / boot ROM）为**测试机约定**；RAM 基址改全 0，复位向量/ROM 与 exit port 不变。[ADR-0020 D15][ADR-0004 R3][Machine-01 §1]
- 核内地址空间非法访问触发对应 cfx 的 `CFXMEM`（`1<<1`）；测试机退出码 = `0x80 | 1 = 0x81`；保留 cfx（6–14、19–61）的普通 `ld/st` 也触发 `CFXMEM`；`0x87`（unmapped）为测试机约定、无 spec cause。[DADAO-12 §2.1 核内地址空间][DADAO-12 §4. 专有寄存器设计规范][ADR-0004 D5.8]
- 越界**取指**与越界数据访问**同等报异常**，不得静默；fault 码表冻结不重排。[ADR-0020 D15][ADR-0004 D5.8]
- **`cfx_pmem` SRAM 与 DMA**：`cfx_pmem`（cfxha 17）内含 64 KiB SRAM（内部偏移 0x3ff_0000_0000，核内起始 `0x47ff_0000_0000`），CPU 用普通 `ld/st` 访问、越界 ⇒ `CFXMEM`；DMA 只在 SRAM ↔ PA 间搬运，`cg15` 寄存器为 `dma_src`/`dma_dst`/`dma_size`/`dma_ctrl`/`dma_status`；CFX 侧取低 42 位、PA 侧取低 56 位（高位忽略），`size` 30 位、合法 `1..2^29`。[DADAO-12 §2.1 核内地址空间][DADAO-12 §4.9 cfx_pmem - physical memory management][ADR-0042 D3/D6/D7.1–D7.3]
- **`cfx_pmem` DMA 控制/状态**：`dma_ctrl` bit0 `START`（自清）/bit1 `DIR`（0=CFX→PA，1=PA→CFX）/bit2 `IRQ_EN`；`dma_status` bit0 `BUSY`、bit1 `DONE`（W1C）、bit2 `ERROR`（W1C，同时清 `ERR_CODE`）、bit3–15 `ERR_CODE`（one-hot：`SIZE`/`CFX_RANGE`/`PA_RANGE`/`PA_FAULT`）；`BUSY=1` 时 cg15 写与 DONE/ERROR W1C 被忽略；`PMEM_DMA`（`1 << 8`）异步可屏蔽，`IRQ_EN=1` 时 DONE/ERROR 触发、`cause_info` = `dma_status`，被屏蔽时置 `cfx_pmem_excp_pending`；单 hart 直接投递 `cfx_pmem`。[DADAO-12 §4.9 cfx_pmem - physical memory management][ADR-0042 D7.2/D7.4]

## §3 cfx 与权限

- 每个 cfx 提供 cg0–cg7 共有寄存器（含 `global_cfx_mask`、指令类型 mask、`switch_run_mode`、`switch_cfx_mask`、`excp_vector`、`excp_cause_mask`）。[DADAO-12 §3. 共有寄存器设计规范]
- mask 语义：0=可触发，1=屏蔽；自身 cfxha 对应位由硬件忽略。[DADAO-12 §3. 共有寄存器设计规范]
- reserved cfxha（`6`–`14`、`19`–`61`）触发 `ILLI`；cfxha 合法但指令 cfx mask 禁止亦触发 `ILLI`。[DADAO-12 §5. 异常进入与异常退出]
- 访问**未实现**的核芯功能扩展（其 cfx 寄存器）触发 `CFXREG`。[DADAO-22 §3. 系统信息（smon）]
- `NUPERM`/`NJPERM`/`NSPERM`/`NHPERM` 属于页级/PTW 权限异常：当前运行模式对应的 HSJU 位为 0 时触发（U/J/S/H 分别对应 `NUPERM`/`NJPERM`/`NSPERM`/`NHPERM`）；地址转换第一步不再按 `VA[47:42]` 选择 PTBR，也无 PTBR 模式权限位图。[DADAO-12 §2.2.5 操作系统页管理][DADAO-12 §4.5 cfx_ptw - page table walker]
- **两层权限不可混同**：PTW 层权限（`NUPERM` 等，出自 cfx_ptw 异常原因表）与 cfx 访问权限（cfx mask 不允许 ⇒ `ILLI`）分属不同层次。[ADR-0020 D9][DADAO-12 §4. 专有寄存器设计规范]
- v5 测试机 cfx 实现范围 = `cfx0/1/2/3/63` 以及 `cfx4` 的 PTW/TLB 寄存器（`cfx_ptw_ptbr`/`cfx_ptw_enable`/`cfx_ptw_tlb_*`）、页表步进、TLB 命中/填充/失效与 A/D 回写，加上 `cfx17` 的 64 KiB SRAM 与 `cg15` DMA，属**测试机约定**、非上游架构限制；`cfx5`（`cache`）已分配未实现、按未实现 cfx 处理（`CFXREG`）；范围外未实现 cfx 触发 `CFXREG`。[ADR-0020 D9][Machine-01 §3]

## §4 `trap`/`escape` 与异常进入/退出

- `trap cfxha, immu18`：`cfxha` 为服务提供者、`immu18` 为功能编号。[DADAO-22 §1. 调用约定]
- 一般 trap（`immu18 < 0x3FF00`）走 `DADAO-12 §5` 异常进入流程步骤 1–10，进入目标 cfx 异常向量。[DADAO-12 §5. 异常进入与异常退出][ADR-0020 D10]
- `escape cfxha, [excp_cause_ip, imms20]` 完成异常退出；编码层 `imms18`，`Addr = excp_cause_ip + (imms18 << 2)`，`imms20` 须 `%4==0`。[DADAO-12 §异常退出流程][SimRISC-11 §退出指令]
- 被调方经 `escape cfxha, [excp_cause_ip, 4]` 返回 trap 下一条指令。[DADAO-22 §1. 调用约定]
- **两条路分离**：semihosting（`immu18[17:8] == 0x3FF`，即 `0x3FF00–0x3FFFF`）经实现层短路、不进入向量、IP 步进返回，见 `contract-semihosting.md`；不得混入向量路径。[ADR-0020 D10][Machine-01 §4]

## §5 SBI 调用约定

- 调用方 `trap cfxha, immu18` 陷入目标 cfx；被调方经 `escape cfxha, [excp_cause_ip, 4]` 返回。[DADAO-22 §1. 调用约定]
- 参数传递与 ABI 传参规范一致（参见 `contract-abi.md`）。[DADAO-22 §1. 调用约定][DADAO-21 §传参：Parameter Passing]
- 参数寄存器：`rd16–rd31`（数据）、`rb16–rb31`（地址）、`rf16–rf31`（浮点）；三组独立计数、从 16 起递增。[DADAO-21 §参数寄存器：Parameter registers]
- 标量返回值用 `rd8`；指针返回值用 `rb8`。[DADAO-21 §标量类型返回值：Scalar type return]
- 系统调用号存于 `rd15`，与 `immu18` 为两个独立层次。[DADAO-21 §系统调用规范]
- 错误码：`0 = SBI_SUCCESS`、`−1 = SBI_ERR_FAILED`、`−2 = SBI_ERR_NOT_SUPPORTED`、`−3 = SBI_ERR_INVALID_PARAM`、`−4 = SBI_ERR_NO_DEVICE`。[DADAO-22 §1. 调用约定]

---

## 附录 A：来源对照

| 本合约 § | 内容 | spec/ 来源 |
|----------|------|-----------|
| §1 | 运行模式（四模式）、任意模式执行核芯功能扩展指令、switch_run_mode | `DADAO-12 §1. 运行模式与核芯功能扩展`、`§5. 异常进入与异常退出`；`DADAO-13 §1. cg3 - hypv mode 寄存器`；`SimRISC-11 §指令域与执行条件` |
| §2 | 核内地址空间 / 复位向量 / CFXMEM / cfx_pmem SRAM+DMA / 测试机划分 | `DADAO-12 §2.1 核内地址空间`、`§4. 专有寄存器设计规范`、`§4.9 cfx_pmem - physical memory management`；`ADR-0020 D15`、`ADR-0004 D5.8`/`R3`；`ADR-0042 D3/D6/D7` |
| §3 | cfx 共有寄存器 / mask / PERM 层次 / 未实现 cfx | `DADAO-12 §3. 共有寄存器设计规范`、`§5. 异常进入与异常退出`、`§2.2.1 超页的地址转换`、`§2.2.2 普通页的地址转换`；`DADAO-22 §3. 系统信息（smon）`；`ADR-0020 D9` |
| §4 | trap/escape 路由、异常进入/退出 | `DADAO-12 §5. 异常进入与异常退出`、`§异常退出流程`；`DADAO-22 §1. 调用约定`；`SimRISC-11 §退出指令`；`ADR-0020 D10` |
| §5 | SBI 调用约定、参数/返回寄存器、错误码 | `DADAO-22 §1. 调用约定`；`DADAO-21 §参数寄存器：Parameter registers`、`§标量类型返回值：Scalar type return`、`§系统调用规范` |
