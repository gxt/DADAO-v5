@@ tests/arch/time/time_rtl.S — `cfx_time`（cfxha 34）RTL 探针（m16-chipyard-023）
@@
@@ 目的：在 **Kaiwu-Vast RTL（chipyard `WumingVastConfig`）** 上验证
@@ `spec/DADAO-12 §4.10` 的 `cfx_time`：per-system 全局时间计数器、**只读**、
@@ **没有中断**（per-hart 的比较与 `TIMER` 在 `cfx_hart §4.7`，本 cfx 不配置、
@@ 不等待任何中断）。
@@
@@ 一份载体、两条 case、三种运行模式（汇编期 `--defsym` 选择）：
@@
@@   `TCASE=1`（`arch-time-001`，7 槽，`TMODE=3/2/0` 各跑一次）：
@@     cg10 rc0 的 `time_freq` 与再读（RO）；隔约 900 条指令读两次 `time_value`
@@     并断言**单调 / 严格递增 / 增量有界**；`time_value` 高位置 0（epoch 合理）；
@@     与 `cfx_hart cg8 rc2 cycle` **同基准**（`contract-see §3`：1 count = 1 ns、
@@     单 hart 下读数相等 ⇒ 只判同基准，不判两者不等）。
@@   `TCASE=2`（`arch-time-002`，6 槽，只 `TMODE=3`）：
@@     `cg10 rc2`/`rc63` 保留 rc 读、`rc0`/`rc1` 的 RO 写 ⇒ `CFXREG`（cause_id =
@@     `1 << 2`，`contract-see §6.1`）；被拒的写不改 `time_freq`。**cfx34 没有
@@     `timer_cmp`/`timer_ctrl`**，rc2..rc63 的拒绝面就是这条的机械证据。
@@
@@ 运行模式（`§5.2`）：交付状态是 `cfx_power`/hypv（`spec/Kaiwu §6.2`）；
@@ `TMODE=3` 就地跑（hypv）；`TMODE=2/0` 用目标 monitor 的 hypv 行
@@ `switch_run_mode` + `excp_vector` 后 `trap` 进入（同 `tests/arch/hart/cfx15.S`）。
@@
@@ 两轴放行（`contract-see §3`）：在 hypv（降模式前）把 `cfx_time`/`cfx_hart` 的
@@ 三行源掩码全放开（0 = 允许所有源），并清各自 `cg3 rc12` 的对应 cg 位
@@ （`cfx_time` → bit10、`cfx_hart` → bit8；bit3 硬件恒 1）。RTL 的 hypv 行不
@@ 强制（`DIV-07`），S/U 行按目标 cfx 的 `<mode>_cfxreg` + deleg 正常判。
@@
@@ 故障观察（`TCASE=2`）：固件 hmon 的同步异常处理把 `excp_cause_id` 写进
@@ profile 的 fault-record 槽（`machine-vast.inc` 的 `FAULT_RECORD`）并从
@@ `cause_ip + 4` 复位 ⇒ 每条故障例先清槽、触发、再读槽（同 `tests/inst`）。
@@
@@ 寄存器约定：探针体用 rd5–rd15、rb2；rb30 = 签名写指针（`SIG_BEGIN` 另用
@@ rd20）；rb20 = fault-record 基址（仅 `TCASE=2`）。期望值见
@@ `tests/arch/time/time_oracle.py`（现场从 `spec/` + `.tao/contracts/` 派生）。
@@ **只在 `WumingVastConfig` 上跑**（Tiny 无 cfx34、无 S/U 模式）。

	.include "tests/shared/asm/signature.inc"

	.equ	ENTRY,   0xffffff010100
	.equ	SIG_BUF, 0xffffff015000
	.equ	SIG_N,   16			@@ 签名区容量（槽数 ≤ 16）
	.equ	EXITB,   0xffffff015800
	@@ RTL 的 hmon 是**共享的 Tiny 保存-跳转处理器**（`make build-bootrom` 的
	@@ `--hmon-elf $(TINY_BOOTROM_DIR)/hmon.elf`，`m16-chipyard-025`）：它的
	@@ cause_id 槽 = `hmon SRAM + 0xE0`、回落点 = `+0xF8`
	@@ （`tools/testcases/arch/build_tiny_bootrom.py` 的固定布局；地址取
	@@ `DadaoConfigs` 的 `hmonBase`）。**不能用** QEMU/gem5 的 `FAULT_RECORD`
	@@ —— RTL 本体开着 PTW，`0x7ffc_0000` 不在固件建的页表里（实测
	@@ `CFXMEM [57] NONPTW` 循环）。
	.equ	HMON_BASE, 0x0fff00000000

	.ifndef	TCASE
	.equ	TCASE, 1
	.endif
	.ifndef	TMODE
	.equ	TMODE, 3
	.endif
	.if	TCASE == 1
	.equ	SIG_SLOTS, 7
	.else
	.equ	SIG_SLOTS, 6
	.endif

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

@@ ---------------------------------------------------------------------------
	.text
	.globl	_start
_start:
	@@ 签名槽数（按 case）
	set.rb	rb1, sig_bytes
	set.rd	rd6, (SIG_SLOTS * 8)
	st.o	rd6, [rb1, 0]

	@@ 两轴放行：源掩码 0（允许所有源；本 case 只读时间）
	WCFX_IMM   cfx_time, cg0, rc2, 0
	WCFX_IMM   cfx_time, cg1, rc2, 0
	WCFX_IMM   cfx_time, cg2, rc2, 0
	@@ supv 访问 cfx_time 的 cg10 还需其 `cg3 rc12` bit10 = 0（bit3 恒 1）
	WCFX_IMM   cfx_time, cg3, rc12, 0xFFFFFFFFFFFFFBFF
	@@ 同基准读数用的 cfx_hart cg8：三行源掩码 + deleg bit8 = 0
	WCFX_IMM   cfx_hart, cg0, rc2, 0
	WCFX_IMM   cfx_hart, cg1, rc2, 0
	WCFX_IMM   cfx_hart, cg2, rc2, 0
	WCFX_IMM   cfx_hart, cg3, rc12, 0xFFFFFFFFFFFFFEFF

	.if	TCASE == 2
	jump	[rb0, reject_entry]
	.elseif	TMODE == 2
	@@ S（smon + supv）
	WCFX_LABEL cfx_smon, cg3, rc10, time_body
	WCFX_IMM   cfx_smon, cg3, rc8, 2
	trap	cfx_smon, 0
	swym	0
	.elseif	TMODE == 0
	@@ U（umon + user）
	WCFX_LABEL cfx_umon, cg3, rc10, time_body
	WCFX_IMM   cfx_umon, cg3, rc8, 0
	trap	cfx_umon, 0
	swym	0
	.else
	@@ H：交付状态即 cfx_power / hypv，就地跑（`spec/Kaiwu §6.2`）
	jump	[rb0, time_body]
	.endif

@@ ---------------------------------------------------------------------------
@@ TCASE=1：只读时间面（7 槽；三模式同一份槽序）
@@ ---------------------------------------------------------------------------
time_body:
	SIG_BEGIN SIG_BUF, SIG_SLOTS

	@@ 槽 0：time_freq（cg10 rc0，RO）
	cfx2rd	cfx_time, cg10, rc0, rd5
	REC	rd5

	@@ 槽 1：time_freq 再读（RO 稳定）
	cfx2rd	cfx_time, cg10, rc0, rd6
	REC	rd6

	@@ 第一次读数 t0（rd9）
	cfx2rd	cfx_time, cg10, rc1, rd9

	@@ 隔约 900 条指令（300 次迭代 × 3 条）
	set.rd	rd7, 300
t_gap:
	add.si	rb2, 1
	add.si	rd7, -1
	br.nz	{rd7}?, [rb0, t_gap]

	@@ 第二次读数 t1（rd10），紧邻的 t2（rd11）与 cfx_hart cycle（rd12）
	cfx2rd	cfx_time, cg10, rc1, rd10
	cfx2rd	cfx_time, cg10, rc1, rd11
	cfx2rd	cfx_hart, cg8, rc2, rd12

	@@ 槽 2：单调（t1 >= t0）
	cmp.uo	rd13, rd10, rd9
	set.rd	rd6, -1
	cmp.uo	rd14, rd13, rd6		@@ 0 ⇔ t1 < t0
	set.rd	rd5, 1
	br.nz	{rd14}?, [rb0, t_mono_rec]
	set.rd	rd5, 0
t_mono_rec:
	REC	rd5

	@@ 槽 3：严格递增（t1 > t0）
	set.rd	rd6, 1
	cmp.uo	rd14, rd13, rd6		@@ 0 ⇔ t1 > t0
	set.rd	rd5, 1
	br.z	{rd14}?, [rb0, t_strict_rec]
	set.rd	rd5, 0
t_strict_rec:
	REC	rd5

	@@ 槽 4：增量有界（高 32 位差 ∈ {0,1}）
	shr.uo	rd7, rd10, 32
	shr.uo	rd8, rd9, 32
	cmp.uo	rd13, rd7, rd8
	set.rd	rd6, -1
	cmp.uo	rd14, rd13, rd6		@@ 0 ⇔ hi(t1) < hi(t0)
	set.rd	rd5, 1
	br.nz	{rd14}?, [rb0, t_bound_rec]
	set.rd	rd5, 0
t_bound_rec:
	REC	rd5

	@@ 槽 5：epoch 合理（t0 高位置 0）
	shr.uo	rd7, rd9, 63
	set.rd	rd6, 0
	cmp.uo	rd14, rd7, rd6
	set.rd	rd5, 1
	br.z	{rd14}?, [rb0, t_epoch_rec]
	set.rd	rd5, 0
t_epoch_rec:
	REC	rd5

	@@ 槽 6：同基准（cycle >= t2 且同一 2^32 窗口）
	cmp.uo	rd13, rd12, rd11
	set.rd	rd6, -1
	cmp.uo	rd14, rd13, rd6		@@ 0 ⇔ cycle < t2
	shr.uo	rd7, rd12, 32
	shr.uo	rd8, rd11, 32
	cmp.uo	rd15, rd7, rd8		@@ 0 ⇔ 同一窗口
	set.rd	rd5, 1
	br.z	{rd14}?, [rb0, t_base_fail]
	br.z	{rd15}?, [rb0, t_base_rec]
t_base_fail:
	set.rd	rd5, 0
t_base_rec:
	REC	rd5

	jump	[rb0, done_ok]

@@ ---------------------------------------------------------------------------
@@ TCASE=2：保留 rc / RO 写的拒绝面（6 槽；只 hmon）
@@ ---------------------------------------------------------------------------
reject_entry:
	SIG_BEGIN SIG_BUF, SIG_SLOTS
	set.rb	rb20, HMON_BASE

	@@ 槽 0：time_freq（cg10 rc0，RO）
	cfx2rd	cfx_time, cg10, rc0, rd5
	REC	rd5

	@@ 槽 1：cg10 rc2（保留）读 ⇒ CFXREG
	st.o	rd0, [rb20, 0xE0]		@@ 清固件 cause 槽（不靠残留）
	set.rb	rb21, rf_rc2
	st.o	rb21, [rb20, 0xF8]		@@ 回落点 = 触发指令之后
	cfx2rd	cfx_time, cg10, rc2, rd6
rf_rc2:
	ld.o	rd5, [rb20, 0xE0]
	REC	rd5

	@@ 槽 2：cg10 rc63（保留，rc 上界）读 ⇒ CFXREG
	st.o	rd0, [rb20, 0xE0]
	set.rb	rb21, rf_rc63
	st.o	rb21, [rb20, 0xF8]
	cfx2rd	cfx_time, cg10, rc63, rd6
rf_rc63:
	ld.o	rd5, [rb20, 0xE0]
	REC	rd5

	@@ 槽 3：写 cg10 rc0（RO）⇒ CFXREG
	st.o	rd0, [rb20, 0xE0]
	set.rb	rb21, rf_w0
	st.o	rb21, [rb20, 0xF8]
	set.rd	rd6, 0
	cfx2rc	cfx_time, cg10, rc0, rd6
rf_w0:
	ld.o	rd5, [rb20, 0xE0]
	REC	rd5

	@@ 槽 4：写 cg10 rc1（RO）⇒ CFXREG
	st.o	rd0, [rb20, 0xE0]
	set.rb	rb21, rf_w1
	st.o	rb21, [rb20, 0xF8]
	set.rd	rd6, 0
	cfx2rc	cfx_time, cg10, rc1, rd6
rf_w1:
	ld.o	rd5, [rb20, 0xE0]
	REC	rd5

	@@ 槽 5：被拒的写没有改到 freq（仍 1 GHz）
	cfx2rd	cfx_time, cg10, rc0, rd5
	REC	rd5

	jump	[rb0, done_ok]

@@ ---------------------------------------------------------------------------
done_ok:
	DUMP_AND_EXIT 0

	@@ 数据（`sig_bytes` 由启动段按 case 填）
	.data
	.p2align 3
sig_bytes:
	.dd.o64	0
