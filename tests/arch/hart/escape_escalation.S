@@ escape_escalation.S — RTL `escape cfxHA` 判据探针（`m18-chipyard-002`）
@@
@@ 目的：在 **Kaiwu-Vast RTL** 上覆盖 `escape` 的三条退出前判据
@@ （`spec/DADAO-12 §5.1/§5.3`，`ADR-0061` R3）：
@@   1. `rc11` **整字**写入目标模式 monitor 的 `cg15 rc3`（增量写反例会残留旧位）；
@@   2. 目标模式升权（`rc8 > inner_run_mode`）⇒ 当前 cfx 的 `CFXESC`，不改任何状态；
@@   3. 目标 cfx 未实现（`rc9 = 6`）⇒ 当前 cfx 的 `CFXESC`；
@@   4. `imms18 != 0` ⇒ `ILLI`（进入当前运行模式 monitor）。
@@
@@ 环境：RTL 固定 BootROM 以 cfx_power / hypv 交付 ENTRY（`spec/Kaiwu §6.2`）；
@@ `PERM_MON_OPEN` 先以 cfx_hmon 放行目标 cfx 的 hypv 掩码，再回到 cfx_power。
@@ 探针把 cfx_smon 的 hypv 向量/switch 设为 s_entry/supv 后 `trap cfx_smon`，
@@ 于是从 supv 发起升权/非法目标的 `escape`。成功 = `SYS_EXIT 0`；失败码：
@@   1 首次 trap 不是 CFXTRAP          2 rc11 整字恢复不符
@@   3 升权 escape 误落地             4 升权未报 CFXESC / info 不符
@@   5 未实现目标误落地               6 未实现目标未报 CFXESC
@@   7 imm3 escape 未报 ILLI          98 phase 越界  99 trap 返回
@@
@@ 链接：`cfx15.lds`（ENTRY + 0x0000 .text / +0x4000 .data）。

	.include "tests/shared/asm/machine-vast.inc"
	.include "tests/shared/asm/perm_hypv.inc"

	.equ	EXITB, 0xffffff000030
	.equ	ESC_RC11_PATTERN, 0x0123456789ABCDEF
	.equ	ESC_BAD_MASK, 0xFFFFFFFF00000000
	.equ	ESC_SMON_INFO, 0x000000007E080000	@@ (0x7E << 24) | (2 << 18)
	.equ	ESC_SMON_IMM3, 0x000000007E080003	@@ imms18 = 3（SBZ 非 0）

	.macro	WCFX_IMM ha, cg, rc, imm
	set.rd	rd6, \imm
	cfx2rc	\ha, \cg, \rc, rd6
	.endm
	.macro	WCFX_LABEL ha, cg, rc, lab
	set.rb	rb2, \lab
	rb2rd	rd6, rb2, 1
	cfx2rc	\ha, \cg, \rc, rd6
	.endm

	.macro	EXIT code
	set.rb	rb16, EXITB
	set.rd	rd4, 0x20026
	st.o	rd4, [rb16, 0]
	set.rd	rd4, \code
	st.o	rd4, [rb16, 8]
	set.zw	rd16, wp0, 0x18
	trap	cfx0, 0x3FF18
	swym	0
	.endm

	.text
	.globl	_start

_start:
	@@ 两轴放行（本探针只要求 smon 的 hypv 掩码被打开）。
	PERM_MON_OPEN perm_mon

	@@ cfx_smon：hypv 向量 = s_entry、hypv switch = supv；supv 向量/switch 同样
	@@ 指向 s_entry / supv（CFXESC 与 ILLI 都会进入当前模式的 smon 向量）；
	@@ deleg 只留 bit3（硬件固定 1），放行 supv 访问 smon 自己的 cg5/cg15。
	WCFX_LABEL cfx_smon, cg3, rc15, s_entry
	WCFX_IMM   cfx_smon, cg3, rc14, 2
	WCFX_LABEL cfx_smon, cg2, rc15, s_entry
	WCFX_IMM   cfx_smon, cg2, rc14, 2
	WCFX_IMM   cfx_smon, cg3, rc12, 8

	set.rb	rb1, phase
	set.rd	rd5, 0
	st.o	rd5, [rb1, 0]

	trap	cfx_smon, 0
	EXIT	99

	.balign	4
s_entry:
	cfx2rd	cfx_smon, cg5, rc4, rd5		@@ cause id
	set.rb	rb1, phase
	ld.o	rd6, [rb1, 0]
	set.rd	rd7, 0
	br.eq	{rd6, rd7}?, [rb0, s_phase0]
	set.rd	rd7, 1
	br.eq	{rd6, rd7}?, [rb0, s_phase1]
	set.rd	rd7, 2
	br.eq	{rd6, rd7}?, [rb0, s_phase2]
	set.rd	rd7, 3
	br.eq	{rd6, rd7}?, [rb0, s_phase3]
	EXIT	98

s_phase0:
	@@ 首次同步 trap 必须是 CFXTRAP（1 << 0）。
	set.rd	rd7, 1
	br.ne	{rd5, rd7}?, [rb0, fail1]
	@@ rc11 整字恢复：目标模式 supv → smon cg15 rc3 必须恰为 PATTERN。
	set.rd	rd5, 2
	cfx2rc	cfx_smon, cg5, rc8, rd5
	set.rd	rd5, 2
	cfx2rc	cfx_smon, cg5, rc9, rd5
	set.rd	rd5, esc_land
	cfx2rc	cfx_smon, cg5, rc10, rd5
	set.rd	rd5, ESC_RC11_PATTERN
	cfx2rc	cfx_smon, cg5, rc11, rd5
	escape	cfx_smon
	EXIT	99

esc_land:
	cfx2rd	cfx_smon, cg15, rc3, rd5
	set.rd	rd7, ESC_RC11_PATTERN
	br.ne	{rd5, rd7}?, [rb0, fail2]
	@@ 升权：目标模式 hypv（3）> 当前 supv（2）⇒ CFXESC，不得落地。
	set.rb	rb1, phase
	set.rd	rd5, 1
	st.o	rd5, [rb1, 0]
	set.rd	rd5, 3
	cfx2rc	cfx_smon, cg5, rc8, rd5
	set.rd	rd5, 2
	cfx2rc	cfx_smon, cg5, rc9, rd5
	set.rd	rd5, esc_bad
	cfx2rc	cfx_smon, cg5, rc10, rd5
	set.rd	rd5, ESC_BAD_MASK
	cfx2rc	cfx_smon, cg5, rc11, rd5
	escape	cfx_smon
esc_bad:
	EXIT	3

s_phase1:
	@@ 升权必须在切换任何状态前报 CFXESC（1 << 3），info = escape cfx_smon。
	set.rd	rd7, 8
	br.ne	{rd5, rd7}?, [rb0, fail4]
	cfx2rd	cfx_smon, cg5, rc5, rd5
	set.rd	rd7, ESC_SMON_INFO
	br.ne	{rd5, rd7}?, [rb0, fail4]
	@@ 目标 cfx 未实现（rc9 = 6）⇒ CFXESC。
	set.rb	rb1, phase
	set.rd	rd5, 2
	st.o	rd5, [rb1, 0]
	set.rd	rd5, 2
	cfx2rc	cfx_smon, cg5, rc8, rd5
	set.rd	rd5, 6
	cfx2rc	cfx_smon, cg5, rc9, rd5
	set.rd	rd5, esc_bad2
	cfx2rc	cfx_smon, cg5, rc10, rd5
	escape	cfx_smon
esc_bad2:
	EXIT	5

s_phase2:
	set.rd	rd7, 8
	br.ne	{rd5, rd7}?, [rb0, fail6]
	cfx2rd	cfx_smon, cg5, rc5, rd5
	set.rd	rd7, ESC_SMON_INFO
	br.ne	{rd5, rd7}?, [rb0, fail6]
	@@ imms18 != 0 ⇒ ILLI（1 << 8），进入当前模式 monitor（smon）。
	set.rb	rb1, phase
	set.rd	rd5, 3
	st.o	rd5, [rb1, 0]
	.dd.t32	ESC_SMON_IMM3
	EXIT	99

s_phase3:
	set.rd	rd7, 0x100
	br.ne	{rd5, rd7}?, [rb0, fail7]
	EXIT	0

fail1:
	EXIT	1
fail2:
	EXIT	2
fail4:
	EXIT	4
fail6:
	EXIT	6
fail7:
	EXIT	7

	@@ 放行块：以 cfx_hmon（源 cfx = 3）打开 cfx_smon 的 hypv 四类掩码。
	.balign	4
perm_mon:
	PERM_OPEN	cfx_smon
	PERM_MON_CLOSE

	.data
	.p2align 3
phase:
	.dd.o64	0
