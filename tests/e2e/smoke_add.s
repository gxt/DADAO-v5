; smoke_add: E2E smoke test — RD arithmetic + XOR+ORR comparison
; Tests: set.zw (RD immediate), add.si (riii add-immediate),
;        xor.o (orrr XOR — MISC-octa), or.o (orrr OR — MISC-octa)
; Comparison pattern: XOR+ORR (ADR-0009 D2)
; Exit channel: semihosting SYS_EXIT (ADR-0020 D8; replaces the legacy MMIO halt device).
;   rd16 = service number 0x18 (SYS_EXIT); rb16 = argument-block pointer.
; Exit code: 0x00 = PASS, 0x01 = FAIL
;
; NOTE: the wyde position must be written as a named token wp0/wp1/wp2/wp3.
;       Bare numeric 0/1/2/3 is rejected by the assembler (Error), and wpN is
;       encoded verbatim (no longer silently ignored).
;
; Entry state (ADR-0004 D6.5):
;   rb0=0x0000_0000_0000 (PC), rb1=0x0000_0000_00ff_0000 (SP), rb2=0x0000_0000_0000
;   rd0=0 (hardwired), all other rd/rb/ra = 0

_start:
    ; 0. Build the SYS_EXIT argument block at rb16 = 0x0000_0000_00ff_f000:
    ;    block[0] = 0x20026 (ADP_Stopped_ApplicationExit).
    or.w    rb16, wp1, 0x00ff
    or.w    rb16, wp0, 0xf000
    set.zw  rd6, wp1, 0x0002
    or.w    rd6, wp0, 0x0026
    st.o    rd6, [rb16, 0]

    ; 1. Load two immediates
    set.zw  rd1, wp0, 100
    set.zw  rd2, wp0, 55

    ; 2. RD arithmetic: rd1 = 100 + (-45) = 55
    add.si  rd1, -45

    ; 3. XOR+ORR comparison (ADR-0009 D2):
    ;    xor.o → rd3 = rd1 XOR rd2 = 0 if equal
    ;    or.o  → fold/accumulate (identity for rd0=0; multi-field: OR multiple XORs)
    xor.o   rd3, rd1, rd2
    or.o    rd3, rd3, rd0

    ; 4. Map XOR result to exit code: 0 → PASS, non-zero → FAIL
    br.nz   {rd3}?, [rb0, Lfail]

    ; 5. PASS: report 0x00 via SYS_EXIT (rd3 = 0 from XOR equality)
    st.o    rd3, [rb16, 8]
    set.zw  rd16, wp0, 0x0018
    trap    cfx_umon, 0x30000

Lfail:
    ; 6. FAIL: report 0x01 via SYS_EXIT
    set.zw  rd4, wp0, 1
    st.o    rd4, [rb16, 8]
    set.zw  rd16, wp0, 0x0018
    trap    cfx_umon, 0x30000
    swym    0
