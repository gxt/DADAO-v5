@@ app.S — m12-chipyard-019 RTL case: cfx register groups + the five synchronous
@@ fault classes entering the cfx_hmon vector (spec/Machine-v5 §2/§3/§4.4,
@@ spec/DADAO-13 §1–§2, spec/DADAO-12 §5.2/§5.3).
@@
@@ Runs on the chipyard WumingTinyConfig harness: the fixed 64 KiB BootROM
@@ firmware (power stub + dispatching hmon handler) hands over to this ELF at the
@@ fixed entry 0xffff_ff01_0100.  The program is one object with `_start` at the
@@ entry (no crt: it uses no stack) and prints nothing itself — every assertion is
@@ either a self-check (failure => SYS_EXIT with 0x40 + check id) or a
@@ `WumingCore: cfx2/excp/escape` log line that the evidence script compares with
@@ the ELF symbols and the spec.
@@
@@ hmon clobbers rd6–rd14, so this program keeps all live state in rd15–rd31 /
@@ rb1–rb31.
@@
@@ Fault cases: 3 × CFXMEM / ILLI / UNDI / MALIGN / IALIGN, one CFXREG for each
@@ unimplemented cg8 rc1, and the cg3-only-in-hypv pair (case + counter-example).

	.include "tests/shared/asm/machine-tiny.inc"
	.include "tests/shared/asm/machine.inc"
	.include "tests/shared/bootrom/tiny/tiny_common.inc"

	.equ	PARAM,      ENTRY + 0x6000	@@ SYS_EXIT parameter block
	.equ	SITE0,      ENTRY + 0x4000	@@ IALIGN jump sites
	.equ	SITE1,      ENTRY + 0x4100
	.equ	SITE2,      ENTRY + 0x4200
	.equ	TGT0,       ENTRY + 0x5000	@@ IALIGN illegal addresses
	.equ	TGT1,       ENTRY + 0x5100
	.equ	TGT2,       ENTRY + 0x5200
	.equ	LAND,       ENTRY + 0x4300	@@ cg3-permission landing block
	.equ	FORGE,      ENTRY + 0x4400	@@ forged frame

	.text
	.globl	_start
_start:
	@@ ---- cfx_hmon cg3 rc10: reset value = the hmon SRAM base -----------
	set.zw	rd31, wp0, 0x0001
	cfx2rd	cfx_hmon, cg3, rc10, rd20
	LOAD_ADDR rd21, HMON_BASE
	cmp.uo	rd30, rd20, rd21
	br.nz	{rd30}?, [rb0, fail]

	@@ ---- cg3 rc10 write drops the low two bits (+3 => base) -------------
	set.zw	rd31, wp0, 0x0002
	LOAD_ADDR rd21, HMON_BASE
	add.si	rd21, 3
	cfx2rc	cfx_hmon, cg3, rc10, rd21
	cfx2rd	cfx_hmon, cg3, rc10, rd20
	LOAD_ADDR rd21, HMON_BASE
	cmp.uo	rd30, rd20, rd21
	br.nz	{rd30}?, [rb0, fail]

	@@ ---- cg3 rc8 switch_run_mode: 3, a write of 0 is ignored -----------
	set.zw	rd31, wp0, 0x0003
	cfx2rd	cfx_hmon, cg3, rc8, rd20
	set.zw	rd21, wp0, 0x0003
	cmp.uo	rd30, rd20, rd21
	br.nz	{rd30}?, [rb0, fail]

	set.zw	rd31, wp0, 0x0004
	cfx2rc	cfx_hmon, cg3, rc8, rd0		@@ guest asks for user mode
	cfx2rd	cfx_hmon, cg3, rc8, rd20
	set.zw	rd21, wp0, 0x0003
	cmp.uo	rd30, rd20, rd21
	br.nz	{rd30}?, [rb0, fail]

	@@ ---- cg3 rc0/rc4 reset values --------------------------------------
	set.zw	rd31, wp0, 0x0005
	cfx2rd	cfx_hmon, cg3, rc0, rd20
	LOAD_ADDR rd21, 0x7ffffffffffffff7
	cmp.uo	rd30, rd20, rd21
	br.nz	{rd30}?, [rb0, fail]

	set.zw	rd31, wp0, 0x0006
	cfx2rd	cfx_hmon, cg3, rc4, rd20
	LOAD_ADDR rd21, 0xffffffffffffffff
	cmp.uo	rd30, rd20, rd21
	br.nz	{rd30}?, [rb0, fail]

	@@ ---- cg3 rc1 is RW (0xF0F round trip; masks do not gate synchronous
	@@ exceptions, DADAO-12 §5.2(二), so the stored value is inert here) --
	set.zw	rd31, wp0, 0x0007
	LOAD_ADDR rd21, 0x0f0f
	cfx2rc	cfx_hmon, cg3, rc1, rd21
	cfx2rd	cfx_hmon, cg3, rc1, rd20
	LOAD_ADDR rd21, 0x0f0f
	cmp.uo	rd30, rd20, rd21
	br.nz	{rd30}?, [rb0, fail]

	@@ ---- cg7 block 0 of cfx_hmon: exists|SRAM, start, size, R|W|X ------
	set.zw	rd31, wp0, 0x0008
	cfx2rd	cfx_hmon, cg7, rc0, rd20
	set.zw	rd21, wp0, 0x0003
	cmp.uo	rd30, rd20, rd21
	br.nz	{rd30}?, [rb0, fail]

	set.zw	rd31, wp0, 0x0009
	cfx2rd	cfx_hmon, cg7, rc1, rd20
	LOAD_ADDR rd21, 0x3ff00000000
	cmp.uo	rd30, rd20, rd21
	br.nz	{rd30}?, [rb0, fail]

	set.zw	rd31, wp0, 0x000a
	cfx2rd	cfx_hmon, cg7, rc2, rd20
	LOAD_ADDR rd21, 0x10000
	cmp.uo	rd30, rd20, rd21
	br.nz	{rd30}?, [rb0, fail]

	set.zw	rd31, wp0, 0x000b
	cfx2rd	cfx_hmon, cg7, rc3, rd20
	set.zw	rd21, wp0, 0x0007
	cmp.uo	rd30, rd20, rd21
	br.nz	{rd30}?, [rb0, fail]

	@@ ---- cg7 block 1 (rc4): not present => 0 ---------------------------
	set.zw	rd31, wp0, 0x000c
	cfx2rd	cfx_hmon, cg7, rc4, rd20
	set.zw	rd21, wp0, 0x0000
	cmp.uo	rd30, rd20, rd21
	br.nz	{rd30}?, [rb0, fail]

	@@ ---- cg7 block 0 of cfx_power: exists|ROM, BootROM, R|X ------------
	set.zw	rd31, wp0, 0x000d
	cfx2rd	cfx_power, cg7, rc0, rd20
	set.zw	rd21, wp0, 0x0005
	cmp.uo	rd30, rd20, rd21
	br.nz	{rd30}?, [rb0, fail]

	set.zw	rd31, wp0, 0x000e
	cfx2rd	cfx_power, cg7, rc1, rd20
	LOAD_ADDR rd21, 0x3ffffff0000
	cmp.uo	rd30, rd20, rd21
	br.nz	{rd30}?, [rb0, fail]

	set.zw	rd31, wp0, 0x000f
	cfx2rd	cfx_power, cg7, rc2, rd20
	LOAD_ADDR rd21, 0x10000
	cmp.uo	rd30, rd20, rd21
	br.nz	{rd30}?, [rb0, fail]

	set.zw	rd31, wp0, 0x0010
	cfx2rd	cfx_power, cg7, rc3, rd20
	set.zw	rd21, wp0, 0x0005
	cmp.uo	rd30, rd20, rd21
	br.nz	{rd30}?, [rb0, fail]

	@@ ---- cfx_power cg3 rc10 = the BootROM base; cg3 rc0 reset value ----
	set.zw	rd31, wp0, 0x0011
	cfx2rd	cfx_power, cg3, rc10, rd20
	LOAD_ADDR rd21, BOOTROM_BASE
	cmp.uo	rd30, rd20, rd21
	br.nz	{rd30}?, [rb0, fail]

	set.zw	rd31, wp0, 0x0012
	cfx2rd	cfx_power, cg3, rc0, rd20
	LOAD_ADDR rd21, 0xfffffffffffffff7
	cmp.uo	rd30, rd20, rd21
	br.nz	{rd30}?, [rb0, fail]

	@@ ---- unimplemented cg8 rc1 (cfx_power_ctrl) => CFXREG ------------
	set.zw	rd31, wp0, 0x0013
	set.zw	rd20, wp0, 0xbeef	@@ rejected reads must not write back
	set.zw	rd22, wp0, 0xbeef
	.globl	f_cg8_hmon
f_cg8_hmon:
	cfx2rd	cfx_hmon, cg8, rc1, rd20
	.globl	f_cg8_power
f_cg8_power:
	cfx2rd	cfx_power, cg8, rc1, rd22
	set.zw	rd21, wp0, 0xbeef
	cmp.uo	rd30, rd20, rd21
	br.nz	{rd30}?, [rb0, fail]
	cmp.uo	rd30, rd22, rd21
	br.nz	{rd30}?, [rb0, fail]

	@@ ---- MALIGN x 3 (8-byte access, unaligned) ------------------------
	set.zw	rd15, wp0, 0xbeef		@@ load destination sentinel
	LOAD_ADDR rb4, RAM_BASE+1
	set.zw	rd31, wp0, 0x0014
	.globl	f_malign0
f_malign0:
	ld.o	rd15, [rb4, 0]			@@ MALIGN: precise, rd15 unchanged
	set.zw	rd21, wp0, 0xbeef
	cmp.uo	rd30, rd15, rd21
	br.nz	{rd30}?, [rb0, fail]

	LOAD_ADDR rb4, RAM_BASE
	ld.o	rd15, [rb4, 0]			@@ reference word (SRAM zero fill)
	LOAD_ADDR rb5, RAM_BASE+4
	set.zw	rd31, wp0, 0x0015
	.globl	f_malign1
f_malign1:
	st.o	rd15, [rb5, 0]			@@ MALIGN: no store is issued
	LOAD_ADDR rb4, RAM_BASE
	ld.o	rd16, [rb4, 0]			@@ still the untouched word
	cmp.uo	rd30, rd16, rd15
	br.nz	{rd30}?, [rb0, fail]

	set.zw	rd17, wp0, 0xbeef
	LOAD_ADDR rb4, RAM_BASE+2
	set.zw	rd31, wp0, 0x0016
	.globl	f_malign2
f_malign2:
	ld.o	rd17, [rb4, 0]			@@ MALIGN: rd17 unchanged
	set.zw	rd21, wp0, 0xbeef
	cmp.uo	rd30, rd17, rd21
	br.nz	{rd30}?, [rb0, fail]

	@@ ---- ILLI x 3 (reserved cfx through trap / cfx2rd / escape) -------
	set.zw	rd31, wp0, 0x0017
	.globl	f_illi0
f_illi0:
	trap	cfx7, 0

	set.zw	rd31, wp0, 0x0018
	.globl	f_illi1
f_illi1:
	cfx2rd	cfx7, cg0, rc0, rd18

	set.zw	rd31, wp0, 0x0019
	.globl	f_illi2
f_illi2:
	escape	cfx7, [excp_cause_ip, 4]

	@@ ---- UNDI x 3 (blank QFC cells) ------------------------------------
	set.zw	rd31, wp0, 0x001a
	.globl	f_undi0
f_undi0:
	.dd.t32	0x08040001

	set.zw	rd31, wp0, 0x001b
	.globl	f_undi1
f_undi1:
	.dd.t32	0x1B040001

	set.zw	rd31, wp0, 0x001c
	.globl	f_undi2
f_undi2:
	.dd.t32	0x58040001

	@@ ---- CFXMEM x 3 (data access to an address no manager backs) ------
	LOAD_ADDR rb4, 0x1000000000
	set.zw	rd31, wp0, 0x001d
	.globl	f_mem0
f_mem0:
	ld.o	rd18, [rb4, 0]

	LOAD_ADDR rb4, 0xffffff800000
	set.zw	rd31, wp0, 0x001e
	.globl	f_mem1
f_mem1:
	ld.o	rd18, [rb4, 0]

	LOAD_ADDR rb4, HMON_BASE + 0x10000
	set.zw	rd31, wp0, 0x001f
	.globl	f_mem2
f_mem2:
	ld.o	rd18, [rb4, 0]

	@@ ---- IALIGN x 3: jump to an address with IP[1:0] != 00 ------------
	set.zw	rd31, wp0, 0x0020
	br.z	{rd0}?, [rb0, ialign_go0]
	.org	SITE0 - ENTRY
	.globl	ialign_go0
ialign_go0:
	LOAD_ADDR rd20, TGT0 - SITE0 - 16 + 1
	jump	[rb0, rd20, 0]
ialign_after0:
	set.zw	rd31, wp0, 0x0021
	LOAD_ADDR rd21, TGT0 - SITE0 - 16 + 1
	cmp.uo	rd30, rd20, rd21
	br.nz	{rd30}?, [rb0, fail]
	set.zw	rd21, wp0, 0x0001
	cmp.uo	rd30, rd23, rd21
	br.nz	{rd30}?, [rb0, fail]

	set.zw	rd31, wp0, 0x0022
	br.z	{rd0}?, [rb0, ialign_go1]
	.org	SITE1 - ENTRY
	.globl	ialign_go1
ialign_go1:
	LOAD_ADDR rd20, TGT1 - SITE1 - 16 + 2
	jump	[rb0, rd20, 0]
ialign_after1:
	set.zw	rd31, wp0, 0x0023
	set.zw	rd21, wp0, 0x0002
	cmp.uo	rd30, rd24, rd21
	br.nz	{rd30}?, [rb0, fail]

	set.zw	rd31, wp0, 0x0024
	br.z	{rd0}?, [rb0, ialign_go2]
	.org	SITE2 - ENTRY
	.globl	ialign_go2
ialign_go2:
	LOAD_ADDR rd20, TGT2 - SITE2 - 16 + 3
	jump	[rb0, rd20, 0]
ialign_after2:
	set.zw	rd31, wp0, 0x0025
	set.zw	rd21, wp0, 0x0003
	cmp.uo	rd30, rd25, rd21
	br.nz	{rd30}?, [rb0, fail]

	@@ ---- cg3 in a non-hypv run mode => CFXREG (case + counter-example) -
	@@ A guest can forge a frame (cg5 rc3/rc0 are RW, DADAO-12 §3.6) and
	@@ `escape` into a lower run mode; the hardware must then reject cg3.
	@@ The forged block sits at a fixed offset (FORGE), its target at LAND.
	set.zw	rd31, wp0, 0x0026
	br.z	{rd0}?, [rb0, forge_site]
	.globl	forge_after
forge_after:

	@@ ---- pass ---------------------------------------------------------
	LOAD_ADDR rb16, PARAM
	LOAD_ADDR rd20, 0x20026		@@ ADP_Stopped_ApplicationExit
	set.zw	rd21, wp0, 0x0000		@@ status 0 = pass
	st.o	rd20, [rb16, 0]
	st.o	rd21, [rb16, 8]
	set.zw	rd16, wp0, 0x0018		@@ SYS_EXIT
	trap	cfx_hmon, 0x3FF18
pass_spin:
	br.z	{rd0}?, [rb0, pass_spin]

	@@ ---- failure: SYS_EXIT(0x40 + check id) ---------------------------
fail:
	LOAD_ADDR rb16, PARAM
	LOAD_ADDR rd20, 0x20026
	add.si	rd31, 0x40
	st.o	rd20, [rb16, 0]
	st.o	rd31, [rb16, 8]
	set.zw	rd16, wp0, 0x0018
	trap	cfx_hmon, 0x3FF18
fail_spin:
	br.z	{rd0}?, [rb0, fail_spin]

	@@ ---- cg3 permission case: forged frame + lower run mode ------------
	.org	LAND - ENTRY
	.globl	land_supv
	.globl	land_supv
land_supv:
	set.zw	rd31, wp0, 0x0026
	.globl	f_cg3_supv
f_cg3_supv:
	cfx2rd	cfx_hmon, cg3, rc10, rd26	@@ CFXREG (cg3 needs hypv)
	.globl	land_after
	.globl	land_after
land_after:
	set.zw	rd31, wp0, 0x0027
	cfx2rd	cfx_hmon, cg3, rc10, rd26	@@ hypv again: succeeds
	LOAD_ADDR rd27, HMON_BASE
	cmp.uo	rd30, rd26, rd27
	br.nz	{rd30}?, [rb0, fail]
	br.z	{rd0}?, [rb0, forge_after]

	@@ ---- forged exception frame (excp_cause_ip / excp_prev_run_mode) ---
	.org	FORGE - ENTRY
	.globl	forge_site
	.globl	forge_site
forge_site:
	LOAD_ADDR rb21, (FORGE + 16) - (LAND - 4)
	sub.o	rd20, rb0, rb21		@@ rb0 = this instruction's IP
	cfx2rc	cfx_hmon, cg5, rc3, rd20	@@ excp_cause_ip = LAND - 4
	set.zw	rd20, wp0, 0x0002
	cfx2rc	cfx_hmon, cg5, rc0, rd20	@@ excp_prev_run_mode = supv
	escape	cfx_hmon, [excp_cause_ip, 4]	@@ => IP = LAND, run mode supv

	@@ ---- IALIGN landing blocks: [4-aligned filler][recovery] -----------
	.org	TGT0 - ENTRY
	.globl	ialign_tgt0
ialign_tgt0:
	set.zw	rd22, wp0, 0x1111	@@ filler at the 4-aligned address
	set.zw	rd23, wp0, 0x0001	@@ recovery point (aligned+4)
	br.z	{rd0}?, [rb0, ialign_after0]

	.org	TGT1 - ENTRY
	.globl	ialign_tgt1
ialign_tgt1:
	set.zw	rd22, wp0, 0x2222
	set.zw	rd24, wp0, 0x0002
	br.z	{rd0}?, [rb0, ialign_after1]

	.org	TGT2 - ENTRY
	.globl	ialign_tgt2
ialign_tgt2:
	set.zw	rd22, wp0, 0x3333
	set.zw	rd25, wp0, 0x0003
	br.z	{rd0}?, [rb0, ialign_after2]

	@@ ---- SYS_EXIT parameter block -------------------------------------
	.org	PARAM - ENTRY
	.space	16

	.section .note.GNU-stack, "", @progbits
