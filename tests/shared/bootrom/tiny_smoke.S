@@ tiny_smoke.S — Machine-v5-Tiny loadmem / boot closed-loop smoke program
@@ (m12-chipyard-003; m12-chipyard-007 adds the crt front end).
@@
@@ m12-007: the application is `tiny_crt.o` + this object linked into one ELF;
@@ crt (``_start``, at the fixed entry ``ENTRY``) sets SP and falls through
@@ into the code below.  The BootROM fixed firmware (power -> hmon) jumps to
@@ that entry after the handoff (spec/Machine-v5 §6.2).  The image is loaded
@@ into SRAM by the harness `+loadmem=` loader.
@@
@@ It deliberately contains no syscall and no semihosting (both belong to
@@ m12-chipyard-004): the visible result is the SRAM store below plus the
@@ terminal undefined instruction, which stops the simulation
@@ (TestDriver `$stop`; QEMU reports the same undefined instruction).
@@
@@ Every instruction used here is part of the subset executed by the temporary
@@ `WumingCoreStub` interpreter (m12-chipyard-003); the real core replaces it
@@ from m12-chipyard-005 on.

	.include "tests/shared/asm/machine-tiny.inc"
	.include "tests/shared/asm/machine.inc"

	.equ	RESULT, ENTRY + 0x2000
	.equ	APP_DATA, ENTRY + 0x100
	.equ	APP_BSS, ENTRY + 0x108

	.text
	.globl	tiny_smoke_main
tiny_smoke_main:
	@@ 1. read the preset .rodata octa (proves the read-only data was loaded)
	LOAD_ADDR rb4, APP_DATA
	ld.o	rd10, [rb4, 0]

	@@ 2. read the .bss octa (must read zero: loadmem zero-fills p_memsz tail)
	LOAD_ADDR rb5, APP_BSS
	ld.o	rd11, [rb5, 0]

	@@ 3. build the magic 0x9abc_5678_1234_c0de in rd8 (integer instructions)
	set.zw	rd8, wp3, 0x9abc
	or.w	rd8, wp2, 0x5678
	or.w	rd8, wp1, 0x1234
	or.w	rd8, wp0, 0xc0de

	@@ 4. write it to SRAM and read it back
	LOAD_ADDR rb6, RESULT
	st.o	rd8, [rb6, 0]
	ld.o	rd9, [rb6, 0]

	@@ 5. terminal: SYS_EXIT(0).  m12-chipyard-019 routes synchronous faults
	@@ into the cfx_hmon vector (spec/Machine-v5 §4.4), so the m12-003
	@@ undefined-instruction terminator would be skipped by the handler
	@@ (`escape +4`) instead of stopping the core.  The parameter block lives in
	@@ the SRAM scratch octa above RESULT.
	LOAD_ADDR rb6, RESULT+0x10
	LOAD_ADDR rd8, 0x20026		@@ ADP_Stopped_ApplicationExit
	st.o	rd8, [rb6, 0]
	set.zw	rd8, wp0, 0x0000	@@ status 0
	st.o	rd8, [rb6, 8]
	set.zw	rd16, wp0, 0x0018	@@ SYS_EXIT
	LOAD_ADDR rb16, RESULT+0x10
	trap	cfx_hmon, 0x3FF18
smoke_spin:
	br.z	{rd0}?, [rb0, smoke_spin]

	.section .rodata
	.p2align 3
	.globl	APP_DATA
APP_DATA:
	.dd.o64	0x1122334455667788

	.section .bss
	.p2align 3
	.globl	APP_BSS
APP_BSS:
	.space	8
