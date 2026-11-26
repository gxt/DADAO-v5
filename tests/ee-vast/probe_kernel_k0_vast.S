@@ probe_kernel.S — Kaiwu-Vast K1 minimal kernel probe (m14-qemu-001 §8)
@@
@@ This is NOT Linux: it is the smallest possible kernel-shaped payload that
@@ proves the K1 handover (spec/Kaiwu §6.3.4) on QEMU.  It is entered by
@@ smon's `escape cfx_smon`（cg5 rc10 = kernel_base）at the VA kernel_base with
@@   rb16 = entry VA, rb17 = boot info VA, rb3 = 0, run mode supv,
@@   cfxcode smon (2), PTW on (PTBR = 0, prebuilt page table), async masked.
@@
@@ It never builds a page table and never writes the boot info page: it only
@@ reads them through the prebuilt mapping and records what it saw in the
@@ observation registers of the last `-d cpu` dump (task §8):
@@   rd5..rd15   boot info fields 0x00..0x40 in §6.3.3 order
@@   rd17..rd20  ptbr / page_size_log2 / hart_id / flags
@@   rd21..rd24  PTE[PTE_INDEX+0..3] read through VA (the page table page)
@@   rd25..rd27  rb16 / rb17 / rb3 as saved at entry
@@   rd28        non-zero 8-byte words in the 64 KiB page table page (expect 1)
@@   rd29        non-zero 8-byte words in boot info [0x60, page end) (expect 0)
@@   rd30        self-check failure mask (bit n-1 = check n failed; 0 = pass)
@@
@@ Self-check: every expectation is a --defsym value derived by
@@ tools/qemu/k0_boot_probe.py from contracts/linux-boot.yaml plus the actual
@@ image size, so the guest oracle never restates the implementation.
@@ Exit: semihosting SYS_EXIT (service 0x18, block in RAM).  Code 0 = all
@@ checks pass; 0xD0 | n = the first failing check (n as in README.md; for
@@ n >= 16 the low nibble aliases and rd30 identifies the exact check).
@@
@@ The SYS_EXIT block pointer is passed as the *PA* of the block: the
@@ semihosting responder reads it through QEMU's debug/identity translation
@@ (target/dadao/cpu.c), which does not walk the page table.  This is the
@@ observation channel only, not part of the boot ABI.


	@@ CHK64 idx, reg, exp: compare `reg` with the 64-bit constant `exp` (a
	@@ --defsym value derived from contracts/linux-boot.yaml) and leave on the
	@@ first mismatch (rd30 bit idx-1 + exit code 0xD0|idx).
	.macro	CHK64 idx, reg, exp
	set.rd	rd2, \exp
	cmp.uo	rd3, \reg, rd2
	br.z	{rd3}?, [rb0, 9f]
	set.rd	rd4, (\idx - 1)
	set.rd	rd3, 1
	shl.o	rd2, rd3, rd4
	or.o	rd30, rd30, rd2
	set.rd	rd1, (0x00d0 | \idx)
	jump	[rb0, pk_exit]
9:
	.endm

	.text
	.globl	_start

_start:
	@@ --- handover registers as seen at the first kernel instruction ---
	rb2rd	rd25, rb16, 1			@@ rb16 = entry VA
	rb2rd	rd26, rb17, 1			@@ rb17 = boot info VA
	rb2rd	rd27, rb3, 1			@@ rb3 (rbtp) = 0

	@@ --- boot info fields (§6.3.3 order) ---
	set.rb rb4, BI_VA
	ld.ut	rd5, [rb4, 0x00]		@@ magic
	ld.uw	rd6, [rb4, 0x04]		@@ version
	ld.uw	rd7, [rb4, 0x06]		@@ size
	ld.o	rd8, [rb4, 0x08]		@@ ram_base
	ld.o	rd9, [rb4, 0x10]		@@ ram_size
	ld.o	rd10, [rb4, 0x18]		@@ kernel_base
	ld.o	rd11, [rb4, 0x20]		@@ kernel_size
	ld.o	rd12, [rb4, 0x28]		@@ initramfs_base
	ld.o	rd13, [rb4, 0x30]		@@ initramfs_size
	ld.o	rd14, [rb4, 0x38]		@@ cmdline_base
	ld.o	rd15, [rb4, 0x40]		@@ cmdline_size
	ld.o	rd17, [rb4, 0x48]		@@ ptbr
	ld.ut	rd18, [rb4, 0x50]		@@ page_size_log2
	ld.ut	rd19, [rb4, 0x54]		@@ hart_id
	ld.o	rd20, [rb4, 0x58]		@@ flags

	@@ --- PTE[PTE_INDEX .. PTE_INDEX+3] through the prebuilt mapping ---
	set.rb rb4, PT_VA + PTE_INDEX * 8
	ld.o	rd21, [rb4, 0]
	ld.o	rd22, [rb4, 8]
	ld.o	rd23, [rb4, 16]
	ld.o	rd24, [rb4, 24]

	@@ --- page table page: non-zero 8-byte word count (expect 1) ---
	set.rb rb4, PT_VA
	set.rd	rd28, 0
	set.rd rd2, 0x0000000000002000	@@ 8192 entries
pk_pt_count:
	ld.o	rd63, [rb4, 0]
	br.z	{rd63}?, [rb0, pk_pt_next]
	add.si	rd28, 1
pk_pt_next:
	add.si	rb4, 8
	add.si	rd2, -1
	br.nz	{rd2}?, [rb0, pk_pt_count]

	@@ --- boot info page tail: non-zero count (expect 0) ---
	set.rb rb4, BI_VA + BI_SIZE
	set.rd	rd29, 0
	set.rd rd2, 0x0000000000001ff4	@@ (0x10000 - 0x60) / 8
pk_bi_count:
	ld.o	rd63, [rb4, 0]
	br.z	{rd63}?, [rb0, pk_bi_next]
	add.si	rd29, 1
pk_bi_next:
	add.si	rb4, 8
	add.si	rd2, -1
	br.nz	{rd2}?, [rb0, pk_bi_count]

	@@ --- self-check 1..15: the 15 boot info fields ---
	CHK64	1, rd5, EXP_MAGIC
	CHK64	2, rd6, EXP_VERSION
	CHK64	3, rd7, EXP_BI_SIZE
	CHK64	4, rd8, EXP_RAM_BASE
	CHK64	5, rd9, EXP_RAM_SIZE
	CHK64	6, rd10, EXP_KERNEL_BASE
	CHK64	7, rd11, EXP_KERNEL_SIZE
	CHK64	8, rd12, EXP_INITRAMFS_BASE
	CHK64	9, rd13, EXP_INITRAMFS_SIZE
	CHK64	10, rd14, EXP_CMDLINE_BASE
	CHK64	11, rd15, EXP_CMDLINE_SIZE
	CHK64	12, rd17, EXP_PTBR
	CHK64	13, rd18, EXP_PAGE_SHIFT
	CHK64	14, rd19, EXP_HART_ID
	CHK64	15, rd20, EXP_FLAGS

	@@ --- self-check 16..19: the four PTE words at the kernel-window index ---
	CHK64	16, rd21, EXP_PTE0
	CHK64	17, rd22, EXP_PTE1
	CHK64	18, rd23, EXP_PTE2
	CHK64	19, rd24, EXP_PTE3

	@@ --- self-check 20..21: page-table page / boot info page occupancy ---
	CHK64	20, rd28, EXP_PT_NONZERO
	CHK64	21, rd29, EXP_BI_TAIL_NONZERO

	@@ --- self-check 22..24: handover registers ---
	CHK64	22, rd25, EXP_ENTRY
	CHK64	23, rd26, EXP_BI_VA
	CHK64	24, rd27, EXP_RB3

	@@ --- all checks passed ---
	set.rd	rd1, 0
	jump	[rb0, pk_exit]

pk_exit:
	@@ SYS_EXIT (service 0x18): block = {reason, code}.  The block lives in
	@@ the probe's own RAM page (PA below) and is reached through the mapping
	@@ by VA; the pointer handed to semihosting is its PA (see file header).
	set.rb rb4, EXIT_BLOCK_VA
	set.rd rd2, 0x0000000000020026	@@ ADP_Stopped_ApplicationExit
	st.o	rd2, [rb4, 0]
	st.o	rd1, [rb4, 8]
	set.rb rb16, EXIT_BLOCK_PA
	set.rd rd16, 0x0000000000000018
	trap	cfx_umon, 0x3FF00
	swym	0
	jump	[rb0, pk_exit]
