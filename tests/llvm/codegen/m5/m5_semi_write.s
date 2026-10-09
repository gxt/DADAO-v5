; m5_semi_write.s — M5 L3 execution vector: semihosting SYS_OPEN + SYS_WRITE (TESTCASES-033t).
;
; Capability: semihosting file service SYS_OPEN (0x01) followed by SYS_WRITE
; (0x05); the argument block is {handle, buffer pointer, byte count} and the
; return is the number of bytes NOT written (contract-semihosting.md §3;
; Machine-01 §5.3).  The host file is opened with mode 4 ("w", write+create+
; truncate, Arm Semihosting / gdb_open_modeflags[4]).
;
; SYS_WRITE writes the 4-byte buffer "WXYZ" into the host file "m5_write.txt"
; (relative to the QEMU working directory chosen by the driver).
;
; Loaded as a flat bin at the RAM@0 base 0x0000_0000_0000 by `-kernel`
; (ADR-0004 D2.3 path B) and entered in user mode by the SEE bootrom.
;
; Expected: host file m5_write.txt = "WXYZ"; host $? = 0x42 (SYS_EXIT pass token).

; @m5 name=m5_semi_write
; @m5 kind=semihosting
; @m5 service=0x05
; @m5 service_name=SYS_WRITE
; @m5 console=
; @m5 console_data=5758595a
; @m5 file=m5_write.txt
; @m5 file_data=5758595a
; @m5 exit=0x42

	.text
	.globl	_start
_start:
	; --- path "m5_write.txt\0" at RAM@0 + 0x3200 ---
	set.zw	rb16, wp0, 0x3200
	set.zw	rd8, wp0, 0x006D		; 'm'
	st.b	rd8, [rb16, 0]
	set.zw	rd8, wp0, 0x0035		; '5'
	st.b	rd8, [rb16, 1]
	set.zw	rd8, wp0, 0x005F		; '_'
	st.b	rd8, [rb16, 2]
	set.zw	rd8, wp0, 0x0077		; 'w'
	st.b	rd8, [rb16, 3]
	set.zw	rd8, wp0, 0x0072		; 'r'
	st.b	rd8, [rb16, 4]
	set.zw	rd8, wp0, 0x0069		; 'i'
	st.b	rd8, [rb16, 5]
	set.zw	rd8, wp0, 0x0074		; 't'
	st.b	rd8, [rb16, 6]
	set.zw	rd8, wp0, 0x0065		; 'e'
	st.b	rd8, [rb16, 7]
	set.zw	rd8, wp0, 0x002E		; '.'
	st.b	rd8, [rb16, 8]
	set.zw	rd8, wp0, 0x0074		; 't'
	st.b	rd8, [rb16, 9]
	set.zw	rd8, wp0, 0x0078		; 'x'
	st.b	rd8, [rb16, 10]
	set.zw	rd8, wp0, 0x0074		; 't'
	st.b	rd8, [rb16, 11]
	set.zw	rd8, wp0, 0x0000		; NUL
	st.b	rd8, [rb16, 12]

	; --- write buffer "WXYZ" at RAM@0 + 0x3300 ---
	set.zw	rb16, wp0, 0x3300
	set.zw	rd8, wp0, 0x0057		; 'W'
	st.b	rd8, [rb16, 0]
	set.zw	rd8, wp0, 0x0058		; 'X'
	st.b	rd8, [rb16, 1]
	set.zw	rd8, wp0, 0x0059		; 'Y'
	st.b	rd8, [rb16, 2]
	set.zw	rd8, wp0, 0x005A		; 'Z'
	st.b	rd8, [rb16, 3]

	; --- SYS_OPEN: block at RAM@0 + 0x3000 = {path ptr, mode, len} ---
	set.zw	rb16, wp0, 0x3000
	set.zw	rd8, wp0, 0x3200
	st.o	rd8, [rb16, 0]
	set.zw	rd9, wp0, 0x0004		; mode 4 = write
	st.o	rd9, [rb16, 8]
	set.zw	rd9, wp0, 0x000C		; name length 12
	st.o	rd9, [rb16, 16]
	set.zw	rd16, wp0, 0x0001		; SYS_OPEN
	trap	cfx_umon, 0x30000

	; --- SYS_WRITE: block at RAM@0 + 0x3100 = {handle, buf ptr, count} ---
	set.zw	rb16, wp0, 0x3100
	st.o	rd31, [rb16, 0]			; handle returned in rd31
	set.zw	rd8, wp0, 0x3300
	st.o	rd8, [rb16, 8]
	set.zw	rd9, wp0, 0x0004
	st.o	rd9, [rb16, 16]
	set.zw	rd16, wp0, 0x0005		; SYS_WRITE
	trap	cfx_umon, 0x30000

	; --- self-check: SYS_WRITE returns 0 (no unwritten bytes) ---
	set.zw	rd12, wp0, 0x0000
	cmp.so	rd11, rd31, rd12
	br.nz	{rd11}?, [rb0, fail]

	; report success via SYS_EXIT (pass token 0x42)
	set.zw	rb16, wp0, 0x2000
	set.zw	rd8, wp1, 0x0002
	or.w	rd8, wp0, 0x0026
	st.o	rd8, [rb16, 0]
	set.zw	rd9, wp0, 0x0042
	st.o	rd9, [rb16, 8]
	set.zw	rd16, wp0, 0x0018
	trap	cfx_umon, 0x30000
	swym	0

fail:
	; SYS_WRITE did not consume the whole buffer -> distinct fail token 0xE1
	set.zw	rb16, wp0, 0x2000
	set.zw	rd8, wp1, 0x0002
	or.w	rd8, wp0, 0x0026
	st.o	rd8, [rb16, 0]
	set.zw	rd9, wp0, 0x00E1
	st.o	rd9, [rb16, 8]
	set.zw	rd16, wp0, 0x0018
	trap	cfx_umon, 0x30000
	swym	0
