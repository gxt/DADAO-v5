@@ hmon.S — Machine-v5-Vast K1 boot hmon (spec/Machine-v5 §6.3, ADR-0051 D6)
@@
@@ Linked at HMON_BASE (0x0fff_0000_0000, 64 KiB) and entered by
@@ `trap cfx_hmon, 0x30001` from the reused step5 power stage.
@@
@@ K1 differs from the step5 hmon on purpose (task m14-qemu-001 §2):
@@   * it does NOT build a page table and does NOT write PA 0 — the first page
@@     table belongs to smon alone (`PTBR = 0` is smon's write);
@@   * it does NOT touch the boot info page — the host loader writes it and
@@     power/hmon/smon only read it (spec/Machine-v5 §6.3.3);
@@   * it loads the smon ELF (image index table type 2) into smon SRAM with the
@@     shared ROM `elf_loader`, programs cfx_smon's hypv vector/switch mode and
@@     opens exactly the supv permissions smon needs, then traps into smon.
@@
@@ Failure codes (task §7, unchanged step5 values): image index table 0xB1/0xB2/
@@ 0xB6, smon ELF 0xB3-0xB5, trap cause / boot magic mismatch 0xB8.  Every
@@ failure is a semihosting SYS_EXIT (block in hmon SRAM) and never traps into
@@ smon: a half-initialised chain must not hand over.
@@
@@ Test-only negative variants (`--defsym SMON_NEG_CASE=1|2`) DMA-patch one
@@ boot info field right before the smon trap so the probe can prove smon's
@@ read-only validation rejects a bad boot info.  The production image is
@@ assembled with SMON_NEG_CASE=0: the block expands to nothing.

	.include "tests/shared/asm/machine-vast.inc"
	.include "tests/shared/asm/machine.inc"

	.ifndef	SMON_NEG_CASE
	.equ	SMON_NEG_CASE, 0
	.endif
	.ifndef	BOOT_INFO_PA
	.equ	BOOT_INFO_PA, 0x10000
	.endif

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

	@@ --- 1. trap cause / boot magic (CFXTRAP = 1<<0, magic 0x30001) ---
	cfx2rd	cfx_hmon, cg5, rc2, rd6
	LD64	rd7, 0x0001, 0x0000, 0x0000, 0x0000
	cmp.uo	rd8, rd6, rd7
	br.nz	{rd8}?, [rb0, hmon_exit_b8]
	cfx2rd	cfx_hmon, cg5, rc4, rd6
	LD64	rd7, 0xffff, 0x0003, 0x0000, 0x0000
	and.o	rd6, rd6, rd7
	LD64	rd7, 0x0001, 0x0003, 0x0000, 0x0000	@@ 0x0003_0001
	cmp.uo	rd8, rd6, rd7
	br.nz	{rd8}?, [rb0, hmon_exit_b8]

	@@ --- 2. look up the smon image (type 2) in the BootROM table ---
	LD64	rd1, 0x0002, 0x0000, 0x0000, 0x0000
	LOAD_ADDR rb9, RESET_PC + 0x2000	@@ rom_validate_table (shared)
	call	[rb9, rd0, 0]
	br.nz	{rd8}?, [rb0, hmon_exit_rd8]

	@@ --- 3. load the smon ELF into smon SRAM (0x0bff_0000_0000) ---
	LOAD_ADDR rb2, SMON_BASE
	LOAD_ADDR rb9, RESET_PC + 0x2400	@@ elf_loader (shared)
	call	[rb9, rd0, 0]
	br.nz	{rd8}?, [rb0, hmon_exit_rd8]

	@@ --- 4. cfx_smon: hypv vector = smon e_entry, switch mode = supv (2) ---
	cfx2rc	cfx_smon, cg3, rc10, rd5
	LD64	rd6, 0x0002, 0x0000, 0x0000, 0x0000
	cfx2rc	cfx_smon, cg3, rc8, rd6

	@@ --- 5. open exactly the supv permissions smon needs ---
	@@ smon runs in supv (cfxcode 2) and must reach cfx_pmem (DMA),
	@@ cfx_ptw (PTBR/PTW_ENABLE/TLB) and its own cfx_smon exception frame.
	@@ Two axes per target cfx (DADAO-12 §3.2/§3.3, DADAO-13 §1):
	@@   supv_cfxreg bit2 = 0  (source cfx 2 = smon may use cfx2rd/cfx2rc)
	@@   supv_cfxmem bit2 = 0  (cfx_pmem only: st to the pmem SRAM)
	@@   hypv_cg_reg_deleg  = 0x8 (every cg except the hypv row cg3)
	@@ hmon runs in hypv, so its own writes use the hypv rows (bit3 = 0).
	@@
	@@ The cleared source bits are {2, 15}: the kernel starts as cfx_smon (2),
	@@ and from the first cfx_hart interrupt delivery on its inner_cfx_code is
	@@ cfx_hart (15) -- `escape` restores only the run mode (DADAO-12 §5.3, no
	@@ previous cfx in the frame), so the target cfx stays.  Both are the same
	@@ kernel asking (tools/testcases/arch/min_rom_probe_integ051t.py records
	@@ the same convention), so both source bits are opened.
	.macro	OPEN_SUPV_REGS cfx
	cfx2rd	\cfx, cg2, rc2, rd6
	LD64	rd7, 0x7ffb, 0xffff, 0xffff, 0xffff	@@ ~((1 << 2) | (1 << 15))
	and.o	rd6, rd6, rd7
	cfx2rc	\cfx, cg2, rc2, rd6
	LD64	rd6, 0x0008, 0x0000, 0x0000, 0x0000
	cfx2rc	\cfx, cg3, rc12, rd6
	.endm
	OPEN_SUPV_REGS cfx_pmem
	OPEN_SUPV_REGS cfx_ptw
	OPEN_SUPV_REGS cfx_smon
	@@ cfx_pmem supv cfxmem: the pmem SRAM is the page-table staging area.
	cfx2rd	cfx_pmem, cg2, rc1, rd6
	LD64	rd7, 0xfffb, 0xffff, 0xffff, 0xffff
	and.o	rd6, rd6, rd7
	cfx2rc	cfx_pmem, cg2, rc1, rd6

	@@ K2 (m14-linux-007): the kernel reads cfx_time (freq/value) and programs
	@@ the cfx_hart timer (cmp/ctrl), so those two targets need the same two
	@@ axes -- supv_cfxreg source bits {2, 15} cleared and hypv_cg_reg_deleg =
	@@ 0x8 (cfx_hart needs cg8, cfx_time cg10; 0x8 opens every cg but cg3).
	@@ K2_TIME_PERM=0 assembles the negative variant the K2 gate uses to prove
	@@ these permissions really come from the firmware: with it the kernel's
	@@ first cfx_time read is CFXPERM.  The committed image keeps them open.
	.ifndef	K2_TIME_PERM
	.equ	K2_TIME_PERM, 1
	.endif
	.if K2_TIME_PERM
	OPEN_SUPV_REGS cfx_hart
	OPEN_SUPV_REGS cfx_time
	.endif

	@@ --- 6. test-only boot info patch (SMON_NEG_CASE 1|2) ---
	.if SMON_NEG_CASE != 0
	@@ DMA one field over the host-written boot info (PA side); PTW is still
	@@ off, so a direct store to PA memory is impossible by construction.
	@@ The staging word must live in the cfx_pmem SRAM: the DMA's 42-bit cfx
	@@ view only reaches that window (the hmon/smon SRAM addresses alias it
	@@ after masking), so staging in hmon SRAM would copy unrelated bytes.
	LOAD_ADDR rb4, PMEM_BASE + 0x1000	@@ staging word in pmem SRAM
	.if SMON_NEG_CASE == 1
	LD64	rd6, 0x0020, 0x0000, 0x0000, 0x0000	@@ size = 0x20 (field 0x06)
	st.w	rd6, [rb4, 0]
	LOAD_ADDR rb5, BOOT_INFO_PA + 0x06
	LD64	rd11, 0x0002, 0x0000, 0x0000, 0x0000	@@ 2 bytes
	.elseif SMON_NEG_CASE == 2
	LD64	rd6, 0x0001, 0x0010, 0x0200, 0x0000	@@ kernel_base VA | 1
	st.o	rd6, [rb4, 0]
	LOAD_ADDR rb5, BOOT_INFO_PA + 0x18
	LD64	rd11, 0x0008, 0x0000, 0x0000, 0x0000	@@ 8 bytes
	.else
	@@ hart_id = 5 (field 0x54): zero is the *valid* value here, so this case
	@@ also proves the injected bytes really reach the boot info page (a
	@@ zero-filling or mis-addressed DMA would leave smon happy).
	LD64	rd6, 0x0005, 0x0000, 0x0000, 0x0000
	st.t	rd6, [rb4, 0]
	LOAD_ADDR rb5, BOOT_INFO_PA + 0x54
	LD64	rd11, 0x0004, 0x0000, 0x0000, 0x0000	@@ 4 bytes
	.endif
	rb2rd	rd10, rb5, 1			@@ dma_dst = boot info field PA
	LOAD_ADDR rd9, PMEM_BASE + 0x1000
	cfx2rc	cfx_pmem, cg15, rc0, rd9	@@ dma_src (pmem staging word)
	cfx2rc	cfx_pmem, cg15, rc1, rd10	@@ dma_dst
	cfx2rc	cfx_pmem, cg15, rc2, rd11	@@ dma_size
	LD64	rd9, 0x0001, 0x0000, 0x0000, 0x0000	@@ START, DIR=0
	cfx2rc	cfx_pmem, cg15, rc3, rd9
hmon_neg_poll:
	cfx2rd	cfx_pmem, cg15, rc4, rd9
	LD64	rd7, 0x0001, 0x0000, 0x0000, 0x0000
	and.o	rd8, rd9, rd7
	br.nz	{rd8}?, [rb0, hmon_neg_poll]
	LD64	rd7, 0x0004, 0x0000, 0x0000, 0x0000	@@ ERROR
	and.o	rd8, rd9, rd7
	br.nz	{rd8}?, [rb0, hmon_exit_b8]
	.endif

	@@ --- 7. hand over to smon (runs in supv, cfxcode 2) ---
	trap	cfx_smon, 0x30001
	swym	0
	jump	[rb0, hmon_exit_b8]	@@ smon must not return; park loudly

hmon_exit_rd8:
	rd2rd	rd9, rd8, 1
	jump	[rb0, hmon_exit]

hmon_exit_b8:
	LD64	rd9, 0x00b8, 0x0000, 0x0000, 0x0000

hmon_exit:
	@@ SYS_EXIT block in hmon SRAM (semihosting reads it through the debug
	@@ identity translation, which covers the monitor SRAM).
	LOAD_ADDR rb16, HMON_BASE + 0x0d00
	LD64	rd16, 0x0026, 0x0002, 0x0000, 0x0000
	st.o	rd16, [rb16, 0]
	st.o	rd9, [rb16, 8]
	LD64	rd16, 0x0018, 0x0000, 0x0000, 0x0000
	trap	cfx_umon, 0x3FF00
	swym	0
