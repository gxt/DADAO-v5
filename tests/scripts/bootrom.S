; bootrom.S — DADAO-v5 SEE bootrom firmware (QEMU-047t, M5).
;
; First real user of the LLVM-060t cfx instructions (`cfx2rc` / `trap`); see
; ADR-0020 D12 (new bootrom: initial permission/vector configuration) and
; ADR-0004 R1 (`-bios` load, reset vector unchanged, bootrom hypv -> user
; direct jump, no supv this version).
;
; Loading model (ADR-0004 D2.3 path B — the raw-bin dual-image path):
;   qemu-system-dadao -M dadao-m1 -bios bootrom.bin -kernel app.bin
;   * this ROM blob is loaded at the boot ROM base 0xffff_ffff_0000
;     (= cfx_power_hypv_excp_vector, spec/DADAO-12 §2.1) via `-bios`;
;   * reset PC (rb0) = 0xffff_ffff_0000 is unchanged, so the bootrom runs first
;     in hypv/CfxPower (cpu reset state, QEMU-044t);
;   * the flat test application is loaded at the legacy RAM base
;     0xffff_0000_0000 by `-kernel` (path B fixed entry, ADR-0004 D2.2/D2.3);
;   * the bootrom configures cfx then hands off to that entry in user mode.
; The M4 single-ELF path (ADR-0004 D2.2/D2.3 path A, no `-bios`) is untouched.
;
; What the bootrom configures (spec/Machine-01 §2/§3/§4, contract-see §1/§3):
;   * rb1 (SP) -> RAM@0 (ADR-0004 R3 / ADR-0020 D15): the application's stack and
;     data live in the new RAM@0 segment supplied by QEMU-049t, not in the
;     legacy RAM segment (kept only for the M1-M4 tests);
;   * cfx_umon (cfxha 0) hypv cg3: switch_run_mode = user (0), switch_cfx_mask = 0,
;     excp_vector = application entry  ->  the `trap` below is the hypv -> user
;     direct jump (QEMU-044t cfx_enter steps 7/8/10; Machine-01 §2);
;   * cfx_umon / cfx_power user cg0: excp_vector = handler, switch_run_mode = user
;     (so a user-mode trap stays in user; supv is never enabled), and the
;     instruction-type trap cfx mask + global cfx mask are cleared (0 = allow);
;   * cfx_power (cfxha 63) hypv excp_vector = handler.
;
; Register map used: rb1 = SP, rd2 = app entry, rd3 = handler address.
; Address construction uses the same `set.zw` + `or.w` wyde sequence as the
; M1-M3 test patterns (ADR-0004 D6.2); all immediates are hand-derived from the
; memory map above (no relocation — checked with `llvm-readobj -r`).

	.text
	.globl	_start
_start:
	; --- SP (rb1) -> RAM@0 top-ish (0x0000_0000_00f0_0000 = RAM@0 + 15 MiB) ---
	set.zw	rb1, wp1, 0x00f0

	; --- rd2 = application entry = legacy RAM base 0xffff_0000_0000 ---
	set.zw	rd2, wp2, 0xffff

	; --- rd3 = user exception handler = 0xffff_ffff_0200 (ROM base + 0x200) ---
	set.zw	rd3, wp2, 0xffff
	or.w	rd3, wp1, 0xffff
	or.w	rd3, wp0, 0x0200

	; --- cfx_umon (cfxha 0) cg3/hypv: mode-transfer + handoff vector ---
	cfx2rc	cfx_umon, cg3, rc8, rd0		; switch_run_mode = user (0)
	cfx2rc	cfx_umon, cg3, rc9, rd0		; switch_cfx_mask = 0 (allow all)
	cfx2rc	cfx_umon, cg3, rc10, rd2	; excp_vector   = app entry

	; --- cfx_umon (cfxha 0) cg0/user: vectors + masks ---
	cfx2rc	cfx_umon, cg0, rc8, rd0		; switch_run_mode = user (0)
	cfx2rc	cfx_umon, cg0, rc10, rd3	; excp_vector   = handler
	cfx2rc	cfx_umon, cg0, rc6, rd0		; trap_cfx_mask = 0 (allow)
	cfx2rc	cfx_umon, cg0, rc1, rd0		; global_cfx_mask = 0 (allow)

	; --- cfx_power (cfxha 63) cg0/user: vectors + masks ---
	cfx2rc	cfx_power, cg0, rc8, rd0	; switch_run_mode = user (0)
	cfx2rc	cfx_power, cg0, rc10, rd3	; excp_vector   = handler
	cfx2rc	cfx_power, cg0, rc6, rd0	; trap_cfx_mask = 0 (allow)
	cfx2rc	cfx_power, cg3, rc10, rd3	; hypv excp_vector = handler

	; --- hypv -> user direct jump: general trap enters cfx_umon's hypv vector
	;     (app entry) and switches the run mode to user (Machine-01 §2) ---
	trap	cfx_umon, 0
	swym	0				; guard: not reached on the handoff

	; --- semihosting parameter block {reason=ADP_Stopped_ApplicationExit, 0}
	;     read by the handler's SYS_EXIT (Machine-01 §5.3/§5.5) ---
	.org 0x180
_exit_block:
	.quad 0x20026				; ADP_Stopped_ApplicationExit
	.quad 0

	; --- user exception handler (cfx_umon.cg0.excp_vector target).  Returns to
	;     the instruction after the caller's `trap` through `escape`
	;     (Machine-01 §4.2; contract-see §4). ---
	.org 0x200
_handler:
	escape	cfx_umon, [excp_cause_ip, 4]
	swym	0
