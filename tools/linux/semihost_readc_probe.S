@@ semihost_readc_probe.S — K1 gate probe: SYS_READC's scratch slot is a PA
@@ (ISS-452)
@@
@@ Runs on `-M kaiwu-vast` under the K1 firmware (`tests/ee-vast/*_k0_vast.*`, the
@@ same power -> hmon -> smon chain `check-linux-k1` boots through), so PTW is
@@ already on and PTBR points at the prebuilt table (VA = PA + 2 TiB over the
@@ kernel window, spec/Kaiwu §6.3 / contract `contracts/linux-boot.yaml`).
@@
@@ SYS_READC (0x07) takes no buffer argument: the responder stores the character
@@ it read into an internal slot derived from the stack pointer, then reads the
@@ byte back out of that slot and returns it.  Upstream puts that slot at
@@ `SP - 1` — correct only while SP lives in the semihosting pointer space.
@@ Here SP is a **VA** in the kernel window (exactly like the kernel's own early
@@ stack) while every semihosting pointer is a **PA** (spec/Kaiwu §5.2,
@@ contract-semihosting §2): the responder must name the *PA of that slot*, not
@@ the VA.  With the VA it reads 2 TiB beyond RAM and returns −1 (EFAULT).
@@
@@ The probe therefore sets rb1 (rbsp, contract-abi §2.1) to a kernel-window VA
@@ above its own 64 KiB image and asks for one character; the gate feeds a known
@@ byte on the semihosting console chardev and the guest must get exactly that
@@ byte back.
@@
@@ Self-checks (guest side, before any I/O; each failure is its own exit code,
@@ so the gate can never mistake a broken *setup* for a broken responder):
@@   0xE3  PTE[SCRATCH_VA >> 29] has P == 0 -> the slot's VA is not mapped, so
@@         the page-walk round trip the fix performs could not succeed anyway
@@   0xE5  SCRATCH_VA < 2^32 -> the slot's numeric value would still be a
@@         plausible PA (RAM is smaller), so the probe could not discriminate
@@   0xE4  SYS_READC returned something other than the fed byte (-1 = the
@@         responder could not name the slot: the ISS-452 bug)
@@
@@ Exit: SYS_EXIT (0x18) with block pointer = EXIT_BLOCK_PA, code 0 on success.
@@
@@ --defsym inputs (all derived by `check_k1.py` from the contract / this file;
@@ none of them is a literal in the body):
@@   ENTRY_VA          kernel-window base VA (contract: kernel.start)
@@   SCRATCH_VA        the SP this probe installs (VA, inside the mapped
@@                     superpage, above this image)
@@   SCRATCH_PTE_INDEX SCRATCH_VA >> 29  (L1 index that must be present)
@@   PT_VA             VA of the prebuilt page table (PA 0)
@@   EXPECT_CHAR       the byte the gate feeds on the console chardev (also the
@@                     literal in the image at sp_char, so the echo proves it)
@@   CHAR_PA           PA of that echoed character byte
@@   EXIT_BLOCK_PA/VA  SYS_EXIT block, addressed by PA


	.text
	.globl	_start

_start:
	@@ ---- the stack slot: a VA in the kernel window, like the kernel's ---
	@@ own early stack (its numeric value is NOT a PA -- self-check B).
	set.rb rb1, SCRATCH_VA

	@@ ---- self-check A: the slot's VA is mapped (PTE P = 1) --------------
	set.rb rb4, PT_VA + SCRATCH_PTE_INDEX * 8
	ld.o	rd5, [rb4, 0]
	br.nz	{rd5}?, [rb0, sc_a_ok]
	set.rd	rd1, 0x0E3
	jump	[rb0, readc_exit]
sc_a_ok:

	@@ ---- self-check B: SP >= 2^32, i.e. not a PA in this machine's RAM --
	@@ (the gate asserts RAM <= 2 GiB, so bit 32 set => SP as a PA is
	@@ outside RAM and the pre-fix responder must fault on it).
	rb2rd	rd6, rb1, 1
	set.rd rd3, 0xffffffff00000000	@@ 0xFFFF_FFFF_0000_0000
	and.o	rd7, rd6, rd3
	br.nz	{rd7}?, [rb0, sc_b_ok]
	set.rd	rd1, 0x0E5
	jump	[rb0, readc_exit]
sc_b_ok:

	@@ ---- SYS_READC (0x07): no argument, returns the character in rd8 ----
	set.zw	rd16, wp0, 0x0007
	trap	cfx_umon, 0x3FF00

	@@ rd8 must be exactly the byte the gate fed (a byte is 0..255; the
	@@ failure value is -1, which no 8-bit character can collide with).
	set.rd	rd3, EXPECT_CHAR
	cmp.uo	rd4, rd8, rd3
	br.z	{rd4}?, [rb0, readc_ok]
	set.rd	rd1, 0x0E4
	jump	[rb0, readc_exit]
readc_ok:
	set.rd	rd1, 0
	@@ Echo the character just read, so the gate sees the value on the
	@@ console as well (rd1 keeps the exit code; SYS_WRITEC returns nothing).
	set.rb rb16, CHAR_PA
	set.zw	rd16, wp0, 0x0003
	trap	cfx_umon, 0x3FF00

readc_exit:
	@@ SYS_EXIT (0x18): block {reason, code}, pointer handed over as its PA.
	set.rb rb4, EXIT_BLOCK_VA
	set.rd rd2, 0x0000000000020026	@@ ADP_Stopped_ApplicationExit
	st.o	rd2, [rb4, 0]
	st.o	rd1, [rb4, 8]
	set.rb rb16, EXIT_BLOCK_PA
	set.zw	rd16, wp0, 0x0018
	trap	cfx_umon, 0x3FF00
	swym	0
	jump	[rb0, readc_exit]

	@@ ---- exit block + echoed character, at fixed offsets from ENTRY_VA ---
	.org	0xA00
sp_exit_block:
	.dd.o64	0
	.dd.o64	0
	.org	0xB00
sp_char:
	.ascii	"K"
