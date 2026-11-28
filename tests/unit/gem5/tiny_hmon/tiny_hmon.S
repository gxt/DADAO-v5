@@ tiny_hmon.S — Kaiwu-Tiny cfx_power + cfx3 hmon execution case
@@ (m13-gem5-001; m13-gem5-005 moves it onto the §6.2 two-piece load contract;
@@  m13-gem5-010 records the shared minimal handler's SRAM slots.)
@@
@@ Load contract (spec/Kaiwu §6.2): the host loader installs exactly two
@@ artefacts — the fixed 8 KiB BootROM firmware (shared power stub + the shared
@@ minimal hmon of tests/ee-tiny/cfx_hmon_tiny.S, built by
@@ build_tiny_bootrom.py) and this application ELF, whose only PT_LOAD is in
@@ SRAM and whose e_entry is the fixed ENTRY 0xffff_ff00_2000.  The host never
@@ installs BootROM or hmon.
@@
@@ Structure:
@@
@@   BootROM (0xffff_ffff_0000, power/cfx63) — shared firmware power stub:
@@     * validates the image index table, copies the hmon code into the hmon
@@       SRAM, writes the default return address (data page +0x18), `trap
@@       cfx_hmon, 0x30001`
@@     * jumps to the fixed application entry after the hmon escape
@@
@@   hmon SRAM (0x0fff_0000_0000, cfx3) — shared minimal handler (m13-integ-007):
@@     * saves excp_cause_id / excp_cause_ip / excp_cause_info to the data-page
@@       slots +0x00 / +0x08 / +0x10 (page base 0xC00), restores rd63/rb63, and
@@       escapes to the framework return address read from slot +0x18; no magic
@@       check, no IALIGN rewrite, no `+4` policy, no park loop (the data page
@@       0xC00–0xCFF is outside the copied image segment)
@@
@@   Application (SRAM 0xffff_ff00_2000, running with cfx_power current):
@@     * records the hand-over (record 0) from the hmon data slots
@@       +0x00/+0x08/+0x10/+0x18 of the 0xC00 page
@@     * cfx2rd/cfx2rc register checks (power/hmon id, vector, switch mode,
@@       prev mode, counters, scratch, intr mask, cg7 space descriptors)
@@     * five synchronous fault classes x 3 cases (CFXMEM/ILLI/UNDI/MALIGN/
@@       IALIGN), plus CFXTRAP/CFXESC/CFXPERM/CFXREG: before each fault the
@@       application writes its landing address to the return slot (+0x18); at
@@       the landing it records the four hmon data slots, so every cause record
@@       is the handler's own saved state (no test-only dispatch path)
@@     * CFXESC is the exception: it is delivered to the *current* cfx
@@       (cfx63, DADAO-12 §5.2(一)), so the body installs cfx63's hypv
@@       vector (cg3 rc15) at `esc_land`, records cfx63's own cg5 frame
@@       there, and asserts the monitor's SRAM slots and `excp_sync_num`
@@       were not written (reverse assertion)
@@     * Tiny hypv invariance: write switch_run_mode = user, take CFXMEM,
@@       read a cg3 (hypv-only) register, prev_run_mode stays 3
@@     * exports the result table through SYS_OPEN + SYS_WRITE and stops with
@@       SYS_EXIT (0x21 pass, 0x71 fail)
@@
@@ The expected values live in `expected.yaml`; this program never decides the
@@ oracle by itself (it only records the architectural values).

	.include "machine-tiny.inc"
	.include "tiny_hmon_layout.inc"

	.macro	LOAD_ABS reg, sym
	@@ Absolute symbol address (link-time R_DADAO_ABS48): the linker fills the
	@@ four 16-bit fields from the symbol value (the `set.rb` pseudo-instruction
	@@ only masks numeric constants and cannot take a section-relative label).
	set.zw	\reg, wp0, \sym
	or.w	\reg, wp1, \sym
	or.w	\reg, wp2, \sym
	or.w	\reg, wp3, \sym
	.endm

	.equ	IALIGN_TARGET0, ENTRY + 0x1C01
	.equ	IALIGN_TARGET1, ENTRY + 0x1C02
	.equ	IALIGN_TARGET2, ENTRY + 0x1C03

	.globl	IALIGN_TARGET0
	.globl	IALIGN_TARGET1
	.globl	IALIGN_TARGET2

@@ ---------------------------------------------------------------------------
@@ Application: entered from the power stub at the fixed entry after the
@@ hand-over.  The host loader installed only this ELF; power/hmon came from
@@ the BootROM firmware image.
@@ ---------------------------------------------------------------------------
	.text
	.globl	_start
_start:

	@@ Initialise the result slot before any check: the application owns the
	@@ slot pointer (the power stub no longer prepares result memory).
	set.rd rd22, RESULTS
	set.rb rb3, SLOT_PTR
	st.o	rd22, [rb3, 0]
	set.rb rb4, FAILCNT
	st.o	rd0, [rb4, 0]
	LOAD_ABS rb21, record_cause		@@ append a cause record from the slots
	set.rb rb22, HMON_BASE + HMON_DATA	@@ hmon data page base (0xC00)

	@@ Record 0: the power -> hmon hand-over.  The shared minimal handler
	@@ saved the CFXTRAP cause registers to +0x00/+0x08/+0x10 and escaped to
	@@ the power stub via the return address power put in +0x18 (trap + 4).
	call	[rb21, rd0, 0]

	.globl	main
main:
	set.rb rb20, RECORD_CHECK

	@@ ---- register checks (ids 1..16) -------------------------------------
	cfx2rd	cfx_hmon, cg4, rc0, rd10
	set.zw	rd11, wp0, 3
	set.zw	rd12, wp0, 1
	call	[rb20, rd0, 0]

	cfx2rd	cfx_power, cg4, rc0, rd10
	set.zw	rd11, wp0, 63
	set.zw	rd12, wp0, 2
	call	[rb20, rd0, 0]

	cfx2rd	cfx_hmon, cg3, rc15, rd10
	set.rd rd11, HMON_BASE
	set.zw	rd12, wp0, 3
	call	[rb20, rd0, 0]

	cfx2rd	cfx_hmon, cg3, rc14, rd10
	set.zw	rd11, wp0, 3
	set.zw	rd12, wp0, 4
	call	[rb20, rd0, 0]

	cfx2rd	cfx_hmon, cg5, rc0, rd10
	set.zw	rd11, wp0, 3
	set.zw	rd12, wp0, 5
	call	[rb20, rd0, 0]

	cfx2rd	cfx_hmon, cg4, rc2, rd10
	set.zw	rd11, wp0, 1
	set.zw	rd12, wp0, 6
	call	[rb20, rd0, 0]

	set.rd rd11, 0x1122334455667788
	cfx2rc	cfx_hmon, cg6, rc0, rd11
	cfx2rd	cfx_hmon, cg6, rc0, rd10
	set.zw	rd12, wp0, 7
	call	[rb20, rd0, 0]

	@@ cg15 rc3 `cfx_hmon_async_intr_mask` is RW (DADAO-12 §4.1/§5.4;
	@@ ADR-0064 D6: the mask moved here, cg8 rc1 is reserved).
	set.rd rd11, 0x0000000000000F0F
	cfx2rc	cfx_hmon, cg15, rc3, rd11
	cfx2rd	cfx_hmon, cg15, rc3, rd10
	set.zw	rd12, wp0, 8
	call	[rb20, rd0, 0]

	cfx2rd	cfx_hmon, cg7, rc0, rd10
	set.zw	rd11, wp0, 3
	set.zw	rd12, wp0, 9
	call	[rb20, rd0, 0]

	cfx2rd	cfx_hmon, cg7, rc1, rd10
	set.rd rd11, 0x3FF00000000
	set.zw	rd12, wp0, 10
	call	[rb20, rd0, 0]

	cfx2rd	cfx_hmon, cg7, rc2, rd10
	set.rd rd11, 0x2000
	set.zw	rd12, wp0, 11
	call	[rb20, rd0, 0]

	cfx2rd	cfx_hmon, cg7, rc3, rd10
	set.zw	rd11, wp0, 7
	set.zw	rd12, wp0, 12
	call	[rb20, rd0, 0]

	cfx2rd	cfx_power, cg7, rc0, rd10
	set.zw	rd11, wp0, 5
	set.zw	rd12, wp0, 13
	call	[rb20, rd0, 0]

	cfx2rd	cfx_power, cg7, rc1, rd10
	set.rd rd11, 0x3FFFFFF0000
	set.zw	rd12, wp0, 14
	call	[rb20, rd0, 0]

	cfx2rd	cfx_power, cg7, rc2, rd10
	set.rd rd11, 0x2000
	set.zw	rd12, wp0, 15
	call	[rb20, rd0, 0]

	cfx2rd	cfx_power, cg7, rc3, rd10
	set.zw	rd11, wp0, 5
	set.zw	rd12, wp0, 16
	call	[rb20, rd0, 0]

	@@ ---- cg3 rc15 write ignores the low two bits (DADAO-13 §1) -----------
	@@ Writing HMON_BASE|3 must land as HMON_BASE: no fault, low bits cleared,
	@@ read-back is the stored value.
	set.rd rd11, HMON_BASE + 3
	cfx2rc	cfx_hmon, cg3, rc15, rd11
	cfx2rd	cfx_hmon, cg3, rc15, rd10
	set.rd rd11, HMON_BASE
	set.zw	rd12, wp0, 41
	call	[rb20, rd0, 0]

	@@ ---- CFXMEM x 3 (17..19) --------------------------------------------
	@@ Before each fault: the return slot (+0x18) <- the landing address the
	@@ framework wants the handler to escape to.  At the landing, record_cause
	@@ reads the four hmon data-page slots into one 32-byte record.
	LOAD_ABS rb5, land_mem0
	st.o	rb5, [rb22, HMON_SLOT_RETURN]
	set.rb rb3, 0x1000000000
	.globl	f_mem0
f_mem0:
	ld.o	rd10, [rb3, 0]
	.globl	land_mem0
land_mem0:
	call	[rb21, rd0, 0]

	LOAD_ABS rb5, land_mem1
	st.o	rb5, [rb22, HMON_SLOT_RETURN]
	set.rb rb3, 0xFFFFFF800000
	.globl	f_mem1
f_mem1:
	ld.o	rd10, [rb3, 0]
	.globl	land_mem1
land_mem1:
	call	[rb21, rd0, 0]

	LOAD_ABS rb5, land_mem2
	st.o	rb5, [rb22, HMON_SLOT_RETURN]
	set.rb rb3, HMON_BASE + 0x10000
	.globl	f_mem2
f_mem2:
	ld.o	rd10, [rb3, 0]
	.globl	land_mem2
land_mem2:
	call	[rb21, rd0, 0]

	@@ ---- ILLI x 3 (20..22) ----------------------------------------------
	LOAD_ABS rb5, land_illi0
	st.o	rb5, [rb22, HMON_SLOT_RETURN]
	.globl	f_illi0
f_illi0:
	trap	cfx7, 0
	.globl	land_illi0
land_illi0:
	call	[rb21, rd0, 0]

	LOAD_ABS rb5, land_illi1
	st.o	rb5, [rb22, HMON_SLOT_RETURN]
	.globl	f_illi1
f_illi1:
	cfx2rd	cfx7, cg0, rc0, rd10
	.globl	land_illi1
land_illi1:
	call	[rb21, rd0, 0]

	LOAD_ABS rb5, land_illi2
	st.o	rb5, [rb22, HMON_SLOT_RETURN]
	.globl	f_illi2
f_illi2:
	@@ reserved target: `escape cfxHA` has imms18 = 0 (SBZ, §5.1) => ILLI.
	escape	cfx7
	.globl	land_illi2
land_illi2:
	call	[rb21, rd0, 0]

	@@ ---- UNDI x 3 (23..25) ----------------------------------------------
	LOAD_ABS rb5, land_undi0
	st.o	rb5, [rb22, HMON_SLOT_RETURN]
	.globl	f_undi0
f_undi0:
	.dd.t32	0x08040001
	.globl	land_undi0
land_undi0:
	call	[rb21, rd0, 0]

	LOAD_ABS rb5, land_undi1
	st.o	rb5, [rb22, HMON_SLOT_RETURN]
	.globl	f_undi1
f_undi1:
	.dd.t32	0x1B040001
	.globl	land_undi1
land_undi1:
	call	[rb21, rd0, 0]

	LOAD_ABS rb5, land_undi2
	st.o	rb5, [rb22, HMON_SLOT_RETURN]
	.globl	f_undi2
f_undi2:
	.dd.t32	0x58040001
	.globl	land_undi2
land_undi2:
	call	[rb21, rd0, 0]

	@@ ---- MALIGN x 3 (26..28) --------------------------------------------
	LOAD_ABS rb5, land_malign0
	st.o	rb5, [rb22, HMON_SLOT_RETURN]
	set.rb rb3, RAM_BASE + 1
	.globl	f_malign0
f_malign0:
	ld.o	rd10, [rb3, 0]
	.globl	land_malign0
land_malign0:
	call	[rb21, rd0, 0]

	LOAD_ABS rb5, land_malign1
	st.o	rb5, [rb22, HMON_SLOT_RETURN]
	set.rb rb3, RAM_BASE + 4
	.globl	f_malign1
f_malign1:
	st.o	rd10, [rb3, 0]
	.globl	land_malign1
land_malign1:
	call	[rb21, rd0, 0]

	LOAD_ABS rb5, land_malign2
	st.o	rb5, [rb22, HMON_SLOT_RETURN]
	set.rb rb3, RAM_BASE + 2
	.globl	f_malign2
f_malign2:
	ld.ut	rd10, [rb3, 0]
	.globl	land_malign2
land_malign2:
	call	[rb21, rd0, 0]

	@@ ---- IALIGN x 3 (29..31) --------------------------------------------
	@@ The recorded IP is the illegal target itself (no next-IP write-back):
	@@ the fail-and-resume path goes through the framework return slot only.
	LOAD_ABS rb5, land_ialign0
	st.o	rb5, [rb22, HMON_SLOT_RETURN]
	set.rb rb2, IALIGN_TARGET0
	.globl	f_ialign0
f_ialign0:
	jump	[rb2, rd0, 0]
	.globl	land_ialign0
land_ialign0:
	call	[rb21, rd0, 0]

	LOAD_ABS rb5, land_ialign1
	st.o	rb5, [rb22, HMON_SLOT_RETURN]
	set.rb rb2, IALIGN_TARGET1
	.globl	f_ialign1
f_ialign1:
	jump	[rb2, rd0, 0]
	.globl	land_ialign1
land_ialign1:
	call	[rb21, rd0, 0]

	LOAD_ABS rb5, land_ialign2
	st.o	rb5, [rb22, HMON_SLOT_RETURN]
	set.rb rb2, IALIGN_TARGET2
	.globl	f_ialign2
f_ialign2:
	jump	[rb2, rd0, 0]
	.globl	land_ialign2
land_ialign2:
	call	[rb21, rd0, 0]

	@@ ---- general trap into hmon (32) ------------------------------------
	LOAD_ABS rb5, land_trap
	st.o	rb5, [rb22, HMON_SLOT_RETURN]
	.globl	f_trap
f_trap:
	trap	cfx_hmon, 0x0123
	.globl	land_trap
land_trap:
	call	[rb21, rd0, 0]

	@@ ---- escape frame error => CFXESC (33) ------------------------------
	@@ DADAO-12 §5.1/§5.2(一): an escape target/frame error raises the
	@@ *current* cfx's CFXESC, never the current run mode monitor.  The body
	@@ runs with current cfx = cfx_power (63): hmon's escape restored
	@@ `excp_prev_cfx_code` = 63 (§5.3 step 1), and cfx63's cg5 was never
	@@ written (no earlier exception targets cfx63), so `excp_cause_id` = 0
	@@ and the cg5 frame is invalid (§5.1 "所选帧无效").
	@@ The frame is delivered to cfx63's hypv vector (cg3 rc15, §3.4); point
	@@ it at `esc_land` first -- the platform initial value (BootROM base)
	@@ would restart the machine from reset instead of recording the frame.
	LOAD_ABS rb5, esc_land
	rb2rd	rd10, rb5, 1			@@ rb-group address -> rd operand of cfx2rc
	cfx2rc	cfx_power, cg3, rc15, rd10
	LOAD_ABS rb5, land_esc
	st.o	rb5, [rb22, HMON_SLOT_RETURN]
	.globl	f_esc
f_esc:
	escape	cfx_power
	.globl	land_esc
land_esc:
	@@ Reverse assertion (§5.2(一) last row: CFXESC is not a monitor route):
	@@ the monitor handled only the 5 x 3 synchronous faults above, so its
	@@ `excp_sync_num` (§5.2(三) step 3) is 15 and must not have grown.
	cfx2rd	cfx_hmon, cg4, rc3, rd10
	set.zw	rd11, wp0, 15
	set.zw	rd12, wp0, 43
	call	[rb20, rd0, 0]

	@@ ---- cfxtrap mask denial => CFXPERM (34) ----------------------------
	@@ DADAO-12 §5.2(一): a `trap` whose target cfx denies the source cfx in
	@@ its `<mode>_cfxtrap` mask raises CFXPERM into the current run mode
	@@ monitor (Tiny: cfx3 hmon, Kaiwu §2).  The source is the current cfx
	@@ (63); the mask bit index is the source cfxha (§3.4 rc0), so deny bit
	@@ 63 in hmon's hypv row.  A self-trap (`trap cfx_power` from cfx63)
	@@ cannot produce CFXPERM: the cfx axis bypasses the source's own bit.
	cfx2rd	cfx_hmon, cg3, rc0, rd20
	set.rd	rd10, 0x8000000000000000
	cfx2rc	cfx_hmon, cg3, rc0, rd10
	LOAD_ABS rb5, land_perm
	st.o	rb5, [rb22, HMON_SLOT_RETURN]
	.globl	f_perm
f_perm:
	trap	cfx_hmon, 0
	.globl	land_perm
land_perm:
	call	[rb21, rd0, 0]
	cfx2rc	cfx_hmon, cg3, rc0, rd20

	@@ ---- unimplemented cfx register => CFXREG (35) ----------------------
	LOAD_ABS rb5, land_reg
	st.o	rb5, [rb22, HMON_SLOT_RETURN]
	.globl	f_reg
f_reg:
	cfx2rd	cfx5, cg0, rc0, rd10
	.globl	land_reg
land_reg:
	call	[rb21, rd0, 0]

	@@ ---- Tiny stays in hypv under a guest-written switch mode (36..40) --
	@@ Kaiwu §2: Tiny has no mode-switch path; a guest write of
	@@ switch_run_mode = user(0) must not move the run mode on fault entry.
	cfx2rd	cfx_hmon, cg3, rc14, rd10	@@ switch_run_mode (cg3 is hypv-only)
	set.zw	rd11, wp0, 3
	set.zw	rd12, wp0, 36
	call	[rb20, rd0, 0]

	set.zw	rd13, wp0, 0			@@ guest asks for user mode
	cfx2rc	cfx_hmon, cg3, rc14, rd13

	@@ Kaiwu §2: the write is ignored -- the saved value stays 3 and a
	@@ read returns the saved value.  Check it before the fault so the two
	@@ checks (immediate read-back / read-back after the fault) are distinct.
	cfx2rd	cfx_hmon, cg3, rc14, rd10
	set.zw	rd11, wp0, 3
	set.zw	rd12, wp0, 42
	call	[rb20, rd0, 0]

	@@ No handler probe: the shared minimal handler has no test hook.  The
	@@ mode invariance is observed after the fault (checks 38-40); the old
	@@ in-handler cg3 read belonged to the dispatch fixture and is gone.
	LOAD_ABS rb5, land_hypv
	st.o	rb5, [rb22, HMON_SLOT_RETURN]
	set.rb rb3, HMON_BASE + 0x10000	@@ unmapped => CFXMEM
	.globl	f_hypv
f_hypv:
	ld.o	rd10, [rb3, 0]
	.globl	land_hypv
land_hypv:
	call	[rb21, rd0, 0]

	cfx2rd	cfx_hmon, cg5, rc0, rd10	@@ excp_prev_run_mode
	set.zw	rd11, wp0, 3
	set.zw	rd12, wp0, 38
	call	[rb20, rd0, 0]

	cfx2rd	cfx_hmon, cg3, rc15, rd10	@@ cg3 still readable after the fault
	set.rd rd11, HMON_BASE
	set.zw	rd12, wp0, 39
	call	[rb20, rd0, 0]

	cfx2rd	cfx_hmon, cg3, rc14, rd10	@@ still the saved value (3) after the fault
	set.zw	rd11, wp0, 3
	set.zw	rd12, wp0, 40
	call	[rb20, rd0, 0]

	@@ ---- hmon saves and restores the scratch originals (44..47) ---------
	@@ The handler uses rb63 as its data-page base and rd63 as scratch, so it
	@@ saves their originals in the data page +0x20/+0x28 and restores both
	@@ before `escape`.  Put sentinels in both, take one CFXMEM, then read the
	@@ saved slots back and check the registers themselves survived.
	set.rd rd63, 0x5A5A5A5A5A5A5A5A
	set.rb rb63, 0x0BADF00D0BADF00D
	LOAD_ABS rb5, land_scratch
	st.o	rb5, [rb22, HMON_SLOT_RETURN]
	set.rb rb3, HMON_BASE + 0x10000	@@ unmapped => CFXMEM
	.globl	f_scratch
f_scratch:
	ld.o	rd10, [rb3, 0]
	.globl	land_scratch
land_scratch:
	call	[rb21, rd0, 0]		@@ cause record (CFXMEM)

	ld.o	rd10, [rb22, HMON_SLOT_RD63]	@@ saved rd63 original
	set.rd rd11, 0x5A5A5A5A5A5A5A5A
	set.zw	rd12, wp0, 44
	call	[rb20, rd0, 0]

	ld.o	rd10, [rb22, HMON_SLOT_RB63]	@@ saved rb63 original
	set.rd rd11, 0x0BADF00D0BADF00D
	set.zw	rd12, wp0, 45
	call	[rb20, rd0, 0]

	or.o	rd10, rd63, rd0		@@ rd63 restored by the handler
	set.rd rd11, 0x5A5A5A5A5A5A5A5A
	set.zw	rd12, wp0, 46
	call	[rb20, rd0, 0]

	rb2rd	rd10, rb63, 1			@@ rb63 restored by the handler
	set.rd rd11, 0x0BADF00D0BADF00D
	set.zw	rd12, wp0, 47
	call	[rb20, rd0, 0]

	@@ ---- export the result table and stop ------------------------------
	set.rb rb16, MSG
	set.zw	rd16, wp0, 0x0004		@@ SYS_WRITE0
	trap	cfx_power, 0x3FF00

	set.rb rb4, PARAM
	set.rb rb5, FNAME
	st.o	rb5, [rb4, 0]
	set.zw	rd6, wp0, 5			@@ "wb"
	st.o	rd6, [rb4, 8]
	set.zw	rd6, wp0, 17
	st.o	rd6, [rb4, 16]
	set.zw	rd16, wp0, 0x0001		@@ SYS_OPEN
	set.rb rb16, PARAM
	trap	cfx_hmon, 0x3FF00

	set.rb rb4, PARAM
	st.o	rd8, [rb4, 0]			@@ handle
	set.rd rd6, RESULTS
	st.o	rd6, [rb4, 8]
	set.zw	rd6, wp0, 0x1000
	st.o	rd6, [rb4, 16]
	set.zw	rd16, wp0, 0x0005		@@ SYS_WRITE
	set.rb rb16, PARAM
	trap	cfx_hmon, 0x3FF00

	set.rb rb4, PARAM
	set.zw	rd6, wp1, 0x0002
	or.w	rd6, wp0, 0x0026		@@ ADP_Stopped_ApplicationExit
	st.o	rd6, [rb4, 0]
	set.rb rb5, FAILCNT
	ld.o	rd7, [rb5, 0]
	set.zw	rd8, wp0, 0x0021
	set.zw	rd9, wp0, 0x0071
	cmp.so	rd10, rd7, rd0
	br.z	{rd10}?, [rb0, exit_pass]
	st.o	rd9, [rb4, 8]
	jump	[rb0, exit_go]
exit_pass:
	st.o	rd8, [rb4, 8]
exit_go:
	set.zw	rd16, wp0, 0x0018		@@ SYS_EXIT
	set.rb rb16, PARAM
	trap	cfx_hmon, 0x3FF00
	swym	0

@@ ---------------------------------------------------------------------------
@@ record_check: rd10 = actual, rd11 = expected, rd12 = check id.
@@ Records {id, actual, expected, 0} and bumps failcnt on a mismatch.
@@ ---------------------------------------------------------------------------
	.section .rcheck, "ax"
record_check:
	set.rb rb4, SLOT_PTR
	ld.o	rb5, [rb4, 0]
	st.o	rd12, [rb5, 0]
	st.o	rd10, [rb5, 8]
	st.o	rd11, [rb5, 16]
	set.zw	rd14, wp0, 0
	st.o	rd14, [rb5, 24]
	add.si	rb5, 32
	st.o	rb5, [rb4, 0]

	cmp.so	rd13, rd10, rd11
	br.z	{rd13}?, [rb0, rc_ok]
	set.rb rb4, FAILCNT
	ld.o	rd14, [rb4, 0]
	add.si	rd14, 1
	st.o	rd14, [rb4, 0]
rc_ok:
	ret	rd0, 0

@@ ---------------------------------------------------------------------------
@@ record_cause: append one cause record {cause_id, cause_ip, cause_info,
@@ return_slot} read from the hmon SRAM data slots.  The shared minimal handler
@@ saved the three cause slots before it overwrote excp_cause_ip, and the
@@ return slot holds the framework return address; the application only
@@ observes, it never decides.
@@ rb22 = HMON_BASE + HMON_DATA is set once in _start.
@@ ---------------------------------------------------------------------------
record_cause:
	set.rb rb4, SLOT_PTR
	ld.o	rb5, [rb4, 0]
	ld.o	rd10, [rb22, HMON_SLOT_CAUSE_ID]	@@ excp_cause_id
	ld.o	rd11, [rb22, HMON_SLOT_CAUSE_IP]	@@ excp_cause_ip (fault IP)
	ld.o	rd12, [rb22, HMON_SLOT_CAUSE_INFO]	@@ excp_cause_info
	ld.o	rd13, [rb22, HMON_SLOT_RETURN]		@@ framework return address
	st.o	rd10, [rb5, 0]
	st.o	rd11, [rb5, 8]
	st.o	rd12, [rb5, 16]
	st.o	rd13, [rb5, 24]
	add.si	rb5, 32
	st.o	rb5, [rb4, 0]
	ret	rd0, 0

@@ ---------------------------------------------------------------------------
@@ record_esc_frame: append one cause record read from the *current* cfx's own
@@ cg5 frame (DADAO-12 §3.6): {cause_id, cause_ip, cause_info, prev_cfx_code}.
@@ Used at `esc_land`, where a CFXESC frame is delivered to cfx63 (§5.2(一)).
@@ The monitor's SRAM slots are read separately: they must still hold the
@@ previous monitor entry.
@@ ---------------------------------------------------------------------------
record_esc_frame:
	set.rb rb4, SLOT_PTR
	ld.o	rb5, [rb4, 0]
	cfx2rd	cfx_power, cg5, rc4, rd10	@@ excp_cause_id (CFXESC = 1<<3)
	cfx2rd	cfx_power, cg5, rc2, rd11	@@ excp_cause_ip (f_esc)
	cfx2rd	cfx_power, cg5, rc5, rd12	@@ excp_cause_info (escape encoding)
	cfx2rd	cfx_power, cg5, rc1, rd13	@@ excp_prev_cfx_code (63)
	st.o	rd10, [rb5, 0]
	st.o	rd11, [rb5, 8]
	st.o	rd12, [rb5, 16]
	st.o	rd13, [rb5, 24]
	add.si	rb5, 32
	st.o	rb5, [rb4, 0]
	ret	rd0, 0

@@ ---------------------------------------------------------------------------
@@ esc_land: cfx63's hypv exception vector (cg3 rc15), installed by the body
@@ before `f_esc`.  A CFXESC frame enters the current cfx (§5.2(一)), so the
@@ frame is observed here -- not in the monitor.  `escape` now takes only
@@ cfxHA and returns through `cg5 rc10`; the entry copied `excp_cause_ip`
@@ (f_esc) into rc10, so write rc10 = excp_cause_ip + 4 to resume at
@@ `land_esc` (§5.1 "跳过触发指令").
@@ ---------------------------------------------------------------------------
	.globl	esc_land
esc_land:
	LOAD_ABS rb5, record_esc_frame
	call	[rb5, rd0, 0]
	@@ Reverse assertion: the monitor's data slots still hold the previous
	@@ monitor entry (the CFXESC entry did not run the hmon handler).
	call	[rb21, rd0, 0]
	cfx2rd	cfx_power, cg5, rc2, rd10	@@ excp_cause_ip (f_esc)
	add.si	rd10, 4
	cfx2rc	cfx_power, cg5, rc10, rd10	@@ exit ip <- f_esc + 4
	escape	cfx_power

@@ ---------------------------------------------------------------------------
@@ Fixed data area (DATA_BASE = ENTRY + 0x3100, see tiny_hmon.lds).
@@ +0x00 slot_ptr / +0x10 failcnt
@@ +0x40 SYS_OPEN|SYS_WRITE|SYS_EXIT parameter block
@@ +0x80 file name / +0xC0 console message
@@ ---------------------------------------------------------------------------
	.data
	.p2align 3
	.space	0x40
	.space	0x40
fname:
	.asciz	"hmon_results.bin"
	.p2align 3
	.space	0x28
msg:
	.asciz	"hmon-ok\n"

@@ ---------------------------------------------------------------------------
@@ Result table (zero-filled; the runner reads until the first zero record).
@@ ---------------------------------------------------------------------------
	.section .results, "aw", @nobits
	.p2align 3
	.globl	results
results:
	.space	0x1000
	.globl	results_end
results_end:
