@@ pmem_dma.S — `cfx_pmem`（cfxha 32）DMA 完成中断 + 同界多源（`m16-testcases-014`）
@@
@@ 目的：在 **Kaiwu-Vast** 的三承载（QEMU / gem5 / chipyard `WumingVastConfig`）上
@@ 验证 `spec/DADAO-12 §4.9`（DMA 与 D-cache 的一致性 = 软件负责）与
@@ `§4.7`/`§5.4`（`ADR-0064`：`cfx_hart cg15` 是进入瞬间的捕获缓冲 / `cg5 rc8–rc11` 出口意图）的 **PMEM_DMA** 面：
@@
@@   * `cg15` DMA：配置/搬运/完成状态；8 B 往返与 3 B 部分拍（邻居字节保留）；
@@     `DONE` / `ERROR` + `ERR_CODE`（SIZE / PA_FAULT；BootROM 可读不可写）。
@@   * **DMA 与 D-cache 一致性（A）**：CPU 先写过 PA 页 ⇒ 按 A 在 `START` 前
@@     对 PA 源区间 `clean`、在 `DONE && BUSY=0` 后对 PA 目标区间 `invalidate`；
@@     断言 CPU 读到 DMA 写入的新值 / DMA 读到 CPU `clean` 过的值（不依赖硬件一致）。
@@   * 放行位：mask = **当前运行模式 monitor** 的 `cg15 rc3`，bit32 = 源 cfxha 32；
@@     源自己的 `cfx_pmem cg16 rc16` 也必须放开（复位全 1）；屏蔽期只置
@@     `cfx_pmem cg16 rc17` bit0 / 汇总 `cfx_hart cg15 rc5` bit32，放行后异步进入。
@@   * 捕获：`src_frame = 1 << 32`、`src_pending` 汇总在进入后仍置位（ack 才清）；
@@     细节回源 `cfx_pmem cg15 rc4 dma_status`（DONE/ERROR、ERR_CODE）。
@@   * **同界多源**：TIMER(15) + DMA(32) 同时 pending 且放行 ⇒ **一次进入**、
@@     `src_frame` = 两位并集、`src_pending` 两位保持到各自 ack、`excp_async_num` 只 +1；
@@     与「拆成两次/单源帧」可达 FAIL 对照（证据脚本注入）。
@@   * 源 ack：`cfx_pmem cg16 rc18` W1C 只清中断 pending；`dma_status` 仍走自己的
@@     W1C；解除屏蔽不产生遗留投递。
@@   * **覆盖语义**：不搬走再到期 ⇒ 每次进入整体覆盖 `cg15`（不是只置 pending）。
@@   * **正常异步返回**：`escape cfx_hart`（rc8/rc9 保持进入前模式/cfx、rc10 可改、
@@     `rc11` 整字写目标 monitor 的 `cg15 rc3`）；`imms18 = 3` / `[17:2] != 0` ⇒ `ILLI`。
@@   * H/S/U 三模式各跑一次（`--defsym TMODE=3/2/0`），各写**自己** monitor 的
@@     掩码行；投递目标都是 `cfx_hart` 的 supv 单向量。
@@
@@ 为什么不含 cfx_pmem 的 cg8/cg12/13/14 寄存器面：这些槽是三承载都已实现
@@ 的寄存器面（QEMU `m16-qemu-006`、gem5 `m16-gem5-025`、RTL
@@ `m16-chipyard-022`），但另由 RTL 探针 `pmem.S` 逐槽覆盖；本文件只碰
@@ cg15 + `cfx_hart cg15` + monitor 掩码 + `cfx_cache cg8`，故可逐槽比较。
@@
@@ 期望值见 `pmem_oracle.py`（现场从 `spec/DADAO-12 §1/§4.6/§4.9/§5.1/§5.4`、
@@ `spec/Kaiwu §1.1/§3`、`.tao/adr/adr-0061-*.md`、`contract-see` §3/§6.1 与
@@ `contracts/opcodes.yaml` 派生；`cause_ip` 用 ELF 符号精确断言）。
@@
@@ 寄存器约定：探针体用 rd5–rd9、rb1–rb3、rb5；handler 用 rd5/rd21–rd23、
@@ rb3/rb4；rb30 = 签名写指针（任何处理器都不得写）；rd16/rb16 = semihosting。
@@
@@ **只在 `WumingVastConfig` 上跑**（Tiny 无 cfx32）。

	.include "tests/shared/asm/signature.inc"
	.include "tests/shared/asm/perm_hypv.inc"

	.ifndef	ENTRY
	.equ	ENTRY,   0xffffff010100
	.endif
	.ifndef	SIG_BUF
	.equ	SIG_BUF, 0xffffff015000
	.endif
	.equ	SIG_N,   96
	.ifndef	EXITB
	.equ	EXITB,   0xffffff015800
	.endif

	.ifndef	TMODE
	.equ	TMODE, 3
	.endif

	.if TMODE == 3
	.equ	SIG_SLOTS, 48
	.else
	.equ	SIG_SLOTS, 10
	.endif

	@@ cfx_pmem SRAM（`spec/Kaiwu §1.1`：(cfxha 32 << 42) | 0x3ff_0000_0000）
	.equ	PMEM_SRAM, 0x83ff00000000
	@@ PA 测试窗（PTW 首张页表的 PTE0 覆盖 PA [0, 512 MiB)，VA = PA）
	.equ	PA_T,     0x200000
	@@ BootROM（只读；两 profile 同址）
	.equ	ROM_BASE, 0xffffffc00000

	@@ dma_ctrl / dma_status 位（`DADAO-12 §4.9`）
	.equ	CTRL_START, 1
	.equ	CTRL_DIR,   2
	.equ	ST_BUSY,    1
	.equ	ST_DONE,    2
	.equ	ST_ERROR,   4

	@@ 源位图 = 源 cfxha：TIMER = 15、PMEM_DMA = 32（`ADR-0061` D2）
	.equ	TIMER_BIT,  0x0000000000008000
	.equ	PMEM_BIT,   0x0000000100000000
	.equ	MASK_ALL,         0xFFFFFFFFFFFFFFFF	@@ 全屏蔽
	.equ	MASK_ALLOW_PMEM,  0xFFFFFFFEFFFFFFFF	@@ bit32 = 0
	.equ	MASK_ALLOW_TIMER, 0xFFFFFFFFFFFF7FFF	@@ bit15 = 0（只放行 TIMER）
	.equ	MASK_ALLOW_BOTH,  0xFFFFFFFEFFFF7FFF	@@ bit15 = 0 且 bit32 = 0

	@@ cfx_cache：D 侧 clean / invalidate + PA 区间（`DADAO-12 §4.6`）
	.equ	CACHE_D_CLEAN_SPAN, 0x4009		@@ bit14=D | [1:0]=01 | [3:2]=10
	.equ	CACHE_D_INVAL_SPAN, 0x400A		@@ bit14=D | [1:0]=10 | [3:2]=10
	.equ	CACHE_SPAN,         0x10000

	.equ	ESC_IMM3, (0x7E000000 | (15 << 18) | 3)
	.equ	ESC_IMM4, (0x7E000000 | (15 << 18) | 4)

	.equ	P1, 0x0123456789ABCDEF
	.equ	P2, 0x1111222233334444
	.equ	P3, 0xAAAABBBBCCCCDDDD
	.equ	P4, 0x5555666677778888
	.equ	PARTIAL,  0xAABBCC0011223344
	.equ	PARTIALP, 0xDEADBE5A11223344	@@ 目的首 3 字节之前的邻居值
	.equ	PARTIAL_EXP, 0xAABBCC5A11223344	@@ 部分拍只改前 3 字节

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

@@ 只填 src/dst/size，不启动（START 由 DMA_GO 单独写；中断屏蔽归 cfx_pmem cg16 rc16）
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

@@ 等 pending 的源位出现（DMA 在另一运行模式下完成时用）
.macro POLL_PENDING bit
__pollp_\@:
	cfx2rd	cfx_hart, cg15, rc5, rd5
	set.rd	rd6, \bit
	and.o	rd5, rd5, rd6
	br.z	{rd5}?, [rb0, __pollp_\@]
.endm

@@ cfx_cache 维护命令（D 侧；PA 区间 = [CACHE_PA, CACHE_PA+CACHE_SPAN)）
.macro CACHE_D ctrl
	set.rd	rd6, PA_T
	cfx2rc	cfx_cache, cg8, rc10, rd6
	set.rd	rd6, CACHE_SPAN
	cfx2rc	cfx_cache, cg8, rc11, rd6
	set.rd	rd6, \ctrl
	cfx2rc	cfx_cache, cg8, rc9, rd6
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

.macro BURN_SHORT rd, rb
	set.rd	\rd, 40
__spin_\@:
	add.si	\rb, 1
	add.si	\rd, -1
	br.nz	{\rd}?, [rb0, __spin_\@]
.endm

@@ ---------------------------------------------------------------------------
@@ 入口：cfx_power + hypv（`spec/Kaiwu §6.2` 固定 BootROM 移交）
@@ ---------------------------------------------------------------------------
	.text
	.globl	_start
_start:
	@@ 测试侧两轴放行（`DIV-07` 关闭后 hypv 也判权；body 以 cfx_power 交付）
	PERM_MON_OPEN perm_mon
	SIG_BEGIN SIG_BUF, SIG_N
	set.rb	rb1, phase
	set.rd	rd6, 0
	st.o	rd6, [rb1, 0]

	@@ ---- 共用初始化（hypv；目标 cfx 的 hypv 源掩码已由 perm_mon 打开） ----
	@@ PTW：PTBR = PA 0、TLB invalid、ptw_enable = 1。QEMU/gem5 的 step5
	@@ BootROM 已做（这里幂等）；RTL 的固定 BootROM 不做 ⇒ 统一在这里建。
	@@ RTL 的页表由链接布局装到 PA 0（`.pt_l1`，4 个 512 MiB 超页，VA = PA）。
	WCFX_IMM cfx_ptw, cg9, rc0, 0
	WCFX_IMM cfx_ptw, cg12, rc0, 2
	WCFX_IMM cfx_ptw, cg8, rc8, 1
	WCFX_LABEL cfx_hart, cg15, rc15, async_entry
	@@ cfx_pmem：U/S 行的源位清 0（0 = 允许），deleg 放开 cg8/cg12..15；
	@@ supv 行还须清 bit15（supv handler 以 cfx_hart 身份访问 cfx_pmem）
	WCFX_IMM cfx_pmem, cg0, rc2, 0xFFFFFFFFFFFFFFFE	@@ U: 允许 cfx_umon
	WCFX_IMM cfx_pmem, cg1, rc2, 0xFFFFFFFFFFFFFFFA	@@ J: 允许 cfx_jmon
	WCFX_IMM cfx_pmem, cg2, rc2, 0xFFFFFFFFFFFF7FFA	@@ S: 允许 cfx_smon / cfx_hart
	WCFX_IMM cfx_pmem, cg3, rc12, 0xFFFFFFFFFFFE0EF7	@@ deleg: cg8/cg12-16
	@@ cfx_hart：U/S 行允许 umon/smon/hart 源；deleg 放开 cg4/5/8/9
	WCFX_IMM cfx_hart, cg0, rc2, 0xFFFFFFFFFFFFFFF8
	WCFX_IMM cfx_hart, cg1, rc2, 0xFFFFFFFFFFFFFFF8
	WCFX_IMM cfx_hart, cg2, rc2, 0xFFFFFFFFFFFFFFF8
	WCFX_IMM cfx_hart, cg3, rc12, 0xFFFFFFFFFFFE7CC7
	@@ cfx_smon：supv handler 以 cfx_hart 身份写它的掩码行
	WCFX_IMM cfx_smon, cg2, rc2, 0xFFFFFFFFFFFF7FFB
	WCFX_IMM cfx_smon, cg3, rc12, 0xFFFFFFFFFFFF7CF7
	WCFX_LABEL cfx_smon, cg3, rc15, smon_fault
	@@ 兜底：U/S 下的意外同步异常分别进 umon 的 user 行 / smon 的 supv 行
	WCFX_LABEL cfx_umon, cg0, rc15, smon_fault
	WCFX_LABEL cfx_smon, cg2, rc15, smon_fault
	@@ timer 关；DMA 源 mask 放开（复位全 1），并 ack 启动链 DMA 留下的 pending
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
@@ H（hmon + hypv）：DMA / 一致性 / 捕获 / 多源 / 覆盖 / escape
@@ ---------------------------------------------------------------------------
setup_h:
	set.rb	rb1, sig_bytes
	set.rd	rd6, SIG_SLOTS*8
	st.o	rd6, [rb1, 0]
	@@ 首次真正的 `trap cfx_hmon, 0` 进入 h_trap_entry（CFXTRAP）；随后把向量切到 h_fault。
	@@ 不写 reserved 的 cg3 rc8（§3.4：⇒ CFXREG）；进入路径不依赖任何异常副作用。
	WCFX_LABEL cfx_hmon, cg3, rc15, h_trap_entry
	trap	cfx_hmon, 0
	swym	0

h_trap_entry:
	@@ 进入路径自证：cause 必须是 CFXTRAP（1<<0）；若是 CFXREG/其它 ⇒ 判红。
	@@ （恢复旧 rc8 写时这里会读到 CFXREG=1<<2 ⇒ 直接 fail，证明不再靠副作用进入。）
	cfx2rd	cfx_hmon, cg5, rc4, rd5
	set.rd	rd6, 0x1
	cmp.uo	rd7, rd5, rd6
	br.z	{rd7}?, [rb0, h_trap_ok]
	set.rd	rd5, 0xBAD00002
	REC	rd5
	jump	[rb0, fail_exit]
h_trap_ok:
	WCFX_LABEL cfx_hmon, cg3, rc15, h_fault
	jump	[rb0, h_body]

h_fault:
	@@ 记录 cause_id / cause_info，再写 rc10 = prev ip + 4 后 escape
	cfx2rd	cfx_hmon, cg5, rc4, rd5
	REC	rd5
	cfx2rd	cfx_hmon, cg5, rc5, rd5
	REC	rd5
	cfx2rd	cfx_hmon, cg5, rc2, rd6
	add.si	rd6, 4
	cfx2rc	cfx_hmon, cg5, rc10, rd6
	escape	cfx_hmon
	swym	0

h_body:
	@@ =====================================================================
	@@ DMA 功能：8 B 往返 / 3 B 部分拍
	@@ =====================================================================
	PMW	4, (ST_DONE | ST_ERROR)
	set.rb	rb3, (PMEM_SRAM + 0x100)
	set.rd	rd7, P1
	st.o	rd7, [rb3, 0]
	DMA_SETUP_CFX 0x100, PA_T, 8
	DMA_GO CTRL_START
	POLL_BUSY
	PMR	4, rd5
	REC	rd5				@@ 0 DONE
	DMA_SETUP_PA PA_T, 0x200, 8
	DMA_GO (CTRL_START | CTRL_DIR)
	POLL_BUSY
	set.rb	rb3, (PMEM_SRAM + 0x200)
	ld.o	rd5, [rb3, 0]
	REC	rd5				@@ 1 P1

	@@ 3 B 部分拍：SRAM[0x600] -> PA_T+0x1000 -> SRAM[0x700]（第 4 字节保留）
	set.rb	rb3, (PMEM_SRAM + 0x600)
	set.rd	rd7, PARTIAL
	st.o	rd7, [rb3, 0]
	set.rb	rb3, (PMEM_SRAM + 0x700)
	set.rd	rd7, PARTIALP
	st.o	rd7, [rb3, 0]
	DMA_SETUP_CFX 0x600, (PA_T + 0x1000), 3
	DMA_GO CTRL_START
	POLL_BUSY
	DMA_SETUP_PA (PA_T + 0x1000), 0x700, 3
	DMA_GO (CTRL_START | CTRL_DIR)
	POLL_BUSY
	set.rb	rb3, (PMEM_SRAM + 0x700)
	ld.o	rd5, [rb3, 0]
	REC	rd5				@@ 2 PARTIALP

	@@ =====================================================================
	@@ 状态 / 错误码
	@@ =====================================================================
	PMW	4, (ST_DONE | ST_ERROR)
	PMW	0, (PMEM_SRAM + 0x100)
	PMW	1, PA_T
	PMW	2, 0
	DMA_GO CTRL_START
	PMR	4, rd5
	REC	rd5				@@ 3 ERROR | SIZE
	PMW	4, ST_ERROR
	PMR	4, rd5
	REC	rd5				@@ 4 0（W1C 清 ERR_CODE）
	PMW	1, (ROM_BASE + 0x1000)
	PMW	2, 8
	DMA_GO CTRL_START
	PMR	4, rd5
	REC	rd5				@@ 5 ERROR | PA_FAULT（写 ROM）
	PMW	4, ST_ERROR
	PMR	4, rd5
	REC	rd5				@@ 6 0
	PMW	0, ROM_BASE
	PMW	1, (PMEM_SRAM + 0x300)
	PMW	2, 8
	DMA_GO (CTRL_START | CTRL_DIR)
	POLL_BUSY
	PMR	4, rd5
	REC	rd5				@@ 7 DONE（读 ROM 合法）
	PMW	4, ST_DONE

	@@ =====================================================================
	@@ DMA 与 D-cache 一致性（A）：软件 clean / invalidate
	@@ =====================================================================
	@@ CFX->PA：CPU 先写脏行 P2 落在目标页；DMA 写 P3；invalidate 后读到 P3
	set.rb	rb5, PA_T
	set.rd	rd7, P2
	st.o	rd7, [rb5, 0x40]
	set.rb	rb3, (PMEM_SRAM + 0x400)
	set.rd	rd7, P3
	st.o	rd7, [rb3, 0]
	DMA_SETUP_CFX 0x400, (PA_T + 0x40), 8
	DMA_GO CTRL_START
	POLL_BUSY
	CACHE_D CACHE_D_INVAL_SPAN
	ld.o	rd5, [rb5, 0x40]
	REC	rd5				@@ 8 P3（invalidate 后读到 DMA 写入值）

	@@ PA->CFX：CPU 先写脏行 P4；clean 后 DMA 读到 P4
	set.rd	rd7, P4
	st.o	rd7, [rb5, 0x80]
	CACHE_D CACHE_D_CLEAN_SPAN
	DMA_SETUP_PA (PA_T + 0x80), 0x500, 8
	DMA_GO (CTRL_START | CTRL_DIR)
	POLL_BUSY
	set.rb	rb3, (PMEM_SRAM + 0x500)
	ld.o	rd5, [rb3, 0]
	REC	rd5				@@ 9 P4（clean 后 DMA 读到 CPU 写入值）

	@@ =====================================================================
	@@ escape 非法编码：imms18 = 3 / [17:2] != 0（4）⇒ ILLI
	@@ =====================================================================
	.dd.t32	ESC_IMM3
	set.rd	rd5, 0xC0DE0005
	REC	rd5				@@ 12 ILLI 见证
	.dd.t32	ESC_IMM4
	set.rd	rd5, 0xC0DE0006
	REC	rd5				@@ 15 ILLI 见证

	@@ =====================================================================
	@@ 捕获：屏蔽期只置 pending（bit32），放行后同一界投递
	@@ =====================================================================
	WCFX_IMM cfx_hmon, cg15, rc3, MASK_ALL
	PMW	4, (ST_DONE | ST_ERROR)
	DMA_SETUP_CFX 0x100, (PA_T + 0x200), 8
	DMA_GO CTRL_START
	POLL_BUSY
	cfx2rd	cfx_hart, cg15, rc5, rd5
	REC	rd5				@@ 16 = 1<<32
	cfx2rd	cfx_hart, cg15, rc4, rd5
	REC	rd5				@@ 17 = 0（捕获缓冲尚未覆盖）
	cfx2rd	cfx_hart, cg4, rc4, rd5
	REC	rd5				@@ 18 = 0（还没有异步进入）
	WCFX_IMM cfx_hmon, cg15, rc3, MASK_ALLOW_PMEM
capture_fallback:
	set.rd	rd5, 0xDEAD0004
	REC	rd5				@@ 投递未发生时才会执行
	jump	[rb0, fail_exit]

@@ ---------------------------------------------------------------------------
@@ 异步入口（cfx_hart supv 单向量）；用 phase 分派
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
	@@ 19-24 捕获现场（prev = hypv/cfx_hmon，cause_ip = capture_fallback）
	cfx2rd	cfx_hart, cg15, rc0, rd5
	REC	rd5				@@ 19
	cfx2rd	cfx_hart, cg15, rc1, rd5
	REC	rd5				@@ 20
	cfx2rd	cfx_hart, cg15, rc2, rd5
	REC	rd5				@@ 21
	cfx2rd	cfx_hart, cg15, rc4, rd5
	REC	rd5				@@ 22 = 1<<32
	cfx2rd	cfx_hart, cg15, rc5, rd5
	REC	rd5				@@ 23 = 0
	cfx2rd	cfx_hart, cg4, rc4, rd5
	REC	rd5				@@ 24 = 1
	@@ 细节回源：cfx_pmem cg15 rc4 dma_status（DONE / ERR_CODE）
	PMR	4, rd5
	REC	rd5				@@ 25 = DONE
	@@ handler 在 escape 前 ack 已进入的源（进入不清 pending）
	WCFX_IMM cfx_pmem, cg16, rc18, 1

	@@ ---- 正常异步返回：rc8/rc9 = 进入前 (supv, cfx_hart)、rc10 = after_escape、
	@@   rc11 = P1（整字写 smon cg15 rc3；bit15/32=1 ⇒ 后续事件先置 pending） ----
	set.rd	rd5, 2
	cfx2rc	cfx_hart, cg5, rc8, rd5
	set.rd	rd5, 15
	cfx2rc	cfx_hart, cg5, rc9, rd5
	set.rd	rd5, after_escape
	cfx2rc	cfx_hart, cg5, rc10, rd5
	set.rd	rd5, P1
	cfx2rc	cfx_hart, cg5, rc11, rd5
	escape	cfx_hart
	swym	0
after_escape:
	cfx2rd	cfx_smon, cg15, rc3, rd5
	REC	rd5				@@ 26 = P1（rc11 整字，返回第一条指令即生效）

	@@ ---- 源 ack + 同界多源（TIMER 15 + DMA 32） ----
	WCFX_IMM cfx_pmem, cg16, rc18, 1
	cfx2rd	cfx_hart, cg15, rc5, rd5
	REC	rd5				@@ 27 = 0（ack 后 pending 落）
	cfx2rd	cfx_hart, cg15, rc4, rd5
	REC	rd5				@@ 28 = 1<<32（捕获快照仍在）
	WCFX_IMM cfx_smon, cg15, rc3, MASK_ALL
	WCFX_IMM cfx_hart, cg16, rc0, 0
	cfx2rd	cfx_hart, cg8, rc2, rd5
	add.si	rd5, 150
	cfx2rc	cfx_hart, cg16, rc1, rd5
	WCFX_IMM cfx_hart, cg16, rc0, 1
	DMA_SETUP_CFX 0x100, (PA_T + 0x300), 8
	DMA_GO CTRL_START
	POLL_BUSY
	BURN	rd21, rb3
	cfx2rd	cfx_hart, cg15, rc5, rd5
	REC	rd5				@@ 29 = TIMER | PMEM
	cfx2rd	cfx_hart, cg15, rc4, rd5
	REC	rd5				@@ 30 = 1<<32（捕获未被覆盖）
	cfx2rd	cfx_hart, cg4, rc4, rd5
	REC	rd5				@@ 31 = 1
	WCFX_IMM cfx_smon, cg15, rc3, MASK_ALLOW_BOTH
multi_fallback:
	set.rd	rd5, 0xDEAD0005
	REC	rd5
	jump	[rb0, fail_exit]

async_phase2:
	@@ 32-37 多源捕获现场
	cfx2rd	cfx_hart, cg15, rc0, rd5
	REC	rd5				@@ 32 supv
	cfx2rd	cfx_hart, cg15, rc1, rd5
	REC	rd5				@@ 33 cfx_hart
	cfx2rd	cfx_hart, cg15, rc2, rd5
	REC	rd5				@@ 34 multi_fallback
	cfx2rd	cfx_hart, cg15, rc4, rd5
	REC	rd5				@@ 35 位图并集
	cfx2rd	cfx_hart, cg15, rc5, rd5
	REC	rd5				@@ 36 = 0（两位一次清）
	cfx2rd	cfx_hart, cg4, rc4, rd5
	REC	rd5				@@ 37 = 2（一次进入只 +1）
	@@ ack 两个源（`cg16 rc18` W1C；只清中断 pending）
	WCFX_IMM cfx_hart, cg16, rc18, 1
	WCFX_IMM cfx_pmem, cg16, rc18, 1
	cfx2rd	cfx_hart, cg15, rc5, rd5
	REC	rd5				@@ 38 = 0

	@@ ---- 屏蔽 → pending → W1C ack → pending 落 → 放行无遗留投递 ----
	WCFX_IMM cfx_smon, cg15, rc3, MASK_ALL
	DMA_SETUP_CFX 0x100, (PA_T + 0x400), 8
	DMA_GO CTRL_START
	POLL_BUSY
	cfx2rd	cfx_hart, cg15, rc5, rd5
	REC	rd5				@@ 39 = 1<<32
	WCFX_IMM cfx_pmem, cg16, rc18, 1
	cfx2rd	cfx_hart, cg15, rc5, rd5
	REC	rd5				@@ 40 = 0
	WCFX_IMM cfx_smon, cg15, rc3, MASK_ALLOW_PMEM
	BURN_SHORT	rd21, rb3
	set.rd	rd5, 0xDEAD0006
	REC	rd5				@@ 41 = 无遗留投递的见证

	@@ ---- 覆盖语义：不搬走再到期 ⇒ 第二次进入整体覆盖 cg15 ----
	WCFX_IMM cfx_smon, cg15, rc3, MASK_ALL
	DMA_SETUP_CFX 0x100, (PA_T + 0x500), 8
	DMA_GO CTRL_START
	POLL_BUSY
	WCFX_IMM cfx_smon, cg15, rc3, MASK_ALLOW_PMEM
overwrite_fallback:
	set.rd	rd5, 0xDEAD0007
	REC	rd5
	jump	[rb0, fail_exit]

async_phase3:
	@@ 42-47 覆盖后的现场
	cfx2rd	cfx_hart, cg15, rc0, rd5
	REC	rd5				@@ 42
	cfx2rd	cfx_hart, cg15, rc1, rd5
	REC	rd5				@@ 43
	cfx2rd	cfx_hart, cg15, rc2, rd5
	REC	rd5				@@ 44 overwrite_fallback
	cfx2rd	cfx_hart, cg15, rc4, rd5
	REC	rd5				@@ 45 = 1<<32
	cfx2rd	cfx_hart, cg15, rc5, rd5
	REC	rd5				@@ 46 = 0
	cfx2rd	cfx_hart, cg4, rc4, rd5
	REC	rd5				@@ 47 = 3（每次进入 +1）
	WCFX_IMM cfx_pmem, cg16, rc18, 1
	jump	[rb0, done_ok]
	.endif

@@ ---------------------------------------------------------------------------
@@ U（umon + user） / S（smon + supv）：DMA 在 hypv 启动、完成事件落在目标模式
@@ ---------------------------------------------------------------------------
setup_u:
	set.rb	rb1, sig_bytes
	set.rd	rd6, SIG_SLOTS*8
	st.o	rd6, [rb1, 0]
	@@ 把首张页表 PTE0 的 HSJU 置 0xF（U=1），并失效 TLB（VA 0 -> PA 0）
	set.rd	rd6, 0xF00000000000FFEF
	set.rb	rb2, 0
	st.o	rd6, [rb2, 0]
	set.rd	rd6, 2
	cfx2rc	cfx_ptw, cg12, rc0, rd6
	WCFX_IMM cfx_hmon, cg15, rc3, MASK_ALL		@@ DMA 完成不得在 hypv 投递
	WCFX_IMM cfx_umon, cg15, rc3, MASK_ALL
	WCFX_LABEL cfx_umon, cg3, rc15, u_entry
	WCFX_IMM cfx_umon, cg3, rc14, 0
	PMW	4, (ST_DONE | ST_ERROR)
	DMA_SETUP_CFX 0x2000, (PA_T + 0x8000), 0x800
	DMA_GO CTRL_START
	trap	cfx_umon, 0
	swym	0

u_entry:
	jump	[rb0, mode_body]

setup_s:
	set.rb	rb1, sig_bytes
	set.rd	rd6, SIG_SLOTS*8
	st.o	rd6, [rb1, 0]
	WCFX_IMM cfx_hmon, cg15, rc3, MASK_ALL
	WCFX_IMM cfx_smon, cg15, rc3, MASK_ALL
	WCFX_LABEL cfx_smon, cg3, rc15, s_entry
	WCFX_IMM cfx_smon, cg3, rc14, 2
	PMW	4, (ST_DONE | ST_ERROR)
	DMA_SETUP_CFX 0x2000, (PA_T + 0x8000), 0x800
	DMA_GO CTRL_START
	trap	cfx_smon, 0
	swym	0

s_entry:
	jump	[rb0, mode_body]

@@ S/U 共用：各写自己 monitor 的掩码行 → 等 DMA 完成 ⇒ 只置 pending →
@@ 放行 ⇒ 同一界投递（进入 async_entry 的 S/U 分支）
mode_body:
	.if TMODE == 0
	cfx2rd	cfx_umon, cg15, rc3, rd5
	REC	rd5				@@ 0 本模式掩码行 = 全 1
	.else
	cfx2rd	cfx_smon, cg15, rc3, rd5
	REC	rd5				@@ 0 本模式掩码行 = 全 1
	.endif
	POLL_PENDING PMEM_BIT
	cfx2rd	cfx_hart, cg15, rc5, rd5
	REC	rd5				@@ 1 = 1<<32
	cfx2rd	cfx_hart, cg15, rc4, rd5
	REC	rd5				@@ 2 = 0
	cfx2rd	cfx_hart, cg4, rc4, rd5
	REC	rd5				@@ 3 = 0
	.if TMODE == 0
	WCFX_IMM cfx_umon, cg15, rc3, MASK_ALLOW_PMEM
	.else
	WCFX_IMM cfx_smon, cg15, rc3, MASK_ALLOW_PMEM
	.endif
umode_wait_begin:
	set.rd	rd5, 0xDEAD0033
	REC	rd5				@@ 未投递时才会执行
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

	@@ RTL 承载的页表由链接布局装到 PA 0；QEMU/gem5 用 step5 BootROM 的表。
	.ifdef	RTL_PTW_TABLE
	.section .pt_l1,"aw"
	.dd.o64	0xc00000000000ffef	@@ PTE0: PPN 0（VA = PA，[0, 512 MiB)）
	.dd.o64	0xc00000002000ffef	@@ PTE1: PPN 1
	.dd.o64	0xc00000004000ffef	@@ PTE2: PPN 2
	.dd.o64	0xc00000006000ffef	@@ PTE3: PPN 3
	.endif

	@@ 放行块（cfx_hmon/hypv 下打开目标 cfx 的 hypv 源掩码）
	.text
	.balign 4
perm_mon:
	PERM_OPEN	cfx_ptw
	PERM_OPEN	cfx_cache
	PERM_OPEN_DELEG	cfx_pmem
	PERM_OPEN_DELEG	cfx_hart
	PERM_OPEN_DELEG	cfx_smon
	PERM_OPEN_DELEG	cfx_umon
	PERM_MON_CLOSE

	.data
	.p2align 3
phase:
	.dd.o64	0
sig_bytes:
	.dd.o64	0
