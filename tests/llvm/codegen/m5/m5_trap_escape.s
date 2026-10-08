; m5_trap_escape.s — M5 L3 execution vector: general trap enters the vector, escape returns (TESTCASES-033t).
;
; Capability: a general (non-semihosting) `trap cfx_umon, immu18` with
; immu18[17:16] != 2'b11 records cause CFXTRAP (1<<0) and enters the target cfx
; exception vector; the callee returns with `escape cfx_umon, [excp_cause_ip, 4]`
; (DADAO-12 §5; contract-see.md §4; DADAO-22 §1).  The SEE bootrom installed the
; cfx_umon user exception vector at ROM+0x200 whose handler is exactly that
; `escape`, so the trap round-trips back to the instruction after the trap.
;
; The vector verifies (a) the recorded cause id is CFXTRAP and (b) escape_num
; (cfx_umon.cg4.rc5) advanced by one, i.e. the escape really executed.
;
; Expected: cause = CFXTRAP (0x1); escape_num = 1; host $? = 0x60 (SYS_EXIT pass token).

; @m5 name=m5_trap_escape
; @m5 kind=trap
; @m5 cause=CFXTRAP
; @m5 op=trap cfx_umon, 0x0123
; @m5 exit=0x60
; @m5 fail_exit=0xE2

	.text
	.globl	_start
_start:
	; general trap: immu18[17:16] = 0x0 (not the semihosting tag 2'b11)
	trap	cfx_umon, 0x0123

	; (a) cause id must be CFXTRAP
	cfx2rd	cfx_umon, cg5, rc2, rd10
	set.zw	rd12, wp0, 0x0001		; CFXTRAP = 1 << 0
	cmp.so	rd11, rd10, rd12
	br.nz	{rd11}?, [rb0, fail]

	; (b) escape_num must have advanced to 1 (the handler ran `escape`)
	cfx2rd	cfx_umon, cg4, rc5, rd13
	set.zw	rd12, wp0, 0x0001
	cmp.so	rd11, rd13, rd12
	br.nz	{rd11}?, [rb0, fail]

	; pass: SYS_EXIT(0x60)
	set.zw	rb16, wp0, 0x2000
	set.zw	rd8, wp1, 0x0002
	or.w	rd8, wp0, 0x0026
	st.o	rd8, [rb16, 0]
	set.zw	rd9, wp0, 0x0060
	st.o	rd9, [rb16, 8]
	set.zw	rd16, wp0, 0x0018
	trap	cfx_umon, 0x30000
	swym	0

fail:
	set.zw	rb16, wp0, 0x2000
	set.zw	rd8, wp1, 0x0002
	or.w	rd8, wp0, 0x0026
	st.o	rd8, [rb16, 0]
	set.zw	rd9, wp0, 0x00E2
	st.o	rd9, [rb16, 8]
	set.zw	rd16, wp0, 0x0018
	trap	cfx_umon, 0x30000
	swym	0
