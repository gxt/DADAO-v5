@@ tiny_hmon.S — Machine-v5-Tiny cfx_power + cfx3 hmon execution case (m13-gem5-001).
@@
@@ Structure (spec/Machine-v5 §1.1/§2/§3/§4.4/§5; DADAO-12 §5):
@@
@@   BootROM (0xffff_ffff_0000, power/cfx63)
@@     * writes cfx_hmon_hypv_excp_vector = HMON_BASE with cfx2rc
@@     * initialises the result slot pointer in SRAM
@@     * `trap cfx_hmon, 0` (general trap -> CFXTRAP into the hmon vector)
@@
@@   hmon SRAM (0x0fff_0000_0000, cfx3)
@@     * synchronous-fault handler: records excp_cause_id / excp_cause_ip /
@@       excp_cause_info / handler PC into a 32-byte result record, then
@@       `escape cfx_hmon, [excp_cause_ip, 4]` (or rewrites excp_cause_ip for
@@       IALIGN and escapes with 0)
@@
@@   Application (SRAM 0xffff_ff01_0100, running with cfx3 current)
@@     * cfx2rd/cfx2rc register checks (power/hmon id, vector, switch mode,
@@       prev mode, counters, scratch, intr mask, cg7 space descriptors)
@@     * five synchronous fault classes x 3 cases (CFXMEM/ILLI/UNDI/MALIGN/
@@       IALIGN), plus CFXTRAP/CFXESC/CFXPERM/CFXREG
@@     * exports the result table through SYS_OPEN + SYS_WRITE and stops with
@@       SYS_EXIT (0x21 pass, 0x71 fail)
@@
@@ The expected values live in `expected.yaml`; this program never decides the
@@ oracle by itself (it only records the architectural values).

	.include "machine.inc"
	.include "machine-tiny.inc"

	.equ	DATA_BASE, ENTRY + 0x3100
	.equ	SLOT_PTR,  DATA_BASE + 0x00
	.equ	RECOVERY,  DATA_BASE + 0x08
	.equ	FAILCNT,   DATA_BASE + 0x10
	.equ	HANDLE,    DATA_BASE + 0x18
	.equ	PARAM,     DATA_BASE + 0x40
	.equ	FNAME,     DATA_BASE + 0x80
	.equ	MSG,       DATA_BASE + 0xC0
	.equ	RESULTS,   ENTRY + 0x4000
	.equ	RECORD_CHECK, ENTRY + 0x2000

	.equ	IALIGN_TARGET0, ENTRY + 0x1C01
	.equ	IALIGN_TARGET1, ENTRY + 0x1C02
	.equ	IALIGN_TARGET2, ENTRY + 0x1C03

	.globl	IALIGN_TARGET0
	.globl	IALIGN_TARGET1
	.globl	IALIGN_TARGET2

@@ ---------------------------------------------------------------------------
@@ BootROM: power (cfx63) installs the hmon vector and hands over.
@@ ---------------------------------------------------------------------------
	.section .bootrom, "ax"
	.globl	_start
_start:
	LOAD_ADDR rd22, HMON_BASE
	cfx2rc	cfx_hmon, cg3, rc10, rd22

	LOAD_ADDR rd22, RESULTS
	LOAD_ADDR rb3, SLOT_PTR
	st.o	rd22, [rb3, 0]

	.globl	hmon_handover
hmon_handover:
	trap	cfx_hmon, 0

	LOAD_ADDR rb2, ENTRY
	jump	[rb2, rd0, 0]
	swym	0

@@ ---------------------------------------------------------------------------
@@ hmon vector: record the frame, then escape (IALIGN rewrites cause_ip).
@@ ---------------------------------------------------------------------------
	.section .hmon, "ax"
	.globl	hmon_entry
hmon_entry:
	rb2rd	rd4, rb0, 1			@@ handler PC (must equal HMON_BASE)
	cfx2rd	cfx_hmon, cg5, rc2, rd10	@@ excp_cause_id
	cfx2rd	cfx_hmon, cg5, rc3, rd11	@@ excp_cause_ip
	cfx2rd	cfx_hmon, cg5, rc4, rd12	@@ excp_cause_info

	LOAD_ADDR rb4, SLOT_PTR
	ld.o	rb5, [rb4, 0]
	st.o	rd10, [rb5, 0]
	st.o	rd11, [rb5, 8]
	st.o	rd12, [rb5, 16]
	st.o	rd4,  [rb5, 24]
	add.si	rb5, 32
	st.o	rb5, [rb4, 0]

	@@ IALIGN (1 << 13): the illegal IP is recorded; resume at RECOVERY.
	set.zw	rd13, wp0, 0x2000
	cmp.so	rd14, rd10, rd13
	br.nz	{rd14}?, [rb0, hmon_escape4]

	LOAD_ADDR rb7, RECOVERY
	ld.o	rd15, [rb7, 0]
	cfx2rc	cfx_hmon, cg5, rc3, rd15
	escape	cfx_hmon, [excp_cause_ip, 0]

hmon_escape4:
	escape	cfx_hmon, [excp_cause_ip, 4]

@@ ---------------------------------------------------------------------------
@@ Application.
@@ ---------------------------------------------------------------------------
	.text
	.globl	main
main:
	LOAD_ADDR rb20, RECORD_CHECK

	@@ ---- register checks (ids 1..16) -------------------------------------
	cfx2rd	cfx_hmon, cg4, rc0, rd10
	set.zw	rd11, wp0, 3
	set.zw	rd12, wp0, 1
	call	[rb20, rd0, 0]

	cfx2rd	cfx_power, cg4, rc0, rd10
	set.zw	rd11, wp0, 63
	set.zw	rd12, wp0, 2
	call	[rb20, rd0, 0]

	cfx2rd	cfx_hmon, cg3, rc10, rd10
	LOAD_ADDR rd11, HMON_BASE
	set.zw	rd12, wp0, 3
	call	[rb20, rd0, 0]

	cfx2rd	cfx_hmon, cg3, rc8, rd10
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

	LOAD_ADDR rd11, 0x1122334455667788
	cfx2rc	cfx_hmon, cg6, rc0, rd11
	cfx2rd	cfx_hmon, cg6, rc0, rd10
	set.zw	rd12, wp0, 7
	call	[rb20, rd0, 0]

	LOAD_ADDR rd11, 0x0000000000000F0F
	cfx2rc	cfx_hmon, cg3, rc4, rd11
	cfx2rd	cfx_hmon, cg3, rc4, rd10
	set.zw	rd12, wp0, 8
	call	[rb20, rd0, 0]

	cfx2rd	cfx_hmon, cg7, rc0, rd10
	set.zw	rd11, wp0, 3
	set.zw	rd12, wp0, 9
	call	[rb20, rd0, 0]

	cfx2rd	cfx_hmon, cg7, rc1, rd10
	LOAD_ADDR rd11, 0x3FF00000000
	set.zw	rd12, wp0, 10
	call	[rb20, rd0, 0]

	cfx2rd	cfx_hmon, cg7, rc2, rd10
	LOAD_ADDR rd11, 0x10000
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
	LOAD_ADDR rd11, 0x3FFFFFF0000
	set.zw	rd12, wp0, 14
	call	[rb20, rd0, 0]

	cfx2rd	cfx_power, cg7, rc2, rd10
	LOAD_ADDR rd11, 0x10000
	set.zw	rd12, wp0, 15
	call	[rb20, rd0, 0]

	cfx2rd	cfx_power, cg7, rc3, rd10
	set.zw	rd11, wp0, 5
	set.zw	rd12, wp0, 16
	call	[rb20, rd0, 0]

	@@ ---- CFXMEM x 3 (17..19) --------------------------------------------
	LOAD_ADDR rb3, 0x1000000000
	.globl	f_mem0
f_mem0:
	ld.o	rd10, [rb3, 0]

	LOAD_ADDR rb3, 0xFFFFFF800000
	.globl	f_mem1
f_mem1:
	ld.o	rd10, [rb3, 0]

	LOAD_ADDR rb3, HMON_BASE + 0x10000
	.globl	f_mem2
f_mem2:
	ld.o	rd10, [rb3, 0]

	@@ ---- ILLI x 3 (20..22) ----------------------------------------------
	.globl	f_illi0
f_illi0:
	trap	cfx7, 0

	.globl	f_illi1
f_illi1:
	cfx2rd	cfx7, cg0, rc0, rd10

	.globl	f_illi2
f_illi2:
	escape	cfx7, [excp_cause_ip, 4]

	@@ ---- UNDI x 3 (23..25) ----------------------------------------------
	.globl	f_undi0
f_undi0:
	.dd.t32	0x08040001

	.globl	f_undi1
f_undi1:
	.dd.t32	0x1B040001

	.globl	f_undi2
f_undi2:
	.dd.t32	0x58040001

	@@ ---- MALIGN x 3 (26..28) --------------------------------------------
	LOAD_ADDR rb3, RAM_BASE + 1
	.globl	f_malign0
f_malign0:
	ld.o	rd10, [rb3, 0]

	LOAD_ADDR rb3, RAM_BASE + 4
	.globl	f_malign1
f_malign1:
	st.o	rd10, [rb3, 0]

	LOAD_ADDR rb3, RAM_BASE + 2
	.globl	f_malign2
f_malign2:
	ld.ut	rd10, [rb3, 0]

	@@ ---- IALIGN x 3 (29..31) --------------------------------------------
	LOAD_ADDR rb3, RECOVERY
ialign_pre0:
	rb2rd	rd2, rb0, 1			@@ rd2 = address of ialign_pre0
	add.si	rd2, 32				@@ -> ialign_rec0
	st.o	rd2, [rb3, 0]
	LOAD_ADDR rb2, IALIGN_TARGET0
	jump	[rb2, rd0, 0]
ialign_rec0:

	LOAD_ADDR rb3, RECOVERY
ialign_pre1:
	rb2rd	rd2, rb0, 1
	add.si	rd2, 32				@@ -> ialign_rec1
	st.o	rd2, [rb3, 0]
	LOAD_ADDR rb2, IALIGN_TARGET1
	jump	[rb2, rd0, 0]
ialign_rec1:

	LOAD_ADDR rb3, RECOVERY
ialign_pre2:
	rb2rd	rd2, rb0, 1
	add.si	rd2, 32				@@ -> ialign_rec2
	st.o	rd2, [rb3, 0]
	LOAD_ADDR rb2, IALIGN_TARGET2
	jump	[rb2, rd0, 0]
ialign_rec2:

	@@ ---- general trap into hmon (32) ------------------------------------
	.globl	f_trap
f_trap:
	trap	cfx_hmon, 0x0123

	@@ ---- escape target error => CFXESC (33) ------------------------------
	.globl	f_esc
f_esc:
	escape	cfx_power, [excp_cause_ip, 4]

	@@ ---- cfxtrap mask denial => CFXPERM (34) ----------------------------
	cfx2rd	cfx_power, cg3, rc0, rd20
	set.zw	rd10, wp0, 8
	cfx2rc	cfx_power, cg3, rc0, rd10
	.globl	f_perm
f_perm:
	trap	cfx_power, 0
	cfx2rc	cfx_power, cg3, rc0, rd20

	@@ ---- unimplemented cfx register => CFXREG (35) ----------------------
	.globl	f_reg
f_reg:
	cfx2rd	cfx5, cg0, rc0, rd10

	@@ ---- export the result table and stop ------------------------------
	LOAD_ADDR rb16, MSG
	set.zw	rd16, wp0, 0x0004		@@ SYS_WRITE0
	trap	cfx_power, 0x3FF00

	LOAD_ADDR rb4, PARAM
	LOAD_ADDR rb5, FNAME
	st.o	rb5, [rb4, 0]
	set.zw	rd6, wp0, 5			@@ "wb"
	st.o	rd6, [rb4, 8]
	set.zw	rd6, wp0, 17
	st.o	rd6, [rb4, 16]
	set.zw	rd16, wp0, 0x0001		@@ SYS_OPEN
	LOAD_ADDR rb16, PARAM
	trap	cfx_hmon, 0x3FF00

	LOAD_ADDR rb4, PARAM
	st.o	rd8, [rb4, 0]			@@ handle
	LOAD_ADDR rd6, RESULTS
	st.o	rd6, [rb4, 8]
	set.zw	rd6, wp0, 0x1000
	st.o	rd6, [rb4, 16]
	set.zw	rd16, wp0, 0x0005		@@ SYS_WRITE
	LOAD_ADDR rb16, PARAM
	trap	cfx_hmon, 0x3FF00

	LOAD_ADDR rb4, PARAM
	set.zw	rd6, wp1, 0x0002
	or.w	rd6, wp0, 0x0026		@@ ADP_Stopped_ApplicationExit
	st.o	rd6, [rb4, 0]
	LOAD_ADDR rb5, FAILCNT
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
	LOAD_ADDR rb16, PARAM
	trap	cfx_hmon, 0x3FF00
	swym	0

@@ ---------------------------------------------------------------------------
@@ record_check: rd10 = actual, rd11 = expected, rd12 = check id.
@@ Records {id, actual, expected, 0} and bumps failcnt on a mismatch.
@@ ---------------------------------------------------------------------------
	.section .rcheck, "ax"
record_check:
	LOAD_ADDR rb4, SLOT_PTR
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
	LOAD_ADDR rb4, FAILCNT
	ld.o	rd14, [rb4, 0]
	add.si	rd14, 1
	st.o	rd14, [rb4, 0]
rc_ok:
	ret	rd0, 0

@@ ---------------------------------------------------------------------------
@@ Fixed data area (DATA_BASE = ENTRY + 0x3100, see tiny_hmon.lds).
@@ +0x00 slot_ptr / +0x08 recovery / +0x10 failcnt / +0x18 handle
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
