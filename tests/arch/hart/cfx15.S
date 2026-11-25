@@ cfx15.S — `cfx_hart`（cfxha 15）RTL 探针（`m16-chipyard-021` 起，`m16-chipyard-026` 改到 R2）
@@
@@ 目的：在 **Kaiwu-Vast RTL（chipyard `WumingVastConfig`）** 上验证
@@ `spec/DADAO-12 §4.7`/`§5.4` 的 cfx_hart（**R2：cg9 是进入瞬间的捕获缓冲**）：
@@   * cg8 管理寄存器：hart_id / cycle / insn / timer_cmp / timer_ctrl；
@@   * cg9 **七槽**捕获缓冲：rc0 prev_run_mode / rc1 prev_cfx_code / rc2 cause_ip /
@@     rc3 src_frame（HW/RO，位 = 源 cfxha）/ rc4 src_pending（HW/RO）/
@@     rc5 excp_vector / rc6 switch_run_mode（固定 supv = 2）；rc7–rc15 reserved；
@@   * 两个位图**软件写忽略、读回不变、不产生异常**（不报 CFXREG）；
@@   * 来源掩码在**当前运行模式 monitor** 的 `cg8 rc1`（bit15 = 源 cfxha 15，
@@     0 = 允许 / 1 = 屏蔽）：屏蔽期只置 `src_pending` 的 bit15，解除后补投；
@@   * 投递：一帧多源（本机只有一个源）→ `src_frame` = 位 15、pending 扣除、
@@     `excp_async_num` +1；
@@   * **覆盖语义**：第一次进入后不搬走现场，再次到期 ⇒ 同一指令边界整体覆盖
@@     `cg9`（`prev_*`/`cause_ip`/`src_frame`），**不是**只置 pending；
@@   * 源 ack（重装 `timer_cmp`）后 pending 落；
@@   * `escape` 的帧选择位 `imms18[1] = 1`（汇编 `imms20 = 8`）**不是异步返回**：
@@     按所选帧无效报当前 cfx 的 `CFXESC`，不改变 cfx/运行模式/`cg9`；
@@     `imms18 = 3` / `imms18[17:2] != 0` ⇒ ILLI；同步 `cg5` 帧返回仍有效；
@@   * **精确点**：在 `jump` 目标处到期时 `cause_ip` = 目标（SimRISC-06 的
@@     `jump`，不是 RISC-V `jal`）；实现用「从 0 起逐步加 1 个 cycle」的有界
@@     搜索命中目标边界（各平台的读周期延迟不同，不能写死补偿）；
@@   * H/S/U 三模式下掩码都取**当前运行模式** monitor 的那一行（`--defsym
@@     TMODE=3/2/0`），投递目标都是 cfx_hart/supv。`PTW_UMAP`（仅 QEMU
@@     承载）在 U 模式下把镜像所在 512 MiB 超页的 PTE 置 U=1。
@@
@@ **一份 case、三种运行模式**：本文件是唯一载体，汇编期用 `-defsym TMODE=`
@@ 选择目标运行模式（0 = umon/U、2 = smon/S、3 = hmon/H）；H 模式额外做寄存器面
@@ 与非法编码探针。期望值见 `check_cfx15.py`（现场从 `spec/DADAO-12` §1/§3.6/§4.7/
@@ §5.1/§5.4、`.tao/adr/adr-0061-*.md`、`contract-see` §3/§6.1 与
@@ `contracts/opcodes.yaml` 派生）。
@@
@@ 入口约定：chipyard 固定 BootROM（`spec/Kaiwu §6.2`）以 cfx_power 在 hypv 跳到
@@ `ENTRY`。H 模式先 `trap cfx_hmon` 进入 hmon/hypv；U/S 模式按 `§5.2` 用
@@ `trap cfx_umon` / `trap cfx_smon` + 目标 cfx 的 hypv 行向量/切换值进入。
@@
@@ 不变量：
@@   * 签名槽顺序固定（见 checker 的 expected），漏跑/多跑都判红；
@@   * `cause_ip` 用 ELF 符号**精确**断言（投递发生在“下一条指令的边界”，该指令
@@     未执行 ⇒ 其地址就是 `cause_ip`）；
@@   * 两个位图的期望值全由源 cfxha 派生（TIMER = cfx_hart = 15 ⇒ `1 << 15`）；
@@   * 期望值不从 RTL 观测值反推；探针只 `REC` 实测值。
@@
@@ 寄存器约定：探针体用 rd5–rd7、rb1–rb3、rb5；handler 用 rd5/rd21/rd22/rd23、
@@ rb3/rb4；rb30 = 签名写指针（任何处理器都不得写）；rd16/rb16 = semihosting；
@@ rb20 = hmon SRAM 基址（仅 H 的寄存器面探针使用）。
@@ **只在 `WumingVastConfig` 上跑**（Tiny 无 cfx15、无 U/S 模式）。

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
	.ifndef	HMON_BASE
	.equ	HMON_BASE, 0xffffff018000
	.endif

	.ifndef	TMODE
	.equ	TMODE, 3
	.endif

	@@ 每个镜像的签名槽数（与 checker 的 `expected()` 一一对应）
	.if TMODE == 3
	.equ	SIG_SLOTS, 80
	.else
	.equ	SIG_SLOTS, 40
	.endif

	@@ `DADAO-12 §5.1`（R2）：escape 的 imms18 = 2 选 cg9 编码合法但**不返回**
	@@ （⇒ 当前 cfx 的 CFXESC）；3 非法。合法返回用汇编层 `imms20 = 8`
	@@ （= imms18 2）；非法编码（3/4）汇编器会拒绝，故用原始编码字直接喂给核。
	.equ	ESC_HART_IMM3, (0x7E000000 | (15 << 18) | 3)
	.equ	ESC_HART_IMM4, (0x7E000000 | (15 << 18) | 4)

	.equ	PATTERN64, 0x123456789ABCDEF0
	.equ	TIMER_SRC_BIT, 0x0000000000008000	@@ 1 << 15（源 cfxha = 15）
	.equ	MASK_PATTERN,  0xFFFFFFFFFFFF7FFF	@@ bit15 = 0（允许 TIMER）

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

@@ 计时等待：约 300 条指令（每迭代 3 条），覆盖 timer deadline。
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
@@ 入口：cfx_power + hypv
@@ ---------------------------------------------------------------------------
	.text
	.globl	_start
_start:
	@@ 测试侧两轴放行（`DIV-07` 关闭后 hypv 也判权；body 以 cfx_power 交付）
	PERM_MON_OPEN perm_mon
	SIG_BEGIN SIG_BUF, SIG_N
	@@ 清 `hphase`（hmon 入口分派用）与 `phase`（async handler 分派用）
	set.rb	rb1, hphase
	set.rd	rd6, 0
	st.o	rd6, [rb1, 0]
	set.rb	rb1, phase
	st.o	rd6, [rb1, 0]
	@@ rd20 = 跳转精确点模式（0 = 捕获流程；1 = jump 目标到期搜索）
	set.rd	rd20, 0

	@@ ---- 共用初始化：cfx_hart 的异步入口 / 三行来源掩码 / 两轴放行 ----
	WCFX_LABEL cfx_hart, cg9, rc5, async_entry	@@ async_excp_vector
	@@ R2：`escape imms18 = 2` 在 supv 执行时按“帧无效”进当前 cfx（cfx_hart），
	@@ 目标取 cfx_hart 的 supv 行向量（cg2 rc10），切到 esc9_entry。
	WCFX_LABEL cfx_hart, cg2, rc10, esc9_entry
	@@ umon/smon 的 `cg8 rc1` 先放开源 cfxha 15（bit15 = 0）——U/S 体与 supv
	@@ handler 里的覆盖/屏蔽测试都靠这两行；hmon 行留到 H 体里先验复位值再改写。
	WCFX_IMM   cfx_umon, cg8, rc1, MASK_PATTERN
	WCFX_IMM   cfx_smon, cg8, rc1, MASK_PATTERN
	@@ supv handler 要写 cfx_smon 的 `cg8 rc1`（临时屏蔽当前模式）：放开源位 15
	@@ 在 cfx_smon 的 supv `cfxreg` 行（cg2 rc2），并在它自己的 `cg3 rc12`
	@@ deleg 里放开 cg8/cg9（supv 访问非当前 cfx 还受目标 cfx 的 deleg 约束）。
	WCFX_IMM   cfx_smon, cg2, rc2, MASK_PATTERN
	WCFX_IMM   cfx_smon, cg3, rc12, 0xFFFFFFFFFFFFFCF7
	@@ 兜底：supv 下的意外同步异常进 cfx_smon，落 smon_fault 快速失败
	WCFX_LABEL cfx_smon, cg3, rc10, smon_fault
	@@ timer 关：cmp 全 1、ctrl 0
	WCFX_IMM   cfx_hart, cg8, rc4, 0xFFFFFFFFFFFFFFFF
	WCFX_IMM   cfx_hart, cg8, rc5, 0
	@@ 两轴放行：目标 cfx（cfx_hart）的 user/jail/supv cfxreg 源位清 0
	WCFX_IMM   cfx_hart, cg0, rc2, 0xFFFFFFFFFFFFFFF8
	WCFX_IMM   cfx_hart, cg1, rc2, 0xFFFFFFFFFFFFFFF8
	WCFX_IMM   cfx_hart, cg2, rc2, 0xFFFFFFFFFFFFFFF8
	@@ cg3 rc12 delegation：放开 cg4/cg5/cg8/cg9（bit3 硬件恒 1）
	WCFX_IMM   cfx_hart, cg3, rc12, 0xFFFFFFFFFFFFFCC7

	.if TMODE == 0
	.ifdef	PTW_UMAP
	@@ QEMU step5 页表在 PA 0；镜像所在的 512 MiB 超页置 HSJU=0xF（U=1）
	set.rd	rd6, 0xF00000000000FFEF
	set.rb	rb2, 0
	st.o	rd6, [rb2, 0]
	set.rd	rd6, 2				@@ tlb_control = invalid all
	cfx2rc	cfx_ptw, cg12, rc0, rd6
	.endif
	.endif
	.if TMODE == 3
	jump	[rb0, setup_h]
	.elseif TMODE == 2
	jump	[rb0, setup_s]
	.else
	jump	[rb0, setup_u]
	.endif

@@ ---------------------------------------------------------------------------
@@ H（hmon + hypv）：先进入 cfx_hmon，再在 h_entry 里跑寄存器面 + timer
@@ ---------------------------------------------------------------------------
setup_h:
	set.rb	rb1, sig_bytes
	set.rd	rd6, 80*8
	st.o	rd6, [rb1, 0]
	WCFX_LABEL cfx_hmon, cg3, rc10, h_entry
	WCFX_IMM   cfx_hmon, cg3, rc8, 3
	trap	cfx_hmon, 0
	swym	0

h_entry:
	@@ 同步异常（CFXTRAP 以外的 cause）走 h_fault；初次 trap 的低位是 CFXTRAP
	cfx2rd	cfx_hmon, cg5, rc2, rd5
	set.rd	rd6, 1
	and.o	rd5, rd5, rd6
	br.nz	{rd5}?, [rb0, h_initial]
	cfx2rd	cfx_hmon, cg5, rc2, rd5
	set.rd	rd6, 1
	and.o	rd5, rd5, rd6
	br.z	{rd5}?, [rb0, h_fault]
h_initial:
	set.rb	rb1, hphase
	ld.o	rd5, [rb1, 0]
	br.nz	{rd5}?, [rb0, h_fault]
	set.rd	rd5, 1
	st.o	rd5, [rb1, 0]
	jump	[rb0, h_body]

h_fault:
	@@ 故障处理：记 cause_id / cause_info，然后 escape +4 跳过故障指令
	cfx2rd	cfx_hmon, cg5, rc2, rd5
	REC	rd5
	cfx2rd	cfx_hmon, cg5, rc4, rd5
	REC	rd5
	escape	cfx_hmon, [excp_cause_ip, 4]
	swym	0

@@ ---------------------------------------------------------------------------
@@ H 测试体：寄存器面 + 保留/非法编码 + 屏蔽/pending
@@ ---------------------------------------------------------------------------
h_body:
	@@ 0 hart_id = 0
	cfx2rd	cfx_hart, cg8, rc0, rd5
	REC	rd5
	@@ 1/2 cycle 递增
	cfx2rd	cfx_hart, cg8, rc2, rd5
	REC	rd5
	add.si	rb1, 1
	add.si	rb1, 1
	add.si	rb1, 1
	cfx2rd	cfx_hart, cg8, rc2, rd5
	REC	rd5
	@@ 3/4 insn 递增
	cfx2rd	cfx_hart, cg8, rc3, rd5
	REC	rd5
	add.si	rb1, 1
	add.si	rb1, 1
	cfx2rd	cfx_hart, cg8, rc3, rd5
	REC	rd5
	@@ 5 timer_cmp RW
	set.rd	rd6, PATTERN64
	cfx2rc	cfx_hart, cg8, rc4, rd6
	cfx2rd	cfx_hart, cg8, rc4, rd5
	REC	rd5
	@@ 先写全 1 关闭匹配，再测 timer_ctrl 的 [1:0] 读回
	WCFX_IMM   cfx_hart, cg8, rc4, 0xFFFFFFFFFFFFFFFF
	.set	__ctrl, 0
	.rept	5
	set.rd	rd6, __ctrl
	cfx2rc	cfx_hart, cg8, rc5, rd6
	cfx2rd	cfx_hart, cg8, rc5, rd5
	REC	rd5
	.set	__ctrl, __ctrl + 1
	.endr
	@@ 11 cg9 rc0 prev_run_mode：写全 1，读回 2 位 = 3
	WCFX_IMM   cfx_hart, cg9, rc0, 0xFFFFFFFFFFFFFFFF
	cfx2rd	cfx_hart, cg9, rc0, rd5
	REC	rd5
	@@ 12 rc1 prev_cfx_code：写全 1，读回 6 位 = 63
	WCFX_IMM   cfx_hart, cg9, rc1, 0xFFFFFFFFFFFFFFFF
	cfx2rd	cfx_hart, cg9, rc1, rd5
	REC	rd5
	@@ 13 rc2 cause_ip：写全 1，读回 48 位且低 2 位为 0
	WCFX_IMM   cfx_hart, cg9, rc2, 0xFFFFFFFFFFFFFFFF
	cfx2rd	cfx_hart, cg9, rc2, rd5
	REC	rd5
	@@ 14 rc3 src_frame：HW/RO —— 写 PATTERN 被忽略、读回不变（捕获缓冲 = 0）
	WCFX_IMM   cfx_hart, cg9, rc3, PATTERN64
	cfx2rd	cfx_hart, cg9, rc3, rd5
	REC	rd5
	@@ 15 rc4 src_pending：HW/RO —— 同上
	WCFX_IMM   cfx_hart, cg9, rc4, PATTERN64
	cfx2rd	cfx_hart, cg9, rc4, rd5
	REC	rd5
	@@ 16 rc5 excp_vector：写全 1，读回 48 位且低 2 位 0
	WCFX_IMM   cfx_hart, cg9, rc5, 0xFFFFFFFFFFFFFFFF
	cfx2rd	cfx_hart, cg9, rc5, rd5
	REC	rd5
	@@ 恢复真向量（后面的 timer 投递必须落到 async_entry）
	WCFX_LABEL cfx_hart, cg9, rc5, async_entry
	@@ 17 rc6 switch：固定 supv（2）；只读回（写忽略行为由 QEMU 差异登记）
	cfx2rd	cfx_hart, cg9, rc6, rd5
	REC	rd5

	@@ 18-26 保留 rc（cg9 rc7 / rc8 / rc15）⇒ CFXREG：cause_id / cause_info / 见证
	cfx2rd	cfx_hart, cg9, rc7, rd5
	set.rd	rd5, 0xC0DE0013
	REC	rd5
	cfx2rd	cfx_hart, cg9, rc8, rd5
	set.rd	rd5, 0xC0DE0018
	REC	rd5
	cfx2rd	cfx_hart, cg9, rc15, rd5
	set.rd	rd5, 0xC0DE0019
	REC	rd5
	@@ 27-29 写 RO（cg8 rc0）⇒ CFXREG
	set.rd	rd6, 0
	cfx2rc	cfx_hart, cg8, rc0, rd6
	set.rd	rd5, 0xC0DE0014
	REC	rd5
	@@ 30-32 读保留（cfx_hart 自己的 cg8 rc1）⇒ CFXREG
	cfx2rd	cfx_hart, cg8, rc1, rd5
	set.rd	rd5, 0xC0DE0015
	REC	rd5
	@@ 33-35 escape imms18=3 ⇒ ILLI
	.dd.t32	ESC_HART_IMM3
	set.rd	rd5, 0xC0DE0016
	REC	rd5
	@@ 36-38 escape imms18=4（[17:2] ≠ 0）⇒ ILLI
	.dd.t32	ESC_HART_IMM4
	set.rd	rd5, 0xC0DE0017
	REC	rd5

	@@ ---- 39 cfx3（hmon）的 `cg8 rc1` 复位 = 全 1（ADR-0061 D5） ----
	cfx2rd	cfx_hmon, cg8, rc1, rd5
	REC	rd5

	@@ ---- 40/41 屏蔽期：只置 pending、不投递 ----
	@@ 只屏蔽**当前运行模式**（hmon）的行；umon/smon 仍放行 —— 若投递错取
	@@ 别的行，这里会提前进入 handler
	WCFX_IMM   cfx_hmon, cg8, rc1, 0xFFFFFFFFFFFFFFFF	@@ bit15 = 1（屏蔽）
	cfx2rd	cfx_hart, cg8, rc2, rd5
	add.si	rd5, 150
	cfx2rc	cfx_hart, cg8, rc4, rd5
	WCFX_IMM   cfx_hart, cg8, rc5, 1
	BURN	rd7, rb1
	cfx2rd	cfx_hart, cg9, rc4, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg9, rc3, rd5
	REC	rd5
	@@ 放开当前模式的掩码行 ⇒ **下一指令边界投递**（timer 仍到期、源尚未 ack）
	WCFX_IMM   cfx_hmon, cg8, rc1, MASK_PATTERN

wait_begin:
	set.rd	rd7, 300
wait_loop:
	add.si	rb5, 1
	add.si	rd7, -1
	br.nz	{rd7}?, [rb0, wait_loop]
wait_end:
	@@ 投递未发生：签名缺槽 ⇒ 红
	set.rd	rd5, 0xDEAD0003
	REC	rd5
	jump	[rb0, fail_exit]

@@ ---------------------------------------------------------------------------
@@ U（umon + user）
@@ ---------------------------------------------------------------------------
setup_u:
	set.rb	rb1, sig_bytes
	set.rd	rd6, 40*8
	st.o	rd6, [rb1, 0]
	WCFX_LABEL cfx_umon, cg3, rc10, u_entry
	WCFX_IMM   cfx_umon, cg3, rc8, 0
	trap	cfx_umon, 0
	swym	0

u_entry:
	jump	[rb0, mode_body]

@@ ---------------------------------------------------------------------------
@@ S（smon + supv）
@@ ---------------------------------------------------------------------------
setup_s:
	set.rb	rb1, sig_bytes
	set.rd	rd6, 40*8
	st.o	rd6, [rb1, 0]
	WCFX_LABEL cfx_smon, cg3, rc10, s_entry
	WCFX_IMM   cfx_smon, cg3, rc8, 2
	@@ supv 下访问自身 cg8/cg9 受 `cg3 rc12` deleg 约束（bit8/bit9 = 0 才允许）
	WCFX_IMM   cfx_smon, cg3, rc12, 0xFFFFFFFFFFFFFCF7
	trap	cfx_smon, 0
	swym	0

s_entry:
	jump	[rb0, mode_body]

@@ ---------------------------------------------------------------------------
@@ U/S 共用测试体：屏蔽 → pending → 放开 → 投递
@@ ---------------------------------------------------------------------------
mode_body:
	@@ 屏蔽**本模式**的掩码行（另两行仍放行）
	.if TMODE == 0
	WCFX_IMM   cfx_umon, cg8, rc1, 0xFFFFFFFFFFFFFFFF
	.else
	WCFX_IMM   cfx_smon, cg8, rc1, 0xFFFFFFFFFFFFFFFF
	.endif
	cfx2rd	cfx_hart, cg8, rc2, rd5
	add.si	rd5, 150
	cfx2rc	cfx_hart, cg8, rc4, rd5
	WCFX_IMM   cfx_hart, cg8, rc5, 1
	BURN	rd7, rb1
	@@ 0/1 屏蔽期只置 pending（源 cfxha 15）
	cfx2rd	cfx_hart, cg9, rc4, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg9, rc3, rd5
	REC	rd5

	@@ 放开本模式的掩码行 ⇒ 下一指令边界投递（timer 仍到期、源尚未 ack）
	.if TMODE == 0
	WCFX_IMM   cfx_umon, cg8, rc1, MASK_PATTERN
	.else
	WCFX_IMM   cfx_smon, cg8, rc1, MASK_PATTERN
	.endif

umode_wait_begin:
	set.rd	rd7, 300
umode_wait:
	add.si	rb5, 1
	add.si	rd7, -1
	br.nz	{rd7}?, [rb0, umode_wait]
umode_wait_end:
	@@ 投递未发生：签名缺槽 ⇒ 红
	set.rd	rd5, 0xDEAD0033
	REC	rd5
	jump	[rb0, fail_exit]

@@ ---------------------------------------------------------------------------
@@ 异步入口：cfx_hart 的 supv 单向量（三模式同一入口）
@@ 第一次进入记现场并做 escape/覆盖测试；第二次记覆盖并做屏蔽/ack；
@@ 第三次记放开掩码后的投递，然后收尾。
@@ ---------------------------------------------------------------------------
async_entry:
	@@ 精确点搜索阶段：rd20 = 1 时所有进入都走 jump 处理器
	br.nz	{rd20}?, [rb0, async_jump]
	set.rb	rb4, phase
	ld.o	rd22, [rb4, 0]
	add.si	rd22, 1
	st.o	rd22, [rb4, 0]
	set.rd	rd23, 1
	br.eq	{rd22, rd23}?, [rb0, async_phase1]
	set.rd	rd23, 2
	br.eq	{rd22, rd23}?, [rb0, async_phase2]
	jump	[rb0, async_phase3]

async_phase1:
	@@ 2-9 现场：rc0 prev_run_mode、rc1 prev_cfx_code、rc2 cause_ip、
	@@ rc3 src_frame、rc4 src_pending（投递后已清）、rc5 向量、rc6 固定 supv
	cfx2rd	cfx_hart, cg9, rc0, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg9, rc1, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg9, rc2, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg9, rc3, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg9, rc4, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg9, rc5, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg9, rc6, rd5
	REC	rd5
	@@ 9 一帧只计一次
	cfx2rd	cfx_hart, cg4, rc4, rd5
	REC	rd5

	@@ ---- escape imms18 = 2（imms20 = 8）：R2 不返回 ----
	@@ 当前 cfx 是 cfx_hart、src_frame != 0；若按所选帧无效 ⇒ CFXESC 进当前 cfx
	@@ （supv 行向量 = esc9_entry），不改变 cfx/运行模式/cg9。
	@@ 旧模型/注入“cg9 返回”时这里会直接跳回 cause_ip，签名随即错位。
	escape	cfx_hart, [excp_cause_ip, 8]
	swym	0

	@@ ---- 覆盖语义：不搬走现场，再次到期 ⇒ 整体覆盖 cg9 ----
	@@ 先关 timer 再设新 deadline、最后使能：这样“事件成立”只发生在使能写之后，
	@@ 投递边界 = 下一条指令（rearm_fallback）。
	WCFX_IMM   cfx_hart, cg8, rc5, 0
	cfx2rd	cfx_hart, cg8, rc2, rd5
	cfx2rc	cfx_hart, cg8, rc4, rd5
	WCFX_IMM   cfx_hart, cg8, rc5, 1
rearm_fallback:
	@@ 覆盖未发生（旧“帧活动期”只置 pending）时才会执行到这里
	set.rd	rd5, 0xDEAD0001
	REC	rd5
	jump	[rb0, fail_exit]

async_phase2:
	@@ 17-22 覆盖证据：prev = supv/cfx_hart，cause_ip = 再次武装后的下一条
	cfx2rd	cfx_hart, cg9, rc0, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg9, rc1, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg9, rc2, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg9, rc3, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg9, rc4, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg4, rc4, rd5
	REC	rd5

	@@ ---- supv 下屏蔽当前模式（smon 行）：只置 pending ----
	WCFX_IMM   cfx_smon, cg8, rc1, 0xFFFFFFFFFFFFFFFF
	cfx2rd	cfx_hart, cg8, rc2, rd5
	cfx2rc	cfx_hart, cg8, rc4, rd5
	WCFX_IMM   cfx_hart, cg8, rc5, 1
	BURN_SHORT	rd21, rb3
	cfx2rd	cfx_hart, cg9, rc4, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg9, rc3, rd5
	REC	rd5
	@@ ---- 源 ack：重装 timer_cmp ⇒ pending 落（仍屏蔽） ----
	WCFX_IMM   cfx_hart, cg8, rc4, 0xFFFFFFFFFFFFFFFF
	cfx2rd	cfx_hart, cg9, rc4, rd5
	REC	rd5
	@@ ---- 再武装（仍屏蔽）⇒ pending 重新置位 ----
	cfx2rd	cfx_hart, cg8, rc2, rd5
	cfx2rc	cfx_hart, cg8, rc4, rd5
	BURN_SHORT	rd21, rb3
	cfx2rd	cfx_hart, cg9, rc4, rd5
	REC	rd5
	@@ ---- 放开当前模式掩码 ⇒ 下一指令边界投递 ----
	WCFX_IMM   cfx_smon, cg8, rc1, MASK_PATTERN
pending_fallback:
	@@ 放开掩码后仍未投递时才会执行到这里
	set.rd	rd5, 0xDEAD0002
	REC	rd5
	jump	[rb0, fail_exit]

async_phase3:
	@@ 28-32 第三次进入：覆盖后的现场 + 投递扣除 pending
	cfx2rd	cfx_hart, cg9, rc0, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg9, rc2, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg9, rc3, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg9, rc4, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg4, rc4, rd5
	REC	rd5
	@@ 源 ack 后 pending = 0
	WCFX_IMM   cfx_hart, cg8, rc4, 0xFFFFFFFFFFFFFFFF
	cfx2rd	cfx_hart, cg9, rc4, rd5
	REC	rd5
	jump	[rb0, jump_setup]

@@ ---------------------------------------------------------------------------
@@ 精确点：在 `jump` 目标处到期（SimRISC-06 的 jump）
@@ 读 cycle 的延迟随平台不同（QEMU icount vs RTL 流水线），不能写死补偿；
@@ 从 delta=0 起每次 +1 cycle 重试，直到捕获到的 cause_ip == jump_target。
@@ 处理器在每次进入先 ack timer（电平源不会在读 cg9 期间重入）。
@@ ---------------------------------------------------------------------------
jump_setup:
	set.rd	rd20, 1
	set.rd	rd9, 0			@@ delta（cycle 偏移）
	set.rd	rd13, 0			@@ 尝试次数
	set.rb	rb2, jump_target	@@ 目标运行时地址（镜像不搬移）
	WCFX_IMM cfx_hart, cg8, rc4, 0xFFFFFFFFFFFFFFFF
	WCFX_IMM cfx_hart, cg8, rc5, 1
	cfx2rd	cfx_hart, cg8, rc2, rd3
	add.uo	{rd0, rd5}, rd3, rd9
	cfx2rc	cfx_hart, cg8, rc4, rd5
	jump	[rb2, rd0, 0]

jump_target:
	add.si	rd15, 1
	jump	[rb0, jump_target]

async_jump:
	@@ 先 ack（写全 1 落 pending），再读捕获；电平源不会在读期间重入
	WCFX_IMM cfx_hart, cg8, rc4, 0xFFFFFFFFFFFFFFFF
	cfx2rd	cfx_hart, cg9, rc2, rd5
	set.rb	rb2, jump_target
	rb2rd	rd6, rb2, 1
	cmp.uo	rd8, rd5, rd6
	set.rd	rd7, 0
	br.nz	{rd8}?, [rb0, jump_retry]
	@@ 命中目标边界：cause_ip == jump_target
	REC	rd5
	cfx2rd	cfx_hart, cg9, rc0, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg9, rc1, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg9, rc3, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg9, rc4, rd5
	REC	rd5
	set.rd	rd5, 1
	REC	rd5
	set.rd	rd20, 0
	jump	[rb0, done_ok]

jump_retry:
	add.si	rd13, 1
	set.rd	rd7, 64
	br.eq {rd13, rd7}?, [rb0, jump_fail]
	add.si	rd9, 1			@@ 晚一个 cycle
	WCFX_IMM cfx_hart, cg8, rc5, 1
	cfx2rd	cfx_hart, cg8, rc2, rd3
	add.uo	{rd0, rd5}, rd3, rd9
	cfx2rc	cfx_hart, cg8, rc4, rd5
	set.rb	rb2, jump_target
	jump	[rb2, rd0, 0]

jump_fail:
	set.rd	rd5, 0xBAD00002
	REC	rd5
	jump	[rb0, fail_exit]


@@ ---------------------------------------------------------------------------
@@ 同步 CFXESC 处理（escape imms18 = 2）：记 cfx_hart cg5 帧与 cg9 快照，
@@ 再用同步 cg5 帧 escape 回 escape 指令之后（+4）。
@@ ---------------------------------------------------------------------------
esc9_entry:
	cfx2rd	cfx_hart, cg5, rc2, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg5, rc4, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg5, rc0, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg5, rc1, rd5
	REC	rd5
	@@ cg9 不被 escape 改变（与异步捕获槽相等）
	cfx2rd	cfx_hart, cg9, rc0, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg9, rc1, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg9, rc2, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg9, rc3, rd5
	REC	rd5
	escape	cfx_hart, [excp_cause_ip, 4]
	swym	0

@@ ---------------------------------------------------------------------------
@@ 收尾
@@ ---------------------------------------------------------------------------
smon_fault:
	@@ supv 下的意外同步异常（如 CFXPERM）：记见证后快速失败
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
	PERM_OPEN_DELEG	cfx_smon
	PERM_OPEN_DELEG	cfx_umon
	PERM_OPEN	cfx_ptw
	PERM_MON_CLOSE

	.data
	.p2align 3
hphase:
	.dd.o64	0
phase:
	.dd.o64	0
sig_bytes:
	.dd.o64	0
