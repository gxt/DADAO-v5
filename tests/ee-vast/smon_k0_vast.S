@@ smon.S — Kaiwu-Vast K1 smon firmware (spec/Kaiwu §6.3, ADR-0051 D6)
@@
@@ Linked at SMON_BASE (0x0bff_0000_0000, 64 KiB) and entered by
@@ `trap cfx_smon, 0x30001` from the K1 boot hmon, which programs
@@ cfx_smon.hypv_excp_vector = this image's e_entry and
@@ cfx_smon.hypv_switch_run_mode = supv (2).  smon therefore runs in supv
@@ (cfxcode 2) and hands the kernel over in the same mode.
@@
@@ What it does (task m14-qemu-001 §2, spec §6.3.4):
@@   1. check the trap cause / boot magic (else semihosting exit 0xB8);
@@   2. DMA-read the host-written boot info (PA 0x1_0000, 0x60 bytes) into the
@@      cfx_pmem staging page and validate it read-only; a bad field exits with
@@      its fixed code and never escapes;
@@   3. clear the 64 KiB staging page, write ONE 512 MiB superpage PTE mapping
@@      VA [0x0200_0000_0000, +512 MiB) -> PA [0, 512 MiB) at L1 index
@@      VA[41:29] = 4096 (the kernel-window base segment; every other entry
@@      stays zero) and DMA the whole page to PA 0;
@@   4. read the PTE back through the DMA, invalidate the TLB, set PTBR = 0 and
@@      ptw_enable = 1, then read both back;
@@   5. load rb16 = kernel_base (VA), rb17 = boot info VA, rb3 = 0;
@@   6. write cfx_smon.excp_prev_run_mode = supv and
@@      cfx_smon.excp_cause_ip = kernel_base, then
@@      `escape cfx_smon, [excp_cause_ip, 0]` — the only entry jump.
@@
@@ Why DMA: with `ptw_enable = 0` every access to the memory window
@@ (`addr[47:42] = 0`) is CFXMEM, so PA memory (boot info, page table target)
@@ is reachable only through the cfx_pmem DMA.  The DMA's 42-bit cfx view only
@@ covers the pmem SRAM window (the hmon/smon SRAM addresses alias it after
@@ masking), so the staging page is pmem SRAM.
@@
@@ The page table page has exactly one writer in the whole boot chain: smon.
@@ The K1 hmon and the host loader never write PA 0 (the probe re-checks that
@@ with the page-table page's non-zero entry count).
@@
@@ Boot info is read-only here: no store ever targets the boot info page, and
@@ the only DMA destination is PA 0 (page table), so the host-written page
@@ survives the handover (probe: boot info page tail non-zero count == 0).
@@
@@ Failure codes (task §7; identical in this source and
@@ tools/qemu/k0_boot_probe.py):
@@   0xB8 trap cause / boot magic mismatch (step5 value, unchanged)
@@   0xC1 boot info magic or version mismatch
@@   0xC2 boot info size < 0x60
@@   0xC3 kernel_base not the fixed base VA / not 64 KiB aligned
@@   0xC4 initramfs fields out of range (K1 requires size == 0, base fixed)
@@   0xC5 page-table DMA failed or the PTE read-back differs
@@   0xC6 PTBR / ptw_enable read-back differs
@@   0xC7 RAM geometry / page size / hart id mismatch
@@ No failure escapes into the kernel.

	.include "tests/shared/asm/machine-vast.inc"

	.ifndef	BOOT_INFO_PA
	.equ	BOOT_INFO_PA, 0x10000
	.endif
	.ifndef	BOOT_INFO_VA
	.equ	BOOT_INFO_VA, 0x20000010000
	.endif
	.ifndef	KERNEL_BASE_VA
	.equ	KERNEL_BASE_VA, 0x20000100000
	.endif
	.ifndef	RAM_BASE_VA
	.equ	RAM_BASE_VA, 0x20000000000
	.endif
	.ifndef	RAM_SIZE
	.equ	RAM_SIZE, 0x80000000
	.endif
	.ifndef	PAGE_SHIFT
	.equ	PAGE_SHIFT, 16
	.endif
	.ifndef	PTE_INDEX
	.equ	PTE_INDEX, 4096			@@ VA[41:29] of 0x0200_0000_0000
	.endif
	.ifndef	PTE_VALUE
	.equ	PTE_VALUE, 0xC00000000000FFEF	@@ H=S=1, PPN 0, SPF=0xFF, RWX/G/A/D/SP/P
	.endif
	.ifndef	INITRAMFS_BASE_VA
	.equ	INITRAMFS_BASE_VA, 0x20004000000
	.endif
	.ifndef	BOOTINFO_SIZE
	.equ	BOOTINFO_SIZE, 0x60
	.endif
	.ifndef	BOOTINFO_MAGIC
	.equ	BOOTINFO_MAGIC, 0x4442494E
	.endif
	.ifndef	BOOTINFO_VERSION
	.equ	BOOTINFO_VERSION, 1
	.endif
	.ifndef	HART_ID
	.equ	HART_ID, 0
	.endif

	.text
	.globl	_start

_start:
	set.rb rb1, SMON_BASE + 0x0ff0	@@ smon rbsp (SYS_EXIT block)

	@@ --- 1. trap cause / boot magic (CFXTRAP = 1<<0, magic 0x30001) ---
	cfx2rd	cfx_smon, cg5, rc2, rd6
	set.rd	rd7, 0x1
	cmp.uo	rd2, rd6, rd7
	br.nz	{rd2}?, [rb0, smon_exit_b8]
	cfx2rd	cfx_smon, cg5, rc4, rd6
	set.rd	rd7, 0x3ffff
	and.o	rd6, rd6, rd7
	set.rd	rd7, 0x30001
	cmp.uo	rd2, rd6, rd7
	br.nz	{rd2}?, [rb0, smon_exit_b8]

	@@ --- 2. DMA the boot info (PA) into the cfx_pmem staging page ---
	set.rb rb5, BOOT_INFO_PA
	rb2rd	rd9, rb5, 1
	cfx2rc	cfx_pmem, cg15, rc0, rd9	@@ dma_src = PA 0x1_0000
	set.rb rb5, PMEM_BASE
	rb2rd	rd9, rb5, 1
	cfx2rc	cfx_pmem, cg15, rc1, rd9	@@ dma_dst = pmem SRAM
	set.rd	rd9, 0x60
	cfx2rc	cfx_pmem, cg15, rc2, rd9	@@ dma_size
	set.rd	rd9, 0x3			@@ START, DIR=1 (PA -> cfx)
	cfx2rc	cfx_pmem, cg15, rc3, rd9
	call	[rb0, smon_dma_wait]
	set.rb rb4, PMEM_BASE

	@@ magic / version (0xC1)
	ld.ut	rd6, [rb4, 0x00]
	set.rd	rd7, BOOTINFO_MAGIC
	cmp.uo	rd2, rd6, rd7
	br.nz	{rd2}?, [rb0, smon_exit_c1]
	ld.uw	rd6, [rb4, 0x04]
	set.rd	rd7, BOOTINFO_VERSION
	cmp.uo	rd2, rd6, rd7
	br.nz	{rd2}?, [rb0, smon_exit_c1]

	@@ size >= 0x60 (0xC2)
	ld.uw	rd6, [rb4, 0x06]
	set.rd	rd7, BOOTINFO_SIZE
	cmp.uo	rd2, rd6, rd7
	br.n	{rd2}?, [rb0, smon_exit_c2]

	@@ RAM geometry / page size / hart (0xC7)
	ld.o	rd6, [rb4, 0x08]
	set.rd	rd7, RAM_BASE_VA
	cmp.uo	rd2, rd6, rd7
	br.nz	{rd2}?, [rb0, smon_exit_c7]
	ld.o	rd6, [rb4, 0x10]
	set.rd	rd7, RAM_SIZE
	cmp.uo	rd2, rd6, rd7
	br.nz	{rd2}?, [rb0, smon_exit_c7]
	ld.ut	rd6, [rb4, 0x50]
	set.rd	rd7, PAGE_SHIFT
	cmp.uo	rd2, rd6, rd7
	br.nz	{rd2}?, [rb0, smon_exit_c7]
	ld.ut	rd6, [rb4, 0x54]
	set.rd	rd7, HART_ID
	cmp.uo	rd2, rd6, rd7
	br.nz	{rd2}?, [rb0, smon_exit_c7]

	@@ kernel_base: the fixed base VA, 64 KiB aligned (0xC3).  It is kept in
	@@ rb7 because the page clear below needs rd8-rd63 to read as zero.
	ld.o	rb7, [rb4, 0x18]
	rb2rd	rd20, rb7, 1
	set.rd	rd7, KERNEL_BASE_VA
	cmp.uo	rd2, rd20, rd7
	br.nz	{rd2}?, [rb0, smon_exit_c3]
	set.rd	rd7, 0xffff
	and.o	rd6, rd20, rd7
	br.nz	{rd6}?, [rb0, smon_exit_c3]

	@@ initramfs: K1 has none (size == 0, base fixed) (0xC4)
	ld.o	rd6, [rb4, 0x30]
	br.nz	{rd6}?, [rb0, smon_exit_c4]
	ld.o	rd6, [rb4, 0x28]
	set.rd	rd7, INITRAMFS_BASE_VA
	cmp.uo	rd2, rd6, rd7
	br.nz	{rd2}?, [rb0, smon_exit_c4]

	@@ --- 3. clear the 64 KiB cfx_pmem staging page (page table = zeros) ---
	@@ The store set is rd8-rd63, so every one of them must read as zero here
	@@ (rd6/rd7 hold the clear counter and are outside the set).
	set.rd	rd8, 0
	set.rd	rd9, 0
	set.rd	rd10, 0
	set.rd	rd11, 0
	set.rd	rd12, 0
	set.rd	rd13, 0
	set.rd	rd14, 0
	set.rd	rd15, 0
	set.rd	rd16, 0
	set.rd	rd17, 0
	set.rd	rd18, 0
	set.rd	rd19, 0
	set.rd	rd20, 0
	set.rd	rd21, 0
	set.rd	rd22, 0
	set.rd	rd23, 0
	set.rd	rd24, 0
	set.rd	rd25, 0
	set.rd	rd26, 0
	set.rd	rd27, 0
	set.rd	rd28, 0
	set.rd	rd29, 0
	set.rd	rd30, 0
	set.rd	rd31, 0
	set.rd	rd32, 0
	set.rd	rd33, 0
	set.rd	rd34, 0
	set.rd	rd35, 0
	set.rd	rd36, 0
	set.rd	rd37, 0
	set.rd	rd38, 0
	set.rd	rd39, 0
	set.rd	rd40, 0
	set.rd	rd41, 0
	set.rd	rd42, 0
	set.rd	rd43, 0
	set.rd	rd44, 0
	set.rd	rd45, 0
	set.rd	rd46, 0
	set.rd	rd47, 0
	set.rd	rd48, 0
	set.rd	rd49, 0
	set.rd	rd50, 0
	set.rd	rd51, 0
	set.rd	rd52, 0
	set.rd	rd53, 0
	set.rd	rd54, 0
	set.rd	rd55, 0
	set.rd	rd56, 0
	set.rd	rd57, 0
	set.rd	rd58, 0
	set.rd	rd59, 0
	set.rd	rd60, 0
	set.rd	rd61, 0
	set.rd	rd62, 0
	set.rd	rd63, 0
	set.rb rb3, PMEM_BASE
	set.rd	rd6, 146
smon_clear:
	stm.o	{rd8:rd63}, [rb3, rd0]
	add.si	rb3, 448
	add.si	rd6, -1
	br.nz	{rd6}?, [rb0, smon_clear]
	stm.o	{rd8:rd23}, [rb3, rd0]

	@@ --- 4. one superpage PTE at L1 index PTE_INDEX, page stays zero ---
	@@ PTE bits (spec/DADAO-12 §2.2.3): HSJU = H|S (0xC), PPN[55:29] = PA(0)>>29,
	@@ SPF = 0xFF, R=W=X=G=A=D=SP=P = 0xEF.
	set.rb rb3, PMEM_BASE
	set.rd	rd6, PTE_INDEX * 8
	add.o	rb4, rb3, rd6
	set.rd	rd6, PTE_VALUE
	st.o	rd6, [rb4, 0]

	@@ --- 5. DMA the page table page to PA 0 and read the PTE back ---
	set.rb rb5, PMEM_BASE
	rb2rd	rd9, rb5, 1
	cfx2rc	cfx_pmem, cg15, rc0, rd9	@@ dma_src = pmem SRAM
	set.rd	rd9, 0x0
	cfx2rc	cfx_pmem, cg15, rc1, rd9	@@ dma_dst = PA 0
	set.rd	rd9, 0x10000
	cfx2rc	cfx_pmem, cg15, rc2, rd9	@@ 64 KiB
	set.rd	rd9, 0x1			@@ START, DIR=0 (cfx -> PA)
	cfx2rc	cfx_pmem, cg15, rc3, rd9
	call	[rb0, smon_dma_wait]

	set.rd	rd9, PTE_INDEX * 8
	cfx2rc	cfx_pmem, cg15, rc0, rd9	@@ dma_src = PA 0x8000 (PTE_INDEX*8)
	set.rb rb5, PMEM_BASE + 0x0e00
	rb2rd	rd9, rb5, 1
	cfx2rc	cfx_pmem, cg15, rc1, rd9
	set.rd	rd9, 0x8
	cfx2rc	cfx_pmem, cg15, rc2, rd9
	set.rd	rd9, 0x3			@@ START, DIR=1
	cfx2rc	cfx_pmem, cg15, rc3, rd9
	call	[rb0, smon_dma_wait]
	set.rb rb4, PMEM_BASE + 0x0e00
	ld.o	rd6, [rb4, 0]
	set.rd	rd7, PTE_VALUE
	cmp.uo	rd2, rd6, rd7
	br.nz	{rd2}?, [rb0, smon_exit_c5]

	@@ --- 6. invalidate the TLB, PTBR = 0, ptw_enable = 1, read back ---
	set.rd	rd9, 0x2			@@ tlb_control = invalid all
	cfx2rc	cfx_ptw, cg12, rc0, rd9
	set.rd	rd9, 0x0
	cfx2rc	cfx_ptw, cg9, rc0, rd9		@@ PTBR PPN = 0 (PA 0)
	set.rd	rd9, 0x1
	cfx2rc	cfx_ptw, cg8, rc8, rd9		@@ ptw_enable = 1
	cfx2rd	cfx_ptw, cg9, rc0, rd6
	br.nz	{rd6}?, [rb0, smon_exit_c6]
	cfx2rd	cfx_ptw, cg8, rc8, rd7
	set.rd	rd9, 0x1
	cmp.uo	rd2, rd7, rd9
	br.nz	{rd2}?, [rb0, smon_exit_c6]

	@@ --- 6. handover registers (spec §6.3.4) ---
	rb2rb	rb16, rb7, 1			@@ rb16 = kernel_base (entry VA)
	set.rb rb17, BOOT_INFO_VA		@@ rb17 = boot info VA
	set.zw	rb3, wp0, 0			@@ rb3 (rbtp) = 0

	@@ --- 7. cfx_smon exception frame: return into supv at the entry VA ---
	set.rd	rd9, 0x2			@@ supv
	cfx2rc	cfx_smon, cg5, rc0, rd9		@@ excp_prev_run_mode
	rb2rd	rd20, rb7, 1
	cfx2rc	cfx_smon, cg5, rc3, rd20	@@ excp_cause_ip = entry VA
	escape	cfx_smon, [excp_cause_ip, 0]	@@ the only entry jump
	swym	0
	jump	[rb0, smon_exit_b8]		@@ unreachable: escape never returns

@@ smon_dma_wait — wait for BUSY=0, require DONE and no ERROR (0xC5).
smon_dma_wait:
	set.rd	rd2, 0x1			@@ BUSY
smon_dma_poll:
	cfx2rd	cfx_pmem, cg15, rc4, rd6
	and.o	rd7, rd6, rd2
	br.nz	{rd7}?, [rb0, smon_dma_poll]
	set.rd	rd7, 0x4			@@ ERROR
	and.o	rd7, rd6, rd7
	br.nz	{rd7}?, [rb0, smon_exit_c5]
	set.rd	rd7, 0x2			@@ DONE
	and.o	rd7, rd6, rd7
	br.z	{rd7}?, [rb0, smon_exit_c5]
	ret	rd0, 0

smon_exit_c1:
	set.rd	rd1, 0xC1
	jump	[rb0, smon_exit]
smon_exit_c2:
	set.rd	rd1, 0xC2
	jump	[rb0, smon_exit]
smon_exit_c3:
	set.rd	rd1, 0xC3
	jump	[rb0, smon_exit]
smon_exit_c4:
	set.rd	rd1, 0xC4
	jump	[rb0, smon_exit]
smon_exit_c5:
	set.rd	rd1, 0xC5
	jump	[rb0, smon_exit]
smon_exit_c6:
	set.rd	rd1, 0xC6
	jump	[rb0, smon_exit]
smon_exit_c7:
	set.rd	rd1, 0xC7
	jump	[rb0, smon_exit]

smon_exit_b8:
	set.rd	rd1, 0xB8

smon_exit:
	@@ SYS_EXIT block in smon SRAM (semihosting reads it through the debug
	@@ identity translation, which covers the monitor SRAM).
	set.rb rb16, SMON_BASE + 0x0ff0
	set.rd	rd16, 0x20026
	st.o	rd16, [rb16, 0]
	st.o	rd1, [rb16, 8]
	set.rd	rd16, 0x18
	trap	cfx_umon, 0x3FF00
	swym	0
