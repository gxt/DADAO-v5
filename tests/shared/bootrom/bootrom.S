 @@ bootrom.S — DADAO-v5 SEE bootrom firmware (QEMU-047t, M5).
 @@
 @@ First real user of the LLVM-060t cfx instructions (`cfx2rc` / `trap`); see
 @@ ADR-0020 D12 (new bootrom: initial permission/vector configuration), ADR-0043
 @@ D8/D9 (power -> hmon -> smon handoff) and ADR-0045 (two-axis cfx permission).
 @@
 @@ Loading model (ADR-0004 D2.3 path B — the raw-bin dual-image path):
 @@   qemu-system-dadao -M dadao-m1 -bios bootrom.bin -kernel app.bin
 @@   * this ROM blob is loaded at the boot ROM base 0xffff_ffff_0000
 @@     (= cfx_power_hypv_excp_vector, spec/DADAO-12 §2.1) via `-bios`;
 @@   * reset PC (rb0) = 0xffff_ffff_0000 is unchanged, so the bootrom runs first
 @@     in hypv/CfxPower (cpu reset state, QEMU-044t);
 @@   * the flat test application is loaded at the RAM base
 @@     0xFC00_0000_0000 by `-kernel` (path B fixed entry, ADR-0004 D2.2/D2.3;
 @@     RAM is the single RAM segment, ADR-0004 R3 + rev. 2026-10-11);
 @@   * the bootrom configures cfx then hands off to that entry in user mode.
 @@ The M4 single-ELF path (ADR-0004 D2.2/D2.3 path A, no `-bios`) is untouched.
 @@
 @@ What the bootrom configures (spec/Machine-01 §2/§3/§4, contract-see §1/§3):
 @@   * power stage (cfx63, reset cfx) only configures hmon (cfx3): cfx_hmon
 @@     hypv cfxtrap allows power (default) and its H-mode vector points at the
 @@     hmon stage below (ADR-0043 D8; power cannot configure other cfx under
 @@     ADR-0045 D4 -- their masks default to hmon-only);
 @@   * hmon stage (cfx3, still executing from the power BootROM) configures
 @@     cfx_umon (cfx0) user/hypv vectors and switch modes, clears cfx_power's
 @@     cfxmem/cfxexe masks for source cfx0 (so the user app can use RAM and
 @@     fetch this ROM), then `trap cfx_umon` -> user app (ADR-0043 D9);
 @@   * hmon parks after the handoff (D14); it never escapes back to power.
 @@
 @@ Register map used: rb1 = SP, rd2 = app entry, rd3 = handler address,
 @@ rd4 = hmon stage address.  Address construction uses the same `set.zw` +
 @@ `or.w` wyde sequence as the M1-M3 test patterns (ADR-0004 D6.2); all
 @@ immediates are hand-derived from the memory map above (no relocation --
 @@ checked with `llvm-readobj -r`).

	.text
	.globl	_start
_start:
	@@ --- power stage (cfx63, hypv) ---
	@@ SP (rb1) -> RAM top-ish (0xFC00_0000_00f0_0000 = RAM base + 15 MiB)
	set.zw	rb1, wp1, 0x00f0
	or.w	rb1, wp2, 0xfc00

	@@ rd2 = application entry = RAM base 0xFC00_0000_0000
	set.zw	rd2, wp2, 0xfc00

	@@ rd3 = user exception handler = 0xffff_ffff_0200 (ROM base + 0x200)
	set.zw	rd3, wp2, 0xffff
	or.w	rd3, wp1, 0xffff
	or.w	rd3, wp0, 0x0200

	@@ rd4 = hmon stage = 0xffff_ffff_0280 (ROM base + 0x280)
	set.zw	rd4, wp2, 0xffff
	or.w	rd4, wp1, 0xffff
	or.w	rd4, wp0, 0x0280

	@@ cfx_hmon (cfxha 3) hypv vector = hmon stage; cfxtrap already allows
	@@ power (0x7FFF_FFFF_FFFF_FFF7, ADR-0045 D4).
	cfx2rc	cfx_hmon, cg3, rc10, rd4

	@@ hypv -> hmon handoff (ADR-0043 D8)
	trap	cfx_hmon, 0
	swym	0				@@ guard: power never resumes (D14)

	.org 0x180
_exit_block:
	.dd.o64 0x20026				@@ ADP_Stopped_ApplicationExit
	.dd.o64 0

	@@ --- user exception handler (cfx_umon.cg0.excp_vector target).  Returns to
	@@     the instruction after the caller's `trap` through `escape`
	@@     (Machine-01 §4.2; contract-see §4). ---
	.org 0x200
_handler:
	escape	cfx_umon, [excp_cause_ip, 4]
	swym	0

	@@ --- hmon stage (cfx3, executing from the power BootROM; source cfx3 is
	@@     allowed by the default masks of every cfx). ---
	.org 0x280
_hmon_stage:
	@@ cfx_umon hypv: switch to user + vector = app entry (handoff target)
	cfx2rc	cfx_umon, cg3, rc8, rd0		@@ switch_run_mode = user (0)
	cfx2rc	cfx_umon, cg3, rc9, rd0		@@ switch_cfx_mask = 0 (allow all)
	cfx2rc	cfx_umon, cg3, rc10, rd2	@@ excp_vector   = app entry

	@@ cfx_umon user: handler vector + user mode for later traps
	cfx2rc	cfx_umon, cg0, rc8, rd0		@@ switch_run_mode = user (0)
	cfx2rc	cfx_umon, cg0, rc10, rd3	@@ excp_vector   = handler

	@@ cfx_power user: allow source cfx_umon (0) to access RAM/MMIO and fetch
	@@ this BootROM (cfxtrap/cfxreg are not needed by the app).
	cfx2rc	cfx_power, cg0, rc1, rd0	@@ cfxmem mask = 0
	cfx2rc	cfx_power, cg0, rc3, rd0	@@ cfxexe mask = 0

	@@ hmon -> user app (trap cfx_umon uses cfx_umon.hypv vector above)
	trap	cfx_umon, 0
	swym	0				@@ hmon parks (D14)
