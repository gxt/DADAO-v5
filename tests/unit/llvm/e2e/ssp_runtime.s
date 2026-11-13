@@ ssp_runtime.s -- the two stack-protector externals the compiler only declares
@@ (m14-llvm-002).  The backend emits external references to
@@
@@   __stack_chk_guard   pointer-width (8-byte) data object; the prologue loads
@@                       it and the epilogue compares the frame copy against it.
@@   __stack_chk_fail    void(void), noreturn; entered when the check fails.
@@
@@ and never defines them: the definition belongs to the runtime (the Linux
@@ kernel's CONFIG_STACKPROTECTOR path, picolibc's libc/ssp, musl).  This file
@@ is the minimal link-time provider for the E2E vector only; it is not part of
@@ the toolchain.
@@
@@ The guard is a non-zero .data constant, so a frame slot the compiler forgot
@@ to initialise still mismatches.  The fail path reports through semihosting
@@ SYS_EXIT with code 66 (0x42), reusing the crt0 handshake:
@@ block[0] = ADP_Stopped_ApplicationExit (0x20026), block[1] = exit code,
@@ trap cfx0, 0x3FF00.

	.section	.data,"aw"
	.p2align 3
	.globl	__stack_chk_guard
__stack_chk_guard:
	.dd.o64	0x0123456789abcdef

	.section	.text,"ax"
	.globl	__stack_chk_fail
__stack_chk_fail:
	set.rb	rb16, __exit_block
	set.zw	rd16, wp1, 0x0002
	or.w	rd16, wp0, 0x0026
	st.o	rd16, [rb16, 0]

	set.zw	rd16, wp0, 0x0042
	st.o	rd16, [rb16, 8]

	set.zw	rd16, wp0, 0x0018
	trap	cfx0, 0x3FF00
	swym	0
