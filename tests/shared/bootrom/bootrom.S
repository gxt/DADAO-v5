@@ bootrom.S — DADAO-v5 Machine-v5-Tiny trampoline/BootROM.
@@
@@ TESTCASES-091t (user ruling 2026-11-02): Tiny has **no cfx at all**
@@ (including cfx_power), cannot run in user mode, but semihosting is allowed.
@@ This ROM is only a trampoline: set SP from the profile and jump to the raw
@@ application entry.  No cfx2rc/trap/escape/user-mode switch is used here.
@@
@@ Geometry is injected by tests/shared/asm/machine-tiny.inc (generated from
@@ tests/shared/machine-profiles.yaml); no address literal is hand-written.

	.include "tests/shared/asm/machine-tiny.inc"
	.include "tests/shared/asm/machine.inc"

	.text
	.globl	_start
_start:
	LOAD_ADDR rb1, SP
	LOAD_ADDR rb2, ENTRY
	jump	[rb2, rd0, 0]
	swym	0
