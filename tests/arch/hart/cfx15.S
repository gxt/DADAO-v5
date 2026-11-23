@@ cfx15.S — `cfx_hart`（cfxha 15）RTL 探针（`m16-chipyard-021`，`ADR-0061` 修订）
@@
@@ 目的：在 **Kaiwu-Vast RTL（chipyard `WumingVastConfig`）** 上验证 `ADR-0061`
@@ 与 `spec/DADAO-12 §4.7`/`§5.4` 的 cfx_hart：
@@   * cg8 管理寄存器：hart_id / cycle / insn / timer_cmp / timer_ctrl；
@@   * cg9 **七槽**异步现场：rc0 prev_run_mode / rc1 prev_cfx_code / rc2 cause_ip /
@@     rc3 src_frame（HW/RO，位 = 源 cfxha）/ rc4 src_pending（HW/RO）/
@@     rc5 excp_vector / rc6 switch_run_mode（固定 supv = 2）；rc7–rc15 reserved；
@@   * 两个位图**软件写忽略、读回不变、不产生异常**（不报 CFXREG）；
@@   * 来源掩码在**当前运行模式 monitor** 的 `cg8 rc1`（bit15 = 源 cfxha 15，
@@     0 = 允许 / 1 = 屏蔽）：屏蔽期只置 `src_pending` 的 bit15，解除后补投；
@@   * 投递：一帧多源（本机只有一个源）→ `src_frame` = 位 15、pending 扣除、
@@     `excp_async_num` +1；帧活动期（`src_frame != 0`）新事件只置 pending；
@@   * 源 ack（重装 `timer_cmp`）后 pending 落；
@@   * `escape` 的 frame selector bit1（`imms18 = 2`）返回并**释放帧**
@@     （`src_frame` 清 0），不恢复任何来源掩码；
@@   * `imms18 = 3` / `imms18[17:2] != 0` ⇒ ILLI；
@@   * H/S/U 三模式下掩码都取**当前运行模式** monitor 的那一行（`--defsym
@@     TMODE=3/2/0`），投递目标都是 cfx_hart/supv。
@@
@@ **一份 case、三种运行模式**：本文件是唯一载体，汇编期用 `-defsym TMODE=`
@@ 选择目标运行模式（0 = umon/U、2 = smon/S、3 = hmon/H）；H 模式额外做寄存器面
@@ 与非法编码探针。期望值见 `check_cfx15.py`（现场从 `spec/DADAO-12` §1/§3.6/§4.7/
@@ §5.4、`.tao/adr/adr-0061-*.md`、`contract-see` §3/§6.1 与
@@ `contracts/opcodes.yaml` 派生）。
@@
@@ 入口约定：chipyard 固定 BootROM（`spec/Kaiwu §6.2`）以 cfx_power 在 hypv 跳到
@@ `ENTRY`。H 模式先 `trap cfx_hmon` 进入 hmon/hypv；U/S 模式按 `§5.2` 用
@@ `trap cfx_umon` / `trap cfx_smon` + 目标 cfx 的 hypv 行向量/切换值进入。
@@
@@ 不变量：
@@   * 签名槽顺序固定（见 checker 的 SLOTS），漏跑/多跑都判红；
@@   * `cause_ip` 只断言落在等待循环的符号区间内（中断边界取决于时序）；
@@   * 两个位图的期望值全由源 cfxha 派生（TIMER = cfx_hart = 15 ⇒ `1 << 15`）；
@@   * 期望值不从 RTL 观测值反推；探针只 `REC` 实测值。
@@
@@ 寄存器约定：探针体用 rd5–rd7、rb1–rb3、rb5；handler 用 rd20/rd21、rb3；
@@ rb30 = 签名写指针（任何处理器都不得写）；rd16/rb16 = semihosting；
@@ rb20 = hmon SRAM 基址（仅 H 的寄存器面探针使用）。
@@ **只在 `WumingVastConfig` 上跑**（Tiny 无 cfx15、无 U/S 模式）。

	.include "tests/shared/asm/signature.inc"

	.equ	ENTRY,   0xffffff010100
	.equ	SIG_BUF, 0xffffff015000
	.equ	SIG_N,   64
	.equ	EXITB,   0xffffff015800
	.equ	HMON_BASE, 0xffffff018000

	.ifndef	TMODE
	.equ	TMODE, 3
	.endif

	@@ `ADR-0061` D9：escape 的 imms18 = 2 选 cg9 帧（偏移 0）；3 非法。
	@@ 合法返回用汇编层 `imms20 = 8`（`spec/DADAO-12 §5.1`）；非法编码（3/4）
	@@ 汇编器会拒绝，故用原始编码字直接喂给核。
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
	SIG_BEGIN SIG_BUF, SIG_N
	@@ 清 `phase`（H 的 hmon 入口分派用）
	set.rb	rb1, phase
	set.rd	rd6, 0
	st.o	rd6, [rb1, 0]

	@@ ---- 共用初始化：cfx_hart 的异步入口 / 三行来源掩码 / 两轴放行 ----
	WCFX_LABEL cfx_hart, cg9, rc5, async_entry	@@ async_excp_vector
	@@ umon/smon 的 `cg8 rc1` 先放开源 cfxha 15（bit15 = 0）——U/S 体与 supv
	@@ 下的 handler（帧活动期再武装 timer）都要靠这两行；hmon 行留到 H 体里
	@@ 先验复位值（全 1）再改写
	WCFX_IMM   cfx_umon, cg8, rc1, MASK_PATTERN
	WCFX_IMM   cfx_smon, cg8, rc1, MASK_PATTERN
	@@ timer 关：cmp 全 1、ctrl 0
	WCFX_IMM   cfx_hart, cg8, rc4, 0xFFFFFFFFFFFFFFFF
	WCFX_IMM   cfx_hart, cg8, rc5, 0
	@@ 两轴放行：目标 cfx（cfx_hart）的 user/jail/supv cfxreg 源位清 0
	WCFX_IMM   cfx_hart, cg0, rc2, 0xFFFFFFFFFFFFFFF8
	WCFX_IMM   cfx_hart, cg1, rc2, 0xFFFFFFFFFFFFFFF8
	WCFX_IMM   cfx_hart, cg2, rc2, 0xFFFFFFFFFFFFFFF8
	@@ cg3 rc12 delegation：放开 cg8 / cg9（bit3 硬件恒 1）
	WCFX_IMM   cfx_hart, cg3, rc12, 0xFFFFFFFFFFFFFCF7

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
	set.rd	rd6, 56*8
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
	set.rb	rb1, phase
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
@@ H 测试体：寄存器面 + 保留/非法编码 + 屏蔽/投递/释放
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
	@@ 14 rc3 src_frame：HW/RO —— 写 PATTERN 被忽略、读回不变（帧空 = 0）
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
	@@ 17 rc6 switch：写 0 被忽略，读回 2（固定 supv）
	set.rd	rd6, 0
	cfx2rc	cfx_hart, cg9, rc6, rd6
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
	@@ 放开当前模式的掩码行 ⇒ **下一指令边界补投**（timer 仍到期、源尚未 ack）
	WCFX_IMM   cfx_hmon, cg8, rc1, MASK_PATTERN

	@@ ---- 投递：TIMER 到期 → cfx_hart + supv；handler 记 42-51 ----
wait_begin:
	set.rd	rd7, 300
wait_loop:
	add.si	rb5, 1
	add.si	rd7, -1
	br.nz	{rd7}?, [rb0, wait_loop]
wait_end:
	@@ 51 escape 返回见证
	set.rd	rd5, 0xC0DE0021
	REC	rd5
	@@ 52 escape 释放帧
	cfx2rd	cfx_hart, cg9, rc3, rd5
	REC	rd5
	@@ 53 来源掩码不随 escape 保存/恢复：hmon 行仍是放开值
	cfx2rd	cfx_hmon, cg8, rc1, rd5
	REC	rd5
	@@ 54 一帧只计一次：cfx_hart 的 excp_async_num（cg4 rc4）= 1
	cfx2rd	cfx_hart, cg4, rc4, rd5
	REC	rd5
	jump	[rb0, done_ok]

@@ ---------------------------------------------------------------------------
@@ U（umon + user）
@@ ---------------------------------------------------------------------------
setup_u:
	set.rb	rb1, sig_bytes
	set.rd	rd6, 16*8
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
	set.rd	rd6, 16*8
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
@@ U/S 共用测试体：屏蔽 → pending → 投递 → 无嵌套 → ack → escape
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
	@@ 2 投递前的见证（必须在放开掩码**之前**记，否则补投会先抢走槽序）
	set.rd	rd5, 0xC0DE0031
	REC	rd5

	@@ 放开本模式的掩码行 ⇒ 下一指令边界补投（timer 仍到期、源尚未 ack）
	.if TMODE == 0
	WCFX_IMM   cfx_umon, cg8, rc1, MASK_PATTERN
	.else
	WCFX_IMM   cfx_smon, cg8, rc1, MASK_PATTERN
	.endif

	@@ 3-12 投递：handler 记现场 / pending / 无嵌套 / ack
umode_wait_begin:
	set.rd	rd7, 300
umode_wait:
	add.si	rb5, 1
	add.si	rd7, -1
	br.nz	{rd7}?, [rb0, umode_wait]
umode_wait_end:
	@@ 13 escape 返回见证
	set.rd	rd5, 0xC0DE0032
	REC	rd5
	@@ 14 帧已释放
	cfx2rd	cfx_hart, cg9, rc3, rd5
	REC	rd5
	@@ 15 来源掩码不随 escape 保存/恢复
	.if TMODE == 0
	cfx2rd	cfx_umon, cg8, rc1, rd5
	.else
	cfx2rd	cfx_smon, cg8, rc1, rd5
	.endif
	REC	rd5
	jump	[rb0, done_ok]

@@ ---------------------------------------------------------------------------
@@ 异步入口：cfx_hart 的 supv 单向量（三模式同一入口）
@@ ---------------------------------------------------------------------------
async_entry:
	@@ 41/3-6 现场：rc0 prev_run_mode、rc1 prev_cfx_code、rc2 cause_ip、
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

	@@ 无嵌套：帧活动期再武装一次 timer（cmp = now，立即到期），只置 pending、
	@@ 不改现场。此刻运行模式是 supv ⇒ 取 smon 的掩码行（放开 bit15），
	@@ 所以"不进入"只能由 `src_frame != 0` 解释。
	cfx2rd	cfx_hart, cg8, rc2, rd5
	cfx2rc	cfx_hart, cg8, rc4, rd5
	@@ 处理器专用寄存器（不能动等待循环的 rd7/rb5）
	BURN_SHORT	rd21, rb3
	cfx2rd	cfx_hart, cg9, rc3, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg9, rc4, rd5
	REC	rd5

	@@ 源 ack：重装 timer_cmp（全 1 = 关闭）⇒ pending 落
	WCFX_IMM   cfx_hart, cg8, rc4, 0xFFFFFFFFFFFFFFFF
	cfx2rd	cfx_hart, cg9, rc4, rd5
	REC	rd5
	WCFX_IMM   cfx_hart, cg8, rc5, 0
	@@ escape：frame selector bit1 = 1（cg9 偏移 0）
	escape	cfx_hart, [excp_cause_ip, 8]
	swym	0

@@ ---------------------------------------------------------------------------
@@ 收尾
@@ ---------------------------------------------------------------------------
done_ok:
	DUMP_AND_EXIT 0

	.data
	.p2align 3
phase:
	.dd.o64	0
sig_bytes:
	.dd.o64	0
