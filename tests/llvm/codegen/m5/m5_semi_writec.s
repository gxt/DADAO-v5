; m5_semi_writec.s — M5 L3 execution vector: semihosting SYS_WRITEC (TESTCASES-033t).
;
; Capability: semihosting "console" service SYS_WRITEC (0x03) writes the single
; character at the argument pointer (rb16) to the semihosting console
; (contract-semihosting.md §3; Machine-01 §5.3).  Entry tag immu18[17:16]==2'b11
; (contract-semihosting.md §1); the call is short-circuited in the decode layer
; and returns by pc += 4 (contract-semihosting.md §4).
;
; Loaded as a flat bin at the RAM@0 base 0x0000_0000_0000 by `-kernel`
; (ADR-0004 D2.3 path B) and entered in user mode by the SEE bootrom
; (QEMU-047t / Machine-01 §2).  Expected values are derived on the host from the
; contract (see tools/testcases/validate_m5_vectors.py); they are never taken
; from QEMU output.
;
; Expected: console "A"; host $? = 0x40 (SYS_EXIT pass token).

; @m5 name=m5_semi_writec
; @m5 kind=semihosting
; @m5 service=0x03
; @m5 service_name=SYS_WRITEC
; @m5 console=41
; @m5 console_data=41
; @m5 exit=0x40

	.text
	.globl	_start
_start:
	; rb16 -> RAM@0 + 0x1000 (argument pointer)
	set.zw	rb16, wp0, 0x1000
	; store 'A' at [rb16]
	set.zw	rd8, wp0, 0x0041
	st.b	rd8, [rb16, 0]
	; SYS_WRITEC = 0x03, then the semihosting trap (tag 0x3000_0 sets
	; immu18[17:16] = 2'b11)
	set.zw	rd16, wp0, 0x0003
	trap	cfx_umon, 0x30000
	; report success via SYS_EXIT (pass token 0x40)
	set.zw	rb16, wp0, 0x2000
	set.zw	rd8, wp1, 0x0002
	or.w	rd8, wp0, 0x0026
	st.o	rd8, [rb16, 0]
	set.zw	rd9, wp0, 0x0040
	st.o	rd9, [rb16, 8]
	set.zw	rd16, wp0, 0x0018
	trap	cfx_umon, 0x30000
	swym	0
