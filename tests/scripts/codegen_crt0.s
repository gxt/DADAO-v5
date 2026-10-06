; codegen_crt0.s — minimal freestanding startup stub for the M3 CodeGen E2E gate
; (INTEG-012t).
;
; This stub is concatenated *ahead* of the llc-generated program `.s`
; (`cat codegen_crt0.s prog.s` -> one `.s`), and the combined **single
; translation unit** is assembled with llvm-mc -- there is no linker
; (ADR-0003 D5: single-TU, self-contained, in-place label resolution).
;
; Entry / exit channel frozen with tests/llvm/codegen/expected.yaml:
;   * every program defines `define i64 @main()`;
;   * `_start` sets up the stack pointer (rb1), calls `@main`; the returned
;     value arrives in rd31 (ABI C5);
;   * `_start` writes that value to the exit port `0xffff_8000_0000`
;     (ADR-0004 D3) and halts;
;   * the **guest process exit code** is the low byte of that written value.
;
; Entry state (ADR-0004 D6.5): rb0 = 0xffff_0000_0000 (PC),
;   rb1 = 0xffff_00ff_0000 (SP; also set by the ROM trampoline),
;   all other RD/RB/RA = 0, rf0 = 0x7FF8_0000_7FC0_0000.
;
; Register use: rb1 (SP) and rb16 (exit-port address).  rb16 is caller-saved,
; so the exit-port address is built *after* the call returns; building it
; before the call would let the callee clobber it.

	.text
	.globl	_start
_start:
	; 1. Stack pointer rbsp = rb1 = 0xffff_00ff_0000 (near the RAM top).
	set.zw	rb1, wp2, 0xffff
	or.w	rb1, wp1, 0x00ff

	; 2. Call the program entry point; the result returns in rd31.
	call	[rb0, main]

	; 3. Build exit-port address rb16 = 0xffff_8000_0000.
	set.zw	rb16, wp2, 0xffff
	or.w	rb16, wp1, 0x8000

	; 4. Write the 64-bit return value to the exit port (low byte = code).
	st.o	rd31, [rb16, 0]

	; 5. Halt (the exit-port store already halts the guest; kept as a guard).
	swym	0
