@@ bootrom_app.S — Tiny sample application for the raw BootROM trampoline.
@@
@@ TESTCASES-091t (user ruling 2026-11-02): Tiny has no cfx and no user mode.
@@ This sample only uses ordinary loads/stores and semihosting SYS_EXIT; it does
@@ not use cfx2rd/cfx2rc/trap-to-cfx/escape.  It is loaded at the Tiny raw entry
@@ by the trampoline and exits with SYS_EXIT(0) on success, 0xE0 on failure.
@@
@@ Geometry comes from tests/shared/asm/machine-tiny.inc.

	.include "tests/shared/asm/machine-tiny.inc"
	.include "tests/shared/asm/machine.inc"

	.text
	.globl	_app
_app:
	@@ 1. RAM data round-trip at ENTRY + 1 MiB
	LOAD_ADDR rb4, ENTRY + 0x100000
	set.zw	rd8, wp0, 0xBEEF
	st.o	rd8, [rb4, 0]
	ld.o	rd9, [rb4, 0]
	cmp.uo	rd10, rd9, rd8
	br.nz	{rd10}?, [rb0, app_fail]

	@@ 2. stack round-trip through SP (rb1)
	set.zw	rd11, wp0, 0x5A5A
	st.o	rd11, [rb1, -8]
	ld.o	rd12, [rb1, -8]
	cmp.uo	rd13, rd12, rd11
	br.nz	{rd13}?, [rb0, app_fail]

	@@ 3. SYS_EXIT(0): {ADP_Stopped_ApplicationExit, 0}
	set.rb	rb16, EXIT_BLOCK
	set.zw	rd16, wp1, 0x0002
	or.w	rd16, wp0, 0x0026
	st.o	rd16, [rb16, 0]
	set.zw	rd16, wp0, 0x0000
	st.o	rd16, [rb16, 8]
	set.zw	rd16, wp0, 0x0018
	trap	cfx0, 0x3FF00
	swym	0

app_fail:
	@@ SYS_EXIT(0xE0)
	set.rb	rb16, EXIT_BLOCK
	set.zw	rd16, wp1, 0x0002
	or.w	rd16, wp0, 0x0026
	st.o	rd16, [rb16, 0]
	set.zw	rd16, wp0, 0x00E0
	st.o	rd16, [rb16, 8]
	set.zw	rd16, wp0, 0x0018
	trap	cfx0, 0x3FF00
	swym	0
