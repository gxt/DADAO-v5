@@ m5_perm_badcombo_cfxreg.s — M5 L3 execution vector: out-of-range cfx register combo => CFXREG (TESTCASES-033t).
@@
@@ Capability / permission counter-example: reading a non-existent / over-count
@@ cfx register combination must fail with CFXREG.  contract-see.md §3 (SimRISC-11
@@ SimRISC-11 指令域与执行条件: 不存在寄存器组合 => CFXREG); DADAO-12 §3 (rc >= scratch_regs_num =>
@@ CFXREG).  Every cfx has scratch_regs_num = 4 (cg6 rc0..3); asking for
@@ cfx_umon.cg6.rc63 is outside the register file, so `cfx2rd` raises CFXREG.
@@
@@ DADAO-12 §5.2 / QEMU-083t: the fault is delivered to the *current-mode
@@ monitor* (the body runs in hypv, so cfx_hmon), not to the accessed cfx.
@@ hmon records the cause in the profile fault-record slot and resumes after
@@ the faulting instruction; this vector reads that slot (TESTCASES-092t §3/§4).
@@ The old body-installed cfx_umon hypv stub is gone: passing must not depend
@@ on that workaround (ISS-342).
@@
@@ Expected: cause = CFXREG (0x4); host $? = 0x23 (SYS_EXIT pass token).

@@ @m5 name=m5_perm_badcombo_cfxreg
@@ @m5 kind=permission
@@ @m5 rule=bad_register_combo
@@ @m5 cause=CFXREG
@@ @m5 op=cfx2rd cfx_umon, cg6, rc63, rd10
@@ @m5 exit=0x23
@@ @m5 fail_exit=0x71

	.include "machine.inc"

	.text
	.globl	_start
_start:
	@@ cg6 is the scratch register bank; rc must be < scratch_regs_num (4)
	cfx2rd	cfx_umon, cg6, rc63, rd10	@@ -> CFXREG into the current-mode monitor
	LOAD_ADDR rb4, FAULT_RECORD
	ld.o	rd10, [rb4, 0]			@@ fault-record[0] = cause id
	set.zw	rd12, wp0, 0x0004		@@ CFXREG = 1 << 2
	cmp.so	rd11, rd10, rd12
	br.nz	{rd11}?, [rb0, fail]

	@@ pass: SYS_EXIT(0x23)
	LOAD_ADDR rb16, ENTRY + 0x2000
	set.zw	rd8, wp1, 0x0002
	or.w	rd8, wp0, 0x0026
	st.o	rd8, [rb16, 0]
	set.zw	rd9, wp0, 0x0023
	st.o	rd9, [rb16, 8]
	set.zw	rd16, wp0, 0x0018
	trap	cfx_umon, 0x3FF00
	swym	0

fail:
	LOAD_ADDR rb16, ENTRY + 0x2000
	set.zw	rd8, wp1, 0x0002
	or.w	rd8, wp0, 0x0026
	st.o	rd8, [rb16, 0]
	set.zw	rd9, wp0, 0x0071
	st.o	rd9, [rb16, 8]
	set.zw	rd16, wp0, 0x0018
	trap	cfx_umon, 0x3FF00
	swym	0
