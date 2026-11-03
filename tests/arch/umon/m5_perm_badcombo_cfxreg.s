@@ m5_perm_badcombo_cfxreg.s — M5 L3 execution vector: out-of-range cfx register combo => CFXREG (TESTCASES-033t).
@@
@@ Capability / permission counter-example: reading a non-existent / over-count
@@ cfx register combination must fail with CFXREG.  contract-see.md §3 (SimRISC-11
@@ SimRISC-11 指令域与执行条件: 不存在寄存器组合 => CFXREG); DADAO-12 §3 (rc >= scratch_regs_num =>
@@ CFXREG).  Every cfx has scratch_regs_num = 4 (cg6 rc0..3); asking for
@@ cfx_umon.cg6.rc63 is outside the register file, so `cfx2rd` raises CFXREG.
@@
@@ TESTCASES-092t (§4): this CFXREG is framed on the *accessed* cfx (cfx_umon),
@@ not on the current-mode monitor, so the body first installs cfx_umon's hypv
@@ vector (`cfx2rc cfx_umon, cg3, rc10, <stub>`; cfx0 is the body's own cfx, so
@@ the write is legal) pointing at the local one-word stub
@@ `escape cfx_umon, [excp_cause_ip, 4]`.  The stub returns to excp_cause_ip+4
@@ and the vector reads cfx_umon.cg5.rc2 to check the cause.
@@
@@ Expected: cause = CFXREG (0x4); host $? = 0x53 (SYS_EXIT pass token).

@@ @m5 name=m5_perm_badcombo_cfxreg
@@ @m5 kind=permission
@@ @m5 rule=bad_register_combo
@@ @m5 cause=CFXREG
@@ @m5 op=cfx2rd cfx_umon, cg6, rc63, rd10
@@ @m5 exit=0x53
@@ @m5 fail_exit=0xE1

	.include "machine.inc"

	.text
	.globl	_start
_start:
	jump	[rb0, main]			@@ word 0: skip the vector stub

escape_stub:
	@@ cfx_umon hypv exception vector: return to excp_cause_ip + 4
	escape	cfx_umon, [excp_cause_ip, 4]

main:
	@@ cfx_umon.hypv.excp_vector = escape_stub (the word right before main).
	@@ Required because the CFXREG of an out-of-range register combo is raised
	@@ with *cfx_umon* as the target cfx (the accessed cfx), so it enters
	@@ cfx_umon's hypv vector — which hmon left pointing at the profile ENTRY,
	@@ i.e. at this vector's first word (a self-loop).  cfx0 is the body's own
	@@ cfx, so installing its own vector is legal.
	rb2rd	rd22, rb0, 1			@@ rd22 = address of main
	add.si	rd22, -4			@@ main - 1 word = escape_stub
	cfx2rc	cfx_umon, cg3, rc10, rd22

	@@ cg6 is the scratch register bank; rc must be < scratch_regs_num (4)
	cfx2rd	cfx_umon, cg6, rc63, rd10	@@ -> CFXREG into the stub, returns here
	cfx2rd	cfx_umon, cg5, rc2, rd10	@@ cause id recorded by that entry
	set.zw	rd12, wp0, 0x0004		@@ CFXREG = 1 << 2
	cmp.so	rd11, rd10, rd12
	br.nz	{rd11}?, [rb0, fail]

	@@ pass: SYS_EXIT(0x53)
	LOAD_ADDR rb16, ENTRY + 0x2000
	set.zw	rd8, wp1, 0x0002
	or.w	rd8, wp0, 0x0026
	st.o	rd8, [rb16, 0]
	set.zw	rd9, wp0, 0x0053
	st.o	rd9, [rb16, 8]
	set.zw	rd16, wp0, 0x0018
	trap	cfx_umon, 0x3FF00
	swym	0

fail:
	LOAD_ADDR rb16, ENTRY + 0x2000
	set.zw	rd8, wp1, 0x0002
	or.w	rd8, wp0, 0x0026
	st.o	rd8, [rb16, 0]
	set.zw	rd9, wp0, 0x00E1
	st.o	rd9, [rb16, 8]
	set.zw	rd16, wp0, 0x0018
	trap	cfx_umon, 0x3FF00
	swym	0
