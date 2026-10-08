; m5_semi_exit.s — M5 L3 execution vector: semihosting SYS_EXIT (TESTCASES-033t).
;
; Capability: semihosting SYS_EXIT (0x18) terminates the guest and propagates its
; status code to the host $?.  The argument block is {reason, subcode}; reason
; ADP_Stopped_ApplicationExit (0x20026) selects a normal application exit and
; the subcode becomes the process exit status (contract-semihosting.md §5;
; Machine-01 §5.5; ADR-0020 D8).
;
; Loaded as a flat bin at the legacy RAM base 0xffff_0000_0000 by `-kernel`
; (ADR-0004 D2.3 path B) and entered in user mode by the SEE bootrom.
;
; Expected: host $? = 0x43 (the subcode itself; this vector has no separate pass
; token because SYS_EXIT is the observation).

; @m5 name=m5_semi_exit
; @m5 kind=semihosting
; @m5 service=0x18
; @m5 service_name=SYS_EXIT
; @m5 console=
; @m5 console_data=
; @m5 exit=0x43

	.text
	.globl	_start
_start:
	; argument block at RAM@0 + 0x2000 = {0x20026, 0x43}
	set.zw	rb16, wp0, 0x2000
	set.zw	rd8, wp1, 0x0002
	or.w	rd8, wp0, 0x0026		; rd8 = 0x0002_0026
	st.o	rd8, [rb16, 0]
	set.zw	rd9, wp0, 0x0043
	st.o	rd9, [rb16, 8]
	; SYS_EXIT = 0x18
	set.zw	rd16, wp0, 0x0018
	trap	cfx_umon, 0x30000
	; not reached on a successful SYS_EXIT
	swym	0
