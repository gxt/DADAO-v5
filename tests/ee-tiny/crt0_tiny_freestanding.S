@@ tests_embench_crt0.S — minimal freestanding startup stub（Tiny embench；复制自 tests/ee-user/crt0_user.s）
@@
@@ Responsibilities (TESTCASES-091t; user ruling 2026-11-02):
@@   1. set SP = __stack_top (linker script / raw driver defines it);
@@   2. clear BSS [__bss_start, __bss_end) itself -- loaders do NOT zero it;
@@   3. call @main; the returned value becomes the SYS_EXIT status;
@@   4. report via semihosting SYS_EXIT (trap cfx0, 0x3FF00; this is not a cfx
@@      service: Tiny has no cfx but semihosting is allowed).
@@
@@ The stub is placed in .text.start: Tiny links it at the fixed SRAM entry
@@ (0xffff_ff00_2000, spec/Kaiwu §6.2; `kernel_reserved = 0`), Vast at the
@@ profile entry.  The linked-ELF pipeline uses
@@ tests_freestanding_tiny.lds / kernel_vast.lds; the single-TU CodeGen pipeline
@@ supplies __stack_top/__exit_block/__bss_* as assembler symbols and loads the
@@ raw blob at the Tiny kernel base (= the entry itself now).
@@
@@ Exit block: {ADP_Stopped_ApplicationExit (0x20026), code} at __exit_block
@@ (`MAIN_SRAM_BASE + 0x0030`; code at +0x38).
@@
@@ MemRAS: this crt leaves `ra0` (MRPTR) at its reset value 0 = MemRAS disabled
@@ (`spec/SimRISC-00 §2.4`; spec/Kaiwu §6.2.1 fixes the 4 KiB MemRAS at
@@ MAIN_SRAM_BASE+0x3F000 with MRPTR = +0x40000, set only by a harness that wants
@@ it).  No C program here depends on MemRAS spill.

	.section	.text.start,"ax"
	.globl	_start
_start:
	@@ 1. SP = __stack_top
	set.rb	rb1, __stack_top

	@@ 2. Clear BSS byte-wise: [__bss_start, __bss_end)
	set.rb	rb2, __bss_start
	set.rb	rb3, __bss_end
bss_check:
	cmp.uo	rd4, rb2, rb3
	br.n	{rd4}?, [rb0, bss_clear]
	jump	[rb0, bss_done]
bss_clear:
	st.b	rd0, [rb2, 0]
	add.si	rb2, 1
	jump	[rb0, bss_check]

bss_done:
	@@ 3. Call the program entry point; result returns in rd8 (M6).
	call	[rb0, main]

	@@ 4. SYS_EXIT argument block at __exit_block:
	@@    block[0] = 0x20026 (ADP_Stopped_ApplicationExit).
	set.rb	rb16, __exit_block
	set.zw	rd16, wp1, 0x0002
	or.w	rd16, wp0, 0x0026
	st.o	rd16, [rb16, 0]

	@@    block[1] = @main return value (low byte = guest exit code).
	st.o	rd8, [rb16, 8]

	@@ 5. rd16 = 0x18 (SYS_EXIT); trap with the semihosting tag.
	set.zw	rd16, wp0, 0x0018
	trap	cfx0, 0x3FF00
	swym	0
