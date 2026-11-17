@@ semihost_pa_probe.S — K1 gate probe: semihosting pointers are PAs (ISS-450)
@@
@@ Runs on `-M kaiwu-vast` under the K1 firmware (`tests/shared/bootrom/k0/`, the
@@ same power -> hmon -> smon chain `check-linux-k1` boots the kernel through),
@@ so it is entered exactly like the kernel image: PTW is already on and PTBR
@@ points at the prebuilt table, which maps exactly ONE 512 MiB superpage at the
@@ kernel-window base with `VA = PA + BIAS` (spec/Kaiwu §6.3, contract
@@ `contracts/linux-boot.yaml`).
@@
@@ Consequence used by this probe: every datum below lives at `PA < 512 MiB`, so
@@ its PA, *taken as a VA*, is outside the mapped superpage and therefore
@@ unmapped.  Handing semihosting the PA is exactly the "read from the PA of an
@@ unmapped VA" case required by spec/Kaiwu §5.2 and contract-semihosting
@@ §2 ("指针一律为 PA，不经页表翻译"):
@@   * a responder that walks the page table faults on it (bug),
@@   * a responder that reads physical memory does not.
@@
@@ Self-checks (guest side, before any I/O; a failure is a distinct exit code so
@@ the gate can never mistake a broken *setup* for a broken responder):
@@   0xE1  PTE[PAYLOAD_PA >> 29] != 0  -> the PA is mapped as a VA, the probe
@@         would not be testing the PA path at all (all data share that index)
@@   0xE2  PTE[ENTRY_VA >> 29] has P == 0 -> the payload's *VA* is not mapped,
@@         so the probe could not even be loaded/run on the table
@@
@@ Console expectation is derived from this file by the gate (the `.ascii`
@@ payloads below, in file order): [0] SYS_WRITE0 string, [1] SYS_WRITEC
@@ characters, [2] SYS_OPEN success marker, [3] SYS_OPEN failure marker,
@@ [4] the file name handed to SYS_OPEN, then everything after it concatenated
@@ = the SYS_WRITE0 long string (m14-qemu-007).  Never from QEMU's own output:
@@   SYS_WRITE0 (0x04, string pointer = PAYLOAD_PA)   -> "W0PAOK\n"
@@   SYS_WRITE0 (0x04, string pointer = LONG_PA)      -> 640 bytes (> 2 x the
@@     responder's 256-byte block read, and the string starts 48 bytes into such
@@     a block) — the length probe must cross block boundaries and return the
@@     exact length; a truncated measurement shows up as a byte-exact mismatch
@@   SYS_WRITEC (0x03, char pointers  = charset PAs)  -> "XYZ"
@@   SYS_OPEN   (0x01, block {name PA, mode 0, len 0}) -> "+" (handle >= 0)
@@                                                       or "-" (EFAULT)
@@ Exit: SYS_EXIT (0x18) with block pointer = EXIT_BLOCK_PA, code 0.
@@
@@ --defsym inputs (all derived by `check_k1.py` from the contract / this file;
@@ none of them is a literal in the body):
@@   ENTRY_VA          kernel-window base VA (contract: kernel.start)
@@   PAYLOAD_PA/VA     SYS_WRITE0 string VA (mapped) and its PA (unmapped as VA)
@@   LONG_PA           PA of the SYS_WRITE0 long string (same "unmapped as VA"
@@                     rule; longer than the responder's block read)
@@   CHARSET_PA        PA of the first SYS_WRITEC character ("XYZ")
@@   MARK_OK_PA        PA of the SYS_OPEN success marker
@@   MARK_BAD_PA       PA of the SYS_OPEN failure marker
@@   PATH_PA           PA of the SYS_OPEN file name (":tt", the semihosting
@@                     console name the responder special-cases)
@@   OPEN_BLOCK_PA/VA  SYS_OPEN argument block {name pointer, mode, length}
@@   EXIT_BLOCK_PA/VA  SYS_EXIT block, again addressed by PA
@@   PT_VA             VA of the prebuilt page table (PA 0)
@@   PA_PTE_INDEX      PAYLOAD_PA >> 29   (L1 index of the data *as a VA*)
@@   ENTRY_PTE_INDEX   ENTRY_VA   >> 29   (L1 index that must be present)

	.include "tests/shared/asm/machine.inc"

	.macro	LD64 rd, w0, w1, w2, w3
	set.zw	\rd, wp0, \w0
	.if \w1 != 0
	or.w	\rd, wp1, \w1
	.endif
	.if \w2 != 0
	or.w	\rd, wp2, \w2
	.endif
	.if \w3 != 0
	or.w	\rd, wp3, \w3
	.endif
	.endm

	.text
	.globl	_start

_start:
	@@ ---- self-check A: the data PA, read as a VA, is NOT mapped ---------
	LOAD_ADDR rb4, PT_VA + PA_PTE_INDEX * 8
	ld.o	rd5, [rb4, 0]
	br.z	{rd5}?, [rb0, sc_a_ok]
	set.rd	rd1, 0x0E1
	jump	[rb0, sp_exit]
sc_a_ok:

	@@ ---- self-check B: the payload's VA *is* mapped (P = bit 0) ---------
	LOAD_ADDR rb4, PT_VA + ENTRY_PTE_INDEX * 8
	ld.o	rd6, [rb4, 0]
	set.rd	rd2, 0x1
	and.o	rd7, rd6, rd2
	br.nz	{rd7}?, [rb0, sc_b_ok]
	set.rd	rd1, 0x0E2
	jump	[rb0, sp_exit]
sc_b_ok:

	@@ ---- SYS_WRITE0 (0x04): NUL-terminated string, pointer = its PA ------
	LOAD_ADDR rb16, PAYLOAD_PA
	set.zw	rd16, wp0, 0x0004
	trap	cfx_umon, 0x3FF00

	@@ ---- SYS_WRITE0 (0x04) again: the long string (m14-qemu-007) -------
	@@ Same pointer rule (PA of data whose PA-as-VA is unmapped), but the text
	@@ is longer than the responder's 256-byte block read and starts 48 bytes
	@@ into such a block, so a page-table walk or a truncated measurement
	@@ (first block only / window cut short) cannot produce it byte-exactly.
	LOAD_ADDR rb16, LONG_PA
	set.zw	rd16, wp0, 0x0004
	trap	cfx_umon, 0x3FF00

	@@ ---- SYS_WRITEC (0x03) x3: one character, pointer = its PA ----------
	LOAD_ADDR rb16, CHARSET_PA
	set.zw	rd16, wp0, 0x0003
	trap	cfx_umon, 0x3FF00
	LOAD_ADDR rb16, CHARSET_PA + 1
	set.zw	rd16, wp0, 0x0003
	trap	cfx_umon, 0x3FF00
	LOAD_ADDR rb16, CHARSET_PA + 2
	set.zw	rd16, wp0, 0x0003
	trap	cfx_umon, 0x3FF00

	@@ ---- SYS_OPEN (0x01): name given only by pointer (length field 0) ---
	@@ The name pointer, the argument block and the name itself are all PAs;
	@@ the responder must measure + read the name physically (it is not a
	@@ mapped VA here), i.e. `lock_user_string` must not walk the page table.
	LOAD_ADDR rb4, OPEN_BLOCK_VA
	LOAD_ADDR rb5, PATH_PA
	rb2rd	rd5, rb5, 1
	st.o	rd5, [rb4, 0]			@@ file name pointer = PA
	set.rd	rd2, 0
	st.o	rd2, [rb4, 8]			@@ mode 0 = "r"
	st.o	rd2, [rb4, 16]			@@ length 0 = "measure it"
	LOAD_ADDR rb16, OPEN_BLOCK_PA
	set.zw	rd16, wp0, 0x0001
	trap	cfx_umon, 0x3FF00
	@@ rd8 = guest handle (>= 0) on success, -1 (EFAULT) on a bad pointer.
	LD64	rd3, 0xFFFF, 0xFFFF, 0xFFFF, 0xFFFF
	cmp.uo	rd4, rd8, rd3
	br.z	{rd4}?, [rb0, sp_open_fail]
	LOAD_ADDR rb16, MARK_OK_PA
	set.zw	rd16, wp0, 0x0003
	trap	cfx_umon, 0x3FF00
	jump	[rb0, sp_open_done]
sp_open_fail:
	LOAD_ADDR rb16, MARK_BAD_PA
	set.zw	rd16, wp0, 0x0003
	trap	cfx_umon, 0x3FF00
sp_open_done:

	@@ ---- all good ------------------------------------------------------
	set.rd	rd1, 0

sp_exit:
	@@ SYS_EXIT (0x18): block {reason, code}, pointer handed over as its PA.
	LOAD_ADDR rb4, EXIT_BLOCK_VA
	LD64	rd2, 0x0026, 0x0002, 0x0000, 0x0000	@@ ADP_Stopped_ApplicationExit
	st.o	rd2, [rb4, 0]
	st.o	rd1, [rb4, 8]
	LOAD_ADDR rb16, EXIT_BLOCK_PA
	set.zw	rd16, wp0, 0x0018
	trap	cfx_umon, 0x3FF00
	swym	0
	jump	[rb0, sp_exit]

	@@ ---- console payloads at fixed offsets from ENTRY_VA ----------------
	@@ Fixed offsets (not symbol-relative arithmetic) keep the immediates
	@@ above independent of the linked image's size; the gate asserts every
	@@ `sp_*` symbol resolves to the offset it passed to --defsym.
	.org	0x800
sp_payload:
	.ascii	"W0PAOK\n"
	.dd.b08	0
	.org	0x810
sp_chars:
	.ascii	"XYZ"
	.org	0x820
sp_mark_ok:
	.ascii	"+"
	.org	0x828
sp_mark_bad:
	.ascii	"-"

	.org	0x900
sp_exit_block:
	.dd.o64	0
	.dd.o64	0
	.org	0x940
sp_open_block:
	.dd.o64	0
	.dd.o64	0
	.dd.o64	0
	.org	0x980
sp_path:
	.ascii	":tt"
	.dd.b08	0

	@@ ---- the SYS_WRITE0 long string (m14-qemu-007) ---------------------
	@@ 640 bytes = 2.5 x the responder's 256-byte block read, starting 48
	@@ bytes into the first block: the length probe must join three block
	@@ reads.  No "+"/"-" so the SYS_OPEN markers stay findable.
	.org	0x1030
sp_long:
	.ascii	"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
	.ascii	"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
	.ascii	"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
	.ascii	"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
	.ascii	"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
	.dd.b08	0
