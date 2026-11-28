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
	.include "tests/shared/asm/perm_hypv.inc"

	.ifndef	CCASE
	.equ	CCASE, 1
	.endif
	.ifndef	TMODE
	.equ	TMODE, 3
	.endif

	.equ	ENTRY,   0xffffff002000
	.equ	SIG_BUF, 0xffffff001000
	.equ	EXITB,   0xffffff000030
	.equ	HMON_BASE, 0x0fff00000000

	.if	CCASE == 1
	.equ	CSLOTS, 21
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
	@@ 测试侧两轴放行（`DIV-07` 关闭后 hypv 也判权；body 以 cfx_power 交付）：
	@@ 打开 cfx_ptw/cfx_cache 与 S/U 目标 monitor 的 hypv 源掩码，使下面的
	@@ 「模式行」写与 `trap` 不被来源掩码拒绝。
	PERM_MON_OPEN perm_mon

	@@ 页表：PTBR = 0（L1 在 PA 0；其 0x1000 号项在 PA 0x8000），开 PTW
	set.rd	rd6, 0
	cfx2rc	cfx_ptw, cg9, rc0, rd6
	set.rd	rd6, 1
	cfx2rc	cfx_ptw, cg8, rc8, rd6

	@@ S/U 可达（DIV-16 收窄）：cfx5 现在有 `commonRows`（cg0-cg3 模式行 +
	@@ `cg3 rc12` deleg + cg4/cg5/cg6 共享面）。两轴判权不放宽：
	@@   * 源 cfx 保持 `cfx_hmon`（与 `common/env-*` 同一交付方式）：本段仍在
	@@     hypv，先把 supv/user 行里「源 cfx = hmon」的 `cfxreg` 位清 0
	@@     （其余位保持屏蔽），只打开本探针需要的 cfx5；
	@@   * supv 还查目标 cfx5 的 `cg3 rc12`（复位全 1）——在 hypv 写 0x8
	@@     （整组开放，bit3 恒 1）；user 不查 deleg；
	@@   * 降模式经 **cfx_hmon** 的 `<mode>` 行（`trap cfx_hmon`），因此
	@@     `inner_cfx_code` 仍是 hmon，不同时把源 cfx 改成 smon/umon。
	.if	TMODE == 2
	@@ supv：**源 cfx = cfx_smon(2)**（降模式目标 = cfx_smon，hypv 行可写）。
	@@ cfx5 的 `cg2 rc2` 只清源位 2（0x...FB），其余来源保持屏蔽；
	@@ cfx5 的 `cg3 rc12 = 0x8`（整组开放，bit3 恒 1）是 supv 的 cg 授权。
	WCFX_IMM   cfx_cache, cg2, rc2, 0xFFFFFFFFFFFFFFFB
	WCFX_IMM   cfx_cache, cg3, rc12, 0x8
	@@ 收尾 `trap cfx_umon` 的源 cfx 也是 smon ⇒ 只清 cfx_umon 的 supv
	@@ `cfxtrap` 源位 2（保留其余位）
	WCFX_IMM   cfx_umon, cg2, rc0, 0xFFFFFFFFFFFFFFFB
	@@ 从 **hypv** 陷入 cfx_smon：用它的 hypv 行（cg3）选新运行模式
	WCFX_LABEL cfx_smon, cg3, rc10, c_body
	WCFX_IMM   cfx_smon, cg3, rc8, 2
	trap	cfx_smon, 0
	swym	0
	.elseif	TMODE == 0
	@@ user：源 cfx = cfx_umon(0)。cfx5 的 `cg0 rc2` 只清源位 0；
	@@ user 不查 `cg3 rc12`（`contract-see §3`）
	WCFX_IMM   cfx_cache, cg0, rc2, 0xFFFFFFFFFFFFFFFE
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

	@@ I+D 同选（CACHE-21）：`[15:14] = 11` 的合法操作组合（操作/范围两维
	@@ 两侧共用 ⇒ 同选面只有 clean/invalidate/flush 三条命令）。
	@@ 1) invalidate：两侧都丢弃（脏行不写回）⇒ 读回内存旧值
	ST8	A_D, M_D
	WCTRL	D_FLUSH_ALL
	ST8	A_D, N_D
	WADDR	PA_D
	WSIZE	64
	WCTRL	ID_INVAL_LINE
	LD8	A_D, rd5
	SIGUPD	rd5

	@@ 2) flush：I 侧丢弃 + D 侧写回 ⇒ 取指重取新码
	PATCH_CODE WORD_ID
	WADDR	PA_CODE
	WSIZE	64
	WCTRL	ID_FLUSH_LINE
	RUN_CODE c_id1
	REC_CODE c_id1

	@@ 3) clean：I 侧 no-op + D 侧写回 ⇒ 再失效后读回新值
	ST8	A_D, M_D
	WCTRL	D_FLUSH_ALL
	ST8	A_D, N_D
	WADDR	PA_D
	WSIZE	64
	WCTRL	ID_CLEAN_LINE
	WCTRL	D_INVAL_LINE
	LD8	A_D, rd5
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

	@@ 放行块（cfx_hmon/hypv 下打开目标 cfx 的 hypv 源掩码）
	.text
	.balign 4
perm_mon:
	PERM_OPEN	cfx_ptw
	PERM_OPEN	cfx_cache
	PERM_OPEN_DELEG	cfx_smon
	PERM_OPEN_DELEG	cfx_umon
	PERM_MON_CLOSE

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
