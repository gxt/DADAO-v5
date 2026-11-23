@@ cfx15.S — `cfx_hart`（cfxha 15）RTL 探针（`m16-chipyard-021`）
@@
@@ 目的：在 **Kaiwu-Vast RTL（chipyard `WumingVastConfig`）** 上验证 `ADR-0060`
@@ （hart-first）与 `spec/DADAO-12 §4.7` 的 cfx_hart：
@@   * cg8 管理寄存器：hart_id / cycle / insn / timer_cmp / timer_ctrl；
@@   * 新增 cg9 异步现场（16 rc，`ADR-0060` D2）：prev_run_mode / prev_cfx_code /
@@     cause_ip / cause_id / saved_global_intr_mask / pending / vector /
@@     switch_run_mode（固定 supv=2）/ 五个 mask（位索引 = 源 cfxha 15）；
@@   * TIMER（`1 << 17`）到期投 **cfx_hart 的 supv 单向量**：写 cg9 现场、
@@     pending 位置 `1 << 17`（不是 cfxha 位 15）、mask 位 15；
@@   * 无嵌套：帧活动期新事件只置 pending；`escape` 的 frame selector bit1
@@     （`imms18 = 2`）返回并释放帧、恢复 mode/cfx 与 async_global_intr_mask；
@@     `imms18 = 3` / `imms18[17:2] != 0` ⇒ ILLI；
@@   * H/S/U 三模式下投递目标都是 cfx_hart/supv（`--defsym TMODE=3/2/0`）。
@@
@@ **一份 case、三种运行模式**：本文件是唯一载体，链接期用 `--defsym TMODE=`
@@ 选择目标运行模式（0 = umon/U、2 = smon/S、3 = hmon/H）；H 模式额外做寄存器面
@@ 与非法编码探针。期望值见 `check_cfx15.py`（现场从 `spec/DADAO-12` §3.6/§4.7、
@@ `ADR-0060` D2/D4、`contract-see` §6.1.1 与 `contracts/opcodes.yaml` 派生）。
@@
@@ 入口约定：chipyard 固定 BootROM（`spec/Kaiwu §6.2`）以 cfx_power 在 hypv 跳到
@@ `ENTRY`。H 模式先 `trap cfx_hmon` 进入 hmon/hypv；U/S 模式按 `§5.2` 用
@@ `trap cfx_umon` / `trap cfx_smon` + 目标 cfx 的 hypv 行向量/切换值进入。
@@
@@ 不变量：
@@   * 签名槽顺序固定（见 checker 的 SLOTS），漏跑/多跑都判红；
@@   * `cause_ip` 只断言落在等待循环的符号区间内（中断边界取决于时序）；
@@   * `cause_id` 记完整 64 位；TIMER = `1 << 17`；
@@   * 期望值不从 RTL 观测值反推；探针只 `REC` 实测值。
@@
@@ 寄存器约定：探针体用 rd5–rd7、rb1–rb3、rb5；handler 用 rd20/rd21；
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

	@@ `ADR-0060` D4：escape 的 imms18 = 2 选 cg9 帧（偏移 0）；3 非法。
	@@ 当前工具链的汇编器仍只接受 imms18[17:1] == 0，故用原始编码。
	.equ	ESC_HART_IMM2, (0x7E000000 | (15 << 18) | 2)
	.equ	ESC_HART_IMM3, (0x7E000000 | (15 << 18) | 3)
	.equ	ESC_HART_IMM4, (0x7E000000 | (15 << 18) | 4)

	.equ	PATTERN64, 0x123456789ABCDEF0
	.equ	TIMER_BIT_MASK, 0x0000000000020000	@@ 1 << 17
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

.macro FAIL code, marker
	set.rd	rd20, \marker
	REC	rd20
	DUMP_AND_EXIT \code
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

	@@ ---- 共用初始化：cfx_hart 的异步入口 / mask / 两轴放行 ----
	WCFX_LABEL cfx_hart, cg9, rc6, async_entry
	@@ 五个 mask：先允许源 cfxha 15（bit15 = 0）
	WCFX_IMM   cfx_hart, cg9, rc8,  MASK_PATTERN
	WCFX_IMM   cfx_hart, cg9, rc9,  MASK_PATTERN
	WCFX_IMM   cfx_hart, cg9, rc10, MASK_PATTERN
	WCFX_IMM   cfx_hart, cg9, rc11, MASK_PATTERN
	WCFX_IMM   cfx_hart, cg9, rc12, MASK_PATTERN
	@@ 帧空、pending 清、timer 关
	WCFX_IMM   cfx_hart, cg9, rc3, 0
	WCFX_IMM   cfx_hart, cg9, rc5, 0
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
	set.rd	rd6, 58*8
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
@@ H 测试体：寄存器面 + 保留/非法编码 + timer 投递
@@ ---------------------------------------------------------------------------
h_body:
	@@ 1 hart_id = 0
	cfx2rd	cfx_hart, cg8, rc0, rd5
	REC	rd5
	@@ 2/3 cycle 递增
	cfx2rd	cfx_hart, cg8, rc2, rd5
	REC	rd5
	add.si	rb1, 1
	add.si	rb1, 1
	add.si	rb1, 1
	cfx2rd	cfx_hart, cg8, rc2, rd5
	REC	rd5
	@@ 4/5 insn 递增
	cfx2rd	cfx_hart, cg8, rc3, rd5
	REC	rd5
	add.si	rb1, 1
	add.si	rb1, 1
	cfx2rd	cfx_hart, cg8, rc3, rd5
	REC	rd5
	@@ 6 timer_cmp RW
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
	@@ 12 cg9 rc0 prev_run_mode：写全 1，读回 2 位 = 3
	WCFX_IMM   cfx_hart, cg9, rc0, 0xFFFFFFFFFFFFFFFF
	cfx2rd	cfx_hart, cg9, rc0, rd5
	REC	rd5
	@@ 13 rc1 prev_cfx_code：写全 1，读回 6 位 = 63
	WCFX_IMM   cfx_hart, cg9, rc1, 0xFFFFFFFFFFFFFFFF
	cfx2rd	cfx_hart, cg9, rc1, rd5
	REC	rd5
	@@ 14 rc2 cause_ip：写全 1，读回 48 位
	WCFX_IMM   cfx_hart, cg9, rc2, 0xFFFFFFFFFFFFFFFF
	cfx2rd	cfx_hart, cg9, rc2, rd5
	REC	rd5
	@@ 15 rc3 cause_id：整 64 位往返（随后清零释放）
	WCFX_IMM   cfx_hart, cg9, rc3, PATTERN64
	cfx2rd	cfx_hart, cg9, rc3, rd5
	REC	rd5
	WCFX_IMM   cfx_hart, cg9, rc3, 0
	@@ 16 rc4 saved_global_intr_mask
	WCFX_IMM   cfx_hart, cg9, rc4, PATTERN64
	cfx2rd	cfx_hart, cg9, rc4, rd5
	REC	rd5
	@@ 17 rc5 pending（timer 关闭，无源置位）
	set.rd	rd6, PATTERN64
	cfx2rc	cfx_hart, cg9, rc5, rd6
	cfx2rd	cfx_hart, cg9, rc5, rd5
	REC	rd5
	WCFX_IMM   cfx_hart, cg9, rc5, 0
	@@ 18 rc6 vector：写全 1，读回 48 位且低 2 位 0
	WCFX_IMM   cfx_hart, cg9, rc6, 0xFFFFFFFFFFFFFFFF
	cfx2rd	cfx_hart, cg9, rc6, rd5
	REC	rd5
	@@ 恢复真向量（后面的 timer 投递必须落到 async_entry）
	WCFX_LABEL cfx_hart, cg9, rc6, async_entry
	@@ 19 rc7 switch：写 0 被忽略，读回 2（固定 supv）
	set.rd	rd6, 0
	cfx2rc	cfx_hart, cg9, rc7, rd6
	cfx2rd	cfx_hart, cg9, rc7, rd5
	REC	rd5
	@@ 20-24 五个 mask：整 64 位往返
	WCFX_IMM   cfx_hart, cg9, rc8, PATTERN64
	cfx2rd	cfx_hart, cg9, rc8, rd5
	REC	rd5
	WCFX_IMM   cfx_hart, cg9, rc9, PATTERN64
	cfx2rd	cfx_hart, cg9, rc9, rd5
	REC	rd5
	WCFX_IMM   cfx_hart, cg9, rc10, PATTERN64
	cfx2rd	cfx_hart, cg9, rc10, rd5
	REC	rd5
	WCFX_IMM   cfx_hart, cg9, rc11, PATTERN64
	cfx2rd	cfx_hart, cg9, rc11, rd5
	REC	rd5
	WCFX_IMM   cfx_hart, cg9, rc12, PATTERN64
	cfx2rd	cfx_hart, cg9, rc12, rd5
	REC	rd5

	@@ 25-27 保留 rc（cg9 rc13）⇒ CFXREG：cause_id / cause_info / 见证
	cfx2rd	cfx_hart, cg9, rc13, rd5
	set.rd	rd5, 0xC0DE0013
	REC	rd5
	@@ 28-30 保留 rc（cg9 rc14）
	cfx2rd	cfx_hart, cg9, rc14, rd5
	set.rd	rd5, 0xC0DE0018
	REC	rd5
	@@ 31-33 保留 rc（cg9 rc15）
	cfx2rd	cfx_hart, cg9, rc15, rd5
	set.rd	rd5, 0xC0DE0019
	REC	rd5
	@@ 34-36 写 RO（cg8 rc0）⇒ CFXREG：cause_id / cause_info / 见证
	set.rd	rd6, 0
	cfx2rc	cfx_hart, cg8, rc0, rd6
	set.rd	rd5, 0xC0DE0014
	REC	rd5
	@@ 37-39 读保留（cg8 rc1）⇒ CFXREG：cause_id / cause_info / 见证
	cfx2rd	cfx_hart, cg8, rc1, rd5
	set.rd	rd5, 0xC0DE0015
	REC	rd5
	@@ 40-42 escape imms18=3 ⇒ ILLI：cause_id / cause_info / 见证
	.dd.t32	ESC_HART_IMM3
	set.rd	rd5, 0xC0DE0016
	REC	rd5
	@@ 43-45 escape imms18=4（[17:2] ≠ 0）⇒ ILLI：cause_id / cause_info / 见证
	.dd.t32	ESC_HART_IMM4
	set.rd	rd5, 0xC0DE0017
	REC	rd5

	@@ ---- 46/47 masked pending：屏蔽期只置 pending、不投递 ----
	@@ 寄存器面测试把五个 mask 写成了 PATTERN（bit15 = 1），恢复为允许源 15
	WCFX_IMM   cfx_hart, cg9, rc9,  MASK_PATTERN
	WCFX_IMM   cfx_hart, cg9, rc10, MASK_PATTERN
	WCFX_IMM   cfx_hart, cg9, rc11, MASK_PATTERN
	WCFX_IMM   cfx_hart, cg9, rc12, MASK_PATTERN
	WCFX_IMM   cfx_hart, cg9, rc8, 0xFFFFFFFFFFFFFFFF	@@ bit15 = 1（屏蔽）
	WCFX_IMM   cfx_hart, cg9, rc5, 0
	cfx2rd	cfx_hart, cg8, rc2, rd5
	add.si	rd5, 150
	cfx2rc	cfx_hart, cg8, rc4, rd5
	WCFX_IMM   cfx_hart, cg8, rc5, 1
	BURN	rd7, rb1
	cfx2rd	cfx_hart, cg9, rc5, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg9, rc3, rd5
	REC	rd5
	WCFX_IMM   cfx_hart, cg8, rc4, 0xFFFFFFFFFFFFFFFF
	WCFX_IMM   cfx_hart, cg8, rc5, 0
	WCFX_IMM   cfx_hart, cg9, rc5, 0
	WCFX_IMM   cfx_hart, cg9, rc8, MASK_PATTERN

	@@ ---- 投递：TIMER 到期 → cfx_hart + supv；handler 记 48-55 ----
	cfx2rd	cfx_hart, cg8, rc2, rd5
	add.si	rd5, 150
	cfx2rc	cfx_hart, cg8, rc4, rd5
	WCFX_IMM   cfx_hart, cg8, rc5, 1
wait_begin:
	set.rd	rd7, 300
wait_loop:
	add.si	rb5, 1
	add.si	rd7, -1
	br.nz	{rd7}?, [rb0, wait_loop]
wait_end:
	@@ 56 escape 返回见证
	set.rd	rd5, 0xC0DE0021
	REC	rd5
	@@ 57 escape 释放帧
	cfx2rd	cfx_hart, cg9, rc3, rd5
	REC	rd5
	@@ 58 async_global_intr_mask 已恢复
	cfx2rd	cfx_hart, cg9, rc8, rd5
	REC	rd5
	jump	[rb0, done_ok]

@@ ---------------------------------------------------------------------------
@@ U（umon + user）
@@ ---------------------------------------------------------------------------
setup_u:
	set.rb	rb1, sig_bytes
	set.rd	rd6, 14*8
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
	set.rd	rd6, 14*8
	st.o	rd6, [rb1, 0]
	WCFX_LABEL cfx_smon, cg3, rc10, s_entry
	WCFX_IMM   cfx_smon, cg3, rc8, 2
	trap	cfx_smon, 0
	swym	0

s_entry:
	jump	[rb0, mode_body]

@@ ---------------------------------------------------------------------------
@@ U/S 共用测试体：masked pending + 投递（目标固定 cfx_hart/supv）
@@ ---------------------------------------------------------------------------
mode_body:
	@@ 0/1 masked pending：bit15=1 时只置 pending（1<<17）
	WCFX_IMM   cfx_hart, cg9, rc8, 0xFFFFFFFFFFFFFFFF
	WCFX_IMM   cfx_hart, cg9, rc5, 0
	cfx2rd	cfx_hart, cg8, rc2, rd5
	add.si	rd5, 150
	cfx2rc	cfx_hart, cg8, rc4, rd5
	WCFX_IMM   cfx_hart, cg8, rc5, 1
	BURN	rd7, rb1
	cfx2rd	cfx_hart, cg9, rc5, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg9, rc3, rd5
	REC	rd5
	WCFX_IMM   cfx_hart, cg8, rc4, 0xFFFFFFFFFFFFFFFF
	WCFX_IMM   cfx_hart, cg8, rc5, 0
	WCFX_IMM   cfx_hart, cg9, rc5, 0
	WCFX_IMM   cfx_hart, cg9, rc8, MASK_PATTERN

	@@ 2 投递前的见证（屏蔽已放开）
	set.rd	rd5, 0xC0DE0031
	REC	rd5

	@@ 3-10 投递：handler 记 prev_mode/prev_cfx/cause_ip/cause_id/saved/pending/
	@@      no-nest cause/pending
	cfx2rd	cfx_hart, cg8, rc2, rd5
	add.si	rd5, 150
	cfx2rc	cfx_hart, cg8, rc4, rd5
	WCFX_IMM   cfx_hart, cg8, rc5, 1
umode_wait_begin:
	set.rd	rd7, 300
umode_wait:
	add.si	rb5, 1
	add.si	rd7, -1
	br.nz	{rd7}?, [rb0, umode_wait]
umode_wait_end:
	@@ 11 escape 返回见证
	set.rd	rd5, 0xC0DE0032
	REC	rd5
	@@ 12 帧已释放
	cfx2rd	cfx_hart, cg9, rc3, rd5
	REC	rd5
	@@ 13 async_global_intr_mask 已恢复
	cfx2rd	cfx_hart, cg9, rc8, rd5
	REC	rd5
	jump	[rb0, done_ok]

@@ ---------------------------------------------------------------------------
@@ 异步入口：cfx_hart 的 supv 单向量（三模式同一入口）
@@ ---------------------------------------------------------------------------
async_entry:
	@@ 37/4-6-7-8-9-10 的公共现场（H）或 3-10（U/S）：顺序由 checker 按模式切
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

	@@ 无嵌套：帧活动期再武装一次 timer，只置 pending、不改现场
	cfx2rd	cfx_hart, cg8, rc2, rd5
	add.si	rd5, 10
	cfx2rc	cfx_hart, cg8, rc4, rd5
	WCFX_IMM   cfx_hart, cg8, rc5, 1
	@@ 处理器专用寄存器（不能动等待循环的 rd7/rb5）
	BURN_SHORT	rd21, rb3
	cfx2rd	cfx_hart, cg9, rc3, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg9, rc5, rd5
	REC	rd5

	@@ 关闭 timer、清 pending（帧由 escape 释放）
	WCFX_IMM   cfx_hart, cg8, rc4, 0xFFFFFFFFFFFFFFFF
	WCFX_IMM   cfx_hart, cg8, rc5, 0
	WCFX_IMM   cfx_hart, cg9, rc5, 0
	@@ escape：frame selector bit1 = 1（cg9 偏移 0）
	.dd.t32	ESC_HART_IMM2
	swym	0

@@ ---------------------------------------------------------------------------
@@ 收尾
@@ ---------------------------------------------------------------------------
done_ok:
	DUMP_AND_EXIT 0

wrong_mode:
	set.rd	rd20, 0xDEAD0001
	REC	rd20
	DUMP_AND_EXIT 0xE1

	.data
	.p2align 3
phase:
	.dd.o64	0
sig_bytes:
	.dd.o64	0
