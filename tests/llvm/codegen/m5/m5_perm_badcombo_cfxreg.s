; m5_perm_badcombo_cfxreg.s — M5 L3 execution vector: out-of-range cfx register combo => CFXREG (TESTCASES-033t).
;
; Capability / permission counter-example: reading a non-existent / over-count
; cfx register combination must fail with CFXREG.  contract-see.md §3 (SimRISC-11
; §特权指令: 不存在寄存器组合 => CFXREG); DADAO-12 §3 (rc >= scratch_regs_num =>
; CFXREG).  Every cfx has scratch_regs_num = 4 (cg6 rc0..3); asking for
; cfx_umon.cg6.rc63 is outside the register file, so `cfx2rd` raises CFXREG.
;
; Expected: cause = CFXREG (0x4); host $? = 0x53 (SYS_EXIT pass token).

; @m5 name=m5_perm_badcombo_cfxreg
; @m5 kind=permission
; @m5 rule=bad_register_combo
; @m5 cause=CFXREG
; @m5 op=cfx2rd cfx_umon, cg6, rc63, rd10
; @m5 exit=0x53
; @m5 fail_exit=0xE1

	.text
	.globl	_start
_start:
	; cg6 is the scratch register bank; rc must be < scratch_regs_num (4)
	cfx2rd	cfx_umon, cg6, rc63, rd10
	cfx2rd	cfx_umon, cg5, rc2, rd10
	set.zw	rd12, wp0, 0x0004		; CFXREG = 1 << 2
	cmp.so	rd11, rd10, rd12
	br.nz	{rd11}?, [rb0, fail]

	; pass: SYS_EXIT(0x53)
	set.zw	rb16, wp0, 0x2000
	set.zw	rd8, wp1, 0x0002
	or.w	rd8, wp0, 0x0026
	st.o	rd8, [rb16, 0]
	set.zw	rd9, wp0, 0x0053
	st.o	rd9, [rb16, 8]
	set.zw	rd16, wp0, 0x0018
	trap	cfx_umon, 0x30000
	swym	0

fail:
	set.zw	rb16, wp0, 0x2000
	set.zw	rd8, wp1, 0x0002
	or.w	rd8, wp0, 0x0026
	st.o	rd8, [rb16, 0]
	set.zw	rd9, wp0, 0x00E1
	st.o	rd9, [rb16, 8]
	set.zw	rd16, wp0, 0x0018
	trap	cfx_umon, 0x30000
	swym	0
