@@ tests/arch/cache/cache_rtl.S — cfx5（`cfx_cache`）RTL 承载（`m16-testcases-009`）
@@
@@ 与 QEMU/gem5 的 body（`cache.body.S`）**同一组槽序与期望**
@@ （`cache_oracle.py`）：寄存器面、D 侧单行/范围/all、I 侧取指重取、使能门控、
@@ 非法编码拒绝面。区别只在载体：
@@
@@  * QEMU/gem5 用 `common/env-{hmon,smon,umon}` 与 step5 BootROM；
@@  * 本文件在 `WumingVastConfig` 上由固定 BootROM（power → hmon）交付，自己在
@@    `_start` 里建 PTW、开 cfx5 的两轴掩码，再按 `TMODE` 进 hmon/smon/umon。
@@
@@ 汇编期 `--defsym`：
@@   CCASE = 1 / 2 / 3（arch-cache-001/002/003）；4（off 分支）在 RTL 上没有
@@           机器开关 ⇒ `check_cache_rtl.py` 记 GAP（不跑本文件）；
@@   TMODE = 3 / 2 / 0（hypv / supv / user）。
@@
@@ 页表/地址/控制字/magic 全部来自 `cache_rtl_tables.inc`（`cache_oracle.py` 现场
@@ 生成；PTE 布局复用 `gen_cfx5_maint_tables.pte`）。数据行在 PA 0x4_1200 /
@@ 0x4_1240 / 0x4_5000 / 0x4_5100，代码行在 PA 0x8_1000；VA = PA + 2 TiB。
@@
@@ 故障观察（CCASE=3）：固定 hmon 的 save-and-jump 槽 = HMON_BASE + 0xE0
@@ （cause_id）、+0xF0（cause_info）、+0xF8（回落点）；每条故障例在触发前把
@@ 自己的 resume 写进 +0xF8（同 `cfx5_maint.S` 的写法）。
@@
@@ 只在 `WumingVastConfig` 上跑（Tiny 无 cfx5、无 S/U 模式）。

	.include "cache_rtl_tables.inc"
	.include "signature.inc"

	.ifndef	CCASE
	.equ	CCASE, 1
	.endif
	.ifndef	TMODE
	.equ	TMODE, 3
	.endif

	.equ	ENTRY,   0xffffff010100
	.equ	SIG_BUF, 0xffffff015000
	.equ	EXITB,   0xffffff015800
	.equ	HMON_BASE, 0x0fff00000000

	.if	CCASE == 1
	.equ	CSLOTS, 18
	.elseif	CCASE == 2
	.equ	CSLOTS, 12
	.else
	.equ	CSLOTS, 16
	.endif

@@ ---------------------------------------------------------------------------
@@ 宏
@@ ---------------------------------------------------------------------------
.macro WCFX_IMM ha, cg, rc, imm
	set.rd	rd6, \imm
	cfx2rc	\ha, \cg, \rc, rd6
.endm

.macro WCFX_LABEL ha, cg, rc, lab
	set.rb	rb2, \lab
	rb2rd	rd6, rb2, 1
	cfx2rc	\ha, \cg, \rc, rd6
.endm

.macro WCTRL word
	set.rd	rd6, \word
	cfx2rc	cfx_cache, cg8, rc9, rd6
.endm

.macro WADDR addr
	set.rd	rd7, \addr
	cfx2rc	cfx_cache, cg8, rc10, rd7
.endm

.macro WSIZE size
	set.rd	rd7, \size
	cfx2rc	cfx_cache, cg8, rc11, rd7
.endm

.macro WENABLE val
	set.rd	rd6, \val
	cfx2rc	cfx_cache, cg8, rc8, rd6
.endm

.macro ST8 addr, val
	set.rb	rb8, \addr
	set.rb	rb9, \val
	st.o	rb9, [rb8, 0]
.endm

.macro LD8 addr, dst
	set.rb	rb8, \addr
	ld.o	\dst, [rb8, 0]
.endm

.macro PATCH_CODE word
	set.rb	rb8, A_CODE
	set.rd	rd9, \word
	st.t	rd9, [rb8, 0]
.endm

.macro RUN_CODE resume
	set.rb	rb5, \resume
	set.rb	rb8, A_CODE
	jump	[rb8, rd0, 0]
.endm

.macro REC_CODE resume
\resume:
	or.o	rd5, rd20, rd0
	SIGUPD	rd5
.endm

.macro SETMEM
	ST8	A_R0, M_R0
	ST8	A_R1, M_R1
	ST8	A_D,  M_D
	ST8	A_OUT, M_OUT
	WCTRL	D_FLUSH_ALL
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

.macro DUMP_AND_EXIT
	SIG_DUMP_CHARS SIG_BUF, CSLOTS
	EXIT	0
.endm

@@ 故障例：把回落点写进固定 hmon 的 +0xF8（`aip.si` 的当前 IP + 16 ⇒ resume）。
.macro SET_FB
	aip.si	rb21, 0
	add.si	rb21, 16
	st.o	rb21, [rb20, 0xF8]
.endm

.macro REC_CAUSE
	ld.o	rd5, [rb20, 0xE0]
	SIGUPD	rd5
	ld.o	rd5, [rb20, 0xF0]
	SIGUPD	rd5
.endm

@@ ---------------------------------------------------------------------------
	.text
	.globl	_start
_start:
	@@ 页表：PTBR = 0（L1 在 PA 0；其 0x1000 号项在 PA 0x8000），开 PTW
	set.rd	rd6, 0
	cfx2rc	cfx_ptw, cg9, rc0, rd6
	set.rd	rd6, 1
	cfx2rc	cfx_ptw, cg8, rc8, rd6

	@@ **不写 cfx5 的 cg0-cg7**：RTL 的 cfx5 只有 cg8 面（`commonRows` 未开，
	@@ DIV-16）；写 cg0-cg3 ⇒ CFXREG。hmon 走 hypv 行（RTL 不强制），cg8 可访问；
	@@ S/U 的 cfx5 访问在 `check_cache_rtl.py` 记 GAP（同一原因），不执行本段。

	.if	TMODE == 2
	WCFX_LABEL cfx_smon, cg3, rc10, c_body
	WCFX_IMM   cfx_smon, cg3, rc8, 2
	trap	cfx_smon, 0
	swym	0
	.elseif	TMODE == 0
	WCFX_LABEL cfx_umon, cg3, rc10, c_body
	WCFX_IMM   cfx_umon, cg3, rc8, 0
	trap	cfx_umon, 0
	swym	0
	.else
	jump	[rb0, c_body]
	.endif

c_body:
	SIG_BEGIN SIG_BUF, CSLOTS

.if	CCASE == 1
	@@ ---------------- arch-cache-001 ----------------
	ST8	A_D, M_D
	PATCH_CODE WORD_OLD
	set.rb	rb8, A_CODE
	set.rd	rd9, WORD_JUMP
	st.t	rd9, [rb8, 4]
	WCTRL	D_FLUSH_ALL

	cfx2rd	cfx_cache, cg8, rc0, rd5
	SIGUPD	rd5
	cfx2rd	cfx_cache, cg8, rc8, rd5
	SIGUPD	rd5
	WENABLE	0
	cfx2rd	cfx_cache, cg8, rc8, rd5
	SIGUPD	rd5
	WENABLE	3
	cfx2rd	cfx_cache, cg8, rc8, rd5
	SIGUPD	rd5
	set.rd	rd6, 0xFFFFFFFFFFFFFFFF
	cfx2rc	cfx_cache, cg8, rc8, rd6
	cfx2rd	cfx_cache, cg8, rc8, rd5
	SIGUPD	rd5
	set.rd	rd7, 0xFFFFFFFFFFFFFFFF
	cfx2rc	cfx_cache, cg8, rc10, rd7
	cfx2rd	cfx_cache, cg8, rc10, rd5
	SIGUPD	rd5
	set.rd	rd7, C_PATTERN64
	cfx2rc	cfx_cache, cg8, rc10, rd7
	cfx2rd	cfx_cache, cg8, rc10, rd5
	SIGUPD	rd5
	cfx2rc	cfx_cache, cg8, rc11, rd7
	cfx2rd	cfx_cache, cg8, rc11, rd5
	SIGUPD	rd5

	ST8	A_D, N_D
	WADDR	PA_D
	WSIZE	64
	WCTRL	D_INVAL_LINE
	LD8	A_D, rd5
	SIGUPD	rd5

	ST8	A_D, N_D
	WADDR	PA_D
	WSIZE	64
	WCTRL	D_CLEAN_LINE
	WCTRL	D_INVAL_LINE
	LD8	A_D, rd5
	SIGUPD	rd5

	ST8	A_D, P_D
	WADDR	PA_D
	WSIZE	64
	WCTRL	D_FLUSH_LINE
	LD8	A_D, rd5
	SIGUPD	rd5

	PATCH_CODE WORD_INVAL
	WADDR	PA_CODE
	WSIZE	64
	WCTRL	D_CLEAN_LINE
	WCTRL	I_CLEAN_LINE
	WCTRL	I_INVAL_LINE
	RUN_CODE c_i1
	REC_CODE c_i1

	PATCH_CODE WORD_FLUSH
	WADDR	PA_CODE
	WSIZE	64
	WCTRL	D_CLEAN_LINE
	WCTRL	I_FLUSH_LINE
	RUN_CODE c_i2
	REC_CODE c_i2

	PATCH_CODE WORD_RANGE
	WADDR	PA_CODE
	WSIZE	64
	WCTRL	D_CLEAN_LINE
	WCTRL	I_INVAL_RANGE
	RUN_CODE c_i3
	REC_CODE c_i3

	ST8	A_OUT, N_EN
	WENABLE	0
	WADDR	PA_OUT
	WSIZE	64
	WCTRL	D_INVAL_LINE
	WENABLE	3
	WCTRL	D_CLEAN_LINE
	WCTRL	D_INVAL_LINE
	LD8	A_OUT, rd5
	SIGUPD	rd5

	WADDR	PA_NOLINE
	WSIZE	64
	WCTRL	D_INVAL_LINE
	WCTRL	D_CLEAN_RANGE
	WCTRL	I_FLUSH_RANGE
	set.rd	rd5, W_MMIO
	SIGUPD	rd5

	WSIZE	0
	WCTRL	NONE_SEL_FLUSH_RESV
	set.rd	rd5, W_SEL0
	SIGUPD	rd5
	WCTRL	ID_NONE_RANGE
	set.rd	rd5, W_NONE
	SIGUPD	rd5
	DUMP_AND_EXIT
.endif

.if	CCASE == 2
	@@ ---------------- arch-cache-002 ----------------
	SETMEM
	ST8	A_R0, N_R0
	ST8	A_R1, N_R1
	WADDR	PA_R0
	WSIZE	64
	WCTRL	D_INVAL_LINE
	LD8	A_R0, rd5
	SIGUPD	rd5
	LD8	A_R1, rd5
	SIGUPD	rd5

	SETMEM
	ST8	A_R0, N_R0
	ST8	A_R1, N_R1
	WADDR	PA_R0
	WSIZE	128
	WCTRL	D_INVAL_RANGE
	LD8	A_R0, rd5
	SIGUPD	rd5
	LD8	A_R1, rd5
	SIGUPD	rd5

	SETMEM
	ST8	A_R0, N_R0
	ST8	A_R1, N_R1
	WADDR	PA_R0
	WSIZE	128
	WCTRL	D_CLEAN_RANGE
	WSIZE	64
	WCTRL	D_INVAL_LINE
	WADDR	PA_R1
	WCTRL	D_INVAL_LINE
	LD8	A_R0, rd5
	SIGUPD	rd5
	LD8	A_R1, rd5
	SIGUPD	rd5

	SETMEM
	ST8	A_R0, P_R0
	ST8	A_R1, P_R1
	WADDR	PA_R0
	WSIZE	128
	WCTRL	D_FLUSH_RANGE
	LD8	A_R0, rd5
	SIGUPD	rd5
	LD8	A_R1, rd5
	SIGUPD	rd5

	SETMEM
	ST8	A_OUT, N_OUT
	ST8	A_R0, N_R0
	WADDR	PA_R0
	WSIZE	128
	WCTRL	D_INVAL_RANGE
	LD8	A_OUT, rd5
	SIGUPD	rd5

	SETMEM
	ST8	A_D, N_D
	WCTRL	D_INVAL_ALL
	LD8	A_D, rd5
	SIGUPD	rd5

	SETMEM
	ST8	A_D, N_D
	WCTRL	D_CLEAN_ALL
	WADDR	PA_D
	WSIZE	64
	WCTRL	D_INVAL_LINE
	LD8	A_D, rd5
	SIGUPD	rd5

	SETMEM
	ST8	A_D, P_D
	WCTRL	D_FLUSH_ALL
	LD8	A_D, rd5
	SIGUPD	rd5
	DUMP_AND_EXIT
.endif

.if	CCASE == 3
	@@ ---------------- arch-cache-003（只 hmon） ----------------
	set.rb	rb20, HMON_BASE
	set.rb	rb21, c_abort
	st.o	rb21, [rb20, 0xF8]

	cfx2rd	cfx_cache, cg8, rc0, rd5
	SIGUPD	rd5

	SET_FB
	cfx2rd	cfx_cache, cg8, rc9, rd5
c_f1:
	REC_CAUSE

	set.rd	rd6, 0
	SET_FB
	cfx2rc	cfx_cache, cg8, rc0, rd6
c_f2:
	REC_CAUSE

	SET_FB
	cfx2rd	cfx_cache, cg8, rc1, rd5
c_f3:
	REC_CAUSE

	WADDR	PA_D
	WSIZE	64
	set.rd	rd6, ID_CLEAN_RESV
	SET_FB
	cfx2rc	cfx_cache, cg8, rc9, rd6
c_f4:
	REC_CAUSE

	WSIZE	0
	set.rd	rd6, D_INVAL_RANGE
	SET_FB
	cfx2rc	cfx_cache, cg8, rc9, rd6
c_f5:
	REC_CAUSE

	WENABLE	0
	set.rd	rd6, D_CLEAN_RESV
	SET_FB
	cfx2rc	cfx_cache, cg8, rc9, rd6
c_f6:
	REC_CAUSE
	WENABLE	3

	SETMEM
	ST8	A_D, N_D
	WADDR	PA_D
	WSIZE	64
	set.rd	rd6, ID_CLEAN_RESV
	SET_FB
	cfx2rc	cfx_cache, cg8, rc9, rd6
c_f7:
	WADDR	PA_D
	WSIZE	64
	WCTRL	D_INVAL_LINE
	LD8	A_D, rd5
	SIGUPD	rd5

	SETMEM
	ST8	A_D, N_D
	WADDR	PA_D
	WSIZE	0
	set.rd	rd6, D_INVAL_RANGE
	SET_FB
	cfx2rc	cfx_cache, cg8, rc9, rd6
c_f8:
	WADDR	PA_D
	WSIZE	64
	WCTRL	D_CLEAN_LINE
	WCTRL	D_INVAL_LINE
	LD8	A_D, rd5
	SIGUPD	rd5

	cfx2rd	cfx_cache, cg8, rc0, rd5
	SIGUPD	rd5
	DUMP_AND_EXIT

c_abort:
	EXIT	126
.endif

	@@ 页表内容（+loadmem 按 p_paddr 装入）
	.section .pt_l1,"aw"
	.dd.o64	PTE_L1
	.section .pt_l2,"aw"
	.dd.o64	0			@@ L2[0]
	.dd.o64	0			@@ L2[1]
	.dd.o64	0			@@ L2[2]
	.dd.o64	0			@@ L2[3]
	.dd.o64	PTE_DATA		@@ L2[4]：页 4（R0/R1/D/OUT）
	.dd.o64	0
	.dd.o64	0
	.dd.o64	0
	.dd.o64	PTE_CODE		@@ L2[8]：页 8（代码行）
	.dd.o64	0
	.dd.o64	0
	.dd.o64	0
	.dd.o64	0
	.dd.o64	0
	.dd.o64	0
	.dd.o64	0
