@@ smon.S — DADAO-v5 step5 smon stage (INTEG-046t; ADR-0043 D5/D10/D11)
@@
@@ Linked at the smon SRAM base 0x0bff_0000_0000 (64 KiB) and entered by
@@ `trap cfx_smon, <boot_magic>` from hmon.  It:
@@   1. checks the trap cause (CFXTRAP + boot magic 0x30001), else exits 0xB8;
@@   2. builds the first page table in cfx_pmem SRAM (64 KiB zero page, four
@@      PTEs at offset 0) and copies it to PA 0 with the cg15 DMA: PTBR=0,
@@      four 512 MiB superpages at L1 index 0-3 mapping
@@      VA [0, 2 GiB) -> PA [0, 2 GiB) (ADR-0043 D10);
@@   3. enables PTW and checks VA->PA in both data directions with DMA;
@@   4. reads the power BootROM header at its fixed address (hmon opened only
@@      cfx_power supv cfxmem bit2 for this; the power delegation stays closed);
@@   5. writes the three chain markers and the poison words into registers
@@      rd5-rd14 for the `-d cpu` dump, then SYS_EXIT(0).
@@
@@ Observation registers (probe compares the last dump block):
@@   rd5  VA write -> VA read magic
@@   rd6  DMA PA 0x12000 -> SRAM readback of the same magic
@@   rd7  DMA PA 0x11000 (written from SRAM) -> VA read magic2
@@   rd8  cfx_ptw_ptbr readback (0)
@@   rd9  cfx_ptw_enable readback (1)
@@   rd10 power marker (RAM 0x10000, read through the page table)
@@   rd11 hmon marker (mirrored by hmon to RAM 0x10008)
@@   rd12 smon marker (smon SRAM 0x0e00, mirrored to RAM 0x10010)
@@   rd13 OR of the power/hmon poison words (must stay 0)
@@   rd14 PTE0 readback via DMA from PA 0 (PTE1-3 kept in rd23-rd25)
@@   rd15 DMA status of the page-table copy (DONE = 2)
@@   rd17/rd18/rd19 cg_reg_deleg readback of cfx_ptw/cfx_pmem/cfx_smon (0x8)
@@   rd20 power BootROM header word at BOOTROM_BASE (0x4442_4f54_0001_0002)
@@   rd21 cfx_power supv cfxmem (0xffff_ffff_ffff_fff3: only bit2 cleared)
@@   rd22 cfx_power cg_reg_deleg (all ones: never opened)
@@
@@ Exit channel: semihosting SYS_EXIT with the block in smon SRAM.

	.macro	LD64 rd, w0, w1, w2, w3
	set.zw	\rd, wp0, \w0
	.if \w1 != 0
	or.w	\rd, wp1, \w1
	.endif
	.if \w2 != 0
	or.w	\rd, wp2, \w2
	.endif
	.if \w3 != 0
	or.w	\rd, wp3, \w3
	.endif
	.endm

	.include "tests/shared/asm/machine-vast.inc"
	.include "tests/shared/asm/machine.inc"

	.text
	.globl	_start
_start:
	LD64	rb1, 0xfff0, 0x0000, 0x0bff, 0x0000	@@ smon rbsp

	@@ --- 1. trap cause / magic check (CFXTRAP = 1<<0, magic 0x30001) ---
	cfx2rd	cfx_smon, cg5, rc2, rd6
	LD64	rd7, 0x0001, 0x0000, 0x0000, 0x0000
	cmp.uo	rd2, rd6, rd7
	br.nz	{rd2}?, [rb0, smon_exit_b8]
	cfx2rd	cfx_smon, cg5, rc4, rd6
	LD64	rd7, 0xffff, 0x0003, 0x0000, 0x0000
	and.o	rd6, rd6, rd7
	LD64	rd7, 0x0001, 0x0003, 0x0000, 0x0000
	cmp.uo	rd2, rd6, rd7
	br.nz	{rd2}?, [rb0, smon_exit_b8]

	@@ --- 2a. clear the 64 KiB cfx_pmem SRAM (page-table page) ---
	@@ rd8-rd63 are still zero here; 146 * 56 octas + 16 octas = 64 KiB.
	LD64	rb3, 0x0000, 0x0000, 0x83ff, 0x0000
	LD64	rd6, 0x0092, 0x0000, 0x0000, 0x0000	@@ 146
smon_clear:
	stm.o	{rd8:rd63}, [rb3, rd0]
	add.si	rb3, 448
	add.si	rd6, -1
	br.nz	{rd6}?, [rb0, smon_clear]
	stm.o	{rd8:rd23}, [rb3, rd0]

	@@ --- 2a2. read the power BootROM header at its fixed address (R6) ---
	@@ Source cfx2/supv; requires cfx_power.supv.cfxmem bit2 = 0 (hmon).
	@@ rd20 is cleared first so a rejected read fails visibly, and it is read
	@@ after the SRAM clear because the clear loop uses rd8-rd63 as zeros.
	LD64	rd20, 0x0000, 0x0000, 0x0000, 0x0000
	LOAD_ADDR rb4, BOOTROM_BASE
	ld.o	rd20, [rb4, 0]

	@@ --- 2b. four L1 PTEs at SRAM offset 0 (L1 index 0-3) ---
	@@ HSJU=0xC (H=1, S=1, U=J=0), PPN[55:29]=i, SPF=0xFF,
	@@ flags P/SP/D/A/G/X/W/R = 0xEF (spec/DADAO-12 §2.2.3, ADR-0043 D10).
	@@ The template starts at PMEM_BASE + 0 so the 2c copy lands the PTEs at
	@@ PA 0..0x18; a non-zero offset here would put them at that PA instead.
	LD64	rb3, 0x0000, 0x0000, 0x83ff, 0x0000
	LD64	rd6, 0x0000, 0x0000, 0x0000, 0x0000	@@ template offset 0 in PMEM SRAM
	add.o	rb4, rb3, rd6
	LD64	rd6, 0xffef, 0x0000, 0x0000, 0xc000	@@ PTE0: PPN 0
	st.o	rd6, [rb4, 0]
	LD64	rd6, 0xffef, 0x2000, 0x0000, 0xc000	@@ PTE1: PPN 0x2000
	st.o	rd6, [rb4, 8]
	LD64	rd6, 0xffef, 0x4000, 0x0000, 0xc000	@@ PTE2: PPN 0x4000
	st.o	rd6, [rb4, 16]
	LD64	rd6, 0xffef, 0x6000, 0x0000, 0xc000	@@ PTE3: PPN 0x6000
	st.o	rd6, [rb4, 24]

	@@ --- 2c. DMA the 64 KiB zero page (4 PTEs at offset 0) to PA 0 ---
	LD64	rd2, 0x0001, 0x0000, 0x0000, 0x0000	@@ BUSY mask
	LD64	rd6, 0x0000, 0x0000, 0x83ff, 0x0000
	cfx2rc	cfx_pmem, cg15, rc0, rd6
	LD64	rd6, 0x0000, 0x0000, 0x0000, 0x0000
	cfx2rc	cfx_pmem, cg15, rc1, rd6
	LD64	rd6, 0x0000, 0x0001, 0x0000, 0x0000	@@ 0x0001_0000
	cfx2rc	cfx_pmem, cg15, rc2, rd6
	LD64	rd6, 0x0001, 0x0000, 0x0000, 0x0000	@@ START, DIR=0
	cfx2rc	cfx_pmem, cg15, rc3, rd6
	call	[rb0, smon_dma_wait]
	rd2rd	rd15, rd6, 1

	@@ --- 2d. read all four PTEs back from PA 0 via DMA (32 bytes) ---
	@@ rd14 keeps PTE0 for the observation dump; rd23-rd25 hold PTE1-3 for
	@@ the self-check below.  The DMA source is PA 0 (L1 index 0), not the
	@@ old single-entry PA 0x8000.
	LD64	rd6, 0x0000, 0x0000, 0x0000, 0x0000
	cfx2rc	cfx_pmem, cg15, rc0, rd6
	LD64	rd6, 0x0e00, 0x0000, 0x83ff, 0x0000
	cfx2rc	cfx_pmem, cg15, rc1, rd6
	LD64	rd6, 0x0020, 0x0000, 0x0000, 0x0000	@@ 32 bytes = 4 PTEs
	cfx2rc	cfx_pmem, cg15, rc2, rd6
	LD64	rd6, 0x0003, 0x0000, 0x0000, 0x0000	@@ START, DIR=1
	cfx2rc	cfx_pmem, cg15, rc3, rd6
	call	[rb0, smon_dma_wait]
	LD64	rb4, 0x0e00, 0x0000, 0x83ff, 0x0000
	ld.o	rd14, [rb4, 0]
	ld.o	rd23, [rb4, 8]
	ld.o	rd24, [rb4, 16]
	ld.o	rd25, [rb4, 24]

	@@ --- 3a. PTBR = 0, then enable PTW ---
	LD64	rd6, 0x0000, 0x0000, 0x0000, 0x0000
	cfx2rc	cfx_ptw, cg9, rc0, rd6
	LD64	rd6, 0x0001, 0x0000, 0x0000, 0x0000
	cfx2rc	cfx_ptw, cg8, rc8, rd6
	cfx2rd	cfx_ptw, cg9, rc0, rd8
	cfx2rd	cfx_ptw, cg8, rc8, rd9

	@@ --- 3b. VA write -> VA read (PA 0x12000) ---
	LD64	rb4, 0x2000, 0x0001, 0x0000, 0x0000	@@ 0x0000_0001_2000
	LD64	rd6, 0x7788, 0x5566, 0x3344, 0x1122
	st.o	rd6, [rb4, 0]
	ld.o	rd5, [rb4, 0]

	@@ 3c. DMA PA 0x12000 -> SRAM 0x0e08, read back (rd6)
	LD64	rd6, 0x2000, 0x0001, 0x0000, 0x0000
	cfx2rc	cfx_pmem, cg15, rc0, rd6
	LD64	rd6, 0x0e08, 0x0000, 0x83ff, 0x0000
	cfx2rc	cfx_pmem, cg15, rc1, rd6
	LD64	rd6, 0x0008, 0x0000, 0x0000, 0x0000
	cfx2rc	cfx_pmem, cg15, rc2, rd6
	LD64	rd6, 0x0003, 0x0000, 0x0000, 0x0000
	cfx2rc	cfx_pmem, cg15, rc3, rd6
	call	[rb0, smon_dma_wait]
	LD64	rb4, 0x0e08, 0x0000, 0x83ff, 0x0000
	ld.o	rd6, [rb4, 0]
	rd2rd	rd3, rd6, 1

	@@ 3d. SRAM 0x0e10 -> DMA PA 0x11000 -> VA read (rd7)
	LD64	rb4, 0x0e10, 0x0000, 0x83ff, 0x0000
	LD64	rd6, 0xff00, 0xddee, 0xbbcc, 0x99aa	@@ 0x99aa_bbcc_ddee_ff00
	st.o	rd6, [rb4, 0]
	LD64	rd6, 0x0e10, 0x0000, 0x83ff, 0x0000
	cfx2rc	cfx_pmem, cg15, rc0, rd6
	LD64	rd6, 0x1000, 0x0001, 0x0000, 0x0000	@@ PA 0x11000
	cfx2rc	cfx_pmem, cg15, rc1, rd6
	LD64	rd6, 0x0008, 0x0000, 0x0000, 0x0000
	cfx2rc	cfx_pmem, cg15, rc2, rd6
	LD64	rd6, 0x0001, 0x0000, 0x0000, 0x0000
	cfx2rc	cfx_pmem, cg15, rc3, rd6
	call	[rb0, smon_dma_wait]
	LD64	rb4, 0x1000, 0x0001, 0x0000, 0x0000	@@ 0x0000_0001_1000
	ld.o	rd7, [rb4, 0]
	rd2rd	rd4, rd7, 1

	@@ --- 3e. markers: smon SRAM 0x0e00 -> RAM PA 0x10010 via VA ---
	LD64	rb4, 0x0e00, 0x0000, 0x0bff, 0x0000
	LD64	rd6, 0x4f4e, 0x534d, 0x0000, 0x0000	@@ "SMON"
	st.o	rd6, [rb4, 0]
	ld.o	rd6, [rb4, 0]
	LD64	rb4, 0x0010, 0x0001, 0x0000, 0x0000
	st.o	rd6, [rb4, 0]

	LD64	rb4, 0x0000, 0x0001, 0x0000, 0x0000
	ld.o	rd10, [rb4, 0]			@@ power marker
	LD64	rb4, 0x0008, 0x0001, 0x0000, 0x0000
	ld.o	rd11, [rb4, 0]			@@ hmon marker
	LD64	rb4, 0x0010, 0x0001, 0x0000, 0x0000
	ld.o	rd12, [rb4, 0]			@@ smon marker

	@@ poison words: RAM 0x10100 (power) / 0x10108 (hmon)
	LD64	rb4, 0x0100, 0x0001, 0x0000, 0x0000
	ld.o	rd6, [rb4, 0]
	LD64	rb4, 0x0108, 0x0001, 0x0000, 0x0000
	ld.o	rd7, [rb4, 0]
	or.o	rd13, rd6, rd7
	@@ hmon's cg_reg_deleg readbacks (stored at PA 0x10018/0x10020/0x10028)
	@@ and cfx_power's supv cfxmem / delegation (PA 0x10030/0x10038).
	LD64	rb4, 0x0018, 0x0001, 0x0000, 0x0000
	ld.o	rd17, [rb4, 0]
	LD64	rb4, 0x0020, 0x0001, 0x0000, 0x0000
	ld.o	rd18, [rb4, 0]
	LD64	rb4, 0x0028, 0x0001, 0x0000, 0x0000
	ld.o	rd19, [rb4, 0]
	LD64	rb4, 0x0030, 0x0001, 0x0000, 0x0000
	ld.o	rd21, [rb4, 0]
	LD64	rb4, 0x0038, 0x0001, 0x0000, 0x0000
	ld.o	rd22, [rb4, 0]
	rd2rd	rd6, rd3, 1
	rd2rd	rd7, rd4, 1

	@@ --- 4. self-check every observation; any mismatch => 0xB9 ---
	LD64	rd1, 0x7788, 0x5566, 0x3344, 0x1122
	cmp.uo	rd2, rd5, rd1
	br.nz	{rd2}?, [rb0, smon_fail]
	cmp.uo	rd2, rd6, rd1			@@ rd6 was overwritten by the last ld
	br.nz	{rd2}?, [rb0, smon_fail]
	LD64	rd1, 0xff00, 0xddee, 0xbbcc, 0x99aa
	cmp.uo	rd2, rd7, rd1
	br.nz	{rd2}?, [rb0, smon_fail]
	LD64	rd1, 0x0000, 0x0000, 0x0000, 0x0000
	cmp.uo	rd2, rd8, rd1
	br.nz	{rd2}?, [rb0, smon_fail]
	LD64	rd1, 0x0001, 0x0000, 0x0000, 0x0000
	cmp.uo	rd2, rd9, rd1
	br.nz	{rd2}?, [rb0, smon_fail]
	LD64	rd1, 0x5745, 0x504f, 0x0000, 0x0000	@@ "POWE"
	cmp.uo	rd2, rd10, rd1
	br.nz	{rd2}?, [rb0, smon_fail]
	LD64	rd1, 0x4f4e, 0x484d, 0x0000, 0x0000	@@ "HMON"
	cmp.uo	rd2, rd11, rd1
	br.nz	{rd2}?, [rb0, smon_fail]
	LD64	rd1, 0x4f4e, 0x534d, 0x0000, 0x0000	@@ "SMON"
	cmp.uo	rd2, rd12, rd1
	br.nz	{rd2}?, [rb0, smon_fail]
	LD64	rd1, 0x0000, 0x0000, 0x0000, 0x0000
	cmp.uo	rd2, rd13, rd1
	br.nz	{rd2}?, [rb0, smon_fail]
	LD64	rd1, 0xffef, 0x0000, 0x0000, 0xc000	@@ PTE0 (rd14)
	cmp.uo	rd2, rd14, rd1
	br.nz	{rd2}?, [rb0, smon_fail]
	LD64	rd1, 0xffef, 0x2000, 0x0000, 0xc000	@@ PTE1 (rd23)
	cmp.uo	rd2, rd23, rd1
	br.nz	{rd2}?, [rb0, smon_fail]
	LD64	rd1, 0xffef, 0x4000, 0x0000, 0xc000	@@ PTE2 (rd24)
	cmp.uo	rd2, rd24, rd1
	br.nz	{rd2}?, [rb0, smon_fail]
	LD64	rd1, 0xffef, 0x6000, 0x0000, 0xc000	@@ PTE3 (rd25)
	cmp.uo	rd2, rd25, rd1
	br.nz	{rd2}?, [rb0, smon_fail]
	LD64	rd1, 0x0002, 0x0000, 0x0000, 0x0000
	cmp.uo	rd2, rd15, rd1
	br.nz	{rd2}?, [rb0, smon_fail]
	LD64	rd1, 0x0008, 0x0000, 0x0000, 0x0000
	cmp.uo	rd2, rd17, rd1
	br.nz	{rd2}?, [rb0, smon_fail]
	cmp.uo	rd2, rd18, rd1
	br.nz	{rd2}?, [rb0, smon_fail]
	cmp.uo	rd2, rd19, rd1
	br.nz	{rd2}?, [rb0, smon_fail]
	LD64	rd1, 0xfff3, 0xffff, 0xffff, 0xffff
	cmp.uo	rd2, rd21, rd1
	br.nz	{rd2}?, [rb0, smon_fail]
	LD64	rd1, 0xffff, 0xffff, 0xffff, 0xffff
	cmp.uo	rd2, rd22, rd1
	br.nz	{rd2}?, [rb0, smon_fail]
	LD64	rd1, 0x0002, 0x0001, 0x4f54, 0x4442	@@ 0x4442_4f54_0001_0002
	cmp.uo	rd2, rd20, rd1
	br.nz	{rd2}?, [rb0, smon_fail]

	LD64	rd1, 0x0000, 0x0000, 0x0000, 0x0000
	jump	[rb0, smon_exit]

smon_fail:
	LD64	rd1, 0x00b9, 0x0000, 0x0000, 0x0000
	jump	[rb0, smon_exit]

smon_exit_b8:
	LD64	rd1, 0x00b8, 0x0000, 0x0000, 0x0000

smon_exit:
	@@ SYS_EXIT block in smon SRAM (0x0bff_0000_0ff0).
	LD64	rb16, 0x0ff0, 0x0000, 0x0bff, 0x0000
	LD64	rd16, 0x0026, 0x0002, 0x0000, 0x0000
	st.o	rd16, [rb16, 0]
	st.o	rd1, [rb16, 8]
	LD64	rd16, 0x0018, 0x0000, 0x0000, 0x0000
	trap	cfx_umon, 0x3FF00
	swym	0

@@ smon_dma_wait — wait for BUSY=0, return dma_status in rd6, 0xB9 on ERROR.
@@ Called with rd2 = 1 (BUSY mask) and the cg15 transfer already started.
smon_dma_wait:
smon_dma_poll:
	cfx2rd	cfx_pmem, cg15, rc4, rd6
	and.o	rd7, rd6, rd2
	br.nz	{rd7}?, [rb0, smon_dma_poll]
	LD64	rd7, 0x0004, 0x0000, 0x0000, 0x0000	@@ ERROR
	and.o	rd7, rd6, rd7
	br.nz	{rd7}?, [rb0, smon_fail]
	ret	rd0, 0
