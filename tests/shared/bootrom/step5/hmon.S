@@ hmon.S — DADAO-v5 step5 hmon stage (INTEG-046t; ADR-0043 D4/D8/D9/D13/D14)
@@
@@ Linked at the hmon SRAM base 0x0fff_0000_0000 (64 KiB) and entered by
@@ `trap cfx_hmon, <boot_magic>` from power.  It:
@@   1. checks the trap cause (CFXTRAP + boot magic 0x30001), else exits 0xB7;
@@   2. looks up the smon entry in the BootROM image index table and loads the
@@      smon ELF into smon SRAM with the shared ROM loader;
@@   3. programs cfx_smon's S-mode vector/switch mode and opens the run-time
@@      cfx permissions needed by smon (cfx_ptw / cfx_pmem);
@@   4. revokes its own cfx_pmem access (D13), traps into smon and parks.
@@
@@ Exit channel: semihosting SYS_EXIT with the argument block in hmon SRAM
@@ (QEMU's debug translation maps the monitor SRAM windows; see cpu.c).

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
	LD64	rb1, 0xfff0, 0x0000, 0x0fff, 0x0000	@@ hmon rbsp

	@@ hmon marker: write it into hmon SRAM (0x0e00), read it back and mirror
	@@ it to RAM PA 0x10008 so smon can report all three stage markers.
	LD64	rb4, 0x0e00, 0x0000, 0x0fff, 0x0000
	LD64	rd6, 0x4f4e, 0x484d, 0x0000, 0x0000	@@ "HMON"
	st.o	rd6, [rb4, 0]
	ld.o	rd7, [rb4, 0]
	LD64	rb4, 0x0008, 0x0001, 0xfc00, 0x0000
	st.o	rd7, [rb4, 0]

	@@ --- 1. trap cause / magic check (CFXTRAP = 1<<0, magic 0x30001) ---
	cfx2rd	cfx_hmon, cg5, rc2, rd6		@@ cause_id
	LD64	rd7, 0x0001, 0x0000, 0x0000, 0x0000
	cmp.uo	rd8, rd6, rd7
	br.nz	{rd8}?, [rb0, hmon_exit_b7]
	cfx2rd	cfx_hmon, cg5, rc4, rd6		@@ cause_info
	LD64	rd7, 0xffff, 0x0003, 0x0000, 0x0000	@@ 0x0003_ffff
	and.o	rd6, rd6, rd7
	LD64	rd7, 0x0001, 0x0003, 0x0000, 0x0000	@@ 0x0003_0001
	cmp.uo	rd8, rd6, rd7
	br.nz	{rd8}?, [rb0, hmon_exit_b7]

	@@ --- 2. lookup + load smon ---
	LD64	rd1, 0x0002, 0x0000, 0x0000, 0x0000	@@ type 2 = smon
	LD64	rb9, 0x2000, 0xffff, 0xffff, 0x0000
	call	[rb9, rd0, 0]
	br.nz	{rd8}?, [rb0, hmon_exit_code]
	rd2rb	rb14, rd4, 1			@@ save flags across the loader

	LD64	rb2, 0x0000, 0x0000, 0x0bff, 0x0000	@@ smon SRAM base
	LD64	rb9, 0x2400, 0xffff, 0xffff, 0x0000
	call	[rb9, rd0, 0]
	br.z	{rd8}?, [rb0, hmon_smon_loaded]

	@@ load failed: REQUIRED=0 skips the copy and continues (the chain then
	@@ fails visibly, never silently); REQUIRED=1 reports the loader code.
	rb2rd	rd7, rb14, 1
	LD64	rd6, 0x0001, 0x0000, 0x0000, 0x0000
	and.o	rd7, rd7, rd6
	br.nz	{rd7}?, [rb0, hmon_exit_code]
	rb2rd	rd5, rb2, 1			@@ fallback vector = smon base
hmon_smon_loaded:
	@@ rd5 = smon e_entry

	@@ --- 3a. cfx_smon: S-mode vector + switch_run_mode = supv ---
	cfx2rc	cfx_smon, cg3, rc10, rd5
	LD64	rd6, 0x0002, 0x0000, 0x0000, 0x0000
	cfx2rc	cfx_smon, cg3, rc8, rd6

	@@ --- 3b. run-time cfx permissions (ADR-0043 D9, ADR-0045 D4) ---
	@@ 0xffff_ffff_ffff_fff3 = default mask with source smon (bit2) and hmon
	@@ (bit3) cleared; only implemented cfx are touched.
	LD64	rd6, 0xfff3, 0xffff, 0xffff, 0xffff
	cfx2rc	cfx_ptw, cg2, rc0, rd6
	cfx2rc	cfx_ptw, cg2, rc1, rd6
	cfx2rc	cfx_ptw, cg2, rc2, rd6
	cfx2rc	cfx_ptw, cg2, rc3, rd6
	cfx2rc	cfx_pmem, cg2, rc0, rd6
	cfx2rc	cfx_pmem, cg2, rc1, rd6
	cfx2rc	cfx_pmem, cg2, rc2, rd6
	cfx2rc	cfx_pmem, cg2, rc3, rd6
	cfx2rc	cfx_ptw, cg3, rc12, rd6
	cfx2rc	cfx_pmem, cg3, rc12, rd6
	@@ Read back the delegation register and hand it to smon through RAM
	@@ (QEMU currently only stores it; the probe asserts the stored value).
	cfx2rd	cfx_ptw, cg3, rc12, rd6
	LD64	rb4, 0x0018, 0x0001, 0xfc00, 0x0000
	st.o	rd6, [rb4, 0]

	@@ cfx_hmon.supv.cfxtrap: allow source smon to trap back to hmon
	@@ (poweroff/reset service, D13).
	cfx2rc	cfx_hmon, cg2, rc0, rd6

	@@ --- 3c. revoke hmon's own cfx_pmem access (D13).  rc2 (cfxreg) is
	@@ written last: after it hmon can no longer touch cfx_pmem at all.
	LD64	rd6, 0xffff, 0xffff, 0xffff, 0xffff
	cfx2rc	cfx_pmem, cg3, rc0, rd6
	cfx2rc	cfx_pmem, cg3, rc1, rd6
	cfx2rc	cfx_pmem, cg3, rc3, rd6
	cfx2rc	cfx_pmem, cg3, rc2, rd6

	@@ --- 4. clear the observation registers, hand off to smon ---
	LD64	rd5, 0x0000, 0x0000, 0x0000, 0x0000
	LD64	rd6, 0x0000, 0x0000, 0x0000, 0x0000
	LD64	rd7, 0x0000, 0x0000, 0x0000, 0x0000
	LD64	rd8, 0x0000, 0x0000, 0x0000, 0x0000
	LD64	rd9, 0x0000, 0x0000, 0x0000, 0x0000
	LD64	rd10, 0x0000, 0x0000, 0x0000, 0x0000
	LD64	rd11, 0x0000, 0x0000, 0x0000, 0x0000
	LD64	rd12, 0x0000, 0x0000, 0x0000, 0x0000
	LD64	rd13, 0x0000, 0x0000, 0x0000, 0x0000
	LD64	rd14, 0x0000, 0x0000, 0x0000, 0x0000
	trap	cfx_smon, 0x30001

hmon_park:
	@@ D14: hmon never returns to power.  Poison word at RAM 0x...0f08.
	LD64	rb4, 0x0108, 0x0001, 0xfc00, 0x0000
	LD64	rd6, 0xbeef, 0xdead, 0x0000, 0x0000
	st.o	rd6, [rb4, 0]
hmon_spin:
	jump	[rb0, hmon_spin]

hmon_exit_b7:
	LD64	rd8, 0x00b7, 0x0000, 0x0000, 0x0000
hmon_exit_code:
	rd2rd	rd1, rd8, 1
	jump	[rb0, hmon_exit]

hmon_exit:
	@@ SYS_EXIT block in hmon SRAM (0x0fff_0000_0ff0).
	LD64	rb16, 0x0ff0, 0x0000, 0x0fff, 0x0000
	LD64	rd16, 0x0026, 0x0002, 0x0000, 0x0000
	st.o	rd16, [rb16, 0]
	st.o	rd1, [rb16, 8]
	LD64	rd16, 0x0018, 0x0000, 0x0000, 0x0000
	trap	cfx_umon, 0x3FF00
	swym	0
