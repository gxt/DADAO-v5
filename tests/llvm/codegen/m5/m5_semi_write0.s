; m5_semi_write0.s — M5 L3 execution vector: semihosting SYS_WRITE0 (TESTCASES-033t).
;
; Capability: semihosting SYS_WRITE0 (0x04) writes the NUL-terminated string at
; the argument pointer (rb16) to the semihosting console
; (contract-semihosting.md §3; Machine-01 §5.3).
;
; Loaded as a flat bin at the legacy RAM base 0xffff_0000_0000 by `-kernel`
; (ADR-0004 D2.3 path B) and entered in user mode by the SEE bootrom
; (QEMU-047t / Machine-01 §2).
;
; Expected: console "OK\n"; host $? = 0x41 (SYS_EXIT pass token).

; @m5 name=m5_semi_write0
; @m5 kind=semihosting
; @m5 service=0x04
; @m5 service_name=SYS_WRITE0
; @m5 console=4f4b0a
; @m5 console_data=4f4b0a00
; @m5 exit=0x41

	.text
	.globl	_start
_start:
	; rb16 -> RAM@0 + 0x1000; build "OK\n\0" byte by byte
	set.zw	rb16, wp0, 0x1000
	set.zw	rd8, wp0, 0x004F		; 'O'
	st.b	rd8, [rb16, 0]
	set.zw	rd8, wp0, 0x004B		; 'K'
	st.b	rd8, [rb16, 1]
	set.zw	rd8, wp0, 0x000A		; '\n'
	st.b	rd8, [rb16, 2]
	set.zw	rd8, wp0, 0x0000		; NUL terminator
	st.b	rd8, [rb16, 3]
	; SYS_WRITE0 = 0x04
	set.zw	rd16, wp0, 0x0004
	trap	cfx_umon, 0x30000
	; report success via SYS_EXIT (pass token 0x41)
	set.zw	rb16, wp0, 0x2000
	set.zw	rd8, wp1, 0x0002
	or.w	rd8, wp0, 0x0026
	st.o	rd8, [rb16, 0]
	set.zw	rd9, wp0, 0x0041
	st.o	rd9, [rb16, 8]
	set.zw	rd16, wp0, 0x0018
	trap	cfx_umon, 0x30000
	swym	0
