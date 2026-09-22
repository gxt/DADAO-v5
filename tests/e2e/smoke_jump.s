# smoke_jump: E2E smoke test — jump-iiii skips error path
# Tests: jump-iiii (iiii unconditional jump), set.zw, st.o
# The jump must skip the error path; if it fails, error path writes 0x01.
# Exit code: 0x00 = PASS (jump succeeded), 0x01 = FAIL (jump failed)
#
# NOTE: llvm-mc AsmParser bug — wpN named constants are silently ignored,
#       always encoding wp0. Use numeric wyde positions (0/1/2/3) instead.
#
# Layout:
#   [0x00] set.zw rb3, 2, 0xffff     ; construct exit port addr
#   [0x04] or.w   rb3, 1, 0x8000     ; rb3 = 0xffff_8000_0000
#   [0x08] set.zw rd5, 0, 0          ; prepare PASS value (0) in rd5
#   [0x0C] set.zw rd4, 0, 1          ; prepare FAIL value (1) in rd4
#   [0x10] jump   2                   ; skip 1 instruction → PC = 0x10 + 2*4 = 0x18
#   [0x14] st.o   rd4, rb3, 0        ; Lfail: write 0x01 (SKIPPED by jump)
#   [0x18] st.o   rd5, rb3, 0        ; Lpass: write 0x00 (land here)
#
# jump-iiii: Addr = rb0 + (imms24 << 2), rb0 = current instruction address
#   At 0x10: Addr = 0x10 + (2 << 2) = 0x10 + 8 = 0x18 → Lpass ✓
#
# Entry state (ADR-0004 D6.5):
#   rb0=0xffff_0000_0000 (PC), rb1=0xffff_00ff_0000 (SP), rb2=0xffff_0000_0000
#   rd0=0 (hardwired), all other rd/rb/ra = 0

_start:
    # 1. Construct exit port address rb3 = 0xffff_8000_0000
    set.zw  rb3, 2, 0xffff
    or.w    rb3, 1, 0x8000

    # 2. Prepare PASS value in rd5 (0) and FAIL value in rd4 (1)
    set.zw  rd5, 0, 0
    set.zw  rd4, 0, 1

    # 3. Jump over error path: jump 2 → skip 1 instruction → land at Lpass
    jump    2

Lfail:
    # 4. Error path (skipped by jump): write 0x01
    st.o    rd4, rb3, 0

Lpass:
    # 5. PASS path: write 0x00 → exit port
    st.o    rd5, rb3, 0
    swym    0
