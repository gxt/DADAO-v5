@@ hmon.S — Machine-v5-Node hmon stage (TESTCASES-091t).
@@
@@ Linked at HMON_BASE (0x0fff_0000_0000, 64 KiB) and entered by
@@ `trap cfx_hmon, <boot_magic>` from the Node power stage.
@@
@@ Node (user ruling 2026-11-02): hmon drives cfx_pmem, installs a first-level
@@ page table with four 512 MiB superpages covering PA [0, 2 GiB) (SPF=0xFF),
@@ enables PTW, sets the cfx_umon hypv vector to the profile ENTRY, and traps
@@ into the test body in hypv.  smon is reserved and not used by this stage.
@@
@@ Page table PTE (spec/DADAO-12 §2.2.3, ADR-0040 D1/D4):
@@   HSJU=0xF, PPN[55:29]=i, SPF=0xFF, flags P/SP/D/A/G/X/W/R = 0xEF
@@   i = 0..3 -> PA i*512 MiB; L1 index VA[41:29] selects entry i.
@@ PTBR = 0 (PA 0) and ptw_enable = 1.  The table template lives in hmon SRAM
@@ and is copied to PA 0 through cfx_pmem DMA (PTW is off until the copy is done).

	.include "tests/shared/asm/machine-node.inc"
	.include "tests/shared/asm/machine.inc"

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

	.text
	.globl	_start
_start:
	LOAD_ADDR rb1, SP

	@@ --- 1. trap cause / magic check (CFXTRAP = 1<<0, magic 0x30001) ---
	cfx2rd	cfx_hmon, cg5, rc2, rd6
	LD64	rd7, 0x0001, 0x0000, 0x0000, 0x0000
	cmp.uo	rd8, rd6, rd7
	br.nz	{rd8}?, [rb0, hmon_exit_b7]
	cfx2rd	cfx_hmon, cg5, rc4, rd6
	LD64	rd7, 0xffff, 0x0003, 0x0000, 0x0000	@@ 0x0003_ffff
	and.o	rd6, rd6, rd7
	LD64	rd7, 0x0001, 0x0003, 0x0000, 0x0000	@@ 0x0003_0001
	cmp.uo	rd8, rd6, rd7
	br.nz	{rd8}?, [rb0, hmon_exit_b7]

	@@ --- 2. page-table template in hmon SRAM (16 PTEs reserved, 4 used) ---
	LOAD_ADDR rb2, HMON_BASE + 0x1000
	LOAD_ADDR rb3, PMEM_BASE
	LD64	rd4, 0xffef, 0x0000, 0x0000, 0xf000	@@ PTE0: PPN 0
	st.o	rd4, [rb2, 0]
	st.o	rd4, [rb3, 0]
	LD64	rd4, 0xffef, 0x2000, 0x0000, 0xf000	@@ PTE1: PPN 0x2000
	st.o	rd4, [rb2, 8]
	st.o	rd4, [rb3, 8]
	LD64	rd4, 0xffef, 0x4000, 0x0000, 0xf000	@@ PTE2: PPN 0x4000
	st.o	rd4, [rb2, 16]
	st.o	rd4, [rb3, 16]
	LD64	rd4, 0xffef, 0x6000, 0x0000, 0xf000	@@ PTE3: PPN 0x6000
	st.o	rd4, [rb2, 24]
	st.o	rd4, [rb3, 24]

	@@ --- 3. cfx_pmem DMA: PMEM SRAM -> PA 0, 32 bytes, DIR=0 ---
	LOAD_ADDR rd9, PMEM_BASE
	cfx2rc	cfx_pmem, cg15, rc0, rd9	@@ dma_src
	cfx2rc	cfx_pmem, cg15, rc1, rd0	@@ dma_dst = PA 0
	LD64	rd9, 0x0020, 0x0000, 0x0000, 0x0000	@@ dma_size = 32
	cfx2rc	cfx_pmem, cg15, rc2, rd9
	LD64	rd9, 0x0001, 0x0000, 0x0000, 0x0000	@@ START, DIR=0
	cfx2rc	cfx_pmem, cg15, rc3, rd9
hmon_dma_poll:
	cfx2rd	cfx_pmem, cg15, rc4, rd9	@@ dma_status
	LD64	rd10, 0x0001, 0x0000, 0x0000, 0x0000
	and.o	rd9, rd9, rd10
	br.nz	{rd9}?, [rb0, hmon_dma_poll]

	@@ --- 4. invalidate TLB, PTBR=0, ptw_enable=1 ---
	LD64	rd9, 0x0002, 0x0000, 0x0000, 0x0000	@@ tlb_control = invalid all
	cfx2rc	cfx_ptw, cg12, rc0, rd9
	cfx2rc	cfx_ptw, cg9, rc0, rd0		@@ PTBR PPN = 0 (PA 0)
	LD64	rd9, 0x0001, 0x0000, 0x0000, 0x0000
	cfx2rc	cfx_ptw, cg8, rc8, rd9		@@ ptw_enable = 1

	@@ --- 5. cfx_umon hypv: vector = ENTRY, switch mode = hypv (3), mask 0 ---
	LOAD_ADDR rd5, ENTRY
	cfx2rc	cfx_umon, cg3, rc10, rd5
	LD64	rd6, 0x0003, 0x0000, 0x0000, 0x0000
	cfx2rc	cfx_umon, cg3, rc8, rd6		@@ switch_run_mode = hypv
	cfx2rc	cfx_umon, cg3, rc9, rd0		@@ switch_cfx_mask = 0

	@@ --- 6. handoff to the test body in hypv ---
	trap	cfx_umon, 0
	swym	0

hmon_exit_b7:
	@@ SYS_EXIT with the argument block in hmon SRAM.
	LOAD_ADDR rb16, HMON_BASE + 0x0d00
	LD64	rd16, 0x0026, 0x0002, 0x0000, 0x0000
	st.o	rd16, [rb16, 0]
	LD64	rd16, 0x00b7, 0x0000, 0x0000, 0x0000
	st.o	rd16, [rb16, 8]
	LD64	rd16, 0x0018, 0x0000, 0x0000, 0x0000
	trap	cfx_umon, 0x3FF00
	swym	0
