; smoke_jump: E2E smoke test — jump-iiii skips error path
; Tests: jump-iiii (iiii unconditional jump), set.zw, st.o
; The jump must skip the error path; if it fails, error path writes 0x01.
; Exit code: 0x00 = PASS (jump succeeded), 0x01 = FAIL (jump failed)
;
; NOTE: the wyde position must be written as a named token wp0/wp1/wp2/wp3.
;       Bare numeric 0/1/2/3 is rejected by the assembler (Error), and wpN is
;       encoded verbatim (LLVM-045t / ISS-128).
;
; Layout:
;   [0x00] set.zw rb3, wp2, 0xffff   ; construct exit port addr
;   [0x04] or.w   rb3, wp1, 0x8000   ; rb3 = 0xffff_8000_0000
;   [0x08] set.zw rd5, wp0, 0        ; prepare PASS value (0) in rd5
;   [0x0C] set.zw rd4, wp0, 1        ; prepare FAIL value (1) in rd4
;   [0x10] jump   [rb0, 8]           ; skip 1 instruction → PC = 0x10 + 8 = 0x18
;   [0x14] st.o   rd4, [rb3, 0]     ; Lfail: write 0x01 (SKIPPED by jump)
;   [0x18] st.o   rd5, [rb3, 0]     ; Lpass: write 0x00 (land here)
;
; jump-iiii: Addr = rb0 + (imms24 << 2), rb0 = current instruction address
;   At 0x10: Addr = 0x10 + (8 >> 2 << 2) = 0x10 + 8 = 0x18 → Lpass ✓
;
; Entry state (ADR-0004 D6.5):
;   rb0=0xffff_0000_0000 (PC), rb1=0xffff_00ff_0000 (SP), rb2=0xffff_0000_0000
;   rd0=0 (hardwired), all other rd/rb/ra = 0

_start:
    ; 1. Construct exit port address rb3 = 0xffff_8000_0000
    set.zw  rb3, wp2, 0xffff
    or.w    rb3, wp1, 0x8000

    ; 2. Prepare PASS value in rd5 (0) and FAIL value in rd4 (1)
    set.zw  rd5, wp0, 0
    set.zw  rd4, wp0, 1

    ; 3. Jump over error path: jump [rb0, 8] → skip 1 instruction → land at Lpass
    jump    [rb0, 8]

Lfail:
    ; 4. Error path (skipped by jump): write 0x01
    st.o    rd4, [rb3, 0]

Lpass:
    ; 5. PASS path: write 0x00 → exit port
    st.o    rd5, [rb3, 0]
    swym    0
