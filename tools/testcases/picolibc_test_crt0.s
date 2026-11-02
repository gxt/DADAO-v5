@@ picolibc_test_crt0.s — stack-setup wrapper for the picolibc self-test harness
@@ (TESTCASES-042t).
@@
@@ QEMU's dadao-m1 "path A" (ELF over -kernel, components/qemu/patches/hw/dadao/
@@ dadao-machine.c.patch) jumps to e_entry with PC = e_entry and leaves the
@@ register file at its reset values — in particular rb1 (the stack pointer) is
@@ 0, because on the ELF path the ROM trampoline does not run.  picolibc's own
@@ crt0 (`crt0-semihost.o`, built from picocrt/shared/crt0.c) assumes the
@@ architecture start-up code has already established the stack; there is no
@@ `picocrt/machine/dadao` port, so nothing sets rb1.
@@
@@ This stub is linked with the entry symbol `_start`; picolibc's crt0.o is linked
@@ in with `--redefine-sym _start=_picolibc_start` (see the harness), so the flow
@@ is:
@@   _start (this stub): set rb1 = profile SP (0xffff_ff7e_ff00), then call
@@                       picolibc `_picolibc_start`
@@   __start (picolibc): init .data/.bss, run constructors, call main, exit()
@@
@@ The stub is placed in .text.start at ROM 0xffff_ffff_0000 (Tiny A scheme:
@@ e_entry in ROM, application in SRAM); picolibc __start clears BSS.
@@ Entry/exit conventions follow tests/shared/crt0/minimal_crt0.s and
@@ contract-semihosting.md §3/§5 (SYS_EXIT reaches the host $?).

	.include "tests/shared/asm/machine-tiny.inc"
	.include "tests/shared/asm/machine.inc"

	.section	.text.start,"ax"
	.globl	_start
_start:
	@@ rb1 = profile SP (48-bit, near the RAM top).
	LOAD_ADDR rb1, SP

	@@ Hand control to picolibc's start-up (renamed _picolibc_start).
	call	[rb0, _picolibc_start]

	@@ __start is __noreturn; this guard is unreachable.
	swym	0
