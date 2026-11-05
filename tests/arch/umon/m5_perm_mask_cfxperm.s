@@ m5_perm_mask_cfxperm.s — M5 L3 execution vector: cfx cfxtrap mask forbidden => CFXPERM (TESTCASES-033t).
@@
@@ Capability / permission counter-example: a general `trap` to a *legal but
@@ denied* cfx raises CFXPERM.  DADAO-12 §3 (cfxtrap source mask, 1 = masked);
@@ DADAO-12 §5 / ADR-0045 D6 (permission denial => CFXPERM, current-mode monitor).
@@
@@ cfx_jmon (cfxha 1) keeps its reset cfxtrap mask 0xFFFF_FFFF_FFFF_FFF7, so
@@ source cfx_umon (0) is denied.  The body runs in hypv, so CFXPERM is delivered
@@ to hypv's current-mode monitor (cfx_hmon), which records the cause in the
@@ profile fault-record slot and resumes after the faulting instruction
@@ (TESTCASES-092t §3/§4); the vector then reads that slot.
@@
@@ Expected: cause = CFXPERM (0x80); host $? = 0x21 (SYS_EXIT pass token).

@@ @m5 name=m5_perm_mask_cfxperm
@@ @m5 kind=permission
@@ @m5 rule=target_cfxtrap_denied
@@ @m5 cause=CFXPERM
@@ @m5 op=trap cfx_jmon, 0
@@ @m5 exit=0x21
@@ @m5 fail_exit=0x71

	.include "machine.inc"

	.text
	.globl	_start
_start:
	@@ legal cfxha (jmon = 1) but cfxtrap source bit 0 is set -> CFXPERM
	trap	cfx_jmon, 0
	LOAD_ADDR rb4, FAULT_RECORD
	ld.o	rd10, [rb4, 0]			@@ fault-record[0] = cause id
	set.zw	rd12, wp0, 0x0080		@@ CFXPERM
	cmp.so	rd11, rd10, rd12
	br.nz	{rd11}?, [rb0, fail]

	@@ pass: SYS_EXIT(0x21)
	LOAD_ADDR rb16, ENTRY + 0x2000
	set.zw	rd8, wp1, 0x0002
	or.w	rd8, wp0, 0x0026
	st.o	rd8, [rb16, 0]
	set.zw	rd9, wp0, 0x0021
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
