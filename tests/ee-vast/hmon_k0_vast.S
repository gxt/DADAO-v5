@@ hmon.S — Kaiwu-Vast K1 boot hmon (spec/Kaiwu §6.3, ADR-0051 D6)
@@
@@ Linked at HMON_BASE (0x0fff_0000_0000, 64 KiB) and entered by
@@ `trap cfx_hmon, 0x30001` from the reused step5 power stage.
@@
@@ K1 differs from the step5 hmon on purpose (task m14-qemu-001 §2):
@@   * it does NOT build a page table and does NOT write PA 0 — the first page
@@     table belongs to smon alone (`PTBR = 0` is smon's write);
@@   * it does NOT touch the boot info page — the host loader writes it and
@@     power/hmon/smon only read it (spec/Kaiwu §6.3.3);
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

	.ifndef	SMON_NEG_CASE
	.equ	SMON_NEG_CASE, 0
	.endif
	.ifndef	BOOT_INFO_PA
	.equ	BOOT_INFO_PA, 0x10000
	.endif

	.text
	.globl	_start

_start:
	set.rb rb1, SP

	@@ --- 1. trap cause / boot magic (CFXTRAP = 1<<0, magic 0x30001) ---
	cfx2rd	cfx_hmon, cg5, rc4, rd6		@@ excp_cause_id（新布局 rc4）
	set.rd rd7, 0x0000000000000001
	cmp.uo	rd8, rd6, rd7
	br.nz	{rd8}?, [rb0, hmon_exit_b8]
	cfx2rd	cfx_hmon, cg5, rc5, rd6		@@ excp_cause_info（新布局 rc5）
	set.rd rd7, 0x000000000003ffff
	and.o	rd6, rd6, rd7
	set.rd rd7, 0x0000000000030001	@@ 0x0003_0001
	cmp.uo	rd8, rd6, rd7
	br.nz	{rd8}?, [rb0, hmon_exit_b8]

	@@ --- 2. look up the smon image (type 2) in the BootROM table ---
	set.rd rd1, 0x0000000000000002
	set.rb rb9, RESET_PC + 0x2000	@@ rom_validate_table (shared)
	call	[rb9, rd0, 0]
	br.nz	{rd8}?, [rb0, hmon_exit_rd8]

	@@ --- 3. load the smon ELF into smon SRAM (0x0bff_0000_0000) ---
	set.rb rb2, SMON_BASE
	set.rb rb9, RESET_PC + 0x2400	@@ elf_loader (shared)
	call	[rb9, rd0, 0]
	br.nz	{rd8}?, [rb0, hmon_exit_rd8]

	@@ --- 4. cfx_smon: hypv vector = smon e_entry, switch mode = supv (2) ---
	cfx2rc	cfx_smon, cg3, rc15, rd5		@@ hypv_excp_vector（原 rc10）
	set.rd rd6, 0x0000000000000002
	cfx2rc	cfx_smon, cg3, rc14, rd6		@@ hypv_switch_run_mode（原 rc8）

	@@ --- 5. hand every cfx's supv permissions to smon (hmon itself excluded) ---
	@@ User ruling 2026-11-17 (m14-testcases-006): hmon hands *every* cfx
	@@ over to smon, except hmon itself.  smon runs in supv with cfxcode 2,
	@@ so for a target cfx C != cfx_hmon the firmware opens all four
	@@ synchronous source masks of C's supv row (DADAO-12 §3.3, ADR-0045 D6):
	@@   C supv cfxtrap/cfxmem/cfxreg/cfxexe (cg2 rc0..rc3) bit2 = 0
	@@     (source cfx 2 = smon may trap / ld-st / cfx2rd-cfx2rc / fetch
	@@      into C)
	@@   C hypv_cg_reg_deleg (cg3 rc12) = 0x8  (every cg row except the hypv
	@@     row cg3, whose bit3 is hardware-fixed 1; DADAO-13 §1)
	@@ cfx_hmon is deliberately absent from the open list: the kernel may
	@@ neither enter nor read/write the hypervisor monitor, so its masks keep
	@@ the reset value (~0x8, i.e. bit2 still set = source smon denied).
	@@ hmon runs in hypv, so its own writes use the hypv rows (bit3 = 0).
	@@
	@@ The cleared source bits are {2, 15}: the kernel starts as cfx_smon (2),
	@@ and async entries deliver to cfx_hart (15); escape restores run mode/cfx/ip
	@@ from `cg5 rc8`-`rc11` (DADAO-12 §5.3), so the kernel that runs inside the
	@@ async handler is still cfx_hart when it issues cfx-register accesses.
	@@ Both are the same kernel asking (tools/testcases/arch/min_rom_probe_integ051t.py
	@@ records the same convention), so both source bits are opened.
	.macro	OPEN_SUPV_REGS cfx
	cfx2rd	\cfx, cg2, rc0, rd20		@@ supv cfxtrap
	cfx2rd	\cfx, cg2, rc1, rd21		@@ supv cfxmem
	cfx2rd	\cfx, cg2, rc2, rd22		@@ supv cfxreg
	cfx2rd	\cfx, cg2, rc3, rd23		@@ supv cfxexe
	set.rd rd24, 0xffffffffffff7ffb	@@ ~((1 << 2) | (1 << 15))
	and.o	rd20, rd20, rd24
	and.o	rd21, rd21, rd24
	and.o	rd22, rd22, rd24
	and.o	rd23, rd23, rd24
	cfx2rc	\cfx, cg2, rc0, rd20
	cfx2rc	\cfx, cg2, rc1, rd21
	cfx2rc	\cfx, cg2, rc2, rd22
	cfx2rc	\cfx, cg2, rc3, rd23
	set.rd rd24, 0x0000000000000008
	cfx2rc	\cfx, cg3, rc12, rd24
	.endm

	@@ The three cfx the boot chain itself needs stay open unconditionally:
	@@ smon stages the page table through cfx_pmem (its SRAM is the staging
	@@ area, i.e. the cfxmem axis covers it), programs cfx_ptw and reads its
	@@ own cfx_smon exception frame -- all *before* the kernel exists, so a
	@@ negative variant that closed them would stop the chain at smon.
	OPEN_SUPV_REGS cfx_pmem
	OPEN_SUPV_REGS cfx_ptw
	OPEN_SUPV_REGS cfx_smon

	@@ Every other cfx is opened for smon by the same macro.  OPEN_SUPV_ALL=0
	@@ assembles the permission-negative variant the K0/K1/K2/K3 gates use to
	@@ prove these permissions really come from the firmware (not from a
	@@ hardware default): with it the kernel's first cfx2rd cfx_umon is
	@@ CFXPERM, and the boot chain still reaches the kernel.  The committed
	@@ image keeps them open.
	@@
	@@ Only cfx this machine implements are listed.  `spec/Kaiwu §「测试机 cfx
	@@ 实现范围（按 profile）」` fixes the Kaiwu-Vast set at cfx0/1/2/3/63 +
	@@ cfx4 (ptw) + cfx32 (pmem) and states that cfx5 (cache) is allocated but
	@@ not implemented (`cfx2rd`/`cfx2rc` on it => CFXREG); cfx15 (hart) and
	@@ cfx34 (time) are the K2 time sources this machine implements
	@@ (`spec/DADAO-12 §4.7`/`§4.10`).  cfx33 (llc) and cfx62 (uart) sit in
	@@ the same `cfx32`–`cfx63` per-system range (`spec/DADAO-12 §1`) but are
	@@ not implemented here, so cfx5/33/62 have no supv rows to open.
	@@ cfx_hmon (3) is excluded on purpose (see above); a platform that
	@@ implements more must extend this list.
	.ifndef	OPEN_SUPV_ALL
	.equ	OPEN_SUPV_ALL, 1
	.endif
	.if OPEN_SUPV_ALL
	OPEN_SUPV_REGS cfx_umon
	OPEN_SUPV_REGS cfx_jmon
	@@ K2 (m14-linux-007): the kernel reads cfx_time (freq/value) and programs
	@@ the cfx_hart timer (cmp/ctrl).  K2_TIME_PERM=0 closes exactly these two
	@@ so the K2 gate can show the same firmware-sourced permission.
	.ifndef	K2_TIME_PERM
	.equ	K2_TIME_PERM, 1
	.endif
	.if K2_TIME_PERM
	OPEN_SUPV_REGS cfx_hart
	OPEN_SUPV_REGS cfx_time
	.endif
	OPEN_SUPV_REGS cfx_power
	.endif

	@@ --- 6. test-only boot info patch (SMON_NEG_CASE 1|2) ---
	.if SMON_NEG_CASE != 0
	@@ DMA one field over the host-written boot info (PA side); PTW is still
	@@ off, so a direct store to PA memory is impossible by construction.
	@@ The staging word must live in the cfx_pmem SRAM: the DMA's 42-bit cfx
	@@ view only reaches that window (the hmon/smon SRAM addresses alias it
	@@ after masking), so staging in hmon SRAM would copy unrelated bytes.
	set.rb rb4, PMEM_BASE + 0x1000	@@ staging word in pmem SRAM
	.if SMON_NEG_CASE == 1
	set.rd rd6, 0x0000000000000020	@@ size = 0x20 (field 0x06)
	st.w	rd6, [rb4, 0]
	set.rb rb5, BOOT_INFO_PA + 0x06
	set.rd rd11, 0x0000000000000002	@@ 2 bytes
	.elseif SMON_NEG_CASE == 2
	set.rd rd6, 0x0000020000100001	@@ kernel_base VA | 1
	st.o	rd6, [rb4, 0]
	set.rb rb5, BOOT_INFO_PA + 0x18
	set.rd rd11, 0x0000000000000008	@@ 8 bytes
	.else
	@@ hart_id = 5 (field 0x54): zero is the *valid* value here, so this case
	@@ also proves the injected bytes really reach the boot info page (a
	@@ zero-filling or mis-addressed DMA would leave smon happy).
	set.rd rd6, 0x0000000000000005
	st.t	rd6, [rb4, 0]
	set.rb rb5, BOOT_INFO_PA + 0x54
	set.rd rd11, 0x0000000000000004	@@ 4 bytes
	.endif
	rb2rd	rd10, rb5, 1			@@ dma_dst = boot info field PA
	set.rd rd9, PMEM_BASE + 0x1000
	cfx2rc	cfx_pmem, cg15, rc0, rd9	@@ dma_src (pmem staging word)
	cfx2rc	cfx_pmem, cg15, rc1, rd10	@@ dma_dst
	cfx2rc	cfx_pmem, cg15, rc2, rd11	@@ dma_size
	set.rd rd9, 0x0000000000000001	@@ START, DIR=0
	cfx2rc	cfx_pmem, cg15, rc3, rd9
hmon_neg_poll:
	cfx2rd	cfx_pmem, cg15, rc4, rd9
	set.rd rd7, 0x0000000000000001
	and.o	rd8, rd9, rd7
	br.nz	{rd8}?, [rb0, hmon_neg_poll]
	set.rd rd7, 0x0000000000000004	@@ ERROR
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
	set.rd rd9, 0x00000000000000b8

hmon_exit:
	@@ SYS_EXIT block in hmon SRAM (semihosting reads it through the debug
	@@ identity translation, which covers the monitor SRAM).
	set.rb rb16, HMON_BASE + 0x0d00
	set.rd rd16, 0x0000000000020026
	st.o	rd16, [rb16, 0]
	st.o	rd9, [rb16, 8]
	set.rd rd16, 0x0000000000000018
	trap	cfx_umon, 0x3FF00
	swym	0
