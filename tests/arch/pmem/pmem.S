@@ pmem.S — `cfx_pmem`（cfxha 32）RTL 探针（`m16-chipyard-022`）
@@
@@ 目的：在 **Kaiwu-Vast RTL（chipyard `WumingVastConfig`）** 上验证
@@ `spec/DADAO-12 §4.9` 的 cfx_pmem 寄存器面、DMA 与 `PMEM_DMA` 完成投递：
@@   * `cg8 rc0 pmem_exist`（RO）、`cg12/13/14 rc0..63`（start/size/attr，RW）；
@@   * `cg15 rc0..4`：`dma_src`/`dma_dst`/`dma_size`（30 位）/`dma_ctrl`
@@     （START 自清、DIR 读回、bit2 保留读 0）/`dma_status`（BUSY、DONE/ERROR W1C、
@@     ERR_CODE one-hot）；BUSY 期 cg15 写被忽略；
@@   * `cfx_pmem cg16 rc16/17/18`：源 mask / pending（RO）/ ack（W1C），
@@     子事件合并 bit0 = 「传输结束（DONE 或 ERROR）」（`ADR-0064` D2/D3）；
@@   * DMA 逐字节搬运（CFX→PA、PA→CFX、非对齐部分拍保留邻居字节）与四类
@@     setup 错误（SIZE/CFX_RANGE/PA_RANGE/PA_FAULT）、只读 BootROM 可读不可写；
@@   * 完成事件：源 `cfx_pmem cg16 rc17` bit0 置位；`cfx_hart cg15 rc5` 是原始
@@     pending 汇总（bit32）；**进入不清 pending**，只有 `cg16 rc18` ack 才清；
@@     同一界 timer(15)+DMA(32) 一次进入、位图并集、`excp_async_num` 每次 +1；
@@   * 源 ack：`cfx_pmem cg16 rc18` W1C 后 pending 落，解除掩码不产生遗留进入；
@@   * 覆盖语义：进入后再触发 ⇒ 下一次进入整体覆盖 `cg15`；
@@   * `escape imms18 = 2` ⇒ 当前 cfx 的 `CFXESC` 且 `cg15` 不变；
@@   * H/S/U 三模式下掩码各写**当前运行模式** monitor 的 `cg15 rc3`
@@     （`--defsym TMODE=3/2/0`），异步进入目标都是 cfx_hart/supv。
@@
@@ S/U 变体的 DMA 在 hypv 里先启动（长传输），进入 U/S 后完成 ⇒ 完成事件落在
@@ 目标运行模式；U/S 体只写自己的掩码行并观察 `cfx_hart cg15`（两轴判权下 U/S
@@ 不能访问非 monitor 的 cfx_pmem，这是既有 `m16-chipyard-020` 口径）。
@@
@@ 期望值见 `check_pmem.py`（现场从 `spec/DADAO-12 §1/§3.6/§4.9/§5.1/§5.4`、
@@ `spec/Kaiwu §1.1/§3`、`.tao/adr/adr-0064-*.md`、`contract-see` §3/§6.1 与
@@ `contracts/opcodes.yaml` 派生；`pmem_exist` 的读回值是测试机约定
@@ 「64 个 PM 区域全部存在」，见 README）。
@@
@@ 只在 `WumingVastConfig` 上跑（Tiny 无 cfx32）。
@@
@@ 寄存器约定：探针体用 rd5–rd7、rb1–rb3、rb5；handler 用 rd5/rd21–rd23、
@@ rb3/rb4；rb30 = 签名写指针（任何处理器都不得写）；rd16/rb16 = semihosting。

	.include "tests/shared/asm/signature.inc"
	.include "tests/shared/asm/perm_hypv.inc"

	.equ	ENTRY,   0xffffff010100
	.equ	SIG_BUF, 0xffffff015000
	.equ	SIG_N,   96
	.equ	EXITB,   0xffffff015800

	.ifndef	TMODE
	.equ	TMODE, 3
	.endif

	.if TMODE == 3
	.equ	SIG_SLOTS, 87
	.else
	.equ	SIG_SLOTS, 9
	.endif

	@@ cfx_pmem SRAM（`spec/Kaiwu §1.1`：(cfxha 32 << 42) | 0x3ff_0000_0000）
	.equ	PMEM_SRAM, 0x83ff00000000
	@@ PA 目标（PA RAM `[0, 2 GiB)`）
	.equ	PA_A, 0x1000
	.equ	PA_B, 0x2000
	.equ	PA_C, 0x3000
	.equ	PA_D, 0x8000
	.equ	PA_E, 0x4000
	@@ BootROM（只读）
	.equ	ROM_BASE, 0xffffffc00000

	@@ dma_ctrl / dma_status 位（`DADAO-12 §4.9`）
	.equ	CTRL_START, 1
	.equ	CTRL_DIR, 2
	.equ	ST_BUSY, 1
	.equ	ST_DONE, 2
	.equ	ST_ERROR, 4

	.equ	PATTERN64, 0x0123456789ABCDEF
	.equ	PATTERN2, 0xFEDCBA9876543210
	.equ	PARTIAL,  0xAABBCC0000000000
	.equ	PARTIALP, 0xAABBCC5A00000000

	@@ 源位图 = 源 cfxha：TIMER = 15、PMEM_DMA = 32（`ADR-0064` D2）
	.equ	PMEM_BIT,  0x0000000100000000
	.equ	MASK_ALLOW_PMEM, 0xFFFFFFFEFFFFFFFF
	.equ	MASK_ALLOW_BOTH, 0xFFFFFFFEFFFF7FFF
	.equ	ESC_IMM3, (0x7E000000 | (15 << 18) | 3)
	.equ	ESC_IMM4, (0x7E000000 | (15 << 18) | 4)

@@ ---------------------------------------------------------------------------
@@ 文件专用宏
@@ ---------------------------------------------------------------------------
.macro REC reg
	st.o	\reg, [rb30, 0]
	add.si	rb30, 8
.endm

.macro WCFX_IMM ha, cg, rc, imm
	set.rd	rd6, \imm
	cfx2rc	\ha, \cg, \rc, rd6
.endm
.macro WCFX_LABEL ha, cg, rc, lab
	set.rb	rb2, \lab
	rb2rd	rd6, rb2, 1
	cfx2rc	\ha, \cg, \rc, rd6
.endm

@@ cfx_pmem cg15 寄存器读写
.macro PMW rc, imm
	set.rd	rd6, \imm
	cfx2rc	cfx_pmem, cg15, rc\rc, rd6
.endm
.macro PMR rc, reg
	cfx2rd	cfx_pmem, cg15, rc\rc, \reg
.endm

@@ 只填 src/dst/size，不启动（START 由 DMA_GO 单独写）
.macro DMA_SETUP_CFX src_off, pa, size
	set.rd	rd6, (PMEM_SRAM + \src_off)
	cfx2rc	cfx_pmem, cg15, rc0, rd6
	set.rd	rd6, \pa
	cfx2rc	cfx_pmem, cg15, rc1, rd6
	set.rd	rd6, \size
	cfx2rc	cfx_pmem, cg15, rc2, rd6
.endm
.macro DMA_SETUP_PA pa, dst_off, size
	set.rd	rd6, \pa
	cfx2rc	cfx_pmem, cg15, rc0, rd6
	set.rd	rd6, (PMEM_SRAM + \dst_off)
	cfx2rc	cfx_pmem, cg15, rc1, rd6
	set.rd	rd6, \size
	cfx2rc	cfx_pmem, cg15, rc2, rd6
.endm
.macro DMA_GO flags
	PMW	3, \flags
.endm

@@ 等 DMA 完成（BUSY = 0）
.macro POLL_BUSY
__poll_\@:
	PMR	4, rd5
	set.rd	rd6, ST_BUSY
	and.o	rd5, rd5, rd6
	br.nz	{rd5}?, [rb0, __poll_\@]
.endm

@@ 等 pending 的源位出现（DMA 完成在另一运行模式下发生时用）
.macro POLL_PENDING bit
__pollp_\@:
	cfx2rd	cfx_hart, cg15, rc5, rd5
	set.rd	rd6, \bit
	and.o	rd5, rd5, rd6
	br.z	{rd5}?, [rb0, __pollp_\@]
.endm

@@ R3 `escape cfxHA`：返回点由软件写 `cg5 rc10`（prev ip + 4）
.macro ESCAPE_SKIP4 cfx
	cfx2rd	\cfx, cg5, rc2, rd6
	add.si	rd6, 4
	cfx2rc	\cfx, cg5, rc10, rd6
	escape	\cfx
.endm

.macro EXIT code
	set.rb	rb16, EXITB
	set.rd	rd4, 0x20026
	st.o	rd4, [rb16, 0]
	set.rd	rd4, \code
	st.o	rd4, [rb16, 8]
	set.zw	rd16, wp0, 0x18
	trap	cfx0, 0x3FF18
	swym	0
.endm

.macro DUMP_AND_EXIT code
	set.rb	rb1, sig_bytes
	ld.o	rd17, [rb1, 0]
	set.rb	rb16, SIG_BUF
	set.zw	rd16, wp0, 0x03
__dump_\@:
	trap	cfx0, 0x3FF03
	add.si	rb16, 1
	add.si	rd17, -1
	br.nz	{rd17}?, [rb0, __dump_\@]
	EXIT	\code
.endm

.macro BURN rd, rb
	set.rd	\rd, 300
__burn_\@:
	add.si	\rb, 1
	add.si	\rd, -1
	br.nz	{\rd}?, [rb0, __burn_\@]
.endm

@@ ---------------------------------------------------------------------------
@@ 入口：cfx_power + hypv（`spec/Kaiwu §6.2` 固定 BootROM 移交）
@@ ---------------------------------------------------------------------------
	.text
	.globl	_start
_start:
	SIG_BEGIN SIG_BUF, SIG_N
	@@ 测试侧两轴放行（`DIV-07` 关闭后 hypv 也判权；body 以 cfx_power 交付）
	PERM_MON_OPEN perm_mon
	set.rb	rb1, phase
	set.rd	rd6, 0
	st.o	rd6, [rb1, 0]

	@@ ---- 共用初始化（hypv：两轴判权不生效） ----
	WCFX_LABEL cfx_hart, cg15, rc5, async_entry
	WCFX_LABEL cfx_hart, cg2, rc10, esc9_entry
	@@ cfx_pmem：U/S 行的源位清 0（0 = 允许），deleg 放开 cg8/cg12..15；
	@@ supv 行还须清 bit15（supv handler 以 cfx_hart 身份访问 cfx_pmem）。
	WCFX_IMM cfx_pmem, cg0, rc2, 0xFFFFFFFFFFFFFFFE	@@ U: 允许 cfx_umon
	WCFX_IMM cfx_pmem, cg1, rc2, 0xFFFFFFFFFFFFFFFA	@@ J: 保留位（cfx1/jmon 未实现，不纳入本机）
	WCFX_IMM cfx_pmem, cg2, rc2, 0xFFFFFFFFFFFF7FFA	@@ S: 允许 cfx_smon / cfx_hart
	WCFX_IMM cfx_pmem, cg3, rc12, 0xFFFFFFFFFFFF0EF7	@@ deleg: cg8/cg12-15
	@@ cfx_hart：U/S 行允许 umon/smon/hart 源；deleg 放开 cg4/5/8/9
	WCFX_IMM cfx_hart, cg0, rc2, 0xFFFFFFFFFFFFFFF8
	WCFX_IMM cfx_hart, cg1, rc2, 0xFFFFFFFFFFFFFFF8
	WCFX_IMM cfx_hart, cg2, rc2, 0xFFFFFFFFFFFFFFF8
	WCFX_IMM cfx_hart, cg3, rc12, 0xFFFFFFFFFFFF7FCF
	@@ cfx_smon：supv handler 以 cfx_hart 身份写它的掩码行
	WCFX_IMM cfx_smon, cg2, rc2, 0xFFFFFFFFFFFF7FFB
	WCFX_IMM cfx_smon, cg3, rc12, 0xFFFFFFFFFFFFFCF7
	WCFX_LABEL cfx_smon, cg3, rc10, smon_fault
	@@ 兜底：U/S 下的意外同步异常分别进 umon 的 user 行 / smon 的 supv 行
	WCFX_LABEL cfx_umon, cg0, rc10, smon_fault
	WCFX_LABEL cfx_smon, cg2, rc10, smon_fault
	@@ timer 关；两个源的 mask 放开（复位全 1），并 ack 启动链遗留的 pending
	WCFX_IMM cfx_hart, cg16, rc1, 0xFFFFFFFFFFFFFFFF
	WCFX_IMM cfx_hart, cg16, rc0, 0
	WCFX_IMM cfx_hart, cg16, rc16, 0
	WCFX_IMM cfx_pmem, cg16, rc16, 0
	WCFX_IMM cfx_pmem, cg16, rc18, 1

	.if TMODE == 3
	jump	[rb0, setup_h]
	.elseif TMODE == 2
	jump	[rb0, setup_s]
	.else
	jump	[rb0, setup_u]
	.endif

@@ ---------------------------------------------------------------------------
@@ H（hmon + hypv）：寄存器面 + DMA + 捕获/多源/覆盖
@@ ---------------------------------------------------------------------------
setup_h:
	set.rb	rb1, sig_bytes
	set.rd	rd6, 87*8
	st.o	rd6, [rb1, 0]
	@@ 首次 trap 的入口 = h_trap_entry（CFXTRAP），随后把向量切到 h_fault
	WCFX_LABEL cfx_hmon, cg3, rc10, h_trap_entry
	WCFX_IMM cfx_hmon, cg3, rc14, 3
	trap	cfx_hmon, 0
	swym	0

h_trap_entry:
	WCFX_LABEL cfx_hmon, cg3, rc10, h_fault
	jump	[rb0, h_body]

h_fault:
	@@ 记录 cause_id / cause_info，然后 escape +4 跳过故障指令
	cfx2rd	cfx_hmon, cg5, rc2, rd5
	REC	rd5
	cfx2rd	cfx_hmon, cg5, rc4, rd5
	REC	rd5
	ESCAPE_SKIP4 cfx_hmon
	swym	0

h_body:
	@@ ---- 0 pmem_exist（RO，测试机：64 个 PM 区域全部存在） ----
	cfx2rd	cfx_pmem, cg8, rc0, rd5
	REC	rd5
	@@ ---- 1-3 写 pmem_exist（RO）⇒ CFXREG（cause/info + 见证） ----
	WCFX_IMM cfx_pmem, cg8, rc0, 0
	set.rd	rd5, 0xC0DE0001
	REC	rd5

	@@ ---- 4/5 pmem_start[0]/[63] RW ----
	WCFX_IMM cfx_pmem, cg12, rc0, PATTERN64
	cfx2rd	cfx_pmem, cg12, rc0, rd5
	REC	rd5
	WCFX_IMM cfx_pmem, cg12, rc63, PATTERN2
	cfx2rd	cfx_pmem, cg12, rc63, rd5
	REC	rd5
	@@ ---- 6/7 pmem_size[0] / pmem_attr[63] RW ----
	WCFX_IMM cfx_pmem, cg13, rc0, PATTERN64
	cfx2rd	cfx_pmem, cg13, rc0, rd5
	REC	rd5
	WCFX_IMM cfx_pmem, cg14, rc63, PATTERN2
	cfx2rd	cfx_pmem, cg14, rc63, rd5
	REC	rd5
	@@ ---- 8/9 dma_src / dma_dst RW ----
	PMW	0, PATTERN64
	PMR	0, rd5
	REC	rd5
	PMW	1, PATTERN2
	PMR	1, rd5
	REC	rd5
	@@ ---- 10 dma_size 30 位字段（写全 1 读回 0x3FFFFFFF） ----
	PMW	2, 0xFFFFFFFFFFFFFFFF
	PMR	2, rd5
	REC	rd5
	@@ ---- 11 dma_ctrl：写 START|DIR，START 自清、DIR 读回、bit2 保留读 0 ----
	PMW	3, (CTRL_START | CTRL_DIR | 4)
	PMR	3, rd5
	REC	rd5
	@@ ---- 12-14 读 cg15 rc5（保留）⇒ CFXREG ----
	PMR	5, rd5
	set.rd	rd5, 0xC0DE0002
	REC	rd5
	@@ ---- 15-17 读 cg15 rc63（保留）⇒ CFXREG ----
	PMR	63, rd5
	set.rd	rd5, 0xC0DE0003
	REC	rd5
	@@ ---- 18-20 读 cfx_pmem cg8 rc1（保留）⇒ CFXREG ----
	cfx2rd	cfx_pmem, cg8, rc1, rd5
	set.rd	rd5, 0xC0DE0004
	REC	rd5

	@@ =====================================================================
	@@ DMA 功能：逐字节搬运
	@@ =====================================================================
	PMW	4, (ST_DONE | ST_ERROR)
	@@ SRAM[0x100] = PATTERN64；8 字节 CFX->PA_A，再 PA_A->SRAM[0x200]
	set.rb	rb3, (PMEM_SRAM + 0x100)
	set.rd	rd7, PATTERN64
	st.o	rd7, [rb3, 0]
	DMA_SETUP_CFX 0x100, PA_A, 8
	DMA_GO CTRL_START
	POLL_BUSY
	PMR	4, rd5
	REC	rd5				@@ 21 DONE
	DMA_SETUP_PA PA_A, 0x200, 8
	DMA_GO (CTRL_START | CTRL_DIR)
	POLL_BUSY
	set.rb	rb3, (PMEM_SRAM + 0x200)
	ld.o	rd5, [rb3, 0]
	REC	rd5				@@ 22 PATTERN64

	@@ 4 个字（32 字节）往返
	set.rb	rb3, (PMEM_SRAM + 0x400)
	set.rd	rd7, 0x1111111111111111
	st.o	rd7, [rb3, 0]
	set.rd	rd7, 0x2222222222222222
	st.o	rd7, [rb3, 8]
	set.rd	rd7, 0x3333333333333333
	st.o	rd7, [rb3, 16]
	set.rd	rd7, 0x4444444444444444
	st.o	rd7, [rb3, 24]
	DMA_SETUP_CFX 0x400, PA_B, 32
	DMA_GO CTRL_START
	POLL_BUSY
	DMA_SETUP_PA PA_B, 0x500, 32
	DMA_GO (CTRL_START | CTRL_DIR)
	POLL_BUSY
	set.rb	rb3, (PMEM_SRAM + 0x500)
	.set	__k, 0
	.rept	4
	ld.o	rd5, [rb3, __k]
	REC	rd5				@@ 23-26
	.set	__k, __k + 8
	.endr

	@@ 非对齐 3 字节：SRAM[0x600] -> PA_C -> SRAM[0x700]（第 4 字节 0x5A 保留）
	set.rb	rb3, (PMEM_SRAM + 0x600)
	set.rd	rd7, PARTIAL
	st.o	rd7, [rb3, 0]
	set.rb	rb3, (PMEM_SRAM + 0x700)
	set.rd	rd7, PARTIALP
	st.o	rd7, [rb3, 0]
	DMA_SETUP_CFX 0x600, PA_C, 3
	DMA_GO CTRL_START
	POLL_BUSY
	DMA_SETUP_PA PA_C, 0x700, 3
	DMA_GO (CTRL_START | CTRL_DIR)
	POLL_BUSY
	set.rb	rb3, (PMEM_SRAM + 0x700)
	ld.o	rd5, [rb3, 0]
	REC	rd5				@@ 27 PARTIALP

	@@ 跨拍：src 0x607（6 B）→ PA_E → dst 0x70F（两端都跨 8 字节拍）
	set.rb	rb3, (PMEM_SRAM + 0x600)
	set.rd	rd7, 0x0011223344556677
	st.o	rd7, [rb3, 0]
	set.rb	rb3, (PMEM_SRAM + 0x608)
	set.rd	rd7, 0x8899AABBCCDDEEFF
	st.o	rd7, [rb3, 0]
	set.rb	rb3, (PMEM_SRAM + 0x708)
	set.rd	rd7, 0xDEADBEEFCAFE0000
	st.o	rd7, [rb3, 0]
	set.rb	rb3, (PMEM_SRAM + 0x710)
	set.rd	rd7, 0x1111111111111111
	st.o	rd7, [rb3, 0]
	DMA_SETUP_CFX 0x607, PA_E, 6
	DMA_GO CTRL_START
	POLL_BUSY
	DMA_SETUP_PA PA_E, 0x70F, 6
	DMA_GO (CTRL_START | CTRL_DIR)
	POLL_BUSY
	set.rb	rb3, (PMEM_SRAM + 0x708)
	ld.o	rd5, [rb3, 0]
	REC	rd5				@@ 28 跨拍目的低字
	set.rb	rb3, (PMEM_SRAM + 0x710)
	ld.o	rd5, [rb3, 0]
	REC	rd5				@@ 29 跨拍目的高字

	@@ CFX 侧末边界：0xFFF8 + 8 = 64 KiB 合法 ⇒ 传输并 DONE
	PMW	4, (ST_DONE | ST_ERROR)
	PMW	0, (PMEM_SRAM + 0xFFF8)
	PMW	1, PA_A
	PMW	2, 8
	DMA_GO CTRL_START
	POLL_BUSY
	PMR	4, rd5
	REC	rd5				@@ 30 CFX 末边界合法
	PMW	4, ST_DONE

	@@ =====================================================================
	@@ setup 错误：SIZE / CFX_RANGE / PA_RANGE / PA_FAULT
	@@ =====================================================================
	PMW	4, (ST_DONE | ST_ERROR)
	PMW	0, (PMEM_SRAM + 0x100)
	PMW	1, PA_A
	PMW	2, 0
	DMA_GO CTRL_START
	PMR	4, rd5
	REC	rd5				@@ 28 = ERROR|SIZE
	PMW	4, ST_ERROR
	PMR	4, rd5
	REC	rd5				@@ 29 = 0
	PMW	2, 0x20000001
	DMA_GO CTRL_START
	PMR	4, rd5
	REC	rd5				@@ 31 = ERROR|SIZE
	PMW	4, ST_ERROR
	PMW	2, 0x20000000			@@ 2^29 合法（SIZE 通过），但超 64 KiB
	DMA_GO CTRL_START
	PMR	4, rd5
	REC	rd5				@@ 33 = ERROR|CFX_RANGE
	PMW	4, ST_ERROR
	PMW	0, (PMEM_SRAM + 0xFFFC)
	PMW	2, 8
	DMA_GO CTRL_START
	PMR	4, rd5
	REC	rd5				@@ 32 = ERROR|CFX_RANGE
	PMW	4, ST_ERROR
	set.rd	rd6, 0x0000800000000000
	cfx2rc	cfx_pmem, cg15, rc0, rd6
	PMW	2, 8
	DMA_GO CTRL_START
	PMR	4, rd5
	REC	rd5				@@ 34 = ERROR|CFX_RANGE
	PMW	4, ST_ERROR
	PMW	0, (PMEM_SRAM + 0x100)
	set.rd	rd6, 0x00FFFFFFFFFFFFF000
	cfx2rc	cfx_pmem, cg15, rc1, rd6
	PMW	2, 0x2000
	DMA_GO CTRL_START
	PMR	4, rd5
	REC	rd5				@@ 36 = ERROR|PA_RANGE
	PMW	4, ST_ERROR
	PMW	1, (ROM_BASE + 0x1000)
	PMW	2, 8
	DMA_GO CTRL_START
	PMR	4, rd5
	REC	rd5				@@ 38 = ERROR|PA_FAULT
	PMW	4, ST_ERROR
	PMW	0, ROM_BASE
	PMW	1, (PMEM_SRAM + 0x800)
	PMW	2, 8
	DMA_GO (CTRL_START | CTRL_DIR)
	POLL_BUSY
	PMR	4, rd5
	REC	rd5				@@ 40 = DONE
	PMW	4, ST_DONE
	PMR	4, rd5
	REC	rd5				@@ 41 = 0

	@@ =====================================================================
	@@ BUSY 期写忽略（1 KiB 传输给出足够窗口）
	@@ =====================================================================
	PMW	4, (ST_DONE | ST_ERROR)
	PMW	0, (PMEM_SRAM + 0x2000)
	PMW	1, PA_D
	PMW	2, 0x400
	DMA_GO CTRL_START
	PMR	4, rd5
	REC	rd5				@@ 42 = BUSY
	PMW	0, PATTERN64
	PMR	0, rd5
	REC	rd5				@@ 43 = PMEM_SRAM+0x2000
	POLL_BUSY
	PMR	4, rd5
	REC	rd5				@@ 44 = DONE
	PMW	4, ST_DONE
	PMR	4, rd5
	REC	rd5				@@ 45 = 0

	@@ ---- escape 非法编码：imms18=3 / [17:2]≠0（4）⇒ ILLI ----
	.dd.t32	ESC_IMM3
	set.rd	rd5, 0xC0DE0005
	REC	rd5
	.dd.t32	ESC_IMM4
	set.rd	rd5, 0xC0DE0006
	REC	rd5

	@@ =====================================================================
	@@ 完成投递：屏蔽期只置 pending（bit32），放行后同一界投递
	@@ =====================================================================
	WCFX_IMM cfx_hart, cg15, rc14, 3	@@ hypv 体：模式上限抬到 hypv
	WCFX_IMM cfx_hmon, cg15, rc3, 0xFFFFFFFFFFFFFFFF
	DMA_SETUP_CFX 0x100, PA_A, 8
	DMA_GO CTRL_START
	POLL_BUSY
	cfx2rd	cfx_hart, cg15, rc5, rd5
	REC	rd5				@@ 46 = 1<<32（pending 汇总）
	cfx2rd	cfx_hart, cg15, rc4, rd5
	REC	rd5				@@ 47 = 0（尚无进入，捕获帧不写）
	cfx2rd	cfx_hart, cg4, rc4, rd5
	REC	rd5				@@ 48 = 0
	WCFX_IMM cfx_hmon, cg15, rc3, MASK_ALLOW_PMEM
capture_fallback:
	set.rd	rd5, 0xDEAD0004
	REC	rd5
	jump	[rb0, fail_exit]

@@ ---------------------------------------------------------------------------
@@ 异步入口（cfx_hart supv 单向量）
@@ ---------------------------------------------------------------------------
async_entry:
	.if TMODE != 3
	cfx2rd	cfx_hart, cg15, rc0, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc1, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc2, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc4, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc5, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg4, rc4, rd5
	REC	rd5
	@@ handler 在返回前 ack 已进入的源
	WCFX_IMM cfx_pmem, cg16, rc18, 1
	jump	[rb0, done_ok]
	.else
	set.rb	rb4, phase
	ld.o	rd22, [rb4, 0]
	add.si	rd22, 1
	st.o	rd22, [rb4, 0]
	set.rd	rd23, 1
	br.eq	{rd22, rd23}?, [rb0, async_phase1]
	set.rd	rd23, 2
	br.eq	{rd22, rd23}?, [rb0, async_phase2]
	jump	[rb0, async_phase3]
	.endif

	.if TMODE == 3
async_phase1:
	@@ 49-54 捕获现场（进入不清 pending，rc5 仍置位）
	cfx2rd	cfx_hart, cg15, rc0, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc1, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc2, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc3, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc4, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc5, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg4, rc4, rd5
	REC	rd5
	@@ escape imms18 = 2（imms20 = 8）：R2 不返回 ⇒ 当前 cfx 的 CFXESC
	set.rd	rd5, 3
	cfx2rc	cfx_hart, cg5, rc8, rd5
	escape	cfx_hart
	swym	0

	@@ ---- 源 ack + 同界多源（timer 15 + DMA 32） ----
	WCFX_IMM cfx_pmem, cg16, rc18, 1
	PMW	4, ST_DONE
	WCFX_IMM cfx_smon, cg15, rc3, 0xFFFFFFFFFFFFFFFF
	WCFX_IMM cfx_hart, cg16, rc0, 0
	cfx2rd	cfx_hart, cg8, rc2, rd5
	add.si	rd5, 150
	cfx2rc	cfx_hart, cg16, rc1, rd5
	WCFX_IMM cfx_hart, cg16, rc0, 1
	DMA_SETUP_CFX 0x100, PA_A, 8
	DMA_GO CTRL_START
	POLL_BUSY
	BURN	rd21, rb3
	cfx2rd	cfx_hart, cg15, rc5, rd5
	REC	rd5				@@ 63 = TIMER|PMEM（pending 汇总）
	cfx2rd	cfx_hart, cg15, rc4, rd5
	REC	rd5				@@ 64 = 1<<32（上一次捕获帧）
	cfx2rd	cfx_hart, cg4, rc4, rd5
	REC	rd5				@@ 65 = 1
	WCFX_IMM cfx_smon, cg15, rc3, MASK_ALLOW_BOTH
multi_fallback:
	set.rd	rd5, 0xDEAD0005
	REC	rd5
	jump	[rb0, fail_exit]

async_phase2:
	@@ 66-71 多源捕获现场（rc5 仍为两源并集，ack 才清）
	cfx2rd	cfx_hart, cg15, rc0, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc1, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc2, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc3, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc4, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc5, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg4, rc4, rd5
	REC	rd5
	@@ ack 两个源（`cg16 rc18` W1C），引擎状态另行 W1C
	WCFX_IMM cfx_hart, cg16, rc18, 1
	WCFX_IMM cfx_pmem, cg16, rc18, 1
	PMW	4, (ST_DONE | ST_ERROR)
	@@ ---- ack 后 pending 落：屏蔽 → DMA 完成 → ack → pending=0 ----
	WCFX_IMM cfx_smon, cg15, rc3, 0xFFFFFFFFFFFFFFFF
	DMA_SETUP_CFX 0x100, PA_A, 8
	DMA_GO CTRL_START
	POLL_BUSY
	cfx2rd	cfx_hart, cg15, rc5, rd5
	REC	rd5				@@ 72 = 1<<32
	WCFX_IMM cfx_pmem, cg16, rc18, 1
	cfx2rd	cfx_hart, cg15, rc5, rd5
	REC	rd5				@@ 73 = 0
	PMW	4, ST_DONE
	WCFX_IMM cfx_smon, cg15, rc3, MASK_ALLOW_PMEM
	BURN	rd21, rb3
	set.rd	rd5, 0xDEAD0006
	REC	rd5				@@ 74 = 无遗留进入的见证
	@@ ---- 覆盖语义：屏蔽期再完成，放行后第二次进入整体覆盖 ----
	WCFX_IMM cfx_smon, cg15, rc3, 0xFFFFFFFFFFFFFFFF
	DMA_SETUP_CFX 0x100, PA_A, 8
	DMA_GO CTRL_START
	POLL_BUSY
	WCFX_IMM cfx_smon, cg15, rc3, MASK_ALLOW_PMEM
overwrite_fallback:
	set.rd	rd5, 0xDEAD0007
	REC	rd5
	jump	[rb0, fail_exit]

async_phase3:
	@@ 75-79 覆盖后的现场（pending 仍置位，ack 才清）
	cfx2rd	cfx_hart, cg15, rc0, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc2, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc3, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc5, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg4, rc4, rd5
	REC	rd5
	WCFX_IMM cfx_pmem, cg16, rc18, 1
	PMW	4, ST_DONE
	jump	[rb0, done_ok]
	.endif

@@ ---------------------------------------------------------------------------
@@ CFXESC 处理（escape imms18 = 2）：记 cfx_hart cg5 帧与 cg15 快照后返回 +4
@@ ---------------------------------------------------------------------------
esc9_entry:
	.if TMODE == 3
	cfx2rd	cfx_hart, cg5, rc2, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg5, rc4, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg5, rc0, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg5, rc1, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc0, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc1, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc2, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc3, rd5
	REC	rd5
	ESCAPE_SKIP4 cfx_hart
	swym	0
	.else
	jump	[rb0, smon_fault]
	.endif

@@ ---------------------------------------------------------------------------
@@ U（umon + user） / S（smon + supv）
@@ ---------------------------------------------------------------------------
setup_u:
	set.rb	rb1, sig_bytes
	set.rd	rd6, 9*8
	st.o	rd6, [rb1, 0]
	WCFX_LABEL cfx_umon, cg3, rc10, u_entry
	WCFX_IMM cfx_umon, cg3, rc14, 0
	@@ hypv 里启动 8 KiB 长传输；完成事件落在 user
	PMW	4, (ST_DONE | ST_ERROR)
	DMA_SETUP_CFX 0x2000, PA_D, 0x800
	DMA_GO CTRL_START
	trap	cfx_umon, 0
	swym	0

u_entry:
	jump	[rb0, mode_body]

setup_s:
	set.rb	rb1, sig_bytes
	set.rd	rd6, 9*8
	st.o	rd6, [rb1, 0]
	WCFX_LABEL cfx_smon, cg3, rc10, s_entry
	WCFX_IMM cfx_smon, cg3, rc14, 2
	PMW	4, (ST_DONE | ST_ERROR)
	DMA_SETUP_CFX 0x2000, PA_D, 0x800
	DMA_GO CTRL_START
	trap	cfx_smon, 0
	swym	0

s_entry:
	jump	[rb0, mode_body]

@@ S/U 共用：屏蔽本模式行 → 等 DMA 完成 ⇒ 只置 pending → 放行 ⇒ 投递
mode_body:
	.if TMODE == 0
	WCFX_IMM cfx_umon, cg15, rc3, 0xFFFFFFFFFFFFFFFF
	.else
	WCFX_IMM cfx_smon, cg15, rc3, 0xFFFFFFFFFFFFFFFF
	.endif
	POLL_PENDING PMEM_BIT
	cfx2rd	cfx_hart, cg15, rc5, rd5
	REC	rd5				@@ 0 = 1<<32（pending 汇总）
	cfx2rd	cfx_hart, cg15, rc4, rd5
	REC	rd5				@@ 1 = 0（尚无进入）
	cfx2rd	cfx_hart, cg4, rc4, rd5
	REC	rd5				@@ 2 = 0
	.if TMODE == 0
	WCFX_IMM cfx_umon, cg15, rc3, MASK_ALLOW_PMEM
	.else
	WCFX_IMM cfx_smon, cg15, rc3, MASK_ALLOW_PMEM
	.endif
umode_wait_begin:
	set.rd	rd5, 0xDEAD0033
	REC	rd5
	jump	[rb0, fail_exit]

@@ ---------------------------------------------------------------------------
@@ 收尾
@@ ---------------------------------------------------------------------------
smon_fault:
	set.rd	rd5, 0xBAD00001
	REC	rd5
	jump	[rb0, fail_exit]

fail_exit:
	DUMP_AND_EXIT 1

done_ok:
	DUMP_AND_EXIT 0

	@@ 放行块（cfx_hmon/hypv 下打开目标 cfx 的 hypv 源掩码）
	.balign 4
perm_mon:
	PERM_OPEN_DELEG	cfx_hart
	PERM_OPEN_DELEG	cfx_pmem
	PERM_OPEN_DELEG	cfx_smon
	PERM_OPEN_DELEG	cfx_umon
	PERM_MON_CLOSE

	.data
	.p2align 3
phase:
	.dd.o64	0
sig_bytes:
	.dd.o64	0
