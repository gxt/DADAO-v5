; codegen_crt0.s — minimal freestanding startup stub for the M3 CodeGen E2E gate
; (INTEG-012t) and the M4 ELF gate (INTEG-016t).
;
; This stub is concatenated *ahead* of the llc-generated program `.s`
; (`cat codegen_crt0.s prog.s` -> one `.s`), and the combined **single
; translation unit** is assembled with llvm-mc -- there is no linker
; (ADR-0003 D5: single-TU, self-contained, in-place label resolution).  The
; M4 ELF gate assembles this same stub to `crt0.o` and links it with ld.lld.
;
; Entry / exit channel frozen with tests/llvm/codegen/expected.yaml:
;   * every program defines `define i64 @main()`;
;   * `_start` sets up the stack pointer (rb1), calls `@main`; the returned
;     value arrives in rd8 (ABI §返回值, M6 contract-abi.md §6.1);
;   * `_start` reports that value through the semihosting `SYS_EXIT` service
;     (ADR-0020 D8: SYS_EXIT replaces the legacy MMIO halt device, ADR-0004 `D3` superseded);
;   * the **guest process exit code** is the low byte of that value.
;
; SYS_EXIT protocol (contract-semihosting.md §3/§5):
;   * the argument block is 64-bit big-endian {reason, exit code};
;   * reason = ADP_Stopped_ApplicationExit (0x20026) selects a normal exit and
;     the second field becomes the process exit status;
;   * rd16 = service number 0x18 (SYS_EXIT), rb16 = argument-block pointer;
;   * `trap cfx_umon, 0x30000` (immu18[17:16] == 2'b11) is the semihosting tag.
;   The harness must run QEMU with `-semihosting-config enable=on,target=native`
;   (ADR-0020 D7: native is explicitly enabled by the test harness).
;
; Entry state (ADR-0004 D6.5): rb0 = 0xffff_0000_0000 (PC),
;   rb1 = 0xffff_00ff_0000 (SP; also set by the ROM trampoline),
;   all other RD/RB/RA = 0, rf0 = 0x7FF8_0000_7FC0_0000.
;
; Register use: rb1 (SP), rb16 (argument-block pointer) and rd16 (block field
;   temp, then the SYS_EXIT service number).  All of them are caller-saved, so
;   the block is built *after* the call returns (building it before the call
;   would let the callee clobber it).  The block lives near the top of RAM
;   (0xffff_00ff_f000, above the downward-growing stack).

	.text
	.globl	_start
_start:
	; 1. Stack pointer rbsp = rb1 = 0xffff_00ff_0000 (near the RAM top).
	set.zw	rb1, wp2, 0xffff
	or.w	rb1, wp1, 0x00ff

	; 2. Call the program entry point; the result returns in rd8 (M6).
	call	[rb0, main]

	; 3. Build the SYS_EXIT argument block at rb16 = 0xffff_00ff_f000:
	;    block[0] = 0x20026 (ADP_Stopped_ApplicationExit).
	set.zw	rb16, wp2, 0xffff
	or.w	rb16, wp1, 0x00ff
	or.w	rb16, wp0, 0xf000
	set.zw	rd16, wp1, 0x0002
	or.w	rd16, wp0, 0x0026
	st.o	rd16, [rb16, 0]

	; 4. block[1] = @main return value (low byte = guest exit code).
	st.o	rd8, [rb16, 8]

	; 5. rd16 = 0x18 (SYS_EXIT); trap with the semihosting tag.
	set.zw	rd16, wp0, 0x0018
	trap	cfx_umon, 0x30000

	; 6. SYS_EXIT never returns; kept as a guard.
	swym	0
