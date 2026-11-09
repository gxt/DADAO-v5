@@ tiny_smoke.S — Machine-v5-Tiny loadmem / boot closed-loop smoke program
@@ (m12-chipyard-003).
@@
@@ The BootROM is the static trampoline from `bootrom.S`: it loads SP and the
@@ fixed application entry (`ENTRY`, tests/shared/asm/machine-tiny.inc) and
@@ jumps there.  This program is that application; it is loaded into SRAM by
@@ the harness `+loadmem=` loader and executed from ENTRY.
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
	.globl	_start
_start:
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

	@@ 5. terminal: undefined instruction (no cfx / no semihosting on Tiny)
	.dd.t32	0x00000000

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
