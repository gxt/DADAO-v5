; p2align_e2e.s -- LLVM-075t (ISS-182) end-to-end vector.
;
; A `.text`-internal `.p2align` is assembled and linked with the freestanding
; crt0 (`tests/scripts/codegen_crt0.s`) by ld.lld, then run on qemu-system-dadao.
; crt0 calls `main` and reports the returned value (rd8) through the semihosting
; SYS_EXIT service; the guest process exit code is main's low byte.
;
; `main` deliberately falls through two `.p2align 4` paddings before returning,
; so the emitted padding MUST be a legal instruction sequence (the canonical
; `swym 0` NOP), not zero/UNDI bytes.  It returns 0 on success.
;
; `globl main` because it is referenced from the separately assembled crt0.o.

	.text
	.globl	main
main:
	.p2align 4
	swym	0
	.p2align 4
	set.zw	rd8, wp0, 0
	ret	rd0, 0
