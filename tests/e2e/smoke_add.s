# smoke_add: E2E smoke test — RD arithmetic + XOR+ORR comparison
# Tests: set.zw (RD immediate), add.si (riii add-immediate),
#        xor.o (orrr XOR — MISC-octa), or.o (orrr OR — MISC-octa)
# Comparison pattern: XOR+ORR (ADR-0009 D2)
# Exit code: 0x00 = PASS, 0x01 = FAIL
#
# NOTE: llvm-mc AsmParser bug — wpN named constants are silently ignored,
#       always encoding wp0. Use numeric wyde positions (0/1/2/3) instead.
#
# Entry state (ADR-0004 D6.5):
#   rb0=0xffff_0000_0000 (PC), rb1=0xffff_00ff_0000 (SP), rb2=0xffff_0000_0000
#   rd0=0 (hardwired), all other rd/rb/ra = 0

_start:
    # 1. Construct exit port address rb3 = 0xffff_8000_0000
    set.zw  rb3, 2, 0xffff
    or.w    rb3, 1, 0x8000

    # 2. Load two immediates
    set.zw  rd1, 0, 100
    set.zw  rd2, 0, 55

    # 3. RD arithmetic: rd1 = 100 + (-45) = 55
    add.si  rd1, -45

    # 4. XOR+ORR comparison (ADR-0009 D2):
    #    xor.o → rd3 = rd1 XOR rd2 = 0 if equal
    #    or.o  → fold/accumulate (identity for rd0=0; multi-field: OR multiple XORs)
    xor.o   rd3, rd1, rd2
    or.o    rd3, rd3, rd0

    # 5. Map XOR result to exit code: 0 → PASS, non-zero → FAIL
    br.nz   rd3, Lfail

    # 6. PASS: write 0x00 → exit port (rd3 = 0 from XOR equality)
    st.o    rd3, rb3, 0

Lfail:
    # 7. FAIL: write 0x01 → exit port
    set.zw  rd4, 0, 1
    st.o    rd4, rb3, 0
    swym    0
