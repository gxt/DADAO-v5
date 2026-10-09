; smoke_jump: E2E smoke test — jump-iiii skips error path
; Tests: jump-iiii (iiii unconditional jump), set.zw, st.o
; The jump must skip the error path; if it fails, error path reports 0x01.
; Exit channel: semihosting SYS_EXIT (ADR-0020 D8; replaces the legacy MMIO halt device).
;   rd16 = service number 0x18 (SYS_EXIT); rb16 = argument-block pointer.
; Exit code: 0x00 = PASS (jump succeeded), 0x01 = FAIL (jump failed)
;
; NOTE: the wyde position must be written as a named token wp0/wp1/wp2/wp3.
;       Bare numeric 0/1/2/3 is rejected by the assembler (Error), and wpN is
;       encoded verbatim (LLVM-045t / ISS-128).
;
; Layout:
;   [0x00] or.w   rb16, wp1, 0x00ff   ; build SYS_EXIT block address (RAM@0)
;   [0x04] or.w   rb16, wp0, 0xf000   ; rb16 = 0x0000_0000_00ff_f000
;   [0x08] set.zw rd6, wp1, 0x0002    ; block[0] = 0x20026
;   [0x0C] or.w   rd6, wp0, 0x0026
;   [0x10] st.o   rd6, [rb16, 0]
;   [0x14] set.zw rd5, wp0, 0         ; prepare PASS value (0) in rd5
;   [0x18] set.zw rd4, wp0, 1         ; prepare FAIL value (1) in rd4
;   [0x1C] jump   [rb0, Lpass]        ; skip 3 instructions → land on Lpass
;   [0x20] st.o   rd4, [rb16, 8]      ; Lfail: report 0x01 (SKIPPED by jump)
;   [0x24] set.zw rd16, wp0, 0x0018   ; Lfail: SYS_EXIT (SKIPPED)
;   [0x28] trap   cfx_umon, 0x30000   ; Lfail: semihosting trap (SKIPPED)
;   [0x2C] st.o   rd5, [rb16, 8]      ; Lpass: report 0x00 (land here)
;   [0x30] set.zw rd16, wp0, 0x0018   ; Lpass: SYS_EXIT
;   [0x34] trap   cfx_umon, 0x30000   ; Lpass: semihosting trap
;
; jump-iiii: Addr = rb0 + (imms24 << 2), rb0 = current instruction address.
;   The jump target is the `Lpass` label (the assembler computes the offset),
;   so it skips the three error-path instructions.
;
; Entry state (ADR-0004 D6.5):
;   rb0=0x0000_0000_0000 (PC), rb1=0x0000_0000_00ff_0000 (SP), rb2=0x0000_0000_0000
;   rd0=0 (hardwired), all other rd/rb/ra = 0

_start:
    ; 1. Build the SYS_EXIT argument block at rb16 = 0x0000_0000_00ff_f000.
    or.w    rb16, wp1, 0x00ff
    or.w    rb16, wp0, 0xf000
    set.zw  rd6, wp1, 0x0002
    or.w    rd6, wp0, 0x0026
    st.o    rd6, [rb16, 0]

    ; 2. Prepare PASS value in rd5 (0) and FAIL value in rd4 (1)
    set.zw  rd5, wp0, 0
    set.zw  rd4, wp0, 1

    ; 3. Jump over the error path (skip to Lpass)
    jump    [rb0, Lpass]

Lfail:
    ; 4. Error path (skipped by jump): report 0x01 via SYS_EXIT
    st.o    rd4, [rb16, 8]
    set.zw  rd16, wp0, 0x0018
    trap    cfx_umon, 0x30000

Lpass:
    ; 5. PASS path: report 0x00 via SYS_EXIT
    st.o    rd5, [rb16, 8]
    set.zw  rd16, wp0, 0x0018
    trap    cfx_umon, 0x30000
    swym    0
