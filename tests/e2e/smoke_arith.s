; smoke_arith: E2E smoke test — add.si arithmetic
; Tests: set.zw (RD immediate), add.si (riii add-immediate), cmp.so (orrr compare)
; Exit channel: semihosting SYS_EXIT (ADR-0020 D8; replaces the legacy MMIO halt device).
;   rd16 = service number 0x18 (SYS_EXIT); rb16 = argument-block pointer.
; Exit code: 0x00 = PASS, 0x01 = FAIL
;
; NOTE: the wyde position must be written as a named token wp0/wp1/wp2/wp3.
;       Bare numeric 0/1/2/3 is rejected by the assembler (Error); wpN is
;       encoded verbatim (LLVM-045t / ISS-128, superseding the old LLVM-013t note).
;
; Entry state (ADR-0004 D6.5):
;   rb0=0x0000_0000_0000 (PC), rb1=0x0000_0000_00ff_0000 (SP), rb2=0x0000_0000_0000
;   rd0=0 (hardwired), all other rd/rb/ra = 0

_start:
    ; 0. Build the SYS_EXIT argument block at rb16 = 0x0000_0000_00ff_f000.
    or.w    rb16, wp1, 0x00ff
    or.w    rb16, wp0, 0xf000
    set.zw  rd6, wp1, 0x0002
    or.w    rd6, wp0, 0x0026
    st.o    rd6, [rb16, 0]

    ; 1. Arithmetic under test: rd1 = 42 + 7 = 49
    set.zw  rd1, wp0, 42
    add.si  rd1, 7

    ; 2. Expected value
    set.zw  rd2, wp0, 49

    ; 3. Compare: cmp.so rd3, rd1, rd2 → rd3 = 0 if equal
    cmp.so  rd3, rd1, rd2
    br.nz   {rd3}?, [rb0, Lfail]

    ; 4. PASS: report 0x00 via SYS_EXIT (rd3 = 0 from cmp.so equality result)
    st.o    rd3, [rb16, 8]
    set.zw  rd16, wp0, 0x0018
    trap    cfx_umon, 0x30000

Lfail:
    ; 5. FAIL: report 0x01 via SYS_EXIT
    set.zw  rd4, wp0, 1
    st.o    rd4, [rb16, 8]
    set.zw  rd16, wp0, 0x0018
    trap    cfx_umon, 0x30000
    swym    0
