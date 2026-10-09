; bootrom_app.S — DADAO-v5 sample user application for the SEE bootrom E2E
; (QEMU-047t, M5).
;
; Loaded as a flat binary by `-kernel` at the RAM@0 base
; 0x0000_0000_0000 (ADR-0004 D2.3 path B fixed entry; single RAM segment since
; C1 step2) and entered there by the bootrom in `user` mode (Machine-01 §2/§6).
; It is the first real user of
; `cfx2rd` / `trap` / `escape` in an application, plus semihosting `SYS_EXIT`.
;
; What it does:
;   1. reads back cfx_umon.cg0.excp_vector with `cfx2rd` and compares it to the
;      bootrom-configured handler 0xffff_ffff_0200 (proves the bootrom's
;      initial vector configuration took effect);
;   2. writes/reads a value at RAM@0 + 1 MiB and round-trips a value through
;      the bootrom-provided stack pointer (rb1) in RAM@0 (proves the
;      application's stack and data live in the new RAM@0 segment);
;   3. enters the configured cfx_umon user vector with `trap`; the ROM handler
;      returns via `escape`;
;   4. exits with semihosting `SYS_EXIT` (reason ADP_Stopped_ApplicationExit,
;      code 0) — host `$?` = 0.
; Any failed check jumps to `app_fail`, which exits with SYS_EXIT code 0xE0
; (host `$?` = 224) so a broken bootrom config is observable, not silent.
;
; Raw-bin pipeline (ADR-0003 D5): single self-contained TU, assembled to an
; object and reduced to `.text` bytes with `llvm-objcopy -O binary` (no linker,
; no relocations — verified with `llvm-readobj -r`).

	.text
	.globl	_app
_app:
	; --- 1. read back cfx_umon user exception vector (cfx2rd) ---
	cfx2rd	cfx_umon, cg0, rc10, rd5		; rd5 = cfx0.cg0.excp_vector
	set.zw	rd6, wp2, 0xffff
	or.w	rd6, wp1, 0xffff
	or.w	rd6, wp0, 0x0200		; rd6 = 0xffff_ffff_0200 (handler)
	cmp.so	rd7, rd5, rd6			; rd7 = 0 iff equal
	br.nz	{rd7}?, [rb0, app_fail]

	; --- 2. RAM@0 data round-trip at 0x0000_0000_0010_0000 ---
	set.zw	rb4, wp1, 0x0010		; rb4 = RAM@0 + 1 MiB
	set.zw	rd8, wp0, 0xBEEF
	st.o	rd8, [rb4, 0]
	ld.o	rd9, [rb4, 0]
	cmp.so	rd10, rd9, rd8
	br.nz	{rd10}?, [rb0, app_fail]

	; --- 2b. stack round-trip through SP (rb1) in RAM@0 ---
	set.zw	rd11, wp0, 0x5A5A
	st.o	rd11, [rb1, -8]
	ld.o	rd12, [rb1, -8]
	cmp.so	rd13, rd12, rd11
	br.nz	{rd13}?, [rb0, app_fail]

	; --- 3. enter the configured cfx_umon user vector (trap -> handler) ---
	trap	cfx_umon, 0

	; --- 4. semihosting SYS_EXIT(0): block in ROM, rd16 = 0x18 ---
	set.zw	rb16, wp2, 0xffff
	or.w	rb16, wp1, 0xffff
	or.w	rb16, wp0, 0x0180		; rb16 -> ROM exit block
	set.zw	rd16, wp0, 0x0018		; SYS_EXIT
	trap	cfx_umon, 0x30000		; immu18[17:16]=2'b11 => semihosting
	swym	0

app_fail:
	; build {0x20026, 0xE0} in RAM@0 and SYS_EXIT(0xE0) -> host $? = 224
	set.zw	rb16, wp1, 0x0010		; rb16 = RAM@0 + 1 MiB
	set.zw	rd8, wp1, 0x0002
	or.w	rd8, wp0, 0x0026		; rd8 = 0x0002_0026
	st.o	rd8, [rb16, 0]
	set.zw	rd9, wp0, 0x00E0
	st.o	rd9, [rb16, 8]
	set.zw	rd16, wp0, 0x0018		; SYS_EXIT
	trap	cfx_umon, 0x30000
	swym	0
