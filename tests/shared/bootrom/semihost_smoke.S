@@ semihost_smoke.S — Machine-v5-Tiny semihosting responder probe
@@ (m12-chipyard-004).
@@
@@ Runs unchanged on QEMU `dadao-tiny`, gem5 FS `tiny` and the chipyard
@@ `WumingTinyConfig` harness: the same ELF is loaded into the SRAM window and
@@ starts at the profile entry.  It exercises the five services implemented by
@@ the harness responder (spec/Machine-v5 §5.3):
@@
@@   SYS_WRITE0 (0x04)  long UTF-8 message -> stdout, byte-exact, no truncation
@@   SYS_WRITEC (0x03)  one character       -> stdout
@@   SYS_WRITE  (0x05)  64-byte buffer      -> stdout (handle 1)
@@   SYS_CLOCK  (0x10)  twice; the responder must report non-decreasing values
@@   SYS_EXIT   (0x18)  {ADP_Stopped_ApplicationExit, EXIT_CODE}
@@
@@ Every instruction is part of the temporary `WumingCoreStub` subset
@@ (set.zw/or.w/st.o/trap); no branches are needed.  The service number is
@@ carried in rd16 and the argument/parameter-block pointer in rb16
@@ (contract-semihosting §2); the trap tag is 0x3FF00+op (contract §1).
@@
@@ Build variants (Makefile `build-bootrom`; all three symbols always given):
@@   SEMIHOST_WRITE=0 EXIT_CODE=0x00 SEMIHOST_UNIMPL=0
@@                                             semihost_smoke.elf    (3-platform)
@@   SEMIHOST_WRITE=0 EXIT_CODE=0x40 SEMIHOST_UNIMPL=0
@@                                             semihost_fail.elf     (guest FAIL)
@@   SEMIHOST_WRITE=0 EXIT_CODE=0x00 SEMIHOST_UNIMPL=1
@@                                             semihost_unimpl.elf   (SYS_OPEN)
@@   SEMIHOST_WRITE=1 EXIT_CODE=0x00 SEMIHOST_UNIMPL=0
@@                                             semihost_write.elf    (SYS_WRITE)
@@ The unimpl variant must make a harness responder report the unimplemented
@@ service number instead of silently returning 0.  SYS_WRITE is split into its
@@ own image because gem5's generic responder crashes on raw stdout handle 1
@@ (`files[1]` is out of bounds when no file was SYS_OPENed); the 3-platform
@@ image therefore exercises only services all three engines serve correctly.

	.include "tests/shared/asm/machine-tiny.inc"
	.include "tests/shared/asm/machine.inc"

@@ Fixed placement (kept in sync by semihost_smoke.lds ASSERTs):
@@   .text     ENTRY + 0x000   (<= 0x400)
@@   BUF       ENTRY + 0x400   (64 bytes, payload of SYS_WRITE)
@@   EXCL      ENTRY + 0x440   (one character for SYS_WRITEC)
@@   MSG       ENTRY + 0x448   (NUL-terminated message for SYS_WRITE0)
@@   BLOCK     ENTRY + 0x2000  (SYS_WRITE parameter block: handle/buf/len)
@@   EXITBLK   ENTRY + 0x2100  (SYS_EXIT parameter block: reason/code)
	.equ	BUF, ENTRY + 0x400
	.equ	EXCL, ENTRY + 0x440
	.equ	MSG, ENTRY + 0x448
	.equ	BLOCK, ENTRY + 0x2000
	.equ	EXITBLK, ENTRY + 0x2100

	.text
	.globl	_start
_start:
	@@ 1. SYS_WRITE0: 64-bit pointer in rb16, service 0x04 in rd16.
	LOAD_ADDR rb16, MSG
	set.zw	rd16, wp0, 0x0004
	trap	cfx0, 0x3FF04

	@@ 2. SYS_WRITEC: one character.
	LOAD_ADDR rb16, EXCL
	set.zw	rd16, wp0, 0x0003
	trap	cfx0, 0x3FF03

	@@ 3. SYS_WRITE: parameter block {handle=1, buffer, length=64}.
	.if SEMIHOST_WRITE
	LOAD_ADDR rb4, BLOCK
	set.zw	rd5, wp0, 0x0001
	st.o	rd5, [rb4, 0]
	LOAD_ADDR rd6, BUF
	st.o	rd6, [rb4, 8]
	set.zw	rd7, wp0, 0x0040
	st.o	rd7, [rb4, 16]
	LOAD_ADDR rb16, BLOCK
	set.zw	rd16, wp0, 0x0005
	trap	cfx0, 0x3FF05
	.endif

	@@ 4. SYS_CLOCK twice: the responder (and the spec) require monotonic
	@@    centiseconds; both values are also visible in the responder log.
	set.zw	rb16, wp0, 0x0000
	set.zw	rd16, wp0, 0x0010
	trap	cfx0, 0x3FF10
	trap	cfx0, 0x3FF10

	@@ 5. Optional unimplemented service (SYS_OPEN 0x01): must be a loud error.
	.if SEMIHOST_UNIMPL
	set.zw	rb16, wp0, 0x0000
	set.zw	rd16, wp0, 0x0001
	trap	cfx0, 0x3FF01
	.endif

	@@ 6. SYS_EXIT: {0x20026 ADP_Stopped_ApplicationExit, EXIT_CODE}.
	LOAD_ADDR rb16, EXITBLK
	set.zw	rd4, wp1, 0x0002
	or.w	rd4, wp0, 0x0026
	st.o	rd4, [rb16, 0]
	set.zw	rd5, wp0, (EXIT_CODE & 0xFFFF)
	st.o	rd5, [rb16, 8]
	set.zw	rd16, wp0, 0x0018
	trap	cfx0, 0x3FF18

	@@ Never reached: a responder that lets SYS_EXIT return is broken.
	.dd.t32	0x00000000

	.section .rodata
	.p2align 3
BUF:
	.ascii	"0123456789ABCDEF0123456789ABCDEF"
	.ascii	"0123456789ABCDEF0123456789ABCDEF"
EXCL:
	.ascii	"!"
	.p2align 3
MSG:
	.include "tests/shared/bootrom/semihost_msg.inc"

	.section .bss
	.p2align 3
	.space	0x200
