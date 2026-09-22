# smoke_arith: E2E smoke test — add.si arithmetic
# Tests: set.zw (RD immediate), add.si (riii add-immediate), cmp.so (orrr compare)
# Exit code: 0x00 = PASS, 0x01 = FAIL
#
# NOTE: llvm-mc AsmParser bug — wpN named constants (wp0/wp1/wp2/wp3) are
#       silently ignored, always encoding wp0. Use numeric wyde positions
#       (0/1/2/3) as workaround. See LLVM-013t for tracking.
#
# Entry state (ADR-0004 D6.5):
#   rb0=0xffff_0000_0000 (PC), rb1=0xffff_00ff_0000 (SP), rb2=0xffff_0000_0000
#   rd0=0 (hardwired), all other rd/rb/ra = 0

_start:
    # 1. Construct exit port address rb3 = 0xffff_8000_0000
    set.zw  rb3, 2, 0xffff       # rb3[47:32] = 0xffff, rest = 0
    or.w    rb3, 1, 0x8000       # rb3[31:16] |= 0x8000 → 0x0000_ffff_8000_0000

    # 2. Arithmetic under test: rd1 = 42 + 7 = 49
    set.zw  rd1, 0, 42
    add.si  rd1, 7

    # 3. Expected value
    set.zw  rd2, 0, 49

    # 4. Compare: cmp.so rd3, rd1, rd2 → rd3 = 0 if equal
    cmp.so  rd3, rd1, rd2
    br.nz   rd3, Lfail

    # 5. PASS: write 0x00 → exit port
    #    rd3 = 0 from cmp.so equality result
    st.o    rd3, rb3, 0

Lfail:
    # 6. FAIL: write 0x01 → exit port
    set.zw  rd4, 0, 1
    st.o    rd4, rb3, 0
    swym    0
