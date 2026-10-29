@@ m5_perm_unimpl_cfxreg.s — M5 L3 execution vector: unimplemented cfx => CFXREG (TESTCASES-033t).
@@
@@ Capability / permission counter-example: accessing an allocated-but-unimplemented
@@ core function extension must fail with CFXREG (not ILLI).  contract-see.md §3:
@@ "访问未实现的核芯功能扩展（其 cfx 寄存器）触发 CFXREG"; DADAO-22 §3;
@@ SimRISC-11 指令域与执行条件.  The test machine implements cfx0/1/2/3/63 and
@@ only cfx_ptw's Step 1 registers (ADR-0020 D9 / Machine-01 §3); cfx_tlb
@@ (cfxha 5) is allocated by the spec but not implemented here, so a `trap` to
@@ it raises CFXREG.
@@
@@ Expected: cause = CFXREG (0x4); host $? = 0x52 (SYS_EXIT pass token).

@@ @m5 name=m5_perm_unimpl_cfxreg
@@ @m5 kind=permission
@@ @m5 rule=unimplemented_cfx
@@ @m5 cause=CFXREG
@@ @m5 op=trap cfx_tlb, 0
@@ @m5 exit=0x52
@@ @m5 fail_exit=0xE1

	.text
	.globl	_start
_start:
	@@ cfxha 5 (cfx_tlb) is allocated but not implemented by the test machine
	trap	cfx_tlb, 0
	cfx2rd	cfx_umon, cg5, rc2, rd10
	set.zw	rd12, wp0, 0x0004		@@ CFXREG = 1 << 2
	cmp.so	rd11, rd10, rd12
	br.nz	{rd11}?, [rb0, fail]

	@@ pass: SYS_EXIT(0x52)
	set.zw	rb16, wp0, 0x2000
	or.w	rb16, wp2, 0xfc00
	set.zw	rd8, wp1, 0x0002
	or.w	rd8, wp0, 0x0026
	st.o	rd8, [rb16, 0]
	set.zw	rd9, wp0, 0x0052
	st.o	rd9, [rb16, 8]
	set.zw	rd16, wp0, 0x0018
	trap	cfx_umon, 0x3FF00
	swym	0

fail:
	set.zw	rb16, wp0, 0x2000
	or.w	rb16, wp2, 0xfc00
	set.zw	rd8, wp1, 0x0002
	or.w	rd8, wp0, 0x0026
	st.o	rd8, [rb16, 0]
	set.zw	rd9, wp0, 0x00E1
	st.o	rd9, [rb16, 8]
	set.zw	rd16, wp0, 0x0018
	trap	cfx_umon, 0x3FF00
	swym	0
