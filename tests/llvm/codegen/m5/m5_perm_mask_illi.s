; m5_perm_mask_illi.s — M5 L3 execution vector: cfx instruction-mask forbidden => ILLI (TESTCASES-033t).
;
; Capability / permission counter-example: a general `trap` to a *legal but
; masked* cfx must fail with ILLI.  contract-see.md §3: "cfxha 合法但指令 cfx
; mask 禁止亦触发 ILLI"; DADAO-12 §3 (mask 1 = masked); DADAO-12 §5.
;
; The bootrom clears only cfx_umon/cfx_power user trap masks; cfx_jmon (cfxha 1)
; keeps its reset value (cg0 instruction-type masks = all-1, QEMU-044t).  Since
; the current cfx is umon (0) and the target is jmon (1), the mask check applies
; and the trap is redirected to the current-mode monitor as ILLI.
;
; Expected: cause = ILLI (0x100); host $? = 0x51 (SYS_EXIT pass token).

; @m5 name=m5_perm_mask_illi
; @m5 kind=permission
; @m5 rule=mask_forbidden
; @m5 cause=ILLI
; @m5 op=trap cfx_jmon, 0
; @m5 exit=0x51
; @m5 fail_exit=0xE1

	.text
	.globl	_start
_start:
	; legal cfxha (jmon = 1) but its user trap mask bit is set -> ILLI
	trap	cfx_jmon, 0
	cfx2rd	cfx_umon, cg5, rc2, rd10
	set.zw	rd12, wp0, 0x0100		; ILLI = 1 << 8
	cmp.so	rd11, rd10, rd12
	br.nz	{rd11}?, [rb0, fail]

	; pass: SYS_EXIT(0x51)
	set.zw	rb16, wp0, 0x2000
	set.zw	rd8, wp1, 0x0002
	or.w	rd8, wp0, 0x0026
	st.o	rd8, [rb16, 0]
	set.zw	rd9, wp0, 0x0051
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
