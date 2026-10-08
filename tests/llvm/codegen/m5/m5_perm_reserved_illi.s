; m5_perm_reserved_illi.s — M5 L3 execution vector: reserved cfxha => ILLI (TESTCASES-033t).
;
; Capability / permission counter-example: a general `trap` whose cfxha is a
; reserved code (7-14, 19-61) must fail with ILLI, redirected to the current-mode
; monitor (contract-see.md §3 "reserved cfxha (7-14, 19-61) 触发 ILLI";
; DADAO-12 §5; SimRISC-11 §特权指令).  cfxha 7 is reserved (contract-cfx-aliases
; §1 lists only umon/jmon/smon/hmon/ptw/tlb/cache/hart/llc/pmem/timer/uart/power).
;
; The application runs in user mode after the SEE bootrom handoff; the bootrom
; installed the cfx_umon user exception vector (ROM+0x200, `escape`) so the
; redirect is observable and execution resumes after the trap.  The vector then
; reads cfx_umon.cg5.rc2 (excp_cause_id) and requires it to be ILLI (1<<8).
;
; Expected: cause = ILLI (0x100); host $? = 0x50 (SYS_EXIT pass token).

; @m5 name=m5_perm_reserved_illi
; @m5 kind=permission
; @m5 rule=reserved_cfxha
; @m5 cause=ILLI
; @m5 op=trap cfx7, 0
; @m5 exit=0x50
; @m5 fail_exit=0xE1

	.text
	.globl	_start
_start:
	; reserved cfxha (7) -> ILLI
	trap	cfx7, 0
	; read back the recorded exception cause id
	cfx2rd	cfx_umon, cg5, rc2, rd10
	set.zw	rd12, wp0, 0x0100		; ILLI = 1 << 8
	cmp.so	rd11, rd10, rd12
	br.nz	{rd11}?, [rb0, fail]

	; pass: SYS_EXIT(0x50)
	set.zw	rb16, wp0, 0x2000
	set.zw	rd8, wp1, 0x0002
	or.w	rd8, wp0, 0x0026
	st.o	rd8, [rb16, 0]
	set.zw	rd9, wp0, 0x0050
	st.o	rd9, [rb16, 8]
	set.zw	rd16, wp0, 0x0018
	trap	cfx_umon, 0x30000
	swym	0

fail:
	; wrong cause -> SYS_EXIT(0xE1)
	set.zw	rb16, wp0, 0x2000
	set.zw	rd8, wp1, 0x0002
	or.w	rd8, wp0, 0x0026
	st.o	rd8, [rb16, 0]
	set.zw	rd9, wp0, 0x00E1
	st.o	rd9, [rb16, 8]
	set.zw	rd16, wp0, 0x0018
	trap	cfx_umon, 0x30000
	swym	0
