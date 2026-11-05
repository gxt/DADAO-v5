@@ m5_trap_escape.s — M5 L3 execution vector: general trap enters the vector, escape returns (TESTCASES-033t).
@@
@@ Capability: a general (non-semihosting) `trap cfx_umon, immu18` with
@@ immu18 < 0x3FF00 records cause CFXTRAP (1<<0) and enters the target cfx
@@ exception vector of the *current* run mode; the callee returns with
@@ `escape cfx_umon, [excp_cause_ip, 4]` (DADAO-12 §5; contract-see.md §4;
@@ DADAO-22 §1).
@@
@@ TESTCASES-092t (§4): the body runs in hypv and the earlier boot stage (hmon)
@@ points cfx_umon's hypv vector at the profile ENTRY, i.e. at the body itself —
@@ a trap into that vector would restart the body (self-loop).  The body
@@ therefore installs its own vector first: `cfx2rc cfx_umon, cg3, rc10, <stub>`.
@@ cfx0 is the body's *own* cfx (self), so the write is legal; cfx_hmon's vector
@@ is CFXPERM-denied from hypv and cannot be installed.  The stub is the single
@@ word `escape cfx_umon, [excp_cause_ip, 4]`, placed *immediately before*
@@ `main`; the installer builds its address as `rb0(main) - 4` (one word back),
@@ so no absolute label is needed (DADAO has no PC-relative label relocation for
@@ `add.si`).
@@
@@ The vector verifies (a) the recorded cause id is CFXTRAP and (b) escape_num
@@ (cfx_umon.cg4.rc5) advanced by one, i.e. the escape really executed.
@@
@@ Expected: cause = CFXTRAP (0x1); escape_num = 1; host $? = 0x30 (SYS_EXIT pass token).

@@ @m5 name=m5_trap_escape
@@ @m5 kind=trap
@@ @m5 cause=CFXTRAP
@@ @m5 op=trap cfx_umon, 0x0123
@@ @m5 exit=0x30
@@ @m5 fail_exit=0x72

	.include "machine.inc"

	.text
	.globl	_start
_start:
	jump	[rb0, main]			@@ word 0: skip the vector stub

escape_stub:
	@@ cfx_umon hypv exception vector: return to excp_cause_ip + 4
	escape	cfx_umon, [excp_cause_ip, 4]

main:
	@@ cfx_umon.hypv.excp_vector = escape_stub (the word right before main)
	rb2rd	rd22, rb0, 1			@@ rd22 = address of main
	add.si	rd22, -4			@@ main - 1 word = escape_stub
	cfx2rc	cfx_umon, cg3, rc10, rd22

	@@ general trap: immu18 = 0x0123 (below the semihosting range 0x3FF00-0x3FFFF)
	trap	cfx_umon, 0x0123

	@@ (a) cause id must be CFXTRAP
	cfx2rd	cfx_umon, cg5, rc2, rd10
	set.zw	rd12, wp0, 0x0001		@@ CFXTRAP = 1 << 0
	cmp.so	rd11, rd10, rd12
	br.nz	{rd11}?, [rb0, fail]

	@@ (b) escape_num must have advanced to 1 (the handler ran `escape`)
	cfx2rd	cfx_umon, cg4, rc5, rd13
	set.zw	rd12, wp0, 0x0001
	cmp.so	rd11, rd13, rd12
	br.nz	{rd11}?, [rb0, fail]

	@@ pass: SYS_EXIT(0x30)
	LOAD_ADDR rb16, ENTRY + 0x2000
	set.zw	rd8, wp1, 0x0002
	or.w	rd8, wp0, 0x0026
	st.o	rd8, [rb16, 0]
	set.zw	rd9, wp0, 0x0030
	st.o	rd9, [rb16, 8]
	set.zw	rd16, wp0, 0x0018
	trap	cfx_umon, 0x3FF00
	swym	0

fail:
	LOAD_ADDR rb16, ENTRY + 0x2000
	set.zw	rd8, wp1, 0x0002
	or.w	rd8, wp0, 0x0026
	st.o	rd8, [rb16, 0]
	set.zw	rd9, wp0, 0x0072
	st.o	rd9, [rb16, 8]
	set.zw	rd16, wp0, 0x0018
	trap	cfx_umon, 0x3FF00
	swym	0
